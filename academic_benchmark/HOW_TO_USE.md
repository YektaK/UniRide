# UniRide Academic Benchmark — How to Use

**Date:** 2026-05-19
**Version:** 3.4
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
├──────────────────────────┬──────────────────────────────────────┤
│   master_numba_engine    │    master_sota_engine                │
│   ┌──────────────────┐   │   ┌──────────────────────────────┐   │
│   │ 2-opt            │   │   │ E2BSO-TSP                    │   │
│   │ 3-opt-bounded    │   │   │ E2BSO-TSP-CPSO               │   │
│   │ swap             │   │   │ R2DMA-TSP                    │   │
│   │ insert           │   │   │ P-AOEA-TSP                   │   │
│   │ or-opt           │   │   │ CGO-TSP                      │   │
│   │ 2.5-opt          │   │   │ RUN-TSP                      │   │
│   │ B-PSO            │   │   └──────────────────────────────┘   │
│   │ B-GA             │   │                                      │
│   │ B-ACO            │   │   AlgorithmRegistry (shared)         │
│   │ B-SA             │   │   ┌──────────────────────────────┐   │
│   │ B-TS             │   │   │ register()                   │   │
│   │ B-DE             │   │   │ register_param_space()       │   │
│   │ B-HHO            │   │   │ register_warmup()            │   │
│   │ B-GWO            │   │   │ execute()                    │   │
│   │ B-WOA            │   │   └──────────────────────────────┘   │
│   │ B-MFO            │   │                                      │
│   │ B-LS             │   │   Engine Interface                   │
│   └──────────────────┘   │   ┌──────────────────────────────┐   │
│                          │   │ solve(coordinates) -> Result │   │
│                          │   │ set_dist_matrix(matrix)      │   │
│                          │   └──────────────────────────────┘   │
└──────────────────────────┴──────────────────────────────────────┘
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

### 2. `master_numba_engine.py` — Numba Engine Standalone

**Purpose:** Run Numba-optimized algorithms directly. 11 algorithms with JIT compilation.

**Algorithms:** 2-opt, 3-opt-bounded, swap, insert, or-opt, 2.5-opt, B-PSO, B-GA, B-ACO, B-SA, B-TS, B-DE, B-HHO, B-GWO, B-WOA, B-MFO, B-LS

**Run:**
```bash
# Interactive mode
python -m academic_benchmark.master_numba_engine

# CLI mode
python -m academic_benchmark.master_numba_engine --mode tuning --problems berlin52,eil51 --runs 5
python -m academic_benchmark.master_numba_engine --mode default --problems berlin52 --algos B-PSO,B-GA --runs 3
```

**CLI Arguments:**
| Flag | Description | Example |
|------|-------------|---------|
| `--mode` | `tuning`, `default`, or `benchmark` | `--mode tuning` |
| `--problems` | Comma-separated problem names | `--problems berlin52,eil51` |
| `--algos` | Comma-separated algorithm names | `--algos B-PSO,B-GA` |
| `--runs` | Number of runs per combo | `--runs 5` |
| `--workers` | Parallel worker count | `--workers 4` |
| `--size-limit` | Max problem dimension | `--size-limit 100` |

**Menu Flow:**
```
┌─────────────────────────────────────────────┐
│       NUMBA ENGINE — Ana Menu               │
├─────────────────────────────────────────────┤
│ [1] TUNING (Grid/Fractional/Bayesian)       │
│ [2] BENCHMARK (DB/Manual/Default params)    │
│ [3] QUICK BENCHMARK (Default params only)   │
│ [D] DASHBOARD                               │
│ [Q] CIKIS                                   │
└─────────────────────────────────────────────┘
```

---

### 3. `master_sota_engine.py` — SOTA Engine Standalone

**Purpose:** Run state-of-the-art metaheuristics. 6 algorithms.

**Algorithms:** E2BSO-TSP, E2BSO-TSP-CPSO, R2DMA-TSP, P-AOEA-TSP, CGO-TSP, RUN-TSP

**Run:**
```bash
# Interactive mode
python -m academic_benchmark.master_sota_engine

# CLI mode
python -m academic_benchmark.master_sota_engine --mode tuning --problems berlin52 --algos E2BSO-TSP,R2DMA-TSP --runs 5
```

**CLI Arguments:** Same as numba engine.

**Menu Flow:**
```
┌─────────────────────────────────────────────┐
│       SOTA ENGINE — Ana Menu                │
├─────────────────────────────────────────────┤
│ [1] TUNING (Grid/Fractional/Bayesian)       │
│ [2] BENCHMARK (DB/Manual/Default params)    │
│ [3] QUICK BENCHMARK (Default params only)   │
│ [D] DASHBOARD                               │
│ [Q] CIKIS                                   │
└─────────────────────────────────────────────┘
```

---

### 4. `dashboard.py` — Streamlit Dashboard

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

### 5. `tsplib_manager.py` — TSPLIB Database Manager

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

