# UniRide Ultimate Audit

**Original audit:** 2026-07-16
**Current scoped update:** 2026-08-24
**Verified base commit:** `fef5a2b537da7068b51b3b3a50c6d633a2853404`
**Verification basis:** remediation working tree derived from `fef5a2b`; evidence captured before integration

## 1. Reality check

UniRide has a credible dual-engine direction: a production student-transport application and an academic routing laboratory share algorithms through `uniride_core`. That structure is useful only when the core stays neutral and both engines retain their own evidence and lifecycle contracts.

The project is **not production-ready**. Fail-closed feasibility admission, service/tenant authentication, typed lowering-only compute limits, bounded compare orchestration, and a process-local rate window now protect the current heavy production paths. High-impact boundaries remain open: hard cancellation and process isolation, durable jobs, distributed admission/rate-limit state, matrix provenance, frontend async state, dependency security, and route geometry/GIS.

The 2026-08-24 verification is a functional baseline, not a release certificate:

| Gate | Result |
| --- | --- |
| Full Python discovery | 3,355 passed, 1 skipped, 45 warnings, 429.17s |
| Frontend Vitest | 21 files / 58 tests passed, 78.99s |
| TypeScript | passed |
| ESLint | 0 errors, 158 warnings |
| `npm run build` | passed on Next.js 16.1.6; 57 dynamic, server-rendered routes |
| `npm audit --omit=dev --json` | not refreshed; last recorded 84 findings (2 critical, 22 high, 59 moderate, 1 low) |

A nonzero audit result is security debt, not a functional-gate failure. Conversely, passing tests or a production build do not resolve that debt or establish general runtime security.

## 2. Findings closed to verified scope

The following earlier findings must no longer be presented as current open defects without their scope:

- **Customer occurrence identity:** covered production paths preserve distinct customer occurrences at a shared physical location; this does not exempt future strategy adapters from the same contract.
- **Split decoder:** infeasible-state initialization, strict/soft behavior, feasible prefixes, violation accounting, depot continuity, and missing directed arcs have targeted repair coverage.
- **Bildiri canonical extraction:** active academic GWO/HHO/Numba behavior is now protected by a core/legacy boundary and archive checks. This does not validate every academic algorithm for publication.
- **Matrix repository:** the process-level `DataLoader` remains a singleton facade over an injectable repository. Timeout, cache-health, last-known-good retention, and invalid off-diagonal arc rejection are covered; the old claim that every `get_instance()` call creates a new loader is retired.
- **Deterministic seeding:** explicit seed `0` and PSO deterministic seed behavior are repaired on their tested paths. The earlier PSO wall-clock fallback claim is retired.
- **Quick fixes:** canonical pytest discovery, optional-solver API null safety, deferred Supabase client construction, the authenticated admin route-test BFF, and removal of five unused direct dependency edges are verified.
- **Production admission:** `/optimize` and `/compare` attach the solver-independent certificate and demote unsuccessful, infeasible, uncertified, or timed-out results; requested-algorithm policy extends the same gate to the tested production surfaces.
- **Compute protection:** current heavy endpoints use service/tenant authorization, immutable lowering-only limits, canonical alias resolution, bounded compare workers, a soft response deadline, deterministic ranking, and a process-local tenant/IP rate window.
- **Validation integrity:** Vitest is restricted to the current root `src` tree; the matrix timeout fallback test owns its credential-free precondition; ignored local Bildiri artifacts were hash-preserved outside the repository before boundary re-verification.

These are scoped closures. A passing build does not prove deployment credentials, authorization policy, distributed quotas, or dependency security, and a new solver/router still requires explicit certificate and compute-policy evidence.

## 3. Critical open risks

### Feasibility is enforced on current paths, not universally certified

The independent final certificate covers occurrence identity/coverage, capacity, duration, time windows, depot closure/continuity, matrix completeness, and fail-closed error handling on the current production boundaries. The remaining risk is extension drift: every future solver, router, persistence layer, or response surface must prove that it cannot bypass this admission contract.

