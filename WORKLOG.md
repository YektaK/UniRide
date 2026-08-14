# UniRide Worklog

This is a curated chronology. It records verified work and does not turn archived reports or agent assertions into current truth.

## 2026-08-14 — Package B compute policy: final verification and documentation synchronization

**Scope.** The Package B compute-policy branch was independently re-verified at HEAD `ed54d5cebdc849fb0df2743692f0eca385a4750a` in isolated worktree `.temp\worktrees\package-b-compute-policy-20260812`. At that evidence tip, the branch was 19 commits ahead of clean `origin/WIP` at `b9becba1cded4dcfa897cecab9046b322b3be5d7`. The initial Task 8 gates ran at `b0b3a11`; the post-audit Python gates below ran after the documentation and auth-test isolation follow-ups at `ed54d5c`.

**Evidence-bearing Package B commit list through `ed54d5c`** (oldest to newest; 3 documentation commits, 7 task commits, 9 follow-up fixes):

| Commit | Subject |
| --- | --- |
| `419c8e466db5632e35b4f17495f412356d776e9a` | `docs: specify Package B compute policy` |
| `4789a730750073d7368110857e6897e43e662bae` | `docs: plan Package B compute policy` |
| `882e602b7627908d9a9d5e497fe784a43c3a347e` | `feat(api): protect production compute routes` |
| `bf51eef603ee3ed2b561e43697bd27d408bdd843` | `fix(api): reject non-ascii auth keys safely` |
| `2037590652260763032bb8605993d25d2388894b` | `feat(api): add conservative compute profile` |
| `0c5bf75b87f3c9a7f755d29744f1e6fb388202cf` | `fix(api): reject malformed compute policy enums` |
| `ba3894748eb69464b565e1936fcbcbae23eca709` | `feat(api): canonicalize strategy aliases` |
| `89f2a3da99b1188cb9ae8ea0451beeb7fa156599` | `fix(api): fail closed on strategy registry drift` |
| `e94509d0ed7d17287be6a8ee09971409971de56a` | `feat(api): apply request-local compute budgets` |
| `ca0f1141a325c4902227121c9d5f74b75b61f3ab` | `fix(api): enforce evidence-based solver budgets` |
| `f694f712e15bdc359f16d97be8348ae8a0a9e1f8` | `feat(api): bound canonical comparison execution` |
| `d76c62f0279ce4e258596cefa3d0c9dcc30a8600` | `fix(api): preserve truthful comparison policy metadata` |
| `10852e0eeeb9bd837eb536e0bfaa2e724f4d422a` | `fix(core): reject oversized exact TSP requests` |
| `8836972e581690dd5e3206c598637e1ebd06cd90` | `fix(api): preflight oversized exact comparisons` |
| `d9a5f4632c884697b6e347c0fc75c05eb29abe2a` | `feat(web): authenticate server optimizer calls` |
| `edabf29e79c84751679c9843840ddfff7df80f42` | `fix(web): harden optimizer transport boundary` |
| `b0b3a11fb4374c0470f4b6762251483f8f8ac81b` | `fix(web): sanitize optimizer transport failures` |
| `8da15ddeb6aa572abf27844da014c839d773ca97` | `docs: record production compute policy` |
| `ed54d5cebdc849fb0df2743692f0eca385a4750a` | `fix(test): isolate stale auth-guard tests; correct full-suite baseline claim` |

**Changed boundaries (verified against live source).**

- Heavy endpoints `POST /api/v1/optimize`, `POST /api/v1/compare`, and `POST /api/v1/vehicle-calculator` deny missing/wrong internal keys with 403 (constant-time comparison, router-level dependency). `/health`, `/api/v1/strategies`, and the time-window/schedule utilities remain public. `UNIRIDE_DISABLE_AUTH=1` is a startup error under `APP_ENV=production` (`optimizer_api/runtime_config.py:37-50`).
- The frozen `production-conservative-v1` profile (`optimizer_api/compute_policy.py:25-36`) fixes 250 students, 50 vehicles, 6 algorithms, 2 workers, 120s soft deadline, 60 solver seconds, 2,000 iterations, 250 population, 2s local search. The nine `UNIRIDE_COMPUTE_*` overrides may only lower ceilings; invalid values fail at startup.
- Strategies resolve to one canonical identity per request; each run gets a fresh factory instance and fails closed on name drift (`optimizer_api/strategies/canonical.py:46-57`).
- `/compare` runs at most 2 canonical workers under one 120-second **soft** response deadline (`optimizer_api/routers/optimization.py:427,438-468`); results are admitted only with a feasible Package A certificate and ranked deterministically; pending threads are not waited on (`wait=False`), so Package B is **not** hard cancellation.
- Exact/permutation requests above ten waypoints fail fast via `ExactTSPSizeError` before the solver runs (`uniride_core/algorithms/string_exact_tsp.py:11-30`, router preflight `optimization.py:67-76,136-137,312-313,412-419`).
- Next.js server code calls heavy endpoints only through server-only `optimizerFetch` (`src/lib/optimizer-server.ts:1-14`); the internal key is never exposed via `NEXT_PUBLIC_*`; the browser boundary test blocks it from client code.