### 6. `run_numba_with_bildiri_params.py` — Bildiri2026 Param Runner

**Purpose:** Run Numba algorithms with parameters from the bildiri2026 paper experiments.

**Run:**
```bash
python -m academic_benchmark.run_numba_with_bildiri_params --problems berlin52 --algos B-PSO,B-GA --runs 10
```

**CLI Arguments:**
| Flag | Description |
|------|-------------|
| `--problems` | Comma-separated problem names |
| `--algos` | Comma-separated algorithm names |
| `--runs` | Number of runs |
| `--workers` | Parallel workers |
| `--output` | Output CSV path |

---

### 7. `param_db.py` — Parameter Database Module

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

### 8. `benchmark_utils.py` — Shared Utilities

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

### 9. `engine_core.py` — Core Dataclasses

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

## Bildiri2026 Pipeline (Legacy but Active)

The `bildiri2026/` directory contains the original paper experiment pipeline. Run in order:

### Step 1: Generate Config
```bash
python -m academic_benchmark.bildiri2026.1_generate_config
```
Generates tuning configurations for all problem/algorithm combinations.

### Step 2: Run Tuning
```bash
python -m academic_benchmark.bildiri2026.2_run_tuning
```
Executes parameter tuning. Outputs: `bildiri2026/results/tuning/`

### Step 3: Run Benchmark
```bash
python -m academic_benchmark.bildiri2026.3_run_benchmark
```
Runs benchmarks with tuned params. Outputs: `bildiri2026/results/benchmark/`

### Step 4: Analyze (optional)
```bash
python -m academic_benchmark.bildiri2026.analyze_tuning
python -m academic_benchmark.bildiri2026.analyze_benchmark
```

### Step 5: Visualize
```bash
python -m academic_benchmark.bildiri2026.5_visualize
```
Generates plots and tables for the paper.

### Additional Tools:
| Script | Purpose |
|--------|---------|
| `orchestrate_batch.py` | Run full pipeline end-to-end |
| `run_targeted.py` | Run specific problem/algorithm combos |
| `data_manager.py` | Manage bildiri2026 result data |
| `benchmarks/tsplib_benchmark.py` | Standalone TSPLIB benchmark runner |
| `benchmarks/timematrix_benchmark.py` | Time-matrix problem benchmark |

---

## Process Flows

### Flow 1: First-Time User (Recommended Path)

```
1. smart_benchmark.py
   ├── [1] TUNING
   │   ├── Select problems (e.g., berlin52, eil51, st70)
   │   ├── Select algorithms (e.g., B-PSO, B-GA, E2BSO-TSP)
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

### Flow 3: Reproduce Paper Results

```
1. bildiri2026/orchestrate_batch.py
   └── Runs full pipeline: config → tuning → benchmark → analyze

2. Or step-by-step:
   ├── 1_generate_config.py
   ├── 2_run_tuning.py
   ├── 3_run_benchmark.py
   ├── analyze_tuning.py
   ├── analyze_benchmark.py
   └── 5_visualize.py
```

### Flow 4: Single Algorithm Deep Dive

```
1. master_numba_engine.py (or master_sota_engine.py)
   ├── [1] TUNING
   │   ├── Select one problem (e.g., berlin52)
   │   ├── Select one algorithm (e.g., B-PSO)
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

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENBLAS_NUM_THREADS` | 1 | Prevent OpenBLAS multiprocessing crashes |
| `NUMEXPR_NUM_THREADS` | 1 | Prevent NumExpr thread conflicts |
| `OMP_NUM_THREADS` | 1 | Prevent OpenMP thread conflicts |
| `MKL_NUM_THREADS` | 1 | Prevent MKL thread conflicts |

**Note:** These are set automatically at module top in both master engines. Do not override unless you know what you're doing.

### File Locations

| Path | Purpose |
|------|---------|
| `academic_benchmark/tsplib.db` | TSPLIB problem database (SQLite) |
| `academic_benchmark/benchmark_db/` | Benchmark results directory |
| `academic_benchmark/benchmark_db/benchmark_progress.csv` | All run results |
| `academic_benchmark/benchmark_db/results.csv` | Aggregated results |
| `academic_benchmark/benchmark_db/metadata.json` | Tuning metadata + best params |
| `academic_benchmark/benchmark_db/param_db.sqlite` | Parameter database |
| `academic_benchmark/benchmark_db/configs/` | Saved benchmark configurations |
| `academic_benchmark/benchmark_db/history/` | Interrupted benchmark saves |

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
| `test_sota_e2e.py` | SOTA solver end-to-end tests |
| `test_sota_parity.py` | SOTA algorithm parity tests |
| `test_numba_three_opt.py` | 3-opt-bounded correctness |
| `test_benchmark_robustness.py` | Worker backend + seed stability |
| `test_problem_selector.py` | Problem selection logic |

**Current status:** 55/55 tests passing.
