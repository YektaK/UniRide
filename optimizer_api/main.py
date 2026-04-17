"""
UniRide Optimization Engine API
FastAPI-based microservice for vehicle routing optimization

Version: 3.1.0 - CVRPTW Support Added
- Time window constraints
- Direction-based optimization (pickup/dropoff)
- Backward/forward scheduling
"""

import time
import os
import asyncio
import logging
import threading
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# TSPLIB parser for benchmark problems
from utils.tsplib_parser import (
    get_available_problems as get_tsplib_problems,
    get_problem_by_name,
    load_problem_coordinates,
    TSPLIBProblemInfo,
    TSPLIB_OPTIMALS,
    euclidean_distance_2d,
    parse_tsplib_file,
    download_tsplib_problem,
    ensure_tsplib_problems,
)

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    CompareRequest, CompareResponse, AlgorithmResult,
    StrategyInfo, VehicleRoute, Direction, TimeWindow,
    IEResponseData, BottleneckInfo, TimeShiftSuggestion,
    WeeklyScheduleEntry, WeeklyScheduleRequest, StudentNode,
    BenchmarkRunRequest,
)
from strategies import (
    STRATEGY_REGISTRY, get_strategy, get_strategy_info,
    GeneticAlgorithmStrategy, PSOStrategy,
    GreyWolfOptimizerStrategy, HarrisHawksOptimizerStrategy,
    TwoOptStrategy
)
from utils.resource_profiler import ResourceProfiler
from utils.time_window_extractor import TimeWindowExtractor
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES
from benchmark_runner import BenchmarkRunner, BenchmarkProblem, AlgorithmConfig, ExperimentResult

# Create FastAPI app
app = FastAPI(
    title="UniRide Optimization Engine API",
    description="""
    Python Microservice for Vehicle Routing Problem (VRP) solving.
    
    ## Version 3.1.0 - CVRPTW Support
    
    This version adds Time Window support for CVRPTW:
    - **direction**: Optimize for 'pickup' (geliş) or 'dropoff' (gidiş)
    - **use_time_windows**: Enable time window constraints
    - **target_time**: Global target time for scheduling
    - **offset_minutes**: Buffer time for driver notifications

    ## Available Algorithms

    - **genetic_algorithm (ga)**: Genetic Algorithm - Population-based metaheuristic
    - **pso**: Particle Swarm Optimization - Swarm intelligence metaheuristic
    - **gwo**: Grey Wolf Optimizer - Social hierarchy-based metaheuristic
    - **hho**: Harris Hawks Optimizer - Hunting behavior-based metaheuristic
    - **two_opt**: Two-Opt Local Search - Classic local search algorithm
    - **greedy**: Greedy/Nearest Neighbor - Fast heuristic
    - **permutation_tsp**: Complete Permutation Search - Optimal for n≤10
    - **ortools_cvrp**: Google OR-Tools - Industry standard solver
    - **ga_split**: GA + Optimal Split (Recommended for CVRP)
    - **pso_split**: PSO + Optimal Split

    ## Local Search Options

    All meta-heuristic algorithms (GA, PSO, GWO, HHO) support configurable
    local search methods for solution refinement:
    - `none`: No local search
    - `two_opt`: Classic 2-opt edge exchange
    - `three_opt`: 3-opt for higher quality solutions
    - `or_opt`: Node relocation for clustered problems
    - `hybrid`: Combination of methods

    ## Endpoints

    - `POST /api/v1/optimize` - Optimize with single algorithm
    - `POST /api/v1/compare` - Compare all algorithms
    - `GET /api/v1/strategies` - List available strategies
    - `POST /api/v1/extract-time-windows` - Extract time windows from weekly schedules
    - `GET /api/v1/benchmark/problems` - List available TSPLIB benchmark problems
    - `GET /api/v1/benchmark/results/{run_id}` - Get benchmark results
    """,
    version="3.1.0"
)

# CORS middleware
_allowed_origins = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:9002,http://127.0.0.1:9002,http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for parallel algorithm execution
executor = ThreadPoolExecutor(max_workers=5)


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "UniRide Optimization Engine is running.",
        "version": "3.1.0",
        "features": ["CVRP", "CVRPTW", "Heterogeneous Fleet", "IE Resource Analysis"],
        "algorithms": list(set(s.name for s in STRATEGY_REGISTRY.values()))
    }


@app.get("/api/v1/strategies", response_model=List[StrategyInfo])
def list_strategies() -> List[StrategyInfo]:
    """List all available optimization strategies"""
    strategies = get_strategy_info()
    recommended = ["ga_split", "pso_split", "genetic_algorithm", "pso", "gwo", "hho"]

    return [
        StrategyInfo(
            name=s["name"],
            display_name=s["display_name"],
            description=s["description"],
            complexity=_get_complexity(s["name"]),
            recommended=s["name"] in recommended
        )
        for s in strategies
    ]


def _get_complexity(name: str) -> str:
    """Get time complexity for algorithm"""
    complexities = {
        "genetic_algorithm": "O(generations × population × n²)",
        "ga_split": "O(generations × population × n²)",
        "pso": "O(iterations × swarm × n²)",
        "pso_split": "O(iterations × swarm × n²)",
        "gwo": "O(iterations × pack × n²)",
        "gwo_split": "O(iterations × pack × n²)",
        "hho": "O(iterations × hawks × n²)",
        "hho_split": "O(iterations × hawks × n²)",
        "two_opt": "O(n²) per improvement",
        "greedy": "O(n²)",
        "permutation_tsp": "O(n!)",
        "ortools_cvrp": "O(n³) worst case"
    }
    return complexities.get(name, "Unknown")


