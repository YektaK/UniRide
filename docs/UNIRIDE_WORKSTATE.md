# UniRide Work State

> Current checkpoint, not a substitute for approved specifications. Read the dated audit only when its evidence or a selected task requires it.

**Updated:** 2026-09-23, Europe/Istanbul

**Repository:** `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide`

**Integration/default branch:** `WIP`

**Verified local and actual remote HEAD:** `73618255d94f2e51ae01c8bcedbf9c1b43c9a6ff` — `fix(campus): unify Dudullu location defaults`

**Detailed evidence and continuation plan:** [2026-09-22 recovery audit/plan](superpowers/plans/2026-09-22-uniride-recovery-and-continuation.md)

## Current verdict

The repository has a passing functional baseline. Local, administrator-authenticated Dudullu readiness reached PASS on 2026-09-23 after the matrix provider fix. Complete daily operations, academic Gate C/D completion, and production readiness are not established.

Keep three tracks separate: Dudullu operations; shared production infrastructure/security; academic research. A blocked Dudullu live gate does not block independent security or academic work.

## 2026-09-23 continuation

- OPS-01 passed locally after the user restored Supabase. The user reported PASS, 29 matrix nodes and 812 directed arcs on /admin/readiness; local server logs showed authenticated administrator readiness HTTP 200 and internal time-matrix readiness HTTP 200. The UI response body was not independently captured because computer-use access failed.
- A read-only live Supabase count found 812 time_matrix rows, so the earlier BLOCKED-DATA display (0 nodes / 0 arcs) did not mean the table was empty. The Python provider failed while constructing its SDK client: it imported the base ClientOptions class, which lacks storage. The tracked one-line fix imports the SDK's concrete ClientOptions from supabase.client. The existing declared supabase requirement was installed into ignored local .venv-jit; no dependency manifest or database rows changed.
- Direct read-only provider verification after the fix reported source=supabase, loaded=true, no provider error, 29/29 nodes, 812/812 arcs, ready=true. Focused matrix/readiness tests: 47 passed. This establishes the local data gate, not deployed-production readiness.
- The Dudullu launcher now passes --hostname 127.0.0.1 to Next. All 20 launcher tests passed; live listeners on ports 8000 and 9002 were verified bound to 127.0.0.1. The code change is uncommitted.
- SEC-01 initial ownership only: next and xlsx are direct dependencies; protobufjs and websocket-driver enter through transitive chains. Reachability and remediation remain open.

## Fresh verification at the recorded HEAD

