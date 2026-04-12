# BENCHMARK CVRPTW Architecture Plan

## Executive Summary
The benchmark system must support BOTH:
1. **TSP Problems** (from TSPLib) - Simple routing optimization
2. **CVRPTW Problems** (from Solomon instances) - Capacitated routing with time windows

The final product (Faz 4 Complete) already supports CVRPTW, so benchmark infrastructure must align.

## 1. Problem Type Classification

### TSP Problems (Current)
- Source: TSPLib instances (eil51, rat99, etc.)
- Structure: coordinates only, no capacities/time windows
- Strategies: ALL 18 strategies work
- Algorithms to benchmark: GA, PSO, GWO, HHO, Two-Opt, Greedy, Permutation, OR-Tools, PyVRP, VROOM

### CVRPTW Problems (New)
- Source: Solomon instances (RC201, C101, etc.) or custom
- Structure: coordinates + capacity + time windows (pickup/dropoff) + vehicle count
- Strategies: CVRPTW-capable ONLY (Split strategies + OR-Tools + PyVRP + VROOM)
- TSP-only strategies NOT supported: Permutation TSP, Two-Opt (need generalization)

## 2. BenchmarkProblem Data Structure (REVISED)

### Current (TSP-only)
```python
@dataclass
class BenchmarkProblem:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal_score: Optional[int] = None
    category: str = "medium"
```

### Proposed (TSP + CVRPTW)
```python
@dataclass
class BenchmarkProblem:
    # Common fields
    name: str
    problem_type: str  # "tsp" or "cvrptw"
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal_score: Optional[int] = None
    category: str = "medium"  # small, medium, large
    
    # CVRPTW-specific fields
    vehicle_count: int = 1  # For TSP: 1, For CVRPTW: 2-10
    vehicle_capacity: Optional[float] = None  # For CVRPTW
    customer_demands: Optional[List[float]] = None  # [node_0_demand, node_1_demand, ...]
    time_windows: Optional[List[Tuple[float, float]]] = None  # [(earliest, latest), ...]
    service_times: Optional[List[float]] = None  # Service duration at each node
    depot_index: int = 0  # Index of depot node
```

## 3. Strategy Dispatch Logic (Interface Adapter)

### Problem Type Detection
```python
def detect_problem_type(problem: BenchmarkProblem) -> Tuple[str, bool]:
    """
    Returns: (problem_type, is_cvrptw)
    """
    # TSP: no capacity, no time windows
    if problem.vehicle_count == 1 and not problem.vehicle_capacity:
        return ("tsp", False)
    
    # CVRPTW: has capacity OR time windows
    if problem.vehicle_capacity or problem.time_windows:
        return ("cvrptw", True)
    
    raise ValueError(f"Unknown problem type for {problem.name}")
```

### Algorithm Selection Based on Problem Type
```python
# TSP-compatible strategies
TSP_COMPATIBLE_STRATEGIES = {
    "ga", "pso", "gwo", "hho",              # Meta-heuristics
    "two_opt", "greedy",                     # Heuristics
    "permutation_tsp",                       # Exact (n<=10)
    "ortools_cvrp",                          # Works for TSP too
    "pyvrp", "vroom"                         # Optional solvers
}

# CVRPTW-compatible strategies
CVRPTW_COMPATIBLE_STRATEGIES = {
    "ga_split", "pso_split", "gwo_split", "hho_split",  # Pipeline B
    "ortools_cvrp",                                      # Handles CVRPTW
    "pyvrp", "vroom"                                     # Full CVRPTW support
}

# Incompatible combinations
INCOMPATIBLE_COMBINATIONS = {
    ("tsp", "ga_split"): "Split strategies designed for CVRPTW only",
    ("cvrptw", "permutation_tsp"): "Exact TSP not practical for CVRPTW",
}
```

### Strategy Dispatch Flow
```python
def dispatch_strategy(problem: BenchmarkProblem, algorithm_id: str) -> BaseRoutingStrategy:
    """
    Routes to correct strategy based on problem type.
    """
    problem_type, is_cvrptw = detect_problem_type(problem)
    
    # Validate compatibility
    if is_cvrptw and algorithm_id in ["permutation_tsp", "two_opt"]:
        raise ValueError(
            f"Algorithm {algorithm_id} not supported for CVRPTW. "
            f"Use: ga_split, pso_split, ortools, pyvrp, vroom"
        )
    
    if not is_cvrptw and algorithm_id.endswith("_split"):
        logger.warning(
            f"Using {algorithm_id} for TSP (overkill). "
            f"Better: ga, pso, gwo"
        )
    
    # Get strategy from registry
    from strategies import get_strategy
    strategy = get_strategy(algorithm_id)
    
    if not strategy:
        raise ValueError(f"Strategy not found: {algorithm_id}")
    
    return strategy
```

## 4. Strategy Adapter (_convert_benchmark_to_optimization_request)

