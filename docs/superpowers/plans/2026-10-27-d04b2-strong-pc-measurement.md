# D-04b2 measurement on the stronger PC (2026-10-27)

Planning numbers, not evidence. The estimator's own words: "measured on a calibration slice on this machine. They say nothing about any algorithm; evaluation counts are upper bounds (local searches may stop earlier)." Native limits are printed by the tool as `PROVISIONAL, NOT A SCIENTIFIC SETTING` and are copied here unchanged.

Raw outputs stay outside the repository in `C:\wt\d04b2\` (`bildiri\estimate.txt|json`, `yaem\estimate.txt|json`, `bildiri-stdout.txt`, `yaem-stdout.txt`, `help.txt`, `pip-list.txt`, `schemas.txt`, `pytest.txt`, `timings.txt`).

## Machine and packages

| Item | Value |
|---|---|
| Host | YektaPC (desktop) |
| CPU | AMD Ryzen 7 2700X Eight-Core Processor (estimator: AMD64 Family 23 Model 8 Stepping 2, AuthenticAMD), 8 cores, 16 logical, max 3700 MHz |
| RAM | 31.9 GB |
| OS | Windows 11 Pro Insider Preview 10.0.26220 (build 26220) |
| Python (`.venv-jit`) | 3.14.7 |
| numpy / numba / llvmlite | 2.4.6 / 0.66.0 / 0.48.0 |
| scipy / statsmodels | 1.18.1 / 0.15.0 |
| pytest / ortools / pyvrp / highspy | 9.1.1 / 9.15.6755 / 0.14.1 / 1.15.1 |
| Node | v26.0.0 |
| `tsplib.db` present | yes (checked with `Test-Path` only) |
| `PYTHON_BASIC_REPL` | 1 (process and user) |

`.venv-jit` was created on this machine on 2026-10-27 with owner approval: `py -3.14 -m venv .venv-jit`; `pip install -e ".[test,solvers]" -c academic_benchmark/jit-benchmark-constraints.txt`; `pip install -r optimizer_api/requirements.txt -r optimizer_api/requirements-benchmark.txt -r requirements-analysis.txt -r requirements-exact.txt -r requirements-paper.txt -c academic_benchmark/jit-benchmark-constraints.txt`; `pip check`: no broken requirements.

## Commit and repository state

- Measured commit: `8513c2b6a0f82d2ebf19f76004f9bc6b840e3c2f` (`WIP`, equal to `origin/WIP` at the start).
- Estimator: `dirty: True` for both studies. Cause: 176 untracked files under `archive/docs/` in the main checkout (owner: known state, left as is). No tracked file modified.
- Ignored leftovers in the main checkout (not tracked, from before the fast-forward of 693 commits): `academic_benchmark/bildiri2026/`, `academic_benchmark/yaem2026/`, `uniride_core/algorithms/sota_common/`, `optimizer_api/strategies/sota_common/` (caches, old data files).

## Other load during the measurement

- Before the start, Process Lasso (about 1 core) and ProcessGovernor (about 0.65 core) were running; the owner closed both before the estimate runs.
- Remaining during the runs: the Claude desktop app (three `claude` processes, about 1.3 cores in total over a 10 s sample), MSI.TerminalServer (about 0.2 core). Windows load samples just before the start: 69 %, 43 %, 43 %.
- No other measurement, test or build ran during the estimate runs. The test run (Step 3) started after both estimates had finished.

## Commands and durations

| Command | Start | Duration | Exit |
|---|---|---|---|
| `estimate --help > C:\wt\d04b2\help.txt` | 22:46 | <5 s | 0 (flag names as in the prompt) |
| `estimate --study academic_benchmark/studies/bildiri2026/study.json --out ... --run-count 30 --native-global-iterations 1000 --native-polish-iterations 1000` | 22:46:48 | 118 s | 0 |
| same for `yaem2026` (first attempt) | 22:48:46 | 1 s | 2 (refused: output directory not empty) |
| same for `yaem2026` (rerun) | 22:49:13 | 649 s | 0 |
| `python -m academic_benchmark.contracts.export_schemas check` | 23:00:17 | 1 s | 0 (no output) |
| `pytest academic_benchmark/tests uniride_core/tests optimizer_api/tests -m "not requires_ampl" -q -p no:cacheprovider -rs` | 23:00:18 | 1395 s (pytest: 1390.79 s) | non-zero (25 failed) |

Run note: a quoting error in the runner script sent the Bildiri output to the folder `C:\wt\d04b2$s` instead of `C:\wt\d04b2\bildiri`; the folder was moved to `C:\wt\d04b2\bildiri` after the run (the `written:` line in `bildiri-stdout.txt` shows the original path). The first YAEM attempt was refused by the estimator because that same folder was not empty, and YAEM was rerun with the correct path. The runs were serial. The exit code written for pytest in `timings.txt` (0) is not valid (script error); the summary line shows 25 failed.

## Estimate tables (30 runs per cell, level indices 0 and 1 = 50x and 250x)

### Bildiri 2026 (`bildiri2026`, profile status draft)

Instances: berlin52, eil51, eil76, ft53, kroa100, rd100, st70. 10 fixed-budget algorithms, 2 native algorithms.

Fixed budget: **4200 runs, evaluation upper bound 1,722,960,000, estimated 50,479.8 s (14.02 h)** serial.

| Algorithm | Estimated time | eil51 us/eval | kroa100 us/eval |
|---|---|---|---|
| Core-TwoOpt-TSP | 3,436.2 s (0.95 h) | 13.29 | 23.59 |
| Core-ThreeOpt-TSP | 3,697.8 s (1.03 h) | 14.31 | 25.37 |
| Core-OrOpt-TSP | 3,337.1 s (0.93 h) | 14.34 | 22.12 |
| Core-GA-TSP | 4,702.7 s (1.31 h) | 22.96 | 29.66 |
| Core-PSO-TSP | 4,004.0 s (1.11 h) | 18.00 | 26.11 |
| Core-GA-TSP-Memetic-2opt | 4,124.6 s (1.15 h) | 19.38 | 26.43 |
| Core-GWO-TSP-Pure | 15,597.5 s (4.33 h) | 51.56 | 111.85 |
| Core-HHO-TSP-Pure | 4,878.5 s (1.36 h) | 19.62 | 33.07 |
| Core-GWO-TSP-Memetic-2opt | 3,372.9 s (0.94 h) | 13.41 | 22.95 |
| Core-HHO-TSP-Memetic-2opt | 3,328.6 s (0.92 h) | 13.56 | 22.47 |

Native at the provisional limits: **420 runs, estimated 33.9 s (0.01 h)** `[PROVISIONAL, NOT A SCIENTIFIC SETTING]`. Native limits: Core-GWO-TSP-Pure and Core-HHO-TSP-Pure `max_iterations=1000`. Native runs: GWO-Pure 0.030 s (eil51), 0.061 s (kroa100); HHO-Pure 0.095 s, 0.151 s, each over 1000 iterations.

Memetic GWO/HHO (60000 limits): projected iterations at the top level GWO-Memetic-2opt 5,750 (eil51, kroa100), HHO-Memetic-2opt 5,375 (eil51), 5,625 (kroa100); the tool reports "projected iterations stay within max_iterations" for all four rows.

### YAEM 2026 (`yaem2026`, profile status draft)

Instances: berlin52, eil51, kroa100, st70. 11 fixed-budget algorithms, 11 native algorithms.

Fixed budget: **2640 runs, evaluation upper bound 986,634,000, estimated 34,424.9 s (9.56 h)** serial.

| Algorithm | Estimated time | eil51 us/eval | kroa100 us/eval | kroa100 stop |
|---|---|---|---|---|
| Core-TwoOpt-TSP | 1,677.0 s (0.47 h) | 12.73 | 22.79 | evaluation_budget_exhausted |
| Core-ThreeOpt-TSP | 1,866.1 s (0.52 h) | 14.39 | 25.20 | evaluation_budget_exhausted |
| Core-OrOpt-TSP | 1,595.1 s (0.44 h) | 12.30 | 21.54 | evaluation_budget_exhausted |
| Core-GWO-TSP-Pure | 4,688.0 s (1.30 h) | 41.37 | 59.73 | evaluation_budget_exhausted |
| Core-HHO-TSP-Pure | 2,477.0 s (0.69 h) | 20.81 | 32.28 | evaluation_budget_exhausted |
| Core-GWO-TSP-Memetic-2opt | 1,694.0 s (0.47 h) | 13.50 | 22.58 | evaluation_budget_exhausted |
| Core-HHO-TSP-Memetic-2opt | 1,724.7 s (0.48 h) | 13.83 | 22.93 | evaluation_budget_exhausted |
| Core-GWO-TSP-Memetic-3opt | 4,965.7 s (1.38 h) | 32.33 | 71.14 | evaluation_budget_exhausted |
| Core-HHO-TSP-Memetic-3opt | 2,427.6 s (0.67 h) | 20.53 | 31.55 | evaluation_budget_exhausted |
| Core-GWO-TSP-Memetic-ALNS | 7,335.3 s (2.04 h) | 52.68 | 101.73 | stagnation_limit (198,832 of 247,500) |
| Core-HHO-TSP-Memetic-ALNS | 3,974.3 s (1.10 h) | 33.49 | 51.72 | stagnation_limit (198,678 of 247,500) |

Native at the provisional limits: **1320 runs, estimated 21,044.6 s (5.85 h)** `[PROVISIONAL, NOT A SCIENTIFIC SETTING]`. Limits: every algorithm `max_iterations=1000`; composites global 1000 and polish 1000.

| Native (PROVISIONAL, NOT A SCIENTIFIC SETTING) | eil51 run | kroa100 run | kroa100 per iteration |
|---|---|---|---|
| Core-TwoOpt-TSP | 0.734 s (47 it.) | 11.134 s (102 it.) | 0.1092 s |
| Core-ThreeOpt-TSP | 16.532 s (37 it.) | 129.017 s (72 it.) | 1.7919 s |
| Core-OrOpt-TSP | 3.512 s (41 it.) | 58.638 s (93 it.) | 0.6305 s |
| Core-GWO-TSP-Pure | 0.035 s (1000 it.) | 0.054 s (1000 it.) | 0.0001 s |
| Core-HHO-TSP-Pure | 0.093 s (1000 it.) | 0.144 s (1000 it.) | 0.0001 s |
| Core-GWO-TSP-Memetic-2opt | 0.760 s (1000 it.) | 4.933 s (1000 it.) | 0.0049 s |
| Core-HHO-TSP-Memetic-2opt | 0.825 s (1000 it.) | 5.032 s (1000 it.) | 0.0050 s |
| Core-GWO-TSP-Memetic-3opt | 12.924 s (1029 it.) | 107.339 s (1061 it.) | 0.1012 s (polish 1.7588 s) |
| Core-HHO-TSP-Memetic-3opt | 9.563 s (1022 it.) | 89.509 s (1051 it.) | 0.0852 s (polish 1.7522 s) |
| Core-GWO-TSP-Memetic-ALNS | 0.778 s (2000 it.) | 3.098 s (1604 it.) | 0.0019 s (polish 0.0050 s) |
| Core-HHO-TSP-Memetic-ALNS | 0.819 s (2000 it.) | 3.531 s (1697 it.) | 0.0021 s (polish 0.0048 s) |

## Side by side with the laptop measurements

Laptop: Intel64 Family 6 Model 154, 12 logical CPUs (DECISION_LOG A18 D-04b1, A19 MT6-06). In the MT6-06 run the laptop CPU was loaded by another program (A19).

| Item | Laptop D-04b1 (`2b3db473`) | Laptop MT6-06 (`78af0037`) | This PC D-04b2 (`8513c2b6`) |
|---|---|---|---|
| Bildiri fixed budget, serial | 45.1 h | 16.7 h | 14.02 h |
| Bildiri Core-ThreeOpt-TSP | 36.1 h | 1.0 h | 1.03 h |
| YAEM fixed budget, serial | 31.0 h | 11.5 h | 9.56 h |
| YAEM Core-ThreeOpt-TSP | 17.3 h | 0.5 h | 0.52 h |
| YAEM GWO / HHO Memetic-3opt | 4.6 h / 3.7 h | 1.75 h / 0.82 h | 1.38 h / 0.67 h |
| YAEM native | 5.8 h (limit 2) | 0.17 h (limit 2) | 5.85 h (limit 1000) |
| Core-ThreeOpt-TSP kroa100 us/eval | 965 | 25.7 | 25.37 (Bildiri), 25.20 (YAEM) |
| Core-GWO-TSP-Pure kroa100 us/eval | 80 | 148 | 111.85 (Bildiri), 59.73 (YAEM) |
| Native ThreeOpt kroa100 s/iteration | 63.3 | 1.36 | 1.7919 |
| Memetic-3opt polish kroa100 s/iteration | 65.6-68.2 | 1.18-1.39 | 1.7588 (GWO), 1.7522 (HHO) |

## Tests on this PC

`export_schemas check`: exit 0, no output.

pytest summary line: `25 failed, 9109 passed, 169 skipped, 42 deselected, 47 warnings in 1390.79s (0:23:10)`.

### Failures (not fixed; name, first error line, probable cause)

Ignored leftover directories in the main checkout (environment, 7) and the local `tsplib.db` (environment, 2):
- `TestPostArchivalBoundary.test_bildiri_source_tree_and_active_legacy_files_are_absent`: `Bildiri source tree still exists: ...\academic_benchmark\bildiri2026`.
- `TestPostArchivalBoundary.test_distribution_package_discovery_excludes_archive_and_bildiri`: `find_spec('bildiri2026', ...)` returns a namespace spec for `academic_benchmark\bildiri2026`.
- `test_legacy_yaem_package_is_absent_and_not_importable`: `academic_benchmark/yaem2026` exists.
- `test_distribution_discovery_excludes_archive_and_yaem`: `assert not True` (discovery finds the leftover directory).
- `test_the_real_instance_set_is_the_16_tsp_plus_ft53`: `At index 10 diff: 'rat99' != 'kroa100'` (cause corrected in the rerun section below: the local `tsplib.db`, not these directories).
- `test_without_ampl_the_runner_exits_with_code_3_and_writes_nothing`: exit 1 instead of 3, instance-set message (same cause as the line above).
- `test_sota_common_cannot_be_imported[uniride_core.algorithms.sota_common]` and `[optimizer_api.strategies.sota_common]`: namespace specs found for the leftover directories (9 ignored files each).
- `test_shim_directory_is_gone`: `optimizer_api/strategies/sota_common` exists.

Node module missing for the TypeScript CLI (environment, 9):
- `test_exact_option_intervals_equal_the_typescript_intervals[large+doblo_cap3-2026-10-05-50]`, `[large+doblo_cap3-2026-10-07-90]`, `[large+sedan-2026-10-05-50]`, `[large+sedan-2026-10-07-90]`: `node ... Error: Cannot find module 'server-only'`.
- `test_real_ts_cli_confirms_a_typed_cell_and_refuses_a_single_type`: CLI result differs (`source_manifests` diff).
- `test_with_the_real_cli_the_ga_and_union_selections_are_confirmed_and_the_row_is_proven`: `('missing', 'missing') == ('confirmed', 'confirmed')`.
- `test_sedan_2026_10_05_R60_L2_is_ga_menu_infeasible_for_L_with_the_union_cars_and_no_difference`: `'not_independently_confirmed' == 'ga_menu_infeasible_for_L'`.
- `test_slice_run_writes_manifest_csv_and_summary_without_blocking_errors`, `test_slice_manifest_records_commit_provenance_versions_run_history_and_limits`: `4 blocking error(s)`, `run_history.cells[...].cli_error: absolute path not allowed` (probable: the CLI error text after the node failure).

PyVRP 0.14.1 API (environment: `pyvrp>=0.9.0` is not pinned; 6):
- `test_holistic_engines_solve_tsp_and_atsp_as_single_vehicle_routes[tsp-PyVRP]`, `[atsp-PyVRP]`, `test_holistic_engines_solve_cvrp_as_routing_result[PyVRP]`, `test_holistic_engines_enforce_scalar_cvrp_demands[PyVRP]`, `test_solve_pyvrp_cvrp_returns_capacity_feasible_routes`, `test_solve_pyvrp_cvrptw_allows_waiting_for_ready_time`: `PyVRP optimization failed: Model.add_depot() got an unexpected keyword argument 'x'`.

Windows symlink privilege (environment, 1):
- `test_cli_filename_cannot_follow_symlink_outside_result_roots`: `OSError: [WinError 1314]` (symlink creation needs a privilege this user does not have).

### Rerun after environment fixes (2026-10-28, owner approval)

Changes to this PC only (no repository file changed): the four ignored leftover directories moved out of the repository to `C:\wt\leftover-backup-2026-10-27\` (not deleted); `npm ci` (exit 0; `node_modules/server-only` present); `pyvrp` 0.14.1 -> 0.13.4 in `.venv-jit` (0.14.0 replaced `x`/`y` in `Model.add_depot` with `location`; `pip check` clean).

Rerun of the nine files that held the 25 failures (`test_bildiri_quarantine_boundary.py`, `test_yaem_quarantine_boundary.py`, `test_exact_day_joint_runner.py`, `test_phase0_containment.py`, `test_exact_tsp_runner.py`, `test_exact_union_day_runner.py`, `test_holistic_matrix_engine.py`, `test_mt6f_sota_common_retired.py`, `test_pyvrp_cvrp_engine.py`), same flags: `3 failed, 212 passed, 5 warnings in 96.63s`.

- `test_cli_filename_cannot_follow_symlink_outside_result_roots`: `WinError 1314`, unchanged (Windows privilege).
- `test_the_real_instance_set_is_the_16_tsp_plus_ft53` and `test_without_ampl_the_runner_exits_with_code_3_and_writes_nothing`: unchanged, `'rat99' != 'kroa100'`. Correction to the cause given above: the instance set is read from `academic_benchmark/tsplib_data/tsplib.db` (`scripts/run_exact_tsp_reference.py:215-226`, TSP with `optimal` not null and dimension <= 100), not from the leftover data directories. The `tsplib.db` on this PC is 2,906,341,376 bytes, dated 2026-06-30 (file listing only; contents not read).

### Rerun with the laptop's `tsplib.db` (2026-10-28)

The owner copied the laptop's `tsplib.db` to this PC: 1,004,810,240 bytes, dated 2026-10-13 (file listing only; contents not read). Commit `33f1fc2bf4faa2fa9f726862289375a8081b525d` (`WIP`; lead note at merge `1a9bd225`: no file of the study path changed since `8513c2b6`); estimator `dirty: True` (untracked `archive/docs/` only). Outputs in `C:\wt\d04b2\` (`pytest-db2.txt`, `bildiri-db2\`, `yaem-db2\`, `timings-db2.txt`). Process Lasso and ProcessGovernor not running. CPU load was not sampled during these runs; after them: the Claude app about 0.5 core, explorer about 0.3 core, Opera open, Windows load samples 4 %, 54 %, 53 %, power plan Balanced ("Dengeli"), reported clock 3700 MHz.

| Command | Start | Duration | Exit |
|---|---|---|---|
| `pytest uniride_core/tests/test_exact_tsp_runner.py::test_the_real_instance_set_is_the_16_tsp_plus_ft53 ...::test_without_ampl_the_runner_exits_with_code_3_and_writes_nothing -m "not requires_ampl" -q -p no:cacheprovider -rfs` | 00:29 | 7 s | 0: `2 passed in 4.92s` |
| `estimate` Bildiri (same flags as above) | 00:29:18 | 154 s | 0 |
| `estimate` YAEM (same flags as above) | 00:31:52 | 938 s | 0 |

All non-time fields of both estimate outputs are identical to the first run on the old `tsplib.db` (runs, evaluation upper bounds, evaluations and stop reason per calibration row, iterations reached, native iteration counts; checked with a text diff after masking times and the commit line). Times differ:

| Item | First run (`8513c2b6`, old db) | Rerun (`33f1fc2b`, laptop db) |
|---|---|---|
| Bildiri fixed budget | 14.02 h | 18.87 h |
| Bildiri native | 0.01 h | 0.01 h |
| YAEM fixed budget | 9.56 h | 13.12 h |
| YAEM native | 5.85 h | 8.58 h |
| Core-ThreeOpt-TSP kroa100 us/eval | 25.37 (Bildiri), 25.20 (YAEM) | 29.26 (Bildiri), 35.27 (YAEM) |
| Core-GWO-TSP-Pure kroa100 us/eval | 111.85 (Bildiri), 59.73 (YAEM) | 154.35 (Bildiri), 77.42 (YAEM) |
| Native ThreeOpt kroa100 s/iteration | 1.7919 | 2.4368 |
| Memetic-3opt polish kroa100 s/iteration (GWO, HHO) | 1.7588, 1.7522 | 2.5808, 2.5882 |

Rerun per-algorithm fixed-budget estimates. Bildiri: TwoOpt 1.21 h, ThreeOpt 1.25 h, OrOpt 1.18 h, GA 1.89 h, PSO 1.61 h, GA-Memetic-2opt 1.62 h, GWO-Pure 5.97 h, HHO-Pure 1.80 h, GWO-Memetic-2opt 1.23 h, HHO-Memetic-2opt 1.12 h. YAEM: TwoOpt 0.58 h, ThreeOpt 0.68 h, OrOpt 0.59 h, GWO-Pure 1.63 h, HHO-Pure 0.97 h, GWO-Memetic-2opt 0.73 h, HHO-Memetic-2opt 0.71 h, GWO-Memetic-3opt 1.85 h, HHO-Memetic-3opt 1.00 h, GWO-Memetic-ALNS 2.90 h, HHO-Memetic-ALNS 1.47 h.

### Skips (169)

- 157: `uniride_core/tests/test_exact_gurobi_day_backend.py` (126 + 1 + 28 + 1 + 1): `Gurobi through AMPL unavailable: AMPL could not start via amplpy default lookup: RuntimeError`.
- 6: `uniride_core/tests/test_three_opt_candidate_parity.py:407`: `window=None with the frozen generator is slow; best-improvement is covered by window=12`.
- 3: `academic_benchmark/tests/test_archive_manifest.py:436, 573, 774`: symlink creation unavailable (`WinError 1314`).
- 3: `academic_benchmark/tests/test_cx02_dashboard_obsolete_csv.py:54, 61, 67`: `could not import 'streamlit'`.
- 42 deselected by `-m "not requires_ampl"`.
