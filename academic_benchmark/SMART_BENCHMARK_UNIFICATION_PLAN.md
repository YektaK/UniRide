# 🚀 Smart Benchmark Unification Master Plan

**Date:** 2026-05-13  
**Goal:** Create a highly flexible, unified benchmarking suite that merges the best of Numba, SOTA, Legacy UX, and Bildiri2026 pipeline paradigms.  
**Target Audience:** Core Developers, Auto-Coding Agents.

---

## 1. 🎯 Vision & Architectural Shift

The current architecture is fragmented. We have `master_numba_engine.py` and `master_sota_engine.py` doing largely the same things but in isolation. We have excellent interactive UI/UX lost in the `legacy/` folder, and a very clean configuration-pipeline architecture trapped in `bildiri2026/`.

**The Target Architecture:** A single `smart_benchmark.py` engine using the **Strategy/Registry Pattern**. The engine handles the heavy lifting (multiprocessing, TSPLIB parsing, ETA calculation, progress logging) and dynamically dispatches tasks to specific algorithm strategies (Numba GA, SOTA E2BSO, Bildiri PSO), allowing direct, identical-condition comparisons.

---

## 2. 🗺️ Phase-by-Phase Execution Plan

### Phase 1: Core Engine Unification & Legacy UX Restoration
*Goal: Create the scaffolding for the unified `smart_benchmark.py` engine.*

- [x] **Task 1.1:** Create `academic_benchmark/smart_benchmark.py` (or rename/refactor `master_numba_engine.py`).
- [x] **Task 1.2:** Implement an `AlgorithmRegistry`.
    - Create a registry that maps string names (`"GA"`, `"E2BSO-TSP"`, `"B-PSO"`) to their respective executor functions or wrapper classes.
    - Standardize the input/output signature for all solver tasks.
- [x] **Task 1.3:** Restore `legacy/run_smart_benchmark.py` UX.
    - Port the `DynamicTimeEstimator` (which uses past runs to predict ETA accurately).
    - Port the interactive CLI menus (`multi_select_problems`, `multi_select_algorithms`).
    - Port the detailed pre-flight cache summary ("X runs cached, Y runs new").
- [x] **Task 1.4:** Introduce Strict Dataclasses.
    - Define `ProblemInstance` (dimension, coordinates, optimal, distance_matrix).
    - Replace all `Dict[str, Any]` passing between the main process and worker pools with these dataclasses to prevent silent schema drift.

### Phase 2: The "Bildiri" Pipeline & Configuration
*Goal: Adopt Configuration-as-Code for granular execution control.*

- [x] **Task 2.1:** Decouple Config Generation from Execution.
    - Instead of immediately running grid searches, build a `generate_run_config()` mode that outputs a `run_config.json` defining the exact tasks (problem, algorithm, seed, specific parameters).
- [x] **Task 2.2:** Execute from Config.
    - Add a mode to `smart_benchmark.py` to read `run_config.json` and execute it precisely. This allows researchers to manually edit the JSON to force specific parameters for single runs without changing code.

### Phase 3: High-Performance & Academic Algorithmic Upgrades
*Goal: Push the engine's speed and academic rigor to state-of-the-art levels.*

- [x] **Task 3.1:** Numba Multiprocessing Warmup Phase (Critical Lock Fix).
    - *Issue:* Windows `ProcessPoolExecutor` uses `spawn`, causing fresh processes to clash over Numba `.nbi` cache files or redundantly JIT compile.
    - *Fix:* Before opening the multiprocessing pool, the main thread must run `burma14` ($N=14$) once. This safely compiles and locks the cache sequentially, giving all spawned workers instant $O(1)$ load times.
- [x] **Task 3.2:** KNN Subgraph Sparsification.
    - *Issue:* $O(N^2)$ local search is too slow for $N > 500$.
    - *Fix:* During `ProblemInstance` creation, calculate a K-Nearest Neighbor mask ($K=20$). Modify 2-opt/3-opt kernels to only attempt edge swaps if the nodes are within each other's 20 nearest geographic neighbors.
- [x] **Task 3.3:** Hardware-Independent Metrics (MaxFE).
    - Modify the NumPy duration functions to increment an internal `function_evaluations` counter upon every lookup. Log this metric alongside `time_ms` for robust academic reporting.

### Phase 4: Advanced Tuning & Dashboard Proofs
*Goal: Generate publication-ready statistical analysis and optimize intelligently.*

- [x] **Task 4.1:** Bayesian Optimization (Optuna Integration).
    - Replace the Cartesian Grid Search DoE with `optuna`. Define search spaces (e.g., `pop_size: int(50, 200)`) and let Bayesian Optimization find the peak parameters in ~70% fewer runs.
- [x] **Task 4.2:** Dashboard Automated Statistical Proofs.
    - Update `dashboard.py`. Add a "Statistical Significance" tab.
    - Implement a Wilcoxon Signed-Rank Test script that compares the raw multi-run data of two selected algorithms.
    - Automatically output LaTeX: `\textbf{Algorithm A} statistically significantly outperforms Algorithm B ($p < 0.05$).`
- [x] **Task 4.3:** Convergence Curve Visualizations.
    - Fix the solver logging to output a true array of `[best_cost_iter_1, best_cost_iter_2, ...]`.
    - Plot these arrays in the dashboard as Line Charts (Iteration vs. Cost) to analyze exploration/exploitation curves.

---

## 3. 🤖 Agent Delegation Guide

If another AI agent picks up this project, they should follow this context:

1.  **Architecture:** Do NOT duplicate code across Numba/SOTA. If a utility function is needed, it goes in `benchmark_utils.py` or a new `engine_core.py`.
2.  **Multiprocessing Rule:** Always assume `spawn` behavior for Windows. Do not pass large dictionaries or unpicklable objects through multiprocessing queues. Use the Dataclasses defined in Phase 1.4.
3.  **UI Policy:** Do not remove CLI interactivity. The user wants the `legacy` interactive menus where they can explicitly select specific algorithms and problems via aliases (`all`, `small`, `berlin52`).
4.  **Academic Standard:** Never assume `time_ms` is the only metric. Always aim to include `function_evaluations` (MaxFE) and ensure gap percentages are logged at the raw per-run level, not just as aggregates.
