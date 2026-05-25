# UniRide Dual-Engine Architecture Verification Report
### Generated on: 2026-05-25 14:30:00 UTC
#### Prepared by: opencode (powered by arcee-ai/trinity-large-thinking:free)

---

## Executive Summary

This report provides an independent verification of the UniRide codebase following the v5 code review (25 May 2026). The analysis confirms **8 critical findings** from the review, assesses the dual-engine architecture, and proposes a safe refactoring strategy to improve cohabitation between the production API and academic benchmark systems.

---

## 1. Fact-Check Matrix

| Finding | Verdict | Evidence |
|---------|---------|----------|
| **3.1 Dual SOTA Implementations** | VERIFIED | Two separate SOTA implementations exist: `uniride_core/algorithms/sota_tsp/` (6 files) and `optimizer_api/strategies/sota_common/` (9 files) with overlapping functionality but different data structures. |
| **3.2 Broken Integration Path** | VERIFIED | `optimizer_api/run_sota_benchmark.py` imports non-existent `academic_benchmark.run_sota_benchmark`. |
| **3.3 Hardcoded API Key** | VERIFIED | `optimizer_api/test_direct.py` contains a real Azure OpenAI API key. |
| **3.4 Hidden Reverse Dependency** | VERIFIED | `uniride_core/algorithms/tsplib_parser.py` hardcodes path to `optimizer_api/tests/tsplib_data`. |
| **3.6 Singleton Mutation Risk** | VERIFIED | `STRATEGY_REGISTRY` in `optimizer_api/strategies/__init__.py` uses a mutable singleton, risking race conditions under concurrent FastAPI requests. |
| **3.8 ALNS Missing DoE Parameter Space** | VERIFIED | `SOTA_PARAM_SPACES` in `academic_benchmark/param_spaces.py` does not include ALNS-TSP, preventing proper DoE tuning. |
| **3.9 Triple Local Search** | VERIFIED | Three separate local search implementations: `optimizer_api/utils/local_search.py`, `optimizer_api/strategies/sota_common/multi_layer_ls.py`, and `uniride_core/algorithms/sota_tsp/ls_engine.py`. |
| **3.10 Signal Handler Conflict** | VERIFIED | Both `cli_engine.py` and `smart_benchmark.py` install SIGINT handlers, causing conflicts when both modules are imported. |

---

## 2. Dual-Engine Architecture Assessment

### Current State Analysis

The codebase contains **two independent benchmark systems**:

#### Academic Benchmark (`academic_benchmark/`)
- **CLI-based** with interactive menus
- Uses `AlgorithmRegistry` to manage executor callables
- Supports DoE grid search + Optuna Bayesian tuning
- Stores results in CSV/JSON/SQLite
- Parallelism via `ProcessPoolExecutor`

#### Optimizer API Benchmark (`optimizer_api/`)
- **REST API** endpoints for web UI
- Uses `STRATEGY_REGISTRY` with real strategy instances
- No built-in tuning capability
- In-memory state management
- Single-threaded daemon execution

#### Shared Core (`uniride_core/`)
- Contains mathematical models and algorithms
- **Problem:** Currently has hidden dependencies on both engines
- **Risk:** Tight coupling prevents independent evolution

### Key Architectural Issues

1. **Circular Dependencies:** Core imports API test data; API imports core; academic imports both.
2. **Duplication:** SOTA algorithms implemented three times (core + two engines).
3. **Thread Safety:** Singleton registries not safe for concurrent web requests.
4. **Configuration Leakage:** Production secrets committed to git.
5. **Signal Conflicts:** Multiple modules installing signal handlers.

---

## 3. Cohabitation Blueprint

### Core Principle: Strict Separation of Concerns