def _calculate_scheduled_times(
    routes: List[VehicleRoute],
    request: OptimizationRequest,
    distance_matrix: Dict[str, Dict[str, float]]
) -> List[VehicleRoute]:
    """Calculate scheduled times for routes based on direction and time windows
    
    For PICKUP (backward scheduling):
    - Start from target arrival time at school
    - Calculate departure times backward
    
    For DROPOFF (forward scheduling):
    - Start from departure time from school
    - Calculate arrival times forward
    """
    if not request.use_time_windows:
        return routes
    
    time_windows = request.get_time_windows()
    
    for route in routes:
        if not route.route_details:
            continue
        
        # Get locations in order
        locations = []
        for step in route.route_details:
            if step.location1 not in locations:
                locations.append(step.location1)
            if step.location2 not in locations:
                locations.append(step.location2)
        
        # Remove depot duplicates (first and last should be depot)
        if len(locations) > 2 and locations[0] == locations[-1]:
            locations = locations[:-1]
        
        arrival_times = {}
        
        if request.direction == Direction.PICKUP:
            # Backward scheduling: work backwards from target arrival at depot
            # Find the target time for the last location (should be depot/school)
            target_minutes = None
            
            # Get the latest time window for the school destination
            depot_id = request.depot.id
            for loc in reversed(locations):
                if loc in time_windows:
                    target_minutes = time_windows[loc].latest
                    break
            
            if target_minutes is None and request.target_time:
                parts = request.target_time.split(":")
                target_minutes = int(parts[0]) * 60 + int(parts[1])
            
            if target_minutes is None:
                # Default to 9:00 AM if no time specified
                target_minutes = 9 * 60
            
            # Calculate backwards
            current_minutes = target_minutes
            arrival_times[locations[-1]] = _minutes_to_time(current_minutes)
            
            for i in range(len(locations) - 2, -1, -1):
                from_loc = locations[i]
                to_loc = locations[i + 1]
                
                # Get travel time
                travel_time = distance_matrix.get(from_loc, {}).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
                current_minutes -= travel_time
                arrival_times[from_loc] = _minutes_to_time(current_minutes)
            
            # Apply offset for driver notification
            departure_minutes = current_minutes - request.offset_minutes
            route.departure_time = _minutes_to_time(max(0, departure_minutes))
            
        else:
            # Forward scheduling: work forward from departure time
            start_minutes = None
            
            # Find earliest time window
            for loc in locations:
                if loc in time_windows:
                    start_minutes = time_windows[loc].earliest
                    break
            
            if start_minutes is None and request.target_time:
                parts = request.target_time.split(":")
                start_minutes = int(parts[0]) * 60 + int(parts[1])
            
            if start_minutes is None:
                # Default to 2:00 PM for dropoff
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
    """Convert minutes from midnight to HH:MM format"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


@app.post("/api/v1/optimize", response_model=OptimizationResponse)
def optimize_route(request: OptimizationRequest) -> OptimizationResponse:
    """
    Optimize routes using specified algorithm.
    
    CVRPTW Support (v3.1.0):
    - direction: 'pickup' or 'dropoff'
    - use_time_windows: Enable time window constraints
    - target_time: Global target time (HH:MM)
    - offset_minutes: Buffer for driver notification
    
    Request body:
    - algorithm: Algorithm to use (ga_split, pso_split, genetic_algorithm, pso, gwo, hho, etc.)
    - students: List of students to route (with optional pickup_time, dropoff_time)
    - depot: Starting/ending location
    - direction: 'pickup' (geliş) or 'dropoff' (gidiş)
    - use_time_windows: Enable time window constraints
    
    Returns optimized routes with scheduled times and time window info.
    """
    algorithm_key = request.algorithm.lower()

    if algorithm_key not in STRATEGY_REGISTRY:
        available = list(set(s.name for s in STRATEGY_REGISTRY.values()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown algorithm '{algorithm_key}'. Available: {available}"
        )

    strategy = STRATEGY_REGISTRY[algorithm_key]

    try:
        start_time = time.time()
        
        # Extract time windows if enabled
        time_windows = {}
        if request.use_time_windows:
            time_windows = request.get_time_windows()
        
        result = strategy.optimize(request)
        execution_time = time.time() - start_time
        result.execution_time_seconds = round(execution_time, 4)
        
        # Add CVRPTW metadata to response
        result.direction = request.direction
        result.time_windows_used = request.use_time_windows and len(time_windows) > 0
        
        # Calculate scheduled times if time windows are enabled
        if request.use_time_windows and result.success:
            # Build distance matrix from route details (simplified)
            distance_matrix = {}
            for route in result.routes:
                for step in route.route_details:
                    if step.location1 not in distance_matrix:
                        distance_matrix[step.location1] = {}
                    distance_matrix[step.location1][step.location2] = step.duration
            
            result.routes = _calculate_scheduled_times(result.routes, request, distance_matrix)

        # Generate IE analysis using ResourceProfiler
        profiler = ResourceProfiler(
            standard_sw_capacity=request.sw_capacity,
            standard_so_capacity=request.so_capacity,
            max_tour_duration=request.max_travel_time
        )

        # Count Sw/So students
        students = request.students
        sw_count = sum(1 for s in students if s.disability_type == 'Sw')
        so_count = len(students) - sw_count

        # Calculate standard vehicle needs
        standard_needs = profiler.calculate_standard_vehicle_needs(students, mode=request.direction.value)

        # Generate hourly demand (using default time range 6-22)
        hourly_demand_raw = profiler.generate_hourly_demand(students)

        # Convert hourly demand to schema format
        hourly_demand = {
            hour: {
                'pickup': {
                    'Sw': d.pickup_sw,
                    'So': d.pickup_so
                },
                'dropoff': {
                    'Sw': d.dropoff_sw,
                    'So': d.dropoff_so
                }
            }
            for hour, d in hourly_demand_raw.items()
        }

        # Identify bottlenecks using available vehicles from request
        available_vehicles = request.vehicles if request.vehicles else []
        bottlenecks_raw = profiler.identify_bottlenecks(
            hourly_demand_raw,
            available_vehicles,
            mode=request.direction.value
        )

        # Convert bottlenecks to schema format
        bottlenecks = [
            BottleneckInfo(
                time=b.hour,
                type=b.type,
                reason=b.description,
                affected_students=None
            )
            for b in bottlenecks_raw
        ]

        # Generate time shift suggestions
        bottleneck_hours = [b.hour for b in bottlenecks_raw if b.severity in ['high', 'medium']]
        shift_suggestions_raw = profiler.suggest_time_shifts(
            hourly_demand_raw,
            bottleneck_hours,
            slack_window_minutes=request.slack_window_minutes
        )

        # Convert time shift suggestions to schema format
        time_shift_suggestions = [
            TimeShiftSuggestion(
                student_id=s.student_id,
                current_time=s.current_time,
                suggested_time=s.suggested_time,
                savings_vehicles=float(s.savings_vehicles)
            )
            for s in shift_suggestions_raw
        ]

        # Populate ie_data field
        result.ie_data = IEResponseData(
            standard_vehicles_needed=standard_needs.get('standard_vehicles_needed', 0),
            hourly_demand=hourly_demand,
            bottlenecks=bottlenecks,
            time_shift_suggestions=time_shift_suggestions
        )

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/extract-time-windows", response_model=Dict[str, TimeWindow])
def extract_time_windows(
    entries: List[WeeklyScheduleEntry],
    direction: Direction = Query(..., description="pickup or dropoff"),
    target_day: str = Query(..., description="Day of week (monday, tuesday, etc.)"),
    window_minutes: int = Query(30, description="Time window size in minutes")
) -> Dict[str, TimeWindow]:
    """
    Extract time windows from weekly schedule entries.
    
    This endpoint is used to:
    1. Filter entries by target day
    2. Convert startTime/endTime to TimeWindow objects
    3. Return time windows for route optimization
    
    Example:
    ```
    POST /api/v1/extract-time-windows?direction=pickup&target_day=monday
    Body: [{ "dayOfWeek": "monday", "startTime": "09:00", ... }]
    ```
    
    Returns:
    ```
    {
        "Sw1": { "earliest": 510, "latest": 540 },  // 08:30 - 09:00
        "Sw2": { "earliest": 510, "latest": 540 }
    }
    ```
    """
    extractor = TimeWindowExtractor(window_minutes=window_minutes)
    
    # Filter entries by day
    filtered_entries = [
        e for e in entries 
        if e.dayOfWeek.lower() == target_day.lower()
    ]
    
    if not filtered_entries:
        return {}
    
    # Extract time windows
    time_windows = {}
    for entry in filtered_entries:
        tw = extractor.extract(entry, direction)
        # Use entry id as key (in real use, this would be location_code)
        time_windows[entry.id] = tw
    
    return time_windows


@app.post("/api/v1/schedule-to-students", response_model=List[StudentNode])
def convert_schedule_to_students(
    entries: List[WeeklyScheduleEntry],
    target_day: str = Query(..., description="Day of week"),
    user_mapping: Dict[str, Dict] = None
) -> List[StudentNode]:
    """
    Convert weekly schedule entries to StudentNode list for optimization.
    
    This endpoint bridges the gap between weekly_schedules (Supabase) 
    and the optimization engine.
    
    Args:
        entries: List of weekly schedule entries
        target_day: Day to filter for
        user_mapping: Optional mapping of user_id to student info
            {
                "user_id": {
                    "location_code": "Sw1",
                    "disability_type": "Sw",
                    "name": "Student Name"
                }
            }
    
    Returns:
        List of StudentNode objects ready for optimization
    """
    students = []
    
    for entry in entries:
        if entry.dayOfWeek.lower() != target_day.lower():
            continue
        
        # Get user info from mapping or use defaults
        user_info = user_mapping.get(entry.id, {}) if user_mapping else {}
        
        student = StudentNode(
            id=entry.id,
            name=user_info.get("name", ""),
            location_code=user_info.get("location_code", "So1"),
            disability_type=user_info.get("disability_type", "So"),
            pickup_time=entry.startTime,
            dropoff_time=entry.endTime
        )
        students.append(student)
    
    return students


def _run_single_algorithm(algorithm_name: str, request: OptimizationRequest) -> AlgorithmResult:
    """Run a single algorithm and return results"""
    strategy = STRATEGY_REGISTRY.get(algorithm_name)

    if not strategy:
        return AlgorithmResult(
            algorithm=algorithm_name,
            success=False,
            total_vehicles=0,
            total_duration_minutes=0,
            execution_time_seconds=0,
            routes=[],
            error_message=f"Algorithm '{algorithm_name}' not found"
        )

    try:
        start_time = time.time()
        result = strategy.optimize(request)
        execution_time = time.time() - start_time

        return AlgorithmResult(
            algorithm=algorithm_name,
            success=result.success,
            total_vehicles=result.total_vehicles,
            total_duration_minutes=result.total_duration_minutes,
            execution_time_seconds=round(execution_time, 4),
            routes=result.routes,
            error_message=result.error_message
        )

    except Exception as e:
        return AlgorithmResult(
            algorithm=algorithm_name,
            success=False,
            total_vehicles=0,
            total_duration_minutes=0,
            execution_time_seconds=0,
            routes=[],
            error_message=str(e)
        )


@app.post("/api/v1/compare", response_model=CompareResponse)
def compare_algorithms(request: CompareRequest) -> CompareResponse:
    """
    Compare all algorithms on the same problem.

    Runs all available algorithms in parallel and returns:
    - Results from each algorithm
    - Best algorithm (lowest total duration)
    - Fastest algorithm (lowest execution time)
    - Summary comparison table

    This is useful for:
    - Choosing the best algorithm for your problem size
    - Validating algorithm implementations
    - Understanding trade-offs between algorithms
    """
    start_time = time.time()

    # Determine which algorithms to run
    if request.algorithms:
        algorithms_to_run = [a.lower() for a in request.algorithms if a.lower() in STRATEGY_REGISTRY]
    else:
        # Run all unique strategies
        algorithms_to_run = list(set(s.name for s in STRATEGY_REGISTRY.values()))

    if not algorithms_to_run:
        raise HTTPException(
            status_code=400,
            detail="No valid algorithms specified"
        )

    # Create optimization request with CVRPTW fields
    opt_request = OptimizationRequest(
        algorithm=algorithms_to_run[0],  # Will be overridden
        students=request.students,
        depot=request.depot,
        max_travel_time=request.max_travel_time,
        sw_capacity=request.sw_capacity,
        so_capacity=request.so_capacity,
        direction=request.direction,
        use_time_windows=request.use_time_windows
    )

    # Run algorithms in parallel using thread pool
    results: List[AlgorithmResult] = []

    with ThreadPoolExecutor(max_workers=len(algorithms_to_run)) as pool:
        futures = []
        for algo in algorithms_to_run:
            future = pool.submit(_run_single_algorithm, algo, opt_request)
            futures.append((algo, future))

        for algo, future in futures:
            try:
                result = future.result(timeout=120)  # 2 minute timeout per algorithm
                results.append(result)
            except Exception as e:
                results.append(AlgorithmResult(
                    algorithm=algo,
                    success=False,
                    total_vehicles=0,
                    total_duration_minutes=0,
                    execution_time_seconds=0,
                    routes=[],
                    error_message=str(e)
                ))

    # Find best and fastest
    successful_results = [r for r in results if r.success]

    if successful_results:
        best = min(successful_results, key=lambda x: x.total_duration_minutes)
        fastest = min(successful_results, key=lambda x: x.execution_time_seconds)
    else:
        best = results[0] if results else None
        fastest = results[0] if results else None

    # Build summary
    summary = {}
    for r in results:
        summary[r.algorithm] = {
            "total_vehicles": r.total_vehicles,
            "total_duration_minutes": round(r.total_duration_minutes, 2),
            "execution_time_seconds": round(r.execution_time_seconds, 4),
            "success": r.success
        }

    total_time = time.time() - start_time

    return CompareResponse(
        success=len(successful_results) > 0,
        results=results,
        best_algorithm=best.algorithm if best else "",
        fastest_algorithm=fastest.algorithm if fastest else "",
        summary=summary
    )


@app.post("/api/v1/vehicle-calculator", response_model=OptimizationResponse)
def calculate_vehicles(request: OptimizationRequest) -> OptimizationResponse:
    """
    Calculate vehicle requirements and student assignments.

    This endpoint specifically handles the CVRP (Capacitated Vehicle Routing Problem):
    - Estimates minimum number of vehicles needed
    - Clusters students by geographic proximity (K-Means)
    - Validates capacity constraints (Sw/So)
    - Validates tour time constraints
    - Supports CVRPTW with time window constraints

    The algorithm parameter determines the TSP solver used for each cluster.
    """
    return optimize_route(request)


# ============================================================
# BENCHMARK ENDPOINTS
# ============================================================
# TSPLIB Benchmark integration via daemon threads.
# Supports TSP, CVRP, and CVRPTW problem types.
# ============================================================

from benchmark_state import benchmark_state_manager, BenchmarkStatus, MAX_CONCURRENT_BENCHMARKS


@app.get("/api/v1/benchmark/problems")
def list_benchmark_problems(
    category: Optional[str] = Query(None, description="Filter by category: small, medium, large")
) -> List[Dict]:
    """
    List available TSPLIB benchmark problems for selection.
    
    Returns problem metadata including:
    - name, dimension, category, optimal score (if known)
    - Whether the problem file is available locally
    
    Args:
        category: Optional filter (small/medium/large)
    """
    problems = get_tsplib_problems()
    
    if category:
        problems = [p for p in problems if p.category == category]
    
    return [
        {
            "name": p.name,
            "dimension": p.dimension,
            "optimal": p.optimal,
            "category": p.category,
            "problem_type": p.problem_type,
            "edge_weight_type": p.edge_weight_type,
            "available": p.file_path is not None,
        }
        for p in problems
    ]


@app.get("/api/v1/benchmark/problems/{problem_name}")
def get_benchmark_problem_detail(problem_name: str) -> Dict:
    """Get detailed info about a specific TSPLIB problem including coordinates."""
    info = get_problem_by_name(problem_name)
    
    if not info:
        raise HTTPException(status_code=404, detail=f"Problem '{problem_name}' not found")
    
    result = {
        "name": info.name,
        "dimension": info.dimension,
        "optimal": info.optimal,
        "category": info.category,
        "problem_type": info.problem_type,
        "edge_weight_type": info.edge_weight_type,
        "available": info.file_path is not None,
        "coordinates": None,
    }
    
    # Include coordinates if requested
    if info.file_path:
        coords = load_problem_coordinates(problem_name)
        if coords:
            result["coordinates"] = coords
    
    return result


@app.get("/api/v1/benchmark/results/{run_id}")
def get_benchmark_results(run_id: str) -> Dict:
    """
    Get results from a completed benchmark run.
    
    Returns list of experiment results with tour_length, elapsed_ms, gap_percent
    for each algorithm-problem-run combination.
    """
    state = benchmark_state_manager.get_run(run_id)
    
    if not state:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    
    if state.status != BenchmarkStatus.COMPLETED:
        return {
            "run_id": run_id,
            "status": state.status.value,
            "results": [],
            "message": f"Benchmark is still {state.status.value}. Use /api/v1/benchmark/status for progress.",
            "parameters": state.parameters,
        }
    
    # Return results stored in state by BenchmarkRunner
    return {
        "run_id": run_id,
        "status": state.status.value,
        "results_count": state.results_count,
        "total_experiments": state.total_experiments,
        "message": state.message,
        "parameters": state.parameters,
        "results": state.results,
    }


@app.post("/api/v1/benchmark/run")
def start_benchmark(body: BenchmarkRunRequest) -> Dict:
    """
    Start a new benchmark run (JSON body version).
    Accepts a BenchmarkRunRequest Pydantic model as JSON body.
    """
    # Parse fields from body
    run_id = body.run_id
    algorithms = body.algorithms
    problems = body.problems
    settings = body.settings

    return _start_benchmark_impl(run_id, algorithms, problems, settings)


def _start_benchmark_impl(
    run_id: str,
    algorithms: List[Dict],
    problems: List[str],
    settings: Dict
) -> Dict:
    """
    Start a new benchmark run.
    
    DESIGN:
    - Creates benchmark state immediately (thread-safe)
    - Spawns daemon thread for non-blocking execution
    - Returns 200 OK immediately (doesn't wait for completion)
    - Frontend polls /api/v1/benchmark/status for progress updates
    - Enforces concurrent limit (max 3 running) via can_start_run()
    
    ARCHITECTURE:
    HTTP Request (Uvicorn Worker)
        ├─ can_start_run() check → 429 if limit exceeded
        ├─ create_run() → BenchmarkRunState
        ├─ spawn thread → run_benchmark_task()
        └─ return 200 OK (IMMEDIATELY)
    
    Daemon Thread (Background)
        ├─ BenchmarkRunner.run(...) with real algorithm dispatch
        ├─ update_progress() every N experiments
        └─ complete_run() when done
    
    This endpoint integrates TSP Benchmark Studio algorithms with UniRide.
    Benchmarks compare algorithm performance across multiple problems.
    
    Args:
        run_id: Unique benchmark run identifier
        algorithms: List of algorithm configs {"id": "ga", "params": {...}}
        problems: List of problem names to benchmark
        settings: {"n_runs": int, "workers": int, "seed": int, ...}
    
    Returns:
        {
            "run_id": "...",
            "status": "running",
            "total_experiments": int,
            "message": "...",
            "start_time": "..."
        }
    
    Raises:
        HTTPException(429): When MAX_CONCURRENT_BENCHMARKS limit exceeded
    
    See: docs/BENCHMARK_ARCHITECTURE_DEBT.md
    """
    try:
        # ✅ STEP 0: Check concurrent limit (soft limit)
        if not benchmark_state_manager.can_start_run():
            logger.warning(
                f"[Benchmark] Concurrent limit exceeded. "
                f"Max {MAX_CONCURRENT_BENCHMARKS} benchmark runs allowed (currently at limit)"
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": f"Maximum {MAX_CONCURRENT_BENCHMARKS} concurrent benchmarks reached",
                    "error_code": "CONCURRENT_LIMIT_EXCEEDED",
                    "message": "Bekleyen taklada. Diğer benchmarklar tamamlanana kadar bekleyin.",
                    "max_concurrent": MAX_CONCURRENT_BENCHMARKS
                }
            )
        
        # Create and register benchmark run
        n_runs = settings.get("n_runs", 3)
        total_experiments = len(algorithms) * len(problems) * n_runs
        
        # ✅ STEP 1: VALIDATION (P1-5 Fix: Return error before backgrounding if invalid)
        benchmark_problems: List[BenchmarkProblem] = []
        for problem_name in problems:
            info = get_problem_by_name(problem_name)
            if not info or not info.file_path:
                logger.warning(f"[Benchmark] Problem '{problem_name}' not found")
                continue
            
            coords = load_problem_coordinates(problem_name)
            if not coords:
                logger.warning(f"[Benchmark] Could not load coordinates for '{problem_name}'")
                continue
            
            bp = BenchmarkProblem(
                name=info.name,
                dimension=info.dimension,
                coordinates=coords,
                optimal_score=info.optimal,
                category=info.category,
                problem_type="tsp",
                depot_index=0,
            )
            benchmark_problems.append(bp)
        
        if not benchmark_problems:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No valid benchmark problems found",
                    "code": "INVALID_PROBLEMS",
                    "problems_tried": problems
                }
            )

        # ✅ STEP 2: Create state (thread-safe)
        state = benchmark_state_manager.create_run(
            run_id=run_id,
            total_experiments=total_experiments,
            parameters={
                "algorithms": algorithms,
                "problems": problems,
                "settings": settings
            }
        )
        
        # ✅ STEP 3: Define background task
        def run_benchmark_task():
            try:
                logger.info(f"[Benchmark] Executor thread started: {run_id}")
                
                # Resolve algorithm configs
                algo_configs: List[AlgorithmConfig] = []
                for algo_dict in algorithms:
                    algo_configs.append(AlgorithmConfig(
                        name=algo_dict.get("id", algo_dict.get("name", "unknown")),
                        algorithm_id=algo_dict.get("id", algo_dict.get("name", "unknown")),
                        params=algo_dict.get("params", {}),
                    ))
                
                # Create runner with state manager callbacks
                runner = BenchmarkRunner(
                    strategies_registry=STRATEGY_REGISTRY,
                    state_manager=benchmark_state_manager,
                    run_id=run_id
                )
                
                # Run benchmark
                runner.run(
                    problems=benchmark_problems,
                    algorithms=algo_configs,
                    n_runs=n_runs,
                    seed=settings.get("seed", 42),
                    skip_cached=settings.get("skip_cached", False)
                )
                
                logger.info(f"[Benchmark] Executor thread completed: {run_id}")
                
            except Exception as e:
                logger.error(f"[Benchmark] Executor error in {run_id}: {e}", exc_info=True)
                benchmark_state_manager.fail_run(run_id, f"Error: {str(e)}")
        
        # ✅ STEP 3: Spawn daemon thread (non-blocking)
        # This allows endpoint to return immediately while benchmark runs in background
        executor_thread = threading.Thread(
            target=run_benchmark_task,
            daemon=True,
            name=f"benchmark-executor-{run_id}"
        )
        executor_thread.start()
        
        logger.info(f"[Benchmark] Started run {run_id}: {total_experiments} "
                   f"experiments ({len(problems)} problems × {len(algorithms)} "
                   f"algorithms × {n_runs} runs)")
        
        # ✅ Return immediately (thread is running in background)
        return {
            "run_id": run_id,
            "status": "running",
            "total_experiments": total_experiments,
            "problems_count": len(problems),
            "algorithms_count": len(algorithms),
            "message": f"Benchmark run {run_id} arka planda başlatıldı",
            "start_time": state.start_time
        }
    
    except HTTPException:
        # Re-raise FastAPI HTTP exceptions (e.g. 429) as-is
        raise
    except Exception as e:
        logger.error("[Benchmark] Error starting run %s: %s", run_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "code": "START_ERROR",
                "run_id": run_id,
            }
        )

@app.post("/api/v1/benchmark/import")
def import_benchmark(body: BenchmarkImportRequest) -> Dict:
    """
    Import external benchmark results (CLI -> Web).
    Adds results to the in-memory benchmark state manager.
    """
    try:
        data = body.model_dump()
        state = benchmark_state_manager.import_run(body.run_id, data)
        return {
            "run_id": state.run_id,
            "status": state.status.value,
            "results_imported": state.results_count,
            "message": f"Dış benchmark verisi başarıyla içe aktarıldı ({state.results_count} sonuç)"
        }
    except Exception as e:
        logger.error(f"[Benchmark] Error importing run {body.run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/benchmark/status")
def get_benchmark_status(run_id: str) -> Dict:
    """
    Get status of a benchmark run.
    
    Returns:
        {
            "run_id": "...",
            "status": "running|completed|failed|stopped",
            "total_experiments": int,
            "completed_experiments": int,
            "results_count": int,
            "message": "...",
            "progress_percent": float
        }
    """
    state = benchmark_state_manager.get_run(run_id)
    
    if not state:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    
    progress_percent = 0.0
    if state.total_experiments > 0:
        progress_percent = (state.completed_experiments / state.total_experiments) * 100
    
    return {
        "run_id": run_id,
        "status": state.status.value,
        "total_experiments": state.total_experiments,
        "completed_experiments": state.completed_experiments,
        "results_count": state.results_count,
        "message": state.message,
        "progress_percent": min(100.0, progress_percent),
        "start_time": state.start_time,
        "end_time": state.end_time
    }


@app.post("/api/v1/benchmark/stop")
def stop_benchmark(run_id: str) -> Dict:
    """
    Stop a running benchmark.
    
    Returns:
        {
            "run_id": "...",
            "status": "stopped",
            "results_collected": int
        }
    """
    state = benchmark_state_manager.get_run(run_id)
    
    if not state:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    
    benchmark_state_manager.stop_run(run_id, "User requested stop")
    
    logger.info(f"[Benchmark] Stopped run {run_id}, collected {state.results_count} results")
    
    return {
        "run_id": run_id,
        "status": "stopped",
        "results_collected": state.results_count,
        "message": f"Benchmark {run_id} durduruldu"
    }


@app.post("/api/v1/benchmark/download/{problem_name}")
def download_benchmark_problem(problem_name: str) -> Dict:
    """
    Download a missing TSPLIB problem file from the official archive.

    If the file already exists locally, returns its path immediately.
    Otherwise attempts to download from the Heidelberg TSPLIB95 server.
    Tries two URL patterns:
      1. {NAME}.tsp.tgz  (compressed archive)
      2. {NAME}/{NAME}.tsp  (direct file)

    Args:
        problem_name: TSPLIB problem name (e.g. "eil51")

    Returns:
        {
            "problem_name": str,
            "status": "downloaded" | "already_existed" | "failed",
            "file_path": str | None,
            "message": str
        }
    """
    # Validate name against known problems (optional but helpful)
    name_lower = problem_name.lower().strip()

    # Check if already available locally
    info = get_problem_by_name(name_lower)
    if info and info.file_path:
        return {
            "problem_name": name_lower,
            "status": "already_existed",
            "file_path": info.file_path,
            "message": f"Problem '{name_lower}' already available at {info.file_path}",
        }

    # Attempt download
    logger.info(f"[Benchmark] Download request for problem '{name_lower}'")
    result_path = download_tsplib_problem(name_lower)

    if result_path:
        return {
            "problem_name": name_lower,
            "status": "downloaded",
            "file_path": result_path,
            "message": f"Successfully downloaded '{name_lower}' to {result_path}",
        }

    return {
        "problem_name": name_lower,
        "status": "failed",
        "file_path": None,
        "message": (
            f"Could not download '{name_lower}'. "
            f"The problem may not exist in the TSPLIB archive, or the server is unreachable."
        ),
    }


# ============================================================
# CLI → WEB IMPORT BRIDGE
# ============================================================
# Seçenek A: CLI benchmark sonuçlarını web arayüzünde görüntülenebilir hale getiren
# import endpoint'leri. CLI JSON dosyalarını okuyup, benchmark_state_manager
# formatına çevirir. Böylece mevcut /benchmark/results/{run_id} endpoint'i
# ile CLI sonuçları da web frontend'de gösterilebilir.
#
# CLI Format:  {problem, dimension, category, optimal, strategy, avg_length, avg_gap,
#               best_length, best_gap, avg_time_ms, n_runs, timestamp, numba_optimized}
# Web Format:  {algorithm, problem, run_number, tour_length, elapsed_ms, gap_percent,
#               timestamp, metadata: {problem_dimension, problem_category, ...}}
# ============================================================

import json
import glob as glob_mod
from datetime import datetime, timezone

# CLI benchmark results klasörü
CLI_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "tests", "benchmark_results")
CLI_RESULTS_NUMBA_DIR = os.path.join(os.path.dirname(__file__), "tests", "benchmark_results_numba")


def _convert_cli_record_to_web(cli_record: Dict, run_number: int = 1) -> Dict:
    """
    Convert a single CLI benchmark record to web ExperimentResult format.

    CLI stores aggregated data (avg/best over N runs).
    We expand into N individual records — one per conceptual "run".
    For the best-gap run (run_number=1), we use best_length/best_gap.
    For other runs, we use avg_length/avg_gap as representative.

    Args:
        cli_record: Single record from CLI JSON file
        run_number: Virtual run number (1..n_runs)

    Returns:
        Dict compatible with web BenchmarkRunner's ExperimentResult asdict format
    """
    is_best_run = (run_number == 1)

    return {
        "algorithm": cli_record.get("strategy", "unknown"),
        "problem": cli_record.get("problem", "unknown"),
        "run_number": run_number,
        "tour_length": float(cli_record.get("best_length", cli_record.get("avg_length", 0)))
        if is_best_run
        else float(cli_record.get("avg_length", 0)),
        "elapsed_ms": float(cli_record.get("avg_time_ms", 0)),
        "gap_percent": float(cli_record.get("best_gap", cli_record.get("avg_gap", 0)))
        if is_best_run
        else float(cli_record.get("avg_gap", 0)),
        "timestamp": cli_record.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "metadata": {
            "problem_dimension": cli_record.get("dimension", 0),
            "problem_type": "tsp",
            "problem_category": cli_record.get("category", "unknown"),
            "optimal_score": cli_record.get("optimal"),
            "n_runs": cli_record.get("n_runs", 3),
            "numba_optimized": cli_record.get("numba_optimized", True),
            "algorithm_type": cli_record.get("algorithm_type", "local_search"),
            "source": "cli_import",
            "execution_failed": False,
            "routes_count": 1,
            "vehicles_used": 1,
            # Preserve original CLI fields for reference
            "cli_avg_length": cli_record.get("avg_length"),
            "cli_best_length": cli_record.get("best_length"),
            "cli_avg_gap": cli_record.get("avg_gap"),
            "cli_best_gap": cli_record.get("best_gap"),
            "cli_avg_time_ms": cli_record.get("avg_time_ms"),
        },
    }


def _find_cli_json_files() -> List[Dict]:
    """
    Scan CLI benchmark result directories for JSON files.

    Returns:
        List of dicts: {filename, filepath, size_bytes, modified_time, source_dir}
    """
    files = []

    for search_dir in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR]:
        if not os.path.isdir(search_dir):
            continue

        pattern = os.path.join(search_dir, "*.json")
        for filepath in sorted(glob_mod.glob(pattern)):
            try:
                stat = os.stat(filepath)
                files.append({
                    "filename": os.path.basename(filepath),
                    "filepath": filepath,
                    "size_bytes": stat.st_size,
                    "modified_time": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "source_dir": os.path.basename(search_dir),
                })
            except OSError:
                continue

    return files


def _load_and_validate_cli_json(filepath: str) -> List[Dict]:
    """
    Load CLI JSON file and validate format.

    Args:
        filepath: Absolute path to CLI JSON file

    Returns:
        List of CLI records

    Raises:
        HTTPException: If file cannot be read or format is invalid
    """
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"Dosya bulunamadı: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON parse hatası: {e}")

    if not isinstance(data, list):
        raise HTTPException(
            status_code=400,
            detail="CLI JSON dosyası bir dizi (array) olmalıdır"
        )

    if not data:
        raise HTTPException(status_code=400, detail="CLI JSON dosyası boş")

    # Validate required fields in first record
    required_fields = ["problem", "strategy", "dimension"]
    first = data[0]
    missing = [f for f in required_fields if f not in first]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Eksik zorunlu alanlar: {missing}. Beklenen format: CLI benchmark JSON"
        )

    return data


@app.get("/api/v1/benchmark/cli/files")
def list_cli_benchmark_files() -> Dict:
    """
    List available CLI benchmark JSON files for import.

    Returns all JSON files found in optimizer_api/tests/benchmark_results/
    and optimizer_api/tests/benchmark_results_numba/ directories.

    Each file can be imported via POST /api/v1/benchmark/cli/import
    """
    files = _find_cli_json_files()

    return {
        "total_files": len(files),
        "scan_directories": [
            d for d in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR]
            if os.path.isdir(d)
        ],
        "files": files,
    }


@app.post("/api/v1/benchmark/cli/import")
def import_cli_benchmark_results(
    filepath: str = "",
    filename: str = "",
    run_id: Optional[str] = None,
    label: Optional[str] = None,
) -> Dict:
    """
    Import CLI benchmark results into the web benchmark state manager.

    This endpoint reads a CLI JSON file (from run_smart_benchmark_numba.py
    or run_interactive_benchmark_v2_numba.py), converts each record to the
    web ExperimentResult format, and registers them in the benchmark_state_manager.

    Once imported, the results can be viewed via:
      - GET /api/v1/benchmark/results/{run_id}
      - GET /api/v1/benchmark/status/{run_id}

    Args:
        filepath: Absolute or relative path to CLI JSON file
                  (relative to optimizer_api/tests/benchmark_results/)
        filename: Alternative: just the filename (searches in known directories)
        run_id: Custom run_id. If not provided, auto-generated as "cli-import-{timestamp}"
        label: Optional label for the run (e.g., "Numba Small Problems Run")

    Returns:
        {
            "run_id": str,
            "status": "completed",
            "results_count": int,
            "source_file": str,
            "summary": {...}
        }
    """
    # Resolve filepath
    if not filepath and not filename:
        raise HTTPException(
            status_code=400,
            detail="filepath veya filename parametresi gerekiyor"
        )

    if filename and not filepath:
        # Search in known directories
        for search_dir in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR]:
            candidate = os.path.join(search_dir, filename)
            if os.path.isfile(candidate):
                filepath = candidate
                break

        if not filepath:
            raise HTTPException(
                status_code=404,
                detail=f"'{filename}' bulunamadı. GET /api/v1/benchmark/cli/files ile mevcut dosyaları kontrol edin."
            )

    # Normalize path
    filepath = os.path.abspath(filepath)

    # Load and validate
    cli_records = _load_and_validate_cli_json(filepath)

    # Generate run_id
    if not run_id:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"cli-import-{timestamp_str}"

    # Check if run_id already exists
    existing = benchmark_state_manager.get_run(run_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Run ID '{run_id}' zaten mevcut. Farklı bir run_id kullanın."
        )

    # Convert CLI records to web format
    web_results = []
    for record in cli_records:
        n_runs = record.get("n_runs", 3)
        # Expand aggregated CLI record into n_runs individual web records
        for run_num in range(1, n_runs + 1):
            web_record = _convert_cli_record_to_web(record, run_number=run_num)
            web_results.append(web_record)

    # Determine unique problems and strategies for summary
    unique_problems = list(set(r["problem"] for r in cli_records))
    unique_strategies = list(set(r["strategy"] for r in cli_records))
    categories = list(set(r.get("category", "unknown") for r in cli_records))

    # Create run state (immediately completed — no background thread needed)
    state = benchmark_state_manager.create_run(
        run_id=run_id,
        total_experiments=len(web_results),
        parameters={
            "source": "cli_import",
            "source_file": os.path.basename(filepath),
            "source_path": filepath,
            "label": label or f"CLI Import: {os.path.basename(filepath)}",
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "problems": unique_problems,
            "algorithms": unique_strategies,
            "categories": categories,
            "original_record_count": len(cli_records),
            "n_runs_per_combination": cli_records[0].get("n_runs", 3) if cli_records else 1,
        }
    )

    # Add all results and mark as completed
    for result in web_results:
        benchmark_state_manager.add_result(run_id, result)

    benchmark_state_manager.complete_run(
        run_id=run_id,
        results_count=len(web_results),
        message=f"CLI'dan {len(cli_records)} kayıt içe aktarıldı ({os.path.basename(filepath)})"
    )

    logger.info(
        f"[CLI Import] Imported {len(cli_records)} CLI records → {len(web_results)} web records "
        f"as run_id='{run_id}' from {os.path.basename(filepath)}"
    )

    # Build summary
    summary = {
        "unique_problems": len(unique_problems),
        "unique_strategies": len(unique_strategies),
        "categories": categories,
        "problems": unique_problems,
        "strategies": unique_strategies,
    }

    # Per-strategy best gap summary
    strategy_best = {}
    for r in cli_records:
        strat = r.get("strategy", "unknown")
        best_gap = r.get("best_gap", float("inf"))
        if strat not in strategy_best or best_gap < strategy_best[strat]["best_gap"]:
            strategy_best[strat] = {
                "best_gap": best_gap,
                "avg_gap": r.get("avg_gap", 0),
                "best_length": r.get("best_length", 0),
                "problem": r.get("problem", ""),
            }
    summary["strategy_best"] = strategy_best

    return {
        "run_id": run_id,
        "status": "completed",
        "results_count": len(web_results),
        "source_file": os.path.basename(filepath),
        "source_path": filepath,
        "original_records": len(cli_records),
        "summary": summary,
        "message": f"CLI sonuçları içe aktarıldı. GET /api/v1/benchmark/results/{run_id} ile görüntüleyin",
    }


@app.get("/api/v1/benchmark/cli/preview")
def preview_cli_import(
    filepath: str = "",
    filename: str = "",
) -> Dict:
    """
    Preview CLI benchmark file content without importing.

    Shows the first N records in both original CLI format and
    converted web format, so you can verify the conversion
    before importing.

    Args:
        filepath: Absolute or relative path to CLI JSON file
        filename: Alternative: just the filename

    Returns:
        {
            "file": {...},
            "total_records": int,
            "preview": [converted_records],
            "problems": [...],
            "strategies": [...],
            "categories": [...]
        }
    """
    if not filepath and filename:
        for search_dir in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR]:
            candidate = os.path.join(search_dir, filename)
            if os.path.isfile(candidate):
                filepath = candidate
                break

    if not filepath:
        raise HTTPException(status_code=400, detail="filepath veya filename gerekiyor")

    filepath = os.path.abspath(filepath)
    cli_records = _load_and_validate_cli_json(filepath)

    # Convert first 3 records for preview
    preview_records = []
    for record in cli_records[:3]:
        converted = _convert_cli_record_to_web(record, run_number=1)
        preview_records.append({
            "original": {
                "problem": record.get("problem"),
                "dimension": record.get("dimension"),
                "strategy": record.get("strategy"),
                "optimal": record.get("optimal"),
                "avg_length": record.get("avg_length"),
                "best_length": record.get("best_length"),
                "avg_gap": record.get("avg_gap"),
                "best_gap": record.get("best_gap"),
                "avg_time_ms": record.get("avg_time_ms"),
                "n_runs": record.get("n_runs"),
            },
            "converted_web": converted,
        })

    unique_problems = list(set(r["problem"] for r in cli_records))
    unique_strategies = list(set(r["strategy"] for r in cli_records))
    categories = list(set(r.get("category", "unknown") for r in cli_records))

    return {
        "file": {
            "name": os.path.basename(filepath),
            "path": filepath,
            "size_bytes": os.path.getsize(filepath),
        },
        "total_records": len(cli_records),
        "unique_problems": len(unique_problems),
        "unique_strategies": len(unique_strategies),
        "problems": unique_problems,
        "strategies": unique_strategies,
        "categories": categories,
        "preview": preview_records,
        "message": f"Bu dosyayı import etmek için POST /api/v1/benchmark/cli/import?filename={os.path.basename(filepath)}",
    }


# Run server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("OPTIMIZER_PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
