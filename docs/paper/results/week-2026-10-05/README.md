# Daily-plan sensitivity campaign, week of 2026-10-05

Archived output of one daily-plan experiment campaign (anonymized).

Files:

- `summary.csv`: one row per weekday and ride limit (20 rows).
- `weekly.csv`: one row per ride limit (weekly fleet need, per-day vehicles, total vehicle-minutes).
- `run_manifest.json`: parameters, effective configuration, per-run file names and matrix provenance.
- `*.response.json`: optimizer response for each of the 20 runs.
- `*.matrix.json`: directed travel-time matrix used for each run.

Production:

- Command: `npm run experiments:plan -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 --fleet virtual`
- Run date: 2026-10-07.
- Git commit: `51c5c51bfe007672a6618097f2ded64eea91b0f8` (the manifest records a dirty working tree).
- Seed: 42. Algorithm `ga_split`, native termination, one repeat per cell.
- Matrix sha256: `bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5` (29 locations; the same value is recorded for all 20 runs).

Caveats:

- An independent second run produced identical summaries on all 20 rows.
- Results were produced under assumed confirmations (`ADMISSION_ASSUMED`), not real admissions, and per-leg decisions were unavailable (`LEG_DECISIONS_UNAVAILABLE`).
- Vehicle counts are proven only for the solver's fixed routes, not as global optima.
- This is a single snapshot and supports descriptive reporting only.

Analysis: see `../../DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md`, section 6.
