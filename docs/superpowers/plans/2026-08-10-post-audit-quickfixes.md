# Post-Audit Quick Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved low-risk API, build, BFF, discovery, and dependency fixes; verify them; then synchronize the six authority documents and publish the future-agent roadmap.

**Architecture:** Reuse the current registry, lazy Supabase admin helper, authenticated `adminFetch`, and Next.js BFF. Each behavior receives a failing regression test and its own commit. Code verification precedes documentation so claims use immutable commits and measured results.

**Tech Stack:** Python 3.14/FastAPI/Pydantic/pytest; Next.js 16/React 18/TypeScript/Vitest/Zod/Supabase; npm 11.

## Global Constraints

- Verification base: `0b4bef6e77d4eda2812cbe773296978862c25599`.
- Preserve production registry IDs, aliases, and optional `None` entries.
- Health and unknown-algorithm lists: available canonical names, unique and sorted.
- Default compare: available canonical names, unique and sorted; aliases and unavailable entries create no work.
- Strategy listing: retain unavailable optional rows as `available: false` in registry order.
- Never create Supabase clients with empty/invented credentials.
- Credential-free build removes `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`.
- Route-test uses authenticated same-origin `/api/optimize-route` and preserves `local_search_type`.
- Default pytest discovery is exactly the three authoritative test directories.
- Retain `genkit`, `@genkit-ai/googleai`, and `xlsx`; remove only evidence-proven unused direct edges.
- Nonzero `npm audit` is recorded evidence, not automatic failure.
- No solver math, feasibility redesign, general compute-auth redesign, data/archive changes, GIS renderer, merge, push, or unrelated-worktree edit.
- Use RED → observed expected failure → minimal GREEN → focused regression → commit.

## Tooling

Worktree: `C:\tmp\UniRide-post-audit-quickfixes`. Python: `C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe` (3.14.6; pytest 9.1.1; NumPy 2.4.6; Numba 0.66.0; FastAPI 0.141.1; OR-Tools 9.15.6755). Node 25.5.0; npm 11.8.0. `node_modules` is absent; run `npm ci` once before frontend RED tests and confirm manifests stay unchanged.

---

### Task 1: Canonical Pytest Discovery

**Files:** modify `academic_benchmark/tests/test_yaem_quarantine_boundary.py` and `pyproject.toml`.

**Produces:** exact pytest `testpaths`.

- [ ] Add this RED contract beside the existing pytest configuration test:

~~~~python
def test_pytest_testpaths_are_exact_authoritative_suites():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["pytest"]["ini_options"]["testpaths"] == [
        "uniride_core/tests",
        "optimizer_api/tests",
        "academic_benchmark/tests",
    ]
~~~~

- [ ] Run RED:

~~~~powershell
& C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest academic_benchmark\tests\test_yaem_quarantine_boundary.py::test_pytest_testpaths_are_exact_authoritative_suites -q -p no:cacheprovider --basetemp C:\tmp\pytest-post-audit-discovery --tb=short
~~~~

Expected: missing `testpaths` failure.

- [ ] Add under `[tool.pytest.ini_options]`:

~~~~toml
testpaths = ["uniride_core/tests", "optimizer_api/tests", "academic_benchmark/tests"]
~~~~

Do not alter manual scripts or `norecursedirs`.

- [ ] Run GREEN and collection:

~~~~powershell
& C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest academic_benchmark\tests\test_yaem_quarantine_boundary.py::test_pytest_testpaths_are_exact_authoritative_suites -q -p no:cacheprovider --basetemp C:\tmp\pytest-post-audit-discovery --tb=short
& C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest --collect-only -q -p no:cacheprovider --basetemp C:\tmp\pytest-post-audit-collect
~~~~

Expected: green; no collection of `optimizer_api/test_api.py` or `test_direct.py`.

- [ ] `git diff --check`, stage the two files, commit `test(pytest): constrain discovery to canonical suites`.

---

### Task 2: Optional-Solver Null Safety

