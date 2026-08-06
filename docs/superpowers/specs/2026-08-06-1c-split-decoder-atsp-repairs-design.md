# 1C — Split-Decoder / ATSP Repairs + Feasibility-Certificate Wiring (design)

Status: PROPOSED
Date: 2026-08-06
Package: phase1 item 1C (one serial workstream, evidence-gated)
Branch: `codex/phase1-1c-split-decoder-20260806` (from origin/WIP)
Owner: coordinator-package 1C

## Why (evidence)

The 2026-08-06 jury/roadmap conformance review (§6 senior-dev advice, items 1C/1D)
and the phase-0 audit agree on five concrete decoder defects that silently
accept invalid routes:

1. **Missing directed arcs are fabricated, not rejected.** `LinearSplitDecoder._get_distance`
   (`uniride_core/algorithms/linear_split_decoder.py:60-61`) defaults any absent
   arc to `15.0` minutes. `SplitDecoder._get_dist` (`string_split_decoder.py:197-211`)
   falls back to `DEFAULT_TRAVEL_FALLBACK_MINUTES` (15.0) after a symmetric reverse
   lookup. `CVRPTWDecoder.is_feasible` (`cvrptw_decoder.py:100-102`) treats a missing
   arc as **0.0** (worse). Result: an incomplete ATSP matrix silently produces
   plausible-looking but fabricated routes instead of a rejection.
2. **Strict vs soft time-window modes are conflated.** `LinearSplitDecoder` folds
   duration excess into `time_warp_mins` and charges it at the TW penalty rate
   (lines 130-136), so a duration violation is indistinguishable from a TW
   violation. There is no strict (reject) TW mode on the stable `SplitDecoder`.
3. **Pickup prefixes are not enumerated.** `_build_trips_with_tw` PICKUP branch
   (`string_split_decoder.py:293-341`) appends only ONE trip per start index
   (the maximal capacity-feasible prefix ending at `trip_end`), so intermediate
   capacity-feasible prefixes can never be chosen by the DP. DROPOFF emits every
   prefix; PICKUP does not.
4. **Depot-revisit predecessor handling is wrong.** `decode` slices
   `giant_tour[prev:current]` without stripping an interior depot, so a tour that
   revisits the depot produces routes with the depot as an interior stop.
5. **The feasibility certificate is orphaned.** `uniride_core/algorithms/feasibility_certificate.py`
   (1B deliverable) has zero callers; nothing attaches `is_feasible`/violations to
   strategy or runner outputs, so the "invalid routes rejected consistently" gate
   is not yet real.

## Scope (this package only)

Files to modify:

- `uniride_core/algorithms/linear_split_decoder.py` (Tasks A, B, C, D)
- `uniride_core/algorithms/string_split_decoder.py` (Tasks A, B, C, D)
- `uniride_core/algorithms/cvrptw_decoder.py` (Task A: `is_feasible` missing-arc)
- `optimizer_api/benchmark_runner.py` (Task E: attach certificate to ExperimentResult)
- NEW `optimizer_api/verification/response_certifier.py` (Task E: response → int-route
  certificate, coords-built matrix)
- Tests: NEW `uniride_core/tests/test_split_decoder_atsp_strict.py`,
  NEW `optimizer_api/tests/test_response_certifier.py`; extend nothing that asserts
  the old fabricating behavior unless it now asserts the strict contract.
- Docs: `docs/superpowers/specs/2026-08-06-1c-split-decoder-atsp-repairs-design.md`
  (this file), `docs/superpowers/plans/2026-08-06-1c-split-decoder-atsp-repairs.md`,
  `ACTIVE_ROADMAP.md` (mark 1A/1B done, 1C in progress).

Explicitly OUT of scope (tracked separately): seed/objective consistency (1D),
web-proxy key forwarding, auth on `routers/optimization.py` (phase 2), TSPLIB
parser matrix completeness changes.

## Design

### Task A — reject missing directed arcs (strict contract)

Principle: a missing arc is data corruption, not a soft constraint. Neither
decoder may invent travel time for a missing directed arc.

- `LinearSplitDecoder` gains `is_asymmetric: bool = False` (constructor).
  `_get_distance`:
  - symmetric mode: reverse lookup allowed; if both directions absent →
    `math.inf` (trip never selected by the DP; `inf` cannot beat a finite
    objective, so no propagation).
  - asymmetric mode: only `matrix[fr][to]`; absent → `math.inf`.
  - `math.inf` is chosen over raising so GA/meta pipelines (which call decode in
    hot loops) degrade to "this prefix is unusable" instead of crashing.
- `SplitDecoder._get_dist`: same rule — reverse lookup only when
  `not self.is_asymmetric`; absent in all cases → `math.inf`.
- `CVRPTWDecoder.is_feasible`: missing arc → `(False, "missing arc ...")` instead
  of 0.0.
