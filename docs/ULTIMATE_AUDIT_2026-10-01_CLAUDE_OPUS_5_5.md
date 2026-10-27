# UniRide Ultimate Audit — 2026-10-01

> Read-only, evidence-backed audit of the full stack: Next.js UI and BFF (`src/`), the FastAPI optimizer (`optimizer_api/`), the shared kernel (`uniride_core/`), the academic platform (`academic_benchmark/`), and the Supabase SQL (`supabase/`). Written for the human maintainers **and** for AI agents who will remediate the findings.

## Document metadata

| Field | Value |
|---|---|
| Report ID | `UA-2026-10-01-CLAUDE` |
| Written | **2026-10-01 11:01 (+03:00, Europe/Istanbul)**, v1.0 |
| Revised | **2026-10-01 16:53 (+03:00)**, **v1.1**: reconciled with the independent Codex verification (`docs/ULTIMATE_AUDIT_2026-10-01_CODEX_VERIFICATION.md`, reviewed at `a54b786`). See [Revision history](#revision-history). |
| Investigation window | 2026-09-30 ≈17:00 → 2026-10-01 ≈11:00 (+03:00). Paused overnight when the account's 5-hour usage window was exhausted; the investigators were resumed from their saved transcripts. |
| Author (lead agent) | **Claude** (Anthropic), model **Claude Opus 5.5** (`claude-opus-5-5`), running in Claude Code (Claude desktop app, Code tab) |
| Contributing agents | Six Claude Opus 5.5 sub-agents ("investigators"), one per lane: **P1a** constraints and objective math · **P1b** local search, determinism and duplicates · **P2** FastAPI backend · **P3** Next.js frontend and BFF · **P4** dual-engine boundaries and work-package gates · **ACAD** academic accounting, seeds and statistics. The lead re-verified every Critical finding. |
| Requested by | Repository owner (git user `YektaK`) |
| Repository state | Branch `WIP`, HEAD `316cbab` ("docs: record remote branch consolidation"). Working tree clean except the pre-existing untracked `INSTRUCTION_REVIEW_2026-09-07.md`. |
| Audit mode | **Read-only.** No source, config, test or database file was changed; this report is the only repository write. The local databases `academic_benchmark/tsplib_data/tsplib.db` (last modified 2026-07-20) and `db/custom.db` (2026-04-17) were confirmed untouched. |
| Governing instructions | `AGENTS.md` (document precedence, academic boundaries, work-package gates, git safety) |

---

## Table of contents

- [Revision history](#revision-history)

0. [How to use this report](#0-how-to-use-this-report-read-first)
1. [Method, scope and baseline](#1-method-scope-and-baseline)
2. [Executive summary: the reality check](#2-executive-summary-the-reality-check)
3. [Critical findings (fix now)](#3-critical-findings-fix-now)
4. [High findings (fix next)](#4-high-findings-fix-next)
5. [Medium findings](#5-medium-findings)
6. [Low findings](#6-low-findings)
7. [Architecture and performance bottlenecks](#7-architecture-and-performance-bottlenecks)
8. [Unification strategy](#8-unification-strategy)
9. [Master roadmap and task cards](#9-master-roadmap-and-task-cards)
- [Appendix A — Duplicate-implementation map](#appendix-a--duplicate-implementation-map)
- [Appendix B — Import-boundary matrix](#appendix-b--import-boundary-matrix)
- [Appendix C — Work-package gate status](#appendix-c--work-package-gate-status)
- [Appendix D — Academic contract compliance](#appendix-d--academic-contract-compliance)
- [Appendix E — Frontend hygiene counts](#appendix-e--frontend-hygiene-counts)
- [Appendix F — Checked and sound](#appendix-f--checked-and-sound-do-not-re-investigate)
- [Appendix G — Open questions](#appendix-g--open-questions)
- [Appendix H — Reproduction scripts](#appendix-h--reproduction-scripts-re-run-2026-10-01)
- [Appendix I — Verification commands](#appendix-i--verification-commands)
- [Appendix J — Remediation tracker and log](#appendix-j--remediation-tracker-and-log)

---

## Revision history

| Version | Date (+03:00) | Author | Change |
|---|---|---|---|
| v1.0 | 2026-10-01 11:01 | Claude (Opus 5.5) | Initial audit at `316cbab`. |
| v1.1 | 2026-10-01 16:53 | Claude (Opus 5.5) | Reconciled with the independent Codex verification (`docs/ULTIMATE_AUDIT_2026-10-01_CODEX_VERIFICATION.md`, reviewed at `a54b786`). Every disputed claim was re-checked against live code before it was accepted. |

**v1.1 changes** (re-verified by the lead at the cited lines unless noted):

| Item | Change | Basis |
|---|---|---|
| C1 | Severity made explicitly conditional: Critical if the live policies match the repository SQL; the unsafe repository policy is a release blocker regardless. | Codex §3 |
| C1.b | **Re-rated Critical → High.** The gap is limited to the attacker's own requests, and no consequence in the current Dudullu planning/publication flow is verified (legacy routing reads `confirmed` rows). New open question Q20. | Codex §3 |
| C2 | Scope added: snapshot-bound requests already fail closed (`routers/optimization.py:211-234`; Appendix H.4 steps 6 and 9). The fail-open applies to unbound requests; the rounding gap applies with any matrix. | Codex §3; lead repro H.4 |
| C3 | Scope added: the governed fair/native branches (`registry_setup.py:345-365`) bypass the cache, so quarantine follows result provenance, not wholesale. Preferred fix: pass the prebuilt matrix explicitly; no second global cache. | Codex §3 |
| C4 | Severity made conditional on the Next.js app being publicly reachable and the benchmark router being mounted in the deployed optimizer (Q15, Q18). | Codex §3 |
| H20 | **Corrected.** Pushes to `WIP` run 8 focused Python files; pull requests also run `benchmark.yml` (SOTA smoke, ATSP integration, regression gate, SOTA E2E). The finding is now: the full canonical suites and the production build never run in CI. | `.github/workflows/benchmark.yml:3-48` |
| M6 | **Narrowed.** The landing page does show demo badges (`src/app/page.tsx:1156-1160, 1902-1903`). Remaining: unlabelled IE tracks, demo rows saved to history with only a `demo_` prefix, automatic switching. | `page.tsx` |
| M11 | **Re-rated Medium → Low.** Next 16's peers accept React 18.2+ or 19, and the App Router bundles canary React by design; act only on a concrete runtime incompatibility. | `node_modules/next/package.json` |
| M15, §8.4 | **Corrected.** The production registry must stay a domain-aware CVRP/CVRPTW surface with grandfathered `production_ready` flags; it cannot be produced by filtering the permutation-TSP academic catalog. | Unification design, Capability Model; Codex §7.11 |
| M17 | **Corrected.** The generic test lives at `uniride_core/tests/test_archive_boundaries.py` (v1.0 cited a wrong path). The YAEM-specific test does reject static imports of `archive.academic_benchmark.yaem2026_legacy` (`test_yaem_quarantine_boundary.py:39-50`). Residual gaps only: namespace importability, the generic test's markers, dynamic and root-file scans. | test sources |
| M19 | Clarified: `studies/bildiri2026/study.json` is an explicit draft/smoke profile; the finding concerns truthful metadata, not contaminated published results. | Codex §5 |
| M20 | **Re-rated Medium → Low (informational).** Counting repeated objective calls complies with the approved budget definition. The memoization advice is withdrawn: it would change the comparison protocol and needs approval. | Fairness design; Codex §7.9 |
| M24 | Profile before adding virtualization or other abstractions. | Codex §5 |
| M26 | **Re-rated Medium → High; now VERIFIED-LEAD.** The adapter builds a student-only, depot-free, distance-scaled matrix and silently falls back to greedy on any exception (`sota_tsp_strategy_adapter.py:12-23, 61-67`), so production responses can misreport the algorithm that ran. Detailed entry added to §4; new quick win QW11. | lead source read; Codex §5 |
| L3, §8.2 | **Corrected precision.** Only the request-model field `use_sota_engine` (`optimizer_api/models/schemas.py:222`) is unused; the core decoder option of that name is live (`uniride_core/algorithms/cvrptw_decoder.py:25-62`). In `clustering.py` only the duplicate k-means is dead. `sota_common` has consumers (re-exports, compatibility tests, `__main__`) to redirect before retirement. | grep; Codex §6-7 |
| §2.3, §8.6, MT4, MT5, Appendix C | **Withdrawn:** the claim that Package C started while Gate A was incomplete. Gate A (design lines 422-429) covers archival, checksums, schemas, non-importability and green academic tests. Run-manifest integration is Package D, and production → academic isolation is a separate architecture plan. Pilots already emit `manifest.json` (`fair_pilot.py:583`, `native_pilot.py:596`). | design; grep |
| §2.3 | Added two documentation overstatements: `CURRENT_ARCHITECTURE.md:39` ("protected end to end") and `:58` ("academic execution remains separate"). | Codex §8 |
| §7.3, §8.3 | Memoization advice withdrawn (see M20). Shared timing logic should be the smallest common function, not a new scheduling framework. | Codex §9 |
| §9 | Sequencing refined: Phase 0 containment must precede live-data preview and operational acceptance; the offline Package 2 Task 5 fixture may proceed in parallel. Durations are estimates. | Codex §7.14 |
| §1.4, Appendix F, Appendix H | Added Codex's independent selective re-runs and five items confirmed sound. Codex re-ran Appendix H.1 unchanged with the identical 4-of-6 result. | Codex §8, §10 |

**Unchanged:** every other finding. Codex either confirmed the mechanism or did not dispute it with evidence. Where Codex marked a measurement as "not rerun" (H6's 2,703 ms, C2's OR-Tools rounding), the lead had reproduced it on 2026-10-01 (Appendix H.3, H.4).

**IDs are stable across versions.** When a finding is re-rated, its ID stays the same; the severity stated in the finding and in Appendix J is authoritative.

---

## 0. How to use this report (read first)

1. **Precedence.** Per `AGENTS.md`, verified live code and passing tests outrank this document. All line numbers refer to commit `316cbab`. Before acting on a finding, re-open the cited lines (`codegraph node <file>`, or the `codegraph_explore` MCP tool) and confirm the defect still exists.
2. **Status legend.**

   | Status | Meaning |
   |---|---|
   | `VERIFIED-LEAD` | Re-read at the cited lines by the lead agent; where marked "(repro)", also reproduced by the lead on 2026-10-01 (Appendix H). |
   | `CONFIRMED` | Confirmed by an investigator through an end-to-end code trace or an offline demo; not independently re-read by the lead. |
   | `PLAUSIBLE` | Mechanism identified; runtime or live-environment confirmation still required. The **Confirm by** line says how. |
   | `LATENT` | A real defect that is currently unreachable or inactive. |

3. **IDs.** IDs are stable identifiers assigned in v1.0 by original severity: `C#` Critical, `H#` High, `M#` Medium, `L#` Low. A re-rated finding keeps its ID; the severity stated in the finding and in Appendix J is authoritative (see the Revision history). Investigator IDs (for example `P2-01`, `ACAD-03`) appear in parentheses for traceability. Roadmap items are `QW#` (quick wins), `MT#` (mid-term) and `LT#` (long-term).
4. **Working discipline** (`AGENTS.md`, `ACTIVE_ROADMAP.md`):
   - one bounded package per branch, cut from a clean `origin/WIP`;
   - write a failing regression test that reproduces the finding **before** fixing it;
   - run the proportionate suites in Appendix I;
   - never push or merge without review and explicit authorization;
   - **never mutate live Supabase data or policies without explicit authorization.** Every RLS check in this report is a read-only query.
5. **Academic gates still apply.** Fix `academic_benchmark` findings inside the approved gate order A → B → C → D (`ACADEMIC_STUDY_UNIFICATION_DESIGN.md`); see §9 and Appendix C.
6. **Do not rewrite finding text.** When a fix lands, update Appendix J (status, branch, commit, test evidence) and append to the remediation log. If a finding proves wrong, mark it `WITHDRAWN` with the reason; do not delete it.
7. **Governing specifications** (the `AGENTS.md` routing table):
   - Solver ownership, registry, datasets and manifests (H8, H9, H17, H19, M15–M17): `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`.
   - Budgets, seeds, algorithm identity and statistics (C3, C5, H11, H13, M18–M20, L8–L10): `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`, plus the unification design.
   - 3-opt (H10, M14, M25): `CANONICAL_THREE_OPT_DESIGN.md`.
   - Production boundaries and priorities (C1, C2, C4, H1–H7, H14, H15, H18, H20): `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`.
8. **Relationship to other documents.** This report does not replace `UniRide_Ultimate_Audit.md` (the project's maintained master audit) or any approved design. Where they disagree about current behavior, verify the live code. §2.3 lists the discrepancies found. A companion independent review by Codex, `docs/ULTIMATE_AUDIT_2026-10-01_CODEX_VERIFICATION.md` (reviewed at `a54b786`), is reconciled into v1.1; read it for its evidence labels and fresh selective test runs.

---

## 1. Method, scope and baseline

### 1.1 Scope

**In scope:** active code in `uniride_core/`, `optimizer_api/`, `academic_benchmark/`, `src/`, `scripts/`, `supabase/`, root configuration, and CI.

**Excluded** (per the audit brief): `node_modules/`, `.venv*/`, `__pycache__/`, `.next/`, `dist/`, `build/`, `temp/`, `tmp/`, `.temp/`, `cache/`, `archive/`, `legacy/`, `old/`, `.proposed_changes/`, `scratch/`, `agent-ctx/`, databases, logs and TSPLIB dumps. `archive/` is mentioned only where active code depends on it.

### 1.2 Tools and evidence

- **CodeGraph.** The index held 712 files, 11,563 nodes and 30,245 edges, with status "up to date".
  - In this version the MCP server exposes a single tool, `codegraph_explore`. `codegraph_search` and `codegraph_callers` are not MCP tools, so their CLI equivalents were used: `codegraph query|callers|callees|impact|node|files`.
  - CodeGraph does not index Markdown, SQL or JSON; those were read directly.
  - Right after a daemon restart, CodeGraph can falsely report files as "edited N ms ago, pending sync". Check with `codegraph status` and `git status`.
- **Grep** was used only for lexical patterns CodeGraph cannot see: SQL policies, lint directives and import statements.
- **Offline demos.** The investigators wrote about 25 demos and ran them in `.venv-jit`:
  - environment: Python 3.14.3 with NumPy, Numba, FastAPI, pytest and OR-Tools installed; PyVRP, VROOM and SciPy not installed;
  - isolation: `PYTHON_DOTENV_DISABLED=1`, blank Supabase credentials, no network.

  The lead re-ran the five key reproductions on 2026-10-01 (Appendix H).
- **Documentation** was used only as the approved-contract baseline, never as evidence of behavior.

### 1.3 Not inspected

- Live Supabase state: policies, triggers and rows.
- The contents of `tsplib.db` (2.9 GB).
- The optimizer's deployment configuration; the repository contains none.
- `npm audit`, which was not run because it contacts the registry.

### 1.4 Fresh baseline (run by the lead on 2026-09-30)

| Gate | Command | Result |
|---|---|---|
| Python canonical suites | Appendix I.1 | **3,399 passed, 1 skipped, 45 warnings** in 584.6 s |
| Frontend unit tests | `npx vitest run` | **43 files / 315 tests passed** (103.8 s) |
| TypeScript | `npx tsc --noEmit` | clean (exit 0) |
| ESLint | `npx eslint src/ --ext .ts,.tsx -f json` | **0 errors / 163 warnings** over 222 files |

These match the counts documented on 2026-09-30, except lint (documented as 158).

*(v1.1)* Codex independently re-ran selective groups at `a54b786`: 387 Python tests in three groups, 6 Vitest files / 13 tests, typecheck clean, lint 0 errors / 163 warnings (companion report §8 and §10). These are selective runs, not a new full-suite run.

A green suite is not evidence against the findings below. Most defects sit **between** components, and each component is tested only against its own assumptions. For example, the certificate is tested against solver responses, not against the authoritative travel-time matrix.

---

## 2. Executive summary: the reality check

### 2.1 Verdict

UniRide is a well-tested research prototype wrapped in a production-shaped shell. The algorithmic core is better engineered than the layers around it. Its weakest points are **trust boundaries** (who may do what, and which data is believed), not the algorithms. Five Critical defects are reachable today, and the two guarantees the project documents lean on most are weaker than claimed:

1. **The "solver-independent" feasibility certificate re-checks the solver's own travel times**, and the matrix layer falls back to zeros when the matrix is unavailable (C2).
2. **The compute protection can be bypassed** through anonymous BFF benchmark routes, and "stop" does not stop (C4).

In addition: a database-level privilege escalation (C1), silent corruption of academic results through an `id()`-keyed cache (C3), and a dashboard that prints significance claims from invalid statistics (C5).

*(v1.1)* An independent Codex review reproduced the mechanisms of C2 and C4, C3's 4-of-6 corruption, and H2, H3, H5, H13 and M18. It also narrowed several scopes; see the Revision history.

### 2.2 Scorecard

| Dimension | Score (1–5) | Basis |
|---|---|---|
| Core algorithm correctness | 4 | Canonical 3-opt is exact (7 symmetric reconnections, 1 directed, mode chosen automatically). ATSP 2-opt deltas are exact to 3.4e-13. Fixed-budget accounting is exact across 7 algorithms. Minus one: the forbidden Numba 3-opt is still live (H10) and the production default uses a second 3-opt (M14). |
| Constraint integrity (vehicle routing) | 2 | Four incompatible time-window models. The return arc to school is never checked (H2). Search ignores time windows (H4). Solvers ignore the fleet (M1). |
| Production safety guarantees | 1 | The certificate re-certifies solver claims, and the matrix fails open to zeros (C2). |
| Security | 1 | Anyone can register as admin (C1). Benchmark compute is anonymous (C4). Password hints are disclosed (H1). |
| Concurrency and resilience | 2 | Per-request strategy isolation is correct. But there is no global solver cap (H7), stop does not stop (C4), the event loop blocks (H6), and the DataLoader exists twice (H5). |
| Academic rigor | 3 | Gateway and pilots are publication-grade. Storage, IDs, caches and the dashboard are not (C3, C5, H8, H9, H13). |
| Frontend | 2 | Typed and tested, with server-only optimizer transport. But polling races (H14), demo data shown as results (M6), a React version split (M11) and 163 warnings. |
| Engine separation | 2 | The core is clean. Production imports academic code and hosts academic runs (H8, H17). |
| Verification and CI | 3 | 3,399 + 315 passing tests locally, but CI runs only 8 Python test files (H20). |

### 2.3 Where the documentation overstates

Per `AGENTS.md`, these are discrepancies to report, not code to relabel as compliant.

| Documented claim | Observed code | Reference |
|---|---|---|
| "Solver-independent final certificate"; feasibility governance "implemented" (`ACTIVE_ROADMAP.md` Priority 1) | The certifier builds its matrix from the response it certifies. Its own docstring admits that provenance is deferred to "Package E". | `optimizer_api/verification/response_certifier.py:231-236, 374-390` |
| Matrix integrity: strict rejection of invalid arcs | Holds only once a matrix is loaded. Otherwise the code returns an all-zero matrix and never retries a failed first load. | `optimizer_api/utils/matrix_repository.py:239-243, 297-305` |
| The three heavy endpoints are protected by the internal key | The BFF benchmark routes are anonymous and forward requests with the key. Benchmark stop does not stop the worker thread. | `src/app/api/benchmark/run/route.ts:38-40`; `optimizer_api/benchmark_state.py:241-248` |
| ESLint: 0 errors / 158 warnings | 0 errors / 163 warnings today | ESLint JSON, 2026-09-30 |
| Old Numba 3-opt kernels are unreachable from public execution | Live in the final polish of the SOTA solvers | `uniride_core/algorithms/sota_tsp/ls_engine.py:142-150` |
| One canonical ID maps to one implementation; a `production_ready` gate exists | `Core-GWO-TSP` names two different solvers, and no production gate exists | `uniride_core/algorithms/engine_factory.py:28-34`; `optimizer_api/strategies/__init__.py:120-214` |
| ~~Work-package gates run A → B → C → D~~ | **Withdrawn in v1.1.** Gate A's criteria (design lines 422-429) are substantially met. The items v1.0 listed belong to Package D (run-manifest integration) or to a separate architecture plan (production → academic isolation). Residual Gate A hardening only: archive namespace importability and broader import scans. | Appendix C |
| Statistics protocol: Kruskal-Wallis/Mann-Whitney with Holm, or Friedman; no proof language | The dashboard's "Academic Proof" tab runs a Wilcoxon test with rows paired by position | `academic_benchmark/dashboard.py:326-388` |
| `CURRENT_ARCHITECTURE.md:39`: "General production compute is now protected end to end" *(added v1.1)* | Anonymous BFF benchmark routes forward requests with the internal key (C4) | `src/app/api/benchmark/run/route.ts:38-40` |
| `CURRENT_ARCHITECTURE.md:58`: "Academic execution remains separate from production request lifecycles" *(added v1.1)* | The production optimizer mounts the benchmark router and imports academic promoted configs (H8, H17) | `optimizer_api/main.py:18, 109`; `optimizer_api/strategies/promoted_config_loader.py:9` |

Documentation claims that **were confirmed**:
- the test counts (Python and Vitest), and that TypeScript is clean;
- constant-time key comparison;
- the frozen, lowering-only compute policy;
- `/compare` bounded as documented (at most 2 workers, 120 s soft deadline);
- that no GIS renderer exists;
- that the `GWO-LKH` and `HHO-LKH` names are rejected.

### 2.4 What is genuinely strong

- **Backend auth and edges** (Appendix F):
  - keys are compared with `secrets.compare_digest`;
  - the rate limiter does not trust `X-Forwarded-For`;
  - CORS uses an allowlist without credentials;
  - every request gets fresh strategy instances.
- **Frontend secrets:** the service-role key is confined to server code, and the optimizer is reached only through the server-only `optimizerFetch`.
- **Data access:** no IDOR in ride confirmation.
- **Fair-comparison gateway and pilots:**
  - accounting is exact (demonstrated for 2-opt, 3-opt, ALNS and GWO/HHO Pure and Memetic-2opt, on TSP and ATSP);
  - mixed protocols are rejected;
  - pilots enforce replay determinism and write their output atomically.
- **`uniride_core` imports nothing** from `optimizer_api`, `academic_benchmark`, `archive`, FastAPI or SQLite.

### 2.5 Where the audit brief's assumptions do not match the code

- **There is no map or GIS rendering.** No map library, canvas, GeoJSON or polyline code exists; `track-ride` shows a placeholder image. The map-memoization question therefore has no subject, and §7.1 audits the real heavy render surfaces instead.
- **There are no OSRM, Mapbox or Google Maps providers.** The only outbound calls are Supabase PostgREST (the `time_matrix` table) and a plain-HTTP TSPLIB download. Provider risk is concentrated in the Supabase matrix layer (C2, H5, H6, M4).
- **The strategy registry already hands out fresh request-scoped instances.** Shared mutable state lives elsewhere: the duplicated DataLoader (H5), benchmark state (C4), and the global `random` module used by clustering (H12).

---

## 3. Critical findings (fix now)

Each finding follows the same template: status, governing contract, locations, mechanism, evidence, reproduction, impact, fix, acceptance criteria, related findings.

### C1 — Anyone can self-register as admin, then read all student data and reset any password

- **Status:** `VERIFIED-LEAD` (repo code and SQL). **The live database has not been checked.**
- **Severity (v1.1):** Critical if the live policies and user provisioning match the repository SQL. The unsafe repository policy is a release blocker regardless (Codex concurs).
- **Category:** Security / data protection.
- **Sources:** lead finding; impact corroborated by P3.
- **Governing context:** `ACTIVE_ROADMAP.md` (Package 3 RLS is still open); KVKK obligations for disability data.

**Locations**
- `src/components/auth/register-form.tsx:2` (`"use client"`), `:69` (`role: "student"` placed in the payload by the client), `:75` (the `register()` call)
- `src/lib/supabase-auth.ts:121-157`: `signUp(..., role: User["role"] = "student", ...)` builds `newUser` with the caller-supplied `role` and calls `createUser`
- `src/lib/supabase-db.ts:19` (`getClient = () => getSupabaseClient()`, the browser anon client) and `:130-163`: `createUser` inserts into `users` (`.insert(dbData)` at `:151-155`)
- `supabase/rls_policies.sql:46-48`: `users_insert_self ... WITH CHECK (auth.uid() = id)`
- `supabase/rls_policies.sql:59-81`: `prevent_role_change()` and `enforce_no_role_change BEFORE UPDATE OF role`
- `supabase/schema.sql:12`: `role TEXT NOT NULL CHECK (role IN ('student', 'admin', 'driver'))`
- `src/lib/admin-auth.ts:70-99, 121-134`: `requireAdmin` reads `users.role` with the service-role client and trusts it
- Impact surface (P3):
  - `src/app/api/admin/users/route.ts:46-49`: `select("*")` returns every user's email, home address, accessibility needs and `password_hint`;
  - `src/app/api/admin/users/password/route.ts:19-29`: resets any account's password;
  - `src/proxy.ts:30-41`: checks token validity only, never the role.

**Mechanism**
1. The browser creates the `users` row itself, after `auth.signUp`, using the public anon key and the new user's JWT. The `role` value is a client-side variable.
2. RLS permits the insert whenever `id = auth.uid()`. The `CHECK` constraint accepts `'admin'`. The anti-escalation trigger fires **only on `UPDATE OF role`**, never on `INSERT`.
3. An attacker therefore signs up through the Supabase Auth API (the anon key ships in the client bundle) and inserts their own row with `role: 'admin'` through PostgREST. They can do this before or instead of the application's own insert, or simply by modifying the browser request.
4. `requireAdmin` then accepts them. That grants every admin BFF route: full user listing including PII and password hints, password resets of any account (including real admins), vehicles and Dudullu previews over live student data. Disability type is special-category personal data under KVKK.

**Evidence (before)**
```sql
-- supabase/rls_policies.sql:46-48
CREATE POLICY "users_insert_self"
  ON users FOR INSERT
  WITH CHECK (auth.uid() = id);

-- supabase/rls_policies.sql:78-81
CREATE TRIGGER enforce_no_role_change
  BEFORE UPDATE OF role ON users
  FOR EACH ROW
  EXECUTE FUNCTION prevent_role_change();
```
```ts
// src/lib/supabase-auth.ts:121-157 (excerpt)
export const signUp = async (email, password, name, studentNumber?,
  role: User["role"] = "student", userData?) => {
  ...
  const newUser: DbUser = { id: authData.user.id, name, email: authData.user.email!, role, ... };
  await createUser(newUser, authData.user.id);   // browser anon client -> INSERT INTO users
```

**Confirm live exposure** with read-only queries in the Supabase SQL editor:
```sql
select policyname, cmd, roles, qual, with_check from pg_policies where tablename = 'users';
select tgname, pg_get_triggerdef(oid) from pg_trigger where tgrelid = 'public.users'::regclass and not tgisinternal;
select count(*) filter (where role = 'admin') as admins from public.users;  -- compare with the expected admin list
```

**Fix (after)** — ship as a new migration, after confirming the live state:
```sql
-- 1. A self-insert can only ever create a student row
DROP POLICY IF EXISTS "users_insert_self" ON users;
CREATE POLICY "users_insert_self"
  ON users FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = id AND role = 'student');

-- 2. Guard the role column on INSERT as well as UPDATE
CREATE OR REPLACE FUNCTION prevent_role_change()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF auth.role() = 'service_role' THEN RETURN NEW; END IF;
  IF TG_OP = 'INSERT' AND NEW.role <> 'student' THEN
    RAISE EXCEPTION 'Only service_role may create non-student users';
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.role IS DISTINCT FROM OLD.role THEN
    RAISE EXCEPTION 'Direct role modification not allowed';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS enforce_no_role_change ON users;
CREATE TRIGGER enforce_no_role_change
  BEFORE INSERT OR UPDATE OF role ON users
  FOR EACH ROW EXECUTE FUNCTION prevent_role_change();

-- 3. Harden the existing SECURITY DEFINER helper
ALTER FUNCTION is_admin() SET search_path = public;
```
```ts
// src/lib/supabase-auth.ts: role is no longer caller-controlled
export const signUp = async (email, password, name, studentNumber?, userData?) => {
  ...
  const newUser: DbUser = { ..., role: "student", ... };
```

Also:
- Create admin and driver accounts only through the existing service-role route (`src/app/api/admin/users/route.ts:103`, behind `requireAdmin`).
- Preferably move the creation of the `users` row server-side, either via a BFF route or an `auth.users` insert trigger with `SECURITY DEFINER`.
- Remove `password_hint` from `select("*")` responses (see H1 and LT5).

**Acceptance criteria**
- A pgTAP or SQL test running as `authenticated` fails to insert `role='admin'` or `'driver'` for itself and fails to update its own `role`.
- `service_role` can still create admins.
- The registration E2E test still produces a student row.
- The live `pg_policies` query shows the new `WITH CHECK`.

**Related:** C1.b, H1, M21, LT5.

#### C1.b — Students can set any `ride_requests.status`, bypassing admin approval

- **Status:** `VERIFIED-LEAD` (SQL); live state not checked.
- **Severity (v1.1): High** (re-rated from Critical). The gap is limited to the attacker's own requests, and no consequence in the current Dudullu planning/publication flow is verified; legacy routing does read `confirmed` rows. Re-rate to Critical if a live dispatch path that consumes `ride_requests.status` is shown (Q20).
- **Locations:**
  - `supabase/rls_policies.sql:104-116`: `ride_requests_insert_own WITH CHECK (auth.uid() = user_id)` and `ride_requests_update_own USING (auth.uid() = user_id)`;
  - `supabase/schema.sql:35-58`: statuses include `confirmed`, `in_progress`, `completed` and `pending_admin_approval`.
- **Mechanism:** students may insert or update their own rows with **any** status and any `vehicle_id` or `actual_*_time`. P3 notes the BFF's only student write sets `pending_admin_approval` (`src/app/api/ride-confirmation/route.ts:93-95`), and its `legacyBlocker` is computed from `ride_requests.status` (`:141-154`). RLS lets a student bypass or clear both.
- **Fix:**
  ```sql
  DROP POLICY IF EXISTS "ride_requests_insert_own" ON ride_requests;
  CREATE POLICY "ride_requests_insert_own" ON ride_requests FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id
                AND status IN ('pending_admin_approval', 'pending_student_confirmation')
                AND vehicle_id IS NULL AND actual_pickup_time IS NULL AND actual_dropoff_time IS NULL);
  DROP POLICY IF EXISTS "ride_requests_update_own" ON ride_requests;
  CREATE POLICY "ride_requests_update_own" ON ride_requests FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id AND status = 'cancelled_by_student');
  ```
  Alternatively, route every student write through the BFF with service-role and drop student UPDATE.
- **Acceptance:** an authenticated student cannot set `confirmed`, `in_progress` or `completed`, and the BFF flows still pass.

### C2 — The travel-time matrix fails open to zeros, and the "solver-independent" certificate approves whatever durations the solver reports

- **Status:** `VERIFIED-LEAD` (repro).
- **Category:** Production correctness / safety.
- **Sources:** P1A-01, P2-01; both demonstrated by investigators and re-run by the lead.
- **Governing context:** `CURRENT_ARCHITECTURE.md` §5 (matrix contract); `ACTIVE_ROADMAP.md` Priorities 1 and 5.

**Locations**
- `optimizer_api/utils/matrix_repository.py`:
  - `:158-176`: a failed **first** load sets coordinate mode and `_loaded_at=None`;
  - `:239-243`: `_is_cache_stale` returns `False` while `_loaded_at is None`, so the load is never retried;
  - `:293-305`: `get_submatrix` refreshes only in matrix mode; in coordinate mode with no coordinates it returns `[[0.0]*n ...]`;
  - `:314-318`: `get_duration` returns `0.0`;
  - `:492-509`: the coordinate fallback builds Euclidean distances in lat/lng **degrees**, later used as minutes.
- `optimizer_api/utils/data_loader.py:54-69`; `optimizer_api/runtime_config.py:82-100`: missing Supabase credentials are not a startup error, and `.env.example:63-64` marks the URL "Optional".
- `optimizer_api/strategies/ga_split_strategy.py:142`: split strategies call `get_submatrix(physical_ids)` without coordinates, so they receive the zero matrix.
- `optimizer_api/verification/response_certifier.py:231-236` (docstring: the matrix is "synthesized from the response's own route_details") and `:374-390`: `matrix[src][dst] = duration` with `duration >= 0.0` accepted.
- `uniride_core/algorithms/ortools_cvrp_engine.py:65` (`int(round(float(value) * scale))`) and `:178-180` (reports `duration = matrix[from][to] / scale`); `optimizer_api/strategies/holistic_response_builder.py:96, 105` copies them.
- H5: readiness and the solver use different DataLoader singletons, so readiness reports healthy while the solver copy stays empty.
- Reachable through authenticated BFF calls that are not bound to a snapshot: `src/services/optimizer-service.ts:223, 316` and `src/app/api/sandbox/route.ts:177`. The main `/api/optimize-route` proxy never sends `expected_matrix_sha256`.

**Mechanism**
1. **Fail-open matrix.** If Supabase credentials are absent, or the first fetch fails transiently, the repository enters coordinate mode. Split, greedy and permutation strategies then receive an all-zero matrix, and Pipeline A strategies receive degree-based Euclidean "minutes".
2. **No recovery.** Because `_loaded_at is None`, `_is_cache_stale()` returns `False` and `get_submatrix` never refreshes in coordinate mode. The state persists until restart. A forced refresh through `/matrix-snapshot` reaches the *other* DataLoader singleton (H5).
3. **Self-referential certificate.** The certificate checks capacity, coverage, chain continuity, duration and time windows against a matrix built from the response's own step durations. Zero-minute arcs, degree-based arcs and rounded arcs are therefore all "consistent", and the result certifies.
4. **Rounding even with a healthy matrix.** OR-Tools scales arcs by 10 and rounds. Reported durations can be up to 0.05 min per arc lower than the truth, enough to hide a violation of `max_travel_time`.

**Reproduction** (Appendix H.2–H.4; lead re-run, 2026-10-01)
```text
repro_c2_zero_matrix:      ga_split success True total_duration 0.0 steps [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]] cert True 0
                           genetic_algorithm success True total_duration 2.83 steps [[0.28, 0.28, 0.28, 0.57, 0.28, 1.13]] cert True 0
repro_c2_ortools_rounding: reported 60.0, step durations [10.0 x 6], TRUE 60.24, max 60 -> certificate is_feasible: True
repro_c2_h5_dual_singleton: 1 unbound optimize (first load failed): success=True total=0.0 feasible=True
                           3 readiness: {'source': 'supabase', 'ready': True}; 4 same singleton? False (solver repo: empty)
                           5 unbound optimize after readiness recovered: success=True total=0.0 feasible=True
```

**Impact**
- Zero-minute or meaningless routes are returned as `success=True` with `is_feasible=True` and can be saved as route plans.
- Readiness reports healthy at the same time.
- Real violations of `max_travel_time` are hidden by rounding even when the matrix is healthy.

**Scope (v1.1).** Requests bound to a snapshot (`expected_matrix_sha256`) already fail closed when the snapshot is unavailable or changed (`optimizer_api/routers/optimization.py:211-234`; Appendix H.4 steps 6 and 9). The fail-open applies to unbound requests, and the rounding gap applies with any matrix. The certificate is structurally separate from the solver but not independent of its costs: wrapping the self-reported durations again would not fix it. It must certify against the same immutable snapshot the solve used (Codex concurs).

**Fix (before)**
```python
# optimizer_api/utils/matrix_repository.py:239-243
def _is_cache_stale(self) -> bool:
    with self._lock:
        if self._loaded_at is None or self._ttl_seconds <= 0:
            return False                  # failed first load => "fresh" forever
        return (self._clock() - self._loaded_at) > self._ttl_seconds

# :293-305 (get_submatrix)
    with self._lock:
        if not self._use_coordinates and self.time_matrix is not None:
            self.refresh()                # never reached in coordinate mode
        if self._use_coordinates or self.time_matrix is None:
            if coordinates: ...           # lat/lng degrees used as minutes
            return [[0.0] * n for _ in range(n)]

# optimizer_api/verification/response_certifier.py:374-390
    matrix = [[0.0] * dimension for _ in range(dimension)]
    ...
            duration = float(step.duration)            # the solver's own claim
            valid = math.isfinite(duration) and duration >= 0.0
            ...
            matrix[src][dst] = duration
```

**Fix (after)** — a sketch. `physical_code` and `authoritative_snapshot_for` stand for the existing snapshot-binding helpers (`routers/optimization.py::_matrix_snapshot_for_request` and the repository's `_arc_value`).
```python
def _is_cache_stale(self) -> bool:
    with self._lock:
        if self._loaded_at is None:
            return self._provider is not None        # never loaded => retry (after backoff)
        if self._ttl_seconds <= 0:
            return False
        return (self._clock() - self._loaded_at) > self._ttl_seconds

def get_submatrix(self, request_locations, coordinates=None, geo_coords=False, asymmetric_haversine=False):
    self.refresh()                                     # also retries a failed first load
    with self._lock:
        if self._use_coordinates or self.time_matrix is None:
            if not self._allow_coordinate_fallback:    # explicit dev/test opt-in only (env flag, default False)
                raise MatrixSnapshotError("authoritative travel-time matrix unavailable")
            ...                                        # existing fallback, now opt-in
        return [[self._arc_value(a, b) for b in request_locations] for a in request_locations]

# certifier: re-cost every step on the snapshot the solve was bound to
snapshot = authoritative_snapshot_for(request)
for route_index, route in enumerate(response.routes or []):
    for step in route.route_details or []:
        src, dst = loc_to_node.get(str(step.location1)), loc_to_node.get(str(step.location2))
        if src is None or dst is None:
            continue
        expected = snapshot.arc(physical_code(src), physical_code(dst))
        if abs(float(step.duration) - expected) > _ROUNDING_TOLERANCE_STEP:
            pre_violations.append({"type": "arc_duration_mismatch", "severity": "error",
                                   "route_index": route_index,
                                   "details": f"{step.location1}->{step.location2}"})
        matrix[src][dst] = expected                    # feasibility checks use truth, not claims
```

Also:
- Have OR-Tools report raw float arcs (`duration = float(time_matrix[from_node][to_node])` at `ortools_cvrp_engine.py:178`).
- Return the matrix source, version, SHA-256 and age in every response (MT2).
- Make missing Supabase credentials a startup error when `APP_ENV=production`.

**Acceptance criteria**
- With the provider failing on the first call, `/optimize` returns `success=False` with a "matrix unavailable" reason, and a later call succeeds once the provider recovers, without a restart.
- Every response carries matrix provenance.
- The OR-Tools rounding repro yields `arc_duration_mismatch` or a duration violation.
- The Appendix H.2–H.4 scripts flip to the fail-closed behavior and become regression tests.

**Related:** H5, H6, M3, M4, H18, H19.

### C3 — A local-search cache keyed by `id()` feeds one problem's matrix into another problem's run

- **Status:** `VERIFIED-LEAD` (repro).
- **Category:** Scientific evidence integrity.
- **Source:** P1B-01.
- **Governing contract:** `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md`; `ACADEMIC_STUDY_UNIFICATION_DESIGN.md` (result validation).

**Locations**
- `uniride_core/algorithms/local_search_numba.py:74` (module-level `_DIST_MATRIX_CACHE`), `:96-98` (the docstring claims different problems "never share a matrix"), `:109-114` (key and lookup), `:135` and `:149` (stores).
- Reached by:
  - `academic_benchmark/core/registry_setup.py:380/402 → 413/419`: every `Numba-*` ID, plus `Core-TwoOpt/ThreeOpt/OrOpt-TSP` whenever there is no fair/native manifest;
  - `academic_benchmark/cli_engine.py:602-617`;
  - `uniride_core/algorithms/numba_metaheuristics.py:348-365`, including the GA/PSO/GWO/HHO memetic 2-opt (`:86`).

**Mechanism**
1. Each run builds a fresh duration function (`create_np_duration_func`), and same-dimension instances share the node labels `L1..Ln`, so the `frozenset` part of the key is identical.
2. When the previous function is garbage-collected, CPython reuses its memory address, and therefore its `id()`. A later problem then hits the stale entry.
3. The `_np_dist_matrix` fast path (`:116-136`) is consulted only **after** the cache lookup, so it doesn't prevent the hit.
4. The tour is re-scored on the correct matrix, so the corruption shows up as a valid but poor tour.
5. ProcessPool workers (`cli_engine.py:1076`) reuse processes and are affected too. The cache is also unbounded.

**Reproduction** (Appendix H.1; lead re-run)
```text
P1 seed=11 shared-process=6595.6  clean-cache=6595.6
P2 seed=11 shared-process=31434.5 clean-cache=6744.7   <-- DIFFERENT (stale matrix)
P2 seed=12 shared-process=32994.0 clean-cache=6399.4   <-- DIFFERENT (stale matrix)
P3 seed=11 shared-process=30743.3 clean-cache=6413.1   <-- DIFFERENT (stale matrix)
P3 seed=12 shared-process=30523.0 clean-cache=6623.0   <-- DIFFERENT (stale matrix)
runs corrupted: 4 of 6
```

**Impact:** any multi-instance batch (for example kroA100…kroE100) run through these paths without a manifest may contain silently degraded results. Treat such existing results as **suspect** and rerun them after the fix (LT1).

**Scope (v1.1).** The governed fair/native manifest branches (`academic_benchmark/core/registry_setup.py:345-365`) use a direct matrix and accounting path that bypasses this cache, so governed pilot results are not implicated by this reproduction. Decide quarantine or rerun per result provenance (Q17), not wholesale. Codex re-ran Appendix H.1 unchanged and observed the identical 4-of-6 corruption.

**Fix (before)**
```python
_DIST_MATRIX_CACHE: Dict[Tuple, Any] = {}
...
unique_locs = list(dict.fromkeys(route))
cache_key = (frozenset(unique_locs), id(duration_func))   # id() is recycled after GC
cached = _get_cached_matrix(cache_key)
if cached is not None:
    return cached                                         # may be another problem's matrix
```

**Fix (after)**
```python
import weakref
# Entries die with their duration_func, so a recycled id() can never hit them.
_DIST_MATRIX_CACHE = weakref.WeakKeyDictionary()

def _per_func_cache(duration_func):
    try:
        with _DIST_MATRIX_CACHE_LOCK:
            return _DIST_MATRIX_CACHE.setdefault(duration_func, {})
    except TypeError:            # not weak-referenceable: skip caching, never alias
        return None

unique_locs = list(dict.fromkeys(route))
per_func, cache_key = _per_func_cache(duration_func), frozenset(unique_locs)
if per_func is not None and cache_key in per_func:
    return per_func[cache_key]
...                              # build exactly as today, then (replacing :135 and :149):
if per_func is not None:
    with _DIST_MATRIX_CACHE_LOCK:
        per_func[cache_key] = result
```
Preferred (v1.1): pass the already available prebuilt matrix explicitly through the live callers and use it **before** any cache. Keep a cache only if profiling shows it is needed, with a real, bounded lifetime as above; do not add a second global cache.

**Acceptance criteria**
- A regression test solves two same-size, different problems back to back in a loop with `gc.collect()` between them, and asserts that each run's cached matrix equals its own problem's matrix.
- The Appendix H.1 script reports `runs corrupted: 0 of 6`.
- The `CANONICAL_THREE_OPT_DESIGN.md` regression command passes.

**Related:** H9, H13, LT1.

### C4 — Anyone can start benchmark runs in the production optimizer, and "stop" does not stop them

- **Status:** `VERIFIED-LEAD` (repro; BFF side re-read).
- **Severity (v1.1):** Critical when the Next.js app is publicly reachable and the benchmark router is mounted in the deployed optimizer (Q15, Q18; neither verified). The broken status/admission invariant is a defect regardless (Codex reproduced it with finite fake workers).
- **Category:** Availability / security.
- **Sources:** P3-01, P2-02, P4-01.
- **Governing context:** `CURRENT_ARCHITECTURE.md` (compute protection); `ACTIVE_ROADMAP.md` Priorities 2–3.

**Locations**
- BFF:
  - `src/app/api/benchmark/run/route.ts:38-40`: the POST handler goes straight to `request.json()` with no auth;
  - the same holds for all 13 `/api/benchmark/*` routes (academic/best, academic/leaderboard, academic/problems, health, param-spaces, problems, results/[runId], run, run/status, run/stop, status, stop, strategies);
  - `src/proxy.ts:44-46`: the matcher is `['/api/admin/:path*']` only;
  - `src/lib/optimizer-server.ts`: `optimizerFetch` attaches `X-Internal-API-Key`;
  - `src/lib/benchmark-backend-request.ts:65-68`: algorithm `params` are passed through unchanged;
  - `src/app/page.tsx:467`: the anonymous landing page `/` renders `BenchmarkSuitePage`, which calls these routes.
- Backend:
  - `optimizer_api/benchmark_state.py:41` (`MAX_CONCURRENT_BENCHMARKS = 3`), `:152-157` (only RUNNING runs count), `:241-248` (`stop_run` only changes the status);
  - `optimizer_api/benchmark_runner.py:254, 272` (the loop checks its own `self.running`, which nothing external clears);
  - `optimizer_api/routers/benchmark.py:311-317` (the runner is created inside the daemon thread and never registered);
  - `optimizer_api/benchmark_runner.py:453` (`request.ga_config = config_params`, assigned after model validation and never checked against the compute policy);
  - `optimizer_api/models/schemas.py:499-508, 548-550` (up to 100k iterations or population, `n_runs ≤ 100`; `max_no_improvement` and `time_limit` unbounded);
  - `optimizer_api/routers/benchmark.py:31-35` (any tenant key unlocks the router, and it has no rate limit).
- The BFF reads `error.error` while FastAPI returns `detail` (`run/route.ts:122`), so a 429 is shown as "Benchmark servisine bağlanılamadı".

**Mechanism**
1. Anonymous internet users can start benchmarks: the BFF adds the internal key on their behalf (a confused deputy).
2. Stop marks a run STOPPED, which frees one of the 3 slots, while the worker thread continues.
3. Parameters bypass the compute policy, so each run can be configured for hours of CPU.
4. Only the attacker's browser holds the owner cookies needed to stop those runs.

**Reproduction** (Appendix H.5; lead re-run): three starts return 200 and a fourth returns 429. After two stop/start rounds, `benchmark threads alive = 9`, six of them reporting `stopped`. Each was configured for population 5000 × 100k iterations × 100 runs.

**Impact:** anonymous CPU exhaustion of the production optimizer, starving `/optimize` and `/compare`, and the threads cannot be stopped short of a restart.

**Fix**
```ts
// every src/app/api/benchmark/**/route.ts handler (or route the academic console to a separate admin-only service)
export async function POST(request: NextRequest) {
  try {
    await requireAdmin(request);
    const body = await request.json();
    /* … */
  } catch (error) { return handleApiError(error); }
}
// src/proxy.ts
export const config = { matcher: ['/api/admin/:path*', '/api/benchmark/:path*'] };
```
```python
# optimizer_api/benchmark_state.py
def stop_run(self, run_id, message=""):
    with self._lock:
        s = self._runs.get(run_id)
        if s and s.status == BenchmarkStatus.RUNNING:
            s.stop_event.set()        # stays RUNNING (holds its slot) until the thread exits
# runner loop:  if self.state_manager.stop_requested(self.run_id): break
# routers/benchmark.py: dependencies=[Depends(require_internal_api_key), Depends(require_rate_limit)]
# benchmark_runner.py:453: validate params with the compute policy's validate_tuning_dict before assigning
```

**Acceptance criteria**
- An anonymous POST to any `/api/benchmark/*` route returns 401.
- After stop, the worker thread exits within one experiment.
- The slot is released only on thread exit.
- Parameters above the policy ceilings are rejected with 422.
- The Appendix H.5 script shows no live threads after stopping.

**Related:** H7, H8, H14, MT3, MT4.

### C5 — The dashboard prints publication-ready "significantly outperforms" claims from invalid statistics

- **Status:** `VERIFIED-LEAD`.
- **Category:** Scientific integrity.
- **Source:** ACAD-01.
- **Governing contract:** `ACADEMIC_STUDY_UNIFICATION_DESIGN.md` §Statistical Protocol; `AGENTS.md` ("Smoke or pilot runs cannot produce superiority, causality, or proof claims").

**Locations**
- `academic_benchmark/dashboard.py:326-388`: the tab is headed "Wilcoxon Signed-Rank Test (Academic Proof)".
- Launched by `academic_benchmark/__main__.py:10-19` (`python -m academic_benchmark dashboard`).
- Data comes from `dashboard.py:39-90` and `dashboard_utils.py:52-59`.

**Mechanism**
- `wilcoxon(data_A, data_B)` (`:347`) pairs `avg_gap` arrays **by row order**; database rows come out newest first. The only precondition is equal lengths (`:346`), with no matching on `seed_group` or replicate.
- The rows are unvalidated and pooled across protocols, budgets and implementations, including web and smoke runs and CLI averages relabelled as raw (H8, H9).
- Each problem is tested at α = 0.05 with no Holm correction and no effect sizes. The "winner" is chosen by mean.
- The LaTeX sentence (`:368-373`) reports only B's wins and the ties. `losses` is computed (`:365`) but **never printed**, which is selective reporting.
- SciPy is not pinned anywhere and is absent from `.venv-jit`. The tab is live on any machine that has SciPy and Streamlit.

**Fix**
```python
# before (dashboard.py:346-347)
if len(data_A) > 0 and len(data_B) > 0 and len(data_A) == len(data_B):
    stat, p_val = wilcoxon(data_A, data_B, zero_method='zsplit')
# after (until the Package D analysis service exists)
st.info("Inferential tests disabled: rows are not validated, protocol-homogeneous "
        "or seed_group-paired. Use the Package D analysis service.")
```

**Note (v1.1):** this is not evidence that any submitted paper contains such claims. It is a blocker for using this dashboard as evidence.

**Acceptance:** the tab can no longer emit an inferential claim. Package D (LT1) reintroduces inference over validated, protocol-homogeneous records matched on `seed_group`, with Kruskal-Wallis → Mann-Whitney and Holm correction (or Friedman for matched designs), effect sizes and exact sample counts.

**Related:** H8, H9, M20, LT1.

---

## 4. High findings (fix next)

### H1 — `/api/auth/hint` shows password hints to anyone and reveals which accounts exist

- **Status:** `CONFIRMED` (enumeration and disclosure); the limiter bypass is `PLAUSIBLE`.
- **Source:** P3-02.
- **Locations:** `src/app/api/auth/hint/route.ts:43-47, 88-101`.
- **Mechanism:**
  - An unknown user receives `{ hint: null, message }`. An existing user always receives a non-null string: either the real hint or "Bu hesap için özel bir ipucu tanımlanmamış.". `hint === null` therefore exactly identifies a non-existent account, contradicting the comment at `:91`.
  - Any account's real hint is returned without login, and student numbers (`^[a-zA-Z0-9_-]{3,32}$`) can be iterated.
  - The rate-limit key is `x-forwarded-for.split(',')[0]`, held in an in-memory Map at 5 requests per minute per instance. The first XFF entry is client-supplied when a front proxy appends its own.
- **Confirm the limiter bypass by:** sending varied `X-Forwarded-For` headers to the App Hosting deployment.
- **Fix sketch:**
  ```ts
  // before
  if (error || !data) return NextResponse.json({ hint: null, message: "…" }, { status: 200 });
  return NextResponse.json({ hint: userWithHint.password_hint || "Bu hesap için özel bir ipucu tanımlanmamış." });
  // after: identical anonymous response; hint delivered out-of-band
  if (!error && data?.password_hint) await queueHintEmail(normalizedInput, data.password_hint);
  return NextResponse.json({ message: GENERIC_HINT_MESSAGE }, { status: 200 });
  ```
  Key the limiter on a platform-trusted IP and a shared store. Long term, remove password hints entirely (LT5).
- **Acceptance:** responses for existing and non-existing accounts are byte-identical, and no hint ever appears in a response body.

### H2 — Pickup routes: the return arc to school and waiting time are never checked

- **Status:** `CONFIRMED` (demo).
- **Source:** P1A-02.
- **Severity note:** this becomes Critical if "arrive at school by `target_time` (− offset)" is an approved hard constraint (Appendix G, Q2).
- **Locations:**
  - `uniride_core/algorithms/feasibility_certificate.py:206-277` (pickup branch) and `:169` (`check_duration` counts travel only, via `calculate_route_cost`);
  - `uniride_core/algorithms/string_split_decoder.py:415-452`.
- **Mechanism:**
  - The start time is fixed at `current = float(latest) - route_cost - float(offset_minutes)`.
  - The loop waits (`elif current < earliest: current = earliest`) and stops at the last student, with no check of `mat[prev, depot]`.
  - Waiting time is not counted against `max_travel_time`.
- **Failure scenario:** target 08:30, offset 15, two students without `pickup_time` (windows 08:00–08:30); arcs D→A 10, A→B 20, B→D 20.
  - The certificate starts at 07:25. A is reached at 07:35 and waits until 08:00; B is reached at 08:20, and the school at 08:40.
  - Every possible start time reaches the school at 08:40 or later.
  - `/optimize` with `ga_split` returns `success=True` with a feasible certificate, and the 25 minutes of waiting go uncounted.
- **Fix sketch:**
  ```python
              prev = node
          if direction.lower() == "pickup" and current + float(mat[prev, depot]) > float(latest):
              violations.append(Violation(TIME_WINDOW_VIOLATION, "error",
                                          f"Route {idx} reaches depot after {latest}", idx))
  ```
  Measure duration as return time minus departure, including waits. Mirror the change in `SplitDecoder._build_trips_with_tw`. The real fix is one shared simulator (MT1).
- **Acceptance:** the scenario above is rejected, and a property test over random routes shows that certificate feasibility implies arriving by the target.

### H3 — The returned `arrival_times` and `departure_time` come from a third, uncertified schedule model

- **Status:** `CONFIRMED` (demo).
- **Source:** P1A-03.
- **Locations:** `uniride_core/algorithms/route_scheduling.py:37-64`; `optimizer_api/routers/optimization.py:261-271`.
- **Mechanism:**
  - For pickup, the last stop is anchored at its own window close (`target_minutes = time_windows[loc].latest`), and the schedule then walks backwards with no waits and no return arc.
  - It is computed before certification, and the certifier never reads `arrival_times`.
- **Failure scenario:** target 08:30. Student A has `pickup_time` 08:00 (window 07:30–08:00); B has none (08:00–08:30). Arcs: D→A 10, A→B 5, B→D 10.
  - The response says `arrival_times = {LA: 08:25, LB: 08:30}` with departure 08:00: A is picked up 25 minutes after its window closes, and the school is reached at 08:40.
  - The certificate checked a different schedule: depart 07:50, A at 08:00, school at 08:15.
- **Fix sketch:**
  ```python
  sched = simulate_route(nodes, matrix, windows, direction, target, offset)  # same fn as check_time_windows
  route.departure_time = minutes_to_time(sched.departure)
  route.arrival_times = {k: minutes_to_time(t) for k, t in sched.arrivals.items()}
  ```
- **Acceptance:** returned times equal the certificate's simulation for every route, enforced by an equality assertion in the tests.
- **Open question:** does any client consume these fields? The frontend only declares them in its types.

### H4 — The production metaheuristics ignore time windows during search

- **Status:** `CONFIRMED`.
- **Source:** P1A-04.
- **Locations:**
  - `uniride_core/algorithms/ga_split_engine.py:109-118, 132, 379-393`; `gwo_split_engine.py:123-135, 222-236`; `pso_split_engine.py:146, 248`; `hho_split_engine.py:164, 272`; `objective_rank.py:36`;
  - `string_split_decoder.py:419-421, 442, 469-471, 533`;
  - `optimizer_api/strategies/ortools_cvrp.py:64-72`; `optimizer_api/strategies/pyvrp_strategy.py:102-110`.
- **Mechanism:**
  - The search only calls `decode_giant_tour(...)`, which has no windows. The feasibility key is `num_vehicles_int > 0 and math.isfinite(total_cost_float)`.
  - Windows appear only in the final soft decode, `decode_with_time_windows`. That decoder truncates arcs with `int(travel_time)`, anchors pickup at `self.target_time or (9 * 60)`, and for dropoff uses only the first stop's window.
  - OR-Tools, PyVRP and Pipeline A receive no windows. PyVRP also receives no `max_route_duration`.
- **Failure scenarios:**
  - Arcs 10.9 / 10.9 / 10.2, with A's window closing at 07:53. The decoder reports 0 violations and the strategy reports success, but the certificate rejects ("arrival 473.9 exceeds latest 473"), even though departing at 07:42 would be feasible.
  - One student with pickup 07:30 and no `target_time`. `ga_split` is anchored to 09:00, reports 1 violation and fails, while `genetic_algorithm` certifies.
- **Effect:** the system fails closed, but realistic time-window requests return `success=False`.
- **Fix sketch:**
  ```python
  # ga_split_engine.py:109/132  before: result = decode_giant_tour(...); key = objective_key(...)
  result = decode_final_tour(chrom, depot, dm, demands, sw, so, max_dur, use_time_windows=use_tw,
      time_windows=tw, direction=direction, target_time=target, offset_minutes=offset)
  key = (int(result.get("time_window_violations", 0)),) + objective_key(result)
  ```
  Pass windows and maximum duration to OR-Tools and PyVRP (MT1).
- **Acceptance:** on a time-window benchmark set, the share of `success=False` caused by windows drops, and the solver's ranking key equals the certificate's verdict.

### H5 — Two DataLoader singletons: readiness and the solver use different matrix repositories

- **Status:** `VERIFIED-LEAD` (repro).
- **Sources:** P2-03, P4-07.
- **Locations:**
  - `optimizer_api/routers/readiness.py:10-17` imports `optimizer_api.utils.data_loader` (try) or `utils.data_loader`;
  - `optimizer_api/routers/optimization.py:56` and all strategies import `utils.data_loader`;
  - `optimizer_api/utils/patterns.py:21-31`: `SingletonMeta` instances are keyed by class object;
  - `optimizer_api/main.py:18-19`.
- **Mechanism:**
  - With the repository root importable (editable install, or the launcher's working directory), the module loads twice. That gives two classes, two singletons, two Supabase loads and two TTL timers.
  - `/matrix-snapshot` force-refreshes the readiness copy. The snapshot-binding check in `/optimize` reads the solver copy, which may be empty or stale.
- **Reproduction** (Appendix H.4): `same singleton? False | solver repo: empty | readiness repo: supabase`. After the TTL, step 9 reads `bound optimize right after fresh snapshot: success=False certify_error=matrix snapshot unavailable or changed`.
- **Impact:** readiness describes a matrix the solver is not using. In production (TTL 600 s), **snapshot-bound Dudullu previews fail** unless an unbound solve refreshed the solver copy within the previous 10 minutes. This bears directly on the current next task, Dudullu Package 2.
- **Fix sketch:**
  ```python
  # readiness.py, before
  try:
      from optimizer_api.utils.data_loader import DataLoader
  except ModuleNotFoundError:
      from utils.data_loader import DataLoader
  # after: one import root everywhere (or run `uvicorn optimizer_api.main:app` and use package imports consistently)
  from utils.data_loader import DataLoader
  # and in optimization._matrix_snapshot_for_request: call loader.refresh() before the binding check
  ```
- **Acceptance:**
  - `sys.modules` contains only one of `utils.data_loader` / `optimizer_api.utils.data_loader` after `import main`.
  - Appendix H.4 step 4 prints `True`, and steps 6 and 9 succeed.
  - Add a boundary test for this.

### H6 — The async readiness endpoints call Supabase synchronously and block the event loop

- **Status:** `VERIFIED-LEAD` (repro).
- **Source:** P2-04.
- **Locations:** `optimizer_api/routers/readiness.py:57, 74-79, 84, 96-98`; `optimizer_api/utils/matrix_repository.py:178-197, 293-296`.
- **Mechanism:**
  - `async def matrix_snapshot` calls `loader.refresh(force=True)` on every call. That runs a synchronous supabase-py/httpx fetch (10 s timeout per phase) on the event-loop thread.
  - `readiness_summary` and `matrix_snapshot` also block on the repository lock, which `get_submatrix` holds while it refreshes over the network.
- **Reproduction:** `/health` took 14 ms when idle and **2,703 ms** during a 3 s fake fetch (Appendix H.4, step 10).
- **Fix sketch:**
  ```python
  # before (inside async def)
  loader.refresh(force=True)
  # after
  snapshot = await run_in_threadpool(_snapshot_sync, codes)   # TTL-based refresh inside, no per-call force
  ```
- **Acceptance:** `/health` p99 latency stays under 50 ms while a snapshot fetch is in flight.

### H7 — No global cap on solver work; `/compare` threads outlive the soft deadline; `/optimize` has no time limit

- **Status:** `CONFIRMED` for the thread leak and the missing cap; `PLAUSIBLE` for the runtime extrapolation.
- **Source:** P2-05.
- **Locations:**
  - `optimizer_api/routers/optimization.py:228` (`strategy.optimize(request)` with no deadline), `:516-518` (a new executor per request), `:558` (`shutdown(wait=False, cancel_futures=True)`);
  - `optimizer_api/compute_policy.py:31-38`;
  - `optimizer_api/rate_limit.py:24-28` (30 requests per 60 s per key, and all BFF traffic shares one key);
  - `optimizer_api/main.py:94-95` (`/health` is sync).
- **Mechanism:**
  - Each `/compare` leaves up to 2 detached solver threads running; queued futures are cancelled.
  - The rate limit allows about 60 new detached threads per minute with no global cap.
  - Every in-flight request also holds one AnyIO worker from the default pool of 40, the same pool `/health` uses.
  - `/optimize` may legally request population 250 × 2000 iterations at n = 250.
- **Evidence:**
  - With the deadline lowered to 2 s, each of 3 `/compare` calls returned in about 2.2 s, and live executor threads went 2 → 3 → 4 with `max_workers=2`.
  - Two small `ga_split` runs at n = 250 (120 individual-generations in total) had not finished after 100 s. That extrapolates to hours at the ceilings.
- **Fix sketch:**
  ```python
  _SOLVER_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_SOLVES)
  def _guarded(fn, *args):
      if not _SOLVER_SLOTS.acquire(timeout=1):
          raise SolverCapacityError()        # 503 + Retry-After
      try:
          return fn(*args)
      finally:
          _SOLVER_SLOTS.release()
  ```
  Acquire the semaphore inside the worker, so detached runs keep their slot. Pass a cooperative deadline into strategies, and give `/optimize` a wall-clock budget. Then move to process isolation with hard cancellation (MT3).
- **Acceptance:** the number of live solver threads never exceeds the cap, and a request over capacity receives 503 with `Retry-After`.

### H8 — The production process runs academic benchmarks and writes unlabelled rows into the academic database

- **Status:** `CONFIRMED` for the code path; the actual database contents are unknown (`tsplib.db` was not inspected).
- **Sources:** P4-01, ACAD-02.
- **Locations:**
  - Hosting and persistence:
    - `optimizer_api/main.py:18, 109`: the benchmark router is always mounted;
    - `optimizer_api/routers/benchmark.py:302-317` (quick-runner thread), `:336` and `:383-437` (the matrix-native path calls `save_benchmark_run` and `save_benchmark_result`), `:137-214` (`/academic/*`), `:51-52` (`/cli/import` reads `optimizer_api/tests/benchmark_results`);
    - `academic_benchmark/tsplib_manager.py:93-102, 128-151, 467-508`: no columns for protocol, budget, seed, validation or canonical ID;
    - `uniride_core/benchmark_runner.py:115-140`: persists the solver's own `tour_length` without checking the tour.
  - Writers: `academic_benchmark/cli_engine.py:1475-1500, 2059-2101` store `"run_number": 1, "tour_cost": row.get("avg_length"), "gap": row.get("avg_gap")`.
  - Relabelling: `academic_benchmark/dashboard_utils.py:56-59` turns these into `"n_runs": 1, "result_type": "raw"`.
  - Unfiltered readers:
    - `academic_benchmark/results_reader.py:23-74` → `optimizer_api/routers/benchmark.py:137-189` → `src/app/api/benchmark/academic/{leaderboard,best}`;
    - `academic_benchmark/promoted_configs.py:27-58, 250-257` (default `min_evidence_runs=1`);
    - `academic_benchmark/dashboard.py:87`.
- **Mechanism:**
  - Fixed-budget and native rows cannot be told apart, and validated and unvalidated rows share one table.
  - Promotion picks a single best row across all sources, and the leaderboard sorts raw tour lengths across different problems.
  - `best_solutions.tour_length` takes `avg_length` with `tour=[]`.
  - `benchmark_runs.source='web_matrix_native'` is the only marker, and no reader filters on it.
- **Evidence:** a demo turned a 30-run CLI aggregate into `{'n_runs': 1, 'result_type': 'raw'}`.
- **Escalation:** this becomes Critical if `tsplib.db` already contains `web_matrix_native` or pre-governance rows that feed reported results. Confirm with a read-only query on a copy.
- **Fix sketch:**
  ```python
  # serialize_preflight_decision: persist protocol provenance
  return {"protocol": decision.protocol.value, "evaluation_budget": decision.evaluation_budget,
          "validation_status": "passed",
          "requested_algorithm_id": ..., "canonical_algorithm_id": ..., }
  # main.py: academic router only in the academic process
  from routers import optimization, utils, strategies, readiness
  if os.getenv("UNIRIDE_ACADEMIC_PROCESS") == "1":  # never set in production
      from routers import benchmark; app.include_router(benchmark.router)
  ```
  Store only gateway-validated, per-run TSP/ATSP rows; filter every reader by protocol and validation; introduce ResultStore v2 (MT4).
- **Acceptance:**
  - Production `main.py` imports nothing from `academic_benchmark` (boundary test).
  - Every persisted row carries protocol, budget, consumed evaluations, `seed_group`, validation status, backend and canonical ID.
  - Readers reject rows without these fields.

### H9 — One algorithm ID maps to several implementations

- **Status:** `CONFIRMED` (demo).
- **Sources:** ACAD-03, P4-04, P1B-07.
- **Locations:**
  - `uniride_core/algorithms/engine_factory.py:28-34, 94-120, 133`;
  - `academic_benchmark/core/registry_setup.py:453, 595, 597-606, 791-838`;
  - `academic_benchmark/core/algorithm_resolution.py:53-55`;
  - `academic_benchmark/engine_core.py:183` (`cls._registry[name] = func` overwrites silently);
  - `academic_benchmark/cli_engine.py:617`;
  - `uniride_core/algorithms/tsp_meta_engines.py:334, 399-406`.
  - Persisted through `optimizer_api/routers/benchmark.py:390-406` (web `academic_matrix` mode, reachable from `src/lib/benchmark-backend-request.ts:59`), `academic_benchmark/run_matrix_benchmark.py:102-103, 119-120` and `run_smoke_benchmark.py:82-83`.
- **Evidence:**

  | ID | Matrix surface (`engine_factory`) | Academic registry / resolver |
  |---|---|---|
  | `Core-GWO-TSP` | `tsp_meta_engines.solve_gwo_tsp`: population 30, 100 iterations, a final `apply_local_search` | `GWOOptimizer` memetic_2opt: pack 50, 250 iterations, periodic 2-opt (resolver: deprecated alias of `Core-GWO-TSP-Memetic-2opt`) |
  | `Core-HHO-TSP` | `tsp_meta_engines.solve_hho_tsp` | `HHOOptimizer` memetic_2opt |
  | `Core-TwoOpt-TSP` | 10-start `solve_two_opt_tsp` | single-start budgeted 2-opt |

- **Mechanism:**
  - Both surfaces write the same `algorithm` string into `benchmark_results`.
  - The matrix path has no accounting and no validation, and its seed is `settings.seed + run − 1`, the same for every problem.
  - `engine_factory` rejects the canonical GWO/HHO IDs with a `KeyError`.
  - `registry_setup.py:453` registers `Numba-GWO/HHO` from `numba_metaheuristics`. `:828-833` overwrites them with `tsp_matrix_metaheuristics`, but only if that import succeeds; otherwise it logs a warning and silently keeps the old executors.
- **Fix sketch:**
  ```python
  # engine_factory.py, before
  CORE_TSP_SOLVERS = {"Core-TwoOpt-TSP": solve_two_opt_tsp, "Core-GWO-TSP": solve_gwo_tsp, ...}
  # after: legacy matrix engines get truthful names; Core-* IDs resolve only via the catalog + gateway
  MATRIX_TSP_SOLVERS = {"Matrix-TwoOpt-TSP-legacy": solve_two_opt_tsp,
                        "Matrix-GWO-TSP-legacy": solve_gwo_tsp, ...}
  # engine_core.register: raise on duplicate names; registry_setup: fail closed on import errors
  ```
- **Acceptance:** every canonical ID resolves to exactly one callable in every entry point (a parametrized test across CLI, registry, `engine_factory` and the web matrix mode), and duplicate registration raises.

### H10 — The forbidden Numba 3-opt kernel runs in every SOTA final polish

- **Status:** `CONFIRMED`.
- **Source:** P1B-03.
- **Contract:** `CANONICAL_THREE_OPT_DESIGN.md` ("old Numba kernels … unreachable from public execution").
- **Locations:**
  - `uniride_core/algorithms/sota_tsp/ls_engine.py:142-150, 209` → `uniride_core/algorithms/numba_accel.py:199-276`;
  - callers: `e2bso_tsp.py:326-331`, `r2dma_tsp.py:439`, `paoea_tsp.py:299`;
  - production reach: `optimizer_api/strategies/ebso_strategy.py:93-100` → `uniride_core/adapters/sota_tsp_strategy_adapter.py:62-64`;
  - academic reach: the `SOTA-*` executors (`registry_setup.py:459-583`).
- **Mechanism:**
  - The kernel only generates `A+B(±rev)+C(±rev)+D(±rev)` (flag arrays at `numba_accel.py:216-218`) and never exchanges segments.
  - It reverses segments on asymmetric matrices and admits adjacent cuts (`k in range(j + 1, …)`).
  - Tail reversal changes the D→A arc, so some moves change four arcs.
  - A spy wrapper confirmed it is called in every E2BSO run.
- **Fix sketch:**
  ```python
  # before
  improved_np, length = _nb._three_opt_improve_atsp_numba(route_np, dm_np, max_iterations, False, window)
  return _nb._extract_route(improved_np, tour), float(length)
  # after
  res = improve_three_opt(tour, dm, max_iterations=max_iterations, window=window)
  return res.route, float(res.cost)
  ```
  Land this together with the canonical 3-opt speed-up (M25), otherwise SOTA runtimes grow.
- **Acceptance:** a spy test shows that no `numba_accel` 3-opt symbol is reachable from public entry points, and the `CANONICAL_THREE_OPT_DESIGN.md` regression command passes.

### H11 — The SOTA TSP solvers stop on wall-clock time: same seed, different result

- **Status:** `CONFIRMED` (demo).
- **Source:** P1B-02.
- **Locations:**
  - `uniride_core/algorithms/sota_tsp/ls_engine.py:213-217`: a `time.monotonic()` check between layers, with `ls_time_limit=0.5`;
  - `e2bso_tsp.py:321-331, 540-548`: a global `time_limit`, and `final_ls_budget = min(ls_time_limit, remaining)`;
  - the same pattern in `r2dma_tsp.py:439`, `paoea_tsp.py:299`, `cgo_tsp.py:295` and `run_tsp.py:423`.
- **Mechanism:**
  - Whether each local-search layer runs depends on JIT warm-up and CPU contention.
  - `/compare` runs two solvers at once in a ThreadPoolExecutor (`routers/optimization.py:516`), so contention is the normal case.
- **Evidence:** `E2BSO_TSP` (population 24, 60 iterations, seed 42), run three times in one process on one fixed 60-node ATSP matrix, cost 288, 280 and 280. Its 3-opt layer executed 1, 1 and 2 times.
- **Fix sketch:**
  ```python
  # before
  if time.monotonic() - t0 > time_limit:
      break
  # after: terminate on iteration/evaluation counts; wall-clock is an optional, reported safety deadline
  if deadline is not None and time.monotonic() > deadline:   # default None
      stats["termination_reason"] = "wall_clock_deadline"
      break
  ```
- **Acceptance:** the same seed gives an identical route and cost across 5 runs under induced CPU load.

### H12 — Clustering uses the unseeded global `random`

- **Status:** `CONFIRMED` (demo).
- **Source:** P1B-04.
- **Locations:**
  - `uniride_core/algorithms/clustering_strategies/kmeans.py:11, 23`, `k_medoids.py:16`, `fuzzy_cmeans.py:11`;
  - `optimizer_api/models/schemas.py:229` (free-string `clustering_algorithm`, with no policy check);
  - `uniride_core/algorithms/vehicle_assignment.py:70`, used by the ga, pso, gwo, hho, two_opt and permutation strategies;
  - `optimizer_api/strategies/seed_utils.py:21`.
- **Mechanism:**
  - The strategies seed only their private `random.Random(seed)`; clustering calls `random.randint` and `random.random` on the global state.
  - That state is shared across `/compare` threads and reseeded globally by academic code (`registry_setup.py:407`, `cli_engine.py:605`).
- **Evidence:** 40 points, 8 vehicles, 6 identical calls produced 6 distinct k-means partitions, 6 k-medoids, 5 fuzzy-c-means, and 1 sweep (deterministic).
- **Fix sketch:**
  ```python
  # before
  def initialize_centroids_kmeans_plus_plus(points, k):
      first_idx = random.randint(0, len(points) - 1)
  # after
  def initialize_centroids_kmeans_plus_plus(points, k, rng: random.Random):
      first_idx = rng.randint(0, len(points) - 1)
  ```
  Pass the strategy's `rng` through `get_clustering_strategy`, validate `clustering_algorithm` against an allowlist, and replace global reseeding in the academic code with local `random.Random(seed)`.
- **Acceptance:** an identical request and seed produce an identical partition and routes, including under concurrent `/compare`.

### H13 — Governed CLI and Smart runs always fail post-run validation, and their seeds break the contract

- **Status:** `CONFIRMED` (demo). This fails closed, so no invalid evidence is produced; but only the two pilots can produce governed evidence.
- **Source:** ACAD-04.
- **Locations:**
  - `academic_benchmark/core/execution_gateway.py:217-219`;
  - `academic_benchmark/smart_benchmark.py:437-451, 646-668, 755-759`;
  - `academic_benchmark/cli_engine.py:814, 955-970`;
  - `academic_benchmark/core/registry_setup.py:348-366, 469-487, 646-681`;
  - `academic_benchmark/core/algorithm_errors.py:88`.
- **Mechanism:**
  - The gateway authorizes a protocol and budget, then calls `executor(problem, params, seed, run_idx)` **without** a manifest. Manifests are injected only by `fair_pilot.py:518/543` and `native_pilot.py:485/519`.
  - Without one, executors return legacy results. The gateway raises `ResultContractViolation` ("result algorithm_id must be the canonical algorithm_id selected by preflight"). That class subclasses `AlgorithmSelectionError`, so Smart aborts the whole batch.
  - Seeds are `42 + run_idx` (Smart) and `1000 + combo_idx*100 + run_idx` (CLI). They include the parameter-combination index and exclude the problem identity.
- **Evidence:** Core-TwoOpt-TSP, ALNS-TSP and Core-GWO-TSP-Pure all raised `ResultContractViolation` in the demo.
- **Fix sketch:**
  ```python
  # before
  result = registry_getter(decision.executor_registry_id)(problem, params, seed, run_idx)
  # after
  params = dict(params)
  if decision.protocol is ExecutionProtocol.FIXED_BUDGET:
      params.setdefault("fair_comparison", {"protocol_version": "uniride-fair-tsp-v2",
          "comparison_regime": "fixed_evaluation_budget", "base_seed": base_seed,
          "budget_policy": "atomic_upper_bound_v1",
          "evaluation_budget": decision.evaluation_budget})
  else:
      params.setdefault("native_comparison", {"base_seed": base_seed})
  result = registry_getter(decision.executor_registry_id)(problem, params, seed, run_idx)
  ```
  Derive seeds with the contract digest (`fairness.py:219-231`).
- **Acceptance:** a governed CLI run and a governed Smart run each produce validated results with contract seeds, shared across algorithms within a (problem, replicate) group.

### H14 — Benchmark polling can stick, race and orphan runs

- **Status:** code paths `CONFIRMED`; timing triggers `PLAUSIBLE` under backend load.
- **Source:** P3-03.
- **Locations:**
  - `src/app/(app)/admin/benchmark/page.tsx:89, 267-301, 304-336, 358-366`;
  - `src/app/page.tsx:578-631, 673-703, 816-825`;
  - `src/services/benchmark-service.ts:328-346`;
  - `src/lib/benchmark-owner-cookie.ts:4`;
  - `optimizer_api/routers/benchmark.py:43-50`; `optimizer_api/benchmark_state.py:94`.
- **Mechanisms:**
  - **(a) Overlapping requests.** `setInterval(async …)` fires every 2000 ms while each request can take up to 10 s, with no in-flight guard or response ordering. A late "running" response can overwrite "completed" after the interval is cleared, leaving the badge stuck. Two ticks can both see "completed", giving a double `fetchResults` and duplicate toasts.
  - **(b) Silent infinite polling.** Every non-OK response is swallowed (`catch { /* continue */ }`). That includes 403 once the 7200 s owner cookie expires on runs longer than 2 hours, and 404 after an optimizer restart (the run registry is in memory). The page then polls every 2 s forever with a stale "running"; Stop and Results also return 403.
  - **(c) Orphaned runs.** `runId` exists only in component state, so leaving the page orphans the run. If the start POST hits its 30 s client timeout, the `Set-Cookie` is lost while the backend run continues.
  - **(d) Landing-page demo flip.** One slow health check (15 s interval, 5 s timeout) flips `isApiOnline`. The effect at `:598-631` then resets selections and turns on `isDemoMode`. Stop takes the demo branch (`:820-825`), marking the run stopped locally without calling the backend, while the real interval flips the status back.
  - **(e) Mislabelled export.** The admin page never clears the previous `results` when a run starts, so Export names the file with the new `runId` but writes the old results.
- **Fix sketch:**
  ```ts
  const ac = new AbortController(); abortRef.current?.abort(); abortRef.current = ac;
  let failures = 0;
  const tick = async () => {
    try {
      const s = await pollStatus(rid, ac.signal); if (ac.signal.aborted) return;
      failures = 0; setRunStatus(s);
      if (TERMINAL.has(s.status)) return void onTerminal(rid, s);
    } catch (e) {
      if (ac.signal.aborted) return;
      if (++failures >= 5 || isHttpStatus(e, 403, 404)) return setPollError(e);
    }
    timerRef.current = setTimeout(tick, Math.min(POLL_INTERVAL_MS * 2 ** failures, 30_000));
  };
  void tick();
  ```
  Also: keep `runId` in the URL, abort on unmount, refresh the owner cookie on each status call, and clear `results` when a run starts.
- **Acceptance:** fake-timer tests cover out-of-order responses, 403/404 terminal handling, unmount cleanup and backoff.

### H15 — Vehicle planning lists every wheelchair (Sw) student as seated (So)

- **Status:** `CONFIRMED`.
- **Source:** P3-04.
- **Locations:**
  - `src/app/(app)/admin/vehicle-planning/page.tsx:64-67, 100, 183-184`;
  - `src/app/api/admin/users/route.ts:46-55`;
  - the fixture `src/app/(app)/admin/vehicle-planning/page.test.tsx:70`.
- **Mechanism:**
  - The API returns raw snake_case rows (`disability_type`, from `select("*")`), but the page filters on `s.disabilityType === "Sw"`.
  - The Sw list is therefore always empty and every student appears under So; "Select all Sw" does nothing and the Sw counts show 0.
  - The sandbox page (`sandbox/page.tsx:223, 379-384`) and `calculate-vehicles` (`:198-199`) read both forms, so optimizer input is correct.
  - The camelCase test fixture hides the bug.
- **Fix sketch:**
  ```ts
  // before
  const studentUsers = usersArray.filter((u: User) => u.role === "student");
  // after
  type Row = User & { disability_type?: "Sw" | "So" | null; location_code?: string | null };
  const studentUsers = (usersArray as Row[]).filter((u) => u.role === "student")
    .map((u) => ({ ...u, disabilityType: u.disabilityType ?? u.disability_type ?? undefined,
                   locationCode: u.locationCode ?? u.location_code ?? undefined }));
  ```
  Change the fixture to snake_case. Better: define one typed DTO mapper in `src/lib` used by every admin page.
- **Acceptance:** a test with snake_case fixtures shows the correct Sw/So split.

### H16 — Academic CVRPTW (Solomon) is validated with school-pickup rules

- **Status:** `CONFIRMED` (demo). Severity depends on whether CVRPTW results are used as scientific evidence (Appendix G, Q3).
- **Source:** P1A-05.
- **Locations:**
  - `uniride_core/models.py:30, 137`; `uniride_core/adapters/matrix_builder.py:332-338`;
  - `uniride_core/algorithms/split_decoder.py:147-179, 277-296`; `holistic_matrix_engine.py:254-285`; `feasibility_certificate.py:206-229`;
  - `academic_benchmark/dashboard_utils.py:107-111`.
- **Mechanism:**
  - `from_solomon_text` sets no direction, so it defaults to `"pickup"`.
  - The split path runs the capacity-only split, then counts window violations with `latest - int(cost) - offset`, never checking the depot due time.
  - The holistic engines simulate forward from the depot ready time and do check the depot due time.
  - The dashboards treat "violation count == 0" as feasible.
- **Failure scenario:** depot window (0, 45); customers with window (0, 50) and service time 10. Route [1, 2] cannot return before 54.14. The split path reports 0 violations and the certificate says feasible, while the holistic counter returns 1.
- **Fix sketch:** add a separate forward time-window validator (depot window, service time, waiting), used by the decoders and by `certify_*`, and set the direction explicitly at parse time:
  ```python
  # matrix_builder.py:332  before: ConstraintProfile(..., depot_index=0)
  ConstraintProfile(..., depot_index=0, direction="forward_tw")
  ```
- **Acceptance:** the scenario is infeasible on every path, and a Solomon smoke test agrees with the holistic counter.

### H17 — Production algorithm parameters can come from academic results

- **Status:** coupling `CONFIRMED`; impact `PLAUSIBLE`/`LATENT` (the parameter file does not exist today).
- **Source:** P4-02.
- **Locations:**
  - `optimizer_api/strategies/promoted_config_loader.py:9-13, 31-36`;
  - `ga_strategy.py:51-53`, `gwo_strategy.py:61-63`, `two_opt_strategy.py:56-58`, and also pso, hho, aoea, ebso and rdma;
  - `optimizer_api/strategies/__init__.py:79-98`;
  - `academic_benchmark/promoted_configs.py:33, 116-133, 166-172`;
  - `optimizer_api/tests/test_production_registry_snapshot.py:34-51`.
- **Mechanism:**
  - Building the registry reads `benchmark_db/promoted_configs.json` (or `UNIRIDE_PROMOTED_CONFIG_PATH`).
  - That file is built from `best_solutions` rows (hard-coded as TSP/distance) and from `benchmark_results` rows, including web runs whose parameters come from `metadata.algorithm_params`. One supporting row is enough.
  - Production cannot start without `academic_benchmark` installed.
  - The snapshot test checks only that capabilities are not loaded; it does not check for `academic_benchmark`.
- **Fix sketch:**
  ```python
  # before
  from academic_benchmark.promoted_configs import (DEFAULT_PROMOTED_CONFIG_PATH, ...)
  # after: production-owned, reviewed file; only travel-time evidence accepted
  PRODUCTION_PARAMS_PATH = os.path.join(os.path.dirname(__file__), "production_params.json")
  def get_promoted_params(algorithms, *, problem_type, matrix_kind, path=None):
      if matrix_kind != "travel_time":
          return {}
  ```
- **Acceptance:** `import optimizer_api.main` loads no `academic_benchmark.*` module (boundary test).

### H18 — `/optimize` silently ignores a caller-supplied `distance_matrix`

- **Status:** `CONFIRMED`.
- **Source:** P4-05.
- **Locations:** `optimizer_api/models/schemas.py:232-288` (`:246` `distance_matrix = data.get("distance_matrix") or {}`; `:249` `loc: {"lat": float(idx), "lng": 0.0}`; `:287` uses it only for `is_asymmetric`); `optimizer_api/routers/optimization.py:183-184`.
- **Mechanism:** costs come from Supabase (codes match), an error (no match), or Euclidean distance between fabricated `(idx, 0)` points (Supabase unavailable). The caller is never told.
- **Fix sketch:**
  ```python
  if "distance_matrix" in data or "time_matrix" in data:
      raise ValueError("explicit matrices are not accepted by production endpoints")
  ```
- **Acceptance:** a request containing `distance_matrix` receives 422.

### H19 — The TSPLIB quick-runner optimizes one objective and reports another

- **Status:** `CONFIRMED` (code reading; not executed).
- **Source:** P4-03.
- **Locations:**
  - `optimizer_api/routers/benchmark.py:276-317`;
  - `optimizer_api/benchmark_runner.py:154-226` (TSPLIB x/y used as lat/lng, `:172`) and `:369-401` (`tour_length = self._compute_tsplib_tour_distance(...)` at `:381`);
  - `optimizer_api/utils/matrix_repository.py:297-305`;
  - `optimizer_api/models/schemas.py:60-61`.
- **Mechanism:**
  - The default mode feeds TSPLIB coordinates into production strategies, whose costs come from the shared DataLoader.
  - With Supabase loaded, the `loc_i` IDs raise `IncompleteTravelMatrixError`. Without Supabase, the cluster-first strategies optimize Euclidean distance and the split strategies get zeros.
  - The tour is then rescored with the TSPLIB metric (EUC_2D, GEO or ATT), so the reported gap measures a different objective from the one optimized.
  - GEO instances pass the lat/lng validators; most other instances fail validation and produce NaN rows.
- **Fix sketch:**
  ```python
  if settings.get("execution_mode") not in {"matrix_native", "academic_matrix"}:
      raise HTTPException(410, "TSPLIB runs cannot use production travel-time strategies")
  return _start_matrix_native_benchmark_impl(run_id, algorithms, problems, settings)
  ```
- **Acceptance:** the quick runner is retired or relocated to the lab service (MT4).

### H20 — CI never runs the full canonical suites or a production build *(corrected in v1.1)*

- **Status:** `VERIFIED-LEAD`.
- **Location:** `.github/workflows/ci.yml:45-60`; `.github/workflows/benchmark.yml:3-48`.
- **Mechanism (corrected in v1.1):**
  - On pushes to `WIP`, `ci.yml` only *collects* the three canonical suites, then executes 8 focused files.
  - Pull requests also run `benchmark.yml` (SOTA solver smoke tests, ATSP integration, the regression gate and SOTA E2E). It does not run on pushes to `WIP`: its push trigger is `main`/`master` only.
  - Neither workflow executes the full ~3,400-test canonical suites, and CI has no `npm run build` and no dependency audit.
- **Fix sketch:**
  ```yaml
        - name: Run canonical Python suites
          env:
            PYTHON_DOTENV_DISABLED: "1"
            SUPABASE_URL: ""
            SUPABASE_SERVICE_ROLE_KEY: ""
          run: python -B -m pytest uniride_core/tests optimizer_api/tests academic_benchmark/tests -q -p no:cacheprovider --tb=short
  # frontend job
        - name: Production build
          run: npm run build
        - name: Dependency audit (report-only until triaged)
          run: npm audit --omit=dev || true
  ```
  Shard the Python suite with `pytest-xdist` if runtime is a concern; the full run is about 10 minutes locally.
- **Acceptance:** CI fails on any failure in the canonical suites and on any build failure.

### M26 — The production SOTA strategies optimize a different objective and can silently run greedy instead *(re-rated Medium → High in v1.1)*

- **Status:** `VERIFIED-LEAD` (v1.1, source read). Re-rated at Codex's recommendation.
- **Locations:** `uniride_core/adapters/sota_tsp_strategy_adapter.py:12-23` (`build_solver_matrix`) and `:45-67` (`solve_student_order_with_sota_tsp`); production callers via `optimizer_api/strategies/ebso_strategy.py:93-100` (e2bso, rdma and paoea, per P1b).
- **Mechanism:**
  - The solver matrix covers students only, with the depot excluded, and is built from `distance_lookup` scaled to integers (`max(1, int(distance * 1000))`). Responses, however, report depot-anchored *duration*.
  - Any exception inside the SOTA solver is swallowed and replaced by `greedy_student_order` (`:66-67`), and nothing in the response says so.
- **Impact:** a caller who requests `e2bso`, `rdma` or `paoea` can receive a greedy route labelled as that algorithm, and the SOTA search optimizes a different objective from the one reported and certified. This is an algorithm-identity truthfulness defect on a production surface.
- **Fix sketch:** build the solver matrix from the depot-anchored duration matrix (include the depot as the fixed tour start). On solver failure, either fail the request or set an explicit fallback marker (for example `algorithm_used="greedy_fallback"`) that the certificate and the UI surface.
- **Acceptance:** a test that forces the SOTA solver to raise gets a failed or explicitly labelled fallback response, and a parity test shows that the optimized objective equals the reported duration.

---

## 5. Medium findings

| ID | Finding | Locations | Status | Fix guidance |
|---|---|---|---|---|
| M1 (P1A-06) | **Solvers ignore the heterogeneous fleet** (`request.vehicles`); no strategy reads it. Only the certifier enforces it, disabling the global caps when a fleet is given. Any fleet tighter than `sw/so_capacity`, or with fewer vehicles than the solver's route count, gives `success=False`. | `optimizer_api/strategies/*` (0 reads); `optimizer_api/verification/response_certifier.py:136-193` | CONFIRMED | Pass vehicle-indexed capacities to the solvers, or add a route-to-vehicle assignment stage before certification (MT1). |
| M2 (P1A-07) | **Pickup windows can be built from `dropoff_time`.** In a PICKUP request, a student with only `dropoff_time` gets `(dropoff−30, dropoff)` as a morning pickup window. | `optimizer_api/models/schemas.py:350-357` | CONFIRMED | No fallback across directions; require `pickup_time`, or derive from `target_time`. |
| M3 (P1A-08) | **"km" is actually lat/lng degrees** (roughly 1/111 of the real value; the ratio varies with latitude and axis). The same degree matrix is used as minutes in the fallback. | `optimizer_api/strategies/ga_strategy.py:158`; `sota_response_builder.py:46-57`; `matrix_repository.py:492-509` | CONFIRMED | Use haversine km or drop the field; never use degrees as minutes (C2). |
| M4 (P2-06) | **Stale matrix served indefinitely** after a failed refresh: no maximum age, and the backoff (equal to the TTL) repeats. Responses carry no provenance. The `.select()` has no `.range()` and no row-count check, so a PostgREST max-rows limit (1,000 by default when hosted) truncates matrices above about 32 locations. Truncation fails closed via `IncompleteTravelMatrixError`. | `optimizer_api/utils/matrix_repository.py:81-87, 165-171, 186-191`; `optimizer_api/models/schemas.py:428-442` | CONFIRMED (stale / provenance); PLAUSIBLE (truncation; confirm max_rows and location count) | Maximum staleness, then fail closed; provenance fields in responses; paginated fetch with an expected row count (MT2). |
| M5 (P2-07) | **The benchmark router leaks internal errors** to clients: error text, exception messages in run status, and absolute server paths. | `optimizer_api/routers/benchmark.py:154, 174, 192, 214` (`detail=f"... {exc}"`), `:653`, `:314, 434`, `:554, 560` | CONFIRMED | Return fixed messages and log details server-side. |
| M6 (P3-05) | **Synthetic data shown without enough provenance** *(narrowed in v1.1: the landing page does show demo badges, `src/app/page.tsx:1156-1160, 1902-1903`)*. The IEDashboard "tracks" tab always draws hard-coded blocks (pickups 8–11, drop-offs 14–17, 2 Sw / 3 So) with no demo label. The sandbox `transformIEData` zeroes several metrics. Landing-page demo mode invents gap and time values from hard-coded per-algorithm ranges that already encode a ranking, saves them to run history with only a `demo_` prefix, and switches on automatically when a health check fails. | `src/components/admin/ie-dashboard.tsx:72-107, 376-379`; `src/app/api/sandbox/route.ts:104-120`; `src/app/page.tsx:309-350, 745, 775` | CONFIRMED | Remove it or label it prominently, never persist demo data to history, and never auto-enable demo mode. |
| M7 (P3-06) | **Drivers page shows stale data, hidden by a lint suppression.** The suppression says "fetch-on-mount", but the effect re-runs on `[selectedDate]`. If dates are switched quickly, an older response overwrites the newer one, so the table shows date A while the picker shows B, and exports are labelled with the wrong date (`driver-export.ts:103`). The page also reads users through the browser anon client; repo RLS has only `users_select_own`, so drivers appear unassigned unless live RLS differs. | `src/app/(app)/admin/drivers/page.tsx:30-57` | CONFIRMED (race); PLAUSIBLE (RLS effect) | Ignore stale responses or use an AbortController; fetch via the admin BFF. |
| M8 (P3-07) | **Possible stored XSS in the driver PDF export, under a loose CSP.** The export writes `s.name`, `studentNumber`, and driver and vehicle names unescaped into an `about:blank` popup via `document.write`. The CSP allows `script-src 'self' 'unsafe-inline' 'unsafe-eval'` in **all** environments, `connect-src` includes localhost, there is no HSTS, and the session lives in localStorage. Students can set their own name. | `src/services/excel/driver-export.ts:123-128, 252-254, 285`; `next.config.ts:36, 40`; `src/lib/supabase.ts:130-133` | PLAUSIBLE (exploitation needs the list to include other users) | HTML-escape every interpolated value; nonce-based CSP in production; drop `unsafe-eval` and the localhost entries; add HSTS. |
| M9 (P3-08) | **The dev-reset secret is optional, and the UI never sends it.** `next dev` binds `0.0.0.0`, so with `ENABLE_DEV_RESET=true` anyone on the LAN could reset any account's password in whichever Supabase project `.env.local` points to. Production builds fail closed. | `src/app/api/auth/dev-reset/route.ts:23-28`; `src/app/(auth)/forgot-password/page.tsx:89-95` | PLAUSIBLE (configuration-dependent) | Always require the secret and refuse non-loopback requests. |
| M10 (P3-09) | **Password change with only a bearer token**, without re-authentication, so a stolen token means permanent takeover. Auth failures come back as HTTP 500. | `src/app/api/profile/password/route.ts:34-37, 55-56` | CONFIRMED | Require the current password or a recent re-login; map auth errors to 401/403. |
| M11 (P3-10) | **Severity (v1.1): Low** (re-rated). **Production and tests run different React builds.** Next 16.1.6 accepts React 18.2+ or 19 as peers, and the App Router runs Next's bundled `19.3.0-canary-f93b9fd4-20251217` by design. `node_modules/react` 18.3.1 serves Vitest, Testing Library and `@types/react` 18.3.18, so component tests and type-checking do not exercise the production React build. | `package.json`; `node_modules/next/package.json` (peerDependencies); `node_modules/next/dist/compiled/react/cjs/react.production.js:557`; `vite.config.ts:10-13` | CONFIRMED (expected framework behavior) | Treat only a concrete runtime incompatibility as a defect, and cover the production React with E2E tests against `next build`. An upgrade alone does not give exact parity. |
| M12 (P3-11) | **`xlsx` 0.18.5 parses admin uploads.** Known issues: CVE-2023-30533 (prototype pollution, fixed in 0.19.3) and CVE-2024-22363 (ReDoS, fixed in 0.20.2). The npm release line is unmaintained. | `package.json:73`; `src/services/excel/import.ts:6, 138` | CONFIRMED (version); exploitation needs a crafted file | Use the SheetJS CDN build ≥ 0.20.2 or exceljs; add file size and type limits. |
| M13 (P3-13) | **Async `onAuthStateChange` callback** that awaits a database query. auth-js deprecates async callbacks because they can deadlock, and the callbacks are not sequenced, so a slow lookup can finish after SIGNED_OUT and put the user back. | `src/lib/supabase-auth.ts:236-257` | PLAUSIBLE (confirm with a multi-tab or token-refresh test) | Keep the callback synchronous and defer DB work; sequence by event. |
| M14 (P1B-05) | **The production default uses a second, non-canonical 3-opt.** The "hybrid" local search is the default in `ga_split` (the API default algorithm), the gwo/hho/pso split strategies and `hho_strategy`. Its cases are B'C', B'C, BC (identity), CB, C'B and CB': 6 distinct non-identity moves, with C'B' missing. `A = route[:i+1]`, so the depot→first-stop arc is never cut. Tours stay valid (full costing), but the search is weaker and drifts from the contract. | `uniride_core/algorithms/local_search.py:168-206, 726-732, 800`; `ga_split_strategy.py:67`; `hho_strategy.py:59` | CONFIRMED | Run `improve_three_opt` on `[depot] + route` (directed mode auto-detected), rotate back, and delete `_three_opt_cases` (MT6). |
| M15 (P4-06) | **No `production_ready` gate.** The flag exists only in the academic catalog, where it is forced to False. API exposure is a hard-coded dict, and the snapshot test freezes the key list only. | `optimizer_api/strategies/__init__.py:120-214` (academic SOTA strategies at `:186-196`); `canonical.py:60-81`; `capabilities.py:77, 110-111`; `test_production_registry_snapshot.py:17-31` | CONFIRMED | Add a domain-aware production strategy table (CVRP/CVRPTW/UniRide) with `production_ready`, grandfathering the current API inventory as the unification design requires; check it in `resolve_strategy`; snapshot (key, canonical ID, ready). *(v1.1: do not derive it by filtering the permutation-TSP academic catalog.)* |
| M16 (P4-08) | **`uniride_core` is not neutral.** It owns a TSPLIB registry in repo-root `tsplib_data` (created on first read), an HTTP downloader, the best-known-solution table and the gap logic, all imported eagerly. Three TSPLIB stores are looked up by name only. `CostMatrix.kind` exists but nothing enforces it. The production adapter labels any explicit matrix as travel time and otherwise applies EUC_2D integer rounding to degrees (no production caller yet). | `uniride_core/algorithms/tsplib_parser.py:35-60, 277-280, 366-392`; `uniride_core/benchmark_runner.py:120-157`; `uniride_core/__init__.py:17`; `uniride_core/models.py:10-27, 94, 187`; `uniride_core/adapters/uniride_adapter.py:100-111` | CONFIRMED | Move these to `academic_benchmark`; make the metric domain a required enum checked when an engine starts (MT2, MT4). |
| M17 (P4-09) | **The archive quarantine has hardening gaps** *(corrected in v1.1)*. The YAEM-specific test does reject static imports of `archive.academic_benchmark.yaem2026_legacy` (`test_yaem_quarantine_boundary.py:39-50`), so a working quarantine exists for static imports. Residual gaps: `archive/` has no `__init__.py`, so it is importable as a namespace package; the generic test's markers (`uniride_core/tests/test_archive_boundaries.py:8-13`) do not include `archive.`; and the scans cover static imports in active packages only, missing importlib strings and root, `src` and `scripts` files. | `archive/`; `uniride_core/tests/test_archive_boundaries.py:7-13`; `academic_benchmark/tests/test_yaem_quarantine_boundary.py:39-50, 176-188` | CONFIRMED | Add an `archive/__init__.py` that raises `ImportError`, add `archive.` to the generic markers, and widen the scans to dynamic imports and root files. This is hardening, not a Gate A failure (MT5). |
| M18 (ACAD-05) | **The GWO/HHO executor rounds cost to 2 decimals**, while the gateway uses tolerance 1e-9. Fair runs on fractional ATSP matrices are rejected ("reported tour_cost does not equal the independently recomputed directed closed-cycle cost"); 2-opt, 3-opt and ALNS pass. Any fair pilot on UniRide travel times aborts at the first GWO run. | `academic_benchmark/core/registry_setup.py:710, 715`; `execution_gateway.py:97-111`; `fair_pilot.py:343` | CONFIRMED | Report the unrounded `float(cost)`. |
| M19 (ACAD-06) | **The `memetic_2opt` label is set from a boolean**, not from the polish that ran. `studies/bildiri2026/study.json` sets `polish_iters: 0, final_polish_iters: 0`; *(v1.1)* it is an explicit draft/smoke profile (`study.json:5`), and no contaminated published result is established. In the demo, Memetic-2opt with zero polish was identical to Pure (cost 422.0, 54 evaluations) but labelled memetic, with every polish phase true. The polish schedule is not recorded, although the design requires it. | `academic_benchmark/core/registry_setup.py:767-780`; `tsp_matrix_metaheuristics/gwo_solver.py:116-127, 261-285` (same in `hho_solver.py`) | CONFIRMED | Record the schedule, reject memetic configurations with zero polish, and derive the flags from the executed polish. |
| M20 (ACAD-07) | **Severity (v1.1): Low (informational).** **Many counted evaluations are repeats.** Share of counted evaluations that re-evaluate an already-seen tour (n=30, budget 5,000): GWO 34–62%, HHO 47–50%, ALNS 55–58%, 3-opt 34%, 2-opt 0.3%. Truthful under the contract, but the budget measures calls, not distinct search effort. | `hho_solver.py:154-170, 302`; `gwo_solver.py:229-233`; `fairness.py:388-395`; `sota_tsp/alns_tsp.py:241` | CONFIRMED (measured by the investigator; not re-measured by Codex) | Record distinct-candidate telemetry and discuss it as a threat to validity. Counting repeats complies with the approved budget definition; memoization would change the comparison protocol and requires an approved protocol change (LT1). |
| M21 (lead) | **RLS hygiene.** The `SECURITY DEFINER` functions `is_admin()` and `prevent_role_change()` have no `SET search_path`. `rls_policies.sql:17-24` drops **every** public policy, including migration-owned ones (`route_plans`, `sandbox_scenarios`, `time_matrix`), and does not recreate them, so running it after the migrations breaks access (fail-closed). Policy has three sources of truth: `schema.sql`, `rls_policies.sql` and the migrations. | `supabase/rls_policies.sql:17-36, 59-75`; `supabase/migrations/20260329_add_route_plans.sql:46, 52`; `20260329_add_sandbox_scenarios.sql:30`; `20260305_add_time_matrix.sql:14, 20` | VERIFIED-LEAD | A single migration-owned policy set with `search_path` set; retire the drop-all script (MT8). |
| M22 (P2-08) | **`.env` is loaded after the routers are imported** (`main.py:18` vs `:29`), so settings read at import time ignore it: `UNIRIDE_PROMOTED_CONFIG_PATH` is `lru_cache`d under key None, and `TSPLIB_DATA_DIR` is a module constant. Tests that import `main` read the developer's `optimizer_api/.env` unless `PYTHON_DOTENV_DISABLED` is set, which needs python-dotenv ≥ 1.2 while requirements ask for ≥ 1.0.0. | `optimizer_api/main.py:18, 29`; `strategies/promoted_config_loader.py:31-36`; `strategies/__init__.py:79-98` | CONFIRMED | Load settings before imports (or use a settings object); pin python-dotenv ≥ 1.2. |
| M23 (P2-09, P1A-10) | **Unprotected utility endpoints and an unsafe download.** The `utils` endpoints have no auth and no size limits. `/extract-time-windows` always raises `AttributeError`: it passes a Pydantic model to code that calls `entry.get`. The TSPLIB downloader uses plain `http://` with no integrity check and an unbounded `read()`, reachable via `POST /benchmark/download` with a tenant key. | `optimizer_api/routers/utils.py:11-54` (`:26`); `uniride_core/algorithms/time_window_extractor.py:119`; `uniride_core/algorithms/tsplib_parser.py:39, 323-330` | CONFIRMED | Auth plus size limits; fix the model handling; HTTPS with checksum and size cap, or remove the downloader from production. |
| M24 (P3-12) | **Render hot spots** on the landing and benchmark pages (§7.1). | `src/app/(app)/admin/benchmark/page.tsx:203, 459, 526, 530, 1045, 1282`; `src/app/page.tsx:745, 947, 1016, 1024, 2056` | CONFIRMED (mechanism); impact needs profiling | Profile first (React Profiler on a production build) and apply the §7.1 changes where the profile shows cost; virtualize only if table rendering dominates (v1.1). |
| M25 (P1B-06) | **Canonical 3-opt performance:** duplicate detection dominates (§7.3). | `uniride_core/algorithms/three_opt.py:78-83, 96-101, 151-171`; `local_search_numba.py:778-784` | CONFIRMED (measured) | See §7.3 (MT6), gated by a candidate-parity test. |
| M26 (P1B, cross-lane note) | **Re-rated to High in v1.1; see the M26 entry at the end of §4.** The production SOTA adapter optimizes a student-only, depot-free, distance-scaled matrix while responses report depot-anchored duration, and it silently falls back to greedy on any exception. | `uniride_core/adapters/sota_tsp_strategy_adapter.py:12-23, 61-67` | VERIFIED-LEAD (v1.1) | See §4 and QW11. |

---

## 6. Low findings

| ID | Finding | Locations | Fix |
|---|---|---|---|
| L1 | `@tanstack/react-query` is a dependency but unused: no `QueryClientProvider` or `useQuery` anywhere in `src`. | `package.json` | Adopt it for polling (H14) or remove it. |
| L2 | The landing page calls `/api/ai-advisor`, which does not exist, so the advisor always shows a connection error. | `src/app/page.tsx:555` | Implement the route or remove the UI. |
| L3 | Dead code (each item listed below). | see list | Delete or archive with a manifest (MT6). |
| L4 | `supabase-admin.ts` and `admin-auth.ts` don't `import "server-only"`. | `src/lib/supabase-admin.ts`; `src/lib/admin-auth.ts` | Add the import (defense in depth). |
| L5 | Raw error text reaches clients (each case listed below). | see list | Return generic messages; map auth errors correctly. |
| L6 | `proxy.ts` sets `x-user-id`, which nothing reads, and repeats `getUser`, so every admin call makes two auth round trips. | `src/proxy.ts:38-41` | Remove the header, or pass a verified claim instead of re-verifying. |
| L7 | `admin/layout.tsx` calls `router.replace` during render. | `src/app/(app)/admin/layout.tsx:36` | Move it into an effect. |
| L8 (ACAD-08) | The local-search executor overrides the solver's termination reason (demo: solver `no_improving_move`, result `max_iterations`). | `academic_benchmark/core/registry_setup.py:221-226` | Use `search.termination_reason`. |
| L9 (ACAD-09) | Academic hygiene issues (each listed below). | see list | Fix within the academic gates. |
| L10 (P1B-08) | Latent determinism issues (each listed below). | see list | Fix opportunistically (MT6). |
| L11 (P1A-09) | The core request adapter uses `str(direction)`, which yields `'TripDirection.PICKUP'`, so `direction.lower()=="pickup"` treats it as dropoff. LATENT: only tests call it. | `uniride_core/adapters/uniride_adapter.py:134` | `getattr(d, "value", d)`. |
| L12 (P1A-10) | Latent constraint gaps (each listed below). | see list | MT1. |
| L13 (P4-10) | Boundary hygiene issues (each listed below). | see list | MT4. |
| L14 (P2-08) | The only launcher runs `python main.py`, which starts uvicorn with `reload=True`. | `scripts/start-dudullu-local.mjs:84`; `optimizer_api/main.py:117` | Make `reload` dev-only and use an explicit app path. |
| L15 (P3) | Of the 19 `react-hooks/exhaustive-deps` warnings, 16 are harmless (a missing stable `t`/`tc`/`toast`, or an extra dependency). Driver assignments and history don't cancel requests when the user switches (low). | `driver/assignments` (`:87`); `driver/history` (`:82`) | Cancel on user change. |

**L3 — dead code:**
- `vehicle-planning-page.tsx` is never imported.
- The `run/status` and `run/stop` BFF routes have no client; `run/status` also turns a missing status into `'running'` (`:63`).
- The server-side sandbox-scenario routes are unused (the page uses localStorage) and double-encode JSONB (`sandbox/route.ts:267`).
- In `optimizer_api/utils`, `local_search.py` and `local_search_numba.py` are imported only by tests; the rest are re-export shims.
- `sota_common` (about 2k lines) and its shims. *(v1.1: it has consumers — re-exports, compatibility tests, the `__main__` entry point — that must be redirected or retired deliberately before deletion.)*
- The duplicate k-means in `clustering.py` only. *(v1.1: `Point`, `Cluster`, `calculate_centroid` and the capacity helpers in that module are live.)*
- `local_search_numba._three_opt_improve_numba` / `_cases_numba` (0 callers).
- The request-model field `use_sota_engine` (`optimizer_api/models/schemas.py:222`) is never read. *(v1.1: the core decoder option of the same name is live, `uniride_core/algorithms/cvrptw_decoder.py:25-62`; keep it.)*
- `PenaltyManager` is unused by live solvers.

**L5 — raw error text to clients:**
- 500 messages in `src/lib/admin-auth.ts:165-167`;
- `details: error.toString()` in `src/app/api/benchmark/run/route.ts:150-154`;
- 401/403 reported as 500 in `src/app/api/driver/assignments/route.ts:51-53`.

**L9 — academic hygiene:**
- Global `random.seed` in legacy paths: `registry_setup.py:407`, `cli_engine.py:605`, `benchmark_utils.py:652`.
- `benchmark_utils.make_deterministic_seed` hashes the algorithm name and index (`:666-672`). It is test-only, but would break the seed contract if reused.
- `three_opt.improve_three_opt` doesn't count its initial evaluation (`:208`). Its scale-aware tolerance (`:228-229`) differs from the strict `<` in `fairness.py:396`, so near-ties can diverge.
- Pilot aggregates use `pstdev` (`fair_pilot.py:473`, `native_pilot.py:428`).
- The fair pilot doesn't validate GWO/HHO numeric parameters; a negative `dive_count` makes `consume()` raise mid-generation (fails closed).
- Non-fair GWO/HHO evaluation counts exclude the Numba delta 2-opt polish (`gwo_solver.py:128-137`; latent).

**L10 — latent determinism:**
- `matrix_repository.py:535-538` derives asymmetric-haversine factors from `hash((loc_i, loc_j))`, which is PYTHONHASHSEED-salted per process.
- `:302` sets the asymmetric flag inside `if geo_coords`, so it is always True. No active caller passes `geo_coords=True`.
- `random.Random(None)` is used when no seed is given: `tsp_meta_matrix_engine.py:47`, `fcm_split_engine.py:49/173`, `fuzzy_cmeans_enhanced.py:173`, and the `random_seed=None` defaults in `tsp_matrix_metaheuristics`.
- Dormant `use_random_order` paths: `local_search.py:741`, `local_search_numba.py:1029`.
- The `objective_budget` 2-opt and Or-opt use strict comparisons, while the canonical engine uses a relative tolerance.
- The `local_search_numba` 3-opt wrapper raises on duplicate location codes. Its matrix `f([a,b])−f([a])` (`:145`), costed as a closed cycle, cancels the depot out of the objective. No production caller uses it.

**L12 — latent constraint gaps:**
- Sweep clustering is centred on hard-coded Dudullu coordinates (`sweep.py:24`), and `vehicle_assignment.py:68-75` passes no depot.
- `to_problem_instance` collapses `[sw, so]` to `sw` (`matrix_builder.py:131-136`). `check_capacity_vectors` checks only the smaller number of dimensions (`feasibility_certificate.py:143`), so SO capacity goes unchecked.
- `check_time_windows` skips travel time into stops that have no window (`:239-241`).
- Missing capacities default to total demand (`routing_demand_utils.py:67-68`).
- `is_asymmetric` defaults to False.

**L13 — boundary hygiene:**
- Root scripts import the academic database and monkeypatch production modules (`test_patch.py:26-33`).
- Academic harnesses live in `optimizer_api/tests`.
- One distribution ships all three packages (`pyproject.toml:29`).
- Production requests default to the unused BENCHMARK mode (`schemas.py:20-22, 220`).
- `tsplib_manager.py:17-20` changes `sys.path` inside the production process.
- A core docstring names Bildiri (`numba_accel.py:2`).
- The site root `/` renders `BenchmarkSuitePage`.

---

## 7. Architecture and performance bottlenecks

### 7.1 UI rendering

There is no map to memoize (§2.5). These are the real heavy surfaces.

- **Landing page `/` (`src/app/page.tsx`).**
  - It has 2,739 lines and 32 `useState`.
  - It re-renders entirely on every polling tick (every 2 s, or every 200 ms in demo mode, `:745`), because the run state lives at the top of the page.
  - Charts and tables at `:947, 1016, 1024, 2056` rebuild every tick.
- **`admin/benchmark/page.tsx`.**
  - `getAnalytics` is wrapped in `useCallback`, which caches the **function**, not its result. It is called three times per render (`:459, 526, 530, 1045`), and each call runs `problems.find` over up to 5,000 problems (`:203`).
  - Old results stay in state during a new run, so two aggregations run on every tick.
  - Chart `data` and `config` are rebuilt every render, so Recharts may re-animate (PLAUSIBLE).
  - The raw-results table is not virtualized (`:1282`).
- **What to change:**
  1. Compute analytics once with `useMemo` keyed on `results`.
  2. Move the run and polling panel into its own child component, so a tick re-renders only that panel.
  3. Give charts stable data references (`useMemo`) and wrap them in `React.memo`.
  4. Virtualize the large tables only if profiling shows that table rendering dominates (v1.1: profile first).
  5. Replace the ad-hoc intervals with one polling hook (H14): AbortController, a `setTimeout` chain, backoff, terminal states, and the `runId` kept in the URL. `@tanstack/react-query` is already installed: either use `useQuery` with `refetchInterval` and `enabled: !terminal`, or remove it (L1).
  6. Align React versions (M11), so component tests exercise the React that ships.
- **When GIS work starts** (roadmap Priority 7):
  - define the backend geometry contract first;
  - keep derived layers memoized, handlers stable, and layer data immutable;
  - add a CSP update for the tile and provider hosts.

### 7.2 API latency and capacity

- **The event loop blocks** whenever the readiness endpoints fetch from Supabase (H6).
- **Every in-flight solve holds a worker.** Each uses one AnyIO worker (default pool of 40) shared with `/health`. Threads left behind by `/compare` timeouts and benchmark daemon threads accumulate with no global cap (H7, C4).
- **`/optimize` has no wall-clock limit.** At the policy ceilings (population 250 × 2000 iterations, n = 250), a run can take hours (PLAUSIBLE extrapolation).
- **Matrix layer:**
  - the fetch is unpaginated (M4);
  - two singletons load Supabase twice (H5);
  - `get_submatrix` holds the repository lock during network refreshes.
- **What to change:**
  1. Add a process-wide `BoundedSemaphore`, acquired inside the worker (H7).
  2. Pass a cooperative deadline into strategies.
  3. Wrap sync I/O in `run_in_threadpool` (H6).
  4. Use one import root (H5).
  5. Then a process-isolated solver pool with hard cancellation, and durable jobs (MT3; `ACTIVE_ROADMAP.md` Priorities 2–3).

### 7.3 Algorithmic inefficiencies

- **Canonical 3-opt is dominated by duplicate-detection bookkeeping (M25).** One pass, window 12:

  | n | Symmetric | Directed |
  |---|---|---|
  | 30 | 3.7 s | 0.24 s |
  | 50 | 23.6 s | 2.0 s |
  | 80 | 53 s | 4.3 s |

  - cProfile at n=50: `_symmetric_cycle_key` takes 16.9 s of 25.5 s, and candidate costing about 1.2 s.
  - Every C(n,3) triple is scanned even with a window (`three_opt.py:78-83`).
  - 48 arrangements are tried per triple (`:151-171`).
  - `local_search_numba.py:778-784` passes an ndarray into Python loops.
  - `Numba-3-opt-bounded` allows 400 passes (`numba_strategies.py:6`), which means hours per TSPLIB run.
- **Smallest safe optimization**, preserving the contract:
  - Admitted cuts guarantee at least 2 nodes per segment, so the 7 symmetric reconnections are always distinct (verified for every triple at n = 6..12). Emit them from a fixed (order, reversal) table.
  - Emit the directed `S1+S3+S2` directly.
  - Generate `i`, then `j ∈ [i+2, i+w]`, then `k ∈ [j+2, j+w]` directly; this preserves the current lexicographic order.
  - Pass lists of lists, not an ndarray.
  - Keep the existing sort key and full closed-cycle costing.
  - Gate the change with a candidate-parity test against the current generator.
- **Repeated evaluations (M20):** 34–62% of counted GWO evaluations, 47–50% for HHO, 55–58% for ALNS and 34% for 3-opt re-evaluate tours already seen. This complies with the approved budget definition; record distinct-candidate telemetry. *(v1.1: memoization advice withdrawn — it would change the comparison protocol and needs approval.)*
- **O(n²) matrix rebuild per `improve()` call** in the legacy Numba local search. This is why the faulty C3 cache exists; pass the prebuilt matrix instead.
- **Dead complexity:** `PenaltyManager` (unused by live solvers) and `sota_common` (about 2k lines).

---

## 8. Unification strategy

**Principle: two applications, one pure kernel, no shared runtime.** This refines the approved `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`, whose split into kernel, academic platform and study profiles stands. Items marked † change an approved contract and need their own plan, as `AGENTS.md` requires.

### 8.1 Target architecture

```text
            ┌──────────── uniride_core  (pure library: no I/O, no web, no DB) ─────────────┐
            │ CostMatrix(domain, unit, directed, provenance{source, version, sha256, age}) │
            │ PermutationProblem · VehicleRoutingProblem · ConstraintProfile               │
            │ ObjectiveEvaluator + BudgetCounter (atomic_upper_bound_v1)                   │
            │ RouteSimulator (one time-window model per profile) · Validators · Certificate│
            │ CapabilityCatalog: one canonical ID → one implementation (+ production_ready)│
            └──────────────▲──────────────────────────────────────────▲──────────────────┘
                           │ imports core only                        │ imports core only
 ┌──── optimizer_api (production) ─────────────┐   ┌──── academic_benchmark (lab, separate process) ──┐
 │ DTO → adapter → VehicleRoutingProblem       │   │ TSPLIB/CVRPLIB parsers, best-known values (†)    │
 │ Supabase MatrixProvider → TRAVEL_TIME only, │   │ ExecutionGateway = the only result writer        │
 │   fails closed, snapshot-bound, provenance  │   │ ResultStore v2 (protocol, budget, seed_group,    │
 │ Production registry = catalog ∩ ready       │   │   validation, backend, canonical ID) (†)         │
 │ Solver pool: semaphore → processes, hard    │   │ Study profiles · Package D analysis service      │
 │   cancel · certificate re-costs on snapshot │   │ Never imports optimizer_api                      │
 │ No benchmark router, no academic imports    │   └──────────────▲───────────────────────────────────┘
 └──────────────▲──────────────────────────────┘                  │ separate URL and key, admin only
                │ internal key via admin-checked server routes    │
          Next.js product UI                            academic console / CLI
```

### 8.2 Ownership moves

| Artifact | Today | Target | Notes |
|---|---|---|---|
| `uniride_core/algorithms/tsplib_parser.py`: registry, HTTP downloader, best-known table, gap logic | core | `academic_benchmark/datasets` (†) | Keep a pure text parser in core only if core tests need it. |
| `uniride_core/benchmark_runner.py` | core | `academic_benchmark` (†) | |
| `optimizer_api/routers/benchmark.py`, `benchmark_runner.py`, `benchmark_state.py`, `/academic/*` endpoints | production | lab service | Remove from the production app (H8, C4). |
| The academic import in `optimizer_api/strategies/promoted_config_loader.py` | production | a production-owned `production_params.json` | Reviewed, versioned, travel-time evidence only (H17). |
| Legacy `Core-*-TSP` names in `uniride_core/algorithms/engine_factory.py` | core | resolution through the catalog only | H9. |
| `optimizer_api/utils/*` re-export shims | production | delete | Tests import `uniride_core` directly. |
| `uniride_core/algorithms/sota_common/*` and `optimizer_api/strategies/sota_common/*` | core and production | retire deliberately, then archive with a manifest | Unused by live solvers, but re-exports, compatibility tests and the `__main__` entry point consume it; redirect them first (v1.1). |
| The duplicate k-means in `uniride_core/algorithms/clustering.py` (that function set only) | core | delete | Live code uses `clustering_strategies`; keep `Point`, `Cluster`, `calculate_centroid` and the capacity helpers (v1.1). |
| The Numba 3-opt kernels (`numba_accel` 3-opt, `local_search_numba._three_opt_improve_numba` / `_cases_numba`) | core | delete, or quarantine behind a parity test | `CANONICAL_THREE_OPT_DESIGN.md` (H10). |
| `BenchmarkSuitePage` at `/` | product UI | admin-only academic console | C4, M6. |

### 8.3 Contracts

1. **Metric domain.** `CostMatrix.domain` becomes mandatory and is checked when an engine starts. Production engines accept only `TRAVEL_TIME_MINUTES`; academic adapters produce `TSPLIB_*` domains; a mismatch raises (M16, H18, H19).
2. **One shared route-simulation function per `ConstraintProfile`** (`school_pickup`, `school_dropoff`, `forward_cvrptw`): the smallest common function that owns the existing contract, not a new scheduling framework (v1.1). The decoders, the candidate ranking, the certificate and the response builder all use it, which removes today's four time-window models (H2–H4, H16).
3. **The certificate re-costs on the bound snapshot.** It never trusts reported durations (C2).
4. **Academic persistence uses only the `RunResult` envelope** (already in `academic_benchmark/contracts/run.py`), written by the gateway (H8).

### 8.4 Registries

- **The core catalog** (`capabilities.py` + `registry.py`) is the only place canonical academic IDs are defined: ID → (implementation, capabilities). Duplicate registration raises, and import failures fail closed (H9). Consolidate onto these existing modules rather than adding another registry abstraction (v1.1).
- **The production registry** stays a separate, domain-aware CVRP/CVRPTW/UniRide surface with explicit `production_ready` flags (the current API inventory grandfathered as `true`, per the unification design), plus a snapshot test of (key, canonical ID, ready) (M15). *(v1.1: it cannot be produced by filtering the permutation-TSP academic catalog.)*
- **`engine_factory`** resolves canonical IDs only.

### 8.5 Enforcement

- Extend `uniride_core/tests/test_architecture_boundaries.py` so that:
  - `optimizer_api` cannot import `academic_benchmark` (needs H17 and H8 fixed first);
  - `academic_benchmark` cannot import `optimizer_api` (already true for non-test code);
  - nothing imports `archive` (add an `archive/__init__.py` that raises `ImportError`, M17);
  - checks cover importlib strings and root, `src` and `scripts` files too.
- Use one import root (`uvicorn optimizer_api.main:app`), with no `sys.path` mutation (H5, L13).
- Split packaging into separate distributions or extras (`uniride-core`, `uniride-api`, `uniride-lab`) so production images don't ship academic code (†).

### 8.6 Migration order (respecting the `AGENTS.md` gates)

1. **Phase 0 quick wins** (§9.1). These change no contracts.
2. **Harden the archive quarantine** (namespace importability, generic test markers, dynamic and root-file scans). *(v1.1: Gate A's own criteria are substantially met; run-manifest integration is Package D, and production → academic isolation is step 3's separate plan.)*
3. **Decouple production.** Remove the benchmark router and the promoted-config import from the production process. This is a FastAPI surface change: the unification design allows it "where an import boundary or production-readiness check requires it", but it needs owner approval.
4. **Package C:** catalog unification, truthful hybrid compositions with a shared counter, study loading, the YAEM profile.
5. **Package D:** the analysis service, uniform `RunManifestV1` integration across producers, storage and readers (the pilots already emit `manifest.json`), documentation sync, then a draft PR awaiting the powerful-computer runs.

---

## 9. Master roadmap and task cards

**Sequencing note (refined in v1.1):** complete the Phase 0 containment (at least QW1–QW4) **before** any live-data preview smoke test or operational acceptance in `ACTIVE_ROADMAP.md`. The preview touches live student data (C1), and H5 breaks snapshot-bound previews after the TTL. The offline, deterministic Package 2 Task 5 fixture may proceed in parallel, provided it uses no live student data and makes no acceptance claim. Durations below are estimates, not commitments. Each item is its own branch and plan; suggested branch names are given.

### 9.1 Phase 0 — quick wins (about 1–2 weeks)

| # | Action | Closes | Size | Suggested branch |
|---|---|---|---|---|
| QW1 | Read-only live RLS check; then the role-locked insert policy, an insert-and-update role trigger, `search_path`, server-side creation of user rows, and limits on student `ride_requests` writes | C1, C1.b, part of M21 | S | `fix/qw1-users-role-rls` |
| QW2 | `requireAdmin` on all `/api/benchmark/*` routes and a wider middleware matcher; a generic hint response with out-of-band delivery and a trusted IP; a mandatory dev-reset secret | the BFF half of C4, H1, M9 | S | `fix/qw2-bff-auth` |
| QW3 | Fail closed when the matrix is unavailable; retry the first load; one import root; the certificate re-costs on the bound snapshot; provenance in responses | C2, H5, part of M4 | M | `fix/qw3-matrix-fail-closed` |
| QW4 | A benchmark stop event, the slot held until the thread exits, parameters validated by the compute policy (or unmount the router in production) | C4 | S | `fix/qw4-benchmark-stop` |
| QW5 | Disable the Wilcoxon tab; label or remove the fabricated demo metrics | C5, M6 | XS | `fix/qw5-disable-unsafe-stats` |
| QW6 | The weak-reference cache fix; flag manifest-less multi-instance results as suspect | C3 | XS | `fix/qw6-ls-cache-weakref` |
| QW7 | Pass the strategy's seeded RNG into clustering; validate `clustering_algorithm` | H12 | S | `fix/qw7-cluster-rng` |
| QW8 | A production CSP (nonces, no `unsafe-eval`, no localhost entries) and HSTS; escape the PDF export | M8 | S | `fix/qw8-csp-xss` |
| QW9 | CI: the full canonical Python suite (sharded if needed), `npm run build`, and a report-only `npm audit` | H20 | S | `ci/qw9-full-gates` |
| QW10 | Small fixes: the Sw/So mapping (H15); drop `round(cost, 2)` (M18); keep the solver's termination reason (L8); no window taken across directions (M2); fix the "km" unit (M3); the `/extract-time-windows` crash (M23) | listed | XS | `fix/qw10-small-correctness` |
| QW11 *(v1.1)* | SOTA adapter: no silent greedy fallback (fail, or label it explicitly) and optimize the depot-anchored duration objective | M26 | S | `fix/qw11-sota-adapter-truth` |

#### Task cards

<details>
<summary><b>QW1 — Lock the user role and ride-request status in RLS (C1, C1.b)</b></summary>

- **Goal:** no authenticated user can create or elevate a non-student role or self-approve a ride request.
- **Preconditions:** run the read-only queries in C1 against the live project and record the output in the PR. **Do not change the live database without explicit owner authorization.**
- **Files:**
  - a new `supabase/migrations/<date>_lock_user_role_and_ride_status.sql`;
  - `src/lib/supabase-auth.ts` (drop the `role` parameter);
  - optionally a new server-side registration route.
- **Steps:**
  1. Write SQL tests (pgTAP, or a scripted `set role authenticated` session against a local Supabase).
  2. Add the migration from C1/C1.b.
  3. Remove the client-side role.
  4. Retire `rls_policies.sql`'s drop-all loop (M21).
- **Done when:**
  - the tests prove the insert of `admin`, the update of `role` and status self-approval all fail for `authenticated`;
  - the existing BFF flows pass (`npm test`);
  - the live policies match after the owner applies the migration.
</details>

<details>
<summary><b>QW2 — Authenticate the BFF benchmark routes; fix the hint and dev-reset routes (C4, H1, M9)</b></summary>

- **Files:** all `src/app/api/benchmark/**/route.ts`; `src/proxy.ts`; `src/services/benchmark-service.ts` (send the bearer token via `adminFetch`); `src/app/api/auth/hint/route.ts`; `src/app/api/auth/dev-reset/route.ts`.
- **Steps:**
  1. Add route tests asserting 401 for anonymous callers.
  2. Add `requireAdmin` to every handler.
  3. Make the hint response identical in all cases.
  4. Require the dev-reset secret.
- **Decision needed from the owner:** is the landing-page benchmark meant to be anonymous? If so, provide a read-only cached-results route instead.
- **Done when:** the route tests pass, the landing page still renders for admins, and anonymous POSTs get 401.
</details>

<details>
<summary><b>QW3 — Fail closed on the matrix and certify against the snapshot (C2, H5)</b></summary>

- **Files:** `optimizer_api/utils/matrix_repository.py`, `optimizer_api/utils/data_loader.py`, `optimizer_api/routers/readiness.py`, `optimizer_api/routers/optimization.py`, `optimizer_api/verification/response_certifier.py`, `uniride_core/algorithms/ortools_cvrp_engine.py`, `optimizer_api/runtime_config.py`.
- **Steps:**
  1. Turn Appendix H.2–H.4 into failing pytest cases.
  2. Implement the C2 fix.
  3. Use one DataLoader import path.
  4. Add a startup error for missing Supabase credentials when `APP_ENV=production`.
  5. Add an explicit `UNIRIDE_ALLOW_COORDINATE_FALLBACK` for dev and tests, defaulting to false.
- **Done when:** the repro tests show fail-closed behavior and automatic recovery; one singleton is loaded; the full Python suite passes. Update `CURRENT_ARCHITECTURE.md` §3 truthfully.
</details>

<details>
<summary><b>QW4 — Make benchmark stop real and bounded (C4)</b></summary>

- **Files:** `optimizer_api/benchmark_state.py`, `optimizer_api/benchmark_runner.py`, `optimizer_api/routers/benchmark.py`, `optimizer_api/compute_policy.py`.
- **Steps:**
  1. Turn Appendix H.5 into a failing test.
  2. Add a per-run `threading.Event` that the loop checks.
  3. Hold the slot until the thread exits.
  4. Validate parameters with the compute policy.
  5. Rate-limit the router and require the ops key.
- **Done when:** after stop, no thread is alive within one experiment; oversize parameters get 422.
</details>

<details>
<summary><b>QW5 / QW6 / QW7 — Evidence-integrity quick fixes (C5, M6, C3, H12)</b></summary>

- **QW5:** replace the Wilcoxon tab body with an informational message; remove auto-demo mode and stop persisting demo results; add a visible "DEMO DATA" banner to the IE tracks.
- **QW6:** apply the C3 weak-reference fix plus a regression test (Appendix H.1 → pytest). Add a "suspect results" note to the academic workstate listing which runner paths were affected.
- **QW7:** thread an `rng: random.Random` through `get_clustering_strategy` and every clustering strategy; allowlist `clustering_algorithm`; replace the global reseeding in the academic code.
- **Done when:** the regression tests pass, the canonical suites pass, and the `CANONICAL_THREE_OPT_DESIGN.md` regression command passes.
</details>

### 9.2 Phase 1 — mid-term architecture (about 1–3 months)

| # | Action | Closes | Depends on | Acceptance |
|---|---|---|---|---|
| MT1 | **Time-window unification.** One `RouteSimulator` per profile. Count the return arc to school and waiting time. Rank candidates by (violations, vehicles, cost). Pass windows and maximum duration to OR-Tools and PyVRP. Add a forward CVRPTW profile for Solomon. Make solvers respect the fleet. | H2, H3, H4, H16, M1, L12 | QW3 | Property tests: solver feasibility equals certificate feasibility, and returned times equal the simulated times. |
| MT2 | **Matrix provenance contract** (`ACTIVE_ROADMAP.md` Priority 5): domain, unit and provenance enforced; maximum staleness; paginated fetch with a row-count check; reject caller-supplied matrices. | H18, M4, M16 | QW3 | Every response carries provenance, and the engines reject a mismatched domain. |
| MT3 | **Execution:** a global semaphore, then a process-isolated solver pool with hard cancellation and cooperative deadlines, then durable jobs. Make readiness async-safe. | H6, H7 | QW4 | Live solver workers never exceed the cap; cancel kills the work; `/health` p99 < 50 ms under load. |
| MT4 | **Engine separation:** extract the lab service and ResultStore v2 with gateway-only writes; one ID per implementation; remove the promoted-config import; retire the quick runner. | H8, H9, H17, H19, M15, M16, L13 | An approved contract-change plan (†) | `import optimizer_api.main` loads no academic module; every stored row carries full provenance. |
| MT5 | **Academic work, in gate order:** harden the archive quarantine (M17); inject manifests into CLI/Smart runs (H13); fix fractional costs and memetic metadata (M18, M19); then the Package C hybrids (GWO/HHO-3opt and -ALNS sharing one counter) and the YAEM study profile. Uniform `RunManifestV1` integration belongs to Package D (LT1). *(v1.1: the earlier "close Gate A gaps" framing is withdrawn.)* | H13, M17, M18, M19 | — | Each gate's acceptance per `ACADEMIC_STUDY_UNIFICATION_DESIGN.md`. |
| MT6 | **Local-search consolidation:** remove the forbidden kernel path (H10); canonical 3-opt in the production hybrid (M14); the 3-opt speed-up behind a parity test (M25); iteration- or evaluation-based SOTA termination (H11); archive `sota_common`; remove the shims; fix the SOTA adapter objective (M26). | H10, H11, M14, M25, M26, L3, L10 | QW6 | `CANONICAL_THREE_OPT_DESIGN.md` regression plus new parity tests; same-seed reproducibility under load. |
| MT7 | **Frontend:** a polling hook; memoized analytics (profile first); split the landing page; replace `xlsx`; a synchronous auth callback; re-authentication before password change; a typed snake_case→camelCase DTO mapper; E2E coverage against `next build` for the production React (M11, Low). | H14, H15, M10–M13, M24, L1, L2, L5–L7 | QW2 | Fake-timer polling tests; E2E smoke tests on the production build. |
| MT8 | **Dudullu:** Package 2 Task 5, then Package 3 (transactional publication plus RLS consolidated into migrations, with policy tests). | M21 | QW1, QW3 | Per `ACTIVE_ROADMAP.md`. |

### 9.3 Phase 2 — long-term vision (a quarter or more)

| # | Action |
|---|---|
| LT1 | **Package D analysis service:** pinned SciPy; Kruskal-Wallis → Mann-Whitney with Holm correction, or Friedman plus paired post-hoc tests for matched designs; effect sizes; reproducibility manifests; distinct-candidate reporting (M20); runs on the more powerful computer; held-out problem families; **re-run every result flagged suspect under C3, H9 or H11.** |
| LT2 | Dudullu Packages 4–6 (workflows, certified cross-wave decision support, pilot and operations) on the hardened platform. |
| LT3 | GIS: a backend geometry contract (GeoJSON or encoded polyline, with direction and staleness); a map-provider threat model and CSP update; a renderer with memoized layers (`ACTIVE_ROADMAP.md` Priority 7). |
| LT4 | Distributed admission and rate limiting; observability (matrix source and age, solver slots, queue depth); SLOs; packaging split into separate distributions and images. |
| LT5 | KVKK data minimization (remove `password_hint`; restrict disability data to need-to-know); an admin audit log; a regular dependency-security cadence (`npm audit`, `pip-audit`). |

### 9.4 Exit criteria

- **Production-ready:**
  - no open Critical or High findings;
  - the certificate re-costs routes on the authoritative snapshot;
  - hard cancellation and process isolation;
  - RLS policy tests in CI;
  - CI gates on the full suites, the build and the dependency audit;
  - verified live readiness.
- **Academically rigorous:**
  - every result enters through the gateway into ResultStore v2;
  - Package D statistics;
  - manifests for every run;
  - no pooling across protocols;
  - suspect results re-run.

---

## Appendix A — Duplicate-implementation map

Source: P1B. "Live" means reachable from a production or academic entry point.

| Group | Copies → live/dead | Merge target |
|---|---|---|
| 2-opt | **Live:** `local_search.py` (production); `local_search_numba` (academic legacy); `numba_accel` ATSP (tsp_matrix_metaheuristics, sota_tsp); `objective_budget` (fair); the `ls_engine` Python fallback. **Dead:** `sota_common._layer_2opt`. | `objective_budget` accounting plus one `numba_accel` delta kernel behind a parity test |
| 3-opt | **Canonical:** `three_opt.py`. **Live:** `fairness.improve_three_opt_budgeted` (duplicate controller); `local_search.py` (production default, M14); the `numba_accel` kernel (live and forbidden, H10); the `ls_engine` fallback (reverses the middle segment only); `run_tsp._apply_3opt_bounded` (perturbation; cases 4 and 5 identical). **Dead:** `local_search_numba._three_opt_improve_numba/_cases_numba` (0 callers); `sota_common._layer_3opt` (actually a 2-opt). | `three_opt.py` plus one budget-aware controller |
| Or-opt | **Live:** `local_search.py`, `local_search_numba`, `numba_accel` (node 0 fixed), `objective_budget`, the `ls_engine` fallback. **Dead:** `sota_common`. | `objective_budget.improve_or_opt_budgeted` plus one kernel |
| GA / PSO / GWO / HHO | All live, with different behavior: `tsp_meta_engines.solve_*` (production Pipeline A, routing `Core-*-TSP`, `FCM-*`); `*_split_engine.py` (production Pipeline B); `numba_metaheuristics._run_*` (cli_engine, registry fallback); `tsp_matrix_metaheuristics` GWO/HHO (registry TSP) | One matrix-native engine per family in `uniride_core`; string-based strategies become adapters |
| Destroy/repair and multi-layer local search | **Live:** sota_tsp `destroy_ops`, `repair_ops` and `ls_engine`. **Dead:** `sota_common` destroy/repair/multi_layer_ls/penalty/diversity/acceptance/multi_start (about 2k lines; only its self-shims in `optimizer_api/strategies/sota_common/*` and tests use it). | Keep `sota_tsp`; archive `sota_common` and its shims |
| Hybrid local search | `local_search.py` Hybrid (production default); `local_search_numba` Hybrid (academic) | One composer over the canonical operators |
| Clustering | **Live:** `clustering_strategies/*`. **Dead:** `clustering.py` `kmeans_clustering` / k-means++ (re-export only); `optimizer_api/utils/clustering_strategies/*` (9 shims, 0 importers). | Delete the shims and the `clustering.py` copy |
| `optimizer_api/utils` shims | `local_search.py` and `local_search_numba.py` are imported only by tests; the rest are re-exports | Delete once tests import `uniride_core` |
| Registries | `STRATEGY_REGISTRY` + `STRATEGY_FACTORIES` (with the `canonical.py` parity check); `uniride_core/algorithms/registry.py` (metadata); `engine_factory.py`; `registry_setup` (silent overwrite) | `registry.py` as the single ID → factory catalog (§8.4) |

## Appendix B — Import-boundary matrix

Source: P4, from a scan of every Python import (top-level, lazy, inside try, importlib and sys.path changes) plus an offline import probe.

| From → To | Statements (files) | Example | Verdict |
|---|---|---|---|
| uniride_core → optimizer_api, academic_benchmark or archive | 0 | — | OK |
| optimizer_api → academic_benchmark | 12 (2), 3 at module top level | `strategies/promoted_config_loader.py:9`; `routers/benchmark.py:80, 145, 164, 184, 204, 336` | **VIOLATION** (H8, H17) |
| optimizer_api → uniride_core | 163 (57) | — | OK |
| academic_benchmark → optimizer_api | 0 in non-test code; 2 (1 file) in tests | `tests/test_production_registry_snapshot.py:14` | OK |
| academic_benchmark → uniride_core | 123 (22) | — | OK |
| active code → archive (import, importlib, sys.path or path string) | 0 | — | OK, but `archive` is still importable (M17) |
| root `*.py` → academic_benchmark / optimizer_api | 10 (3) / 4 (1) | `test_patch.py:7-9, 26-28` | Low (L13) |
| `src/`, `scripts/` → Python packages | 0 (HTTP only) | `src/lib/optimizer-server.ts:3, 12`: one `OPTIMIZER_API_URL` serves both `/optimize` and the benchmarks | Shared service (C4, H8) |

**Probe:** `import main` loads `academic_benchmark` (`benchmark_utils`, `promoted_configs`, `results_reader`, `tsplib_manager`), `uniride_core.benchmark_runner` and `uniride_core.algorithms.tsplib_parser`. Four files load under two module names each (H5).

## Appendix C — Work-package gate status

Source: P4 (`ACADEMIC_STUDY_UNIFICATION_DESIGN.md` delivery plan).

| Gate | Status | Evidence |
|---|---|---|
| A — YAEM quarantine and contract foundation | **Substantially present** *(corrected in v1.1)* | **Present:** `archive/academic_benchmark/yaem2026_legacy` has `QUARANTINE.md` and a manifest (`uniride-archive/v1`, 159 entries, all with SHA-256); study, dataset and run v1 schemas plus `contracts/`; quarantine tests that reject static imports of the archived YAEM path (`test_yaem_quarantine_boundary.py:39-50`); `pyproject.toml` excludes `archive` (`:29, :46`). **Residual hardening (not a gate failure):** namespace importability of `archive/` and the scan scope (M17). *(v1.0 also listed a missing optimizer → academic boundary test and missing run-manifest emission; neither is a Gate A criterion. See the D row and §8.6.)* |
| B — Bildiri canonical extraction | **Present** (parity tests not re-run during this audit) | Relocated solvers in `uniride_core/algorithms/tsp_matrix_metaheuristics/{gwo,hho}_solver.py`; parity fixture `bildiri_gwo_hho_v1.json` with `test_bildiri_solver_parity.py`; zero active Bildiri imports (scan; `find_spec` returns None; the folder is gone); `bildiri2026_legacy` has `QUARANTINE.md` and a manifest (233 SHA-256 entries); `academic_benchmark/studies/bildiri2026/study.json` exists with status "draft". Caveat: H9. |
| C — Catalog, composition, experiment services | **Partial** | **Present:** all 14 canonical IDs (`capabilities.py:244-332`) and the resolver. **Absent:** the 3-opt and ALNS hybrid compositions (still PLANNED, `:275-278`; GA and PSO are CANDIDATE); any study loader outside tests; `studies/yaem2026`. **Partial:** fixed vs native separation exists only in the pilot manifests, not in the database. |
| D — Analysis, documentation, publication | **Absent** (as expected at this stage) | The dashboard runs Wilcoxon over pooled, unlabelled rows (C5), and invalid evidence is reachable through `/academic/*` (H8). *(v1.1)* The pilots already emit `manifest.json` (`fair_pilot.py:583`, `native_pilot.py:596`), but no producer validates against `RunManifestV1` (`contracts/run.py:65`); uniform integration across producers, storage and readers is missing. |

**v1.1 correction:** the v1.0 claim that Package C work started while Gate A was incomplete is **withdrawn**. Gate A's criteria (`ACADEMIC_STUDY_UNIFICATION_DESIGN.md:422-429`) are substantially met, and the residual archive hardening (M17) can proceed alongside Package C.

## Appendix D — Academic contract compliance

Source: ACAD.

| Requirement | Status | Evidence |
|---|---|---|
| One evaluation = one complete closed tour; no delta substitution | met (fair paths) | `objective_budget.py:45-47, 94-99`; demo counts exact |
| One shared cap across initialization, search, local search and polish | met | `gwo_solver.py:158-169, 204-207, 116-127`; same in `hho_solver.py` |
| A population phase starts only if a safe bound fits | met, with unvalidated parameters | `gwo_solver.py:204-207`; `hho_solver.py:264-267` |
| Candidate-atomic local search; no overshoot | met | `objective_budget.py:37-43, 94-97`; `fairness.py:391-394` |
| Configured and consumed evaluations recorded; overshoot rejected | met | `execution_gateway.py:133-148`; `fairness.py:249-254` |
| Fabricated or unestablished accounting rejected | partial: claims-gated, no runtime counter | `preflight.py:163-175` |
| `algorithm` = `algorithm_id`; `evaluations` = `objective_evaluations` | met | `execution_gateway.py:72-77, 118-124` |
| GWO/HHO aliases are memetic_2opt and counted | partial | `algorithm_resolution.py:52-55`; M19 |
| Hybrids: 0.80 split, SHA-256 polish seed, fail on polish error, stage metadata | absent (consistent with Package C being gated) | `capabilities.py:275-278` (PLANNED); `preflight.py:332-333` rejects them; schema fields only in `contracts/run.py:40, 52` |
| Digest seed per problem and replicate, shared across algorithms | met in the pilots; violated in CLI, Smart, web and smoke runs | `fairness.py:219-231`; `registry_setup.py:196, 654, 1039, 1138`; H9, H13 |
| No `hash()` or wall-clock seeding | met | none in active academic paths |
| Backend truthfulness | met on the gateway path | `base_solver.py:115-163`; `execution_gateway.py:48-69, 184-186` |
| Independent validation before aggregation | met in the pilots; absent elsewhere | `execution_gateway.py:80-160`; `fair_pilot.py:316-344`; H8, H9 |
| Failed validation blocks aggregation | met in the pilots and Smart | `fair_pilot.py:588-593`; `smart_benchmark.py:755-759` |
| Native results never pooled with fixed-budget results | met in the pilots; violated in the database, dashboard and promotion | `native_pilot.py:395-405`; H8 |
| Kruskal-Wallis/Mann-Whitney with Holm, or Friedman; effect sizes; pinned library | violated / absent | `dashboard.py:326-388` (C5) |
| Smoke and pilot runs descriptive only | met in the pilots; violated in the dashboard | `fair_pilot.py:459-479`; C5 |
| No fixed F thresholds or handwritten p-values | met | none in active code |

## Appendix E — Frontend hygiene counts

| Item | Count |
|---|---|
| ESLint (`src/`, 222 files) | 0 errors / 163 warnings: 70 `@typescript-eslint/no-explicit-any`, 70 `@typescript-eslint/no-unused-vars`, 19 `react-hooks/exhaustive-deps`, 4 `react-hooks/incompatible-library` |
| Top files by warnings | `src/app/page.tsx` 17; `admin/sandbox/page.tsx` 12; `services/doubus/multi-vehicle-routing.ts` 8; `admin/vehicle-planning/vehicle-planning-page.tsx` 8; `admin/route-test/page.tsx` 7; `services/excel/import.ts` 6; `admin/vehicle-planning/page.tsx` 6; `services/schedule-to-requests.ts` 6; `admin/compare/page.tsx` 5; `components/admin/ie-dashboard.tsx` 5 |
| Explicit `any` (non-test, excluding `ui/`) | 62 lines in 32 files, 26 of them `catch (e: any)` |
| `as never` / `as unknown as` | 21 in 6 files (Supabase calls) / 1 |
| `eslint-disable` directives | 12, all `react-hooks/set-state-in-effect` next-line (11 app files, 1 `ui/carousel`); none for `exhaustive-deps` |
| `@ts-ignore` / `@ts-expect-error` / `@ts-nocheck` | 0 / 0 / 0 |
| `exhaustive-deps` assessment | 16 of 19 harmless (a missing stable `t`/`tc`/`toast`, or an extra dependency); 1 real bug (`admin/drivers/page.tsx:57`, M7); 2 low (driver assignments/history, L15) |
| `incompatible-library` | 4 (react-hook-form `watch`); harmless while the React Compiler is off |
| tsconfig scope | `include: **/*.ts(x)` does **not** pull in `.temp/`, because TypeScript's `**` skips dot-folders (1,469 TS files there); `archive/`, `scratch/` and `agent-ctx/` contain no TS files |
| ESLint config | `no-explicit-any` set to "warn"; `react/no-unescaped-entities` off; `reportUnusedDisableDirectives: "warn"` |

## Appendix F — Checked and sound (do not re-investigate)

**Backend**
- **Auth:**
  - keys are compared with `secrets.compare_digest` (`optimizer_api/auth.py:13-55`);
  - the optimization router depends on auth (`routers/optimization.py:60-64`);
  - readiness requires the ops key (`routers/readiness.py:19-23`).
  - Deviation: tenant keys also unlock the benchmark router (C4).
- **Strategy isolation:**
  - each request gets a fresh, name-checked strategy instance (`strategies/canonical.py:46-57`);
  - `apply_compute_policy` deep-copies the request (`compute_policy.py:394`) and changes only that fresh instance (`:447`);
  - the compute policy is a frozen dataclass, lowering-only and validated at startup (`:25-75`);
  - admission limits apply on `/optimize` and `/compare` (`schemas.py:298-323, 467-478`), but not on benchmark runs.
- **`/compare` orchestration:** at most 2 workers, a 120 s soft deadline via `wait()`, and queued futures cancelled, as documented.
- **Edges:**
  - the rate limiter is lock-protected and keyed by tenant or `request.client.host`, so `X-Forwarded-For` is not trusted (`rate_limit.py:24-55`);
  - CORS is an environment allowlist with no credentials (`main.py:79-92`).
- **Shared state:** no global RNG seeding, `os.environ` writes, logging reconfiguration or parallel Numba kernels in request paths.
- **Error sanitizing:** the global 500 handler (`main.py:72-75`) and certifier errors (`response_certifier.py:119-129`) are sanitized.
- **Matrix repository:**
  - the Supabase timeout is applied (`ClientOptions`);
  - invalid arcs are rejected while a matrix is loaded (`matrix_repository.py:471-487`);
  - the binding rejects stale or unhealthy snapshots (`:428-435`).
- **Paths and tokens:** CLI filename resolution and the problem-name regex block path traversal (`routers/benchmark.py:627-642`); owner tokens are hashed and compared with `compare_digest`.
- **Outbound calls:** only Supabase PostgREST and the TSPLIB archive; `uniride_core/adapters/matrix_builder.py` is pure.

**Frontend**
- **Secrets:** only `supabase-admin.ts` reads the service-role key, and only route handlers and `admin-auth` import it. No `NEXT_PUBLIC_*` variable holds a secret.
- **Optimizer transport:** every optimizer-bound route uses the server-only `optimizerFetch` (`optimizer-service.ts:8, 223, 316`).
- **Role checks:** `requireAdmin` and `requireRole` verify the JWT and look up the role server-side by id (`admin-auth.ts:70-134`). They are applied on `admin/*`, sandbox, route-plans, calculate-vehicles, compare, the optimize POST, and the driver and profile routes. (But see C1: the role column itself is writable at insert.)
- **No IDOR:**
  - ride-confirmation takes the user from the token, every query uses `.eq("user_id", authUser.id)`, and schedule ownership is checked (`:80`);
  - route-plans is admin-only;
  - the driver PUT checks `driver_id`.
- **Benchmark owner cookie:** HttpOnly, SameSite=Lax, Secure in production, path `/api/benchmark`, 2 hours; an opaque token checked by the backend.
- **Dev-reset** is disabled in production builds, and the cached admin token is cleared on every auth event (`auth-context.tsx:29, 52-55`).
- **Benchmark pages** handle all backend terminal states (completed, failed, stopped).

**Core math and local search**
- **Capacity** uses strict `>` everywhere, so a load equal to capacity is allowed:
  - `feasibility_certificate.py:144`, `split_decoder.py:100`;
  - `string_split_decoder.py:321/393/482`, `string_greedy_routing.py:54-57`;
  - `vroom_cvrp_engine.py:210-213`; PyVRP re-checks loads (`pyvrp_cvrp_engine.py:143-148`).
- **Demand and identity:** Sw/So is a 2-D demand vector (`demand_builder.py:16-20`), and occurrence keys are unique per student (`demand_builder.py:38-85`).
- **Certifier structure checks:** coverage and duplicate visits; `student_ids` by position; load counts; chain continuity; interior depot visits; vehicle count; non-finite and negative arcs. It fails closed on exceptions (`response_certifier.py:196-213`), and fleet matching is a correct Kuhn matching (`:136-193`).
- **Directed costs:**
  - every lookup is `matrix[from][to]`;
  - production local search re-evaluates whole routes (`local_search.py:101-140`), with no symmetric 2-opt shortcuts;
  - the reverse-arc fallback in `string_split_decoder.py:289-296` cannot fire, because `_arc_value` rejects missing or zero arcs.
- **Units and engines:**
  - minutes are used end to end, with consistent scale factors (OR-Tools ×10, PyVRP/VROOM ×60);
  - VROOM and PyVRP responses recompute durations from the raw matrix;
  - their window checks run forward, in floats, and include the depot due time (`pyvrp_cvrp_engine.py:181-209`, `vroom_cvrp_engine.py:230-258`).
- **Penalties and ranking:** PenaltyManager weights only increase, are capped and never go negative (`penalty_manager.py:117-185`); `objective_rank.py:14-56` preserves ordering.
- **Numba 2-opt deltas** are exact on asymmetric matrices (`local_search_numba.py:197-219`, `numba_accel.py:43-58`; maximum error 3.4e-13 over 200 random ATSP instances).
- **`three_opt.py` against its contract:**
  - directed mode yields exactly one candidate (S1S3S2);
  - symmetric mode yields exactly 7 distinct valid cycles for every admitted triple at n = 6..12;
  - an asymmetric matrix selects directed mode automatically, and forcing symmetric mode on one raises (`:201-205`);
  - `window` filters cuts only (`:79-83`);
  - improvement is strict with a relative tolerance, and candidate order is deterministic.
- **3-opt wrappers:** `local_search_numba` `ThreeOptLocalSearch` and `improve_route_numba` delegate to the canonical engine (`:778-784, 1180-1197`).
- **RNG use:**
  - production strategies use a per-request `random.Random(seed)`;
  - `tsp_meta_engines`, the split engines, `numba_metaheuristics` and `sota_tsp` use explicit Random instances;
  - there is no `np.random`, no RNG inside Numba, and no `prange`/`parallel=True` in use;
  - sweep clustering is deterministic.

**Academic**
- **Gateway:**
  - `consume()` raises before overshoot;
  - the gateway rejects protocol confusion and mixed backend labels (`execution_gateway.py:133-158`).
- **Pilots:** they enforce strict configs, check problem type against observed asymmetry, verify replay determinism, write output outside the repository, and write files atomically.
- **Accounting:**
  - ALNS destroy and repair use insertion deltas only, with exactly one complete evaluation per candidate;
  - fair-mode accounting is exact for 2-opt, 3-opt, ALNS and GWO/HHO Pure and Memetic-2opt, on TSP and ATSP.
- **Backends and catalog:**
  - the backend probe actually executes the nopython kernel;
  - `Core-OrOpt-TSP` is VERIFIED at runtime through the override (`capabilities.py:317-332`).
- **Seeds and statistics:** no `hash()` or wall-clock seeding in active academic paths, and no fixed F thresholds or handwritten p-values in active code.

**Boundaries and repository**
- **Core imports:** `uniride_core` imports nothing from `optimizer_api`, `academic_benchmark`, `archive`, FastAPI or SQLite (`test_architecture_boundaries.py:17-35`), and non-test academic code never imports `optimizer_api`.
- **Archive:** no active code references archive or legacy paths, and the legacy active folders are gone.
- **False LKH names:** `GWO-LKH` and `HHO-LKH` raise `ForbiddenAliasError` (`algorithm_resolution.py:65-72, 144-148`). They are unknown to the production registry and `engine_factory`, so both return HTTP 400.
- **Responses and UI:** `/optimize` and `/compare` responses carry no gap or best-known fields, and `src/` imports no academic artifacts.
- **Secrets:** no secrets are tracked in git (only `.env.example`); `.env*` is gitignored.

**Added in v1.1** (from the Codex verification, re-checked by the lead):
- Snapshot-bound `/optimize` requests fail closed when the snapshot is unavailable or changed (`optimizer_api/routers/optimization.py:211-234`; reproduced in Appendix H.4 steps 6 and 9).
- The YAEM quarantine test rejects static imports of `archive.academic_benchmark.yaem2026_legacy` (`academic_benchmark/tests/test_yaem_quarantine_boundary.py:39-50`).
- The fair and native pilots write `manifest.json` atomically (`academic_benchmark/fair_pilot.py:583`, `native_pilot.py:596`).
- The landing page labels demo mode in the UI (`src/app/page.tsx:1156-1160, 1902-1903`).
- Next 16's peer range accepts React 18.2+ or 19; the App Router's bundled React is by design.

## Appendix G — Open questions

| # | Question | Affects | How to resolve |
|---|---|---|---|
| Q1 | Do the live RLS policies and triggers on `users` and `ride_requests` match the repo SQL? | C1, C1.b, M7, M8 | Run the read-only queries in C1. |
| Q2 | Is "arrive at school by `target_time` (− offset)" an approved hard constraint? Does `max_travel_time` include waiting or student ride time? | H2 (Critical if yes) | Owner decision; record it in `CURRENT_ARCHITECTURE.md`. |
| Q3 | Are CVRPTW/Solomon results part of any active study's evidence? | H16 | Check the study profiles and manifests. |
| Q4 | Are production `duration_minutes` values fractional? | Size of the C2 rounding issue | `select count(*) from time_matrix where duration_minutes <> round(duration_minutes)` (read-only). |
| Q5 | Does any client consume `arrival_times`/`departure_time`? | H3 | Grep the consumers; the frontend only declares them in its types. |
| Q6 | Is zero service/dwell time on the production path intentional (wheelchair boarding takes time)? | MT1 | Owner decision. |
| Q7 | Is the fixed "latest possible start" rule intended? It rejects routes that are feasible with an earlier departure. | H2, H4 | Owner decision. |
| Q8 | How many pre-governance and `web_matrix_native` rows exist in `tsplib.db`? | H8 (Critical if they feed reported results) | A read-only query on a **copy** of the database. |
| Q9 | Is SciPy plus Streamlit installed in any operator environment? | C5 reachability | Ask the operators. |
| Q10 | Should the matrix-surface TSP IDs stay production-only? | The shape of the H9 fix | Owner decision. |
| Q11 | Is the landing-page benchmark meant to be anonymous? | The shape of the C4/QW2 fix | Owner decision. |
| Q12 | How does App Hosting handle `X-Forwarded-For`? | H1 limiter | Check the platform docs, or a controlled test. |
| Q13 | Has dev-reset ever been pointed at a shared or production Supabase project? | M9 | Owner. |
| Q14 | What are the Supabase `max_rows` setting and the `time_matrix` location count? | M4 | Project settings; `select count(distinct origin_code) from time_matrix`. |
| Q15 | How is the production optimizer launched and packaged, and is the benchmark router reachable in it? | C4, H5, H8 | The deployment configuration, which is not in the repo. |
| Q16 | Does any environment ship `promoted_configs.json` or set `UNIRIDE_PROMOTED_CONFIG_PATH`? | H17 | Environment inventory. |
| Q17 | Were published or archived academic results produced by `Numba-*`/`Core-*-TSP` runs without a manifest, in processes that handled several same-size instances? | C3 rerun scope | Run manifests and `RunResult` types. |
| Q18 | Is the Next.js app internet-facing? | C4, H1 exposure | Deployment configuration (`apphosting.yaml` suggests Firebase App Hosting). |
| Q19 | Memory growth: RUNNING benchmark runs are never evicted, and `/import` accepts unbounded results. | Capacity | A load test (`optimizer_api/models/schemas.py:576-584`; `benchmark_state.py:174-204`). |
| Q20 *(v1.1)* | Does any current dispatch or publication path consume `ride_requests.status`? | C1.b severity (High → Critical if yes) | Trace the consumers of `ride_requests`; legacy routing reads `confirmed` rows. |

## Appendix H — Reproduction scripts (re-run 2026-10-01)

These are adapted from the investigators' scratch scripts, with absolute paths replaced by `UNIRIDE_ROOT` or the current directory; the logic is otherwise unchanged. All five are offline (`.env` disabled, Supabase blank or faked, no network) and write nothing to the repository or any database. Run them from the repository root with the project venv, for example:

```powershell
$env:NUMBA_CACHE_DIR = "$env:TEMP\uniride-numba-cache"   # keep JIT caches outside the repo
.\.venv-jit\Scripts\python.exe -B <path>\repro_c3_cache_idreuse.py
```

After a fix, each script should show the fail-closed or correct behavior. Convert each one into a pytest regression test in the fixing branch. *(v1.1: Codex independently re-ran H.1 unchanged and observed the identical 4-of-6 corruption.)*

### H.1 — C3: `id()`-keyed local-search cache

<details>
<summary>repro_c3_cache_idreuse.py</summary>

```python
"""C3 repro: local_search_numba._DIST_MATRIX_CACHE is keyed by
(frozenset(labels), id(duration_func)). Once a freed duration_func's id() is
reused, a later same-size problem receives a previous problem's matrix."""
import os
import sys

ROOT = os.path.abspath(os.environ.get("UNIRIDE_ROOT", os.getcwd()))
sys.path.insert(0, ROOT)
import numpy as np

from uniride_core.algorithms import local_search_numba as lsn
from uniride_core.algorithms import numba_metaheuristics as nm
from uniride_core.algorithms.local_search_numba import LocalSearchType

ids = []
_orig = nm.create_np_duration_func


def _spy(dm, locs):
    f = _orig(dm, locs)
    ids.append(id(f))
    return f


nm.create_np_duration_func = _spy


class P:
    def __init__(self, name, n, coords):
        self.name = name
        self.dimension = n
        self.coordinates = coords
        self.optimal = None


def mk(n, seed):
    r = np.random.default_rng(seed)
    pts = r.random((n, 2)) * 1000
    D = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
    return [tuple(p) for p in pts.tolist()], D


n = 60
probs = []
for s in (1, 2, 3):
    c, D = mk(n, s)
    probs.append((P(f"P{s}", n, c), D))

ls = LocalSearchType.TWO_OPT
lsn._DIST_MATRIX_CACHE.clear()
shared = {}
for prob, D in probs:
    for seed in (11, 12):
        r = nm.run_single_test(prob, ls, seed, {"max_iterations": 1000}, dist_matrix=D)
        shared[(prob.name, seed)] = (r["tour_length"], ids[-1])
print("cache entries after 6 runs:", len(lsn._DIST_MATRIX_CACHE))

bad = 0
for prob, D in probs:
    for seed in (11, 12):
        lsn._DIST_MATRIX_CACHE.clear()
        r = nm.run_single_test(prob, ls, seed, {"max_iterations": 1000}, dist_matrix=D)
        tl_shared, fid = shared[(prob.name, seed)]
        flag = "" if abs(tl_shared - r["tour_length"]) < 1e-6 else "   <-- DIFFERENT (stale matrix)"
        bad += bool(flag)
        print(f"{prob.name} seed={seed} id={fid} shared-process={tl_shared:.1f} clean-cache={r['tour_length']:.1f}{flag}")
print("runs corrupted:", bad, "of 6")
```
</details>

Observed on 2026-10-01 (`id` values vary by run):
```text
cache entries after 6 runs: 2
P1 seed=11 shared-process=6595.6 clean-cache=6595.6
P1 seed=12 shared-process=6564.6 clean-cache=6564.6
P2 seed=11 shared-process=31434.5 clean-cache=6744.7   <-- DIFFERENT (stale matrix)
P2 seed=12 shared-process=32994.0 clean-cache=6399.4   <-- DIFFERENT (stale matrix)
P3 seed=11 shared-process=30743.3 clean-cache=6413.1   <-- DIFFERENT (stale matrix)
P3 seed=12 shared-process=30523.0 clean-cache=6623.0   <-- DIFFERENT (stale matrix)
runs corrupted: 4 of 6
```

### H.2 — C2(a): zero matrix certified as feasible

<details>
<summary>repro_c2_zero_matrix.py</summary>

```python
"""C2 repro (a): with no Supabase matrix loaded, split strategies receive an
all-zero matrix and the response certificate still reports is_feasible=True."""
import os
import sys

os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
ROOT = os.path.abspath(os.environ.get("UNIRIDE_ROOT", os.getcwd()))
for p in (ROOT, os.path.join(ROOT, "optimizer_api")):
    if p not in sys.path:
        sys.path.insert(0, p)

from models.schemas import OptimizationRequest, LocationNode, StudentNode
from strategies.ga_split_strategy import GASplitStrategy
from strategies.ga_strategy import GeneticAlgorithmStrategy
from verification.response_certifier import certify_optimization_response
from utils.data_loader import DataLoader

print("repo health:", DataLoader.get_instance().health()["source"])
req = OptimizationRequest(
    algorithm="ga_split",
    depot=LocationNode(id="D", lat=41.00, lng=29.17),
    students=[StudentNode(id=f"S{i}", location_code=f"L{i}", disability_type="So",
                          coordinates={"lat": 41.00 + 0.2 * i, "lng": 29.17 + 0.2 * i}) for i in range(1, 6)],
    sw_capacity=4, so_capacity=5, max_travel_time=30,
    use_time_windows=True, target_time="08:30", direction="pickup",
)
for strat in (GASplitStrategy({"seed": 1, "population_size": 6, "max_iterations": 3}),
              GeneticAlgorithmStrategy({"seed": 1, "population_size": 6, "max_iterations": 3})):
    resp = strat.optimize(req)
    cert = certify_optimization_response(req, resp)
    print(strat.name, "success", resp.success, "total_duration", resp.total_duration_minutes,
          "steps", [[s.duration for s in r.route_details] for r in resp.routes],
          "cert", cert["is_feasible"], cert["violation_count"])
```
</details>

Observed:
```text
SUPABASE credentials not found. Using coordinate-based distance calculation.
repo health: coordinates
ga_split success True total_duration 0.0 steps [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]] cert True 0
genetic_algorithm success True total_duration 2.83 steps [[0.28, 0.28, 0.28, 0.57, 0.28, 1.13]] cert True 0
```

### H.3 — C2(b): OR-Tools rounding hides a violation of `max_travel_time`

<details>
<summary>repro_c2_ortools_rounding.py</summary>

```python
"""C2 repro (b): OR-Tools scales arcs by 10 and rounds; the response reports the
rounded step durations and the certificate (which trusts them) passes, while the
true route duration exceeds max_travel_time."""
import os
import sys

os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
ROOT = os.path.abspath(os.environ.get("UNIRIDE_ROOT", os.getcwd()))
for p in (ROOT, os.path.join(ROOT, "optimizer_api")):
    if p not in sys.path:
        sys.path.insert(0, p)


class DirectedLoader:
    """get_submatrix over a directed dict {from: {to: minutes}} keyed by physical codes."""

    def __init__(self, arcs):
        self.arcs = arcs

    def get_submatrix(self, request_locations, coordinates=None, geo_coords=False, asymmetric_haversine=False):
        n = len(request_locations)
        out = [[0.0] * n for _ in range(n)]
        for i, a in enumerate(request_locations):
            for j, b in enumerate(request_locations):
                if a != b:
                    out[i][j] = float(self.arcs[a][b])
        return out


def patch_loader(loader):
    import utils.data_loader as dl
    dl.DataLoader.get_instance = staticmethod(lambda: loader)
    try:
        import strategies.sota_response_builder as srb
        srb.DataLoader.get_instance = staticmethod(lambda: loader)
    except Exception:
        pass


codes = ["D", "L1", "L2", "L3", "L4", "L5"]
arcs = {a: {b: 10.04 for b in codes if b != a} for a in codes}
patch_loader(DirectedLoader(arcs))

from models.schemas import OptimizationRequest, LocationNode, StudentNode
from strategies.ortools_cvrp import ORToolsCVRPStrategy
from verification.response_certifier import certify_optimization_response

req = OptimizationRequest(
    algorithm="ortools_cvrp",
    depot=LocationNode(id="D", lat=0.0, lng=0.0),
    students=[StudentNode(id=f"S{i}", location_code=f"L{i}", disability_type="So",
                          coordinates={"lat": 0.01 * i, "lng": 0.0}) for i in range(1, 6)],
    sw_capacity=4, so_capacity=5, max_travel_time=60,
)
resp = ORToolsCVRPStrategy(time_limit_seconds=1).optimize(req)
cert = certify_optimization_response(req, resp)
print("success:", resp.success, "routes:", len(resp.routes))
for r in resp.routes:
    chain = [r.route_details[0].location1] + [s.location2 for s in r.route_details]
    true = sum(arcs[a][b] for a, b in zip(chain, chain[1:]))
    print(" chain", chain, "reported", r.total_duration_minutes,
          "step durations", [s.duration for s in r.route_details], "TRUE", round(true, 4),
          "max", req.max_travel_time)
print("certificate is_feasible:", cert["is_feasible"], cert["violations"])
```
</details>

Observed:
```text
success: True routes: 1
 chain ['D', 'L5', 'L4', 'L3', 'L2', 'L1', 'D'] reported 60.0 step durations [10.0, 10.0, 10.0, 10.0, 10.0, 10.0] TRUE 60.24 max 60
certificate is_feasible: True []
```

### H.4 — C2, H5 and H6: dual singletons, no recovery, stale bindings, event-loop blocking

<details>
<summary>repro_c2_h5_dual_singleton.py</summary>

```python
"""C2/H5/H6 repro (offline): dual DataLoader singletons, coordinate fallback
served as success, no recovery, bound-preview staleness, event-loop blocking.
SupabaseTimeMatrixProvider.fetch_rows is replaced by an in-memory fake BEFORE any
DataLoader is constructed; .env loading is disabled. Mimics the launcher."""
import os, sys, time, threading

ROOT = os.path.abspath(os.environ.get("UNIRIDE_ROOT", os.getcwd()))
API = os.path.join(ROOT, "optimizer_api")
os.environ.update({
    "PYTHON_DOTENV_DISABLED": "1",
    "SUPABASE_URL": "https://fake.invalid",   # provider constructed; fetch patched below
    "SUPABASE_SERVICE_ROLE_KEY": "dummy",
    "INTERNAL_API_KEY": "demo-key",
    "APP_ENV": "development",
    "TIME_MATRIX_CACHE_TTL_SECONDS": "3",
})
for k in ("UNIRIDE_DISABLE_AUTH", "UNIRIDE_TENANT_KEYS"):
    os.environ.pop(k, None)
os.chdir(API)
sys.path.insert(0, API)
if ROOT not in sys.path:
    sys.path.append(ROOT)   # lets `optimizer_api.*` resolve like the editable install

import utils.matrix_repository as flat_repo  # noqa: E402

CODES = ["D.Kampus", "Sw1", "So1", "So2", "So3"]
ROWS = [
    {"origin_code": a, "destination_code": b, "duration_minutes": 10 + i + j}
    for i, a in enumerate(CODES) for j, b in enumerate(CODES) if a != b
]
STATE = {"calls": 0, "fail_first": True, "sleep": 0.0}


def fake_fetch_rows(self):
    STATE["calls"] += 1
    if STATE["sleep"]:
        time.sleep(STATE["sleep"])
    if STATE["fail_first"] and STATE["calls"] == 1:
        raise RuntimeError("transient outage")
    return [dict(r) for r in ROWS]


def boom(*a, **k):
    raise AssertionError("network client must not be built in demo")


flat_repo.SupabaseTimeMatrixProvider.fetch_rows = fake_fetch_rows
flat_repo.SupabaseTimeMatrixProvider._build_client = boom

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

H = {"X-Internal-API-Key": "demo-key"}
STUDENTS = [
    {"id": f"s{i}", "location_code": c, "disability_type": "Sw" if c.startswith("Sw") else "So"}
    for i, c in enumerate(CODES[1:])
]
BASE = {
    "algorithm": "ga_split", "students": STUDENTS,
    "depot": {"id": "D.Kampus", "lat": 41.0, "lng": 29.1},
    "max_travel_time": 60, "ga_config": {"population_size": 10, "max_iterations": 5, "seed": 1},
}
SNAP = {"student_location_codes": [c for c in CODES[1:]]}


def show_opt(tag, r):
    d = r.json()
    cert = d.get("feasibility_certificate") or {}
    durs = [s["duration"] for rt in d.get("routes", []) for s in rt["route_details"]]
    print(f"{tag}: http={r.status_code} success={d.get('success')} total={d.get('total_duration_minutes')} "
          f"feasible={cert.get('is_feasible')} certify_error={cert.get('certify_error')} arc_durations={durs}")


with TestClient(main.app) as c:
    print("modules loaded:", "utils.data_loader" in sys.modules, "optimizer_api.utils.data_loader" in sys.modules)
    show_opt("1 unbound optimize (first load failed)", c.post("/api/v1/optimize", json=BASE, headers=H))
    r = c.post("/api/v1/internal/matrix-snapshot", json=SNAP, headers=H)
    sha = r.json().get("sha256")
    print("2 matrix-snapshot:", r.status_code, "sha256=", (sha or "")[:12])
    r = c.post("/api/v1/internal/readiness/time-matrix", json=SNAP, headers=H)
    print("3 readiness:", r.status_code, {k: r.json()[k] for k in ("source", "ready", "complete")})
    import utils.data_loader as flat_dl
    import optimizer_api.utils.data_loader as pkg_dl
    a, b = flat_dl.DataLoader.get_instance(), pkg_dl.DataLoader.get_instance()
    print("4 same singleton?", a is b, "| solver repo:", a.health()["source"], a.health()["loaded"],
          "| readiness repo:", b.health()["source"], b.health()["loaded"])
    time.sleep(3.5)  # past backoff/TTL (3 s)
    show_opt("5 unbound optimize after readiness recovered", c.post("/api/v1/optimize", json=BASE, headers=H))
    show_opt("6 bound optimize with fresh sha", c.post("/api/v1/optimize", json={**BASE, "expected_matrix_sha256": sha}, headers=H))

    import utils.patterns as pat
    pat.SingletonMeta._instances.clear()
    STATE["fail_first"] = False
    show_opt("7 unbound optimize (healthy load)", c.post("/api/v1/optimize", json=BASE, headers=H))
    time.sleep(3.5)  # solver repo passes TTL
    r = c.post("/api/v1/internal/matrix-snapshot", json=SNAP, headers=H)
    sha2 = r.json().get("sha256")
    print("8 matrix-snapshot (forced fresh):", r.status_code, (sha2 or "")[:12])
    show_opt("9 bound optimize right after fresh snapshot", c.post("/api/v1/optimize", json={**BASE, "expected_matrix_sha256": sha2}, headers=H))

    t0 = time.perf_counter(); c.get("/health"); base_ms = (time.perf_counter() - t0) * 1000
    STATE["sleep"] = 3.0
    th = threading.Thread(target=lambda: c.post("/api/v1/internal/matrix-snapshot", json=SNAP, headers=H))
    th.start(); time.sleep(0.3)
    t0 = time.perf_counter(); c.get("/health"); blocked_ms = (time.perf_counter() - t0) * 1000
    th.join(); STATE["sleep"] = 0.0
    print(f"10 /health latency: idle={base_ms:.0f} ms, during /matrix-snapshot provider fetch={blocked_ms:.0f} ms")
print("fetch calls:", STATE["calls"])
```
</details>

Observed:
```text
modules loaded: True True
1 unbound optimize (first load failed): http=200 success=True total=0.0 feasible=True certify_error=None arc_durations=[0.0, 0.0, 0.0, 0.0, 0.0]
2 matrix-snapshot: 200 sha256= 7cbc0add06c0
3 readiness: 200 {'source': 'supabase', 'ready': True, 'complete': True}
4 same singleton? False | solver repo: empty False | readiness repo: supabase True
5 unbound optimize after readiness recovered: http=200 success=True total=0.0 feasible=True certify_error=None arc_durations=[0.0, 0.0, 0.0, 0.0, 0.0]
6 bound optimize with fresh sha: http=200 success=False total=0.0 feasible=False certify_error=matrix snapshot unavailable or changed arc_durations=[]
7 unbound optimize (healthy load): http=200 success=True total=80.0 feasible=True certify_error=None arc_durations=[14.0, 14.0, 11.0, 14.0, 15.0, 12.0]
8 matrix-snapshot (forced fresh): 200 7cbc0add06c0
9 bound optimize right after fresh snapshot: http=200 success=False total=0.0 feasible=False certify_error=matrix snapshot unavailable or changed arc_durations=[]
10 /health latency: idle=14 ms, during /matrix-snapshot provider fetch=2703 ms
fetch calls: 7
```

### H.5 — C4: benchmark stop does not stop; slots are freed

<details>
<summary>repro_c4_benchmark_stop.py</summary>

```python
"""C4 repro (offline): /api/v1/benchmark/stop does not stop work and frees the
MAX_CONCURRENT_BENCHMARKS slot; benchmark params bypass the compute policy.
Writes a 12-node TSPLIB file next to this script (the default quick-runner path
does not write to any database). Uses a tenant key. Exits via os._exit."""
import os, sys, time, threading

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "tsplib_demo")
os.makedirs(DATA, exist_ok=True)
with open(os.path.join(DATA, "demo12.tsp"), "w", encoding="utf-8") as f:
    f.write("NAME : demo12\nTYPE : TSP\nDIMENSION : 12\nEDGE_WEIGHT_TYPE : EUC_2D\nNODE_COORD_SECTION\n")
    for i in range(12):
        f.write(f"{i+1} {(i*7)%40} {(i*13)%50}\n")
    f.write("EOF\n")

ROOT = os.path.abspath(os.environ.get("UNIRIDE_ROOT", os.getcwd()))
API = os.path.join(ROOT, "optimizer_api")
os.environ.update({
    "PYTHON_DOTENV_DISABLED": "1", "SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": "",
    "INTERNAL_API_KEY": "demo-key", "APP_ENV": "development", "TSPLIB_DATA_DIR": DATA,
    "UNIRIDE_TENANT_KEYS": '{"tenant-a": "tenant-a-key"}',
})
os.environ.pop("UNIRIDE_DISABLE_AUTH", None)
os.chdir(API)
sys.path.insert(0, API)
if ROOT not in sys.path:
    sys.path.append(ROOT)

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

H = {"X-Internal-API-Key": "tenant-a-key"}  # a tenant key, not the ops key
HEAVY = {"id": "ga", "params": {"population_size": 5000, "max_iterations": 100000,
                                "max_no_improvement": 100000}}


def start(c, rid):
    r = c.post("/api/v1/benchmark/run", headers=H,
               json={"run_id": rid, "algorithms": [HEAVY], "problems": ["demo12"], "settings": {"n_runs": 100}})
    return r.status_code, r.json().get("owner_token")


def alive():
    return sorted(t.name.replace("benchmark-executor-", "") for t in threading.enumerate()
                  if t.name.startswith("benchmark-executor-") and t.is_alive())


with TestClient(main.app) as c:
    tokens = {}
    for rid in ("A", "B", "C"):
        code, tokens[rid] = start(c, rid)
        print("start", rid, code)
    print("start D (cap=3):", start(c, "D")[0])
    for round_ in range(2):
        for rid in list(tokens):
            s = c.post(f"/api/v1/benchmark/stop?run_id={rid}", headers={**H, "X-Benchmark-Owner-Token": tokens[rid]})
            st = c.get(f"/api/v1/benchmark/status?run_id={rid}", headers={**H, "X-Benchmark-Owner-Token": tokens[rid]}).json()
            tokens.pop(rid)
            print(f"  stop {rid}: http={s.status_code} status={st['status']}")
        for i in range(3):
            rid = f"R{round_}{i}"
            code, tokens[rid] = start(c, rid)
            print("  start", rid, code)
        time.sleep(0.5)
        print(f"round {round_}: benchmark threads alive = {len(alive())}: {alive()}")
sys.stdout.flush()
os._exit(0)
```
</details>

Observed:
```text
start A 200
start B 200
start C 200
start D (cap=3): 429
  stop A: http=200 status=stopped
  stop B: http=200 status=stopped
  stop C: http=200 status=stopped
  start R00 200
  start R01 200
  start R02 200
round 0: benchmark threads alive = 6: ['A', 'B', 'C', 'R00', 'R01', 'R02']
  ...
round 1: benchmark threads alive = 9: ['A', 'B', 'C', 'R00', 'R01', 'R02', 'R10', 'R11', 'R12']
```

## Appendix I — Verification commands

### I.1 — Python canonical suites (isolated; never loads `optimizer_api/.env`)

```powershell
$env:PYTHON_DOTENV_DISABLED = "1"
$env:SUPABASE_URL = ""
$env:SUPABASE_SERVICE_ROLE_KEY = ""
.\.venv-jit\Scripts\python.exe -B -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q -p no:cacheprovider --tb=short
```
The system `python` on the audit machine (3.13) has no NumPy, Numba or FastAPI; use `.venv-jit` (3.14.3).

### I.2 — Canonical 3-opt regression (from `CANONICAL_THREE_OPT_DESIGN.md`)

```powershell
python -m pytest academic_benchmark/tests/test_numba_registry_matrix.py academic_benchmark/tests/test_numba_three_opt.py academic_benchmark/tests/test_core_tsp_registry.py uniride_core/tests/test_local_search_core.py uniride_core/tests/test_tsp_meta_engines.py -q -p no:cacheprovider --tb=short
```

### I.3 — Frontend

```powershell
npx vitest run
npx tsc --noEmit
npx eslint src/ --ext .ts,.tsx -f json -o <path-outside-repo>\eslint.json
```

### I.4 — Read-only Supabase checks

See C1 (policies and triggers), Q4 (fractional durations) and Q14 (location count). Never run DDL or DML without explicit owner authorization.

### I.5 — CodeGraph

```powershell
codegraph status                 # index health; "pending sync" right after a daemon restart can be a false positive
codegraph node <file-or-symbol>  # file with line numbers + dependents
codegraph callers <symbol> -l 30
codegraph impact <symbol>
```

## Appendix J — Remediation tracker and log

Update the Status, Branch/PR and Closing commit columns as fixes land (statuses: `OPEN`, `IN PROGRESS`, `FIXED`, `WITHDRAWN`). Do not edit the finding text above.

| ID | Severity | Short title | Roadmap | Status | Branch / PR | Closing commit | Evidence |
|---|---|---|---|---|---|---|---|
| C1 | Critical | Self-registration as admin (RLS insert / role trigger) | QW1 (steps 1-3; step 4: M21 FIXED in repo (fix/route-plans-rls-m21)) | FIXED (live, verified 2026-10-09) | `fix/qw1-users-role-rls` | red `b9a14bd`, green `d80b58a`, review fixes `ca85299` | `src/lib/supabase-auth.signup-role.test.ts` (4 tests), `src/lib/rls-role-lock-migration.test.ts` (9, static clause guard); `supabase/tests/20261009_role_lock.sql` (live-behaviour script, run by the owner on live 2026-10-09 (BEGIN…ROLLBACK, completed without error; no local Postgres)). Live DB 2026-10-09 was worse than the repo SQL: no `prevent_role_change` trigger, no `is_admin()`, `users_update_own` without WITH CHECK. See remediation log. Owner applied 20261009 migration 2026-10-09; lead verified live read-only: users_insert_self WITH CHECK role='student'; users_update_own WITH CHECK; trigger enforce_no_role_change BEFORE INSERT OR UPDATE OF role; prevent_role_change SECURITY INVOKER search_path=''; RPCs anon/authenticated EXECUTE revoked, service_role kept; ride_requests insert/update policies as designed; SQL test script ran to completion with no error; 0 leftover test rows. |
| C1.b | High (v1.1) | Students set any `ride_requests.status` | QW1 | FIXED (live, verified 2026-10-09) | `fix/qw1-users-role-rls` | red `b9a14bd`, green `d80b58a`, review fixes `ca85299` | Same migration; SQL script cases T5/T6. Owner applied 20261009 migration 2026-10-09; lead verified live read-only: users_insert_self WITH CHECK role='student'; users_update_own WITH CHECK; trigger enforce_no_role_change BEFORE INSERT OR UPDATE OF role; prevent_role_change SECURITY INVOKER search_path=''; RPCs anon/authenticated EXECUTE revoked, service_role kept; ride_requests insert/update policies as designed; SQL test script ran to completion with no error; 0 leftover test rows. |
| C1.c (2026-10-09, live) | High | `get_available_drivers()` and `get_route_plans_with_students(date, text)`: SECURITY DEFINER, no `search_path`, EXECUTE for `anon`/`authenticated`, bypass RLS (driver list with emails, all route plans) | QW1 | FIXED (live, verified 2026-10-09) | `fix/qw1-users-role-rls` | green `d80b58a`, review fixes `ca85299` | No caller in `src/` or `optimizer_api/` (grep, no `.rpc(` use); migration pins `search_path` and revokes from PUBLIC/anon/authenticated. SQL script case T7. Owner applied 20261009 migration 2026-10-09; lead verified live read-only: users_insert_self WITH CHECK role='student'; users_update_own WITH CHECK; trigger enforce_no_role_change BEFORE INSERT OR UPDATE OF role; prevent_role_change SECURITY INVOKER search_path=''; RPCs anon/authenticated EXECUTE revoked, service_role kept; ride_requests insert/update policies as designed; SQL test script ran to completion with no error; 0 leftover test rows. |
| C1.d (2026-10-09, live) | High | `route_plans` readable by anonymous users: policy "Drivers can read route_plans" is `SELECT USING (status IN ('confirmed','active','completed'))` with roles `{public}` and no auth check (table had 0 rows when found); the two admin `ALL` policies and the `admin_settings`/`routes`/`vehicles` select_all policies were also `{public}` | QW1 follow-up | FIXED (live, verified 2026-10-09) | `fix/route-plans-rls-m21` | red `003c095`, green `8f27fdb`, review polish `1833d27` | `supabase/migrations/20261010_route_plans_read_lock.sql`; `src/lib/rls-route-plans-lock-migration.test.ts` (static clause guard, red then green); `supabase/tests/20261010_route_plans_read_lock.sql` (BEGIN…ROLLBACK; anon, student, driver, admin cases; owner runs it after applying). Only reader is `/api/route-plans` (`requireAdmin` + service-role key); no student or driver JWT path reads the table. Owner applied 20261010 migration; lead verified live read-only: all policies on route_plans/sandbox_scenarios/admin_settings/routes/vehicles are TO authenticated; 0 public/anon policies; driver read requires role driver/admin and published status; admin ALL has USING and WITH CHECK; test script ran without error; 0 leftover rows. |
| C2 | Critical | Matrix fail-open + self-referential certificate | QW3 (QW3a + QW3b) | FIXED | `worktree-agent-a41a774c1c147fca0` (QW3a) and `worktree-agent-a0d1b474f7f820efe` (QW3b), integrated on the latter | QW3a `a2bc6b8`; QW3b `c6684f3`; integration merge `4f18378` and `6693a14` | Both halves below. Integrated behaviour: an unbound request captures its arcs from the stored matrix BEFORE solving and an unavailable matrix is a redacted 503 (422 for unknown codes) without a solve; a snapshot-bound request keeps the 200 "matrix snapshot unavailable or changed" response; the certificate re-costs on those captured (or snapshot) arcs. Not part of C2: response provenance (MT2). |
| C2 (repository) | Critical | Matrix fails open to zeros / coordinate values; failed first load never retried | QW3a | FIXED | `worktree-agent-a41a774c1c147fca0` (QW3a) | `a2bc6b8` | `optimizer_api/tests/test_c2_matrix_fail_closed.py` (red in `165004a`, green in `a2bc6b8`): H.2 (unbound zero matrix) now raises `MatrixUnavailableError` / redacted 503, H.4 (failed first load) retries after the backoff and recovers without a restart; opt-in flag `UNIRIDE_ALLOW_COORDINATE_FALLBACK`; production startup guard. HTTP re-run of Appendix H.4 (trimmed, offline): step 1 http=503 `travel-time matrix unavailable`, after the backoff http=200 with real arcs, unknown code http=422. Exact suite counts: see the remediation log. Response provenance (MT2) is not part of this row. |
| C2 (certifier + rounding) | Critical | Mechanism points 3 and 4: self-referential certificate; OR-Tools rounding | QW3b | FIXED | `worktree-agent-a0d1b474f7f820efe` (QW3b) | red `db3f8c2`, green `c6684f3`, `43311d8` (`arc_rounding`), `9e34a2f` (pre-solve arc capture); integrated with QW3a in the merge commit and its follow-up on that branch | `optimizer_api/tests/test_certifier_authoritative_matrix.py` and `test_certifier_arc_sources.py` (zero or off-matrix durations rejected, H.3 repro rejected, directed arcs, snapshot-bound endpoint test, fail-closed without a matrix, all 12 operational strategies certify on a real decimal directed repository); `uniride_core/tests/test_ortools_rounding_conservative.py`. Integrated suites (merge `4f18378` + `6693a14`): Python `uniride_core/tests optimizer_api/tests academic_benchmark/tests` 3588 passed, 1 skipped; full `npx vitest run` 47 files, 532 tests passed; `npx tsc --noEmit` clean. |
| M4 / MT2 (partial) | Medium | Matrix provenance in responses; paginated `time_matrix` fetch | MT2 | IN PROGRESS | `worktree-agent-acd00ef10524f7ea0` | see the remediation log | Done: optional `matrix_provenance` on `/optimize`, `/compare`, `/vehicle-calculator` (`optimizer_api/tests/test_matrix_provenance_pagination.py`); `.range()` paging, 2,500-row fake-client test. Staleness half: C2 fail-closed gate KEPT, age shown and `MATRIX_STALE` reason added, FIXED in repo (owner decision 2026-10-14; DECISION_LOG T09), branch `feat/m4-matrix-age-warning`, red `922b1fa`, green `a15f3cb`. Data-freshness display added 2026-10-15 (branch `feat/matrix-data-freshness`): provenance `data_updated_at` / `data_age_seconds` (max `time_matrix.updated_at`) and the daily-plan note "Travel times last updated: ... ago"; schema migration `20261015_time_matrix_updated_at.sql` pending application by the lead (the optimizer tolerates the missing column). Open: matrix domain enum, row-count check. |
| C2 follow-up: 15-minute defaults | Low | Unreachable `DEFAULT_TRAVEL_FALLBACK_MINUTES` in core split/scheduling helpers | | FIXED | `worktree-agent-acd00ef10524f7ea0` | see the remediation log | `uniride_core/tests/test_strict_arcs.py`: a missing arc raises `TravelTimeUnavailableError`. No academic or test path needed the default. |
| C2 follow-up: Clarke-Wright | Low | Clarke-Wright savings used one direction only | | FIXED | `worktree-agent-acd00ef10524f7ea0` | see the remediation log | `uniride_core/tests/test_clustering_matrix_strict.py::test_clarke_wright_directed_saving_beats_one_way_saving`. |
| C3 | Critical | `id()`-keyed local-search cache | QW6 | FIXED | `fix/c3-prebuilt-matrix` (merged 5cfe3df, 2026-10-09) | red `e8c259a`, green `c7ccc0c` | `uniride_core/tests/test_local_search_matrix_isolation.py` (4 tests; red 3 of 3 runs on `7b979bf`, green after the fix); Appendix H.1 rerun: `runs corrupted: 0 of 6`, clean-cache values identical to before the fix. See the remediation log. |
| C4 | Critical | Anonymous, unstoppable benchmark compute | QW2, QW4 | BFF half (QW2 minus H1) and backend half (QW4) FIXED in repo | `fix/qw2-benchmark-bff-auth` (merged in d2e5139) + `fix/qw4-benchmark-stop` | BFF red `b5b0bae`, green `dbca63a`; backend red `daccdf0`, green `939bf9d`, review round red `e363317`, green `fc059c3`; BFF review red `ceca001`, green `ae04696` | `src/app/api/benchmark/benchmark-auth.test.ts` (all 13 routes: 401/403), `src/services/benchmark-auth-header.test.ts`, the gate case in `src/app/page.render-contract.test.ts` and `page.admin-gate.test.tsx` (landing page mounts only for admins), `optimizer_api/tests/test_benchmark_stop_bounded.py`. Open: H8 (router mounted in production), no total-experiment cap, H1 deferred; ~~`ga_split_enhanced` / `ga_split_hf` ignore params and the per-run seed on the benchmark-runner path~~ RESOLVED 2026-10-09 by owner decision (branch `fix/ga-split-variants-params-seed`; DECISION_LOG A06): they now receive params and the per-run seed, the benchmark-runner path is in-memory only (0 tsplib.db rows on 2026-10-09), so the marking tool and `include_obsolete` reader filter guard only rows copied into tsplib.db and result files; pre-fix exports (downloaded JSON, browser copies, POST /import) cannot be marked automatically and must not be pooled; ~~admin benchmark page i18n keys missing~~ RESOLVED 2026-10-09 (branch `fix/admin-benchmark-i18n`: RED `65dfa76`, green `debd9d5`; 37 keys + rawResults param added in tr/en, guarded by `src/i18n/admin-benchmark-messages.test.ts`). |
| C5 | Critical | Dashboard significance claims | QW5 (C5 part) | FIXED in repo | `fix/c5-disable-dashboard-inference` | red `b117e56`, green `a75b1b8` | `academic_benchmark/tests/test_c5_dashboard_no_inference.py`. Tab disabled; Package D present (Gate D closed except D-12 at `04612880`; the dashboard statistics tab stays disabled, DECISION_LOG A18 OQ-11). See DECISION_LOG A09. |
| C5-F1 | Low | Descriptive superiority labels from pooled, unvalidated rows (dashboard.py:149, :169, :335, :357) | C5 review 2026-10-10 | FIXED in repo | `fix/c5f1-descriptive-labels` | red `21192ac`, green `6ed3eb9` | Owner decision 2026-10-15 (DECISION_LOG A15): 'Lower mean gap (descriptive)' / 'Descriptive LaTeX table (not validated for publication)'. Test `academic_benchmark/tests/test_c5f1_descriptive_labels.py`. Labels only. |
| H1 | High | Password-hint disclosure and enumeration | QW2 | DEFERRED (owner decision 2026-10-09, close before go-live) | | | Code untouched. See DECISION_LOG S06. |
| H2 | High | Return arc to school and waiting unchecked | MT1 | OPEN | | | |
| H3 | High | Uncertified `arrival_times` schedule | MT1 | OPEN | | | |
| H4 | High | Search ignores time windows | MT1 | OPEN | | | |
| H5 | High | Dual DataLoader singletons | QW3 (H5 part only; C2 stays open) | FIXED | `worktree-agent-a8fa6fced6451df76` (D1a) | `d672dc7` | `optimizer_api/tests/test_single_data_loader_root.py` (red in `b536600`, green in `d672dc7`); Appendix H.4 offline rerun: one `utils.data_loader` module, steps 4 (readiness DataLoader), 6 and 9 succeed; `optimizer_api/tests` 2101 passed |
| H6 | High | Event loop blocked by readiness | MT3 | async-handler half FIXED in repo; staleness half: fail-closed kept (C2 gate), age shown and `MATRIX_STALE` reason, FIXED in repo (owner decision 2026-10-14; T09) | `fix/h6-readiness-threadpool`; staleness half `feat/m4-matrix-age-warning` | red `c992171`, green `b9350d3`; staleness red `922b1fa`, green `a15f3cb` | `optimizer_api/tests/test_h6_readiness_event_loop.py` (2 tests: time-matrix and matrix-snapshot; a 1.5 s synchronous fake fetch, a concurrent `/health` must finish < 0.5 s late; red 2 of 2 on the old handlers). See the remediation log. |
| H7 | High | No global solver cap; `/compare` thread leak | MT3 | OPEN | | | |
| H8 | High | Academic runs and DB writes in the production process | MT4 | PARTIAL (router gated by UNIRIDE_ACADEMIC_PROCESS; MT4 storage/provenance part still open) | `fix/h8-academic-router-gate` | red `1c359163` (router), `48d6e15f` (BFF), `c4f3c105` (launcher); green `3e16a579`; launcher respects an explicit value in `optimizer_api/.env`: red `3e4b7a5d`, green `69b04245`; merge `20c7d436` | Owner decision 2026-10-19: environment switch instead of the full MT4 separation. `optimizer_api/main.py` imports and mounts `routers.benchmark` only when `UNIRIDE_ACADEMIC_PROCESS` is exactly `1` (read after `load_dotenv`); unset or any other value does not import `routers.benchmark`, the optimizer_api `benchmark_runner` or `benchmark_state`. Other academic code (`uniride_core.benchmark_runner`, `academic_benchmark.*`) still loads through the strategies and `promoted_config_loader` (H17). Tests: `optimizer_api/tests/test_h8_academic_router_gate.py` (subprocess; flag unset/`0`/`true`/`yes`/`2`/` 1` mount nothing, flag `1` mounts the routes, flag from `.env`), `src/app/api/benchmark/academic-disabled.test.ts` (11 BFF routes: optimizer 404 Not Found gives 503 `ACADEMIC_SERVICE_DISABLED`), `src/services/benchmark-service.test.ts`, `scripts/start-dudullu-local.test.mjs`. Local launcher `npm run dev:dudullu` sets the flag for the optimizer child; `.env.example` and README document it. Still open (MT4): ResultStore v2, gateway-only writes, protocol/provenance columns, reader filters, quick-runner retirement. Production launch command not found in the repository (audit Q15). |
| M2 (P1A-07) | Medium | Pickup windows built from `dropoff_time` (cross-direction fallback) | MT1-08 | FIXED in branch fix/mt1-08-window-direction (MT1-08, O09 OQ-MT1-14) | `fix/mt1-08-window-direction` | red `b5413708`; closing commit: lead | `optimizer_api/tests/test_mt1_08_window_direction.py` (9 tests; 7 red on WIP `5e8a8637`): `get_time_windows` uses `pickup_time` for PICKUP and `dropoff_time` for DROPOFF only; the implicit `target - 30 .. target` window for students without a time is deleted; `use_time_windows=true` without `target_time` is refused with 422 `use_time_windows requires target_time` on `/optimize` and `/compare` (`CompareRequest` gained an optional `target_time`). Tests that pinned the old behaviour updated in `test_cvrptw_phase1.py` and `test_scheduling_utils.py`. benchmark_runner CVRPTW rows refused with error_reason cvrptw_refused_h16_mt1_11 until MT1-11. |
| M5 (P2-07) | Medium | Benchmark router leaks internal errors | H8 branch | FIXED in repo | `fix/h8-academic-router-gate` | red `b76cd5d2`, download-case test fix `07973dd2`; green `3e16a579` | `optimizer_api/tests/test_m5_benchmark_error_leaks.py` (8 tests): `/academic/*` failures return fixed detail, the default `/run` worker failure status is a fixed message (`benchmark.py:371`, the audit's old `:314`; red `5c3274dc`, green `69b04245`), matrix-native worker failure status is a fixed message, `/download` returns `file_name` only (no absolute path), `/cli/preview` JSON error is fixed. L5 part: `/api/benchmark/run` no longer returns raw error text (`academic-disabled.test.ts`). Not changed: validation text in 422 `reason` (client input rules), BFF catch blocks in the other benchmark routes that pass `error.message` (their sources are the fixed `optimizerFetch` messages). |
| H9 | High | One ID → several implementations | MT4 (Gate C item C-14, owner Q10 option a) | FIXED (C-14 merged `ecf3c1c4`; routing-refusal follow-up merged `58f77d66`) | `feat/gatec-c14-one-id` | red `e7d9549f`, green `dfd4b409` | `optimizer_api/tests/test_c14_one_id_one_implementation.py` (52 tests across engine_factory, web matrix mode, AlgorithmRegistry and the CLI resolver): matrix engines are `Matrix-TwoOpt/GA/PSO/GWO/HHO-TSP-legacy`; `Core-*` IDs no longer resolve through the factory or the web matrix mode (HTTP 400); `AlgorithmRegistry.register` raises on a duplicate (5 silent overwrites removed); raw `Numba-GA`/`Numba-PSO` executors removed so the alias reaches only the canonical GA/PSO; canonical GWO/HHO import fails closed. Stored matrix-mode `algorithm` strings change: rows under old and new names are not pooled. Follow-up (owner decision 2026-10-21, branch `fix/gatec-core-ids-refuse-routing`, red `68cbb618`, green `5246896e`, tests `47ab4bc4`, cleanup `3560aaa7`; review round 1: red `f914e8d2`, green `91e98541`; merged `58f77d66`): every capability-catalog executor (15 IDs, read from the catalog; an import-time check refuses an unguarded one) refuses CVRP/CVRPTW on every path before any evaluation, in the registry wrapper and again inside each factory executor (`CoreRoutingRefusedError`, names the `CVRP-*`/`CVRPTW-*` alternative or says none exists); the `CVRP-*`/`CVRPTW-*` names are unchanged (for a fixed seed, 38 results on a tiny instance and 38 on a 25-node instance reproduce the pre-change engines). The eight alias names (`Core-GWO-TSP`, `Core-HHO-TSP`, `Numba-2-opt`, `Numba-3-opt-bounded`, `Numba-Or-opt`, `Numba-GWO`, `Numba-HHO`, `SOTA-ALNS-TSP`) no longer have an executor; `cli_engine` re-raises a failed registry import. Test: `academic_benchmark/tests/test_core_ids_refuse_routing.py`. Follow-up merged `e9f11e72` (owner decision 2026-10-23): `Numba-Swap`, `Numba-Hybrid` and `SOTA-E2BSO/R2DMA/P-AOEA/CGO/RUN-TSP` refuse CVRP/CVRPTW too; the greedy-router fallbacks are removed. Still open (owner questions): `FCM-*-TSP` still run Split-based FCM engines on routing problems; the `CVRP-/CVRPTW-Numba-Swap/-Hybrid` aliases run the legacy 2-opt matrix engine under misleading names. |
| H10 | High | Forbidden Numba 3-opt live in SOTA | MT6-02 | FIXED, merged `d0c73a8b` (Opus ONAY); SOTA final polish (`ls_engine.improve_3opt`) calls canonical `improve_three_opt` on every backend; old kernel kept but marked NON-CANONICAL and unreachable from public entry points (owner OQ-MT6-1 a); changes SOTA-E2BSO/R2DMA/P-AOEA and production `ebso`/`rdma`/`aoea` results, no pooling with earlier rows (A14, OQ-MT6-5 a); stored route plans carry no code commit (S08 fields only), so earlier rows are told apart by `route_plans.created_at` against the merge time (no hosted deployment exists yet); `run_tsp._apply_3opt_bounded` and `sota_common` `_layer_3opt` remained non-canonical by owner decision OQ-MT6-7 a; **update (MT6F-04, OQ-F2 b): the `run_tsp` part is FIXED, merged `86f19817` (Opus ONAY)**: `_apply_3opt_bounded` (duplicate case 4/5, missing reconnections, reversals on asymmetric matrices) is replaced by `_apply_random_cut_three_opt` (one admitted random cut, identity plus the canonical generator output, first minimum by `closed_tour_cost`); `SOTA-RUN-TSP` results may change (academic, ungoverned, no profile; no pooling of earlier RUN rows, A14); tests `uniride_core/tests/test_mt6f_run_three_opt_move.py` (MT6F-04 commits: red `58242045`, green `ab97b4ca`, golden `8037b8ee` (only `tsp:SOTA-RUN-TSP`, same cost and cycle, opposite orientation), review round 1 tests `e44fc014` (tie keeps the unchanged tour, solver passes the matrix mode) and window-before-n<6 fix `3b6f4674`); `sota_common` `_layer_3opt` is archived as REFERENCE_ONLY (MT6F-01, merged `80105327`; no `run_tsp` or `sota_common` 3-opt remains non-canonical on a public path) | `fix/mt6-02-sota-canonical-3opt` | red `7213a97c`, green `3b667b5c` | `uniride_core/tests/test_mt6_no_forbidden_three_opt.py` (71 tests: kernel spy through 4 solvers and the production adapter, equality with `improve_three_opt` sym/asym with and without Numba, permutation contract), `academic_benchmark/tests/test_mt6_sota_executors_no_forbidden_kernel.py` (3 executors). Restoring the old `ls_engine.py` makes 70 of 74 red again. |
| H11 | High | Wall-clock termination in SOTA TSP | MT6-03 | FIXED, merged `693d8fd2`; the six SOTA solvers (E2BSO, E2BSO-CPSO, R2DMA, P-AOEA, CGO, RUN) stop on iteration limits only, `MultiLayerLS.improve` has no clock check, the final polish always runs with its iteration limit, `time_limit`/`ls_time_limit` are replaced by opt-in `deadline_seconds=None` (`sota_tsp/deadline.py`; a hit deadline sets `extra_stats["termination_reason"]="wall_clock_deadline"` and `["reproducible"]=False`); production request key `time_limit` is mapped to `deadline_seconds` and `ls_time_limit` is accepted and ignored for one release (labelled in the policy `limits` metadata); no production default deadline is set (owner decides from the latency numbers, OQ-MT6-2 a); changes SOTA-* (academic, ungoverned) and production `ebso`/`rdma`/`aoea` results, no pooling with pre-MT6-03 rows (A14, OQ-MT6-5 a); ALNS not affected | `fix/mt6-03-sota-deterministic-stop` | red `fe4ef3a8` (+ window/max_iterations test `6f940a05`), green `48760640` + `069d795e` | `uniride_core/tests/test_mt6_sota_deterministic_stop.py` (66 tests after the MT6 review polish, 49 at merge: fake clock 10 s/call gives identical tour, cost, history for all six solvers; deadline hit/not hit/unset reporting; final polish after a hit deadline; AST test that in the five solver files and `ls_engine.py` every clock reading is only an elapsed-time measurement that feeds `elapsed*`/stats reporting, with no clock value or elapsed value reaching a comparison, `min`/`max`, `range`/`int` or other arithmetic; a second AST test that no clock is compared inline; solver-level fake-clock tests at N=60 so that each solver, including E2BSO, E2BSO-CPSO, R2DMA and P-AOEA, fails on its own when a per-layer clock check is added to `ls_engine`; a deadline passing in the last iteration still reports `iteration_limit`; the deadline stays soft: a run can overrun it by one iteration plus the final polish), `optimizer_api/tests/test_sota_legacy_clock_keys.py`, `test_package_b_native_runtime.py` (rewritten: the old "final polish never exceeds remaining budget" tests encoded the defect), `test_mt6_no_forbidden_three_opt.py::test_improve_3opt_honours_window_and_max_iterations`. Restoring the six old source files makes 48 of the 49 new tests red again. |
| H12 | High | Clustering uses global `random` | QW7 | FIXED in repo (owner approved 2026-10-15, knowing it changes results) | `fix/qw7-cluster-rng` | red `344d170`, green `af4d5a5` | `uniride_core/tests/test_h12_clustering_rng.py`, `optimizer_api/tests/test_h12_clustering_algorithm_allowlist.py`, `optimizer_api/tests/test_h12_clustering_concurrent_compare.py`, `academic_benchmark/tests/test_h12_no_global_reseeding.py`, review round 1: `uniride_core/tests/test_h12_clustering_rng_threading.py`, `optimizer_api/tests/test_h12_strategy_rng_threading.py` (reverting only kmeans/k_medoids/fuzzy_cmeans fails 18 tests; reverting only `schemas.py` fails 7; reverting the three academic files fails 2). MT6F-03 (2026-10-27, branch `fix/mt6f-03-dead-code`, merged `2174b160`): the legacy-primitive code in `clustering.py` that these round-1 tests pinned (`kmeans_clustering`, `split_cluster`, `initialize_centroids_kmeans_plus_plus`; section "(d) legacy primitives", 3 tests, in `test_h12_clustering_rng_threading.py`) was dead and is deleted together with those tests; the live k-means (`clustering_strategies/kmeans.py`) keeps its H12 threading tests. See the remediation log. |
| H13 | High | Governed CLI/Smart runs always fail; seed contract | MT5 | FIXED in repo (Gate C item C-03; merged `8a440397`) | `fix/gatec-c03-governed-runs` | red `65a0e320`, green `19002a9b`; DUZELT round 1 red `cda78023`, green `31a8cd67`; legacy-loop abort test `42c07eca` | `execute_preflighted(..., comparison_base_seed=...)` builds the v2 fixed-budget `FairComparisonManifest` (or `NativeComparisonManifest`) from the preflight decision, injects it into a copy of `params` and requires the contract seed (`SeedContractViolation` otherwise); Smart (`SMART_GOVERNED_BASE_SEED = 42`) and CLI (`CLI_GOVERNED_BASE_SEED = 1000`) derive governed seeds from `paired_seed(problem, replicate)`, so the parameter-combination index no longer enters; Smart persists `seed_group` and `comparison_base_seed` in the row metadata. Tests: `academic_benchmark/tests/test_c03_governed_runs.py` (16; 7 of the first 10 fail with the original fix reverted, the DUZELT B1 test fails with the B1 abort reverted and the legacy `run_benchmark` abort test fails with its `if governed_batch:` replaced by `if False:`, the non-governed seed pins `42 + run_idx` / `1000 + combo_idx*100 + run_idx` and the six-field tuple pass before and after). Non-governed (`NON_C1_ROUTING`) seeds unchanged. A governed Smart batch (`run_unified_benchmark`, `run_benchmark`) now aborts on ANY task exception, cancels the pending tasks, saves nothing and re-raises (DUZELT B1; test `test_governed_smart_batch_aborts_on_any_task_failure_and_saves_nothing`; non-governed batches still print and skip). Known limitation: governed fair ALNS needs explicit scientific parameters (`fairness.py` `ALNS_REQUIRED_PARAMS`, no defaults by design); the Smart `default` source supplies none, so such a batch aborts with `ALNS parameter schema mismatch` until the parameters are given (choosing defaults is a scientific decision, not made here). CLI `benchmark_results` rows now also carry `seed_group`, `seed_groups`, `comparison_base_seed` and `protocol_version` for governed runs. L9 seed-helper bullet: `benchmark_utils.make_deterministic_seed` removed (its only caller was a test of itself). L9 `pstdev` stays Package D, polish count C-10. Prior rows: governed runs WITHOUT a manifest failed closed, so no such row exists. A governed CLI run whose params already carried a user-supplied `fair_comparison` passed postflight before C-03 and `cli_engine` saves aggregate rows, so such rows may exist (evidence: the WIP tests `test_cli_aggregate_preserves_full_contract_for_every_replicate` with base_seed 91 and `test_bildiri2026_registry_executors_run_problem_dict_wrapper`); their seeds follow the user's manifest base seed, not the C-03 schedule, and they must not be pooled with post-C-03 rows (A13/A14). Such configs are now rejected with `ValueError` (`execution_gateway.py`: params already carry a comparison manifest). Code reasoning only; the DB was not queried. |
| H14 | High | Benchmark polling races and orphans | MT7 | OPEN | | | |
| H15 | High | Vehicle-planning Sw/So mapping | QW10 (H15 part) | FIXED in repo (owner decision 2026-10-13: fix the page and keep it, do not retire it) | `fix/h15-vehicle-planning-sw` | red `0f9eba9`, green `5650728` | `src/app/(app)/admin/vehicle-planning/page.test.tsx` ("counts a wheelchair user returned by the API as Sw, not So (H15)", snake_case fixture; fails with the page change reverted). Users API contract unchanged. |
| H16 | High | Solomon CVRPTW validated with school rules | MT1 | OPEN | | | |
| H17 | High | Production parameters from academic results | MT4 | PARTIAL: silent use FIXED in repo (default-off gate); the `academic_benchmark` import in `promoted_config_loader.py` remains (MT4) | `fix/h17-promoted-config-gate` | red `382bff1`, fix `2aec181`; P6 golden `f9b49a7`; DUZELT round 1: red `6573471`, fix `f0ee271`, docs `08fc73d`; DUZELT round 2: red `e3dcb33`, fix `302d804` (docs in the next commit) | `optimizer_api/tests/test_h17_promoted_config_gate.py`; DECISION_LOG A12 |
| H18 | High | Caller `distance_matrix` silently ignored | MT2 | OPEN | | | |
| H19 | High | TSPLIB quick-runner objective mismatch | MT4 | OPEN | | | |
| H20 | High | CI never runs the full suites or a production build | QW9 | FIXED in repo | `ci/h20-build-and-nightly` | 0a802bc | `npm run build` added to the frontend job; full Python suite runs nightly and on `workflow_dispatch` (`dependency audit` not added) |
| M26 | High (v1.1) | SOTA adapter objective mismatch and silent greedy fallback | QW11 | FIXED in repo (owner approved 2026-10-15: the response must say honestly which algorithm ran) | `fix/qw11-sota-adapter-truth` | red `17f957d`, green `45824a5`, web `4e3798e`, benchmark runner `c87a55a` | `uniride_core/tests/test_sota_tsp_strategy_adapter.py` (matrix parity, real E2BSO/R2DMA/P-AOEA reach the reported-duration optimum), `optimizer_api/tests/test_sota_adapter_truth.py` (forced solver failure is labelled `greedy_fallback`, no exception text, router does not relabel, compare excludes fallback from best/fastest); `src/services/optimizer-service.test.ts` |
| M8 (P3-07) | Medium | Possible stored XSS in the driver PDF export | QW8 | FIXED — escaping (`fix/web-input-hardening`) plus nonce-based production CSP and HSTS (`fix/qw8-csp-hsts`) | `fix/web-input-hardening`, `fix/qw8-csp-hsts` | red `ca1ac3c`, green `c254ff4`; CSP red `f647a71`, fix `4f897e4`, review round 1 on the same branch | `src/services/excel/driver-export-html.test.ts` (reverting only `driver-export.ts` fails 6 tests); `src/lib/security-headers.test.ts` + `src/proxy.test.ts` (reverting only `proxy.ts`/`next.config.ts` to the pre-fix version fails 8 of the 34 tests in `proxy.test.ts`, `next-config-headers.test.ts` and `security-headers.test.ts` (the last file passes because it is kept); the builder tests fail before `security-headers.ts` exists). Builder `src/lib/security-headers.ts`, per-request nonce in `src/proxy.ts`, HSTS in `next.config.ts` (`src/next-config-headers.test.ts`). Review round 1 added bearer-gate tests for `/api/benchmark` and invalid tokens (mutation-checked). Residual: `style-src 'unsafe-inline'` kept on purpose (React style attributes, Radix, recharts, landing `<style>`, print popup); HSTS `preload` not set (not decided). |
| M11 | Low (v1.1) | React build split between tests and production | MT7 | OPEN | | | |
| M20 | Low (v1.1) | Repeated evaluations: telemetry only | LT1 | OPEN | | | |
| M21 | Medium | RLS hygiene: drop-all loop in `rls_policies.sql` (QW1 step 4) | QW1 / MT8 | FIXED in repo (loop retired); `search_path` half already fixed by the 20261009 migration; single-source consolidation stays under MT8 | `fix/route-plans-rls-m21` | red `003c095`, green `8f27fdb`, review polish `1833d27` | `supabase/rls_policies.sql` is now a legacy reference: header, no `pg_policies` loop, an aborting guard inside `BEGIN … COMMIT`; static test in `src/lib/rls-route-plans-lock-migration.test.ts`. |
| M22 (promoted-config part) | Medium | `.env` loaded after router import; `UNIRIDE_PROMOTED_CONFIG_PATH` cached | MT4 | PARTIAL: promoted-config effect FIXED in repo (flag read at call time, default off; on the web benchmark runner the registry singletons are built at import before `.env` loads, so the flag must be in the process environment, not `.env`); `TSPLIB_DATA_DIR` import-time constant, import order in `main.py` and the python-dotenv pin are unchanged | `fix/h17-promoted-config-gate` | `2aec181` | Same tests; DECISION_LOG A12 |
| M17 | Medium | Archive quarantine hardening: `archive/` importable as a namespace package; generic boundary markers lack `archive.`; scans miss importlib strings and root/scripts files | MT5 (Gate C C-01) | FIXED in repo (merged `a3a5039e`) | `fix/gatec-c01-archive-namespace` | red `99564ce5`, green `20b5ed2c` (archive); skip-guard hardening red `07842d08`, green `5bc4cfde` | `archive/__init__.py` raises `ImportError` (pointer to QUARANTINE.md); `uniride_core/tests/test_archive_boundaries.py` (`test_archive_package_is_not_importable`, `test_import_offence_helper_rejects_the_archive_namespace_and_dynamic_imports`, `test_import_offence_helper_respects_component_boundaries`, `test_root_and_scripts_python_files_are_scanned`; scans now cover root and `scripts` files and `importlib.import_module`/`__import__` strings); `academic_benchmark/tests/test_yaem_quarantine_boundary.py` (`test_import_violation_helper_catches_dynamic_import_strings`, active scan widened to root and `scripts`); `academic_benchmark/tests/test_exact_published_tours.py` (`_has_problems_table`, read-only immutable open; `test_the_real_database_test_skips_on_an_empty_database_file`). Reverting the fix breaks those 5 new tests. No academic results change. |
| M18 | Medium | GWO/HHO executor rounds reported cost to 2 decimals; gateway rejects fractional matrices | MT5 / QW10 | FIXED in repo | `fix/m18-gwo-hho-unrounded-cost` | GWO/HHO red `84ca801`, green `ad3ce99`; follow-up 1 red `9813e5d`, green `9dce5a8`; follow-up 2 (DECISION_LOG A14) red `f7decdd`, green `bb1244a` | `academic_benchmark/tests/test_m18_gwo_hho_unrounded_cost.py` (6 tests; GWO/HHO executor, `registry_setup.py:711, 716`), `academic_benchmark/tests/test_m18_other_executors_unrounded_cost.py` (10 tests; `registry_setup.py:130, 135` core executor, `:167, 172` matrix executor, `:432` legacy time-matrix branch) and `academic_benchmark/tests/test_m18_followup_cli_and_truncation.py` (9 tests; `cli_engine.py:632-633` time-matrix rounding, `int()` truncation at `registry_setup.py:432` and `cli_engine.py:632-633`, `cli_engine.py:1458, 1467` 4-dp rows). Every site group is mutation-killed (reverting one group alone fails its own tests). The gateway tolerance is unchanged (1e-9). |
| M19 (ACAD-06) | Medium | `polish_policy` and the memetic-2opt label came from the `polish_enabled` boolean, not from executed polish; the Bildiri profile ran both memetic IDs with zero polish | MT5 / Gate C (C-04) | FIXED in repo (2026-10-20, review rounds 1 and 2 included; merged `6473cd91`) | `fix/gatec-c04-memetic-truth` | round 0: red `19a5c456`, green `dd3800f8`; round 1: red `c6d800a6`, green `7103197a` (B1, P1-P3); red `bc5475aa`, green `4c4b81fb` (B2); red `c660d5aa`, green `8aba194f` (owner budget-level decision); round 2: test-only hardening `d5788742` (sweep skips only the expected rejections; the call-count mutation now fails it) | `academic_benchmark/tests/test_memetic_polish_truthfulness.py` (27 tests). A phase flag is true only when that phase spent at least one polish candidate evaluation: the GWO/HHO solvers record `extra_stats["polish_evaluations"]` (fixed-budget mode; the `budget.used` delta of each `_polish` call minus the one evaluation that prices the start tour) and `polish_executed` (call counts, information only); `_executed_polish_policy` in `registry_setup.py` builds `polish_policy` (`enabled`, phase flags, `operator`, `executed`, `evaluations`); pure results keep the five-key shape. A memetic configuration with `polish_iters <= 0` and `final_polish_iters <= 0` raises `ValueError` before execution; a memetic run that spent no polish evaluation (for example a final polish called with the budget already exhausted) is rejected by the fairness validator. `fairness.py` (`_memetic_polish_count_errors`): memetic results must carry `executed` and `evaluations` as non-negative integer counts, each phase flag must equal `evaluations > 0`, a phase may not spend evaluations without a call, and polish evaluations may not exceed the objective evaluations. The native path has no evaluation counter, so its memetic polish accounting stays with C-10. Owner decision 2026-10-19: `bildiri2026/study.json` memetic entries use `polish_iters: 1, final_polish_iters: 1`; `fixed_budget_levels` rise from `[100, 500]` to `[10000, 50000]` (initial polish on ft53 needs 5516 evaluations for four individuals); all four entries use `max_iterations: 60000` and `max_no_improvement: 60000` so the pure variants spend the budget (with the default stagnation limit of 75 they stopped at 366 and 1513 evaluations). Pins refreshed with the new `study.json` hash: `fixtures/fixed_budget_tables_golden_v1.json` and `PINNED_LF_SHA256` in `test_exact_reference_boundaries.py`. **Smoke rows produced from the zero-polish Bildiri profile (`polish_iters: 0, final_polish_iters: 0`, levels 100/500) are not pooled with rows from the corrected profile.** Valid configurations show no cost change. |
| M7 (P3-06) (race half) | Medium | Drivers page: stale response overwrites newer date | per §5 | FIXED in repo for the race (2026-10-19); the anon-client RLS question (Q1) is untouched | `fix/small-frontend-audit` | red `1ff5b689`, green `4fd9cd3b` | `src/app/(app)/admin/drivers/page.test.tsx`. A request counter ignores stale responses. The `set-state-in-effect` suppression stays (eslint still reports it without it), with a corrected reason. |
| M10 (P3-09) (status half) | Medium | Password route returns provider text as HTTP 500 | per §5 | PARTIAL: status mapping FIXED in repo (2026-10-19); current-password / recent re-login requirement still OPEN (owner design decision) | `fix/small-frontend-audit` | red `1ff5b689`, green `4fd9cd3b` | `src/app/api/profile/password/route.test.ts`. Provider 400/422 map to 400, 401/404 to 401, 403 to 403, anything else to a fixed 500; AppError keeps its status; provider text goes to the server log only. |
| M25 | Medium | Canonical 3-opt dominated by duplicate-detection bookkeeping | MT6-01 | FIXED, merged `7c41237b` (Opus ONAY); speed-up with exact candidate parity, no academic result changes (evaluation counts, routes, costs unchanged); timing re-measure is MT6-06 | `fix/mt6-01-three-opt-speedup` | red `60698a28`, green `da0c2298`; NumPy-matrix wrapper tests `5361c6ad` | `uniride_core/tests/test_three_opt_candidate_parity.py` (frozen historical generator as fixture; exhaustive candidate parity n=6..16 x windows None/2/3/12 x sym/directed, 8736 route-triple pairs, plus seeded n=20..60; full-run parity of `improve_three_opt` and `improve_three_opt_budgeted`; call-count tests). Reverting `three_opt.py` makes the two call-count tests red; mutating the reconnection table makes the parity tests red. M25-d (duplicates never remove a candidate of an admitted cut) held in every case tested. |
| M14 (P1B-05) | Medium | The production hybrid 3-opt used a second, non-canonical neighbourhood (C'B' missing, first position never moved, window bounds off by one, 2-opt fallback under the 3-opt name, running-best instead of best-improvement) | MT6-04 | FIXED, merged `dfaadc2d` (Opus ONAY; Dudullu week 2026-10-05 replay shown to the owner first). Plan check closed: no academic `Matrix-*-legacy` configuration selects `hybrid` or `three_opt` (`uniride_core/algorithms/engine_factory.py:29-36` lists the five engines; no `local_search_type`, `"hybrid"` or `"three_opt"` string appears in non-test code under `academic_benchmark/`) | `fix/mt6-04-path-three-opt` | red `e0e4233f`, green `e3703039` | `uniride_core/tests/test_mt6_path_three_opt.py` (independent brute-force enumerator that does not import the generator: per-cut candidate set, C'B' generated, first position moves, no duplicates for one-node segments, fixed candidate order, window bound equal to the canonical rule, true best-improvement pass equals the reference best move, strict acceptance and call count, no 2-opt for short routes, hybrid keeps 15 / 12) and two tests in `uniride_core/tests/test_local_search_core.py`. Owner decision OQ-MT6-3 b: path 3-opt "reversals fully costed" in `three_opt.py` (design subsection "Path neighbourhood for production local search"); `_three_opt_cases` deleted; production only, no academic registry entry. Reverting `local_search.py` makes 62 of the 132 new tests red. Changes production `ga_split`, `ga_split_hf`, `gwo/hho/pso_split`, `pso_strategy`, `hho_strategy` results; no pooling of production benchmark rows across the change. |
| N-1 (MT6 plan, 2026-10-26; non-audit observation, not an audit finding) | Low | Budgeted 2-opt/Or-opt/3-opt controllers accepted with a strict `<`; `CANONICAL_THREE_OPT_DESIGN.md` asks for a scale-aware tolerance, which `improve_three_opt` already used | MT6-05 | FIXED, merged `9bd31aea` (Sonnet ONAY); owner decision OQ-MT6-6 b (align the code to the design) | `fix/mt6-05-budgeted-tolerance` | red `16ea6261`, green `908fee97`; MT6-01 polish: window validation red `ff67d0e3`, fix `82b218a4` | `uniride_core/tests/test_mt6_budgeted_tolerance.py`: below-tolerance improvements are not accepted by any of the three controllers (scales 1 and 1e6, first and best improvement; red on the old code, 12 failures), above-tolerance improvements are; evaluation counts unchanged; every Bildiri/YAEM study dataset (7 manifests, loaded from the committed `.tsp`/`.atsp` artifacts, integer valued) gives identical fixed-budget results (route hash, cost, evaluations, iterations, termination reason) before and after for the three controllers (golden captured on `a08920e1`, 42 cases). Float-matrix pilot rows are not pooled across this change. The rule lives in `three_opt.is_improving`, reused by `improve_three_opt`. |
| M1–M25 (others) | Medium | See §5 (M7 race half, M10 status half, M14 and M25 have rows above) | per §5 | OPEN | | | |
| L14 | Low | Launcher runs uvicorn with `reload=True` (Windows reload kills the stack) | per §6 | FIXED | `worktree-agent-a03c533784adb2997` | `7cef7ee` | `optimizer_api/tests/test_reload_env.py`; `scripts/start-dudullu-local.test.mjs` (`buildPythonEnv`, `startStack` env tests). Reload is now `UNIRIDE_API_RELOAD`-controlled (default on); the launcher sets `0` for the optimizer child unless the user set it. The "explicit app path" half of the §6 guidance is not done. |
| L4 | Low | `supabase-admin.ts` and `admin-auth.ts` did not `import "server-only"` | per §6 | FIXED (owner approved 2026-10-16) | `fix/l4-server-only` | red `89b31e4`, fix `0b2d8dc` | `src/lib/server-only-guard.test.ts` (reverting only the two `import "server-only"` lines fails both guard tests); seven route tests that load the real admin helpers now mock `server-only` |
| L1 | Low | Unused `@tanstack/react-query` dependency | per §6 | FIXED in repo (2026-10-19) | `fix/small-frontend-audit` | green `4fd9cd3b` | Removed from `package.json`; lockfile updated with `npm install --package-lock-only --ignore-scripts` (removes `@tanstack/react-query` and `query-core`). No test; checked by `tsc`, `vitest`, `next build`. |
| L5 | Low | Raw error text to clients | per §6 | FIXED in repo (2026-10-19): `admin-auth.ts` and `driver/assignments` on `fix/small-frontend-audit` (merge `c6ccc80f`); `benchmark/run` site on `fix/h8-academic-router-gate` (merge `20c7d436`) | `fix/small-frontend-audit` | red `1ff5b689`, green `4fd9cd3b` | `src/lib/admin-auth.handle-api-error.test.ts` and `src/app/api/driver/assignments/route.test.ts` (reverting the two sources fails 5 tests). Driver assignments now keeps AppError 401/403 and returns a fixed 500 for database errors too (GET and PUT). `api/benchmark/run` not touched. |
| L6 | Low | `proxy.ts` sets an unread `x-user-id` | per §6 | FIXED in repo (2026-10-19; header removed, double `getUser` round trip not addressed) | `fix/small-frontend-audit` | red `1ff5b689`, green `4fd9cd3b` | `src/proxy.test.ts` ("sets a CSP for a valid token and no longer forwards an unread x-user-id"). Repo-wide grep, including `optimizer_api`, found no reader. |
| L7 | Low | `admin/layout.tsx` redirects during render | per §6 | FIXED in repo (2026-10-19) | `fix/small-frontend-audit` | red `1ff5b689`, green `4fd9cd3b` | `src/app/(app)/admin/layout.test.tsx` (`renderToString` sees no `router.replace` call; the effect redirects once). |
| L15 | Low | Driver assignments/history do not cancel on user change | per §6 | FIXED in repo (2026-10-19) | `fix/small-frontend-audit` | red `1ff5b689`, green `4fd9cd3b` | `src/app/(app)/driver/assignments/page.test.tsx`, `src/app/(app)/driver/history/page.test.tsx` (a late response for the previous user is ignored). |
| M23 (extract-time-windows bug only) | Medium | `/extract-time-windows` always raised `AttributeError` (Pydantic entry passed to code that calls `entry.get`) | QW10 | PARTIAL (extract-time-windows bug fixed; auth/size limits and downloader open) | `fix/small-python-audit` | red `8043fdac`, fix `8057aaa3` | `optimizer_api/tests/test_extract_time_windows_endpoint.py` (3 tests: pickup, dropoff, empty day; reverting `8057aaa3` fails the pickup and dropoff tests). Fix: `routers/utils.py` passes `entry.model_dump()` and `direction.value`; the extractor keeps its dict contract. NOT changed: auth and size limits on the `utils` endpoints, the TSPLIB downloader (`tsplib_parser.py`) |
| L11 | Low | Core request adapter used `str(direction)` (`'TripDirection.PICKUP'`) | per §6 | FIXED | `fix/small-python-audit` | red `4d367269`, fix `88ed8117`; same pattern in `_student_demand` (DisabilityType): red `ea04d0ad`, fix `1a8165d1`; test relocation `2893dd83` | `uniride_core/tests/test_uniride_adapter_direction.py` (str-Enum, plain Enum, case/space-insensitive strings, DisabilityType-like enum) and `optimizer_api/tests/test_uniride_adapter_api_enums.py` (real `TripDirection`/`DisabilityType`); reverting `88ed8117` fails 5 core tests, reverting `1a8165d1` fails the disability test. Fix: `_normalize_direction` in `uniride_core/adapters/uniride_adapter.py` (`getattr(d, "value", d)`, strip, lower) |
| L2 | Low | The landing page called `/api/ai-advisor`, which has no route, so the advisor always showed an error | per §6 | FIXED in repo (2026-10-19), owner decision "remove" (do not build the route) | `fix/l2-remove-ai-advisor` | red `67cc0ac8`, fix `35a40db9`; catalog count update `bfd98b38` | `src/app/page.no-ai-advisor.test.ts` (4 tests: no source file names `/api/ai-advisor`, page has no advisor state/handler/keys, `page.benchmark.advisor` absent from en and tr; reverting `35a40db9` fails all 4, plus the key-count test in `src/i18n/benchmark-messages.test.ts`). Removed: advisor button, panel, footer chip, state, handler, fetch, unused imports, and the `page.benchmark.advisor` block in `messages/en.json` and `messages/tr.json`. |
| L8 | Low | The 2-opt/3-opt fixed-budget executor derived `termination_reason` from counters (`iterations >= max_iterations`) instead of reporting `search.termination_reason`, so a search that converged (`no_improving_move`) on its last permitted iteration was labelled `max_iterations` | Gate C C-02 | FIXED (2026-10-19; merged `a218f6ab`) | `fix/gatec-c02-termination-reason` | red `04a4a4e9`, fix `082102fd` | `academic_benchmark/tests/test_l8_termination_reason.py` (6 tests; reverting `082102fd` fails the 2 convergence-on-last-iteration tests). Or-opt and native executors already passed the solver's reason through. Costs, evaluation counts and iteration counts are unchanged (golden `test_fixed_budget_tables_unchanged.py` byte-identical, 86 tests in the C-02 acceptance set pass); only the `termination_reason` label can change. **Not pooled (A14 rule):** termination-reason tallies of fixed-budget local-search rows produced before `082102fd` and after it are not pooled; pre-fix `max_iterations` counts for 2-opt/3-opt can include converged runs. Costs and evaluation counts of such rows stay comparable. |
| L3, L9–L10, L12–L13 | Low | See §6 | per §6 | OPEN for L9 and L12–L13 only; **L3 and L10 are split out into the rows L3-a/c, L3-d, L3-e/i, L3-f/g/h and L10-a/b, L10-c, L10-d, L10-f below and no longer open here** (all FIXED and merged; exceptions: L3-b `run/status`/`run/stop` BFF routes moved to MT7 with H14, still OPEN there; L10-c `tsp_matrix_metaheuristics/*` deferred until after the paper campaign, A20 L5; L10-e closed earlier by MT6-05 `9bd31aea`; the backend-dependent `ls_engine` layers, OQ-F8, are a separate later plan) (L9: seed-helper bullet closed by Gate C item C-03, `make_deterministic_seed` removed, merge `8a440397`; polish-count bullet partly addressed by Gate C item C-10; the other L9 bullets stay open) | `feat/gatec-c10-native-memetic`, `feat/gatec-c10-r1` | red `a6cbb838`, `be30ca34`; green `4a91124e`, `84a8fca7`, `f6a1ce90`; merge `3b1bf168` | C-10: the GOVERNED native memetic polish of `Core-GWO-TSP-Memetic-2opt` and `Core-HHO-TSP-Memetic-2opt` is now counted (`count_polish`: budgeted Python 2-opt with an unlimited counter, as in fixed-budget mode), so native `objective_evaluations` and `polish_policy.evaluations` include every polish candidate. UNGOVERNED runs (no protocol manifest) keep the uncounted Numba polish, so their evaluation counts still leave the polish out; L9 therefore stays partly open for ungoverned use. Native memetic rows from before C-10 do not exist as governed rows (the validator rejected them), and counted-polish rows must not be pooled with ungoverned Numba-polish runs. Gate D item D-08a (branch `feat/gated-d08a-summary-guard`, merged `ea199c32`): L9 `pstdev` bullet CLOSED - the fixed-budget and native pilot aggregates now report the SAMPLE standard deviation (n-1, owner OQ-15 / DECISION_LOG A18) under the field `sample_sd_cost` (was `stddev_cost`, population SD; undefined for one run, written as empty/None instead of 0.0); results-changing for the reported SD only (pre-change pilot aggregates must not be pooled with post-change ones for SD). X4: `matrix_run_summary.summarize_benchmark_rows` now refuses rows of different protocol pooling groups, self-contradicting rows and labelled rows mixed with unlabelled ones (unlabelled matrix-native rows stay summarizable as one set). |
| L10-a/b (MT6F-05, 2026-10-27) | Low | Haversine stand-in: salted `hash()` factors and forced asymmetry (`geo_coords=True`) | per §6; plan `2026-10-27-mt6-followup-sota-common-shims-l3-l10.md` MT6F-05, DECISION_LOG A21 OQ-F3 a | FIXED, merged `c09ef75c` (L10-c/d merged `4e116030`, L10-f merged `0dd7e753`; L10-e closed by MT6-05 `9bd31aea`) | `fix/mt6f-05-haversine-stand-in` | red `2dd63b95`, green `e279c91d` | `optimizer_api/tests/test_mt6f_haversine_deterministic.py` (5 tests; two child processes with different `PYTHONHASHSEED` for the academic scope and the opt-in fallback: identical and symmetric matrices; the four asymmetry parameters are gone from the signatures); with the source files restored to `cf77d952` all 5 fail. `build_haversine_matrix` lost `asymmetric`/`asymmetry_range`, `get_submatrix` (repository and `DataLoader`) lost `asymmetric_haversine`, `DataLoader.build_haversine_matrix` lost the two pass-through parameters; `geo_coords=True` now gives the symmetric haversine stand-in. No active caller passed `geo_coords=True` (production strategies call `get_submatrix(ids, coords)`), so no production or study result changes. Test fakes of `get_submatrix` in five optimizer_api tests dropped the parameter. |
| L3-a, L3-c (MT6F-08, 2026-10-27) | Low | Frontend dead code: `vehicle-planning-page.tsx` never imported; unused sandbox scenario handlers `GET`/`PUT`/`DELETE` in `src/app/api/sandbox/route.ts` (JSONB double-encoded in `PUT`) and their caller module `src/services/sandbox-api.ts` (no importer) | per §6; plan `2026-10-27-mt6-followup-sota-common-shims-l3-l10.md` MT6F-08, DECISION_LOG A21 OQ-F6 b | FIXED, merged `530930f7`. **L3-b (`run/status`, `run/stop` BFF routes without a client) is MOVED to MT7 with H14** (still OPEN). | `fix/mt6f-08-frontend-dead-code` | red `9107f54e`, green `4eb37459` | `src/app/api/sandbox/dead-code-removal.test.ts` (3 tests: `vehicle-planning-page.tsx` and its test do not exist while the live `page.tsx` stays; `route.ts` exports only `POST`; `src/services/sandbox-api.ts` does not exist; all 3 fail on `257633e7`). Deleted: `vehicle-planning-page.tsx` and its test, `GET`/`PUT`/`DELETE` and the helpers only they used (`SaveScenarioRequest`, `getSupabaseAdmin` and `Database` imports), `src/services/sandbox-api.ts`. `POST` (live, `sandbox/page.tsx`) and `route.test.ts` kept. No database change: the `sandbox_scenarios` table and its RLS test stay. |
| L3-d (shim part of the collective L3 row above; MT6F-02, DECISION_LOG A21) | Low | The 20 `optimizer_api/utils` re-export shims | MT6F-02 | FIXED, merged `1f21fc29` (MT6F-02) | `fix/mt6f-02-utils-shims` | red `b8bdc298`; redirect `822eaaf5`; delete `645abfa6` | Correction to the audit text at `:1270` / `:1607`: four production modules (`routers/optimization.py`, `routers/utils.py`, `routers/benchmark.py`, `benchmark_runner.py`) still imported shims; they and every script/test import now use `uniride_core.algorithms.*` (same objects; `scheduling` is `route_scheduling`, `split_decoder` is `string_split_decoder`, `haversine` is `distance`, the `clustering` shim's `VehicleCalculator` is `vehicle_assignment`). The 11 shim files, the 9 `clustering_strategies` shims and the 3 compatibility tests (`test_core_utility_shims.py`, `test_clustering_compat.py`, `test_time_window_violation_tracker_compat.py`) are deleted; guard `optimizer_api/tests/test_mt6f_no_utils_shims.py` (AST scan plus `find_spec`). No result change. The other L3 bullets are merged in their own rows below: `sota_common` and `PenaltyManager` (L3-e/i, `80105327`), k-means duplicate, `_three_opt_*_numba` and `use_sota_engine` (L3-f/g/h, `2174b160`), front-end dead code (L3-a/c, `530930f7`); L3-b (`run/status`, `run/stop`) moved to MT7 with H14. |
| L3-e/L3-i (MT6F-01, 2026-10-27) | Low | Unused `sota_common` package (non-canonical `_layer_3opt`, wall-clock stops, unused `PenaltyManager`) and its re-export shims | per §6; plan `2026-10-27-mt6-followup-sota-common-shims-l3-l10.md` MT6F-01, DECISION_LOG A21 OQ-F1 a | FIXED, merged `80105327` (MT6F-01; MT6F-02, MT6F-03, MT6F-08 also merged) | `fix/mt6f-01-archive-sota-common` | red `6795b2f7`, green `bd1c1b12` + `b758d78d` | `uniride_core/tests/test_mt6f_sota_common_retired.py` (5 tests: `find_spec` is None for both package paths, both source folders are gone, an AST scan of `uniride_core`, `optimizer_api`, `academic_benchmark`, `scripts` and root `*.py` finds no import of a name containing `sota_common`, the new manifest verifies with the archive tool and every entry is `REFERENCE_ONLY`); restoring the two source folders from `6795b2f7` makes 3 of the 5 fail. `uniride_core/algorithms/sota_common` (9 files) moved with `archive_manifest quarantine` to `archive/uniride_core/sota_common_legacy/` (manifest 9 entries, all `REFERENCE_ONLY`, `QUARANTINE.md`, `.gitignore` allow rule added because `archive/*` is ignored, line-endings test list extended); the 9 shims in `optimizer_api/strategies/sota_common/` and the two compatibility tests were deleted; the false E2BSO docstring in `optimizer_api/strategies/ebso_strategy.py` now names `uniride_core/algorithms/sota_tsp/`. No solver imported the package, so no result changes. |
| L3-f, L3-g, L3-h (MT6F-03, 2026-10-27) | Low | Duplicate k-means in `uniride_core/algorithms/clustering.py` (`initialize_centroids_kmeans_plus_plus`, `kmeans_clustering`, `split_cluster`); unreferenced `local_search_numba._three_opt_cases_numba` / `_three_opt_improve_numba`; never-read request field `OptimizationRequest.use_sota_engine` | per §6; plan `2026-10-27-mt6-followup-sota-common-shims-l3-l10.md` MT6F-03, DECISION_LOG A21 | FIXED, merged `2174b160` (MT6F-03) | `fix/mt6f-03-dead-code` | red `1b65caf8`, delete `734a1ca2` | `uniride_core/tests/test_mt6f_dead_code_removed.py` (10 tests: the five removed names are gone from the modules and from `clustering.__all__`; the live helpers `Point`, `Cluster`, `calculate_centroid`, `resolve_rng`, `validate_cluster_capacity` stay), `optimizer_api/tests/test_mt6f_use_sota_engine_removed.py` (3 tests: the field is not in `model_fields`; a request still carrying `use_sota_engine: true` validates and the value is ignored); with the three source files restored to `da47a50b` 7 of the 13 tests fail (the live-helper and still-validates tests stay green). Deleted: `clustering.py:75-164`, `:171-174` and the three `__all__` entries (plus the then-unused `haversine_distance` import), `local_search_numba.py:294-449`, `schemas.py:282`. The live k-means is `clustering_strategies/kmeans.py`; the core decoder option `CVRPTWDecoder(use_sota_engine=...)` is untouched; `src/` never sends or reads the field (grep, 0 hits). `CANONICAL_THREE_OPT_DESIGN.md:97` now says the `local_search_numba` 3-opt copy was deleted and the `numba_accel` kernel stays unreachable (OQ-MT6-1 a). Tests that pinned only the removed code were deleted: the k-means cases in `uniride_core/tests/test_clustering_core.py` (the centroid/capacity test now builds its `Cluster` by hand), the two k-means cases and the `sample_points` fixture in `optimizer_api/tests/test_clustering_unit.py`, and section (d) "legacy primitives" (3 tests) of `uniride_core/tests/test_h12_clustering_rng_threading.py`. No result change (no live caller); the API field disappears from the OpenAPI page. The `sota_common` archive and `PenaltyManager` are closed by L3-e/i (`80105327`); L3-b is moved to MT7 with H14. |
| L10-c (MT6F-06, 2026-10-27; partial) | Low | `random.Random(None)` when no seed is given | per §6; plan `2026-10-27-mt6-followup-sota-common-shims-l3-l10.md` MT6F-06, DECISION_LOG A21 OQ-F4 a | FIXED, merged `4e116030` (two engines only; `tsp_matrix_metaheuristics/*` deferred until after the paper campaign, A20 L5; `fuzzy_cmeans_enhanced` already fixed by H12/QW7) | `fix/mt6f-06-seeds-random-order` | red `19f583bc`, green `d972f937` | `uniride_core/tests/test_mt6f_no_unseeded_rng.py` (10 tests: `random.Random` in the two engine modules is replaced by a recorder; `seed=None` never passes `None`, the argument is 42 and `result.seed` is 42 on every path of `FCMSplitMatrixEngine` (<=2 nodes, one cluster, cluster path with both generators) and of `TSPMetaMatrixEngine`; integer seeds (0, 7) pass through unchanged; two `seed=None` runs equal the `seed=42` run); with the four source files restored to the red commit 8 of the 10 tests fail. New `resolve_seed` / `DEFAULT_ENGINE_SEED` in `tsp_meta_matrix_engine.py` (`0` stays `0`), used at `tsp_meta_matrix_engine.py` (`optimize_permutation`) and `fcm_split_engine.py` (`optimize_permutation` and `_cluster_node_indices`). Every caller of the two engines passes an integer seed (registry executors from the experiment runner, `optimizer_api/routers/benchmark.py` (`run_one`, seed `settings.seed + run - 1`), `uniride_core/benchmark_runner.py:85`, `run_matrix_benchmark.py`, `run_fcm_srs_comparison.py`), so no pooled result changes; only direct `seed=None` calls become reproducible. |
| L10-d (MT6F-06, 2026-10-27) | Low | Dormant `use_random_order` / `self.rng = random.Random()` in `HybridLocalSearch` | same | FIXED, merged `4e116030` | `fix/mt6f-06-seeds-random-order` | red `19f583bc`, green `d972f937` | same test file (2 parametrised cases: neither `local_search.py` nor `local_search_numba.py` has the `use_random_order` parameter or a `rng` attribute; passing the argument raises `TypeError`). No caller set the argument (grep over code, tests, configs, `src/`; the only other hit is archived documentation). The then-unused `import random` was dropped from both modules. |
| L10-f (MT6F-07, 2026-10-27) | Low | `local_search_numba` 3-opt wrapper: duplicate location codes raise; fallback matrix `f([a,b]) - f([a])` carries depot terms that cancel only over a closed cycle | same; DECISION_LOG A21 OQ-F5 a | FIXED, merged `0dd7e753` (behaviour unchanged; contract documented and pinned) | `fix/mt6f-07-numba-wrapper-contract` | none (tests document existing behaviour; green before and after) | `uniride_core/tests/test_mt6f_numba_three_opt_contract.py` (5 tests; added to the canonical 3-opt regression command). Docstrings of `ThreeOptLocalSearch` and `_build_or_get_dist_matrix` state the contract. Only message change: `ThreeOptLocalSearch.improve` now raises `ValueError` naming the duplicated codes; before, the same input raised `3-opt route length must equal matrix dimension` from `improve_three_opt`. Mutation check: dropping `- duration_func([loc_i])` from the fallback fails the fallback test. Every active caller attaches a prebuilt matrix (`cli_engine.py:615`, `registry_setup.py:482, 504`, `numba_metaheuristics.py:348`). |
| N1 (2026-10-04) | Medium | Dropoff time-window path: phantom wait vs `max_ride_time`; fallback `error` flag ignored | MT1 | OPEN | | | See remediation log; demo unaffected (`use_time_windows=false`) |

### Codex review 2026-10-09

| ID | Severity | Short title | Source | Status | Branch / PR | Closing commit | Evidence |
|---|---|---|---|---|---|---|---|
| CX-01 | High | Fractional intervals falsely declared infeasible by fleet selection | Codex review 2026-10-09 | FIXED in repo | `fix/cx01-interval-precision` | red `b39faf5`, green `4ae3d57`, review round 1 `0160acb` + fix 0852f72, docs 078161c | `fleet-scenario-run.test.ts` (CX-01), `test_fleet_selection_endpoint.py::test_time_scale_*` and `test_omitted_or_null_cooldown_*`, `test_typed_day_selection.py::test_cx01_*`; DECISION_LOG H05 |
| CX-02 | High | Dashboard CSV ingestion bypasses the obsolete-result guard | Codex review 2026-10-09 | FIXED in repo | `fix/cx02-cx04-academic-guards` | fix `3e14915`, merge `10c1968` | `academic_benchmark/tests/test_cx02_dashboard_obsolete_csv.py`; DECISION_LOG A07 |
| CX-03 | High | One-type typed GA violated P4 (count-first inner objective on nonmetric matrices) | Codex review 2026-10-09 | FIXED in repo | `fix/cx03-typed-ga-parity` | red `5d2efae`, `2f0f66b`; green `11d2c38`, `c8762fe` | `uniride_core/tests/test_ga_split_typed_engine.py`: `test_p4_codex_nonmetric_counterexample`, `test_p4_half_set_quota_is_no_quota`, `test_unknown_minimize_type_raises_value_error`, `test_p4_random_nonmetric_matrices_one_type_equals_untyped`; DECISION_LOG H04 |
| CX-04 | Medium | Direct fairness manifests truncate a non-integer evaluation budget | Codex review 2026-10-09 | FIXED in repo | `fix/cx02-cx04-academic-guards` | fix `3e14915`, merge `10c1968` | `academic_benchmark/tests/test_cx04_fair_manifest_validation.py`; DECISION_LOG A08 |

### Daily plan follow-ups 2026-10-13

| ID | Severity | Short title | Source | Status | Branch / PR | Closing commit | Evidence |
|---|---|---|---|---|---|---|---|
| DP-1 | Medium | The daily plan turns every optimizer failure (HTTP 429, 5xx, timeout) into the generic `OPTIMIZATION_NOT_SUCCESSFUL` | Live check 2026-10-13 (`src/services/daily-plan-run.ts` serial /optimize loop; `optimizer_api/rate_limit.py:28-52`, `compute_policy.py:37-38`) | FIXED on branch | `fix/daily-plan-errors-readiness` | red `7b74ca3`, green `d86bf47` | `src/app/api/admin/dudullu-preview/route.test.ts` ("optimizer failure reasons (DP-1)"), `src/services/daily-plan-view.test.ts` (reason code copy); rate limit itself unchanged |
| F12 | Medium | Readiness reports "ready" while the plan fails with `FLEET_INVALID` (NULL `cooldown_minutes`) or `student_leg_decisions` is missing | `docs/DEMO_ROADMAP_2026-10-04.md` F12, live-verified | FIXED on branch (cooldown and decision table; the admin-account part of F12 is not covered) | `fix/daily-plan-errors-readiness` | red `05d62af`, green `e76ec5d` | `src/app/api/admin/dudullu-readiness/route.test.ts`, `src/services/dudullu-readiness.test.ts`, `src/services/dudullu-readiness-response.test.ts`, `src/i18n/dudullu-readiness-messages.test.ts`, `src/app/(app)/admin/readiness/page.test.tsx` |

### Remediation log

Append one entry per landed fix: date, agent or author, ID(s), branch/commit, tests added, and the suites run with their exact results.

- *(no landed fixes yet)*
- **C2 (repository part), 2026-10-05, QW3a, FIXED.** Branch `worktree-agent-a41a774c1c147fca0`; red tests `165004a`, fix `a2bc6b8`. Owner requirement 2026-10-05: all travel times come from the stored `time_matrix`; no haversine, Euclidean or zero stand-ins in operational paths.
  - `optimizer_api/utils/matrix_repository.py`: `_is_cache_stale` treats "never loaded with a provider" as stale (retried after the existing backoff); `get_submatrix` refreshes in every mode; with no authoritative matrix `get_submatrix` and `get_duration` raise the new `MatrixUnavailableError` (a `MatrixSnapshotError`); unknown codes keep raising `IncompleteTravelMatrixError` (now flagged `unknown_location` to choose 422 vs 503); the coordinate/haversine/Euclidean path exists only behind `UNIRIDE_ALLOW_COORDINATE_FALLBACK` (parsed in `optimizer_api/runtime_config.py`, default off) or the explicit `academic_coordinate_scope()` used by the legacy `/benchmark` runner for TSPLIB problems.
  - `runtime_config.validate_runtime_configuration`: `APP_ENV=production` without `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` is a `SystemExit`; the opt-in flag is also a `SystemExit` in production. Development starts without credentials and fails closed per request.
  - `uniride_core/algorithms/route_metrics.py`: `get_duration`/`calculate_route_duration` are strict by default and take `allow_coordinate_fallback` (default False); `BaseRoutingStrategy` passes the env opt-in.
  - `routers/optimization.py`: unbound `/optimize`, `/vehicle-calculator` and `/compare` return a redacted 503 (`travel-time matrix unavailable`) or 422 (`requested locations are missing from the travel-time matrix`); snapshot-bound requests keep the existing 200 binding failure.
  - Web BFF: `/api/optimize-route`, `/api/calculate-vehicles`, `/api/compare-algorithms` and `/api/sandbox` return 503/422 with a `code`; sandbox, compare and vehicle-planning pages show the message (`common.matrixUnavailable`, `common.matrixLocationsMissing` in `messages/{en,tr}.json`).
  - Tests added: `optimizer_api/tests/test_c2_matrix_fail_closed.py` (46), new cases in `uniride_core/tests/test_route_metrics.py`, `src/services/optimizer-service.test.ts`, `src/app/api/{optimize-route,calculate-vehicles,sandbox}/route.test.ts`. Tests that relied on the silent fallback now opt in explicitly (`test_all_strategies_smoke`, `test_api_hardening_phase0` b5 x3, `test_response_certifier::test_greedy_tsp_certificate_is_feasible`) or were updated for the new contract (`test_matrix_repository`, `test_route_metrics`, `test_phase0_auth_guard::test_g3_main_import_ok_with_key`, the `get_submatrix` fake in `test_split_strategy_core_delegation`).
  - Suites run (offline, `PYTHON_DOTENV_DISABLED=1`, blank Supabase credentials): `uniride_core/tests optimizer_api/tests academic_benchmark/tests` 3537 passed, 1 skipped (baseline before the change 3487 passed, 1 skipped); `npx vitest run` 47 files, 532 tests passed; `npx tsc --noEmit` clean; `git diff --check WIP` clean.
  - Not part of this entry: matrix provenance in responses (MT2); the certifier half is the next entry.
- **C2 (certifier + rounding), FIXED 2026-10-05, branch `worktree-agent-a0d1b474f7f820efe`, red `db3f8c2`, green `c6684f3`; `43311d8` (`arc_rounding`), `9e34a2f` (pre-solve arc capture).** `certify_optimization_response` now takes an injected `arc_lookup` and re-costs every step on the directed matrix (bound snapshot arcs, else the DataLoader repository); `arc_duration_mismatch` tolerance `0.005`; a missing lookup fails closed. OR-Tools scales arcs up and the limit down and reports true unscaled durations. Suites: Python 3523 passed, 1 skipped; vitest (`dudullu-preview`, `services`) 312 passed. Integrated with QW3a: the arc capture uses the public strict `TimeMatrixRepository.capture_arcs`/`arc` accessors (no private repository access) and never serves coordinate-derived values (not under `UNIRIDE_ALLOW_COORDINATE_FALLBACK`, not inside `academic_coordinate_scope()`); an unavailable matrix on an unbound request is a 503/422 before the solve. `certify_benchmark_response` does not use the lookup. For the legacy `/benchmark` runner see the review-fix entry below (its behaviour is NOT unchanged: the split strategies now use the coordinate metric).
- **C2 (integration of QW3a and QW3b), FIXED 2026-10-05, branch `worktree-agent-a0d1b474f7f820efe`, merge `4f18378`, follow-up `6693a14`.** Conflicts resolved in `routers/optimization.py` (imports) and this tracker. Behaviour: an unbound `/optimize` or `/compare` request captures its arcs through the new public strict `TimeMatrixRepository.capture_arcs`/`arc` accessors BEFORE solving; an unavailable matrix is the redacted 503 (422 for unknown codes) with no solve, even with `UNIRIDE_ALLOW_COORDINATE_FALLBACK` on and inside `academic_coordinate_scope()` (those never produce authoritative arcs); a snapshot-bound request keeps the 200 "matrix snapshot unavailable or changed" response and certifies on the snapshot arcs. `authoritative_arcs.py` no longer touches `_arc_value`, `_lock` or `_use_coordinates`. The legacy `/benchmark` runner certifies with `certify_benchmark_response` and keeps the OR-Tools `"nearest"` rounding in `academic_coordinate_scope()`, but see the review-fix entry below for the split-strategy change. Tests: `optimizer_api/tests/test_certifier_arc_sources.py` (503/422 before solving, bound 200, compare 503, accessors strict, academic scope). Suites: Python 3588 passed, 1 skipped; `npx vitest run` 532 passed; `npx tsc --noEmit` clean; diff whitespace check against WIP (excluding `tailwind.config.ts`) clean.
- **C2 review fixes (independent Opus review of the integrated branch), 2026-10-05, branch `worktree-agent-a0d1b474f7f820efe`, commit `0a6746f`; suites: Python 3613 passed, 1 skipped; `npx vitest run` 48 files, 535 tests passed; `npx tsc --noEmit` clean.**
  - Legacy `/benchmark` runner parity (earlier claim "unaffected" was wrong). (a) `ortools_cvrp` now passes `arc_rounding="nearest"` inside `academic_coordinate_scope()` (new public `in_academic_coordinate_scope()`), `"conservative"` otherwise; pinned in `optimizer_api/tests/test_academic_scope_parity.py`. (b) INTENDED CORRECTION, kept: `ga_split`, `pso_split`, `gwo_split`, `hho_split` called `get_submatrix` without coordinates, so on WIP they optimized on an all-zero matrix (the C2 defect itself); inside the scope they now optimize on the coordinate metric. Reviewer measurement on tiny12 EUC, seed 42: `ga_split` 556 -> 264; `pso_split`, `gwo_split` and `hho_split` 468 -> 264 (WIP -> now). Legacy-runner results for these four algorithms produced before this change are not comparable with new ones. Pinned by `test_split_strategies_inside_the_scope_use_the_coordinate_metric_not_zeros`. (c) SECOND INTENDED CORRECTION, kept: every clustering strategy now receives the request's depot, so `sweep` pivots around the real depot instead of the hard-coded (41.001, 29.177): a no-op for the Dudullu depot, a correction for any other. Legacy `/benchmark` cluster-first results (`ga`, `pso`, `gwo`, `hho`, `two_opt`, `permutation_tsp`) are not comparable with earlier ones; measured on tiny12 EUC, seed 42: `two_opt` 276 -> 274. Pinned by `test_sweep_pivots_around_the_passed_depot`. The `academic_benchmark` package itself is untouched: it does not use the repository or `route_metrics`, and its OR-Tools callers keep `"nearest"`.
  - Owner requirement "all operational travel times from `time_matrix`": the cluster-first strategies (`ga`, `pso`, `gwo`, `hho`, `two_opt`, `permutation_tsp`) now pass the authoritative directed matrix (physical codes, depot included) to `VehicleCalculator.calculate`; `k_medoids` and `clarke_wright` use only matrix values and raise `MissingTravelTimeError` for a missing pair (haversine fallback removed; no caller relied on it). Tests: `uniride_core/tests/test_clustering_matrix_strict.py`, `optimizer_api/tests/test_operational_clustering_matrix.py`. Also fixed: the Clarke-Wright depot point had no `location_code`, so every depot arc fell back to haversine.
  - Docs: `CURRENT_ARCHITECTURE.md` open-items cell rewritten; `UNIRIDE_ALLOW_COORDINATE_FALLBACK` described as affecting only direct strategy/repository calls in `README.md`, `.env.example`, `optimizer_api/README_TESTS.md`; provider fetch under the repository lock noted; `vehicle-planning-page.tsx` uses `common.matrixUnavailable` / `common.matrixLocationsMissing` (test `vehicle-planning-page.test.tsx`); `test_response_certifier.py` uses `academic_coordinate_scope()`.
  - Documented follow-ups, still open: Clarke-Wright savings use only the listed-direction arc `t(i, j)` (not symmetrized); PyVRP time scaling (`pyvrp_cvrp_engine.py`, same nearest-integer rounding class as the OR-Tools issue) and the OR-Tools time-window bound rounding (`ortools_cvrp_engine.py`, windows rounded to nearest; the certificate still judges windows on true arcs).
- **C2 follow-ups and MT2 (partial), 2026-10-05, branch `worktree-agent-acd00ef10524f7ea0`.** (1) Provenance: optional `matrix_provenance` (source, sha256, location_count, loaded_at, age_seconds) on `/optimize`, `/compare`, `/vehicle-calculator`, taken from the arcs or snapshot the request was solved and certified with; `SupabaseTimeMatrixProvider` pages with `.range()` (1000 rows) until a short page (M4 truncation closed). Still open: matrix domain enum, maximum staleness, row-count check. (2) The 15-minute defaults in `ga_split_engine.py`, `meta_split_common.py`, `string_split_decoder.py` and `route_scheduling.py` are removed (the unused `optimizer_api/utils/constants.py` is deleted); missing arcs raise `TravelTimeUnavailableError` via `route_metrics.strict_arc`; `route_metrics.get_duration(strict=False)` stays as the explicit non-default escape hatch. (3) Clarke-Wright: the saving is now `S(i -> j) = c(i, D) + c(D, j) - c(i, j)` over ordered pairs with tail-to-head merges (closed tours on a directed matrix). The earlier "Clarke-Wright savings use only the listed-direction arc" follow-up in the C2 integration entry is closed by this.
- **N1 (2026-10-04), OPEN, found in the independent review of R1 (`max_ride_time`); not fixed.** In the dropoff time-window path the split decoder departs at `min(target_time, earliest window)` (`uniride_core/algorithms/string_split_decoder.py`, dropoff branch of `_build_trips_with_tw`, `_get_target_departure_time`), while the published schedule departs at the earliest window without waiting (`uniride_core/algorithms/route_scheduling.py`, ~lines 67-81). The decoder therefore simulates a wait that the published schedule does not contain, and that phantom wait can trip the ride limit and push students into single-vehicle fallback routes. Separately, `GASplitStrategy` ignores the fallback's `"error": "No feasible splitting found"` flag and returns `success=True`. Reviewer repro: 3 students, dropoff, time windows, target 16:00, `max_ride_time=45` gives 3 vehicles although a single vehicle's longest ride would be 42 minutes. The demo preview is unaffected (`use_time_windows=false`). Belongs with the MT1 time-window unification (one simulator per profile, H2-H4).

- **C3 (`id()`-keyed local-search cache), 2026-10-09, FIXED on branch, Claude Opus 5.5.** Branch `fix/c3-prebuilt-matrix` (from `WIP` `7b979bf`; merged into WIP as 5cfe3df (2026-10-09)); red test `e8c259a`, fix `c7ccc0c`. Re-verified against live code first: H.1 on `7b979bf` reproduced the finding exactly (`runs corrupted: 4 of 6`).
  - `uniride_core/algorithms/local_search_numba.py`: `_build_or_get_dist_matrix` now uses the matrix attached by `create_np_duration_func` (`_np_dist_matrix`/`_np_unique_locs`) BEFORE any cache and never caches it. All live callers (`registry_setup.py` Numba-* and Core-*-TSP legacy executor, `cli_engine.run_single_test_with_matrix`, `numba_metaheuristics.run_single_test` including the memetic 2-opt) already build their duration function that way, so they needed no code change. The id()-keyed `_DIST_MATRIX_CACHE` is replaced by a `weakref.WeakKeyDictionary` (`duration_func` -> `{frozenset(locations): result}`) used only when no prebuilt matrix exists; a function that cannot be weakly referenced is not cached. No second global cache. Re-ordering a prebuilt matrix to the route's order is now a numpy index (same values as the old loop). The docstring that claimed different problems never share a matrix is rewritten.
  - `academic_benchmark/cli_engine.py`: only a stale docstring about the cache was corrected. The governed fair/native branches (`registry_setup.py:345-365`) are unchanged.
  - Test added: `uniride_core/tests/test_local_search_matrix_isolation.py` (2-opt, Or-opt, canonical 3-opt with the prebuilt matrix; plain duration function on the fallback path). It solves three same-size different problems in a loop with `gc.collect()` between runs, checks the matrix the search kernel receives against the run's own problem matrix, and compares the tour with a run that keeps every duration function alive. Red 3 of 3 runs (4 failed each) on `7b979bf`; 4 passed after the fix.
  - Appendix H.1 (`runs corrupted: 0 of 6`): shared-process equals clean-cache on every row; clean-cache values unchanged by the fix (6595.6, 6564.6, 6744.7, 6399.4, 6413.1, 6623.0).
  - Suites run: the `CANONICAL_THREE_OPT_DESIGN.md` regression command plus the new module, 52 passed; other tests importing the touched modules (20 files under `academic_benchmark/tests`, `uniride_core/tests`, `optimizer_api/tests/test_seed_contract.py`), 345 passed. The full Python suite was not re-run.
  - Existing results from the unmanifested `Numba-*` / `Core-*-TSP` paths over several same-size instances stay suspect until rerun (LT1); decide per result provenance (Q17). Evaluation counts and the fairness contract are untouched.

- **C1, C1.b, C1.c (live SECURITY DEFINER), 2026-10-09, QW1, FIXED (live, verified 2026-10-09).** Branch `fix/qw1-users-role-rls`; red tests `b9a14bd`, fix `d80b58a`, review fixes `ca85299`. Live state read by the lead on 2026-10-09: `users_insert_self` without a role check, `users_update_own` without WITH CHECK, no `prevent_role_change` trigger and no `is_admin()` (so any authenticated user could set their own role to `admin`); `ride_requests` status/vehicle unrestricted on own rows; the two RPCs executable by `anon`.
  - `supabase/migrations/20261009_lock_user_role_and_ride_status.sql` (idempotent, no `is_admin` dependency): users insert limited to `role='student'`, update with WITH CHECK, `prevent_role_change()` (SECURITY INVOKER, `search_path=''`) on `BEFORE INSERT OR UPDATE OF role`, service_role exempt; ride_requests insert limited to `pending_admin_approval`/`pending_student_confirmation` with no vehicle or actual times, update only on own pending/confirmed rows and only to `cancelled_by_student` with vehicle/actual times still NULL; stray INSERT/UPDATE policies on both tables are dropped first; `search_path` pinned and EXECUTE revoked from PUBLIC/anon/authenticated on the two RPCs (service_role granted).
  - `src/lib/supabase-auth.ts`: `signUp` lost its `role` parameter (always `'student'`); `register` no longer accepts a role; `register-form.tsx` no longer sends one. `supabase/rls_policies.sql` was kept in step (its drop-all loop, M21, is left in place).
  - 2026-10-09: migration applied to live by the owner and verified by the lead (read-only).
  - Done 2026-10-09: the migration is applied (owner) and verified live (lead). Also done: M21 step 4 (drop-all loop in `rls_policies.sql`) FIXED in repo (fix/route-plans-rls-m21). Not done: the BFF still has no server-side registration route (the `users` row is still created from the browser, now constrained to student); `password_hint`/H1 untouched.
- **C1.d and M21, 2026-10-09, FIXED in repo, applied 2026-10-09.** Branch `fix/route-plans-rls-m21`. Live state read by the lead: `route_plans` "Drivers can read route_plans" had roles `{public}` and no auth check, so the anon key could read published plans (0 rows at the time); admin `ALL` policies on `route_plans`/`sandbox_scenarios` and the select_all policies on `admin_settings`/`routes`/`vehicles` were `{public}` too.
  - `supabase/migrations/20261010_route_plans_read_lock.sql`: published-plan read restricted to `authenticated` users whose `users.role` is driver or admin; admin `ALL` policies `TO authenticated` with WITH CHECK; select_all policies `TO authenticated` (same qual); final guard aborts if any policy on the five tables still applies to public/anon. `supabase/rls_policies.sql`: drop-all loop removed, file marked legacy and made to abort when run (M21).
  - Owner steps: apply the migration (paste the whole file and press Run; do not use Run selected), then run `supabase/tests/20261010_route_plans_read_lock.sql`, then re-read `pg_policies` for the five tables.
  - 2026-10-09: migration 20261010 applied to live by the owner and verified by the lead (read-only).
  - H1 is deferred by the owner until go-live; see DECISION_LOG S06.
- **CX-03, 2026-10-09, FIXED in repo.** Branch `fix/cx03-typed-ga-parity`; red `5d2efae` and `2f0f66b`, green `11d2c38` and `c8762fe`. `solve_ga_split_typed` decodes cost-only (no `minimize_type`) for one type and no quota (`quota_type` or `quota` unset), restoring parity gate P4 on nonmetric matrices; two or more types or a quota keep the count-first inner objective; an unknown `minimize_type` raises `ValueError`. Tests: Codex fixture, half-set quota, unknown type, 50 seeded nonmetric cases in 4 variants (pickup/dropoff, R set/None) in `test_ga_split_typed_engine.py`; WP0 goldens green. Suite after the WIP merge (e275ad5): `uniride_core/tests optimizer_api/tests academic_benchmark/tests` 4079 passed, 4 skipped. Decision H04.
- **CX-01 (fleet-selection interval precision), 2026-10-09, FIXED on branch, Claude Opus 5.5.** Branch `fix/cx01-interval-precision`; red `b39faf5`, green `4ae3d57`, review round 1 red `0160acb`. The selection request carries `time_scale` (default 1; the producer sends 100): interval endpoints and cooldowns are integer centi-minutes, `minutes` stays real; endpoints off the 0.01 grid are refused (`blocked_data` / `SELECTION_INTERVAL_PRECISION`), never rounded. No DB constraint or matrix-ingest check was added (open; left for an owner decision). Archive unaffected (all inputs whole minutes). Tests: core pin, endpoint `time_scale`/bounds/default-cooldown, TS exact-intervals, off-grid endpoint and cooldown. Decision H05.
- **CX-02 and CX-04, 2026-10-09, FIXED in repo.** Branch `fix/cx02-cx04-academic-guards`; fix `3e14915`, merge `10c1968` (Opus review approved). Polish branch `fix/cx0204-polish`: tuning/history CSV paths now use the same obsolete filter (A07), empty `metadata` column falls back to `metadata_json`, paired-seed test pinned to the pre-fix literal 583917059. Tests: `academic_benchmark/tests/test_cx02_dashboard_obsolete_csv.py`, `test_cx04_fair_manifest_validation.py`. Opus review of 3e14915 reported 4074 passed, 4 skipped (not re-run for this polish; academic_benchmark/tests alone: 966 passed, 3 skipped at f22d856). Decisions A07, A08.
- **C5 (dashboard significance claims), 2026-10-10, FIXED in repo, Claude Opus 5.5.** Branch `fix/c5-disable-dashboard-inference`; red `b117e56`, green `a75b1b8`. `academic_benchmark/dashboard.py`: the Wilcoxon tab body (scipy import, per-problem tests, "Significant?"/"Winner" columns, the LaTeX "significantly outperforms" sentence and table) is removed; the tab is retitled "Statistical tests (disabled)" and shows an informational message pointing to the Package D analysis service. Test `academic_benchmark/tests/test_c5_dashboard_no_inference.py` (stub streamlit, tab body run by AST; asserts no inferential wording, no scipy test call, neutral tab labels). Descriptive tables untouched. Package D statistics remain unimplemented. DECISION_LOG A09. Descriptive 'best'/'Better' labels in the Leaderboard and Algorithm Comparison tabs (dashboard.py:149, :169, :335, :357) remain and are tracked separately as C5-F1 (OPEN, owner decision).
- **DP-1 and F12 (daily plan follow-ups), 2026-10-13, FIXED on branch, Claude Opus 5.5.** Branch `fix/daily-plan-errors-readiness`; DP-1 red `7b74ca3`, green `d86bf47`; F12 red `05d62af`, green `e76ec5d`. DP-1: `runDailyPlan` now reads the /optimize status and `Retry-After` before failing. HTTP 429 gives `OPTIMIZER_RATE_LIMITED` (optional `retryAfterSeconds` in the response, numeric header only), a 503 with the fixed detail "travel-time matrix unavailable" gives the existing `MATRIX_UNAVAILABLE`, other 5xx and timeouts or network errors give `OPTIMIZER_UNAVAILABLE`; other 4xx keep `OPTIMIZATION_NOT_SUCCESSFUL`. Codes added to `PreviewReasonCode` and `KNOWN_REASON_CODES`, with tr/en copy under `page.admin.dailyPlan.reasons`. The rate limit and the success path are unchanged; the serial 13+ calls per run against the 30-per-60-s limit remain (a third run within a minute now shows the rate-limit message instead of a misleading one). F12: the readiness route selects `cooldown_minutes` and applies the plan's predicate (shared `isValidCooldownMinutes`, whole number and at least 0) to active vehicles (`vehicle_cooldown_invalid`, `fleet.invalidCooldownActiveVehicles`), and probes `student_leg_decisions` with a non-mutating `select("user_id").limit(1)` (missing relation `42P01` or `PGRST205` gives `leg_decisions_unavailable`; any other probe error fails closed with the existing 503). Both are shown on the readiness page with tr/en copy. Not covered: the admin-account check named in F12; readiness still accepts a non-integer capacity that the plan rejects.

- **H6 (async readiness handlers block the event loop), 2026-10-14, async-handler half FIXED on branch, Claude Opus 5.5.** Branch `fix/h6-readiness-threadpool` (from `WIP` `35fba5c`); red test `c992171`, fix `b9350d3`. Re-verified against live code: `time_matrix_readiness` and `matrix_snapshot` in `optimizer_api/routers/readiness.py` called `loader.refresh(...)` and the repository read on the event-loop thread.
  - `optimizer_api/routers/readiness.py`: the two blocking blocks moved into sync helpers (`_readiness_summary_sync`, `_matrix_snapshot_sync`) called through `starlette.concurrency.run_in_threadpool`. Handlers stay `async def` because they `await request.json()`, so converting them to plain `def` was not possible without a larger rewrite. Responses, status codes and the redacted 503 handling are unchanged.
  - Test added: `optimizer_api/tests/test_h6_readiness_event_loop.py` (httpx.AsyncClient on an ASGI app with a provider whose fetch sleeps 1.5 s synchronously; a concurrent `/health` must finish < 0.5 s late and the fetch must still be in flight). Red 2 of 2 on the old handlers, green after the fix. `optimizer_api/tests`: 2527 passed.
  - Other async routes checked: no other route calls the matrix provider or Supabase client on the loop. `optimization.py` and `benchmark.py` endpoints are plain `def` (FastAPI threadpool); `fleet_selection.py` already uses `run_in_threadpool`; `auth.py` dependencies do no I/O.
  - NOT done (owner decision): matrix staleness / max-age logic and `utils/matrix_repository.py` are untouched; the audit's per-call `force=True` refresh in `matrix_snapshot` is unchanged, so the staleness half of H6 stays OPEN.
- **H20 (CI build and full suites), 2026-10-13, FIXED in repo, Claude Opus 5.5.** Branch `ci/h20-build-and-nightly`; commit 0a802bc. `.github/workflows/ci.yml`: the `frontend` job gained a `Production build` step (`npm run build`) with placeholder public variables only (`NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321`, `NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-dummy-anon-key`, `NEXT_TELEMETRY_DISABLED=1`); a new `python-full` job runs `uniride_core/tests optimizer_api/tests academic_benchmark/tests` on `workflow_dispatch` and a nightly `schedule` (03:00 UTC) only, with `PYTHON_DOTENV_DISABLED=1`, empty `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, `PYTHONPATH=optimizer_api`, and the same install steps as the `python` job. The `frontend` and `python` jobs got a job-level `if` (push or pull request) so the new triggers do not duplicate them; the focused test steps are unchanged.
  - Local check: `npm run build` passed with the placeholder variables. The `npm audit` part of the fix sketch was not added (report-only, not requested). Scheduled workflows run from the default branch only, so the nightly job starts once this reaches `WIP`.
  - Not installed by the CI install steps (tests that need them skip or fail on import): `pyvrp`, `pyvroom`, `vrplib` (the `solvers` extra), `streamlit`, `psutil`. `pandas` and `ortools` arrive only transitively. The first nightly run will show which tests skip.
- **H15 (vehicle-planning Sw/So mapping), 2026-10-14, FIXED in repo, Claude Opus 5.5.** Owner decision 2026-10-13: fix the legacy `/admin/vehicle-planning` page and keep it (not retired). Branch `fix/h15-vehicle-planning-sw`; red `0f9eba9`, green `5650728`. Re-verified against live code first: the page read `s.disabilityType` while `GET /api/admin/users` returns raw snake_case rows (`select("*")`, `disability_type`), so every Sw student was listed as So.
  - `src/lib/admin-user-mapper.ts` (new): `normalizeAdminUser` maps `disability_type`/`location_code` to `disabilityType`/`locationCode` and keeps the original fields (the `calculate-vehicles` BFF accepts both spellings). `page.tsx` applies it once where the users arrive (`loadStudents`), so the other reads (`selectAll`, the Sw/So lists, the badge) stay unchanged. The users API contract was not changed.
  - Test: the fixture in `page.test.tsx` now has the real snake_case shape; the new test checks the Sw quick-select, the `1 Sw, 0 So` and `1 Sw, 1 So` counts and the `disabilityType` carried into the optimizer payload. Red on `0f9eba9` (the wheelchair student's checkbox was not selected), green on `5650728`; with the `page.tsx` change reverted the new test fails again and the other six page tests pass.
  - Not changed (other consumers of the same API): `admin/sandbox/page.tsx` reads both spellings; `admin/compare/page.tsx` passes rows through; `admin/users/page.tsx` and `admin/ride-requests/page.tsx` have their own inline converters. The typed shared DTO mapper for all admin pages stays under MT7. `vehicle-planning-page.tsx` uses hard-coded test students, not the API.

- **H17 and M22 (promoted configs in production), 2026-10-14, PARTIAL, FIXED in repo on branch, Claude Opus 5.5.** Owner decision 2026-10-13 (DECISION_LOG A12). Branch `fix/h17-promoted-config-gate` (from `WIP` `c15fdec`); red tests `382bff1` (14 failed on the old code), fix `2aec181`. Re-verified against live code: `optimizer_api/strategies/promoted_config_loader.py` merged academic promoted params into 13 production strategies (12 classes) at construction: ga_split, ga_split_enhanced, ga, pso, pso_split, gwo, gwo_split, hho, hho_split, two_opt, e2bso, r2dma, paoea (`ga_split_hf` never called it). The web benchmark runner passes `STRATEGY_REGISTRY` singletons (`routers/benchmark.py:344`), built at import (`strategies/__init__.py:80-98`) before `main.py:29` loads `.env`, so there the flag must be in the process environment, not `.env`. Fix: `get_promoted_params` (and so `get_promoted_strategy_params`) returns `{}` unless `UNIRIDE_USE_PROMOTED_CONFIG` is exactly `"1"`, read at call time, default OFF. `OptimizationResponse` gained optional `effective_config_source` (`default`, `request`, `promoted`) and `effective_seed`, set by `ga_split`, `ga_split_enhanced` and `ga_split_hf` (also on empty-student and infeasible returns; "promoted+request" when the flag is on and a partial `ga_config` is merged over promoted values) and omitted from JSON when unset. Owner decision 2026-10-14: benchmark results (runner and matrix-native path) record `promoted_config_flag` and `promoted_config_sha256` in their metadata; the singletons were not changed. DUZELT round 1 added tests for ga_split_hf, pso, two_opt, r2dma and the provenance fields. DUZELT round 2 (red `e3dcb33`): runner records for registry singletons use the import-time snapshot `strategies.REGISTRY_PROMOTED_PROVENANCE` (`promoted_config_snapshot` = `registry_import`, or `call` for a fresh `get_strategy()`), because the flag can be set after the singletons were built; the SHA-256 is taken inside the cached loader so it matches the loaded document; matrix-native records carry `promoted_config_applicable: false`. Existing promoted-config tests in `test_sota_config_parity.py` now set the flag. Still open: H17 proper (production still imports `academic_benchmark.promoted_configs`, fix sketch MT4); M22 import-order and `TSPLIB_DATA_DIR` and the dotenv pin; other strategies do not report source and seed; the daily-plan run record and UI do not show them (follow-up, not touched here). `academic_benchmark/promoted_configs.py` unchanged.

#### 2026-10-14 - M4 / MT2 and H6 staleness half: C2 gate kept, matrix age shown (owner decision 2026-10-14)

- Branch `feat/m4-matrix-age-warning`; red `922b1fa`, green `a15f3cb`. DECISION_LOG T09. This replaces the 2026-10-13 warn-and-serve proposal, which was withdrawn after the finding that `matrix_snapshot` already fails closed (C2) on a kept or TTL-old matrix.
- Optimizer: the two `matrix_snapshot` raises are unchanged in behaviour (now `MatrixStaleError`, a `MatrixSnapshotError` subclass; bound `/optimize` still fails closed). Additive: provenance `refresh_failed`; the `/matrix-snapshot` 503 detail is `Matrix snapshot stale` for a stale or kept matrix, otherwise `Matrix snapshot unavailable`. Tests: `optimizer_api/tests/test_m4_matrix_stale_kept.py`; `test_matrix_repository.py` keeps its original rejection assertion.
- Daily plan: `matrixAge` (`loadedAt`, `ageSeconds`) in the response and on `/admin/daily-plan` when a plan is produced; a stale snapshot blocks the plan with reason `MATRIX_STALE` (tr/en copy). No env var and no warn-and-serve copy.
- Polish: `analyzeDudulluReadiness` `legDecisionsReadable` is required (type-level test).
- Still open under M4 / MT2: matrix domain enum, row-count check.
- **Legacy results quarantine (E1-E3, C1-C6 of the 2026-10-14 independent review; supersedes the "hide by default" first version), 2026-10-14, FIXED on branch, Claude Opus 5.5.** Branch `fix/legacy-results-obsolete-2026-10-13`; inherited DUZELT-2 work `38a184f`, red tests `d5a6270`. Owner decision: DECISION_LOG A13. Results stamped before 2026-10-13 are HISTORICAL_UNVERIFIED (visible in a labelled view, never pooled, never deleted); the old tuned parameters are kept and not used as warm start.
  - E1: the code cited a decision that did not exist; every citation now names A13 (A10/A11 are unrelated). E2: `load_metadata` dropped `legacy_best_params`, so the quarantined parameters vanished on the second startup; fixed by the inherited DUZELT-2 work (unknown keys survive) and covered by `test_legacy_best_params_survive_second_startup` (extended to three further startups).
  - C1/C2: `OBSOLETE.md` replaced by `QUARANTINE.md` + `QUARANTINE_MANIFEST.json` (SHA-256 of the committed git bytes, LF; the moved files are byte-identical to their original blobs, `.gitattributes` `-text` pins checkouts, verified on a clean detached worktree) in the two `legacy_pre_2026-10-13/` folders; the three academic endpoints take `include_historical` and return a separate `historical_unverified` section, so the real DB (64 `best_solutions`, 66 `benchmark_results` rows, all pre-cutoff) is no longer an empty view. C4: SQL calls the Python cutoff rule (`uniride_is_legacy`). C5: `mark_legacy_files` skips production-path directories like A06. C3: `cli_engine` writes `best_params_numba_current.json`; stale references are listed in the branch report. C6: commit `e418ac6` shifted two pre-existing test fixture dates. Round 2 (independent review): the first manifest hashed CRLF working copies (9 of 10 entries did not match the committed content) and `842e0f6` had re-added one CSV as CRLF; both are restored/regenerated. The `UNIRIDE_INCLUDE_OBSOLETE` warm-start backdoor is removed (D2). INVALID rows are pinned hidden in the historical view by `test_quarantine_round2.py`.
  - Closes no tracker row. It is the classification step that LT1/Q17 ("existing results stay suspect until rerun") left open for results older than 2026-10-13; H8, H9 and the M-items stay OPEN. The cutoff rationale (owner-confirmed 2026-10-15, DECISION_LOG A13): 2026-10-13 is the day the second of two evidence fixes landed, so every earlier result is missing at least one of them - 2026-10-09 merge `62673ca` (ga_split_enhanced/ga_split_hf params and seed on the benchmark path) and 2026-10-13 merge `2e157a1` (Science-review label/identity fixes). The new tuning output name `best_params_numba_current.json` was approved by the owner 2026-10-15.


#### 2026-10-14 - Reviewer follow-ups bundle (CI flake, M4 polish, H17 polish, Haversine flake)

- Branch `chore/followups-2026-10-14`; one commit per item. Not merged.
- CI flake: `vite.config.ts` sets `test.maxWorkers: 4`. Plain parallel `vitest run` on a 12-core machine oversubscribed the jsdom workers (summed test time 55.7 s uncapped, 26-31 s capped, same wall time) and random tests hit the 5 s timeout. No timeout was raised. Plain `npx vitest run` 3 of 3 green (60 files, 798 tests).
- M4 polish: unused `MatrixAgeUnit` import removed, duplicate fixture import merged, the two "refresh state" comments corrected (TS does not parse `refresh_failed`), `dudullu-readiness.test.ts` indentation fixed. New tests in `optimizer_api/tests/test_m4_matrix_stale_kept.py`: `refresh_failed` True in `matrix_provenance()` after a failed refresh; TTL-only stale path (no `_last_error`) raises `MatrixStaleError` and is 503 through the route (a no-op-refresh loader). Mutation: replacing the TTL raise with `pass` fails 2 tests; forcing `refresh_failed` False fails 1.
- H17 polish: `promoted_config_loader.py` resolves the path before the cached call, so `get_promoted_params` and `promoted_config_provenance` share one explicit cache key (a path change after an earlier lookup used to be masked). A missing, unreadable or malformed file yields defaults, a logged warning (path and exception type only, no file content) and a null SHA; the hash and the parsed document now come from the same bytes. Malformed covers JSON syntax and encoding errors, a RecursionError from deep nesting, and valid JSON of the wrong shape (top level not an object, `configs` not a list of objects, `params` not an object), checked by `_validate_document_shape` (reviewer round 1, E2). Flag off with a path set still reports the file SHA (the flag is reported separately). Tests: `optimizer_api/tests/test_h17_promoted_config_cache_key.py` (red 5 of 7 before the fix).
- Haversine flake: `test_non_negative` never saw a negative value. `haversine_distance` raised `ValueError` for some exactly antipodal pairs (for example 45 N 0 E vs 45 S 180 E: `1 - a` rounds to -2.2e-16 and `math.sqrt` rejects it). FIXED (lead decision): `a` is clamped to [0, 1] in `uniride_core/algorithms/distance.py` with comparisons (`if a > 1.0 ... elif a < 0.0`), not `min`/`max`, so a NaN coordinate still yields NaN instead of 0 m (reviewer round 1, E1: `max(0.0, nan)` is 0.0); red `7955a8d` and `8137c39`, green `0ac0e25` and `20ba673`. `test_exact_antipodal_pair_does_not_raise` is a normal test (distance = pi * R), the four property tests are unguarded again with a pinned antipodal `@example`, and `test_clamp_changes_no_result_for_non_antipodal_pairs` shows bit-identical results against the unclamped formula on a seeded sample of over 1000 pairs, plus NaN and inf inputs (same NaN-ness, same bits, or both raise). Removing the clamp fails the antipodal test and `test_non_negative`.
- **Archive manifests are platform-independent (Opus-review finding of 2026-10-14; existed on `WIP` since the Bildiri/YAEM archives), 2026-10-14, FIXED on branch `fix/archive-manifest-lf`, Claude Opus 5.5.** `test_bildiri_quarantine_boundary.py::TestPostArchivalBoundary::test_archive_verification_passes` and `test_yaem_quarantine_boundary.py::test_archive_manifest_covers_the_original_tracked_inventory_and_verifies` failed on a clean LF checkout (Linux CI; reproduced with `core.autocrlf=false`): the manifests held the size and SHA-256 of CRLF working copies (Windows, `core.autocrlf=true`) while git stores LF, and `verify_manifest` read the disk. 286 of 392 entries were wrong (Bildiri 202 of 233, YAEM 84 of 159); the other 106 (binary or LF-only) already matched. Fix: shared helper `academic_benchmark/committed_bytes.py` (`git cat-file blob`, disk fallback with a logged warning) used by `build_manifest`, `verify_manifest`, `quarantine_tracked_tree` (reads the blob at the pre-move path via `repo_root`), the CLI `verify` and the A13 legacy-results helper (C-3). The 286 entries were regenerated from the committed blobs (only `byte_size` and `sha256` changed; no archived file, path or classification changed; `git diff --stat` on `archive/` lists only the two `manifest.json` files). Regression tests: `academic_benchmark/tests/test_archive_manifest_line_endings.py`. C-2: the `benchmark_summary.csv` line of the 2026-06-30 report now carries the A13 moved-to-legacy note. Review round 1 found a gap in this change itself and it is closed: because the manifest now records the committed blob, `quarantine_tracked_tree` would have archived a source with an uncommitted edit while the manifest described the blob (the end-of-run verify compared the blob with itself). It now raises `QuarantineBlocked` before any move when `git diff --name-only [HEAD] -- <source_root>` is non-empty (staged or unstaged; against the index in a repository without a commit). Conversely `verify_manifest` and the CLI verify now also report `working copy differs from committed: <path>` from one `git diff --name-only --relative` over the archive, so a hand-edited tracked archive file is not hidden by reading the blob; git's own end-of-line normalisation keeps CRLF and LF checkouts clean. The reference is the git INDEX (`:<path>`), not HEAD, because a quarantine moves files before anything is staged; the HEAD check above ties the two together. The helper strips `GIT_DIR`, `GIT_INDEX_FILE` and `GIT_WORK_TREE` so a git hook cannot redirect it. The size/SHA-256 comparison, the quarantine-boundary and zero-active-import tests are unchanged and no check was removed; the new guards add refusals. No `.gitattributes` pin was added for `archive/`: it is not needed once the verifier reads blobs, and the effect of a pin on existing CRLF Windows checkouts was not measured.
- **M26 / QW11 (SOTA adapter objective and silent greedy fallback), 2026-10-15, FIXED in repo, Claude Opus 5.5.** Owner approved 2026-10-15. Branch `fix/qw11-sota-adapter-truth` (from `WIP` `d8ee59b`); red `17f957d`, green `45824a5`, web pass-through `4e3798e`. (1) Objective: `build_solver_matrix` now returns an `(n+1) x (n+1)` directed matrix with the depot at index 0, built from the same `duration_lookup` the response reports (`depot -> s1 -> ... -> sk -> depot`, the closed cycle `build_single_route_response` emits and the certifier checks arc by arc), scaled by `SOTA_DURATION_SCALE = 1000` and never rounded; the solver cycle is rotated to start at the depot and validated as a permutation (`invalid_solver_tour` otherwise). The reported cost is still recomputed from the real durations of the chosen order. The solvers already used full-recompute (ATSP-safe) 2-opt, so directed arcs are honoured. The SOTA strategies ignore `direction` (both pickup and dropoff are served as this depot-anchored cycle, as before); this fix does not change that. (2) Fallback: `solve_student_order_with_sota_tsp` returns `SotaOrderOutcome(order, fallback_reason)`; on failure it logs the exception server-side (`logger.exception`) and serves the greedy order with reason `solver_error` or `invalid_solver_tour`. `OptimizationResponse.algorithm_used` is then `greedy_fallback`, the new optional `fallback_reason` carries the code (both omitted from the JSON when no fallback), and `algorithm_requested` keeps the request; `/optimize` no longer overwrites a fallback label with the canonical name. In `/compare`, `AlgorithmResult.algorithm` stays the requested key but gets optional `algorithm_executed` and `fallback_reason`, and a fallback result is not eligible as `best_algorithm` or `fastest_algorithm`. The web pass-through (`optimizer-service.ts`, `optimize-route`, `calculate-vehicles` as `meta.fallbackReason`, `compare-algorithms`) is additive and conditional; `algorithm_used` reaches the UI message and the BFF `meta.algorithmUsed`, but the vehicle-planning page originally saved the UI-selected strategy, not the response's algorithm, into `route_plans.algorithm_used` (review blocker E1, fixed below). Academic effect: `academic_benchmark` does not import the adapter, but the legacy `optimizer_api/benchmark_runner.py` (`/benchmark`) dispatches to these three strategies under `academic_coordinate_scope`. For those runs the solver now optimises the depot-anchored Euclidean cycle (previously a depot-free matrix of 2-decimal, floored, minimum-1 distances), so e2bso, r2dma and paoea tour lengths from that runner are not comparable with pre-fix exports and must not be pooled; the runner now reads `fallback_reason` (lead decision 2026-10-15, commit `c87a55a`): a fallback run takes the runner's existing failed-run path (NaN tour length, `metadata["execution_failed"] = True`, no gap) and records `metadata["error_reason"] = "sota_fallback:<fallback_reason>"`, so `get_results_summary` and leaderboards drop it like any failed run and it never counts as e2bso, r2dma or p-aoea. No new status was added. Test: `optimizer_api/tests/test_benchmark_sota_fallback.py` (red `5f33fb9`). Review DUZELT 1 (red `0725cae`, green `5b96dc2`): (E1) `formatRoutePlanForSave` now persists the algorithm that actually ran (`meta.algorithmUsed` / `algorithm_used`, i.e. `greedy_fallback`) whenever the response carries a `fallback_reason`; saving is not blocked, and runs without a fallback still save the selected strategy. The compare page labels a fallback row with an amber badge `greedyFallback (<reason>)` (tr and en messages) instead of the plain success badge. `CompareResponse` gains an optional `fallback_algorithms` list (absent when empty) and each fallback entry in `summary` carries `algorithm_executed` and `fallback_reason`. `build_solver_matrix` now runs before the `try`, so a travel-time matrix error fails the request closed instead of becoming a `solver_error` greedy order. The adapter docstring now states the exact claim: the solver objective is 1000x the arc durations, while the reported total sums 2-decimal-rounded steps and can differ from the exact cycle cost by up to `(n + 1) * 0.005` minutes. Tests: `src/services/route-plans.test.ts`, `src/app/(app)/admin/vehicle-planning/page.test.tsx`, `src/app/(app)/admin/compare/page.test.tsx`, `optimizer_api/tests/test_sota_adapter_truth.py`, `uniride_core/tests/test_sota_tsp_strategy_adapter.py`.
- **H12 / QW7 (clustering used the process-global `random`), 2026-10-15, FIXED in repo on branch `fix/qw7-cluster-rng`, Claude Opus 5.5.** Owner approved the fix knowing it changes results. Re-verified against live code first: `kmeans.py` (k-means++ seeding), `k_medoids.py` (`random.sample`) and `fuzzy_cmeans.py` (membership init) read the global `random`; `fuzzy_cmeans_enhanced.py` and `hierarchical_fcm.py` (through `enhanced_fuzzy_c_means_core`) fell back to `random.Random()` seeded from OS entropy; the legacy primitives in `clustering.py` also used the global state; `VehicleCalculator` built a fresh strategy per attempt and passed no generator; `OptimizationRequest.clustering_algorithm` was a free string (an unknown name fell back silently to sweep). Fix: `get_clustering_strategy(name, sw, so, rng=None, **kw)`, `BaseClusteringStrategy(rng=...)` (`self.rng`), every core function and the hierarchical stages take an `rng`; a missing rng becomes a local `random.Random(DEFAULT_CLUSTERING_SEED=42)` (`clustering.resolve_rng`), never the global state. `VehicleCalculator(rng=...)` keeps one generator for all clustering attempts, so its retry loop still explores different partitions, reproducibly. ga, gwo, hho, pso and two_opt pass their own seeded `rng`; `permutation_tsp` (no seed of its own) passes `random.Random(42)`. `SUPPORTED_CLUSTERING_ALGORITHMS` (derived from the factory's own `_CLUSTERING_STRATEGIES` dict, one source of truth) is the allowlist: `OptimizationRequest.clustering_algorithm` is `Optional[Literal[...]]`, default `sweep` unchanged, unknown names are a 422. The factory's own sweep fallback was kept for direct callers. Academic code: `random.seed(seed)` + `random.shuffle` in `cli_engine.py` and `core/registry_setup.py` and `random.seed` + `random.sample` in `benchmark_utils.generate_combinations` became `random.Random(seed).shuffle/sample` (identical permutation and sample, no global mutation); the downstream local-search and Numba code reads no Python global `random` (checked by grep), so no site had to keep the global seed. No `np.random.seed` exists in the scanned code. Fair-protocol budgets and accounting untouched. Tests: 74 in 6 H12 test files (30 + 14 + 15 + 3 + 10 + 2, counted with `pytest --collect-only`), including the 2 academic guards (AST scan: no `random.seed` or `np.random.seed` in production code). Acceptance: 6 concurrent identical calls (with a thread hammering `random.seed`) give one partition for kmeans, k_medoids, fuzzy_cmeans, fuzzy_cmeans_enhanced and hierarchical_fcm, and one partition plus identical routes end to end through `TwoOptStrategy`. Result impact: academic evidence does not change (no academic path calls `VehicleCalculator` or a clustering strategy; the FCM split engine already used a seeded local generator). Production and API results change for requests with clustering `kmeans`, `k_medoids`, `fuzzy_cmeans`, `fuzzy_cmeans_enhanced` or `hierarchical_fcm` (previously unreproducible, now a function of the seed), and, for those requests, the routing rng stream of ga/pso/gwo/hho/two_opt is shifted because clustering draws from the shared strategy rng; default `sweep` and `clarke_wright` draw nothing and are unchanged. Review round 1 (the first tests passed even with the seed thread cut, because `resolve_rng(None)` is a fixed `Random(42)`): added seed-sensitivity tests for `VehicleCalculator` and for fuzzy_cmeans_enhanced and hierarchical_fcm (single stage and N=120 two-stage), identity spies that the enhanced and hierarchical cores receive the strategy's own rng (cluster and split paths, every hierarchical stage), spies that ga, gwo, hho, pso and two_opt hand their own seeded rng (constructor seed and request-config seed) to `VehicleCalculator`, and a global-state check for the legacy `kmeans_clustering` and `split_cluster`; `hierarchical_fcm_clustering` now calls `resolve_rng` once so its stages share one generator. The independent review confirmed by mutation that every seed-threading cut (`VehicleCalculator`; ga, gwo, hho, pso and two_opt; enhanced and hierarchical FCM, including the one-time `resolve_rng`; legacy `clustering.py` and `split_cluster`), the allowlist source revert and the earlier file reverts each fail at least one test. Closed 2026-10-15 by the follow-up polish entry below (`z.enum`, HTTP 400); `/api/calculate-vehicles` and `/api/sandbox` still pass the field through unvalidated (the optimizer's 422 rejects unknown names).
- **M18 (ACAD-05): GWO/HHO reported cost no longer rounded, 2026-10-15, FIXED in repo on branch `fix/m18-gwo-hho-unrounded-cost`, Claude Opus 5.5.** `_make_numba_metah_executor` in `academic_benchmark/core/registry_setup.py` passed `round(cost, 2)` as both `tour_cost` and `objective_cost`; the execution gateway independently recomputes the directed closed-cycle cost and accepts only 1e-9, so every fair GWO/HHO run on a fractional matrix raised `ResultContractViolation`. Fix: report the unrounded `cost` (gap was already computed from the unrounded value). The gateway tolerance was not touched. Test: `academic_benchmark/tests/test_m18_gwo_hho_unrounded_cost.py` runs `Core-GWO-TSP-Pure` and `Core-HHO-TSP-Pure` through the real `execute_preflighted` on a fractional ATSP, and checks tour_cost/objective_cost against the recomputed cycle cost to 1e-9 for the Pure and Memetic-2opt GWO/HHO executors. Follow-up 1 (lead decision, same branch): the same rounding was removed from `registry_setup.py:130, 135` (`_make_core_tsp_executor`), `:167, 172` (`_make_matrix_tsp_executor`, FCM-style engines) and the time-matrix branch of the legacy executor at `:432`; tests in `academic_benchmark/tests/test_m18_other_executors_unrounded_cost.py` (red `9813e5d`, green `9dce5a8`; reverting each site group alone fails its own tests: group A 3, group B 1, group C 2), plus guards that integer instances report identical values. Follow-up 2 (review verdict DUZELT round 1; DECISION_LOG A14): (i) `cli_engine.py:632-633` (`run_single_test_with_matrix`, reached by the legacy `GWO`/`HHO` names) no longer rounds the time-matrix cost to 2 dp; (ii) the `int()` truncation at `registry_setup.py:432` and `cli_engine.py:632-633` was a silent error on fractional non-time matrices (Numba-2-opt on a 7-node fractional ATSP reported 40 against a true 40.28692; reachable via `MatrixBuilder.to_problem_instance` and `tsplib_manager.py:301`): the cost is now an `int` only when every matrix entry is integer-valued (`academic_benchmark/core/reported_cost.py::report_cycle_cost`) and the unrounded float otherwise, so integer TSPLIB instances keep identical `int` values; (iii) the CLI aggregate rows (`cli_engine.py:1458` `avg_length`, `:1467` `objective_cost`) are no longer rounded to 4 dp before the CSV write and `save_benchmark_result`. The CSV readers (`results_reader.py`, `dashboard.py`) parse floats and do not depend on the rounding. Tests: `academic_benchmark/tests/test_m18_followup_cli_and_truncation.py` (red `f7decdd`, green `bb1244a`; reverting group D (`cli_engine.py:632-633`) fails 2, group E (`registry_setup.py:432` `int()`) fails 2, group F (`cli_engine.py` 4-dp rows) fails 1). Display-only rounding (`gap_pct`, `elapsed_sec`, `avg_gap`, `avg_time_ms`) is unchanged; the tuning-progress CSV (`cli_engine.py:1329`, `avg_length` at 4 dp) was not on the reported-result path and is left as is. Note: truthful `GWO-3opt` / `HHO-3opt` do not exist in the registry yet (`Core-*-Memetic-3opt` are `PLANNED`); the fair-approved GWO/HHO identities are the `-Pure` variants, and `Memetic-2opt` exists outside the fair-approved set. Effect on stored numbers: per-run costs on integer-cost instances (TSPLIB) are identical. Costs on fractional matrices are now the exact float where the executors previously stored 2 dp (GWO/HHO, core, matrix and legacy time-matrix paths) or a truncated integer (legacy and CLI distance-matrix path); earlier fair gateway runs on such matrices could not have been stored because the gateway rejected them. CLI aggregate rows now hold `avg_length` and `objective_cost` unrounded instead of 4 dp, so an average over several integer runs that is not an integer differs from the earlier stored value beyond the fourth decimal. Rows exported before this fix on fractional matrices (2 dp or truncated costs, 4-dp CLI averages) must not be pooled with rows produced after it.

#### 2026-10-15 - M4 / MT2 staleness half: the daily-plan note shows the age of the travel-time DATA (owner approval 2026-10-15)

- Branch `feat/matrix-data-freshness`; DECISION_LOG T09 (the C2 gate stays fail-closed; the age is shown) and T10 (the owner's approval of 2026-10-15 to show the age of the travel-time data). Problem: `MatrixAgeNote` showed the matrix LOAD age, which is ~0 s because the snapshot step refreshes before reading, so a months-old matrix read as fresh. Live read-only query 2026-10-15: `public.time_matrix` had 812 rows, all `created_at` 2026-03-05, and no update column.
- Schema (NOT applied to any database; the lead applies it after review): `supabase/migrations/20261015_time_matrix_updated_at.sql` adds `updated_at timestamptz`, backfills `coalesce(created_at, now())` before setting `NOT NULL DEFAULT now()`, and a `BEFORE UPDATE` trigger (`public.set_time_matrix_updated_at`, SECURITY INVOKER, `search_path = ''`). Idempotent, one transaction, no policy or arc change. Mirrored in `supabase/schema.sql`. Static guard: `src/lib/time-matrix-updated-at-migration.test.ts`.
- Optimizer: `SupabaseTimeMatrixProvider` selects `updated_at` with the other columns and, only when PostgREST answers undefined-column (SQLSTATE `42703`, message names `updated_at`), retries the page with the original select. Chosen over a separate optional query because it costs no extra request once the column exists, keeps one paging loop, and any other error still propagates (fails closed as before). `TimeMatrixRepository` keeps `max(updated_at)` per load; provenance gains `data_updated_at` (ISO UTC) and `data_age_seconds` (computed at read time), both null without the column. Nothing in the C2 gate reads them: `MatrixStaleError` / `MatrixSnapshotError` behaviour and the snapshot sha256 are unchanged. Tests: `optimizer_api/tests/test_m4_matrix_data_freshness.py` (column present, missing, unusable values, paging with and without the column, gate unchanged, digest independent of the timestamp).
- TS: `buildMatrixAge`, the preview response `matrixAge`, `PlanMatrixAge` (`dataUpdatedAt`, `dataAgeSeconds`, `dataAgeParts`) and `MatrixAgeNote`, which now shows only the data age: tr "Yolculuk süreleri en son <süre> önce güncellendi", en "Travel times last updated: <age> ago", and an "unknown" text when the data age is null; the old load-age copy (`loaded`, `unknownAge`) is removed. A malformed `data_age_seconds` is dropped on its own and keeps the load fields. Tests: `matrix-age.test.ts`, `daily-plan-view.test.ts`, `page.test.tsx`, `route.test.ts`.
- Operator notes: (a) the trigger advances `updated_at` on every update, including an upsert that writes identical values, so reloading unchanged data makes the data look fresh; the date means "last written", not "last changed". (b) Apply the migration before deploying the optimizer; the optimizer tolerates the missing column, but the date stays unknown until it exists. (c) If PostgREST keeps the old column list after the DDL, run `NOTIFY pgrst, 'reload schema'`. (d) The provider's fallback fires only for SQLSTATE `42703` naming `updated_at`; a 42703 for any other column propagates and the load fails closed (`test_undefined_column_error_for_another_column_is_not_a_missing_updated_at`).
- Behaviour until the migration is applied: the note reads "last update time unknown". After it is applied, existing rows carry 2026-03-05 (from `created_at`), so the note will show the real age; refreshing the matrix with an upsert moves it forward. No effect on optimisation results or the academic benchmark path.

#### 2026-10-15 - follow-up polish for M26 / H12 (compare fallback label, benchmark CSV status, clustering allowlist)

- Branch `fix/compare-fallback-polish` (from `WIP` `2808e02`); red `def07e6`, `e69fc87`, `f4490f8`, fixes `dd88c87`, `9831935`, import fix `8f767a5`. No tracker status changes (M26 and H12 stay FIXED in repo).
- Compare page (`src/app/(app)/admin/compare/page.tsx`): a row with `fallback_reason` that also fails certification (`success: false`) now shows the error badge and the amber `greedyFallback (<reason>)` label together; a successful fallback row still shows only the amber label, a normal row only the success badge. Test: `src/app/(app)/admin/compare/page.test.tsx`.
- Benchmark CSV export (`src/app/page.tsx`): the row builder moved to the pure `src/lib/benchmark-csv.ts`; the seven existing columns keep their order and `execution_failed` and `error_reason` are appended, read from the run's `metadata` (the fields `optimizer_api/benchmark_runner.py` already sets, e.g. `sota_fallback:<reason>`). Missing metadata leaves both cells empty (unknown, not "false"). Test: `src/lib/benchmark-csv.test.ts`.
- `/api/compare-algorithms` (`route.ts`): `clusteringAlgorithm` is `z.enum` over `CLUSTERING_ALGORITHM_NAMES` (new `src/lib/clustering-algorithms.ts`, the same seven names as `SUPPORTED_CLUSTERING_ALGORITHMS`; a test reads the Python factory dict and fails on drift). An unknown name is a 400 `Invalid request body` with `details`, before any optimizer call; the field stays optional with default `sweep`. The compare and vehicle-planning pages now take their option list from the same module. Test: `src/app/api/compare-algorithms/route.test.ts`, `src/lib/clustering-algorithms.test.ts`.
- Not changed: `/api/calculate-vehicles` and `/api/sandbox` do not validate `clusteringAlgorithm` (typed `string`, default `sweep`, passed through), so an unknown name there is still rejected only by the optimizer's 422. Adding a check there would be new validation, not the same fix; left for the lead.
- Revert proof: removing only the badge change, only the two CSV columns, or only `z.enum` makes the matching tests fail again (1, 4 and 1 failures).

#### 2026-10-15 - H17 follow-up: the daily-plan page shows the algorithm settings and seed

- Branch `feat/daily-plan-config-provenance`; closes the UI part of the open item "the daily-plan run record and UI do not show them" in the H17 entry above; persisting the provenance in a run record remains OPEN (DECISION_LOG A12; no optimizer change, no DECISION_LOG edit). `runDailyPlan` (`src/services/daily-plan-run.ts`) reads `effective_config_source` and `effective_seed` from each `/api/v1/optimize` answer (a malformed value is dropped and never blocks the plan), `collectSolverConfig` (`src/services/plan-solver-config.ts`) keeps the distinct values over the waves, the preview response carries `solverConfig`, and `SolverConfigNote` in `src/app/(app)/admin/daily-plan/page.tsx` shows a muted line next to the matrix note: tr "Algoritma ayarları: yerleşik varsayılanlar · tohum 42", en "Algorithm settings: built-in defaults · seed 42". Known values: `default`, `request`, `promoted` (promoted academic config), `promoted+request`; an unknown value is shown raw; waves with different values, or some silent, read "mixed"; a response with neither field (older optimizer, blocked plan) shows nothing. Tests: `plan-solver-config.test.ts`, `daily-plan-view.test.ts`, `page.test.tsx`, `route.test.ts` (red `985bfa7`, fix `af41a83`). Still open: persisting the provenance in a run record (the plan is not stored, so only the live preview shows the line); strategies other than the ga_split family do not report the fields.

#### 2026-10-15 - Archive manifest polish P8 / P9 / P10 (follow-up of the platform-independence fix, Opus review)

- Branch `fix/archive-manifest-polish` (red `59a0113`, green `237eafc`). **P8:** `verify_manifest` verified an archived file that git does not track at the archive path, while the pre-move original is still in the index, as clean (the `committed_bytes` fallback read the original). With `repo_root` it now reports `archive file not tracked in git (stage it): <path>`; new keyword `allow_unstaged_archive` (default False) is passed only by the end-of-run verification inside `quarantine_tracked_tree`, which verifies exactly that moved-but-unstaged state, so the quarantine itself is unchanged. Consequence: CLI `verify` right after a quarantine, before `git add`, now exits 1 until the archive is staged. The existing `test_quarantine_moves_only_tracked_files_and_writes_reproducible_manifest` asserted the old silent pass and now passes the flag. Without `repo_root`, or with neither path tracked (disk fallback with a warning), nothing changed. New helper `committed_bytes.index_has_blob`.
- **P9:** `_uncommitted_changes` ran two git calls with no timeout and let `CalledProcessError`/`FileNotFoundError` escape. Both calls now carry a 120 s timeout (same bound as `working_copy_drift`) and the isolated git environment; timeout, non-zero exit and `OSError` become `QuarantineBlocked("cannot determine the uncommitted state ...; nothing moved")`, so the quarantine still refuses (fail closed) and the CLI exits 2 with that message.
- **P10:** `committed_bytes.py` header, the `committed_bytes` docstring, the `_canonical_bytes` docstring and the disk-fallback warning now say INDEX (staged) bytes and why (a quarantine moves files before staging; the index equals the committed bytes only while nothing is staged over them, which `quarantine_tracked_tree` enforces against HEAD). Wording only; the function name, the `working copy differs from committed` problem text (pinned by tests) and the audit text above (which describes the blob read, correctly) were left alone.
- Tests: `academic_benchmark/tests/test_archive_manifest_polish.py` (19 tests; 11 of the first 13 were red before the fix). Mutation: disabling the P8 branch fails `test_verify_reports_an_untracked_archive_file_whose_original_path_is_tracked`; restoring the pre-fix `_uncommitted_changes` fails 9 P9 tests. Review round 1 added two P8 boundary tests (archive staged while the original removal is not: clean; neither path tracked: clean with the disk-fallback warning), each failing when its own condition in `verify_manifest` is removed, and a P9 guard: `git rev-parse --verify --quiet HEAD` is read as "no HEAD" only for exit status 1 (no such ref); any other non-zero status raises `QuarantineBlocked` (mutation: removing the check fails its test).

#### 2026-10-15 - Web input hardening: clustering allowlist in two routes, CSV formula injection

- Branch `fix/web-input-hardening` (from `WIP` `fc36da4`); red `fdfdb21`, fix `7dbfa5a` (item 1); red `bcb67ce`, fix `28daf71` (item 2). No tracker status changes. Closes the "not changed" note of the M26 / H12 follow-up polish entry above.
- **Item 1:** `/api/calculate-vehicles` and `/api/sandbox` (both parse the body by hand, so both keep that style) now check `clusteringAlgorithm` against `CLUSTERING_ALGORITHM_NAMES` through the new type guard `isClusteringAlgorithmName` (`src/lib/clustering-algorithms.ts`; exact, case-sensitive). Absent means `sweep`; any other value (unknown name, empty string, wrong case, number, `null`) is a 400 before the optimizer is called, in each route's own error format (`{ error: "Invalid clusteringAlgorithm" }`). The sandbox page sends the fixed literal `sweep` and has no option list, so it is unchanged. Tests: `src/app/api/calculate-vehicles/route.test.ts`, `src/app/api/sandbox/route.test.ts` (reverting only the two route files fails 10 tests).
- **Item 2:** `escapeCSV` (`src/lib/benchmark-csv.ts`) now prefixes a TEXT cell that begins with `=`, `+`, `-`, `@`, TAB or CR with a single quote before the existing quoting (a cell containing CR is now quoted too). The decision is by runtime type, not by inspecting the text: numbers (negative numbers included) and booleans are untouched, so the benchmark row's `run_number`, `tour_length`, `elapsed_ms`, `gap_percent` and `execution_failed` columns do not change; `algorithm`, `problem`, `timestamp` and `error_reason` are text and are defused. Exporters checked: (a) `src/app/page.tsx` `handleExportCSV` through `buildBenchmarkCsv`: hardened (problem names can come from imported results). (b) `src/services/excel/driver-export.ts` (XLSX via SheetJS `json_to_sheet`, student, driver and vehicle names, e-mail, address are user-controlled): left unchanged, verified safe: strings become `t: "s"` cells and no formula is written; `driver-export.test.ts` writes `=`, `+`, `-`, `@` payloads into every text field and re-reads the real xlsx, asserting no cell has a formula (characterisation test, not a revert-proof test). (c) `toCsv` in `src/services/plan-experiments.ts` (research scripts `run-plan-experiments.ts`, `run-fleet-scenarios.ts`, files on disk): left unchanged; every column is system-generated (dates, counts, status and reason codes, anonymised ids) and its bytes are reproducibility evidence. (d) `admin/reports` `handleDownloadWeekly` is a toast stub, no file. The JSON downloads and the bulk-upload page (import only) are not CSV exports. Tests: `src/lib/benchmark-csv.test.ts` (reverting only `benchmark-csv.ts` fails 9 tests).
- **M8 / P3-07 (escaping half), same branch (red `ca1ac3c`, green `c254ff4`):** new `escapeHtml` (`src/lib/escape-html.ts`; `& < > " '`, null and undefined become empty). `generatePDFHTML` in `driver-export.ts` now escapes every interpolated value (title and date, vehicle name and plate, driver name, student name and student number, times, counts, status label), so a name such as `<img src=x onerror=alert(1)>` or `"><script>` appears as text in the print window and no raw `<script`, `<img` or `onerror=` survives. Test: `src/services/excel/driver-export-html.test.ts` (5 payloads through `exportDriverAssignmentsToPDF` with a stubbed `window.open`, plus helper tests; reverting only `driver-export.ts` fails 6). Other HTML sinks in `src/`: `document.write` only in this export; `dangerouslySetInnerHTML` in `src/app/page.tsx:1105` (a static CSS constant, no data) and `src/components/ui/chart.tsx:81` (generated CSS from the chart config and a `useId` id; the colours are fixed constants, but the config keys are `ALGORITHM_DISPLAY_NAMES[algo] || algo` (`src/app/page.tsx:957`), so an algorithm name that is not in the display table passes through unchanged from the results, and `/api/v1/benchmark/import` (`optimizer_api/routers/benchmark.py:578`) accepts free text there; the impact is limited to CSS (the keys land in a `--color-<key>` custom property inside a `<style>` element) and no UI path lets a user set such a name, so it is not HTML-escaped and is left as is; a CSS-identifier sanitiser would be the fix if that ever changes); no `innerHTML`, `outerHTML` or `insertAdjacentHTML`. Not changed in this task: the production CSP and HSTS (QW8 rest), so M8 stays PARTIAL.
- **Residual risk (CSV, documented, no code change):** the OWASP "CSV Injection" guidance also notes the separator problem. A Turkish-locale Excel splits CSV on `;`, so a text cell such as `x;=1+1` becomes two cells and the second starts with `=`; neither the quoting nor the single-quote prefix prevents that, because the prefix only protects the first character of the cell. Likelihood is low: the exported text (`algorithm`, `problem`, `error_reason`, `timestamp`) comes from the server or from an admin importing results, not from students. Left as a documented residual; the fix, if ever wanted, would be to defuse every `;`-separated segment or to export with a `;` aware writer.

#### 2026-10-15 - Archive/quarantine git calls: shared timeout, isolated environment, fail-closed errors (P9 follow-up)

- Branch `fix/archive-git-timeouts` (red `6c5f5b0`, fix `4a7c740`; review round 1: red `f0997fe`, fix `9ac6315`). The remaining git calls had no timeout and could raise raw errors to API callers: `_git_paths`, `_git_directory`, `_canonical_repo_root` in `archive_manifest.py`, and `working_copy_drift`, `committed_bytes`, `index_has_blob` in `committed_bytes.py`. All now go through one helper, `committed_bytes.run_git` (constant `GIT_QUERY_TIMEOUT_SECONDS = 120`, `git_environment()`), which raises `GitQueryFailed` (kind timeout / exit / unavailable). `archive_manifest` turns it into `QuarantineBlocked("cannot <action>: ...")` (`_git_query`; non-UTF-8 git output too); `verify_manifest` reports it as an error entry (`cannot verify <file>: ...`, `cannot check the working copy for drift: ...`), so a git failure is never a clean verification, an empty file listing or "no drift".
- Silent paths closed: `working_copy_drift` returned `[]` for ANY git failure (a timeout included), and `committed_bytes`/`index_has_blob` read a timeout as "not in the index" (disk bytes, or `False`). Review round 1 (real Git for Windows 2.55, `GIT_TEST_ASSUME_DIFFERENT_OWNER=1`) found that the first fix still failed open for a repository git refuses to trust (dubious ownership, `safe.directory`): `git diff` then exits 129 with "Not a git repository" (the same words as for a real non-repository) and `git cat-file` exits 128, so the exit status and message cannot be told apart from "no repository" / "not in the index", and the old mocked test (exit 128 "dubious ownership" from `git diff`) did not reproduce what git does. Fix (`9ac6315`): `committed_bytes.is_git_repository` asks git itself (`git rev-parse --git-dir`, only after a failure, cached per directory for one verify/build run via `repository_cache`). The empty drift result and the disk fallback are allowed only when git is missing, or the directory is really not in a repository (rev-parse says "not a git repository" and no `.git` exists at or above it), or, for `cat-file`, the path is not in the index of a healthy repository (exit 128 with git's "does not exist" / "not in the index" message). Dubious ownership, a corrupt `.git` that git calls "not a git repository" (broken HEAD or objects), a corrupt index (`cat-file` and `diff` exit 128 "index file smaller than expected"; rev-parse still succeeds, hence the message test), a timeout or any other exit status raise `GitQueryFailed`; `verify_manifest` reports them as errors and the CLI verify exits 2 on a distrusted repository. A normal verification run needs no probe (tracked files succeed first): the real Bildiri (233 entries, 30 s) and YAEM (159 entries, 16 s) CLI verifications exit 0.
- Limit: none known for the cases above. Messages are matched in English (`LC_ALL=C` is set for those calls); a git release that words the "not in the index" message differently would raise instead of falling back (loud, not silent). The `cat-file` bound rose from 60 s to the shared 120 s.
- Not changed: `fair_pilot._git_metadata` (benchmark provenance, not quarantine; no timeout, returns null revision/dirty on failure). Tests: `academic_benchmark/tests/test_git_call_timeouts.py` (40 tests; 29 red before the first fix and 6 more real-git tests red before the round-1 fix; reverting only the source files fails them again).

#### 2026-10-15 - Dashboard descriptive labels (C5-F1)

- Branch `fix/c5f1-descriptive-labels` (red `21192ac`, fix `6ed3eb9`). Owner decision 2026-10-15 (DECISION_LOG A15). `academic_benchmark/dashboard.py`: the best/Better marking is now 'Lower mean gap (descriptive)' (summary caption, pairwise comparison column and caption, edge-frequency selection text); the LaTeX export is 'Descriptive LaTeX table (not validated for publication)' (heading, button, `caption=` and a leading `%` comment). Also reworded: 'Highlights the best performing algorithms', 'paper-ready', 'top solutions / top N algorithms', tab title 'Leaderboard'. Not changed: computations, sort orders, the 'Best-So-Far gap' footnote (a technical term), 'Ranked by Gap' (a sort). Test: `test_c5f1_descriptive_labels.py` (6 tests, tabs run by AST against a stub `st`; reverting only `dashboard.py` fails all 6).

#### 2026-10-15 - Pilot git provenance: shared timeout, isolated environment, recorded failure reason (follow-up of the archive git entry)

- Branch `fix/fair-pilot-git-metadata-timeout` (red `5e412e5`, fix `5028f53`). `fair_pilot._git_metadata` (also used by `native_pilot`) called `git rev-parse HEAD` and `git status --porcelain` with `subprocess.check_output`: no timeout (a hung git would hang the pilot), the inherited `GIT_DIR`/`GIT_INDEX_FILE`/`GIT_WORK_TREE` (a hook environment would describe another repository), and a `subprocess.TimeoutExpired` would have escaped. Both calls now go through `committed_bytes.run_git` (120 s, `git_environment()`).
- Contract kept: a failure is "unknown", never a clean tree. Any git failure still gives `{"revision": null, "dirty": null}` (also when `rev-parse` succeeded and `status` failed: no revision is recorded next to an unknown dirty flag). New: such a record carries `"git_error": "timeout" | "exit" | "unavailable"` (`GitQueryFailed.kind`). When git answers, the dict is unchanged (`revision`, `dirty`; no new key), so existing manifests keep their shape. The `git` object of the pilot manifests has no schema and no reader: it is not the `GitStateV1` of `run-v1.schema.json` (`commit` 40-hex, `dirty` bool, `extra=forbid`), which no pilot manifest is validated against; a repository-wide search found no consumer of `manifest["git"]`, `revision` or `dirty` outside `fair_pilot.py` and `native_pilot.py`.
- Open observation (policy not changed): no fair-protocol or native-protocol validator checks the git provenance, so a manifest with `revision: null` is accepted as valid evidence today. When the pilot manifests move to `RunManifestV1`, its required 40-hex `commit` would reject it. Deciding whether a null revision may be pooled or published is an owner decision.
- Tests: `academic_benchmark/tests/test_pilot_git_metadata.py` (13: timeout / exit / git missing / permission on the first and on the second call, timeout and environment passed to every call, real-git clean and dirty repository, hostile inherited `GIT_DIR`, directory outside a repository, `native_pilot` shares the function; 11 red before the fix, reverting only `fair_pilot.py` fails them again). `academic_benchmark/tests`: 1170 passed, 3 skipped.

#### 2026-10-15 - Go-live security: Supabase advisor lint 0011 on update_updated_at_column

- Branch `fix/update-updated-at-search-path` (red `592d5bf`, fix `6e3e671`). The Supabase security advisor (lint 0011 `function_search_path_mutable`) flagged `public.update_updated_at_column()`: SECURITY INVOKER plpgsql, `proconfig` null (read-only live query 2026-10-15), so `NOW()` was resolved through the caller's role-mutable `search_path`. It is the shared BEFORE UPDATE trigger function of 8 tables (users, weekly_schedules, ride_requests, vehicles, route_assignments, admin_settings, route_plans, sandbox_scenarios).
- Fix: new migration `supabase/migrations/20261016_update_updated_at_search_path.sql` (idempotent, one transaction) re-defines the same function with `SECURITY INVOKER SET search_path = ''` and `NEW.updated_at := pg_catalog.now()`. Same name, no arguments, `RETURNS trigger`, so `CREATE OR REPLACE` keeps the 8 triggers; the function is not dropped and no trigger is re-created. `supabase/schema.sql` mirrors the final state; the already-applied historical migrations (`20260329_add_route_plans.sql`, `20260329_add_sandbox_scenarios.sql`) are untouched. Behaviour is identical (transaction time). **Not applied to the live database yet**: the lead applies it after review; the advisor result is unchecked until then.
- Test: `src/lib/update-updated-at-search-path-migration.test.ts` (7 static guards: transactional, empty search_path and `pg_catalog.now()`, no DROP FUNCTION or trigger re-creation, no SECURITY DEFINER, schema.sql mirror, eight triggers still wired); removing the migration and restoring the old schema.sql fails 5 of 7. No local Postgres in CI, so it proves the SQL text, not the live effect.
- Open: the same lint may list other trigger functions in the live project (for example `set_student_leg_decided_at`, which has no `SET search_path` in `schema.sql`); this entry covers only `update_updated_at_column`.

#### 2026-10-15 - M8 / QW8: nonce-based production CSP and HSTS

- Branch `fix/qw8-csp-hsts` (red `f647a71`, fix `4f897e4`). Before: `next.config.ts` sent one static CSP in every environment with `script-src 'self' 'unsafe-inline' 'unsafe-eval'` and localhost origins in `connect-src`, and no HSTS. Now `src/proxy.ts` (Next.js 16 proxy, formerly middleware) sets a per-request nonce CSP on every page response and forwards it on the request (`Content-Security-Policy` and `x-nonce`) so Next.js stamps its own scripts; the static CSP was removed from `next.config.ts` (two CSP headers would intersect). The matcher now also covers pages (not `/api/*` other than admin/benchmark, `_next/static`, `_next/image`, favicon, prefetch). `/api/admin` and `/api/benchmark` keep the bearer gate unchanged, and review round 1 added the missing tests for it (`/api/benchmark` and `/api/benchmark/run` without a token return 401 and never build a Supabase client; error and no-user results return 401; mutation-checked). Side effect (low impact): other `/api` JSON responses and static assets no longer carry the old static CSP header.
- Production policy: `default-src 'self'; script-src 'self' 'nonce-<n>' 'strict-dynamic'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: https://placehold.co; connect-src 'self' <supabase https origin> <supabase wss origin> <origin of NEXT_PUBLIC_OPTIMIZER_API_URL if set, loopback dropped>; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'` plus `Strict-Transport-Security: max-age=63072000; includeSubDomains` (preload not set, not decided). HSTS is sent once by `next.config.ts` `headers()` (production only, all paths, so also for responses the proxy does not touch); the proxy does not repeat it. Development keeps `'unsafe-inline' 'unsafe-eval'` scripts and localhost/ws connect sources for HMR, and sends no HSTS.
- Breakage review: no inline `<script>` and no third-party script anywhere in `src`; fonts are `next/font/google` (self-hosted at build, so `fonts.googleapis.com`/`gstatic` were dropped in production); `src/app/page.tsx` and `src/components/ui/chart.tsx` inject `<style>` tags, which is why `style-src 'unsafe-inline'` stays; the driver PDF export (`window.open("")` + `document.write`) inherits the opener's policy, contains only an inline `<style>` and no script, so it is allowed and still prints; CSV/XLSX downloads use `URL.createObjectURL` with an anchor `download`, which CSP does not govern; no web workers, no iframes, no realtime channels in `src` (wss for Supabase is still allowed); the optimizer is only called server-side (BFF), so the server-only `OPTIMIZER_API_URL` is deliberately kept out of the public header (it would leak an internal address) and only `NEXT_PUBLIC_OPTIMIZER_API_URL`, if set, is allowed. Every route is dynamic in `next build`, which nonces require.
- Verification: `npx next build --webpack` succeeds with placeholder env (the Turbopack build failed in the worktree, junction suspected; `npm run build` uses `--webpack`); `next start` and curl on `/`, `/admin/benchmark`, `/login` returned the policy above with a different nonce per request, every `<script>` tag in the HTML carries the nonce, HSTS present exactly once (re-checked after the review fixes, also on the 401 and on a 404 outside the proxy matcher); `/api/admin/users` without a token returns 401. Full `vitest` 964 passed in 72 files (961 before the non-Bearer header cases), `tsc --noEmit` clean. Not done: a real browser pass (console CSP violations), which needs the real Supabase project and a login.
- Open: `style-src 'unsafe-inline'` remains (nonce-ing style attributes is not possible with React inline styles); HSTS `preload` is not set (not decided); a Report-Only rollout against the live deployment is advisable before treating the policy as final.
- **student_leg_decisions live-apply, 2026-10-15, on branch, Claude.** Branch `fix/student-leg-decisions-live`. Finding (live, read-only, lead 2026-10-15): `public.student_leg_decisions` and `public.set_student_leg_decided_at()` do not exist in the live database because `supabase/migrations/20260929_create_student_leg_decisions.sql` (a8b18c9) was never applied. Effect: readiness `legDecisionsReadable` is false, the daily-plan preview reports `LEG_DECISIONS_UNAVAILABLE` and blocks outside demo mode, and `POST`/`GET /api/ride-confirmation` return 503. Owner decision 2026-10-15: create it now. Fix: new `supabase/migrations/20261016b_apply_student_leg_decisions.sql` (sorts after `20261016_update_updated_at_search_path.sql`), single transaction and idempotent, with the exact 20260929 table (columns, three CHECKs, primary key `(user_id, service_date, direction)`, FK to `users(id)` ON DELETE CASCADE) and trigger semantics, the function hardened (`SECURITY INVOKER`, `SET search_path = ''`, `pg_catalog.clock_timestamp()`, lint 0011), RLS on without policies, `REVOKE ALL` from `anon`/`authenticated`, `GRANT` to `service_role`. The 2026-09-29 file is untouched; `supabase/schema.sql` mirrors the hardened function. Code-contract check: columns, value sets and the 0..1439 flexibility range match `DbStudentLegDecision`, `decisionRowSchema` (`daily-plan-run.ts`), the `ride-confirmation` route schema and upsert (`onConflict: user_id,service_date,direction`), and the readiness probe; all access goes through `getSupabaseAdmin()` (service_role), so the revoked anon/authenticated grants and the absence of policies are what the code expects; `optimizer_api` does not touch the table. Guard: `src/lib/student-leg-decisions-live-migration.test.ts` (8 tests; red `7e11ac3`, mutation-checked: unqualified `clock_timestamp`, missing `ENABLE ROW LEVEL SECURITY` and a reverted `schema.sql` each fail it). **Not applied**: the owner pastes the whole file into the SQL editor and then runs the verification queries listed in the file header; until then the live database is unchanged and the finding stays open for the live state.

#### 2026-10-15 - H17 / M26 follow-up: solver provenance saved with each route plan

- Branch `feat/route-plan-solver-provenance` (red `d2cdf0b`, fix `d14af3f`); owner decision 2026-10-15, DECISION_LOG S08. Closes the "persisting the provenance" part left open in the H17 entries above, for the flow that saves plans. Findings before the change (live code): only the vehicle-planning page saves plans (`handleSavePlan` -> `formatRoutePlanForSave` -> `saveRoutePlan` -> `POST /api/route-plans`); the daily-plan flow saves nothing (preview only), and no screen lists saved plans (`getRoutePlans` has no caller). The payload stored `algorithm_used` only (M26: the algorithm that ran when a fallback was served); `effective_config_source` / `effective_seed` never reached the page because `optimizeRoutes` and `/api/calculate-vehicles` dropped them.
- Change: migration `supabase/migrations/20261016c_route_plans_solver_provenance.sql` adds `route_plans.solver_provenance jsonb NULL` with a CHECK (null or JSON object), no default, no backfill (old rows stay null = unknown), no policy or grant change (the 20261009/20261010 policies are table-level). `optimizeRoutes` and `/api/calculate-vehicles` (`meta.effectiveConfigSource`, `meta.effectiveSeed`) now forward the two fields when the optimizer sends them. `buildSolverProvenance` (`src/services/solver-provenance.ts`) builds `{ algorithm_requested, algorithm_used, fallback_reason, effective_config_source, effective_seed }` from the optimizer-reported fields (malformed values dropped; null when the optimizer reported none); `algorithm_used` is the optimizer-reported `meta.algorithmUsed` when present, else the algorithm chosen at calculation time. Review DUZELT 1 and 2: the page captures (initially null; `formatCalculatedPlanForSave` blocks a save without a captured choice) algorithm and clustering at calculation time (like `calculationDirection`) and saves those, so changing the dropdown between calculating and saving no longer rewrites `algorithm_used`/`clustering_used` or contradicts the provenance (red `108c8c0`). `POST /api/route-plans` validates `solverProvenance` with a strict zod schema (five allowlisted keys, short plain tokens, integer seed, non-empty) and answers 400 otherwise; GET returns the column through `select("*")`. `SolverProvenanceNote` shows the same muted line on the vehicle-planning result card (daily-plan wording for source and seed, plus the fallback reason; tr and en).
- Not done: `optimizer_version` (no flow has it at save time, so it is not stored; adding a key later needs no migration); strategies other than the ga_split family still report no config source or seed (their plans store only the algorithm names and any fallback reason); there is no saved-plan list screen to show the stored value on (it is returned by GET for when one exists). The migration must be applied strictly before the app: the optimizer sends `algorithm_requested` on every response, so the old schema would fail almost every save (500). The provenance is asserted by the admin client and only shape-validated server-side (server-side derivation deferred, S08). Tests: `solver-provenance.test.ts`, `route-plans.test.ts`, `src/app/api/route-plans/route.test.ts`, `route-plans-solver-provenance-migration.test.ts`, `solver-provenance-note.test.tsx`, vehicle-planning `page.test.tsx`, `optimizer-service.test.ts`, `calculate-vehicles/route.test.ts`.

#### 2026-10-16 - L4: server-only guard on the admin helpers

- Branch `fix/l4-server-only` (red `89b31e4`, fix `0b2d8dc`, test mocks in a third commit). Re-verified against live code: neither `src/lib/supabase-admin.ts` nor `src/lib/admin-auth.ts` imported `server-only`, although the package is a dependency and `optimizer-server.ts`, `daily-plan-run.ts` and `fleet-scenario-run.ts` already use it.
- Fix: `import "server-only";` added as the first import in both files. A client component that imports either file (directly or through `benchmark-auth.ts`) now fails the build.
- Importers checked (grep over `src`): `admin-auth.ts` and `supabase-admin.ts` are imported only by API route handlers under `src/app/api/**`, by `src/lib/benchmark-auth.ts`, `src/services/daily-plan-run.ts` (type-only import), `src/services/fleet-scenario-run.ts` and their tests. No file with `"use client"` imports them, directly or through those modules.
- Test: `src/lib/server-only-guard.test.ts` reads both sources and asserts a top-level `import "server-only"`; red before the fix, green after, red again with only the two source lines reverted. Seven route tests that load the real helpers (`dudullu-readiness`, `benchmark-auth`, `calculate-vehicles`, `compare-algorithms`, `ride-confirmation`, `route-plans`, `sandbox`) failed with "cannot be imported from a Client Component module" and now use the repo's existing `vi.mock("server-only", () => ({}))` pattern.
- Verification: `npx vitest run` 78 files, 1031 tests passed; `npx tsc --noEmit` clean; `npm run build` succeeded.

---

*End of report — `UA-2026-10-01-CLAUDE` v1.1, written by Claude (Anthropic, Claude Opus 5.5 `claude-opus-5-5`) on 2026-10-01 11:01 (+03:00) and revised at 16:53 (+03:00) after the independent Codex verification.*
