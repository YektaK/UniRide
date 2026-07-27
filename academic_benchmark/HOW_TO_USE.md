# UniRide Academic Benchmark — How to Use

**Date:** 2026-07-27
**Version:** 3.6
**Location:** `academic_benchmark/`

---

## Quick Start

```bash
# 1. Run the main benchmark (recommended for most users)
python -m academic_benchmark.smart_benchmark

# 2. View results dashboard
streamlit run academic_benchmark/dashboard.py

# 3. Run tests
python -m pytest academic_benchmark/tests/ -v
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     smart_benchmark.py                          │
│              (Main Unified CLI — Start Here)                     │
├─────────────────────────────────────────────────────────────────┤
│                      cli_engine.py                              │
│                    (Consolidated Engine)                         │
│   ┌──────────────────┐   ┌──────────────────────────────┐       │
│   │ Numba Strategies │   │ SOTA Solvers (via registry)  │       │
│   │ 2-opt            │   │ E2BSO-TSP                    │       │
│   │ 3-opt-bounded    │   │ E2BSO-TSP-CPSO               │       │
│   │ swap, insert     │   │ R2DMA-TSP                    │       │
│   │ or-opt, 2.5-opt  │   │ P-AOEA-TSP                   │       │
│   │ Numba-GA/PSO     │   │ CGO-TSP, RUN-TSP             │       │
│   │ Numba-GWO/HHO    │   │ ALNS-TSP                     │       │
│   │ Core-GWO/HHO     │   └──────────────────────────────┘       │
│   │ Split aliases    │                                          │
│   │                  │   AlgorithmRegistry (shared)             │
│   │                  │   ┌──────────────────────────────┐       │
│   └──────────────────┘   │ register()                   │       │
│                          │ register_param_space()       │       │
│                          │ execute()                    │       │
│                          └──────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Shared Infrastructure                         │
├──────────────────┬──────────────────┬───────────────────────────┤
│ benchmark_utils  │   engine_core    │    param_db               │
│ • TSPLIB_OPTIMALS│ • ProblemInstance│ • SQLite param store      │
│ • compute_gap()  │ • RunResult      │ • get_best_for()          │
│ • BSFTracker     │ • AlgorithmReg   │ • save_result()           │
│ • ProblemSelector│ • BenchmarkTask  │ • list_entries()          │
│ • save_metadata  │ • BenchmarkConfig│                           │
├──────────────────┴──────────────────┴───────────────────────────┤
│                    Data Layer                                    │
├──────────────────┬──────────────────┬───────────────────────────┤
│ tsplib.db        │ benchmark_db/    │ configs/                  │
│ • problems       │ • progress.csv   │ • tuning configs          │
│ • dist_matrices  │ • results.csv    │ • saved param sets        │
│ • best_solutions │ • metadata.json  │                           │
└──────────────────┴──────────────────┴───────────────────────────┘
```

---

## Algorithm List (18 Listed TSP/ATSP Entries)

| #   | Algorithm           | Engine        | Type                     | ATSP | Complexity      |
| --- | ------------------- | ------------- | ------------------------ | ---- | --------------- |
| 1   | Numba-2-opt         | Numba         | Local Search             | ✅    | O(n²)           |
| 2   | Numba-3-opt-bounded | Numba         | Local Search             | ✅    | O(n·w²)         |
| 3   | Numba-Or-opt        | Numba         | Local Search             | ✅    | O(n²)           |
| 4   | Numba-Swap          | Numba         | Local Search             | ✅    | O(n²)           |
| 5   | Numba-Hybrid        | Numba         | Local Search             | ✅    | O(n³)           |
| 6   | Numba-GA            | Numba         | Meta-heuristic           | ✅    | O(pop·gen·n)    |
| 7   | Numba-PSO           | Numba         | Meta-heuristic           | ✅    | O(swarm·iter·n) |
| 8   | Numba-GWO           | `uniride_core` | Meta-heuristic (memetic) | ✅    | O(pop·iter·n)   |
| 9   | Numba-HHO           | `uniride_core` | Meta-heuristic (memetic) | ✅    | O(pop·iter·n)   |
| 10  | Core-GWO-TSP        | `uniride_core` | Meta-heuristic (memetic) | ✅    | O(pop·iter·n)   |
| 11  | Core-HHO-TSP        | `uniride_core` | Meta-heuristic (memetic) | ✅    | O(pop·iter·n)   |
| 12  | E2BSO-TSP           | SOTA          | Hybrid (Entropy+ALNS)    | ✅    | O(pop·iter·n²)  |
| 13  | E2BSO-TSP-CPSO      | SOTA          | Hybrid (Canonical PSO)   | ✅    | O(pop·iter·n²)  |
| 14  | R2DMA-TSP           | SOTA          | Hybrid (Resonance+ALNS)  | ✅    | O(pop·iter·n²)  |
| 15  | P-AOEA-TSP          | SOTA          | Hybrid (Genome+ALNS)     | ✅    | O(pop·iter·n²)  |
| 16  | CGO-TSP             | SOTA          | Hybrid (Chaos Game+OX)   | ✅    | O(pop·iter·n²)  |
| 17  | RUN-TSP             | SOTA          | Hybrid (RK4+ESQ)         | ✅    | O(pop·iter·n²)  |
| 18  | ALNS-TSP            | SOTA          | Adaptive LNS + SA        | ✅    | O(iter·n²)      |

