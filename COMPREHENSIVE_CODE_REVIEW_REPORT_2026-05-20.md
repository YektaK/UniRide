# UniRide Codebase — Comprehensive Code Review Report

**Date:** 2026-05-20
**Reviewer:** Senior Solutions Architect (15+ years enterprise/research)
**Scope:** `academic_benchmark/` + `optimizer_api/` (excluding `legacy`, `old`, `paper_prompts`, `numba_results`, `sota_results`, `cache`)
**Total Files Reviewed:** ~140 Python files (~28,000+ lines)

---

## 1. Executive Summary

### Overall Health: **B- (Good Foundation, Significant Technical Debt)**

UniRide is a mature, multi-layered vehicle routing optimization platform combining:
- A **FastAPI microservice** (`optimizer_api/main.py`) for production CVRP/CVRPTW solving
- An **academic benchmark suite** (`academic_benchmark/`) for TSPLIB algorithm comparison with DoE tuning
- **6+ meta-heuristic algorithms** (GA, PSO, GWO, HHO, E2BSO, R2DMA, P-AOEA, CGO, RUN) with Numba JIT acceleration
- **3 holistic solvers** (OR-Tools, PyVRP, VROOM) for industry-grade baselines

### Architecture Maturity Matrix

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Code Organization | B- | Good module separation, but god classes (2000+ lines) dominate |
| Algorithm Correctness | A- | Literature-backed implementations with proper references |
| Performance Engineering | A | Numba JIT, ProcessPoolExecutor, OpenBLAS threading control, matrix caching |
| Type Safety | C+ | Pydantic models in API layer; academic layer largely untyped |
| Test Coverage | B- | Unit tests exist but lack property-based and mutation testing |
| Documentation | B | Good docstrings in solvers; missing architecture diagrams |
| Maintainability | C+ | Dual implementations, sys.path pollution, Turkish/English mixing |

### Key Strengths
1. **Numba acceleration** properly implemented with graceful fallback, disk cache sharing across workers
2. **Strategy pattern** well-executed in `optimizer_api/` with `BaseRoutingStrategy` ABC and registry
3. **Thread-safe benchmark state** management with proper locking and concurrent run limits
4. **Academic rigor** — literature references (Holland 1975, Kennedy & Eberhart 1995, Mirjalili 2014, etc.)
5. **SQLite TSPLIB cache** with precomputed distance matrices for all edge weight types (EUC_2D, GEO, ATT, etc.)
6. **Recent consolidation** (FAZ 0-3) successfully extracted shared utilities and unified `TSPResult`, `param_signature`, `param_spaces`

### Critical Concerns
1. **Dual SOTA implementations** — identical algorithms exist in two completely separate codebases (string-based vs integer-based)
2. **God classes** — `master_numba_engine.py` (2,381 lines), `master_sota_engine.py` (2,023 lines), `faz0_interactive.py` (3,141 lines)
3. **`sys.path` manipulation** scattered throughout 15+ files
4. **`TSPProblem` not unified** with `ProblemInstance` — SOTA engine still uses its own dataclass
5. **No mathematical input validation** — negative iterations, zero population sizes accepted silently

---

## 2. Architecture & Design Review

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Microservice                      │
│              optimizer_api/main.py (1,568 lines)             │
│  /api/v1/optimize  /api/v1/benchmark/run  /api/v1/compare   │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴────────────┐
           │   STRATEGY_REGISTRY     │
           │   (strategies/__init__) │
           └───────────┬────────────┘
                       │
       ┌───────────────┼────────────────┐
       │               │                │
  ┌────▼────┐   ┌─────▼─────┐   ┌─────▼─────┐
  │Pipeline A│   │Pipeline B │   │ Holistic  │
  │Cluster-  │   │Split-based│   │ OR-Tools  │
  │First     │   │Route-First│   │ PyVRP     │
  │GA/PSO/   │   │GA/PSO/    │   │ VROOM     │
  │GWO/HHO   │   │GWO/HHO    │   │           │
  └────┬─────┘   └─────┬─────┘   └─────┬─────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
              ┌────────▼────────┐
              │  SOTA Common    │
              │  (FAZ 0 infra)  │
              │  MultiLayerLS   │
              │  ALNS ops       │
              │  Acceptance     │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Local Search   │
              │  (Numba JIT)    │
              │  2/3-opt, Or,   │
              │  Swap, Hybrid   │
              └─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               Academic Benchmark Suite                       │
