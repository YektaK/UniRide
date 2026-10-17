# WP-E10 fleet re-run: README template for a results directory

Copy into the results directory of a re-run (`docs/paper/results/week-2026-10-05-fleet-rerun-<fleet>/`) and fill the `<...>` fields. Design: [`EXACT_SOLVER_AMPL_DESIGN.md`](EXACT_SOLVER_AMPL_DESIGN.md) section 9 ("WP-E10 input rule and acceptance"); decisions: DECISION_LOG E01, E05. Descriptive archive of one snapshot week; no superiority, causality or cost claim. These rows are never pooled with the historical archives (`week-2026-10-05-fleet`, `week-2026-10-05-4sw5so`), which stay untouched and are historical evidence only.

## Command

```text
<the exact command, with the --pin-commit, --reference-manifest and --out values>
```

Pinned commit `<sha>`, `dirty_working_tree: false`, GA seed 42, native termination, CP-SAT 9.15.6755 (`random_seed` 20261008, `num_workers` 1), selection time limit 30 s, node budget 200000, `admission_mode: assume_confirmed` (manifest fields). Fleet types and grid equal the historical manifest `<reference manifest>`.

## Procedure: one fresh detached worktree per run

The preflight refuses a dirty tree, and the output of a run is untracked, so a second run in the same checkout is refused and committing the output would move the pin. Therefore **each run (large+sedan campaign, Doblò campaign, rule (e) second run) gets its own fresh detached worktree at the pinned commit**, and its `--out` lies inside that worktree. The pin is the merged commit that contains this code (`git rev-parse --short=12 HEAD` of the merged branch). The dirty check is never relaxed and the output directory is never excluded from it.

Use a short run-worktree path, for example `C:\wt\e10-ls` (large+sedan), `C:\wt\e10-db` (Doblò), `C:\wt\e10-e2` (second run): deep paths hit the Windows long-path limit (do not change git config for this). `<main>` is the main checkout, `<run-worktree>` the short path.

Create the worktree and the `node_modules` junction (cmd form, also valid when typed in PowerShell or Git Bash as `cmd /c ...`):

```text
git worktree add <run-worktree> <pin> --detach
cmd /c mklink /J <run-worktree>\node_modules <main>\node_modules
```

Then run from the worktree. The interpreter is set once; it serves the optimizer and the CLI. The Supabase environment arrives only through Node's `--env-file` by path (nothing is copied or printed).

PowerShell:

```text
Set-Location <run-worktree>
$env:UNIRIDE_PYTHON = "<main>\.venv-jit\Scripts\python.exe"
node --env-file=<main>\optimizer_api\.env --env-file=<main>\.env.local scripts/run-fleet-rerun-session.mjs --port 8011 --log <log outside the repo> -- <run arguments> --out <out inside this worktree>
```

Git Bash:

```text
cd <run-worktree>
export UNIRIDE_PYTHON="<main>/.venv-jit/Scripts/python.exe"
node --env-file=<main>/optimizer_api/.env --env-file=<main>/.env.local scripts/run-fleet-rerun-session.mjs --port 8011 --log <log outside the repo> -- <run arguments> --out <out inside this worktree>
```

cmd:

```text
cd /d <run-worktree>
set UNIRIDE_PYTHON=<main>\.venv-jit\Scripts\python.exe
node --env-file=<main>\optimizer_api\.env --env-file=<main>\.env.local scripts/run-fleet-rerun-session.mjs --port 8011 --log <log outside the repo> -- <run arguments> --out <out inside this worktree>
```

The session wrapper puts the run worktree first on `PYTHONPATH` (the project venv has an editable install that maps `uniride_core`, `optimizer_api` and `academic_benchmark` to the main checkout), and before it starts the optimizer it asks the same interpreter, with the same environment and working directory, where the three packages resolve; it refuses the run unless all three lie inside the run worktree. The result is written to the log and, through the CLI's Python capture, to the manifest (`python_provenance`, repo-relative).

Afterwards the results are copied (not moved by git) into a results branch of the main repository for merging; the run worktree is then removed (`cmd /c rmdir <run-worktree>\node_modules`, then `git worktree remove <run-worktree>`). Never recursive-delete a worktree that holds the junction.

A rule (e) second run is **not** a campaign: it is written with `--dates <one date> --allow-subset-dates`, its manifest says `run_kind: rule_e_second_run` and `parameters.allow_subset_dates: true`, and it contains a one-line README. Owner decision 2026-10-17: it is made for large+sedan only, in the worktree `C:\wt\e10-e2`. It is copied to `<campaign directory>/rule_e_second_run_<date>/` (never to `docs/paper/results/` as a sibling campaign), and `scripts/verify_fleet_rerun.py` refuses it as `--rerun-dir`.

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
<main>\.venv-jit\Scripts\python.exe scripts/verify_fleet_rerun.py --rerun-dir <this directory> --single-archive docs/paper/results/week-2026-10-05-4sw5so \
  --historical-dir <old fleet archive of the same campaign> --double-run-dir <this directory>/rule_e_second_run_<date> --base <pinned commit>
```

The second run is made in the worktree `C:\wt\e10-e2`; its manifest says `run_kind: rule_e_second_run`. `--base <pinned commit>` is meaningful only when the verifier runs on the results branch (a checkout whose history contains the pinned commit and the copied results); in a run worktree omit it.

Rule (d) base routes, selected-option categories, rule (e) determinism of one full day run twice, rule (g) historical archives untouched. Result: `<pass/fail and the printed report>`.

The H06 category is narrow on purpose. With both days optimal, equal cars and every archived selected option unchanged in the re-run menu, the verifier accepts a changed selection only when the total vehicle-minutes are lower and the car-minutes higher (the order change of H06: before it car-minutes ranked before total vehicle-minutes), or when both are equal (an option-index tie). Every other change is `selection_changed_unexplained` and fails. Limit: the verifier compares only the archived selected options; options that were never selected cannot be compared, so the new selection may use a new or changed option. H06 is then a necessary cause of the change, not proven to be the only one.

`scenario_outcome_differs` is also fail-closed. A failure caused only by `largeVehicles` or by the assignment's `cars` needs **manual review**, not an automatic accept: they are not in the CP-SAT objective, so a genuine H06 reorder of the selection can change them. The rule stays fail-closed; a reviewer decides, case by case, and records the decision.