**Files:** create `optimizer_api/tests/test_optional_solver_api.py`; modify `optimizer_api/strategies/__init__.py`, `optimizer_api/main.py`, and `optimizer_api/routers/optimization.py`; verify `optimizer_api/routers/strategies.py` unchanged.

**Produces:** `get_available_strategy_names() -> list[str]`.

- [ ] Write RED tests named:
  - `test_available_strategy_names_excludes_none_deduplicates_aliases_and_sorts`: monkeypatch registry to duplicate `alpha`, `zeta`, and `pyvrp=None`; expect `["alpha", "zeta"]`.
  - `test_health_reports_only_sorted_available_strategy_names`: patch helper; expect exact list.
  - `test_unknown_algorithm_reports_only_sorted_available_names`: valid minimal `OptimizationRequest`; expect status 400 and exact detail.
  - `test_compare_defaults_to_available_canonical_names`: patch helper and `_run_single_algorithm`; expect each name once and ordered results/summary.
  - `test_strategies_endpoint_keeps_unavailable_entries_in_declared_order`: patch `get_strategy_info`; expect ordered `[True, False]` availability.

Use this minimal helper implementation target:

~~~~python
def get_available_strategy_names() -> List[str]:
    return sorted({
        strategy.name
        for strategy in STRATEGY_REGISTRY.values()
        if strategy is not None
    })
~~~~

- [ ] Run RED:

~~~~powershell
& C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api\tests\test_optional_solver_api.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-post-audit-api --tb=short
~~~~

Expected: missing helper and current `None.name` failures.

- [ ] Add/export the helper. Replace only the three unsafe list expressions in health, unknown error, and default compare. Preserve explicit requested-algorithm behavior and `get_strategy_info()`.

- [ ] Run GREEN:

~~~~powershell
& C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api\tests\test_optional_solver_api.py optimizer_api\tests\test_strategy_registry_minor1.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-post-audit-registry --tb=short
~~~~

- [ ] `git diff --check`; commit the four files as `fix(api): make optional solver surfaces null-safe`.

---

### Task 3: Build-Safe Supabase Construction

**Files:** create `src/proxy.test.ts` and `src/app/api/driver/assignments/route.test.ts`; modify `src/proxy.ts` and `src/app/api/driver/assignments/route.ts`; reuse `src/lib/supabase-admin.ts`.

- [ ] Run `npm ci`; confirm only ignored `node_modules` appears.

- [ ] RED proxy tests: with all three credentials deleted, dynamically import proxy with mocked `createClient`; import must not call it. An authenticated request must return sanitized `503 { error: "Authentication service unavailable" }` without constructing a client. Missing bearer remains 401.

- [ ] RED driver tests: mock `requireRole` and `getSupabaseAdmin`; module import must not call the getter. Calling `GET` after successful auth must call it. When it throws for absent credentials, response is generic `500 { error: "Internal server error" }`.

- [ ] Run RED:

~~~~powershell
npm test -- --run src/proxy.test.ts src/app/api/driver/assignments/route.test.ts
~~~~

Expected: eager import-time clients violate the assertions.

- [ ] In the driver route, replace direct `createClient` with `getSupabaseAdmin()` inside each handler after `requireRole`. In proxy use:

~~~~typescript
function getSupabaseAnon() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  return url && key ? createClient(url, key) : null;
}
~~~~

After the bearer check, return sanitized 503 when the helper returns null; otherwise verify the token. Do not add another wrapper or cache.

- [ ] Run GREEN, typecheck, and credential-free build. First assert there is no untracked `.env*`; report rather than delete any such file. Remove the three process vars inside a PowerShell `try/finally`, run `npm run build`, then restore prior values.

- [ ] `git diff --check`; commit four files as `fix(web): defer Supabase clients until requests`.

---

### Task 4: Authenticated Route-Test BFF

**Files:** create `src/lib/admin-api.test.ts`, `src/app/api/optimize-route/route.test.ts`, `src/app/(app)/admin/route-test/page.bff-contract.test.ts`; modify `src/lib/admin-api.ts`, the BFF route, and the route-test page.

**Produces:** `adminApi.routes.optimize` accepts optional `local_search_type` and `max_travel_time`; BFF validates and forwards local search.

