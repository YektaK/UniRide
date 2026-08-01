# WIP Consolidation Manifest — 2026-08-01

## Immutable heads

| Ref | Full SHA | Treatment |
|---|---|---|
| `origin/WIP` | `a44d50631d826f81fd2a6bb1b73baa4a46e5fa1f` | Preserve as annotated `archive/pre-wip-consolidation-20260801`; do not move in this task. |
| `codex/local-rescue-20260721` | `e0824b42d2251cfd479207d756798913a2313b31` | Preserve as annotated `archive/local-rescue-20260721`; selective reconstruction only. |
| C1 validated spine | `08820813a4657d62bb81c44a6a671984c846e28b` | Authoritative academic spine and hash baseline. |
| Consolidation branch at baseline | `7ffe49c9e249752b8a7f1cf0663d10b6a37e968b` | Descends from C1 and `origin/WIP`; documentation/plan commits only before this manifest. |

### Preservation record

- `git fetch --prune origin` completed without output; `git status --short --branch` reported only `## codex/wip-consolidation-20260801`.
- `git merge-base --is-ancestor 08820813a4657d62bb81c44a6a671984c846e28b HEAD` and `git merge-base --is-ancestor origin/WIP HEAD` both exited `0`.
- Neither required tag name existed before creation. Local tag peeling verifies `archive/pre-wip-consolidation-20260801^{}` = `a44d50631d826f81fd2a6bb1b73baa4a46e5fa1f` and `archive/local-rescue-20260721^{}` = `e0824b42d2251cfd479207d756798913a2313b31`.
- `archive/pre-wip-consolidation-20260801` was pushed and remotely verified: annotated object `309f0e8987339205d9809471b0b8bbcf7dc0f620`, peeled target `a44d50631d826f81fd2a6bb1b73baa4a46e5fa1f`.
- GitHub rejected `archive/local-rescue-20260721`: `refusing to allow an OAuth App to create or update workflow .github/workflows/ci.yml without workflow scope`. A subsequent remote archive-tag listing confirms this tag is absent. This is a WIP-promotion blocker requiring workflow-scoped authentication; independent consolidation Tasks 2–6 may continue.
- No branch was pushed or moved in Task 1.

## Rescue admission ledger

| Commit | Path/hunk | Decision | Live evidence | Validation |
|---|---|---|---|---|
| `3eea998` | all academic hunks | superseded | Package B/C1 ancestry | academic baseline |
| `092efe3` | entire patch | superseded | `git cherry` reports patch-equivalent | none |
| `253155c` | entire patch | superseded | `git cherry` reports patch-equivalent | none |
| `61c36c1` | optimizer API localhost binding | admit | C1 binds `0.0.0.0` | runtime config tests |
| `61c36c1` | CLI arbitrary-path removal | admit | C1 accepts `filepath` | containment tests |
| `61c36c1` | optional CLI internal key | admit | C1 CLI endpoints unguarded | auth tests |
| `61c36c1` | `src/proxy.ts` internal-key forwarding | reject | header is not forwarded by Next route fetches | source trace |
| `dcd5896` | Pydantic pair alignment | admit | pyproject pinned, optimizer requirements broad | dependency tests |
| `dcd5896` | NumPy/Numba minimums | admit | pyproject names unbounded | dependency tests |
| `ea75581` | direct ESLint gate and declared packages | admit | `next lint` script is invalid on Next 16 | npm/lint gate |
| `1e42652` | `requirements-lock.txt` | reject | historical platform lock is not independently required | manifest check |
| `1e42652` | `optimizer_api/routers/benchmark.py` | reject as a historical hunk | Task 2 recreates tested security behavior | containment tests |
| `1e42652` | `uniride_core/algorithms/tsplib_parser.py` | reject | canonical C1 academic spine | unchanged hash |
| `1e42652` | `ACTIVE_ROADMAP.md` and `WORKLOG.md` | reject | stale historical text | current manifest only |
| `1e42652` | CI, flat ESLint config, bounded UI lint hunks | admit per listed path | reproducible lint errors | lint/type/test gates |
| `e0824b4` | use-mobile hydration fix | admit | current hook mutates state in effect and differs on SSR | hook test and lint |
| `e0824b4` | sandbox encoding repair | admit only for six verified mojibake literals | current source reproduces the text corruption | focused diff and typecheck |

`git cherry -v origin/WIP codex/local-rescue-20260721` reported `- 092efe367aa9e98be59d37b25c0b9c1cdfe3b667` and `- 253155cba81504da347271e46fd20eecff64d6e8`, confirming patch equivalence. All `+` entries remain candidates governed by the table above; no rescue patch was cherry-picked or merged.

## C1 evidence inventory

