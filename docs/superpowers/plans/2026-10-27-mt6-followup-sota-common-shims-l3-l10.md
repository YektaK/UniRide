# MT6 follow-up: archive `sota_common`, remove the shims, L3, L10 and the non-canonical `run_tsp` perturbation

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan item by item. Steps use checkbox (`- [ ]`) syntax. **Status: DRAFT for owner approval.** This plan closes owner answer OQ-MT6-7 a (DECISION_LOG A19 `:522`, `:528`): "the rest of the audit's MT6 row (`sota_common` archive, shims, L3, L10, `run_tsp._apply_3opt_bounded`) is a separate follow-up". No code work starts before the owner (or the lead, under the A20 delegation `:533`, since none of these questions is reserved to the owner) answers section 6.

**Goal:** remove dead and duplicate solver code (audit L3, the `sota_common` package and the re-export shims), fix the latent determinism defects of audit L10, and replace the last non-canonical "3-opt" move reachable from a public entry point (`run_tsp._apply_3opt_bounded`, audit `:1601`).

**What this plan is not:** it does not touch study profiles, analysis plans, dataset manifests or any module on the Bildiri/YAEM execution path (section 5); it does not make SOTA solvers governed; it does not touch the old `numba_accel` 3-opt kernel (kept unreachable by OQ-MT6-1 a) or the backend-dependent 2-opt/Or-opt/swap layers of `ls_engine` (OQ-F8); it runs no benchmark.

**Naming note:** "L3" and "L10" in this plan are the **audit** findings (`docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md:1252`, `:1259`), not the A20 lead decisions L3/L10 (`DECISION_LOG.md:536`, `:543`). DURUM.md's "L10 cilası" is the A20 one.

**Base:** branch `WIP`, HEAD `af033e0d` (2026-10-27). The planner read code only; it ran no tests and no Python.

**Fact/assumption key:** **[F]** = verified in live code at `af033e0d` (file:line given); **[A]** = assumption the item's developer checks first; **[O]** = owner choice (section 6).

## Global constraints (every brief repeats these)

- **Python on Windows (top of every brief):** never open interactive Python (no bare `python`/`py`, no `python -i`, no `python -`, no `python -c`, no heredoc or stdin into Python). Write scripts to a file under `C:\wt\<name>` and run them with `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`, `PYTHONPATH` set to the worktree (print `uniride_core.__file__` once). Time-limit every command, redirect output to a file. Stop on `_pyrepl`, `getheightwidth`, `WinError 123` or a repeating traceback.
- Never `taskkill /IM`; kill only your own PIDs. Never `git stash`. No checkout/switch in the main checkout. Temp folders only under `C:\wt\<name>`.
- Never write, copy, delete or open `academic_benchmark/tsplib_data/tsplib.db*`. Never run `test_patch.py` (it opens `tsplib.db`, `test_patch.py:4-17`). Never run AMPL. Never write under `docs/paper/results`.
- Each item in its own worktree and branch from `WIP`, red test first, frequent commits, no merge, no push. The lead merges with `--no-ff` after reviewer ONAY and passing tests.
- No benchmark runs and no timings. Tests use in-memory data.
- Do not change: production strategy exposure (`academic_benchmark/tests/test_production_registry_snapshot.py`, run after every item), study profiles and their scientific values, the canonical 3-opt neighbourhood (`CANONICAL_THREE_OPT_DESIGN.md:37-75`), `numba_accel.py`, `ls_engine.py`.
- Do not reopen A04, A14 (no pooling across result-changing fixes), A17, A18 (OQ-10: one campaign = one clean commit), A19 (OQ-MT6-1..7), A20 L5 (freeze before the campaign).
- Archived code is `REFERENCE_ONLY`: never imported or executed (`archive/__init__.py` raises `ImportError`; `uniride_core/tests/test_archive_boundaries.py`).
- The canonical 3-opt regression command (`CANONICAL_THREE_OPT_DESIGN.md:141-147`) passes before and after every item; a new focused 3-opt test module is added to it by the same item.

---

## 1. Verified current state (live code at `af033e0d`)

### 1.1 `sota_common` and its shims

| # | Claim | Status | Evidence |
|---|---|---|---|
| S-1 | Core package of 9 files, 2,465 lines | **[F]** | `uniride_core/algorithms/sota_common/` (`__init__.py` 74 lines … `repair_operators.py` 333). |
| S-2 | No active solver imports it | **[F]** | Repo-wide search outside `docs/`, `archive/`: only the 9 shims in `optimizer_api/strategies/sota_common/*.py` (3-4 lines each, `from uniride_core.algorithms.sota_common... import *`), two compatibility tests (`optimizer_api/tests/test_sota_common_compat.py:3-26`, `uniride_core/tests/test_sota_common_migration.py:1-24`) and the two `__main__` smoke entry points (`uniride_core/algorithms/sota_common/__main__.py:1-156`, `optimizer_api/strategies/sota_common/__main__.py:1-3`). CodeGraph blast radius for `PenaltyManager`/`MultiLayerLS`: only the package itself and those two tests. Production SOTA uses `sota_tsp/` (`ls_engine.py:34`). |
| S-3 | It holds the non-canonical `_layer_3opt` (a 2-opt) and wall-clock stops | **[F]** | `multi_layer_ls.py:262-311` reverses one segment ("reverse-middle"); `time.monotonic()` stops at `:91-129`, `:167-180`, `:222-245`, `:288-298`, `:338-348`. Dead, so no result is affected. |
| S-4 | `PenaltyManager` (L3 bullet) lives only here | **[F]** | `sota_common/penalty_manager.py:44`; no other definition or importer. |
| S-5 | A production docstring claims E2BSO uses these modules | **[F] new detail** | `optimizer_api/strategies/ebso_strategy.py:7-14` lists `MultiStartInitializer`, `PenaltyManager`, `DiversityController` …; false (S-2). |
| S-6 | An archive tool with manifests exists | **[F]** | `academic_benchmark/archive_manifest.py:640-750` (`quarantine_tracked_tree`), CLI `:777-826` (`quarantine --source --archive --archive-id`, classifier choices `yaem`/`bildiri` only, `:792`); both classify a code file as `REFERENCE_ONLY` (`:117-136`). Precedent manifests: `archive/academic_benchmark/{bildiri2026,yaem2026}_legacy/manifest.json`. Packaging test keeps `archive/` out of the wheel (`academic_benchmark/tests/test_gate_d_packaging.py:153-157`). [A] the tool works on a non-academic source root; the developer runs `scan` first. |

