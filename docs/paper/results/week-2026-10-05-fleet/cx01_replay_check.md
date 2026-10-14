# CX-01 archive replay check

Offline replay of `uniride_core.planning.typed_day_selection.solve_day_selection` on the archived chosen routes of every labelled fleet day (one single-option menu per wave, label fixed by the archived `selectionLabel`), two ways:

- OLD: whole-minute floor(start)/ceil(end), scale 1, raw-minute cooldown (pre-fix producer, `8ab88ca:src/services/fleet-scenario-run.ts:530-548`).
- NEW: exact centi-minute endpoints, `time_scale` 100, cooldown x100 (DECISION_LOG H05).

- Script: `scripts/verify_cx01_archive_replay.py`; command: `PYTHON_DOTENV_DISABLED=1 PYTHONPATH=optimizer_api .venv-jit/Scripts/python.exe -B scripts/verify_cx01_archive_replay.py`
- Repository commit at run time: `fc0aed7aa2019cfe0590e548084077fe4d256ffb` (tracked files clean)
- ortools 9.15.6755; solver seed 20261008, 1 worker (as recorded in each manifest `selection_solver`); time limit and max_cars from each manifest
- Allow-list: `fleet (A, L1-L3)`, `extra/minivan-cap3`, `extra/L4`; refused, never read: `week-2026-10-05` (INVALID: wrong capacity 4 Sw / 10 So, superseded (X01)), `extra/minivan` (superseded: capacity 1 Sw + 3 So (DECISION_LOG H03))

| Campaign | Commit | Response files | Labelled days replayed | Unlabelled / no routes | Arcs | Non-integer arcs | Route endpoints | Non-integer endpoints | OLD vs NEW differences | Cars != archived | Time limit (s) | Cooldown (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fleet (A, L1-L3) | 8ab88ca | 80 | 31 | 49 | 10808 | 0 | 1810 | 0 | 0 | 0 | 30 | large=10, sedan=10 |
| extra/minivan-cap3 | 4200acb | 60 | 60 | 0 | 10808 | 0 | 2408 | 0 | 0 | 0 | 30 | large=10, minivan=10 |
| extra/L4 | afc7208 | 20 | 20 | 0 | 10808 | 0 | 716 | 0 | 0 | 0 | 30 | large=10, sedan=10 |
| **Total** | | 160 | 111 | 49 | 32424 | 0 | 4934 | 0 | 0 | 0 | | |

Result: no difference. Status, cars and large_peak are compared per file; `cars` is also compared with the archived `scenario.cars`. Unlabelled files are scenario A (no typed selection) and infeasible scenarios without routes. One row per replayed file is in `cx01_replay_check.csv`.
The archive holds only the chosen routes, not the full per-wave menus, so this replays the selection stage on the chosen routes; it does not re-run the GA menus.
