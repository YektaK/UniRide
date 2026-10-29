# D-10 paper-scale campaign record (stronger PC, 2026-10-29)

Record of the stronger-PC session that followed "İstem A" of `docs/handoff/2026-10-29-guclu-pc-kampanya-istem.md`. Only measured results; no code, profile or document was changed.

## Commits and paths

- Approval commit `<approval>`: `2c7c5996ca1e924ef31c71f0c84164d3148deaf9` (`git log -1 --format=%H --grep="^D-10 approval commit:" origin/WIP`).
- Base commit `<base>`: `1a322a8f022970d6b7caaef37b127ce594c4d7b7` (`git log -1 --format=%P <approval>`).
- Main checkout on `WIP`, equal to `origin/WIP` = `6d2ddbd10e91aedae5c5924b2045c046da73b583` after `git fetch origin`; `git status --short` listed only the untracked `archive/docs/` files. `git diff --name-only <approval> origin/WIP`: `DURUM.md`, `docs/handoff/2026-10-29-guclu-pc-kampanya-istem.md`. `git log --merges <approval>..origin/WIP`: empty.
- `$CK` = `C:\wt\d10-campaign-ck` (`git worktree add C:\wt\d10-campaign-ck <approval> --detach`).
- `$PY` = `C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`.
- Checks C1-C3 and C5-C7 were run as `C:\wt\d10-campaign\checks.ps1` (`pwsh`, `PYTHONPATH=$CK`, working directory `$CK`); full output `C:\wt\d10-campaign\checks.txt`. Commands as in section 7 of `docs/run_plans/bildiri2026-2026-10-28.md` (read with `git -C $CK show <approval>:docs/run_plans/bildiri2026-2026-10-28.md`).

## Pre-start checks C1-C7

**C1.** `git -C $CK rev-parse HEAD`: `2c7c5996ca1e924ef31c71f0c84164d3148deaf9`. `git -C $CK status --short`: empty (0 lines).

**C2.** `git -C $CK diff -U0 <base> <approval> -- <the four JSON files>`: four hunks, each `@@ -5 +5 @@`, `-  "status": "draft",` / `+  "status": "active",`, in `bildiri2026/analysis_plan.json`, `bildiri2026/study.json`, `yaem2026/analysis_plan.json`, `yaem2026/study.json`. `git -C $CK diff --name-status <base> <approval>`, seven entries:

```
M	academic_benchmark/studies/bildiri2026/analysis_plan.json
M	academic_benchmark/studies/bildiri2026/study.json
M	academic_benchmark/studies/yaem2026/analysis_plan.json
M	academic_benchmark/studies/yaem2026/study.json
M	docs/DECISION_LOG.md
A	docs/run_plans/bildiri2026-2026-10-28.md
A	docs/run_plans/yaem2026-2026-10-28.md
```

**C3.** `git -C $CK check-attr text eol`: `text: set` and `eol: lf` for each of the four JSON files. `Get-FileHash -Algorithm SHA256`:

```
1957AA1D49D3F342D80205D716FECCDAC3198C8E3189F60F94073C73936C309F  academic_benchmark/studies/bildiri2026/study.json
ED24C76F209EE42D2D09CD68CF4D55034CF01BAD5DE5D07E177FA229CDD2A2B8  academic_benchmark/studies/bildiri2026/analysis_plan.json
3D8F4246D56FA32FCF9A686FD2805D64A721CCB090B28AA0A05D63CD7ECD10B1  academic_benchmark/studies/yaem2026/study.json
697AEF871272C539B7223FEFB26A045D7E2E461586A621818856A48A113BE7B1  academic_benchmark/studies/yaem2026/analysis_plan.json
```

Equal (ignoring case) to the four hashes of the plans' section 3.

**C4.** `powercfg /getactivescheme` typed directly in PowerShell: `Power Scheme GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (Yüksek performans)`. `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE`: `Current AC Power Setting Index: 0x00000000`, `Current DC Power Setting Index: 0x00000000`. Load sampler `C:\wt\d04b2-native\load_sampler.ps1` (the D-04b2 fourth-run sampler: Windows `LoadPercentage` and per-process CPU every 15 s, `;`-separated, invariant decimals) started with `Start-Process powershell.exe ... -Out C:\UniRideCampaign\load_samples.csv -WindowStyle Minimized` at 2026-10-29T12:45:04, PID 4555696; stop file `C:\wt\d04b2-native\stop-sampler`. First samples: `2026-10-29T12:45:35;82;claude:1.61;RSLHelper:1.12;Raid:0.48`, `2026-10-29T12:45:55;83;claude:1.66;RSLHelper:0.98;Raid:0.48`.

