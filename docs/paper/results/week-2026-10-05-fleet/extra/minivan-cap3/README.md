# Extra campaign (corrected): wheelchair-accessible minivan with total capacity 3, week of 2026-10-05

Corrected replacement of `../minivan/` (DECISION_LOG H03). Same week, same matrix, same solver settings; only the minivan model differs. Descriptive only; no superiority, causality or cost claim. Used by `scripts/plan_fleet_pareto.py` (see `../../pareto_analysis.md`).

## Minivan model

The minivan type is `minivan:1sw3so:cap3:cd10`: at most 1 wheelchair place (Sw), at most 3 seated places (So), **and at most 3 passengers in total (`cap3`)**, cooldown 10 min. This models a Fiat Doblo: 3 seats in total, at most 1 of the passengers is a wheelchair user (the wheelchair is stowed in the luggage space and the student sits in a seat). The archived `../minivan/` campaign used `minivan:1sw3so:cd10`, which allowed 1 Sw + 3 So = 4 people, overstating capacity; it is superseded and kept only for traceability.

## Command (equivalent invocation)

```text
npm run experiments:fleet -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 \
  --fleet-types large:4sw5so:cd10,minivan:1sw3so:cap3:cd10 --fixed-type large --minimize-type minivan \
  --scenarios 0,1,2 --out <output folder>
```

Scenarios `L0`, `L1`, `L2`: exactly 0, 1 or 2 large minibuses (4 Sw + 5 So) and the minimum number of minivans per weekday. Grid: 5 weekdays x R in {50, 60, 70, 90} x 3 scenarios = 60 scenario runs. In the CSVs the generic columns `cars`, `car_vehicle_minutes`, `car_routes` and `car_usage_windows.csv` refer to the minimised type, here minivans (manifest `minimize_type: minivan`; `totalCapacity: 3` is recorded in the manifest fleet types).

## Provenance

- Git commit in the manifest: `4200acb7a8ab7bac60f4d411128c82e9dc8054e9` (`dirty_working_tree: true`).
- Settings as in the parent campaign: GA seed 42, native termination, CP-SAT `random_seed` 20261008, tour limit 150, `admission_mode: assume_confirmed`, `db_vehicles_consulted: false`.
- Result statuses: 60 of 60 rows `ok`, assignment `proven` (minimum over the generated route menus, exact assignment; not a global minimum over all possible routes).

## Files

`run_manifest.json`, `scenario_daily.csv`, `scenario_weekly.csv`, `car_usage_windows.csv`, `<date>_R<R>_L<0|1|2>.response.json` (60 anonymised route files) and `<date>_R<R>.matrix.json` (20 arc files).

## Privacy check

No personal data and no local paths: labels are anonymised (`Sw`/`So` plus an index), vehicles are `Vehicle<n>`, locations are the campus code plus anonymised stop codes. A search for user names, drive paths, e-mail addresses and `@` found nothing.
