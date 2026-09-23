# UniRide Recovery and Continuation Implementation Plan

> **For agentic workers:** This document records an audit and a gated continuation plan, not blanket permission to implement every task. For an authorized implementation package, use `superpowers:executing-plans` inline, or `superpowers:subagent-driven-development` when delegation is requested. Keep one active writer per worktree.

**Date:** 2026-09-22, Europe/Istanbul

**Goal:** Recover a verifiable project baseline and continue with bounded tasks that survive model, task, and computer changes.

**Architecture:** Next.js production UI/BFF and the academic platform share neutral algorithms through `uniride_core`. Operational data, experiment evidence, and their acceptance gates remain separate.

**Tech stack observed:** Next.js 16.1.6, React 18.3.1, Vitest 4.0.18, Node 25.5.0, npm 11.8.0; Python 3.14.3, NumPy 2.4.6, Numba 0.66.0, Pydantic 2.13.4 / pydantic-core 2.46.4, FastAPI 0.141.1.

**Repository:** `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide`

**Audited HEAD:** `73618255d94f2e51ae01c8bcedbf9c1b43c9a6ff` (`WIP`).

## Global constraints

- Current authorization: detailed review, verification, planning, and these documentation artifacts. No production-code repair, dependency update, database mutation, integration, push, or deployment was performed.
- Preserve existing changes in `.gitignore`, `AGENTS.md`, and `INSTRUCTION_REVIEW_2026-09-07.md`.
- Evidence of existing behavior does not override approved requirements.
- Academic ownership, fairness, and canonical 3-opt contracts remain authoritative for their scopes.
- Do not skip academic Gates A/B/C/D. Do not confuse those names with production Packages A/B/C or Dudullu Packages 0–6.
- Fixed evaluation budgets remain the primary scientific protocol; native termination is separate. A passing test suite or smoke profile is not publication evidence.
- Use CodeGraph first when indexed. On a lock, record the failure; do not delete its database or kill a shared process as an audit workaround.
- Record only redacted readiness aggregates. Never put credentials or student records in checkpoints, task prompts, or reports.
- Follow the existing package order. Each future source change needs a bounded implementation task and appropriate verification.

## 1. Executive assessment

Luna's method is a useful starting point: one coordinator, a portable checkpoint, isolated implementation worktrees, and local verification of external results. Its repository snapshot is correct. Its project summary is incomplete because it concentrates on the most recent Dudullu work.

The project has a substantial tested implementation. It is not a completed daily-operations product or a completed academic unification/publication pipeline. Three work streams must be tracked separately:

1. **Dudullu operations:** demand domain and readiness UI exist; authenticated live readiness has no current result; preview/publication/operational flows remain gated.
2. **Shared production infrastructure:** feasibility and compute boundaries have strong test coverage; cancellation, terminal job states, durable execution, matrix provenance, and dependency security still have concrete gaps.
3. **Academic platform:** quarantine/extraction, catalog/preflight, Or-opt, ALNS, fixed/native accounting, and parity tests exist; GA/PSO promotion, four hybrid compositions, the active YAEM profile, and full downstream evidence remain unfinished.

No completion percentage is assigned: the remaining gates have very different importance and cannot be inferred from file or test counts.

## 2. Scope and method

Inspected current Git status/history, remote HEAD/default branch/CI/open PRs, all 17 registered worktree statuses, architecture and approved designs, package plans, relevant source paths and callers, and selected turns from four related Codex tasks. Ran the full canonical Python suite, full frontend suite, typecheck, lint, launcher tests, production build, launcher configuration probe, and npm production dependency audit.

This is a repository recovery audit with targeted source verification, not an exhaustive proof of every function, vulnerability exploitability, live deployment, or every historical experiment. It does not claim to have read every turn in every task or every ignored/generated file.

