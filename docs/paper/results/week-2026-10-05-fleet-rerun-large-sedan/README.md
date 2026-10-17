# WP-E10 fleet re-run: large + sedan (week of 2026-10-05)

Design: [`EXACT_SOLVER_AMPL_DESIGN.md`](../../../designs/EXACT_SOLVER_AMPL_DESIGN.md) section 9 ("WP-E10 input rule and acceptance"); decisions: DECISION_LOG E01, E05. Descriptive archive of one snapshot week; single campaign run (plus the rule (e) second run of one day), single seed (42), native termination protocol; no superiority, causality or cost claim. These rows are never pooled with the historical archives (`week-2026-10-05-fleet`, `week-2026-10-05-4sw5so`), which stay untouched and are historical evidence only.

## Command

Command used (not recorded in the manifest); `<main>` is the main checkout, `<run-worktree>` a fresh detached worktree at the pin:

```text
node --env-file=<main>\optimizer_api\.env --env-file=<main>\.env.local scripts/run-fleet-rerun-session.mjs --port 8011 --log <log outside the repo> -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 --fleet-types large:4sw5so:cd10,sedan:0sw4so:cd10 --fixed-type large --minimize-type sedan --scenarios A,1,2,3 --pin-commit f29aa3d88488 --reference-manifest docs/paper/results/week-2026-10-05-fleet/run_manifest.json --out docs/paper/results/week-2026-10-05-fleet-rerun-large-sedan
```

The run was made according to the procedure in `docs/designs/WP_E10_RUN_README_TEMPLATE.md` (the manifest evidences the pin, a clean tree and `python_provenance`). The manifest records: pinned commit `f29aa3d88488`, `dirty_working_tree: false`, GA seed 42, CP-SAT 9.15.6755 (`random_seed` 20261008, `num_workers` 1), selection time limit 30 s, node budget 200000, `admission_mode: assume_confirmed`, and `python_provenance` (repo-relative: `uniride_core/__init__.py`, `optimizer_api/__init__.py`, `academic_benchmark/__init__.py`). Fleet types and grid equal the historical manifest `docs/paper/results/week-2026-10-05-fleet/run_manifest.json`.

## Run facts (from `run_manifest.json`)

- State `completed`, `run_kind: campaign`; 20 (date, R) cells, all `ready`; 80 scenario rows.
- `timestamp` 2026-10-17T04:38:53.833Z, `completed_at` 2026-10-17T04:43:38.418Z (UTC); duration 4 min 45 s.
- `optimizer_policy.responses_checked`: 1004 `/optimize` responses checked; `limits_identical: true`.
- `rate_limit_waits` and `optimizer_http_failures` are empty in every cell.
- Sub-directory `rule_e_second_run_2026-10-05/`: the rule (e) second run (not a campaign), see its own README.

## What the preflight proves, and what it cannot

The run refuses before any solve unless the live inputs equal the historical campaign; the manifest `preflight` holds one entry per check, and all 14 are `ok` (`clean_tree`, `pinned_commit`, `fleet_types`, `grid`, `admission_mode`, `node_budget`, `selection_time_limit`, `ga_configuration`, `hf_configuration`, `seeds`, `selection_solver`, `matrix_sha256`, `occurrence_ids`, `reference_matches_design`). All five live matrices declare sha256 `bfb2dd85...`; 57 waves and 226 legs equal the archive. The occurrence check has an exact limit, also recorded in the manifest (`preflight.occurrence_check_limit`):

> The alias is <location_code>~<rank of the raw id among that day's occurrences at that location> (plan-experiments anonymizeResponse). The check detects added or removed students, a change of location, direction or anchor, a rank shift, and a change of the Sw/So count of a wave. It cannot detect a different student at the same location and rank; rule (d) (base routes equal to the 4sw5so routes) is the backstop.

By design (template, E05) the same composition check also runs on every cell at capture time; after the run `scripts/verify_fleet_rerun.py` repeats it (`verification.txt`, `failures: []`).

## Failure behaviour

Specified behaviour (template, E05); this run demonstrates only the completed-manifest conditions in the last sentence.

- The extended archive (`<date>_R<R>.menu_options.json`, `<date>_R<R>_L<n>.selection_exchange.json`) is validated against its schema before it is written. A schema failure aborts the whole campaign (fail closed); the manifest is kept with `state: "failed"` and the cells written so far. Nothing is repaired or skipped.
- A changed matrix sha256, a composition difference or a non-OK optimizer answer (also a 429 that survived the retries) aborts or invalidates the run: a completed manifest requires every (date, R) cell `ready` exactly once and `optimizer_http_failures` empty in every cell. This manifest is `completed` and meets both conditions.

## Optimizer policy and rate limit

Per DECISION_LOG E05 and the template, the wrapper sets `UNIRIDE_RATE_LIMIT_WINDOW_SECONDS=1` and changes no other compute-policy variable; the manifest shows the effective values: `compute_policy` (profile `production-conservative-v1`): `rate_limit_requests` 30, `rate_limit_window_seconds` 1, `max_students` 250, `max_vehicles` 50, `max_algorithms` 6, `max_workers` 2, `deadline_seconds` 120, `solver_seconds` 60, `max_iterations` 2000, `max_population` 250, `local_search_seconds` 2. The `optimizer_policy` (same profile) is taken from every `/optimize` answer (1004 responses checked, limits identical). The limit only gates admission; GA stopping is native and requests are sequential.

## Acceptance

`verification.txt` is the verifier output for this directory (`--base f29aa3d88488`).

Command used (the arguments are not recorded in `verification.txt`):

```text
<main>\.venv-jit\Scripts\python.exe scripts/verify_fleet_rerun.py --rerun-dir docs/paper/results/week-2026-10-05-fleet-rerun-large-sedan --single-archive docs/paper/results/week-2026-10-05-4sw5so --historical-dir docs/paper/results/week-2026-10-05-fleet --double-run-dir docs/paper/results/week-2026-10-05-fleet-rerun-large-sedan/rule_e_second_run_2026-10-05 --base f29aa3d88488
```

Result: exit code 0, `failures: []`: 20 cells; 228 waves checked against 4sw5so (rule (d), base routes equal); selected-option categories `identical` 344, `both_not_ok_identical` 29, `selection_changed_h06_expected` 5; rule (e) double-run files identical 4/4; rule (g) historical archives untouched (`history_untouched: true`).

The H06 category is narrow on purpose. With both days optimal, equal cars and every archived selected option unchanged in the re-run menu, the verifier accepts a changed selection only when the total vehicle-minutes are lower and the car-minutes higher (the order change of H06: before it car-minutes ranked before total vehicle-minutes), or when both are equal (an option-index tie); every other change fails as `selection_changed_unexplained`. Limit: the verifier compares only the archived selected options; options that were never selected cannot be compared, so the new selection may use a new or changed option. H06 is then a necessary cause of the 5 changes, not proven to be the only one. `scenario_outcome_differs` is also fail-closed; none occurred.