### TSP Conversion
```python
def convert_tsp_to_optimization_request(
    problem: BenchmarkProblem,
    algorithm_params: Dict
) -> OptimizationRequest:
    """
    Convert TSP BenchmarkProblem → OptimizationRequest (single depot + students)
    """
    # First node (index 0) is depot
    depot = StudentNode(
        id="depot",
        latitude=problem.coordinates[0][0],
        longitude=problem.coordinates[0][1],
        node_type="depot"
    )
    
    # Remaining nodes are students
    students = [
        StudentNode(
            id=f"node_{i}",
            latitude=problem.coordinates[i][0],
            longitude=problem.coordinates[i][1],
            pickup_time_start=0,
            pickup_time_end=24*60,  # Full day
            dropoff_time_start=0,
            dropoff_time_end=24*60
        )
        for i in range(1, problem.dimension)
    ]
    
    return OptimizationRequest(
        students=students,
        depot=depot,
        vehicle_count=1,
        solver_timeout_seconds=300,
        # TSP has no capacity constraints
        algorithm_params=algorithm_params
    )
```

### CVRPTW Conversion
```python
def convert_cvrptw_to_optimization_request(
    problem: BenchmarkProblem,
    algorithm_params: Dict
) -> OptimizationRequest:
    """
    Convert CVRPTW BenchmarkProblem → OptimizationRequest (multiple vehicles + time windows)
    """
    # Depot
    depot = StudentNode(
        id="depot",
        latitude=problem.coordinates[problem.depot_index][0],
        longitude=problem.coordinates[problem.depot_index][1],
        node_type="depot"
    )
    
    # Customers with time windows and demands
    students = []
    for i in range(problem.dimension):
        if i == problem.depot_index:
            continue
        
        tw = problem.time_windows[i] if problem.time_windows else (0, 24*60)
        demand = problem.customer_demands[i] if problem.customer_demands else 0
        service_time = problem.service_times[i] if problem.service_times else 0
        
        students.append(
            StudentNode(
                id=f"customer_{i}",
                latitude=problem.coordinates[i][0],
                longitude=problem.coordinates[i][1],
                num_days=1,
                demand=demand,  # Capacity constraint
                pickup_time_start=tw[0],
                pickup_time_end=tw[1],
                service_time=service_time,  # Time window service duration
                # ... other fields
            )
        )
    
    # MultipleVehicles with capacity
    vehicles = [
        VehicleConfig(
            vehicle_id=f"vehicle_{j}",
            capacity=problem.vehicle_capacity or 1000,
            max_tour_time=24*60,
            availability_start=0,
            availability_end=24*60
        )
        for j in range(problem.vehicle_count)
    ]
    
    return OptimizationRequest(
        students=students,
        depot=depot,
        vehicle_count=problem.vehicle_count,
        vehicles=vehicles,
        solver_timeout_seconds=300,
        algorithm_params=algorithm_params
    )
```

## 5. Compatibility Matrix

### Algorithm × Problem Type Support
| Algorithm | TSP | CVRP | CVRPTW | Notes |
|-----------|-----|------|--------|-------|
| GA | ✅ | ✅ | ⚠️ (no time windows) | Pipeline A |
| PSO | ✅ | ✅ | ⚠️ (no time windows) | Pipeline A |
| GWO | ✅ | ✅ | ⚠️ (no time windows) | Pipeline A |
| HHO | ✅ | ✅ | ⚠️ (no time windows) | Pipeline A |
| GA-Split | ❌ | ✅ | ✅ | Pipeline B (CVRPTW native) |
| PSO-Split | ❌ | ✅ | ✅ | Pipeline B (CVRPTW native) |
| GWO-Split | ❌ | ✅ | ✅ | Pipeline B (CVRPTW native) |
| HHO-Split | ❌ | ✅ | ✅ | Pipeline B (CVRPTW native) |
| Greedy | ✅ | ✅ | ✅ | Simple heuristic |
| Two-Opt | ✅ | ⚠️ | ❌ | Local search (time windows problematic) |
| Permutation | ✅ | ❌ | ❌ | Exact (TSP only), n≤10 |
| OR-Tools | ✅ | ✅ | ✅ | Industry standard |
| PyVRP | ✅ | ✅ | ✅ | SOTA (if available) |
| VROOM | ✅ | ✅ | ✅ | Ultra-fast (if available) |

## 6. Updated _run_single_experiment

