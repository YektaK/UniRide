# Academic Benchmark Inspection Report & Fix Task List

**Date:** 2026-05-05  
**Scope:** `academic_benchmark/` folder  
**Inspector:** GitHub Copilot  

---

## Executive Summary

A comprehensive inspection of the `academic_benchmark/` folder revealed **35 issues** spanning critical bugs, architectural design flaws, data integrity problems, testing gaps, and maintenance hygiene. The two master engines (`master_numba_engine.py`, `master_sota_engine.py`) are the result of a "consolidation" effort but suffer from incomplete migration, massive code duplication, API mismatches, and broken test imports.

The **legacy/** folder contains 6 pre-consolidation files that have **working implementations** of many functions that were incompletely or incorrectly ported. These legacy files are a goldmine for fixing the current issues.

---

## Severity Legend

| Icon | Severity |
|------|----------|
| 🔴 | Critical — Crash, blocker, or completely broken functionality |
| 🟠 | Major — Design flaw, significant duplication, or fragile architecture |
| 🟡 | Moderate — Data/logic issue that may cause incorrect results silently |
| 🟢 | Minor — Testing gap or code quality issue |
| 🔵 | Hygiene — Maintenance, naming, or organizational issue |

---

## Detailed Issue Registry

### 🔴 Critical Issues (5 issues)

#### C1. `TypeError` in Numba Engine Startup
- **File:** `master_numba_engine.py:887`
- **Issue:** `check_algorithms_status(ALGORITHMS_TO_CHECK, metadata, lambda m: save_metadata(...))` is called with 3 arguments, but `benchmark_utils.check_algorithms_status()` only accepts 2 (`metadata` and `algorithms_to_check`). The third argument (a callback) does not exist in the current signature.
- **Impact:** Engine crashes immediately on startup with `TypeError: check_algorithms_status() takes 2 positional arguments but 3 were given`.
- **Fix:** Remove the callback argument. Call `save_metadata()` separately after `check_algorithms_status()` returns.
- **Legacy Reference:** `run_smart_benchmark_numba.py` correctly calls `check_algorithms_status()` without callbacks.

#### C2. Broken Test Imports Point to Non-Existent Legacy Files
- **File:** `tests/test_benchmark_robustness.py:1`
- **Issue:** Imports `run_smart_benchmark_numba` and `run_smart_benchmark_sota` as modules. These files were moved to `legacy/` during consolidation and are no longer importable at the `academic_benchmark` package level.
- **Impact:** `pytest` fails immediately with `ModuleNotFoundError`.
- **Fix:** Update imports to target `master_numba_engine` and `master_sota_engine`. Update function references (e.g., `get_worker_backend_module`, `make_deterministic_seed`).
- **Legacy Reference:** `run_smart_benchmark_numba.py` has the original `get_worker_backend_module()` implementation.

#### C3. `benchmark_utils.py` is Truncated — Syntax Error
- **File:** `benchmark_utils.py:~line 300`
- **Issue:** `select_run_count()` function is cut off mid-implementation. The last visible line is `return default` but the function body is incomplete (missing closing braces, the entire function after `if raw:` block is truncated).
- **Impact:** Python cannot parse the file. Any import of `benchmark_utils` raises `SyntaxError` or behaves unpredictably depending on the exact truncation point.
- **Fix:** Reconstruct the complete function using the legacy `run_smart_benchmark_numba.py` (lines 155-185 approx) which has a fully working `select_run_count()`.

#### C4. `sys.path` Hacks in SOTA TSP Solvers
- **Files:** `sota_tsp/e2bso_tsp.py:39`, `sota_tsp/r2dma_tsp.py`, `sota_tsp/paoea_tsp.py`
- **Issue:** Each solver file contains a `sys.path.insert(0, ...)` hack to import `utils_benchmark.compute_population_diversity`. This is fragile and breaks if the folder is moved, renamed, or imported from a different working directory.
- **Impact:** Silent import failures or wrong module resolution in certain execution contexts.
- **Fix:** Convert `academic_benchmark/` into a proper Python package by adding `__init__.py`, then use relative or absolute imports (e.g., `from academic_benchmark.utils_benchmark import compute_population_diversity`).
- **Legacy Reference:** Legacy solvers also used this hack; this is a known pattern that should be cleaned up.

#### C5. Potential `TypeError` on Missing Optimal Value
- **File:** `master_numba_engine.py` (inside `_evaluate_param_combo()`)
- **Issue:** The `gap` computation accesses `problem.optimal` even when it is `None`. The code attempts: `((tour_length - optimal) / optimal) * 100` where `optimal` may be `None`. In Python, `tour_length - None` raises `TypeError`.
- **Impact:** Crash when benchmarking problems without known optimal values.
- **Fix:** Guard the gap computation with `if optimal and optimal > 0:`.
- **Legacy Reference:** `run_sota_benchmark.py` handles this correctly with `if optimal and optimal > 0:`.

---

### 🟠 Major Issues (7 issues)

#### M1. Missing `__init__.py` — Folder Not a Proper Package
- **File:** `academic_benchmark/__init__.py` (missing)
- **Issue:** The `academic_benchmark/` folder has no `__init__.py`. Python 3 allows implicit namespace packages for absolute imports, but relative imports (`from . import utils`) and certain tooling (pytest discovery, mypy, IDE navigation) require explicit `__init__.py` files.
- **Impact:** Relative imports fail. The folder is treated as a namespace package, which can cause surprising behavior with `sys.path` resolution.
- **Fix:** Create `academic_benchmark/__init__.py`. Optionally add `__version__` and re-export common utilities.

#### M2. Duplicate Utility Modules: `benchmark_utils.py` vs `utils_benchmark.py`
- **Files:** `benchmark_utils.py`, `utils_benchmark.py`
- **Issue:** Both files define overlapping functions with identical names and purposes:
  - `load_metadata` / `get_latest_metadata`
  - `save_metadata`
  - `check_algorithms_status`
  - `compute_population_diversity`
  - `get_file_hash`
  - `_sync_hash_fields`
- **Impact:** Code drift between the two files. It is unclear which is canonical. `master_sota_engine.py` imports from `benchmark_utils`, but legacy code imported from `utils_benchmark`.
- **Fix:** Consolidate into a single canonical module. Keep `benchmark_utils.py` as the primary (it is imported by both engines), and remove or deprecate `utils_benchmark.py`. Ensure all imports point to `benchmark_utils`.
- **Legacy Reference:** Legacy files imported from `utils_benchmark`; the consolidation migration introduced `benchmark_utils` as the "new" module but left the old one in place.

#### M3. Redundant Local Functions in `master_sota_engine.py`
- **File:** `master_sota_engine.py` (~lines 830-850)
- **Issue:** Defines `_param_signature()` and `_generate_combinations()` locally, even though identical functions are already imported from `benchmark_utils.py` at the top of the file (`param_signature`, `generate_combinations`).
- **Impact:** Maintenance burden. Changes to `benchmark_utils.py` won't affect these local copies.
- **Fix:** Delete the local `_param_signature` and `_generate_combinations`. Use the imported ones.

#### M4. Massive Code Duplication Between Engines
- **Files:** `master_numba_engine.py`, `master_sota_engine.py`
- **Issue:** Both engines independently implement:
  - `_parse_tsplib_text` (TSPLIB text parser)
  - `_clean_tsplib_name` (name normalization)
  - `load_problems` (TSPLIB archive + fallback loader)
  - `_signal_handler` (Ctrl+C graceful shutdown)
  - `_ensure_dirs` (directory creation)
  - `_run_pool` / parallel execution wrappers
  - `_build_*_parameter_space` (parameter space builders)
- **Each duplication is ~150-250 lines.** Total duplicated code exceeds 500 lines.
- **Impact:** Any bug fix or TSPLIB format change must be applied in two places. High risk of divergence.
- **Fix:** Extract shared logic into `benchmark_utils.py` or a new `engine_core.py` module. Both engines should import from the shared module.
- **Legacy Reference:** The legacy files (`run_smart_benchmark_numba.py`, `run_smart_benchmark_sota.py`) also had this duplication, but they were separate standalone scripts. The "consolidation" was supposed to fix this, but it didn't.

#### M5. `_save_incremental()` Violates Single Responsibility
- **File:** `master_sota_engine.py` (~line 525)
- **Issue:** One function mutates JSON metadata, appends to a CSV log, AND updates file hashes.
- **Impact:** Hard to unit test. Side effects are hidden and tightly coupled.
- **Fix:** Split into three functions: `_update_metadata_result()`, `_append_csv_result()`, `_save_if_needed()`. Call them sequentially in the caller.

#### M6. Dashboard Schema Mismatch with SOTA Engine Output
- **File:** `dashboard.py:22`
- **Issue:** The Streamlit dashboard expects columns `avg_length`, `avg_gap`, `avg_time_ms`. However, `master_sota_engine.py`'s `_save_incremental()` writes `gap_pct` and `elapsed_sec` (different column names) and also writes per-run rows instead of aggregated rows.
- **Impact:** Dashboard shows empty or incorrect data for SOTA benchmark runs. Only Numba engine data may display correctly.
- **Fix:** Standardize the CSV schema across both engines, OR make the dashboard tolerant of both schemas by detecting column names dynamically.
- **Legacy Reference:** `run_smart_benchmark_sota.py` writes a consistent schema; the master engine broke it during consolidation.

#### M7. `dataset_loader.py` Mock Fallback Creates Wrong Objects
- **File:** `dataset_loader.py:15-35`
- **Issue:** When `v2` and `v1` imports both fail, the module defines mock `TSPLIBProblem` classes and `ALL_PROBLEMS = []`. However, the mock class has slightly different field names and missing methods compared to the real `TSPLIBProblem`.
- **Impact:** Downstream code may break with `AttributeError` when accessing fields the mock doesn't have (e.g., `edge_weight_type`, `optimal` checks).
- **Fix:** Either raise a clear `ImportError` with instructions instead of silently creating mocks, or ensure the mock class is 100% compatible with the real class interface.

---


### 🟡 Moderate Issues (5 issues)

#### D1. TSPLIB Optimal Lookup Case Sensitivity Mismatch
- **File:** `benchmark_utils.py:21-68` (`TSPLIB_OPTIMALS`)
- **Issue:** The dictionary uses lowercase keys (e.g., `"lin105"`), and `_clean_tsplib_name()` lowercases input. However, some real TSPLIB files use mixed case (`kroA100` becomes `kroa100` after lowercasing, which matches). But if a file uses a non-standard case (e.g., `KroA100`), it still works. The real risk is that the `TSPLIB_OPTIMALS` dict is missing some problems that are present in `tsplib_data/`, causing silent `None` optimal values.
- **Impact:** Gap calculations silently return `N/A` for problems that ARE in TSPLIB but missing from the hardcoded dictionary.
- **Fix:** Add a runtime check in `load_problems()` that warns about loaded problems missing from `TSPLIB_OPTIMALS`. Optionally auto-download or compute optimals from `.opt.tour` files using `dataset_loader.compute_tour_length()`.

#### D2. Numba Engine Skips `.tsp.gz` Files in tar.gz
- **File:** `master_numba_engine.py:160`
- **Issue:** `_parse_tsplib_text()` checks `member.name.lower().endswith(".tsp")`, but the `ALL_tsp.tar.gz` archive contains files with `.tsp.gz` extension (gzip-compressed inside the tar). The Numba engine skips them.
- **Impact:** Fewer problems loaded than expected. The SOTA engine handles `.tsp.gz` correctly (line 207 in `master_sota_engine.py`).
- **Fix:** Change the check to also handle `.tsp.gz` by looking for `.tsp` as a substring, or replicate the SOTA engine's logic.
- **Legacy Reference:** `run_smart_benchmark_sota.py` correctly handles `.tsp.gz` with `gzip.decompress()`.

#### D3. CSV Schema Divergence Between Engines
- **Files:** `master_numba_engine.py`, `master_sota_engine.py`
- **Issue:** Both write to `benchmark_progress.csv` but with different schemas:
  - Numba: `timestamp, problem, strategy, avg_length, avg_gap, avg_time_ms, n_runs, params_json`
  - SOTA: `timestamp, problem, strategy, avg_length, avg_gap, avg_time_ms, n_runs, params_json` (but SOTA also writes per-run data with `gap_pct` and `elapsed_sec` during `_save_incremental`, and SOTA's `benchmark_summary.csv` has a different structure)
- **Impact:** Aggregation scripts, dashboards, and manual analysis must handle two schemas. Data pipeline is brittle.
- **Fix:** Define a single shared CSV schema constant in `benchmark_utils.py` and enforce it in both engines.

#### D4. `_sync_hash_fields()` Unconditionally Merges Hashes
- **File:** `utils_benchmark.py:75`
- **Issue:** When both `file_hashes` and `algorithm_hashes` exist with different values, `_sync_hash_fields()` merges them with `{**fh, **ah}`, silently preferring `algorithm_hashes`. If they intentionally diverged (e.g., user manually edited one), the merge destroys that information.
- **Impact:** May mask real algorithm changes or falsely report "CURRENT" when files have actually changed.
- **Fix:** If both keys exist and have different values, raise a warning or prefer the newer timestamp rather than unconditional merging.

#### D5. `master_sota_engine.py` Swallows Exceptions Silently
- **File:** `master_sota_engine.py` (inside `_evaluate_sota_combo()`)
- **Issue:** The tuning loop catches `Exception` with `continue` and does not log the error:
  ```python
  except Exception:
      continue
  ```
- **Impact:** Failed solver runs are invisible. Debugging is impossible. Data appears "missing" for no apparent reason.
- **Fix:** At minimum, print the exception with traceback. Better: log to a dedicated `errors.csv` or `error_log.json`.
- **Legacy Reference:** `run_sota_benchmark.py` logs errors with full traceback.

---

### 🟢 Testing Issues (5 issues)

#### T1. Tests Have No Entry Point
- **File:** `tests/test_sota_e2e.py`
- **Issue:** No `if __name__ == "__main__": pytest.main()` block. Cannot be executed standalone without `pytest` CLI.
- **Impact:** Inconvenient for quick manual testing.
- **Fix:** Add `if __name__ == "__main__": pytest.main([__file__, "-v"])`.

#### T2. `monkeypatch` Test Assumes Wrong Function Location
- **File:** `tests/test_sota_parity.py:9`
- **Issue:** `monkeypatch.setattr(ls_engine, "improve_3opt", fake_3opt)` assumes `improve_3opt` is a module-level function in `ls_engine`. However, `ls_engine.py` may define it as a method inside `MultiLayerLS` or another class.
- **Impact:** Test may fail with `AttributeError` if the function location has changed.
- **Fix:** Verify the actual location of `improve_3opt` in `ls_engine.py` and update the monkeypatch target accordingly.

#### T3. Weak Destroy Ops Test Assertion
- **File:** `tests/test_sota_e2e.py:130`
- **Issue:** `test_destroy_n_remove_exceeds_tour_length` asserts:
  ```python
  assert all_nodes == [0, 1, 2, 3, 4] or len(remaining) >= 2
  ```
  The second condition (`len(remaining) >= 2`) is too weak — it passes even if nodes are lost.
- **Impact:** Test does not actually validate that destroy + repair preserves all nodes.
- **Fix:** Assert that `set(removed) | set(remaining) == set(tour)` AND `len(remaining) >= 2`.

#### T4. Missing Pytest Configuration at Test Directory Level
- **File:** `academic_benchmark/tests/` (no `conftest.py` or `pytest.ini`)
- **Issue:** The `conftest.py` exists at `optimizer_api/conftest.py` but not here. Fixtures and config may not be discoverable depending on how pytest is invoked.
- **Impact:** Test discovery and fixture resolution may be inconsistent.
- **Fix:** Add a minimal `conftest.py` in `academic_benchmark/tests/` or add a `pytest.ini` at the project root.

#### T5. Core Business Logic is Untested
- **Files:** `master_numba_engine.py`, `master_sota_engine.py`
- **Issue:** Functions like `_make_solver()`, `_make_solver_config()`, `_run_solver_task()`, `_evaluate_sota_combo()`, `_evaluate_param_combo()` have zero unit test coverage.
- **Impact:** Refactoring these functions is risky. Bugs can be introduced without any test catching them.
- **Fix:** Add unit tests for each core function, mocking the heavy solver calls.

---

### 🔵 Hygiene Issues (6 issues)

#### H1. Metadata File Proliferation in `benchmark_db/`
- **Folder:** `benchmark_db/`
- **Issue:** Contains 5+ metadata JSON files with overlapping purposes:
  - `latest_metadata.json`
  - `latest_metadata_numba.json`
  - `latest_metadata_sota.json`
  - `master_numba_metadata.json`
  - `master_sota_metadata.json`
- **Impact:** Unclear which file is authoritative. State fragmentation.
- **Fix:** Consolidate to exactly 2 files: `master_numba_metadata.json` and `master_sota_metadata.json`. Delete legacy `latest_metadata*.json` files. Update all references.

#### H2. Dashboard Uses Hardcoded Relative Paths
- **File:** `dashboard.py:10-14`
- **Issue:** `RESULT_DIRS` uses `os.path.join(os.path.dirname(__file__), "results")` etc. If the dashboard is launched from the project root (`streamlit run academic_benchmark/dashboard.py`), this works. If launched from another directory, paths may resolve incorrectly.
- **Impact:** Dashboard may report "No benchmark results found" even when results exist.
- **Fix:** Use an environment variable or project-root detection (e.g., `pathlib.Path(__file__).resolve().parent.parent`) instead of `__file__`-relative paths.

#### H3. Convergence Profile is a Single-Value List
- **File:** `master_numba_engine.py:680`
- **Issue:** `best_params[best_key]["convergence_profile"]` is stored as `[res["avg_length"]]` — a list with one element. The name "convergence profile" implies a time-series of best-so-far values across iterations.
- **Impact:** Misleading data. Not a real convergence history.
- **Fix:** Either rename the key to `"best_length"` (scalar), or actually collect iteration-level best costs from the solver.

#### H4. Untested Core Metrics
- **Files:** `sota_tsp/e2bso_tsp.py` (`_edge_entropy`), `sota_tsp/r2dma_tsp.py` (`_compute_resonance`)
- **Issue:** These functions are only tested via end-to-end solver tests, not directly. Edge cases (empty population, n<2, identical tours) are not explicitly covered.
- **Impact:** If the math is wrong, E2E tests may still pass by coincidence (the solver might work even if the diversity metric is broken).
- **Fix:** Add direct unit tests for `_edge_entropy()` and `_compute_resonance()`.

#### H5. Confusing Boolean Return in `select_mode()`
- **File:** `benchmark_utils.py:225`
- **Issue:** `select_mode()` returns `True` for sequential. The docstring clarifies this, but the API is confusing (`True = sequential` is counterintuitive).
- **Impact:** API clarity. Developers may expect `True = parallel`.
- **Fix:** Rename to `select_sequential_mode()` or return an enum (`Mode.SEQUENTIAL`, `Mode.PARALLEL`).

#### H6. Inconsistent Naming: `strategy` vs `algorithm`
- **Files:** Both engines, dashboard, tests
- **Issue:** The Numba engine uses `strategy` as the column name, while the SOTA engine uses `algorithm` in its result dicts. The dashboard expects `strategy`. CSV files mix both.
- **Impact:** Constant mapping/renaming is required when processing results.
- **Fix:** Standardize on `algorithm` everywhere (more descriptive) OR `strategy` everywhere. Pick one and enforce it.

---

## Task List: Fix Plan

### Phase 1: Critical Blockers (Must Fix First)

| # | Task | File(s) | Effort | Legacy Help |
|---|------|---------|--------|-------------|
| 1.1 | **Complete `select_run_count()` in `benchmark_utils.py`** | `benchmark_utils.py` | Small | `run_smart_benchmark_numba.py` has full impl |
| 1.2 | **Fix `check_algorithms_status()` call in Numba engine** | `master_numba_engine.py:887` | Small | Remove 3rd argument |
| 1.3 | **Add `academic_benchmark/__init__.py`** | New file | Small | — |
| 1.4 | **Fix test imports in `test_benchmark_robustness.py`** | `tests/test_benchmark_robustness.py` | Small | `run_smart_benchmark_numba.py` for ref |
| 1.5 | **Guard `optimal` access in `_evaluate_param_combo()`** | `master_numba_engine.py` | Small | `run_sota_benchmark.py` |
| 1.6 | **Replace `sys.path` hacks with proper imports** | `sota_tsp/e2bso_tsp.py`, `r2dma_tsp.py`, `paoea_tsp.py` | Small | Add `__init__.py` first |

### Phase 2: Consolidation & Deduplication

| # | Task | File(s) | Effort | Legacy Help |
|---|------|---------|--------|-------------|
| 2.1 | **Merge `utils_benchmark.py` into `benchmark_utils.py`** (canonical) | `benchmark_utils.py`, `utils_benchmark.py` | Medium | Compare both, pick best version |
| 2.2 | **Extract shared TSPLIB loader to `benchmark_utils.py`** | `benchmark_utils.py`, both engines | Medium | `run_smart_benchmark_sota.py` has best parser |
| 2.3 | **Extract shared signal handler & `_ensure_dirs()`** | New/shared module | Small | Both engines have identical code |
| 2.4 | **Extract shared `_run_pool()` / parallel execution** | `benchmark_utils.py` or new module | Medium | `run_smart_benchmark_numba.py` has clean impl |
| 2.5 | **Remove redundant `_param_signature` / `_generate_combinations` from SOTA engine** | `master_sota_engine.py` | Small | Use imported ones |
| 2.6 | **Clean up metadata files in `benchmark_db/`** | `benchmark_db/` | Small | Delete `latest_metadata*.json` |

### Phase 3: Data Integrity & Schema Standardization

| # | Task | File(s) | Effort | Legacy Help |
|---|------|---------|--------|-------------|
| 3.1 | **Define unified CSV schema constant in `benchmark_utils.py`** | `benchmark_utils.py` | Small | — |
| 3.2 | **Refactor SOTA `_save_incremental()` into 3 focused functions** | `master_sota_engine.py` | Medium | — |
| 3.3 | **Fix `.tsp.gz` handling in Numba engine** | `master_numba_engine.py` | Small | `master_sota_engine.py` has working code |
| 3.4 | **Add missing-optimal warning in `load_problems()`** | Both engines | Small | — |
| 3.5 | **Fix `_sync_hash_fields()` to not unconditionally merge** | `utils_benchmark.py` | Small | — |
| 3.6 | **Add error logging in `_evaluate_sota_combo()`** | `master_sota_engine.py` | Small | `run_sota_benchmark.py` logs tracebacks |
| 3.7 | **Standardize `strategy` vs `algorithm` naming** | All files | Medium | Pick one, rename consistently |

### Phase 4: Dashboard & Visualization

| # | Task | File(s) | Effort | Legacy Help |
|---|------|---------|--------|-------------|
| 4.1 | **Make dashboard schema-aware (handle both SOTA and Numba columns)** | `dashboard.py` | Medium | — |
| 4.2 | **Fix dashboard path resolution** | `dashboard.py` | Small | Use project-root detection |
| 4.3 | **Fix convergence profile (rename or implement actual profile)** | `master_numba_engine.py` | Small | — |

### Phase 5: Testing & Quality

| # | Task | File(s) | Effort | Legacy Help |
|---|------|---------|--------|-------------|
| 5.1 | **Add `conftest.py` or `pytest.ini`** | `tests/` | Small | — |
| 5.2 | **Add standalone pytest entry points to test files** | `tests/*.py` | Small | — |
| 5.3 | **Fix monkeypatch target in `test_sota_parity.py`** | `tests/test_sota_parity.py` | Small | Inspect `ls_engine.py` first |
| 5.4 | **Strengthen destroy/repair test assertion** | `tests/test_sota_e2e.py` | Small | — |
| 5.5 | **Add unit tests for `_edge_entropy` and `_compute_resonance`** | New test file | Medium | — |
| 5.6 | **Add unit tests for core engine functions** (mocked solvers) | New test file | Medium | — |

---

## Legacy File Reference Map

Use these legacy files to recover working implementations:

| Legacy File | Contains Working Implementation Of | Relevant For Issues |
|-------------|--------------------------------------|---------------------|
| `run_smart_benchmark_numba.py` | `normalize_strategy_entry`, `get_worker_backend_module`, `update_algorithm_hashes`, `select_worker_count`, `format_time`, `signal_handler`, `load_problems_smart` | C1, C2, C3, M4, M2 |
| `run_smart_benchmark_sota.py` | `_parse_tsplib_text`, `_clean_tsplib_name`, `_load_problems`, `_signal_handler`, `_check_algorithms_status`, `_save_metadata`, `_get_latest_metadata`, `_get_file_hash` | D2, M4, H1, C5 |
| `run_smart_benchmark_numba_doe.py` | `DOEProblem`, `StrategySpec`, `run_single_test_with_matrix`, `_normalize_strategy_entry`, `_load_problems` | M4, C4 |
| `run_sota_benchmark.py` | `_make_solver_config`, `_run_solver_task`, `_ETATracker`, `parse_tsplib`, error logging with traceback, optimal handling | C5, D5, M4, H1 |
| `run_smart_benchmark.py` | `DynamicTimeEstimator`, early v2 loader patterns, hash tracking | M4, D4 |

---

## Recommended Execution Order

1. **Phase 1 first** — These are blockers. Nothing works reliably until they are fixed.
2. **Phase 2 in parallel with Phase 3** — Consolidation and data integrity are interdependent.
3. **Phase 4 after Phase 3** — Dashboard fixes depend on schema standardization.
4. **Phase 5 last** — Tests are validation; they should cover the fixed code.

---

## Appendix: Files to Read for Deep Context

- `academic_benchmark/sota_tsp/ls_engine.py` — Verify `improve_3opt` location (for T2)
- `academic_benchmark/sota_tsp/base_solver.py` — Understand solver interface (for T5, M7)
- `optimizer_api/tests/run_interactive_benchmark_v2_numba.py` — Understand `STRATEGIES` format (for C2)
- `optimizer_api/tests/run_interactive_benchmark_v2.py` — Fallback strategy loader
