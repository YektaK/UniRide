# WP-E11 global joint day model: implementation plan

Status: **plan for owner approval; nothing implemented.** Date: 2026-10-20, at WIP `f8aaff1b`. Design: [`docs/designs/JOINT_DAY_MODEL_DESIGN.md`](../../designs/JOINT_DAY_MODEL_DESIGN.md) (cited as "design §n"). Decision basis: DECISION_LOG E13 (EQ3 reopened), E01-E12, H01, H03, H05, H06, A04.

**Goal.** Bring the joint day model (LB0, homogeneous joint MIP, typed joint MIP for large+sedan and large+Doblò cap3) into `uniride_core`, with an independent checker in `academic_benchmark`, a separate protocol `exact_day_joint_v1`, and one clean serial campaign whose results are compared with, but never tuned toward, the Claude Science prototype.

## Global constraints (every brief repeats these, Python rules first)

- **Python on Windows.** Never open interactive Python: no bare `python`/`py`/`python3`, no `python -i`, no `python -` or heredoc. Write scripts to a `.py` file under `C:\wt\<name>` and run them with `.venv-jit\Scripts\python.exe`, `PYTHONPATH` = the item's worktree first. `-c` only for one-liners. Time-limit long commands and redirect output to files. Stop on `_pyrepl`, `getheightwidth`, `WinError 123` or a repeating traceback.
- Never `taskkill /IM`; kill only by PID of a process the agent started.
- Each item: its own worktree (`git worktree add .claude/worktrees/<name> -b <branch> WIP`), its own branch, frequent commits, red test first, the reverted fix shown to break the test in the report. Temp folders only under `C:\wt\<name>`.
- Never write, copy or delete `tsplib.db*`. Never print `.env` values, licence text or Gurobi logs.
- No AMPL, HiGHS or Gurobi solve longer than a unit test in items J1-J9; the measured runs (J10, J11) are started by the lead.
- `uniride_core` imports nothing from `academic_benchmark` or `optimizer_api` (core boundary test); `academic_benchmark/validation/day_plan.py` imports nothing from `uniride_core.exact`, `uniride_core.planning` or `optimizer_api`. No file under `src/` names a result folder (E12 note of 2026-10-19). New scripts never import `archive/` (Gate C C-01 boundary scans).
- Do not edit Gate C files (list in "Parallel safety"). Do not merge or push; the lead merges with `--no-ff` after review and tests.
- Kod hattı: the reviewer always runs; Opus for formulation, bounds, labels and accounting; Sonnet for plumbing. At most 3 DUZELT rounds per item, then the owner is asked.

## Items

Each item lists goal, files, red test first, acceptance, risk and reviewer.

### J1 Day instance, columns and intervals (pure)

- **Goal:** assemble one cell: waves of the date, complete enumerations, columns with type, multiplicities, tour, busy interval and the service-day filter (design §1.2, §2.1, §2.3); refuse the cell when any wave is not `complete`.
- **Files:** new `uniride_core/exact/day_instance.py`; `uniride_core/exact/__init__.py` (exports, no solver import); new `uniride_core/tests/test_exact_day_instance.py`.
- **Red test first:** (1) the interval of every column equals the interval `fleet_selection_request.build_selection_request` builds for the same route (`fleet_selection_request.py:134-141`) at `time_scale = 100`; (2) pickup/dropoff anchoring as `run_exact_union_day.py:173-176`, including a route outside minute 0..1440; (3) a date with one capped wave gives `not_run_enumeration_cap`; (4) per-day column totals of the archive equal the WP-E1 `enumeration_counts.csv` sums (largest day 45 302 / 47 215 / 46 571).
- **Acceptance:** all tests green; no AMPL or solver import; counts per (fleet, date, R) logged.
- **Risk:** low-medium (interval off-by-one, cooldown units).
- **Reviewer:** Opus (accounting of intervals).

### J2 Lower bounds and infeasibility certificates (pure + wave objective option)

