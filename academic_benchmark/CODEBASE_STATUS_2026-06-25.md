# UniRide Codebase Status Report — 2026-06-25

**Author:** Opencode (glm-5.2)
**Scope:** Full project review after extended absence
**Method:** Codebase exploration, git history, test execution, architecture analysis

---

## 1. Architecture Evolution (Since Last Work)

The project has undergone a **major architectural transformation**. What was a single `academic_benchmark/` package is now a **3-layer architecture**:

```
uniride_core/          ← Layer 1: Algorithms (canonical, pure Python)
├── algorithms/        ← 48 files: SOTA, Numba, split engines, CVRP decoders
├── adapters/          ← Problem adapters (TSP, ATSP, CVRP, CVRPTW)
├── models.py          ← Shared data models
└── benchmark_runner.py← Matrix-native benchmark runner

optimizer_api/         ← Layer 2: FastAPI web layer (thin wrappers)
├── routers/           ← API endpoints
├── strategies/        ← Production strategy wrappers → delegate to uniride_core
└── main.py            ← FastAPI app

src/                   ← Layer 3: Next.js 14 frontend (React, i18n)
├── app/               ← App router
├── components/        ← React components
└── i18n/              ← next-intl localization

academic_benchmark/    ← Academic benchmarking CLI + registry
├── cli_engine.py      ← 2196 lines — consolidated engine (was master_numba + master_sota)
├── core/              ← NEW: registry_setup, doe, evaluation, cli
├── smart_benchmark.py ← Main unified CLI
└── tests/             ← 173 tests
```

**Key moves:**
- SOTA solvers: `academic_benchmark/sota_tsp/` → `uniride_core/algorithms/sota_tsp/` (old dir is empty, only `__pycache__/`)
- Engine consolidation: `master_numba_engine.py` + `master_sota_engine.py` → `cli_engine.py` (2196 lines)
- New: ALNS solver, CVRP/CVRPTW support, ATSP support, matrix-native benchmark runner, promotion manager, BKS manager

---

## 2. Test Status

| Suite | Passed | Failed | Errors | Skipped |
|-------|--------|--------|--------|---------|
| `academic_benchmark/tests/` | 168 | 4 | 3 (collection) | 1 |
| `uniride_core/tests/` | 168 | 6 | 1 (collection) | 0 |
| **Total** | **336** | **10** | **4** | **1** |

### Failures Breakdown

| # | Test | Cause | Severity |
|---|------|-------|----------|
| 1 | `test_problem_selector.py` (collection) | `_ab_dir` NameError in `cli_engine.py:155` | **CRITICAL** — blocks 3 files |
| 2 | `test_cli_engine_param_db_save.py` (collection) | Same `_ab_dir` bug | CRITICAL |
| 3 | `test_academic_cvrp_execution.py` (collection) | Same `_ab_dir` bug | CRITICAL |
| 4 | `test_critical_fixes.py` (3 tests) | Cascading: imports `smart_benchmark` → imports `cli_engine` → hits `_ab_dir` bug | CRITICAL |
| 5 | `test_benchmark_robustness.py` (1 test) | Legacy import path `optimizer_api.tests.*` no longer exists | MEDIUM |
| 6 | `test_pyvrp_cvrp_engine.py` (2 tests) | `pyvrp` not installed (optional dep) | LOW |
| 7 | `test_holistic_matrix_engine.py` (4 tests) | `pyvrp` not installed | LOW |
| 8 | `test_distance_properties.py` (collection) | `hypothesis` not installed | LOW |

---

## 3. The Critical Bug: `_ab_dir` NameError

**File:** `academic_benchmark/cli_engine.py:155`

```python
def _detect_numba() -> bool:
    ...
    if spec is None and os.path.isdir(_ab_dir):  # ← _ab_dir NOT defined here
        ...
        sys.path.remove(_ab_dir)                 # ← same
    ...

_NUMBA_AVAILABLE = _detect_numba()  # ← runs at import time, crashes
```

`_ab_dir` is defined at line 908 (inside a different function), but used at line 155 in `_detect_numba()`. This is a **scoping bug** — it crashes at import time, which cascades to `smart_benchmark.py` and 6 test files.

**Impact:** Any import of `smart_benchmark`, `cli_engine`, or anything that transitively imports them will crash with `NameError: name '_ab_dir' is not defined`.

---

## 4. Project Accomplishments (This Year)

350 commits since January 2026. Major milestones:

- ✅ 3-layer architecture (`uniride_core` → `optimizer_api` → `src`)
- ✅ CVRP/CVRPTW support (OR-Tools, PyVRP, VROOM adapters)
- ✅ ATSP support (18 instances + parser)
- ✅ ALNS solver (4 destroy + 3 repair operators, SA acceptance)
- ✅ Matrix-native benchmark runner
- ✅ Promotion manager (evidence-based config gating)
- ✅ BKS (Best Known Solutions) manager
- ✅ i18n with next-intl (en/tr, ~300 keys)
- ✅ GitHub Actions CI pipeline
- ✅ Vectorized `ProblemInstance.prepare_matrices` (NumPy)
- ✅ Thread-safe RNG per request (6 strategies)
- ✅ Asymmetric Haversine fallback

---

## 5. Improvement Recommendations

### Immediate (blocks development)

