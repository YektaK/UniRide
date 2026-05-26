# UniRide Dual-Engine — Independent Verification & Architectural Blueprint

**Date:** 25.05.2026  
**Role:** Independent Senior Systems Architect / Principal Engineer / Academic Research Lead  
**Task:** Fact-check v5 Code Review findings via structural analysis + Design clean cohabitation architecture  

---

## 1. Fact-Check Matrix

| # | Report Finding | Verdict | Evidence |
|---|---------------|---------|----------|
| 3.1 | **Dual SOTA Implementations** — `sota_tsp/` and `sota_common/` are redundant duplications | **PARTIALLY VERIFIED — NUANCED** | `sota_common/` in active codebase contains **only infrastructure** (destroy/repair ops, acceptance criteria, MultiLayerLS, etc.) — 8 files, no algorithm classes. The full algorithm classes (`E2BSO`, `R2DMA`, `PAOEA` as non-TSP variants) exist **only in `.proposed_changes/`**, not in active code. `sota_tsp/` contains the TSP-native algorithm classes (`E2BSO_TSP`, `R2DMA_TSP`, etc.) that inherit from `BaseTSPSolver`. These are **mathematically distinct**: `sota_common/MultiLayerLS` operates on `List[str]` tours with callable cost functions; `sota_tsp/ls_engine/MultiLayerLS` operates on `List[int]` tours with Numba-accelerated distance matrices. They are NOT simple duplicates — they are different abstraction layers. However, the infrastructure modules (destroy/repair ops, acceptance criteria) ARE duplicated between `sota_common/` and `sota_tsp/` with only minor interface differences. |
| 3.2 | **Broken Import** — `run_sota_benchmark.py` imports nonexistent `academic_benchmark.run_sota_benchmark` | **VERIFIED** | `optimizer_api/run_sota_benchmark.py:3` imports `from academic_benchmark.run_sota_benchmark import main`. No file `academic_benchmark/run_sota_benchmark.py` exists. The `academic_benchmark/` directory has `sota_engine.py` with the actual benchmark logic. This is dead code that crashes at import time. |
| 3.3 | **Hardcoded API Key** in `test_direct.py` | **VERIFIED** | `test_direct.py:6` contains `api_key = "YF7tYODTYg1IWyfvkc0LGFUBadElrLZFnvzqWxPzIJMcZzG6j8VlJQQJ99CDACfhMk5XJ3w3AAAAACOGayNH"` — a live Azure OpenAI key in plaintext. |
| 3.4 | **Hidden Reverse Dependency** — `uniride_core` references `optimizer_api` path | **VERIFIED** | `uniride_core/algorithms/tsplib_parser.py:32-33`: `TSPLIB_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'optimizer_api', 'tests', 'tsplib_data')`. The shared kernel hardcodes a path into the production package. |
| 3.5 | **ESLint Completely Disabled** | **VERIFIED** | `eslint.config.mjs` disables 15+ rules including `no-explicit-any`, `no-unused-vars`, `no-console`, `prefer-const`. All set to `"off"`. |
| 3.6 | **Singleton Config Mutation Risk** | **VERIFIED** | `optimizer_api/strategies/__init__.py` creates module-level singletons: `_ga_strategy = GeneticAlgorithmStrategy()`, etc. The `ebso_strategy.py:49` stores config as `self._config = config or E2BSOTSPConfig(...)`. The `optimize()` method at line 135 creates `e2bso = E2BSO_TSP(self._config)` — this creates a new solver instance per call, which is safe. However, the singleton strategy instances themselves are shared across requests. If any strategy mutates `self._config` during `optimize()`, it affects all subsequent requests. The current SOTA wrappers are safe (they create new solver instances), but the GA/PSO/GWO/HHO strategies in `optimizer_api/strategies/` directly use `self.config` without copying. |
| 3.7 | **Duplicate Hook Files** | **VERIFIED** | `src/hooks/use-mobile.ts` and `src/hooks/use-mobile.tsx` are byte-identical. |
| 3.8 | **ALNS Missing DoE Space** | **VERIFIED** | `academic_benchmark/param_spaces.py` has `SOTA_PARAM_SPACES` with entries for E2BSO, R2DMA, P-AOEA, CGO, RUN — but **no ALNS-TSP entry**. `sota_engine.py:SOTA_ALGO_MAP` includes `"ALNS-TSP": (ALNS_TSP, ALNSConfig)`, but `_get_sota_param_space("ALNS-TSP")` returns `{}`. |
| 3.9 | **Triple Local Search** | **VERIFIED — BUT INTENTIONAL** | Three implementations exist: (1) `optimizer_api/utils/local_search.py` — ABC-based `BaseLocalSearch` hierarchy with `TwoOptLocalSearch`, `ThreeOptLocalSearch`, etc. operating on `List[str]` routes with callable cost functions. Used by GA/PSO/GWO/HHO strategy wrappers. (2) `optimizer_api/strategies/sota_common/multi_layer_ls.py` — `MultiLayerLS` class operating on `List[str]` tours with `CostFunc` callables. Used by `faz0_interactive.py`. (3) `uniride_core/algorithms/sota_tsp/ls_engine.py` — `MultiLayerLS` class operating on `List[int]` tours with Numba-accelerated distance matrices. Used by SOTA TSP solvers. These are **three different abstraction layers** for three different contexts (production strategies, interactive research, pure TSP solvers). Merging them would couple the layers. |
| 3.10 | **Signal Handler Conflict** | **VERIFIED** | `cli_engine.py` and `smart_benchmark.py` both install `signal.SIGINT` handlers. When `smart_benchmark` imports from `cli_engine`, the last handler wins. |
| 3.11 | **Scheduling Logic in Route Handler** | **VERIFIED** | `_calculate_scheduled_times` in `optimization.py` is ~120 lines of complex scheduling logic embedded in the route handler. |
| 3.12 | **ProblemInstance Mixed Concerns** | **VERIFIED** | `uniride_core/models.py:ProblemInstance` has TSPLIB fields (`source`, `file_path`, `edge_weight_type`) and CVRPTW fields (`capacity`, `time_windows`, `depot_index`) in one dataclass. |
| 3.13 | **TSPLIB_OPTIMALS Divergence** | **VERIFIED** | `uniride_core/algorithms/tsplib_parser.py` has ~80 entries. `academic_benchmark/benchmark_utils.py` has 129 entries (superset including ATSP and large instances). |
| — | **Additional: `faz0_interactive.py` is broken** | **VERIFIED (NEW FINDING)** | `optimizer_api/faz0_interactive.py:81-82` imports `E2BSO, E2BSOConfig, E2BSOResult, R2DMA, R2DMAConfig, R2DMAResult, PAOEA, PAOEAConfig, PAOEAResult` from `strategies.sota_common`. But the active `sota_common/__init__.py` does NOT export these classes — it only exports infrastructure modules. These algorithm classes only exist in `.proposed_changes/`. Running `faz0_interactive.py` will crash with `ImportError`. |

