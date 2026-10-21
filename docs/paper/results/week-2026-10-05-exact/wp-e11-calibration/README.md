# WP-E11 J10: calibration run of the joint day model (week of 2026-10-05)

Design: [`JOINT_DAY_MODEL_DESIGN.md`](../../../../designs/JOINT_DAY_MODEL_DESIGN.md) (section 4 solver runs, section 6.1 files); plan item J10 in `docs/superpowers/plans/2026-10-20-wp-e11-joint-day-model.md`; decisions DECISION_LOG E13 and E14 (the notes on J9b, J9c and "owner decision after the J10 calibration: Gurobi work limit 200 for J11"). Protocol `exact_day_joint_v1`. This folder measures runtimes, Gurobi work units and repeatability of the joint day runner on a small subset. It is a calibration archive, not a result table: nothing here is a paper claim.

## What was run

- Runner `scripts/run_exact_day_joint.py`, started serially by the lead from a clean working tree of this results branch (`results/wp-e11-j10-calibration`), with `.venv-jit` and `PYTHONPATH` set to the worktree. Python 3.14.6, HiGHS 1.15.1 (`highspy`, primary), Gurobi 13.0.3 through AMPL (cross-check), Node v25.5.0 for the TypeScript confirmation CLI, host Windows 11. Every manifest has `python_provenance` with the three packages imported from the checkout (relative paths).
- Settings, the same in all 12 manifests: 600 s per solver call (HiGHS and Gurobi), threads 1, no work limit (`work_limit` null for both solvers), Gurobi cross-check on, `wave_values` `sp`, `jobs` 1 (one invocation per slice, `serial` true), `run_label` empty, `sensitivity_run` false, `dirty_working_tree` false, `development_run` false, no blocking error.
- 6 slices, each run twice (folder suffix `a` and `b`, 12 folders):

| Folder pair | Fleet | Date | R | L | Arguments |
|---|---|---|---|---|---|
| `homog-1005-a/b` | `single_4sw5so` | 2026-10-05 | 70, 90 | none | `--fleets single_4sw5so --dates 2026-10-05 --rides 70,90` |
| `homog-1008-a/b` | `single_4sw5so` | 2026-10-08 | 50, 60, 90 | none | `--fleets single_4sw5so --dates 2026-10-08 --rides 50,60,90` |
| `sedan-1005-a/b` | `large+sedan` | 2026-10-05 | 70, 90 | 2 | `--fleets large+sedan --dates 2026-10-05 --rides 70,90 --limits 2` |
| `sedan-1008-a/b` | `large+sedan` | 2026-10-08 | 50, 60, 90 | 2 | `--fleets large+sedan --dates 2026-10-08 --rides 50,60,90 --limits 2` |
| `doblo-1005-a/b` | `large+doblo_cap3` | 2026-10-05 | 70, 90 | 1 | `--fleets large+doblo_cap3 --dates 2026-10-05 --rides 70,90 --limits 1` |
| `doblo-1008-a/b` | `large+doblo_cap3` | 2026-10-08 | 50, 60, 90 | 1 | `--fleets large+doblo_cap3 --dates 2026-10-08 --rides 50,60,90 --limits 1` |

  The manifests record `options` (fleets, dates, rides, limits), which match the table. The remaining arguments (`--out`, and the default 600 s, cross-check and wave values) are as the manifest states; the command lines themselves are the lead's report.
- Order: `homog-1005-a` first, on its own; then one chain: `homog-1005-b`, `homog-1008-a`, `sedan-1005-a`, `sedan-1008-a`, `doblo-1005-a`, `doblo-1008-a`, `homog-1008-b`, `sedan-1005-b`, `sedan-1008-b`, `doblo-1005-b`, `doblo-1008-b`. The result commits on the branch follow this order, and the 12 slices ran one after another. The total of the manifest run times is 5173 s.
- One commit per slice, right after it finished, because the runner (E06) refuses a working tree that contains untracked result folders. Therefore `git_commit` differs between the 12 manifests. In each manifest it is the commit directly before that slice's own result commit. The code is the same throughout: `git diff --stat 87cef0346d18 2da41c3b5f41` between the first manifest commit (`87cef0346d18`, slice `homog-1005-a`) and the last one (`2da41c3b5f41`, slice `doblo-1008-b`) touches 66 files, all under `docs/paper/results/week-2026-10-05-exact/wp-e11-calibration/` (7804 insertions, no other path). Every pair of consecutive manifest commits differs only under that folder as well.
- Offline apart from the solvers: the runner reads the committed source campaigns (`week-2026-10-05-fleet-rerun-*`), no database, no HTTP. The Gurobi log is read in memory for the work units and is not stored.

