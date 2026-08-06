# UniRide Active Roadmap

**Reset:** 2026-07-16; synchronized after live re-verification on 2026-08-01
**Source:** [UniRide_Ultimate_Audit.md](./UniRide_Ultimate_Audit.md) and the verified WIP consolidation manifest

This roadmap contains only work supported by the live audit. Older completion lists, speculative gains, and superseded review tasks have been removed.

## Release Policy

UniRide remains **experimental and not production-ready** until Phase 1 is complete. Algorithm promotion and publication are blocked until feasibility, matrix provenance, deterministic replay, and environment reproducibility gates exist.

## Phase 0: Containment and Reproducible Baseline

Target: 1-2 days.

- [ ] Restrict FastAPI to a trusted network boundary.
- [ ] Authenticate benchmark and CLI-import/preview endpoints.
- [ ] Remove arbitrary `filepath` support.
- [x] Create a clean combined Python validation environment and align compatible Pydantic packages.
- [x] Restore the frontend dependency tree with `npm ci`.
- [x] Replace obsolete `next lint` with a working ESLint gate.
- [x] Re-enable hooks, purity, undefined-name, unreachable-code, fallthrough, and unused-disable rules.
- [x] Establish WIP CI for frontend tests, typecheck, lint, Python collection, and focused solver regressions.

The toolchain gates now execute normally. The 159 lint warnings and 99 npm-audit advisories remain explicit debt accepted only for consolidation; they are not remediated.

Acceptance:

- all suites collect in a clean environment;
- lint and typecheck execute normally;
- no unauthenticated endpoint can read caller-selected files or start unbounded compute.

## Phase 1: Mathematical Correctness and Feasibility

Target: week 1. These are release blockers.

### Customer occurrence identity

- [x] Use unique customer/request IDs as solver nodes.
- [x] Map customer ID to physical location separately.
- [x] Build demand, time-window, and response maps by customer ID.
- [x] Support multiple customers at one stop without aggregation or crossover failure.

### Shared feasibility certificate

- [x] Add a solver-independent validator in `uniride_core`.
- [x] Verify coverage, depot closure, vector capacity, duration, time windows, matrix, and continuity.
- [x] Return structured violations.
- [x] Prohibit `success=True` for hard-constraint violations.
- [x] Attach the certificate to every benchmark result (`certify_benchmark_response`).

### Split-decoder repair

- [x] Initialize unreachable TW-violation DP states to infinity.
- [x] Define explicit strict (`strict_time_windows`) and soft modes.
- [x] Generate every capacity-feasible pickup prefix.
- [x] Separate TW warp, route-duration excess, and capacity overflow.
- [x] Reject missing ATSP arcs (fail closed, no 15-minute fabrication).
- [x] Split giant tours at interior depot revisits; regression proves the next directed arc begins at the depot.

### Objective and RNG consistency

- [ ] Use one objective for fitness, incumbent selection, and reporting.
- [ ] Prefer lexicographic feasibility/vehicle-count/travel-cost ordering in production.
- [ ] Correct cyclic ALNS insertion deltas.
- [ ] Preserve seed `0`.
- [ ] Replace PSO's wall-clock fallback seed with a deterministic caller/default contract and test omitted-seed plus seed-`0` replay.
- [ ] Pass request-local Python and NumPy RNGs through all stochastic components.
- [ ] Remove process-global reseeding from concurrent jobs.

Acceptance:

- regression tests cover duplicate stops, mixed disability classes, duration/TW violations, feasible short prefixes, incomplete ATSP matrices, and seed replay;
- every strategy result carries a feasibility certificate;
- small instances agree with exact/reference solvers where applicable.

## Phase 2: Matrix and Production-API Hardening

Target: weeks 2-3.

- [ ] Preserve the verified process-level singleton while extracting an injectable matrix repository with explicit lifecycle, cache-health, and test boundaries.
- [ ] Add provider timeouts, cache TTL, last-known-good behavior, and health metadata.
- [ ] Reject missing or invalid off-diagonal arcs.
- [ ] Separate production geographic travel time from academic metrics.
- [ ] Create bounded typed algorithm configurations.
- [ ] Bound students, vehicles, algorithms, problems, repetitions, workers, and iterations.
- [ ] Remove the production import of `academic_benchmark.promoted_configs`; consume a neutral, versioned promoted-configuration contract instead.
- [ ] Deduplicate compare aliases and enforce a fixed worker ceiling.
- [ ] Replace shared executable strategies with request-scoped factories.
- [ ] Make optional-solver health/listing null-safe.
- [ ] Add service authentication, authorization, rate limiting, and structured errors.