---

## 2. The Dual-Engine Cohabitation Blueprint

### 2.1 Current Problem: Unclear Layer Boundaries

The refactoring created `uniride_core` as a shared kernel, but the boundaries are fuzzy:

```
CURRENT (MESSY):
┌─────────────────────────────────────────────────────────────┐
│  uniride_core                                               │
│  ├── models.py (ProblemInstance — TSPLIB + CVRPTW mixed)   │
│  ├── tsplib_parser.py (hardcodes optimizer_api path!)       │
│  ├── algorithms/sota_tsp/ (TSP-native solvers)              │
│  │   ├── base_solver.py (BaseTSPSolver)                     │
│  │   ├── e2bso_tsp.py, r2dma_tsp.py, etc.                   │
│  │   ├── ls_engine.py (int-indexed, Numba)                  │
│  │   ├── destroy_ops.py, repair_ops.py                      │
│  │   └── __init__.py                                        │
│  └── algorithms/distance.py, config.py, etc.                │
├─────────────────────────────────────────────────────────────┤
│  optimizer_api                                               │
│  ├── strategies/sota_common/ (infrastructure ONLY)           │
│  │   ├── multi_layer_ls.py (str-indexed, callable cost)     │
│  │   ├── destroy_operators.py, repair_operators.py          │
│  │   ├── acceptance_criteria.py, penalty_manager.py         │
│  │   └── diversity_controller.py                            │
│  ├── strategies/ (27 algorithm wrappers)                     │
│  │   ├── ebso_strategy.py → imports sota_tsp.E2BSO_TSP     │
│  │   ├── ga_strategy.py, pso_strategy.py, etc.              │
│  │   └── __init__.py (singleton instances)                  │
│  ├── utils/local_search.py (ABC-based, str-indexed)         │
│  ├── faz0_interactive.py (BROKEN — imports missing classes) │
│  └── run_sota_benchmark.py (BROKEN — imports missing module)│
├─────────────────────────────────────────────────────────────┤
│  academic_benchmark                                          │
│  ├── sota_engine.py → imports sota_tsp directly             │
│  ├── cli_engine.py (Numba engine)                           │
│  ├── smart_benchmark.py (unified orchestrator)              │
│  └── param_spaces.py (missing ALNS)                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Target Architecture: Three-Layer Clean Separation

```
TARGET (CLEAN):
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: uniride_core — Pure Mathematical/Model Layer             │
│  (No knowledge of production deployment or research harness)        │
│                                                                      │
│  ├── models/                                                         │
│  │   ├── base.py          — BaseProblem (name, dimension, coords)   │
│  │   ├── tsp.py           — TSPProblem (extends BaseProblem)        │
│  │   ├── cvrptw.py        — CVRPTWProblem (extends BaseProblem)     │
│  │   └── result.py        — OptimizationResult (algorithm-agnostic) │
│  ├── distance/                                                       │
│  │   ├── haversine.py     — Haversine distance                      │
│  │   ├── euclidean.py     — Euclidean/TSPLIB distance types         │
│  │   └── matrix.py        — Distance matrix builders                │
│  ├── solvers/                                                        │
│  │   ├── base.py          — BaseSolver ABC                          │
│  │   ├── local_search/                                             │
│  │   │   ├── base.py      — LS ABC (generic, int-indexed)          │
│  │   │   ├── two_opt.py   — 2-opt implementation                   │
│  │   │   ├── or_opt.py    — Or-opt implementation                  │
│  │   │   ├── three_opt.py — 3-opt-bounded implementation           │
│  │   │   └── swap.py      — Swap implementation                    │
│  │   ├── infrastructure/                                           │
│  │   │   ├── destroy.py   — Destroy operators                      │
│  │   │   ├── repair.py    — Repair operators                       │
│  │   │   ├── acceptance.py — SA, LAHC, RTR                         │
│  │   │   ├── initializer.py — Multi-start initialization            │
│  │   │   ├── diversity.py — Diversity measurement/control          │
│  │   │   └── penalty.py   — Adaptive penalty management            │
│  │   └── sota/                                                       │
│  │       ├── e2bso.py     — E²BSO-TSP                              │
│  │       ├── r2dma.py     — R²DMA-TSP                              │
│  │       ├── paoea.py     — P-AOEA-TSP                             │
│  │       ├── cgo.py       — CGO-TSP                                │
│  │       ├── run.py       — RUN-TSP                                │
│  │       └── alns.py      — ALNS-TSP                               │
│  ├── tsplib/                                                         │
│  │   ├── parser.py        — TSPLIB file parser                     │
│  │   ├── optimals.py      — TSPLIB_OPTIMALS (single source)        │
│  │   └── registry.py      — Problem registry/download              │
│  └── numba/                                                          │
│      ├── accel.py        — Numba JIT kernels                       │
│      └── strategies.py   — Numba-accelerated strategy definitions  │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2a: optimizer_api — Production Adapter Layer                 │
│  (Adapts uniride_core to FastAPI/Supabase/CVRPTW context)           │
│                                                                      │
│  ├── models/schemas.py   — Pydantic DTOs (OptimizationRequest, etc)│
│  ├── routers/            — FastAPI endpoints                        │
│  ├── strategies/         — Production strategy wrappers             │
│  │   ├── base_strategy.py — BaseRoutingStrategy ABC                │
│  │   ├── ga_strategy.py   — Wraps uniride_core solvers + LS        │
│  │   ├── ebso_strategy.py — Wraps E²BSO-TSP for CVRPTW            │
│  │   └── __init__.py      — Strategy registry (factory pattern)    │
│  ├── utils/                                                         │
│  │   ├── clustering.py    — K-Means clustering                     │
│  │   ├── split_decoder.py — Prins DP split decoder                 │
│  │   ├── scheduling.py    — Time window scheduling (extracted)     │
│  │   ├── data_loader.py   — Supabase time matrix loader            │
│  │   └── resource_profiler.py — IE resource analysis               │
│  └── config.py           — Production configuration                 │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2b: academic_benchmark — Research Adapter Layer              │
│  (Adapts uniride_core to CLI/DOE/TSPLIB research context)           │
│                                                                      │
│  ├── engine_core.py      — RunResult, BenchmarkTask, AlgorithmReg  │
│  ├── sota_engine.py      — SOTA benchmark orchestration            │
│  ├── cli_engine.py       — Interactive CLI engine                  │
│  ├── smart_benchmark.py  — Unified cross-engine orchestrator       │
│  ├── param_spaces.py     — DoE parameter spaces (all algorithms)   │
│  ├── benchmark_utils.py  — Gap computation, CSV logging, ETA       │
│  └── tsplib_manager.py   — SQLite TSPLIB cache                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Key Architectural Principles

