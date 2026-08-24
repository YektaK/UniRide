# Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the four verified correctness and validation-integrity defects and synchronize master documentation with post-fix evidence.

**Architecture:** Keep validation at existing boundaries: configuration validation in `tenant_keys()`, test collection in Vitest configuration, and environment isolation in the affected test. Preserve ignored Bildiri data outside the repository with hashes instead of deleting it, then update only the canonical root documents.

**Tech Stack:** Python 3.14, pytest, FastAPI configuration helpers, TypeScript, Vitest, Next.js 16, PowerShell, Git

## Global Constraints

- Base all claims on live source and executable checks, not historical reports.
- Preserve `opencode.json` and all unrelated worktree changes.
- Add no dependencies and change no solver, fairness, registry, database, or generated benchmark result.
- Use test-driven development for production behavior changes.
- Move ignored Bildiri artifacts losslessly to `C:\tmp\UniRide-local-artifacts-20260824` with SHA-256 verification.
- Do not commit, merge, or push without separate authorization.

---

### Task 1: Fail-closed tenant credential validation

**Files:**
- Modify: `optimizer_api/tests/test_tenant_authorization.py`
- Modify: `optimizer_api/runtime_config.py`

**Interfaces:**
- Consumes: `tenant_keys() -> dict[str, str]` and `internal_api_key() -> str | None`
- Produces: the same `tenant_keys()` return type for valid configuration, with deterministic `ValueError` rejection for ambiguous configuration

- [x] **Step 1: Write five failing tests**

Add parameterized or separate tests proving rejection of blank/whitespace-padded tenant IDs, the reserved tenant ID `internal`, whitespace-only secrets, duplicate secrets, and reuse of `INTERNAL_API_KEY`. Each test must isolate relevant environment variables with `monkeypatch`.

```python
with pytest.raises(ValueError, match="values must be unique"):
    tenant_keys()
```

- [x] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_tenant_authorization.py -q -p no:cacheprovider --tb=short
```

Expected: the newly added invalid-configuration cases fail because current validation accepts them.

- [x] **Step 3: Implement minimal validation in `tenant_keys()`**

After JSON/type validation, reject invalid identifiers and secrets before returning the mapping:

```python
if any(not tenant_id.strip() or tenant_id != tenant_id.strip() for tenant_id in parsed):
    raise ValueError("UNIRIDE_TENANT_KEYS tenant ids must be non-empty and trimmed")
if "internal" in parsed:
    raise ValueError("UNIRIDE_TENANT_KEYS cannot use reserved tenant id 'internal'")
if any(not secret.strip() for secret in parsed.values()):
    raise ValueError("UNIRIDE_TENANT_KEYS values must be non-empty strings")
if len(set(parsed.values())) != len(parsed):
    raise ValueError("UNIRIDE_TENANT_KEYS values must be unique")
shared_key = internal_api_key()
if shared_key is not None and shared_key in parsed.values():
    raise ValueError("UNIRIDE_TENANT_KEYS cannot reuse INTERNAL_API_KEY")
```

- [x] **Step 4: Re-run the focused suite and confirm GREEN**

Expected: all tests in `test_tenant_authorization.py` pass.

### Task 2: Restore deterministic test boundaries

**Files:**
- Modify: `vite.config.ts`
- Modify: `optimizer_api/tests/test_matrix_repository.py`
- External move only: ignored `academic_benchmark/bildiri2026/`

**Interfaces:**
- Consumes: Vitest's `test.include` glob list and pytest `monkeypatch`
- Produces: root-source-only frontend discovery and environment-independent matrix repository tests

- [x] **Step 1: Record the already observed RED conditions**

Record that default Vitest collected 150 files/406 tests from nested worktrees, the matrix test failed when host Supabase credentials were present, and the two quarantine tests failed because ignored local Bildiri artifacts existed.

- [x] **Step 2: Restrict Vitest to application tests**

Set:

```ts
test: {
  environment: "node",
  include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
},
```

- [x] **Step 3: Make the matrix fallback test hermetic**

Before constructing `DataLoader`, add:

```python
monkeypatch.delenv("SUPABASE_URL", raising=False)
monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
```

- [x] **Step 4: Preserve and move ignored Bildiri artifacts**

Resolve and verify both absolute paths and fail if `C:\tmp\UniRide-local-artifacts-20260824\academic_benchmark\bildiri2026` or its staging sibling already exists. Generate `C:\tmp\UniRide-local-artifacts-20260824\bildiri2026-sha256.csv` from the source with relative path, SHA-256, and byte length. Copy into a fresh `bildiri2026.staging` directory, verify every staged file against the manifest plus total count and bytes, remove only the verified ignored source directory, rename staging to `bildiri2026`, and verify again. Do not mutate the source if any pre-removal check fails.

- [x] **Step 5: Run focused validation**

Run:

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest optimizer_api/tests/test_matrix_repository.py::test_env_timeout_garbage_falls_back_to_default academic_benchmark/tests/test_bildiri_quarantine_boundary.py -q -p no:cacheprovider --tb=short
npm test -- --run
```

Expected: focused Python tests pass and Vitest collects only tests under the current worktree's root `src` directory.

### Task 3: Full verification and canonical documentation sync

**Files:**
- Modify: `README.md`
- Modify: `CURRENT_ARCHITECTURE.md`
- Modify: `ACTIVE_ROADMAP.md`
- Modify: `UniRide_Ultimate_Audit.md`
- Modify: `WORKLOG.md`

**Interfaces:**
- Consumes: exact post-fix command results from Tasks 1 and 2
- Produces: mutually consistent current-state documentation with historical entries preserved

- [x] **Step 1: Run full verification before writing evidence claims**

Run:

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short
npm test -- --run
npm run typecheck
npm run lint
npm run build
git diff --check
```

Every command must exit zero. Record exact pass, skip, warning, and route counts where the tool emits them. Stop before documentation edits if any required command fails.

- [x] **Step 2: Update current master documents**

Before editing claims, inspect the live implementations in `optimizer_api/verification/response_certifier.py`, `optimizer_api/runtime_config.py`, `optimizer_api/rate_limit.py`, and `optimizer_api/routers/optimization.py`. Use those source facts plus exact command results to correct stale test/build evidence, describe the route rendering mode and count emitted by the current build, document tenant/rate-limit environment variables, mark only the live scoped feasibility and compute-policy controls as implemented, and retain hard cancellation, durable jobs, GIS, lint, dependency audit, matrix provenance, and DouBus cleanup as open work.

- [x] **Step 3: Append a worklog entry**

Add a `2026-08-24` entry describing the tenant validation repair, frontend test-discovery boundary, hermetic matrix test, externally preserved Bildiri artifacts, files changed, and exact verification results. Do not rewrite prior worklog entries.

- [x] **Step 4: Re-run documentation-sensitive checks**

Run `git diff --check`, inspect `git status --short --branch`, and confirm the original checkout still reports the pre-existing untracked `opencode.json` and no other unrelated change.

### Task 4: Review gate

**Files:**
- Review: all files changed by Tasks 1–3

**Interfaces:**
- Consumes: complete remediation diff and verification output
- Produces: a bounded readiness verdict; no Git integration action

- [x] **Step 1: Inspect the complete diff for scope and security regressions**

Confirm valid tenant mappings retain exact values, no authentication fallback was added, no ignored artifact was lost, and documentation does not overstate production readiness.

- [x] **Step 2: Report the branch without integrating it**

Return exact files changed, external artifact destination and manifest, test/build counts, remaining deferred debt, and confirmation that no commit, merge, push, or unrelated-file modification occurred.
