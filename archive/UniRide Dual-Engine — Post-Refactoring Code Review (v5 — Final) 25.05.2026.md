# UniRide Dual-Engine — Post-Refactoring Code Review (v5 — Final)

**Date:** 25.05.2026  
**Reviewer:** Senior Software Engineer / Solutions Architect / Research Technical Lead  
**Scope:** Full dual-engine architecture (UniRide Production + Academic Benchmark)  
**Exclusions:** `node_modules/`, `.venv/`, `__pycache__/`, `archive/`, `paper_prompts/`, `numba_results/`, `sota_results/`, `.db`/`.sqlite` binary dumps

---

## 1. Executive Summary

UniRide is a **dual-engine platform** bridging production-grade CVRPTW (Capacitated Vehicle Routing Problem with Time Windows) optimization for university student transportation with a rigorous academic TSP benchmark research framework. The architecture comprises:

| Engine | Stack | Role |
|--------|-------|------|
| **Engine A: UniRide Production** | Next.js 16 + FastAPI + Supabase | Live route optimization, passenger-vehicle matching, IE resource analysis |
| **Engine B: Academic Benchmark** | Python CLI + Numba JIT + Optuna | DOE-driven metaheuristic benchmarking against TSPLIB |
| **Shared Kernel** | `uniride_core` (Python) | Canonical models, SOTA solvers, TSPLIB parser, distance functions |

**Overall Post-Refactor Health: 7.5/10** — The refactoring successfully consolidated 6+ scattered benchmark files into a unified `academic_benchmark/` package, established `uniride_core/` as a shared kernel, and created a clean strategy registry pattern. However, **significant architectural debt remains**: dual SOTA implementations, a broken integration path, a hardcoded API key security vulnerability, and effectively disabled linting across the entire TypeScript codebase.

**Production Readiness: MODERATE** — The production API is well-structured with proper error handling, CORS, and graceful degradation for optional dependencies. The main blockers for production are the disabled ESLint config, singleton config mutation risk, and the orphaned `faz0_interactive.py` research script.

---

## 2. Dual-Engine Integration Review

### 2.1 Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Next.js 16 Frontend (src/)                       │
│  ┌─────────┐  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │ UI Pages │  │  API Routes  │  │  Services (optimizer-service)  │  │
│  │ (app/)   │  │  (api/)      │  │  (benchmark-service)           │  │
│  └────┬─────┘  └──────┬───────┘  └───────────────┬────────────────┘  │
│       │               │                          │                   │
│       └───────────────┼──────────────────────────┘                   │
│                       │                                              │
│              ┌────────▼────────┐                                     │
│              │  Auth Context   │                                     │
│              │  (Supabase)     │                                     │
│              └────────┬────────┘                                     │
└───────────────────────┼──────────────────────────────────────────────┘
                        │ HTTP/REST
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│              optimizer_api (FastAPI, port 8000)                       │
│                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ optimize   │ │ strategies │ │ utils    │ │ benchmark          │  │
│  │ router     │ │ router     │ │ router   │ │ router             │  │
│  └─────┬──────┘ └─────┬──────┘ └────┬─────┘ └──────┬─────────────┘  │
│        │              │             │               │                │
│  ┌─────▼──────────────▼─────────────▼───────────────▼─────────────┐  │
│  │           STRATEGY_REGISTRY (27 algorithms)                     │  │
│  │  Pipeline A (GA/PSO/GWO/HHO) │ Pipeline B (Split-based)       │  │
│  │  Holistic (OR-Tools/PyVRP)   │ SOTA (E²BSO/R²DMA/P-AOEA)     │  │
│  └─────────────────────────┬──────────────────────────────────────┘  │
│                            │                                         │
│  ┌─────────────────────────▼──────────────────────────────────────┐  │
│  │           uniride_core (shared kernel)                          │  │
│  │  models.py │ algorithms/ │ sota_tsp/ │ tsplib_parser.py       │  │
│  └─────────────────────────┬──────────────────────────────────────┘  │
│                            │                                         │
└────────────────────────────┼─────────────────────────────────────────┘
                             │ Python imports
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│           academic_benchmark (research harness)                       │
│  engine_core.py │ sota_engine.py │ cli_engine.py │ smart_benchmark  │
│  tsplib_manager.py │ param_spaces.py │ benchmark_utils.py          │
│  — NOT deployed in production —                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Integration Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Shared Kernel (`uniride_core`)** | ✅ Good | Clean dataclasses, framework-agnostic, proper PEP 561 marker |
| **Strategy Registry Pattern** | ✅ Good | 27 algorithms, clean ABC, graceful optional dependency handling |
| **SOTA Adapter Wrappers** | ✅ Good | `ebso_strategy.py` etc. adapt `BaseTSPSolver` → `BaseRoutingStrategy` |
| **Data Model Sharing** | ⚠️ Moderate | `ProblemInstance` mixes TSPLIB + production fields |
| **SOTA Code Duplication** | 🔴 Critical | Two parallel implementations (see §3.1) |
| **Broken Integration Path** | 🔴 Critical | `run_sota_benchmark.py` → nonexistent module |
| **TSPLIB Opticals Sync** | ⚠️ Moderate | Different dictionaries with different coverage |
| **Benchmark Infrastructure** | ⚠️ Moderate | Two completely separate systems, no code reuse |

