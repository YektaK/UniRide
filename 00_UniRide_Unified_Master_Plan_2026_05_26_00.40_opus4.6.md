# UniRide Ecosystem — Unified Master Plan & Execution Specification

**Date:** May 26, 2026, 00:35 (UTC+3)  
**Architect:** Antigravity (Google DeepMind - Gemini 2.5 Pro, Advanced Agentic Coding)  
**Purpose:** Single source of truth for the entire UniRide refactoring. Covers architecture, all 5 phases, and detailed execution specs for AI agents.

## Core-First Amendment (Codex Implementation Ground)

All critical solver, benchmark, matrix, decoder, algorithm, and result logic must live in `uniride_core` and its subfolders. `optimizer_api` remains a compatibility/application layer for the current UniRide web app and external callers: it should translate FastAPI/web requests into `uniride_core` problem objects, call core engines/functions, and translate core results back to existing response schemas.

`uniride_core` must never import `optimizer_api`. Any reusable code currently owned by `optimizer_api` should be moved into `uniride_core` first, with `optimizer_api` retaining thin wrappers only where needed for backward compatibility.

Capacity is vector-first from Phase 2 onward. Standard CVRP maps to a single demand/capacity dimension, while UniRide maps to multi-dimensional passenger capacity such as `[sw, so]`. CVRPTW support must preserve travel-time matrices, asymmetric costs, service times, max route duration, pickup/dropoff direction, and time-window violation metrics.

---

## Table of Contents