```
uniride_core/                      # PURE MATHEMATICAL LAYER
├── models/                        # Abstract base classes only
│   ├── BaseProblemInstance
│   ├── BaseLocation
│   ├── BaseVehicle
│   └── BaseStudent
├── algorithms/
│   ├── distance.py                # All distance computations
│   ├── local_search.py            # Unified interface + implementations
│   ├── tsplib_parser.py           # Pure parser (no external deps)
│   ├── sota_tsp/                  # Consolidated SOTA solvers
│   └── split_decoder/             # CVRPTW split decoder (ATSP support)
└── utils/                         # Pure utilities

optimizer_api/                     # PRODUCTION ENGINE
├── routers/                       # FastAPI endpoints
├── strategies/                    # Production routing strategies
│   ├── base_strategy.py          # Base class with uniride_core injection
│   ├── hybrid_base_strategy.py
│   ├── ... (all existing strategies)
│   └── sota_bridge.py            # Adapter for uniride_core SOTA solvers
├── models/schemas.py              # Pydantic models (inherit from core)
├── utils/                         # Production utilities (data_loader, etc.)
└── __init__.py

academic_benchmark/                # RESEARCH ENGINE
├── engine_core.py                 # Registry + executor abstractions
├── cli_engine.py                  # Numba CLI engine (consumes uniride_core)
├── sota_engine.py                 # SOTA engine (consumes uniride_core)
├── smart_benchmark.py             # Unified orchestrator
├── param_spaces.py                # Parameter spaces (consumes uniride_core)
└── __init__.py
```

### Critical Changes

1. **Move `sota_common/` to `uniride_core/algorithms/sota_tsp/`** — consolidate all SOTA solvers.
2. **Remove all cross-references** between core and engines.
3. **Introduce abstract base classes** in core; concrete implementations in engines.
4. **Make core import-safe** — no side effects, no hardcoded paths.
5. **Thread-safe registry** in API with proper locking or per-request instances.

---

## 4. Safe Refactoring Roadmap

### Phase 1: Immediate Safety Fixes (Low Risk)

| Priority | Change | Files | Impact |
|----------|--------|-------|--------|
| P0 | Remove hardcoded API key | `optimizer_api/test_direct.py` | Prevents secret leakage |
| P0 | Delete dead `.temp_master_numba.py` | Root | Removes dead code |
| P1 | Fix signal handler conflict | `smart_benchmark.py` | Prevents crashes |
| P1 | Add ALNS parameter space | `academic_benchmark/param_spaces.py` | Enables DoE tuning |

### Phase 2: Consolidation (Medium Risk)

| Priority | Change | Files | Impact |
|----------|--------|-------|--------|
| P2 | Merge triple local search | `optimizer_api/utils/local_search.py`, `optimizer_api/strategies/sota_common/multi_layer_ls.py`, `uniride_core/algorithms/sota_tsp/ls_engine.py` | Eliminates duplication |
| P2 | Fix reverse dependency | `uniride_core/algorithms/tsplib_parser.py` | Decouples core from API |
| P2 | Consolidate SOTA implementations | Move `sota_common/` to core, update both engines | Major reduction in duplication |

### Phase 3: Architecture Improvements (High Risk)

| Priority | Change | Files | Impact |
|----------|--------|-------|--------|
| P3 | Thread-safe registry | `optimizer_api/strategies/__init__.py` | Production safety |
| P3 | Abstract problem models | `uniride_core/models.py` | Enables TSPLIB vs CVRPTW polymorphism |
| P3 | Remove all cross-engine imports | Multiple files | Complete decoupling |

---

## 5. Verification Summary

✅ **All 8 critical findings verified** via CodeGraph structural analysis  
✅ **No false alarms** — all reported issues are real and present in the codebase  
✅ **Architecture assessment complete** — clear picture of dual-engine cohabitation challenges  
✅ **Refactoring plan established** — prioritized, safe-to-execute roadmap  

---

## 6. Next Steps

1. **Execute Phase 1** immediately (simple, high-impact fixes)
2. **Review Phase 2** with team — requires careful testing of both engines
3. **Plan Phase 3** as a longer-term project with proper test coverage

---

**Report End**  
Generated by: opencode (arcee-ai/trinity-large-thinking:free)  
Timestamp: 2026-05-25 14:30:00 UTC