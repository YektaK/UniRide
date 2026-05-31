# Implementation Plan — FCM Split-Route-Stitch (FCM-SRS) Meta-Solver Wrapper

**Status:** Implemented as a core-first research preview (as of 31 May 2026). The active implementation is `uniride_core/algorithms/fcm_split_engine.py` with academic registry entries for `FCM-GA-TSP`, `FCM-PSO-TSP`, `FCM-GWO-TSP`, and `FCM-HHO-TSP`. A repeatable SQLite comparison runner exists at `academic_benchmark/run_fcm_srs_comparison.py` with CLI runtime controls. Controlled 144-node and 256-node SQLite comparison runs have completed successfully; broader real/academic dataset validation is still required before promotion.
**Prerequisites:** BaseTSPSolver refactoring ✅, all 5 solver `_solve()` migration ✅, `solve_with_matrix()` API ✅

Introduce a unified `FCMSplitSolverWrapper` inside `uniride_core` that applies Fuzzy C-Means (FCM) clustering to dynamically partition large TSP problems into $K$ spatial sub-problems, routes them in parallel using PSO/GA/HHO/GWO variants, stitches them using fuzzy border heuristics, and polishes the connections with JIT local search.

---

## 1. Executive Concept

Large-scale TSP problems (e.g., $N \ge 1,000$) suffer from combinatorial explosion in swarm optimizations. By combining the **Fuzzy C-Means (FCM) Clustering Strategy** (from `optimizer_api/utils/clustering_strategies/fuzzy_cmeans.py`) with our JIT-accelerated metaheuristics (`GA_TSP`, `PSO_TSP`, etc.), we establish a highly efficient **Divide-and-Conquer Swarm Solver**.

---

## 2. Key Architectural Decisions

1.  **Unified Wrapper Pattern:** Rather than modifying the individual GA, PSO, GWO, and HHO solvers (which would copy-paste the clustering logic 4+ times), we wrap them dynamically via a single parameterized `FCMSplitSolverWrapper` class inheriting from `BaseTSPSolver`.
2.  **Shared Clustering Engine Import:** The wrapper directly imports and leverages the existing production-grade `fuzzy_c_means_core` from `optimizer_api/utils/clustering_strategies/fuzzy_cmeans.py`, ensuring zero logic duplication.
3.  **Optuna Tuning Extension:** We expose `fcm_clusters` and `fcm_m` as explicit parameter space variables. This lets the `TuningOrchestrator` automatically discover the optimal number of clusters and fuzziness per problem dimension.

---

## 3. Open Questions for Feedback

1.  **FCM Fuzziness $m$ Bounds:** Should we restrict the fuzziness coefficient $m$ range to $[1.1, 3.0]$ inside Optuna tuning to prevent numerical instability (division by zero or infinite distances) during membership matrix updates?
2.  **Depot-0 ATSP Offset Integration:** Standard TSPLIB files are 0-indexed without depots, whereas live production requests prepend depot coordinates at index 0. The stitching manager must handle both transparently based on `is_time_matrix`.
3.  **Sub-problem Concurrency:** Should we enable `ProcessPoolExecutor` multitasking inside the sub-problem routing phase, or rely entirely on the outer benchmark worker pool parallelization? (Outer-only parallelization is recommended to prevent oversubscription).

---

## 4. Proposed Changes

### 4.1 Create `fcm_split_wrapper.py` in `uniride_core`
#### [NEW] [fcm_split_wrapper.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/algorithms/sota_tsp/fcm_split_wrapper.py)
*   Create a clean meta-solver class `FCMSplitSolverWrapper` that inherits from `BaseTSPSolver`.
*   Implement `solve(coordinates)` to:
    1.  Convert float coordinates to `Point` structures.
    2.  Run `fuzzy_c_means_core` to split the map.
    3.  Instantiate the wrapped `base_solver_cls(base_config)` per sub-problem.
    4.  Extract sub-matrices from precomputed parent matrices when available.
    5.  Stitch tours using spatial nearest-neighbor boundary joins.
    6.  Run `MultiLayerLS.improve()` to polish boundary anomalies.

---

### 4.2 Register Hybrid Variants in Benchmark Registry
#### [MODIFY] [registry_setup.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/core/registry_setup.py)
*   Import `FCMSplitSolverWrapper` and your base JIT-heuristics (`Numba-GA`, `Numba-PSO`, etc.).
*   Register hybrid versions dynamically: `FCM-GA-TSP`, `FCM-PSO-TSP`, `FCM-GWO-TSP`, `FCM-HHO-TSP`.
*   Parse `fcm_clusters` (default 3) and `fcm_m` (default 2.0) from parameters, passing the remainder to the inner solver configs.

---

### 4.3 Add Parameter Spaces for Tuning
#### [MODIFY] [param_spaces.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/param_spaces.py)
*   Add parameter space definitions for the new `FCM-*` algorithms:
    *   `fcm_clusters`: `int` in `[2, 6]` (Grid search `[2, 3, 4]`).
    *   `fcm_m`: `float` in `[1.5, 2.5]`.
    *   Plus inherited parameters from their respective base solvers.

---

## 5. Verification Plan

### 5.1 Automated Tests
*   **Smoke Test Suite:** Create a new unit test `uniride_core/tests/sota_tsp/test_fcm_hybrid.py` to:
    1.  Verify that wrapping `E2BSO_TSP` or `R2DMA_TSP` instantiates without error.
    2.  Solve a trivial 10-node coordinate set and assert the tour contains each index exactly once.
    3.  Assert the computed `tour_length` is consistent with `tour_length()`.
*   **CLI Run Verification:** Run a dry tuning cycle from the console to verify that Optuna correctly samples `fcm_clusters` and passes sub-problem evaluations:
    ```bash
    powershell -ExecutionPolicy Bypass -Command "python -m academic_benchmark"
    ```

### 5.2 Manual Verification
*   **Dashboard Validation:** Launch the streamlit dashboard and verify that the results for `FCM-GA-TSP` are logged, showing gaps and execution times against pure baselines.