- Regression: incomplete ATSP matrix (a directed arc absent) → decode returns
  `total_cost = inf` / empty routes / `error` — never a route using a 15-minute
  fabrication. Complete matrix with same topology → normal result.

### Task B — separate strict and soft time-window modes

- `SplitDecoder` gains `strict_time_windows: bool = False`.
  - soft (default, backward compatible): current lexicographic
    (violations then cost) behavior.
  - strict: any prefix whose trip has `time_window_violations > 0` is not added
    to the DP graph; `decode` may return infeasible when no strict-feasible split
    exists.
- `LinearSplitDecoder`: `PenaltyConfig.allow_time_warp` already implements
  soft/strict; document it and add a regression pinning both modes:
  - soft: violating trip accepted with `time_warp_mins > 0`;
  - strict (`allow_time_warp=False`): violating prefix breaks (trip never emitted).
- Both modes keep capacity handling unchanged.

### Task C — enumerate every capacity-feasible pickup prefix; separate violation kinds

- `_build_trips_with_tw` PICKUP branch: after computing `trip_end` (max
  capacity-feasible extent), append a Trip for EVERY prefix `i..k` for
  `k in range(i, trip_end + 1)` with its own backward-scheduled departure and
  per-prefix `time_window_violations` (recompute LOOP 2 per k). This makes PICKUP
  symmetric with DROPOFF; the DP then chooses any capacity-feasible prefix.
- `LinearSplitResult` gains `duration_excess_minutes: float = 0.0` and its
  schedule entries gain `duration_excess`; `PenaltyConfig` gains
  `duration_penalty_rate: float = 10.0`. Duration excess is tracked and charged
  at its own rate — never mixed into `time_warp_mins`/`tw_penalty` (fixes the
  conflation at linear_split_decoder.py:130-136).
- Regressions: PICKUP with capacity 2 over tour [A,B,C] (A,B fit one vehicle)
  yields trips for both [A,B] and [A]; a route with duration > max in soft mode
  reports `duration_excess_minutes > 0` and `time_window_violations == 0` when
  no TW is violated (and vice versa).

### Task D — depot-revisit predecessor handling + directed regression

- `decode` (both decoders): strip the depot from the giant tour at entry,
  matching `optimal_split_result` (`split_decoder.py:78`). Interior depot
  occurrences are dropped; predecessor indexes are computed on the stripped
  tour so a route can never contain the depot as an interior stop.
- Regression: directed (asymmetric) matrix, giant tour `[A, DEPOT, B]` →
  routes `[[A, B]]` (depot stripped), no interior depot, cost uses directed
  arcs `DEPOT→A`, `A→B`, `B→DEPOT`.

### Task E — wire the feasibility certificate into runner outputs

- NEW `optimizer_api/verification/response_certifier.py`:
  `certify_benchmark_response(problem: ProblemInstance, response) -> dict`
  - builds location→node-index map from `problem.coordinates` (depot = depot_index;
    `student_{i}`/`loc_{i}` and occurrence keys → node i);
  - rebuilds int-indexed routes from `response.routes` step locations;
  - builds a full directed matrix from coordinates via
    `tsplib_distance_by_type(problem.edge_weight_type, ...)` when
    `problem.dist_matrix` is None (deterministic, same function as
    `_compute_tsplib_tour_distance`);
  - calls `certify_problem_instance` with a `RoutingResult` carrying
    `capacity_violations`/`tw_violations` from the response and
    `success=response.success`;
  - returns JSON-safe dict `{is_feasible, violation_count, violations}`.
- `benchmark_runner._run_single_experiment`: when `response` exists, set
  `metadata["feasibility_certificate"]` from the certifier (never raises; on
  conversion failure record a `"certify_error"` entry instead of failing the run).
- Regression: small TSP problem, greedy strategy → certificate is feasible
  (all nodes covered, no duplicates, arcs finite). Incomplete ATSP matrix with
  the strict decoder → certificate reports missing-arc violations and/or
  `execution_failed`, never a clean feasible route.

## Acceptance gate

```
pytest uniride_core/tests optimizer_api/tests academic_benchmark/tests/test_atsp_integration.py
```
All existing tests stay green (no silent-behavior tests rewritten unless they
assert fabrication), new tests above pass, `git diff --check` clean.
Strategy smoke: `optimizer_api/tests/test_all_strategies_smoke.py` must pass.

## Sequence

1. Write design + plan docs (this package). 2. Task A (strict arcs + regression).
3. Task B (TW modes + regression). 4. Task C (prefix enumeration + separation).
5. Task D (depot strip + directed regression). 6. Task E (certifier + runner wiring).
7. Full regression + `ACTIVE_ROADMAP.md` update. 8. FF merge into WIP + push.

Each task lands as its own focused commit with its tests (evidence-gated, one
workstream).
