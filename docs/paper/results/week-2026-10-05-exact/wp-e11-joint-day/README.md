# WP-E11 J11: clean serial campaign of the joint day model (week of 2026-10-05)

Design: [`JOINT_DAY_MODEL_DESIGN.md`](../../../../designs/JOINT_DAY_MODEL_DESIGN.md) (section 4.3 labels, 5.3 blocking checks, 6 files and reproduction); plan item J11 in `docs/superpowers/plans/2026-10-20-wp-e11-joint-day-model.md`; decisions DECISION_LOG E13 and E14 (the notes on J9b, J9c and the J10 work limit). Protocol `exact_day_joint_v1`, its own pooling group: never pooled with `exact_reference_v1` wave rows, `union_day_v1` (WP-E4b) rows or heuristic rows. This README describes the files; it is not paper text (the paper text goes through the writing line later).

All tables below are printed by `scripts/report_exact_day_joint.py --tables` from the files of this folder and the inputs it names. Numbers in the prose come from the same files, except the task-1 diagnosis, which names its own source.

## What was run

- Runner `scripts/run_exact_day_joint.py` at commit `f77c2484` (manifest `git_commit` `f77c2484330781cd1ed9e7e339670527d8e25d14`), clean tree (`dirty_working_tree` false, `development_run` false), one serial invocation (`run_history.invocations`: one entry, `jobs` 1, `serial` true; `cache` none), 140 of 140 cells planned and solved, `blocking_errors` empty, invocation wall time 8794.7 s (`total_wall_seconds`).
- Arguments as the manifest records them: `options` = all three fleets (`single_4sw5so`, `large+sedan`, `large+doblo_cap3`) with empty date, R and L lists (the campaign's full grid); 600 s per solver call (`time_limit_seconds` 600 for HiGHS and Gurobi); Gurobi work limit 200 (`work_limit` 200.0, owner decision after J10); cross-check on; `aggregate` true; `run_label` empty; `sensitivity_run` false. The command line itself is the lead's report: `python scripts/run_exact_day_joint.py --work-limit 200`, from the results worktree with `.venv-jit` and `PYTHONPATH` set to the worktree.
- Solvers: HiGHS 1.15.1 through `highspy` (primary; options `output_flag=false threads=1 random_seed=0 mip_rel_gap=0 mip_abs_gap=0.99 time_limit=600`) and Gurobi 13.0.3 through AMPL (cross-check; options `mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 lim:time=600 lim:work=200 outlev=1`). Python 3.14.6; `python_provenance` gives paths relative to the checkout. Offline: the runner reads only the committed source campaigns named in `source_manifests`.
- The six runner files of this folder (`day_joint_manifest.json`, `day_joint.csv`, `day_joint_stages.csv`, `day_joint_plans.json`, `day_joint_week.csv`, `lb0.csv`) are the raw result of commit `2ea2c5a2` and are not edited. `comparison.csv`, `reproduction_check.csv` and this README were added afterwards with `scripts/report_exact_day_joint.py` (read only; no solver).

#### Runtimes and Gurobi work (day_joint_stages.csv, day_joint.csv)

| fleet | cells | stage rows | longest HiGHS call s | longest Gurobi call s | largest Gurobi work | timing_dependent stage rows | longest cell s | sum of cell s |
|---|---|---|---|---|---|---|---|---|
| large+doblo_cap3 | 60 | 360 | 107.88 | 2.48 | 3.68 | 0 | 400.58 | 3755.8 |
| large+sedan | 60 | 226 | 83.95 | 3.12 | 3.62 | 0 | 519.44 | 4240.9 |
| single_4sw5so | 20 | 80 | 61.76 | 2.70 | 2.42 | 0 | 237.25 | 787.3 |

Stage statuses:

| solver | status | stop_reason | rows |
|---|---|---|---|
| gurobi | infeasible_proven | infeasible | 11 |
| gurobi | optimal | optimal | 321 |
| gurobi | rejected | solver_failure | 1 |
| highs | infeasible_proven | infeasible | 11 |
| highs | optimal | optimal | 322 |

No stage row is `timing_dependent`. No call came near the 600 s limit or the work limit of 200.

## Cells and labels

There are 140 cells: `single_4sw5so` 20 (5 dates x R in {50, 60, 70, 90}), `large+sedan` 60 (L in {1, 2, 3}) and `large+doblo_cap3` 60 (L in {0, 1, 2}). `K_or_S` is K (vehicles) for the single type and S (peak of the minimised type: sedans, or Doblòs with type id `minivan`) for typed cells. A cell counts as proven only with a proof label and `proof_claim_allowed` True (DECISION_LOG E14, J9c note). `day_status = optimal` alone is not a two-solver proof.

#### Cells and labels

| fleet | day_status | proof_claim_allowed | cells |
|---|---|---|---|
| large+doblo_cap3 | optimal | False | 1 |
| large+doblo_cap3 | optimal | True | 59 |
| large+sedan | infeasible_certified | True | 15 |
| large+sedan | infeasible_solver_proven | True | 11 |
| large+sedan | optimal | True | 34 |
| single_4sw5so | optimal | True | 20 |

#### Proof claim reasons

| fleet | proof_claim_reason | cells |
|---|---|---|
| large+doblo_cap3 | crosscheck_agree | 59 |
| large+doblo_cap3 | crosscheck_inconclusive | 1 |
| large+sedan | arithmetic_certificate | 8 |
| large+sedan | crosscheck_agree | 45 |
| large+sedan | wave_values_crosscheck_agree | 7 |
| single_4sw5so | crosscheck_agree | 20 |

`arithmetic_certificate` is the tier-1 certificate `certificate_capacity_floor` (design 3.2). `wave_values_crosscheck_agree` is a tier-2 certificate whose wave values both solvers agree on. `crosscheck_agree` means HiGHS and Gurobi both proved the day MIP. All 26 infeasible large+sedan cells have L = 1 (20) or L = 2 (6); see the typed table below.

## The one unclaimed cell and its diagnosis

#### Unclaimed cells

| fleet | date | R | L | day_status | K_or_S | total_minutes | car_minutes | proof_claim_reason | crosscheck_status |
|---|---|---|---|---|---|---|---|---|---|
| large+doblo_cap3 | 2026-10-08 | 50 | 2 | optimal | 2 | 1499 | 540 | crosscheck_inconclusive | inconclusive |

Stage rows of these cells:

| solver | stage | status | stop_reason | objective | bound | solve_result |
|---|---|---|---|---|---|---|
| highs | 1 | optimal | optimal | 2 | 2.0 | kOptimal |
| highs | 2 | optimal | optimal | 1499 | 1498.99998601 | kOptimal |
| highs | 3 | optimal | optimal | 540 | 539.9999956 | kOptimal |
| gurobi | 1 | optimal | optimal | 2 | 2.0 | solved |
| gurobi | 2 | optimal | optimal | 1499 | 1499.0 | solved |
| gurobi | 3 | rejected | solver_failure |  | 539.9999877417731 | solved |

HiGHS proves all three stages (S = 2, total minutes 1499, car minutes 540), and the plan passes the checker and the TypeScript CLI. Gurobi agrees on stages 1 and 2, but its stage 3 is `rejected` / `solver_failure`. The day cross-check is therefore `inconclusive` and the claim is withheld. The label stays `optimal` with `proof_claim_allowed` False, and every comparison below treats the cell as unproven.

Diagnosis (task 1, 2026-10-21; one re-solve of this stage outside the repository, not stored here): the cell was rebuilt with the runner's own code at the results commit. Its stage-3 MPS sha256 `22713c92...addf` is identical to the recorded one. Only Gurobi stage 3 was solved again, with the J11 options. The result is the same as in the campaign: AMPL `solve_result` `solved`, `solve_result_num` 0, first message line `Gurobi 13.0.3: optimal solution; objective 539.9999877`, bound 539.9999877417731, work 0.02.

- Gurobi found the optimum. Its returned objective is 540 - 1.23e-05.
- `ampl_backend.classify_outcome` (`uniride_core/exact/ampl_backend.py:223-227`) rejects an incumbent whose raw objective is more than `_INT_TOL` = 1e-05 (`ampl_backend.py:58`) from an integer, and it does this before the values are rounded.
- The variable values are integral within 1.28e-06: 20 of 490 variables differ from an integer by more than 1e-09, all of them within Gurobi's integrality tolerance. Rounded, they pass `check_integer_solution` with objective 540, the HiGHS value. The objective multiplies each small deviation by a tour length in minutes (for example 66, 72 and 81 among the non-integral variables), so the deviations add up.

This is a gap in the runner's tolerance rule: a per-variable tolerance is applied to the objective. It is neither a numerical failure of Gurobi nor a genuinely open cell. The code fix and the re-run decision belong to the lead; nothing was changed here.

## Blocking checks (design 5.3)

`scripts/report_exact_day_joint.py` runs these checks per cell. The results are in the `check_*` and `blocking_defects` columns of `comparison.csv`.

- `check_bounds`: K or S is not below LB0, LB0w, LB_S, the bound used or any solver's stage-1 bound. Rejected stages and bounds listed in `unverified_bounds` are excluded. The large peak is not below LB_L. Applies to every cell with a value.
- `check_checker`: the runner's independent checker passed the plan (`checker_ok` True). Applies to every cell with a value. The runner itself runs the checker (design 5.1), and on typed plans also the TypeScript CLI.
- `check_union`: where both are proven, joint cars <= WP-E4b union-menu cars, and a proven joint infeasibility never meets a proven union-menu plan. Applies to proven typed cells whose WP-E4b union run is `optimal` (labels `proven_over_union_menu` or `ga_menu_infeasible_for_L`).
- `check_peaks`: a proven joint K is at most the peak of the archived GA routes (`week-2026-10-05-4sw5so/<date>_R<R>_repeat1.response.json`) and the peak of the WP-E3 exact routes (`wp-e3-goal1-single/exact_routes.json`) of the same day. The independent checker (`academic_benchmark/validation/day_plan.py`) recomputes both peaks on the archived matrix slice. Both route sets pass it, with 0 violations on all 20 days.
- The disagreement rule of design 6.3 (a checked prototype plan beating a proven production value) is applied in the reproduction step below.

#### Blocking checks (design 5.3)

| check | pass | fail | not_applicable |
|---|---|---|---|
| check_bounds | 114 | 0 | 26 |
| check_checker | 114 | 0 | 26 |
| check_union | 91 | 0 | 49 |
| check_peaks | 20 | 0 | 120 |

Blocking defects: 0

Cells marked `not_applicable`:

- `check_bounds` and `check_checker`: the 26 infeasible cells, which have no value.
- `check_union`: the 20 single-type cells, the 28 typed cells whose union run is `infeasible_for_L`, and the unclaimed cell.
- `check_peaks`: every typed cell, because this check applies to the single type only.

#### Single type: joint K against archived route sets and the prototype

| date | R | joint K | LB0 | LB0w | GA routes peak | WP-E3 routes peak | joint minutes | GA minutes | WP-E3 minutes | prototype K | prototype minutes | category |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-05 | 50 | 6 | 6 | 6 | 6 | 6 | 1597 | 1600 | 1597 | 6 | 1597 | equal |
| 2026-10-06 | 50 | 4 | 4 | 4 | 5 | 5 | 1346 | 1334 | 1334 | 4 | 1346 | equal |
| 2026-10-07 | 50 | 5 | 3 | 5 | 6 | 6 | 1323 | 1302 | 1293 | 5 | 1323 | equal |
| 2026-10-08 | 50 | 4 | 3 | 4 | 5 | 5 | 1499 | 1494 | 1494 | 4 | 1499 | equal |
| 2026-10-09 | 50 | 6 | 4 | 4 | 6 | 6 | 1085 | 1092 | 1085 | 6 | 1085 | equal |
| 2026-10-05 | 60 | 4 | 4 | 4 | 5 | 4 | 1449 | 1475 | 1449 | 4 | 1449 | equal |
| 2026-10-06 | 60 | 4 | 3 | 3 | 4 | 4 | 1298 | 1307 | 1298 | 4 | 1298 | equal |
| 2026-10-07 | 60 | 5 | 3 | 5 | 6 | 6 | 1278 | 1252 | 1248 | 5 | 1278 | equal |
| 2026-10-08 | 60 | 4 | 3 | 3 | 4 | 4 | 1370 | 1387 | 1370 | 4 | 1370 | equal |
| 2026-10-09 | 60 | 5 | 4 | 4 | 5 | 5 | 1004 | 1029 | 1004 | 5 | 1004 | equal |
| 2026-10-05 | 70 | 4 | 4 | 4 | 4 | 4 | 1348 | 1355 | 1348 | 4 | 1348 | equal |
| 2026-10-06 | 70 | 4 | 3 | 3 | 4 | 4 | 1237 | 1237 | 1237 | 4 | 1237 | equal |
| 2026-10-07 | 70 | 5 | 2 | 5 | 6 | 6 | 1228 | 1209 | 1198 | 5 | 1228 | equal |
| 2026-10-08 | 70 | 3 | 2 | 2 | 4 | 4 | 1317 | 1294 | 1289 | 3 | 1317 | equal |
| 2026-10-09 | 70 | 4 | 3 | 3 | 5 | 5 | 984 | 958 | 956 | 4 | 984 | equal |
| 2026-10-05 | 90 | 3 | 3 | 3 | 4 | 3 | 1303 | 1338 | 1303 | 3 |  | equal |
| 2026-10-06 | 90 | 3 | 2 | 2 | 3 | 3 | 1164 | 1164 | 1164 | 3 | 1164 | equal |
| 2026-10-07 | 90 | 4 | 2 | 3 | 4 | 4 | 1134 | 1141 | 1134 | 4 | 1134 | equal |
| 2026-10-08 | 90 | 3 | 2 | 2 | 4 | 4 | 1313 | 1286 | 1284 | 3 | 1313 | equal |
| 2026-10-09 | 90 | 3 | 3 | 3 | 4 | 4 | 930 | 933 | 928 | 3 | 930 | equal |

#### Typed fleets: joint cars against WP-E4b union-menu cars

| fleet | L | cells | joint < union | joint = union | joint > union | joint value, union menu infeasible | both infeasible | joint infeasible, union value |
|---|---|---|---|---|---|---|---|---|
| large+doblo_cap3 | 0 | 20 | 11 | 9 | 0 | 0 | 0 | 0 |
| large+doblo_cap3 | 1 | 20 | 9 | 11 | 0 | 0 | 0 | 0 |
| large+doblo_cap3 | 2 | 20 | 8 | 12 | 0 | 0 | 0 | 0 |
| large+sedan | 1 | 20 | 0 | 0 | 0 | 0 | 20 | 0 |
| large+sedan | 2 | 20 | 4 | 8 | 0 | 2 | 6 | 0 |
| large+sedan | 3 | 20 | 8 | 12 | 0 | 0 | 0 | 0 |

The two cells under "joint value, union menu infeasible" are large+sedan 2026-10-06 R = 70 and R = 90, L = 2 (WP-E4b `both_infeasible_for_L`). In both, the joint model finds a plan with S = 2. No cell has a joint value above the union-menu value, and no joint infeasibility meets a union-menu plan. The unclaimed Doblò cell (S = 2 against union 3) is counted under "joint < union" but is not checked.

#### Weekly values (day_joint_week.csv)

| fleet | R | L | dates | weekly_fleet_max | vehicle_days_sum | cells_not_proven | cells_without_value |
|---|---|---|---|---|---|---|---|
| single_4sw5so | 50 |  | 5 | 6 | 25 | 0 | 0 |
| single_4sw5so | 60 |  | 5 | 5 | 22 | 0 | 0 |
| single_4sw5so | 70 |  | 5 | 5 | 20 | 0 | 0 |
| single_4sw5so | 90 |  | 5 | 4 | 16 | 0 | 0 |
| large+sedan | 50 | 1 | 5 |  |  | 0 | 5 |
| large+sedan | 50 | 2 | 5 | 4 | 6 | 0 | 3 |
| large+sedan | 50 | 3 | 5 | 3 | 11 | 0 | 0 |
| large+sedan | 60 | 1 | 5 |  |  | 0 | 5 |
| large+sedan | 60 | 2 | 5 | 3 | 10 | 0 | 1 |
| large+sedan | 60 | 3 | 5 | 2 | 7 | 0 | 0 |
| large+sedan | 70 | 1 | 5 |  |  | 0 | 5 |
| large+sedan | 70 | 2 | 5 | 2 | 7 | 0 | 1 |
| large+sedan | 70 | 3 | 5 | 2 | 5 | 0 | 0 |
| large+sedan | 90 | 1 | 5 |  |  | 0 | 5 |
| large+sedan | 90 | 2 | 5 | 2 | 7 | 0 | 1 |
| large+sedan | 90 | 3 | 5 | 1 | 1 | 0 | 0 |
| large+doblo_cap3 | 50 | 0 | 5 | 7 | 27 | 0 | 0 |
| large+doblo_cap3 | 50 | 1 | 5 | 5 | 20 | 0 | 0 |
| large+doblo_cap3 | 50 | 2 | 5 | 4 | 15 | 1 | 0 |
| large+doblo_cap3 | 60 | 0 | 5 | 7 | 26 | 0 | 0 |
| large+doblo_cap3 | 60 | 1 | 5 | 5 | 19 | 0 | 0 |
| large+doblo_cap3 | 60 | 2 | 5 | 3 | 13 | 0 | 0 |
| large+doblo_cap3 | 70 | 0 | 5 | 7 | 26 | 0 | 0 |
| large+doblo_cap3 | 70 | 1 | 5 | 4 | 16 | 0 | 0 |
| large+doblo_cap3 | 70 | 2 | 5 | 3 | 10 | 0 | 0 |
| large+doblo_cap3 | 90 | 0 | 5 | 7 | 26 | 0 | 0 |
| large+doblo_cap3 | 90 | 1 | 5 | 4 | 15 | 0 | 0 |
| large+doblo_cap3 | 90 | 2 | 5 | 2 | 8 | 0 | 0 |

`cells_not_proven` counts cells whose `proof_claim_allowed` is not True (the runner's definition). For large+Doblò cap3 R = 50, L = 2, this is the unclaimed cell above, so that weekly value is not proven.

## Reproduction against the prototype (design 6.3)

The prototype values come from the Claude Science comparison committed in `docs/science_review/2026-10-19_cs_cc_karsilastirma/` (`cs_cc_gun_homojen_4sw5so_20.csv`, `cs_cc_gun_tipli_large_sedan_60.csv`). They are read as data, not as verified truth, and were never an input of the run. Mapping:

- single type: `cs_kanit` `joint MIP optimal` gives the value (K = `cs_ortak_K`, total minutes = `cs_ortak_dakika`). The single row `seq plan = LB0 (MIP status -9)` (2026-10-05 R = 90) gives K only: the prototype's sequential plan equals its LB0, there is no joint plan, and minutes are not compared.
- large+sedan: `cs_durum` `infeasible` means prototype infeasible. `ok...` gives a value (S = `cs_sedan`, and total minutes = `cs_dakika` when present). `acik...` (2026-10-05 R = 90, L = 2) means the prototype left the cell open.
- large+Doblò cap3: there is no external reproduction target (E14 Q1), so these cells have no rows in `reproduction_check.csv`.

The prototype plans are not in the repository, so the checker of design 5.1 was not run on them (`prototype_plan_checked = not_run`, note `prototype_plan_not_verified`). An unchecked prototype plan can never raise the disagreement defect. No category below depended on that, because no prototype value is better than a production value.

`category` compares the objective tuple (K or S, then total minutes) on the components the prototype reports; `fleet_category` compares K or S only. The single type uses a different tie-break order in each implementation (prototype: K, routes, minutes; production: K, minutes, owner decision Q2), so production minutes were expected to be no higher than the prototype's. They are equal in all 19 compared cells.

#### Reproduction by category (objective tuple)

| fleet | category | cells |
|---|---|---|
| large+sedan | equal | 59 |
| large+sedan | prototype_open | 1 |
| single_4sw5so | equal | 20 |

#### Reproduction by category (fleet value only)

| fleet | fleet_category | cells |
|---|---|---|
| large+sedan | equal | 59 |
| large+sedan | prototype_open | 1 |
| single_4sw5so | equal | 20 |

#### Design 6.3 targets, recomputed from both sides' files

| target | prototype | production |
|---|---|---|
| single type weekly fleet, R = 50/60/70/90 | 6/5/5/4 | 6/5/5/4 |
| single type vehicle-days over 20 cells | 83 | 83 |
| large+sedan cells with fewer sedans than the union menu (of 60) | 12 | 12 |
| large+sedan 2026-10-06 R = 70, L = 2 | ok S=2.0 | optimal S=2 (claim True) |
| large+sedan 2026-10-06 R = 90, L = 2 | ok S=2.0 | optimal S=2 (claim True) |
| large+sedan 2026-10-05 R = 90, L = 2 | acik: S in {1,2} S=- | optimal S=2 (claim True) |
| large+sedan weekly sedans at L = 3, R = 50/60/70/90 | 3/2/2/1 | 3/2/2/1 |

The prototype left 2026-10-05 R = 90, L = 2 open (S in {1, 2}). Here it is proven `optimal` with S = 2 (claim True; category `prototype_open`). The design 6.3 minute targets ("+194 min over 19 cells", "+257 min in the 12 cells") are differences against wave optima and union menus, not per-cell values in the prototype CSVs, and are not recomputed here. The per-cell minutes are compared in `reproduction_check.csv`.

## What this does not show

- No paper claim. The rows are descriptive results of one snapshot week, one GA seed (42) on the GA side, one machine and one software version. They support no superiority, causality or generality statement (AGENTS.md). Paper text goes through the writing line.
- The joint rows are a separate protocol (`exact_day_joint_v1`). WP-E4b union-menu cars and the archived route peaks appear next to them as separate columns of `comparison.csv`; nothing is pooled, and no `min(...)` is taken across protocols.
- The unclaimed cell (large+Doblò cap3, 2026-10-08, R = 50, L = 2) is not a two-solver proof, whatever the diagnosis suggests, until the lead decides on a fix and a re-run.
- Agreement with the prototype is agreement with unverified data, because the prototype plans were not checked here.
- No sensitivity run, no longer limit and no other week. The J10 calibration rows are never pooled with these.

## Files

| File | Content |
|---|---|
| `day_joint_manifest.json` | runner manifest: protocol, commit, dirty flag, `python_provenance`, source manifests, solver versions, options and limits, `mps_sha256` per cell and stage, enumeration caps and columns per day, `run_history`, output sha256 (raw, not edited) |
| `day_joint.csv` | one row per cell (140): label, K or S, large peak, minutes, bounds, bound source and proof, proof claim and reason, cross-check and wave-values verdicts, checker, TS confirmation, wall seconds (raw) |
| `day_joint_stages.csv` | one row per cell, solver and stage: status, stop reason, objective, bound, flags, wall seconds, Gurobi work units, solve result, `mps_sha256` (raw) |
| `day_joint_plans.json` | per cell and wave the chosen routes (raw) |
| `day_joint_week.csv` | per fleet, R and L: weekly fleet (maximum over dates), vehicle-days, cells not proven (raw) |
| `lb0.csv` | LB0, LB0w, LB_L, LB_S, certificates and the wave values with both solvers' verdicts (raw) |
| `comparison.csv` | per cell (140): joint values and bounds; WP-E4b GA-menu and union-menu status, cars and label (typed); `joint_minus_union_cars`; peaks, minutes and checker violations of the archived GA and WP-E3 route sets (single type); `check_bounds`, `check_checker`, `check_union`, `check_peaks` (`pass`, `fail`, `not_applicable`) and `blocking_defects` (empty = none) |
| `reproduction_check.csv` | per cell with a prototype target (80: single type and large+sedan): prototype status, value and minutes, `prototype_plan_checked`, production status, claim, value and minutes, `components_compared`, `category`, `fleet_category`, `note` |
| `README.md` | this file |

To reproduce the two derived files and the tables (read only, no solver): `PYTHONPATH=<repo root> python scripts/report_exact_day_joint.py --tables` (exit 0 means no blocking defect). Tests: `academic_benchmark/tests/test_report_exact_day_joint.py`.