### GWO/HHO Algorithm Naming

The active GWO/HHO identities resolve to the canonical classes in
`uniride_core/algorithms/tsp_matrix_metaheuristics/`:

| CLI Name       | Canonical class | Guidance |
| -------------- | --------------- | -------- |
| `Numba-GWO`    | `GWOOptimizer`  | Compatibility registry identity |
| `Numba-HHO`    | `HHOOptimizer`  | Compatibility registry identity |
| `Core-GWO-TSP` | `GWOOptimizer`  | Canonical core identity |
| `Core-HHO-TSP` | `HHOOptimizer`  | Canonical core identity |

`B-GA` and `B-PSO` are retired aliases. Do not route them to archived Bildiri
classes or revive top-level `core.*` fallback imports. Select explicit canonical
pure or memetic variants when a study contract requires that distinction.

### E2BSO-TSP vs E2BSO-TSP-CPSO

| Feature          | E2BSO-TSP (Edge-Heritage)             | E2BSO-TSP-CPSO (Canonical PSO)                                 |
| ---------------- | ------------------------------------- | -------------------------------------------------------------- |
| **Swarm Update** | Edge-force injection (3-5 edges)      | Swap-sequence velocity (v = w·v + c1·r1·Δpbest + c2·r2·Δgbest) |
| **Parameters**   | `p_best`, `p_gbest`, `n_edges`        | `c1`, `c2`, `inertia`, `velocity_max_ratio`                    |
| **DoE Space**    | gamma, injection_rate, remove_ratio   | c1:[1.0,1.5,2.0], c2:[1.0,1.5,2.0], inertia:[0.5,0.7,0.9]      |
| **Use Case**     | TSP-native, focuses on edge structure | General purpose, momentum-based convergence                    |

---

## Program Guide

### 1. `smart_benchmark.py` — Main Unified CLI (Recommended)

**Purpose:** Single entry point for all benchmark operations. Manages both Numba and SOTA engines through a unified menu.

**Run:**

```bash
python -m academic_benchmark.smart_benchmark
```

**Menu Flow:**

```
┌─────────────────────────────────────────────┐
│         UNIRIDE AKADEMIK BENCHMARK          │
├─────────────────────────────────────────────┤
│ [1] TUNING (Parametre Optimizasyonu)        │
│ [2] BENCHMARK (Performans Degerlendirme)    │
│ [3] KARSILASTIRMALI (Numba vs SOTA)         │
│ [4] LOAD CONFIG (Kayitli Ayarlari Yukle)    │
│ [5] PARAMETRE DB (Parametre Veritabani)     │
│ [D] DASHBOARD (Sonuclari Gorsellestir)      │
│ [Q] CIKIS                                   │
└─────────────────────────────────────────────┘
```

**Option 1 — Tuning:**

- Select problems (by dimension range, category, or individual)
- Select algorithms (Numba, SOTA, or both)
- Choose tuning strategy:
  - `[G]` Grid Search — exhaustive, thorough
  - `[F]` Fractional — 1/4 of grid, faster
  - `[B]` Bayesian (Optuna) — smart search, best for high-dim spaces
- Results saved to `benchmark_db/metadata.json` and `param_db`

**Option 2 — Benchmark:**

- Select problems and algorithms
- Choose parameter source:
  - `[B]` Load best from DB (uses tuned params)
  - `[M]` Manual entry
  - `[D]` Default params
- Set run count (3-10 recommended) and worker count
- Results saved to CSV and metadata

**Option 3 — Comparative (Numba vs SOTA):**

- Runs both engines side-by-side on same problems
- Same param selection flow as Option 2
- Best for paper comparisons

**Option 4 — Load Config:**

- Load previously saved benchmark configurations
- Re-run with same settings

**Option 5 — Parametre DB:**

- View, export, or clear stored parameter sets
- See which problem/algorithm combos have tuned params

**Keyboard Controls During Execution:**

- `Ctrl+C` — No-op (intentional, safe for copy-paste from terminal)
- `Ctrl+Q` or `Ctrl+X` — Graceful shutdown (saves results, exits cleanly)
- `q` or `x` — Also triggers graceful shutdown

---

### 2. `cli_engine.py` — Consolidated Engine

**Purpose:** Single engine for all Numba + SOTA algorithms. Replaces the old `master_numba_engine.py` and `master_sota_engine.py`. This is the engine that `smart_benchmark.py` delegates to.

**Algorithms:** Active Numba, canonical `uniride_core` GWO/HHO, and SOTA identities are registered through `core/registry_setup.py` and dispatched by `cli_engine.py`.

**Run:**

```bash
# Interactive mode
python -m academic_benchmark.cli_engine

# CLI mode
python -m academic_benchmark.cli_engine --mode tuning --problems berlin52,eil51 --runs 5
python -m academic_benchmark.cli_engine --mode default --problems berlin52 --algos Core-GWO-TSP,E2BSO-TSP --runs 3
```

