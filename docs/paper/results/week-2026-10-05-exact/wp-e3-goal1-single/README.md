# WP-E3 GOAL 1, single type 4 Sw / 5 So: exact optimum and gap of the archived GA waves

Result directory of work package WP-E3 of `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md`. For every wave
of the archived week (57 waves x R = 50, 60, 70, 90 = 228 (R, wave) rows) it holds the exact
optimum (K*, D*) of the wave problem, the proven lower bounds, and the gap of the archived GA
routes. It is a descriptive measurement of one snapshot week; it makes no superiority claim.

## What was run

- Command: `UNIRIDE_AMPL_DIR=<local AMPL directory> python scripts/run_exact_wave_gaps.py`
  (HiGHS verification is on by default). Offline: it reads only
  `docs/paper/results/week-2026-10-05-4sw5so/` (never the DB or HTTP).
- Commit of the run: `97259e2b1f59eea0192a01f30a485727fd912dff`, `dirty_working_tree: false`
  (the results were produced from a clean worktree; this directory was added afterwards).
- Source campaign (the GA side): `docs/paper/results/week-2026-10-05-4sw5so`, manifest sha256
  `f152ca63068be91be03c7ca27cf767fef52cc9345a6cb69d155f75a137f90b15`, GA commit `6be127d`
  with a dirty working tree (it predates CX-01 and CX-03, design F14).
- Per wave: WP-E1 enumeration (caps 2 000 000 columns / 5 000 000 labels / 600 s; no cap fired,
  all 228 rows are model `SP`), WP-E2 set-partitioning solve with Gurobi 13.0.3 through AMPL
  20260809 / amplpy 0.18.0 (stage 1 min K, stage 2 min D with K fixed, and `D_LB_free`),
  limits 60 s and 20 work units per call, 600 s and 200 work units per call on the five peak
  waves, threads 1, seed 0, `mip:gap=0`, `mip:gapabs=0.99`; verbatim option strings are in
  `exact_manifest.json`.
- Certification (design section 3): the exact routes (expanded to occurrence ids) are wrapped in
  the operational response schema, the operational request is rebuilt with the archived
  parameters, and `certify_optimization_response` judges them on the arcs of the archived
  per-date `*.matrix.json` slice. The archived GA routes of the same wave pass through the same
  call and the same arcs. K and D are recomputed from the certified routes in integer arithmetic
  and equal the solver objective. A failed certificate would give status `rejected`.
- HiGHS 1.15.1 re-solved every Gurobi-`optimal` wave (stage 1 and stage 2, same limits, no work
  limit); a difference in the proven (K*, D*) would be blocking.

## Files

- `exact_manifest.json`: schema `exact_reference_v1` (passes
  `academic_benchmark.exact_reference.protocol.validate_manifest`; no private data): commit and
  dirty flag, source campaign and its manifest sha256, declared matrix sha256 per (date, R) and
  the sha256 of each archived arc slice, the peak-wave list (D-B), AMPL / amplpy / solver versions
  and option strings, caps, per wave the model, column and label counts, the stage rows with status,
  stop reason, `timing_dependent`, `non_lexicographic`, objective, bound, wall seconds, Gurobi work
  units, the wave result row, `blocking_errors` (empty), Python version, host OS.
- `wave_gaps.csv`: one row per (R, wave) with the single-type columns of the WP-E6 list: date, R,
  fleet (`single_4sw5so`), wave id, direction, anchor, students, peak flag, model, columns, labels,
  `K_GA`, `K_LB` (and its source), `K_star`, `D_GA`, `D_LB`, `D_star`, `D_LB_free`, `dK`, `gD`
  (with `gD_note`), `gD_free`, wave `status`, per-stage status / stop reason / `timing_dependent` /
  `non_lexicographic`, solver, runtimes, certificate and cross-check results, HiGHS result, and the
  GA labels `ga_protocol` = `native`, `ga_seed` = 42, `ga_commit` = `6be127d`, `ga_dirty_tree` =
  `True` (read from the source manifest). `D_GA` is the GA duration recomputed on the matrix; it
  equals the archived total of every wave. `K_star`, `D_star` are the incumbent values; they are
  proven optima when `status` is `optimal`. The WP-E6 columns `option` and `quota` are typed-fleet
  columns and are not produced here.
- `summary.json`: counts per R (statuses, stop reasons, `dK`, HiGHS agreement, exact <= GA).

## Measured facts (this machine, one run)

Every row has a status label; no wave is dropped. All 228 rows are `optimal` (all 684 stage rows
have stop reason `optimal`, none `timing_dependent`, no wall or work limit fired); exact and GA
certificates are `is_feasible: true` on all 228 rows; the objective cross-check is `ok` on all
228; exact <= GA holds on all 228 rows; HiGHS gives the same (K*, D*) as Gurobi on all 228.

| R | waves | `dK = 0` | `dK = 1` | `gD` defined | `gD > 0` | mean `gD` | max `gD` | sum K_GA | sum K* | sum D_GA | sum D* |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 50 | 57 | 56 | 1 | 56 | 3 | 0.000552 | 0.018462 | 109 | 108 | 6822 | 6803 |
| 60 | 57 | 56 | 1 | 56 | 6 | 0.004200 | 0.089947 | 94 | 93 | 6450 | 6369 |
| 70 | 57 | 56 | 1 | 56 | 3 | 0.001067 | 0.027778 | 82 | 81 | 6053 | 6028 |
| 90 | 57 | 56 | 1 | 56 | 3 | 0.001135 | 0.034146 | 73 | 72 | 5862 | 5813 |

`dK = K_GA - K_LB` and `K_LB = K*` on every row (K* proven). `gD = (D_GA - D_LB) / D_LB` is defined
only where `K_GA = K*`; the mean is the unweighted mean over those 56 waves per R. The sums run over
all 57 waves. The four waves where the GA used one more route than the optimum (`gD` not
comparable; `gD_free` shown) are all 08:45 pickup waves:

| R | wave | students | K_GA | K* | D_GA | D* |
|---|---|---|---|---|---|---|
| 50 | 2026-10-07:pickup:525 | 11 | 4 | 3 | 256 | 247 |
| 60 | 2026-10-05:pickup:525 | 20 | 5 | 4 | 400 | 374 |
| 70 | 2026-10-07:pickup:525 | 11 | 3 | 2 | 227 | 216 |
| 90 | 2026-10-05:pickup:525 | 20 | 4 | 3 | 364 | 329 |

Largest enumeration: 45 170 columns and 171 053 labels (the 20-leg wave at R = 90). Largest Gurobi
work: 1.64 work units on any call. `K_LB` comes from the solver bound on 183 rows and from AMPL's
presolve on 45 rows. Total run: 870 s (Gurobi solve calls 250 s, HiGHS re-solves 600 s; the two
HiGHS calls on the 20-leg wave at R = 90 took 205 s together, inside that wave's 600 s peak-wave
limit; HiGHS has no work limit, so on a slower host that wave's HiGHS rows could be
`timing_dependent`).

## Wording rule

A single snapshot week; a descriptive gap measurement, not a superiority claim; the GA side is one
seed-42 run under the native secondary protocol (the gap is the gap of that run, not of the GA in
general) at the archived commit `6be127d` (dirty tree). Exact rows (`exact_reference_v1`) are never
pooled, ranked or tested statistically with heuristic rows; the gap is the only cross-protocol
quantity and always carries both labels.