│         academic_benchmark/smart_benchmark.py               │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴────────────┐
           │                        │
  ┌────────▼────────┐     ┌────────▼────────┐
  │ Numba Engine    │     │ SOTA Engine     │
  │ (2,381 lines)   │     │ (2,023 lines)   │
  │ GA/PSO/GWO/HHO  │     │ E2BSO/R2DMA/    │
  │ 2/3-opt/Or/Swap │     │ P-AOEA/CGO/RUN  │
  │ DEFAULT+TUNING  │     │ DEFAULT+TUNING  │
  └────────┬────────┘     └────────┬────────┘
           │                       │
           └───────────┬───────────┘
                       │
              ┌────────▼────────┐
              │  TSPLIB SQLite  │
              │  Distance Matrix│
              │  Cache (DB)     │
              └─────────────────┘
```

### 2.2 Integration Quality: optimizer_api ↔ academic_benchmark

**Rating: C+ (Functional but Fragile)**

The two subsystems communicate through:
1. **Shared imports** — `benchmark_utils`, `engine_core`, `tsplib_manager`
2. **SOTA Common infrastructure** — `optimizer_api/strategies/sota_common/` imported by both
3. **`smart_benchmark.py`** — orchestrator importing deeply from both engines

**Problems:**
- `smart_benchmark.py` imports private functions (`_numba_tune`, `_sota_bench_default`, etc.) from engine modules — violates encapsulation
- `sys.path` manipulation in 15+ files creates import order dependencies
- No clear API boundary between "library" and "application" code

### 2.3 Scalability Assessment

| Aspect | Current State | Scalability Risk |
|--------|--------------|------------------|
| Algorithm addition | New strategy = new file + registry entry | Low — Strategy pattern works well |
| Problem scale | TSPLIB up to ~3,000 nodes | Medium — O(n²) distance matrices |
| Concurrent benchmarks | MAX_CONCURRENT_BENCHMARKS = 3 | Low — Proper state management |
| Parameter tuning | DoE Grid Search (combinatorial explosion) | High — Needs Optuna integration |
| Multi-region deployment | Single-process FastAPI | Medium — No horizontal scaling |

---

## 3. Deep-Dive Analysis (File/Module Level)

### 3.1 CRITICAL: Dual SOTA Implementations

**Files:** `optimizer_api/strategies/sota_common/e2bso.py` (977 lines) vs `academic_benchmark/sota_tsp/e2bso_tsp.py` (565 lines)

The same algorithm (E2BSO) exists in **two completely separate codebases**:

| Aspect | `sota_common/e2bso.py` | `sota_tsp/e2bso_tsp.py` |
|--------|----------------------|------------------------|
| Tour representation | `List[str]` (node names) | `List[int]` (indices) |
| Distance access | `Dict[str, Dict[str, float]]` | `List[List[float]]` + numpy |
| Numba acceleration | No | Yes |
| Used by | `optimizer_api` (production API) | `academic_benchmark` (benchmarks) |
| Lines of code | 977 | 565 |

**Impact:** Bug fixes in one copy are NOT propagated to the other. Algorithm behavior may diverge over time, invalidating academic comparisons.

**Root Cause:** The API layer needs `List[str]` for human-readable route output, while the benchmark layer needs `List[int]` for Numba compatibility. This is a legitimate tension but was solved via duplication instead of abstraction.

### 3.2 CRITICAL: God Classes

**`master_numba_engine.py` — 2,381 lines, 104 KB**

This single file contains:
- Data models (`DOEProblem`, `StrategySpec`)
- Problem loading (TSPLIB text/tar.gz/SQLite)
- Parameter space definitions (now delegated to `param_spaces.py` ✓)
- Worker execution (`_evaluate_param_combo`)
- Bildiri2026 adapters (`_run_bildiri_pso`, `_run_bildiri_ga`)
- Interactive menus (param entry, config save/load, DB management)
- Benchmark orchestration (`_run_benchmark_direct`, `_run_benchmark_with_best`)
- AlgorithmRegistry registration (module-level side effects)
- CLI argument parsing

**SRP Violation Score: 9/10** — This file does everything.

**`faz0_interactive.py` — 3,141 lines**

The largest file in the entire project. An interactive CLI script that should be split into:
- UI/interaction layer (~500 lines)
- Pipeline execution logic (~800 lines)
- Result formatting (~400 lines)
- Configuration management (~300 lines)

### 3.3 HIGH: Ununified Problem Models

Three different problem dataclasses exist:

```python
# engine_core.py — unified, used by Numba engine
@dataclass
class ProblemInstance:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[float]
    category: str
    source: str
    is_time_matrix: bool
    time_matrix: Optional[List[List[float]]]
    dist_matrix: Any
    knn_mask: Optional[Dict[int, List[int]]]