**CLI Arguments:**
| Flag | Description | Example |
|------|-------------|---------|
| `--mode` | `tuning`, `default`, or `benchmark` | `--mode tuning` |
| `--problems` | Comma-separated problem names | `--problems berlin52,eil51` |
| `--algos` | Comma-separated canonical algorithm names | `--algos Core-GWO-TSP,E2BSO-TSP` |
| `--runs` | Number of runs per combo | `--runs 5` |
| `--workers` | Parallel worker count | `--workers 4` |
| `--size-limit` | Max problem dimension | `--size-limit 100` |

**Menu Flow:**

```
┌─────────────────────────────────────────────┐
│       CLI ENGINE — Ana Menu                 │
├─────────────────────────────────────────────┤
│ [1] TUNING (Grid/Fractional/Bayesian)       │
│ [2] BENCHMARK (DB/Manual/Default params)    │
│ [3] QUICK BENCHMARK (Default params only)   │
│ [D] DASHBOARD                               │
│ [Q] CIKIS                                   │
└─────────────────────────────────────────────┘
```

---

### 3. `dashboard.py` — Streamlit Dashboard

**Purpose:** Visualize benchmark results with interactive charts.

**Run:**

```bash
streamlit run academic_benchmark/dashboard.py
```

**Tabs:**

1. **Overview** — Summary stats, total runs, algorithms, problems
2. **Results** — Full result table with filtering
3. **Comparison** — Side-by-side algorithm comparison
4. **Gap Analysis** — Gap% distribution charts
5. **Performance** — Runtime analysis
6. **Heatmap** — Problem × Algorithm gap matrix
7. **Progress** — Benchmark completion status

**Data Sources:**

- `benchmark_db/benchmark_progress.csv` — All run results
- `benchmark_db/results.csv` — Aggregated results
- `benchmark_db/metadata.json` — Tuning metadata

---

### 4. `tsplib_manager.py` — TSPLIB Database Manager

**Purpose:** Manage the TSPLIB SQLite database (`tsplib.db`). Load, verify, and query problem instances.

**Run:**

```bash
python -m academic_benchmark.tsplib_manager --help
```

**Commands:**
| Command | Description |
|---------|-------------|
| `load <path>` | Load TSPLIB files into database |
| `list` | List all problems in database |
| `show <name>` | Show details for a problem |
| `verify` | Verify all problem data integrity |
| `export <name>` | Export a problem to TSPLIB format |
| `stats` | Show database statistics |

**Example:**

```bash
python -m academic_benchmark.tsplib_manager list
python -m academic_benchmark.tsplib_manager show berlin52
python -m academic_benchmark.tsplib_manager verify
```

---

### 5. Bildiri2026 Canonical Study Profile

The removed `run_numba_with_bildiri_params.py` runner is quarantined and must
not be executed. The active, reviewable contract is
`academic_benchmark/studies/bildiri2026/study.json`, which pins the ft53 ATSP
dataset manifest, canonical GWO/HHO variant IDs, paired seeds, fixed-budget
primary protocol, native-termination secondary protocol, and smoke-only
repository output policy.

Validate the profile and quarantine before preparing any run:

```bash
python -m pytest academic_benchmark/tests/test_bildiri_study_profile.py -q -p no:cacheprovider
python -m academic_benchmark.archive_manifest verify --repo-root . --manifest archive/academic_benchmark/bildiri2026_legacy/manifest.json
```

The profile is a draft study contract, not a standalone runner and not proof of
paper-scale reproduction. Use only the canonical registry IDs declared by the
profile; keep paper-scale outputs outside the repository.

---

### 6. `param_db.py` — Parameter Database Module

**Purpose:** SQLite-backed storage for tuned parameters. Not a standalone CLI — used by engines.

**Key Functions:**
| Function | Description |
|----------|-------------|
| `save_result(problem, algo, params, score)` | Save a param set with its score |
| `get_best_for(problem, algo)` | Get best params for a problem/algorithm pair |
| `list_entries()` | List all stored entries |
| `clear()` | Clear all entries |

**Database Location:** `benchmark_db/param_db.sqlite`

---

### 7. `benchmark_utils.py` — Shared Utilities

**Purpose:** Common functions used across all benchmark components. Not a standalone CLI.

**Key Functions:**
| Function | Description |
|----------|-------------|
| `compute_gap(problem, cost, optimal)` | Compute gap% with BSF fallback |
| `TSPLIB_OPTIMALS` | Dict of known optimal values (~130 instances) |
| `BSFTracker` | Track best-so-far solutions for unknown-optimal problems |
| `ProblemSelector` | Interactive problem selection by dimension/category |
| `save_metadata(path, metadata)` | Save benchmark metadata to JSON |
| `load_metadata(path)` | Load benchmark metadata from JSON |
| `append_csv_row(path, fields, row)` | Thread-safe CSV append |

---

### 8. `engine_core.py` — Core Dataclasses

