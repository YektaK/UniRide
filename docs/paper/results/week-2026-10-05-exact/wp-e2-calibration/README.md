# WP-E2 SP solve calibration (exact solver, design sections 1.2, 4, 9)

Measurement for work package WP-E2 of `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md`. It is an
engineering calibration of the AMPL set-partitioning solves, not a result: no route is
certified (that is WP-E3), no GA gap is computed, and nothing here supports a superiority claim.

Files:

- `calibration_calls.csv`: one row per solver call, 2 solvers x 4 R x 57 waves x 3 calls
  (stage 1 min K, stage 2 min D with K fixed, `D_LB_free`) = 1 368 rows. Columns: solver, R,
  wave, date, direction, anchor, legs, peak flag (D-B), column count, stage, fixed K, status,
  stop reason, `timing_dependent`, `non_lexicographic`, incumbent, raw bound, rounded bound,
  bound source, AMPL `solve_result_num`, wall seconds, Gurobi work units, time limit, work
  limit, limit hit.
- `calibration_waves.csv`: one row per (solver, R, wave) = 456 rows: wave status, K, D, K_LB
  (and its source), D_LB, D_LB_free, route count, largest lambda, enumeration and total solve
  seconds.
- `summary.json`: commit, Python, host OS, AMPL/amplpy/solver versions, the verbatim option
  strings (normal and peak), limits, per (solver, R) maxima and status counts, Gurobi/HiGHS
  agreement. The AMPL location is recorded only as "local AMPL installation used".

Production:

- Command: `UNIRIDE_AMPL_DIR=<local AMPL directory> python scripts/calibrate_exact_sp.py`
  (offline; reads `../../week-2026-10-05-4sw5so/` through `scripts/exact_archive_loader.py`,
  enumerates each wave with WP-E1 defaults, solves with `uniride_core/exact/ampl_backend.py`).
- Fleet: single type 4 Sw / 5 So, R = 50, 60, 70, 90, all 57 waves; peak waves (D-B) are the five
  08:45 pickup waves. Limits as in production of GOAL 1: 60 s per call, 600 s per call on a peak
  wave, Gurobi work limit 30 (300 on a peak wave; now 20/200, see below), threads 1, seed 0, `mip:gap=0`,
  `mip:gapabs=0.99`.
- Solvers: Gurobi 13.0.3 and HiGHS 1.15.1 via AMPL 20260809, amplpy 0.18.0 (academic license).

Findings (this machine, single run, 2026-10-15):

- All 1 368 calls ended `optimal` (stop reason `optimal`); no wall, work or other limit fired.
  Every wave is `optimal` for both solvers, and Gurobi and HiGHS give the same (K*, D*) on all
  228 (R, wave) pairs.
- Gurobi: longest call 5.7 s wall (the 20-leg 2026-10-05 08:45 pickup wave, R = 90, stage 1,
  45 170 columns), at most 1.64 work units; every non-peak call at most 2.7 s.
- HiGHS: the same peak wave at R = 90 needs 101 s (stage 1), 114 s (stage 2) and 82 s
  (`D_LB_free`), and 8-12 s at R = 70; every non-peak call at most 3.2 s. These calls exceed the
  60 s normal limit and stay under the 600 s peak-wave limit of D-B; HiGHS has no work limit,
  so a HiGHS run on a slower host could become `timing_dependent` on that wave.
- Wall seconds include AMPL's model generation and the solver process start (on waves with at
  most 3 columns a call averages 0.35 s with Gurobi and 0.53 s with HiGHS; calls that AMPL's
  presolve settles take at most 1.5 ms with Gurobi and 1.1 ms with HiGHS); `lim:time` limits the solver run only.
- `calibration_waves.csv` predates the new `K_LB_source` labels (presolve-settled waves now report
  `ampl_presolve`) and the 20/200 work limit; the reviewer's reruns at R = 90 and R = 50 (342 calls)
  gave identical bounds and statuses.
- Work limit: the calibration ran with a Gurobi work limit of 30 work units per call (300 on a
  peak wave). No call came near either limit (at most 1.64 work units). The setting has since
  changed to 20 (200 on a peak wave), owner decision 2026-10-16 (DECISION_LOG E03); the run was not
  repeated because no call is near the new limit either.
- SP vs brute-force oracle (unit test, 500 generator instances): identical (K, D) and status on
  all 500 for both solvers (334 optimal, 166 proven infeasible, 38 instances use a column more
  than once); runtime 374 s with Gurobi and 555 s with HiGHS. The default test run uses the first
  120 instances (about 70 s and 130 s); `UNIRIDE_EXACT_FULL_ORACLE=1` runs all 500.

Caveats: `summary.json` records commit `73d0009` with `dirty_working_tree: true`; the only
uncommitted tracked change during the run was an edit of `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md`
(text, no code). A single snapshot week and one machine; timings are descriptive and depend on the host
and its load; they are used only to check that the limits do not bind.