## Cells

5 cells per fleet (the plan asks for 5 per fleet including 2026-10-05 R = 70 and R = 90): 2026-10-05 R = 70 and R = 90 (the heaviest day, 14 654 and 45 302 columns for the single type) and 2026-10-08 R = 50, 60 and 90, with one middle L per typed fleet (large+sedan L = 2, large+Doblò cap3 L = 1). That is 15 distinct cells; each was solved twice, which gives 30 cell runs (rows of `calibration_summary.csv`). Counts below are cell runs unless "cells" says otherwise.

- 28 cell runs (14 cells) `optimal`; 2 cell runs (1 cell: large+sedan, 2026-10-08, R = 50, L = 2) `infeasible_solver_proven`.
- All 30 cell runs: `proof_claim_allowed` True (`proof_claim_reason` `crosscheck_agree`), day cross-check `agree` (HiGHS and Gurobi), wave-values verdict `agree`, `timing_dependent` false, `non_lexicographic` false, no flags, no unverified bounds, no certificate tier. 28 optimal runs passed the independent checker (`checker_ok` True); the 18 typed optimal runs are `confirmed` by the TypeScript CLI, the 10 single-type runs are `not_applicable_single_type` (the runner docstring: the CLI needs both a fixed and a minimised type). The infeasible runs have neither a plan nor a TS confirmation.
- Solver stage rows: 76 per solver, all with `timing_dependent` false (HiGHS: 74 `optimal`, 2 `infeasible_proven`; Gurobi: the same). Stage 1 in 30 cell runs, stage 2 in 28, stage 3 in 18 (typed optimal runs).

`K_or_S` in `calibration_summary.csv` is `K` for the single type (vehicles) and `S` for typed cells (peak number of vehicles of the minimised type), as the runner writes it; it is empty for the infeasible cell. Per cell (values equal in both runs unless two numbers are shown; times are `a` / `b`):

| Fleet | Date | R | L | Result | K or S | Cell wall s | HiGHS longest call s | Gurobi longest call s | Gurobi work units (max) |
|---|---|---|---|---|---|---|---|---|---|
| single_4sw5so | 2026-10-05 | 70 | - | optimal | 4 | 76.93 / 77.53 | 16.87 / 16.77 | 0.97 / 1.01 | 0.59 |
| single_4sw5so | 2026-10-05 | 90 | - | optimal | 3 | 360.42 / 291.04 | 95.25 / 71.00 | 2.63 / 3.95 | 2.42 |
| single_4sw5so | 2026-10-08 | 50 | - | optimal | 4 | 32.36 / 36.95 | 0.13 / 0.13 | 0.31 / 0.42 | 0.01 |
| single_4sw5so | 2026-10-08 | 60 | - | optimal | 4 | 31.87 / 32.69 | 0.21 / 0.23 | 0.31 / 0.40 | 0.01 |
| single_4sw5so | 2026-10-08 | 90 | - | optimal | 3 | 33.47 / 33.53 | 0.69 / 0.74 | 0.36 / 0.32 | 0.04 |
| large+sedan | 2026-10-05 | 70 | 2 | optimal | 2 | 127.85 / 124.99 | 8.07 / 7.48 | 2.05 / 2.01 | 1.32 |
| large+sedan | 2026-10-05 | 90 | 2 | optimal | 2 | 675.47 / 679.13 | 117.04 / 88.86 | 3.63 / 3.85 | 3.62 |
| large+sedan | 2026-10-08 | 50 | 2 | infeasible_solver_proven | - | 65.07 / 61.92 | 0.00 / 0.00 | 0.33 / 0.28 | 0.00 |
| large+sedan | 2026-10-08 | 60 | 2 | optimal | 2 | 65.39 / 63.42 | 0.21 / 0.22 | 0.34 / 0.32 | 0.02 |
| large+sedan | 2026-10-08 | 90 | 2 | optimal | 1 | 67.37 / 66.86 | 1.58 / 1.56 | 0.48 / 0.46 | 0.16 |
| large+doblo_cap3 | 2026-10-05 | 70 | 1 | optimal | 4 | 138.21 / 136.73 | 17.87 / 17.43 | 0.84 / 0.81 | 0.64 |
| large+doblo_cap3 | 2026-10-05 | 90 | 1 | optimal | 4 | 705.90 / 787.16 | 193.71 / 242.69 | 3.96 / 3.93 | 3.68 |
| large+doblo_cap3 | 2026-10-08 | 50 | 1 | optimal | 3 | 65.37 / 64.97 | 0.24 / 0.23 | 0.31 / 0.31 | 0.02 |
| large+doblo_cap3 | 2026-10-08 | 60 | 1 | optimal | 3 | 63.30 / 65.28 | 0.31 / 0.31 | 0.32 / 0.35 | 0.03 |
| large+doblo_cap3 | 2026-10-08 | 90 | 1 | optimal | 2 | 66.64 / 66.83 | 0.98 / 1.03 | 0.69 / 0.39 | 0.08 |

