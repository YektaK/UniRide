Goal
----

* Improve academic_benchmark programs for TSP/ATSP benchmarking to find good algorithms/parameters for long-term CWVRP use

Constraints & Preferences
-------------------------

* User wants all 3 phases implemented (foundation fixes, algorithm upgrades, CWVRP readiness)
* For PSO: port swap-sequence velocity mechanism from bildiri2026 into `pso_strategy.py` directly — do NOT delegate to bildiri2026's PSO
* Long-term goal is CWVRP; TSP/ATSP benchmarking is the path to finding good algorithms and parameters

Progress
--------

### Done

* Read all source files for both numba and sota programs
* Ran all test suites: 28/29 passed (SOTA e2e: 17/17, SOTA parity: 3/3, gate validation: 6/6, robustness: 2/2)
* Identified 1 test failure: `test_numba_three_opt` — Numba cache path mismatch (`ModuleNotFoundError: No module named 'core'`)
* Root-caused bildiri2026 vs academic_benchmark performance gap (6 reasons)
* Formulated 3-phase improvement plan with prioritized items (14 items across P0-P3)
* Read current `pso_strategy.py` and `ga_strategy.py` for port planning
* Finalized detailed improvement plan and wrote todo list
* **Step 1 (P0)**: ATSP-correct 2-opt delta in `local_search_numba.py` (verified already done)
* **Step 2 (P0)**: Numba cache enabled with stable project-local dir (verified already done)
* **Step 3 (P1)**: Module-level `_DIST_MATRIX_CACHE` + `_build_or_get_dist_matrix()` — all 5 LS wrapper classes updated
* **Step 6 (P2)**: Swap-sequence PSO velocity ported into `pso_strategy.py` (`_diff_swaps`, `_apply_swaps`, `_combine_velocities`, `reinit_interval`, `max_velocity_size`)
* **Step 7 (P2)**: Swap-sequence PSO velocity ported into `run_interactive_benchmark_v2_numba.py` `_run_pso` (`_diff_swaps_str`, `_apply_swaps_str`, `_combine_velocities_str`)
* **Step 8 (P2)**: GA upgraded in `_run_ga`: tournament k=3, balanced swap/inversion mutation (50/50), `max_no_improvement` early stop
* **Step 9 (P2)**: Final aggressive 2-opt polishing always-on (300 iter) in `_run_meta_heuristic` — replaces profile-dependent `_refine_route`
* **Step 10 (P2)**: 3-opt search window bounded (`j_max=min(n-2,i+12)`, `k_max=min(n-1,j+12)`) in `local_search_numba.py`
* **Step 4 (P1)**: Numpy-backed distance matrix path in `run_interactive_benchmark_v2_numba.py` and `master_numba_engine.py`:
  * Added `create_np_distance_matrix()` + `create_np_duration_func()` with O(1) index lookup and prebuilt matrix attributes
  * `_build_or_get_dist_matrix()` in `local_search_numba.py` upgraded with fast path: detects `_np_dist_matrix` attribute, reuses prebuilt `np.ndarray` (zero extra O(n²) passes)
  * `run_single_test()` and `run_single_test_with_matrix()` both converted to numpy path
* **Step 5 (P2)**: bildiri2026 GA/PSO integrated as first-class strategies in `master_numba_engine.py`:
  * `_run_bildiri_solver()` generic adapter handles depot-index alignment (bildiri2026 node 0 = depot; our routes are 1..n)
  * `_run_bildiri_pso()` / `_run_bildiri_ga()` thin wrappers expose canonical bildiri2026 solver params
  * `BILDIRI_STRATEGIES` list with `B-PSO` and `B-GA` entries
  * `_all_strategy_specs()` extended to include bildiri strategies
  * `_evaluate_param_combo()` routes `BILDIRI_PSO` / `BILDIRI_GA` payloads through the new adapters
  * DoE parameter spaces for B-PSO and B-GA added to `_build_numba_parameter_space()`

### In Progress

* Steps 11-14 (CWVRP readiness): larger refactors across multiple files, pending user direction

### Blocked

* (none)

