# Dirty Checkout Preservation and WIP Documentation Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve every uncommitted artifact in the original rescue checkout and synchronize verified audit corrections plus the approved consolidation waivers into the authoritative WIP documentation.

**Architecture:** Keep the original checkout immutable and create a checksum-verified preservation package under `C:\tmp`. Perform documentation edits only on the isolated `codex/wip-doc-sync-20260801` branch created from the validated WIP head, then validate internal consistency before integrating locally into WIP.

**Tech Stack:** Git worktrees, PowerShell, Markdown, SHA-256.

## Global Constraints

- Do not clean, restore, switch, stage, commit, or otherwise mutate `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide`.
- Do not publish `.codex/config.toml` or its values.
- Treat `academic_benchmark/numba_results/benchmark_progress.csv` as unverified raw evidence, not a scientific result.
- Preserve the original dirty files and a binary Git patch before documentation synchronization.
- Keep `WIP` as the authoritative integration branch.
- Record the user-approved Supabase build waiver, temporary 159-warning waiver, and npm-audit debt disposition accurately.

---

### Task 1: Create and verify the lossless preservation package

**Files:**
- Source: `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide` dirty paths listed in the recovery audit
- Create: `C:\tmp\UniRide-dirty-preservation-20260801\status.txt`
- Create: `C:\tmp\UniRide-dirty-preservation-20260801\tracked-diff.patch`
- Create: `C:\tmp\UniRide-dirty-preservation-20260801\source-sha256.csv`
- Create: `C:\tmp\UniRide-dirty-preservation-20260801\copied-sha256.csv`
- Create: `C:\tmp\UniRide-dirty-preservation-20260801\files\...`

**Interfaces:**
- Consumes: the original dirty checkout without modifying it.
- Produces: a local preservation package whose copied hashes equal the source hashes.

- [ ] **Step 1: Confirm the preservation destination does not already contain an ambiguous prior snapshot**

Run:

```powershell
Test-Path -LiteralPath C:\tmp\UniRide-dirty-preservation-20260801
```

Expected: `False`, or an existing directory that is moved aside only after explicit inspection.

- [ ] **Step 2: Create the preservation directory and copy every dirty path**

Use explicit source and destination paths. Preserve the original relative directory structure, including `.codex/config.toml`, but keep the package local and untracked.

- [ ] **Step 3: Save status and the complete tracked binary patch**

Run from the original checkout:

```powershell
git status --short --branch
git diff --binary
```

Write the exact outputs to `status.txt` and `tracked-diff.patch` in the preservation directory.

- [ ] **Step 4: Hash source and copied files independently**

Use `Get-FileHash -Algorithm SHA256` and save deterministic relative-path/hash manifests as `source-sha256.csv` and `copied-sha256.csv`.

- [ ] **Step 5: Verify hash parity and original-checkout immutability**

Expected:

```text
all copied file hashes equal their source hashes
original git status is byte-for-byte unchanged
```

### Task 2: Synchronize corrected audit findings

**Files:**
- Modify: `UniRide_Ultimate_Audit.md`
- Modify: `CURRENT_ARCHITECTURE.md`
- Modify: `ACTIVE_ROADMAP.md`
- Modify: `WORKLOG.md`
- Reference only: `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\UNIRIDE_ULTIMATE_AUDIT_REVISED_2026-07-31_opencode.md`

**Interfaces:**
- Consumes: verified WIP source behavior and the revised audit's corrected findings.
- Produces: current master documentation that retires the false DataLoader claim, distinguishes latent and active risks, and records the remaining verified issues.

- [ ] **Step 1: Correct the master audit's retired-claim section**

Replace the false statement that `DataLoader.get_instance()` returns a new loader with the verified `SingletonMeta` behavior. Update stale lint, typecheck, and test-gate statements to the validated WIP evidence.

- [ ] **Step 2: Add the verified residual-risk findings**

Record these live-source findings with exact paths:

```text
optimizer_api/strategies/pso_strategy.py:53 — wall-clock seed fallback
optimizer_api/utils/data_loader.py:53-59 — Supabase client without explicit timeout
uniride_core/algorithms/cvrptw_decoder.py:95-111 — depot continue leaves prev stale
optimizer_api/strategies/promoted_config_loader.py:9-13 — production imports academic configuration
```

Distinguish the permissive CVRPTW penalty mode as latent unless a production caller enables it.

- [ ] **Step 3: Correct the architecture document**

Replace the false DataLoader-singleton statement with the verified process-level singleton behavior. Retain the real missing-timeout, cache-health, and dependency-boundary risks without implying that `get_instance()` constructs a new loader.

- [ ] **Step 4: Correct the roadmap**

Remove the false DataLoader-singleton replacement task. Retain provider timeout/cache work as a separate real task. Add explicit tasks for deterministic PSO fallback, depot-transition feasibility, promoted-config boundary isolation, and shared GIS rendering only where supported by live source.

- [ ] **Step 5: Record the documentation correction in WORKLOG**

Add a dated entry explaining that a revised audit corrected prior false positives while preserving still-open verified risks.

### Task 3: Record consolidation waivers durably

**Files:**
- Modify: `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md`
- Modify: `WORKLOG.md`

**Interfaces:**
- Consumes: explicit user approval in the orchestrating task.
- Produces: a durable manifest record closing the three conditional promotion holds without claiming those gates passed.

- [ ] **Step 1: Replace the stale no-waiver statement**

Record that the user explicitly accepted:

```text
Supabase-configured production build waiver
temporary 159-warning lint-cap waiver, with 0 lint errors
npm-audit debt disposition for consolidation
```

- [ ] **Step 2: Preserve the distinction between pass and waiver**

Do not rewrite the Supabase build as successful, the warning count as compliant, or npm advisories as remediated. State only that these were accepted as consolidation debt.

- [ ] **Step 3: Record the final promoted WIP identity**

State that `origin/WIP` was promoted and remotely verified at `0ebd63d337dc3fca1a1c9e7644910ecf2e620a79` after the approved conditions were resolved or waived.

### Task 4: Validate and integrate the documentation-only change

**Files:**
- Validate all modified Markdown files and the implementation plan.

**Interfaces:**
- Consumes: Tasks 1-3 outputs.
- Produces: a reviewable documentation-only commit ready for local WIP integration.

- [ ] **Step 1: Search for contradictory active claims**

Run targeted searches for:

```text
get_instance() returns a new loader
false DataLoader singleton
no waiver is recorded
conditional hold
origin/WIP a44d506
branches are unmerged
```

Expected: no active master-document contradiction remains; historical reports may retain dated evidence.

- [ ] **Step 2: Run repository hygiene checks**

Run:

```powershell
git diff --check
git status --short --branch
```

Expected: no whitespace errors and only intentional documentation changes.

- [ ] **Step 3: Review the final documentation diff**

Confirm that no source, tests, dependencies, databases, generated results, archives, frontend, or API files changed.

- [ ] **Step 4: Commit the documentation-only change**

Run:

```powershell
git add docs/superpowers/plans/2026-08-01-dirty-checkout-preservation-doc-sync.md UniRide_Ultimate_Audit.md CURRENT_ARCHITECTURE.md ACTIVE_ROADMAP.md WORKLOG.md WIP_CONSOLIDATION_MANIFEST_2026-08-01.md
git commit -m "docs: preserve rescue evidence and synchronize WIP audit"
```

- [ ] **Step 5: Integrate locally into WIP after review**

Fast-forward or merge the reviewed documentation branch into local `WIP`, rerun `git diff --check`, and leave pushing to `origin/WIP` as a separately reported action unless explicitly authorized.
