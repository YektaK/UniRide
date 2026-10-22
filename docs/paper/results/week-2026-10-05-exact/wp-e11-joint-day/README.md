# WP-E11 J11 rerun: clean serial campaign of the joint day model (week of 2026-10-05)

Design: [`JOINT_DAY_MODEL_DESIGN.md`](../../../../designs/JOINT_DAY_MODEL_DESIGN.md) (section 4.3 labels, 5.3 blocking checks, 6 files and reproduction); plan item J11 in `docs/superpowers/plans/2026-10-20-wp-e11-joint-day-model.md`; decisions DECISION_LOG E13 and E14 (the notes on J9b, J9c, the J10 work limit, the J11 first run, the integrality fix and the licence retry). Protocol `exact_day_joint_v1`, its own pooling group: never pooled with `exact_reference_v1` wave rows, `union_day_v1` (WP-E4b) rows or heuristic rows. This README describes the files; it is not paper text (the paper text goes through the writing line later).

The tables are printed from the files: those of the J11 record by `scripts/report_exact_day_joint.py --tables`, and the rerun-versus-first-run tables by a check script that is not part of the repository (it reads only committed files through `git show` and runs no solver).

## This folder is the J11 record; the first run is superseded

- The first J11 run (code commit `f77c2484`, results commit `2ea2c5a2` on branch `results/wp-e11-j11-campaign`) left one cell without a proof claim because of a code defect in the Gurobi integrality test (DECISION_LOG E14, note "J11 first run and lead decisions"). The fix was merged before this rerun (E14, note "integrality fix merged before the J11 rerun"), and the lead decided to re-run J11 in full with one code commit for every cell (E06).
- The first run stays on its branch as a superseded record. It is never pooled with this folder, in either direction. The comparison below only checks that the rerun reproduces it.

## What was run

- Command: `scripts/run_exact_day_joint.py --work-limit 200`, run with `.venv-jit` from the worktree of this branch with `PYTHONPATH` set to the worktree, at code commit `e45cd6bf` (manifest `git_commit` `e45cd6bffc743417b1914952a565ae14af75b21f`). Clean tree (`dirty_working_tree` false, `development_run` false), one serial invocation (`jobs` 1, `serial` true, `cache` none), 140 of 140 cells, `blocking_errors` empty, invocation wall time 10060.5 s (`total_wall_seconds`).
- Arguments recorded in the manifest: all three fleets with empty date, R and L lists (the full grid); 600 s per solver call for HiGHS and Gurobi; Gurobi work limit 200; cross-check on; `aggregate` true; `run_label` empty; `sensitivity_run` false.
- Solvers: HiGHS 1.15.1 through `highspy` (primary) and Gurobi 13.0.3 through AMPL (cross-check), with the same option strings as the first run. Python 3.14.6. Offline: only the committed source campaigns named in `source_manifests` are read.
- The six runner files (`day_joint_manifest.json`, `day_joint.csv`, `day_joint_stages.csv`, `day_joint_plans.json`, `day_joint_week.csv`, `lb0.csv`) are the raw result of commit `81638dba` and are not edited. `comparison.csv`, `reproduction_check.csv`, `rerun_vs_first_run.csv` and this README were added afterwards, read only, with no solver.

### Three attempts; only the third is the record

The same command was started three times at commit `e45cd6bf`. The counts come from the lead's run logs (one line per finished cell):

| Attempt | Cells finished | Stop | Written |
|---|---|---|---|
| 1 | 33 | exit 3 in the 34th cell (`large+sedan\|2026-10-09\|R50\|L2`): "gurobi: solver or license missing" | nothing |
| 2 | 112 | exit 3 in the 113th cell (`large+doblo_cap3\|2026-10-05\|R70\|L2`): the same message | nothing |
| 3 | 140 | exit 0 | this folder |