**Immutable verification snapshot (2026-08-13).**

```powershell
& .venv-jit\Scripts\python.exe -m pytest optimizer_api\tests\test_package_b_compute_auth.py optimizer_api\tests\test_package_b_compute_policy.py optimizer_api\tests\test_package_b_canonical_resolution.py optimizer_api\tests\test_package_b_tuning_applicability.py optimizer_api\tests\test_package_b_native_runtime.py optimizer_api\tests\test_package_b_optimize_boundary.py optimizer_api\tests\test_package_b_compare_orchestration.py uniride_core\tests\test_string_exact_tsp.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-pkg-b-focused
& .venv-jit\Scripts\python.exe -m pytest optimizer_api\tests uniride_core\tests academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-pkg-b-full --tb=short
npm test -- --run
npm run typecheck
npm run lint
npm run build
git diff --check
```

- Focused Package B gate: **1,453 tests passed in 12.70s**, zero failures.
- Full affected suites: **2,295 passed, 1 skipped, 3 warnings, 136.92s**. The single remaining failure is `test_matrix_repository.py::test_provider_timeout_plumbed_into_sdk_client`, a genuinely pre-existing Supabase SDK provider-timeout drift (that file is unchanged from base). The 1 skip is `academic_benchmark/tests/test_numba_three_opt.py` (Numba unavailable). **Correction:** an earlier draft of this entry described "20 pre-existing auth order-pollution failures"; that attribution was wrong. Those 20 failures were branch-induced suite-consistency failures — stale Phase 0 tests asserting the old always-deny auth contract — and were fixed as part of the audit follow-up documented below.
- Vitest **21 files / 58 tests passed in 94.71s** (vitest 4.0.18). TypeScript passed. ESLint **0 errors / 158 warnings**.
- Credential-free `npm run build` passed (Next.js 16.1.6, webpack) with **57 static pages**; Supabase missing-env build warnings are expected in a credential-free environment.
- `git diff --check` clean; final worktree status clean.

**Documentation outcome.** Updated `README.md` (verification status, env-var table with `OPTIMIZER_INTERNAL_API_KEY` and the nine `UNIRIDE_COMPUTE_*` variables, new compute-policy section), `CURRENT_ARCHITECTURE.md` (production request path, verified closures, open boundaries, execution/concurrency, verification baseline), `ACTIVE_ROADMAP.md` (completed scoped work, updated Priority 1/2 status with remaining scope), and this worklog. The 2026-08-10 figures were superseded by the initial 2026-08-13 gates and the 2026-08-14 independent rerun below.

**Waivers and remaining risk (documented, not closed).**

- The 158 ESLint warnings continue under a temporary waiver; Priority 4 debt remains.
- `npm audit --omit=dev --json` still exits 1 with 84 findings (2 critical, 22 high, 59 moderate, 1 low).
- Package B provides a **soft** response deadline only: no hard solver cancellation, process isolation, durable jobs, or rate limiting. The exact/permutation fail-fast boundary covers the canonical permutation/exact paths, not every solver family.
- The single remaining full-suite failure (`test_matrix_repository.py`) is genuine pre-existing Supabase SDK provider-timeout drift; the 20 auth failures noted in the earlier draft were branch-induced and are now fixed (see follow-up below).

## 2026-08-14 — Package B audit follow-up: auth suite-consistency fix and doc correction

**Audit.** A final correctness audit of `codex/package-b-compute-policy-20260812` found that the initial documentation claim about "20 pre-existing auth order-pollution baseline failures" was false. Root cause, verified against live source:

- `require_internal_api_key` had no `UNIRIDE_DISABLE_AUTH` bypass at the base; Package B wired in `if internal_auth_disabled(): return` (`optimizer_api/auth.py:16-17`).
- `optimizer_api/tests/test_optional_solver_api.py:9` contains the pre-existing, unchanged module-level `os.environ.setdefault("UNIRIDE_DISABLE_AUTH", "1")`. At the base this was inert; on this branch it activates the bypass for the rest of the suite.
- Stale Phase 0 deny-contract tests (`test_phase0_auth_guard.py` g1/g3, `test_api_hardening_phase0.py` b1/b4, `test_phase0_containment.py::test_internal_key_is_required_and_rejects_mismatch`) assert 403 with a key unset/absent header but never clear `UNIRIDE_DISABLE_AUTH`, so under pollution they observe 200/400/404 instead of 403. These 20 failures are branch-induced suite-consistency failures, **not** pre-existing baseline debt.
- Mechanism reproduced: `test_phase0_auth_guard.py` alone → 12 passed; preceded by `test_optional_solver_api.py` → 4 failed (g1×3 got 400/404, g3 got 200). CI does not catch this because the focused job runs `test_phase0_containment.py` but not the polluter, and the focused Package B gate excludes all four stale files.

**Fix (surgical).** Added the plan's own isolation pattern, `monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)`, to the deny-contract tests in `test_phase0_auth_guard.py` (g1, g3), `test_api_hardening_phase0.py` (test_b1_benchmark_endpoints_reject_missing_key, test_b1_missing_key_does_not_start_benchmark_run, test_b1_missing_key_does_not_trigger_download, test_b4_download_endpoint_does_not_fetch_without_credentials), and `test_phase0_containment.py` (test_internal_key_is_required_and_rejects_mismatch). The polluter line is pre-existing and left unchanged.

**Re-verified results (post-fix).**

```powershell
python -m pytest optimizer_api/tests/test_optional_solver_api.py optimizer_api/tests/test_phase0_auth_guard.py optimizer_api/tests/test_phase0_containment.py optimizer_api/tests/test_api_hardening_phase0.py -q -p no:cacheprovider
python -m pytest optimizer_api/tests -q -p no:cacheprovider
python -m pytest optimizer_api/tests uniride_core/tests academic_benchmark/tests/test_production_registry_snapshot.py -q -p no:cacheprovider
```

- Polluter-first reproduction file set: **75 passed** (previously 4 failed).
- `optimizer_api/tests`: **1,960 passed, 1 failed (matrix drift), 3 warnings, 105.46s**.
- Full affected suites: **2,295 passed, 1 failed (matrix drift), 1 skipped (Numba), 3 warnings, 136.92s**.
- Focused Package B gate: **1,453 passed in 12.70s**.

**Independent controller re-verification at `ed54d5c` (2026-08-14).**

- Polluter-first auth-isolation set: **75 passed in 14.32s**.
- Focused Package B gate: **1,453 passed in 37.37s**.
- Full affected suites: **2,295 passed, 1 failed, 1 skipped, 3 warnings in 167.78s**. The failure remained `test_matrix_repository.py::test_provider_timeout_plumbed_into_sdk_client`.
- The same provider-timeout test failed on clean `WIP` at `b9becba1` (**1 failed in 3.23s**), confirming it is baseline Supabase SDK drift rather than a Package B regression.

**Documentation correction.** The earlier "21 pre-existing baseline failures" claim was corrected in `WORKLOG.md`, `README.md`, `CURRENT_ARCHITECTURE.md`, and `ACTIVE_ROADMAP.md`: 20 were branch-induced stale-test failures fixed in this follow-up; the single `test_matrix_repository.py` failure is genuine pre-existing Supabase SDK drift (file unchanged from base).

**Known remaining (unrelated to this audit).** The optional cosmetics noted by the audit (timed-out compare results reporting `execution_time_seconds=0.0`, and `cancellation_mode="soft_response_deadline"` being emitted when no run is runnable) are still open and out of scope here. `test_phase0_auth_guard.py`'s docstring still references the pre-Package B G3 startup-guard wording; the tests themselves assert the new contract.

## 2026-08-10 — Post-audit quick fixes, immutable verification, and documentation synchronization

**Scope.** Work began from verification base `0b4bef6e77d4eda2812cbe773296978862c25599` in isolated worktree `C:\tmp\UniRide-post-audit-quickfixes`. The last code-bearing commit validated before this documentation update was `ddd85e8b1cc5ed64a8163988b2e179a08c8cfd2f` (`chore(web): prune unused direct dependencies`). The original dirty rescue checkout was preserved and not switched, staged, restored, cleaned, merged, or modified.

**Code commits in the bounded quick-fix package.**