| Priority | Issue | Fix | Effort |
|----------|-------|-----|--------|
| **P0** | `_ab_dir` NameError in `cli_engine.py:155` | Add `_ab_dir = os.path.join(_ENGINE_DIR, 'bildiri2026')` before `_detect_numba()`, or pass as parameter | 5 min |
| **P0** | `test_critical_fixes.py` broken by cascade | Fixed automatically once P0 is resolved | 0 |
| **P1** | `test_benchmark_robustness.py` legacy import | Update import paths from `optimizer_api.tests.*` to `uniride_core.*` or `academic_benchmark.cli_engine` | 10 min |

### Short-term (code hygiene)

| Priority | Issue | Fix | Effort |
|----------|-------|-----|--------|
| **P2** | `hypothesis` not installed | Add to `pyproject.toml` dev dependencies | 2 min |
| **P2** | PyVRP tests fail without pyvrp | Add `pytest.importorskip("pyvrp")` at module level | 5 min |
| **P2** | Empty `academic_benchmark/sota_tsp/` dir (only `__pycache__/`) | Delete directory — solvers moved to `uniride_core` | 1 min |
| **P3** | Root-level temp files | `test_db_matrix.py`, `test_dir/`, `test_patch.py`, `test_tsplib.py`, `test_direct.py`, `.temp_master_numba.py` at repo root | Move to `tests/` or delete | 10 min |
| **P3** | Frontend `next-intl` missing | Run `npm install` | 2 min |

### Medium-term (architecture)

| Priority | Issue | Recommendation |
|----------|-------|----------------|
| **P4** | `cli_engine.py` is 2196 lines | Split into modules: `numba_engine.py`, `doe_engine.py`, `benchmark_runner.py` (the `core/` dir already has `doe.py` — finish the migration) |
| **P4** | Documentation sprawl | 4+ overlapping docs: `HOW_TO_USE.md`, `BENCHMARK_DOKUMANTASYON.md`, `CLASSICAL_PAPER_METHODOLOGY.md`, `SOTA_PAPER_METHODOLOGY.md`, master plan. Consolidate or index them. |
| **P5** | Old `master_numba_engine.py` / `master_sota_engine.py` | Verify they're still used or are dead code — `cli_engine.py` appears to replace them |
| **P5** | `HOW_TO_USE.md` is outdated | References `master_numba_engine.py` and `master_sota_engine.py` as standalone CLIs, but `cli_engine.py` is the new consolidated engine. Update to reflect current architecture. |
| **P5** | `AUDIT_FINDINGS_2026-05-19.md` | Our previous audit fixes (C-01 through H-07) were applied to `master_numba_engine.py`/`master_sota_engine.py`, but the code has since been consolidated into `cli_engine.py`. Verify fixes survived the migration. |

### Strategic (future direction)

| Priority | Area | Recommendation |
|----------|------|----------------|
| **P6** | CVRP validation | Master plan says "full large-dataset validation remains pending" — run CVRPLIB benchmarks at scale |
| **P6** | Web/API sanity path | Master plan marks this as "⏳ Next" — verify matrix-native web execution with editable params |
| **P7** | SOTA for CVRP | Master plan says SOTA solvers have CVRP wrappers but need validation. Benchmark E²BSO/R²DMA/ALNS on CVRPLIB. |
| **P7** | Remaining SOTA candidates | `SOTA_ALGORITHM_CANDIDATES.md` lists SMA, APO, GTO, DBO as not-yet-implemented. Consider if still relevant. |

---

## 6. What To Do Right Now

1. **Fix the `_ab_dir` bug** (5 min) — this unblocks 6+ tests and makes the CLI importable
2. **Update `test_benchmark_robustness.py`** (10 min) — fix legacy import path
3. **Add `pytest.importorskip` for optional deps** (5 min) — pyvrp, hypothesis
4. **Delete empty `sota_tsp/` dir** (1 min)
5. **Run `npm install`** (2 min) — fixes frontend typecheck
6. **Update `HOW_TO_USE.md`** to reflect `cli_engine.py` architecture

---

## Appendix: File Size Reference

### `academic_benchmark/` (largest files)

| File | Lines |
|------|-------|
| `cli_engine.py` | 2196 |
| `tsplib_manager.py` | 1003 |
| `smart_benchmark.py` | 930 |
| `benchmark_utils.py` | 807 |
| `sota_engine.py` | 595 |
| `dashboard.py` | 565 |

### `uniride_core/algorithms/` (largest files)

| File | Lines |
|------|-------|
| `local_search_numba.py` | 1052 |
| `local_search.py` | 740 |
| `tsp_meta_engines.py` | 655 |
| `string_split_decoder.py` | 573 |
| `resource_profiler.py` | 563 |
| `time_window_violation_tracker.py` | 514 |
| `tsplib_parser.py` | 413 |
| `ga_split_engine.py` | 353 |

### Test Counts

| Suite | Tests (collected) | Status |
|-------|-------------------|--------|
| `academic_benchmark/tests/` | 173 | 168 pass, 4 fail, 3 collection errors, 1 skip |
| `uniride_core/tests/` | 174 | 168 pass, 6 fail, 1 collection error |
| **Total** | **347** | **336 pass (97%)** |

---

## Git Context

- **Commits since 2026-01-01:** 350
- **Working tree:** 2 modified files (`.codegraph/.gitignore`, `academic_benchmark/HOW_TO_USE.md`)
- **No uncommitted source code changes** — clean working tree apart from docs/config