- **Goal:** LB0 (prototype definition), LB0w, LB_L with certificate tiers 1-2, LB_S (design §3); the wave values `k_w`, `l_w`, `k_any_w`.
- **Files:** new `uniride_core/exact/day_bounds.py`; if needed, the smallest option in `uniride_core/exact/ampl_backend.py` (`solve_columns`/`solve_wave`, `:659-681`) to minimise the large type without quota and all routes on a typed enumeration (design §3.2 assumption); new `uniride_core/tests/test_exact_day_bounds.py`.
- **Red test first:** hand instances where (a) two concurrent waves each need 2 large routes and L = 3 gives tier-1 `infeasible_certified`; (b) LB0w > LB0; (c) every bound <= the brute-force day optimum on the J3 oracle set (shared fixture); (d) `k_w` equals WP-E3 `K*` on a 3-wave archive subset (AMPL test marked `requires_ampl`); (e) the Doblò floor is 0.
- **Acceptance:** bounds valid on all oracle instances; certificate carries its tier and the contributing waves.
- **Risk:** medium (a bound that is not valid would turn into a false certificate).
- **Reviewer:** Opus.

### J3 Joint model builder, MPS writer and day oracle (pure)

- **Goal:** the solver-neutral sparse MIP of design §2.4 with integer `lambda_c` and the E02 upper bounds, homogeneous and typed stages, optional duration aggregation, deterministic row and column order, canonical MPS output with sha256; brute-force day oracle for tiny days.
- **Files:** new `uniride_core/exact/day_joint.py`, new `uniride_core/exact/day_oracle.py` (tests only, like `brute_force.py`), new `uniride_core/tests/test_exact_day_joint_model.py`.
- **Red test first:** (1) two builds of one cell give byte-identical MPS; (2) aggregated and plain models give the same optimum on the oracle set (solved with a tiny pure-Python enumeration of the MIP for <= 12 integer variables, no external solver); (3) a column needed twice (E02); (4) cooldown 0 vs 10 changes the oracle optimum on a hand instance; (5) the typed model never assigns a column to the other type.
- **Acceptance:** oracle equality for both directions, homogeneous and typed (sedan and Doblò cap3 types), nonmetric revisit wave included.
- **Risk:** medium (row generation at start points, aggregation).
- **Reviewer:** Opus.

### J4 HiGHS backend and stage runner

- **Goal:** solve the J3 model with `highspy` (lazy import, pinned in `requirements-exact.txt`), stages with fixed earlier values, statuses and stop reasons mapped to exact design §4 vocabulary, `timing_dependent`, `non_lexicographic`, the runner's own `incumbent <= ceil(bound - 1e-6)` check, `backend_unavailable` without raising.
- **Files:** new `uniride_core/exact/highs_backend.py`; `requirements-exact.txt`; new `uniride_core/tests/test_exact_highs_backend.py` (marked `requires_highspy`, skipped with reason when absent, never silently).
- **Red test first:** (1) the oracle set gives the oracle tuple; (2) a time-limited fake result is labelled `feasible_with_gap` and `timing_dependent`; (3) stage 1 unproven sets `non_lexicographic` on later stages; (4) absence gives `backend_unavailable`.
- **Acceptance:** tests green with and without `highspy`; option string stored verbatim; threads 1, seed 0, gap 0 / abs gap 0.99.
- **Risk:** medium (HiGHS status codes, new dependency).
- **Reviewer:** Opus (status-to-label accounting).

### J5 Gurobi cross-check adapter (after owner Q4)

- **Goal:** solve the same MPS with Gurobi (`gurobipy` or AMPL, per Q4), same stages and labels, work limit field, log never stored.
- **Files:** new `uniride_core/exact/gurobi_day_backend.py`; tests marked `requires_gurobi`.
- **Red test first:** disagreement on a planted wrong value is reported as blocking; absence is `backend_unavailable`.
- **Acceptance:** equal tuples with HiGHS on the oracle set.
- **Risk:** medium (licence path).
- **Reviewer:** Sonnet.

### J6 Independent day-plan checker (academic_benchmark)

- **Goal:** the checker of design §5.1 (coverage, per-type capacity, arcs, tour <= T, ride <= R, anchored intervals and service day, per-type peaks in minutes and at `time_scale = 100`, minute and route sums).
- **Files:** new `academic_benchmark/validation/day_plan.py`; new `academic_benchmark/tests/test_day_plan_checker.py`; `academic_benchmark/tests/test_exact_reference_boundaries.py` (AST guard entry for the new file).
- **Red test first:** one test per violated rule on a hand plan (missing occurrence, duplicate, Sw on a sedan, Doblò total 4, missing arc, tour 151, ride R+1, peak above L, claimed S off by one, minutes off by one, a centi-grid peak that differs from the minute peak); the archived 4sw5so GA routes of one day pass and give a peak.
- **Acceptance:** standard library only; AST guard green; every rule has a failing case.
- **Risk:** low.
- **Reviewer:** Opus (it is the verification contract).