| Path | Git blob hash |
|---|---|
| `academic_benchmark/numba_results/benchmark_progress.csv` | `62c8e0cf9be90558200a8343be3424db858ee056` |
| `academic_benchmark/numba_results/benchmark_summary.csv` | `72a1c47f1dce038cbe16d46e21095de239f8ac28` |
| `academic_benchmark/numba_results/best_params_numba.json` | `bafa25680ce7c79df9117d09756c0f09b400bc52` |
| `academic_benchmark/numba_results/bildiri_import/benchmark_progress_20260513_003803.csv` | `1b2f3b199dc2d656f19c26ea740124dfc1f35508` |
| `academic_benchmark/numba_results/bildiri_import/benchmark_summary_20260513_003803.csv` | `e95989c34a4e6d04ca3ec211ff365909acf6bc9c` |
| `academic_benchmark/numba_results/bildiri_import/import_report_20260513_003803.json` | `8d29822256c61d77a1332bc2acbb948ff786bf83` |
| `academic_benchmark/numba_results/tuning_progress.csv` | `76dd50dcd4b73ff75f34f735f0b8178af9eed710` |
| `academic_benchmark/sota_results/benchmark_progress.csv` | `f7314f75aac6fa86d5d33d08311f2f2123f0178d` |
| `academic_benchmark/sota_results/benchmark_summary.csv` | `4bf42a5049efb26f4f3421181dc5d079d415b77a` |
| `academic_benchmark/sota_results/doe_sota/tuning_progress.csv` | `f4c0d2e038d729fed55444f81fc2b4e7a1fd9437` |

These are Git blob hashes computed from `0882081`, not workspace copies. No benchmark output was generated or added to the index by this task.

## Baseline environment and results

- Working directory: `C:\\tmp\\UniRide-consolidate-20260801`
- JIT interpreter: `C:\\Users\\yektakayman\\Desktop\\AiCode\\FirebaseUniRide\\UniRide\\.venv-jit\\Scripts\\python.exe` (`Python 3.14.3`)
- pip: `pip 26.1.2` from the JIT environment (Python 3.14)
- Ignored `node_modules` junction: diagnostics only; `npm ci` was not run.