**Purpose:** Shared data structures. Not a standalone CLI.

**Key Classes:**
| Class | Description |
|-------|-------------|
| `ProblemInstance` | Problem data (name, dimension, coordinates, dist_matrix, knn_mask) |
| `RunResult` | Single run result (problem, algorithm, gap, elapsed, tour) |
| `AlgorithmRegistry` | Global registry for algorithm executors, param spaces, warmup |
| `BenchmarkTask` | Task definition for parallel execution |
| `BenchmarkConfig` | Benchmark configuration |

---

## Tuning Strategies

TUNING modunda 3 strateji mevcuttur:

| Strategy                  | Description                                             | Advantage                                      | Disadvantage                      |
| ------------------------- | ------------------------------------------------------- | ---------------------------------------------- | --------------------------------- |
| **[G] Grid Search**       | Tests every combo, picks best tested                    | Comprehensive, deterministic                   | Very slow (exponential combos)    |
| **[F] Fractional**        | Random subsample of grid                                | Faster                                         | May miss optimal combo            |
| **[B] Bayesian (Optuna)** | TPE surrogate model, finds optima between tested points | Best results, finds values between grid points | Probabilistic, repeats may differ |

### Optuna Dynamic Queue Architecture (v3.4+)

Optuna tuning now uses a **dynamic queue (ask/tell) architecture**. This keeps all workers 100% busy:

```
Main Process:
  ├── Creates all Optuna studies (one per problem-algorithm pair)
  ├── Calls study.ask() to generate trial params
  ├── Submits tasks to ProcessPoolExecutor (fills all workers)
  └── As results arrive: study.tell() → check early stop → submit next trial

Workers (e.g., 8 cores):
  ├── Pull trial tasks → run solver → return gap value
  ├── Fast trials (Numba: seconds) cycle through quickly
  ├── Slow trials (SOTA: minutes) occupy 1-2 workers but don't block others
  └── All workers stay busy 100% of the time
```

**Early Stopping:** A study stops automatically when gap ≤ 0.01% for 3 consecutive trials. On small problems (berlin52), 3-4 trials suffice instead of 50 → **95% time savings**.

**Tie-Breaking:** When multiple trials achieve the same gap, the **fastest** one is selected. This provides more efficient parameter sets for large-scale benchmarking.

### Optuna vs Response Surface (Design-Expert)

| Feature                     | Optuna (TPE)                   | Response Surface (Design-Expert)     |
| --------------------------- | ------------------------------ | ------------------------------------ |
| **Model**                   | Probabilistic (kernel density) | Deterministic (quadratic polynomial) |
| **Optimum location**        | Anywhere in space              | Limited to quadratic surface         |
| **Categorical params**      | Native support                 | Requires dummy variables             |
| **Non-linear interactions** | Captures complex patterns      | Only quadratic interactions          |
| **Sample efficiency**       | High (adaptive sampling)       | Requires structured design points    |
| **Output**                  | Best point + uncertainty       | Equation: y = β₀ + Σβᵢxᵢ + Σβᵢᵢxᵢ²   |

> **Note:** For meta-heuristic tuning, Optuna is generally superior because response surfaces are rarely quadratic — they contain plateaus, cliffs, and irregular regions. In practice, Optuna finds 5-15% better solutions because it can search between grid points and handle categorical params naturally. Response Surface should only be added if an analytical equation is needed for academic analysis (e.g., "population_size has the strongest main effect, β=0.42").

---

## Bildiri2026 Quarantine and Canonical Profile

The original pipeline is archived at
`archive/academic_benchmark/bildiri2026_legacy/` and is historical evidence
only. Its 233-entry manifest classifies 133 files as
`HISTORICAL_UNVERIFIED`, 7 as `INVALID`, and 93 as `REFERENCE_ONLY`. Archived
configuration generators, tuning/benchmark runners, analyzers, visualizers,
data managers, orchestrators, tuned databases, and result files are not active
commands.

Current authority is split deliberately:

- Solver code: `uniride_core/algorithms/tsp_matrix_metaheuristics/`.
- Study contract: `academic_benchmark/studies/bildiri2026/study.json`.
- Dataset contract: `academic_benchmark/datasets/ft53.json` plus the pinned
  `academic_benchmark/tsplib_data/ft53.atsp` artifact.
- Quarantine integrity: `archive/academic_benchmark/bildiri2026_legacy/manifest.json`.

Do not import from `academic_benchmark.bildiri2026`, top-level `core.*`, or any
archived runner. Validate the study/profile tests and manifest before using a
canonical registry executor.

---

## Process Flows

### Flow 1: First-Time User (Recommended Path)

```
1. smart_benchmark.py
   ├── [1] TUNING
   │   ├── Select problems (e.g., berlin52, eil51, st70)
   │   ├── Select algorithms (e.g., Core-GWO-TSP, Core-HHO-TSP, E2BSO-TSP)
   │   ├── Choose [B]ayesian (Optuna) — best for most cases
   │   └── Wait for tuning to complete (~5-30 min)
   │
   ├── [2] BENCHMARK
   │   ├── Select same problems + algorithms
   │   ├── Choose [B] DB params (uses tuned results)
   │   ├── Set runs=5, workers=auto
   │   └── Wait for benchmark (~10-60 min)
   │
   └── [D] DASHBOARD
       └── Review results in browser

2. Results saved to:
   ├── benchmark_db/benchmark_progress.csv
   ├── benchmark_db/results.csv
   ├── benchmark_db/metadata.json
   └── benchmark_db/param_db.sqlite
```