Key Decisions
-------------

* All 3 phases to be implemented in order: P0→P1→P2→P3
* PSO swap-sequence velocity to be ported into `pso_strategy.py`, not delegated to bildiri2026
* 14 improvement items prioritized across 3 phases with effort/impact estimates
* PSO swap-sequence velocity also to be ported into `run_interactive_benchmark_v2_numba.py` `_run_pso`

Next Steps
----------

1. **P0**: Fix ATSP-incorrect 2-opt delta in `local_search_numba.py` (add reversal correction loop for ATSP)
2. **P0**: Enable Numba cache — remove `NUMBA_CACHE_DIR=os.devnull`, set `cache=True` on all `@jit`
3. **P1**: Cache distance matrix per problem (add numpy dist matrix cache, pass `np.ndarray` to Numba kernels)
4. **P1**: Refactor `master_numba_engine.py` to use integer routes + `np.ndarray` distance matrices
5. **P1**: Integrate bildiri2026 GA/PSO as first-class strategies in Numba engine (port PSO swap-sequence velocity into `pso_strategy.py`)
6. **P2**: Port swap-sequence velocity into `pso_strategy.py` (swap-sequence + Clerc constriction from bildiri2026)
7. **P2**: Port swap-sequence velocity into `run_interactive_benchmark_v2_numba.py` `_run_pso`
8. **P2**: Upgrade GA selection (tournament k=3 + balanced swap/inversion mutation + `max_no_improvement` early stop)
9. **P2**: Add final aggressive 2-opt polishing to all metaheuristics in `_run_meta_heuristic`
10. **P2**: Bound 3-opt search window (`j_max=min(n-2, i+12)`, `k_max=min(n-1, j+12)`)
11. **P3**: Unified `ProblemInstance` dataclass (coordinates, dist_matrix np.ndarray, demands, capacity, depot, is_symmetric)
12. **P3**: ATSP benchmark support (`EDGE_WEIGHT_SECTION` explicit matrix problems: ftv33, ftv35, ftv38, ftv44, ftv55, ftv70, rbg323)
13. **P3**: Statistical comparison utilities (Wilcoxon signed-rank, Friedman test, box plots, convergence curves)
14. **P3**: CVRP feasibility-aware local search wrappers (capacity checking on 2-opt/3-opt/Or-opt)

Critical Context
----------------

* `local_search_numba.py:97-122`: `_two_opt_delta_numba` is ATSP-incorrect — missing reversal correction loop (`for k in range(i+1,j): delta += d[route[k+1],route[k]] - d[route[k],route[k+1]]`)
* `local_search_numba.py:42`: `os.environ["NUMBA_CACHE_DIR"] = os.devnull` + `cache=False` → every ProcessPool worker recompiles Numba from scratch
* `local_search_numba.py:600-622`: `_prepare_numba_inputs()` rebuilds entire dist matrix O(n²) per LS call
* `master_numba_engine.py` uses `Dict[str, Dict[str, float]]` + `List[str]` routes — forces string↔int conversion, prevents direct Numba array ops
* `pso_strategy.py` uses `_towards_route` with `MOVE_SCALE=0.1` — weak vs bildiri2026's `_diff_swaps` swap-sequence velocity + Clerc constriction
* `ga_strategy.py` already has tournament selection (k=3) + OX crossover, but lacks balanced swap/inversion mutation and early stop
* `base_solver.py:48-55` (bildiri2026): precomputes `_dist_matrix_np` once via `_build_np_cache()`, reused by all Numba kernels
* bildiri2026 solvers apply aggressive 2-opt (300 iter) to best solution after metaheuristic completes — not done in academic_benchmark
* 3-opt in `local_search_numba.py` is unbounded O(n³) full scan; bildiri2026 uses bounded window (±12)
* `sota_tsp/base_solver.py` lacks `exclude_depot` and `_time_matrix` support that `bildiri2026/core/base_solver.py` has
* `dataset_loader.py` only supports coordinate-based TSPLIB (EUC_2D, CEIL_2D) — no `EDGE_WEIGHT_SECTION` for ATSP

