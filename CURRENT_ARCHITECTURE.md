# UniRide Current Architecture

**Verified documentation snapshot:** 2026-08-25
**Historical verification evidence:** 2026-08-24 remediation derived from `fef5a2b537da7068b51b3b3a50c6d633a2853404`
**Latest scoped verification:** Dudullu Package 1 on `codex/dudullu-daily-planner-20260825`, based on `origin/WIP` `60161adeb81b18b3798a9e0c2024163cabf63e50`, with code through `6ef36591215331bcd51b33a0f6f6508c62862702`

This describes current, verified boundaries. It is not a production-readiness claim. When this document conflicts with live code or executable tests, those sources win.

## 1. Dual-engine boundary

```mermaid
flowchart LR
  UI[Next.js browser UI] --> BFF[Same-origin Next.js BFF]
  BFF --> DB[Supabase]
  BFF --> API[FastAPI production optimizer]
  API --> PA[Production adapters]
  CLI[Academic CLI / study protocol] --> AA[Academic adapters]
  PA --> CORE[uniride_core]
  AA --> CORE
```

- **Production** owns identities and authorization, operational DTOs, authoritative locations, travel-time/provider policy, geometry, persistence, and operational failures.
- **Academic** owns TSPLIB/CVRPLIB sources, BKS/gaps, experiment manifests, seed schedules, DOE, statistics, and research-result persistence.
- **`uniride_core`** owns neutral routing models, constraints, algorithm implementations, local search, matrix contracts, and solver-independent validation.

The intended dependency flow is inward: adapters may depend on the core; the core must not depend on FastAPI, Next.js, academic persistence, or study orchestration.

## 2. Current request and study paths

### Production request path

```text
Browser -> authenticated Next.js BFF -> FastAPI internal-key boundary
        -> canonical alias resolution -> fresh request-scoped strategy
        -> immutable compute policy (lowering-only) -> request-scoped solver work
        -> Package A feasibility certificate -> deterministic admission/ranking -> response/persistence
```

The admin route-test workflow calls the authenticated same-origin `/api/optimize-route` BFF and no longer calls the optimizer directly from the browser. General production compute is now protected end to end:

- The FastAPI `optimization` router requires `X-Internal-API-Key` (constant-time compared, router-level dependency) for `POST /api/v1/optimize`, `POST /api/v1/compare`, and `POST /api/v1/vehicle-calculator`. `/health`, `/api/v1/strategies`, `/api/v1/extract-time-windows`, and `/api/v1/schedule-to-students` remain public.
- Next.js server code calls those heavy endpoints only through `optimizerFetch` (`src/lib/optimizer-server.ts`), which imports `server-only`, reads `OPTIMIZER_INTERNAL_API_KEY`, and injects it as a header. Public raw `fetch` is reserved for `/health` and `/api/v1/strategies`. The key is never exposed through a `NEXT_PUBLIC_*` variable, responses, or logs.
- Every submitted strategy key resolves through `resolve_strategy`/`resolve_unique_strategies` (`optimizer_api/strategies/canonical.py`) to one canonical identity; each canonical run receives a fresh instance from `resolution.create()`, which fails closed if the factory returns a mismatched name.
- `apply_compute_policy` (`optimizer_api/compute_policy.py`) applies the frozen, immutable `production-conservative-v1` profile to a request-local copy, returns typed `applied_policy` metadata, and caps native solver budgets (`solver_seconds`, `ls_time_limit`) per request. Overrides may lower ceilings but never raise them.
- `/optimize` and `/compare` results pass through the Package A feasibility certificate; a result is successful only when it is solver-successful **and** `feasibility_certificate.is_feasible`. Failed/infeasible/uncertified/timed-out results are never ranked. Best/fastest ranking is deterministic (duration, vehicles, canonical name / execution seconds, canonical name).
- `/compare` deduplicates aliases, runs at most `max_workers` (2) canonical workers, and applies one 120-second **soft** response deadline via `concurrent.futures.wait`. Pending futures are not waited on and the executor shuts down with `wait=False`; running threads may continue, so Package B is **not** hard cancellation.
- Exact/permutation requests with more than ten waypoints fail fast before the solver method is invoked (`ExactTSPSizeError` in `uniride_core/algorithms/string_exact_tsp.py`; router preflight for `optimize`, `compare`, and `_run_single_algorithm`), with the same sanitized unsuccessful shape used when a solver produces no valid result.