---

## 3. Deep-Dive Technical Analysis

### 3.1 🔴 CRITICAL: Dual SOTA Implementations (Code Duplication)

**Finding:** Two complete SOTA solver implementations exist in parallel:

| Location | Version | Used By | Indexing |
|----------|---------|---------|----------|
| `uniride_core/algorithms/sota_tsp/` | v1.0 (adapted) | Production wrappers + Academic benchmark | Integer-indexed |
| `optimizer_api/strategies/sota_common/` | v3.0 (original FAZ 0) | `faz0_interactive.py` only | String-indexed |

The `sota_tsp/` versions contain explicit adaptation comments:
```python
# uniride_core/algorithms/sota_tsp/e2bso_tsp.py
"""
Adapted from optimizer_api/strategies/sota_common/e2bso.py for pure TSP.
Uses integer-indexed tours and Numba-accelerated distance matrix.
"""
```

**Impact:** Any bug fix or improvement in one implementation does not propagate to the other. The `sota_common/` versions contain standalone infrastructure (`MultiLayerLS`, `PenaltyManager`, `SimulatedAnnealing`, `LateAcceptanceHC`, destroy/repair operators, `DiversityController`) that duplicates code in `sota_tsp/` (`ls_engine.py`, `destroy_ops.py`, `repair_ops.py`).

**Risk:** The `faz0_interactive.py` script in `optimizer_api/` imports from `sota_common/`, meaning it runs a completely different code path than the production API. Research results obtained via `faz0_interactive.py` may not be reproducible through the production API.

### 3.2 🔴 CRITICAL: Broken Integration Path

**File:** `optimizer_api/run_sota_benchmark.py`
```python
from academic_benchmark.run_sota_benchmark import main  # MODULE DOES NOT EXIST
```

The module `academic_benchmark.run_sota_benchmark` does not exist. This is dead code that will crash at import time.

### 3.3 🔴 CRITICAL: Hardcoded API Key (Security Vulnerability)

**File:** `test_direct.py` (root level)
```python
api_key = "YF7tYODTYg1IWyfvkc0LGFUBadElrLZFnvzqWxPzIJMcZzG6j8VlJQQJ99CDACfhMk5XJ3w3AAAAACOGayNH"
```

This is an Azure OpenAI API key committed to the repository. It must be **rotated immediately** and the file should be removed or the key moved to environment variables.

### 3.4 🔴 CRITICAL: Hidden Reverse Dependency

**File:** `uniride_core/algorithms/tsplib_parser.py`
```python
TSPLIB_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..',
                                'optimizer_api', 'tests', 'tsplib_data')
```

The shared kernel (`uniride_core`) references a path inside the production package (`optimizer_api`). This creates a **reverse dependency** — the core should not depend on any specific deployment package. The academic engine, which also uses `uniride_core`, has its own `tsplib_data/` directory and `tsplib_manager.py` with a SQLite cache, making this path reference even more inappropriate.

### 3.5 🟡 SIGNIFICANT: ESLint Completely Disabled

**File:** `eslint.config.mjs`
```javascript
rules: {
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/no-unused-vars": "off",
    "no-console": "off",
    "prefer-const": "off",
    "no-unused-vars": "off",
    // ... 15+ more rules disabled
}
```

Every TypeScript/JavaScript linting rule is disabled. This means `any` types, unused variables, `console.log` statements, and type safety issues go completely undetected across the entire Next.js frontend and API route codebase.

### 3.6 🟡 SIGNIFICANT: Singleton Config Mutation Risk