- [ ] RED admin-client test: mock a `test-token` session and fetch; call with `local_search_type: "or_opt"` and `max_travel_time: 180`. Assert URL is exactly `/api/optimize-route`, method POST, Bearer header present, and body preserves both values.

- [ ] RED BFF tests: mock `requireAdmin` and `optimizeRoutes`. Valid `or_opt` reaches the third optimizer argument after auth. Invalid local search returns 400 and never calls optimizer.

- [ ] RED page source contract: page imports/calls `adminApi.routes.optimize`, sends `local_search_type`, and contains no executable `optimizeRoutes` import or direct optimizer URL.

- [ ] Run RED:

~~~~powershell
npm test -- --run src/lib/admin-api.test.ts src/app/api/optimize-route/route.test.ts "src/app/(app)/admin/route-test/page.bff-contract.test.ts"
~~~~

- [ ] Extend admin helper parameters/payload:

~~~~typescript
local_search_type?: "none" | "two_opt" | "three_opt" | "or_opt" | "hybrid";
max_travel_time?: number;
~~~~

Keep existing authenticated `adminFetch("/api/optimize-route", ...)`.

- [ ] Add BFF Zod field:

~~~~typescript
local_search_type: z.enum(["none", "two_opt", "three_opt", "or_opt", "hybrid"]).optional(),
~~~~

Destructure and forward it. Replace page runtime optimizer-service import and manual student/depot call with:

~~~~typescript
const response = await adminApi.routes.optimize({
  start,
  end,
  waypoints,
  strategy: normalizeAlgorithmName(algorithm),
  local_search_type: algorithmSupportsLocalSearch(algorithm) ? localSearchType : undefined,
  max_travel_time: 180,
});
~~~~

Do not redesign unused `end` behavior.

- [ ] Run focused tests, `npm test -- --run`, and `npm run typecheck`.

- [ ] `git diff --check`; commit six files as `fix(web): route optimizer test through authenticated BFF`.

---

### Task 5: Evidence-Based Dependency Pruning

**Files:** create `src/lib/dependency-manifest-contract.test.ts`; modify `package.json` and `package-lock.json`.

- [ ] Before mutation, save `npm explain` output for all five candidates under ignored `.superpowers/sdd/dependency-before.txt`. Remove `@genkit-ai/ai` only if `genkit` retains it transitively.

- [ ] RED test reads package and lock root metadata and asserts these direct edges absent: `@genkit-ai/ai`, `@genkit-ai/firebase`, `@genkit-ai/google-genai`, `@genkit-ai/next`, `@typespec/compiler`. It also asserts `genkit`, `@genkit-ai/googleai`, and `xlsx` remain. If evidence disproves `@genkit-ai/ai` removal, exclude only that name and document why.

- [ ] Run RED: `npm test -- --run src/lib/dependency-manifest-contract.test.ts`. Expected: candidate declarations fail.

- [ ] Run normal npm operation:

~~~~powershell
npm uninstall @genkit-ai/firebase @genkit-ai/google-genai @genkit-ai/next @typespec/compiler @genkit-ai/ai
~~~~

Omit `@genkit-ai/ai` only under the evidence exception. Do not hand-edit transitive resolutions.

- [ ] Run GREEN; capture fresh `npm explain` for each candidate and `npm audit --omit=dev --json` under ignored `.superpowers/sdd`. Report exact audit counts and nonzero exit. Root-edge absence—not disappearance of every transitive node—is acceptance.

- [ ] Run full Vitest, typecheck, lint; record lint error/warning counts.

- [ ] `git diff --check`; commit three files as `chore(web): prune unused direct dependencies`.

---

### Task 6: Immutable Code Verification Snapshot

**Files:** ignored `.superpowers/sdd/post-audit-verification.md` only.

- [ ] Record base SHA, `git rev-parse HEAD` as the last code-bearing commit, clean status, executable versions, and `git diff --check`.

- [ ] Run:

~~~~powershell
& C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-post-audit-full --tb=short
npm test -- --run
npm run typecheck
npm run lint
~~~~