### Academic path

```text
Dataset/study manifest -> academic registry/protocol -> canonical core solver
                      -> feasibility/result accounting -> analysis artifacts
```

Bildiri legacy solver material has a canonical-core boundary and archive/manifest protection. Academic execution remains separate from production request lifecycles.

## 3. Verified closures, with scope

| Area | Verified closure | Scope limit |
| --- | --- | --- |
| Customer identity | occurrence identity is preserved on the production paths covered by current tests | future/new strategy adapters still need the same contract review |
| Giant-tour splitting | split-decoder corrections cover infeasible-state initialization, prefixes, violation accounting, depot behavior, and missing directed arcs | does not certify every solver family universally |
| Academic solver ownership | active Bildiri GWO/HHO/Numba behavior is canonicalized behind the core boundary | not evidence that every research algorithm is publication-ready |
| Matrix integrity | injectable repository/lifecycle, timeout, last-known-good handling, strict invalid-arc rejection, and cache health are covered | matrix provenance and production/academic metric separation are still open |
| Determinism | seed `0` preservation and PSO deterministic seed handling are covered | each future stochastic algorithm must prove its own replay behavior |
| Python discovery | default pytest discovery is restricted to the three canonical suites | manual scripts remain historical/manual, not default test inputs |
| Optional solvers | health and default-compare enumeration tolerate unavailable optional solvers | explicit requested-algorithm policy remains a separate service concern |
| Supabase construction | proxy and driver routes defer client construction; credential-free build passes | credential-free build is not an authentication/security certification |
| Browser optimization test | admin route-test uses the authenticated BFF | other production/browser compute paths remain to be migrated |
| Dependencies | five unused **direct** root edges were removed | transitive Genkit packages and audit findings remain |
| Compute authentication | all three heavy endpoints deny missing/wrong keys (403) and accept a valid key; public endpoints remain public; `UNIRIDE_DISABLE_AUTH=1` is a startup error under `APP_ENV=production`; tenant keys resolve to distinct tenant identities; blank/untrimmed/reserved IDs, blank/duplicate secrets, and reuse of the ops key fail closed | per-tenant budgets/quotas beyond rate windows are not implemented |
| Compute profile | frozen `production-conservative-v1` ceilings; nine `UNIRIDE_COMPUTE_*` overrides validated at startup and may only lower ceilings; tuning allowlists are exhaustive and fail closed; authenticated rate windows are tenant-keyed with IP fallback | the limiter and profile are process-local to the optimizer service, not distributed admission control |
| Canonical resolution | every alias resolves to one canonical identity; explicit alias duplicates execute once; fresh request-scoped instances per canonical run | future registry additions need the same contract review |
| Bounded comparison | at most 2 workers, one 120-second soft deadline, six canonical defaults, deterministic best/fastest ranking, certificate-gated admission | soft deadline is not hard cancellation or process isolation |
| Exact TSP | >10-waypoint exact/permutation requests fail fast without truncation and never invoke the solver | applies to the canonical permutation_tsp/exact paths; other solver limits unchanged |
| Server-only transport | heavy Next.js calls route through server-only `optimizerFetch`; browser boundary test blocks the internal key from client code | browser-facing pages depend on BFF routes continuing to enforce the boundary |
| Dudullu daily demand domain | pure TypeScript schedule filtering, separate pickup/dropoff occurrences, hourly waves with exact anchors, inclusive previous-day 22:00 `Europe/Istanbul` admission, exception/lead handling, and shift-eligibility precheck are covered by `src/services/daily-planning.test.ts`; final hardening fails closed on out-of-day anchors, blank identities, invalid runtime directions, and malformed source demands, with boundary-first same-wave ordering | no database/API/UI integration, no live-data verification, no optimizer/matrix binding, no full depot-chain timing, no physical-fleet assignment, and no publication |

## 4. Open production boundaries

These are not closed by test count, a build pass, or documentation updates:

1. **Feasibility extension discipline.** The current `/optimize`, `/compare`, and tested requested-algorithm/vehicle-calculator paths are certificate-gated. Every future solver, router, persistence, or response surface must prove the same fail-closed contract; present coverage is not a blanket production certification.
2. **Compute protection and budgets.** Internal-key boundary authentication, tenant-key authorization, typed lowering-only limits, alias deduplication, worker ceilings, soft deadlines, tenant-keyed rate windows with IP fallback, and deterministic compare ranking are implemented. **Hard solver cancellation, process isolation, distributed quota state, and durable jobs remain open.**
3. **Durable execution.** Benchmark work is not yet a durable multi-worker job system with atomic admission, persisted heartbeat, idempotency, and cooperative cancellation.
4. **Matrix provenance.** Production travel time and academic problem metrics still require explicit, non-interchangeable provenance/domain/unit/directionality contracts.
5. **Frontend resilience.** State consolidation, cancellation/timeouts, polling, error handling, and the 158 lint warnings need focused work.
6. **GIS.** There is no current route-geometry contract or GIS renderer. Existing route lists and locations are not a map implementation.
7. **Dependency security.** The last recorded `npm audit --omit=dev --json` reported 84 unresolved findings (2 critical, 22 high, 59 moderate, 1 low); that count was not refreshed on 2026-08-24.
8. **Dudullu daily operations.** Package 1 is a pure, tested demand/slot boundary only. Package 0 must verify live runtime/data readiness (including rather than assuming any historical 28-record import). Package 2 must provide an authenticated preview API, authoritative matrix ID/version/hash, independent used-arc checks, full depot-to-depot timing including the closing arc, and two-stage day-level physical-fleet assignment with truthful shortage/non-publishable semantics. Package 3 requires transactional versioned multi-wave publication and RLS; Package 4 owns admin/student workflows; Package 5 needs certified cross-wave before/after re-solves and lexicographic fleet-first savings; Package 6 is pilot/operations. No automatic student shifting or unverified savings claim is allowed.

## 5. Solver and matrix contract

A production solver input must distinguish a customer occurrence from a physical stop. Multiple students can share coordinates without becoming one demand, time window, service requirement, or route stop.

A matrix must declare its source/domain, units, directionality, identity mapping, completeness, and validity. Invalid off-diagonal values fail closed on covered production paths. Academic TSPLIB/CVRPLIB distances and production travel-time estimates must never be silently substituted for one another.

A target neutral contract is:

```text
Production DTO --production adapter--+
                                      +-> RoutingProblem / CostMatrix / ConstraintProfile
Academic record --academic adapter---+                 |
                                                        v
                                                   Solver / Result
                                                        |
                                                        v
                                           FeasibilityCertificate
```

Production-specific geometry, users, authorization, and errors remain outside this neutral model. BKS/gaps, DOE metadata, dataset persistence, and statistical reporting remain academic-only.

## 6. Execution and concurrency

Registry metadata should be immutable. Executable strategies must be request/job scoped. `/compare` now uses at most 2 canonical workers and a single 120-second soft response deadline; native solver budgets are capped per request. Because the deadline is soft (threads may continue, `wait=False` shutdown), hard cancellation that actually stops loops, process isolation, and durable persistence are still required before this can be treated as multi-worker production infrastructure.

## 7. Verification baseline

On 2026-08-24, branch `codex/audit-remediation-20260824` (base `fef5a2b`) passed full Python discovery with **3,355 passed, 1 skipped, 45 warnings in 429.17s**. Frontend Vitest passed **21 files / 58 tests in 78.99s** after restricting discovery to the current root `src` tree; TypeScript passed; ESLint reported **0 errors / 158 warnings** under the temporary waiver; and the Next.js 16.1.6 production build passed with **57 dynamic, server-rendered routes**. The previous environment-sensitive matrix test and ignored local Bildiri-boundary failures are closed. The npm security audit was not rerun, so the 84-finding figure above remains dated evidence rather than a current count.

On 2026-08-25, the Package 1 feature branch
`codex/dudullu-daily-planner-20260825` at `6ef36591215331bcd51b33a0f6f6508c62862702`
passed `daily-planning` (**1 file / 32 tests**) and the six named regression
files (**6 files / 19 tests**), `npm run typecheck` (**0 errors**), `npm run
lint` (**0 errors / 158 warnings**), and `git diff --check`. This is not a
current live-data or production-operation verification.

See [UniRide_Ultimate_Audit.md](UniRide_Ultimate_Audit.md) for qualifications, [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md) for priority, and [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md) for bounded future handoffs.