**File:** `optimizer_api/strategies/__init__.py`
```python
# All strategies are module-level singletons
_ga_strategy = GeneticAlgorithmStrategy()
_pso_strategy = PSOStrategy()
# ... 20+ more singletons in STRATEGY_REGISTRY
```

While the P1-2 fix added `effective_config = dict(self.config)` pre-init in some strategies, the singleton pattern remains fragile. If any strategy mutates `self.config` during `optimize()`, all subsequent requests are affected. This is a **race condition risk** under concurrent FastAPI requests.

### 3.7 🟡 SIGNIFICANT: Duplicate Hook Files

Both `src/hooks/use-mobile.ts` and `src/hooks/use-mobile.tsx` exist with **identical content**:
```typescript
// Both files contain the exact same useIsMobile() implementation
import * as React from "react"
const MOBILE_BREAKPOINT = 768
export function useIsMobile() { ... }
```

This creates import confusion and maintenance overhead.

### 3.8 🟡 SIGNIFICANT: ALNS Missing DoE Parameter Space

**File:** `academic_benchmark/param_spaces.py`

ALNS-TSP is registered in `SOTA_ALGO_MAP` and the algorithm registry, but has **no entry** in `SOTA_PARAM_SPACES`. The `_get_sota_param_space("ALNS-TSP")` function returns `{}`, meaning DoE tuning for ALNS always uses empty defaults. Given that ALNS has the most complex config (iterations, max_no_improve, remove_ratio, segment_length, weight_update_factor, noise_scale, SA params), this is a significant gap.

### 3.9 🟡 SIGNIFICANT: Triple Local Search Implementation

Local search exists in three separate locations:

| Location | Used By |
|----------|---------|
| `optimizer_api/utils/local_search.py` | Production strategies (GA, PSO, GWO, HHO wrappers) |
| `optimizer_api/strategies/sota_common/multi_layer_ls.py` | FAZ 0 SOTA infrastructure (used by `faz0_interactive.py`) |
| `uniride_core/algorithms/sota_tsp/ls_engine.py` | SOTA TSP solvers (used by both engines) |

### 3.10 🟡 SIGNIFICANT: Signal Handler Conflict

Both `cli_engine.py` and `smart_benchmark.py` install their own `signal.SIGINT` handlers. When `smart_benchmark` imports from `cli_engine`, the last import's handler wins, potentially breaking graceful shutdown in one engine.

### 3.11 🟡 SIGNIFICANT: `_calculate_scheduled_times` — Scheduling Logic in Route Handler

**File:** `optimizer_api/routers/optimization.py` (~120 lines)

The `_calculate_scheduled_times` function is a large, complex scheduling algorithm embedded directly in the route handler file. It handles backward scheduling (pickup), forward scheduling (dropoff), time window extraction, and arrival time calculation — all as a standalone function rather than in a dedicated scheduling module.

### 3.12 🟡 MODERATE: `ProblemInstance` Mixed Concerns

**File:** `uniride_core/models.py`
```python
@dataclass
class ProblemInstance:
    # TSPLIB-specific fields
    source: str = "tsplib"
    file_path: Optional[str] = None
    edge_weight_type: str = "EUC_2D"
    
    # Production-specific fields
    capacity: Optional[int] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
    num_vehicles: Optional[int] = None
```

This single dataclass serves both TSPLIB research problems and production CVRPTW problems. A cleaner approach would use separate types or inheritance.

### 3.13 🟡 MODERATE: `TSPLIB_OPTIMALS` Dictionary Divergence

| Location | Entry Count | Coverage |
|----------|-------------|----------|
| `uniride_core/algorithms/tsplib_parser.py` | ~80 entries | Basic STSP |
| `academic_benchmark/benchmark_utils.py` | 129 entries | STSP + ATSP + large instances |

The academic benchmark has a **superset** of known optimals. If the production engine and research engine compute gaps against different baselines, results will diverge.

### 3.14 🟢 POSITIVE: Clean Strategy Pattern

The `BaseRoutingStrategy` ABC with a registry pattern is well-designed:
```python
class BaseRoutingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse: ...
```

Adding new algorithms requires only implementing the ABC and registering in `STRATEGY_REGISTRY`. The optional dependency handling for PyVRP and VROOM is graceful.

### 3.15 🟢 POSITIVE: IE Resource Profiler

The `ResourceProfiler` module provides sophisticated industrial engineering analysis:
- Vehicle need calculation (Sw/So disability type breakdown)
- Hourly demand analysis
- Bottleneck detection with severity classification
- Time shift suggestions with slack window configuration
- Environment-based scheduling configuration (`DEFAULT_PICKUP_HOUR`, `DEFAULT_DROPOFF_HOUR`)

