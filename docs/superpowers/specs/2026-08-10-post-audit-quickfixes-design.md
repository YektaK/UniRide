# Post-Audit Quick Fixes and Documentation Truth Design

**Status:** Approved design, pending specification review  
**Date:** 2026-08-10  
**Base:** `origin/WIP` at `0b4bef6e77d4eda2812cbe773296978862c25599`  
**Branch:** `codex/post-audit-quickfixes-20260810`

## 1. Objective

Apply a bounded set of low-risk corrections discovered by the 2026-08-10 zero-trust re-verification, then make the root documentation describe the resulting code rather than earlier intentions. The package must also leave a detailed, agent-oriented roadmap in the repository so later solver, API, and frontend work can be handed to DeepSeek, Big Pickle, GPT-5.6 Terra, or GPT-5.6 Luna without reconstructing project history.

This package is not permission to complete the universal feasibility boundary, service authentication, or comparison-engine redesign. Those remain separate, high-risk packages in the new roadmap.

## 2. Verified Starting State

The design relies on executable evidence gathered against the exact base above:

- `uniride_core/tests`, `optimizer_api/tests`, and `academic_benchmark/tests`: 1,670 passed with 48 warnings.
- Frontend: 27 tests passed; TypeScript passed; ESLint reported 0 errors and 158 warnings.
- `npm run build`: compilation and type checking passed, then page-data collection failed with `supabaseUrl is required` from eager server-client construction.
- Production dependency audit: 87 advisories, including 3 critical and 22 high.
- Bildiri boundary/parity/JIT suite: 60 passed; the 233-entry archive manifest verified.
- The production feasibility certificate exists but is not universally enforced by `/optimize` or `/compare`.
- FastAPI benchmark endpoints are authenticated, while general compute endpoints are not yet protected by the same service boundary.
- The local `WIP` worktree was six commits behind the remote at audit time; this package therefore starts directly from the verified remote head.

The `.codegraph/` directory does not contain an operational index in this worktree. `codegraph explore` failed with the tool's explicit instruction not to self-index; targeted source tracing is the authorized fallback.

## 3. Considered Approaches

### A. Bounded quick fixes plus documentation truth — selected

Correct defects whose behavior can be pinned with small tests and whose changes do not redefine solver mathematics or security architecture. Update documentation only after the resulting gates are known.

### B. Documentation-only correction

This would be faster, but would leave easy release/build defects active and immediately make the roadmap partially obsolete. Rejected.

### C. Complete production hardening in one package

This would combine feasibility, authentication, budgets, process isolation, comparison semantics, frontend routing, dependencies, and documentation. The review surface and rollback risk are too large. Rejected.

## 4. Authorized Quick Fixes

### 4.1 Optional-solver null safety

PyVRP and VROOM are optional and can legitimately be represented by `None` in the production registry. Health, unknown-algorithm reporting, strategy listing, and default comparison discovery must not dereference unavailable entries.

The implementation should reuse the existing registry/factory helpers where they already express availability. It must not introduce another registry abstraction. Tests must reproduce the missing-optional-solver profile before implementation and verify stable JSON/listing behavior afterward.

### 4.2 Build-safe Supabase client construction

Server clients must not be constructed at module import time when environment variables are absent. The existing lazy `getSupabaseAdmin()` helper is the preferred admin-client boundary. The driver-assignment handlers should acquire the client inside request execution after authorization.

Any other import-time Supabase construction exposed by the next build, including proxy/JWT code, may be changed only enough to defer construction until request execution and fail closed at runtime when required credentials are absent. No mock/default credentials may be invented.

Acceptance requires `npm run build` to pass in the same environment that previously failed for absent Supabase variables. A build that merely reaches a different missing-environment crash is not success.

### 4.3 Browser optimization through the authenticated BFF

Client components must not call FastAPI through `NEXT_PUBLIC_OPTIMIZER_API_URL` or the browser's `127.0.0.1`. The admin route-test page must use the existing authenticated same-origin `/api/optimize-route` route.

The direct optimizer service remains a server-side adapter for Next.js route handlers. Prefer a native `server-only` boundary or an equivalently small existing-project pattern rather than a new client library. Types may remain shared through type-only imports or a minimal neutral type module if compilation requires it.

Tests must prove the route-test workflow targets the same-origin BFF and that the server adapter is not imported as executable browser code.

### 4.4 Canonical pytest discovery

The repository's authoritative Python suites are:

- `uniride_core/tests`
- `optimizer_api/tests`
- `academic_benchmark/tests`

Configure pytest to discover those paths by default so `pytest` does not import manual `test_*.py` scripts that perform database, network, benchmark, or external-AI actions during collection. Do not delete or rewrite those historical/manual scripts in this package.

The red gate is the current broad collection failure at `optimizer_api/test_api.py` due to undeclared `requests`. The green gate is successful canonical collection without importing that script.

### 4.5 Evidence-based dependency pruning

Remove only direct JavaScript dependencies with zero live imports or required configuration references. The currently identified candidates are:

- `@genkit-ai/firebase`
- `@genkit-ai/google-genai`
- `@genkit-ai/next`
- `@typespec/compiler`