1. **`uniride_core` is a pure math/model layer**: No imports from `optimizer_api` or `academic_benchmark`. No hardcoded paths to either package. No web framework dependencies.

2. **Infrastructure lives in `uniride_core`**: The destroy/repair operators, acceptance criteria, local search, etc. belong in `uniride_core/solvers/infrastructure/` — NOT duplicated in `optimizer_api/strategies/sota_common/`.

3. **Each engine has its own adapter layer**: `optimizer_api` adapts core to web/Supabase/CVRPTW. `academic_benchmark` adapts core to CLI/DOE/TSPLIB. Neither adapter should contain algorithm logic — only orchestration and I/O.

4. **Data models use inheritance, not monolithic dataclasses**: `BaseProblem` → `TSPProblem` / `CVRPTWProblem` keeps concerns separated while sharing common fields.

5. **Strategy registry uses factory pattern, not singletons**: Thread-safe per-request instantiation prevents config mutation races.

---

## 3. Safe Refactoring Recommendations

### 3.1 Fix `uniride_core` Reverse Dependency (Critical — No Breaking Changes)

**Before:**
```python
# uniride_core/algorithms/tsplib_parser.py
TSPLIB_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..',
                                'optimizer_api', 'tests', 'tsplib_data')
```

**After:**
```python
# uniride_core/algorithms/tsplib_parser.py
import os

TSPLIB_DATA_DIR = os.environ.get(
    "TSPLIB_DATA_DIR",
    os.path.join(os.path.dirname(__file__), '..', '..', 'tsplib_data')
)
```