Tool limitations:
- `codegraph index .` failed with an EPERM database lock. `codegraph init .` reported already initialized. `codegraph explore` and `node` worked. Graph search returned archived implementations alongside current ones; import and test evidence were checked directly before drawing conclusions.
- Normal shell startup at the repository failed with error 267 / access denied; approved elevated read/test commands worked.
- Browser inventory was attempted twice with `cua.getState()`; both attempts failed with `trusted Node process exited unexpectedly; kernel reset`. No browser session or authenticated readiness response was obtained.
- Some newest Luna task turns were returned with empty item lists. The user-supplied result and the actual checkpoint file were available; inaccessible turn content was not invented.
- No external model was invoked. Historical agent reports were treated as leads.

## 3. Git, integration, and preservation

| Check | Current evidence |
|---|---|
| Local branch / HEAD | `WIP` / `73618255d94f2e51ae01c8bcedbf9c1b43c9a6ff` |
| Actual remote WIP | `git ls-remote --heads origin WIP main` returned the same SHA for WIP |
| GitHub default branch | `WIP`, verified with `gh api repos/YektaK/UniRide` |
| Last source commit | 2026-09-09, `fix(campus): unify Dudullu location defaults` |
| Remote main | `b6e9220`; not the selected integration baseline |
| Open PRs | `gh pr list --state open` returned an empty list |
| Latest WIP CI | Successful at the audited SHA: [run 34394814724](https://github.com/YektaK/UniRide/actions/runs/34394814724) |
| Existing root dirt | Modified `.gitignore`, `AGENTS.md`; untracked `INSTRUCTION_REVIEW_2026-09-07.md` and Luna's `docs/UNIRIDE_WORKSTATE.md` |
| Stash | One `autostash`; its stat shows deletion of `REVIEW_COMPLETION_SUMMARY.md` (219 lines). Preserved, not applied or dropped |

Existing unrelated files were hash-checked against the start of this audit. No branch, stash, worktree, or remote was changed. Only the checkpoint and this dated audit/plan are intentional documentation outputs.

### Worktree inventory

All listed paths existed. “Integrated” below means HEAD ancestry or patch equivalence, not permission to delete local files.

| Worktree path, relative to the stated prefix | HEAD | Status / integration |
|---|---|---|
| Repository root | 7361825 | Existing root dirt preserved |
| `C:/tmp/UniRide-benchmark-i18n-20260902` | b2ca8b1 | Clean; ancestor of WIP |
| `C:/tmp/UniRide-dudullu-daily-planner-20260825` | 7131cbd | Clean; ancestor |
| `C:/tmp/UniRide-dudullu-readiness-ui-20260903` | 0345e64 | Clean; ancestor |
| `C:/tmp/UniRide-package-a-feasibility` | b9becba | Clean; ancestor |
| `C:/tmp/UniRide-package-b-task5` | 9ac389d | Clean; 2 non-ancestor commits, both patch-equivalent in WIP |
| `C:/tmp/UniRide-package-b-task6` | 3968c97 | Clean; 2 non-ancestor commits, both patch-equivalent |
| `C:/tmp/UniRide-package-b-task7` | 9e65711 | Clean; 3 non-ancestor commits, all patch-equivalent |
| `C:/tmp/UniRide-phase1-occurrence` | 0b4bef6 | Clean; ancestor |
| `C:/tmp/UniRide-post-audit-quickfixes` | 3955199 | Clean; ancestor |
| Root `.temp/worktrees/mutation-proof-20260814` | a14f605 | Clean; ancestor |
| Root `.temp/worktrees/package-b-compute-policy-20260812` | 2d178c9 | Five modified tracked `uniride.egg-info/*` files; ancestor |
| Root `.temp/worktrees/package-b-compute-policy-spec-20260812` | 4789a73 | Clean; ancestor |
| Root `.temp/worktrees/per-tenant-auth-20260815` | fef5a2b | Clean; ancestor |
| Root `.temp/worktrees/rate-limit-20260814` | a1f53a6 | Clean; ancestor |
| Root `.temp/worktrees/requested-algo-policy-20260814` | d7a198c | Clean; ancestor |
| Root `.temp/worktrees/wip-consolidation-20260801` | 7fb9c29 | Clean; ancestor |

For the three Package B branches, `git cherry -v WIP <branch>` returned only `-` entries. An ahead/behind count alone would incorrectly suggest seven missing changes. Ignored files and the complete contents of old rescue branches were not exhaustively inventoried, so bulk cleanup is not justified.

## 4. Fresh verification, including failures

Commands ran at the audited HEAD with the existing local installation. No clean reinstall was performed.

| Command | Result |
|---|---|
| `.venv-jit\Scripts\python.exe -m pip check` | No broken requirements |
| `.venv-jit\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short -ra` | **3,380 passed, 1 skipped, 45 warnings**, 370.77 s; exit 0 |
| First `npm.cmd test -- --run` | **215 passed, 1 failed**, 39 files; one 5,000 ms timeout; exit 1 |
| `npm.cmd test -- --run src/app/api/ride-confirmation/route.test.ts` | **1 passed**, 555 ms total; exit 0 |
| Second `npm.cmd test -- --run`, after Python finished | **39 files / 216 passed**, 10.06 s; exit 0 |
| `npm.cmd run typecheck` | Passed; exit 0 |
| `npm.cmd run lint` | **0 errors, 164 warnings**; exit 0 |
| `node --test scripts/start-dudullu-local.test.mjs` | **20 passed**, no failures/skips; exit 0 |
| `npm.cmd run build` | Passed; Next.js 16.1.6, webpack, 59 route entries; exit 0 |
| `npm.cmd run dev:dudullu -- --check-only` with `UNIRIDE_PYTHON` set to `.venv-jit` | Passed; interpreter selection and npm runner probe succeeded |
| `npm.cmd audit --omit=dev --json` | **86 findings: 3 critical, 21 high, 60 moderate, 2 low**; exit 1 |
| `git diff --check` | Passed; existing LF/CRLF normalization notices only |

Python skip: `uniride_core/tests/test_pyvrp_cvrp_engine.py:3` could not import optional `pyvrp`. This is not PyVRP correctness evidence. Earlier memory-derived `_ab_dir`, missing Hypothesis, and NumPy/Numba import blockers do not describe the current tested environment.

The frontend timeout occurred in `src/app/api/ride-confirmation/route.test.ts:57` while the full Python suite was also running. The isolated file and later entire frontend suite passed without changing code or timeout settings. Resource contention/cold imports are plausible; the precise cause was not proven. Preserve the failed run, and avoid running both heavy suites together when establishing the baseline.

The existing Badge-inside-paragraph DOM warning remains in frontend tests. Lint warnings increased from the older documented 158 to 164; “lint passed” must include that qualification.

Local raw logs are under `.temp/recovery-audit-20260922-01a0c8af/`: `python-full.log`, `frontend-tests.log`, `ride-confirmation-recheck.log`, `frontend-tests-isolated.log`, `typecheck.log`, `lint.log`, `launcher-tests.log`, `build.log`, `launcher-check.log`, and `npm-audit.json`. They are ignored local evidence, not a portable substitute for the command/results table above.

### CI scope

`.github/workflows/ci.yml:12` runs frontend lint/typecheck/tests on Node 22. Its Python job uses Python 3.14, installs under JIT constraints, collects the three suites, then executes **eight focused files**, not the complete Python suite. It also does not run production build or npm audit. The successful GitHub run must be described within this scope.

`.github/workflows/benchmark.yml` has a separate PR/main/master regression workflow on Python 3.12/3.13. A direct WIP push does not trigger that workflow. The local full suite supplies broader evidence for this audit, but optional solver and live deployment gaps remain.

## 5. Completed work and its limits

### 5.1 Production foundation

Source and current tests support the scoped closures described in `CURRENT_ARCHITECTURE.md:30` and `ACTIVE_ROADMAP.md:13`:

- occurrence identity, independent feasibility admission, and directed missing-arc rejection;
- request-scoped strategy instances, canonical alias resolution, and lowering-only compute policy;
- internal-key and tenant authorization, exact-TSP size preflight, and tenant/IP rate windows;
- server-only optimizer transport;
- DUD-01 authenticated calculation and backend-effective direction persistence.

DUD-01 is integrated: `22be4b1` was merged through `df23d15`, followed by `55f7312`. Evidence is in `src/app/api/calculate-vehicles/route.ts:147`, `src/lib/admin-api.ts:333`, `src/services/route-plans.ts:151`, and `src/app/(app)/admin/vehicle-planning/page.tsx:123`. A later selector change does not relabel a previous calculation.

Campus correction `7361825` centralizes `D.Kampus` / `Dudullu` / `Doğuş Üniversitesi, Dudullu Kampüsü` and `41.001, 29.177` in `src/services/dudullu-campus.ts:1`. This fixes active code/future writes, not the correctness of every pre-existing live row.

### 5.2 Dudullu daily operations

Package 1's pure demand and wave logic exists in `src/services/daily-planning.ts:450`. Source search shows the demand-building functions are exercised by tests, while active readiness and schedule editing reuse the campus predicate. A production daily-preview orchestrator is not established by those imports.

Package 0's analyzer, protected FastAPI matrix summary, admin BFF, readiness UI, authenticated client, and launcher exist and are tested. The recorded 2026-09-02 live attempt was `BLOCKED-CONFIG` because the BFF lacked an administrator bearer token (`docs/DUDULLU_RUNTIME_READINESS.md:3`).

**Current live state is NOT VERIFIED.** No new authenticated response was obtained in this audit. No service listened on ports 8000/9002 at the pre-build check. The launcher check-only success does not start the services or establish Supabase/matrix/fleet readiness.

Historical task reports describe a 28-row / 113-entry schedule normalization. That is historical reported evidence, not today's live count. Old persisted `ride_requests` dropoffs also need a separate read-only aggregate audit: the readiness contract is not a blanket check of every legacy ride row.

### 5.3 Academic platform

The current full suite includes quarantine manifests/import boundaries, Bildiri relocation/parity, JIT checks, fixed/native accounting, capability evidence, and production registry boundaries.

Runtime catalog enumeration from `uniride_core.algorithms.capabilities.list_algorithm_capabilities()` returned **14 IDs: 8 verified, 2 candidate, 4 planned**:

| Canonical group | Current catalog state | Scope |
|---|---|---|
| 2-opt, 3-opt, Or-opt | Verified | TSP/ATSP, fixed and native, Python objective |
| GWO-Pure, HHO-Pure | Verified | TSP/ATSP, fixed and native, evidenced Numba objective |
| GWO/HHO Memetic-2opt | Verified | TSP/ATSP **fixed only**; Numba objective, Python polish |
| ALNS-TSP | Verified | Four TSP/ATSP × fixed/native claims; Python, no polish |
| GA, PSO academic IDs | Candidate | No capability claims |
| GWO/HHO Memetic-3opt and Memetic-ALNS | Planned | No capability claims |

Evidence: `uniride_core/algorithms/capabilities.py:244`, `:275`, and `:317`. Or-opt is promoted by the later catalog reconstruction; reading only its initial candidate row would produce a false finding. ALNS was promoted through the August 3 commits, including `a3531ee`, after the C2 Or-opt commit `29095fd`.

Only `academic_benchmark/studies/bildiri2026/study.json` exists in the active study-profile tree. It is explicitly draft, three runs, small budgets, and smoke-only output. There is no active YAEM study profile in that tree.

**Academic Gate C remains partial; Gate D cannot be declared complete.** Four compositions and the YAEM profile remain approved requirements. Existing native/fixed pilots and legacy analysis utilities do not prove the full approved composition, statistically guarded analysis, or publication workflow.

## 6. Confirmed open findings

### F1 — A stopped benchmark can become completed again

- `optimizer_api/benchmark_state.py:241` sets STOPPED.
- `optimizer_api/benchmark_state.py:221` allows a later `complete_run` to overwrite it.
- `optimizer_api/routers/benchmark.py:531` only changes manager state when handling stop.
- The regular runner checks its separate `self.running` flag (`optimizer_api/benchmark_runner.py:272`) and unconditionally completes in `finally` (`:322`).
- Matrix execution also completes later (`optimizer_api/routers/benchmark.py:421`).

A fresh manager-only probe, with no solver, network, or persistence activity, produced:

```text
after_stop=stopped
after_late_completion=completed
```

Reproduce:

```powershell
& '.\.venv-jit\Scripts\python.exe' -c "from optimizer_api.benchmark_state import BenchmarkStateManager; m=BenchmarkStateManager(); s,_=m.create_run('audit-in-memory-only',1,{}); m.stop_run(s.run_id); print('after_stop='+m.get_run(s.run_id).status.value); m.complete_run(s.run_id,1); print('after_late_completion='+m.get_run(s.run_id).status.value)"
```

This proves the terminal-state transition defect. Source tracing also shows the stop signal is not connected to the manager-backed worker loops. A live long-running cancellation scenario was not executed. Correct UI state and actual interruption must be verified separately.

### F2 — Current dependency security debt is larger than the checkpoint suggests

The npm production graph reports 86 affected package entries. Critical entries are `next`, `protobufjs`, and `websocket-driver`; `xlsx` is high with no automatic fix reported. Installed Next is 16.1.6.

These are registry audit findings, not 86 independently demonstrated application exploits. Reachability, affected configurations, and safe upgrade/removal choices need a bounded follow-up. The audit proposes some major-version Genkit changes; blindly running `npm audit fix --force` is not an acceptable plan.

### F3 — Production execution and matrix contracts remain incomplete

- Benchmark state is process memory: `optimizer_api/benchmark_state.py:94`.
- Workers are daemon threads: `optimizer_api/routers/benchmark.py:316` and `:436`.
- Compare uses a soft deadline and `shutdown(wait=False)`: `optimizer_api/routers/optimization.py:440` and `:470`.
- Rate-limit buckets are process-local: `optimizer_api/rate_limit.py:22`.
- Matrix repository has source/cache-health metadata, but the approved artifact ID/version/content-hash/domain contract is not complete: `optimizer_api/utils/matrix_repository.py:85`, with requirements in the Dudullu specification's Package 2.

Some result rows are persisted; this does not make job ownership, heartbeat, cancellation, and restart recovery durable. A single-process admission lock already exists in `create_run`; do not propose fixing a nonexistent absence of local atomic admission. The open requirement is cross-process/durable behavior.

### F4 — Status documents disagree

| Document | Contradiction / stale claim | Handling |
|---|---|---|
| `docs/DUD01_VERIFICATION_2026-09-09.md:3` | Says uncommitted/not integrated | Retain dated test evidence; add an integration-status correction referencing `df23d15` / `55f7312` |
| `CANONICAL_THREE_OPT_DESIGN.md:4` | Says implementation pending | Preserve approved semantics; distinguish historical design state from current implemented catalog/tests |
| `docs/GITHUB_WORKFLOW.md:24` | Old document precedence and obsolete typecheck/lint/Pydantic blockers | Align process guidance with current AGENTS contracts and verified environment |
| `CURRENT_ARCHITECTURE.md:121`, `ACTIVE_ROADMAP.md:37` | Historical test, warning, and security counts | Mark historical; link current checkpoint instead of duplicating changing counts everywhere |
| `ACTIVE_ROADMAP.md:86` versus Dudullu specification `:535` | Package 6 is called pilot/operations in roadmap, but student/driver surfaces in the approved design | Resolve numbering before issuing later-package tasks; preserve the approved scope |

Old task plans with unchecked boxes are not proof that their code was never implemented. Conversely, a merge commit is not proof of live operational acceptance.

## 7. Proposed operating method

| Luna's proposal | Decision | Improvement |
|---|---|---|
| One persistent state file | Accept | Keep it short; link dated evidence, approved designs, and one active task. Avoid copying all history into it |
| One coordinator task | Accept as a role | Continuity belongs in versioned files, not an indefinitely growing chat. A replacement coordinator can resume from the checkpoint |
| Separate worktrees | Accept for independent writers | One writer per worktree; verify base SHA and required dirty docs; read-only reviews do not need another checkout |
| Model changes for quota | Accept | Choose by task risk and context size; do not repeat a full audit after every switch |
| External specialist results | Accept with verification | Fixed base, allowed paths, exact diff and commands, caveats, and locally checked acceptance |
| Next step is live readiness | Accept for Dudullu | It blocks Package 2, not independent security, job-state, or academic evidence work |

### Checkpoint contract

Only the coordinator writes `docs/UNIRIDE_WORKSTATE.md`. Update it after integration, a material blocker/decision, or a handoff—not after every command.

For each active item record: task ID, objective, owner/model, branch/worktree, base/current SHA, permitted files, implementation state, integration state, verification command/date/result, operational evidence if applicable, blocker, and exact next action.

Use separate evidence dimensions. “Implemented”, “integrated”, “tests passed”, “live gate passed”, and “publication/release ready” are not interchangeable. Workstate is an index of evidence, not a new source of architecture requirements.

### Task and model policy

- Luna: bounded inventory, documentation consistency, mechanical test/config edits with deterministic checks.
- Terra: normal implementation, cross-file maintenance, source tracing, and first review.
- Sol: ambiguous architecture, cancellation/concurrency, security-sensitive decisions, solver/budget contracts, and targeted final review.
- Mimo/Muse: use only within the repository's benchmarked boundaries; Muse's coding authority is still unproven.
- External specialists: only when their independent expertise materially helps. Availability must be checked; never claim consultation that did not happen.

Default to one implementation task. A second concurrent task should have separate files/contracts and independently useful output. Keep CPU-heavy verification sequential when diagnosing timeout sensitivity. Do not pay two large models to repeat the same complete audit.

Keep the same Codex task when only the model changes and the objective/context remains coherent. Start a user-requested new bounded task when scope, ownership, or an unwieldy history makes that clearer. Native subagents are for bounded subtasks of the current task; user-visible tasks are for work the user explicitly wants separated.

Official documentation supports [reading/resuming tasks and model overrides](https://learn.chatgpt.com/docs/app-server?translationFallback=es-419) and [worktree isolation/handoff](https://learn.chatgpt.com/docs/environments/git-worktrees?translationFallback=es-419). Local tool availability and Git evidence remain the basis for what was actually done here.

### External return and acceptance

Require the existing AGENTS return package: outcome, confirmed file/line findings, uncertain findings, files inspected/changed, exact commands/results/blockers, patch if needed, remaining risks/next action, and preservation statement. Add **base SHA, final SHA, and working-tree status**.

Review in this order:
1. Is the report for the intended checkout and base?
2. Does the actual diff stay within authority?
3. Do source and tests support each claim?
4. Did the touched contract require a security, feasibility, parity, or publication gate?
5. Can the change be integrated without absorbing unrelated edits?
6. Update the checkpoint only after recording the integration and verification evidence.

No new tracker service or automation is needed for this workflow.

## 8. Ordered continuation tasks

The ordering assumes Dudullu is the first product objective, matching the current roadmap. Academic-only prioritization changes scheduling, not scientific acceptance gates.

### REC-00 — Recovery checkpoint (this task)

**Files:** `docs/UNIRIDE_WORKSTATE.md`; this document.

**Owner:** coordinator. **Authority:** audit/planning documentation.

- [x] Verify Git/remotes/worktrees and selected related tasks.
- [x] Run current full functional checks and record failures as well as passes.
- [x] Distinguish academic, product, shared-infrastructure, and live-data gates.
- [x] Write portable evidence and the continuation sequence.
- [ ] Commit only the two reviewed documentation outputs when integration is authorized. Do not include unrelated root dirt.

### OPS-01 — Current authenticated readiness (next product task)

**Files/contracts:** `docs/DUDULLU_RUNTIME_READINESS.md`, `docs/UNIRIDE_WORKSTATE.md`; existing `/admin/readiness` and `GET /api/admin/dudullu-readiness`.

**Owner:** bounded operator task; Luna is enough for evidence capture if the browser works, Terra for a confirmed cross-layer failure.

**Authority for the proposed task:** read-only runtime check; no data fixes.

- [ ] Recheck branch/HEAD/status; use the credential-bearing checkout selected for runtime.
- [ ] Start the existing launcher with the verified Python path:
  ```powershell
  $env:UNIRIDE_PYTHON = (Resolve-Path '.venv-jit\Scripts\python.exe').Path
  npm.cmd run dev:dudullu
  ```
- [ ] Authenticate through the application's administrator login. Never paste a bearer token into chat or a report.
- [ ] Open `http://127.0.0.1:9002/admin/readiness`; record aggregate fields, fixed reason codes, timestamp, HEAD, and HTTP result.
- [ ] If browser tooling is still unavailable, have the user view that same authenticated page and return only its redacted aggregate. Keep dependent work pending; continue SEC-01 independently.
- [ ] PASS only for an authenticated HTTP 200 response with `ready: true`. Classify authorization/configuration/service/data failures separately.
- [ ] Any data repair must have its own reviewed scope; a readiness check does not authorize a migration.

**Exit:** portable current aggregate evidence. Historical 28/29 counts are comparison data only. No Package 2 implementation before PASS.

### SEC-01 — Dependency reachability and minimal remediation plan

**Inspect:** `package.json`, `package-lock.json`, `next.config.ts`, `src/ai/`, Excel import callers, installed dependency paths.

**Owner:** Terra for bounded inventory, Sol for security-sensitive conclusions.

**Authority initially:** read-only review; a selected patch becomes a separate implementation task.

- [ ] Use the saved current npm audit and `npm.cmd explain next`, `npm.cmd explain protobufjs`, `npm.cmd explain websocket-driver`, and `npm.cmd explain xlsx` to trace direct/transitive ownership.
- [ ] Check actual Next.js configurations and package call sites against current primary advisories.
- [ ] Separate exploitable/reachable findings from conditional or unused paths; record uncertainty.
- [ ] Choose the smallest supported update or removal, one dependency family per patch; do not bulk-force upgrades.
- [ ] Validate each approved patch with frontend tests, typecheck, lint, build, and a refreshed audit. Report residual counts and reachability.

**Exit:** reviewable package changes and remaining exposure explained. This may proceed while OPS-01 is blocked, and must precede a deployment/pilot readiness claim.

### JOB-01 — Truthful stop state, then durable execution

**Existing files:** `optimizer_api/benchmark_state.py`, `optimizer_api/benchmark_runner.py`, `optimizer_api/routers/benchmark.py`.

**Relevant existing checks:** `optimizer_api/tests/test_p3_owner_tokens.py`, `optimizer_api/tests/test_api_hardening_phase0.py`.

**Owner:** Terra implementation with targeted Sol review because worker lifecycle crosses boundaries.

- [ ] First create a bounded plan for F1: terminal transitions, manager/worker stop propagation, and late result/progress/completion behavior on both runner modes.
- [ ] Add one deterministic regression covering a real stopped job receiving a late completion; keep ownership and duplicate-admission behavior covered.
- [ ] Fix the shared state/worker boundary. Do not describe a state guard as hard solver cancellation.
- [ ] Run the two named suites and the new regression, then the full Python suite for cross-runner changes.
- [ ] Only afterward plan production Package C: persisted job state/owner/heartbeat, idempotent recovery, cooperative solver cancellation, and process isolation. Reuse existing persistence where suitable.

**Exit for F1:** no stopped-to-completed resurrection; both worker paths honor the declared stop contract. **Exit for durable jobs:** restart/multi-worker/cancellation tests prove the broader contract. These are separate gates.

### DOC-01 — Reconcile stale status and package labels

**Files:** the five document groups in F4, plus checkpoint links.

**Owner:** Luna with coordinator review. No algorithm redesign.

- [ ] Correct integration-status annotations while preserving historical test dates/counts.
- [ ] Mark the 3-opt implementation status from live catalog/tests without changing its approved mathematical contract.
- [ ] Align workflow precedence and environment instructions with current AGENTS/specs.
- [ ] Resolve the Dudullu Package 6 label against the approved design before dispatching Packages 4–6.
- [ ] Use `git diff --check` and a source/line comparison. No full test rerun is needed for wording-only changes.

**Exit:** one clear current entry point; specifications remain requirements, dated reports remain evidence.

### PROD-02 — Dudullu preview, only after OPS-01 PASS

**Required context:** approved Dudullu design, sections 3.5–3.6 and Package 2 (`:484`); relevant matrix and feasibility contracts.

**Owner:** Sol for the cross-contract design, Terra for bounded implementation; solver-specialist review only if solver semantics change.

- [ ] Write a separate Package 2 implementation plan with exact files/API and tests.
- [ ] Reuse `daily-planning.ts`, authenticated BFF transport, canonical solver adapters, and certificates.
- [ ] Bind drafts to an authoritative matrix artifact ID/version/hash and independently check used arcs.
- [ ] Include closing depot arcs and complete resource intervals.
- [ ] Assign physical vehicles across the day in the approved two stages.
- [ ] Prove a complete certified preview or an explicit non-publishable shortage/unassigned result with the specified fixture.

**Exit:** certified, truthful preview; no publication or claimed fleet savings inferred from route count alone.

Then follow the approved design: Package 3 transactional/RLS publication → Package 4 admin operations → Package 5 certified cross-wave re-solves → Package 6 student/driver surfaces. Resolve F4's numbering drift before issuing those task briefs. Operational pilot/release acceptance is a separate gate.

### ACAD-01 — Finish academic Gate C scope before Gate D

**Required context:** `ACADEMIC_STUDY_UNIFICATION_DESIGN.md:418`, fairness and canonical 3-opt specifications, current capability catalog.

**Owner:** Sol for algorithm/budget contracts; bounded Terra implementation with targeted numerical review as needed.

- [ ] Map the remaining approved IDs and active study-profile requirements; preserve the eight already verified entries.
- [ ] Plan GA/PSO evidence promotion independently from four GWO/HHO 3-opt/ALNS compositions.
- [ ] For compositions, prove shared objective accounting and boundary budgets; do not substitute hidden polish or native evidence for fixed-budget evidence.
- [ ] Add the YAEM active profile only against implemented, evidenced capabilities.
- [ ] Complete Gate C's protocol/schema/pilot acceptance before planning Gate D analysis/reporting.
- [ ] Gate D must independently validate statistical assumptions, evidence provenance, and fixed/native separation. No paper-scale campaign is authorized by this audit.

**Verification baseline:** full `academic_benchmark/tests`, core contract tests, production registry snapshot, and exact new evidence nodes. Current full-suite success does not waive new composition tests or approve superiority claims.

### HOUSE-01 — Optional repository hygiene, last

Preserve the stash, rescue branches, ignored artifacts, and dirty egg-info worktree until ownership/retention is decided. Removing old worktrees does not advance a product or scientific gate. If cleanup is later requested, recheck ancestry/patch equivalence and all tracked/untracked/ignored content before any deletion.

## 9. Resume procedure

1. Read `docs/UNIRIDE_WORKSTATE.md`; read only the linked specification sections relevant to the selected task.
2. Run `git status --short --branch`, `git rev-parse HEAD`, and `git worktree list`.
3. Confirm the task's base and permitted paths. Account for uncommitted instruction changes: a new worktree does not inherit them.
4. Refresh CodeGraph if present; classify a lock explicitly instead of assuming the index is current.
5. Execute the smallest authorized task and its focused gate. Escalate scope only for a demonstrated dependency.
6. Return exact commands/results, final SHA/diff, uncertainty, and one next action.
7. Let the coordinator update the checkpoint; retain the dated report rather than rewriting historical evidence.

**Recommended next action:** OPS-01 authenticated, read-only Dudullu readiness. If administrator/browser access is unavailable, keep that gate open and run SEC-01; do not restart the entire project audit.
