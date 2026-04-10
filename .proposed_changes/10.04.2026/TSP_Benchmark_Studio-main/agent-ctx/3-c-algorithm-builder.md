# Task 3-c: Metaheuristic Algorithm Builder

## Agent: Algorithm Builder (Metaheuristics)

## Task: Build 4 metaheuristic algorithms (SA, GA, ACO, TS)

## Work Log:

### Phase 1: Initial Implementation
- Created `base.py` with `TSPAlgorithm` (ABC) and `AlgorithmResult` (dataclass)
- Created initial versions of all 4 algorithm files with pure-Python fallbacks
- Each algorithm: `np.random.seed(seed)`, time_limit checks, `AlgorithmResult` return

### Phase 2: Coordination with Parallel Agents
- Discovered `numba_utils.py` was created by a parallel agent with `two_opt_improve(route, dist_matrix, max_iter, first_improvement)` signature
- Discovered `local_search.py` was created by another parallel agent with comprehensive local search algorithms
- Discovered SA and GA were overwritten by another agent with enhanced implementations
- Added `_create_result()` convenience method and `display_name` property to `base.py` for compatibility

### Phase 3: Bug Fixes
- Fixed `tabu_search.py` boundary bug: `np.random.randint(ri + 2, n)` fails when `ri + 2 >= n`
  - Added guards for small n in diversification section
  - Fixed `current_length += best_move_delta` being applied incorrectly in diversification case
  - Added `calc_tour_length_numba()` recalculation after diversification moves

### Phase 4: Verification
- Smoke test with 5-city TSP: all 4 algorithms produce valid tours (tour_length=227.35)
- Test with 10-city TSP: SA=273.17, GA=275.29, ACO=280.88, TS=273.17
- All tours are valid permutations, convergence_history populated, execution_time_ms > 0

## Files Created/Modified:
- `core/algorithms/base.py` — Added `_create_result()` helper and `display_name` property
- `core/algorithms/simulated_annealing.py` — SA with cooling, reheat, swap/2-opt neighborhoods (parallel agent version)
- `core/algorithms/genetic_algorithm.py` — GA with OX/PMX crossover, tournament selection, periodic 2-opt (parallel agent version)
- `core/algorithms/ant_colony.py` — ACO with pheromone matrix, elite deposits, periodic 2-opt (parallel agent version)
- `core/algorithms/tabu_search.py` — TS with 2-opt/swap/mixed neighborhoods, tabu list, diversification (fixed boundary bug)
- `core/algorithms/__init__.py` — ALGORITHM_REGISTRY with factory function (parallel agent version)
- `core/__init__.py` — Core module exports

## Stage Summary:
- 4 metaheuristic algorithms: SA, GA, ACO, TS — all passing tests
- All use nearest neighbor for initial solution
- All support time_limit, seed, convergence history
- numba_utils available → JIT-compiled functions used automatically
- Pure-Python fallbacks via local_search module when numba unavailable
- ALGORITHM_REGISTRY provides unified factory: `get_algorithm("sa")`
