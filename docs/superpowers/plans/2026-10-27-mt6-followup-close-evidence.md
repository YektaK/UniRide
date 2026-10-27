# MT6 follow-up (MT6F-01..09): close evidence

Plan: `docs/superpowers/plans/2026-10-27-mt6-followup-sota-common-shims-l3-l10.md`, section 2 (acceptance 1-8). Decisions and merge notes: `docs/DECISION_LOG.md` A21.

## 1. What was checked

- Commit checked: `e8851f34b1803f2c1384525d4694f7528ff54276` (`WIP`, "docs(decision-log): A21 MT6F-07 merged"), in a clean detached-from-main worktree `C:\wt\mt6f09` on branch `docs/mt6f-09-close`. `git status --short` was empty before the documentation edits.
- Date: 2026-10-27. Windows 11, Python 3.14.6 (`.venv-jit`), `PYTHONPATH=C:\wt\mt6f09`, Node with the main checkout's `node_modules` linked into the worktree by a temporary junction (removed afterwards).
- No benchmark, no timing run, no AMPL, `test_patch.py` not run. Database-dependent tests skip in a worktree (listed below).

## 2. Commands and results (before any edit)

| Command | Result |
|---|---|
| `python -m academic_benchmark.contracts.export_schemas check` | exit code 0, no output |
| `pytest uniride_core/tests -m "not requires_ampl" -rs` | `2697 passed, 23 skipped, 42 deselected, 3 warnings in 505.10s` |
| `pytest academic_benchmark/tests -m "not requires_ampl" -rs` | `3628 passed, 5 skipped, 43 warnings in 712.65s` |
| `pytest optimizer_api/tests -m "not requires_ampl" -rs` | `2833 passed, 3 warnings in 444.34s` |
| canonical 3-opt regression command (`CANONICAL_THREE_OPT_DESIGN.md:144`, 12 modules, run with `-rs`) | `548 passed, 6 skipped in 95.42s` |
| `pytest academic_benchmark/tests/test_production_registry_snapshot.py` | `2 passed in 4.48s` |
| `archive_manifest verify` `archive/academic_benchmark/bildiri2026_legacy/manifest.json` | `verified 233 entries` |
| `archive_manifest verify` `archive/academic_benchmark/yaem2026_legacy/manifest.json` | `verified 159 entries` |
| `archive_manifest verify` `archive/uniride_core/sota_common_legacy/manifest.json` | `verified 9 entries` |
| `npx vitest run` | `Test Files 95 passed (95)`, `Tests 1183 passed (1183)` |
| `npx tsc --noEmit` | exit code 0, no output |
| `git status --short` | empty |
| `git diff --stat 488dc937 e8851f34 -- academic_benchmark/studies academic_benchmark/datasets` | NOT empty: `academic_benchmark/studies/run.py`, 7 insertions, 2 deletions (see item 6 below) |

After the documentation edits, the 42 test files that mention the audit, DECISION_LOG or plan paths, plus `test_gate_d_docs_consistency.py`, were re-run: `1496 passed, 7 skipped in 326.27s` (the 7 skips are the `test_exact_tsp_runner.py:57` empty-database skips).

The archive verify form is `python -m academic_benchmark.archive_manifest verify --repo-root <worktree> --manifest <repo-relative manifest.json>`.

### Skip list

- `uniride_core/tests`: 1 `test_pyvrp_cvrp_engine.py:3` (no module `pyvrp`); 7 `test_exact_tsp_runner.py:57` (tsplib.db has no coordinates/problems table, empty database in the worktree); 9 in `test_exact_union_day_runner.py` (lines 146 x4, 259, 322, 333, 352, 449: node or `node_modules/tsx` not installed, TS confirmation CLI); 6 `test_three_opt_candidate_parity.py:407` (window=None with the frozen generator is slow; window=12 covers best-improvement).
- `academic_benchmark/tests`: 3 `test_cx02_dashboard_obsolete_csv.py` (lines 54, 61, 67: no module `streamlit`); 1 `test_exact_day_joint_runner.py:391` (node or `node_modules/tsx` not installed); 1 `test_exact_published_tours.py:125` (tsplib.db has no `problems` table, empty file created by a first read, audit M16).
- `optimizer_api/tests`: none.
- Regression command: the same 6 `test_three_opt_candidate_parity.py:407` skips.
- Note: the test run created an empty, git-ignored `academic_benchmark/tsplib_data/tsplib.db` (4096 bytes) inside the temporary worktree. It was not opened or touched by hand and goes away with the worktree.

