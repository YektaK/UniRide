# UniRide Active Roadmap

**Authoritative planning snapshot:** 2026-08-10
**Verified base:** `0b4bef6e77d4eda2812cbe773296978862c25599`
**Last verified code-bearing commit:** `ddd85e8b1cc5ed64a8163988b2e179a08c8cfd2f`

This is the current priority order. Detailed agent handoffs, gates, and model preferences live in [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md).

## Release policy

UniRide remains experimental. No routing result is production-certified until universal hard-feasibility enforcement, general compute protection, bounded execution, durable jobs, matrix provenance, and operational geometry are implemented and verified. A test/build pass, warning waiver, or audit-debt disposition is not remediation.

## Verified completed, scoped work

The following are closed only to the tested scope recorded in [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md):

- occurrence identity on covered production paths;
- split-decoder repair and missing-directed-arc failure behavior;
- canonical Bildiri extraction and active-import boundary;
- matrix repository/integrity contracts and cache-health hardening;
- seed `0` and PSO deterministic seed repair;
- canonical pytest discovery;
- optional-solver null-safe API enumeration;
- deferred Supabase construction and credential-free build;
- authenticated admin route-test BFF path;
- removal of five unused direct root dependency edges.

The 2026-08-10 immutable verification reported 1,676 passing canonical Python tests, 17 passing Vitest files / 37 tests, passing TypeScript and credential-free build, and ESLint at 0 errors / 158 warnings. `npm audit --omit=dev --json` reports 84 unresolved findings (2 critical, 22 high, 59 moderate, 1 low).

## Priority 1 — Universal production feasibility

**Goal:** A hard-constraint violation can never be returned as a successful `/optimize` or `/compare` result.

- Make one solver-independent final feasibility certificate mandatory at production response boundaries.
- Cover occurrence coverage, depot closure/continuity, capacity, duration, time windows, and matrix completeness.
- Define explicit failure/diagnostic response semantics.
- Compare representative strategies against exact/reference outcomes on small instances.

Exit only when every production strategy and compare path receives the same certificate and mutation tests prove success cannot survive a hard violation.

## Priority 2 — Compute protection, typed budgets, and compare semantics

**Goal:** Make compute admission explicit, authenticated, bounded, and interpretable.

- Apply a common service-authentication/authorization boundary to general compute paths.
- Replace unbounded/free-form request policy with typed bounds for students, vehicles, algorithms, repetitions, iterations, workers, and time.
- Deduplicate aliases, use request-scoped executors, and enforce a worker ceiling.
- Redesign `/compare` ranking so feasibility and policy are explicit rather than accidental.

## Priority 3 — Durable jobs and cancellation

**Goal:** Replace process-local daemon-job behavior with durable, observable execution.

- Atomic admission and idempotent run IDs.
- Persisted state, owner, heartbeat, progress, failure, result location, and termination reason.
- Cooperative cancellation wired into every long-running loop.
- Restart/multi-worker safety and a bounded result-retention policy.

## Priority 4 — Frontend BFF, state, and warning reduction

**Goal:** Move remaining browser-compute workflows behind authenticated same-origin boundaries and make long-running state reliable.

- Remove remaining direct browser optimizer paths.
- Consolidate polling/state with cancellation, timeout, retry, backoff, and terminal-state protection.
- Preserve backend-effective direction and feasibility in persistence/UI.
- Reduce the 158 lint warnings without using broad suppressions.

## Priority 5 — Matrix provenance and metric separation

**Goal:** Prevent silent substitution of production travel-time estimates and academic metrics.

- Add versioned provenance, units, directionality, source, timestamp, identity mapping, and content hash.
- Require adapter-level metric-domain selection.
- Preserve fail-closed invalid-arc behavior while separating production and academic records.

## Priority 6 — Academic validation campaign

**Goal:** Produce defensible TSP, directed ATSP, and CVRP evidence before solver promotion or paper claims.

- Version instance/dataset manifests and synthetic constraints.
- Use declared fixed evaluation budgets as primary evidence and separately label native termination.
- Publish paired seeds, environment/manifests, warm-up, evaluation count, feasibility, cost, runtime distribution, and statistical methods.
- Use held-out families and reference baselines; no pilot/smoke run may become a superiority claim.

## Priority 7 — Backend geometry contract, then GIS

**Goal:** Build mapping only after backend route geometry is authoritative.

- Establish one location catalog and a backend geometry contract (GeoJSON or encoded polyline) with direction/staleness semantics.
- Threat-model/select a map provider and update CSP deliberately.
- Then implement a GIS renderer with memoized derived layers, stable handlers, and route/stop state tests.

There is no current GIS renderer; map rendering is not a prerequisite that can be assumed complete.

## Explicit debt, not completed work

- **Security audit:** 84 npm production dependency findings remain; 2 are critical.
- **Lint:** 158 warnings remain despite 0 errors.
- **Build:** credential-free `npm run build` passed, but it does not validate runtime credentials, authorization, or dependency security.
- **Research evidence:** passing solver tests do not establish TSP/ATSP/CVRP superiority or broad production feasibility.

## Working discipline

Use isolated worktrees from clean `origin/WIP`, create one bounded package per branch, preserve dirty/rescue checkouts, and do not merge/push without review and explicit authorization. External-agent results are proposals until independently checked against live code, diffs, and exact test output.