### J7 Protocol `exact_day_joint_v1` and registry entry

- **Goal:** protocol id, label and stop-reason vocabulary, manifest schema and `validate_day_joint_manifest`; a fourth pooling group in the registry (not rankable, no statistics).
- **Files:** `academic_benchmark/exact_reference/protocol.py`; `academic_benchmark/protocol_registry.py`; `academic_benchmark/tests/test_exact_reference_protocol.py`; `academic_benchmark/tests/test_protocol_registry_pooling.py`.
- **Red test first:** pooling a joint row with a `union_day_v1` row or an `exact_reference_v1` row raises; a manifest with an absolute path, an e-mail, licence text or a missing `run_history` is refused.
- **Acceptance:** existing registry and protocol tests unchanged and green.
- **Risk:** low (but see "Parallel safety": the only item next to Gate C territory).
- **Reviewer:** Sonnet.

### J8 Co-optimal regression test

- **Goal:** design §5.4: the 7 (wave, R) rows with a different grouping, as a committed fixture, and the comparison function that returns `co_optimal_alternative` on equal (K, D).
- **Files:** new `academic_benchmark/tests/fixtures/coopt_waves_2026-10-19.json` (prototype route sets copied with provenance: branch `docs/science-review-2026-10`, commit `74f28f5e`, source path, source sha256; WP-E3 route sets from `wp-e3-goal1-single/exact_routes.json`); new `academic_benchmark/tests/test_coopt_alternative_route_sets.py`; the comparison function in new `academic_benchmark/exact_reference/day_compare.py`.
- **Red test first:** a fixture row with one minute more must give `mismatch`.
- **Acceptance:** 7 of 7 rows: both sets pass the J6 checker at wave level, both recompute to the committed (K*, D*), category `co_optimal_alternative`.
- **Risk:** low. **Depends on:** J6.
- **Reviewer:** Sonnet.

### J9a Runner plumbing

- **Goal:** `scripts/run_exact_day_joint.py`: offline; reads archives through `scripts/exact_archive_loader.py`; runs J1-J5 per cell; certifies every wave's routes (`uniride_core/exact/certification.py`); runs the J6 checker; typed cells through `scripts/verify-typed-selection.ts` (as `run_exact_union_day.py:69, 411`), homogeneous only if the CLI accepts a single type (report either way); writes the files of design §6.1; E04 output rule; E06 `run_history`, stop on solver failure; `python_provenance`.
- **Files:** new `scripts/run_exact_day_joint.py`; new `uniride_core/tests/test_exact_day_joint_runner.py` (subset run with a fake backend; CSV schema; manifest validation with J7; out-dir refusal; dirty-tree flag).
- **Red test first:** an unsafe `--out` exits 2 before any work; a failing checker makes the cell `rejected`.
- **Acceptance:** a 2-cell subset run with the fake backend writes valid files; the real backend is not called in tests.
- **Risk:** medium (size of the runner). **Depends on:** J1-J4, J6, J7.
- **Reviewer:** Sonnet.

### J9b Labels, comparisons and reproduction categories

- **Goal:** pure functions for the cell label (design §4.3), the bound used and its source, the blocking checks of design §5.3 (joint <= union-menu cars where both proven; joint K <= peaks of the archived GA routes and of the WP-E3 routes; values never below a valid bound), and the reproduction categories with the disagreement rule of design §6.3.
- **Files:** new `uniride_core/exact/day_labels.py` (labels, pure) and `academic_benchmark/exact_reference/day_compare.py` (extended from J8); tests next to them.
- **Red test first:** a prototype plan that passes the checker and beats a production `optimal` value raises a blocking defect; production better than a prototype "optimal" is `production_better`, not blocking.
- **Acceptance:** every label and category has a test.
- **Risk:** medium (claim wording). **Depends on:** J2, J8.
- **Reviewer:** Opus.

### J10 Calibration subset run (lead runs)