## 3. Acceptance items 1-8

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | `sota_common` cannot be imported; core tree archived with a verifying manifest; no active import | met | `uniride_core/tests/test_mt6f_sota_common_retired.py` (5 tests, in the passing core suite); `archive/uniride_core/sota_common_legacy/manifest.json` verifies (9 entries); MT6F-01 merge `80105327`; A21 note |
| 2 | 20 `optimizer_api/utils` shims gone; AST guard; app import works; snapshot test unchanged and green | met | `optimizer_api/tests/test_mt6f_no_utils_shims.py` (passing API suite); `test_production_registry_snapshot.py` 2 passed; the `optimizer_api` suite imports the app; MT6F-02 merge `1f21fc29`; A21 note |
| 3 | L3-f, L3-g, L3-h removed with tests; frontend per OQ-F6 | met | `uniride_core/tests/test_mt6f_dead_code_removed.py`, `optimizer_api/tests/test_mt6f_use_sota_engine_removed.py`; MT6F-03 merge `2174b160`; frontend `src/app/api/sandbox/dead-code-removal.test.ts` in the vitest run (1183 passed); MT6F-08 merge `530930f7`; L3-b moved to MT7 with H14 as decided (OQ-F6 b) |
| 4 | Every L10 bullet fixed with red/green test or recorded as closed | met, one part deferred by decision | L10-a/b `optimizer_api/tests/test_mt6f_haversine_deterministic.py`, merge `c09ef75c`; L10-c two engines `uniride_core/tests/test_mt6f_no_unseeded_rng.py` and L10-d, merge `4e116030`; L10-f `uniride_core/tests/test_mt6f_numba_three_opt_contract.py` (pins existing behaviour, green before and after, OQ-F5 a), merge `0dd7e753`; L10-c `fuzzy_cmeans_enhanced` already fixed by H12/QW7; L10-e closed by MT6-05 `9bd31aea`. Deferred by decision (OQ-F4 a, A20 L5): `tsp_matrix_metaheuristics/*` seeds |
| 5 | RUN k2 move through canonical 3-opt, independent test, test in the regression command | met | `uniride_core/tests/test_mt6f_run_three_opt_move.py`, listed in the regression command (548 passed); MT6F-04 merge `86f19817`; golden entry `tsp:SOTA-RUN-TSP` changed (same cost, opposite orientation), other entries unchanged; no pooling of earlier RUN rows (A14) |
| 6 | Bildiri/YAEM results unchanged; no file under `studies/` or `datasets/` changed | met in substance, literal command not empty | The guard tests `test_fixed_budget_tables_unchanged.py`, `test_mt6_budgeted_tolerance.py`, the `gwo_hho_native_pre_schedule.json` and `fcm_tsp_golden_pre_refusal.json` based tests are inside the passing suites, unedited by MT6F. For each of the 8 MT6F merge commits `git diff <merge>^1 <merge> -- academic_benchmark/studies academic_benchmark/datasets` is empty. The literal range `488dc937..e8851f34` shows `academic_benchmark/studies/run.py` (7 insertions, 2 deletions): it comes from the non-MT6F merge `2c718c9c` (analysis polish 2; commits `4029ffdd`, `ac7893b1`), a docstring paragraph and one report sentence ("exits 1 when the report is written (2 if it is refused)"), no scientific value. No `datasets/` change |
| 7 | Three Python suites, regression command, vitest and tsc pass; counts recorded | met | section 2 above |
| 8 | Appendix J rows: L3 and L10 split out; H10 row; H12 row | met | `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md` rows L3-a/c, L3-d, L3-e/i, L3-f/g/h, L10-a/b, L10-c, L10-d, L10-f all say FIXED with merge commits; collective row L3, L9-L10, L12-L13 now says L3 and L10 are split out; H10 row names `86f19817` (run_tsp) and `80105327` (sota_common archived); H12 row names `2174b160` |

## 4. Merge commits

| Item | Merge | Audit rows |
|---|---|---|
| MT6F-01 | `80105327` | L3-e, L3-i |
| MT6F-02 | `1f21fc29` | L3-d |
| MT6F-03 | `2174b160` | L3-f, L3-g, L3-h; H12 row note |
| MT6F-04 | `86f19817` | H10 row (run_tsp) |
| MT6F-05 | `c09ef75c` | L10-a, L10-b |
| MT6F-06 | `4e116030` | L10-c (two engines), L10-d |
| MT6F-07 | `0dd7e753` | L10-f |
| MT6F-08 | `530930f7` | L3-a, L3-c |
| MT6F-09 | this branch (`docs/mt6f-09-close`), documentation only | Appendix J, plan ticks |

## 5. Deferred or open (all decided earlier, nothing new)

- `tsp_matrix_metaheuristics/*` keep their `random_seed=None` defaults; seeds are fixed after the paper campaign (A20 L5, OQ-F4 a). Listed in DURUM.md by the lead.
- Backend-dependent `ls_engine` 2-opt/Or-opt/swap layers (OQ-F8 a): separate later plan; changes production SOTA results.
- L3-b (`run/status`, `run/stop` BFF routes without a client): moved to MT7 with H14, still open there.
- Follow-ups recorded in the A21 notes as polish: `uniride.egg-info/SOURCES.txt` still lists deleted paths; the shim guard does not scan `scripts/`; a test fake in `uniride_core/tests/test_mutation_proof_tsp.py:109` still accepts the removed keyword; the live admin vehicle-planning page has no test for the matrix-error toasts; RUN's k1 2-opt, `_follow_guide` and `_avoid_worst_edges` still reverse segments on ATSP matrices; the constant-matrix tie test has an unused `symmetric` parameter.
- The plan file header still reads "Status: DRAFT for owner approval"; not changed here.
- DECISION_LOG and DURUM.md entries for the close are written by the lead (not edited on this branch).
