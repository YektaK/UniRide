# academic_benchmark Code Review & Fix Report

**Date:** 2026-05-19
**Scope:** `academic_benchmark/` (excluding `bildiri2026/`, `legacy/`, `old/`, `paper_prompts/`, `numba_results/`, `sota_results/`, `cache/`)
**Status:** PEER-REVIEWED, FIXES VALIDATED, WORKFLOW DEFINED

> **Peer review completed 2026-05-19 evening.** All claims verified against actual source code. Three refinements applied per review findings. See §9 for peer review notes.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Actual Architecture](#2-actual-architecture)
3. [bildiri2026 Exclusion Impact](#3-bildiri2026-exclusion-impact)
4. [Critical Issues (Must Fix)](#4-critical-issues-must-fix)
5. [Design Issues (Should Fix)](#5-design-issues-should-fix)
6. [Code Quality Issues](#6-code-quality-issues)
7. [Quick Wins](#7-quick-wins)
8. [Detailed Fix Workflow](#8-detailed-fix-workflow)
9. [Peer Review Notes](#9-peer-review-notes)
10. [Appendix: bildiri2026 Dependency Map](#appendix-bildiri2026-dependency-map)

---

## 1. Executive Summary

The `academic_benchmark/` ecosystem consists of two independent benchmark engines sharing a common orchestrator (`smart_benchmark.py`):

| Engine | Entry Point | Algorithm Implementations |
|--------|-------------|--------------------------|
| Numba | `master_numba_engine.py` | GA, PSO, GWO, HHO, B-PSO\*, B-GA\* + local search (2-opt, 3-opt, Or-opt, hybrid) |
| SOTA | `master_sota_engine.py` | E2BSO-TSP, R2DMA-TSP, P-AOEA-TSP, CGO-TSP, RUN-TSP (from `sota_tsp/`) |

\* B-PSO and B-GA require `bildiri2026/` and must be made optional if that folder is excluded.

**Files excluded from this review:** `bildiri2026/`, `legacy/`, `old/`, `paper_prompts/`, `numba_results/`, `sota_results/`, `cache/`.

**Peer-verified issues:** 4 critical, 4 design, 5 code quality, 6 quick wins.

---

## 2. Actual Architecture

```
smart_benchmark.py          ← Unified orchestrator
│
├── engine_core.py          ← ProblemInstance, RunResult, AlgorithmRegistry, BenchmarkConfig
├── benchmark_utils.py      ← TSPLIB_OPTIMALS (COPY 1, 129 entries), ETATracker, ProblemSelector
│
├── master_numba_engine.py
│   ├── bildiri2026/core/   ← B-PSO, B-GA (REQUIRE bildiri2026 — see §3)
│   └── optimizer_api/utils/local_search_numba.py
│       └── _DIST_MATRIX_CACHE (plain dict, no locking — see C-3)
│
├── master_sota_engine.py
│   └── academic_benchmark/sota_tsp/     ← E2BSO_TSP, R2DMA_TSP, PAOEA_TSP, CGO_TSP, RUN_TSP
│       ├── ls_engine.py   ← Imports numba_accel from bildiri2026 for JIT kernels
│       ├── repair_ops.py
│       └── destroy_ops.py
│
├── tsplib_manager.py       ← SQLite DB cache (edge_weight_type stored in problems table)
├── param_db.py             ← Persistent parameter storage (JSON file)
└── sota_tsp/base_solver.py  ← TSPResult (COPY — duplicated in bildiri2026 and optimizer_api)

optimizer_api/strategies/sota_common/     ← PARALLEL SOTA implementation (v3.0.0, string-based)
└── e2bso.py, r2dma.py, paoea.py          ← NOT used by smart_benchmark
    Uses List[str] node IDs (e.g., "c0")
    More modular: MultiStartInitializer, PenaltyManager, DiversityController, etc.

academic_benchmark/sota_tsp/             ← SOTA implementation used by smart_benchmark (v1.0.0)
    Uses List[int] node IDs (e.g., 0, 1)
    Standalone: ls_engine.py, repair_ops.py, destroy_ops.py
```

**Two completely separate SOTA implementations exist:**

| Attribute | `optimizer_api/strategies/sota_common/` | `academic_benchmark/sota_tsp/` |
|-----------|----------------------------------------|--------------------------------|
| Version | 3.0.0 (FAZ 0 infrastructure) | 1.0.0 (FAZ consolidated) |
| Used by | `optimizer_api/` (API-facing) | `smart_benchmark.py` (benchmarking) |
| Node IDs | `List[str]` (e.g., `"c0"`, `"c1"`) | `List[int]` (e.g., `0`, `1`) |
| Classes | `E2BSO`, `R2DMA`, `PAOEA` | `E2BSO_TSP`, `R2DMA_TSP`, `PAOEA_TSP` |
| Infrastructure | Rich modular: `MultiStartInitializer`, `PenaltyManager`, `DiversityController`, etc. | Standalone: `ls_engine.py`, `repair_ops.py`, `destroy_ops.py` |

---

## 3. bildiri2026 Exclusion Impact

### 3.1 What bildiri2026 Provides (Consumed by academic_benchmark/)

| Dependency | File | Purpose | Impact if Excluded |
|---|---|---|---|
| `numba_accel` module | `sota_tsp/ls_engine.py:24-36` | Numba JIT kernels for 2-opt/3-opt/Or-opt/Swap | SOTA local search falls back to pure Python |
| Numba detection | `master_numba_engine.py:139-148` | Sets `_NUMBA_AVAILABLE` | Always `False` → Numba kernels bypassed |
| `PSOOptimizer`, `GAOptimizer` | `master_numba_engine.py:812-815` | B-PSO and B-GA solver execution | Runtime crash when B-PSO/B-GA selected |
| Numba detection | `master_sota_engine.py:448-455` | Sets `_NUMBA_AVAILABLE` | Always `False` → Numba kernels bypassed |

### 3.2 bildiri2026 Own Workflow (1_generate_config → 2_run_tuning → 3_run_benchmark)

bildiri2026's entry points all use `sys.path.insert(0, SCRIPT_DIR)` to self-resolve imports from its own `core/` directory. They import from:
- `core/__init__.py` (local)
- `benchmarks/tsplib_benchmark.py` (local)
- `config_manager.py` (local)
- `data_manager.py` (local)

**bildiri2026 does NOT import from any file in `academic_benchmark/` that lies outside its own folder.** All proposed fixes to `master_numba_engine.py`, `master_sota_engine.py`, and `sota_tsp/ls_engine.py` are guaranteed not to affect bildiri2026's workflow. See Appendix for full dependency map.

### 3.3 Verification Table

| bildiri2026 file | Imports target files? | Uses proposed fix points? |
|---|---|---|
| `1_generate_config.py` | No | No |
| `2_run_tuning.py` | No | No |
| `3_run_benchmark.py` | No | No |
| `benchmarks/tsplib_benchmark.py` | No | No |
| `benchmarks/timematrix_benchmark.py` | No | No |
| `core/__init__.py` | No | No |
| `core/ga_solver.py`, `core/pso_solver.py` | No | No |
| `core/two_opt.py`, `three_opt.py`, `or_opt.py` | No | No |
| `core/numba_accel.py` | No | No |

---

## 4. Critical Issues (Must Fix)

### C-1: Numba Detection Fails When bildiri2026 Excluded

**Location:** `master_numba_engine.py:139-148`, `master_sota_engine.py:445-455`, `sota_tsp/ls_engine.py:24-36`

**Peer review status:** VERIFIED. All three files checked — none uses `import numba` directly. All go through `from core import numba_accel` via bildiri2026 path hack. Two independent `_NUMBA_OK` variables exist (engine-level + LS-level) and both fall to `False` when bildiri2026 is absent.

**Problem:** Both engines AND `ls_engine.py` detect Numba availability exclusively through bildiri2026's `numba_accel.py`. If bildiri2026 is excluded, ALL three report Numba unavailable, causing all local search to fall back to pure Python even when Numba is installed.

**Critical nuance:** `ls_engine.py` sets `_NUMBA_OK` at module import time as a separate variable from `master_numba_engine._NUMBA_AVAILABLE` and `master_sota_engine._NUMBA_AVAILABLE`. All three must be fixed simultaneously — fixing only the engine-level variables leaves `ls_engine.py._NUMBA_OK = False`.

**Impact:** Performance degradation — all Numba JIT kernels bypassed across both engines and SOTA local search.

**Fix (master_numba_engine.py, master_sota_engine.py, sota_tsp/ls_engine.py — apply to ALL THREE):**

### `_detect_numba()` in master_numba_engine.py and master_sota_engine.py:

```python
def _detect_numba() -> bool:
    """Numba aktif mi tespit et — sistem geneli veya bildiri2026 uzerinden."""
    # 1) Check for Numba directly (works regardless of bildiri2026 presence)
    try:
        import numba          # pylint: disable=unused-import
        return True
    except ImportError:
        pass

    # 2) Fallback: try bildiri2026's numba_accel (backward compatibility)
    import importlib.util
    _ab_dir = os.path.join(_PROJECT_ROOT, "academic_benchmark", "bildiri2026")
    spec = importlib.util.find_spec("core.numba_accel")  # won't modify sys.path
    if spec is None and os.path.isdir(_ab_dir):
        # Only do sys.path insert as last resort
        sys.path.insert(0, _ab_dir)
        try:
            from core import numba_accel as _nb
            return bool(_nb.NUMBA_AVAILABLE)
        except Exception:
            pass
        finally:
            try:
                sys.path.remove(_ab_dir)
            except ValueError:
                pass
    elif spec is not None:
        try:
            from core import numba_accel as _nb
            return bool(_nb.NUMBA_AVAILABLE)
        except Exception:
            pass

    return False
```

### `sota_tsp/ls_engine.py` — Numba Detection (Same Pattern):

```python
_NUMBA_OK = False
_nb = None

# 1) Direct Numba check first
try:
    import numba   # pylint: disable=unused-import
    _NUMBA_OK = True
except ImportError:
    pass

# 2) Fallback: try bildiri2026's numba_accel
if not _NUMBA_OK:
    import importlib.util
    _ls_dir = os.path.dirname(os.path.abspath(__file__))
    _ab_dir = os.path.join(_ls_dir, "..", "bildiri2026")

    spec = importlib.util.find_spec("core.numba_accel")
    if spec is None and os.path.isdir(_ab_dir):
        import sys as _sys
        _sys.path.insert(0, _ab_dir)
        try:
            from core import numba_accel as _nb
            _NUMBA_OK = _nb.NUMBA_AVAILABLE
        except Exception:
            pass
        finally:
            try:
                _sys.path.remove(_ab_dir)
            except ValueError:
                pass
    elif spec is not None:
        try:
            from core import numba_accel as _nb
            _NUMBA_OK = _nb.NUMBA_AVAILABLE
        except Exception:
            pass
```

**Design decision — `importlib.util.find_spec`:** Chosen over `sys.path.insert/remove` to eliminate the `sys.path` pollution risk flagged in peer review. `find_spec` checks if `core.numba_accel` is importable without modifying `sys.path`. Only falls back to `sys.path.insert` when `find_spec` returns `None` (module not on path) AND `bildiri2026/` directory exists — and then cleans up in `finally`.

**bildiri2026 impact:** None. bildiri2026 has its own detection logic. The `finally` block ensures `sys.path` is restored even if the import fails.

---

### C-2: B-PSO/B-GA Crash When bildiri2026 Excluded

**Location:** `master_numba_engine.py:854-869` (BILDIRI_STRATEGIES), lines 658-662 (routing), lines 812-815 (_run_bildiri_pso)

**Peer review status:** VERIFIED. `BILDIRI_STRATEGIES` is a module-level list (line 854, not wrapped in a function). The lazy imports at lines 812-815 and 837-839 mean NO crash at module import time — crash only at runtime when B-PSO/B-GA is actually executed. The routing payload strings are confirmed as `"BILDIRI_PSO"` and `"BILDIRI_GA"`.

**Problem:** When bildiri2026 is excluded, selecting B-PSO or B-GA crashes at runtime when `_run_bildiri_pso` / `_run_bildiri_ga` tries to import `PSOOptimizer` / `GAOptimizer` from bildiri2026.

**Peer review refinement:** The original fix's `_get_bildiri_strategies()` did `from core import pso_solver, ga_solver` as a canary — importing modules it never uses. Changed to `importlib.util.find_spec("core.pso_solver")` which is cleaner. Also added `sys.path` cleanup via `finally`.

**Fix — Step 1: Make BILDIRI_STRATEGIES conditional**

```python
def _get_bildiri_strategies():
    """Return bildiri2026 strategies only if bildiri2026 is importable."""
    import importlib.util

    if importlib.util.find_spec("core.pso_solver") is not None:
        return [
            ("B-PSO", "BILDIRI_PSO", {
                "swarm_size": 50, "max_iterations": 500,
                "inertia_weight": 0.729, "cognitive_coeff": 1.49445,
                "social_coeff": 1.49445, "max_velocity_size": 5,
                "max_no_improvement": 100, "reinit_interval": 50,
                "algorithm_type": "bildiri_meta",
            }),
            ("B-GA", "BILDIRI_GA", {
                "population_size": 100, "generations": 500,
                "crossover_rate": 0.85, "mutation_rate": 0.15,
                "elite_count": 2, "tournament_size": 3,
                "max_no_improvement": 100,
                "algorithm_type": "bildiri_meta",
            }),
        ]

    # find_spec failed, try with sys.path as last resort
    _ab_dir = os.path.join(_PROJECT_ROOT, "academic_benchmark", "bildiri2026")
    if os.path.isdir(_ab_dir):
        if _ab_dir not in sys.path:
            sys.path.insert(0, _ab_dir)
        try:
            from core import pso_solver, ga_solver  # pylint: disable=unused-import
            return [
                ("B-PSO", "BILDIRI_PSO", { ... }),
                ("B-GA", "BILDIRI_GA",  { ... }),
            ]
        except Exception:
            pass
        finally:
            try:
                sys.path.remove(_ab_dir)
            except ValueError:
                pass

    return []

BILDIRI_STRATEGIES: List[Tuple[str, str, Dict[str, Any]]] = _get_bildiri_strategies()
```

**Fix — Step 2: Add safety guard in routing (lines 658-662)**

```python
# Replace lines 658-662:
if str(strategy_payload) in ("BILDIRI_PSO", "BILDIRI_GA"):
    if not BILDIRI_STRATEGIES:
        raise ImportError(
            f"Strategy {strategy_payload} requires bildiri2026 which is not installed. "
            "Either install bildiri2026 or exclude B-PSO/B-GA from the benchmark."
        )
    if str(strategy_payload) == "BILDIRI_PSO":
        result = _run_bildiri_pso(problem_dict, seed, strategy_params)
    else:
        result = _run_bildiri_ga(problem_dict, seed, strategy_params)
```

**Peer review note:** This guard is defense-in-depth. When `BILDIRI_STRATEGIES = []`, the routing block at line 658 is never reached for BILDIRI payloads because `_all_strategy_specs()` never includes them. The guard protects against the pathological case of someone calling `_run_benchmark_combo` directly with manual `strategy_payload="BILDIRI_PSO"`. It costs nothing and provides a clear error message.

**Fix — Step 3: Verify `_all_strategy_specs()` is safe**

No change needed. With `BILDIRI_STRATEGIES = []`, the loop at line 456 produces zero entries. B-PSO and B-GA simply do not appear in the strategy list. The `AlgorithmRegistry` registration block at lines 1946-1957 also loops over an empty list. The entire B-PSO/B-GA pipeline — including `smart_benchmark.py`'s warmup filter at line 221 — becomes dead code for these algorithms.

**Safety chain (validated):**

| Layer | When `BILDIRI_STRATEGIES = []` | Outcome |
|-------|-------------------------------|---------|
| `_get_bildiri_strategies()` | Returns `[]` | B-PSO/B-GA not defined |
| `_all_strategy_specs()` | Empty loop | Not included |
| Registration block (lines 1946-1957) | Empty loop | Not registered |
| `AlgorithmRegistry.list_algorithms()` | No B-PSO/B-GA | Not in menu |
| `smart_benchmark.py` warmup (line 221) | Not in algorithms | Dead code for B- |
| `AlgorithmRegistry.warmup("B-PSO")` | No key in `_warmup_fns` | Silent no-op |
| Execution routing (lines 658-662) | Payload never encountered | Never reached |

**bildiri2026 impact:** None. `BILDIRI_STRATEGIES` is a variable in `master_numba_engine.py` that bildiri2026 never references.

---

### C-3: Global Mutable Cache in `local_search_numba.py`

**Location:** `optimizer_api/utils/local_search_numba.py:72`

**Peer review status:** VERIFIED. `_DIST_MATRIX_CACHE` is a plain `dict` with no locking. However, **practical risk is low** in current code:
- `master_numba_engine.py` and `smart_benchmark.py` use `ProcessPoolExecutor` (multiprocessing) — each worker gets its own copy.
- `optimizer_api/main.py` uses `ThreadPoolExecutor` but imports from `utils.local_search` (pure Python), NOT `utils.local_search_numba`.
- The API thread pool never accesses `_DIST_MATRIX_CACHE`.
- Only potential race: if someone adds threading code that imports `local_search_numba` in the future.

**Problem:** When `_DIST_MATRIX_CACHE` (plain dict) is accessed concurrently within a single process, there is no locking. While current code uses `ProcessPoolExecutor` (each process gets its own cache copy), future code might use `ThreadPoolExecutor` and hit the race condition.

**Fix:** Add `threading.Lock` as defensive measure:

```python
import threading

_DIST_MATRIX_CACHE: Dict[int, np.ndarray] = {}
_DIST_MATRIX_CACHE_LOCK = threading.Lock()

def _get_cached_matrix(key: int):
    """Thread-safe cache read."""
    with _DIST_MATRIX_CACHE_LOCK:
        return _DIST_MATRIX_CACHE.get(key)

def _set_cached_matrix(key: int, value: np.ndarray) -> None:
    """Thread-safe cache write."""
    with _DIST_MATRIX_CACHE_LOCK:
        _DIST_MATRIX_CACHE[key] = value
```

Then update `_build_or_get_dist_matrix` (~line 98, ~line 120, ~line 134) to use `_get_cached_matrix` and `_set_cached_matrix`.

**Peer review note:** The report originally stated "Silent incorrect results or crashes in concurrent benchmark runs." This is accurate for the scenario described but overstated as a *current* risk. The fix remains correct as defensive programming.

**bildiri2026 impact:** None. bildiri2026 does not use `local_search_numba.py`.

---

### C-4: GEO/ATT Distance Matrix Fallback Bug in Numba Engine

**Location:** `master_numba_engine.py:638-669`

**Peer review status:** VERIFIED. `DOEProblem` lacks `edge_weight_type` field. The Numba engine falls back to `create_np_distance_matrix` (EUC_2D only) when `_dm_from_cache()` returns `None`. The SOTA engine is immune — it never falls back to `create_np_distance_matrix`.

**Problem:** The comment at lines 639-641 explicitly warns that the fallback produces wrong distances for GEO/ATT/etc problems. The Numba engine loads from `_dm_from_cache()` (which has correct edge weight type in the DB), but on cache miss falls back to Euclidean-only computation. `DOEProblem` lacks `edge_weight_type`, preventing any fix that needs that information at the DOEProblem level.

**User's chosen approach:** Query DB at fallback time (minimal code changes, no data model modifications).

**Fix:**

```python
# Lines 638-651: Replace the current block with:
dist_matrix_np = None
if not is_time_matrix:
    problem_name = problem_dict.get("name", "")
    if problem_name:
        try:
            db_matrix = _dm_from_cache(problem_name, TSPLIB_DB)
            if db_matrix is not None:
                dist_matrix_np = db_matrix
            else:
                # DB cache miss — compute correct matrix by querying edge_weight_type
                _ewt = _query_edge_weight_type(problem_name, TSPLIB_DB)
                if _ewt is not None and _ewt != "EUC_2D":
                    coords = problem_dict.get("coordinates", [])
                    if coords and _DIST_OK:
                        from academic_benchmark.tsplib_manager import _build_matrix
                        dist_matrix_np = _build_matrix(coords, _ewt)
        except Exception:
            pass
```

And add a helper function:

```python
def _query_edge_weight_type(problem_name: str, db_path: str) -> Optional[str]:
    """Query the TSPLIB DB for a problem's edge_weight_type. Returns None on miss."""
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT edge_weight_type FROM problems WHERE name=?",
            (problem_name,)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None
```

**Notes:**
- `_DIST_OK` must be True (imported from `tsplib_manager.py`'s `tsplib_distance_by_type` availability check).
- `_build_matrix` is the same function `tsplib_manager.py` uses when computing distance matrices for the DB cache — it already handles all edge weight types.
- The fallback adds a single SQLite query + O(n²) matrix computation only when DB cache misses. Normal path (cache hit) is unchanged.
- This covers GEO, ATT, CEIL_2D, GEO, NEU_2D — all types the TSPLIB parser supports.

**Design decision — Query DB at fallback time over Add edge_weight_type to DOEProblem:** Chosen per user preference. Pros: zero data model changes, localized fix. Cons: adds a DB query on the slow path (already slow due to matrix computation, negligible overhead).

**bildiri2026 impact:** None. bildiri2026 has its own distance computation in `core/numba_accel.py`.

---

## 5. Design Issues (Should Fix)

### D-1: Two Problem Types Instead of One

| Engine | Problem Type | Location |
|--------|-------------|----------|
| Numba | `DOEProblem` | master_numba_engine.py:255-265 |
| SOTA | `TSPProblem` | master_sota_engine.py:272-279 |
| Unified | `ProblemInstance` | engine_core.py:6 (exists but unused as canonical) |

`smart_benchmark.py` converts between them at lines 374-401. Standardize on `ProblemInstance` from `engine_core.py`.

**bildiri2026 impact:** None.

---

### D-2: AlgorithmRegistry Execution Disconnect

`master_sota_engine.py:1804-1843` registers SOTA executors with `AlgorithmRegistry` via `_make_sota_executor()`. These are used by the **unified benchmark path** in `smart_benchmark.py:422-425`. However, `_run_engine_default()` and `_run_engine_tuning()` do NOT use the registry — they call `_run_solver_task` and `_evaluate_sota_combo` directly. The registry's `warmup()` only benefits the unified path.

**Fix:** Refactor `_run_engine_default()` and `_run_engine_tuning()` to route through `AlgorithmRegistry.get_executor()`, or document that direct engine calls bypass warmup.

**bildiri2026 impact:** None.

---

### D-3: SOTA Parameter Space Duplicated Across Three Functions

**Locations:**
- `master_sota_engine.py:520-575` — `_build_sota_parameter_space()` for DoE tuning
- `master_sota_engine.py:1046-1089` — `_build_sota_optuna_space()` for Bayesian tuning
- `master_numba_engine.py:465-530` — `_build_numba_parameter_space()` for Numba tuning

Adding a new parameter requires updating both functions. Missing one causes silent inconsistency.

**Fix:** Create a single parameter space definition per algorithm:
```python
# academic_benchmark/param_spaces.py
SOTA_SPACES = {
    "E2BSO-TSP": {
        "population_size":  {"type": "int",   "range": [20, 60]},
        "max_iterations":   {"type": "int",   "range": [150, 500]},
        "gamma":            {"type": "float", "range": [0.10, 0.35]},
        ...
    },
    ...
}
```

Then both DoE and Optuna functions import from here and convert to their format.

**bildiri2026 impact:** None.

---

### D-4: `param_signature` Uses JSON String as Hash

**Location:** `benchmark_utils.py:697-699`

```python
def param_signature(params: Dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, ensure_ascii=False)
```

For large parameter dicts this creates very long strings. Use SHA256:

```python
import hashlib

def param_signature(params: Dict[str, Any]) -> str:
    normalized = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
```

**bildiri2026 impact:** None.

---

## 6. Code Quality Issues

### Q-1: TSPResult Duplicated in Three Places

| Location | Notes |
|----------|-------|
| `academic_benchmark/sota_tsp/base_solver.py:21-29` | Fields: algorithm, tour, tour_length, elapsed_ms, iterations, params, history, seed |
| `academic_benchmark/bildiri2026/core/base_solver.py` | Identical fields |
| `optimizer_api/strategies/sota_common/e2bso.py` | Likely identical |

**Fix:** Move `TSPResult` to `engine_core.py` alongside `RunResult`. `sota_tsp/base_solver.py` imports from `engine_core`. bildiri2026's copy is left unchanged.

---

### Q-2: Duplicate LocalSearch Classes

Five classes in `local_search_numba.py` duplicate identical `_prepare_numba_inputs`, `_indices_to_route`, and `improve` methods. Extract common behavior into a base class with template method pattern.

---

### Q-3: Hardcoded Iteration Limits in HybridLocalSearch

Buried in method body, not constructor parameters. Move to `@dataclass` configuration class.

---

### Q-4: No Schema Validation on Config Files

**Location:** `smart_benchmark.py:773` → `engine_core.py:92`

`BenchmarkConfig.from_json()` does `json.loads()` then `BenchmarkTask(**t)` without validating required fields. Add validation:

```python
required = {"problem_name", "algorithm", "run_idx", "seed", "params"}
if not required.issubset(t.keys()):
    raise ValueError(f"Missing fields: {required - t.keys()}")
```

---

### Q-5: C-4 requires `sqlite3` import in master_numba_engine.py

`master_numba_engine.py` currently does not import `sqlite3`. The DB query at fallback time (C-4 fix) needs `import sqlite3` added to the imports block. Also, `tsplib_manager.py`'s `_build_matrix` must be exposed as a public function (not `_build_matrix` — consider renaming to `build_distance_matrix` for external use).

---

## 7. Quick Wins

| # | Fix | File | Effort | Impact |
|---|-----|------|--------|--------|
| QW-1 | Apply `importlib.util.find_spec` + `finally` cleanup to all three Numba detection points | master_numba_engine.py:139, master_sota_engine.py:445, sota_tsp/ls_engine.py:24 | 15 min | Eliminates `sys.path` pollution, enables bildiri2026 exclusion |
| QW-2 | Add clear error message in `_run_bildiri_pso`/`_run_bildiri_ga` when bildiri2026 missing | master_numba_engine.py:812-815 | 5 min | Prevents confusing ModuleNotFoundError |
| QW-3 | Add `best_params` validation before saving | master_numba_engine.py:1129-1131, master_sota_engine.py:1009-1018 | 10 min | Prevent corrupt JSON |
| QW-4 | Add log line before Phase 1/2 in tuning orchestrator | smart_benchmark.py:349-364 | 2 min | Clarity in mixed runs |
| QW-5 | Document `OPENBLAS_NUM_THREADS=1` / `OMP_NUM_THREADS=1` workaround | master_numba_engine.py, master_sota_engine.py | 5 min | Maintenance clarity |
| QW-6 | Fix duplicate import in `sota_tsp/__init__.py:16-17` | sota_tsp/__init__.py | 1 min | Code cleanliness |

**QW-6 details:** `sota_tsp/__init__.py:16-17` has:
```python
from .base_solver import BaseTSPSolver, TSPResult
from .base_solver import BaseTSPSolver, TSPResult   # duplicate line
```
Remove one of the two identical lines.

---

## 8. Detailed Fix Workflow

### Pre-Flight Checklist

- [ ] Verify `import numba` works in the target Python environment
- [ ] Verify `importlib.util.find_spec` is available (Python 3.4+)
- [ ] Verify `import sqlite3` works in master_numba_engine.py environment
- [ ] Run `python academic_benchmark/tsplib_manager.py status` to confirm DB is populated
- [ ] Take a git snapshot: `git stash && git branch fix-bildiri-exclusion-academic-benchmark`

### Phase 1: bildiri2026 Exclusion Enablement (Estimated: 45 min)

#### Step 1.1: Fix Numba Detection in ALL THREE Files

**Files:** `master_numba_engine.py`, `master_sota_engine.py`, `sota_tsp/ls_engine.py`

**For `master_numba_engine.py` (line 139-148):**
Replace the current `_detect_numba()` function with the code from §C-1. This adds `import numba` as the first check, then falls back to `importlib.util.find_spec` + `finally: sys.path.remove()`.

**For `master_sota_engine.py` (line 445-455):**
Identical replacement to `_detect_numba()`.

**For `sota_tsp/ls_engine.py` (lines 24-36):**
Replace the entire `try/except` block with the code from §C-1. This adds `import numba` first, then `find_spec` + `finally: sys.path.remove()`.

**Verification:**
```bash
# Test 1: With bildiri2026 present
python -c "from academic_benchmark.master_numba_engine import _NUMBA_AVAILABLE; print('Numba:', _NUMBA_AVAILABLE)"
# Test 2: After moving bildiri2026/ to bildiri2026_bak/
mv academic_benchmark/bildiri2026 academic_benchmark/bildiri2026_bak
python -c "from academic_benchmark.master_numba_engine import _NUMBA_AVAILABLE; print('Numba:', _NUMBA_AVAILABLE)"
# Test 3: Verify ls_engine.py
python -c "from academic_benchmark.sota_tsp.ls_engine import _NUMBA_OK; print('LS Numba:', _NUMBA_OK)"
# Test 4: Restore bildiri2026
mv academic_benchmark/bildiri2026_bak academic_benchmark/bildiri2026
```

---

#### Step 1.2: Make BILDIRI_STRATEGIES Conditional

**File:** `master_numba_engine.py`

**Delete** the current block at lines 854-869:
```python
BILDIRI_STRATEGIES: List[Tuple[str, str, Dict[str, Any]]] = [
    ("B-PSO", "BILDIRI_PSO", {...}),
    ("B-GA", "BILDIRI_GA",  {...}),
]
```

**Insert** the `_get_bildiri_strategies()` function (from §C-2) and replace with:
```python
BILDIRI_STRATEGIES: List[Tuple[str, str, Dict[str, Any]]] = _get_bildiri_strategies()
```

**Verification:**
```bash
# Test 1: With bildiri2026
python -c "from academic_benchmark.master_numba_engine import BILDIRI_STRATEGIES; print('Strategies:', len(BILDIRI_STRATEGIES))"
# Expected: 2

# Test 2: Without bildiri2026
mv academic_benchmark/bildiri2026 academic_benchmark/bildiri2026_bak
python -c "from academic_benchmark.master_numba_engine import BILDIRI_STRATEGIES; print('Strategies:', len(BILDIRI_STRATEGIES))"
# Expected: 0
mv academic_benchmark/bildiri2026_bak academic_benchmark/bildiri2026

# Test 3: Verify AlgorithmRegistry doesn't list B-PSO/B-GA when absent
python -c "from academic_benchmark.engine_core import AlgorithmRegistry; print('B-PSO' in AlgorithmRegistry.list_algorithms())"
```

---

#### Step 1.3: Add Safety Guard in Routing

**File:** `master_numba_engine.py`

**Replace** lines 658-662:
```python
if str(strategy_payload) in ("BILDIRI_PSO", "BILDIRI_GA"):
    if str(strategy_payload) == "BILDIRI_PSO":
        result = _run_bildiri_pso(problem_dict, seed, strategy_params)
    else:
        result = _run_bildiri_ga(problem_dict, seed, strategy_params)
```

**With:**
```python
if str(strategy_payload) in ("BILDIRI_PSO", "BILDIRI_GA"):
    if not BILDIRI_STRATEGIES:
        raise ImportError(
            f"Strategy {strategy_payload} requires bildiri2026 which is not installed. "
            "Either install bildiri2026 or exclude B-PSO/B-GA from the benchmark."
        )
    if str(strategy_payload) == "BILDIRI_PSO":
        result = _run_bildiri_pso(problem_dict, seed, strategy_params)
    else:
        result = _run_bildiri_ga(problem_dict, seed, strategy_params)
```

**Verification:** This guard is defense-in-depth. When `BILDIRI_STRATEGIES = []`, the routing is never reached. To test, manually trigger:
```python
# In a Python REPL:
from academic_benchmark.master_numba_engine import _get_bildiri_strategies, _run_benchmark_combo
# (set BILDIRI_STRATEGIES = [] then call with BILDIRI_PSO payload)
```

---

#### Step 1.4: Fix GEO/ATT Distance Matrix Fallback

**File:** `master_numba_engine.py`

**Add** to imports (top of file):
```python
import sqlite3
```

**Expose** `tsplib_manager._build_matrix` as public. In `tsplib_manager.py`, add a wrapper or rename:

```python
# tsplib_manager.py — add at module level (alongside existing _build_matrix):
def build_distance_matrix(coords, ewt: str):
    """Public wrapper for _build_matrix. Uses tsplib_distance_by_type."""
    return _build_matrix(coords, ewt)
```

**Add** helper function to `master_numba_engine.py` (before the `_run_benchmark_combo` function or at module level):

```python
def _query_edge_weight_type(problem_name: str, db_path: str) -> Optional[str]:
    """Query the TSPLIB DB for a problem's edge_weight_type."""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT edge_weight_type FROM problems WHERE name=?",
            (problem_name,)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None
```

**Replace** lines 642-651 (`dist_matrix_np = None ...` block) with:

```python
    dist_matrix_np = None
    if not is_time_matrix:
        problem_name = problem_dict.get("name", "")
        if problem_name:
            try:
                db_matrix = _dm_from_cache(problem_name, TSPLIB_DB)
                if db_matrix is not None:
                    dist_matrix_np = db_matrix
                else:
                    # DB cache miss — compute correct matrix type from DB metadata
                    _ewt = _query_edge_weight_type(problem_name, TSPLIB_DB)
                    if _ewt is not None and _ewt != "EUC_2D":
                        coords = problem_dict.get("coordinates", [])
                        if coords and _DIST_OK:
                            from academic_benchmark.tsplib_manager import build_distance_matrix
                            dist_matrix_np = build_distance_matrix(coords, _ewt)
            except Exception:
                pass
```

**Verification:**
```bash
# Test: Force DB cache miss for a GEO problem (e.g., burma14) and verify correct distance
# Delete its entry from distance_matrices table, then run a quick benchmark:
python -c "
from academic_benchmark.master_numba_engine import _run_benchmark_combo, 
# ... create a test problem_dict for burma14 with no DB cache ...
"
# Verify tour_length matches optimal (3323 for burma14) not ~30 (EUC_2D on lat/lon)
```

---

#### Step 1.5: Thread-Safe Global Cache

**File:** `optimizer_api/utils/local_search_numba.py`

**Add** (after imports, ~line 72):
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

**Update** `_build_or_get_dist_matrix` function (~line 98, ~line 120, ~line 134):
- Replace `if cache_key in _DIST_MATRIX_CACHE:` with `cached = _get_cached_matrix(cache_key); if cached is not None: return cached`
- Replace `_DIST_MATRIX_CACHE[cache_key] = result` with `_set_cached_matrix(cache_key, result)`

**Verification:**
```bash
# No behavior change expected — this is a defensive fix
python -m pytest optimizer_api/tests/ -k "local_search" 2>/dev/null || echo "No LS tests found, manual verification needed"
```

---

#### Step 1.6: Apply Quick Wins

**QW-6 (1 min):** Remove duplicate import at `sota_tsp/__init__.py:17`
```python
# Line 16-17: Keep only ONE line
from .base_solver import BaseTSPSolver, TSPResult
```

**QW-5 (5 min):** Add doc comments at both engines' env variable blocks explaining the OpenBLAS workaround:
```python
# Prevent OpenBLAS/NumPy crashes when using ProcessPoolExecutor on Linux/macOS.
# Each worker process would otherwise try to spawn its own BLAS thread pool,
# causing massive oversubscription and deadlocks. Setting to 1 forces single-threaded
# BLAS in each worker, which is optimal for our embarrassingly parallel workload.
# Windows is less affected but benefits from the same constraint.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
```

**Verification:**
```bash
git diff --stat  # Should show 3 files changed
python -c "from academic_benchmark.master_sota_engine import ALL_ALGOS; print('OK')"
```

---

### Phase 2: Design Improvements (Estimated: 120 min)

#### Step 2.1: Standardize on ProblemInstance (D-1)
#### Step 2.2: Route engine execution through AlgorithmRegistry (D-2)
#### Step 2.3: Consolidate SOTA parameter spaces (D-3)
#### Step 2.4: Replace param_signature with SHA256 (D-4)

*Details to be fleshed out after Phase 1 completion.*

---

### Phase 3: Code Quality (Estimated: 95 min)

#### Step 3.1: Move TSPResult to engine_core.py (Q-1)
#### Step 3.2: Extract base class for LocalSearch (Q-2)
#### Step 3.3: Parametrize HybridLocalSearch iteration limits (Q-3)
#### Step 3.4: Add config schema validation (Q-4)
#### Step 3.5: Expose _build_matrix as public (Q-5)

*Details to be fleshed out after Phase 2 completion.*

---

### Post-Implementation Verification

```bash
# 1. Verify both engines import without bildiri2026
mv academic_benchmark/bildiri2026 academic_benchmark/bildiri2026_bak
python -c "from academic_benchmark.master_numba_engine import *; print('Numba engine OK')"
python -c "from academic_benchmark.master_sota_engine import *; print('SOTA engine OK')"
python -c "from academic_benchmark.smart_benchmark import *; print('Smart benchmark OK')"

# 2. Verify AlgorithmRegistry
python -c "from academic_benchmark.engine_core import AlgorithmRegistry; print(AlgorithmRegistry.list_algorithms())"
# B-PSO and B-GA should NOT appear

# 3. Verify with bildiri2026 restored
mv academic_benchmark/bildiri2026_bak academic_benchmark/bildiri2026
python -c "from academic_benchmark.master_numba_engine import *; print('Numba engine OK (with bildiri)')"
# B-PSO and B-GA SHOULD appear

# 4. Full integration test (if available)
python -m academic_benchmark.smart_benchmark --help
```

---

## 9. Peer Review Notes

### Review Methodology
All four critical claims (C-1 through C-4) were verified by reading actual source code with line-level precision. The review checked:
1. Does the claimed code actually exist? (Yes for all)
2. Does the proposed fix interact correctly with the existing code? (Yes, with refinements)
3. Are there edge cases or logic errors the report missed? (Three found — see below)

### Refinements Applied

| # | Original Claim | Peer Review Finding | Resolution |
|---|---------------|---------------------|------------|
| 1 | C-1 fix only shows code for two engine detection functions | `ls_engine.py` has a third independent Numba detection point (`_NUMBA_OK`) that must also be fixed | Added ls_engine.py code with same `importlib.util.find_spec` pattern. All three now fixed together. |
| 2 | C-2 `_get_bildiri_strategies()` does `from core import pso_solver, ga_solver` as canary | Imports unused modules. Better to use `importlib.util.find_spec` to avoid side effects. | Changed to `find_spec("core.pso_solver")`. Added `finally: sys.path.remove()` for cleanup. |
| 3 | C-4 fix says "call _build_matrix" but DOEProblem lacks edge_weight_type | `DOEProblem` has no `edge_weight_type` field. `_build_matrix(coords, ewt)` requires `ewt`. | User chose "query DB at fallback time" approach. Added `_query_edge_weight_type()` helper + `sqlite3` import. Noted Q-5 requirement to expose `_build_matrix` as public. |
| 4 | C-3 risk level overstated | Current code uses ProcessPoolExecutor (process isolation), not ThreadPoolExecutor. API thread pool imports from `utils.local_search` (pure Python), not `utils.local_search_numba`. Race condition is theoretical in current code. | Updated fix description to note the practical risk is low. Fix remains as defensive programming. |
| 5 | `sys.path` pollution at all bildiri2026 detection points | All `_detect_numba()` functions and `_get_bildiri_strategies()` insert bildiri2026/ at `sys.path[0]` without cleanup. This hijacks the `core` namespace for all subsequent imports. | Applied `importlib.util.find_spec` (no path modification) + `finally: sys.path.remove()` as cleanup when fallback path insertion is necessary. Applied to all fix points. |
| 6 | C-4 SOTA engine immunity not explained | SOTA engine is immune to GEO/ATT bug because it never falls back to `create_np_distance_matrix` — always uses DB cache. Report noted this but didn't explain WHY. | Added explanation: SOTA engine always goes through `_dm_from_cache()` which uses pre-computed matrices from `tsplib_manager._build_matrix` (which respects edge_weight_type). |

### Architectural Decisions (User-Confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| TSPLIB_OPTIMALS consolidation | **Keep separate copies** | Avoids dependency inversion between optimizer_api and academic_benchmark. Risk of drift accepted. |
| GEO/ATT fallback fix | **Query DB at fallback time** | Minimal code changes, no data model modifications. |
| sys.path pollution fix | **Fix now** with `importlib.util.find_spec` + `finally` | Eliminates latent risk of `core` namespace hijacking. |

---

## Appendix: bildiri2026 Dependency Map

```
bildiri2026/core/
├── __init__.py          ← Exports: TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer, BaseTSPSolver, TSPResult
├── base_solver.py       ← BaseTSPSolver, TSPResult
├── numba_accel.py       ← Numba JIT kernels (_nb.NUMBA_AVAILABLE)
├── two_opt.py            ← from . import numba_accel as _nb
├── three_opt.py          ← from . import numba_accel as _nb
├── or_opt.py             ← from . import numba_accel as _nb
├── pso_solver.py         ← from . import numba_accel as _nb
└── ga_solver.py          ← from . import numba_accel as _nb

bildiri2026 entry points:
├── 1_generate_config.py  ← sys.path.insert(0, SCRIPT_DIR) + local imports only
├── 2_run_tuning.py       ← sys.path.insert(0, SCRIPT_DIR) + from core import ...
├── 3_run_benchmark.py    ← sys.path.insert(0, SCRIPT_DIR) + from core import ...
├── benchmarks/
│   ├── tsplib_benchmark.py    ← Own TSPLIB_OPTIMALS, own parse_tsplib
│   └── timematrix_benchmark.py
├── config_manager.py           ← No external dependencies
├── data_manager.py             ← No external dependencies
└── orchestrate_batch.py        ← Calls subprocess on other scripts

Consumed by academic_benchmark/:
├── master_numba_engine.py         ← Imports PSOOptimizer, GAOptimizer (lines 812-815)
├── master_numba_engine.py         ← _detect_numba() uses numba_accel (lines 139-148)
├── master_sota_engine.py          ← _detect_numba() uses numba_accel (lines 448-455)
└── sota_tsp/ls_engine.py          ← from core import numba_accel as _nb (lines 24-36)
```

---

## File Change Summary

| File | Phase 1 Critical | Phase 2 Design | Phase 3 Quality | Quick Wins |
|------|-----------------|----------------|-----------------|------------|
| master_numba_engine.py | C-1, C-2, C-4 | D-1, D-2 | Q-4 | QW-5 |
| master_sota_engine.py | C-1 | D-2, D-3 | - | QW-5 |
| sota_tsp/ls_engine.py | C-1 | - | - | - |
| sota_tsp/__init__.py | - | - | - | QW-6 |
| optimizer_api/utils/local_search_numba.py | C-3 | - | Q-2, Q-3 | - |
| tsplib_manager.py | C-4 (expose build_distance_matrix) | - | Q-5 | - |
| smart_benchmark.py | - | D-2 | - | QW-4 |
| benchmark_utils.py | - | D-4 | - | - |
| engine_core.py | - | D-1 | Q-1 | - |
| **Files touched (Phase 1 only)** | **5** | | | **2** |