- **Goal:** measure model sizes, runtimes and Gurobi work units on 5 cells per fleet including 2026-10-05 R = 70 and R = 90; solve each twice for determinism; propose the Gurobi work limit; find where 600 s per call stops proving.
- **Files:** `docs/paper/results/week-2026-10-05-exact/wp-e11-calibration/` (README, manifest, CSV).
- **Acceptance:** identical repeat results; a work-limit proposal for the owner (E03 practice); a list of cells expected to stay open.
- **Risk:** medium (open cells may need a decision on limits, Q3).
- **Reviewer:** Sonnet (results check).

### J11 Clean serial campaign (lead runs)

- **Goal:** all 140 cells (20 homogeneous, 60 large+sedan, 60 large+Doblò cap3) in one clean serial run per E06, results in `docs/paper/results/week-2026-10-05-exact/wp-e11-joint-day/`.
- **Acceptance:** every blocking check of design §5.3 holds; every plan passes the checker; `reproduction_check.csv` filled; two solvers agree where Q5 requires it.
- **Risk:** medium-high (runtime; disagreement with the prototype must be reported, not tuned away).
- **Reviewer:** Opus, with an independent recomputation of the labels and of a sample of plans.

### J12 Records

- **Goal:** WP-E11 status paragraph in the exact design §9 and in the new design; DECISION_LOG entry for the owner decisions on this plan (E14) and for any run decisions; results README; memory update by the lead.
- **Files:** `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md`, `docs/designs/JOINT_DAY_MODEL_DESIGN.md`, `docs/DECISION_LOG.md`.
- **Reviewer:** Sonnet.

## Order

```text
J0 owner approval of design + plan (DECISION_LOG E14)
 ├─ J1 ──┬─ J2 ─────────────┐
 │       └─ J3 ── J4 ── J5 ─┤
 ├─ J6 ── J8 ───────────────┤
 └─ J7 ─────────────────────┴─ J9a + J9b ── J10 ── (owner: limits if needed) ── J11 ── J12
```

- J1, J6 and J7 can start at once, in parallel (separate new files).
- J2 and J3 need J1's column contract; J4 needs J3; J5 waits for Q4.
- J8 needs J6. J9a/J9b need J2-J4, J6-J8.
- J10 before J11; J11 starts only after every earlier item is merged and the owner has answered Q2-Q5.
- Licence window: if Q4 keeps AMPL for the Gurobi cross-check, J10 and J11 must finish before 2026-11-05 (DECISION_LOG E09) or wait for a renewal.

## Parallel safety against Gate C

Gate C (plan `docs/superpowers/plans/2026-10-19-gate-c-catalog-composition-experiment-services.md`, A17) edits `academic_benchmark/core/*` (`registry_setup.py`, `execution_gateway.py`), `academic_benchmark/fairness.py`, `academic_benchmark/studies/*`, `academic_benchmark/engine_core.py`, `academic_benchmark/smart_benchmark.py`, `academic_benchmark/datasets/*`, `academic_benchmark/schemas/study-v1.schema.json`, files under `uniride_core/algorithms/` (among them `capabilities.py`, `composition.py`, `objective_budget.py`, the GA/PSO/GWO solvers and `engine_factory.py`), `scripts/run_exact_tsp_reference.py`, and the tests named in its items (file list read from the plan text on 2026-10-20).

| WP-E11 item | Files | Collision with Gate C |
|---|---|---|
| J1-J5, J9b core part | new files in `uniride_core/exact/`; `uniride_core/exact/__init__.py`; `requirements-exact.txt`; possibly `ampl_backend.py` (J2) | none |
| J6 | new `academic_benchmark/validation/day_plan.py`; `test_exact_reference_boundaries.py` | none listed |
| J7 | `academic_benchmark/exact_reference/protocol.py`, `academic_benchmark/protocol_registry.py` and their tests | **adjacent, not listed:** the Gate C plan cites the registry only as status evidence (its §1.1 table, D6) and no Gate C item edits these files; Package D (after Gate C) will call `assert_single_pooling_group`. Mitigation: J7 is a small separate branch, rebased on WIP right before merge, and the lead checks open Gate C branches for these two files first |
| J8, J9b compare | new files under `academic_benchmark/exact_reference/` and `academic_benchmark/tests/` | none |
| J9a | new `scripts/run_exact_day_joint.py` | must pass the Gate C C-01 boundary scans of `scripts/` (no `archive` import) |
| J12 | `docs/DECISION_LOG.md`, design docs | shared documentation; append-only entries, merge conflicts are text-only |

