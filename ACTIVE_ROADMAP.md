# ACTIVE_ROADMAP.md
# UniRide — Active Technical Debt & Future Development
# Generated: 2026-06-01 | All items verified against codegraph (540 files indexed)
#
# Every item below was verified as UNRESOLVED in the current codebase.
# Items that were found to be already fixed have been excluded.

---

## P0 — Critical (do first)

### 1. Strategy 4× optimize() body duplication
- **Files:** `optimizer_api/strategies/{ga,gwo,hho,pso}_strategy.py`
- **Issue:** ~150 lines of nearly identical `optimize()` body across 4 files. Only differences: config attribute name, strategy label, TSP solver function.
- **Fix target:** Hoist `optimize()` to `HybridSplitBaseStrategy` (exists but empty). Parameterize by `_solve_tsp_func`, `_strategy_label`, `_config_attr`.
- **Blast radius:** 16 subclasses, `optimize` is runtime dispatch (17 targets). No external caller calls `optimize` directly on a subclass — all go through `STRATEGY_REGISTRY`.
- **Test coverage:** ✅ `test_strategy_no_legacy_algorithm_helpers.py`, `test_strategy_rng_state.py` exist.
- **Effort:** 4–6h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.1, §6.1

### 2. ShawRemoval max_dist normalization bug
- **File:** `uniride_core/algorithms/sota_common/destroy_operators.py:222–226`
- **Issue:** `max_dist` initialized to 1.0, updated by iterating `remaining` using `dist.get(seed_node, {}).get(node, 0.0)`. If any edges are missing (returns 0.0), `max_dist` never updates, normalization collapses to 0 for all nodes. ShawRemoval silently degrades to RandomRemoval.
- **Fix:** `max_dist = max((dist.get(seed_node, {}).get(node, 0.0) for node in remaining), default=1.0) or 1.0`
- **Blast radius:** 2 callers (`__init__.py` re-export + `test_sota_e2e.py`). 1-line fix.
- **Note:** The `sota_tsp/destroy_ops.py` version of ShawRemoval does NOT have this bug (uses `List[List[float]]` matrix with direct index access, no normalization).
- **Effort:** 15 min
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §5.1, §6.9

### 3. BenchmarkRunRequest schema-less
- **File:** `optimizer_api/models/schemas.py:330`
- **Issue:** Uses `Dict[str, Any]` for `algorithms`, `problems`, `settings`. Any typo in API payload surfaces as runtime 500, not validation 400.
- **Fix:** Replace with strict typed Pydantic models (`AlgorithmSetting`, `ProblemEntry`, etc.).
- **Blast radius:** 1 caller (`routers/benchmark.py:237`).
- **Effort:** 2h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.3, §6.2

### 4. Sync `def` endpoints block event loop
- **File:** `optimizer_api/routers/optimization.py:22, 143`
- **Issue:** `optimize_route` and `compare_algorithms` are `def` (not `async def`). FastAPI runs blocking algorithm in event loop thread. Under load, `/health` and `/strategies` become unresponsive.
- **Fix:** `async def` + `await run_in_threadpool(optimize_route_impl, request)`.
- **Blast radius:** 1 internal caller (`calculate_vehicles`).
- **Effort:** 30 min
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §5.4, §6.4

---

## P1 — High (do soon)

### 5. Dead `_is_tw_feasible` in repair operators
- **File:** `uniride_core/algorithms/sota_common/repair_operators.py:118–128`
- **Issue:** `_is_tw_feasible` always returns `True` regardless of time windows. Comment admits "simplified". If anyone relies on this for feasibility checking, it silently passes any solution.
- **Fix:** Implement proper TW feasibility check or raise `NotImplementedError` to prevent silent misuse.
- **Blast radius:** Called in `GreedyInsertion.repair()` only.
- **Effort:** 2h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.7

### 6. Two parallel benchmark execution paths
- **Files:** `optimizer_api/routers/benchmark.py` (`_start_benchmark_impl` vs `_start_matrix_native_benchmark_impl`), `academic_benchmark/cli_engine.py` (`_run_benchmark_with_best` vs `_run_benchmark_direct`), `academic_benchmark/sota_engine.py` (`_run_engine_tuning/default/with_params`)
- **Issue:** Multiple near-identical runner functions with duplicated thread-spawn, pool dispatch, exception handling, and persistence logic.
- **Fix:** Consolidate into a single `BenchmarkRunner.run(config)` method. Existing aliases become thin wrappers.
- **Effort:** 4h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.5, §6.6

