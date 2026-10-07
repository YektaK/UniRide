# Daily-plan sensitivity campaign, week of 2026-10-05 (corrected capacity, 4 Sw / 5 So)

Archived output of one daily-plan experiment campaign (anonymized). It **supersedes** `../week-2026-10-05/`, which was computed with a wrong large-vehicle capacity (4 Sw / 10 So) caused by a database data error. The physical minibus has a fixed layout of 4 Sw + 5 So; the database record was corrected on 2026-10-07 and this campaign was re-run with the same command.

Files:

- `summary.csv`: one row per weekday and ride limit (20 rows).
- `weekly.csv`: one row per ride limit (weekly fleet need, per-day vehicles, total vehicle-minutes).
- `run_manifest.json`: parameters, effective configuration, per-run file names and matrix provenance.
- `*.response.json`: optimizer response for each of the 20 runs.
- `*.matrix.json`: directed travel-time matrix used for each run.
- `schedule_verification.md`, `figures/`, `fleet_mix*.csv`, `fleet_mix_analysis.md`: derived by the scripts below.

Production:

- Command (same as the superseded campaign): `npm run experiments:plan -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 --fleet virtual`
- Run date: 2026-10-08 (manifest timestamp 2026-10-07T21:04:14Z).
- Git commit: `6be127d048ae6c871baffd0c1992e0eb617231b2` (the manifest sets a dirty flag; the working tree was not clean at run time).
- Seed: 42. Algorithm `ga_split`, native termination, one repeat per cell.
- Vehicle template: 4 Sw / 5 So, cooldown 10 min (read from every response; checked by the verification script).
- Matrix sha256: `bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5` (29 locations; the same value is recorded for all 20 runs and equals the superseded campaign's).

Caveats:

- Confirmations were assumed (`ADMISSION_ASSUMED`), not real admissions, and per-leg decisions were unavailable (`LEG_DECISIONS_UNAVAILABLE`).
- Vehicle counts are proven only for the solver's fixed routes, not as global optima.
- This is a single snapshot and supports descriptive reporting only.

Analysis: see `../../DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md`, section 6.

Regenerate (standard library only), in this order, each with this directory as argument:

```
python scripts/plan_schedule_report.py docs/paper/results/week-2026-10-05-4sw5so
python scripts/plan_resource_profile.py docs/paper/results/week-2026-10-05-4sw5so
python scripts/plan_fleet_mix.py docs/paper/results/week-2026-10-05-4sw5so
```

Fleet-mix what-if: car type 0 Sw / 4 So, large type 4 Sw / 5 So. Browse figures via [figures/index.html](figures/index.html).