# master_sota_engine.py — separate, NOT unified
class TSPProblem:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[float]
    category: str
    source: str

# benchmark_runner.py — yet another
@dataclass
class BenchmarkProblem:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal_score: Optional[int]
    category: str
    problem_type: str  # "tsp" or "cvrptw"
    capacity: Optional[int]
    num_vehicles: Optional[int]
    time_windows: Optional[List[Tuple[int, int]]]
    depot_index: int
```

**Impact:** Code duplication, conversion overhead, inconsistent field names (`optimal` vs `optimal_score`).

### 3.4 HIGH: sys.path Pollution

Found in **15+ files**:

```python
# Pattern repeated everywhere:
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_ENGINE_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
```

**Files affected:**
- `academic_benchmark/master_numba_engine.py`
- `academic_benchmark/master_sota_engine.py`
- `academic_benchmark/smart_benchmark.py`
- `academic_benchmark/tsplib_manager.py`
- `academic_benchmark/bildiri2026/1_generate_config.py`
- `academic_benchmark/bildiri2026/2_run_tuning.py`
- `academic_benchmark/bildiri2026/3_run_benchmark.py`
- `academic_benchmark/bildiri2026/benchmarks/*.py`
- `optimizer_api/test_*.py` (multiple)
- `optimizer_api/strategies/sota_common/__main__.py`

**Risk:** Import order dependencies, module shadowing, unpredictable behavior in different execution contexts.

### 3.5 MEDIUM: Missing Mathematical Input Validation

Solver constructors accept invalid parameters without validation:

```python
# bildiri2026/core/ga_solver.py
def __init__(self, population_size=50, max_iterations=200, ...):
    # No validation: population_size=-5 accepted silently
    # No validation: max_iterations=0 causes infinite loop
    pass

# sota_tsp/e2bso_tsp.py
@dataclass
class E2BSOTSPConfig:
    population_size: int = 36
    max_iterations: int = 300
    # No __post_init__ validation
```

**Risk:** Silent failures, infinite loops, or nonsensical benchmark results.

### 3.6 MEDIUM: Duplicate LocalSearchType Enums

```python
# optimizer_api/utils/local_search_numba.py
class LocalSearchType(str, Enum):
    NONE = "none"
    TWO_OPT = "two_opt"
    THREE_OPT = "three_opt"
    OR_OPT = "or_opt"
    SWAP = "swap"
    CROSS_EXCHANGE = "cross_exchange"
    TIME_WINDOW_AWARE = "time_window_aware"
    HYBRID = "hybrid"

# optimizer_api/models/schemas.py (Pydantic)
class LocalSearchType(str, Enum):
    NONE = "none"
    TWO_OPT = "two_opt"
    THREE_OPT = "three_opt"
    OR_OPT = "or_opt"
    HYBRID = "hybrid"
    # Missing: SWAP, CROSS_EXCHANGE, TIME_WINDOW_AWARE
```

**Impact:** API schema doesn't expose all available local search types. Clients can't request `swap` or `cross_exchange` via the API.

### 3.7 MEDIUM: Mixed Language Comments

Turkish and English comments are mixed throughout:

```python
# master_numba_engine.py
"""Konsolidasyon FAZ 3 çıktı."""  # Turkish
"""Numba için 'Time Matrix' tabanlı özel problem çözümleyicisi."""  # Turkish

# benchmark_utils.py
"""Benchmark Utils — Ortak araçlar modülü (Konsolidasyon FAZ 0)"""  # Mixed
```

**Impact:** Reduces accessibility for international collaborators, inconsistent documentation standards.

### 3.8 LOW: Hardcoded Configuration Paths

```python
# master_numba_engine.py
CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "configs")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "numba_results")

# bildiri2026/2_run_tuning.py
CONFIG_DIR = os.path.join(SCRIPT_DIR, "configs")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

# param_db.py
_PARAM_DB_PATH = os.path.join(os.path.dirname(__file__), "benchmark_db", "param_db.json")
```

**Impact:** Inflexible deployment, difficult to redirect output for CI/CD pipelines.

---

## 4. Concrete Refactoring Recommendations

### 4.1 Unify SOTA Implementations via Adapter Pattern

**Problem:** Two separate E2BSO implementations (string-based vs integer-based).

**Before (current — duplicated):**
```python
# optimizer_api/strategies/sota_common/e2bso.py
class E2BSO:
    def solve(self, coordinates: List[Tuple[float, float]], 
              dm: Optional[Dict[str, Dict[str, float]]] = None) -> E2BSOResult:
        # Uses List[str] tours, Dict-based distance matrix
        tour = ["c0", "c3", "c1", "c2"]  # string names
        cost = dm["c0"]["c3"] + dm["c3"]["c1"] + ...

# academic_benchmark/sota_tsp/e2bso_tsp.py  
class E2BSO_TSP:
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        # Uses List[int] tours, numpy distance matrix
        tour = [0, 3, 1, 2]  # integer indices
        cost = self._dm[0][3] + self._dm[3][1] + ...
```

**After (unified with adapter):**
```python
# academic_benchmark/sota_tsp/e2bso_tsp.py — single canonical implementation
class E2BSO_TSP:
    """Canonical E2BSO implementation using integer-indexed tours + numpy."""
    
    def solve(self, coordinates: List[Tuple[float, float]],
              dm: Optional[np.ndarray] = None) -> TSPResult:
        # Single implementation, Numba-accelerated
        tour = np.array([0, 3, 1, 2], dtype=np.int64)
        cost = _tour_cost_numba(tour, dm)
        return TSPResult(...)

# optimizer_api/strategies/sota_common/e2bso_adapter.py
class E2BSO:
    """Adapter: wraps E2BSO_TSP for string-based API compatibility."""
    
    def __init__(self, config: E2BSOConfig):
        self._solver = E2BSO_TSP(config.to_tsp_config())
        self._name_map: Dict[int, str] = {}
    
    def solve(self, coordinates, dm: Optional[Dict] = None):
        # Convert Dict[str, Dict] → np.ndarray
        np_dm = self._dict_to_numpy(dm) if dm else None
        result = self._solver.solve(coordinates, np_dm)
        # Convert List[int] → List[str]
        tour_str = [self._name_map[i] for i in result.tour]
        return E2BSOResult(tour=tour_str, tour_length=result.tour_length, ...)
```

**Benefit:** Single source of truth for algorithm logic. Bug fixes automatically propagate. API layer gets clean adapter.

### 4.2 Extract Engine Submodules from God Classes

**Before (master_numba_engine.py — 2,381 lines monolith):**
```python
# Everything in one file:
# - Data models
# - Problem loading
# - Parameter spaces
# - Worker execution
# - Bildiri adapters
# - Interactive menus
# - Benchmark orchestration
# - Registry registration
# - CLI parsing
```

**After (modular structure):**
```
academic_benchmark/
├── engines/
│   ├── __init__.py
│   ├── numba/
│   │   ├── __init__.py
│   │   ├── models.py          # DOEProblem, StrategySpec
│   │   ├── problem_loader.py  # load_problems(), TSPLIB parsing
│   │   ├── worker.py          # _evaluate_param_combo()
│   │   ├── bildiri_adapter.py # _run_bildiri_pso/ga
│   │   ├── benchmark.py       # _run_benchmark_direct, _run_benchmark_with_best
│   │   └── registry.py        # AlgorithmRegistration
│   └── sota/
│       ├── __init__.py
│       ├── models.py          # TSPProblem → ProblemInstance
│       ├── worker.py          # _run_solver_task, _evaluate_sota_combo
│       ├── benchmark.py       # _run_engine_default, _run_engine_tuning
│       └── registry.py        # AlgorithmRegistration
├── cli/
│   ├── numba_cli.py           # Interactive menus for Numba engine
│   └── sota_cli.py            # Interactive menus for SOTA engine
├── smart_benchmark.py         # Orchestrator (thin, <300 lines)
└── engine_core.py             # Shared models (ProblemInstance, RunResult, etc.)
```

### 4.3 Add Mathematical Input Validation via `__post_init__`

**Before (no validation):**
```python
@dataclass
class E2BSOTSPConfig:
    population_size: int = 36
    max_iterations: int = 300
    gamma: float = 0.20
    injection_rate: float = 0.12
```

**After (with validation):**
```python
@dataclass
class E2BSOTSPConfig:
    population_size: int = 36
    max_iterations: int = 300
    gamma: float = 0.20
    injection_rate: float = 0.12
    
    def __post_init__(self):
        if self.population_size < 4:
            raise ValueError(f"population_size must be >= 4, got {self.population_size}")
        if self.max_iterations < 1:
            raise ValueError(f"max_iterations must be >= 1, got {self.max_iterations}")
        if not (0.0 < self.gamma < 1.0):
            raise ValueError(f"gamma must be in (0, 1), got {self.gamma}")
        if not (0.0 < self.injection_rate < 1.0):
            raise ValueError(f"injection_rate must be in (0, 1), got {self.injection_rate}")
```

Apply the same pattern to all solver configs: `R2DMATSPConfig`, `PAOEAConfig`, `CGOConfig`, `RUNConfig`, and bildiri2026 solvers.

### 4.4 Replace sys.path Manipulation with Proper Package Structure

**Before (sys.path pollution):**
```python
# In 15+ files:
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_ENGINE_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
```

**After (pyproject.toml + editable install):**
```toml
# pyproject.toml
[project]
name = "uniride"
version = "3.1.0"

[tool.setuptools.packages.find]
include = ["optimizer_api*", "academic_benchmark*"]

# Install once:
# pip install -e .
# Then all imports work without sys.path manipulation:
# from academic_benchmark.engine_core import ProblemInstance
# from optimizer_api.strategies import STRATEGY_REGISTRY
```

### 4.5 Unify Problem Models

**Before (3 separate dataclasses):**
```python
# engine_core.py
@dataclass
class ProblemInstance: ...

# master_sota_engine.py  
class TSPProblem: ...

# benchmark_runner.py
@dataclass
class BenchmarkProblem: ...
```

**After (single model with optional CVRPTW extensions):**
```python
# engine_core.py
@dataclass
class ProblemInstance:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[float] = None
    category: str = "small"
    source: str = "tsplib"
    is_time_matrix: bool = False
    time_matrix: Optional[List[List[float]]] = None
    dist_matrix: Any = None
    knn_mask: Optional[Dict[int, List[int]]] = None
    # CVRPTW extensions
    problem_type: str = "tsp"
    capacity: Optional[int] = None
    num_vehicles: Optional[int] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
    depot_index: int = 0
    
    @property
    def optimal_score(self) -> Optional[float]:
        """Alias for backward compatibility with BenchmarkProblem."""
        return self.optimal
```

### 4.6 Add Config Schema Validation to Solver Constructors

**Before (silent acceptance of invalid params):**
```python
def __init__(self, population_size=50, max_iterations=200):
    self.population_size = population_size  # -5 accepted!
    self.max_iterations = max_iterations    # 0 accepted!
```

**After (validation at construction):**
```python
def __init__(self, population_size: int = 50, max_iterations: int = 200):
    self.population_size = self._validate_population_size(population_size)
    self.max_iterations = self._validate_max_iterations(max_iterations)

@staticmethod
def _validate_population_size(value: int) -> int:
    if value < 4:
        raise ValueError(f"population_size must be >= 4, got {value}")
    if value > 10000:
        raise ValueError(f"population_size must be <= 10000, got {value}")
    return value
```

---

## 5. Quick Wins & Long-Term Roadmap

### 5.1 Quick Wins (High Impact, Low Effort — 1-3 days each)

| # | Action | Impact | Effort | Files |
|---|--------|--------|--------|-------|
| QW-1 | Add `__post_init__` validation to all solver configs | Prevents silent failures | 1 day | All `*Config` dataclasses |
| QW-2 | Unify `LocalSearchType` enums — use single source | API parity | 2 hours | `models/schemas.py`, `local_search_numba.py` |
| QW-3 | Standardize comments to English only | Accessibility | 1 day | All files with Turkish comments |
| QW-4 | Extract `CONFIGS_DIR`, `RESULTS_DIR`, `DB_PATH` to `constants.py` | Deployability | 2 hours | 8+ files |
| QW-5 | Add `pyproject.toml` for editable install | Eliminates sys.path | 1 day | Root directory |
| QW-6 | Add `typing` to `benchmark_utils.py` public functions | Type safety | 2 days | `benchmark_utils.py` |
| QW-7 | Add `pytest.mark.parametrize` tests for edge cases | Catch regressions | 1 day | `academic_benchmark/tests/` |
| QW-8 | Replace `TSPProblem` with `ProblemInstance` in SOTA engine | Model unification | 3 hours | `master_sota_engine.py` |

### 5.2 Medium-Term (1-2 weeks each)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| MT-1 | Extract `master_numba_engine.py` into `engines/numba/` subpackage | Maintainability | 1 week |
| MT-2 | Extract `master_sota_engine.py` into `engines/sota/` subpackage | Maintainability | 1 week |
| MT-3 | Implement SOTA adapter pattern (single canonical + API adapter) | Correctness guarantee | 2 weeks |
| MT-4 | Add Optuna Bayesian optimization as alternative to DoE Grid Search | Tuning efficiency | 1 week |
| MT-5 | Add property-based testing (Hypothesis) for solver invariants | Algorithm correctness | 1 week |
| MT-6 | Create architecture diagram + ADR (Architecture Decision Records) | Onboarding | 3 days |

### 5.3 Long-Term (1-2 months each)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| LT-1 | Migrate to proper package layout with `pyproject.toml` editable install | Eliminates all sys.path issues | 2 weeks |
| LT-2 | Implement gRPC interface for high-throughput benchmark orchestration | Scalability | 1 month |
| LT-3 | Add distributed benchmark execution (Ray/Dask) | Horizontal scaling | 2 months |
| LT-4 | Implement algorithm abstraction layer that works for both TSP and CVRP | Code reuse | 1 month |
| LT-5 | Add CI/CD pipeline with automated benchmark regression detection | Quality gates | 2 weeks |
| LT-6 | Migrate interactive CLI to Typer/Click with proper subcommands | UX improvement | 1 week |

---

## 6. Positive Notes

The codebase demonstrates several **exemplary practices** worth preserving:

1. **Numba disk cache sharing** — `_cache_base` with fallback to `~/.UniRide_numba_cache` ensures multiprocessing workers share JIT artifacts
2. **OpenBLAS thread control** — `os.environ["OPENBLAS_NUM_THREADS"] = "1"` prevents BLAS oversubscription in ProcessPoolExecutor
3. **Thread-safe benchmark state** — `BenchmarkStateManager` with `threading.Lock` and `MAX_CONCURRENT_BENCHMARKS` limit
4. **Academic references** — Every solver cites its source paper (Holland 1975, Kennedy & Eberhart 1995, Mirjalili 2014, Heidari 2019, etc.)
5. **Edge weight type handling** — TSPLIB manager correctly handles EUC_2D, GEO, ATT, MAN_2D, CEIL_2D with proper distance formulas
6. **Recent consolidation work** — FAZ 0-3 successfully unified `TSPResult`, created `param_spaces.py`, added `ConfigSchema`, parametrized `HybridLocalSearch`

---

## 7. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Dual SOTA implementations diverge | **Critical** | High (already happening) | Unify via adapter pattern (4.1) |
| God classes become unmaintainable | **High** | Medium | Extract subpackages (4.2) |
| sys.path causes import failures in CI | **High** | Medium | pyproject.toml editable install (4.4) |
| Invalid params cause silent wrong results | **Medium** | High | `__post_init__` validation (4.3) |
| No type hints cause runtime errors | **Medium** | Medium | Add typing to public APIs (QW-6) |
| Hardcoded paths break deployments | **Low** | Low | Extract to constants.py (QW-4) |

---

*End of Report*
