# UniRide Active Roadmap

**Authoritative planning snapshot:** 2026-08-24
**Verified base commit:** `fef5a2b537da7068b51b3b3a50c6d633a2853404`
**Verification basis:** remediation working tree derived from `fef5a2b`; evidence captured before integration

This is the current priority order. Detailed agent handoffs, gates, and model preferences live in [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md).

## Release policy

UniRide remains experimental. Current heavy production paths have fail-closed feasibility admission, bounded compute policy, tenant authorization, and a process-local rate window; those controls are scoped closures, not a production certificate. Durable jobs, hard cancellation/process isolation, distributed admission/rate-limit state, matrix provenance, and operational geometry remain mandatory. A test/build pass, warning waiver, or audit-debt disposition is not remediation.

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
- removal of five unused direct root dependency edges;
- production compute authentication on the three heavy endpoints (internal-key boundary; startup error when auth is disabled in production);
- immutable, lowering-only `production-conservative-v1` compute profile with nine typed overrides;
- canonical alias resolution with fail-closed registry drift handling and fresh request-scoped instances;
- request-local compute budgets and capped native solver runtimes;
- bounded `/compare` execution (at most 2 workers, one 120-second soft response deadline, six canonical defaults, certificate-gated deterministic ranking);
- exact/permutation fail-fast rejection above ten waypoints;
- server-only Next.js optimizer transport with a browser boundary test;
- fail-closed tenant configuration (trimmed/non-reserved IDs, unique nonblank secrets, and no ops-key reuse);
- root-only Vitest discovery and environment-independent matrix repository tests.

The 2026-08-24 remediation branch passed full Python discovery with **3,355 passed, 1 skipped, 45 warnings in 429.17s**. Frontend Vitest passed **21 files / 58 tests in 78.99s** after excluding nested worktree copies; TypeScript passed; ESLint remained **0 errors / 158 warnings** under the temporary waiver; and the Next.js 16.1.6 production build passed with **57 dynamic, server-rendered routes**. The npm security audit was not rerun; its last recorded baseline remains **84 findings: 2 critical, 22 high, 59 moderate, 1 low**.

## Priority 1 — Feasibility governance and extension

**Status: implemented on current heavy production paths.** A result is successful only when solver-successful **and** `feasibility_certificate.is_feasible`; failed/infeasible/uncertified/timed-out results are never ranked. The remaining action is governance: every future solver, router, persistence, or response surface must prove the same contract before exposure.

- **Requested-algorithm policy** — verified: non-default explicitly requested algorithms pass the identical mandatory certificate contract on `/optimize`, `/compare`, and `/vehicle-calculator`. CodeGraph confirms the optimization router owns the strategy invocation path and current tests include non-default `hho_split`/`gwo_split`/`pso_split`/`e2bso`/`rdma`/`paoea`/`permutation_tsp` cases plus a load-bearing demotion test. Evidence remains in `docs/REQUESTED_ALGORITHM_POLICY_VERIFICATION.md`; the 2026-08-24 full suite is 3,355 passed, 1 skipped, 0 failed.
- **Mutation proof** — implemented (`d3b19de`): 114 mutation tests across every solver surface (canonical strategies incl. OR-Tools behind `importorskip`, core CVRP engines incl. non-finite-arc instance mutations, canonical 3-opt TSP/ATSP input contracts, permutation exact path n<=10, and the academic execution-gateway RunResult contract). Each test runs a real solve, certifies the unmutated output feasible, then injects a single hard violation (missing/duplicate occurrence, capacity overflow, non-finite arc, inflated cost, identity/evaluation/budget/termination/backend tampering) and requires the final certificate or gateway to reject it. Full suite at `d3b19de`: 3,314 passed, 1 skipped, 0 failed.

## Priority 2 — Compute protection, typed budgets, and compare semantics

**Status: implemented for the scoped Package B surface** — the three heavy endpoints are internal-key authenticated, the compute profile is typed/lowering-only, aliases are deduplicated, `/compare` is bounded and deterministically ranked, and exact/permutation requests fail fast above ten waypoints. Remaining scope is tracked below:

- **Hard cancellation and process isolation** — the current 120-second deadline is a soft response deadline; running threads may continue (`wait=False` shutdown).
- **Rate limiting** — verified: the fixed-window limiter keys authenticated requests by tenant identity and falls back to client IP when a tenant identity is absent. All three heavy endpoints return HTTP 429 + `Retry-After` on exceed; `UNIRIDE_RATE_LIMIT_REQUESTS` / `UNIRIDE_RATE_LIMIT_WINDOW_SECONDS` default to 30 requests / 60 seconds. It is in-memory and process-local; shared multi-instance quota state remains open.
- **Per-tenant authorization** — verified: `UNIRIDE_TENANT_KEYS` resolves a unique secret to a tenant identity using constant-time comparison; the shared `INTERNAL_API_KEY` remains the ops override (`tenant_id="internal"`). Startup now rejects blank or untrimmed tenant IDs, the reserved `internal` ID, blank/duplicate tenant secrets, and secrets that reuse the ops key. Evidence: `optimizer_api/auth.py`, `optimizer_api/runtime_config.py`, and **16 passing tests** in `optimizer_api/tests/test_tenant_authorization.py`.

## Priority 3 — Durable jobs and cancellation

**Goal:** Replace process-local daemon-job behavior with durable, observable execution.

- Atomic admission and idempotent run IDs.
- Persisted state, owner, heartbeat, progress, failure, result location, and termination reason.
- Cooperative cancellation wired into every long-running loop.
- Restart/multi-worker safety and a bounded result-retention policy.

## Priority 4 — Frontend BFF, state, and warning reduction

**Goal:** Keep all browser-compute workflows behind authenticated same-origin boundaries and make long-running state reliable.

- Browser optimizer calls now route through server-only `optimizerFetch` (the admin route-test BFF and the compare page); audit any future/new browser compute path against this boundary.
- Keep default Vitest collection restricted to root `src/**/*.test.ts(x)`; the 2026-08-24 gate is 21 files / 58 tests, not nested worktree copies.
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

- **Security audit:** the last recorded npm production audit reported 84 findings, including 2 critical; refresh before remediation decisions.
- **Lint:** 158 warnings remain despite 0 errors.
- **Build:** the current `npm run build` passed with 57 dynamic routes; it does not validate runtime credentials, authorization, or dependency security.
- **Research evidence:** passing solver tests do not establish TSP/ATSP/CVRP superiority or broad production feasibility.

## Working discipline

Use isolated worktrees from clean `origin/WIP`, create one bounded package per branch, preserve dirty/rescue checkouts, and do not merge/push without review and explicit authorization. External-agent results are proposals until independently checked against live code, diffs, and exact test output.
