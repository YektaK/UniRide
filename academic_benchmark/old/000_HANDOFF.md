# UniRide Smart Benchmark Engine - Handoff Document

This document summarizes the current architectural state, recent bug fixes, and the structural pipeline of the UniRide Smart Benchmark Engine. It is intended to quickly onboard the next AI agent or developer to continue Phase 4 (Analysis & Paper Generation) and address any remaining edge-case problems.

## 1. Architectural State (The "Config-as-Code" Engine)
The benchmarking pipeline has been successfully unified into a single, high-performance execution engine (`academic_benchmark/smart_benchmark.py`) that handles both **Legacy Numba Heuristics** and **Modern SOTA Solvers**.

*   **Engine Core (`academic_benchmark/engine_core.py`)**: Houses the standardized `ProblemInstance`, `RunResult`, `BenchmarkConfig`, and the `AlgorithmRegistry`.
*   **Smart Benchmark (`academic_benchmark/smart_benchmark.py`)**: The interactive CLI and `multiprocessing.Pool` orchestrator. It acts as the wrapper that unifies I/O, config serialization, and algorithm execution.
*   **Legacy Numba Executors**: Imported directly from `optimizer_api.tests.run_interactive_benchmark_v2_numba.py`.
*   **SOTA Executors**: Imported from `academic_benchmark.sota_tsp` (e.g., `E2BSO_TSP`, `PAOEA_TSP`, `R2DMA_TSP`).

## 2. Recent Critical Patches (Must Read)
To ensure mathematical validity across different TSPLIB coordinate domains, several "Monkey Patches" are dynamically applied at runtime. **Do not remove these without refactoring the underlying legacy solvers.**

1.  **TSPLIB Geographic (GEO) & Pseudo-Euclidean (ATT) Distances**:
    *   *Bug*: SOTA and Numba solvers were hardcoded to use Cartisian `math.hypot()` logic, causing catastrophic Gap % errors on non-Cartesian problems like `ulysses22` (-98%) and `att48` (+215%).
    *   *Fix*: `smart_benchmark.py`'s `load_problems()` now explicitly parses the `EDGE_WEIGHT_TYPE` from the `.tsp` files and mathematically builds the exact matrix. The engine then uses Python subclassing/monkey-patching to forcefully inject this `dist_matrix` into the solvers right before execution.
2.  **Missing Optimals (`Gap: ERR`)**:
    *   *Bug*: `pr76` and potentially other problems were missing from the global dictionary.
    *   *Fix*: Added to `TSPLIB_OPTIMALS` in `academic_benchmark/benchmark_utils.py`.
3.  **HHO (Harris Hawks Optimization) Poor Performance**:
    *   *Bug*: `Numba-HHO` lacked the final combinatorial local-search polish present in GA/PSO, causing 300%+ gaps.
    *   *Fix*: Added `_apply_2opt_to_route(best, duration_func, max_iter=300)` to the end of `_run_hho` in `run_interactive_benchmark_v2_numba.py`.
4.  **Terminal Copy/Paste Interference**:
    *   *Fix*: `Ctrl+C` (`SIGINT`) is now explicitly ignored (`pass`) in `smart_benchmark.py` so the user can highlight and copy terminal logs. The graceful shutdown (CSV saving) is instead wired to **`Ctrl+X`** or **`Ctrl+Q`** using a non-blocking `msvcrt.kbhit()` checker inside the worker pool loop.

## 3. Pending Tasks & Known Issues for the Next Agent
*   **Phase 4: LaTeX & Academic Proof Generation**: The `SMART_BENCHMARK_UNIFICATION_PLAN.md` calls for finalizing the dashboard to automatically generate LaTeX tables and Wilcoxon Signed-Rank test exports.
*   **Algorithm Verification**: While HHO was fixed, the user noted they are continuing work on "the rest of the problems". Watch for other continuous-to-discrete metaheuristics (e.g., GWO) that might still be underperforming or requiring better parameter tuning via Optuna.
*   **Progress UI**: If the console gets cluttered on Windows, consider implementing a single-line `tqdm` style progress bar that clears itself effectively, though the current padded `\r` implementation works securely.
*   **Parameter Persistence**: The current engine asks for custom JSON parameters at runtime. Implementing a way to save these custom parameter overrides into the persistent `BenchmarkConfig` state (`run_config.json`) would improve workflow continuity.