### Flow 2: Quick Comparison (Default Params)

```
1. smart_benchmark.py
   ├── [3] KARSILASTIRMALI
   │   ├── Select problems (small set: berlin52, eil51)
   │   ├── Select algorithms (mix of Numba + SOTA)
   │   ├── Choose [D] Default params
   │   ├── Set runs=3, workers=auto
   │   └── Run (~5-15 min)
   │
   └── [D] DASHBOARD
       └── Quick comparison view
```

### Flow 3: Prepare a Bildiri2026 Reproduction Study

```
1. Validate the canonical study and ft53 dataset manifests.
2. Verify the 233-entry legacy quarantine manifest.
3. Use only the canonical GWO/HHO IDs declared in study.json.
4. Keep repository runs smoke-only; place paper-scale artifacts externally.
5. Report the exact commands, environment, seeds, and validation results.
```

The archived pipeline cannot establish reproducibility and must not be run.

### Flow 4: Single Algorithm Deep Dive

```
1. cli_engine.py
   ├── [1] TUNING
   │   ├── Select one problem (e.g., berlin52)
   │   ├── Select one algorithm (e.g., Core-GWO-TSP)
   │   ├── Choose [G] Grid Search (exhaustive)
   │   └── Wait for tuning
   │
   ├── [2] BENCHMARK
   │   ├── Select same problem + algorithm
   │   ├── Choose [B] DB params
   │   ├── Set runs=30 (statistical significance)
   │   └── Run
   │
   └── Analyze results in metadata.json
```

---

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  TSPLIB      │────▶│  Problem     │────▶│  Engine      │
│  Files       │     │  Instance    │     │  (Numba/SOTA)│
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌──────────────┐     ┌──────▼───────┐
                     │  Dashboard   │◀────│  RunResult   │
                     │  (Streamlit) │     │  (gap, time) │
                     └──────┬───────┘     └──────┬───────┘
                            │                    │
                     ┌──────▼───────┐     ┌──────▼───────┐
                     │  CSV Files   │◀────│  Metadata    │
                     │  (progress,  │     │  (JSON)      │
                     │   results)   │     └──────┬───────┘
                     └──────────────┘            │
                                                  │
                     ┌──────────────┐     ┌──────▼───────┐
                     │  Param DB    │◀────│  Tuning      │
                     │  (SQLite)    │     │  Results     │
                     └──────────────┘     └──────────────┘
```

---

## CSV Schemas

**benchmark_summary.csv:**

```
problem, strategy, avg_length, avg_gap, avg_time_ms, n_runs
```

**benchmark_progress.csv:**

```
timestamp, problem, strategy, avg_length, avg_gap, avg_time_ms, n_runs, result_type, params_json
```

- `result_type = "raw"`: single run (SOTA engine)
- `result_type = "aggregate"`: param combo average (Numba engine)

---

## Configuration

### Environment Variables

| Variable               | Default | Purpose                                  |
| ---------------------- | ------- | ---------------------------------------- |
| `OPENBLAS_NUM_THREADS` | 1       | Prevent OpenBLAS multiprocessing crashes |
| `NUMEXPR_NUM_THREADS`  | 1       | Prevent NumExpr thread conflicts         |
| `OMP_NUM_THREADS`      | 1       | Prevent OpenMP thread conflicts          |
| `MKL_NUM_THREADS`      | 1       | Prevent MKL thread conflicts             |

**Note:** These are set automatically at module top in `cli_engine.py`. Do not override unless you know what you're doing.

### File Locations

| Path                                                     | Purpose                          |
| -------------------------------------------------------- | -------------------------------- |
| `academic_benchmark/tsplib.db`                           | TSPLIB problem database (SQLite) |
| `academic_benchmark/benchmark_db/`                       | Benchmark results directory      |
| `academic_benchmark/benchmark_db/benchmark_progress.csv` | All run results                  |
| `academic_benchmark/benchmark_db/results.csv`            | Aggregated results               |
| `academic_benchmark/benchmark_db/metadata.json`          | Tuning metadata + best params    |
| `academic_benchmark/benchmark_db/param_db.sqlite`        | Parameter database               |
| `academic_benchmark/benchmark_db/configs/`               | Saved benchmark configurations   |
| `academic_benchmark/benchmark_db/history/`               | Interrupted benchmark saves      |

---

## Developer Guide

### Adding a New Algorithm (5 Steps)

**Step 1:** Write the solver in an active package (`uniride_core/algorithms/sota_tsp/new_algo.py` or `uniride_core/algorithms/<family>/new_algo.py`)

```python
from .base_solver import BaseTSPSolver, TSPResult