**Migration path:** Set `TSPLIB_DATA_DIR` env var in `optimizer_api/.env` to point to its local `tests/tsplib_data/`. The academic engine sets it to its own `tsplib_data/`. `uniride_core` becomes path-agnostic.

### 3.2 Separate `ProblemInstance` via Inheritance (Non-Breaking)

**Before:**
```python
# uniride_core/models.py
@dataclass
class ProblemInstance:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    # TSPLIB fields
    source: str = "tsplib"
    file_path: Optional[str] = None
    edge_weight_type: str = "EUC_2D"
    # CVRPTW fields
    capacity: Optional[int] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
    depot_index: int = 0
```

**After:**
```python
# uniride_core/models/base.py
@dataclass
class BaseProblem:
    """Pure mathematical problem — no deployment-specific fields."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[float] = None

# uniride_core/models/tsp.py
@dataclass
class TSPProblem(BaseProblem):
    """TSPLIB research problem."""
    edge_weight_type: str = "EUC_2D"
    category: str = "small"  # small/medium/large for benchmark selection

# uniride_core/models/cvrptw.py
@dataclass
class CVRPTWProblem(BaseProblem):
    """Production CVRPTW problem."""
    capacity: int = 0
    time_windows: List[Tuple[int, int]] = field(default_factory=list)
    depot_index: int = 0
    num_vehicles: int = 1

# uniride_core/models/__init__.py
# Backward compatibility alias
ProblemInstance = BaseProblem  # Deprecated, use TSPProblem or CVRPTWProblem
```

**Migration path:** Keep `ProblemInstance` as a deprecated alias for 2-3 sprints. Update `academic_benchmark` to use `TSPProblem` and `optimizer_api` to use `CVRPTWProblem`. Remove alias in a future version.

### 3.3 Consolidate Infrastructure into `uniride_core` (Non-Breaking)

Move the shared infrastructure from `optimizer_api/strategies/sota_common/` into `uniride_core/solvers/infrastructure/`:

```
uniride_core/solvers/infrastructure/
├── __init__.py
├── destroy.py       # From sota_common/destroy_operators.py
├── repair.py        # From sota_common/repair_operators.py
├── acceptance.py    # From sota_common/acceptance_criteria.py
├── initializer.py   # From sota_common/multi_start_initializer.py
├── diversity.py     # From sota_common/diversity_controller.py
└── penalty.py       # From sota_common/penalty_manager.py
```