1. [The Core Challenge](#1-the-core-challenge)
2. [Three-Layer Solver Architecture](#2-three-layer-solver-architecture)
3. [Algorithm Inventory — Current State](#3-algorithm-inventory--current-state)
4. [Phase 1: Foundation Cleanup](#phase-1-foundation-cleanup-critical)
5. [Phase 2: Unified Engine + Core Infrastructure](#phase-2-unified-engine--core-infrastructure-high)
6. [Phase 3: CVRPLIB Integration + CVRP Benchmark Support](#phase-3-cvrplib-integration--cvrp-benchmark-support-high)
7. [Phase 4: Promotion Gate + Production Integration](#phase-4-promotion-gate--production-integration-medium)
8. [Phase 5: Data & Web Dashboard Unification](#phase-5-data--web-dashboard-unification-medium)
9. [Verification Checklists](#verification-checklists)

---

## 1. The Core Challenge

**Write an algorithm ONCE, use it EVERYWHERE:**

```
Same Algorithm Implementation
         │
         ├── Benchmark on TSPLIB (TSP/ATSP)    → Academic Paper #1
         ├── Benchmark on CVRPLIB (CVRP)        → Academic Paper #2
         ├── Benchmark on Real Data (CVRPTW)     → Academic Paper #3
         └── Deploy in UniRide Web (Production)  → Student transportation
```

Currently this is **impossible** because:
- `sota_tsp/` solvers accept `List[int]` + distance matrix → TSP only
- `optimizer_api/strategies/` accept `OptimizationRequest` → CVRP/CVRPTW only
- An algorithm must be reimplemented to cross from research to production

### Resolved User Decisions

| Question | Decision |
|:---------|:---------|
| Web benchmark page | **Keep both** — quick web benchmarks + academic DB as source of truth. **Adjustable parameters** on web. |
| Academic benchmark algorithms | **All algorithms available** — Pipeline A/B, Holistic, Heuristic, SOTA, and Numba variants |
| CVRPLIB integration | **Separate dedicated effort** (Phase 3 in this plan) — detailed execution spec included |
| Promotion automation | **Semi-automated CLI** — `python -m academic_benchmark promote` validates criteria before promoting |
| TSPLIB data location | **SQLite DB-first** — `academic_benchmark/tsplib_data/tsplib.db` is canonical |
| Travel time matrix | **Preferred over Euclidean** — fallback to EUC_2D/ATT if unavailable. Synthetic conversion (dist ÷ speed + noise) for benchmarks |
| `faz0_interactive.py` | **DELETE** — broken legacy |
| `run_sota_benchmark.py` | **DELETE** — dead code, web uses its own `benchmark_runner.py` |

---

## 2. Three-Layer Solver Architecture

```mermaid
graph TB
    subgraph "Layer 1: Problem Adapters"
        PA1["TSPAdapter<br/>TSPLIB .tsp files"]
        PA2["ATSPAdapter<br/>TSPLIB .atsp files"]
        PA3["CVRPAdapter<br/>CVRPLIB instances<br/>+ synthetic from TSPLIB"]
        PA4["CVRPTWAdapter<br/>Solomon instances<br/>+ real UniRide data"]
        PA5["TravelTimeAdapter<br/>Supabase/Google Maps"]
    end

    subgraph "Layer 2: Metaheuristic Engines"
        ME1["GA"] & ME2["PSO"] & ME3["GWO"] & ME4["HHO"]
        ME5["E²BSO"] & ME6["R²DMA"] & ME7["ALNS"]
        ME8["2-opt / 3-opt / Or-opt"]
        ME9["P-AOEA"] & ME10["CGO"] & ME11["RUN"]
    end

    subgraph "Layer 3: Solution Strategies"
        SS1["DirectTSP<br/>Engine solves single tour"]
        SS2["ClusterFirst<br/>Sweep/CW → per-cluster TSP"]
        SS3["SplitDecoder<br/>Giant tour → optimal split"]
        SS4["Holistic<br/>OR-Tools / PyVRP / VROOM"]
    end

    PA1 & PA2 -->|"distance_matrix"| SS1
    PA3 & PA4 & PA5 -->|"dm + capacity<br/>+ time_windows"| SS2 & SS3
    PA3 & PA4 & PA5 -->|"native format"| SS4
    SS1 & SS2 & SS3 -->|"uses"| ME1 & ME2 & ME3 & ME4 & ME5 & ME6 & ME7 & ME8 & ME9 & ME10 & ME11
```

**Key insight:** Every metaheuristic operates on the same primitive — **permuting a sequence of nodes and evaluating cost via a distance/time matrix**. The difference between TSP and CVRP is not in the algorithm, but in **how the permutation is decoded** (single tour vs. split into routes).

| Layer | Responsibility | Lives In |
|:------|:--------------|:---------|
| **Problem Adapter** | Converts any problem format into `distance_matrix` + `constraints` | `uniride_core/adapters/` |
| **Metaheuristic Engine** | Pure algorithm: takes `distance_matrix`, returns `permutation` + `cost` | `uniride_core/algorithms/` |
| **Solution Strategy** | Wraps engine for a problem type: TSP→direct, CVRP→cluster+TSP or TSP+split | `optimizer_api/strategies/` + `academic_benchmark/` |

---

## 3. Algorithm Inventory — Baseline State at Plan Start

### In `uniride_core/algorithms/sota_tsp/` (Pure Python)

| Algorithm | TSP | ATSP | CVRP | CVRPTW | Notes |
|:----------|:---:|:----:|:----:|:------:|:------|
| E²BSO, R²DMA, P-AOEA, CGO, RUN, ALNS | ✅ | ✅ | ❌ | ❌ | Need CVRP wrapper (Phase 2-3) |

### In `optimizer_api/strategies/` (Production Wrappers)

| Algorithm | TSP | ATSP | CVRP | CVRPTW | Notes |
|:----------|:---:|:----:|:----:|:------:|:------|
| GA/PSO/GWO/HHO (Sweep) | ❌ | ❌ | ✅ | ✅ | Cluster-first pipeline |
| GA/PSO/GWO/HHO (Split) | ❌ | ❌ | ✅ | ✅ | Route-first + Split pipeline |
| OR-Tools, PyVRP, VROOM | ❌ | ❌ | ✅ | ✅ | Holistic solvers |
| E²BSO, R²DMA | ❌ | ❌ | ✅ | ❌ | SOTA wrappers |
| 2-opt, Greedy | ❌ | ❌ | ✅ | ❌ | Heuristics |

### In `academic_benchmark/` (Via registry_setup.py)

| Algorithm | TSP | ATSP | CVRP | Notes |
|:----------|:---:|:----:|:----:|:------|
| Numba-2opt, 3opt, Or-opt, Swap, Hybrid, GA, PSO, GWO, HHO | ✅ | ✅ | ❌ | Local search + metaheuristic |
| SOTA-E2BSO, R2DMA, P-AOEA, CGO, RUN, ALNS | ✅ | ✅ | ❌ | Via SOTA executor |

**Original Gap at Plan Start:** No algorithm could be benchmarked on CVRP/CVRPTW in `academic_benchmark`.

## 3A. Algorithm Inventory — Current Status as of 2026-05-31

### In `uniride_core/algorithms/`

| Capability | TSP | ATSP | CVRP | CVRPTW | UniRide | Current Status |
|:-----------|:---:|:----:|:----:|:------:|:-------:|:---------------|
| Core matrix engines (`GreedyMatrixEngine`, TSP/local-search engines) | ✅ | ✅ | ✅ | ✅ | ✅ | Matrix-first execution path is available through `RoutingProblem` and `MatrixBenchmarkRunner`. |
| Metaheuristic TSP engines (GA, PSO, GWO, HHO, TwoOpt) | ✅ | ✅ | via split | via split | via split | Critical TSP/metaheuristic logic moved to `uniride_core`; production wrappers delegate. |
| Split engines (GA/PSO/GWO/HHO Split) | ✅ via direct delegation | ✅ via direct delegation | ✅ | ✅ | ✅ | Split strategy internals moved to `uniride_core`; wrappers remain in `optimizer_api`. For pure TSP/ATSP, split-compatible matrix engines call the corresponding direct core engine and return one tour/route rather than forcing artificial vehicle splitting. |
| Holistic CVRP adapters (OR-Tools, PyVRP, VROOM) | ✅ | ✅ | ✅ | partial | partial | Core-owned adapters and unified `solve_problem(RoutingProblem)` dispatch exist. OR-Tools and PyVRP use native adapters; VROOM uses native pyvroom when possible and deterministic sweep fallback when the Windows pyvroom matrix API rejects the buffer format. |
| SOTA TSP solvers (E²BSO, R²DMA, P-AOEA, CGO, RUN, ALNS) | ✅ | ✅ | via registry/split wrapper path | via registry/split wrapper path | via registry/split wrapper path | Academic CVRP/CVRPTW registry entries exist, but full large-dataset validation remains pending. |

### In `academic_benchmark/`

| Capability | Status | Evidence / Notes |
|:-----------|:-------|:-----------------|
| SQLite problem source of truth | ✅ Available | Unified storage handles TSP, ATSP, CVRP, CVRPTW, and UniRide problem shapes. |
| CVRPLIB/Solomon facade | ✅ Available | `academic_benchmark.cvrplib_manager` delegates to `tsplib_manager.store_academic_text()` / `store_routing_problem()`. |
| Smoke dataset coverage | ✅ Available locally | Real DB seeded with `smoke-tsp`, `smoke-atsp`, `smoke-cvrp`, `smoke-solomon`, and `smoke-uniride`. |
| Matrix-native smoke benchmark | ✅ Passed locally | Run id `academic-matrix-smoke-20260531`: 5 persisted results, 0 errors. |
| Full academic/core test gate | ✅ Passed | `python -m pytest academic_benchmark/tests uniride_core/tests -q` passes with 310 tests. |
| Promoted config generation | ✅ Available | Promotion manager generated 26 configs from existing `best_solutions`; generated JSON is local/ignored. |
| Web/API sanity path | ⏳ Next | Verify matrix-native web execution with editable params and academic read endpoints. |
| Full CVRPLIB/Solomon dataset scale | ✅ Starter real dataset available | Raw public CVRPLIB/Solomon files are tracked under `academic_benchmark/datasets/raw/`; the local SQLite DB was seeded from those files and a first real matrix benchmark slice ran successfully. Broader validation still remains before promotion. |

---

## Phase 1: Foundation Cleanup (CRITICAL) — Status: DONE

> **Risk:** 🟢 Zero to Low — No behavioral changes to production.  
> **Goal:** Delete dead code, fix security, fix reverse dependencies.

### Files to Study First

| File | Why |
|:-----|:----|
| [tsplib_parser.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/algorithms/tsplib_parser.py) | Contains hardcoded reverse dependency to `optimizer_api` |
| [test_direct.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/test_direct.py) | Contains hardcoded Azure API key |
| [param_spaces.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/param_spaces.py) | Missing ALNS-TSP entry |
| [benchmark_utils.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/benchmark_utils.py) | TSPLIB_OPTIMALS (129 entries) to merge into core |

### Task 1.1: Delete Dead Files — DONE

| File | Action | Reason |
|:-----|:-------|:-------|
| `optimizer_api/faz0_interactive.py` | **DELETE** | 3,142 lines, broken imports (`TSPLIBProblemInfo`), superseded by `cli_engine.py` |
| `optimizer_api/run_sota_benchmark.py` | **DELETE** | Broken import: `from academic_benchmark.run_sota_benchmark import main`. Web uses `benchmark_runner.py`. |

### Task 1.2: Fix Hardcoded API Key — DONE

**File:** `test_direct.py`  
**Change:** Replace hardcoded Azure API key with `os.environ.get("AZURE_OPENAI_API_KEY")`  
**User action:** Rotate key in Azure portal.

### Task 1.3: Fix Reverse Dependency — DONE

**File:** `uniride_core/algorithms/tsplib_parser.py` (line 35-36)  
**Change:** Replace `../../optimizer_api/tests/tsplib_data` with env var fallback:
```python
TSPLIB_DATA_DIR = os.environ.get(
    "TSPLIB_DATA_DIR",
    os.path.join(os.path.dirname(__file__), '..', '..', 'tsplib_data')
)
```
**Purpose:** Core must never import from `optimizer_api`.

### Task 1.4: Add Missing ALNS-TSP Parameter Space — DONE

**File:** `academic_benchmark/param_spaces.py`  
**Change:** Add entry:
```python
"ALNS-TSP": {
    "population_size":  {"type": "int",   "doe": [24, 36, 48],   "optuna": (20, 60)},
    "max_iterations":   {"type": "int",   "doe": [200, 320, 450],"optuna": (150, 500)},
    "remove_ratio":     {"type": "float", "doe": [0.10, 0.15, 0.20], "optuna": (0.05, 0.25)},
    "time_limit":       {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
}
```

### Task 1.5: Merge TSPLIB_OPTIMALS Into Core — DONE

**Files:** `uniride_core/algorithms/tsplib_parser.py` (47 entries) ← `academic_benchmark/benchmark_utils.py` (129 entries)  
**Change:** Merge the comprehensive 129-entry dict into core. Update `benchmark_utils.py` to import from core:
```python
from uniride_core.algorithms.tsplib_parser import TSPLIB_OPTIMALS
```

### Task 1.6: Fix Signal Handler Conflicts — DONE

**Files:** `academic_benchmark/smart_benchmark.py` (line 136), `academic_benchmark/cli_engine.py` (line 263)  
**Change:** Use a guard to chain signal handlers instead of overwriting.

### Phase 1 Verification

```bash
cd optimizer_api && python -c "from main import app; print('API OK')"
python -c "from academic_benchmark.param_spaces import SOTA_PARAM_SPACES; assert 'ALNS-TSP' in SOTA_PARAM_SPACES; print('ALNS OK')"
grep -r "optimizer_api" uniride_core/  # Should return 0 results
python -c "from uniride_core.algorithms.tsplib_parser import TSPLIB_OPTIMALS; assert len(TSPLIB_OPTIMALS) >= 129; print(f'OK: {len(TSPLIB_OPTIMALS)} entries')"
```

---

## Phase 2: Unified Engine + Core Infrastructure (HIGH) — Status: DONE

> **Risk:** 🟡 Medium — New abstractions, but backward compatible.  
> **Goal:** Create `UnifiedEngine`, `MatrixBuilder`, `SplitDecoder`, and `CVRPResult` in `uniride_core`.  
> **Dependencies:** Phase 1 complete.

### Files to Study First

| File | Why |
|:-----|:----|
| [base_solver.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/algorithms/sota_tsp/base_solver.py) | Current `BaseTSPSolver` ABC — new `UnifiedEngine` must coexist |
| [models.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/uniride_core/models.py) | `ProblemInstance`, `TSPResult` — extend with CVRP fields |
| [hybrid_base_strategy.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/optimizer_api/strategies/hybrid_base_strategy.py) | Contains Split logic to extract into core |

### Task 2.1: Extend `ProblemInstance` and Create `CVRPResult` — DONE

**File:** `uniride_core/models.py` (MODIFY — add ~30 lines)

Add to `ProblemInstance`:
```python
demands: Optional[List[int]] = None              # demand per node, index 0 = depot (0)
service_times: Optional[List[int]] = None        # service time per node (CVRPTW)
num_vehicles_bks: Optional[int] = None           # BKS vehicle count
```

New dataclass:
```python
@dataclass
class CVRPResult:
    """Output from a CVRP/CVRPTW optimization algorithm."""
    algorithm: str
    routes: List[List[int]]              # List of routes, each is list of node indices
    total_cost: float
    num_vehicles: int
    time_ms: float = 0.0
    optimal_gap: Optional[float] = None
    capacity_violations: int = 0
    tw_violations: int = 0
    convergence_curve: Optional[List[float]] = None
    iterations: int = 0
    seed: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    route_costs: Optional[List[float]] = None
    route_loads: Optional[List[int]] = None
```

### Task 2.2: Create `MatrixBuilder` Adapter — DONE

**File:** `uniride_core/adapters/__init__.py` (NEW — empty)  
**File:** `uniride_core/adapters/matrix_builder.py` (NEW — ~120 lines)

```python
class MatrixBuilder:
    @staticmethod
    def from_coordinates(coords, edge_weight_type="EUC_2D") -> np.ndarray:
        """Build distance matrix using tsplib_distance_by_type. Returns int32."""

    @staticmethod
    def from_explicit_matrix(matrix: List[List[float]]) -> np.ndarray:
        """Convert explicit matrix to numpy. Returns float64."""

    @staticmethod
    def from_travel_times(time_matrix: List[List[float]]) -> np.ndarray:
        """Convert travel time matrix. Returns float64."""

    @staticmethod
    def tsplib_to_travel_time(coords, speed_kmh=40.0, noise_pct=0.10, seed=42) -> np.ndarray:
        """Convert TSPLIB coords to synthetic travel times.
        travel_time_min = (euclidean_dist / speed_kmh) * 60 + noise
        Returns float64."""
```

**MUST use** `uniride_core.algorithms.tsplib_parser.tsplib_distance_by_type` for distance calculation.

### Task 2.3: Create Split Decoder — DONE

**File:** `uniride_core/algorithms/split_decoder.py` (NEW — ~200 lines)

Pure math module — **NO web/API dependencies**.

```python
def optimal_split(permutation, distance_matrix, demands, capacity, depot=0) -> List[List[int]]:
    """Bellman-style DP split: giant tour → feasible CVRP routes. O(n²)."""

def split_with_time_windows(permutation, dm, demands, capacity, time_windows, service_times, depot=0) -> List[List[int]]:
    """Split with time window feasibility checks."""

def calculate_route_cost(route, distance_matrix, depot=0) -> float:
    """Cost of depot → c1 → c2 → ... → depot."""

def calculate_total_cost(routes, distance_matrix, depot=0) -> float:
    """Sum of all route costs."""

def validate_cvrp_solution(routes, demands, capacity, num_customers) -> Tuple[bool, List[str]]:
    """Check: all customers visited once, no route exceeds capacity."""

def validate_cvrptw_solution(routes, dm, demands, capacity, time_windows, service_times, depot=0) -> Tuple[bool, List[str]]:
    """Check CVRP + time window adherence."""
```

**Implementation hint:** Extract the Split logic from `optimizer_api/strategies/ga_split_strategy.py` and/or `hybrid_base_strategy.py`.

### Task 2.4: Create `UnifiedEngine` ABC — DONE

**File:** `uniride_core/algorithms/base_engine.py` (NEW — ~60 lines)

```python
class UnifiedEngine(ABC):
    @abstractmethod
    def optimize_permutation(self, distance_matrix, config, seed) -> PermutationResult:
        """Return best permutation and its cost."""

    def solve_tsp(self, dm, config, seed) -> TSPResult:
        """Direct TSP: permutation = tour."""

    def solve_cvrp(self, dm, config, seed, demands, capacity, depot=0, split_method="optimal_split") -> CVRPResult:
        """CVRP: permutation → optimal_split → routes."""

    def solve_cvrptw(self, dm, config, seed, demands, capacity, depot, time_windows, service_times) -> CVRPTWResult:
        """CVRPTW: permutation → split with time window checks."""
```

**Backward compatibility:** Existing `BaseTSPSolver` stays. Solvers can inherit both:
```python
class E2BSO_TSP(BaseTSPSolver, UnifiedEngine):
    def optimize_permutation(self, dm, config, seed):
        # Same algorithm code as _solve()
    def _solve(self):
        # Legacy interface → delegates to optimize_permutation()
```

### Phase 2 Verification

```bash
python -c "
from uniride_core.models import ProblemInstance, CVRPResult
from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.algorithms.split_decoder import optimal_split, validate_cvrp_solution
import numpy as np

# Test MatrixBuilder
coords = [(0,0), (3,4), (6,8)]
dm = MatrixBuilder.from_coordinates(coords, 'EUC_2D')
assert dm.shape == (3, 3) and dm[0,1] == 5

# Test SplitDecoder
dm6 = np.array([[0,10,20,30,40,50],[10,0,15,25,35,45],[20,15,0,10,20,30],
                [30,25,10,0,10,20],[40,35,20,10,0,10],[50,45,30,20,10,0]], dtype=np.float64)
routes = optimal_split([1,2,3,4,5], dm6, [0,3,4,3,4,3], capacity=8, depot=0)
ok, errs = validate_cvrp_solution(routes, [0,3,4,3,4,3], 8, 5)
assert ok, errs
print(f'Phase 2 OK: dm={dm.shape}, routes={len(routes)}')
"
```

---

## Phase 3: CVRPLIB Integration + CVRP Benchmark Support (HIGH) — Status: PARTIAL

> **Risk:** 🟡 Medium — New external dependency (`vrplib`), new DB, new executors.  
> **Goal:** Download CVRPLIB/Solomon instances, store in SQLite, register CVRP executors, extend dashboard.  
> **Dependencies:** Phase 2 complete (needs `CVRPResult`, `MatrixBuilder`, `split_decoder`).

### Files to Study First

| File | Why |
|:-----|:----|
| [tsplib_manager.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/tsplib_manager.py) | **Primary pattern reference** — `cvrplib_manager.py` must mirror this |
| [engine_core.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/engine_core.py) | `AlgorithmRegistry`, `RunResult` — executor signature |
| [registry_setup.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/core/registry_setup.py) | Pattern for CVRP executor registration |
| [param_spaces.py](file:///c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/param_spaces.py) | Pattern for param space addition |

### Task 3.1: Install / Verify Optional Importer Dependencies — DONE / ENVIRONMENT VERIFIED

`vrplib`, `ortools`, `pyvrp`, and the `pyvroom` package's `vroom` module are
importable in the current environment. The academic importer and holistic
adapter code should still keep graceful optional-dependency handling so the
application can start when one of these packages is missing on another machine.

### Task 3.2: Create CVRPLIB Manager — PARTIAL / INTEGRATED

**File:** `academic_benchmark/cvrplib_manager.py` (NEW — ~450 lines)

Implemented as a facade over the unified academic SQLite schema, not as a
second CVRP-only database. It exposes file/text import helpers, CVRP/CVRPTW
listing, legacy `ProblemInstance` conversion, and a small CLI:
`python -m academic_benchmark.cvrplib_manager <import|list|status>`.

**Directory layout:**
```
academic_benchmark/cvrplib_data/
├── cvrplib.db              ← SQLite DB
├── instances/              ← Downloaded .vrp / .sol files
└── solomon/                ← Solomon VRPTW instances
```

**SQLite Schema (6 tables):**

```sql
CREATE TABLE IF NOT EXISTS cvrp_problems (
    name TEXT PRIMARY KEY,
    dimension INTEGER NOT NULL,
    num_customers INTEGER NOT NULL,       -- dimension - 1
    capacity INTEGER NOT NULL,
    best_known REAL,                      -- BKS cost
    num_vehicles_bks INTEGER,
    problem_type TEXT NOT NULL DEFAULT 'CVRP',  -- 'CVRP' or 'CVRPTW'
    dataset TEXT NOT NULL,                -- 'augerat_A', 'cmt', 'solomon_R1', etc.
    category TEXT NOT NULL,               -- 'small' (≤50), 'medium' (≤200), 'large' (>200)
    edge_weight_type TEXT NOT NULL DEFAULT 'EUC_2D',
    source TEXT DEFAULT 'cvrplib',
    extracted_at TEXT, comment TEXT
);

CREATE TABLE IF NOT EXISTS cvrp_coordinates (
    problem_name TEXT NOT NULL, node_idx INTEGER NOT NULL,
    x REAL NOT NULL, y REAL NOT NULL,
    PRIMARY KEY (problem_name, node_idx),
    FOREIGN KEY (problem_name) REFERENCES cvrp_problems(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cvrp_demands (
    problem_name TEXT NOT NULL, node_idx INTEGER NOT NULL, demand INTEGER NOT NULL,
    PRIMARY KEY (problem_name, node_idx),
    FOREIGN KEY (problem_name) REFERENCES cvrp_problems(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cvrp_time_windows (
    problem_name TEXT NOT NULL, node_idx INTEGER NOT NULL,
    ready_time INTEGER NOT NULL, due_date INTEGER NOT NULL,
    service_time INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (problem_name, node_idx),
    FOREIGN KEY (problem_name) REFERENCES cvrp_problems(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cvrp_distance_matrices (
    problem_name TEXT PRIMARY KEY, matrix_blob BLOB NOT NULL,
    dtype TEXT NOT NULL DEFAULT 'int32', shape_n INTEGER NOT NULL,
    edge_weight_type TEXT NOT NULL, computed_at TEXT NOT NULL,
    FOREIGN KEY (problem_name) REFERENCES cvrp_problems(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cvrp_best_solutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_name TEXT NOT NULL, algorithm TEXT NOT NULL,
    params_json TEXT NOT NULL, routes_json TEXT NOT NULL,
    total_cost REAL, num_vehicles INTEGER, gap REAL, timestamp TEXT NOT NULL,
    FOREIGN KEY (problem_name) REFERENCES cvrp_problems(name) ON DELETE CASCADE
);
```

**Required Functions:**

| Function | Description |
|:---------|:-----------|
| `import_cvrplib_text()` / `import_cvrplib_file()` | Parse and store CVRPLIB CVRP instances through unified academic storage |
| `import_solomon_text()` / `import_solomon_file()` | Parse and store Solomon CVRPTW instances through unified academic storage |
| `import_cvrp_paths(paths)` | Import supported `.vrp`, `.txt`, and `.solomon` files from files/directories |
| `load_cvrp_problem(name)` | Load a CVRP/CVRPTW problem as a core `RoutingProblem` |
| `get_cvrp_problems(db_path, max_dim, as_legacy)` | Return stored CVRP/CVRPTW rows, optionally as legacy `ProblemInstance` objects |
| `get_cvrp_problem_as_instance(problem_name, db_path)` | Return one CVRP/CVRPTW problem as legacy `ProblemInstance` |
| `summarize_cvrp_store()` | Print/count stored CVRP/CVRPTW problems |

**CLI entry point:** `python -m academic_benchmark.cvrplib_manager <import|list|status>`

**BKS Dictionary:** Include `CVRP_BKS` dict with known optimal values for Augerat A/B, CMT, and Solomon instances. Fetch complete values from CVRPLIB website or from `.sol` files.

### Task 3.3: Register CVRP Executors — DONE / INTEGRATED

**Files:** `academic_benchmark/core/registry_setup.py`, `academic_benchmark/tests/test_academic_cvrp_execution.py`

Registers `CVRP-{algo}` and `CVRPTW-{algo}` executors through the unified academic registry. Each executor:

1. Receives `ProblemInstance` with CVRP fields
2. Builds distance matrix via `MatrixBuilder`
3. Calls a matrix-native `UnifiedEngine.solve_problem()` path or a holistic core adapter
4. Runs core split/decoder behavior through the unified engine where applicable
5. Returns `RunResult` with CVRP/CVRPTW metrics

**Registers:** core greedy, core TSP meta engines, Numba compatibility aliases, split compatibility aliases, and holistic `OR-Tools`, `PyVRP`, and `VROOM` aliases for both CVRP and CVRPTW.

**Integration:** Implemented directly in `registry_setup.py` to avoid a second academic registry source.

### Task 3.4: Add CVRP Parameter Spaces — DONE

**File:** `academic_benchmark/param_spaces.py` (MODIFY — add ~40 lines)

```python
CVRP_PARAM_SPACES = {
    "CVRP-E2BSO-TSP": {
        **SOTA_PARAM_SPACES.get("E2BSO-TSP", {}),
        "split_method": {"type": "categorical", "doe": ["optimal_split"], "optuna": ["optimal_split"]},
    },
    # ... repeat for all CVRP algorithms
}
SOTA_PARAM_SPACES.update(CVRP_PARAM_SPACES)
```

### Task 3.5: Create Synthetic CVRP/CVRPTW Generator — DONE

**File:** `academic_benchmark/synthetic_cvrp_generator.py` (NEW — ~150 lines)

```python
def generate_cvrp_from_tsplib(problem_name, capacity=None, demand_range=(1,10), seed=42):
    """Create CVRP from TSPLIB TSP: add random demands + capacity."""

def generate_cvrptw_from_tsplib(problem_name, capacity=None, speed_kmh=40.0, time_window_width=60, seed=42):
    """Create CVRPTW: add travel time matrix + random time windows."""

def batch_generate_cvrp(problem_names=None, max_dim=500, seed=42):
    """Generate CVRP instances for all eligible TSPLIB problems."""
```

### Task 3.6: Extend Dashboard for CVRP Metrics — DONE

**Files:** `academic_benchmark/dashboard.py`, `academic_benchmark/dashboard_utils.py`

Implemented first-class SQLite-backed routing metric reporting:
- dashboard now appends canonical `benchmark_results` rows from SQLite to the progress data frame,
- dashboard metric selection includes `objective_cost`, `tour_cost`, `num_vehicles`, `capacity_violations`, and `tw_violations`,
- dashboard labels now refer to routing problems instead of TSP-only problems,
- `dashboard_utils.py` normalizes DB rows into the existing dashboard progress schema so CSV workflows remain compatible.

Remaining polish for this task, if needed later: add a dedicated CVRP/CVRPTW tab with dataset-family grouping and BKS vehicle comparisons after the full CVRPLIB/Solomon importer is finalized.

### Phase 3 Verification

```bash
# 1. vrplib installed
python -c "import vrplib; print(f'vrplib {vrplib.__version__} OK')"

# 2. CVRPLIB manager works
python academic_benchmark/cvrplib_manager.py download --datasets A,B
python academic_benchmark/cvrplib_manager.py extract
python academic_benchmark/cvrplib_manager.py compute-dm
python academic_benchmark/cvrplib_manager.py status
python -c "
from academic_benchmark.cvrplib_manager import get_cvrp_problems
problems = get_cvrp_problems()
assert len(problems) >= 40
print(f'OK: {len(problems)} CVRP problems')
"

# 3. CVRP executors registered
python -c "
from academic_benchmark.engine_core import AlgorithmRegistry
import academic_benchmark.core.registry_setup
import academic_benchmark.core.cvrp_registry_setup
cvrp = [a for a in AlgorithmRegistry.list_algorithms() if a.startswith('CVRP-')]
assert len(cvrp) >= 6
print(f'CVRP algorithms: {cvrp}')
"

# 4. End-to-end test
python -c "
from academic_benchmark.engine_core import AlgorithmRegistry
import academic_benchmark.core.registry_setup
import academic_benchmark.core.cvrp_registry_setup
from academic_benchmark.cvrplib_manager import get_cvrp_problem_as_instance
problem = get_cvrp_problem_as_instance('A-n32-k5')
executor = AlgorithmRegistry.get_executor('CVRP-E2BSO-TSP')
result = executor(problem, {'population_size': 20, 'max_iterations': 50}, seed=42, run_idx=1)
print(f'E2E OK: {result.algorithm} cost={result.tour_cost} gap={result.gap_pct}%')
"
```

---

## Phase 4: Promotion Gate + Production Integration (MEDIUM) — Status: PARTIAL

> **Risk:** 🟡 Medium — Changes production algorithm loading.  
> **Goal:** Formalize the research → production pipeline. Promoted algorithms get locked params.  
> **Dependencies:** Phase 2 complete.

### Task 4.1: Create `promoted_configs.json` — DONE

**File:** `academic_benchmark/promoted_configs.py` (NEW)

```json
{
  "schema_version": 1,
  "source": "academic_db",
  "generated_at": "2026-05-31T12:00:00",
  "selection_rule": "best finite gap, then best finite objective/tour cost per algorithm/problem_type/matrix_kind",
  "configs": [
    {
      "algorithm": "Numba-Or-opt",
      "problem_type": "atsp",
      "matrix_kind": "travel_time",
      "params": {"max_passes": 2},
      "score": 20.0,
      "gap": null,
      "source_table": "benchmark_results",
      "selected_from": {"problem": "tiny-atsp", "run_id": "run-1"}
    }
  ]
}
```

Implemented as a generator/reader instead of committing a stale static JSON snapshot:
- `build_promoted_configs()` reads canonical SQLite rows from `best_solutions` and `benchmark_results`,
- `write_promoted_configs()` emits `academic_benchmark/benchmark_db/promoted_configs.json`,
- `resolve_promoted_params()` gives core/API callers a neutral parameter lookup by algorithm, problem type, and matrix kind,
- no `optimizer_api` ownership or imports are introduced.

### Task 4.2: Create Promotion Manager — DONE

**File:** `academic_benchmark/promotion_manager.py` (NEW)

```python
# CLI:
# python -m academic_benchmark.promotion_manager --dry-run
# python -m academic_benchmark.promotion_manager --output academic_benchmark/benchmark_db/promoted_configs.json
```

Implemented promotion workflow:
- builds promoted configs from academic SQLite rows,
- validates minimum config count and parameter presence,
- supports `--dry-run`, `--allow-empty-params`, `--db-path`, `--output`, and `--limit`,
- exits non-zero with a validation message instead of writing empty promotion files.

### Task 4.3: Update Strategy Registry — DONE

**Files:** `optimizer_api/strategies/__init__.py`, production wrappers, `promoted_config_loader.py`

- DONE: add `STRATEGY_FACTORIES` for every compatibility registry key.
- DONE: make `get_strategy()` return fresh strategy instances instead of reusing mutable singleton objects.
- DONE: keep backward-compatible `STRATEGY_REGISTRY` for read-only lookups and optional dependency availability checks.
- DONE: load promoted configs into SOTA strategy construction through fresh factories and request-local config merge.
- DONE: non-SOTA wrappers consume promoted configs automatically as default-only constructor values; explicit constructor config and request-level configs still win.
- DONE: academic parameter names (`pop_size`, `generations`, `pack_size`, `hawks`, etc.) are normalized to production wrapper keys.

### Task 4.4: Simplify SOTA Wrappers — PARTIAL / PROMOTION COMPLETE

**Files:** `ebso_strategy.py`, `rdma_strategy.py`, `aoea_strategy.py`, `sota_config_utils.py`, non-SOTA strategy wrappers (MODIFY/NEW)

- DONE: add request-level `sota_config` to `OptimizationRequest`.
- DONE: add dataclass-safe SOTA config merge helper that ignores unknown keys and preserves typed tuple fields.
- DONE: make E²BSO, R²DMA, and P-AOEA wrappers use request-local effective configs instead of mutating constructor configs.
- DONE: load optional promoted config JSON via `UNIRIDE_PROMOTED_CONFIG_PATH` / default academic benchmark path.
- DONE: GA/PSO/GWO/HHO, TwoOpt, and GA/PSO/GWO/HHO-Split wrappers load promoted defaults when no explicit constructor config is supplied.
- REMAINING: optionally route these wrappers through `UnifiedEngine` once promoted config injection and native routing variants are fully wired.

### Task 4.5: Update Web Algorithm Constants — DONE

**Files:** `src/lib/algorithm-constants.ts`, `src/services/optimizer-service.ts`, `optimizer_api/benchmark_runner.py`

- DONE: add Research-Promoted (SOTA) category to frontend algorithm constants.
- DONE: add SOTA keys, aliases, display names, descriptions, and complexity entries for E²BSO, R²DMA, and P-AOEA.
- DONE: keep alias normalization for `entropy_bso`, `e2b`, `rdma`, and `aoea`.
- DONE: forward quick-benchmark params for SOTA algorithms into `request.sota_config`.
- REMAINING: optionally render promoted-config evidence/status in the UI once academic read endpoints expose promotion metadata.

### Task 4.6: Web Benchmark Adjustable Parameters — DONE

**Files:** `src/app/(app)/admin/benchmark/page.tsx`, `optimizer_api/routers/benchmark.py`

- DONE: benchmark page already renders editable controls from `/api/benchmark/param-spaces`.
- DONE: backend now exposes web-facing SOTA aliases (`e2bso`, `r2dma`, `paoea`) mapped to academic SOTA parameter spaces.
- DONE: selected SOTA algorithm params now flow from web quick benchmark into backend `request.sota_config`.
- REMAINING: optional UI polish to display promoted-config evidence/status beside each SOTA algorithm.

---

## Phase 5: Data & Web Dashboard Unification (MEDIUM) — Status: PARTIAL

> **Risk:** 🟢 Low — Read-only integration, no changes to write paths.  
> **Goal:** Web app reads from academic SQLite DB. Both quick benchmarks and academic results visible.  
> **Dependencies:** Phases 2-3 complete.

### Task 5.1: New API Endpoints for Academic Results — DONE

**Files:** `optimizer_api/routers/benchmark.py`, `academic_benchmark/results_reader.py`

```python
@router.get("/academic/leaderboard")        # Algorithm comparison
@router.get("/academic/best")               # Best result lookup
@router.get("/academic/benchmark-results")  # Raw/summary result rows
@router.get("/academic/problems")           # TSPLIB/CVRPLIB/Solomon problem inventory
```

The academic problems endpoint reports SQLite source-of-truth metadata: problem type,
matrix kind, dimension, category, coordinate/matrix availability, routing constraint
availability, vehicle count, direction, depot index, and max route duration.

### Task 5.2: Web Benchmark Reads Academic DB — DONE

**Files:** Admin benchmark page and Next proxy routes read from both:
- In-memory `benchmark_state.py` for live runs
- SQLite DB for historical academic results

Implemented web-side academic problem inventory:
- `src/app/api/benchmark/academic/problems/route.ts` proxies the SQLite source-of-truth problem endpoint.
- `src/services/benchmark-service.ts` exposes typed `fetchAcademicProblems()` metadata for TSP, ATSP, CVRP, and CVRPTW.
- `src/app/(app)/admin/benchmark/page.tsx` merges live quick-run TSPLIB inventory with academic DB inventory, preserving academic routing metadata.
- `src/services/benchmark-service.test.ts` verifies the academic problem API contract and metadata mapping.

### Task 5.3: Real Data Export Tool — DONE

**Files:** `academic_benchmark/data_export.py`, `academic_benchmark/tests/test_data_export.py`

Export anonymized UniRide production data from Supabase for CVRPTW benchmarking.

Implemented:
- Pure `build_uniride_export_problem()` builder that converts UniRide-style depot, students, SW/SO demand, pickup/dropoff time windows, and travel-time matrices into core `RoutingProblem`.
- Anonymized matrix labels (`depot`, `student_001`, ...) and metadata that avoids original student IDs/names.
- `store_uniride_export()` storage through the unified academic SQLite problem schema.
- CLI paths for `--input-json` and optional `--from-supabase` export using `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.

### Task 5.4: Thread-Safety Fix — DONE

**File:** `optimizer_api/strategies/__init__.py` (already in Phase 4)

Implemented:

- `STRATEGY_FACTORIES` returns fresh strategy instances from `get_strategy()`,
  avoiding shared mutable strategy objects on active request paths.
- `optimizer_api.utils.patterns.SingletonMeta` provides thread-safe
  double-checked singleton construction for app-owned shared utilities.
- `optimizer_api.utils.data_loader.DataLoader` uses `SingletonMeta` plus an
  `RLock` around matrix cache access and refresh.
- Focused verification: `python -m pytest optimizer_api\tests\test_strategy_registry_minor1.py academic_benchmark\tests\test_cvrplib_manager.py academic_benchmark\tests\test_seed_smoke_datasets.py -q` passes with 9 tests.

### Task 5.5: Scheduling Logic Extraction — DONE

**Files:** `optimizer_api/utils/scheduling.py`, `optimizer_api/tests/test_scheduling_utils.py`  
Extract `_calculate_scheduled_times()` + `_minutes_to_time()` from `optimization.py`.

Implemented:
- `calculate_scheduled_times()` utility for pickup backward scheduling and dropoff forward scheduling.
- `minutes_to_time()` clamped HH:MM conversion.
- `optimization.py` imports the utility instead of owning scheduling internals.
- Tests cover pickup, dropoff, and day-bound clamping behavior.

---

## File Summary — All Phases

| Phase | File | Action | ~Lines |
|:------|:-----|:-------|:-------|
| 1 | `optimizer_api/faz0_interactive.py` | DELETE | -3142 |
| 1 | `optimizer_api/run_sota_benchmark.py` | DELETE | -3 |
| 1 | `test_direct.py` | MODIFY | ~5 |
| 1 | `uniride_core/algorithms/tsplib_parser.py` | MODIFY | ~10 |
| 1 | `academic_benchmark/param_spaces.py` | MODIFY | +6 |
| 1 | `academic_benchmark/benchmark_utils.py` | MODIFY | ~3 |
| 1 | `academic_benchmark/smart_benchmark.py` | MODIFY | ~5 |
| 1 | `academic_benchmark/cli_engine.py` | MODIFY | ~5 |
| 2 | `uniride_core/models.py` | MODIFY | +30 |
| 2 | `uniride_core/adapters/__init__.py` | NEW | 1 |
| 2 | `uniride_core/adapters/matrix_builder.py` | NEW | ~120 |
| 2 | `uniride_core/algorithms/split_decoder.py` | NEW | ~200 |
| 2 | `uniride_core/algorithms/base_engine.py` | NEW | ~60 |
| 3 | `academic_benchmark/cvrplib_manager.py` | NEW | ~450 |
| 3 | `academic_benchmark/core/cvrp_registry_setup.py` | NEW | ~200 |
| 3 | `academic_benchmark/param_spaces.py` | MODIFY | +40 |
| 3 | `academic_benchmark/synthetic_cvrp_generator.py` | NEW | ~150 |
| 3 | `academic_benchmark/dashboard.py` | MODIFY | +100 |
| 4 | `promoted_configs.json` | NEW | ~50 |
| 4 | `academic_benchmark/promotion_manager.py` | NEW | ~150 |
| 4 | `optimizer_api/strategies/__init__.py` | MODIFY | ~50 |
| 4 | `optimizer_api/strategies/ebso_strategy.py` | MODIFY | -100 |
| 4 | `src/lib/algorithm-constants.ts` | MODIFY | +30 |
| 4 | `src/app/(app)/admin/benchmark/page.tsx` | MODIFY | +50 |
| 5 | `optimizer_api/routers/benchmark.py` | MODIFY | +60 |
| 5 | `src/app/api/benchmark/academic/problems/route.ts` | NEW | ~40 |
| 5 | `src/services/benchmark-service.ts` | MODIFY | +70 |
| 5 | `src/services/benchmark-service.test.ts` | NEW | ~50 |
| 5 | `academic_benchmark/data_export.py` | NEW | ~350 |
| 5 | `academic_benchmark/tests/test_data_export.py` | NEW | ~80 |
| 5 | `optimizer_api/utils/scheduling.py` | NEW | ~50 |

---

## Execution Order & Dependencies

```mermaid
graph TD
    P1["Phase 1<br/>Foundation Cleanup<br/>(CRITICAL)"]
    P2["Phase 2<br/>Unified Engine +<br/>Core Infrastructure<br/>(HIGH)"]
    P3["Phase 3<br/>CVRPLIB Integration +<br/>CVRP Benchmarks<br/>(HIGH)"]
    P4["Phase 4<br/>Promotion Gate +<br/>Production<br/>(MEDIUM)"]
    P5["Phase 5<br/>Web Dashboard<br/>Unification<br/>(MEDIUM)"]

    P1 --> P2
    P2 --> P3
    P2 --> P4
    P3 --> P5
    P4 --> P5

    style P1 fill:#e53935,color:#fff
    style P2 fill:#fb8c00,color:#fff
    style P3 fill:#fb8c00,color:#fff
    style P4 fill:#43a047,color:#fff
    style P5 fill:#43a047,color:#fff
```

> [!IMPORTANT]
> **For AI agents executing this plan:** Each phase has its own Verification section. Run ALL verification commands after completing a phase before moving to the next. If any check fails, fix before proceeding.

---

## Implemented Since Plan (2026-05-26)

Verified changes completed after initial plan authoring. Tests exist for each item.

### Infrastructure

- **SQLite benchmark source-of-truth** — `benchmark_runs` / `benchmark_results` tables added as canonical DB-backed store for benchmark data.
- **SQLite run updates fixed** — `save_benchmark_run()` updates existing run rows in place, so marking a run `completed` no longer deletes child `benchmark_results` through SQLite `REPLACE` cascade behavior.
- **Matrix-native benchmark runner path** — Benchmark runner accepts pre-built distance/duration matrices, avoiding redundant computation.
- **Matrix-native SQLite smoke coverage** — TSP, ATSP, CVRP, CVRPTW, and UniRide matrix-native benchmark results are persisted and queried through the canonical SQLite result tables.

### Algorithm Migration to `uniride_core`

| Module | Status | Details |
|:-------|:-------|:--------|
| `ga_split_engine.py` | **Moved** | Full GA-Split engine in `uniride_core`. `ga_split_strategy.py` is wrapper. |
| `pso_split_engine.py` | **Moved** | Full PSO-Split engine in `uniride_core`. `pso_split_strategy.py` is wrapper. |
| `gwo_split_engine.py` | **Moved** | Full GWO-Split engine in `uniride_core`. `gwo_split_strategy.py` is wrapper. |
| `hho_split_engine.py` | **Moved** | Full HHO-Split engine in `uniride_core`. `hho_split_strategy.py` is wrapper. |
| `tsp_meta_engines.py` — GA | **Moved** | `solve_ga_tsp`, `tournament_selection`, operators. Wrapper delegates. |
| `tsp_meta_engines.py` — PSO | **Moved** | `solve_pso_tsp`, swap-sequence velocity. Wrapper delegates. |
| `tsp_meta_engines.py` — GWO | **Moved** | `solve_gwo_tsp`, `update_gwo_position`, difference operators. Wrapper delegates. |
| `tsp_meta_engines.py` — HHO | **Moved** | `solve_hho_tsp`, siege methods, `levy_flight_permutation`. Wrapper delegates. |
| `tsp_meta_engines.py` — TwoOpt | **Moved** | `solve_two_opt_tsp`, `nearest_neighbor_route`. Wrapper delegates. |
| `ortools_cvrp_engine.py` | **Moved** | OR-Tools CVRP adapter is core-owned. `ortools_cvrp.py` is a thin production wrapper. |
| `pyvrp_cvrp_engine.py` | **Moved** | PyVRP CVRP adapter is core-owned with installed-library validation and infeasibility handling. |
| `vroom_cvrp_engine.py` | **Moved** | VROOM CVRP adapter and deterministic fallback are core-owned. `vroom_strategy.py` maps API responses only. |
| `cvrptw_decoder.py` | **Moved** | CVRPTW stable/bounded decoder selection and time-window helpers are core-owned. `cvrptw_wrapper.py` is a compatibility export. |
| `sota_common/` | **Moved** | String-indexed SOTA infrastructure now lives under `uniride_core.algorithms.sota_common`; `optimizer_api/strategies/sota_common` is compatibility-only. |
| `clustering_strategies/` + `VehicleCalculator` | **Moved** | Cluster-first vehicle assignment logic now lives in `uniride_core`; `optimizer_api/utils/clustering*` is compatibility-only. |

### Wrapper Pattern

All `optimizer_api/strategies/*_strategy.py` files now follow a consistent pattern:
1. Build `duration_func` closure from request context (time matrix + coordinates).
2. Delegate TSP solving to `uniride_core.algorithms.tsp_meta_engines.*`.
3. Handle request parsing, vehicle assignment, and response formatting only.

Stale imports (`logging`, `SingletonMeta`, unused `BaseRoutingStrategy`) cleaned from all strategy files.

### Tests

- `uniride_core/tests/test_tsp_meta_engines.py` — 7 tests covering GA, PSO, GWO, HHO, TwoOpt TSP solvers.
- `uniride_core/tests/test_meta_split_engines.py` — 3 tests covering GWO-Split, HHO-Split, PSO-Split.
- `uniride_core/tests/test_algorithm_imports.py` — Smoke test verifying all `__all__` exports are importable across 6 core modules.
- `optimizer_api/tests/test_all_strategies_smoke.py` — Integration smoke test for all strategy wrappers.

---

## Independent Review Follow-up (2026-05-31)

The independent v4 verification report is broadly correct on the core-first
architecture, but the following verified follow-ups remain:

| Finding | Status | Priority | Notes |
|:--------|:-------|:---------|:------|
| Frontend typecheck failure in `src/app/(app)/admin/vehicle-planning/page.tsx` | RESOLVED | Formerly high, non-academic | Current `npm run typecheck` passes. Keep this row only as historical context from the earlier review state. |
| PSO production wrapper still has instance-level `self.rng` helper paths | RESOLVED | Formerly medium | Active `optimizer_api/strategies/pso_strategy.py` no longer keeps `self.rng`; helpers use request-local `random.Random` instances and delegate solver logic to `uniride_core`. Regression coverage proves request-level `pso_config` is passed without mutating strategy defaults. |
| HHO production wrapper still creates `self.rng` | RESOLVED | Formerly low | Active `hho_strategy.py` no longer assigns `self.rng`; `optimize()` builds request-local RNG/config and delegates TSP solving to `uniride_core`. Regression coverage proves request-level `hho_config` is passed without mutating strategy defaults. |
| Duplicate `Direction` enum names | RESOLVED | Formerly low/medium | `optimizer_api.models.schemas.TripDirection` is now canonical and `Direction` remains a backward-compatible alias. Core split decoders normalize enum-like direction values without importing `optimizer_api`; regression coverage verifies API enum values work at the core boundary. |
| Duplicate SOTA Euclidean helper | RESOLVED | Formerly low | `uniride_core.algorithms.sota_tsp.base_solver.BaseTSPSolver.euclidean_distance()` delegates to canonical `distance.euclidean_distance_2d`; regression coverage monkeypatches the canonical helper to prove delegation rather than merely equal output. |
| `ProblemInstance` legacy/god-model shape | VERIFIED | Low now, medium later | Keep as legacy academic adapter until benchmark suite is stable. Model subpackage split is useful but should not precede today's academic benchmark readiness work. |
| `registry_setup.py` import claim in review was over-broad | CORRECTED | Informational | It imports from `academic_benchmark.engine_core` as expected. The important invariant remains: `uniride_core` does not import `academic_benchmark` or `optimizer_api`. |

---

## Candidate Research Extension: FCM-SRS Large-TSP Meta-Solver (2026-05-31)

Source document: `implementation_plan_fcm_hybrid.md`.

Status: **IMPLEMENTED / RESEARCH PREVIEW**. The reusable FCM clustering pieces
remain in `uniride_core.algorithms.clustering_strategies`, and the FCM
Split-Route-Stitch meta-solver is now implemented as
`uniride_core.algorithms.fcm_split_engine.FCMSplitMatrixEngine`. Academic
registry entries exist for `FCM-GA-TSP`, `FCM-PSO-TSP`, `FCM-GWO-TSP`, and
`FCM-HHO-TSP`, with DoE/Optuna parameter spaces for `fcm_clusters`, `fcm_m`,
`fcm_iterations`, and polish controls.

Design correction before implementation:

- Use only `uniride_core.algorithms.clustering_strategies.*` for FCM. The
  original plan's `optimizer_api.utils.clustering_strategies.fuzzy_cmeans`
  import is no longer acceptable under the core-first architecture.
- Keep FCM-SRS academic-first and matrix-first. It should not become a
  production default until it proves value in SQLite-backed academic runs.
- Start with coordinate-backed TSP large-instance decomposition. Explicit
  matrix-only ATSP needs a separate clustering/embedding decision; CVRP/CVRPTW
  decomposition needs capacity and time-window aware stitching and should be a
  later extension.
- Avoid nested oversubscription: prefer outer benchmark workers by default;
  only enable subproblem parallelism when the outer worker count is one.
- Clamp `fcm_m` above `1.0`. Initial tuning bounds should stay conservative,
  for example `[1.5, 2.5]`, with implementation guards for `[1.1, 3.0]`.

Implementation roadmap:

| Order | Task | Dependency | Notes |
|:------|:-----|:-----------|:------|
| FCM-1 | Add core `FCMSplitMatrixEngine` | DONE | Implemented in `uniride_core`; wraps existing core TSP solvers rather than duplicating GA/PSO/GWO/HHO logic. |
| FCM-2 | Add deterministic stitching and polish tests | DONE | Tests verify every node appears once and factory-created FCM engines solve matrix-native TSP problems. |
| FCM-3 | Register `FCM-GA-TSP`, `FCM-PSO-TSP`, `FCM-GWO-TSP`, `FCM-HHO-TSP` | DONE | Registered through academic/core registry construction without adding optimizer-api dependencies. |
| FCM-4 | Add Optuna/grid parameter spaces | DONE | Includes `fcm_clusters`, `fcm_m`, `fcm_iterations`, `fcm_min_cluster_size`, and polish controls with inherited base params. |
| FCM-5 | Run academic benchmark comparison versus pure base solvers | SMOKE COMPLETE / LARGE VALIDATION PENDING | `run_fcm_srs_comparison` persists paired core-vs-FCM results to SQLite. Initial 24-node smoke completed; medium/large sweeps are still required before promotion. |

---

## Remaining Tasks (Logical Order)

This list is reordered for today's priority: make the `academic_benchmark`
suite runnable end-to-end first, then return to production hardening.

| Order | Task | Phase | Dependency | Notes |
|:------|:-----|:------|:-----------|:------|
| 1 | Broaden CVRPLIB/Solomon benchmark execution | 3.2 / 3.3 | Depends on verified optional deps, seeded smoke path, downloaded instance files, and BKS metadata | DONE for current imported corpus / MONITORED for future imports. Starter dataset download/import is done, BKS-backed hierarchical gap handling is active, and all imported CVRP/CVRPTW rows have current OR-Tools/PyVRP single-seed and two-seed validation evidence. Continue only when adding more instances, more algorithms, or higher time-limit promotion runs. |
| 2 | Holistic solver constraint-validation pass | 3.3 / 4.2 | DONE / MONITORED | Root causes identified and fixed/guarded. Scalar CVRP demand, Solomon distance semantics, CVRPTW windows/service times, defensive returned-route validation, hierarchical VRPTW gap reporting, broader all-imported dataset execution, and VROOM uint32 C-contiguous matrix-buffer preparation are covered. Remaining work is monitoring solver quality/runtime as more real instances are imported or solver configs are promoted. |
| 3 | Promotion-quality config generation | 4.1 / 4.2 | Depends on tasks 1 and 2 with real datasets | FUNCTIONAL / EVIDENCE-GATED. Promotion generation includes feasible benchmark rows with empty `{}` params when allowed, excludes failed/infeasible rows, prefers non-smoke evidence, normalizes near-zero gaps, reads benchmark params from result metadata, and now supports opt-in `min_evidence_runs` gating so release-grade configs can require multiple feasible rows for the same promoted parameter set. Continue by running broader real multi-seed jobs before freezing a release config file. |
| 4 | Additional controlled FCM-SRS validation | Phase 6 candidate | Independent after current controlled runs | DONE for first controlled pass on 144-node GA/PSO, 256-node PSO, and 500-node PSO. Continue only if targeting FCM promotion; add more seeds, dimensions, and real TSPLIB-style instances before promoting. |
| 5 | Production strategy migration: remaining SOTA wrappers | 4.x | Independent of academic runs, lower priority | AUDITED / COVERED. E2BSO/R2DMA/P-AOEA wrappers delegate to core TSP solvers, use promoted constructor defaults, and merge per-request `sota_config` into request-local dataclass configs without mutating defaults. Remaining work is only future UI exposure if richer SOTA parameter editing is needed. |
| 6 | Production strategy migration: holistic/split wrapper thinning | 4.x | Depends on holistic comparison clarity | COVERED for current active wrappers, with active cleanup continuing. `optimizer_api` remains responsible for API mapping; OR-Tools/PyVRP/VROOM solver logic, VROOM sweep fallback routing, string greedy routing, exact string TSP, and GWO/HHO split search logic are guarded as core-owned. GA, PSO, and GWO TSP wrapper dead operator helpers plus the unused TwoOpt shuffle helper have been removed so the active route-search boundary is `_solve_tsp() -> uniride_core.solve_*_tsp()`. Continue with the same cleanup pattern for other wrappers if audits find unused private algorithm helpers. |
| 7 | Packaging and requirements cleanup | Cross-phase | After dependency decisions | FUNCTIONAL for current scope. `pyproject.toml` pins the compatible `pydantic` / `pydantic-core` pair and declares optional solver/importer packages (`vrplib`, `ortools`, `pyvrp`, `pyvroom`) under `solvers`. Keep graceful fallback imports. |
| 8 | Full regression gate before release branch | Cross-phase | Depends on chosen release scope | CURRENTLY GREEN for the main local gate: `academic_benchmark\tests` passes with 194 tests, `uniride_core\tests` passes with 204 tests, focused optimizer API compatibility/migration tests pass with 43 tests, and `npm run typecheck` passes. The all-in-one Python command can exceed a 180s tool timeout because the optimizer smoke subset takes about 162s alone; run the gate in chunks. Remaining release-scope work is broader optimizer API/frontend runtime coverage if requested. |

### Progress Update (2026-05-31)

Completed today:

- Task 1: full academic/core verification is green — `python -m pytest academic_benchmark/tests uniride_core/tests -q` passes with 310 tests.
- Task 2: optional dependency check completed — `vrplib`, `ortools`, `pyvrp`, and the `pyvroom` package's `vroom` module are importable/available for current adapters.
- Task 3: `academic_benchmark.cvrplib_manager` added as a facade over unified SQLite storage; it does not introduce a second schema.
- Task 4: smoke seed utility added and executed locally. Real DB now has `smoke-tsp`, `smoke-atsp`, `smoke-cvrp`, `smoke-solomon`, and `smoke-uniride`.
- Task 5: matrix-native academic smoke benchmark added and executed locally with run id `academic-matrix-smoke-20260531`; 5 results persisted, 0 errors.
- Task 6: promotion manager dry-run and write completed locally; 26 configs generated from existing `best_solutions`, not smoke params. The generated JSON is ignored/untracked.
- Task 7: web/API sanity path verified locally. Academic problem/result endpoints read from SQLite, param spaces expose editable params, and matrix-native web execution persisted run id `web-matrix-sanity-20260531-r2` with editable `Core-TwoOpt-TSP` params.
- Task 8: CVRP/CVRPTW dashboard polish added. Dashboard utilities now derive dataset family, routing feasibility, constraint status, and vehicle gap; the Streamlit dashboard has a dedicated routing diagnostics tab.
- Task 10: frontend typecheck failure fixed. `src/app/(app)/admin/vehicle-planning/page.tsx` had a corrupted student-selection JSX block; `npm run typecheck` now passes.
- Task 11: PSO/HHO rng cleanup completed. `pso_strategy.py` and `hho_strategy.py` no longer keep `self.rng`; PSO legacy helpers use local RNG instances and active optimization keeps per-request RNG forwarding into `uniride_core`.
- Task 12: Direction enum rename completed. `optimizer_api.models.schemas.TripDirection` is now the canonical API enum and `Direction = TripDirection` remains as a compatibility alias for existing callers/tests.
- Task 13: SOTA Euclidean helper consolidation completed. `BaseTSPSolver.euclidean_distance()` now delegates to the canonical raw `euclidean_distance_2d` helper and regression tests cover direct coordinate matrix construction.
- Task 14: DataLoader ownership cleanup completed. `optimizer_api.utils.data_loader` remains app-owned because it owns Supabase credentials, cache TTL, and request-time matrix glue; its fallback Euclidean/haversine matrix helpers now use canonical `uniride_core.algorithms.distance` functions.
- Task 9: FCM-SRS large-TSP research extension implemented as a research preview. `FCMSplitMatrixEngine` lives in `uniride_core`, `FCM-GA/PSO/GWO/HHO-TSP` are available in the core factory and academic registry, and DoE/Optuna parameter spaces include FCM controls. Added `academic_benchmark.run_fcm_srs_comparison` as a repeatable SQLite validation gate with CLI runtime controls. Local run `fcm-srs-comparison-20260601` completed with 2 saved results and no errors; `Core-GA-TSP` beat `FCM-GA-TSP` on the 24-node synthetic smoke. Local run `fcm-srs-default-20260601` completed with 4 saved results and no errors on 36 nodes; `FCM-GA-TSP` slightly beat `Core-GA-TSP`, while `Core-PSO-TSP` beat `FCM-PSO-TSP`. Local run `fcm-srs-medium-20260601` completed with 4 saved results and no errors on 100 nodes; pure core GA/PSO remained slightly better. A 500-node paired pure-vs-FCM run timed out before persisting rows, but FCM-only `fcm-srs-large-fcm-pso-only-20260601` completed with 1 saved result and no errors, showing large-instance feasibility for the split path. Controlled run `fcm-srs-controlled-144-20260601` completed with 4 saved results and no errors using population 8, max iterations 5, and FCM polish 10: `FCM-GA-TSP` improved objective/runtime versus `Core-GA-TSP` (328.416 vs 348.220; 7.6s vs 36.8s), and `FCM-PSO-TSP` slightly improved objective versus `Core-PSO-TSP` with similar runtime (346.743 vs 349.776; 4.3s vs 4.2s). Controlled run `fcm-srs-controlled-256-pso-20260601` completed with 2 saved results and no errors: `FCM-PSO-TSP` was effectively tied on objective and somewhat faster than `Core-PSO-TSP` (384.194 vs 384.216; 31.0s vs 35.5s). Controlled run `fcm-srs-controlled-500-pso-20260601` completed with 2 saved results and no errors using population 6, max iterations 3, and FCM polish 5: `Core-PSO-TSP` had lower objective, while `FCM-PSO-TSP` was faster (518.643 vs 528.444; 252.4s vs 214.3s). Promotion still requires multi-seed and real benchmark-family validation.
- Task 15: CVRPLIB/Solomon facade CLI added. `python -m academic_benchmark.cvrplib_manager status` works against the local academic DB and reports the current smoke CVRP/CVRPTW counts (`total=2`, `CVRP=1`, `CVRPTW=1`). `import` supports supported files/directories without creating a second schema.
- Task 16: Split-engine TSP/ATSP compatibility dispatch completed. `GA-Split`, `PSO-Split`, `GWO-Split`, and `HHO-Split` are accepted by the core matrix engine factory for TSP/ATSP `RoutingProblem`s and delegate to their direct TSP metaheuristic engines, preserving split decoding for CVRP/CVRPTW/UniRide paths. Focused verification: `python -m pytest uniride_core\tests\test_split_engine_tsp_atsp_dispatch.py uniride_core\tests\test_engine_factory.py -q` passes with 12 tests, and academic registry/CVRP focused tests pass with 16 tests.
- Task 17: Holistic adapter unified dispatch completed. `OR-Tools`, `PyVRP`, and `VROOM` are accepted by the core matrix engine factory and solve TSP/ATSP as one-vehicle routing plus CVRP as `RoutingResult`. VROOM keeps native pyvroom use when available and falls back to deterministic sweep routing if the Windows pyvroom matrix API rejects the buffer format. Verification: `python -m pytest uniride_core\tests academic_benchmark\tests -q` passes with 343 tests.
- Task 18: Benchmark API request contract tightened. `BenchmarkRunRequest` now preserves the existing web payload shape while validating non-empty run ids, algorithm ids/names, problem names, matrix-native execution modes, run counts, workers, seeds, and skip-cache flags before runtime. Focused verification: `python -m pytest optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 20 tests. Broader verification: `python -m pytest uniride_core\tests academic_benchmark\tests optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 363 tests.
- Task 19: `academic_benchmark/bildiri2026/orchestrate_batch.py` subprocess hardening completed. Batch orchestration now invokes Python scripts with argv lists, fixed script-directory working directory, and no `shell=True`. Regression test added. Verification: `python -m pytest academic_benchmark\tests\test_orchestrate_batch.py academic_benchmark\tests uniride_core\tests -q` passes with 344 tests.
- Task 20: Academic `compute_gap` drift reduced. `academic_benchmark.core.evaluation.compute_gap()` is now a compatibility wrapper over the canonical `academic_benchmark.benchmark_utils.compute_gap()` helper, preserving the two-argument API while removing the second independent formula. Regression test added. Verification: `python -m pytest academic_benchmark\tests uniride_core\tests -q` passes with 345 tests.
- Task 21: Academic parameter-value validation duplication removed. `academic_benchmark.benchmark_utils.validate_param_value()` now has one implementation that supports both simple parser use and validator-bound interactive parameter edits; the overwritten duplicate was removed. Regression tests cover the 3-argument and 4-argument paths. Verification: `python -m pytest academic_benchmark\tests uniride_core\tests -q` passes with 347 tests.
- Task 22: Generic SQLite matrix-native benchmark CLI added. `python -m academic_benchmark.run_matrix_benchmark` can select stored academic problems by explicit name or problem type, instantiate core matrix engines by factory alias, run them directly on `RoutingProblem`, and persist all result/error rows to the academic SQLite source-of-truth. Current active workspace scan found no real CVRPLIB/Solomon files to import, so Task 1 broad import remains waiting on dataset files. Smoke CVRP/CVRPTW execution completed and persisted: `matrix-cvrp-cvrptw-core-20260601` saved 8 rows for `Core-Greedy-Routing`, `Core-TwoOpt-TSP`, `GA-Split`, and `PSO-Split`; `matrix-cvrp-cvrptw-holistic-20260601` saved 6 rows for `OR-Tools`, `PyVRP`, and `VROOM`; both had `errors=[]`. Verification: `python -m pytest academic_benchmark\tests uniride_core\tests -q` passes with 349 tests.
- Task 23: CVRPLIB/Solomon import readiness improved. `python -m academic_benchmark.cvrplib_manager scan <paths>` now reports supported, skipped, and missing files without writing SQLite, and the importer recognizes common Solomon `.vrptw` files in addition to `.txt` and `.solomon`. Verification: `python -m pytest academic_benchmark\tests uniride_core\tests -q` passes with 351 tests.
- Task 24: Public CVRP/CVRPTW starter datasets downloaded and placed. CVRPLIB starter files from <https://galgos.inf.puc-rio.br/cvrplib/en/instances> and SINTEF Solomon 100-customer files from <https://www.sintef.no/projectweb/top/vrptw/100-customers/> are tracked under `academic_benchmark/datasets/raw/` with `SOURCES.md`. Local ignored SQLite was seeded from those files and a real matrix slice (`matrix-real-slice-core-holistic-20260601`) saved 24 rows with `errors=[]`. Important caveat: holistic adapter outputs on real Solomon/CVRPLIB cases are not promotion-quality yet because some rows are suspiciously below known benchmark expectations; audit adapter constraint mapping before using them for algorithm ranking.
- Task 25: Lower-than-BKS holistic quality investigation completed for the first root causes. Fixed generic vector/scalar demand enforcement in OR-Tools, PyVRP, and VROOM core adapters, preserving UniRide SW/SO compatibility while honoring scalar CVRP loads. Fixed Solomon parser distance semantics to use double-precision Euclidean distances instead of TSPLIB integer rounding. Added CVRPTW post-validation for holistic results so time-window-infeasible Solomon rows are persisted with nonzero `tw_violations`. Reimported local ignored SQLite from tracked raw files and reran real slices: `matrix-real-slice-holistic-capacityfix-20260601` shows A-n32-k5 PyVRP = 784, A-n33-k5 OR-Tools/PyVRP = 661, and B-n31-k5 OR-Tools/PyVRP = 672; `matrix-real-solomon-holistic-twflag-20260601` shows remaining below-BKS Solomon rows carry high `tw_violations`. Verification: `python -m pytest academic_benchmark\tests uniride_core\tests -q` passes with 356 tests.
- Task 26: Native/defensive CVRPTW enforcement added to holistic core adapters. OR-Tools now uses a cumulative time dimension with waiting, service times, depot/customer windows, and route duration horizon. PyVRP now receives `tw_early`, `tw_late`, `service_duration`, depot windows, and shift duration, with adapter-level returned-route validation. VROOM now receives job/vehicle time windows and service times; for CVRPTW it no longer falls back to the non-time-window sweep fallback when pyvroom fails. Real Solomon slice `matrix-real-solomon-holistic-cvrptw-native-20260601` now has feasible rows with `tw_violations=0` and solver failures represented as errors instead of infeasible ranked results. Verification: `python -m pytest academic_benchmark\tests uniride_core\tests -q` passes with 362 tests.
- Task 27: Promotion-safe feasible-row filtering added. `academic_benchmark.promoted_configs` now ignores benchmark rows with `execution_failed`, nonzero `capacity_violations`, nonzero `tw_violations`, or no finite objective/tour cost before selecting promoted params. `academic_benchmark.results_reader.get_benchmark_rows(..., feasible_only=True)` now exposes the same feasibility gate for dashboard/API callers while preserving raw audit rows by default. Verification: focused results/promoted-config tests pass with 16 tests.
- Task 28: Academic benchmark-results API now exposes feasible-row filtering. `optimizer_api.routers.benchmark.get_academic_benchmark_results()` accepts `feasible_only` and forwards it to `academic_benchmark.results_reader.get_benchmark_rows()`, so web/API consumers can request promotion-safe rows while raw rows remain available by default. Verification: focused router/results/promoted-config tests pass with 23 tests.
- Task 29: Broader real CVRPLIB/Solomon post-fix slice executed locally. Run id `matrix-real-broader-core-holistic-20260602` covered 8 selected CVRPLIB instances plus 9 representative Solomon C/R/RC instances across `Core-Greedy-Routing`, OR-Tools, PyVRP, and VROOM. SQLite saved 68 rows: 46 feasible rows, 13 execution-failed rows, 9 time-window-violating rows, 0 capacity-violating rows. CVRP rows were all feasible; CVRPTW rows are now cleanly separated into feasible versus excluded instead of silently ranking infeasible lower-than-BKS outputs. This run is local/ignored DB evidence, not committed benchmark data.
- Task 30: Promotion-quality config generation fixed and rerun. Root cause found: `--allow-empty-params` relaxed validation but `_benchmark_result_candidates()` still dropped feasible benchmark rows with empty `{}` params, excluding deterministic/core/holistic routing algorithms. The builder/CLI now propagates `include_empty_params` when empty params are allowed. Local generated config now has 65 configs: 37 TSP, 7 ATSP, 7 CVRP, 7 CVRPTW, and 7 UniRide entries; 39 entries come from `benchmark_results`, including `Core-Greedy-Routing`, `Core-TwoOpt-TSP`, `GA-Split`, `PSO-Split`, OR-Tools, PyVRP, and VROOM. Verification: `python -m pytest academic_benchmark\tests\test_promoted_configs.py academic_benchmark\tests\test_results_reader.py -q` passes with 11 tests.
- Task 31: Bounded multi-run real CVRPLIB/Solomon validation executed locally. Run id `matrix-real-multirun-core-holistic-20260602` covered `A-n32-k5`, `A-n33-k5`, `B-n31-k5`, `C101`, `R101`, and `RC101` across `Core-Greedy-Routing`, OR-Tools, PyVRP, and VROOM with 3 runs each. SQLite saved 72 rows: 48 feasible, 15 execution-failed, 9 time-window-violating, 0 capacity-violating. Best feasible examples: `A-n32-k5` PyVRP 784 / OR-Tools 796, `A-n33-k5` OR-Tools/PyVRP 661, `B-n31-k5` OR-Tools/PyVRP 672, `C101` OR-Tools/PyVRP 828.9369, `R101` PyVRP 1702.9163, `RC101` PyVRP 1787.4575. VROOM still fails on Solomon under Windows pyvroom matrix buffer handling; OR-Tools still fails to find solutions on selected R/RC instances under current defaults. This is local/ignored DB evidence.
- Task 32: Matrix benchmark CLI solver-param override added. `academic_benchmark.run_matrix_benchmark` now accepts programmatic `algorithm_params` and CLI `--params-json`, stores those params in benchmark run settings, and passes them through `MatrixAlgorithmConfig.params` into core engines. This enables academic SQLite runs with controlled solver knobs such as `{"time_limit_seconds": 5}` without routing through production `OptimizationRequest`. Local targeted run `matrix-real-solomon-time5-20260602` saved 6 rows: OR-Tools/PyVRP both feasible on `C101` at 828.9369, PyVRP feasible on `R101` at 1655.8213 and `RC101` at 1639.9684, while OR-Tools still failed on `R101`/`RC101`. Verification: `python -m pytest academic_benchmark\tests\test_run_matrix_benchmark.py -q` passes with 4 tests.
- Task 33: OR-Tools academic search strategy knobs added. `solve_ortools_cvrp()` now accepts `first_solution_strategy` and `local_search_metaheuristic` as OR-Tools enum names or integer values, and `HolisticMatrixEngine` forwards these from matrix benchmark params. Defaults remain `PATH_CHEAPEST_ARC` and `GUIDED_LOCAL_SEARCH`. Local targeted run `matrix-real-solomon-ortools-pci-time10-20260602` with `PARALLEL_CHEAPEST_INSERTION`, `GUIDED_LOCAL_SEARCH`, and `time_limit_seconds=10` completed without errors: `C101` 828.9369, `R101` 1663.9249, `RC101` 1702.9194, all feasible with zero TW violations. Verification: focused OR-Tools and matrix benchmark tests pass.
- Task 34: OR-Tools integer precision control added for academic CVRPTW. OR-Tools matrix/service/window scaling now uses rounded integer conversion, and `HolisticMatrixEngine` forwards `scale` into OR-Tools and PyVRP adapters. Local R102-only run `matrix-real-r102-ortools-pci-time10-scale1000-20260602` cleared the previous OR-Tools TW violation (`R102` 1483.8836, 18 vehicles, 0 TW, 0 capacity violations). Broader local run `matrix-real-solomon-holistic-time10-pci-scale1000-20260602` covered `C101`, `C102`, `R101`, `R102`, `RC101`, and `RC102` for OR-Tools/PyVRP: 12 rows, all feasible, 0 execution errors, 0 TW violations, 0 capacity violations. Best examples: `R101` PyVRP 1642.8769 / OR-Tools 1663.8784, `R102` PyVRP 1472.8149 / OR-Tools 1483.8836, `RC101` PyVRP 1627.1358 / OR-Tools 1700.65, `RC102` PyVRP 1461.233 / OR-Tools 1560.9693. Verification: focused OR-Tools/holistic/matrix benchmark tests pass.
- Task 35: Promotion ranking and per-algorithm benchmark params cleaned up. Promotion now prefers non-smoke evidence, uses finite gaps when available, and for no-gap VRP rows prefers the latest validation before objective cost, preventing stale pre-fix rows from outranking current evidence. Promoted benchmark params now fall back to `metadata.algorithm_params`, which is where matrix-native runs persist solver settings. `run_matrix_benchmark` also accepts `--algorithm-params-json` for per-algorithm overrides merged over global `--params-json`, so OR-Tools-specific strategy fields no longer pollute PyVRP configs. Clean local run `matrix-real-solomon-holistic-peralgo-time10-scale1000-20260602` saved 12/12 feasible Solomon OR-Tools/PyVRP rows with separated params; regenerated promoted CVRPTW configs now select this run: OR-Tools params include insertion strategy/GLS/scale/time limit, PyVRP params include only scale/time limit. Verification: focused promotion and matrix benchmark tests pass.
- Task 36: CVRPLIB/Solomon BKS application and hierarchical VRPTW gap handling added. New `academic_benchmark.bks_manager` parses tracked CVRPLIB `.sol` files and SINTEF Solomon solution route files, computes Solomon BKS distances from stored matrices, updates `problems.optimal`, and stores `bks_cost`, `bks_vehicles`, and `bks_source` in routing metadata. Local DB update applied 64 real problem BKS records with no skips. `MatrixBenchmarkRunner` now records `vehicle_gap` for CVRPTW rows with BKS vehicle metadata and suppresses distance gap when solver vehicle count differs from BKS vehicle count, avoiding misleading negative distance gaps for hierarchical VRPTW. Promotion also normalizes near-zero floating gap noise to `0.0`. Local run `matrix-bks-gap-hierarchical-20260603` verified CVRP gaps (`A-n32-k5` OR-Tools/PyVRP 0.0) and CVRPTW behavior (`C101` vehicle_gap 0 with zero gap; `R102`/`RC102` vehicle_gap positive with distance gap suppressed). Verification: focused BKS/runner tests pass.
- Task 37: BKS/vehicle-gap dashboard exposure and bounded validation completed. `academic_benchmark.dashboard_utils.benchmark_rows_to_progress_frame()` now flattens benchmark-result metadata into first-class dashboard columns: `bks_cost`, `bks_vehicles`, `num_vehicles_bks`, `vehicle_gap`, and `bks_source`. Regression coverage verifies SQLite-style rows preserve these fields. Local run `matrix-bks-dashboard-broader-20260603` saved 16 OR-Tools/PyVRP rows with no errors across `A-n32-k5`, `A-n33-k5`, `B-n31-k5`, `B-n34-k5`, `C101`, `C102`, `R101`, and `RC101`. Expected hierarchical behavior was observed: `C101`/`C102` match BKS vehicle count and keep zero distance gap, while `R101`/`RC101` have positive `vehicle_gap` and suppress distance gap. Promotion regenerated 65 configs. Verification: `python -m pytest academic_benchmark\tests -q` passes with 180 tests.
- Task 38: Dependency pin cleanup and full local regression gate completed. Local environment blocker was confirmed (`pydantic-core 2.47.0` with `pydantic 2.13.4`, which requires `2.46.4`) and resolved by installing `pydantic-core==2.46.4`. `pyproject.toml` now pins `pydantic==2.13.4` and `pydantic-core==2.46.4`, and exposes optional solver/importer packages through the `solvers` extra. `academic_benchmark/tests/test_dependency_manifest.py` guards those manifest contracts. Local broader validation run `matrix-bks-broader-ab-solomon-20260603` saved 34 OR-Tools/PyVRP rows with no errors, no capacity violations, and no time-window violations across selected CVRPLIB A/B and Solomon C/R/RC instances; R/RC cases with positive vehicle gaps correctly suppress distance gaps. Verification: focused dependency/API tests pass with 22 tests; combined `python -m pytest academic_benchmark\tests uniride_core\tests optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 403 tests; `npm run typecheck` passes.
- Task 39: Production SOTA wrapper audit completed. `E2BSoStrategy`, `R2DMAStrategy`, and `PAOEAStrategy` are confirmed thin production wrappers over `uniride_core` SOTA TSP solvers and `solve_student_order_with_sota_tsp`; no critical SOTA algorithm logic remains in those wrappers. Regression coverage now proves promoted constructor defaults load for all three wrappers and that request-time `sota_config` is merged into an effective dataclass config without mutating the stored default config. Verification: `python -m pytest optimizer_api\tests\test_sota_config_parity.py -q` passes with 12 tests; combined `python -m pytest academic_benchmark\tests uniride_core\tests optimizer_api\tests\test_sota_config_parity.py optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 415 tests.
- Task 40: Repeatable matrix-run summary reporting added. New `academic_benchmark.matrix_run_summary` summarizes persisted matrix-native benchmark runs from SQLite, including total/failed/feasible rows, capacity and time-window violation counts, positive vehicle-gap counts, distance-gap suppression counts, unexpected distance gaps with positive vehicle gaps, per-problem-type counts, and best feasible rows by problem/algorithm. CLI usage: `python -m academic_benchmark.matrix_run_summary <run_id>`. Current local summary for `matrix-bks-broader-ab-solomon-20260603` reports 34 total rows, 34 feasible rows, 0 failures, 0 capacity violations, 0 time-window violations, 11 positive vehicle-gap rows, 11 distance-gap-suppressed rows, and 0 unexpected distance gaps with vehicle gaps. Verification: `python -m pytest academic_benchmark\tests\test_matrix_run_summary.py -q` passes with 3 tests; combined `python -m pytest academic_benchmark\tests uniride_core\tests optimizer_api\tests\test_sota_config_parity.py optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 418 tests.
- Task 41: Repeatable multi-seed matrix validation plan added and run. New `academic_benchmark.matrix_validation_plan` builds named validation jobs for solver time-limit variants, runs them through `run_matrix_benchmark`, and immediately summarizes the persisted SQLite rows with `matrix_run_summary`. Default variants cover OR-Tools/PyVRP with `time10-scale1000` and `time20-scale1000`, OR-Tools parallel cheapest insertion plus guided local search, and selected CVRPLIB/Solomon families. Regression coverage verifies job construction, runner/summarizer wiring, and JSON serialization of tuple-keyed best-feasible summaries. Local bounded multi-seed run `matrix-validation-ms-20260603-time10-scale1000` used 7 representative CVRP/CVRPTW problems, OR-Tools/PyVRP, and 2 runs per solver/problem: 28 total rows, 28 feasible rows, 0 failures, 0 capacity violations, 0 time-window violations, 8 positive vehicle-gap rows, 8 distance-gap-suppressed rows, and 0 unexpected distance gaps with vehicle gaps. Verification: `python -m pytest academic_benchmark\tests\test_matrix_validation_plan.py academic_benchmark\tests\test_matrix_run_summary.py -q` passes with 6 tests; combined `python -m pytest academic_benchmark\tests uniride_core\tests optimizer_api\tests\test_sota_config_parity.py optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 421 tests.
- Task 42: Full default two-variant multi-seed validation completed locally. `python -m academic_benchmark.matrix_validation_plan --run-id-prefix matrix-validation-full-20260603 --n-runs 2 --seed 2400` ran the default OR-Tools/PyVRP validation plan over 10 selected CVRPLIB/Solomon instances and both solver variants (`time10-scale1000`, `time20-scale1000`). Each run persisted 40 SQLite rows with `errors=[]`. Direct summaries show both variants have 40 total rows, 40 feasible rows, 0 failed rows, 0 capacity violations, 0 time-window violations, 14 positive vehicle-gap rows, 14 distance-gap-suppressed rows, and 0 unexpected distance gaps with positive vehicle gaps. Promotion regeneration still yields 65 configs; OR-Tools/PyVRP CVRP/CVRPTW promoted entries remain at normalized `0.0` gap.
- Task 43: Holistic production wrapper response mapping thinned. `optimizer_api/strategies/holistic_response_builder.py` now owns API-schema conversion for holistic core route plans: sequence-based customer routes used by PyVRP/VROOM and indexed-step routes used by OR-Tools. `pyvrp_strategy.py`, `vroom_strategy.py`, and `ortools_cvrp.py` now delegate duplicated response construction to that compatibility helper while keeping solver logic in `uniride_core`. Regression coverage pins both response-mapping contracts. Verification: focused holistic wrapper/core tests pass with 30 tests.
- Task 44: Broader academic matrix validation executed locally. Run id `matrix-validation-broader-20260603-time10-scale1000` covered 13 imported non-smoke CVRPLIB A/B instances plus 18 Solomon C/R/RC 101-106 instances across OR-Tools and PyVRP with one run each and `time_limit_seconds=10`, `scale=1000`. SQLite saved 62 rows with `errors=[]`: 62 feasible rows, 0 failed rows, 0 capacity violations, 0 time-window violations, 23 positive vehicle-gap rows, 23 distance-gap-suppressed rows, and 0 unexpected distance gaps with positive vehicle gaps. CVRP rows were all feasible; C-family Solomon rows include finite zero/near-zero gaps where vehicle counts match BKS, while R/RC rows correctly suppress distance gap when solver vehicle count is above BKS. Promotion regeneration check passed with `--allow-empty-params --min-configs 60`, yielding 65 local ignored configs.
- Task 45: All imported real CVRPLIB/Solomon validation executed locally through the existing matrix validation CLI. Run id `matrix-validation-all-imported-20260603-time10-scale1000` covered all 69 imported non-smoke CVRP/CVRPTW problems: 13 CVRPLIB A/B instances and 56 Solomon C/R/RC instances, across OR-Tools and PyVRP with one run each. SQLite saved 138 rows with `errors=[]`: 138 feasible rows, 0 failed rows, 0 capacity violations, 0 time-window violations, 75 positive vehicle-gap rows, 75 distance-gap-suppressed rows, and 0 unexpected distance gaps with positive vehicle gaps. C-family Solomon rows with matching BKS vehicle counts keep normal distance gaps; R/RC rows with extra vehicles remain explicitly hierarchical via `vehicle_gap` and suppressed distance gap. Promotion regeneration check still passes with 65 local ignored configs.
- Task 46: Production RNG-state regression coverage strengthened. `optimizer_api/tests/test_strategy_rng_state.py` now proves PSO and HHO production wrappers do not keep instance-level RNG state and that request-level `pso_config` / `hho_config` values are passed into the core TSP solver path without mutating constructor/default configs. Verification: `rg "self\.rng" optimizer_api\strategies -g "*.py"` returns no active strategy matches; focused wrapper tests pass with 17 tests; broader gate `python -m pytest academic_benchmark\tests uniride_core\tests optimizer_api\tests\test_strategy_rng_state.py optimizer_api\tests\test_all_strategies_smoke.py optimizer_api\tests\test_sota_config_parity.py optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 426 tests; `npm run typecheck` passes.
- Task 47: Promotion evidence gating added. `academic_benchmark.promoted_configs.build_promoted_configs()` and the promotion CLI now accept `min_evidence_runs`, carry `evidence_count` into promoted config entries, and can reject parameter sets backed by too few feasible benchmark rows. Defaults preserve current behavior (`1` evidence row), while release-grade promotion can require multi-seed evidence before writing configs. Local dry-run against SQLite with `--allow-empty-params --min-evidence-runs 2 --dry-run` returned 48 configs without writing. Verification: focused promotion tests pass with 18 tests; `python -m pytest academic_benchmark\tests -q` passes with 194 tests.
- Task 48: VROOM fallback production wrapper delegation pinned. `VROOMFallbackStrategy` remains an API compatibility wrapper while fallback route construction stays in `uniride_core.algorithms.vroom_cvrp_engine.solve_sweep_fallback_routes`; new regression coverage verifies the wrapper passes customer indices, coordinates, disability types, capacities, max route duration, and duration lookup into the core solver. Verification: focused optimizer migration tests pass with 9 tests.
- Task 49: Greedy production wrapper delegation pinned. `GreedyHeuristicStrategy` remains an API compatibility wrapper while route construction stays in `uniride_core.algorithms.string_greedy_routing.solve_string_greedy_routes`; new regression coverage verifies the wrapper passes customer locations, disability map, depot id, capacities, max route duration, and duration lookup into the core solver. Refreshed split verification: `academic_benchmark\tests` passes with 194 tests, `uniride_core\tests` passes with 204 tests, focused optimizer compatibility/migration subset passes with 43 tests, and `npm run typecheck` passes.
- Task 50: Exact permutation TSP wrapper delegation pinned. `PermutationTSPStrategy._solve_tsp_optimal()` remains a thin production boundary over `uniride_core.algorithms.string_exact_tsp.solve_exact_tsp_route`; new regression coverage verifies waypoint/depot forwarding, max permutation limit forwarding, and duration lookup wiring. Verification: focused delegation suite passes with 5 tests.
- Task 51: GA TSP production wrapper dead helper cleanup completed. `GeneticAlgorithmStrategy` no longer owns unused private GA operator helpers (`_initialize_population`, `_evaluate_population`, `_tournament_selection`, `_order_crossover`, `_mutate`, `_evolve`); those behaviors remain in `uniride_core` operators/engines and the production wrapper keeps only request mapping plus `_solve_tsp()` delegation to `solve_ga_tsp()`. New regression coverage prevents the legacy helpers from returning to the wrapper. Verification: RED test failed before cleanup as expected; after cleanup `python -m pytest optimizer_api\tests\test_strategy_no_legacy_algorithm_helpers.py optimizer_api\tests\test_strategy_rng_state.py optimizer_api\tests\test_all_strategies_smoke.py -q` passes with 6 tests, and focused delegation suite passes with 6 tests.
- Task 52: PSO TSP production wrapper dead helper cleanup completed. `PSOStrategy` no longer owns unused private PSO operator helpers (`_shuffle`, `_generate_random_velocity`, `_initialize_swarm`, `_diff_swaps`, `_apply_swaps`, `_combine_velocities`, `_get_difference_swaps`, `_apply_velocity`, `_update_velocity`); those behaviors remain in `uniride_core` operators/engines and the production wrapper keeps request mapping, request-local RNG construction, and `_solve_tsp()` delegation to `solve_pso_tsp()`. Regression coverage prevents the legacy helpers from returning to the wrapper. Verification: RED test failed before cleanup as expected; after cleanup `python -m pytest optimizer_api\tests\test_strategy_no_legacy_algorithm_helpers.py optimizer_api\tests\test_strategy_rng_state.py optimizer_api\tests\test_all_strategies_smoke.py -q` passes with 7 tests, and focused migration suite passes with 7 tests.
- Task 53: GWO TSP production wrapper dead helper cleanup completed. `GreyWolfOptimizerStrategy` no longer owns unused private GWO operator helpers (`_shuffle`, `_initialize_pack`, `_get_difference_vector`, `_apply_swaps`, `_update_position`); those behaviors remain in `uniride_core` operators/engines and the production wrapper keeps request mapping plus `_solve_tsp()` delegation to `solve_gwo_tsp()`. Regression coverage prevents the legacy helpers from returning to the wrapper. Verification: RED test failed before cleanup as expected; after cleanup `python -m pytest optimizer_api\tests\test_strategy_no_legacy_algorithm_helpers.py optimizer_api\tests\test_all_strategies_smoke.py -q` passes with 4 tests, and focused migration suite passes with 8 tests.
- Task 54: TwoOpt production wrapper unused helper cleanup completed. `TwoOptStrategy` no longer owns the unused `_shuffle` helper or imports `shuffle_permutation`; the active initializer remains `_nearest_neighbor_initial()` delegating to `uniride_core.nearest_neighbor_route`, followed by `_solve_tsp()` delegation to `solve_two_opt_tsp()`. Regression coverage prevents the unused helper from returning to the wrapper. Verification: RED test failed before cleanup as expected; after cleanup `python -m pytest optimizer_api\tests\test_strategy_no_legacy_algorithm_helpers.py optimizer_api\tests\test_all_strategies_smoke.py -q` passes with 5 tests, and focused migration suite passes with 9 tests.
- Task 47: TripDirection alias/core-boundary regression coverage strengthened. `optimizer_api/tests/test_trip_direction_alias.py` now verifies the API `TripDirection` canonical enum, backward-compatible `Direction` alias, and core `LinearSplitDecoder` normalization of API enum values without creating a reverse dependency. Verification: `python -m pytest optimizer_api\tests\test_trip_direction_alias.py optimizer_api\tests\test_cvrptw_wrapper_compat.py -q` passes with 4 tests; `rg "optimizer_api" uniride_core` returns no reverse imports; `npm run typecheck` passes.
- Task 48: SOTA base solver Euclidean helper delegation locked down. `uniride_core/tests/test_sota_base_solver_distance.py` now monkeypatches `uniride_core.algorithms.sota_tsp.base_solver.euclidean_distance_2d` and proves `BaseTSPSolver.euclidean_distance()` delegates to the canonical core distance helper. This closes the duplicate SOTA Euclidean helper review row with executable evidence. Verification: focused distance tests pass with 48 tests; broader gate `python -m pytest academic_benchmark\tests uniride_core\tests optimizer_api\tests\test_strategy_rng_state.py optimizer_api\tests\test_trip_direction_alias.py optimizer_api\tests\test_benchmark_run_request_schema.py optimizer_api\tests\test_benchmark_router_problem_loading.py -q` passes with 417 tests; `npm run typecheck` passes.
- Task 49: Repeatable matrix-validation profiles added for academic benchmark readiness. `academic_benchmark.matrix_validation_plan` now supports `--profile quick-real` for the existing curated real-instance validation, `--profile all-imported` for all stored CVRP/CVRPTW rows in SQLite, and `--profile all-imported-multiseed` for the same corpus with two seeded runs. The all-imported profiles use one `time10-scale1000` variant, OR-Tools + PyVRP, and `limit=100000`, while still allowing explicit CLI overrides for problems, problem types, runs, limit, and variants. Verification: `python -m pytest academic_benchmark\tests\test_matrix_validation_plan.py -q` passes with 6 tests; broader `python -m pytest academic_benchmark\tests -q` passes with 190 tests; live single-seed profile run `python -m academic_benchmark.matrix_validation_plan --profile all-imported --run-id-prefix matrix-validation-all-imported-20260604` completed as `matrix-validation-all-imported-20260604-time10-scale1000` with 142 saved rows, `errors=[]`, 142 feasible rows, 0 failed rows, 0 capacity violation rows, 0 time-window violation rows, 75 positive vehicle-gap rows, 75 suppressed distance-gap rows, and 0 unexpected distance gaps when vehicle count is worse than BKS. Live multi-seed run `python -m academic_benchmark.matrix_validation_plan --profile all-imported --run-id-prefix matrix-validation-all-imported-multiseed-20260604 --n-runs 2` completed as `matrix-validation-all-imported-multiseed-20260604-time10-scale1000` with 284 saved rows, `errors=[]`, 284 feasible rows, 0 failed rows, 0 capacity violation rows, 0 time-window violation rows, 150 positive vehicle-gap rows, 150 suppressed distance-gap rows, and 0 unexpected distance gaps when vehicle count is worse than BKS.
- Task 50: SOTA common compatibility shims locked down. `optimizer_api/tests/test_sota_common_compat.py` now checks not only top-level `optimizer_api.strategies.sota_common` exports, but every active SOTA common shim submodule (`acceptance_criteria`, `destroy_operators`, `diversity_controller`, `multi_layer_ls`, `multi_start_initializer`, `penalty_manager`, `repair_operators`). The test asserts public core-owned objects are re-exported by identity from `uniride_core.algorithms.sota_common`, preventing critical SOTA infrastructure from drifting back into `optimizer_api`. Verification: `python -m pytest optimizer_api\tests\test_sota_common_compat.py -q` passes with 2 tests.
- Task 51: VROOM matrix-buffer compatibility hardened in core. `uniride_core.algorithms.vroom_cvrp_engine` now builds VROOM duration/distance matrices through a dedicated helper that scales minutes to seconds, clips negative entries to zero, validates square shape, and returns a C-contiguous `uint32` matrix for pyvroom. This addresses the remaining Windows matrix-buffer compatibility concern without moving any VROOM logic into `optimizer_api`. Verification: `python -m pytest uniride_core\tests\test_vroom_cvrp_engine.py uniride_core\tests\test_holistic_matrix_engine.py -q` passes with 20 tests.
- Task 52: GWO/HHO split production wrappers now have core-delegation regression coverage. `optimizer_api/tests/test_split_strategy_core_delegation.py` monkeypatches the wrapper-imported `solve_gwo_split` and `solve_hho_split` functions and verifies `GWOSplitStrategy.optimize()` / `HHOSplitStrategy.optimize()` pass request-local configs, capacities, waypoints, depot, and matrix-derived context into `uniride_core` solver calls while keeping response construction in `optimizer_api`. Verification: `python -m pytest optimizer_api\tests\test_split_strategy_core_delegation.py -q` passes with 2 tests; focused production wrapper suite `python -m pytest optimizer_api\tests\test_split_strategy_core_delegation.py optimizer_api\tests\test_strategy_rng_state.py optimizer_api\tests\test_sota_common_compat.py optimizer_api\tests\test_all_strategies_smoke.py -q` passes with 9 tests.

Recommended next task: continue production strategy migration only where `optimizer_api/strategies/*` still owns critical algorithm behavior, then run a release-scope optimizer API/frontend runtime gate if this branch is being prepared for merge.

---

## Documents Superseded by This Plan

This single document replaces:
- `00_25.05.2026_opus_implementation_plan.md` (Master Architecture Plan)
- `CVRPLIB_Integration_Plan_2026_05_26_0020.md` (CVRPLIB Execution Spec)

Both documents can be archived or deleted.
