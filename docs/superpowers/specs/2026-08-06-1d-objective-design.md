# 1D-OBJECTIVE — One Objective for Fitness, Incumbent, and Reporting (design)

Status: PROPOSED
Date: 2026-08-06
Package: phase1 item 1D, second serial workstream (after 1D-RNG)
Branch: `codex/phase1-1d-objective-20260806` (from origin/WIP)
Owner: coordinator-package 1D-objective

## Why (evidence)

`ACTIVE_ROADMAP.md` "Objective and RNG consistency" requires:

1. Use one objective for fitness, incumbent selection, and reporting.
2. Prefer lexicographic feasibility/vehicle-count/travel-cost ordering in
   production.
3. Correct cyclic ALNS insertion deltas.

Evidence audit against WIP @ `200c140`:

- **(3) is already fixed.** The C3 ALNS package contributed
  `test_alns_repair_boundary_insertions_use_exact_directed_cycle_delta`
  (`academic_benchmark/tests/test_alns_c3_evidence.py:149`) and
  `repair_ops.py` now computes the one directed-cycle delta at both boundary
  positions (`pos=0` wraps to `result[-1]`, `pos=len` wraps to `result[0]`).
  Ran: **54 passed**. No code change needed; record evidence and mark the
  roadmap item done.
- **(Items 1-2) are broken in every split engine.** The objective used to
  rank candidates differs across engines and disaligned from what production
  reports:

  | Engine | Fitness / rank objective | Reported metric |
  |---|---|---|
  | `ga_split_engine.py:124` | `fitness = 1/(total_cost + 50*num_vehicles)` | `total_duration_minutes` (ga_split_strategy) |
  | `gwo_split_engine.py:131` | `fitness = 1/split_penalized_cost`, ranks by `total_cost` | duration |
  | `hho_split_engine.py:172` | `fitness = 1/split_penalized_cost`, ranks by `total_cost` | duration |
  | `pso_split_engine.py` | `split_penalized_cost = total_cost + 50*vehicles` (`meta_split_common.py:65`) | duration |

  Consequences:
  - GA and PSO reward fewer vehicles at a hard-coded `50` minutes-per-vehicle
    scalar inside the objective; GWO/HHO rank by raw `total_cost` so a
    candidate with more vehicles can beat one with fewer but slightly higher
    cost. The three families do not share one objective.
  - Production routes report `total_duration_minutes`/`total_vehicles`
    (computed from decoded routes at the strategy layer), while the engines
    ranked candidates on travel-cost/vehicle-penalty scalars — selection
    optimizes `cost(+50*v)` and reporting shows `duration`, so the reported
    route is not selected by the metric the user sees.
  - No lexicographic guarantee: feasibility → vehicle count → travel cost is
    implicit and inconsistent (`num_vehicles==0` is the only infeasibility
    handled, at `ga_split_engine.py:114`).

## Scope (this package only)

Files to modify:

- `uniride_core/algorithms/objective_rank.py` (NEW) — single lexicographic
  objective key + comparison/fitness bridge shared by all split engines.
- `uniride_core/algorithms/ga_split_engine.py` (Task A)
- `uniride_core/algorithms/gwo_split_engine.py` (Task A)
- `uniride_core/algorithms/hho_split_engine.py` (Task A)
- `uniride_core/algorithms/pso_split_engine.py` (Task A)
- `uniride_core/algorithms/meta_split_common.py` (Task A: replace
  `split_penalized_cost` in engine call sites / keep as vehicle-penalized
  scalar but route ranking through the lexicographic key)
- Tests: NEW `uniride_core/tests/test_objective_rank.py`; extend
  `uniride_core/tests/test_ga_split_engine.py` and add per-engine ranking
  tests as needed.
- Docs: this file, `docs/superpowers/plans/2026-08-06-1d-objective.md`,
  `ACTIVE_ROADMAP.md` (mark the three items done).