| Command | Result |
|---|---|
| `& $JIT_PY -m pip check` | PASS — `No broken requirements found.` |
| `& $JIT_PY -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short` | PASS — 786 passed, 42 warnings, 50.26s. Warnings are deprecation warnings for legacy algorithm identifiers. |
| `& $JIT_PY -m pytest uniride_core/tests optimizer_api/tests -q -p no:cacheprovider --tb=short` | BLOCKED — 2 collection errors and 1 skipped in 2.78s: `ModuleNotFoundError: No module named 'fastapi'` when importing `optimizer_api.routers.benchmark`. |
| `.\\node_modules\\.bin\\eslint.cmd src --ext .ts,.tsx` | BASELINE RED — 24 errors, 7 warnings (31 problems), matching the expected lint baseline. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` | PASS — exit 0, no diagnostics. |
| `.\\node_modules\\.bin\\vitest.cmd run` | PASS — 3 test files and 15 tests passed (Vitest 4.0.18; 1.17s). |

## Boundaries and next checks

- This commit is documentation/evidence only. It does not modify production code, tests, dependencies, lockfiles, generated artifacts, source branches, or WIP.
- Before admitting any `admit` ledger item, reconstruct only the listed behavior in current C1 files and run its listed focused validation plus the full matrix.
- Before WIP promotion, workflow-scoped authentication must push and remotely peel-verify `archive/local-rescue-20260721`; the `fastapi` baseline environment blocker must also be resolved or handled through the design's explicit user-waiver policy.

## Task 2 containment reconstruction evidence

- Admitted `61c36c1` localhost binding through dynamic `optimizer_host()`; the default is loopback and `OPTIMIZER_HOST` remains an explicit runtime override.
- Admitted CLI arbitrary-path removal: `/cli/import` and `/cli/preview` now accept only a filename resolved beneath `CLI_RESULTS_DIR` or `CLI_RESULTS_NUMBA_DIR`; traversal and resolved symlink escapes are rejected. CLI listings no longer expose `filepath`.
- Admitted optional internal-key protection only on `/api/v1/benchmark/cli/files`, `/cli/import`, and `/cli/preview`; `INTERNAL_API_KEY` is read at request time and compared with `secrets.compare_digest`.
- Rejected `src/proxy.ts` internal-key forwarding remains unchanged because the historical header was not forwarded by the Next route fetches to the Python backend.
- RED: `& .\\.venv-consolidation\\Scripts\\python.exe -m pytest optimizer_api/tests/test_phase0_containment.py -q -p no:cacheprovider --tb=short` failed at collection with `ModuleNotFoundError: No module named 'optimizer_api.auth'`, before implementation.
- GREEN: `& .\\.venv-consolidation\\Scripts\\python.exe -m pytest optimizer_api/tests/test_phase0_containment.py optimizer_api/tests/test_benchmark_router_problem_loading.py -q -p no:cacheprovider --tb=short` passed: 23 passed in 3.59s.
- Scope check: no academic code, dependency files, `src/proxy.ts`, refs, tags, remotes, or pre-existing `uniride.egg-info` changes were modified by this task.
- Follow-up RED: the new response-level listing test failed because `scan_directories` returned absolute temporary result roots. Follow-up GREEN: the focused suite passed `24 passed in 1.13s` after mapping configured roots to basenames while preserving the list key and shape.
- Follow-up files: `optimizer_api/routers/benchmark.py` and `optimizer_api/tests/test_phase0_containment.py`; no other behavior changed.
- Final API follow-up: the late-missing-file checks cover disappearance both after safe resolution and at `open()` after the `isfile()` precheck. `& .\.venv-consolidation\Scripts\python.exe -m pytest optimizer_api/tests/test_phase0_containment.py optimizer_api/tests/test_benchmark_router_problem_loading.py -q -p no:cacheprovider --tb=short` passed: 26 passed in 1.06s. Both serialized 404 responses are generic `File not found` and omit the resolved temporary root.

## Task 3 dependency-contract evidence

- RED: `& .\.venv-consolidation\Scripts\python.exe -m pytest academic_benchmark/tests/test_dependency_manifest.py -q -p no:cacheprovider --tb=short` failed as intended: the new NumPy/Numba-floor and optimizer Pydantic-pair assertions failed; the two existing assertions passed.
- GREEN: the same manifest test passed: `4 passed in 0.34s`.
- Environment consistency: `& .\.venv-consolidation\Scripts\python.exe -m pip check` passed: `No broken requirements found.`
- Scope check: only the four authorized files changed: the manifest test, `pyproject.toml`, `optimizer_api/requirements.txt`, and this consolidation manifest; no lockfile, generated metadata, environment, or academic solver code was touched.

## Task 4 frontend lint and hydration evidence

- RED: `.\\node_modules\\.bin\\vitest.cmd run src/hooks/use-mobile.test.tsx` failed exactly because the direct contract did not contain `useSyncExternalStore`; the resize behavior test passed, proving it alone could not distinguish the legacy effect hook.
- RED: `.\\node_modules\\.bin\\eslint.cmd src --ext .ts,.tsx` reported 24 errors and 7 warnings (31 problems).
- Admitted only the 21 TypeScript/TSX paths named by `git show --name-only 1e42652 -- src`, including the duplicate mobile-hook modules, the approved six sandbox mojibake literals, direct ESLint package/config files, the hook test, and this manifest. No API, academic, workflow, roadmap, or worklog hunk was imported.
- `npm install --package-lock-only --ignore-scripts` completed successfully; no dependency installation or lifecycle script was run through the ignored `node_modules` junction.
- GREEN: focused hook test passed 2/2; `npm run typecheck` passed; `npm test -- --run` passed 4 files / 17 tests; and `git diff --check` passed.
- `npm run lint` exited 0 with zero lint errors, but the approved at-most-7 warning cap is not met: 159 warnings surfaced (69 `@typescript-eslint/no-unused-vars`, 67 `@typescript-eslint/no-explicit-any`, 19 `react-hooks/exhaustive-deps`, 4 `react-hooks/incompatible-library`). This is an unresolved protocol deviation, not a fully GREEN lint gate; promotion requires warning reduction to the approved cap or an explicit user waiver. No warning rule was suppressed and only `react/no-unescaped-entities` remains disabled.
- Scope check: no generated artifacts, unrelated dependencies or installed environment artifacts, refs, remotes, source branches, API files, academic code, CI workflow, roadmap, or worklog were modified by Task 4.
- Subsequent frontend final fix `a147027` stabilized sandbox skeletons and IDs; its committed coverage includes `sandbox-vehicle-id.test.ts` and `sidebar.test.tsx`. It is recorded here only as post-Task-4 evidence; this remediation does not edit frontend files.

## Task 5 WIP CI evidence

- Admitted the bounded `1e42652` CI candidate as a new `.github/workflows/ci.yml`; the pre-existing `benchmark.yml` remains unchanged.
- The workflow runs on pushes and pull requests targeting only `WIP`. Its frontend job uses Node 22 with `npm ci`, lint, typecheck, and Vitest. Its Python job uses Python 3.14, the declared JIT constraints install contract, `pip check`, collection of the active suites, and focused academic, core, and API integration tests.
- Python installs the small runtime dependency set required by the selected API tests after the constrained project test extra; it does not introduce a platform-specific `requirements-lock.txt`.
- RED: `test_ci_contract.py` failed because `.github/workflows/ci.yml` was absent.
- GREEN: `test_ci_contract.py` passed after the workflow was added. YAML is static CI configuration; no workflow run is generated during local consolidation.
- Scope check: only the CI workflow, its contract test, and this manifest changed; `.github/workflows/benchmark.yml`, dependencies, lockfiles, refs, remotes, and source branches remain untouched.

### Task 5 review hardening

- The workflow now declares top-level `permissions: contents: read`.
- The CI contract independently checks the `push` and `pull_request` blocks, each requiring the immediately nested `branches: [WIP]` value. Mutation coverage changes each trigger separately to `[main]` and proves that its dedicated assertion rejects it without a YAML-test dependency.
- The ad hoc API package install was replaced by the repository-declared `optimizer_api/requirements.txt` contract under the same academic JIT constraints as the editable test install.
- RED: the strengthened test failed on missing top-level permissions while the mutation test already passed; GREEN: `2 passed in 0.30s` after workflow hardening.
- Static YAML parsing returned `YAML_OK`; `git diff --check` passed; `.github/workflows/benchmark.yml` remains unchanged.

## Task 6 final validation and promotion decision

- Final validation head before this evidence commit: `615d8282fa5c46078be68b69eba0e927f8d3e650`; reviewed range: `08820813a4657d62bb81c44a6a671984c846e28b..615d8282fa5c46078be68b69eba0e927f8d3e650` (15 commits, `0b4b98b` through `615d828`).
- Integrity passed: artifact search printed nothing; the `0882081..HEAD` TSPLIB parser diff was empty; `git diff --check` passed; and `origin/WIP` is an ancestor of HEAD. Every C1 evidence hash was recomputed from object `0882081` and exactly matched the inventory; no benchmark artifact was generated or staged.
- JIT environment: Python `3.14.3`, pip `26.1.2`; `pip check` passed. Academic suite passed `790 passed, 42 warnings in 47.40s` (Task 1: 786 passed, 42 warnings; no failures or new skips). The exact JIT core/API suite remained environment-blocked at collection: `3 errors, 1 skipped in 3.03s`, all `ModuleNotFoundError: No module named 'fastapi'`; the third error is the newly admitted containment test, so this is the same missing-FastAPI condition, not an executed functional regression.
- Supplementary `.venv-consolidation` validation used no installation or dependency change. `pip check` passed; the core/API suite reported `450 passed, 1 skipped, 9 failed in 20.40s`, each failure returning `OR-Tools not installed. Run: pip install ortools`. This is an optional-dependency environment limitation, not a source finding.
- Frontend isolation: the initial worktree `node_modules` Junction targeted exactly the original checkout tree; only that link was removed and the original target remained present. A timed-out first `npm ci` left a verified real partial worktree directory; only that directory was then removed under explicit recovery authorization. The final clean `npm ci` passed (`1419` packages added, `1420` audited) and reported 99 dependency-audit advisories (3 low, 64 moderate, 28 high, 4 critical), recorded as dependency debt.
- Isolated frontend results: `npm run lint` passed with `0 errors, 159 warnings` (the Task 4 warning debt); typecheck passed; Vitest passed `5 files / 19 tests` in 2.98s. `npm run build` compiled and TypeScript-checked successfully, then failed page-data collection for `/api/driver/assignments` because the environment lacks a Supabase URL (`Error: supabaseUrl is required`). No dummy credential or source/config workaround was introduced.
- Whole-branch review (`git log --oneline`, `git diff --stat`, `git diff --check`, and status for `0882081..HEAD`) found no whitespace errors or product artifacts. Admitted rescue decisions remain API containment, dependency alignment, bounded lint/hydration, and WIP CI; proxy forwarding, platform lockfile, parser, stale roadmap/worklog, and other rescue content remain excluded.
- Promotion decision: **conditional hold**. Do not move WIP until all of the following are resolved or explicitly waived by the user: (1) `archive/local-rescue-20260721` is successfully pushed and remotely peel-verified with workflow-scoped authentication; (2) the JIT suite can collect with FastAPI available; (3) the supplementary OR-Tools failures are resolved; (4) the Supabase-configured production build passes; (5) the 159-warning result is reduced to the approved at-most-7 cap; and (6) the 99 npm-audit advisories receive an explicit disposition. No waiver is recorded by this manifest.
- Open post-consolidation audit backlog: wall-clock fallback seeds; Supabase explicit timeouts; CVRPTW depot `prev` feasibility; production imports of academic promoted configurations; unrecognized promoted-name pass-through; and no reusable GIS map implementation.
- Original dirty checkout reinspection showed its pre-existing dirty set unchanged. This task changes only this manifest; isolated `node_modules` and `.next` are ignored local artifacts.