By design (E06), `backend_unavailable` stops the run and nothing is written, so attempts 1 and 2 left no result and no cell of them is used. The third attempt ran the full grid in one invocation from the start, so the record is still one clean serial run at one commit. DECISION_LOG E14, note "owner decision: a Gurobi solve that fails with a licence-type error is retried up to 2 times before the run stops (amends E06)" (commit `33ec7aa3`), diagnoses the stops as transient failures of the temporary local AMPL licence's online renewal, not an absent solver. That retry was decided after these runs: code commit `e45cd6bf` does not contain it, and no retry occurred in this record.

#### Runtimes of the rerun (day_joint_stages.csv, day_joint.csv)

| fleet | cells | stage rows | longest HiGHS call s | longest Gurobi call s | largest Gurobi work | timing_dependent stage rows | longest cell s | sum of cell s |
|---|---|---|---|---|---|---|---|---|
| large+doblo_cap3 | 60 | 360 | 110.25 | 2.73 | 3.68 | 0 | 422.65 | 4452.6 |
| large+sedan | 60 | 226 | 86.27 | 3.64 | 3.62 | 0 | 568.31 | 4794.0 |
| single_4sw5so | 20 | 80 | 64.56 | 1.95 | 2.42 | 0 | 251.48 | 809.7 |

Stage statuses:

| solver | status | stop_reason | rows |
|---|---|---|---|
| gurobi | infeasible_proven | infeasible | 11 |
| gurobi | optimal | optimal | 322 |
| highs | infeasible_proven | infeasible | 11 |
| highs | optimal | optimal | 322 |

crosscheck_status: {'agree': 125, 'not_run': 15}; wave_values_status: {'agree': 140}.

No stage row is `timing_dependent`. No call came near the 600 s limit or the work limit of 200.

## Cells and labels

There are 140 cells: `single_4sw5so` 20 (5 dates x R in {50, 60, 70, 90}), `large+sedan` 60 (L in {1, 2, 3}) and `large+doblo_cap3` 60 (L in {0, 1, 2}). `K_or_S` is K (vehicles) for the single type and S (peak of the minimised type: sedans, or Doblòs with type id `minivan`) for typed cells. A cell counts as proven only with a proof label and `proof_claim_allowed` True (E14, J9c note). In this run every cell carries the claim.

#### Cells and labels

| fleet | day_status | proof_claim_allowed | cells |
|---|---|---|---|
| large+doblo_cap3 | optimal | True | 60 |
| large+sedan | infeasible_certified | True | 15 |
| large+sedan | infeasible_solver_proven | True | 11 |
| large+sedan | optimal | True | 34 |
| single_4sw5so | optimal | True | 20 |

#### Proof claim reasons

| fleet | proof_claim_reason | cells |
|---|---|---|
| large+doblo_cap3 | crosscheck_agree | 60 |
| large+sedan | arithmetic_certificate | 8 |
| large+sedan | crosscheck_agree | 45 |
| large+sedan | wave_values_crosscheck_agree | 7 |
| single_4sw5so | crosscheck_agree | 20 |

`arithmetic_certificate` is the tier-1 certificate `certificate_capacity_floor` (design 3.2). `wave_values_crosscheck_agree` is a tier-2 certificate whose wave values both solvers agree on. `crosscheck_agree` means HiGHS and Gurobi both proved the day MIP. The 15 certified cells have day cross-check `not_run`, because the certificate decides them without a day MIP.

## Blocking checks (design 5.3)

`scripts/report_exact_day_joint.py` runs these checks per cell. The results are in the `check_*` and `blocking_defects` columns of `comparison.csv`.

- `check_bounds`: K or S is not below LB0, LB0w, LB_S, the bound used or any solver's stage-1 bound, and the large peak is not below LB_L.
- `check_checker`: the runner's independent checker passed the plan (`checker_ok` True).
- `check_union`: where both are proven, joint cars <= WP-E4b union-menu cars, and a proven joint infeasibility never meets a proven union-menu plan.
- `check_peaks`: a proven joint K is at most the peak of the archived GA routes and of the WP-E3 exact routes of the same day. The independent checker recomputes both peaks, and both route sets pass it.

