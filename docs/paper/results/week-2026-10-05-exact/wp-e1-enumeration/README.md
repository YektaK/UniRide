# WP-E1 route enumeration counts (exact solver, design section 1.1 Step A)

Measurement for work package WP-E1 of `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md`. It is an
engineering measurement of the enumeration step, not a result: no model is solved here and no
gap, bound or optimum is reported.

Files:

- `enumeration_counts.csv`: one row per (fleet, R, wave), 3 fleets x 4 R x 57 waves = 684 rows.
  Columns: fleet (`single_4sw5so`, `large+sedan`, `large+doblo_cap3`), the types enumerated,
  service date, R, wave id, direction, anchor, legs, (location, class) items, peak flag (D-B),
  status, cap fired, model, column count, label count, largest label level, number of levels,
  seconds (wall clock of this machine; descriptive only).
- `summary.json`: commit, Python version, host OS, caps used and per (fleet, R) maxima.

Production:

- Command: `python scripts/measure_exact_enumeration.py` (offline; reads the archives through
  `scripts/exact_archive_loader.py`, never the DB or HTTP).
- Inputs: `../../week-2026-10-05-4sw5so/` (single type 4 Sw / 5 So), `../../week-2026-10-05-fleet/`
  (large 4/5 + sedan 0/4) and `../../week-2026-10-05-fleet/extra/minivan-cap3/` (large 4/5 +
  Doblo 1/3 cap 3). Typed fleets enumerate both types together (quota and minimised type do not
  enter enumeration; they are SP-model constraints).
- Caps during the measurement: column cap 2 000 000, **no label cap** (the measurement fixes the
  label cap), wall-clock safety limit 600 s.

Findings:

- All 684 enumerations completed; no cap fired.
- Largest wave everywhere: 2026-10-05 08:45 pickup, 20 legs (20 distinct locations, 5 Sw / 15 So):
  labels 4 207 / 15 355 / 42 644 / 171 053 at R = 50 / 60 / 70 / 90 (identical for the three
  fleets, because the large type admits every label any other type admits); columns at R = 90:
  45 170 (single), 47 027 (large+sedan), 46 333 (large+Doblo cap3). About 1 s at R = 90.
- Label cap: 5 000 000 (about 29x the measured maximum), approved by the owner 2026-10-15 (DECISION_LOG E02).
  Basis (independent reviewer, 2026-10-15): on the R = 90, 20-leg wave `tracemalloc` peaked at
  44 MB, about 257 bytes per label; on a synthetic 22-location instance the 5 000 000 cap fired
  deterministically at 5 000 001 labels after 22.5-36.5 s, with a peak working set of 949 MB.

Caveats: a single snapshot week; timings depend on the machine and are not used for any decision
(the model choice depends on count caps only).
