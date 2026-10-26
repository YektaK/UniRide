# Gate D and MT6 close evidence (items D-13 and MT6-07)

Date: 2026-10-26. Checked commit: `04612880` (`WIP`, code identical to `a9372e73` plus a decision-log line). This file and the status edits that go with it were written afterwards on branch `docs/gated-mt6-07-d13-close`; they change documentation and one documentation test only.

What this file is: a record of what was run and what it showed. It claims nothing beyond that. Planned references: Gate D plan section 2 (criteria 1-11) and MT6 plan section 2 (items 1-6); DECISION_LOG A18, A19, A20 (L1: Gate D closes with D-04b2 deferred as a precondition of the paper-scale run, not as an acceptance item; D-12 publication needs the owner's explicit permission and is not part of this record).

## 1. Environment

- Windows 11, interpreter `.venv-jit` of the main checkout, `PYTHONPATH=C:/wt/close` (a clean worktree of the commit), `PYTHON_BASIC_REPL=1`.
- Python 3.14.6, numpy 2.4.6, numba 0.66.0, llvmlite 0.48.0, scipy 1.18.1, statsmodels 0.15.0, setuptools 84.2.1, pytest 9.1.1.
- The worktree has no `tsplib.db`. Tests that need the real database skip (listed in section 4). The lead runs the real-database suite separately in the main checkout and records those counts in the decision log; they are not in this file.
- Adaptation of the plan's command block: the block is PowerShell (`Invoke-Limited`). I ran the same commands from bash with `timeout` instead, added `-rs` to every pytest call so skips are listed, and wrote the smoke output to `C:/wt/close-scratch/post-smoke-bildiri` and `post-smoke-yaem` (outside the repository) instead of `C:\wt\gated`. The 3-opt block was run twice: as written in `CANONICAL_THREE_OPT_DESIGN.md:144` and as written in the Gate D block (which names `test_canonical_three_opt.py`, `test_canonical_three_opt_integration.py` and the registry snapshot). `test_mt6_sota_deterministic_stop.py` is in neither command, so it was run separately. The boundary tests of criterion 9 were run as one line. The suites ran after the two smoke commands (the plan lists them before); the order has no effect on the results. Raw outputs are in `C:/wt/close-scratch/post/`.

## 2. Commands and results (commit `04612880`)

| Check | Command (short form) | Result |
|---|---|---|
| Schema check | `python -m academic_benchmark.contracts.export_schemas check` | exit 0, no output |
| Gate D focused block, 14 modules (the 13 of the plan plus `test_problem_type_canonical.py`) | `python -m pytest <modules> -q -rs -p no:cacheprovider --tb=short` | 499 passed, 0 skipped, 125.8 s |
| Academic suite | `pytest academic_benchmark/tests -m "not requires_ampl"` | 3552 passed, 5 skipped, 582.5 s |
| Core suite | `pytest uniride_core/tests -m "not requires_ampl"` | 2606 passed, 23 skipped, 42 deselected, 372.5 s |
| API suite | `pytest optimizer_api/tests -m "not requires_ampl"` | 2792 passed, 0 skipped, 333.8 s |
| 3-opt regression command (`CANONICAL_THREE_OPT_DESIGN.md:144`, 10 modules) | `pytest <modules> -q -rs ...` | 480 passed, 6 skipped |
| Gate D 3-opt block (8 modules incl. `test_production_registry_snapshot.py`) | `pytest <modules> -q -rs ...` | 62 passed |
| MT6 deterministic stop plus registry snapshot | `pytest uniride_core/tests/test_mt6_sota_deterministic_stop.py academic_benchmark/tests/test_production_registry_snapshot.py` | 68 passed |
| Import boundaries (`test_yaem_quarantine_boundary.py`, `test_bildiri_quarantine_boundary.py`, `uniride_core/tests/test_archive_boundaries.py`) | `pytest <3 modules>` | 43 passed |
| Smoke, Bildiri | `python -m academic_benchmark.studies.run --study academic_benchmark/studies/bildiri2026/study.json --mode smoke --out <outside folder>` | exit 0; 252 planned, 252 completed, 0 failed; 14 report tables; index sha256 `af1db06c5b59b21c0f9ccd80c644909761950e8531f893e37fc3b5c722252634` |
| Smoke, YAEM | same with `yaem2026/study.json` | exit 0; "Every planned run completed and every row passed validation"; 8 report tables; index sha256 `6be4d855dd8ade00d93ef7170101091fa5c27d0682b96c6fed8dccc424745897` |
| Manifest verification | `python -m academic_benchmark.studies.verify_manifests <both folders>` | exit 0; 252 and 264 run manifests verified; profile and plan hashes match the files at the commit |
| `git diff --check` | | exit 0, no output |
| `git status --short` (before any edit) | | no output |

The 3-opt regression command passes at the same commit as the other checks. The registry snapshot test (`test_production_registry_snapshot.py`) passed in the Gate D 3-opt block and in the MT6 line.

## 3. Criteria

Gate D plan section 2 (all lines are about commit `04612880` unless stated):

| No. | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Comparison identity (D-01) | met | `test_gate_d_comparison_identity.py` in the focused block (499 passed); merged `6fa88a9d` (A18) |
| 2 | Run manifests (D-02) | met | `test_run_manifest_writer.py` in the focused block; both smoke folders verify (252 and 264 manifests, `verify_manifests` exit 0); merged `6e704d8b`, run index v2 `0e3d0ee8` |
| 3 | Paper mode guards (D-03) | met | `test_study_run_service.py` in the focused block; merged `7fd27979`. Paper mode was not executed here; the guards are shown by tests only |
| 4 | Statistics (D-05) | met | `test_analysis_statistics.py` in the focused block; merged `d8259753` |
| 5 | Gap columns (D-06) | met | `test_analysis_gap_columns.py` and, for the real reference table, `test_problem_type_canonical.py` (smoke study through the run service with the committed reference, descriptive report required); merged `6416ab6e`, problem-type fix `a9372e73` |
| 6 | Profiles | met | both smoke CLIs exit 0 at `04612880`; the profiles and plans load, preflight and smoke-run through the D-03 service; `fix/fixed-budget-hygiene` merged before D-03 (A18); profile values are checked by the owner-approval step, see section 6 |
| 7 | No invalid evidence reachable from active reporting (D-08b) | met | `test_gate_d_reporting_sweep.py` in the focused block; merged `b814b674` |
| 8 | Descriptive smoke reports (D-07) | met | `descriptive_report.txt/json` exist in both smoke folders with the mode, commit, dirty flag, plan hash and manifest index checksum in the banner; the columns are n, median, iqr, min, max, mean, sd as the analysis plan declares; `test_analysis_report.py` (wording check) passes; merged `25333088` |
| 9 | Suites and packaging | met | schema check exit 0; academic, core and API suites pass with the skips in section 4; 3-opt regression plus snapshot pass; `test_gate_d_packaging.py` passed without a skip (wheel built locally in `.venv-jit`; no CI wheel job was run, so no job link exists); boundary tests 43 passed; `git diff --check` clean |
| 10 | Documentation consistent (D-11) | met | `test_gate_d_docs_consistency.py` passes (in the focused block, and again after the edits of this branch, section 5); merged `69bd7168` |
| 11 (clean-tree part) | `git status --short` empty | met | empty after all suites and smoke runs, in the integration worktree at `04612880` |
| 11 (publication part) | D-12 | deferred (owner permission; not part of this record) | |
| D-04b2 | final estimate on the stronger computer | deferred (A20 L1): precondition of the paper-scale run, not a Gate D acceptance item | no criterion above depends on it |

MT6 plan section 2:

| No. | Item | Status | Evidence |
|---|---|---|---|
| 1 | No `numba_accel` 3-opt symbol reachable from a public entry point (H10) | met | `uniride_core/tests/test_mt6_no_forbidden_three_opt.py` and `academic_benchmark/tests/test_mt6_sota_executors_no_forbidden_kernel.py` in the 3-opt regression command (480 passed, 6 skipped); merged `d0c73a8b` |
| 2 | Canonical candidate parity and full-run parity (M25) | met | `uniride_core/tests/test_three_opt_candidate_parity.py` (same command; 6 cases with `window=None` skip by design); merged `7c41237b` |
| 3 | Same seed gives the same route and cost for every SOTA solver under a fake clock and under CPU load (H11) | met | `uniride_core/tests/test_mt6_sota_deterministic_stop.py` (68 passed with the snapshot test); merged `693d8fd2`, polish `3146165e`. The "5 real runs under induced CPU load" part is what that test module checks; this record did not repeat it by hand |
| 4 | Production hybrid uses the core-owned neighbourhood with an independent reference enumerator; `_three_opt_cases` deleted (M14) | met | `uniride_core/tests/test_mt6_path_three_opt.py` and `test_local_search_core.py` in the 3-opt regression command; merged `dfaadc2d` |
| 5 | Regression command, new MT6 modules and the three suites pass; counts recorded; snapshot unchanged | met | section 2; A19 holds the lead's earlier post-merge counts. `uniride_core/tests/test_mt6_budgeted_tolerance.py` (MT6-05, merged `9bd31aea`) is in the regression command |
| 6 | Appendix J rows FIXED with commits; A19 records approvals, no-pooling statements and the re-measured D-04b1 rows | met | rows H10, H11, M14, M25 and N-1 of Appendix J say FIXED/merged with commits and test names; A19 holds the approvals and the MT6-06 re-measure (planning numbers) |

## 4. Skips (commit `04612880`, `-rs`)

Academic suite, 5 skips:
- 3 in `test_cx02_dashboard_obsolete_csv.py` (lines 54, 61, 67): `streamlit` is not installed.
- 1 in `test_exact_day_joint_runner.py:390`: node or `node_modules/tsx` is not installed (TS confirmation CLI).
- 1 in `test_exact_published_tours.py:125`: `tsplib.db` has no `problems` table (the worktree has no real database).

Core suite, 23 skips (42 tests deselected by `not requires_ampl`):
- 1 in `test_pyvrp_cvrp_engine.py:3`: `pyvrp` is not installed.
- 7 in `test_exact_tsp_runner.py:57`: `tsplib.db` is empty or a placeholder.
- 9 in `test_exact_union_day_runner.py` (lines 146 (4 tests), 259, 322, 333, 352, 449): node or `node_modules/tsx` is not installed.
- 6 in `test_three_opt_candidate_parity.py:407`: `window=None` with the frozen generator is slow; best-improvement is covered by `window=12`.

3-opt regression command: the same 6 parity skips. API suite and the Gate D focused block: no skips.

## 5. Checks after the documentation edits of this branch

The Gate D status phrase was changed to "Gate D is closed except D-12 (publication, owner permission); D-04b2 (final estimate on the stronger computer) is a precondition of the paper-scale run, not a Gate D acceptance item" in `docs/UNIRIDE_WORKSTATE.md` (row ACAD-01), `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, `README.md`, `UniRide_Ultimate_Audit.md` and in `GATE_D_STATUS_PHRASE` of `academic_benchmark/tests/test_gate_d_docs_consistency.py` (the test still checks all five documents).

First run after the edits: 312 passed, 2 failed. The two failures were `test_the_paper_run_preconditions_are_mt6_d04b2_and_oq4` for `ACTIVE_ROADMAP.md` and `CURRENT_ARCHITECTURE.md`, which look for a sentence starting "Preconditions of any paper-scale run" that names MT6, D-04b2 and OQ-4. I rewrote that sentence in both documents (MT6 done, OQ-4 answered, D-04b2 open) and did not change the test. Second run: `test_gate_d_docs_consistency.py`, `test_gate_d_redline_applied.py`, `test_gate_d_run_plan_template.py`, `test_archive_manifest.py`, `test_fixed_budget_tables_unchanged.py`: 158 passed. The first run also covered `test_gate_d_packaging.py`, `test_exact_inputs_confinement.py`, `test_exact_reference_reader.py`, `uniride_core/tests/test_exact_gap_report.py`, `uniride_core/tests/test_local_search_matrix_isolation.py` and `optimizer_api/tests/test_single_data_loader_root.py`; apart from the two failures above they passed. Outputs: `C:/wt/close-scratch/post/after_edits.out.txt` and `after_edits2.out.txt`.

## 6. Deferred and owner-only

- D-04b2: final cost estimate with the chosen run counts on the stronger computer (A20 L1). Needed before the paper-scale run.
- D-12: publication (push and draft PR, OQ-13 a). Needs the owner's explicit permission, on the same commit the checks ran on; its text must say that paper-scale runs and the full-suite verification on the stronger computer are still pending.
- Profile values: both study profiles and both analysis plans are still `draft` and smoke-only (`run_count` 3 in the files; the owner confirmed 30 runs per cell in A18, 2026-10-26, which is not yet in the files). The values enter the files in the owner's pre-approval commit; no paper-scale run exists, and smoke runs and cost estimates support no superiority, causality or proof claim.
- Real-database suite on the main checkout: run by the lead; counts go to the decision log.
- CI wheel job: not run; the packaging test ran locally.

## 7. Found during the close check

The first run of this record at `eeeb727b` ended with exit 2 for both smoke commands: the run itself completed and 252 and 264 manifests verified, but the descriptive report was refused with `berlin52: row problem type 'tsp' differs from the exact reference contract 'TSP'`. The run service stores the lowercase problem type in every row (`academic_benchmark/studies/run.py:165, :173`), the exact-reference records carry the uppercase contract, and `academic_benchmark/analysis/gaps.py` compared the two as plain strings. Every suite was green because the gap tests used uppercase rows and no test ran a smoke study together with the real reference table. Fix: A20 L10, merged `a9372e73` (fix commit `9d71c27e`; red tests `f9904bbc`, `5e04e449`): the analysis layer compares problem types as canonical `ProblemContract` values through `academic_benchmark/analysis/problem_contract.py`. New test: `academic_benchmark/tests/test_problem_type_canonical.py`, which runs `run_study` on profile slices of both studies with the committed reference table and requires the descriptive report with gap columns; the reviewer showed it fails with the original refusal when the old comparison is restored (A20 L10). All checks in section 2 were then re-run in full on `04612880`.
