# UniRide Worklog

This is a curated chronology. It records verified work and does not turn archived reports or agent assertions into current truth.

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