@dataclass
class YeniAlgoConfig:
    population_size: int = 40
    max_iterations: int = 500
    seed: int = 42

class YeniAlgo(BaseTSPSolver):
    def __init__(self, config=None):
        super().__init__("YeniAlgo", config.seed if config else 42)
        self.cfg = config or YeniAlgoConfig()

    def solve(self, coordinates):
        self._set_problem(coordinates)
        # ... algorithm implementation ...
        return TSPResult(algorithm="YeniAlgo", tour=best, tour_length=best_cost, ...)
```

**Step 2:** Export it from the active package `__init__.py`; never add code under the archived Bildiri tree.

```python
from .yeni_algo import YeniAlgo, YeniAlgoConfig
__all__ = [..., "YeniAlgo", "YeniAlgoConfig"]
```

**Step 3:** In `cli_engine.py`:

```python
# Add to ALL_ALGOS list
ALL_ALGOS = [..., "YENI-ALGO"]

# Add to _make_solver_config
"YENI-ALGO": {"population_size": pop, "max_iterations": max_iter, ...}

# Add to _build_sota_parameter_space
if algo_name == "YENI-ALGO":
    return {"population_size": [24, 36, 48], ...}

# Add to _make_solver factory
if algo_name == "YENI-ALGO":
    return YeniAlgo(YeniAlgoConfig(seed=seed, **cfg))
```

**Step 4:** Write test (`tests/test_yeni_algo.py`)

**Step 5:** Run tests

```bash
python -m pytest academic_benchmark/tests/ -v --tb=short
```

### Adding a New Problem

TSPLIB problems are loaded automatically from `ALL_tsp.tar.gz` archive. To add manually:

```bash
# Extract a single problem
python academic_benchmark/tsplib_manager.py extract --problems berlin52

# With size limit
python academic_benchmark/tsplib_manager.py extract --size-limit 200
```

For custom time_matrix JSON problems, add JSON file to `academic_benchmark/data/` folder.

---

## Troubleshooting

### "No module named 'academic_benchmark'"

Run from the project root (`UniRide/`), not from inside `academic_benchmark/`.

### "Pickle error: cannot pickle local class"

This was the C-02 bug. Fixed in 2026-05-19. If you still see it, update your code.

### "AttributeError: 'Result' object has no attribute 'elapsed_ms'"

This was the C-04 bug. Fixed in 2026-05-19.

### "Gap shows 754200%"

This was the C-03 bug. Fixed in 2026-05-19. Unknown-optimal problems now show "N/A".

### "NameError: name 'Path' is not defined"

This was the C-05 bug. Fixed in 2026-05-19.

### Dashboard shows no data

Check that `benchmark_db/benchmark_progress.csv` exists and has data. Run a benchmark first.

### Ctrl+C crashes the benchmark

Ctrl+C is intentionally a no-op (safe for copy-paste). Use `Ctrl+Q` or `Ctrl+X` to stop gracefully.

### Streamlit dashboard won't open

```bash
pip install streamlit
streamlit run academic_benchmark/dashboard.py
```

### Optuna not installed

```bash
pip install optuna
```

### ProcessPoolExecutor hang

Try `--workers 1` with a single worker to isolate the issue.

### Numba compilation error

```bash
pip install --upgrade numba numpy
```

**Known environment issue (2026-06):** The current Python environment has NumPy 2.5.0 installed,
but Numba requires NumPy ≤ 2.4. Numba is not installed and the JIT-accelerated paths
(`@njit` kernels in `numba_accel.py`) degrade to pure Python fallbacks. The algorithms still
work correctly but run ~10-50x slower than with Numba. To restore JIT acceleration:

```bash
pip install "numpy<2.5" numba
```

### "'_Problem' object has no attribute 'prepare_matrices'"

This was fixed on 2026-06-30. The CLI worker's internal `_Problem` wrapper in `cli_engine.py`
was missing the `prepare_matrices()` method needed by registry-backed algorithms (GWO, HHO).
Update your code to get the fix.

### Matrix comes back None

Run `tsplib_manager.py compute-dm` to precompute distance matrices.

---

## Migration Notes

### 2026-05-19: DB Param Key Format Change (H-04)

**What changed:** DB parameter keys changed from `{algo: params}` to `{f"{prob.name}::{algo}": params}`.

**Why:** Multi-problem DB loads silently overwrote params (last problem won). New format stores per-problem params correctly.

**Impact:**

- Old metadata files still work via legacy fallback
- New tuning runs produce per-problem keys
- To get correct per-problem params: re-run tuning

**See:** `AUDIT_FINDINGS_2026-05-19.md` Appendix C for full details.

### 2026-05-19: 3-opt Renamed to 3-opt-bounded

**What changed:** Algorithm name changed from `"3-opt"` to `"3-opt-bounded"` to reflect the ±12 scan window.

**Impact:** Any saved configs or scripts referencing `"3-opt"` need updating to `"3-opt-bounded"`.

### 2026-05-19: Optuna Parallelization (D-01 to D-04)

**What changed:** Optuna tuning migrated from `study.optimize()` loop to `study.ask()` / `study.tell()` dynamic queue architecture.

**Why:** Previous approach ran studies sequentially (1 worker active, rest idle). Now all workers stay busy regardless of algorithm speed differences.

**Impact:**

- 5-10x faster tuning for mixed workloads (Numba + SOTA together)
- Early stopping: small problems stop after 3-4 trials instead of 50
- Tie-breaking: fastest params selected among equal-gap trials
- Progress output shows real-time trial count and active workers

**See:** `PARALLELIZATION_STRATEGY_2026-05-19.md` for full architecture details.

---

## Testing

```bash
# Run all tests
python -m pytest academic_benchmark/tests/ -v