### 3.16 🟢 POSITIVE: Split Decoder Quality

Both classic O(n²) Prins (2004) and SOTA bounded split decoders are implemented with full time window support, backward/forward scheduling, and direction awareness. The implementation is well-documented with academic references.

### 3.17 🟢 POSITIVE: Thread-Safe Benchmark State

`BenchmarkStateManager` uses proper `threading.Lock` for concurrent access, TTL-based eviction, and a max concurrent run limit (3). This is production-quality state management.

### 3.18 🟢 POSITIVE: Global Exception Handler

```python
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

The production API never leaks internal error details to clients. All exceptions are logged server-side.

---

## 4. Concrete Refactoring Recommendations

### 4.1 Fix Broken `run_sota_benchmark.py`

**Before:**
```python
# optimizer_api/run_sota_benchmark.py
from academic_benchmark.run_sota_benchmark import main  # DOES NOT EXIST
if __name__ == "__main__":
    sys.exit(main())
```

**After:**
```python
# optimizer_api/run_sota_benchmark.py
"""
SOTA Benchmark Runner — delegates to academic_benchmark.sota_engine.

Usage: python run_sota_benchmark.py --algo E2BSO-TSP --problems berlin52,eil51
"""
import sys
import argparse
from academic_benchmark.sota_engine import (
    run_engine_default, run_engine_tuning, ALL_ALGOS,
)

def main():
    parser = argparse.ArgumentParser(description="UniRide SOTA Benchmark Runner")
    parser.add_argument("--algo", nargs="+", default=ALL_ALGOS,
                        help=f"Algorithms to benchmark. Available: {ALL_ALGOS}")
    parser.add_argument("--problems", nargs="+", default=None,
                        help="TSPLIB problem names (default: all small)")
    parser.add_argument("--tune", action="store_true",
                        help="Run DoE parameter tuning before benchmarking")
    parser.add_argument("--runs", type=int, default=3,
                        help="Number of runs per configuration")
    args = parser.parse_args()

    if args.tune:
        for algo in args.algo:
            run_engine_tuning(algo, problems=args.problems, n_runs=args.runs)

    for algo in args.algo:
        run_engine_default(algo, problems=args.problems, n_runs=args.runs)

if __name__ == "__main__":
    sys.exit(main())
```

### 4.2 Remove Hardcoded API Key

**Immediate action required:**
1. Rotate the Azure OpenAI API key (it's compromised in the repository)
2. Delete `test_direct.py` or replace with environment-based configuration:

```python
# test_direct.py — FIXED
import os
from openai import OpenAI

endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "DeepSeek-V3.2-Speciale-1")
api_key = os.environ.get("AZURE_OPENAI_API_KEY")

if not all([endpoint, api_key]):
    raise RuntimeError("Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY env vars")

client = OpenAI(base_url=endpoint, api_key=api_key)
```

### 4.3 Fix Hidden Reverse Dependency in `tsplib_parser.py`

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

# Default TSPLIB data directory — can be overridden via environment variable
TSPLIB_DATA_DIR = os.environ.get(
    "TSPLIB_DATA_DIR",
    os.path.join(os.path.dirname(__file__), '..', '..', 'tsplib_data')
)
```

### 4.4 Consolidate Dual SOTA Implementations

**Recommended approach:** Deprecate `optimizer_api/strategies/sota_common/` entirely.

1. Move any unique functionality from `sota_common/` into `uniride_core/algorithms/sota_tsp/`
2. Update `faz0_interactive.py` to import from `uniride_core.algorithms.sota_tsp`
3. Delete `optimizer_api/strategies/sota_common/` directory
4. Update `optimizer_api/tests/` imports if any reference `sota_common/`

### 4.5 Add ALNS DoE Parameter Space

**Before:** ALNS has no entry in `SOTA_PARAM_SPACES`

