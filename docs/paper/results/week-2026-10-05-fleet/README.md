# Heterogeneous fleet scenarios, week of 2026-10-05

Campaign of the typed-fleet planner (`docs/designs/HETEROGENEOUS_FLEET_DESIGN.md`, WP5 to WP7). Descriptive results for one snapshot of the timetable; no superiority, causality or cost claim. Management summary (Turkish): [YONETIM_OZETI.md](YONETIM_OZETI.md). Paper subsection: "Heterogeneous fleet scenarios" in `../../DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md`.

## Command

```text
npm run experiments:fleet -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 \
  --fleet-types large:4sw5so:cd10,sedan:0sw4so:cd10 --fixed-type large --minimize-type sedan \
  --scenarios A,1,2,3 --out .temp/experiments/fleet-week-20261008-120446
```

The manifest records the parsed parameters, not the literal command line; the command above is the equivalent invocation. Defaults used: node budget 200000, selection time limit 30 s, no cap on sedans (`max_cars: null`). Grid: 5 weekdays (2026-10-05 to 2026-10-09) x R in {50, 60, 70, 90} x scenarios A, L1, L2, L3 = 80 scenario runs. The run finished on 2026-10-08 (manifest `state: completed`).

## Scenarios and fleet

| Label here | CSV `scenario` | Meaning |
|---|---|---|
| A | `A` | all-large: minimum number of large vehicles, no sedans |
| B | `L1` | exactly 1 large vehicle, minimum number of sedans |
| C | `L2` | exactly 2 large vehicles, minimum number of sedans |
| D | `L3` | exactly 3 large vehicles, minimum number of sedans |

| Type | Sw | So | Cooldown | Source |
|---|---|---|---|---|
| large | 4 | 5 | 10 min | CLI (`fleet_types_source: "cli"`) |
| sedan | 0 | 4 | 10 min | CLI |

`db_vehicles_consulted` is `false`: the `vehicles` table was never read; the types above are the only fleet. The sedan has no wheelchair place (Sw = 0). Whether a sedan can carry a wheelchair user is an open owner question; it is a parameter (`sedan:1sw3so`), not a finding. Ride limit R and tour limit 150 apply to both types.

## Seeds, solver and provenance

- Route menus: GA with effective seed 42 for the baseline (`ga_split`, scenario A) and for the typed menu (`ga_split_hf`, `hf_effective_seed` 42); native termination.
- Day selection: CP-SAT 9.15.6755, `random_seed` 20261008, 1 worker, 30 s per stage.
- Git commit: `8ab88ca35ae05418a0cdae4f4c7a6337ca189c0b` (manifest `git_commit`). The manifest also records `dirty_working_tree: true`, so the run is tied to that commit plus uncommitted changes in the working tree at the time.
- Matrix: all 20 (date, R) runs report the same matrix sha256 `bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5` (source `supabase`, 29 locations, loaded 2026-10-08). The per-run `*.matrix.json` files are the arcs used by each run.
- HTTP: 33 rate-limit waits (429) were retried; no optimizer HTTP failures. All 20 days have `day_status: ready`.

## Statuses

- Scenario A: all 20 rows `ok`, `large_vehicles_proven` true.
- Scenarios L1 to L3 (60 rows): `ok` with `cars_status = proven_over_menu` and `assignment_status = proven` on 31 rows (L2: 11, L3: 20); `infeasible_for_L` on 29 rows (L1: 20 of 20, L2: 9 of 20). No row is `witness`, `indeterminate` or unproven.
- `proven_over_menu`: the sedan count is the minimum over the generated route menus (heuristic GA routes), and the assignment of the chosen routes to physical vehicles is exact. It is not a global minimum over all possible routes.

## Confirmations are assumed

`admission_mode` is `assume_confirmed`: every student with a timetable class on the day is treated as confirmed. No real participation or cancellation data is used.

## How to read `infeasible_for_L`

A row with `status = infeasible_for_L` means that, within the generated menus, the fixed number L of large vehicles cannot serve that day under the ride limit R. It is a statement about that (L, day, R) cell only. It does not mean that zero sedans are needed: `cars`, `cars_status` and the minutes columns are empty on purpose, and the reason is in `reason_codes` (and in `selection.diagnostics` of the response JSON).

