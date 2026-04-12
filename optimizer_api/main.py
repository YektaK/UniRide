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

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    CompareRequest, CompareResponse, AlgorithmResult,
    StrategyInfo, VehicleRoute, Direction, TimeWindow,
    IEResponseData, BottleneckInfo, TimeShiftSuggestion,
    WeeklyScheduleEntry, WeeklyScheduleRequest, StudentNode
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
from benchmark_runner import BenchmarkRunner, BenchmarkProblem, AlgorithmConfig

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
    """,
    version="3.1.0"
)

# CORS middleware
# Read allowed origins from ALLOWED_ORIGINS env var (comma-separated).
# Default to localhost dev server. Set ALLOWED_ORIGINS=* only if truly needed.
_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:9002,http://127.0.0.1:9002").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
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
# BENCHMARK ENDPOINTS (TSP Benchmark Studio Integration)
# ============================================================
# 
# 🔴 CRITICAL ARCHITECTURE DEBT - See docs/BENCHMARK_ARCHITECTURE_DEBT.md
# 
# ISSUE: Benchmark runner is never actually started!
# - POST /api/v1/benchmark/run creates state but doesn't run benchmark
# - BenchmarkRunner imported but never instantiated/executed
# - Frontend polling /status gets infinite "running" with 0% progress
# - 2-3 hour benchmarks would block Uvicorn worker (if started)
#
# SOLUTION: Use daemon thread for non-blocking execution
# See: docs/BENCHMARK_ARCHITECTURE_DEBT.md for implementation details
#
# TODO[P0]: Replace start_benchmark() with daemon thread implementation
# TODO[P0]: Add state_manager callbacks to BenchmarkRunner
# TODO[P1]: Add concurrent benchmark limit (max 3 running)
# TODO[P1]: Implement graceful shutdown handler
# ============================================================

import threading
from benchmark_state import benchmark_state_manager, BenchmarkStatus


@app.post("/api/v1/benchmark/run")
def start_benchmark(
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
    
    ARCHITECTURE:
    HTTP Request (Uvicorn Worker)
        ├─ create_run() → BenchmarkRunState
        ├─ spawn thread → run_benchmark_task()
        └─ return 200 OK (IMMEDIATELY)
    
    Daemon Thread (Background)
        ├─ BenchmarkRunner.run(...)
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
    
    See: docs/BENCHMARK_ARCHITECTURE_DEBT.md
    """
    try:
        # Create and register benchmark run
        n_runs = settings.get("n_runs", 3)
        total_experiments = len(algorithms) * len(problems) * n_runs
        
        # ✅ STEP 1: Create state immediately (thread-safe)
        state = benchmark_state_manager.create_run(
            run_id=run_id,
            total_experiments=total_experiments,
            parameters={
                "algorithms": algorithms,
                "problems": problems,
                "settings": settings
            }
        )
        
        # ✅ STEP 2: Define background task
        # TODO[P0]: This is the FIXED implementation (daemon thread pattern)
        def run_benchmark_task():
            """
            Background task executed in daemon thread.
            Runs benchmark and updates state_manager with progress.
            
            See: docs/BENCHMARK_ARCHITECTURE_DEBT.md for rationale
            """
            try:
                logger.info(f"[Benchmark] Executor thread started: {run_id}")
                
                # ✅ Create runner with state manager callbacks
                runner = BenchmarkRunner(
                    strategies_registry=STRATEGY_REGISTRY,
                    state_manager=benchmark_state_manager,
                    run_id=run_id
                )
                
                # ✅ Run benchmark (will update state_manager automatically)
                runner.run(
                    problems=problems,
                    algorithms=algorithms,
                    n_runs=n_runs,
                    seed=settings.get("seed", 42),
                    skip_cached=settings.get("skip_cached", False)
                )
                
                logger.info(f"[Benchmark] Executor thread completed: {run_id}, "
                           f"results={len(runner.results)}")
                
            except Exception as e:
                logger.error(f"[Benchmark] Executor error in {run_id}: {e}", exc_info=True)
                # Mark run as failed
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
    
    except Exception as e:
        logger.error(f"[Benchmark] Error starting run: {e}", exc_info=True)
        return {
            "run_id": run_id,
            "status": "error",
            "error": str(e),
            "code": "START_ERROR"
        }


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


# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
