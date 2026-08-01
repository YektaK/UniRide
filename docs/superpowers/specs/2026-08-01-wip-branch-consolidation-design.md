# WIP Branch Consolidation Design

**Date:** 2026-08-01
**Status:** Approved approach; implementation pending
**Target branch:** `WIP`
**Implementation branch:** `codex/wip-consolidation-20260801`
**Validated spine:** `codex/package-c1-capability-preflight-design` at `0882081`

## 1. Purpose

UniRide currently has several local and remote branches representing partially overlapping recovery, academic-extraction, governance, audit, and Phase 0 production-hardening work. This design establishes one authoritative development line without losing provenance, importing generated artifacts, or repeating already-integrated changes.

The result will make `WIP` the sole shared integration branch for ongoing work. Feature branches remain short-lived and must merge into `WIP` only after their defined validation gates pass.

## 2. Verified Repository Reality

The following topology was verified after `git fetch --prune origin`:

| Ref | Head | Relationship to current `WIP` (`a44d506`) | Consolidation treatment |
|---|---:|---|---|
| `WIP`, `origin/WIP` | `a44d506` | Current integration base | Fast-forward target only |
| `codex/reconcile-native-protocol` | `002d461` | Already an ancestor of `WIP` | Do not merge |
| `codex/package-b-bildiri-extraction` | `9efaa91` | 30 commits after `WIP` | Already contained in C1 |
| `codex/package-c1-capability-preflight-design` | `0882081` | 69 commits after `WIP` | Authoritative spine |
| `origin/copilot/evaluate-implementations` | `9efaa91` | Exact Package B duplicate | Do not merge |
| `origin/copilot/check-implementations-and-refactor` | `0882081` | Exact C1 duplicate | Do not merge |
| `codex/local-rescue-20260721` | `e0824b4` | Diverged from `3534ae8`; 8 branch-only commits, 6 patch-unique, and 34 WIP-only commits | Selective reconstruction only |
| `origin/copilot/evaluate-last-15-commits` | `90cd1bb` | One unique documentation-only commit | Evidence only; do not merge |
| older Copilot evaluation refs | various | Already ancestors of `WIP` | Do not merge |
| `origin/main` | `b6e9220` | Divergent legacy line with merge base `ab0232e` | Never merge into `WIP` |

Package C1 contains Package B in full. Advancing from C1 therefore incorporates Package A, Package B, and Package C1 exactly once.

## 3. Governing Decisions

### 3.1 Single integration spine

`codex/wip-consolidation-20260801` starts at C1 `0882081`. No merge commit is required for Package B or Package A because both are already ancestors of that head.

### 3.2 Selective reconstruction, not branch merging

`codex/local-rescue-20260721` must not be merged or cherry-picked as a range. Its history overlaps older academic work and its resulting tree contains generated Numba cache binaries. Potentially useful Phase 0 behavior will be independently reconstructed on the C1 spine and validated in the consolidated context.

### 3.3 Evidence-gated admission

A rescue change is admitted only when all of the following are true:

1. Its intended behavior is still absent from C1.
2. It is not superseded by Package B or C1.
3. Its source diff can be isolated from generated, historical, or unrelated material.
4. A focused regression test, build check, or deterministic static gate proves the behavior.
5. It passes the full validation matrix after integration.

Commit ancestry and commit names are not sufficient evidence of correctness.

### 3.4 Preservation before mutation

Before `WIP` moves, the old integration and rescue heads must remain recoverable:

- Record exact full SHAs in the consolidation manifest.
- Create `archive/pre-wip-consolidation-20260801` at the recorded pre-consolidation `origin/WIP` SHA.
- Create `archive/local-rescue-20260721` at `e0824b42d2251cfd479207d756798913a2313b31`.
- Refuse a tag-name collision unless the existing tag peels to the required recorded commit.
- Push both annotated tags and verify their remote peeled targets with `git ls-remote --tags origin` before moving `WIP`.
- Do not delete local or remote source branches during consolidation.
- Do not rewrite any source branch.

A local-only preservation tag is insufficient because no current remote branch contains the rescue head.

### 3.5 Fast-forward-only WIP promotion

The final consolidation head must descend from `origin/WIP`. Promotion uses a normal fast-forward push. Force-push, `reset --hard`, history replacement, and merge of unrelated histories are prohibited.

## 4. Source Admission Matrix

### 4.1 Academic benchmark work