| Commit | Subject |
| --- | --- |
| `0449a66111a0facefadb60347c33f17a9a60fb2d` | `test(pytest): constrain discovery to canonical suites` |
| `3fe0809e4d6895588f4bf053e72d367c146da20a` | `fix(api): make optional solver surfaces null-safe` |
| `5e048ec18fa7346a03b0553d60e95e21704b5988` | `fix(web): defer Supabase clients until requests` |
| `7eb9c254d9a9d43dcbaaa6e4b521c699bc5793e3` | `fix(web): route optimizer test through authenticated BFF` |
| `ddd85e8b1cc5ed64a8163988b2e179a08c8cfd2f` | `chore(web): prune unused direct dependencies` |

**Verified corrections.**

- Default pytest discovery is restricted to `uniride_core/tests`, `optimizer_api/tests`, and `academic_benchmark/tests`; manual scripts are not default collection targets.
- Health/default compare enumeration tolerates unavailable optional solvers while the strategy listing retains registry-declared unavailable rows.
- Supabase clients are created during request execution rather than route/proxy import; the credential-free production build is now a passing gate.
- The admin route-test UI calls the authenticated same-origin `/api/optimize-route` BFF and preserves local-search selection. This is not a general compute-authentication change.
- Removed direct root dependency edges: `@genkit-ai/ai`, `@genkit-ai/firebase`, `@genkit-ai/google-genai`, `@genkit-ai/next`, and `@typespec/compiler`. Retained Genkit packages still bring some components transitively.

**Immutable verification snapshot.**

```powershell
& C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-post-audit-full --tb=short
npm test -- --run
npm run typecheck
npm run lint
npm run build
npm audit --omit=dev --json
git diff --check
git status --short --branch
```

- The first Python attempt timed out in the execution harness after 124070ms before output; one authorised longer rerun passed **1,676 tests with 48 warnings in 238.17s**.
- Vitest passed **17 files / 37 tests** in **2.83s**. TypeScript passed. ESLint passed with **0 errors / 158 warnings**.
- A child environment removed and restored exactly `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`; `npm run build` passed. No root `.env*` file was present before or after the gate.
- `npm audit --omit=dev --json` exited 1 with **84 findings**: **2 critical, 22 high, 59 moderate, 1 low**. This remains unresolved dependency-security debt, not a failed functional test or remediation.
- Final worktree status was clean and `git diff --check` passed.

**Documentation outcome.** Updated `README.md`, `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, `UniRide_Ultimate_Audit.md`, and this worklog; added `NEXT_PHASE_EXECUTION_ROADMAP.md`. The documents now distinguish scoped closures from open universal feasibility, general compute protection, durable jobs, matrix provenance, frontend resilience, academic validation, and GIS work.

## 2026-08-01 — WIP consolidation and rescue preservation

- Consolidated validated work into `WIP` while preserving the original rescue checkout and tags.
- Earlier build, warning, and npm-audit dispositions were temporary consolidation evidence only. They are superseded by the 2026-08-10 verification figures above.
- Re-verified that the `DataLoader` singleton facade is intentional; matrix lifecycle work belongs in the repository/provenance boundary rather than a claim that every lookup creates a new singleton.

## 2026-07-24 to 2026-07-27 — Bildiri canonical extraction

- Canonicalized active Bildiri GWO/HHO/Numba behavior into the shared core boundary.
- Quarantined legacy Bildiri evidence with reproducible manifest checks and protected zero-active-import rules.
- Preserved fixed-budget and native-termination protocol separation; archived/pilot evidence is not publication proof.

## 2026-07-22 — YAEM quarantine and contract foundation

- Quarantined legacy YAEM evidence and established manifest/archive contract checks.
- Kept historical files available as evidence while excluding them from active execution and current-architecture claims.

## April–June 2026 — Dual-engine exploration

- Established production versus academic rationale, cluster-first and giant-tour/split research tracks, reference solver roles, and early DOE ideas.
- Retained useful methodology: fixed/paired seeds, versioned datasets, held-out instances, feasibility-first reporting, and reproducibility records.
- Treated projected improvements and historical “complete” claims as hypotheses unless later executable evidence confirmed them.

## Documentation rule

Current authority order is live code/tests first, then [UniRide_Ultimate_Audit.md](UniRide_Ultimate_Audit.md), [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md), [ACTIVE_ROADMAP.md](ACTIVE_ROADMAP.md), and [NEXT_PHASE_EXECUTION_ROADMAP.md](NEXT_PHASE_EXECUTION_ROADMAP.md). Everything under `archive/` is historical context, not current truth.