### Compute protection is scoped, not durable

The optimizer has service/tenant authentication, typed lowering-only budgets, alias canonicalization, worker ceilings, request-scoped strategies, deterministic ranking, and tenant-keyed rate windows. The 120-second deadline is still soft: running threads may continue. The limiter is in-memory per process. Hard cancellation, process isolation, atomic distributed admission, shared quota state, and durable execution remain open.

### Job lifecycle is not durable

Process-local/daemon-style orchestration is not a durable queue. A production design requires atomic admission, idempotent IDs, persisted owner/status/heartbeat/progress/results/failures, cooperative cancellation inside loops, and restart/multi-worker safety.

### Matrix provenance and metric separation remain incomplete

Valid-arc rejection is not enough. A cost matrix still needs declared source, domain, units, directionality, generation time, identity mapping, and content hash. Production travel-time estimates and TSPLIB/CVRPLIB metrics must remain explicit and non-substitutable.

### Frontend/GIS remains incomplete

Remaining browser compute paths, overlapping polling, cancellation/timeouts, direction/persistence consistency, and the 158 lint warnings are active work. There is **no GIS renderer** and no authoritative backend route-geometry contract; a route list is not map rendering.

### Dependency security remains open

Removing five direct dependency edges did not remove all transitive Genkit components. The last recorded production audit had 84 findings, including 2 critical and 22 high; it was not refreshed on 2026-08-24. This requires a separate evidence-led remediation plan; audit churn must not be disguised as a test result.

## 4. Architecture judgement

The desired ownership model is sound:

```text
Production DTO -> production adapter --+
                                        +-> neutral core problem/result/validation
Academic record -> academic adapter ----+
```

The core should own neutral routing constraints, identity/matrix contracts, deterministic solver inputs, result/violation structures, and feasibility validation. Production owns users, authorization, locations, provider policy, route geometry, and operational errors. Academic tooling owns datasets, optima/gaps, DOE, seeds, environment records, statistics, and evidence publication.

The remaining architectural danger is boundary erosion: production importing academic configuration concepts, academic records leaking into core DTOs, mutable/shared executable registry instances, new request surfaces bypassing policy/certification, and process-local controls being mistaken for distributed guarantees. These deserve explicit package-level fixes, not incidental refactors.

## 5. Historical context and design decisions

The repository accumulated two engines because operational planning and research have different success criteria. That rationale remains valid. The failure mode was allowing contracts and lifecycle assumptions to drift across the boundary.

Cluster-first and giant-tour/split pipelines were retained for different research trade-offs; neither is production-certified merely because it exists. OR-Tools, PyVRP, and VROOM are useful baselines, not claims of original solver quality. ALNS, adaptive operators, diversity control, FCM border-customer ideas, and candidate metaheuristics are research hypotheses requiring deterministic design, ablation, held-out instances, and independent feasibility evidence.

Durable academic methodology retained from earlier work is: versioned instances and synthesized constraints, fixed/paired seeds, fixed evaluation budgets as the primary protocol, separately labelled native termination, warm-up/environment/hardware records, feasibility-first reporting, held-out families, reference baselines, and appropriate paired/rank statistics. Historical percentage-improvement, “always feasible,” and unverified report claims are not current evidence.

## 6. Roadmap judgement

The dependency order is intentional:

1. preserve certificate/policy coverage as production surfaces evolve;
2. implement hard cancellation, process isolation, and durable jobs;
3. add distributed admission/rate-limit state where multi-instance deployment requires it;
4. complete frontend state/timeout/warning work;
5. add matrix provenance and metric separation;
6. run the academic TSP/ATSP/CVRP validation campaign;
7. define backend geometry, then build GIS rendering.

See [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md) for the concise priority list and [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md) for implementation gates and handoff prompts.

## 7. Evidence rule

Live code, diffs, and executable tests outrank documents, comments, past reviews, model confidence, archived reports, and benchmark reputation. External agent output is an unverified proposal until a local reviewer checks exact files, lines, commands, and results.