No WP-E11 item touches `capabilities.py`, `academic_benchmark/core`, `fairness.py` or `studies/`.

## Owner questions

| # | Question | Options | Recommendation |
|---|---|---|---|
| Q1 | When does Doblò cap3 run? (E13 already puts it in scope) | (a) in the same campaign J11; (b) after large+sedan has been reproduced | **(a)**: same code path; the README states that Doblò has no external reproduction target and is checked only by the checker, the TS CLI and the joint <= union-menu rule |
| Q2 | Tie-break order (design §1.3) | Homogeneous: (a) K, total vehicle-minutes; (b) K, routes, minutes (prototype). Typed: (a) S, total minutes, car minutes (H06 without the option index); (b) S, total minutes (prototype) | **(a) for both**: consistent with H06; fleet targets are unaffected; minute targets are then compared as "<= prototype" only |
| Q3 | Time and work limits | (a) 600 s per solver call (every day contains its date's peak wave, D-B/D-C), Gurobi work limit from J10; (b) a longer limit for open cells as a separately labelled sensitivity run | **(a)**; (b) only on request after J10, never pooled with (a) |
| Q4 | Solver access | (a) HiGHS via `highspy` (new pinned dependency, no licence) primary; Gurobi via `gurobipy` on the same MPS if the owner's licence covers it, else via AMPL until 2026-11-05; (b) both through AMPL (reuses `ampl_backend`, blocked after the AMPL licence ends unless renewed); (c) CP-SAT primary (already installed) | **(a)**; the owner confirms which product the Gurobi licence to about 2027-10 covers |
| Q5 | Is the Gurobi cross-check required? | (a) required for every `optimal` and every `infeasible_solver_proven` cell used in a paper table; (b) optional, rows marked `crosscheck: not_run` | **(a)** for the paper campaign; optional for development runs |
| Q6 | GA-side comparison at day level | (a) descriptive only, with existing GA sources (WP-E4b GA-menu cars, the peaks of the archived GA routes); (b) a new GA day-level heuristic | **(a)**; (b) would be a new heuristic, outside WP-E11 |
| Q7 | Bounds beyond the prototype's LB0 | (a) add LB0w and LB_S, reported separately; (b) LB0 only | **(a)**: both are valid by construction and may close open cells without longer limits |
| Q8 | Solver-proven infeasibility without a certificate | (a) accept `infeasible_solver_proven` with two-solver agreement and the wording "infeasible, solver-proven"; (b) add an item for an LP Farkas certificate checked in exact rational arithmetic | **(a)** now; decide (b) after J2 reports how many prototype-infeasible cells the tier-1/2 certificate explains |

## Out of scope

- A compact or branch-and-price day model (E11); municipal-scale data.
- New GA runs, multi-seed GA (EQ5), other weeks.
- Any change to production day selection (`typed_day_selection.py`) or to `/optimize`; the exact path stays out of `optimizer_api` (exact design §2).
- Paper text (writing line, after J11).

## Confirmed facts vs assumptions

- **Confirmed (source, 2026-10-20):** interval, peak and objective rules (`uniride_core/planning/typed_day_selection.py:11-22, 87-97, 150-205`); centi grid (`uniride_core/planning/fleet_selection_request.py:29-32, 83-88, 134-141`); anchoring and service day (`scripts/run_exact_union_day.py:68, 173-176`); columns (`uniride_core/exact/route_enumeration.py:73-80, 247-264`); backend limits (`uniride_core/exact/ampl_backend.py:41-53`); protocol and registry (`academic_benchmark/exact_reference/protocol.py:25, 243-253`; `academic_benchmark/protocol_registry.py:1-18, 96-104`); per-day column totals (`wp-e1-enumeration/enumeration_counts.csv`); installed packages in `.venv-jit` (no `scipy`, `highspy`, `gurobipy`); Gate C file list (plan text).
- **Prototype data, not verified:** all reproduction targets (design §6.3) and the prototype runtimes (design §2.5).
- **Assumptions to be checked:** production runtimes and the open-cell count (J10); wave objective options in `solve_wave` (J2); single-type input of the TS CLI (J9a); the Gurobi licence path (Q4).