**After:**
```python
# academic_benchmark/param_spaces.py — add to SOTA_PARAM_SPACES:
"ALNS-TSP": {
    "max_iterations":      {"type": "int",   "doe": [500, 1000, 2000],    "optuna": (200, 3000)},
    "max_no_improve":      {"type": "int",   "doe": [50, 100, 200],       "optuna": (20, 300)},
    "remove_ratio":        {"type": "float", "doe": [0.10, 0.20, 0.30],    "optuna": (0.05, 0.40)},
    "segment_length":      {"type": "int",   "doe": [3, 5, 8],            "optuna": (2, 12)},
    "weight_update_factor":{"type": "float", "doe": [0.1, 0.3, 0.5],      "optuna": (0.05, 0.7)},
    "noise_scale":         {"type": "float", "doe": [0.05, 0.10, 0.20],   "optuna": (0.01, 0.30)},
    "sa_initial_temp":     {"type": "float", "doe": [100.0, 500.0, 1000.0], "optuna": (50.0, 2000.0)},
    "sa_cooling_rate":     {"type": "float", "doe": [0.95, 0.98, 0.99],   "optuna": (0.90, 0.995)},
    "time_limit":          {"type": "float", "doe": [300.0, 600.0, 1200.0], "optuna": None},
},
```

### 4.6 Fix Singleton Config Mutation Risk

**Before:**
```python
# optimizer_api/strategies/__init__.py
_ga_strategy = GeneticAlgorithmStrategy()
STRATEGY_REGISTRY = {"genetic_algorithm": _ga_strategy, ...}
```

**After:**
```python
# optimizer_api/strategies/__init__.py
from typing import Dict, Optional, Type

# Registry mapping name -> strategy CLASS (not instance)
STRATEGY_REGISTRY_CLASSES: Dict[str, Optional[Type[BaseRoutingStrategy]]] = {
    "genetic_algorithm": GeneticAlgorithmStrategy,
    "ga": GeneticAlgorithmStrategy,
    "pso": PSOStrategy,
    # ... etc
}

# Thread-local storage for strategy instances
import threading
_thread_local = threading.local()

def get_strategy(name: str) -> Optional[BaseRoutingStrategy]:
    """Get or create a thread-local strategy instance."""
    if not hasattr(_thread_local, 'strategies'):
        _thread_local.strategies = {}
    
    if name not in _thread_local.strategies:
        cls = STRATEGY_REGISTRY_CLASSES.get(name)
        _thread_local.strategies[name] = cls() if cls else None
    
    return _thread_local.strategies[name]
```

### 4.7 Re-enable Critical ESLint Rules

**Before:** All rules disabled

**After:**
```javascript
// eslint.config.mjs
rules: {
    // Keep these off for gradual migration:
    "@typescript-eslint/no-explicit-any": "warn",  // Changed from "off" to "warn"
    
    // Re-enable critical rules:
    "@typescript-eslint/no-unused-vars": "warn",   // Re-enabled
    "no-console": "warn",                           // Re-enabled (allow in dev)
    "prefer-const": "warn",                         // Re-enabled
    "no-unused-vars": "warn",                       // Re-enabled
    
    // Keep off for React/Next.js compatibility:
    "react-hooks/exhaustive-deps": "off",
    "@next/next/no-img-element": "off",
}
```

### 4.8 Remove Duplicate Hook File

Delete either `src/hooks/use-mobile.ts` or `src/hooks/use-mobile.tsx` (they are identical). Keep the `.tsx` version since it's in a React project and update any imports referencing the `.ts` version.

### 4.9 Extract Scheduling Logic from Route Handler

**Before:** `_calculate_scheduled_times` (~120 lines) in `routers/optimization.py`

**After:** Create `optimizer_api/utils/scheduling.py`:
```python
# optimizer_api/utils/scheduling.py
"""
Scheduling utilities for CVRPTW route optimization.

Handles backward scheduling (pickup) and forward scheduling (dropoff)
with time window constraints.
"""
from typing import List, Dict, Optional
from models.schemas import VehicleRoute, OptimizationRequest, Direction
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

def calculate_scheduled_times(
    routes: List[VehicleRoute],
    request: OptimizationRequest,
    distance_matrix: Dict[str, Dict[str, float]]
) -> List[VehicleRoute]:
    """Calculate arrival/departure times for routes with time window constraints."""
    # ... extracted from optimization.py ...

def minutes_to_time(minutes: float) -> str:
    """Convert minutes from midnight to HH:MM string."""
    total = max(0, min(int(minutes), 23 * 60 + 59))
    return f"{total // 60:02d}:{total % 60:02d}"
```

### 4.10 Unify `TSPLIB_OPTIMALS` Dictionary

**Before:** Two separate dictionaries in two files

**After:** Add to `uniride_core/algorithms/tsplib_parser.py`:
```python
# Import the comprehensive dictionary from academic_benchmark
# This makes uniride_core the single source of truth
from academic_benchmark.benchmark_utils import TSPLIB_OPTIMALS as _FULL_OPTIMALS

# Re-export for backward compatibility
TSPLIB_OPTIMALS = _FULL_OPTIMALS
```