Then make `optimizer_api/strategies/sota_common/` a thin re-export layer for backward compatibility:

```python
# optimizer_api/strategies/sota_common/__init__.py
"""DEPRECATED: Import from uniride_core.solvers.infrastructure instead."""
import warnings
warnings.warn("sota_common is deprecated. Import from uniride_core.solvers.infrastructure", 
              DeprecationWarning, stacklevel=2)

from uniride_core.solvers.infrastructure import (
    MultiStartInitializer,
    PenaltyManager, PenaltyState,
    SimulatedAnnealing, LateAcceptanceHC, RecordToRecordTravel,
    RandomRemoval, WorstRemoval, ShawRemoval, RelatedRemoval,
    GreedyInsertion, Regret2Insertion, Regret3Insertion,
    DiversityController, DiversityState,
)
```

**Migration path:** The re-export layer ensures nothing breaks immediately. Update imports incrementally. Remove `sota_common/` after 2-3 sprints.

### 3.4 Fix Strategy Registry — Factory Pattern (Non-Breaking)

**Before:**
```python
# optimizer_api/strategies/__init__.py
_ga_strategy = GeneticAlgorithmStrategy()
STRATEGY_REGISTRY = {"genetic_algorithm": _ga_strategy, ...}
```

**After:**
```python
# optimizer_api/strategies/__init__.py
import threading
from typing import Dict, Optional, Type

_strategy_classes: Dict[str, Type[BaseRoutingStrategy]] = {
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "ga": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    # ... etc
}

_thread_local = threading.local()

def get_strategy(name: str) -> Optional[BaseRoutingStrategy]:
    """Get or create a thread-local strategy instance."""
    if not hasattr(_thread_local, 'cache'):
        _thread_local.cache = {}
    if name not in _thread_local.cache:
        cls = _strategy_classes.get(name)
        _thread_local.cache[name] = cls() if cls else None
    return _thread_local.cache[name]

# Backward compatibility
STRATEGY_REGISTRY = _strategy_classes  # Dict-compatible for existing code
```

**Migration path:** `STRATEGY_REGISTRY` remains a dict, so existing code using `STRATEGY_REGISTRY[name]` still works. New code uses `get_strategy(name)` for thread safety.

### 3.5 Fix `run_sota_benchmark.py` (Non-Breaking)

**Before:**
```python
from academic_benchmark.run_sota_benchmark import main  # DOES NOT EXIST
```

**After:**
```python
"""
SOTA Benchmark Runner — delegates to academic_benchmark.sota_engine.
"""
import sys
from academic_benchmark.sota_engine import run_engine_default

if __name__ == "__main__":
    run_engine_default()
```

### 3.6 Fix `faz0_interactive.py` Broken Imports (Non-Breaking)

**Option A (Recommended):** Delete `faz0_interactive.py`. It's a legacy research script that's been superseded by `academic_benchmark/smart_benchmark.py`. The fact that it already has broken imports confirms it's not being maintained.

**Option B (If needed for research):** Update imports to use `uniride_core` directly:

```python
# faz0_interactive.py — fix imports
from uniride_core.algorithms.sota_tsp import (
    E2BSO_TSP, E2BSOTSPConfig,
    R2DMA_TSP, R2DMATSPConfig,
    PAOEA_TSP, PAOEAConfig,
)
from uniride_core.algorithms.sota_tsp.ls_engine import MultiLayerLS
from uniride_core.algorithms.sota_tsp.destroy_ops import (
    RandomRemoval, WorstRemoval, ShawRemoval, RelatedRemoval,
)
from uniride_core.algorithms.sota_tsp.repair_ops import (
    GreedyInsertion, Regret2Insertion, Regret3Insertion,
)
# ... etc
```

### 3.7 Unify `TSPLIB_OPTIMALS` (Non-Breaking)

Move the comprehensive dictionary into `uniride_core` and have `academic_benchmark` import from there:

```python
# uniride_core/tsplib/optimals.py
"""Single source of truth for TSPLIB known optimal values."""
TSPLIB_OPTIMALS: Dict[str, int] = {
    # 129 entries from academic_benchmark/benchmark_utils.py
    "berlin52": 7542,
    # ... all 129 entries ...
}

# academic_benchmark/benchmark_utils.py — replace local dict with:
from uniride_core.tsplib.optimals import TSPLIB_OPTIMALS
```