| Source | Decision | Reason |
|---|---|---|
| Package A / reconcile | Retain through ancestry | Already in WIP |
| Package B | Retain through C1 ancestry | C1 contains all 30 Package B commits |
| Package C1 | Retain as canonical spine | Latest validated academic ownership, preflight, provenance, and quarantine work |
| rescue commit `3eea998` | Reject as a whole | Academic behavior is older and superseded by Package B/C1 |
| rescue commits `092efe3`, `253155c` | Do not reapply | Patch-equivalent work is already in WIP |
| historical benchmark outputs | Preserve only on existing refs/archive | Not active source and not consolidation input |

### 4.2 Phase 0 production work requiring reconstruction review

| Rescue commit | Candidate behavior | Treatment |
|---|---|---|
| `61c36c1` | API authentication boundary and proxy/header behavior | Reconstruct with backend security tests |
| `dcd5896` | Python dependency constraints | Reconcile against C1 packaging and verify clean installation metadata |
| `ea75581` | Direct ESLint gate and package script changes | Reconstruct with lockfile consistency and lint verification |
| `1e42652` | Python CI, React hook lint restoration, UI lint fixes | Split into CI, lint-policy, and bounded UI changes; exclude stale roadmap/worklog edits |
| `e0824b4` | Sandbox encoding repair and `use-mobile` hydration behavior | Reconstruct only if current C1 source still exhibits the defects; add focused checks |

Before any edit, the implementation must create a per-path and, where a file mixes concerns, per-hunk candidate ledger. Every item is classified as `admit`, `superseded`, `reject`, or `blocked`, with live C1 evidence and its validation command. Unclassified content defaults to `reject`. The implementation plan must inspect these candidates separately and must not use a range cherry-pick.

The mixed `1e42652` patch has these binding classifications:

| Path or concern | Default classification |
|---|---|
| `.github/workflows/ci.yml` | Candidate; reconstruct against current commands |
| `eslint.config.mjs` and `.eslintrc.json` deletion | Candidate only after the flat-config lint gate is proven |
| bounded TypeScript/TSX lint fixes | Candidate per hunk with focused lint/typecheck evidence |
| `requirements-lock.txt` | Reject historical file copy; regenerate only if the dependency task independently requires a lock artifact |
| `optimizer_api/routers/benchmark.py` | Reject historical hunk; security behavior must be independently specified and tested in its own task |
| `uniride_core/algorithms/tsplib_parser.py` | Reject; no academic hunk may be reconstructed without a newly reproduced C1 defect and separate user authorization |
| `ACTIVE_ROADMAP.md` and `WORKLOG.md` | Reject as stale historical edits; write current consolidation records instead |

These defaults can be made stricter without user input. Relaxing a `reject` classification requires new live evidence and explicit user authorization.

### 4.3 Explicitly prohibited imports

The following material must never enter the consolidated tree:

- `.numba_cache/`, `*.nbc`, or `*.nbi` files
- `__pycache__/`, `.pytest_cache/`, `.next/`, build outputs, newly generated benchmark outputs, or local virtual environments
- dirty files from the original checkout
- the two audit-only files in `90cd1bb`
- obsolete branch analysis documents presented as implementation
- experimental changes from `origin/main`

This prohibition is evaluated relative to C1 `0882081`. C1 already contains intentionally tracked benchmark evidence under `academic_benchmark/numba_results` and `academic_benchmark/sota_results`. Consolidation must:

1. inventory and hash those pre-existing tracked files in the consolidation manifest;
2. preserve them byte-for-byte unless the user separately authorizes archival or removal;
3. prove no additional rescue-derived or test-generated benchmark output becomes tracked;
4. continue to prohibit all Numba cache binaries.

## 5. External Audit Recheck Boundary

The supplied `UNIRIDE_ULTIMATE_AUDIT_REVISED_2026-07-31_opencode.md` is evidence, not authority. Its topology section is superseded by the live Git graph. Targeted C1 source inspection reconfirmed these open issues:

- wall-clock fallback seeds in production metaheuristic strategies;
- Supabase client construction without an explicit timeout;
- CVRPTW feasibility traversal that skips a depot without resetting `prev`;
- production imports from `academic_benchmark.promoted_configs`;
- promoted parameter names that can pass through without consumer recognition;
- absence of a reusable GIS map implementation.

The report correctly retracts its earlier DataLoader singleton claim: C1's `SingletonMeta` caches instances, and `DataLoader.get_instance()` delegates to that metaclass.

These findings are not silently fixed during branch consolidation. They become a separate, prioritized post-consolidation remediation package so Git recovery is not mixed with unrelated behavioral changes.

## 6. Consolidation Execution Flow