### 1.2 `optimizer_api/utils` re-export shims

| # | Claim | Status | Evidence |
|---|---|---|---|
| U-1 | 20 pure re-export files | **[F]** | `clustering.py`, `haversine.py`, `linear_split_decoder.py`, `local_search.py`, `local_search_numba.py`, `resource_profiler.py`, `scheduling.py`, `split_decoder.py`, `time_window_extractor.py`, `time_window_violation_tracker.py`, `tsplib_parser.py` (each only imports from `uniride_core`), plus `clustering_strategies/*.py` (9 files). Real modules that stay: `data_loader.py`, `matrix_repository.py`, `patterns.py`, `resource_profiler_demo.py`. |
| U-2 | **Correction to the audit:** production code still imports four shims | **[F]** | `optimizer_api/routers/optimization.py:56-57` (`utils.resource_profiler`, `utils.scheduling`), `optimizer_api/routers/utils.py:7` (`utils.time_window_extractor`), `optimizer_api/routers/benchmark.py:25` and `optimizer_api/benchmark_runner.py:186` (`utils.tsplib_parser`). Audit `:1270`, `:1607` say only tests import them; that holds for `local_search`/`local_search_numba` only. Deleting first would break app start. |
| U-3 | Script and test importers | **[F]** | Scripts: `optimizer_api/utils/resource_profiler_demo.py:16`, `optimizer_api/test_linear_split_perf.py:7-8`, `optimizer_api/test_strategies.py:325`, root `test_patch.py:28`. Tests: `test_clustering_unit.py:3`, `test_clustering_compat.py:1-2`, `benchmark_hierarchical_threshold.py:38-39`, `test_local_search.py:32`, `test_local_search_unit.py:2`, `test_algorithm_comparison.py:34`, `run_interactive_benchmark.py:32`, `run_interactive_benchmark_v2.py:41`, `test_cvrptw_phase1.py:19`, `test_cvrptw_phase2.py:13`, `test_cvrptw_phase3.py:19`, `test_split_decoder_audit.py:7`, `test_split_decoder_unit.py:2`, `test_core_utility_shims.py:6-8`, `test_resource_profiler.py:16`, `test_scheduling_utils.py:2`, `test_time_window_violation_tracker_compat.py:2` (all under `optimizer_api/tests/`). `haversine.py` has no importer. [A] string monkeypatch targets such as `"utils.scheduling..."`; the developer searches for them. |
| U-4 | An existing guard names some shims | **[F]** | `uniride_core/tests/test_architecture_boundaries.py:38-51` (benchmark helpers must not import six shim modules). |

### 1.3 L3 (dead code), remaining bullets (audit `:1266-1275`)

