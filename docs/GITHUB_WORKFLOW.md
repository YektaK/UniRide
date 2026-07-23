# UniRide GitHub Workflow

**Verified:** 2026-07-16

This runbook defines the contribution and review process. It does not claim the current CI gates are green; known failures are listed below.

## 1. Branch and Change Discipline

- Start from the repository's designated integration branch.
- Use a focused branch for each change; Codex-created branches should use the `codex/` prefix.
- Do not combine mathematical corrections, dependency upgrades, UI redesign, and generated benchmark results in one review.
- Preserve unrelated dirty-tree changes.
- Never commit credentials, local environment files, databases, logs, caches, or raw benchmark outputs unless explicitly approved.

Before work:

```powershell
git status --short --branch
git rev-parse HEAD
```

Record the starting commit in audit-sensitive work.

## 2. Documentation Authority

Reviewers should resolve conflicts in this order:

1. live code and reproducible verification;
2. `UniRide_Ultimate_Audit.md`;
3. `CURRENT_ARCHITECTURE.md`;
4. `ACTIVE_ROADMAP.md`;
5. current operational runbooks;
6. archived historical material.

Nothing under `archive/` is a current implementation instruction.

## 3. Local Verification

### Frontend

```powershell
npm ci
npm test -- --run
npm run typecheck
npm run lint
```

Current baseline:

- unit tests pass;
- typecheck is blocked by an inconsistent local dependency install plus source typing errors;
- lint script/configuration requires repair.

A pull request must not describe these gates as passing unless the posted command output comes from a clean install.

### Python

Use a clean supported virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r optimizer_api\requirements.txt
python -m pip install -e ".[test]"
python -m pytest uniride_core\tests optimizer_api\tests academic_benchmark\tests -q --tb=short
```

Current baseline is blocked by an incompatible Pydantic installation in the audit environment. Dependency/environment failure must be separated from source-test failure.

### Focused correctness gates

Mathematical changes require targeted tests for:

- duplicate customer occurrences at one location;
- exact customer coverage;
- SW/SO capacity;
- maximum duration;
- pickup/dropoff time windows;
- missing and asymmetric arcs;
- deterministic seed replay;
- comparison with exact/reference solvers on small instances.

### Diff checks

```powershell
git diff --check
git status --short
git diff --stat
```

Inspect the full diff before staging.

## 4. Benchmark Evidence Policy

Raw generated CSV/JSON/database outputs are evidence artifacts, not source code.

Default policy:

- keep raw outputs untracked;
- publish a curated Markdown report;
- record command, commit, dataset, matrix semantics, seed schedule, parameters, environment, and hardware;
- report all failed/infeasible runs;
- never compute/promote a gap without feasibility certification.

If raw evidence must be versioned, use an explicitly approved path and explain retention/size policy in the pull request.

## 5. Pull Request Requirements

Every pull request should include:

- objective and scope;
- exact affected components;
- risk and rollback notes;
- test commands and results;
- environment/dependency caveats;
- screenshots for visible UI changes;
- before/after evidence for performance claims;
- matrix/dataset/seed provenance for algorithm changes;
- documentation updates where contracts or architecture change.

For algorithmic changes, also include:

- objective definition;
- hard versus soft constraint policy;
- feasibility-certificate result;
- deterministic replay evidence;
- reference-solver or exact-instance comparison;
- ablation where a new research mechanism is claimed.

## 6. Review Discipline

Reviewers must:

- require exact file/line references;
- separate confirmed defects from hypotheses;
- verify severity independently;
- reject unsupported P0/P1 claims;
- check runtime dispatch and blast radius before approving removals;
- confirm archived documents were not used as current truth;
- verify migrations and DTO changes end to end;
- check that optional dependencies fail gracefully.

No strategy may be archived merely because a historical report called it superseded. Pipeline A remains active.

## 7. Required CI Target State

Branch protection should eventually require:

1. frontend unit tests;
2. TypeScript typecheck;
3. ESLint with zero warnings for correctness rules;
4. Python import/collection check;
5. core unit/regression suite;
6. optimizer API contract tests;
7. academic benchmark tests that do not require network;
8. feasibility and deterministic-replay gates;
9. secret scanning;
10. dependency vulnerability review;
11. documentation-link/contract drift checks.

CPU-heavy publications and large DOE runs belong in scheduled/manual workflows, not every pull request.

## 8. Secrets and Environments

- Store repository/deployment secrets in the platform's encrypted secret store.
- Use minimum scope and expiration/rotation policies.
- Never place service-role keys in `NEXT_PUBLIC_*` variables.
- Never paste real keys into issues, pull requests, test output, documentation, or benchmark metadata.
- Treat previously exposed credentials as compromised and rotate them.
- Development reset must remain disabled by default.

## 9. Merge and Release

Before merge:

- required checks pass in a clean environment;
- approvals are complete;
- generated artifacts and dirty-tree state are understood;
- documentation matches the changed behavior;
- no unresolved feasibility or security regression exists.

For releases:

- record and verify the release commit;
- use an annotated tag when tags are required;
- verify both `git rev-parse HEAD` and the peeled tag commit;
- attach reproducibility manifests to academic releases;
- do not label UniRide production-ready while Phase 1 release blockers remain open.

## 10. Historical Workflow Material

The prior workflow document is preserved at `archive/docs/GITHUB_WORKFLOW.md`. It contains useful historical review discipline but also obsolete commands and unsafe credential-lifetime advice. It must not be followed directly.
