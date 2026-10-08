# Extra campaign: large minibuses + wheelchair-accessible minivans, week of 2026-10-05

Additional scenarios of the heterogeneous-fleet campaign in the parent folder (same week, same matrix, same solver settings), with a third vehicle type: a wheelchair-accessible minivan (Fiat Doblo type). Descriptive only; no superiority, causality or cost claim. Used by `scripts/plan_fleet_pareto.py` (see `../../pareto_analysis.md`).

## Minivan capacity is an assumption

The minivan type is `minivan:1sw3so:cd10`: 1 wheelchair place (Sw) + 3 seated places (So), cooldown 10 min. This capacity is an **assumption and a parameter**, not a measured property of any vehicle. It can be tested as `minivan:1sw2so` (one seated place fewer) by re-running the command below with that type; that variant has **not** been run, and no result here applies to it.

## Command (equivalent invocation)

```text
npm run experiments:fleet -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 \
  --fleet-types large:4sw5so:cd10,minivan:1sw3so:cd10 --fixed-type large --minimize-type minivan \
  --scenarios 0,1,2 --out <output folder>
```

The manifest records the parsed parameters, not the literal command line. Scenarios `L0`, `L1`, `L2`: exactly 0, 1 or 2 large minibuses (4 Sw + 5 So) and the minimum number of minivans per weekday. Grid: 5 weekdays x R in {50, 60, 70, 90} x 3 scenarios = 60 scenario runs; manifest `state: completed`. In the CSVs the generic columns `cars`, `car_vehicle_minutes`, `car_routes` and `car_usage_windows.csv` refer to the minimised type, here minivans (manifest `minimize_type: minivan`).

## Provenance

- Git commit in the manifest: `afc72089389165e5b03657d246f37029e9669baa` (`dirty_working_tree: true`).
- Same settings as the parent campaign: GA seed 42, native termination, CP-SAT `random_seed` 20261008, tour limit 150, cooldown 10 min, `admission_mode: assume_confirmed`, `db_vehicles_consulted: false`.
- Matrix sha256 `bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5` in all runs (identical to the parent campaign).
- Result statuses: 60 of 60 rows `ok` (every L, including L0, is feasible on every weekday and R), minivan count `proven_over_menu`, assignment `proven` (minimum over the generated route menus, exact assignment; not a global minimum over all possible routes).

## Files

`run_manifest.json`, `scenario_daily.csv`, `scenario_weekly.csv`, `car_usage_windows.csv`, `<date>_R<R>_L<0|1|2>.response.json` (60 anonymised route files) and `<date>_R<R>.matrix.json` (20 arc files).

## Privacy check

The files contain no personal data and no local paths: occurrences are anonymised labels (`Sw`/`So` plus an index), vehicles are `Vehicle<n>`, and locations are the campus code plus anonymised stop codes (`Sw<n>`, `So<n>`; 29 locations in the matrix). A search for user names, drive paths, e-mail addresses and credentials found nothing.