## Determinism (repeat runs)

For each of the 6 pairs (`a` against `b`) `determinism.csv` has one row and one boolean column per compared file. Comparison rule:

- `day_joint.csv`, `day_joint_stages.csv`, `lb0.csv`, `day_joint_week.csv`: row by row, after removing the columns `wall_seconds`, `work_units` and `note` (the three columns that exist in these files and can differ between runs; `note` is empty in all 30 `day_joint.csv` rows). Only `day_joint.csv` and `day_joint_stages.csv` have `wall_seconds`; only the stages file has `work_units`.
- `day_joint_plans.json`: byte-identical.
- `mps_sha256` of the manifest (the canonical MPS per cell and stage): equal.

Result: all 6 pairs are equal in all six columns. In addition, the Gurobi work units (the `work_units` column, excluded above because it is a measurement) are equal in every stage row of every pair. Only the wall times differ between a pair, for example HiGHS on 2026-10-05 R = 90, large+Doblò cap3, took 193.71 s in run `a` and 242.69 s in run `b`, and on the single type 95.25 s and 71.00 s. The plans, values, statuses, bounds and labels do not change. This is a repeat check of 15 cells on one machine with one software version, not a statement about other machines.

## Runtimes and Gurobi work

All numbers from `calibration_summary.csv` (cell wall seconds from `day_joint.csv`; call seconds and work units from the `day_joint_stages.csv` rows of the day MIP stages).

- Longest HiGHS call: 242.69 s (run `doblo-1005-b`, large+Doblò cap3, 2026-10-05, R = 90, L = 1, stage 1), 40 percent of the 600 s limit. Next: 193.71 s (same cell, run `a`), then 117.04 s (large+sedan, 2026-10-05, R = 90, L = 2, run `a`). Every other HiGHS call is under 100 s.
- Longest Gurobi call: 3.96 s (`doblo-1005-a`, same cell, stage 3). Gurobi's calls are 3.96 s or shorter in all 30 cell runs.
- Largest Gurobi work: 3.68 work units (large+Doblò cap3, 2026-10-05, R = 90, L = 1, stage 3, identical in both runs). Next: 3.62 (large+sedan, 2026-10-05, R = 90, L = 2), 2.42 (single type, 2026-10-05, R = 90), 1.32, 0.64, 0.59; every 2026-10-08 cell is 0.16 or lower.
- Longest cell: 787.16 s (`doblo-1005-b`, the cell above). The cell wall second is not a solver call: it also contains the enumeration, the wave-value solves of both solvers, the certification and the checks. The 600 s limit applies to each solver call, and no call came close to it. The wave-value call times are not recorded in these files, so this README makes no statement about them beyond what the cell wall seconds include. The 2026-10-08 typed cells take about 62 to 67 s each although their day MIP stages take at most 1.6 s (HiGHS) and 0.7 s (Gurobi); the single-type 2026-10-08 cells take about 32 to 37 s.
- The heaviest day (2026-10-05, R = 90) is the longest cell for each fleet: 291.04 to 360.42 s (single type), 675.47 to 679.13 s (large+sedan), 705.90 to 787.16 s (large+Doblò cap3). Sum of all manifest run times: 5173.1 s.
- HiGHS has no work limit (design section 4.2), so a HiGHS call that stops on its time limit would be `timing_dependent` true. None did in this subset.