Explicitly OUT of scope: RNG/seed (done in 1D-RNG), ALNS delta code change
(already done in C3 — evidence only), TSPLib/matrix, API/auth, capacity/TW
decoder semantics (1C done), numpy/global-RNG (done).

## Design

### Core: lexicographic objective `(feasible, vehicles, travel_cost)`

`objective_rank.py`:

- `objective_key(result: DecodeResultLike) -> Tuple[int, int, float]`:
  - `feasible = 0` when the decode reports a usable route set
    (`num_vehicles > 0` and `total_cost < inf`), else `1` (infeasible wins
    worst).
  - `vehicles = num_vehicles`.
  - `travel_cost = total_cost`.
- `is_better(a_key, b_key) -> bool`: strict lexicographic
  `<` on the tuple — feasibility dominates vehicle count; vehicle count
  dominates travel cost. This is the **single** comparator used by every
  engine for incumbent/global-best/leader/prey updates and final reporting.
- `fitness_from_key(key, max_cost=None) -> float`: a monotone scalar for GA
  tournament/survivor sampling that *preserves* the lexicographic order.
  Convention: `1/(1 + 1000*feasible_badness + vehicles + travel_cost)`
  (feasibility dominates via `1000` multiplier; then vehicles; then cost).
  Document that GA ranking must sort by `objective_key` first and use
  `fitness_from_key` only to break order-admitting momentum in tournaments.

### Task A — one objective everywhere

Replace per-engine divergence with the shared key:

- `ga_split_engine._evaluate_individual` computes `objective_key`. Fitness
  stored on `GAIndividual` is `fitness_from_key`. `tournament_selection`,
  `diversify_population` and final incumbent **sort by `key` lexicographically
  (min), not by `fitness` scalar**.
- `gwo_split_engine`: `consistent_alpha/beta/delta` (leader updates) compare
  with `is_better`; `_to_wolf` stores `key`; pack ordering by `key`.
- `hho_split_engine`: prey/hawk updates by `is_better`.
- `pso_split_engine.global_best`: track `(key, position)` and accept a new
  global/particle best only when `is_better`; personal best likewise.
- `meta_split_common`: `split_penalized_cost` stays (used by
  uniride_core academic loaders / policy callers) but split engines now
  consume the full decode and compute `objective_key`; remove reliance on the
  `50*-per-vehicle` scalar inside PSO/GWO/HHO selection paths. Keep
  `split_penalized_cost` exported for back-compat with any tests/callers that
  pin its value.
- Behavioral regression examples that must be pinned in tests:
  - A 1-vehicle route with travel cost `X+ε` beats a 2-vehicle route with
    travel cost `X` (fuel: vehicles dominate cost — opposite of the old
    GA `+50*v` scalar when per-vehicle cost differences exceed the scalar).
  - A 2-vehicle `total_cost=100` beats any infeasible decode regardless of
    `num_vehicles=999`.
  - Reporting: engine `final`/`best` selection uses the same key as ranking;
    production routes (strategy) re-validate selection equality.

Task B — reporting-is-ranking check

`objective_rank.py` → `report_key_from_routes(routes, distance_matrix, depot)`:
computes the same travel cost used at ranking from the returned route set so
that the reported `total_duration`/`total_cost` corresponds to the selected
objective. Wire the split strategy post-processing (each strategy already
recomputes `total_duration`; option assert/`objective_key` consistency in
tests rather than changing the wire format).

### Verification gates

- New tests: lexicographic ordering dominance table (feasible > vehicles >
  cost), GA tournament/keep order by key, GWO alpha/beta by key, HHO prey by
  key, PSO global best by key; regression that evaluates the actual split
  routes produced for a known instance match the candidate ranked best under
  the key.
- Full suite green: `optimizer_api/tests`, `uniride_core/tests`, and
  `academic_benchmark/tests/test_alns_c3_evidence.py` (ALNS evidence intact).
- `git diff --check` clean.