#### Blocking checks (design 5.3)

| check | pass | fail | not_applicable |
|---|---|---|---|
| check_bounds | 114 | 0 | 26 |
| check_checker | 114 | 0 | 26 |
| check_union | 92 | 0 | 48 |
| check_peaks | 20 | 0 | 120 |

Blocking defects: 0

Cells marked `not_applicable`:

- `check_bounds` and `check_checker`: the 26 infeasible cells, which have no value.
- `check_union`: the 20 single-type cells and the 28 typed cells whose union run is `infeasible_for_L`.
- `check_peaks`: every typed cell, because this check applies to the single type only.

Compared with the first run, `check_union` has one more `pass`: the Doblò cell 2026-10-08 R = 50, L = 2 is now proven (S = 2 against union 3).

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

The two cells under "joint value, union menu infeasible" are large+sedan 2026-10-06 R = 70 and R = 90, L = 2 (WP-E4b `both_infeasible_for_L`). In both, the joint model finds a plan with S = 2.

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
| large+doblo_cap3 | 50 | 2 | 5 | 4 | 15 | 0 | 0 |
| large+doblo_cap3 | 60 | 0 | 5 | 7 | 26 | 0 | 0 |
| large+doblo_cap3 | 60 | 1 | 5 | 5 | 19 | 0 | 0 |
| large+doblo_cap3 | 60 | 2 | 5 | 3 | 13 | 0 | 0 |
| large+doblo_cap3 | 70 | 0 | 5 | 7 | 26 | 0 | 0 |
| large+doblo_cap3 | 70 | 1 | 5 | 4 | 16 | 0 | 0 |
| large+doblo_cap3 | 70 | 2 | 5 | 3 | 10 | 0 | 0 |
| large+doblo_cap3 | 90 | 0 | 5 | 7 | 26 | 0 | 0 |
| large+doblo_cap3 | 90 | 1 | 5 | 4 | 15 | 0 | 0 |
| large+doblo_cap3 | 90 | 2 | 5 | 2 | 8 | 0 | 0 |

## Reproduction against the prototype (design 6.3)

The prototype values come from the Claude Science comparison in `docs/science_review/2026-10-19_cs_cc_karsilastirma/`. They are read as data, not as verified truth, and were never an input of the run. The mapping is the one of the report script's docstring, and is unchanged from the first run. The prototype plans are not in the repository, so the checker of design 5.1 was not run on them (`prototype_plan_checked = not_run`). An unchecked prototype plan can never raise the disagreement defect, and no prototype value is better than a production value. large+Doblò cap3 has no external reproduction target (E14 Q1) and gets the category `no_external_target`, so every cell has a reproduction row (E14, J11 first-run note, decision 3).

`category` compares the objective tuple (K or S, then total minutes) on the components the prototype reports; `fleet_category` compares K or S only.

#### Reproduction by category (objective tuple)

| fleet | category | cells |
|---|---|---|
| large+doblo_cap3 | no_external_target | 60 |
| large+sedan | equal | 59 |
| large+sedan | prototype_open | 1 |
| single_4sw5so | equal | 20 |

#### Reproduction by category (fleet value only)

| fleet | fleet_category | cells |
|---|---|---|
| large+doblo_cap3 | no_external_target | 60 |
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

The design 6.3 minute targets ("+194 min over 19 cells", "+257 min in the 12 cells") are differences against wave optima and union menus, not per-cell values in the prototype CSVs, and are not recomputed here.

## Rerun against the first run

Per cell, all non-timing columns are compared: `wall_seconds` of `day_joint.csv`, and `wall_seconds` and `work_units` of `day_joint_stages.csv`, are excluded. Plans are compared per cell as parsed JSON, `lb0.csv` rows per cell, and the MPS sha256 of every stage from the manifests. The per-cell result is in `rerun_vs_first_run.csv`.