```python
def _run_single_experiment(
    self,
    problem: BenchmarkProblem,
    algorithm: AlgorithmConfig,
    run_number: int
) -> ExperimentResult:
    """
    Run a single algorithm on single problem (TSP or CVRPTW).
    
    Detects problem type, dispatches to correct strategy,
    converts data, and collects metrics.
    """
    start_time = time.time()
    
    try:
        # Step 1: Detect problem type (TSP vs CVRPTW)
        problem_type, is_cvrptw = detect_problem_type(problem)
        
        # Step 2: Dispatch strategy (with compatibility check)
        strategy = dispatch_strategy(problem, algorithm.algorithm_id)
        
        # Step 3: Convert BenchmarkProblem → OptimizationRequest
        if is_cvrptw:
            opt_request = convert_cvrptw_to_optimization_request(
                problem, 
                algorithm.params
            )
        else:
            opt_request = convert_tsp_to_optimization_request(
                problem, 
                algorithm.params
            )
        
        # Step 4: Run strategy (returns OptimizationResponse)
        opt_response = strategy.optimize(opt_request)
        
        # Step 5: Extract tour length from response
        # For TSP: sum of distances
        # For CVRPTW: sum of all route distances
        tour_length = calculate_tour_length(opt_response, problem)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Step 6: Calculate GAP if optimal known
        gap_percent = None
        if problem.optimal_score:
            gap_percent = ((tour_length - problem.optimal_score) / problem.optimal_score) * 100
        
        return ExperimentResult(
            algorithm=algorithm.algorithm_id,
            problem=problem.name,
            problem_type=problem_type,  # NEW: track problem type
            run_number=run_number,
            tour_length=tour_length,
            elapsed_ms=elapsed_ms,
            gap_percent=gap_percent,
            metadata={
                "problem_dimension": problem.dimension,
                "problem_category": problem.category,
                "problem_type": problem_type,
                "vehicle_count": problem.vehicle_count,  # NEW
                "algorithm_params": algorithm.params
            }
        )
    
    except Exception as e:
        logger.error(
            f"Experiment failed: {problem.name} × {algorithm.algorithm_id} "
            f"(run {run_number}): {e}"
        )
        # Return failed result OR raise (depending on error handling strategy)
        raise
```

## 7. Import Organization

### Current (WRONG - line 703)
```python
import threading  # ← In middle of function!
```

### Proposed (CORRECT - file top)
```python
# main.py - top of file after other imports
import threading
from concurrent.futures import ThreadPoolExecutor

# ... rest of imports
from benchmark_state import benchmark_state_manager, BenchmarkStatus
from strategies import get_strategy, STRATEGY_REGISTRY
```

## 8. Concurrent Benchmark Limit

### BenchmarkStateManager Enhancement
```python
MAX_CONCURRENT_BENCHMARKS = 3

class BenchmarkStateManager:
    def can_start_run(self) -> bool:
        """Check if we can start new benchmark without exceeding limit."""
        with self._lock:
            running_count = len([
                s for s in self._runs.values()
                if s.status == BenchmarkStatus.RUNNING
            ])
            return running_count < MAX_CONCURRENT_BENCHMARKS
```

### main.py Enforcement
```python
@app.post("/api/v1/benchmark/run")
def start_benchmark(...):
    # Check concurrent limit BEFORE creating run
    if not benchmark_state_manager.can_start_run():
        return {
            "error": "Maximum concurrent benchmarks reached",
            "max_concurrent": MAX_CONCURRENT_BENCHMARKS,
            "status": "queue",
        }, 429  # Too Many Requests
    
    # ... rest of function
```

## 9. Implementation Roadmap (Integrated into Faz 4.5)

### Phase 1: Infrastructure (Day 1)
- [ ] Update BenchmarkProblem dataclass
- [ ] Create problem type detection function
- [ ] Add compatibility matrix

### Phase 2: Strategy Adapter (Day 1-2)
- [ ] Implement convert_tsp_to_optimization_request()
- [ ] Implement convert_cvrptw_to_optimization_request()
- [ ] Implement dispatch_strategy() with validation

### Phase 3: Core Implementation (Day 2-3)
- [ ] Update _run_single_experiment() with real dispatch
- [ ] Update benchmark_runner.py with new logic
- [ ] Move imports (threading to file top)

### Phase 4: Concurrent Limits (Day 3)
- [ ] Add can_start_run() to BenchmarkStateManager
- [ ] Add validation in start_benchmark()
- [ ] Error response with 429 status

### Phase 5: Testing & Docs (Day 4)
- [ ] Unit tests for problem type detection
- [ ] Integration tests for strategy dispatch
- [ ] E2E test with both TSP and CVRPTW
- [ ] Update BENCHMARK_ARCHITECTURE_DEBT.md

## 10. Quality Gates (Before Merge)

- [ ] No stub code (random.uniform removed)
- [ ] Real algorithm execution
- [ ] Both TSP and CVRPTW tested
- [ ] Concurrent limit enforced (4th request → 429)
- [ ] All imports organized
- [ ] Thread safety verified
- [ ] Documentation updated

---

**Output:** This is the blueprint for implementing real algorithm dispatch with CVRPTW support.
Once this is committed and documented properly, the benchmark system is production-ready for both academic (TSP) and commercial (CVRPTW) use cases.