- `SW_DEMAND_EXCEEDS_LARGE_CAPACITY`: some single arrival or departure wave contains wheelchair (Sw) passengers whose routes must be driven by large vehicles (a sedan has no Sw place), and even the best menu option needs more than L large vehicles for that wave alone. `selection.diagnostics.lower_bound_L` is the smallest L for which this check passes.
- `CROSS_WAVE_CONFLICT`: every wave alone fits in L large vehicles, but no combination of menu options keeps the large-only routes of neighbouring waves (including the 10-minute cooldown) within L at the same time.

`weekly_cars` in `scenario_weekly.csv` is empty and `complete_week` false when any weekday is infeasible; `infeasible_days` counts those days. In figures and tables a weekly total exists only if all five days are feasible.

## Files

| File | Content |
|---|---|
| `run_manifest.json` | parameters, fleet types, solver settings, matrix provenance, menu sizes and statuses per (day, R, scenario) |
| `scenario_daily.csv` | one row per date x R x scenario (cars, vehicles, minutes, ride statistics, statuses, reason codes) |
| `scenario_weekly.csv` | one row per R x scenario (weekly maximum and per-day need) |
| `car_usage_windows.csv` | per sedan: first start, last end, busy minutes, routes |
| `<date>_R<R>_<A\|L1\|L2\|L3>.response.json` | anonymised routes with vehicle types and ids (80 files); `<date>_R<R>.matrix.json` (20 files) |
| `weekly_summary.md` | weekly table and daily demand, recomputed from the CSVs by the script |
| `fleet_verification.md` | independent recomputation checks (pass/fail per run) |
| `figures/` | SVG figures and `index.html` |

Regenerate the derived files with `python scripts/plan_fleet_scenarios.py` (standard library only; reads the files above, rewrites `figures/`, `weekly_summary.md`, `fleet_verification.md`).

## Figures

Marks: grey hatch = infeasible on at least one weekday; red hatch or red outline and `*` = sedan count not proven over the menu (none occurs in this campaign).

- `figures/fleet_scenarios_R50.svg`, `_R60`, `_R70`, `_R90`: weekly large + sedan stacked bars for A, B, C, D; per-day need under each bar.
- `figures/fleet_scenarios_all.svg`: the four panels together with a shared y-scale.
- `figures/fleet_daily_heatmap.svg`: one cell per scenario x weekday x R, "L+C" or "infeasible".
- `figures/fleet_resource_L3_R50.svg`, `_R60`, `_R70`, `_R90`: busy vehicles by type (large, sedan) including cooldown for scenario D, five weekdays each.
- `figures/fleet_sedan_gantt_L3_R60.svg`: sedan route windows, scenario D, R = 60, all weekdays.
- `figures/index.html`: all of the above plus the daily table.

## Verification

`fleet_verification.md` recomputes from the response routes: no overlap and cooldown per vehicle and type, Sw never on a sedan, per-route capacity by type, ride time <= R and tour <= 150, every leg served exactly once, plus consistency with the CSVs. Result: see that file (all 51 runs with routes pass; the 29 infeasible rows have no routes).

## Not archived

The Monday R = 60 smoke run (`fleet-smoke-20261008-120302`) stays in `.temp/experiments/` and is not part of this campaign.

## Extra campaigns and multi-objective (Pareto) analysis

- `extra/L4/` (4 large minibuses + sedans) and `extra/minivan-cap3/` (0, 1, 2 large minibuses + wheelchair-accessible minivans, **assumed** capacity: 3 passengers in total, at most 1 Sw) are archived with their own READMEs; same week, matrix and settings. `extra/minivan/` (capacity 1 Sw + 3 So = 4 people) is superseded and no longer used (DECISION_LOG H03).
- `pareto_analysis.md`: epsilon-constraint method, objectives (f1 owned minibuses, f2 peak borrowed vehicles, f3 borrowed vehicle-hours per week, f4 borrowed days, f5 service level), all options, non-dominated sets, utilisation, limits.
- `pareto_options.csv` (one row per option), `pareto_daily.csv` (per option and weekday, with vehicle windows), `pareto_borrowed_hourly.csv` (per option, weekday and clock hour).
- `figures/pareto_*.svg` and section (e) of `figures/index.html`. Regenerate with `python scripts/plan_fleet_pareto.py` (standard library only; run it after `plan_fleet_scenarios.py`, which rewrites `index.html`); self-test: `python scripts/test_plan_fleet_pareto.py`.