| # | Bullet | Status | Evidence |
|---|---|---|---|
| L3-a | `vehicle-planning-page.tsx` never imported | **[F]** | Only its own test imports it (`src/app/(app)/admin/vehicle-planning/vehicle-planning-page.test.tsx:37`); the route is `page.tsx` (486 lines; H15 fix lives there, tracker H15 row). |
| L3-b | `run/status`, `run/stop` BFF routes have no client | **[F]** | No caller in `src/` outside `src/app/api`; only route tests (`src/app/api/benchmark/academic-disabled.test.ts:11-12, 62-63`, `benchmark-auth.test.ts:48-49`). `status: data.status \|\| 'running'` is at `run/status/route.ts:69` (audit `:63`). H14 (polling, MT7) is still OPEN (tracker H14 row). |
| L3-c | Sandbox scenario server routes unused, JSONB double-encoded | **[F] refined** | `POST` (re-optimise) **is used** (`src/app/(app)/admin/sandbox/page.tsx:265`). `GET`/`PUT`/`DELETE` (`src/app/api/sandbox/route.ts:237`, `:276`, `:316`) are unused: the page stores scenarios in `localStorage` (`page.tsx:147`, `:164`). `vehicles: JSON.stringify(vehicles)` at `route.ts:291`. New detail: `src/services/sandbox-api.ts` (callers of those handlers, `:37`, `:59`, `:81`, `:101`) has no importer. |
| L3-d | `optimizer_api/utils` local-search shims test-only | **[F]** | U-1..U-3. |
| L3-e | `sota_common` and its shims | **[F]** | S-1..S-5. |
| L3-f | Duplicate k-means in `clustering.py` | **[F]** | `uniride_core/algorithms/clustering.py:75-107` (`initialize_centroids_kmeans_plus_plus`), `:110-164` (`kmeans_clustering`), `:171-174` (`split_cluster`, a k-means wrapper): no non-test caller (only the shim and tests: `uniride_core/tests/test_clustering_core.py:4, 11, 27`, `optimizer_api/tests/test_clustering_unit.py:3, 24, 36`, `uniride_core/tests/test_h12_clustering_rng_threading.py:150-176`). The live k-means is `clustering_strategies/kmeans.py:7, 35`. `validate_cluster_capacity` (`:167`), `Point`, `Cluster`, `calculate_centroid`, `resolve_rng` are live (`clustering_strategies/*.py`, e.g. `sweep.py:3`), as audit v1.1 says (`:74`). |
| L3-g | `local_search_numba._three_opt_improve_numba` / `_three_opt_cases_numba`, 0 callers | **[F]** | Defined `uniride_core/algorithms/local_search_numba.py:294-400` and `:402-449`; the only caller of the cases function is the improve function (`:428`); no other reference in the repository. `CANONICAL_THREE_OPT_DESIGN.md:97` names this path as non-canonical and removed from public execution. |
| L3-h | Request field `use_sota_engine` never read | **[F]** | `optimizer_api/models/schemas.py:282` (audit said `:222`); no reader in `optimizer_api`, `src`, `scripts`. `OptimizationRequest` (`:248`) sets no `extra="forbid"`, so a request that still sends the key validates after removal [F: no `model_config`/`extra` in `schemas.py` for it]. The core decoder option `cvrptw_decoder.py:25-62` is live and stays. |
| L3-i | `PenaltyManager` unused | **[F]** | S-4. |

### 1.4 L10 (latent determinism, audit `:1290-1296`)

| # | Bullet | Status | Evidence |
|---|---|---|---|
| L10-a | Asymmetric haversine factors from `hash()` (salted per process) | **[F] CONFIRMED, moved** | `optimizer_api/utils/matrix_repository.py:860-866` (audit `:535-538`). |
| L10-b | Asymmetric flag always True | **[F] CONFIRMED, two sites** | Academic coordinate scope: `:487-490` (`asymmetric=True` whenever `geo_coords`); fallback: `:498-502` (`asymmetric_haversine if not geo_coords else True` inside `if geo_coords`). No active caller passes `geo_coords=True`: only tests (`optimizer_api/tests/test_c2_matrix_fail_closed.py:111, 291`) and the pass-through `utils/data_loader.py:105-119`; production strategies call `get_submatrix(ids, coords)` (e.g. `strategies/sota_response_builder.py:59`, `ga_split_strategy.py:164`). |
| L10-c | `random.Random(None)` when no seed is given | **[F] partly fixed** | Still open: `uniride_core/algorithms/tsp_meta_matrix_engine.py:47`, `fcm_split_engine.py:62`, `:187`; `tsp_matrix_metaheuristics/base_solver.py:43`, `:276`, `ga_solver.py:98`, `gwo_solver.py:101`, `hho_solver.py:112`, `pso_solver.py:95` (`random_seed=None` default). **Fixed already:** `fuzzy_cmeans_enhanced.py:173` now uses `resolve_rng` (H12/QW7; `clustering.py:17-19`). Current callers pass integers: `academic_benchmark/core/registry_setup.py:111, 235, 1043, 1206`, `composition.py:528`, `optimizer_api/routers/benchmark.py:470` [A: the developer lists every caller of the two matrix engines, including `academic_benchmark/run_matrix_benchmark.py`, `run_fcm_srs_comparison.py`]. Repository precedent for a missing seed: a fixed default 42 (`clustering.py:14-19` for H12; `optimizer_api/strategies/seed_utils.py:7-20` for production). |
| L10-d | Dormant `use_random_order` | **[F] CONFIRMED, moved** | `uniride_core/algorithms/local_search.py:664, 692, 695, 730-731` (`self.rng = random.Random()`), `local_search_numba.py:1011, 1029, 1033, 1054-1055`. No caller sets it: `get_local_search(**kwargs)` (`local_search.py:784-814`), `apply_local_search` (`:817-842`) and every `HybridLocalSearch(` construction (`optimizer_api/tests/test_local_search.py:424-674`, `uniride_core/tests/test_mt6_path_three_opt.py:519`) leave it False. |
| L10-e | `objective_budget` strict comparisons | **[F] CLOSED by MT6-05** | `objective_budget.py:201, 283, 364` call `is_improving` (`three_opt.py:46-55`); tracker N-1 row. Only the record is missing. |
| L10-f | `local_search_numba` 3-opt wrapper: duplicates raise; fallback matrix cancels the depot | **[F] CONFIRMED, latent** | Fallback matrix `dist_matrix[i, j] = f([a,b]) - f([a])` at `local_search_numba.py:145-149`; `ThreeOptLocalSearch.improve` passes it to the closed-cycle engine (`:780-788`), which rejects duplicate indices (`CANONICAL_THREE_OPT_DESIGN.md:119`). Every active caller attaches a prebuilt matrix, so the fallback is not used: `academic_benchmark/cli_engine.py:615`, `registry_setup.py:482, 504`, `numba_metaheuristics.py:348`. The fallback and its weak-keyed cache are pinned by `uniride_core/tests/test_local_search_matrix_isolation.py`. |

