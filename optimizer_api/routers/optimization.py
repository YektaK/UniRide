import time
import json
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    CompareRequest, CompareResponse, AlgorithmResult,
    IEResponseData, BottleneckInfo,
    TimeShiftSuggestion, FeasibilityCertificateInfo
)
from strategies import STRATEGY_REGISTRY, get_available_strategy_names
from utils.resource_profiler import ResourceProfiler
from utils.scheduling import calculate_scheduled_times
from verification.response_certifier import certify_optimization_response

router = APIRouter(prefix="/api/v1", tags=["Optimization"])
logger = logging.getLogger(__name__)
_INVALID_CERTIFICATE_ERROR = "certification aborted: invalid certificate payload"
_UNAVAILABLE_CERTIFICATE_ERROR = "certification unavailable: algorithm produced no result"


def _typed_certificate(payload: dict | None) -> FeasibilityCertificateInfo:
    if payload is not None:
        try:
            return FeasibilityCertificateInfo.model_validate(payload)
        except Exception:
            logger.exception("Invalid feasibility certificate payload")
    return FeasibilityCertificateInfo(
        is_feasible=False,
        violation_count=0,
        violations=[],
        certify_error=(
            _INVALID_CERTIFICATE_ERROR
            if payload is not None
            else _UNAVAILABLE_CERTIFICATE_ERROR
        ),
    )

@router.post("/optimize", response_model=OptimizationResponse)
def optimize_route(request: OptimizationRequest) -> OptimizationResponse:
    algorithm_key = request.algorithm.lower()

    if algorithm_key not in STRATEGY_REGISTRY:
        available = get_available_strategy_names()
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
        if result is None:
            typed_certificate = _typed_certificate(None)
            return OptimizationResponse(
                algorithm_used=algorithm_key,
                success=False,
                routes=[],
                execution_time_seconds=round(execution_time, 4),
                error_message=json.dumps(typed_certificate.model_dump(exclude_none=True)),
                feasibility_certificate=typed_certificate,
            )
        original_result_success = result.success
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
            result.routes = calculate_scheduled_times(result.routes, request, distance_matrix)

        typed_certificate = _typed_certificate(
            certify_optimization_response(request, result)
        )
        result.feasibility_certificate = typed_certificate
        result.success = bool(original_result_success and typed_certificate.is_feasible)
        if not result.success:
            result.error_message = json.dumps(
                typed_certificate.model_dump(exclude_none=True)
            )

        if result.success:
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
        typed_certificate = _typed_certificate(None)
        return AlgorithmResult(
            algorithm=algorithm_name, success=False, total_vehicles=0,
            total_duration_minutes=0, execution_time_seconds=0, routes=[],
            error_message=json.dumps(typed_certificate.model_dump(exclude_none=True)),
            feasibility_certificate=typed_certificate,
        )
    try:
        start_time = time.time()
        result = strategy.optimize(request)
        if result is None:
            typed_certificate = _typed_certificate(None)
            return AlgorithmResult(
                algorithm=algorithm_name, success=False, total_vehicles=0,
                total_duration_minutes=0, execution_time_seconds=round(time.time() - start_time, 4),
                routes=[],
                error_message=json.dumps(typed_certificate.model_dump(exclude_none=True)),
                feasibility_certificate=typed_certificate,
            )
        execution_time = time.time() - start_time
        original_result_success = result.success
        typed_certificate = _typed_certificate(
            certify_optimization_response(request, result)
        )
        success = bool(original_result_success and typed_certificate.is_feasible)
        error_message = (
            json.dumps(typed_certificate.model_dump(exclude_none=True))
            if not success
            else result.error_message
        )
        return AlgorithmResult(
            algorithm=algorithm_name, success=success, total_vehicles=result.total_vehicles,
            total_duration_minutes=result.total_duration_minutes, execution_time_seconds=round(execution_time, 4),
            routes=result.routes, error_message=error_message,
            feasibility_certificate=typed_certificate,
        )
    except Exception:
        logger.exception("Algorithm %s failed during compare", algorithm_name)
        typed_certificate = _typed_certificate(None)
        return AlgorithmResult(
            algorithm=algorithm_name, success=False, total_vehicles=0,
            total_duration_minutes=0, execution_time_seconds=0, routes=[],
            error_message=json.dumps(typed_certificate.model_dump(exclude_none=True)),
            feasibility_certificate=typed_certificate,
        )
@router.post("/compare", response_model=CompareResponse)
def compare_algorithms(request: CompareRequest) -> CompareResponse:
    start_time = time.time()
    if request.algorithms:
        algorithms_to_run = [a.lower() for a in request.algorithms if a.lower() in STRATEGY_REGISTRY]
    else:
        algorithms_to_run = get_available_strategy_names()

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
            except Exception:
                typed_certificate = _typed_certificate(None)
                results.append(AlgorithmResult(
                    algorithm=algo, success=False, total_vehicles=0,
                    total_duration_minutes=0, execution_time_seconds=0, routes=[],
                    error_message=json.dumps(typed_certificate.model_dump(exclude_none=True)),
                    feasibility_certificate=typed_certificate,
                ))

    successful_results = [
        r for r in results
        if r.success
        and r.feasibility_certificate is not None
        and r.feasibility_certificate.is_feasible
    ]
    if successful_results:
        best = min(successful_results, key=lambda x: x.total_duration_minutes)
        fastest = min(successful_results, key=lambda x: x.execution_time_seconds)
    else:
        best = None
        fastest = None

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
