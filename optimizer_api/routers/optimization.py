import time
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    CompareRequest, CompareResponse, AlgorithmResult,
    VehicleRoute, Direction, IEResponseData, BottleneckInfo,
    TimeShiftSuggestion
)
from strategies import STRATEGY_REGISTRY
from utils.resource_profiler import ResourceProfiler
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

router = APIRouter(prefix="/api/v1", tags=["Optimization"])
logger = logging.getLogger(__name__)

def _calculate_scheduled_times(
    routes: List[VehicleRoute],
    request: OptimizationRequest,
    distance_matrix: Dict[str, Dict[str, float]]
) -> List[VehicleRoute]:
    if not request.use_time_windows:
        return routes
    
    time_windows = request.get_time_windows()
    
    for route in routes:
        if not route.route_details:
            continue
        
        locations = []
        for step in route.route_details:
            if step.location1 not in locations:
                locations.append(step.location1)
            if step.location2 not in locations:
                locations.append(step.location2)
        
        if len(locations) > 2 and locations[0] == locations[-1]:
            locations = locations[:-1]
        
        arrival_times = {}
        
        if request.direction == Direction.PICKUP:
            target_minutes = None
            for loc in reversed(locations):
                if loc in time_windows:
                    target_minutes = time_windows[loc].latest
                    break
            
            if target_minutes is None and request.target_time:
                parts = request.target_time.split(":")
                target_minutes = int(parts[0]) * 60 + int(parts[1])
            
            if target_minutes is None:
                target_minutes = 9 * 60
            
            current_minutes = target_minutes
            arrival_times[locations[-1]] = _minutes_to_time(current_minutes)
            
            for i in range(len(locations) - 2, -1, -1):
                from_loc = locations[i]
                to_loc = locations[i + 1]
                
                travel_time = distance_matrix.get(from_loc, {}).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
                current_minutes -= travel_time
                arrival_times[from_loc] = _minutes_to_time(current_minutes)
            
            departure_minutes = current_minutes - request.offset_minutes
            route.departure_time = _minutes_to_time(max(0, departure_minutes))
            
        else:
            start_minutes = None
            for loc in locations:
                if loc in time_windows:
                    start_minutes = time_windows[loc].earliest
                    break
            
            if start_minutes is None and request.target_time:
                parts = request.target_time.split(":")
                start_minutes = int(parts[0]) * 60 + int(parts[1])
            
            if start_minutes is None:
                start_minutes = 14 * 60
            
            current_minutes = start_minutes
            arrival_times[locations[0]] = _minutes_to_time(current_minutes)
            route.departure_time = _minutes_to_time(current_minutes)
            
            for i in range(len(locations) - 1):
                from_loc = locations[i]
                to_loc = locations[i + 1]
                
                travel_time = distance_matrix.get(from_loc, {}).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
                current_minutes += travel_time
                arrival_times[to_loc] = _minutes_to_time(current_minutes)
        
        route.arrival_times = arrival_times
    
    return routes

def _minutes_to_time(minutes: float) -> str:
    """Convert minutes from midnight to HH:MM string.
    
    Clamps to valid range [00:00, 23:59] to handle overflow from
    backward/forward scheduling calculations.
    """
    total = max(0, min(int(minutes), 23 * 60 + 59))
    hours = total // 60
    mins = total % 60
    return f"{hours:02d}:{mins:02d}"