# Run specific test file
python -m pytest academic_benchmark/tests/test_critical_fixes.py -v

# Run with coverage
python -m pytest academic_benchmark/tests/ --cov=academic_benchmark -v
```

**Test files:**
| File | Coverage |
|------|----------|
| `test_critical_fixes.py` | C-01, C-03, C-04, C-05, C-06, H-06 regression tests |
| `test_core_tsp_registry.py` | Registry executors, including canonical `uniride_core` GWO/HHO classes |
| `test_sota_e2e.py` | SOTA solver end-to-end tests |
| `test_sota_parity.py` | SOTA algorithm parity tests |
| `test_numba_three_opt.py` | 3-opt-bounded correctness |
| `test_benchmark_robustness.py` | Worker backend + seed stability |
| `test_problem_selector.py` | Problem selection logic |

**Current status:** Run the pinned verification commands in `WORKLOG.md`; do not rely on a static count in this guide.

---

## Academic Methodology (English)

*The following sections are adapted from `CLASSICAL_PAPER_METHODOLOGY.md` and `SOTA_PAPER_METHODOLOGY.md` and are ready for inclusion in academic publications.*

### Classical Paper Methodology

To rigorously evaluate the performance of classical meta-heuristic algorithms (e.g., Genetic Algorithm, Particle Swarm Optimization, Grey Wolf Optimizer, and Harris Hawks Optimization) on the Traveling Salesman Problem (TSP), a custom, high-performance computational infrastructure was developed. This custom-built "Numba-Accelerated Benchmark Engine" was designed to bridge the gap between high-level algorithmic flexibility and low-level computational efficiency, establishing a standardized environment for fair comparative analysis.

#### JIT-Optimized Meta-heuristic Implementation

A primary challenge in benchmarking complex meta-heuristics using high-level interpreted languages, such as Python, is the inherent execution overhead that can skew computational time analyses. To resolve this, the proposed framework integrates Just-In-Time (JIT) compilation technology via the Numba library. Core algorithmic routines, including fitness evaluations, population updates, and local search operations, were compiled directly into optimized machine code (`@njit(nogil=True)`). This approach effectively eliminated interpreter latency, achieving execution speeds comparable to native C++ implementations while preserving the dynamic adaptability required for algorithmic modifications.

To maintain strict computational rigor, a mandatory "Warm-up" protocol was instituted. Since JIT compilation requires an initial overhead during the first execution of any compiled function, this compilation time was explicitly isolated and excluded from all benchmark measurements. Consequently, the reported execution times strictly reflect the mathematical efficiency and convergence speed of the algorithms, rather than the underlying language mechanics.

#### Parameter Standardization via Design of Experiments

In heuristic-based optimization, algorithm performance is highly sensitive to hyperparameter configurations. To eliminate human bias and prevent overfitting to specific problem topologies, hyperparameters were neither manually selected nor randomly assigned. Instead, a rigorous "Design of Experiments" (DoE) methodology was implemented.

Prior to the formal benchmarking phase, a dedicated DoE module performed a systematic grid search across the multidimensional parameter space of each algorithm. This procedure evaluated various combinations of parameters across a representative subset of TSPLIB instances. The configurations yielding the optimal balance between solution quality (gap percentage) and convergence stability were extracted and uniformly applied during the final evaluation phase.

#### Parallel Execution and Computational Stability

Given the combinatorial explosion inherent to the TSP and the necessity for statistically significant trial repetitions, the framework was engineered for massive scalability. A robust, Windows-safe parallel processing architecture was deployed utilizing a `ProcessPoolExecutor`. Unlike traditional multi-processing models that are prone to memory leaks and synchronization deadlocks on certain operating systems, this isolated memory-space approach ensured high throughput and process stability across multi-core architectures.

Furthermore, strict protocols for data integrity and reproducibility were established. An incremental result persistence mechanism was designed to log experimental outputs (e.g., route lengths, convergence gaps, and execution times) into distinct Comma-Separated Values (CSV) files in real time. This was coupled with a metadata-driven state management system (`metadata.json`) that continuously tracked the execution status of the benchmark matrix.

### SOTA Paper Methodology

To ensure a high-fidelity evaluation of complex, modern solvers for the Traveling Salesman Problem (TSP)—specifically State-of-the-Art (SOTA) algorithms such as E²BSO, R²DMA, P-AOEA, CGO, and RUN—a custom "Unified SOTA Benchmark Engine" was conceptualized and developed.

#### Unified Evaluation Framework for SOTA Solvers

Evaluating SOTA algorithms necessitates an architecture that accommodates significant variations in algorithmic complexity, structural memory footprints, and search paradigms. The developed framework employs a consolidated architectural pattern, standardizing the input-output interfaces across entirely different solver topologies.

To bridge the operational differences between these algorithms, an adaptive evaluation methodology was introduced. This methodology incorporates dynamically assigned local search budgets and time-matrix integrations, ensuring that algorithms are not only tested under idealized distance models but also under realistic, varied constraint scenarios.

#### Algorithmic Adaptations for Large-Scale Stability

While the core generative mechanisms and mathematical operators of E²BSO, R²DMA, P-AOEA, CGO, and RUN were strictly preserved to ensure theoretical fidelity, several critical architectural adaptations were engineered to facilitate large-scale, production-grade execution:

1. **Adaptive Local Search Budgets:** Canonical implementations frequently rely on unbounded local search neighborhoods. On massive instances (exceeding 1,000 nodes), this induces a combinatorial explosion (O(N²) to O(N³)), leading to severe computational deadlocks. To resolve this, a dimension-adaptive budget manager was integrated, dynamically bounding search depths based on the problem size (N).

2. **Distance Metric Agnosticism (Asymmetric Capability):** Original SOTA solvers are predominantly hardcoded to process symmetric 2D Euclidean spatial graphs. Our framework abstracts the evaluation objective function entirely, rendering the solvers "metric agnostic." This adaptation allows the algorithms to seamlessly transition from standard TSPLIB Euclidean calculations to processing custom, non-Euclidean, and asymmetric real-world transit networks.

3. **Dynamic Parameter Abstraction:** In conventional academic codebases, hyperparameters are typically hardcoded or statically assigned. Our implementation entirely decoupled the hyperparameter definitions from the core solver logic. By abstracting variables into a dynamic `StrategySpec` payload, the algorithms were rendered fully compatible with our external Design of Experiments (DoE) module, enabling automated and mathematically unbiased parameter tuning.

---

## Roadmap & Future Work

### RL Parameter Control (Priority — 3rd Paper Candidate)

**Status:** Design phase. See `.opencode/plans/2026-05-15-docs-dashboard-roadmap-plan.md`

**Summary:** Q-Learning based dynamic parameter adaptation. The algorithm automatically adjusts mutation rate, population size, and local search budget based on stagnation, diversity, and gap status during execution.

**Architecture:**

- **State space:** 144 states (diversity × stagnation × gap × progress)
- **Action space:** 6 actions (↑mutation, ↓mutation, ↑ls, ↓ls, ↑exploration, ↓exploration)
- **Reward:** `-Δgap` (improvement = positive reward)

**Estimated time:** 2-3 weeks
**Paper potential:** High — RL-based meta-heuristic control is underexplored in TSP literature.

### LKH-3 Integration (Future Work Note)

**Status:** Low priority, kept as a note.

**Summary:** Integration of Lin-Kernighan-Helsgaun (LKH-3) heuristic as a local search operator.

**Assessment:**

- Expected ~1-2% gap improvement on n > 2000 problems
- C-based, requires wrapper
- Current SOTA algorithms already give competitive results at n ≤ 1000
- **Recommendation:** Not necessary for paper-focused work; consider for large-scale industrial applications

### GPU Acceleration (Low Priority)

**Status:** Out of priority.

**Assessment:**

- Numba CUDA (`@cuda.jit`) for fitness eval loops on GPU
- Requires NVIDIA GPU
- TSP bottleneck is local search (memory-bound), not fitness compute (compute-bound)
- **Recommendation:** Low ROI — CPU Numba JIT already provides sufficient performance

---

## Version History

| Version | Date       | Changes                                                                                                               |
| ------- | ---------- | --------------------------------------------------------------------------------------------------------------------- |
| 3.5     | 2026-06-30 | Fix _Problem.prepare_matrices() for registry GWO/HHO, clarify algorithm naming (Numba-GWO vs GWO), Numba env docs    |
| 3.4     | 2026-05-19 | Optuna dynamic queue architecture (ask/tell), early stopping, tie-based tie-breaking, parallel execution optimization |
| 3.3     | 2026-05-16 | 3 tuning strategies (Grid/Fractional/Bayesian), Optuna added to SOTA, problem size sorting                            |
| 3.2     | 2026-05-16 | RUN-TSP added (Runge Kutta Optimizer), 17 algorithms, metaphor-free solver                                            |
| 3.1     | 2026-05-16 | CGO-TSP added (Chaos Game Optimization), 16 algorithms, 45 tests                                                      |
| 3.0     | 2026-05-15 | Dual-engine architecture, 15 algorithms, CPSO variant, BSF fallback, Streamlit dashboard, RL roadmap                  |
| 2.0     | 2026-05-09 | SOTA engine consolidation, DoE tuning, ProcessPoolExecutor                                                            |
| 1.0     | 2026-04-06 | Initial benchmark system, V1/V2, multiprocessing                                                                      |

---

*This document was last updated on 2026-06-30 (v3.5).*
