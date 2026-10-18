# Scaling probe: exact route enumeration (scoping measurement)

Facts only. The probe makes no paper claim: no superiority, causality or proof statement follows from it.

## What was measured
- `uniride_core/exact/route_enumeration.py` (WP-E1) run on synthetic waves, one subprocess per enumeration (hard timeout 660 s, in-process working-set guard 2500 MB), serially.
- Caps in force: 2 000 000 columns, 5 000 000 labels, wall-clock limit 600 s. Tour cap 150; pickup anchor 525 (dropoff run with the same anchor).

## The waves are synthetic
- Travel times are the REAL captured matrix: the union of the arcs of the per-date `*.matrix.json` slices of `week-2026-10-05-4sw5so` (one snapshot, sha256 `bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5`), integer minutes, depot D.Kampus.
- 28 distinct stop locations appear in the archive; 26 have their full arc set (to and from the depot and every other stop) and are used. Excluded: So3, Sw8. Arcs absent from the archive union: So3->Sw8, Sw8->So3.
- There are at most 26 real locations, so a larger n means more students per location (n = 80 on 26 locations is about 3.1 students per location).
- Students are placed at k distinct stops (k = 10, 20, all usable; k <= n): a uniform sample without replacement, one student per chosen stop first, the rest spread uniformly at random.
- Class: the number of Sw students is n x 68/226 (the Sw share of the legs of the archive waves) rounded half up, on uniformly random students. The class is drawn independently of the stop, so one stop can hold Sw and So students (two items at one location). In the archive a stop code carries its class.
- Seeds 1, 2, 3 per cell; the instance is `random.Random("scaling-probe:<seed>:<n>:<k>")`, identical for every R, fleet and direction.

## Grid and stopping rules
- n in 20, 30, 50, 80; R in 50, 70, 90; fleets: single type 4 Sw / 5 So (large); large + sedan (0 Sw / 4 So); large + Doblo (minivan 1 Sw / 3 So, total capacity 3), types as in the WP-E10 manifests.
- Typed fleets ran only where the single type completed (all seeds) at that (direction, n, k, R).
- Along n, a cell with any seed not complete stops the larger sizes of the same (fleet, direction, k, R): status `not_run_smaller_capped`; `not_run_single_not_complete` marks typed cells whose single-type cell did not complete.
- Dropoff direction check: n = 50, k = all, every fleet under the same typed rule, no early stop.

## Statuses
`complete`; `column_cap`, `label_cap` (deterministic caps); `timing_dependent_abort` (600 s wall-clock limit); `memory_guard_abort` (probe guard on the working set, not an enumerator cap; labels and columns unknown); `memory_error`; `subprocess_timeout`, `subprocess_crash` (harness).

## Run
- Rows: 324 (231 enumerations run). Status counts: complete: 213, label_cap: 18, not_run_single_not_complete: 78, not_run_smaller_capped: 15.
- Peak working set over the runs: 1742.5 MB.
- Total wall time of the probe: 5322 s.
- Files: `probe.csv` (one row per run), `summary.md`, `manifest.json` (commit, dirty flag, matrix sha256 values, seeds, caps, versions, `python_provenance`).
- Reproduce: `PYTHONPATH=<repo root> python scripts/probe_exact_enumeration_scaling.py` from a clean commit.
