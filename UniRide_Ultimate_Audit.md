# UniRide Ultimate Audit

**Original audit:** 2026-07-16
**Current scoped update:** 2026-08-10
**Immutable verification base:** `0b4bef6e77d4eda2812cbe773296978862c25599`
**Last verified code-bearing commit:** `ddd85e8b1cc5ed64a8163988b2e179a08c8cfd2f`

## 1. Reality check

UniRide has a credible dual-engine direction: a production student-transport application and an academic routing laboratory share algorithms through `uniride_core`. That structure is useful only when the core stays neutral and both engines retain their own evidence and lifecycle contracts.

The project is **not production-ready**. Multiple high-impact boundaries remain open: universal feasibility at `/optimize` and `/compare`, general compute authentication and typed budgets, durable cancellation, matrix provenance, frontend async state, dependency security, and route geometry/GIS.

The 2026-08-10 verification is a functional baseline, not a release certificate:

| Gate | Result |
| --- | --- |
| Canonical Python suites | 1,676 passed, 48 warnings, 238.17s |
| Frontend Vitest | 17 files / 37 tests passed, 2.83s |
| TypeScript | passed |
| ESLint | 0 errors, 158 warnings |
| Credential-free `npm run build` | passed |
| `npm audit --omit=dev --json` | 84 unresolved findings: 2 critical, 22 high, 59 moderate, 1 low |

A nonzero audit result is security debt, not a functional-gate failure. Conversely, passing tests or a credential-free build do not resolve that debt or establish general runtime security.

## 2. Findings closed to verified scope

The following earlier findings must no longer be presented as current open defects without their scope:

- **Customer occurrence identity:** covered production paths preserve distinct customer occurrences at a shared physical location; this does not exempt future strategy adapters from the same contract.
- **Split decoder:** infeasible-state initialization, strict/soft behavior, feasible prefixes, violation accounting, depot continuity, and missing directed arcs have targeted repair coverage.
- **Bildiri canonical extraction:** active academic GWO/HHO/Numba behavior is now protected by a core/legacy boundary and archive checks. This does not validate every academic algorithm for publication.
- **Matrix repository:** the process-level `DataLoader` remains a singleton facade over an injectable repository. Timeout, cache-health, last-known-good retention, and invalid off-diagonal arc rejection are covered; the old claim that every `get_instance()` call creates a new loader is retired.
- **Deterministic seeding:** explicit seed `0` and PSO deterministic seed behavior are repaired on their tested paths. The earlier PSO wall-clock fallback claim is retired.
- **Quick fixes:** canonical pytest discovery, optional-solver API null safety, deferred Supabase client construction, the authenticated admin route-test BFF, and removal of five unused direct dependency edges are verified.

The BFF correction is limited to the admin route-test workflow; it is not general FastAPI compute authentication. The passing credential-free build replaces the earlier Supabase page-data build waiver; it is not a security waiver closure.

## 3. Critical open risks

### Universal feasibility remains incomplete

The target is one independent final certificate covering occurrence coverage, capacity, duration, time windows, depot closure/continuity, and matrix completeness. Until `/optimize` and `/compare` apply it to every production result, hard-constraint violations may retain misleading success semantics.

### General compute protection and policy remain incomplete

The API still needs a coherent service-authentication/authorization boundary for general compute, typed request budgets, alias canonicalization, worker ceilings, request-scoped executors, cancellation semantics, and explicit compare ranking. Earlier containment for selected benchmark/CLI routes does not prove these guarantees.

### Job lifecycle is not durable

Process-local/daemon-style orchestration is not a durable queue. A production design requires atomic admission, idempotent IDs, persisted owner/status/heartbeat/progress/results/failures, cooperative cancellation inside loops, and restart/multi-worker safety.

### Matrix provenance and metric separation remain incomplete

Valid-arc rejection is not enough. A cost matrix still needs declared source, domain, units, directionality, generation time, identity mapping, and content hash. Production travel-time estimates and TSPLIB/CVRPLIB metrics must remain explicit and non-substitutable.

### Frontend/GIS remains incomplete

Remaining browser compute paths, overlapping polling, cancellation/timeouts, direction/persistence consistency, and the 158 lint warnings are active work. There is **no GIS renderer** and no authoritative backend route-geometry contract; a route list is not map rendering.

### Dependency security remains open

Removing five direct dependency edges did not remove all transitive Genkit components. The current production audit has 84 findings, including 2 critical and 22 high. This requires a separate evidence-led remediation plan; audit churn must not be disguised as a test result.

## 4. Architecture judgement

The desired ownership model is sound:

```text
Production DTO -> production adapter --+
                                        +-> neutral core problem/result/validation
Academic record -> academic adapter ----+
```

The core should own neutral routing constraints, identity/matrix contracts, deterministic solver inputs, result/violation structures, and feasibility validation. Production owns users, authorization, locations, provider policy, route geometry, and operational errors. Academic tooling owns datasets, optima/gaps, DOE, seeds, environment records, statistics, and evidence publication.

The remaining architectural danger is boundary erosion: production importing academic configuration concepts, academic records leaking into core DTOs, mutable/shared executable registry instances, and unbounded request policy. These deserve explicit package-level fixes, not incidental refactors.

## 5. Historical context and design decisions

The repository accumulated two engines because operational planning and research have different success criteria. That rationale remains valid. The failure mode was allowing contracts and lifecycle assumptions to drift across the boundary.

Cluster-first and giant-tour/split pipelines were retained for different research trade-offs; neither is production-certified merely because it exists. OR-Tools, PyVRP, and VROOM are useful baselines, not claims of original solver quality. ALNS, adaptive operators, diversity control, FCM border-customer ideas, and candidate metaheuristics are research hypotheses requiring deterministic design, ablation, held-out instances, and independent feasibility evidence.

Durable academic methodology retained from earlier work is: versioned instances and synthesized constraints, fixed/paired seeds, fixed evaluation budgets as the primary protocol, separately labelled native termination, warm-up/environment/hardware records, feasibility-first reporting, held-out families, reference baselines, and appropriate paired/rank statistics. Historical percentage-improvement, “always feasible,” and unverified report claims are not current evidence.

## 6. Roadmap judgement

The dependency order is intentional:

1. universal feasibility;
2. compute authentication, typed budgets, and compare semantics;
3. durable jobs/cancellation;
4. frontend BFF/state/warning work;
5. matrix provenance and metric separation;
6. academic TSP/ATSP/CVRP validation;
7. backend geometry, then GIS rendering.

See [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md) for the concise priority list and [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md) for implementation gates and handoff prompts.

## 7. Evidence rule

Live code, diffs, and executable tests outrank documents, comments, past reviews, model confidence, archived reports, and benchmark reputation. External agent output is an unverified proposal until a local reviewer checks exact files, lines, commands, and results.