### 1.5 `run_tsp._apply_3opt_bounded`

| # | Claim | Status | Evidence |
|---|---|---|---|
| R-1 | Cases 4 and 5 are identical | **[F] CONFIRMED** | `uniride_core/algorithms/sota_tsp/run_tsp.py:124` and `:128` build the same list. |
| R-2 | More drift than the audit lists | **[F] new detail** | Docstring "Try all 7 Lin-Kernighan reconnection patterns" (`:101`) is false: the identity (`:105`), three in-place reversals (`:108-121`), `A C B D` twice (`:124`, `:128`) and `A C B' D` (`:132`); `A C' B D` and `A C' B' D` are missing. Cuts allow a one-node first segment (`j = randint(i + 1, ...)`, `:98`), and position 0 never moves (`A = result[:i + 1]`). Reversals are applied on asymmetric matrices, but every candidate is fully costed (`:135`, `_tour_cost` `:167-173`), so tours stay valid. |
| R-3 | Reach | **[F]** | Called once per RUN update as the "k2" move (`run_tsp.py:275`). RUN is reached only by the academic `SOTA-RUN-TSP` (`academic_benchmark/core/registry_setup.py:614`, `academic_benchmark/sota_engine.py:64-75`), refused in protocol mode (`registry_setup.py:592-596`), in no study profile (`academic_benchmark/studies/{bildiri2026,yaem2026}/study.json`, `algorithm_ids`), and not a production strategy (snapshot list `test_production_registry_snapshot.py:17-25`). |
| R-4 | Tests that pin RUN | **[F]** | `academic_benchmark/tests/test_regression_gate.py:37` (gap < 15 %, n <= 8), `uniride_core/tests/sota_tsp/test_sota_algorithms.py:41, 96`, `uniride_core/tests/test_mt6_sota_deterministic_stop.py:52`, and the exact golden `academic_benchmark/tests/fixtures/numba_sota_tsp_golden_pre_refusal.json` (keys `tsp:SOTA-RUN-TSP`, `atsp:SOTA-RUN-TSP`, n = 9; used by `test_numba_sota_ids_refuse_routing.py:181`). |
| R-5 | A core generator for one cut exists | **[F]** | `three_opt.generate_three_opt_candidates(route, i, j, k, *, directed)` (`three_opt.py:159-205`; 7 symmetric reconnections or the single directed `S1+S3+S2`, admitted cuts only, `:179-180`), `is_symmetric_matrix` (`:59`), `validate_three_opt_window` (`:81`), `closed_tour_cost` (`:33`). |

### 1.6 Observation carried over from the MT6 plan

| # | Observation | Status | Evidence |
|---|---|---|---|
| N-2 | `ls_engine` 2-opt/Or-opt/swap layers depend on the backend (Numba kernel vs Python fallback) | **[F] still present** | `sota_tsp/ls_engine.py:53-80`, `:83-115`, `:118-140`. MT6 plan section 8 parked it "with OQ-MT6-7", but the owner's answer A19 `:522` does not list it. OQ-F8. |

---

## 2. Acceptance definition

The follow-up is closed when, on one recorded `WIP` commit (MT6F-09):

1. `uniride_core.algorithms.sota_common` and `optimizer_api.strategies.sota_common` cannot be imported; per OQ-F1 the core tree is in `archive/` with a manifest that `python -m academic_benchmark.archive_manifest verify` accepts; no active file imports `sota_common`.
2. The 20 `optimizer_api/utils` shim modules are gone; an AST guard finds no import of them in `optimizer_api`, `academic_benchmark`, `uniride_core` or root `*.py`; `import optimizer_api.main` works; `test_production_registry_snapshot.py` unchanged and green.
3. L3 Python items L3-f, L3-g, L3-h removed with tests; frontend items per OQ-F6.
4. Every L10 bullet is either fixed with a red/green test (L10-a/b per OQ-F3, L10-c per OQ-F4, L10-d, L10-f per OQ-F5) or recorded as already closed with evidence (L10-c `fuzzy_cmeans_enhanced`, L10-e).
5. `run_tsp` k2 move per OQ-F2 with an independent test; no duplicate candidate; the new test module is in the regression command.
6. Bildiri/YAEM results unchanged: `academic_benchmark/tests/test_fixed_budget_tables_unchanged.py`, `uniride_core/tests/golden/gwo_hho_native_pre_schedule.json`-based tests, `uniride_core/tests/test_mt6_budgeted_tolerance.py` and `academic_benchmark/tests/fixtures/fcm_tsp_golden_pre_refusal.json`-based tests pass unedited; no file under `academic_benchmark/studies/` or `academic_benchmark/datasets/` changed (`git diff --stat` in the close record).
7. `uniride_core/tests`, `academic_benchmark/tests`, `optimizer_api/tests` (`-m "not requires_ampl"`), the regression command, and for MT6F-08 `vitest` + `tsc` pass; counts recorded in the DECISION_LOG entry.
8. Appendix J: L3 and L10 split out of the collective row (`ULTIMATE_AUDIT…:2365`) with branch, red/green commits and test names; H10 row (`:2328`) note "run_tsp/sota_common remain non-canonical" updated; H12 row note if H12 legacy-primitive tests are removed (MT6F-03).

---

## 3. Work items

Developer Sonnet for every item. Reviewer named per item. Suggested tool-call ceiling 15-25 per item (requested, not enforced).

### MT6F-01: Archive `sota_common`, delete its shims (L3-e, L3-i)

