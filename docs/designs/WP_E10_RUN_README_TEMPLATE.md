# WP-E10 fleet re-run: README template for a results directory

Copy into the results directory of a re-run (`docs/paper/results/week-2026-10-05-fleet-rerun-<fleet>/`) and fill the `<...>` fields. Design: [`EXACT_SOLVER_AMPL_DESIGN.md`](EXACT_SOLVER_AMPL_DESIGN.md) section 9 ("WP-E10 input rule and acceptance"); decisions: DECISION_LOG E01, E05. Descriptive archive of one snapshot week; no superiority, causality or cost claim. These rows are never pooled with the historical archives (`week-2026-10-05-fleet`, `week-2026-10-05-4sw5so`), which stay untouched and are historical evidence only.

## Command

```text
<the exact command, with the --pin-commit, --reference-manifest and --out values>
```

Pinned commit `<sha>`, `dirty_working_tree: false`, GA seed 42, native termination, CP-SAT 9.15.6755 (`random_seed` 20261008, `num_workers` 1), selection time limit 30 s, node budget 200000, `admission_mode: assume_confirmed` (manifest fields). Fleet types and grid equal the historical manifest `<reference manifest>`.

## What the preflight proves, and what it cannot

The run refuses before any solve unless the live inputs equal the historical campaign (manifest `preflight`, one entry per check). The occurrence check has an exact limit, repeated here and in the manifest (`preflight.occurrence_check_limit`):

> The alias is <location_code>~<rank of the raw id among that day's occurrences at that location> (plan-experiments anonymizeResponse). The check detects added or removed students, a change of location, direction or anchor, a rank shift, and a change of the Sw/So count of a wave. It cannot detect a different student at the same location and rank; rule (d) (base routes equal to the 4sw5so routes) is the backstop.

The same composition check runs again on every (date, R) cell at capture time (before the cell is written) and after the run in `scripts/verify_fleet_rerun.py`.

## Failure behaviour

- The extended archive (`<date>_R<R>.menu_options.json`, `<date>_R<R>_L<n>.selection_exchange.json`) is validated against its schema before it is written. **A schema failure aborts the whole campaign** (fail closed); the manifest is kept with `state: "failed"` and the cells written so far. Nothing is repaired or skipped.
- A changed matrix sha256, a composition difference or a non-OK optimizer answer (also a 429 that survived the retries) aborts or invalidates the run: a completed manifest requires every (date, R) cell `ready` exactly once and `optimizer_http_failures` empty in every cell.

## Optimizer policy and rate limit

The session wrapper starts the optimizer with `UNIRIDE_RATE_LIMIT_WINDOW_SECONDS=1` (30 requests per second; the ceiling of 30 requests per window cannot be raised) so a sequential campaign never waits and never receives a 429. No other compute-policy variable is changed. The values are recorded in the manifest (`compute_policy` of the CLI environment, identical to the optimizer's through the wrapper, and `optimizer_policy` from every `/optimize` answer). The limit only gates admission; GA stopping is native and requests are sequential, so results do not change.

## Acceptance (run after the campaign)

```text
python scripts/verify_fleet_rerun.py --rerun-dir <this directory> --single-archive docs/paper/results/week-2026-10-05-4sw5so \
  --historical-dir <old fleet archive of the same campaign> --double-run-dir <second run of one day> --base <pinned commit>
```

Rule (d) base routes, selected-option categories (including the expected H06 category), rule (e) determinism of one full day run twice, rule (g) historical archives untouched. Result: `<pass/fail and the printed report>`.
