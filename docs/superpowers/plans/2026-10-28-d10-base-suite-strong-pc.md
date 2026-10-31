# D-10 base commit: full suite and pre-start checks on the stronger PC (2026-10-28)

Record of the stronger-PC session that followed `docs/handoff/2026-10-28-guclu-pc-temel-commit-test-istem.md`. Only measured results; no code, profile or document was changed.

## Base commit and conditions

- Base commit: `1a322a8f022970d6b7caaef37b127ce594c4d7b7`, message `docs: D-10 base commit: A18 note on the activation-ready test merge and the refreshed run plans; stronger-PC prompt for the full-suite run at this commit; DURUM (WIP frozen until the approval commit)`. Main checkout on `WIP`, equal to `origin/WIP` after `git fetch origin`; `git status --short` listed only the untracked `archive/docs/` files.
- Power plan (`powercfg /getactivescheme` typed directly in PowerShell before the start): `Power Scheme GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (Yüksek performans)`. Opera was running at the start (17 processes); load was not sampled.
- Clean checkout: `git worktree add C:\wt\d10-base-ck 1a322a8f022970d6b7caaef37b127ce594c4d7b7 --detach` (`$CK`); `git -C $CK status --short` printed nothing before the runs.
- Python: `C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe` (the main-checkout venv on this PC; the path in the Gate D plan does not exist here). `PYTHONPATH=C:\wt\d10-base-ck`, `PYTHON_BASIC_REPL=1`.

## Gate D command block on `$CK`