Or better, move the comprehensive dictionary into `uniride_core` and have `academic_benchmark` import from there.

---

## 5. Quick Wins & Long-Term Roadmap

### Quick Wins (1-2 days each, high impact)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 1 | **Rotate API key** and fix `test_direct.py` | 🔴 Security | 30 min |
| 2 | **Fix `run_sota_benchmark.py`** or delete it | 🔴 Broken code | 1 hour |
| 3 | **Fix `TSPLIB_DATA_DIR`** reverse dependency | 🟡 Architecture | 30 min |
| 4 | **Delete duplicate `use-mobile.ts`** | 🟢 Cleanup | 15 min |
| 5 | **Re-enable critical ESLint rules** (warn mode) | 🟡 Code quality | 1 hour |
| 6 | **Add ALNS DoE parameter space** | 🟡 Research gap | 2 hours |
| 7 | **Add `__init__.py`** to `uniride_core/algorithms/` | 🟢 Import fix | 15 min |
| 8 | **Delete `src/app/api/route.ts`** (dead "Hello, world!" stub) | 🟢 Cleanup | 5 min |

### Medium-Term (1-2 weeks each)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 9 | **Consolidate dual SOTA implementations** — deprecate `sota_common/` | 🔴 Architecture | 1 week |
| 10 | **Unify `TSPLIB_OPTIMALS`** into `uniride_core` as single source of truth | 🟡 Data integrity | 2 hours |
| 11 | **Refactor singleton strategies** to thread-local pattern | 🟡 Concurrency | 2 days |
| 12 | **Extract scheduling logic** from `optimization.py` into `utils/scheduling.py` | 🟡 Modularity | 1 day |
| 13 | **Add tests for `cli_engine.py`** and `smart_benchmark.py` | 🟡 Test coverage | 3 days |
| 14 | **Resolve signal handler conflict** between `cli_engine` and `smart_benchmark` | 🟡 Reliability | 1 day |
| 15 | **Add rate limiting middleware** (config.ts has `RATE_LIMIT_REQUESTS_PER_MINUTE` but no middleware) | 🟡 Security | 1 day |

### Long-Term Roadmap (1-3 months)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 16 | **Separate `ProblemInstance` into `TSPProblem` and `CVRPTWProblem`** | 🟡 Architecture | 1 week |
| 17 | **Shared benchmark infrastructure** — unify production benchmark router with academic engine | 🟡 Code reuse | 2 weeks |
| 18 | **Statistical rigor in DoE** — add confidence intervals, hypothesis testing, effect size reporting | 🟡 Research quality | 2 weeks |
| 19 | **Full ESLint re-enablement** with gradual migration to strict mode | 🟢 Code quality | 2 weeks |
| 20 | **Performance profiling** of matching algorithms under production load | 🟡 Performance | 1 week |
| 21 | **Migrate `faz0_interactive.py`** into `academic_benchmark/` or delete | 🟢 Cleanup | 3 days |
| 22 | **Add integration tests** for the full tune→benchmark→report pipeline | 🟡 Test coverage | 1 week |

---

## 6. Summary Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| **Post-Refactoring Cleanliness** | 7/10 | Good consolidation, but dual SOTA and orphaned scripts remain |
| **Architecture & Modularity** | 7.5/10 | Clean strategy pattern, but singleton risks and mixed concerns |
| **Code Quality** | 6/10 | ESLint disabled, duplicate files, but good type hints in Python |
| **Type Safety** | 6.5/10 | Python side well-typed; TypeScript side has no linting |
| **Performance** | 8/10 | Numba JIT, split decoder, KNN masks, thread-safe state management |
| **Security** | 5/10 | Hardcoded API key, no rate limiting, but good CORS and error handling |
| **Test Coverage** | 5/10 | Good SOTA E2E tests, but zero coverage for cli_engine and smart_benchmark |
| **DOE Rigor** | 6/10 | Systematic grid search + Optuna, but no statistical validation or ALNS coverage |
| **Academic Rigor** | 7/10 | Good reproducibility, seed management, TSPLIB coverage; missing confidence intervals |
| **Production Readiness** | 6.5/10 | Solid API design, but linting, singleton risks, and security issues need addressing |
| **Overall** | **6.8/10** | A well-architected dual-engine system with clear separation of concerns, held back by post-refactoring cleanup items and security concerns |