- [x] **MERGED `80105327` (2026-10-27, Sonnet ONAY).** **Red test first** (`uniride_core/tests/test_mt6f_sota_common_retired.py`): (a) `importlib.util.find_spec` is `None` for both packages (red today); (b) AST scan of `uniride_core`, `optimizer_api`, `academic_benchmark`, `scripts`, root `*.py`: no import of a name containing `sota_common` (green today: guard); (c) the new manifest verifies (red today).
- **Change (per OQ-F1 a):** `archive_manifest scan`, then `quarantine --source uniride_core/algorithms/sota_common --archive archive/uniride_core/sota_common_legacy --archive-id sota_common_legacy` (default classifier: every file `REFERENCE_ONLY`); add `QUARANTINE.md` (copy the YAEM wording) and an "Archived on" entry in `archive/README.md`; delete the 9 `optimizer_api/strategies/sota_common/*.py` shims (pure re-exports, nothing to preserve); delete `optimizer_api/tests/test_sota_common_compat.py` and `uniride_core/tests/test_sota_common_migration.py`; correct `ebso_strategy.py:7-14`; add the new manifest to the list in `academic_benchmark/tests/test_archive_manifest_line_endings.py:28-29` [A: the developer checks whether that list must contain every manifest].
- **Files:** as above. **Acceptance:** red tests green; snapshot test, `academic_benchmark/tests` (archive and packaging tests), `uniride_core/tests`, `optimizer_api/tests` green.
- **Closes:** L3-e, L3-i. **Depends on:** OQ-F1. **Risk:** low. **Results change:** none (dead code, S-2). **Reviewer:** Sonnet.

### MT6F-02: Remove the `optimizer_api/utils` re-export shims (L3-d, audit `:1607`)

- [x] **MERGED `1f21fc29` (2026-10-27, Sonnet ONAY).** **Red test first** (`optimizer_api/tests/test_mt6f_no_utils_shims.py`): AST scan of every `.py` under `optimizer_api` (tests included), `academic_benchmark`, `uniride_core`, root: no `utils.<shim>` / `optimizer_api.utils.<shim>` import, static or by `importlib` string (red today, U-2/U-3); `find_spec` is `None` for each of the 20 modules (red).
- **Commit 1 (no behaviour change):** point the 5 production imports (U-2) at `uniride_core.algorithms.<module>` (same objects), then scripts and tests (U-3). Run the snapshot test and `optimizer_api/tests` with the shims still present.
- **Commit 2:** delete the 20 files and the compatibility tests `optimizer_api/tests/test_core_utility_shims.py`, `test_clustering_compat.py`, `test_time_window_violation_tracker_compat.py`; keep `test_architecture_boundaries.py:38-51` (it still forbids the names).
- **Acceptance:** red tests green; `import optimizer_api.main` smoke (an existing app-import test, e.g. `optimizer_api/tests/test_reload_env.py` [A]); snapshot and both test packages green; revert of commit 2 makes `find_spec` red.
- **Closes:** L3-d, shim part of MT6 row. **Depends on:** none (before MT6F-03, which edits `test_clustering_unit.py`). **Risk:** medium (an import error stops the API; mitigated by commit order). **Results change:** none. **Reviewer:** Sonnet.

### MT6F-03: Remaining L3 Python dead code (L3-f, L3-g, L3-h)

- [x] **MERGED `2174b160` (2026-10-27, Sonnet ONAY).** **Red tests first** (`uniride_core/tests/test_mt6f_dead_code_removed.py`, `optimizer_api/tests/test_mt6f_use_sota_engine_removed.py`): `clustering` has no `kmeans_clustering`, `initialize_centroids_kmeans_plus_plus`, `split_cluster`; `local_search_numba` has no `_three_opt_improve_numba`, `_three_opt_cases_numba`; `"use_sota_engine" not in OptimizationRequest.model_fields` and a request carrying `use_sota_engine: true` still validates (red, red, red; the last assertion green both).
- **Change:** delete `clustering.py:75-107`, `:110-164`, `:171-174` and their `__all__` lines; delete the tests that pin only them (`test_clustering_core.py` k-means cases, `test_clustering_unit.py:24, 36`, `test_h12_clustering_rng_threading.py:150-176` section "(d) legacy primitives"; record in the H12 tracker row that these pinned removed code); delete `local_search_numba.py:294-449`; update `CANONICAL_THREE_OPT_DESIGN.md:97` to say the `local_search_numba` copy was deleted (L3) and the `numba_accel` kernel stays unreachable (OQ-MT6-1 a); delete `schemas.py:282`.
- **Acceptance:** red tests green; regression command, all three Python suites, snapshot green.
- **Closes:** L3-f, L3-g, L3-h. **Depends on:** MT6F-02. **Risk:** low. **Results change:** none (no live caller). The API field disappears from the OpenAPI page; old clients are unaffected. **Reviewer:** Sonnet.

### MT6F-04: RUN "k2" move through the canonical 3-opt (R-1, R-2; audit `:1601`)

