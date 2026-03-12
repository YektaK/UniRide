from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import os
from dotenv import load_dotenv

# Load .env file from the same directory before any other imports that use env vars
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from models.schemas import OptimizationRequest, OptimizationResponse
from strategies import STRATEGY_REGISTRY

app = FastAPI(
    title="UniRide Optimization Engine API",
    description="Python Microservice for Vehicle Routing Problem solving using Strategy Pattern.",
    version="1.0.0"
)

# Allow Next.js frontend to communicate with this local API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev. In production, add Next.js domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "UniRide Optimization Engine is running."}

@app.post("/api/v1/optimize", response_model=OptimizationResponse)
def optimize_route(request: OptimizationRequest):
    """
    Main endpoint for triggering the routing algorithm.
    Reads 'algorithm' from payload and routes it to the correct strategy.
    """
    algorithm_key = request.algorithm.lower()
    
    if algorithm_key not in STRATEGY_REGISTRY:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported algorithm '{algorithm_key}'. Valid options: {list(STRATEGY_REGISTRY.keys())}"
        )
        
    strategy = STRATEGY_REGISTRY[algorithm_key]
    
    # Start timer for metrics
    start_time = time.time()
    
    try:
        # Execute Strategy Pattern
        result = strategy.optimize(request)
        
        # Add execution time to metrics
        execution_time = time.time() - start_time
        result.execution_time_seconds = execution_time
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# To run this script locally without command line:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