### 7. Runtime imports in hot paths
- **Files:** `optimizer_api/routers/benchmark.py:_academic_param_spaces()`, `academic_benchmark/core/registry_setup.py` executors
- **Issue:** `from academic_benchmark.param_spaces import ...` executed inside function body on every call. `importlib.import_module(...)` inside executor closures dispatches SOTA solvers per call.
- **Fix:** Hoist all imports to module level. Replace `importlib.import_module` with a precomputed dispatch table.
- **Effort:** 1h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.6, §6.5

### 8. God function `optimize_route`
- **File:** `optimizer_api/routers/optimization.py:22–117`
- **Issue:** Mixes 5 concerns: algorithm dispatch, time-window post-processing, ResourceProfiler IE telemetry, bottleneck detection, time-shift suggestions. ~117 lines, hard to test.
- **Fix:** Split into `dispatch_algorithm`, `apply_time_windows`, `profile_resources`, `detect_bottlenecks`.
- **Blast radius:** 1 caller (`calculate_vehicles`).
- **Effort:** 2h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.4, §6.7

### 9. Missing test coverage for critical SOTA infrastructure
- **Symbols:** `ConfigSchema.validate`, `DiversityController`, `PenaltyManager`, `MultiStartInitializer`, `MultiLayerLS`
- **Issue:** Codegraph blast-radius analysis flags these as having ⚠️ no covering tests in the active code path.
- **Fix:** Write unit tests for each.
- **Effort:** 4h
- **Source:** `docs/01.06.2026_UniRide_Codegraph_Analysis_Report.md` §11, `docs/01.06.2026_UniRide_Blast_Radius_Verification.md` §6.8

### 10. Daemon thread benchmark — no graceful cancellation
- **File:** `optimizer_api/routers/benchmark.py:283`
- **Issue:** Daemon threads are killed on process shutdown. No `try/finally` cleanup. Half-written CSV files, stuck `"running"` DB state, partial SQLite state.
- **Fix:** Use `asyncio.create_task` with proper cleanup, or add `threading.Event` cancellation token + `try/finally` in worker.
- **Effort:** 2h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §5.5, §6.14

### 11. Benchmark exception swallowing (silent failures)
- **File:** `optimizer_api/routers/benchmark.py:280–281`
- **Issue:** `run_benchmark_task` catches all exceptions via state manager `fail_run()`, but never logs the exception type, message, or stack trace at error level.
- **Fix:** `except Exception as e: logger.exception("benchmark failed: %s", e); fail_run(...)`.
- **Effort:** 30 min
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §5.6

### 12. `_make_legacy_executor` re-reads distance matrix from disk per call
- **File:** `academic_benchmark/core/registry_setup.py:179`
- **Issue:** Inside the executor closure, `get_distance_matrix(...)` is called for every benchmark run, even though the matrix is loaded once and reused across all algorithms. 10–100× I/O amplification.
- **Fix:** Pre-load matrix at task dispatch time, pass as argument.
- **Effort:** 30 min
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §5.7

---

## P2 — Medium (plan carefully)

### 13. Two parallel strategy registries
- **File:** `optimizer_api/strategies/__init__.py`
- **Issue:** `STRATEGY_REGISTRY` (instances) and `STRATEGY_FACTORIES` (classes) hold the same data. Plus hardcoded `pipeline_map`, `_OPTIONAL_META`, and alias dicts.
- **Fix:** Single decorator-based registration: `@StrategyRegistry.register(name, pipeline, label)`.
- **Blast radius:** HIGH — all routers and BenchmarkRunner depend on `STRATEGY_REGISTRY`.
- **Effort:** 3h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.2, §6.3

### 14. `shell=True` in orchestrate_batch.py
- **File:** `academic_benchmark/bildiri2026/orchestrate_batch.py`
- **Issue:** `subprocess.run(cmd, shell=True)` — injection risk if any argument includes user input.
- **Fix:** `subprocess.run([sys.executable, str(script_path), *args], shell=False, ...)`.
- **Effort:** 15 min
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.11, §6.10