**C5.** `pytest academic_benchmark/tests/test_analysis_environment.py -q -p no:cacheprovider`: `14 passed in 14.69s`, exit 0. `pip check`: `No broken requirements found.`, exit 0. `pip list --format=freeze`: `llvmlite==0.48.0`, `numba==0.66.0`, `numpy==2.4.6`.

**C6.** `C:\wt\d10-base\which_package.py` with `PYTHONPATH=$CK`: `C:\wt\d10-campaign-ck\academic_benchmark\__init__.py`, `C:\wt\d10-campaign-ck\uniride_core\__init__.py`; exit 0.

**C7.** `git -C $CK merge-base --is-ancestor <commit> 1a322a8f022970d6b7caaef37b127ce594c4d7b7` for the 32 commits of section 9: exit 0 for all 32 (`3d50a7e0`, `e24a5cd1`, `e9f11e72`, `a75cdde1`, `7c41237b`, `d0c73a8b`, `693d8fd2`, `dfaadc2d`, `9bd31aea`, `3146165e`, `80105327`, `1f21fc29`, `2174b160`, `530930f7`, `c09ef75c`, `4e116030`, `0dd7e753`, `86f19817`, `e8851f34`, `04612880`, `33f1fc2b`, `8513c2b6`, `cb449ed4`, `2323fb7a`, `1a9bd225`, `6efe8bb5`, `ecea6ee6`, `12bb24c9`, `565fcad3`, `bcef9feb`, `8ef7a23e`, `44c47434`).

`git -C $CK status --short` after the checks: empty (0 lines).

## Heavy programs open at the checks

No browser (`opera`, `chrome`, `msedge`, `firefox`), no `cbc`, no Claude Science `ie492` worker. Running: `Raid` (PID 3959892, started 2026-10-28 17:02:15) and `RSLHelper` (PID 3955884, started 2026-10-28 17:00:12); in the first samples `RSLHelper` 0.98-1.12 cores and `Raid` 0.48 cores.

## Output folders

`C:\UniRideCampaign\bildiri2026` and `C:\UniRideCampaign\yaem2026`: absent before the launch (`C:\UniRideCampaign` created for the sampler output only).

## Launch

- Before the launch the owner closed `Raid` and `RSLHelper`; at 2026-10-29T14:29:29 no `RSLHelper`, `Raid`, browser or `cbc` process was running, and `Test-Path` gave `False` for both output folders.
- Script `C:\wt\d10-campaign\run_campaign.ps1`: `PYTHONPATH=$CK`, `PYTHON_BASIC_REPL=1`, working directory `$CK`; runs `& $PY -m academic_benchmark.studies.run --study academic_benchmark/studies/<study>/study.json --mode paper --out C:\UniRideCampaign\<study>` for `bildiri2026`, then `yaem2026` (the second regardless of the first exit code); stdout and stderr to `C:\UniRideCampaign\<study>.out.txt` / `.err.txt`; start, `exit <study> <code>` and end lines to `C:\UniRideCampaign\campaign_log.txt`.
- Launched with `Start-Process pwsh -ArgumentList '-NoProfile','-File','C:\wt\d10-campaign\run_campaign.ps1' -WindowStyle Minimized -PassThru` at 2026-10-29T14:29:34; script PID 4632476. Bildiri run processes at 14:29:45: `python.exe` 4495852 (parent 4632476) and 4632564 (parent 4495852).
- `campaign_log.txt` at 14:34:08: `campaign script PID 4632476 start 2026-10-29T14:29:35`, `start bildiri2026 2026-10-29T14:29:35`. `bildiri2026.out.txt` and `bildiri2026.err.txt` empty; `C:\UniRideCampaign\bildiri2026\checkpoint\` holds `campaign.json` and `rows\` (156 files under `bildiri2026` at 14:34:08). Load samples 14:33:14-14:34:08: `python` 1.13-1.14 cores.
