# WP-E10 fleet re-run: large + Doblo cap3 (week of 2026-10-05)

Design: [`EXACT_SOLVER_AMPL_DESIGN.md`](../../../designs/EXACT_SOLVER_AMPL_DESIGN.md) section 9 ("WP-E10 input rule and acceptance"); decisions: DECISION_LOG E01, E05. Descriptive archive of one snapshot week; no superiority, causality or cost claim. These rows are never pooled with the historical archives (`week-2026-10-05-fleet`, `week-2026-10-05-4sw5so`), which stay untouched and are historical evidence only.

## Command

Run from a fresh detached worktree at the pin (`C:\wt\e10-db`, with the `node_modules` junction), through the session wrapper, `UNIRIDE_PYTHON` set to the project `.venv-jit` interpreter, the Supabase environment passed only through Node `--env-file`:

```text
node --env-file=<main>\optimizer_api\.env --env-file=<main>\.env.local scripts/run-fleet-rerun-session.mjs --port 8011 --log <log outside the repo> -- --week-of 2026-10-05 --ride-limits 50,60,70,90 --tour-limit 150 --fleet-types large:4sw5so:cd10,minivan:1sw3so:cap3:cd10 --fixed-type large --minimize-type minivan --scenarios 0,1,2 --pin-commit f29aa3d88488 --reference-manifest docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3/run_manifest.json --out docs/paper/results/week-2026-10-05-fleet-rerun-doblo-cap3
```

Pinned commit `f29aa3d88488`, `dirty_working_tree: false`, GA seed 42, native termination, CP-SAT 9.15.6755 (`random_seed` 20261008, `num_workers` 1), selection time limit 30 s, node budget 200000, `admission_mode: assume_confirmed` (manifest fields). Fleet types and grid equal the historical manifest `docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3/run_manifest.json`.

## Run facts

- Preflight (read-only, run before the full run as a separate preflight-only run and again at the start of the full run): 14 of 14 checks passed (`clean_tree`, `pinned_commit`, `fleet_types`, `grid`, `admission_mode`, `node_budget`, `selection_time_limit`, `ga_configuration`, `hf_configuration`, `seeds`, `selection_solver`, `matrix_sha256`, `occurrence_ids`, `reference_matches_design`); all five live matrices declare sha256 `bfb2dd85...`; 57 waves and 226 legs equal the archive.
- Manifest `timestamp` 2026-10-17T04:44:45Z (UTC), `completed_at` 2026-10-17T04:49:18Z; duration about 4 min 33 s. State `completed`, `run_kind: campaign`, 20 (date, R) cells all `ready`, 60 scenario rows.
- Optimizer log (kept outside the repository): 868 `POST /api/v1/optimize`, 60 `POST /api/v1/internal/fleet-selection` and 25 `POST /api/v1/internal/matrix-snapshot` calls, all answered 200; no 429, no retry; `rate_limit_waits` and `optimizer_http_failures` are empty in every cell.
- Python provenance (manifest `python_provenance`, repo-relative): `uniride_core/__init__.py`, `optimizer_api/__init__.py`, `academic_benchmark/__init__.py`.

## Acceptance

Run on the results branch (`results/wp-e10-fleet-rerun`, which contains the pinned commit and the copied results). No rule (e) second run was made for this campaign (owner decision 2026-10-17: large+sedan only), so `--double-run-dir` is not passed.

```text
<main>\.venv-jit\Scripts\python.exe scripts/verify_fleet_rerun.py --rerun-dir docs/paper/results/week-2026-10-05-fleet-rerun-doblo-cap3 --single-archive docs/paper/results/week-2026-10-05-4sw5so --historical-dir docs/paper/results/week-2026-10-05-fleet/extra/minivan-cap3 --base f29aa3d88488
```

Result: exit code 0, `failures: []`. Full printed report in `verification.txt`: 20 cells; 228 waves checked against 4sw5so (rule (d), base routes equal); selected-option categories `identical` 654, `selection_changed_h06_expected` 30; rule (g) historical archives untouched (`history_untouched: true`).

The H06 category is narrow (see `docs/designs/WP_E10_RUN_README_TEMPLATE.md`): the verifier compares only the archived selected options, so H06 is a necessary cause of those 30 selection changes, not proven to be the only one.