Relevant Files
--------------

* `academic_benchmark/master_numba_engine.py`: main numba benchmark engine, delegates to optimizer_api
* `academic_benchmark/master_sota_engine.py`: SOTA benchmark engine (E2BSO, R2DMA, P-AOEA)
* `academic_benchmark/bildiri2026/core/numba_accel.py`: Numba JIT kernels (2-opt, 3-opt, Or-opt, Swap), `cache=True`
* `academic_benchmark/bildiri2026/core/base_solver.py`: base class with `_build_np_cache()`, `_tour_length_fast()`, ATSP support, `exclude_depot`
* `academic_benchmark/bildiri2026/core/ga_solver.py`: GA with OX crossover, 2-opt polished init, final aggressive 2-opt, tournament k=3
* `academic_benchmark/bildiri2026/core/pso_solver.py`: PSO with `_diff_swaps` swap-sequence velocity, Clerc constriction, reinit, final 2-opt
* `academic_benchmark/bildiri2026/core/two_opt.py`, `three_opt.py`, `or_opt.py`: LS solvers with Numba fast-path
* `academic_benchmark/sota_tsp/base_solver.py`: SOTA base — lacks `exclude_depot`, `_time_matrix`
* `academic_benchmark/sota_tsp/ls_engine.py`: MultiLayerLS (light/moderate/full chains), imports numba_accel from bildiri2026
* `academic_benchmark/sota_tsp/e2bso_tsp.py`, `r2dma_tsp.py`, `paoea_tsp.py`: SOTA solvers
* `academic_benchmark/dataset_loader.py`: TSPLIB loader — coordinates only, no EDGE_WEIGHT_SECTION
* `optimizer_api/utils/local_search_numba.py`: Numba LS with `cache=False`, ATSP-incorrect 2-opt delta, per-call `_prepare_numba_inputs()`
* `optimizer_api/strategies/pso_strategy.py`: PSO with `_towards_route` velocity — needs swap-sequence port
* `optimizer_api/strategies/ga_strategy.py`: GA with tournament selection already, needs balanced mutation + early stop
* `optimizer_api/tests/run_interactive_benchmark_v2_numba.py`: legacy GA/PSO with string routes, dict matrix — PSO also needs swap-sequence port
  
  

Implementation Plan — Ready to Execute
--------------------------------------

### Phase 1: Foundation Fixes (P0)

**1. Fix ATSP-incorrect 2-opt delta** in `optimizer_api/utils/local_search_numba.py:97-121`

* Current: `_two_opt_delta_numba` only computes `new_cost - original_cost` using 4 edges
* Fix: Add reversal correction loop `for k in range(i+1, j): delta += d[route[k+1], route[k]] - d[route[k], route[k+1]]` (as in bildiri2026 `numba_accel.py:55-56`)
* This is a correctness bug — results are wrong for ATSP (asymmetric) problems
* For symmetric TSP, the correction loop sums to 0, so this change is safe

**2. Enable Numba cache** in `optimizer_api/utils/local_search_numba.py:42`

* Remove `os.environ["NUMBA_CACHE_DIR"] = os.devnull` (line 42)
* Change all `cache=False` to `cache=True` on `@jit` decorators
* Must also fix the multiprocessing import context issue (use `NUMBA_CACHE_DIR` pointing to a stable path instead of disabling)

### Phase 2: Performance & Architecture (P1)

**3. Cache distance matrix per problem** — eliminate per-call `_prepare_numba_inputs()` O(n²) rebuild

* Add a module-level or class-level `_dist_matrix_cache` dict
* Key: frozenset of route nodes; Value: (np.ndarray dist_matrix, dict index_map)
* Currently `_prepare_numba_inputs` is called in every `TwoOptLocalSearch.improve()`, `ThreeOptLocalSearch.improve()`, etc.

**4. Refactor `master_numba_engine.py`** to use integer routes + `np.ndarray` distance matrices

* Currently uses `Dict[str, Dict[str, float]]` + `List[str]` routes — forces string↔int conversion at every step
* Change `DOEProblem` to include `dist_matrix: np.ndarray`
* Pass integer arrays directly to Numba kernels