1. **Snapshot:** record all relevant refs, full SHAs, merge bases, worktree statuses, and remote URL.
2. **Preserve:** create, push, and remotely verify the two annotated preservation tags.
3. **Baseline:** run and record exact academic, backend, frontend, and packaging commands on the clean C1-derived worktree before reconstruction.
4. **Characterize each Phase 0 candidate:** build the per-path/per-hunk ledger, compare intended behavior with C1, and classify every item as `admit`, `superseded`, `reject`, or `blocked`.
5. **Implement admitted behavior:** use test-first, bounded commits on the consolidation branch. Recreate behavior in current files instead of copying historical files blindly.
6. **Artifact audit:** prove prohibited generated files are absent and `.gitignore` covers relevant local artifacts.
7. **Full validation:** repeat the exact baseline commands in the same environment, run all additional required suites, and record commands, counts, skips, warnings, and environment blockers.
8. **Independent diff review:** inspect the complete `origin/WIP..HEAD` diff and the narrower `C1..HEAD` Phase 0 diff.
9. **Manifest:** add a root-level consolidation manifest containing selected/rejected refs and hunks, the immutable C1 evidence-file hash inventory, commit decisions, verification evidence, and remaining audit backlog.
10. **Promote:** push the consolidation branch, then fast-forward `WIP` and verify `origin/WIP` equals the validated head.
11. **Stabilize:** perform a clean checkout smoke verification from `origin/WIP` before recommending branch archival.

## 7. Conflict and Failure Policy

- Stop on every semantic conflict; do not use blanket `ours` or `theirs` resolution.
- Preserve current C1 academic contracts when Phase 0 work touches the same file.
- If a candidate lacks a deterministic validation mechanism, classify it as blocked rather than importing it speculatively.
- Functional or test failures always block promotion.
- Baseline and final results must use the same commands and environment; final failures and unexpected skips must not exceed the baseline.
- A red baseline may be characterized, but it cannot conceal a new failure or justify moving `WIP`.
- If final validation fails, do not move or push `WIP`. The consolidation branch remains available for repair.
- If the remote advances during work, fetch and re-evaluate ancestry. Do not force the push.
- Only genuine environment-only blockers may be waived. Every waiver requires explicit user acceptance and must be recorded in the manifest before `WIP` moves.

## 8. Validation Gates

### 8.1 Git integrity

- clean consolidation worktree;
- `git diff --check` passes;
- `git merge-base --is-ancestor origin/WIP HEAD` succeeds;
- no newly tracked prohibited artifact exists relative to C1;
- pre-existing C1 benchmark evidence matches the manifest hash inventory;
- local preservation tags resolve to the recorded SHAs;
- remote tag verification resolves to the same peeled SHAs.

### 8.2 Academic benchmark

- focused manifest, archive, capability, preflight, parity, ATSP, and JIT/fallback tests;
- full `academic_benchmark/tests` suite;
- accurate reporting of skips and optional dependency blockers;
- no large benchmark experiment generation.

### 8.3 Backend and core

- `uniride_core` tests;
- optimizer API tests relevant to authentication, benchmark routing, feasibility, data loading, and strategy construction;
- Python import/compile or equivalent packaging checks;
- dependency metadata consistency.

### 8.4 Frontend

- dependency lockfile consistency;
- ESLint;
- TypeScript typecheck;
- frontend unit tests;
- production build when the environment permits it.

### 8.5 Promotion

- consolidation branch is pushed successfully;
- `WIP` fast-forwards without force;
- remote SHA verification succeeds;
- a fresh worktree at `origin/WIP` passes a small smoke set.

## 9. Deliverables

The consolidation produces:

1. a validated `WIP` head containing Package A, Package B, Package C1, and only accepted Phase 0 behavior;
2. `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md` at repository root;
3. atomic implementation commits grouped by behavior and validation boundary;
4. a per-path/per-hunk admission ledger and immutable C1 evidence-file hash inventory in the manifest;
5. preserved source branches and remotely verified recovery tags;
6. a post-consolidation remediation backlog for verified audit findings;
7. a branch-retirement recommendation, executed only after the user approves cleanup.

## 10. Acceptance Criteria

Consolidation is complete only when:

- Package B is present exactly once through C1 ancestry;
- no active code is lost from the validated academic line;
- every admitted Phase 0 behavior has current-context validation;
- no new generated cache or benchmark output is tracked relative to C1, and pre-existing evidence is unchanged;
- all functional and test gates pass with no increase in failures or unexpected skips;
- any environment-only blocker is explicitly documented and accepted by the user before promotion;
- `origin/WIP` points at the verified consolidation head through a fast-forward update;
- the original dirty checkout and all unrelated user changes remain untouched;
- no source branch is deleted as part of this package.