### 15. Hardcoded model IDs in orchestrate_batch.py
- **File:** `academic_benchmark/bildiri2026/orchestrate_batch.py:28–34`
- **Issue:** Model IDs `"1,2,3"`, `"4,5,6"` etc. hardcoded. Breaks on DB change.
- **Fix:** Query DB for model IDs by problem name at runtime.
- **Effort:** 1h
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §4.12

### 16. `convert_schedule_to_students` mutable default
- **File:** `optimizer_api/routers/utils.py:35`
- **Issue:** `user_mapping: Dict[str, Dict] = None` — type hint says non-Optional but default is `None`.
- **Fix:** `user_mapping: Optional[Dict[str, Dict]] = None`.
- **Effort:** 5 min

### 17. `get_time_windows` silent IndexError
- **File:** `optimizer_api/models/schemas.py:262–278`
- **Issue:** `parts[0] * 60 + parts[1]` with bare `except (ValueError, IndexError): pass` — malformed time strings silently produce no time window.
- **Fix:** Raise `ValueError` with meaningful message.
- **Effort:** 15 min

### 18. TSPLIB DB path via `os.path.dirname(os.path.dirname(__file__))`
- **Files:** `academic_benchmark/core/registry_setup.py:206, 319`, `academic_benchmark/cli_engine.py`, `academic_benchmark/sota_engine.py:125`
- **Issue:** Brittle path computation. Breaks on symlink/namespace package/install changes.
- **Fix:** Centralize in `academic_benchmark/__init__.py:tsplib_db_path()`.
- **Effort:** 30 min
- **Source:** `docs/01.06.2026_UniRide_Comprehensive_Code_Review.md` §6.11

### 19. Side-effect imports (BLAS thread env vars)
- **File:** `academic_benchmark/sota_engine.py:37–40`, `academic_benchmark/cli_engine.py:36–39`
- **Issue:** `os.environ.setdefault("OMP_NUM_THREADS", "1")` at module top-level. Importing mutates process environment.
- **Fix:** Guard with function-level initialization in `main()`.
- **Effort:** 30 min

### 20. Mixed time sources
- **Files:** Various — `time.time()` for timestamps, `time.perf_counter()` for elapsed, `datetime.now(timezone.utc)` for serialization
- **Issue:** `time.time()` is wall-clock, jumps on NTP correction. Used for elapsed measurements in some files.
- **Fix:** Use `time.perf_counter()` universally for elapsed, `datetime.now(timezone.utc)` for timestamps.
- **Effort:** 1h

---

## P3 — Low (backlog)

### 21. Turkish-language strings in academic_benchmark
- **Issue:** `UYARI`, `SECIM`, `BILGI`, `HATA` throughout `benchmark_utils.py`, `cli_engine.py`. Blocks i18n.
- **Fix:** Extract to `messages_tr.py` / `messages_en.py`.
- **Effort:** 4h

### 22. Interactive `input()` calls block CI/testing
- **Issue:** `select_worker_count`, `select_run_count`, `select_mode`, `edit_param_space`, `_edit_param_space_interactive`, `_param_db_menu` — all use `input()`.
- **Fix:** Factor into `prompter.py` that can be monkey-patched in tests.
- **Effort:** 4h

### 23. O(n²) `_matrix_is_asymmetric` validation
- **File:** `optimizer_api/models/schemas.py:120–130`
- **Issue:** O(n²) over distance matrix at request validation time. For 1000-node problems, 1M comparisons per request.
- **Fix:** Move to `model_validator(mode="after")` with `DEBUG` guard, or cache.
- **Effort:** 1h

### 24. Duplicate `validate_param_value` in benchmark_utils.py
- **File:** `academic_benchmark/benchmark_utils.py:588` (4-arg) and `:908` (3-arg)
- **Issue:** Two definitions with different arity and behavior.
- **Fix:** Remove one, update all call sites.
- **Effort:** 15 min