## Work-limit proposal and owner decision

Starting point (design section 4.2 and E03): the Gurobi work limit of 200 per peak-wave call. The largest Gurobi work observed in this subset is 3.68 units, so 200 is about 54 times the largest observed work, and the limit would not have stopped any of the 76 Gurobi calls. The owner decision is recorded in DECISION_LOG E14 (2026-10-21, "owner decision after the J10 calibration: Gurobi work limit 200 for J11"): the J11 campaign passes `--work-limit 200`, and the 600 s per call stays as a safety net. This calibration itself ran without a work limit (manifest `work_limit` null), so no row of this folder is a work-limited run.

## Cells expected to stay open

None in this subset: every one of the 15 cells was proven by both solvers at 600 s per call in both runs. Caveat: the subset has one L per typed fleet (L = 2 for large+sedan, L = 1 for large+Doblò cap3) and two dates (2026-10-05 and 2026-10-08), so other L values, other dates and the remaining R values may still stay open in J11. The longest HiGHS call is 40 percent of the time limit on a cell with 45 302 (single type) to 47 215 (large+sedan) columns; the subset does not locate the point where 600 s stops proving.

## What this does not show

- No claim beyond these 15 cells (30 cell runs): no statement about the other cells of the 140-cell campaign, other weeks, other machines or other software versions.
- The calibration rows are never pooled into the J11 table, in either direction, and are not used to tune the model (E14: prototype results are reproduction targets, never tuning targets). The protocol `exact_day_joint_v1` is its own pooling group, never pooled with `exact_reference_v1`, `union_day_v1` or heuristic rows.
- No comparison with the prototype or with the production run is made here; that belongs to J11 (`comparison.csv`, `reproduction_check.csv`), which also writes the final README.
- The values in the rows (K or S, plans) are descriptive results of these cells; no comparison with the GA or any other method is made, so there is no ranking or superiority statement.

## Files

| File | Content |
|---|---|
| `<slice>/day_joint_manifest.json` | per slice: commit and dirty flag, options, solver versions, limits and work limit, `mps_sha256` per cell and stage, output sha256, run history (invocation seconds, cell seconds, status), blocking errors (empty), `python_provenance` |
| `<slice>/day_joint.csv` | one row per cell: status, K or S, bounds, bound source and proof, proof claim and reason, cross-check and wave-values verdicts, checker, TS confirmation, wall seconds |
| `<slice>/day_joint_stages.csv` | one row per solver and stage: status, stop reason, objective, bound, wall seconds, Gurobi work units, `mps_sha256` |
| `<slice>/day_joint_plans.json` | the plans |
| `<slice>/day_joint_week.csv` | per fleet, R and L: aggregation over the slice's dates (one date per slice here) |
| `<slice>/lb0.csv` | lower bounds with their wave-value sources |
| `calibration_summary.csv` | one row per cell and run (30 rows): `fleet, date, R, L, run, day_status, K_or_S, proof_claim_allowed, crosscheck_status, wave_values_status, cell_wall_seconds, highs_max_call_seconds, gurobi_max_call_seconds, gurobi_max_work_units`; sorted by fleet, date, R, L, run; `L` empty for the single type |
| `determinism.csv` | one row per pair (6 rows) with the columns `day_joint_csv_equal, day_joint_stages_csv_equal, lb0_csv_equal, day_joint_week_csv_equal, day_joint_plans_json_byte_identical, mps_sha256_equal` |

`calibration_summary.csv` and `determinism.csv` are derived from the 12 slice folders by a check script that is not part of the repository (it reads only the committed files and `git` and does not run any solver). The slice folders are the raw results and are not edited.