- [x] **MERGED `86f19817` (2026-10-27, Opus ONAY after one fix round).** **Change (per OQ-F2 b):** replace `_apply_3opt_bounded` by `_apply_random_cut_three_opt`: draw one admitted cut `(i, j, k)` within `validate_three_opt_window(window)` (canonical rules `j - i >= 2`, `k - j >= 2`, `n - k + i >= 2`, `three_opt.py:122-128`), candidates = `[tour] + generate_three_opt_candidates(tour, i, j, k, directed=not is_symmetric_matrix(dm))`, return the first minimum by `closed_tour_cost`; `n < 6` returns the tour unchanged; truthful docstrings (`run_tsp.py:18-25`, `:267-273`). Option a instead: delete case 5, rename, correct the docstring.
- **Red tests first** (`uniride_core/tests/test_mt6f_run_three_opt_move.py`, added to the regression command): with a stub RNG fixing the cut, the returned tour is the identity or the independent brute-force best of the canonical candidates (own enumerator, not importing the generator, design `:126`), symmetric and asymmetric n = 8/12 (red today: wrong candidate set, reversals on asymmetric); no duplicate candidate is costed (spy on the cost function: 8 calls symmetric, 2 directed; red today: 7 with a duplicate); same seed gives the same RUN result (green both).
- **Acceptance:** red tests green; `test_regression_gate.py`, `uniride_core/tests/sota_tsp`, `test_mt6_sota_deterministic_stop.py` green; if the two `SOTA-RUN-TSP` entries of `numba_sota_tsp_golden_pre_refusal.json` change, the developer regenerates only those two entries in a separate commit with the reason in the message (the golden pins routing refusal, not RUN quality). Under option a the golden must stay unchanged (it proves the no-change claim).
- **Closes:** the `run_tsp` part of OQ-MT6-7 a. **Depends on:** OQ-F2. **Risk:** low-medium (one academic, ungoverned solver). **Results change:** option b **yes**, `SOTA-RUN-TSP` only (academic, ungoverned, no profile, not production); no pooling of earlier RUN rows (A14). Option a: none. **Reviewer:** Opus for b (neighbourhood change), Sonnet for a.

### MT6F-05: Haversine stand-in: no salted hash, no forced asymmetry (L10-a, L10-b)

- [x] **MERGED `c09ef75c` (2026-10-27, Sonnet ONAY).** **Red test first** (`optimizer_api/tests/test_mt6f_haversine_deterministic.py`): run the same `get_submatrix(..., geo_coords=True)` (academic scope and opt-in fallback) in two subprocesses with different `PYTHONHASHSEED`; identical matrices (red today) and, per OQ-F3 a, symmetric (red today).
- **Change (per OQ-F3 a):** remove the synthetic asymmetry from `build_haversine_matrix` (`matrix_repository.py:842-866`: `asymmetric`, `asymmetry_range`, the `hash` lines) and the `asymmetric_haversine` parameter from `get_submatrix` (`:465-502`) and `DataLoader.get_submatrix` (`data_loader.py:105-119`); `geo_coords=True` gives the symmetric haversine stand-in. Option b instead: a stable digest (`hashlib.blake2b` of the ordered pair) and honour the flag at both sites.
- **Acceptance:** red test green; `test_c2_matrix_fail_closed.py`, `test_data_loader_matrix_helpers.py`, `test_academic_scope_parity.py`, snapshot green.
- **Closes:** L10-a, L10-b. **Depends on:** OQ-F3. **Risk:** low. **Results change:** none for current callers ([F] L10-b: no active caller passes `geo_coords=True`). **Reviewer:** Sonnet.

### MT6F-06: No unseeded generator; remove dormant random order (L10-c, L10-d)

- [x] **MERGED `4e116030` (2026-10-27, Sonnet ONAY).** **Red tests first** (`uniride_core/tests/test_mt6f_no_unseeded_rng.py`): monkeypatch `random.Random` in `tsp_meta_matrix_engine` and `fcm_split_engine` to record its argument; `optimize_permutation(..., seed=None)` must never pass `None` (red today), and the result reports the effective seed; `HybridLocalSearch` in both modules has no `use_random_order` parameter and no `rng` attribute (red today).
- **Change (per OQ-F4 a):** a missing seed resolves to the repository default 42 (one helper, e.g. reuse the `clustering.resolve_rng` pattern) at `tsp_meta_matrix_engine.py:47` and `fcm_split_engine.py:62, 187`, reported in `PermutationResult.seed`; delete `use_random_order` and `self.rng` (`local_search.py:664, 674, 692, 695, 730-731`; `local_search_numba.py:1011, 1029, 1033, 1054-1055`). `tsp_matrix_metaheuristics` (study path) is **not** changed now; it is listed in DURUM as a post-campaign item.
- **Acceptance:** red tests green; `fcm_tsp_golden_pre_refusal.json` tests and `test_fixed_budget_tables_unchanged.py` pass unedited (integer seeds unchanged); [A] the developer lists every caller of the two engines and shows each passes an integer.
- **Closes:** L10-c (except the deferred study-path module, named in the tracker), L10-d. **Depends on:** OQ-F4; after MT6F-03 (both edit `local_search_numba.py`). **Risk:** low. **Results change:** none for integer-seeded calls; `seed=None` calls become reproducible (they were never reproducible, so nothing to pool). **Reviewer:** Sonnet (Opus if OQ-F4 b brings in the study path).

### MT6F-07: Numba 3-opt wrapper contract (L10-f)