Record exact passes/fails/skips/warnings and elapsed times.

- [ ] With no untracked `.env*`, run credential-free `npm run build` using a child environment that removes exactly the three Supabase variables and restores them in `finally`. A different env crash is failure.

- [ ] Run `npm audit --omit=dev --json` and `npm explain @genkit-ai/ai` / `@genkit-ai/firebase`. Record exact paths/counts even on nonzero exit.

- [ ] Write all exact commands/results to the ignored report; confirm worktree clean.

---

### Task 7: Synchronize Six Authority Documents

**Files:** modify `README.md`, `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, `UniRide_Ultimate_Audit.md`, `WORKLOG.md`; create `NEXT_PHASE_EXECUTION_ROADMAP.md`.

- [ ] From Task 6, create an ignored fact table for base SHA, last code-bearing SHA, all gate counts, build result, audit counts, removed root edges, closures, and open boundaries. All six docs copy this truth.

- [ ] Correct the five existing docs:
  - README: current Dual-Engine/setup/status/authority links; no browser-direct optimizer workflow or obsolete DataLoader/Pydantic claim.
  - Architecture: scoped closures for occurrence identity, split decoder, Bildiri extraction, matrix repository, seed-0, and quick fixes; universal feasibility/security/durability/provenance/GIS remain open.
  - Roadmap: close only verified quick fixes; universal feasibility is first; link detailed roadmap; waiver is not remediation.
  - Ultimate Audit: dated scoped closure notes, remove stale PSO wall-clock seed claim, retain open production findings.
  - Worklog: prepend 2026-08-10 entry with immutable commits, exact commands/results, paths, closures/open work, audit/build evidence, and original-checkout preservation.

- [ ] New roadmap must contain verified baseline/non-goals, common entry/exit protocol, and these packages/orders:
  1. Universal feasibility — DeepSeek, Big Pickle, Terra, Luna.
  2. Compute auth/typed budgets/compare — Big Pickle, Terra, Luna, DeepSeek; move DeepSeek forward for solver semantics.
  3. Durable jobs/cancellation — Terra, DeepSeek, Big Pickle, Luna.
  4. Frontend BFF/state/warnings — Terra, Luna, Big Pickle, DeepSeek.
  5. Matrix provenance/metric separation — Big Pickle, Terra, DeepSeek, Luna.
  6. Academic TSP/ATSP/CVRP campaign — DeepSeek, Big Pickle, Terra, Luna.
  7. Backend geometry contract then GIS renderer — Terra, Luna, Big Pickle, DeepSeek.

For every package include scope, dependencies, entry/exit gates, exact verification, and one complete copy/paste prompt with: role/model, objective, `<REPOSITORY_PATH>`, verified context, scope, exclusions, authorization, CodeGraph-first/TDD workflow, exact checks, eight-part return package, and external-result verification rule. No unavailable model may be silently substituted.

- [ ] Check all six docs contain identical immutable commits/results; search and correct stale `159 warnings`, `99 vulnerabilities`, PSO wall-clock-seed, universal-feasibility-complete, and implemented-GIS claims. Temporary branch name is not permanent truth.

- [ ] `git diff --check`; stage six docs; commit `docs: synchronize post-audit project truth`.

---

### Task 8: Final Review Gate

**Files:** ignored review artifacts only unless a reviewer confirms a defect.

- [ ] Re-run complete Python, Vitest, typecheck, lint, credential-free build, audit evidence, `git diff --check`, and status.

- [ ] Generate a full review package from base `0b4bef6e77d4eda2812cbe773296978862c25599` to HEAD containing commits, stat, and `git diff -U10`. Never use `HEAD~1`.

- [ ] Independent reviewer judges spec compliance, code quality, unauthorized scope, and six-doc consistency. One bounded fixer handles all Critical/Important findings, runs focused tests, and returns for re-review.

- [ ] Finish with a clean feature worktree and untouched original checkout. Do not merge or push. Return commits, changed files, commands/results, audit debt, remaining risks, and recommended integration action.
