# UniRide Improvement & Remediation Roadmap

## Phase 1: Forensic Audit Remediation (COMPLETED)

All technical debt tasks from the April 2026 Codebase Analysis have been fully remediated and verified via dedicated test suites.

- [x] **FIX-01 to FIX-03 (Split Decoder TW Limits):** Fixed negative departure calculations, accumulated correct time window violations during Dropoff, and constrained backward calculations strictly to the limits of each individual trip iteration boundary. Verified via `tests/test_split_decoder_audit.py`.
- [x] **FIX-04 & FIX-08 (Travel Fallback Standardization):** Extracted standalone 15.0 magic numbers across the entire suite of metaheuristic algorithms (GA, PSO, GWO, HHO, PyVRP, VROOM, Greedy, 2-Opt) and substituted them with `DEFAULT_TRAVEL_FALLBACK_MINUTES`. Integrated centralized `logger.warning` events to emit telemetry upon every route network failure.
- [x] **FIX-05, FIX-06, FIX-07 (Deduplication):** Eliminated `main.old.py` clutter. Consolidated inline `_minutes_to_time` and cross-module `haversine_distance` into their respective utility domains (`data_loader.py` and constants).
- [x] **FIX-11 (GAP Calculation Benchmarks):** Rectified TSPLIB parsing and rounding heuristics (Standard NINT Rounding instead of Python's Banker's Rounding `round()`). This eliminates artificial compression of distances which theoretically caused the "Negative GAP" bugs mapping routes to mathematically impossible short distances.
- [x] **Smoke Tests:** Created `tests/test_all_strategies_smoke.py` validating that every registered algorithm can instantiate and process a fully-loaded time window optimization payload without raising exceptions or encountering missing internal references.

---

## Phase 2: System Improvements & Evolution (PROPOSED NEXT STEPS)

With the core routing algorithms stabilized, standard unified fallback behaviors applied, and TSPLIB validation fixed, focus should shift to system operability, UI/UX, and data ingress optimization.

### 1. Unified Algorithm Parameter Config UI (Frontend)
Currently, algorithms like GA, PyVRP, or PSO have disparate internal hardcoded settings or static payload assumptions (e.g., population sizes, generation iterations, temperature).
*   **Actionable:** Build an advanced settings form (drawer/modal) in the frontend. When a user selects "Genetic Algorithm", dynamically expose its parameter config (Population Size: [number], Max Iterations: [number]), and pass these directly via the `configs` dictionary inside `OptimizationRequest`.

### 2. Time Matrix Database Observability
With the insertion of `logger.warning("Distance Matrix MISS...")`, we now have logging whenever Supabase yields an incomplete pairwise edge matrix. 
*   **Actionable:** Add an admin observability dashboard or daily cron job mapping out "Nodes with highest Missing Rate". This provides actionable data mapping out what coordinate boundaries the Supabase API is choking on. Include automated cache invalidation logic upon manual corrections.

### 3. Data Loader / Memory Optimization (Backend)
Currently, `haversine_distance` acts as a hard fallback, but large scale multi-school problem instances will compute an exponentially increasing amount of O(N^2) data permutations.
*   **Actionable:** Implement an external standard library like `scipy.spatial.distance_matrix` using memory-mapped `.npy` blobs for huge workloads, drastically limiting compute time during dynamic routing, especially for the high-end meta-heuristics like local search permutation building.

### 4. Continuous Integration / End-to-End Pipeline
Currently, the codebase executes the tests linearly at times. Certain dependencies (like `pandas`, `pytest`) are missing globally from system runners but exist locally in virtual machines.
*   **Actionable:** Stand up a standard `.github/workflows/python-app.yml` or containerized `.gitlab-ci.yml` file to formalize the installation of Python 3.12/3.14 via poetry or pip and run `test_all_strategies_smoke.py` and `run_all_tests.py` automatically before any pull request merger to `main`. This prevents regressions.

### 5. Multi-Depot and Dynamic Load Balancing
With CVRP successfully modeled, the logic revolves around single Depot dispatching. In practical university operations, different vehicles might stage at different satellite campus lots.
*   **Actionable:** Broaden the `OptimizationRequest` array to accept `[depots]` (multiple keys). Evolve the `SplitDecoder` to factor in vehicle-specific starting depots using algorithms akin to MDVRP processing.