- [x] **MERGED `0dd7e753` (2026-10-27, Sonnet ONAY).** **Change (per OQ-F5 a):** no behaviour change. Docstrings of `ThreeOptLocalSearch` (`local_search_numba.py:745-794`) and `_build_or_get_dist_matrix` (`:97-117`) state the contract: unique location codes; with a prebuilt matrix (every active caller, L10-f) the objective is the matrix cycle; without one the fallback matrix optimises the closed cycle over the waypoints and the depot terms cancel. Tests pin it: duplicate codes raise a `ValueError` naming duplicates; the fallback objective equals the closed waypoint cycle on a depot-costed `duration_func`.
- **Acceptance:** new tests green (they document, so green both before and after, except a clearer error message if the developer adds one); regression command green.
- **Closes:** L10-f. **Depends on:** OQ-F5; after MT6F-06 (same file). **Risk:** low. **Results change:** none. **Reviewer:** Sonnet.

### MT6F-08: Frontend L3 items (per OQ-F6 b)

- [x] **MERGED `530930f7` (2026-10-27, Sonnet ONAY).** **Red tests first (vitest):** `vehicle-planning-page.tsx` does not exist; `src/app/api/sandbox/route.ts` exports only `POST`; `src/services/sandbox-api.ts` does not exist (all red today).
- **Change:** delete `src/app/(app)/admin/vehicle-planning/vehicle-planning-page.tsx` and its test; delete the `GET`/`PUT`/`DELETE` handlers (`route.ts:236-345` region) and `src/services/sandbox-api.ts`; keep `POST`. No database change: the `sandbox_scenarios` table and its RLS test (`src/lib/rls-route-plans-lock-migration.test.ts:39`) stay (live database writes are outside the delegation, A20 `:533`). `run/status` and `run/stop` go to MT7 with H14.
- **Acceptance:** `vitest`, `tsc` green; `src/app/api/sandbox/route.test.ts` (POST) green.
- **Closes:** L3-a, L3-c; L3-b recorded as moved to MT7. **Depends on:** OQ-F6. **Risk:** low. **Results change:** none. **Reviewer:** Sonnet.

### MT6F-09: Close the follow-up

- [x] **Documentation part DONE on branch `docs/mt6f-09-close`** (evidence file `docs/superpowers/plans/2026-10-27-mt6-followup-close-evidence.md`, checked commit `e8851f34`; Appendix J rows updated). The DECISION_LOG entry (A21 already holds every MT6F merge note) and DURUM.md are written by the lead. Original brief: Run section 2 on one clean `WIP` commit; Appendix J rows (split L3 and L10 from `:2365`; L10-e evidence = MT6-05 `9bd31aea`; L10-c `fuzzy_cmeans_enhanced` evidence = H12/QW7; H10 row `:2328`; H12 row if MT6F-03 removed its tests); regression command in `CANONICAL_THREE_OPT_DESIGN.md:144`; DECISION_LOG entry (suggest **A21 "MT6 follow-up plan and decisions"**, or an A19 bullet) with answers, test counts and the results-change statement; DURUM.md (deferred `tsp_matrix_metaheuristics` seed item, OQ-F8 item). **Reviewer:** Sonnet fact-check.

---

## 4. Lanes and order

```text
Answers first: OQ-F1..OQ-F8 (owner, or lead under A20)
Lane A (Python, serial):  MT6F-02 shims (redirect commit, then delete)
                            -> MT6F-03 dead code -> MT6F-06 seeds/random order -> MT6F-07 numba wrapper
Lane B (independent):     MT6F-01 sota_common archive
Lane C (independent):     MT6F-04 RUN k2 move
Lane D (independent):     MT6F-05 haversine stand-in
Lane E (frontend):        MT6F-08
Close:                    MT6F-09 after every merged item
```

**Production exposure:** the only items that touch production import paths are MT6F-02 (redirect before delete, two commits) and MT6F-05 (an unused branch). The snapshot test runs after every merge. MT6F-01 deletes a subpackage of `optimizer_api/strategies` that `strategies/__init__.py` never imports (S-2).

**Open items this plan depends on or must avoid (OQ-F7):**
- **D-04b2** (estimate on the stronger PC, DURUM.md `:21`) and the **pre-approval commit** (profile values, `.gitattributes`, approved run plan; DURUM.md `:22`; template `docs/designs/PAPER_SCALE_RUN_PLAN_TEMPLATE.md:14-19`: the campaign runs from the approved commit; a changed commit needs a new approval). No item here changes study code or timing, but every merge changes the commit. Rule: merge all items before D-04b2 is measured and before the prepare commit; if the hardware arrives first, stop merging and resume after the campaign; never merge between the approval commit and the campaign.
- **D-12** (publication, owner only): no dependency in either direction.

---

## 5. What changes results and what does not

| Item | Production SOTA `ebso`/`rdma`/`aoea` | Other production (hybrid users, `/compare`) | Academic SOTA-* | Bildiri / YAEM profiles |
|---|---|---|---|---|
| MT6F-01 | none (dead code) | none | none | none |
| MT6F-02 | none (same objects) | none | none | none |
| MT6F-03 | none | none (field never read) | none | none |
| MT6F-04 | none (RUN not in production) | none | **b: `SOTA-RUN-TSP` changes**; a: none | none (no SOTA ID in a profile) |
| MT6F-05 | none (no `geo_coords=True` caller) | none | none | none |
| MT6F-06 | none | none (`use_random_order` never set) | none | none (integer seeds; `tsp_matrix_metaheuristics` untouched) |
| MT6F-07 | none | none | none | none |
| MT6F-08 | none | none | none | none |

