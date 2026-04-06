"""
UniRide Optimization Engine API
FastAPI-based microservice for vehicle routing optimization
"""

import time
import os
import asyncio
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    CompareRequest, CompareResponse, AlgorithmResult,
    StrategyInfo, VehicleRoute
)
from strategies import (
    STRATEGY_REGISTRY, get_strategy, get_strategy_info,
    GeneticAlgorithmStrategy, PSOStrategy, GWOStrategy, HHOStrategy
)

# Create FastAPI app
app = FastAPI(
    title="UniRide Optimization Engine API",
    description="""
    Python Microservice for Vehicle Routing Problem (VRP) solving.

    ## Available Algorithms

    - **genetic_algorithm (ga)**: Genetic Algorithm - Population-based metaheuristic
    - **pso**: Particle Swarm Optimization - Swarm intelligence metaheuristic
    - **gwo**: Grey Wolf Optimizer - Social hierarchy-based metaheuristic
    - **hho**: Harris Hawks Optimization - Escape energy-based adaptive search
    - **greedy**: Greedy/Nearest Neighbor - Fast heuristic
    - **permutation_tsp**: Complete Permutation Search - Optimal for n≤10
    - **ortools_cvrp**: Google OR-Tools - Industry standard solver

    ## Endpoints

    - `POST /api/v1/optimize` - Optimize with single algorithm
    - `POST /api/v1/compare` - Compare all algorithms
    - `GET /api/v1/strategies` - List available strategies
    """,
    version="2.2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for parallel algorithm execution
executor = ThreadPoolExecutor(max_workers=5)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "UniRide Optimization Engine is running.",
        "version": "2.2.0"
    }


@app.get("/api/v1/strategies", response_model=List[StrategyInfo])
def list_strategies():
    """List all available optimization strategies"""
    strategies = get_strategy_info()
    return [
        StrategyInfo(
            name=s["name"],
            display_name=s["display_name"],
            description=s["description"],
            complexity=_get_complexity(s["name"]),
            recommended=s["name"] in ["genetic_algorithm", "pso", "gwo", "hho"]
        )
        for s in strategies
    ]


def _get_complexity(name: str) -> str:
    """Get time complexity for algorithm"""
    complexities = {
        "genetic_algorithm": "O(generations × population × n²)",
        "pso": "O(iterations × swarm × n²)",
        "gwo": "O(iterations × population × n²)",
        "hho": "O(iterations × hawks × n²)",
        "greedy": "O(n²)",
        "permutation_tsp": "O(n!)",
        "ortools_cvrp": "O(n³) worst case"
    }
    return complexities.get(name, "Unknown")


@app.post("/api/v1/optimize", response_model=OptimizationResponse)
def optimize_route(request: OptimizationRequest):
    """
    Optimize routes using specified algorithm.

    Request body:
    - algorithm: Algorithm to use (genetic_algorithm, pso, greedy, etc.)
    - students: List of students to route
    - depot: Starting/ending location
    - max_travel_time: Maximum tour time per vehicle (minutes)
    - sw_capacity: Wheelchair capacity per vehicle
    - so_capacity: Walking student capacity per vehicle

    Returns optimized routes with duration and vehicle assignments.
    """
    algorithm_key = request.algorithm.lower()

    if algorithm_key not in STRATEGY_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown algorithm '{algorithm_key}'. Available: {list(set(s.name for s in STRATEGY_REGISTRY.values()))}"
        )

    strategy = STRATEGY_REGISTRY[algorithm_key]

    try:
        start_time = time.time()
        result = strategy.optimize(request)
        execution_time = time.time() - start_time
        result.execution_time_seconds = round(execution_time, 4)

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
def compare_algorithms(request: CompareRequest):
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

    # Create optimization request
    opt_request = OptimizationRequest(
        algorithm=algorithms_to_run[0],  # Will be overridden
        students=request.students,
        depot=request.depot,
        max_travel_time=request.max_travel_time,
        sw_capacity=request.sw_capacity,
        so_capacity=request.so_capacity
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
def calculate_vehicles(request: OptimizationRequest):
    """
    Calculate vehicle requirements and student assignments.

    This endpoint specifically handles the CVRP (Capacitated Vehicle Routing Problem):
    - Estimates minimum number of vehicles needed
    - Clusters students by geographic proximity (K-Means)
    - Validates capacity constraints (Sw/So)
    - Validates tour time constraints

    The algorithm parameter determines the TSP solver used for each cluster.
    """
    return optimize_route(request)


# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