| Check | 2026-09-22 result |
|---|---|
| Full Python, `.venv-jit` | **3,380 passed, 1 skipped, 45 warnings**, exit 0 |
| Full frontend, isolated rerun | **39 files / 216 passed**, exit 0 |
| First concurrent frontend run | 215 passed / 1 timeout at `ride-confirmation/route.test.ts:57`; the file and then full suite passed unchanged |
| TypeScript / build | Both passed; build used existing local installation and `.env.local` |
| ESLint | **0 errors / 164 warnings** |
| Launcher tests / configuration probe | **20/20**; `--check-only` passed with `UNIRIDE_PYTHON=.venv-jit\Scripts\python.exe` |
| Python dependency graph | `pip check`: no broken requirements |
| Production npm audit | **86 findings: 3 critical, 21 high, 60 moderate, 2 low** |
| Latest WIP GitHub CI | [Successful at 7361825](https://github.com/YektaK/UniRide/actions/runs/34394814724); focused Python execution, not the full suite |
| Current authenticated readiness | Local PASS: user-reported UI 29/29 nodes, 812/812 arcs; local authenticated API HTTP 200; direct provider aggregate ready=true |

Python skip is the optional PyVRP module: not installed. The timeout cause is not proven; avoid concurrent heavy suites when establishing a baseline. Audit package counts do not establish exploitability. Exact commands, scope, and log locations are in the dated audit.

## Completed and integrated, within tested scope

- Production occurrence identity, matrix integrity, feasibility admission, compute policy/authentication, tenant authorization, rate windows, canonical strategy resolution, and server-only transport.
- Academic quarantine/extraction and catalog/preflight foundations; C2 Or-opt `29095fd`; **C3 ALNS** promotion and evidence on August 3.
- Dudullu Package 1 pure demand/wave domain; Package 0 readiness implementation; authenticated readiness UI/client.
- DUD-01 calculation authentication and direction persistence: `22be4b1`, merged by `df23d15`; integration documentation `55f7312`.
- Campus contract `7361825`: machine code `D.Kampus`, schedule label `Dudullu`, address `Doğuş Üniversitesi, Dudullu Kampüsü`, coordinates `41.001, 29.177`.

Source integration does not certify persisted historical records or a live deployment.

## Open work and evidence

| ID / track | Verified current state | Next acceptance gate |
|---|---|---|
| OPS-01 / Dudullu | Local PASS on 2026-09-23 after SDK client-options fix; UI result reported by user and corroborated by HTTP logs plus direct aggregate | Package 2 preview plan; deployed-production acceptance remains separate |
| SEC-01 / dependencies | Critical audit entries: Next, protobufjs, websocket-driver; xlsx high, no automatic fix reported | Reachability review and separately scoped safe remediation |
| JOB-01 / job lifecycle | Fresh in-memory repro: `stopped -> completed` after a late completion; workers are not wired to manager stop state | Terminal-state and worker-stop regression, then separate durable-execution gate |
| DOC-01 / continuity | DUD-01 verification header, 3-opt status, workflow baseline/precedence, and Package 6 labels are stale/conflicting | Correct status annotations without rewriting approved contracts or historical evidence |
| PROD-02 / daily preview | Domain functions exist; full production preview/fleet orchestration remains pending | OPS-01 PASS, then approved Package 2 plan and certified truthful preview |
| ACAD-01 / academic Gate C | Runtime catalog: **8 verified, 2 candidate, 4 planned**; only Bildiri active study profile | Remaining capability/composition/profile gates before Gate D |
| Later production | Soft deadlines, in-memory jobs/rate limits, incomplete matrix provenance; no established GIS renderer | Scoped durability/cancellation/provenance and geometry gates before release claims |

Academic detail: GA/PSO remain candidates; GWO/HHO 3-opt and ALNS hybrids remain planned. GWO/HHO memetic-2opt catalog evidence is fixed-budget only. The Bildiri profile is draft/smoke-only; active YAEM profile is absent. Do not call the overall academic unification complete.

Dudullu order follows the approved design: Package 2 preview → 3 transactional publication/RLS → 4 admin operations → 5 certified cross-wave recommendations → 6 student/driver surfaces. The roadmap currently labels Package 6 differently; resolve that before dispatching later packages. Current live counts and old persisted ride dropoffs remain unaudited.

## Git and environment boundaries

- Preserve unrelated modified `.gitignore` and `AGENTS.md`, and untracked `INSTRUCTION_REVIEW_2026-09-07.md`. Their hashes were unchanged through this audit.
- The dated audit and this checkpoint are uncommitted. The 2026-09-23 Dudullu launcher/test and matrix provider/test are also modified. The existing declared Supabase SDK was added only to ignored .venv-jit; no tracked dependency or DB edits, commit, merge, push, or worktree cleanup occurred.
- **17 registered worktrees** were inspected: root plus 16 linked trees. Of the linked trees, 15 were clean; one has five modified `uniride.egg-info/*` files.
- Package B task5/task6/task7 have seven non-ancestor commits in total, but all are patch-equivalent to WIP. Do not merge them merely because ahead/behind is nonzero.
- One old `autostash` is preserved. Ignored artifacts and all rescue-branch contents were not exhaustively reviewed; no blanket cleanup is approved.
- No open GitHub PR was found at capture. Recheck before future integration.
- `codegraph index .` failed with an EPERM lock; init reported already initialized; explore/node worked. Treat graph relationships as leads and verify active imports/current source.
- Browser inventory failed twice with `trusted Node process exited unexpectedly`. This audit did not reach the administrator UI.
- The local launcher subsequently started both services on 127.0.0.1; FastAPI health and internal readiness handshakes passed. The process was restarted on 2026-09-23 to open the web panel.
- Verified runtime: Python 3.14.3, NumPy 2.4.6, Numba 0.66.0; Node 25.5.0 locally, Node 22 in frontend CI. No clean reinstall was attempted.

## Relevant Codex tasks

Selected relevant turns were read; no claim of exhaustive transcript coverage.

| Task title | ID | Context |
|---|---|---|
| Audit UniRide dual-engine stack | `019f6a37-11eb-79c0-b8f5-bd49aa916005` | Integration, campus review, historical schedule correction, failed live/browser checks |
| Role and target model: You are GPT-5.6 Luna, acting as a bo… | `01a081cd-c3c7-74a3-8686-0adbe48286bb` | DUD-01 and campus work; newest returned turns had empty items; checkpoint verified from disk |
| Commit C2 Or-opt promotion | `019fc354-6a35-7872-85dd-292cf34cb796` | Historical Or-opt integration/evidence |
| Fix benchmark test blockers | `019f174e-638a-7d43-aaed-ef09c8c9fd0d` | Older context under another project; current full suite supersedes obsolete environment blockers |

The archived-task listing ended with no archived UniRide match. External reports and historical data-mutation claims remain historical until independently checked. No external agent was invoked in this audit.

## Resume and coordination protocol

1. Read this checkpoint, then only the selected task's specification sections.
2. Recheck `git status --short --branch`, `git rev-parse HEAD`, `git worktree list`, and the task's base.
3. Use one active writer per implementation worktree. A new worktree does not inherit uncommitted AGENTS changes or local credentials.
4. Record objective, allowed files, base/current SHA, exact tests/results, uncertainty, and one next action in each handoff.
5. Luna for bounded deterministic work; Terra for ordinary implementation/review; Sol for targeted architecture/security/solver/concurrency escalation. External models only when available and useful.
6. The coordinator updates this file at material checkpoints. Keep implementation, integration, functional verification, and live acceptance separate.
7. Carry existing authorization forward. A model change does not itself authorize new scope or require a new complete audit.

**Next product task:** Prepare the scoped Dudullu Package 2 preview plan from the approved package design, using the 2026-09-23 local OPS-01 PASS as its entry evidence. Keep SEC-01 as an independent security track. Recheck the live data gate before any later deployment or publication claim.

**If the live gate regresses:** record the current redacted aggregate and the failing layer before changing data or beginning Package 2 implementation.