**No pooling (A14):** only `SOTA-RUN-TSP` rows from before and after MT6F-04 (option b) must not be pooled. **Study scientific values:** no file under `academic_benchmark/studies/` or `academic_benchmark/datasets/` is edited, and no module on the study execution path (`registry_setup.py`, `composition.py`, `objective_budget.py`, `three_opt.py`, `tsp_matrix_metaheuristics/*`, `sota_tsp/alns_tsp.py`) changes; MT6F-04 only imports from `three_opt.py`. The D-04b1/MT6-06 timing table is unaffected.

---

## 6. Owner questions

None is reserved to the owner by A20 (`:533`); the lead may answer under the delegation and record pros/cons. Recommendations in bold.

| # | Question | Options | Recommendation | Pros / cons |
|---|---|---|---|---|
| OQ-F1 | `sota_common` (2,465 lines): archive or delete | a) physical archive with the existing manifest tool; b) delete, rely on git history plus a DECISION_LOG note | **a** | a: follows the audit fix ("archive with a manifest", `:1252`, `:1425`) and the design's "physical archival" rule (`ACADEMIC_STUDY_UNIFICATION_DESIGN.md:25`); checksums prove what was removed; - tool's CLI is academic-labelled. b: less in the tree; - history only, no manifest |
| OQ-F2 | RUN k2 move | a) delete duplicate case 5, truthful name and docstring (no result change, R-1); b) canonical candidates for one random admitted cut, directed mode on asymmetric matrices; c) path 3-opt arrangements (7, reversals fully costed) | **b**, with approval that `SOTA-RUN-TSP` results change (no pooling) | a: zero risk; - keeps a second, incomplete reconnection set. b: one 3-opt family on every public path (MT6 goal, AGENTS "canonical algorithms in `uniride_core`"), correct ATSP semantics; - changes an ungoverned academic solver. c: complete set; - path semantics are for open sequences with a black-box objective (`CANONICAL_THREE_OPT_DESIGN.md:103`), RUN optimises a matrix cycle |
| OQ-F3 | Synthetic asymmetric haversine stand-in | a) remove it (symmetric stand-in only); b) stable digest and honour the flag | **a** | a: removes invented ±15 % data from a fail-closed opt-in fallback; no active caller. b: keeps the feature deterministic; - keeps made-up asymmetry |
| OQ-F4 | Missing seeds | a) `None` -> fixed default 42, reported, in the two matrix engines now; `tsp_matrix_metaheuristics` after the paper campaign; b) refuse `None` everywhere now, study path included; c) document only | **a** | a: same rule as H12 and production (`clustering.py:14-19`, `seed_utils.py:7-20`), no study-path change before the campaign (A20 L5). b: strictest; - edits study-path modules and many test constructors right before the campaign. c: defect stays |
| OQ-F5 | Numba 3-opt wrapper | a) document and pin the contract, no behaviour change; b) refuse the fallback matrix (prebuilt matrix required) | **a** | a: no caller uses the fallback (L10-f); the fallback cache has its own tests. b: fail-closed; - removes a tested feature for no current caller |
| OQ-F6 | Frontend L3 items | a) all here; b) `vehicle-planning-page.tsx`, sandbox `GET/PUT/DELETE` and `sandbox-api.ts` here, `run/status`/`run/stop` with MT7 (H14 polling); c) all to MT7 | **b** | b: removes clearly dead code now, leaves the two routes to the item that may reuse them. a: one pass; - may delete what H14 needs. c: frontend items stay open longer |
| OQ-F7 | Order against the paper campaign | a) merge everything before D-04b2 and the prepare commit, else pause until after the campaign; b) after the campaign | **a** | a: the campaign commit already contains the cleanup; no study change. b: zero interference; - L3/L10 stay open for weeks |
| OQ-F8 | `ls_engine` backend-dependent 2-opt/Or-opt/swap (N-2) | a) separate plan later (JIT parity task); b) include here | **a** | a: needs Numba parity work and changes production SOTA results; not in the A19 answer. b: one pass; - larger, result-changing scope |

---

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A redirected import breaks API start | Redirect commit before delete commit; snapshot test, app-import test and `optimizer_api/tests` after each |
| The archive tool refuses or mislabels a code tree | `scan` first; manifest verify test; reviewer checks every entry is `REFERENCE_ONLY` |
| Deleting H12 legacy-primitive tests looks like losing H12 evidence | The tests pinned only the removed functions; tracker H12 row notes it; the live strategies keep their H12 tests |
| MT6F-04 silently changes more than RUN | Change confined to `run_tsp.py`; golden for other SOTA IDs unchanged; Opus review |
| A merge lands between the approval commit and the campaign | OQ-F7 rule; DURUM entry |
| Agents slip into interactive Python or touch `tsplib.db` | Global constraints at the top of every brief; `test_patch.py` is only edited, never run |

## 8. Confirmed facts vs assumptions (summary)

- **Confirmed [F]:** S-1..S-6 (tool behaviour), U-1..U-4 including the audit correction U-2, L3-a..L3-i (L3-c refined: POST is live), L10-a/b/d/f, L10-c (two parts fixed, rest open), L10-e closed by MT6-05, R-1..R-5, N-2; no study profile, dataset manifest or study-path module is touched.
- **Assumptions [A]:** the archive tool runs on a non-academic source; whether `test_archive_manifest_line_endings.py` must list every manifest; string monkeypatch targets on shim paths; the exact app-import test name; that every caller of the two matrix engines passes an integer seed; whether the two `SOTA-RUN-TSP` golden entries change under OQ-F2 b.