### 3.8 Add ALNS DoE Parameter Space (Non-Breaking)

```python
# academic_benchmark/param_spaces.py — add to SOTA_PARAM_SPACES:
"ALNS-TSP": {
    "max_iterations":       {"type": "int",   "doe": [500, 1000, 2000],     "optuna": (200, 3000)},
    "max_no_improve":       {"type": "int",   "doe": [50, 100, 200],        "optuna": (20, 300)},
    "remove_ratio":         {"type": "float", "doe": [0.10, 0.20, 0.30],     "optuna": (0.05, 0.40)},
    "segment_length":       {"type": "int",   "doe": [3, 5, 8],             "optuna": (2, 12)},
    "weight_update_factor": {"type": "float", "doe": [0.1, 0.3, 0.5],       "optuna": (0.05, 0.7)},
    "noise_scale":          {"type": "float", "doe": [0.05, 0.10, 0.20],    "optuna": (0.01, 0.30)},
    "sa_initial_temp":      {"type": "float", "doe": [100.0, 500.0, 1000.0], "optuna": (50.0, 2000.0)},
    "sa_cooling_rate":      {"type": "float", "doe": [0.95, 0.98, 0.99],    "optuna": (0.90, 0.995)},
    "time_limit":           {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
},
```

---

## 4. Summary Scorecard (Independent Assessment)

| Category | v5 Report Score | Independent Score | Notes |
|----------|----------------|-------------------|-------|
| Post-Refactoring Cleanliness | 7/10 | 7/10 | Agreed. Dual SOTA concern is nuanced (infrastructure IS duplicated, algorithms are distinct layers) |
| Architecture & Modularity | 7.5/10 | 7/10 | Slightly lower due to `faz0_interactive.py` being broken (new finding) and `sota_common/` still existing |
| Code Quality | 6/10 | 6/10 | Agreed. ESLint disabled is the primary blocker |
| Type Safety | 6.5/10 | 6.5/10 | Agreed |
| Performance | 8/10 | 8/10 | Agreed. Numba JIT, split decoder, KNN masks are excellent |
| Security | 5/10 | 4/10 | Lower due to hardcoded API key being worse than reported — it's a live production key |
| Test Coverage | 5/10 | 5/10 | Agreed |
| DOE Rigor | 6/10 | 6/10 | Agreed. ALNS gap confirmed |
| Academic Rigor | 7/10 | 7/10 | Agreed |
| Production Readiness | 6.5/10 | 6/10 | Lower due to `faz0_interactive.py` broken import and `run_sota_benchmark.py` dead code |
| **Overall** | **6.8/10** | **6.5/10** | The report is accurate. Two additional broken imports found. The dual SOTA finding is partially a false alarm (algorithms are distinct layers) but the infrastructure duplication is real. |

---

## 5. Priority Action Plan

### Immediate (This Week)
1. **Rotate the Azure OpenAI API key** — it's compromised in the repository
2. **Delete or fix `test_direct.py`** — use environment variables
3. **Delete `optimizer_api/run_sota_benchmark.py`** — it's dead code that crashes
4. **Delete `optimizer_api/faz0_interactive.py`** — it has broken imports, superseded by `academic_benchmark/`
5. **Fix `TSPLIB_DATA_DIR`** in `uniride_core` — use env var with fallback

### Short-Term (Next 2-4 Weeks)
6. **Add ALNS DoE parameter space** — 2 hours of work, fills a real research gap
7. **Re-enable ESLint rules in warn mode** — start catching issues without breaking builds
8. **Delete duplicate `use-mobile.ts`** — 5 minutes
9. **Unify `TSPLIB_OPTIMALS`** into `uniride_core` — single source of truth

### Medium-Term (Next 1-2 Months)
10. **Refactor `ProblemInstance` into inheritance hierarchy** — `BaseProblem` → `TSPProblem` / `CVRPTWProblem`
11. **Consolidate infrastructure** — move `sota_common/` modules into `uniride_core/solvers/infrastructure/`
12. **Refactor strategy registry** to factory pattern with thread-local instances
13. **Extract scheduling logic** from `optimization.py` into `utils/scheduling.py`

### Long-Term (Next 3-6 Months)
14. **Full `uniride_core` purification** — remove all deployment-specific knowledge from core
15. **Shared benchmark infrastructure** — unify production and academic benchmark execution
16. **Statistical rigor in DoE** — confidence intervals, hypothesis testing, sensitivity analysis