#### Rerun against the first run (per cell, timing columns excluded)

| comparison | cells equal | cells differing |
|---|---|---|
| day_status_equal | 140 | 0 |
| K_or_S_equal | 140 | 0 |
| minutes_equal | 140 | 0 |
| plan_equal | 140 | 0 |
| lb0_rows_equal | 140 | 0 |
| mps_sha256_equal | 140 | 0 |

Cells with any other difference (day_joint.csv non-timing column, stage field, lb0 row, plan or MPS hash): 114

- 113 cells differ only in the raw `bound` column of Gurobi stage rows (199 stage rows over all cells; stage keys gurobi2, gurobi3); in none of them does `bound_ceil`, `status`, `objective` or `bound_source` change.
- 1 cell(s) differ in anything else:

| cell | day_joint.csv columns differing | stage fields differing |
|---|---|---|
| large+doblo_cap3 2026-10-08 R50 L2 | proof_claim_allowed:False->True;proof_claim_reason:crosscheck_inconclusive->crosscheck_agree;crosscheck_status:inconclusive->agree | gurobi2.bound:1499.0->1498.99998601;gurobi3.status:rejected->optimal;gurobi3.stop_reason:solver_failure->optimal;gurobi3.objective:->540;gurobi3.bound:539.9999877417731->539.9999833417733;gurobi3.bound_ceil:->540;gurobi3.bound_source:->solver |

Whole files: day_joint_plans.json byte-identical: True; day_joint_week.csv byte-identical: False; lb0.csv byte-identical: True.
Manifest: git_commit f77c2484 -> e45cd6bf; total_wall_seconds 8794.7 -> 10060.5; mps_sha256 entries 333 / 333, all equal: True.
Gurobi work units (measurement, excluded above): stage rows with a different value 0; largest 3.68 -> 3.68.

How to read this:

- Every cell has the same label, the same K or S, the same minutes, the same plan, the same bound rows and the same model bytes (MPS sha256) as in the first run. `day_joint_plans.json` and `lb0.csv` are byte-identical. The Gurobi work units are identical in every stage row, so Gurobi did the same work on the same models.
- The raw Gurobi `bound` column of the stage rows changed in 113 cells. This is the intended effect of fix item (2) (E14): the Gurobi day bound now goes through the HiGHS rule `snap_to_integer_data` (`uniride_core/exact/ampl_backend.py`, called from `classify_gurobi_outcome` in `uniride_core/exact/gurobi_day_backend.py`). The integer ceiling used for proofs, `bound_ceil`, is unchanged in all of these rows. The first run's values, for example 1671.0, are now written as, for example, 1670.99998429.
- `day_joint_week.csv` differs in one value: `cells_not_proven` of large+Doblò cap3 R = 50, L = 2 is now 0 (it was 1).

#### large+doblo_cap3|2026-10-08|R50|L2

| run | solver | stage | status | stop_reason | objective | bound | bound_ceil | solve_result |
|---|---|---|---|---|---|---|---|---|
| first | gurobi | 1 | optimal | optimal | 2 | 2.0 | 2 | solved |
| first | gurobi | 2 | optimal | optimal | 1499 | 1499.0 | 1499 | solved |
| first | gurobi | 3 | rejected | solver_failure |  | 539.9999877417731 |  | solved |
| first | highs | 1 | optimal | optimal | 2 | 2.0 | 2 | kOptimal |
| first | highs | 2 | optimal | optimal | 1499 | 1498.99998601 | 1499 | kOptimal |
| first | highs | 3 | optimal | optimal | 540 | 539.9999956 | 540 | kOptimal |
| rerun | gurobi | 1 | optimal | optimal | 2 | 2.0 | 2 | solved |
| rerun | gurobi | 2 | optimal | optimal | 1499 | 1498.99998601 | 1499 | solved |
| rerun | gurobi | 3 | optimal | optimal | 540 | 539.9999833417733 | 540 | solved |
| rerun | highs | 1 | optimal | optimal | 2 | 2.0 | 2 | kOptimal |
| rerun | highs | 2 | optimal | optimal | 1499 | 1498.99998601 | 1499 | kOptimal |
| rerun | highs | 3 | optimal | optimal | 540 | 539.9999956 | 540 | kOptimal |

