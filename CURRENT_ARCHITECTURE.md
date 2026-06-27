# CURRENT_ARCHITECTURE.md
# UniRide Dual-Engine — Current System Architecture
# Generated: 2026-06-01 | Codegraph-verified against 540 indexed files

## 1. System Overview

UniRide is a vehicle-routing platform for special-education student transportation. It solves CVRP/CVRPTW problems with a heterogeneous fleet (wheelchair-bound "Sw" and standard "So" passengers). The system has two execution surfaces that share a single algorithmic core:

- **Production API** (`optimizer_api/`) — FastAPI microservice serving the Next.js frontend
- **Academic Benchmark** (`academic_benchmark/`) — CLI + tuning pipeline for TSPLIB/CVRPLIB research

Both surfaces import the same pure-Python algorithm library (`uniride_core/`), ensuring **write-once, use-everywhere** algorithm logic.

## 2. Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTATION (Next.js 16, Port 3000)                   │
│  Admin Panel · Driver UI · Student UI · SOTA Dashboard  │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────┐
│  API LAYER                                              │
│  ┌────────────────────┐  ┌─────────────────────────┐    │
│  │ Next.js API Routes  │  │ Python FastAPI (Port    │    │
│  │ /api/optimize-route │  │ 8000) optimizer_api/    │    │
│  │ /api/admin/*        │  │  /api/v1/optimize       │    │
│  │ /api/benchmark/*    │  │  /api/v1/compare        │    │
│  └─────────┬──────────┘  │  /api/v1/benchmark/*    │    │
│            │             │  /api/v1/strategies     │    │
│            └────────────►│  /api/v1/extract-tw     │    │
│                          └────────────┬────────────┘    │
└───────────────────────────────────────┼─────────────────┘
                                        │ Python imports
                                        ▼
┌─────────────────────────────────────────────────────────┐
│  ALGORITHMIC CORE (uniride_core/)                       │
│  No HTTP, no I/O, no FastAPI — pure algorithms          │
│                                                         │
│  algorithms/                    adapters/               │
│  ├── sota_common/ (ALNS infra)  ├── matrix_builder      │
│  ├── sota_tsp/ (6 SOTA solvers) ├── demand_builder      │
│  ├── clustering_strategies/    ├── string_matrix_builder│
│  ├── split_decoder (Prins DP)   └── uniride_adapter     │
│  ├── local_search + numba       models.py               │
│  ├── ga/gwo/hho/pso engines     benchmark_runner.py     │
│  ├── ortools/vroom/pyvrp engines                        │
│  └── engine_factory · registry                          │
└─────────────────────────────────────────────────────────┘
```

**Key invariant:** `uniride_core/` never imports `optimizer_api/` or `academic_benchmark/`. It is a pure leaf library.

## 3. Algorithm Inventory

### 3.1 Pipeline A — Cluster-First, Route-Second

| Algorithm | Strategy File | Core Engine | Clustering |
|-----------|--------------|-------------|------------|
| GA | `ga_strategy.py` | `tsp_meta_engines.solve_ga_tsp` | Sweep/CW/FCM |
| PSO | `pso_strategy.py` | `tsp_meta_engines.solve_pso_tsp` | Sweep/CW/FCM |
| GWO | `gwo_strategy.py` | `tsp_meta_engines.solve_gwo_tsp` | Sweep/CW/FCM |
| HHO | `hho_strategy.py` | `tsp_meta_engines.solve_hho_tsp` | Sweep/CW/FCM |

Flow: Students → **Clustering** (Sweep/Clarke-Wright/K-Means/FCM) → Per-cluster TSP solve → Response.

### 3.2 Pipeline B — Route-First, Cluster-Second (Split)

| Algorithm | Strategy File | Core Engine | Split Decoder |
|-----------|--------------|-------------|---------------|
| GA-Split | `ga_split_strategy.py` | `ga_split_engine.solve_ga_split` | `split_decoder` (Prins DP) |
| PSO-Split | `pso_split_strategy.py` | `pso_split_engine.solve_pso_split` | `split_decoder` |
| GWO-Split | `gwo_split_strategy.py` | `gwo_split_engine.solve_gwo_split` | `split_decoder` |
| HHO-Split | `hho_split_strategy.py` | `hho_split_engine.solve_hho_split` | `split_decoder` |

Flow: Giant tour → **Split Decoder** (Prins 2004 DP, O(n²) or O(n·B) bounded) → Vehicle routes.

Strategy files are **thin wrappers**: they parse the HTTP request, build matrices/demands, call the core engine, and format the response. All algorithm logic lives in `uniride_core/algorithms/`.

### 3.3 Holistic Solvers

| Solver | Strategy File | Core Engine | Optional? |
|--------|--------------|-------------|-----------|
| OR-Tools | `ortools_cvrp.py` | `ortools_cvrp_engine.solve_ortools_cvrp` | No |
| PyVRP (HGS) | `pyvrp_strategy.py` | `pyvrp_cvrp_engine.solve_pyvrp_cvrp` | Yes (graceful fallback) |
| VROOM | `vroom_strategy.py` | `vroom_cvrp_engine.solve_vroom_cvrp` | Yes (graceful fallback) |

### 3.4 SOTA Algorithms (ALNS-based)

6 SOTA TSP solvers in `uniride_core/algorithms/sota_tsp/`:

| Algorithm | Class | DNA Components |
|-----------|-------|----------------|
| E²BSO | `E2BSO_TSP` | Entropy-balanced swarm + destroy/repair |
| R²DMA | `R2DMA_TSP` | Resonance-supported destroy-and-merge |
| P-AOEA | `PAOEA_TSP` | Production adaptive operator evolution |
| CGO | `CGO_TSP` | Chaos game optimization |
| RUN | `RUN_TSP` | Runge-Kutta optimization |
| ALNS | `ALNS_TSP` | Standard ALNS |

All share infrastructure from `sota_common/`:
- **Destroy operators**: RandomRemoval, WorstRemoval, ShawRemoval, RelatedRemoval
- **Repair operators**: GreedyInsertion, Regret2Insertion, Regret3Insertion
- **Acceptance criteria**: SimulatedAnnealing, LateAcceptanceHC, RecordToRecordTravel
- **Penalty manager**: 3-phase IPM (relax → moderate → strict)
- **Diversity controller**: Edge-based Shannon entropy
- **Multi-layer LS**: 2-opt + 3-opt + Or-opt + Cross-exchange
- **Multi-start initializer**: Nearest-neighbor + random + sweep

### 3.5 Heuristics

| Heuristic | File | Use Case |
|-----------|------|----------|
| Greedy/NN | `greedy_heuristic.py` | Fast baseline |
| 2-opt | `two_opt_strategy.py` | Local search polish |
| Permutation | `permutation_tsp.py` | Exact for n ≤ 10 |

## 4. Strategy Registry

`optimizer_api/strategies/__init__.py` maintains two parallel registries:

- **`STRATEGY_REGISTRY`** — `Dict[str, Optional[BaseRoutingStrategy]]` mapping name→singleton instance. Used by routers for dispatch.
- **`STRATEGY_FACTORIES`** — `Dict[str, Optional[Type]]` mapping name→class. Used to create fresh instances.

The `optimize` method on `BaseRoutingStrategy` is a **runtime dispatch point** — 17 implementations are registered, and the specific target is chosen by the algorithm key in the HTTP request.

## 5. Academic Benchmark Pipeline

### 5.1 Core Components

| Component | File | Role |
|-----------|------|------|
| `RunResult` | `engine_core.py` | Standardized result dataclass |
| `AlgorithmRegistry` | `engine_core.py` | Name→executor dispatch |
| `ConfigSchema` | `engine_core.py` | Validation for tuning configs |
| `registry_setup.py` | `core/registry_setup.py` | Import-time registration of all executors |
| `param_spaces.py` | `param_spaces.py` | Unified DoE/Optuna parameter spaces |
| `cli_engine.py` | `cli_engine.py` | Main CLI (1400+ lines, tuning + benchmark modes) |
| `sota_engine.py` | `sota_engine.py` | SOTA-specific benchmark orchestration |

### 5.2 bildiri2026 Pipeline (Paper Experiment)

5-stage pipeline for academic paper experiments:
1. `1_generate_config.py` — Generate DoE configs
2. `2_run_tuning.py` — Taguchi/Optuna parameter tuning
3. `3_run_benchmark.py` — Resilient batch benchmark (append-only CSV)
4. (Stage 4: analyze_benchmark.py)
5. `5_visualize.py` — Convergence plots, box plots, Taguchi effect plots

## 6. Data Layer

- **Supabase (PostgreSQL)** — User, vehicle, route, ride request tables with RLS policies
- **TSPLIB SQLite DB** — `academic_benchmark/tsplib_data/tsplib.db` — canonical TSPLIB problem store (coordinates, optima, distance matrices)
- **Parameter DB** — `benchmark_db/param_db.json` — tuned parameters per (problem, algorithm)
- **Best Solutions** — SQLite table in tsplib.db — best known solutions per (problem, algorithm)

## 7. Key Design Decisions (from Unified Master Plan, verified as executed)

| Decision | Status | Evidence |
|----------|--------|----------|
| Core-First migration (all algorithms in `uniride_core/`) | ✅ Done | Strategy files delegate to core engines |
| `faz0_interactive.py` DELETE | ✅ Done | File does not exist |
| `run_sota_benchmark.py` DELETE | ✅ Done | File does not exist |
| TSPLIB SQLite DB-first | ✅ Done | `tsplib_manager.py` + `tsplib.db` |
| Capacity is vector-first `[sw, so]` | ✅ Done | `DemandVector` in core models |
| CORS env-configured | ✅ Done | `ALLOWED_ORIGINS` in `main.py` |
| Auth guard on calculate-vehicles | ✅ Done | `requireAdmin` in route.ts |
| `total_time_window_violations` in schema | ✅ Done | `schemas.py:293` |
| `haversine.py` is re-export from core | ✅ Done | `from uniride_core.algorithms.distance import haversine_distance` |
| `compute_gap` unified via delegation | ✅ Done | `evaluation.py` delegates to `benchmark_utils.py` |
| Benchmark daemon thread + state manager | ✅ Done | `benchmark_runner.py` + `benchmark_state.py` |

## 8. Test Infrastructure

- **`uniride_core/tests/`** — 38 tests covering core algorithms, clustering, local search, split decoder, SOTA solvers, engine factory
- **`optimizer_api/tests/`** — 27 tests covering strategies, benchmark router, CVRPTW phases, clustering, split decoder, scheduling, resource profiler, SOTA compat
- **`academic_benchmark/tests/`** — 26 tests covering CVRP execution, problem storage, regression gates, promotion, SOTA parity, dashboard, data export
- **Test framework:** pytest with conftest.py fixtures