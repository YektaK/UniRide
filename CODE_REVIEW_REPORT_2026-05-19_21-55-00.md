# Comprehensive Code Review Report
## UniRide Optimization Codebase

**Report Generated**: 2026-05-19
**Reviewer**: Senior Software Engineer & Solutions Architect
**Scope**: `optimizer_api/` + `academic_benchmark/` (excluding `bildiri2026/`, `legacy/`, `old/`, `paper_prompts/`, `numba_results/`, `sota_results/`, `cache/`)

> **Update note (2026-05-19 evening):** This report supersedes the earlier `CODE_REVIEW_REPORT_2026-05-19_21-55-00.md`. Key corrections from follow-up review:
> - SOTA engine calls `academic_benchmark/sota_tsp/`, NOT `optimizer_api/strategies/sota_common/`
> - Two completely separate SOTA implementations exist (v1.0.0 vs v3.0.0, string vs int node IDs)
> - bildiri2026 exclusion requires 4 targeted fixes in `academic_benchmark/` (all proven safe for bildiri2026's own workflow)
> - See `CODE_REVIEW_AND_FIX_REPORT_2026-05-19.md` for the consolidated fix roadmap

---

## 1. Executive Summary

| Dimension | Assessment |
|-----------|------------|
| **Architecture** | Well-structured with clear separation between API (`optimizer_api`) and research (`academic_benchmark`). Strategy pattern implemented correctly. Two independent benchmark engines (Numba, SOTA) share a unified orchestrator (`smart_benchmark.py`). |
| **Code Quality** | Moderate-High. Academic research code with good algorithmic foundations but technical debt from rapid iteration. Significant duplication issues. |
| **Performance** | Strong. Numba JIT acceleration, distance matrix caching, SQLite pre-computation. |
| **Robustness** | Moderate. Error handling present but inconsistent. Global mutable state and bildiri2026 coupling require attention before exclusion. |
| **Documentation** | Good docstrings in core algorithms. Academic comments in research code. Missing parameter documentation. |
| **Type Safety** | Partial. Pydantic schemas for API, internal algorithms lack comprehensive type hints. |

**Overall Maturity**: Pre-production research prototype. Core algorithms are sound. bildiri2026 exclusion requires 4 targeted fixes. See §4 and the companion fix report.

---

## 2. Architecture & Design Review

### 2.1 High-Level Architecture (Corrected)

```
optimizer_api/                    academic_benchmark/
├── main.py                       ├── smart_benchmark.py     ← Unified orchestrator
├── benchmark_runner.py           ├── engine_core.py         ← ProblemInstance, RunResult,
├── models/schemas.py             │                           AlgorithmRegistry, BenchmarkConfig
├── strategies/                   ├── benchmark_utils.py    ← TSPLIB_OPTIMALS (COPY 1), ETATracker,
│   ├── base_strategy.py          │                           ProblemSelector
│   ├── ga_strategy.py            ├── master_numba_engine.py
│   ├── *_split_strategy.py       │   ├── bildiri2026/core/  ← B-PSO, B-GA (* requires bildiri2026)
│   └── sota_common/              │   └── optimizer_api/utils/local_search_numba.py
│       ├── e2bso.py              ├── master_sota_engine.py
│       ├── r2dma.py              │   └── academic_benchmark/sota_tsp/  ← E2BSO_TSP, R2DMA_TSP, etc.
│       └── paoea.py                  ├── base_solver.py
└── utils/                            ├── ls_engine.py       ← Imports numba_accel from bildiri2026
    ├── local_search_numba.py          ├── repair_ops.py
    ├── tsplib_parser.py           ├── tsplib_manager.py    ← SQLite DB cache
    └── data_loader.py             ├── param_db.py          ← Persistent parameter storage
                                    └── bildiri2026/         ← STANDALONE (own workflow, excluded)
```

### 2.2 Corrected SOTA Call Chain

**smart_benchmark.py does NOT call `optimizer_api/strategies/sota_common/`.**

Two completely separate SOTA implementations exist:

| | `optimizer_api/strategies/sota_common/` | `academic_benchmark/sota_tsp/` |
|---|---|---|
| Version | 3.0.0 (FAZ 0 infrastructure) | 1.0.0 (FAZ consolidated) |
| Used by | `optimizer_api/` (API-facing) | `smart_benchmark.py` (benchmarking) |
| Node IDs | `List[str]` (e.g., `"c0"`, `"c1"`) | `List[int]` (e.g., `0`, `1`) |
| Classes | `E2BSO`, `R2DMA`, `PAOEA` | `E2BSO_TSP`, `R2DMA_TSP`, `PAOEA_TSP` |
| Infrastructure | Rich modular: `MultiStartInitializer`, `PenaltyManager`, `DiversityController`, `Destroy/RepairOperators`, `AcceptanceCriteria` | Standalone: `ls_engine.py`, `repair_ops.py`, `destroy_ops.py` |

**SOTA execution paths from `smart_benchmark.py`:**

*Path 1 — Unified benchmark (AlgorithmRegistry):*
```
smart_benchmark.py:422
  └── AlgorithmRegistry.get_executor(task.algorithm)
        └── _make_sota_executor()              master_sota_engine.py:1804
              └── _make_solver()               master_sota_engine.py:582
                    └── from sota_tsp import (E2BSO_TSP, R2DMA_TSP, ...)  ← academic_benchmark/sota_tsp/
```

*Path 2 — Direct engine tuning:*
```
smart_benchmark.py:406-414
  └── _run_sota_optuna_tuning() OR _sota_tune()
        └── _run_engine_tuning()               master_sota_engine.py:931
              └── _evaluate_sota_combo() / _run_solver_task()
                    └── _make_solver()         master_sota_engine.py:582
                          └── from sota_tsp import (E2BSO_TSP, ...)       ← academic_benchmark/sota_tsp/
```

### 2.3 Design Pattern Analysis

**Strategy Pattern (Excellent)**
- `BaseRoutingStrategy` abstract class with `optimize()` contract
- `STRATEGY_REGISTRY` dict mapping names → instances
- Support for aliases
- Singleton instances for efficiency

**Factory Pattern (Good)**
- `get_local_search()` factory in `local_search_numba.py`
- `get_strategy()` utility for dynamic lookup

**Singleton Pattern (Adequate)**
- `SingletonMeta` with double-checked locking is thread-safe
- `DataLoader` correctly uses it

### 2.4 Scalability Assessment

| Component | Scalability | Notes |
|-----------|-------------|-------|
| API Layer | Good | Stateless request handling |
| Strategy Execution | Good | Strategy instances are stateless, support parallel execution |
| Distance Matrix Cache | **Concern** | `_DIST_MATRIX_CACHE` in `local_search_numba.py` — global mutable state, not thread-safe |
| TSPLIB DB Cache | Good | SQLite WAL mode, per-problem blob storage |

---

## 3. Deep-Dive Analysis (File/Module Level)

### 3.1 Critical Issues

#### Issue #1: Duplicate `TSPResult` Dataclasses — Three Copies

| Location | File |
|----------|------|
| `academic_benchmark/sota_tsp/base_solver.py:21-29` | Fields: algorithm, tour, tour_length, elapsed_ms, iterations, params, history, seed |
| `academic_benchmark/bildiri2026/core/base_solver.py` | Identical fields |
| `optimizer_api/strategies/sota_common/e2bso.py` (and r2dma, paoea) | Likely identical |

The fields are identical. Importing the wrong one can cause subtle bugs when a function expects one namespace's type. The SOTA engine (`sota_tsp/`) and bildiri2026 both use `List[int]` tours, while `optimizer_api/strategies/sota_common/` uses `List[str]`.

**Fix:** Move `TSPResult` to `engine_core.py` alongside `RunResult`. `sota_tsp/base_solver.py` imports from `engine_core` instead of defining its own. bildiri2026 is left unchanged (out of scope).

#### Issue #2: Duplicate `euclidean_distance` in `data_loader.py:229-247`

```python
# Lines 229-235
def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    import math
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

# Lines 241-247 — DUPLICATE (second shadows first)
def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    import math
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
```

Also, `from utils.haversine import haversine_distance, estimate_travel_time` at line 238 is imported but never used in this file.

#### Issue #3: Global Mutable Cache in `local_search_numba.py:72`

```python
_DIST_MATRIX_CACHE: Dict[int, np.ndarray] = {}
```

This is shared across all concurrent benchmark tasks. When `ProcessPoolExecutor` is used with `workers=1`, or within the main process before forking, concurrent read/write access has no locking. This can cause `KeyError` or corrupt entries. See §4, Issue C-3 for the fix.

#### Issue #4: Hardcoded Iteration Limits in `HybridLocalSearch`

```python
# local_search_numba.py — iteration_limits dict buried in method body
iteration_limits = {
    LocalSearchType.SWAP: 100,
    LocalSearchType.TWO_OPT: 80,
    LocalSearchType.OR_OPT: 60,
    LocalSearchType.CROSS_EXCHANGE: 40,
    LocalSearchType.THREE_OPT: 25,
    LocalSearchType.TIME_WINDOW_AWARE: 50,
}
```

Should be constructor parameters with sensible defaults.

### 3.2 Major Issues

#### Issue #5: Code Duplication in LocalSearch Classes

Five classes (`TwoOptLocalSearch`, `ThreeOptLocalSearch`, `OrOptLocalSearch`, `SwapLocalSearch`, `HybridLocalSearch`) all duplicate identical `_prepare_numba_inputs`, `_indices_to_route`, and `improve` method implementations.

**Refactoring opportunity:** Extract to a base class `NumbaLocalSearchBase` with template method pattern. See §4.2 for before/after snippet.

#### Issue #6: Missing Input Validation in `OptimizationRequest`

```python
# models/schemas.py
class OptimizationRequest(BaseModel):
    algorithm: str = "ga_split"
    students: List[StudentNode]
    depot: LocationNode
    # No validation for:
    # - Empty students list
    # - Duplicate student IDs
    # - Negative max_travel_time
    # - Invalid clustering_algorithm name
```

Validation is scattered across strategies rather than centralized in the schema.

#### Issue #7: Numba Cache Directory Without Cleanup

```python
_cache_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".numba_cache")
try:
    os.makedirs(_cache_base, exist_ok=True)
except (OSError, PermissionError):
    _cache_base = os.path.join(os.path.expanduser("~"), ".UniRide_numba_cache")
    os.makedirs(_cache_base, exist_ok=True)
```

No cleanup policy. Large numba cache could consume significant disk space. On Windows, `~` expansion may need `os.path.expanduser`.

### 3.3 Moderate Issues

#### Issue #8: Inconsistent Error Handling in API Endpoints

`main.py:437-440` uses broad `except Exception` with `traceback.print_exc()` (writes to stdout, not logger). Other endpoints use specific validation. This inconsistency makes production debugging difficult.

#### Issue #9: Magic Numbers Without Constants

```python
# main.py:236
target_minutes = 9 * 60  # Why 9 AM?
# main.py:271
start_minutes = 14 * 60  # Why 2 PM?
# ga_strategy.py:54
"max_no_improvement": 50,  # bildiri2026: 100; keep 50 for routing responsiveness
```

These should be named constants with clear documentation.

#### Issue #10: Two Problem Types Instead of One

| Engine | Problem Type | Location |
|--------|-------------|----------|
| Numba | `DOEProblem` | master_numba_engine.py:256 |
| SOTA | `TSPProblem` | master_sota_engine.py:273 |
| Unified | `ProblemInstance` | engine_core.py:6 (exists but unused as canonical) |

`smart_benchmark.py` converts between them at lines 374-401. Standardizing on `ProblemInstance` would eliminate this friction.

#### Issue #11: AlgorithmRegistry Execution Disconnect

`master_sota_engine.py:1804-1843` registers SOTA executors with `AlgorithmRegistry` via `_make_sota_executor()`. These are used by the **unified benchmark path** in `smart_benchmark.py:422`. However, `_run_engine_default()` and `_run_engine_tuning()` in `master_sota_engine.py` do NOT use the registry — they call `_run_solver_task` and `_evaluate_sota_combo` directly. The registry warmup at `smart_benchmark.py:229` only benefits the unified path.

#### Issue #12: SOTA Parameter Space Duplicated Across Functions

- `master_sota_engine.py:520-575` — `_build_sota_parameter_space()` (DoE tuning)
- `master_sota_engine.py:1046-1089` — `_build_sota_optuna_space()` (Bayesian tuning)
- `master_numba_engine.py:465-530` — `_build_numba_parameter_space()` (Numba tuning)

Adding a new E²BSO parameter requires updating both SOTA functions and the Numba one.

#### Issue #13: GEO/ATT Distance Matrix Fallback Bug in Numba Engine

Comment at `master_numba_engine.py:639-641` explicitly warns:
> "This is CRITICAL: run_single_test falls back to create_np_distance_matrix which only does EUC_2D, producing wrong distances for GEO/ATT/etc problems"

When `_dm_from_cache()` returns `None` (DB miss), the code falls back to Euclidean distance regardless of the problem's actual `EDGE_WEIGHT_TYPE`.

---

## 4. bildiri2026 Exclusion Impact

> **CRITICAL for exclusion planning.** See companion document `CODE_REVIEW_AND_FIX_REPORT_2026-05-19.md` for full fix details.

### 4.1 What bildiri2026 Provides

| Dependency | File | Purpose | Impact if Excluded |
|---|---|---|---|
| `numba_accel` module | `sota_tsp/ls_engine.py:24-36` | Numba JIT kernels for 2-opt/3-opt/Or-opt/Swap | SOTA local search falls back to pure Python |
| Numba detection | `master_numba_engine.py:139-148` | Sets `_NUMBA_AVAILABLE` | Always `False` → Numba kernels bypassed |
| `PSOOptimizer`, `GAOptimizer` | `master_numba_engine.py:812-815` | B-PSO and B-GA execution | `ModuleNotFoundError` crash |
| Numba detection | `master_sota_engine.py:448-455` | Sets `_NUMBA_AVAILABLE` | Always `False` → Numba kernels bypassed |

### 4.2 bildiri2026 Own Workflow is Self-Contained

 bildiri2026's entry points all use `sys.path.insert(0, SCRIPT_DIR)` to self-resolve imports from its own `core/` directory. They import from:
- `core/__init__.py`
- `benchmarks/tsplib_benchmark.py`
- `config_manager.py`
- `data_manager.py`

** bildiri2026 does NOT import from any file in `academic_benchmark/` that lies outside its own folder.** No proposed fix touches any file bildiri2026 relies on.

### 4.3 Required Fixes (academic_benchmark/ only — bildiri2026 untouched)

All four fixes add new code (`import numba` check) before the bildiri2026 path. Nothing is removed or modified that bildiri2026 depends on.

| Fix | File | What Changes |
|-----|------|-------------|
| **C-1** | `master_numba_engine.py:139-148` | `import numba` check before bildiri2026 path in `_detect_numba()` |
| **C-2** | `master_numba_engine.py:854-869` | `BILDIRI_STRATEGIES` becomes a function returning `[]` when bildiri2026 unavailable; guard in routing |
| **C-3** | `master_sota_engine.py:448-455` | `import numba` check before bildiri2026 path in `_detect_numba()` |
| **C-4** | `sota_tsp/ls_engine.py:24-36` | `import numba` check before bildiri2026 path for Numba detection |

See companion report for exact code snippets.

---

## 5. Concrete Refactoring Recommendations

### 5.1 Critical Fix: Duplicate `euclidean_distance` in `data_loader.py`

**BEFORE:**
```python
# Lines 229-235
def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    import math
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

# Line 238 — dead import
from utils.haversine import haversine_distance, estimate_travel_time

# Lines 241-247 — DUPLICATE
def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    import math
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
```

**AFTER:**
```python
def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate euclidean (L2) distance between two 2D points."""
    import math
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

# Remove the duplicate definition and the dead haversine import
```

### 5.2 Refactor: Extract Base Class for Numba Local Search

**BEFORE (code duplication across 5 classes):**
```python
class TwoOptLocalSearch(BaseLocalSearch):
    def _prepare_numba_inputs(self, route, duration_func):
        self._index_map, self._dist_matrix, self._unique_locs = _build_or_get_dist_matrix(route, duration_func)
        return np.array([self._index_map[loc] for loc in route], dtype=np.int64), self._dist_matrix

    def _indices_to_route(self, route_indices, original_route):
        return [self._unique_locs[idx] for idx in route_indices]

    def improve(self, route, duration_func):
        # ... nearly identical except which numba kernel is called
```

**AFTER (template method pattern):**
```python
class NumbaLocalSearchBase(BaseLocalSearch):
    def __init__(self, max_iterations: int = 1000, first_improvement: bool = False):
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self._index_map = None
        self._dist_matrix = None
        self._unique_locs = None

    def _prepare_numba_inputs(self, route, duration_func):
        self._index_map, self._dist_matrix, self._unique_locs = _build_or_get_dist_matrix(route, duration_func)
        route_indices = np.array([self._index_map[loc] for loc in route], dtype=np.int64)
        return route_indices, self._dist_matrix

    def _indices_to_route(self, route_indices, original_route):
        return [self._unique_locs[idx] for idx in route_indices]

    @abstractmethod
    def _numba_improve(self, route, dist_matrix):
        pass

    def improve(self, route, duration_func):
        if len(route) < 3:
            return route, duration_func(route)
        route_indices, dist_matrix = self._prepare_numba_inputs(route, duration_func)
        improved_indices, _ = self._numba_improve(route_indices, dist_matrix)
        return self._indices_to_route(improved_indices, route), duration_func(...)

class TwoOptLocalSearch(NumbaLocalSearchBase):
    def _numba_improve(self, route, dist_matrix):
        return _two_opt_improve_numba(route, dist_matrix, self.max_iterations, self.first_improvement)
```

### 5.3 Refactor: Thread-Safe Distance Matrix Cache

**BEFORE (`local_search_numba.py:72`):**
```python
_DIST_MATRIX_CACHE: Dict[int, np.ndarray] = {}
```

**AFTER:**
```python
import threading

_DIST_MATRIX_CACHE: Dict[int, np.ndarray] = {}
_DIST_MATRIX_CACHE_LOCK = threading.Lock()

def _get_cached_matrix(key: int):
    with _DIST_MATRIX_CACHE_LOCK:
        return _DIST_MATRIX_CACHE.get(key)

def _set_cached_matrix(key: int, value: np.ndarray) -> None:
    with _DIST_MATRIX_CACHE_LOCK:
        _DIST_MATRIX_CACHE[key] = value
```

### 5.4 Refactor: Configurable Iteration Limits

**BEFORE:**
```python
iteration_limits = {
    LocalSearchType.SWAP: 100,
    LocalSearchType.TWO_OPT: 80,
    # ...
}
```

**AFTER:**
```python
@dataclass
class HybridLocalSearchConfig:
    swap_max_iterations: int = 100
    two_opt_max_iterations: int = 80
    or_opt_max_iterations: int = 60
    cross_exchange_max_iterations: int = 40
    three_opt_max_iterations: int = 25
    time_window_aware_max_iterations: int = 50

class HybridLocalSearch(BaseLocalSearch):
    def __init__(self, config: Optional[HybridLocalSearchConfig] = None, ...):
        self._config = config or HybridLocalSearchConfig()
```

### 5.5 Refactor: Centralized Validation in Schema

**BEFORE:**
```python
class OptimizationRequest(BaseModel):
    algorithm: str = "ga_split"
    students: List[StudentNode]
    depot: LocationNode
    max_travel_time: int = 120
    # No validation
```

**AFTER:**
```python
class OptimizationRequest(BaseModel):
    algorithm: str = "ga_split"
    students: List[StudentNode]
    depot: LocationNode
    max_travel_time: int = 120

    @field_validator('max_travel_time')
    @classmethod
    def validate_max_travel_time(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('max_travel_time must be positive')
        return v

    @field_validator('students')
    @classmethod
    def validate_students(cls, v: List[StudentNode]) -> List[StudentNode]:
        if not v:
            return v
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate student IDs detected')
        return v

    @field_validator('clustering_algorithm')
    @classmethod
    def validate_clustering_algorithm(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valid = {'sweep', 'kmeans', 'k_medoids', 'clarke_wright', 'fuzzy_cmeans'}
        if v.lower() not in valid:
            raise ValueError(f'clustering_algorithm must be one of {valid}')
        return v.lower()
```

---

## 6. Quick Wins & Long-Term Roadmap

### 6.1 Quick Wins (High Impact, Low Effort)

| Priority | Issue | Fix | Effort | Impact |
|----------|-------|-----|--------|--------|
| **P1** | Duplicate `euclidean_distance` in `data_loader.py` | Remove duplicate + dead import | 5 min | Prevents shadowing bugs |
| **P1** | `traceback.print_exc()` in `main.py:439` | Replace with `logger.error` | 2 min | Better production logging |
| **P2** | `sota_tsp/__init__.py:16-17` duplicate import | Remove one line | 1 min | Code cleanliness |
| **P2** | Magic numbers for time (9*60, 14*60) | Named constants | 5 min | Self-documenting code |
| **P3** | bildiri2026 exclusion guard missing | See §4, C-2 | 5 min | Prevents crash |

### 6.2 Medium-Term Refactoring

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| **P1** | Extract `NumbaLocalSearchBase` to eliminate code duplication | 2-3 hrs | Maintainability |
| **P1** | Thread-safe `_DIST_MATRIX_CACHE` wrapper | 1 hr | Production safety |
| **P2** | Make `HybridLocalSearch.iteration_limits` configurable | 1 hr | Flexibility |
| **P2** | Consolidate `TSPResult` into `engine_core.py` | 30 min | Reduced confusion |
| **P3** | Route engine execution through `AlgorithmRegistry` | 30 min | Eliminates dual execution paths |

### 6.3 Long-Term Roadmap

| Priority | Initiative | Effort | Strategic Value |
|----------|------------|--------|-----------------|
| **P1** | bildiri2026 exclusion fixes (C-1 through C-4) | 1 hr | Enables bildiri2026 exclusion |
| **P2** | Standardize on `ProblemInstance` across both engines | 45 min | Eliminates type conversion friction |
| **P2** | Consolidate SOTA parameter spaces into `param_spaces.py` | 20 min | Single update point |
| **P2** | Fix GEO/ATT fallback to use correct distance computation | 30 min | Accurate gap calculations |
| **P2** | Add comprehensive input validation using Pydantic validators | 4-6 hrs | Production hardening |
| **P3** | Decide: keep two parallel SOTA implementations or unify via integer-index adapter | Arhitectural | Reduce duplication |
| **P3** | Add structured logging (JSON) throughout | 4 hrs | Observability |
| **P3** | Implement graceful degradation when Numba unavailable | 2-3 hrs | Robustness |

---

## Appendix: File-Specific Findings

### `optimizer_api/main.py`
- **Good**: Comprehensive API documentation, CORS configuration via env vars
- **Good**: Background thread management for benchmarks
- **Issue**: `traceback.print_exc()` instead of logger at line 439
- **Issue**: Magic numbers for time (9*60, 14*60) not named constants

### `optimizer_api/benchmark_runner.py`
- **Good**: Clean separation of concerns, dataclasses for type safety
- **Good**: TSPLIB-native distance calculation
- **Good**: State manager callbacks for progress tracking

### `optimizer_api/models/schemas.py`
- **Good**: Comprehensive Pydantic models with clear field documentation
- **Good**: Enum usage for Direction, DisabilityType
- **Issue**: Missing validators for edge cases (empty students, duplicate IDs, negative max_travel_time)
- **Issue**: `StudentNode.disability_type: str` should be `DisabilityType` enum

### `optimizer_api/strategies/__init__.py`
- **Excellent**: Clean strategy registry with alias support
- **Excellent**: Optional dependency handling for PyVRP and VROOM
- **Good**: `get_recommended_strategy()` based on problem size

### `optimizer_api/utils/local_search_numba.py`
- **Excellent**: Numba JIT compilation with caching
- **Excellent**: Distance matrix cache to avoid O(n^2) rebuilds
- **Good**: Comprehensive docstrings with performance notes
- **Issue**: Global mutable `_DIST_MATRIX_CACHE` not thread-safe (C-3)
- **Issue**: Hardcoded iteration limits (Issue #4)
- **Issue**: Code duplication across LocalSearch subclasses (Issue #5)

### `optimizer_api/utils/tsplib_parser.py`
- **Excellent**: Comprehensive TSPLIB95 support
- **Excellent**: Path traversal protection in tar extraction
- **Good**: On-demand download with graceful fallback

### `academic_benchmark/smart_benchmark.py`
- **Good**: Unified orchestrator with clear phase separation
- **Good**: AlgorithmRegistry-based warmup
- **Note**: SOTA calls `academic_benchmark/sota_tsp/`, not `optimizer_api/strategies/sota_common/`
- **Issue**: Dual execution paths in SOTA engine (registry vs direct)
- **Issue**: B-PSO/B-GA appear in warmup list even if bildiri2026 unavailable

### `academic_benchmark/master_numba_engine.py`
- **Good**: Clean DoE/tuning architecture
- **Issue**: Numba detection depends entirely on bildiri2026 (fails when excluded)
- **Issue**: BILDIRI_STRATEGIES always defined (crashes when bildiri2026 excluded)
- **Issue**: GEO/ATT fallback uses EUC_2D only (critical bug on DB cache miss)

### `academic_benchmark/master_sota_engine.py`
- **Good**: Three tuning modes (Grid/Optuna/Bayesian), dynamic budget adaptation
- **Good**: AlgorithmRegistry registration for SOTA executors
- **Issue**: Numba detection depends on bildiri2026 (fails when excluded)
- **Issue**: SOTA parameter space duplicated in DoE and Optuna functions

### `academic_benchmark/sota_tsp/ls_engine.py`
- **Good**: Multi-layer LS (light/moderate/full) with numba fallback
- **Issue**: Numba detection only via bildiri2026 path (fails when excluded)
- **Issue**: No thread-safety for shared cache

### `academic_benchmark/tsplib_manager.py`
- **Good**: SQLite WAL mode, proper edge weight type storage
- **Good**: Imports `TSPLIB_OPTIMALS` from `benchmark_utils` (correct direction)
- **Note**: ATSP support via explicit matrix parsing

### `academic_benchmark/bildiri2026/core/base_solver.py`
- **Good**: Clean abstract interface
- **Good**: NumPy cache optimization (`_build_np_cache()`)
- **Good**: Fallback to Python if Numba unavailable
- **Note**: Duplicate `TSPResult` definition (out of scope — bildiri2026 is excluded)

### `academic_benchmark/sota_tsp/base_solver.py`
- **Good**: Minimal, focused interface
- **Good**: `set_dist_matrix()` for precomputed matrices
- **Issue**: Duplicate `TSPResult` definition (Issue #1)
- **Issue**: `_NUMBA_AVAILABLE` only checked via bildiri2026 path (C-3 equivalent)

---

**Report Generated**: 2026-05-19 (original), updated 2026-05-19 evening
**Companion Document**: `academic_benchmark/CODE_REVIEW_AND_FIX_REPORT_2026-05-19.md` — consolidated fix roadmap with exact code snippets