first: day_status optimal, K_or_S 2, total_minutes 1499, car_minutes 540, proof_claim_allowed False (crosscheck_inconclusive), crosscheck inconclusive.

rerun: day_status optimal, K_or_S 2, total_minutes 1499, car_minutes 540, proof_claim_allowed True (crosscheck_agree), crosscheck agree.

So this cell has the same value as in the first run (S = 2, total minutes 1499, car minutes 540; Gurobi stage 3 objective 540 = HiGHS). Now that Gurobi stage 3 is accepted, the day cross-check agrees and the claim is allowed.

## What this does not show

- No paper claim. The rows are descriptive results of one snapshot week, one GA seed (42) on the GA side, one machine and one software version. They support no superiority, causality or generality statement (AGENTS.md). Paper text goes through the writing line.
- The joint rows are a separate protocol (`exact_day_joint_v1`). WP-E4b union-menu cars and the archived route peaks appear as separate columns of `comparison.csv`; nothing is pooled, and no `min(...)` is taken across protocols.
- The first run and the J10 calibration rows are never pooled with this folder. The rerun-versus-first-run table is a repeat check on one machine with one software version, not a statement about other machines.
- Agreement with the prototype is agreement with unverified data, because the prototype plans were not checked here.
- No sensitivity run, no longer limit and no other week.

## Files

| File | Content |
|---|---|
| `day_joint_manifest.json` | runner manifest: protocol, commit, dirty flag, `python_provenance`, source manifests, solver versions, options and limits, `mps_sha256` per cell and stage, enumeration caps and columns per day, `run_history`, output sha256 (raw, not edited) |
| `day_joint.csv` | one row per cell (140): label, K or S, large peak, minutes, bounds, bound source and proof, proof claim and reason, cross-check and wave-values verdicts, checker, TS confirmation, wall seconds (raw) |
| `day_joint_stages.csv` | one row per cell, solver and stage: status, stop reason, objective, bound, flags, wall seconds, Gurobi work units, solve result, `mps_sha256` (raw) |
| `day_joint_plans.json` | per cell and wave the chosen routes (raw) |
| `day_joint_week.csv` | per fleet, R and L: weekly fleet (maximum over dates), vehicle-days, cells not proven (raw) |
| `lb0.csv` | LB0, LB0w, LB_L, LB_S, certificates and the wave values with both solvers' verdicts (raw) |
| `comparison.csv` | per cell (140): joint values and bounds; WP-E4b GA-menu and union-menu status, cars and label (typed); `joint_minus_union_cars`; peaks, minutes and checker violations of the archived GA and WP-E3 route sets (single type); `check_bounds`, `check_checker`, `check_union`, `check_peaks` and `blocking_defects` (empty = none) |
| `reproduction_check.csv` | per cell (140): prototype status, value and minutes, `prototype_plan_checked`, production status, claim, value and minutes, `components_compared`, `category` (`no_external_target` for large+Doblò cap3), `fleet_category`, `note` |
| `rerun_vs_first_run.csv` | per cell (140): the first and rerun day status, K or S and proof claim; booleans `day_status_equal`, `K_or_S_equal`, `minutes_equal` (total minutes, car minutes, large peak), `plan_equal`, `lb0_rows_equal`, `mps_sha256_equal`; `mps_stages`; the non-timing `day_joint.csv` columns and stage fields that differ, as `old->new` |
| `README.md` | this file |

To reproduce `comparison.csv`, `reproduction_check.csv` and the J11 tables (read only, no solver): `PYTHONPATH=<repo root> python scripts/report_exact_day_joint.py --tables` (exit 0 means no blocking defect).