### 25. Add structured logging
- **Issue:** `print()` used for all user-facing output in `cli_engine.py` and `benchmark_utils.py`.
- **Fix:** Adopt `structlog` or `loguru`. Add `request_id` via `contextvars`.
- **Effort:** 4h

### 26. Superseded code cleanup (from Archive Classification Report)
- **Files to archive:** 4 non-split strategies, 8 sota_common re-export shims, 9 duplicate clustering_strategies, 7 duplicate utils
- **Prerequisite:** Run grep verification from `docs/01.06.2026_UniRide_Archive_Classification_Report.md` §10
- **Effort:** 2h (after grep verification)

---

## Resolved Items (verified — NOT in this roadmap)

The following items from older documentation were **verified as already fixed** via codegraph:

| Old Claim | Source Doc | Verification |
|-----------|-----------|--------------|
| CORS wildcard `["*"]` | `05_Code_Quality_Roadmap.md` A-2 | ✅ `ALLOWED_ORIGINS` env var in `main.py:74–87` |
| Missing auth guard on calculate-vehicles | `05_Code_Quality_Roadmap.md` A-1 | ✅ `requireAdmin` at `route.ts:22,148` |
| Broken sandbox IE endpoint | `05_Code_Quality_Roadmap.md` A-3 | ✅ `ie_data` embedded in optimize response (`route.ts:196`) |
| `total_time_window_violations` missing | `05_Code_Quality_Roadmap.md` B-1 | ✅ `schemas.py:293` |
| `strategy` → `algorithm` field name | `05_Code_Quality_Roadmap.md` B-2/B-3 | ✅ Both APIs send `algorithm:` |
| `max_tour_time` → `max_travel_time` | `05_Code_Quality_Roadmap.md` B-4 | ✅ Both APIs send `max_travel_time:` |
| Benchmark runner not executing | `BENCHMARK_ARCHITECTURE_DEBT.md` | ✅ Daemon thread + state manager operational |
| `compute_gap` duplication | `06_COMPREHENSIVE_REVIEW` | ✅ `evaluation.py` delegates to `benchmark_utils.py` |
| Haversine copy in clustering.py | `01_Implementation_Status.md` FIX-07 | ✅ Now re-exports from `uniride_core.algorithms.distance` |
| Core-First migration incomplete | `00_Unified_Master_Plan` | ✅ All strategy files delegate to `uniride_core/algorithms/` |
| `faz0_interactive.py` to delete | `00_Unified_Master_Plan` | ✅ File deleted |
| 3-opt missing in ls_engine | `docs_dev/findings.md` | ✅ Fixed (2026-04-30) |
| Regret3Insertion missing | `docs_dev/findings.md` | ✅ Fixed (2026-04-30) |
| R2DMA resonance simplified | `docs_dev/findings.md` | ✅ Fixed (2026-04-30) |
| Non-deterministic seeds | `docs_dev/findings.md` | ✅ `make_deterministic_seed()` via hashlib |
| 19 benchmark fix issues | `docs_dev/task_plan.md` | ✅ ALL RESOLVED (2026-05-06) |
| All 15 v1–v3 review findings | `00_code_review_reportOpus4.6` | ✅ ALL RESOLVED (v4, May 31) |

---

## Execution Priority

| Phase | Items | Total Effort |
|-------|-------|-------------|
| **Phase 1** (Quick wins) | #2 ShawRemoval fix, #4 threadpool, #11 exception logging, #14 shell=True, #16 mutable default, #17 silent IndexError, #24 duplicate validate | ~2h |
| **Phase 2** (Strategy dedup) | #1 hoist optimize to HybridSplitBase | 4–6h |
| **Phase 3** (Schema + API) | #3 BenchmarkRunRequest, #8 split god function | 4h |
| **Phase 4** (Benchmark unification) | #6 consolidate runners, #7 hoist imports, #10 cancellation, #12 disk re-read | 6h |
| **Phase 5** (Test coverage) | #9 SOTA infra tests, #5 dead _is_tw_feasible | 6h |
| **Phase 6** (Registry + cleanup) | #13 unify registries, #18 TSPLIB path, #19 env side-effects, #20 time sources, #26 superseded code | 5h |
| **Phase 7** (Backlog) | #21 i18n, #22 input() calls, #23 O(n²) validation, #25 structured logging | 13h |