The block of `docs/superpowers/plans/2026-10-23-gate-d-analysis-documentation-publication.md:102-128`, run as `C:\wt\d10-base\block.ps1` with `pwsh`. Changes from the plan text: `<checkout>` = `$CK`; `$PY` as above; `Start-Process` has `-WorkingDirectory $CK` (this also applies to the two `git` lines); each line also prints its start time and wall seconds. Outputs in `C:\wt\gated\`.

| Line | Result | Start | Seconds | Summary |
|---|---|---|---|---|
| `schemas` | OK exit 0 | 19:40:22 | 3.5 | stdout and stderr empty |
| `focused` | OK exit 0 | 19:40:25 | 141.6 | `491 passed in 137.88s (0:02:17)` |
| `academic` | OK exit 0 | 19:42:47 | 872.8 | `3678 passed, 8 skipped, 43 warnings in 869.27s (0:14:29)` |
| `core` | OK exit 0 | 19:57:20 | 370.2 | `2571 passed, 179 skipped, 42 deselected, 5 warnings in 367.44s (0:06:07)` |
| `api` | FAIL exit '1' | 20:03:30 | 477.2 | `1 failed, 2932 passed, 4 warnings in 474.66s (0:07:54)` |
| `threeopt` | OK exit 0 | 20:11:27 | 7.3 | `62 passed in 5.58s` |
| `smoke_bildiri` | OK exit 0 | 20:11:34 | 2926.8 | `Descriptive report: descriptive_report.txt (14 table(s), index sha256 c1cd7df75474b750a74a9cb7fb60b6f950634cea83f0ab78661bc19d4262ced4)`; `Note: profile and analysis plan sha256 match the file(s) at commit 1a322a8f0229` |
| `smoke_yaem` | OK exit 0 | 21:00:21 | 2653.0 | `Descriptive report: descriptive_report.txt (8 table(s), index sha256 67d921646538fb0945db10294df93593e77c0cc1b04ecf3a2c52942925e7ae25)`; same sha256 note |
| `verify` | OK exit 0 | 21:44:34 | 3.0 | `OK C:\wt\gated\smoke-bildiri: 420 run manifest(s) verified`; `OK C:\wt\gated\smoke-yaem: 264 run manifest(s) verified`; both with the sha256 note |
| `diffcheck` | OK exit 0 | 21:44:38 | 0.1 | stdout and stderr empty |
| `status` | OK exit 0 | 21:44:38 | 0.1 | `status.out.txt` 0 bytes |

Skips in `$CK` are counted from the summary lines only (`$CK` has no `tsplib.db`, so database tests skip there; reasons were not collected separately).

### Failed test

- `optimizer_api/tests/test_phase0_containment.py::test_cli_filename_cannot_follow_symlink_outside_result_roots` (`optimizer_api\tests\test_phase0_containment.py:61`): `E   OSError: [WinError 1314]` (Windows message: the client does not hold a required privilege) when creating the symlink `...\results\outside-link.json` -> `...\outside.json` under the pytest temp folder. Probable cause: environment (symlink creation privilege on this Windows account), not code. Same failure as in the D-04b2 record.

## Database run in the main checkout

Main checkout at `1a322a8f022970d6b7caaef37b127ce594c4d7b7`, `PYTHONPATH` empty, 2400 s limit:
`.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests uniride_core/tests -m "not requires_ampl" -q -p no:cacheprovider -rs`

- Start 21:44:54, exit 0, 1294 s.
- Summary: `6267 passed, 169 skipped, 42 deselected, 48 warnings in 1289.51s (0:21:29)`.
- Skip reasons (`-rs`, grouped):
  - 157: `uniride_core\tests\test_exact_gurobi_day_backend.py`: `Gurobi through AMPL unavailable: AMPL could not start via amplpy default lookup: RuntimeError`
  - 6: `uniride_core\tests\test_three_opt_candidate_parity.py:407`: `window=None with the frozen generator is slow; best-improvement is covered by window=12`
  - 3: `academic_benchmark\tests\test_cx02_dashboard_obsolete_csv.py`: `could not import 'streamlit': No module named 'streamlit'`
  - 3: `academic_benchmark\tests\test_archive_manifest.py`: `symlink creation unavailable` (2) and `directory symlink unavailable` (1), each `[WinError 1314]`
- `git status --short` in the main checkout afterwards: only the untracked `archive/docs/` files.

## Pre-start checks C5-C7 (run plan section 7) on `$CK`

Run as `C:\wt\d10-base\c567.ps1` with `PYTHONPATH=$CK`, working directory `$CK`.

- **C5:** `pytest academic_benchmark/tests/test_analysis_environment.py -q -p no:cacheprovider`: `14 passed in 11.60s`, exit 0. `pip check`: `No broken requirements found.`, exit 0. `pip list --format=freeze`: `llvmlite==0.48.0`, `numba==0.66.0`, `numpy==2.4.6`.
- **C6:** `C:\wt\d10-base\which_package.py` printed `C:\wt\d10-base-ck\academic_benchmark\__init__.py` and `C:\wt\d10-base-ck\uniride_core\__init__.py`; exit 0.
- **C7:** `git -C $CK merge-base --is-ancestor <commit> 1a322a8f022970d6b7caaef37b127ce594c4d7b7` for the 32 commits of section 9 of `docs/run_plans/bildiri2026-2026-10-28.md` (read from `origin/docs/d10-run-plans-v2`): exit 0 for all 32 (`3d50a7e0`, `e24a5cd1`, `e9f11e72`, `a75cdde1`, `7c41237b`, `d0c73a8b`, `693d8fd2`, `dfaadc2d`, `9bd31aea`, `3146165e`, `80105327`, `1f21fc29`, `2174b160`, `530930f7`, `c09ef75c`, `4e116030`, `0dd7e753`, `86f19817`, `e8851f34`, `04612880`, `33f1fc2b`, `8513c2b6`, `cb449ed4`, `2323fb7a`, `1a9bd225`, `6efe8bb5`, `ecea6ee6`, `12bb24c9`, `565fcad3`, `bcef9feb`, `8ef7a23e`, `44c47434`).

C1-C4 were not run (campaign start, approval commit).

## Clean state after the runs

`git -C $CK status --short` after all runs (block line `status` and the end of `c567.ps1`): empty, 0 lines. `$CK` is kept for the campaign.
