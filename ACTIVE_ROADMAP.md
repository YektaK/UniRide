# UniRide Active Roadmap

**Authoritative planning snapshot:** 2026-08-14
**Verified evidence tip:** `ed54d5cebdc849fb0df2743692f0eca385a4750a`
**Last verified code-bearing commit:** `ed54d5c`

This is the current priority order. Detailed agent handoffs, gates, and model preferences live in [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md).

## Release policy

UniRide remains experimental. No routing result is production-certified until universal hard-feasibility enforcement across all solver surfaces, durable jobs, hard cancellation, rate limiting, matrix provenance, and operational geometry are implemented and verified. A test/build pass, warning waiver, or audit-debt disposition is not remediation.

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
- server-only Next.js optimizer transport with a browser boundary test.

The 2026-08-14 verification at `ed54d5c` reported **1,453 passing focused Package B Python tests, 37.37s** and **2,295 passing full affected-suite Python tests, 1 skip (Numba unavailable), 3 warnings, 167.78s**, with one remaining pre-existing `test_matrix_repository.py` Supabase SDK provider-timeout drift failure reproduced on clean `WIP`. The unchanged frontend gate remains **21 passing Vitest files / 58 tests** with passing TypeScript, ESLint at **0 errors / 158 warnings (temporary waiver)**, and a passing credential-free production build with **57 static pages**. `npm audit --omit=dev --json` exited **1** with **84 unresolved findings: 2 critical, 22 high, 59 moderate, 1 low**.

## Priority 1 — Universal production feasibility

**Status: certificate attached as the final admission gate on `/optimize` and `/compare`.** A result is successful only when solver-successful **and** `feasibility_certificate.is_feasible`; failed/infeasible/uncertified/timed-out results are never ranked. Remaining scope:

- **Requested-algorithm policy** — non-default explicit requested algorithms still need the same certificate contract.
- **Mutation proof** — mutation tests proving success cannot survive a hard violation are still pending across every solver surface.

## Priority 2 — Compute protection, typed budgets, and compare semantics

**Status: implemented for the scoped Package B surface** — the three heavy endpoints are internal-key authenticated, the compute profile is typed/lowering-only, aliases are deduplicated, `/compare` is bounded and deterministically ranked, and exact/permutation requests fail fast above ten waypoints. Remaining scope is tracked below:

- **Hard cancellation and process isolation** — the current 120-second deadline is a soft response deadline; running threads may continue (`wait=False` shutdown).
- **Rate limiting** — there is no per-tenant or per-IP request throttling.
- **Per-tenant authorization** — the boundary is gated on the shared internal key, not on tenant identity.
- **Requested-algorithm policy** — explicit non-default requested-algorithm admission still needs the same contract review as the six canonical defaults.

## Priority 3 — Durable jobs and cancellation

**Goal:** Replace process-local daemon-job behavior with durable, observable execution.

- Atomic admission and idempotent run IDs.
- Persisted state, owner, heartbeat, progress, failure, result location, and termination reason.
- Cooperative cancellation wired into every long-running loop.
- Restart/multi-worker safety and a bounded result-retention policy.

## Priority 4 — Frontend BFF, state, and warning reduction

**Goal:** Keep all browser-compute workflows behind authenticated same-origin boundaries and make long-running state reliable.

- Browser optimizer calls now route through server-only `optimizerFetch` (the admin route-test BFF and the compare page); audit any future/new browser compute path against this boundary.
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