Acceptance:

- every optimization records matrix provenance;
- invalid matrices fail closed;
- load tests cannot exceed configured budgets;
- production routers contain no caller-controlled filesystem access.

## Phase 3: Durable Benchmark Execution

Target: weeks 3-5.

- [ ] Replace daemon threads with a durable queue and worker process.
- [ ] Make admission and run creation atomic.
- [ ] Enforce unique/idempotent run IDs.
- [ ] Add cooperative cancellation inside every experiment loop.
- [ ] Persist status, heartbeat, owner, progress, termination reason, results, and failures.
- [ ] Prevent stopped runs from becoming completed.
- [ ] Record code/dependency/dataset hashes, environment, seeds, parameters, warm-up, and evaluation count.
- [ ] Keep raw generated benchmark outputs uncommitted by default; publish curated reports.

Acceptance:

- jobs survive API restart;
- multiple API workers share consistent state;
- cancellation stops computation;
- concurrent jobs cannot reseed one another.

## Phase 4: Frontend State, Direction, and Security

Target: weeks 3-5.

- [ ] Route Vehicle Planning and Sandbox through authenticated wrappers.
- [ ] Preserve 401/403 responses.
- [ ] Propagate pickup/dropoff and time-window settings end to end.
- [ ] Persist the effective backend direction.
- [ ] Replace async intervals with one serialized, cancellable React Query hook.
- [ ] Add abort signals, timeouts, retry budgets, backoff, and visible errors.
- [ ] Avoid React-state mutation during render.
- [ ] Remove full user-response logs.
- [ ] Remove production `unsafe-eval` and plan nonce-based CSP.
- [ ] Eliminate browser-direct FastAPI calls.

Acceptance:

- authenticated admin flows preserve role errors;
- benchmark polls never overlap for the same run;
- saved plans match backend direction and feasibility.

## Phase 5: GIS Foundation

Target: weeks 5-7; starts after Phase 2.

- [ ] Establish one authoritative depot/location catalog.
- [ ] Remove conflicting `D.Kampus` coordinates.
- [ ] Define encoded-polyline or GeoJSON route geometry.
- [ ] Select and threat-model a map provider.
- [ ] Implement the map after the geometry contract exists.
- [ ] Memoize layer derivation and stabilize handlers.
- [ ] Add route/stop/direction/staleness UI tests.

## Phase 6: Core Unification

Target: months 2-3.

- [ ] Standardize neutral `RoutingProblem`, `CostMatrix`, `ConstraintProfile`, `RoutingResult`, and `FeasibilityCertificate`.
- [ ] Migrate production DTOs through production adapters.
- [ ] Migrate academic records through academic adapters.
- [ ] Remove TSPLIB paths, BKS/gaps, and DOE metadata from neutral core models.
- [ ] Consolidate duplicate Numba and repair implementations.
- [ ] Keep compatibility shims temporary and tested.

Acceptance:

- `uniride_core` imports neither production DTOs nor academic persistence;
- both engines execute the same solver implementations through explicit adapters.

## Phase 7: Academic Validation and Promotion

- [ ] Publish versioned instance manifests for synthesized constraints.
- [ ] Use fixed paired seeds and held-out instance families.
- [ ] Compare project baselines, ablations, classical methods, and external solvers.
- [ ] Report feasibility first, then vehicles, cost, evaluations, runtime distribution, and effect size.
- [ ] Use appropriate paired Wilcoxon/Friedman/multiple-comparison procedures.
- [ ] Promote only after replay, ablation, occurrence-safety, feasibility, and held-out gates.
- [ ] Recreate a verified Smart Benchmark manual after CLI and instrumentation repair.

## Deferred Research Backlog

These are hypotheses, not commitments:

- conventional ALNS with problem-aware destroy/repair;
- entropy-based diversity control;
- structural/resonance-guided crossover;
- operator-policy co-evolution;
- FCM border-customer transfer;
- Pareto scenario presentation after a versioned multi-objective contract.

Neural, quantum-inspired, or metaphor-heavy algorithms require independent literature review and evidence before receiving implementation priority.