`@genkit-ai/ai` may be removed as a direct dependency only if the lock graph and live imports prove it remains correctly supplied by the retained `genkit` package. Retain `genkit`, `@genkit-ai/googleai`, and `xlsx` in this package; replacing `xlsx` or redesigning the AI flow is future work.

Regenerate `package-lock.json` using npm's normal package operation. Unit tests, typecheck, lint, build, and a fresh production-only audit must follow. The package is accepted when advisories do not increase and the removable `tar`/`websocket-driver` critical paths disappear where the dependency graph permits. It is not required to eliminate all npm debt.

## 5. Documentation Deliverables

After code verification, synchronize these root files:

- `README.md`
- `CURRENT_ARCHITECTURE.md`
- `ACTIVE_ROADMAP.md`
- `UniRide_Ultimate_Audit.md`
- `WORKLOG.md`

Corrections must include:

- current branch/base and actual verification counts;
- occurrence identity, split-decoder, canonical Bildiri extraction, matrix repository, and seed-`0` fixes as verified closures with their scope stated accurately;
- universal production feasibility enforcement as open;
- compute authentication, typed bounds, alias deduplication, worker ceilings, hard cancellation, and comparison ranking as open;
- production build and npm advisory status based on the final commands from this package;
- no claim that a waiver equals remediation or a passing gate;
- no stale PSO wall-clock seed claim;
- no implication that a GIS renderer currently exists.

Create one new root-level authority document:

`NEXT_PHASE_EXECUTION_ROADMAP.md`

It must contain:

1. Current verified baseline and explicit non-goals.
2. Dependency-ordered packages with entry and exit gates.
3. Exact affected subsystems and minimum verification commands.
4. Agent preference order for each package using the user's available external models.
5. A reusable handoff packet for each future package containing the required role, objective, repository path placeholder, verified context, scope, exclusions, authorization, workflow, verification, and return-package fields.
6. A rule that external results are proposals until locally verified against code, diff, and tests.

The roadmap's initial package order is:

1. Universal production feasibility enforcement.
2. Compute authentication, typed budgets, and `/compare` redesign.
3. Durable benchmark execution and cancellation.
4. Frontend optimizer/BFF state consolidation and warning reduction.
5. Matrix provenance and production/academic metric separation.
6. Academic validation campaign for TSP, ATSP, CVRP, and later problem families.
7. GIS geometry contract and renderer only after the backend geometry boundary exists.

## 6. Agent Routing

Implementation uses fresh, bounded subagents and independent review. Local callable agents may be used directly; unavailable external agents receive copy/paste prompt packets rather than being silently substituted.

Future package preference orders:

- Solver correctness and feasibility: DeepSeek, Big Pickle, GPT-5.6 Terra; Luna for bounded test generation only.
- Schemas, budgets, validators, and data contracts: Big Pickle, GPT-5.6 Terra, GPT-5.6 Luna; DeepSeek for solver-facing edge cases.
- API/concurrency integration: GPT-5.6 Terra, DeepSeek, Big Pickle; Luna for mechanical regression fixtures.
- Frontend/BFF and build hygiene: GPT-5.6 Terra, GPT-5.6 Luna, Big Pickle; DeepSeek only if solver semantics are implicated.
- Documentation consolidation: GPT-5.6 Terra, GPT-5.6 Luna; technical claims require repository verification.

No external model output may be accepted solely because it reports that tests passed. Exact commands, counts, failures, changed files, and caveats are mandatory.

## 7. Verification

Each behavioral change follows red-green TDD with the smallest focused test. Final verification must include:

```powershell
python -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --tb=short
npm test -- --run
npm run typecheck
npm run lint
npm run build
npm audit --omit=dev --json
git diff --check
git status --short --branch
```

The implementation plan may select the known dependency-complete Python interpreter and existing Node installation, but it must record their exact paths/versions. It must not modify existing virtual environments.

## 8. Exclusions

- No universal feasibility integration in this quick-fix package.
- No authentication redesign for `/optimize` or `/compare`.
- No solver mathematics, fairness-budget, termination, seed schedule, or capability-promotion changes.
- No benchmark dataset, database, CSV, report, or historical archive mutation.
- No large TSPLIB/CVRPLIB experiments.
- No replacement of `xlsx`, Genkit, Supabase, Next.js, FastAPI, or the strategy registry.
- No GIS renderer or geometry-provider integration.
- No changes to the original dirty checkout or unrelated worktrees.
- No merge or push without explicit user authorization after review.

## 9. Completion Criteria

The package is complete only when:

- every authorized quick fix has focused regression evidence;
- the complete Python and frontend gates pass;
- the production build passes without relying on the prior Supabase waiver;
- dependency pruning is demonstrated by a fresh audit and dependency trace;
- all five master documents agree with live code and final command results;
- `NEXT_PHASE_EXECUTION_ROADMAP.md` is complete enough for another agent to start without reading this conversation;
- an independent whole-branch review finds no unresolved critical or important issue;
- the feature worktree is clean and the original dirty checkout remains untouched.