@router.post("/optimize", response_model=OptimizationResponse)
def optimize_route(request: OptimizationRequest) -> OptimizationResponse:
    algorithm_key = request.algorithm.lower()

    if algorithm_key not in STRATEGY_REGISTRY:
        available = list(set(s.name for s in STRATEGY_REGISTRY.values()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown algorithm '{algorithm_key}'. Available: {available}"
        )

    strategy = STRATEGY_REGISTRY[algorithm_key]

    if strategy is None:
        raise HTTPException(
            status_code=400,
            detail=f"Algorithm '{algorithm_key}' is not available — missing optional dependency (pyvrp/vroom package)"
        )

    try:
        start_time = time.time()
        time_windows = {}
        if request.use_time_windows:
            time_windows = request.get_time_windows()
        
        result = strategy.optimize(request)
        execution_time = time.time() - start_time
        result.execution_time_seconds = round(execution_time, 4)
        
        result.direction = request.direction
        result.time_windows_used = request.use_time_windows and len(time_windows) > 0
        
        if request.use_time_windows and result.success:
            distance_matrix = {}
            for route in result.routes:
                for step in route.route_details:
                    if step.location1 not in distance_matrix:
                        distance_matrix[step.location1] = {}
                    distance_matrix[step.location1][step.location2] = step.duration
            result.routes = _calculate_scheduled_times(result.routes, request, distance_matrix)

        profiler = ResourceProfiler(
            standard_sw_capacity=request.sw_capacity,
            standard_so_capacity=request.so_capacity,
            max_tour_duration=request.max_travel_time
        )

        students = request.students
        sw_count = sum(1 for s in students if s.disability_type == 'Sw')
        so_count = len(students) - sw_count

        standard_needs = profiler.calculate_standard_vehicle_needs(students, mode=request.direction.value)
        hourly_demand_raw = profiler.generate_hourly_demand(students)

        hourly_demand = {
            hour: {
                'pickup': { 'Sw': d.pickup_sw, 'So': d.pickup_so },
                'dropoff': { 'Sw': d.dropoff_sw, 'So': d.dropoff_so }
            }
            for hour, d in hourly_demand_raw.items()
        }

        available_vehicles = request.vehicles if request.vehicles else []
        bottlenecks_raw = profiler.identify_bottlenecks(
            hourly_demand_raw, available_vehicles, mode=request.direction.value
        )

        bottlenecks = [
            BottleneckInfo(
                time=b.hour, type=b.type, reason=b.description, affected_students=None
            ) for b in bottlenecks_raw
        ]

        bottleneck_hours = [b.hour for b in bottlenecks_raw if b.severity in ['high', 'medium']]
        shift_suggestions_raw = profiler.suggest_time_shifts(
            hourly_demand_raw, bottleneck_hours, slack_window_minutes=request.slack_window_minutes
        )

        time_shift_suggestions = [
            TimeShiftSuggestion(
                student_id=s.student_id, current_time=s.current_time,
                suggested_time=s.suggested_time, savings_vehicles=float(s.savings_vehicles)
            ) for s in shift_suggestions_raw
        ]

        result.ie_data = IEResponseData(
            standard_vehicles_needed=standard_needs.get('standard_vehicles_needed', 0),
            hourly_demand=hourly_demand, bottlenecks=bottlenecks,
            time_shift_suggestions=time_shift_suggestions
        )

        return result

    except Exception as e:
        logger.exception("Optimization endpoint failed")
        raise HTTPException(status_code=500, detail="Internal optimization error")

def _run_single_algorithm(algorithm_name: str, request: OptimizationRequest) -> AlgorithmResult:
    strategy = STRATEGY_REGISTRY.get(algorithm_name)
    if not strategy:
        return AlgorithmResult(
            algorithm=algorithm_name, success=False, total_vehicles=0,
            total_duration_minutes=0, execution_time_seconds=0, routes=[],
            error_message=f"Algorithm '{algorithm_name}' not found"
        )
    try:
        start_time = time.time()
        result = strategy.optimize(request)
        execution_time = time.time() - start_time
        return AlgorithmResult(
            algorithm=algorithm_name, success=result.success, total_vehicles=result.total_vehicles,
            total_duration_minutes=result.total_duration_minutes, execution_time_seconds=round(execution_time, 4),
            routes=result.routes, error_message=result.error_message
        )
    except Exception as e:
        logger.exception("Algorithm %s failed during compare", algorithm_name)
        return AlgorithmResult(
            algorithm=algorithm_name, success=False, total_vehicles=0,
            total_duration_minutes=0, execution_time_seconds=0, routes=[], error_message=f"Algorithm '{algorithm_name}' failed — check server logs"
        )

@router.post("/compare", response_model=CompareResponse)
def compare_algorithms(request: CompareRequest) -> CompareResponse:
    start_time = time.time()
    if request.algorithms:
        algorithms_to_run = [a.lower() for a in request.algorithms if a.lower() in STRATEGY_REGISTRY]
    else:
        algorithms_to_run = list(set(s.name for s in STRATEGY_REGISTRY.values()))

    if not algorithms_to_run:
        raise HTTPException(status_code=400, detail="No valid algorithms specified")

    opt_request = OptimizationRequest(
        algorithm=algorithms_to_run[0], students=request.students, depot=request.depot,
        max_travel_time=request.max_travel_time, sw_capacity=request.sw_capacity,
        so_capacity=request.so_capacity, direction=request.direction,
        use_time_windows=request.use_time_windows
    )

    results: List[AlgorithmResult] = []
    with ThreadPoolExecutor(max_workers=len(algorithms_to_run)) as pool:
        futures = []
        for algo in algorithms_to_run:
            future = pool.submit(_run_single_algorithm, algo, opt_request)
            futures.append((algo, future))
        for algo, future in futures:
            try:
                result = future.result(timeout=120)
                results.append(result)
            except Exception as e:
                results.append(AlgorithmResult(
                    algorithm=algo, success=False, total_vehicles=0,
                    total_duration_minutes=0, execution_time_seconds=0, routes=[], error_message=str(e)
                ))

    successful_results = [r for r in results if r.success]
    if successful_results:
        best = min(successful_results, key=lambda x: x.total_duration_minutes)
        fastest = min(successful_results, key=lambda x: x.execution_time_seconds)
    else:
        best = results[0] if results else None
        fastest = results[0] if results else None

    summary = {}
    for r in results:
        summary[r.algorithm] = {
            "total_vehicles": r.total_vehicles,
            "total_duration_minutes": round(r.total_duration_minutes, 2),
            "execution_time_seconds": round(r.execution_time_seconds, 4),
            "success": r.success
        }

    return CompareResponse(
        success=len(successful_results) > 0, results=results,
        best_algorithm=best.algorithm if best else "",
        fastest_algorithm=fastest.algorithm if fastest else "",
        summary=summary
    )

@router.post("/vehicle-calculator", response_model=OptimizationResponse)
def calculate_vehicles(request: OptimizationRequest) -> OptimizationResponse:
    return optimize_route(request)
