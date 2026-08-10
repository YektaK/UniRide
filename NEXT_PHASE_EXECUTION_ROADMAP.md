# Next-Phase Execution Roadmap

**Planning authority date:** 2026-08-10
**Verified base:** `0b4bef6e77d4eda2812cbe773296978862c25599`
**Last verified code-bearing commit:** `ddd85e8b1cc5ed64a8163988b2e179a08c8cfd2f`

This is the handoff-ready roadmap for subsequent work. It is deliberately dependency ordered. Do not begin a later package by assuming an earlier boundary has been solved.

## Verified baseline

- Canonical Python suites: **1,676 passed, 48 warnings, 238.17s**.
- Frontend: **17 Vitest files / 37 tests passed in 2.83s**; TypeScript passed; ESLint reported **0 errors, 158 warnings**.
- Credential-free `npm run build` passed after removing/restoring exactly `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in the child process.
- `npm audit --omit=dev --json` remains unresolved at **84 findings**: **2 critical, 22 high, 59 moderate, 1 low**.
- Current scoped closures are occurrence identity on covered production paths, split-decoder repair, canonical Bildiri extraction, matrix integrity/repository work, seed-0/PSO replay fixes, canonical pytest discovery, optional-solver API null safety, deferred Supabase construction, the admin route-test BFF, and five removed unused direct root dependency edges.

## Explicit non-goals for every package

Do not modify the original dirty/rescue checkout, historical archives, generated benchmark CSVs/reports, datasets/databases, dependency manifests, frontend/API surfaces outside the approved package, solver mathematics outside the approved package, or unrelated worktrees. Do not run paper-scale TSPLIB/CVRPLIB experiments unless the package explicitly authorizes a bounded pilot. Do not merge or push without user authorization.

A passing build does not resolve dependency security. The admin route-test BFF is not general compute authentication. No GIS renderer currently exists.

## Common entry protocol

1. Create an isolated worktree from clean `origin/WIP`; record branch, base SHA, status, and `git diff --check`.
2. Read `AGENTS.md`, [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md), [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md), [UniRide_Ultimate_Audit.md](UniRide_Ultimate_Audit.md), and the relevant academic designs before changing solver/benchmark material.
3. If `.codegraph/` is indexed, use CodeGraph before manual tracing. If unavailable, state the exact blocker and use targeted inspection.
4. Use test-driven development: record a focused RED failure, make the smallest change, then record GREEN. Keep a factual before/after report.
5. Preserve dirty-tree boundaries. Do not accept an external model’s “all tests pass” claim without commands, counts, files, and line evidence.

## Common exit protocol

- Run the package’s focused tests plus the proportionate shared gate.
- Run `git diff --check`, inspect `git diff --name-only`, and record `git status --short --branch`.
- Separate confirmed findings, uncertainty, environment blockers, and untested paths.
- Request an independent review for solver correctness, numerical claims, cross-table consistency, or architecture decisions.
- Treat every external result as an unverified proposal until it is checked locally against live files, diffs, and executable tests.

## Package A — Universal production feasibility enforcement

**Depends on:** current occurrence and split-decoder contracts.
**Scope:** one mandatory solver-independent final certificate at `/optimize` and `/compare`; coverage, continuity/depot closure, capacity, duration, time windows, and matrix completeness; truthful failure/diagnostic responses.
**Entry gate:** map every production strategy/compare exit and identify any path that can set success without certification.
**Exit gate:** mutation tests prove no hard violation can return `success=True`; all production strategies/compare paths attach the same certificate; small-instance reference checks agree on feasibility semantics.
**Verification:** focused new feasibility tests; `python -m pytest uniride_core\tests optimizer_api\tests -q -p no:cacheprovider --tb=short`; `git diff --check`.
**Agent preference:** DeepSeek V4Pro -> Big Pickle -> GPT-5.6 Terra -> GPT-5.6 Luna (Luna only for bounded tests/mechanical work).

### External Agent Handoff - Package A

```text
Role and target model: You are DeepSeek V4Pro, acting as a solver-correctness and production-feasibility engineer.
Objective: Implement one mandatory final feasibility-certificate boundary for all production /optimize and /compare results, with regression proof that a hard violation cannot be returned as success.
Repository and working directory: <REPOSITORY_PATH>
Verified context: Base from clean origin/WIP. Occurrence identity and split-decoder repairs exist on covered paths, but universal production feasibility remains open. The admin route-test BFF is unrelated to this package.
Scope: uniride_core feasibility/result contracts; optimizer_api production strategy/compare response boundaries; focused tests only as required.
Exclusions: No academic archive/dataset/report changes, frontend redesign, dependency changes, large experiments, merge/push, or unrelated dirty-tree edits.
Authorization: edits authorized only for this bounded package and its focused tests/documented evidence.
Required workflow: Create an isolated branch/worktree from clean origin/WIP; record the base SHA, `git status --short --branch`, and `git diff --check` before editing. Preserve the original dirty checkout and every unrelated worktree. Start with git status and diff check. Use CodeGraph first if indexed; otherwise state why and trace callers manually. Use RED-GREEN TDD. Cite exact file/line evidence. Preserve occurrence identity and directed-matrix semantics. Separate confirmed behavior from assumptions. Do not change solver mathematics unless needed to enforce the final certificate. The orchestrating agent must re-verify every returned claim against live files, the actual diff, and exact test output before acceptance.
Verification: Run focused RED/GREEN tests, then python -m pytest uniride_core\tests optimizer_api\tests -q -p no:cacheprovider --tb=short, git diff --check, and git status --short --branch.
Return package: 1) outcome summary; 2) confirmed findings with file/line references; 3) uncertainty/assumptions; 4) exact files inspected/changed; 5) commands/tests and full results; 6) concise diff/patch if direct edits were impossible; 7) remaining risks and next action; 8) confirmation unrelated changes were not modified. Treat your output as an unverified proposal until locally rechecked.
```

## Package B — Compute authentication, typed budgets, and compare semantics

**Depends on:** Package A certificate semantics.
**Scope:** service authentication/authorization for general compute, typed request bounds, alias canonicalization, worker limits, request-scoped executors, and explicit `/compare` ranking policy.
**Entry gate:** inventory all compute endpoints, registry aliases, config inputs, thread-pool construction, and authorization dependencies.
**Exit gate:** unauthorized compute fails closed; invalid budgets fail before work; aliases produce one canonical run; worker count is bounded; compare output states feasibility/ranking policy.
**Verification:** API/strategy focused tests; `python -m pytest optimizer_api\tests uniride_core\tests -q -p no:cacheprovider --tb=short`; `git diff --check`.
**Agent preference:** Big Pickle -> GPT-5.6 Terra -> GPT-5.6 Luna -> DeepSeek V4Pro; move DeepSeek forward when solver semantics dominate.

### External Agent Handoff - Package B

```text
Role and target model: You are Big Pickle, acting as a production API policy, schema, and concurrency engineer.
Objective: Make general compute admission authenticated, typed, bounded, alias-canonical, and explicit about /compare feasibility/ranking semantics.
Repository and working directory: <REPOSITORY_PATH>
Verified context: Universal feasibility is the preceding dependency; selected benchmark/CLI containment does not prove general compute authentication. Optional-solver listing safety exists but does not define explicit-request policy.
Scope: optimizer_api routers/DTOs/strategy registry factories/compare orchestration and focused tests required for admission, bounds, aliases, workers, and response policy.
Exclusions: No durable queue implementation, academic experiments, frontend redesign, dependency changes, merges/pushes, or unrelated worktrees.
Authorization: edits authorized only for this bounded package and focused tests.
Required workflow: Create an isolated branch/worktree from clean origin/WIP; record the base SHA, `git status --short --branch`, and `git diff --check` before editing. Preserve the original dirty checkout and every unrelated worktree. Start clean and record base. Use CodeGraph first if indexed; otherwise state the fallback. Trace every compute caller. Use RED-GREEN TDD; do not silently broaden auth. Cite exact file/line evidence and distinguish policy decisions from observed behavior. Preserve existing public contracts unless an explicitly versioned change is necessary. The orchestrating agent must re-verify every returned claim against live files, the actual diff, and exact test output before acceptance.
Verification: Run focused API tests, then python -m pytest optimizer_api\tests uniride_core\tests -q -p no:cacheprovider --tb=short, git diff --check, and git status --short --branch.
Return package: 1) outcome summary; 2) confirmed findings with file/line references; 3) uncertainty/assumptions; 4) exact files inspected/changed; 5) commands/tests and full results; 6) concise diff/patch if direct edits were impossible; 7) remaining risks and next action; 8) confirmation unrelated changes were not modified. Treat your output as an unverified proposal until locally rechecked.
```

## Package C — Durable jobs and cancellation

**Depends on:** Package B admission/budget contract.
**Scope:** durable benchmark/long-running execution, atomic admission, idempotent IDs, persistence, heartbeat/progress/failure state, cooperative cancellation, restart and multi-worker behavior.
**Entry gate:** characterize current process-local state and every loop that must observe cancellation.
**Exit gate:** restart-safe state; cancellation halts work rather than only changing status; stopped jobs cannot become completed; concurrent creation is idempotent/atomic.
**Verification:** new deterministic job lifecycle tests plus `python -m pytest optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --tb=short`; no large benchmark run.
**Agent preference:** GPT-5.6 Terra -> DeepSeek V4Pro -> Big Pickle -> GPT-5.6 Luna.

### External Agent Handoff - Package C

```text
Role and target model: You are GPT-5.6 Terra, acting as a Python durable-execution and cancellation engineer.
Objective: Replace process-local benchmark/job lifecycle assumptions with a minimal durable, atomic, observable, cooperatively cancellable execution design.
Repository and working directory: <REPOSITORY_PATH>
Verified context: Current work needs durable jobs; a status mutation alone is not cancellation. Compute admission/budgets are a prerequisite and must be respected. No paper-scale experiment is authorized.
Scope: optimizer_api job/benchmark orchestration, persistence seams, cancellation checks in long-running loops, and deterministic lifecycle tests.
Exclusions: No solver-mathematics change, dataset/report generation, frontend redesign, dependency/lockfile change unless separately authorized, merge/push, or unrelated worktree changes.
Authorization: edits authorized only for the durable-job package and focused tests.
Required workflow: Create an isolated branch/worktree from clean origin/WIP; record the base SHA, `git status --short --branch`, and `git diff --check` before editing. Preserve the original dirty checkout and every unrelated worktree. Start with clean Git evidence. Use CodeGraph first if indexed. Map ownership and every cancellation loop before editing. Use RED-GREEN TDD with in-memory/fake-clock seams where possible. Cite exact file/line references; separate confirmed concurrency behavior from assumptions. Avoid a new framework if existing persistence primitives suffice. The orchestrating agent must re-verify every returned claim against live files, the actual diff, and exact test output before acceptance.
Verification: Run focused lifecycle tests, then python -m pytest optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --tb=short, git diff --check, and git status --short --branch.
Return package: 1) outcome summary; 2) confirmed findings with file/line references; 3) uncertainty/assumptions; 4) exact files inspected/changed; 5) commands/tests and full results; 6) concise diff/patch if direct edits were impossible; 7) remaining risks and next action; 8) confirmation unrelated changes were not modified. Treat your output as an unverified proposal until locally rechecked.
```

## Package D — Frontend BFF, state, and warning reduction

**Depends on:** Package B API/auth contracts; Package C job status/cancellation contract where benchmark UI is touched.
**Scope:** remaining browser-direct optimizer calls, authenticated BFFs, serialized/cancellable polling, effective direction/feasibility state, user-safe errors, and targeted reduction of 158 lint warnings.
**Entry gate:** map browser imports, `NEXT_PUBLIC_*` optimizer usage, polling ownership, and warning categories.
**Exit gate:** no remaining selected browser-direct compute path; polls cannot overlap/stale-write; cancellation/error state is visible; warning reductions are real rather than disabled rules.
**Verification:** focused Vitest plus `npm test -- --run`, `npm run typecheck`, `npm run lint`, and `npm run build`.
**Agent preference:** GPT-5.6 Terra -> GPT-5.6 Luna -> Big Pickle -> DeepSeek V4Pro.

### External Agent Handoff - Package D

```text
Role and target model: You are GPT-5.6 Terra, acting as a Next.js BFF and frontend-state reliability engineer.
Objective: Move selected remaining optimizer browser workflows behind authenticated same-origin BFF routes, make async state cancellable/serialized, and reduce real lint debt without suppressing correctness rules.
Repository and working directory: <REPOSITORY_PATH>
Verified context: The admin route-test page already uses /api/optimize-route. That scoped fix is not proof that other pages are safe. ESLint currently has 0 errors and 158 warnings; there is no GIS renderer.
Scope: src/ browser pages/hooks/services and matching same-origin route tests, limited to the approved workflow inventory.
Exclusions: No FastAPI policy redesign, solver changes, map-provider integration, dependency changes, generated artifacts, merge/push, or unrelated worktree edits.
Authorization: edits authorized only for this bounded frontend package and its tests.
Required workflow: Create an isolated branch/worktree from clean origin/WIP; record the base SHA, `git status --short --branch`, and `git diff --check` before editing. Preserve the original dirty checkout and every unrelated worktree. Start with Git evidence. Use CodeGraph first if indexed. Trace executable imports, not comments. Use RED-GREEN Vitest/TDD. Preserve server-only boundaries and authentication ordering. Cite exact file/line evidence and separate verified UI behavior from assumptions. The orchestrating agent must re-verify every returned claim against live files, the actual diff, and exact test output before acceptance.
Verification: Run focused Vitest, npm test -- --run, npm run typecheck, npm run lint, npm run build, git diff --check, and git status --short --branch.
Return package: 1) outcome summary; 2) confirmed findings with file/line references; 3) uncertainty/assumptions; 4) exact files inspected/changed; 5) commands/tests and full results; 6) concise diff/patch if direct edits were impossible; 7) remaining risks and next action; 8) confirmation unrelated changes were not modified. Treat your output as an unverified proposal until locally rechecked.
```

## Package E — Matrix provenance and production/academic metric separation

**Depends on:** Package A feasibility uses matrix validity; Package B typed configuration provides policy carriage.
**Scope:** versioned matrix provenance, unit/domain/directionality/source/time/hash/identity mapping, explicit metric selection, and prevention of production/academic metric substitution.
**Entry gate:** inventory every matrix constructor, adapter, persistence record, and distance fallback.
**Exit gate:** every supported matrix has provenance; adapters reject incompatible domains; tests cover directed and missing arcs plus production-versus-academic separation.
**Verification:** matrix/unit tests; `python -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --tb=short`; no data regeneration.
**Agent preference:** Big Pickle -> GPT-5.6 Terra -> DeepSeek V4Pro -> GPT-5.6 Luna.

### External Agent Handoff - Package E

```text
Role and target model: You are Big Pickle, acting as a routing-matrix schema and provenance engineer.
Objective: Introduce explicit matrix provenance and prevent silent substitution between production travel-time estimates and academic TSPLIB/CVRPLIB metrics.
Repository and working directory: <REPOSITORY_PATH>
Verified context: Invalid arcs fail closed on covered production paths, but provenance/domain/unit/directionality/identity/hash contracts remain open. Directed ATSP behavior must not be downgraded to symmetric assumptions.
Scope: uniride_core matrix models/adapters, optimizer_api repository seams, academic_benchmark adapters/manifests, and focused contract tests.
Exclusions: No dataset downloads/regeneration, benchmark reports, solver algorithm changes, frontend/GIS changes, dependency changes, merge/push, or unrelated worktrees.
Authorization: edits authorized only for the provenance/metric-separation package and focused tests.
Required workflow: Create an isolated branch/worktree from clean origin/WIP; record the base SHA, `git status --short --branch`, and `git diff --check` before editing. Preserve the original dirty checkout and every unrelated worktree. Start clean. Use CodeGraph first if indexed and trace every matrix creator/consumer. Use RED-GREEN TDD with small in-memory directed/symmetric fixtures. Cite exact file/line evidence. Preserve legacy data only through explicit adapters/migrations; do not fabricate provenance. The orchestrating agent must re-verify every returned claim against live files, the actual diff, and exact test output before acceptance.
Verification: Run focused matrix tests, then python -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --tb=short, git diff --check, and git status --short --branch.
Return package: 1) outcome summary; 2) confirmed findings with file/line references; 3) uncertainty/assumptions; 4) exact files inspected/changed; 5) commands/tests and full results; 6) concise diff/patch if direct edits were impossible; 7) remaining risks and next action; 8) confirmation unrelated changes were not modified. Treat your output as an unverified proposal until locally rechecked.
```

## Package F — Academic TSP/ATSP/CVRP validation campaign

**Depends on:** Package E metric/provenance contract and existing fairness/study designs.
**Scope:** manifests, reproducible runner configuration, fixed-budget primary protocol, separately labelled native termination, representative TSP/ATSP/CVRP test families, reference baselines, and analysis-ready evidence schema.
**Entry gate:** read `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`, `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`, and `CANONICAL_THREE_OPT_DESIGN.md`; verify active solver identities and JIT/fallback truthfulness.
**Exit gate:** bounded smoke/pilot validation is reproducible and clearly non-publication evidence; paper-scale execution requires a separately approved run plan.
**Verification:** focused academic protocol/parity tests, manifest checks, and bounded dry-run/pilot only; do not generate large CSV/report artifacts by default.
**Agent preference:** DeepSeek V4Pro -> Big Pickle -> GPT-5.6 Terra -> GPT-5.6 Luna.

### External Agent Handoff - Package F

```text
Role and target model: You are DeepSeek V4Pro, acting as an operations-research experiment and solver-parity engineer.
Objective: Prepare a reproducible, scientifically defensible TSP/ATSP/CVRP validation campaign without claiming paper-scale results from smoke or pilot runs.
Repository and working directory: <REPOSITORY_PATH>
Verified context: Bildiri canonical extraction and fairness contracts exist; fixed objective-evaluation budgets are primary, native termination is separately labelled. TSP/ATSP Hamiltonian cycles and CVRP/CVRPTW multi-route validation are different contracts.
Scope: academic_benchmark manifests/protocols/runners/tests and neutral core accounting needed for controlled campaign readiness.
Exclusions: No production API/frontend changes, no large experiments, no unreviewed CSV/report publication, no solver renaming, no dependency change, merge/push, or unrelated worktree edits.
Authorization: edits authorized for bounded reproducibility contracts, fixtures, and dry-run/pilot support only; paper-scale runs require later approval.
Required workflow: Create an isolated branch/worktree from clean origin/WIP; record the base SHA, `git status --short --branch`, and `git diff --check` before editing. Preserve the original dirty checkout and every unrelated worktree. Begin with clean Git evidence. Use CodeGraph first if indexed. Read the three named academic design documents before editing. Use RED-GREEN tests, fixed seeds, independent closed-tour/multi-route validation, and truthful JIT/fallback reporting. Cite exact file/line evidence and separate observed evidence from assumptions. The orchestrating agent must re-verify every returned claim against live files, the actual diff, and exact test output before acceptance.
Verification: Run relevant academic parity/protocol/manifest tests, python -m pytest academic_benchmark\tests -q -p no:cacheprovider --tb=short when proportionate, git diff --check, and git status --short --branch. Report any skipped JIT case explicitly.
Return package: 1) outcome summary; 2) confirmed findings with file/line references; 3) uncertainty/assumptions; 4) exact files inspected/changed; 5) commands/tests and full results; 6) concise diff/patch if direct edits were impossible; 7) remaining risks and next action; 8) confirmation unrelated changes were not modified. Treat your output as an unverified proposal until locally rechecked.
```

## Package G — Backend geometry contract, then GIS renderer

**Depends on:** Package B authenticated service boundary and Package E location/matrix provenance. The renderer begins only after the backend geometry contract passes its gates.
**Scope:** authoritative location catalog, direction/staleness semantics, GeoJSON or encoded-polyline contract, provider threat model/CSP, then a minimal map renderer with memoized layers/handlers and tests.
**Entry gate:** no current GIS renderer may be assumed; map provider selection and geometry source must be explicit.
**Exit gate:** backend emits validated geometry with location identity/provenance; selected UI renders it with stable state/handlers; CSP/provider constraints are tested; no fake map data becomes operational truth.
**Verification:** focused Python contract test `python -m pytest optimizer_api\tests\test_route_geometry_contract.py -q -p no:cacheprovider --tb=short` (the package may create this file); full relevant Python suites `python -m pytest optimizer_api\tests uniride_core\tests -q -p no:cacheprovider --tb=short`; focused UI tests; `npm test -- --run`; `npm run typecheck`; `npm run lint`; `npm run build`.
**Agent preference:** GPT-5.6 Terra -> GPT-5.6 Luna -> Big Pickle -> DeepSeek V4Pro.

### External Agent Handoff - Package G

```text
Role and target model: You are GPT-5.6 Terra, acting as a backend geometry-contract and GIS integration engineer.
Objective: First define and test an authoritative backend route-geometry contract; only then implement a minimal production GIS renderer against that contract.
Repository and working directory: <REPOSITORY_PATH>
Verified context: There is currently no GIS renderer and no authoritative route geometry. Existing route lists/coordinates are not proof of a map contract. Matrix/location provenance and compute authorization are prerequisite boundaries.
Scope: backend location/geometry DTOs and adapters, selected Next.js map/UI components, CSP/provider configuration only when justified, and focused tests.
Exclusions: No map implementation before a tested geometry contract, no provider credentials in source/docs, no solver or benchmark changes, no broad frontend redesign, dependency change unless separately approved, merge/push, or unrelated worktree edits.
Authorization: edits authorized only for this staged geometry-then-renderer package and focused tests.
Required workflow: Create an isolated branch/worktree from clean origin/WIP; record the base SHA, `git status --short --branch`, and `git diff --check` before editing. Preserve the original dirty checkout and every unrelated worktree. Start clean and split the work into backend-contract gate then renderer gate. Use CodeGraph first if indexed. Use RED-GREEN tests with deterministic geometry fixtures. Cite exact file/line evidence; threat-model any provider/CSP change; preserve occurrence/location identity and backend-effective direction. The orchestrating agent must re-verify every returned claim against live files, the actual diff, and exact test output before acceptance.
Verification: Create/run `python -m pytest optimizer_api/tests/test_route_geometry_contract.py -q -p no:cacheprovider --tb=short`, then run `python -m pytest optimizer_api/tests uniride_core/tests -q -p no:cacheprovider --tb=short`, focused Vitest, npm test -- --run, npm run typecheck, npm run lint, npm run build, git diff --check, and git status --short --branch.
Return package: 1) outcome summary; 2) confirmed findings with file/line references; 3) uncertainty/assumptions; 4) exact files inspected/changed; 5) commands/tests and full results; 6) concise diff/patch if direct edits were impossible; 7) remaining risks and next action; 8) confirmation unrelated changes were not modified. Treat your output as an unverified proposal until locally rechecked.
```

## Model-routing rule

The preference order is a task-fit policy, not evidence that Codex can invoke an external model. If the preferred external model is unavailable, do not silently substitute it: issue the relevant handoff prompt, state the alternative, and continue only independent safe work. Final numerical, solver, and architecture claims require local evidence and an appropriately strong independent review.
