"""
UniRide Optimization Engine API
FastAPI-based microservice for vehicle routing optimization

Version: 3.1.0 - CVRPTW Support Added
- Time window constraints
- Direction-based optimization (pickup/dropoff)
- Backward/forward scheduling
"""

import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import optimization, utils, strategies, benchmark, readiness
from strategies import get_available_strategy_names
try:
    from optimizer_api.runtime_config import optimizer_host, validate_bind_host, validate_runtime_configuration
except ModuleNotFoundError:  # direct `python optimizer_api/main.py` compatibility
    from runtime_config import optimizer_host, validate_bind_host, validate_runtime_configuration

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

validate_runtime_configuration()
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

# Global exception handler — never leak internal details to the client
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "UniRide Optimization Engine is running.",
        "version": "3.1.0",
        "features": ["CVRP", "CVRPTW", "Heterogeneous Fleet", "IE Resource Analysis"],
        "algorithms": get_available_strategy_names()
    }

# Mount Routers
app.include_router(optimization.router)
app.include_router(utils.router)
app.include_router(strategies.router)
app.include_router(benchmark.router)
app.include_router(readiness.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("OPTIMIZER_PORT", "8000"))
    bind_host = optimizer_host()
    validate_bind_host(bind_host)
    uvicorn.run("main:app", host=bind_host, port=port, reload=True)