**5. Integrate bildiri2026 GA/PSO as first-class strategies in Numba engine**

* Port the integer-route + numpy cache pattern from bildiri2026 into the numba engine

### Phase 3: Algorithm Quality (P2)

**6. Port swap-sequence PSO velocity into `pso_strategy.py`**

* Replace `_get_difference_swaps` (position-indexed, probabilistic) with `_diff_swaps` (swap-sequence, deterministic) from bildiri2026
* Replace `_update_velocity` (inertia with probability threshold) with `_combine_velocities` (Clerc-style probabilistic per-component)
* Add `_apply_swaps` (deterministic apply) alongside probabilistic `_apply_velocity`
* Add `reinit_interval` for periodic swarm diversity

**7. Port swap-sequence PSO velocity into `run_interactive_benchmark_v2_numba.py` `_run_pso`**

* Replace `_towards_route` + `MOVE_SCALE=0.1` with `_diff_swaps` + `_combine_velocities` pattern
* Currently uses weak `_towards_route` which scales moves by `MOVE_SCALE=0.1` — too conservative

**8. Upgrade GA** in `ga_strategy.py` and `_run_ga`

* `ga_strategy.py`: Already has tournament k=3 + OX. Add balanced swap/inversion mutation (50/50 like bildiri2026 `_mutate`) + `max_no_improvement` early stop
* `_run_ga` in benchmark v2: Currently uses roulette-like selection from top half, no tournament. Add tournament k=3, add inversion mutation alongside swap, add early stop

**9. Add final aggressive 2-opt polishing** to all metaheuristics in `_run_meta_heuristic`

* Current `_refine_route` does 300-iter 2-opt for quality_first profile — this is already close
* But bildiri2026 applies 300-iter 2-opt specifically to the best solution **after** the metaheuristic completes
* Make the 2-opt polishing always-on (not profile-dependent), 300 iterations, matching bildiri2026

**10. Bound 3-opt search window** in `local_search_numba.py`

* Current: unbounded O(n³) full scan
* Fix: `j_max = min(n-2, i+12)`, `k_max = min(n-1, j+12)` (as in bildiri2026 `numba_accel.py:179-182`)

### Phase 4: CWVRP Readiness (P3)

**11. Unified `ProblemInstance` dataclass** **12. ATSP benchmark support** (EDGE_WEIGHT_SECTION) **13. Statistical comparison utilities** **14. CVRP feasibility-aware local search wrappers**

* * *

### Execution Order

| Step  | Item                              | File(s)                                                   | Risk                                                | Est.  |
| ----- | --------------------------------- | --------------------------------------------------------- | --------------------------------------------------- | ----- |
| 1     | ATSP 2-opt delta fix              | `local_search_numba.py`                                   | Low — additive for symmetric                        | 15min |
| 2     | Enable Numba cache                | `local_search_numba.py`                                   | Medium — cache path must be stable across processes | 20min |
| 3     | Cache dist matrix per problem     | `local_search_numba.py`                                   | Low                                                 | 20min |
| 4     | Integer routes + np dist matrices | `master_numba_engine.py`                                  | Medium — large refactor                             | 45min |
| 5     | Integrate bildiri2026 GA/PSO      | `master_numba_engine.py`                                  | Medium                                              | 30min |
| 6     | PSO swap-sequence (strategy)      | `pso_strategy.py`                                         | Low                                                 | 25min |
| 7     | PSO swap-sequence (benchmark)     | `run_interactive_benchmark_v2_numba.py`                   | Low                                                 | 25min |
| 8     | GA upgrades                       | `ga_strategy.py`, `run_interactive_benchmark_v2_numba.py` | Low                                                 | 20min |
| 9     | Final aggressive 2-opt            | `run_interactive_benchmark_v2_numba.py`                   | Low                                                 | 10min |
| 10    | Bound 3-opt window                | `local_search_numba.py`                                   | Low                                                 | 10min |
| 11-14 | CWVRP readiness                   | Multiple                                                  | Medium-High                                         | 2-3hr |
