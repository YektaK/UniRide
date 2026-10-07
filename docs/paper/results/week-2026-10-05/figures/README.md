# Figures

Hand-written SVG Gantt charts (standard library only). Open `index.html` in a browser to browse all 24; hover a bar for student count, route minutes and max ride.
Colours (Okabe-Ito, colourblind safe): blue = pickup, orange = drop-off, hatched = 10-min cooldown after each route.

- `gantt_week_R<R>.svg` (4 files): Monday to Friday stacked on a shared time axis, one per ride limit R in 50, 60, 70, 90.
- `gantt_<date>_R<R>.svg` (20 files): one weekday and ride limit; rows are physical vehicles.

Daily charts:

- `gantt_2026-10-05_R50.svg`: Monday, R=50, 6 vehicles
- `gantt_2026-10-06_R50.svg`: Tuesday, R=50, 5 vehicles
- `gantt_2026-10-07_R50.svg`: Wednesday, R=50, 6 vehicles
- `gantt_2026-10-08_R50.svg`: Thursday, R=50, 5 vehicles
- `gantt_2026-10-09_R50.svg`: Friday, R=50, 6 vehicles
- `gantt_2026-10-05_R60.svg`: Monday, R=60, 5 vehicles
- `gantt_2026-10-06_R60.svg`: Tuesday, R=60, 4 vehicles
- `gantt_2026-10-07_R60.svg`: Wednesday, R=60, 6 vehicles
- `gantt_2026-10-08_R60.svg`: Thursday, R=60, 4 vehicles
- `gantt_2026-10-09_R60.svg`: Friday, R=60, 5 vehicles
- `gantt_2026-10-05_R70.svg`: Monday, R=70, 4 vehicles
- `gantt_2026-10-06_R70.svg`: Tuesday, R=70, 4 vehicles
- `gantt_2026-10-07_R70.svg`: Wednesday, R=70, 6 vehicles
- `gantt_2026-10-08_R70.svg`: Thursday, R=70, 4 vehicles
- `gantt_2026-10-09_R70.svg`: Friday, R=70, 5 vehicles
- `gantt_2026-10-05_R90.svg`: Monday, R=90, 3 vehicles
- `gantt_2026-10-06_R90.svg`: Tuesday, R=90, 3 vehicles
- `gantt_2026-10-07_R90.svg`: Wednesday, R=90, 4 vehicles
- `gantt_2026-10-08_R90.svg`: Thursday, R=90, 4 vehicles
- `gantt_2026-10-09_R90.svg`: Friday, R=90, 4 vehicles

Weekly charts:

- `gantt_week_R50.svg`: R=50
- `gantt_week_R60.svg`: R=60
- `gantt_week_R70.svg`: R=70
- `gantt_week_R90.svg`: R=90

Verification: see `../schedule_verification.md`.
