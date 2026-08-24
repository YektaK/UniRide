# Audit Remediation Design

**Status:** Approved on 2026-08-24
**Evidence base:** `WIP` commit `fef5a2b537da7068b51b3b3a50c6d633a2853404` plus live source and test execution
**Scope:** Minimal correctness and validation-integrity repairs only

## Objective

Close four verified defects without expanding product behavior: fail closed on ambiguous tenant credentials, prevent Vitest from collecting tests in nested worktrees, make one environment-sensitive repository test hermetic, and remove ignored local Bildiri artifacts from the active repository boundary without destroying them. Synchronize current master documentation with the verified result.

## Design Decisions

### Tenant configuration

`optimizer_api.runtime_config.tenant_keys()` remains the single validation boundary for `UNIRIDE_TENANT_KEYS`. It will reject:

- blank or whitespace-padded tenant identifiers;
- the reserved tenant identifier `internal`;
- blank or whitespace-only tenant secrets;
- duplicate tenant secrets;
- a tenant secret equal to `INTERNAL_API_KEY`.

The function will not silently trim identifiers or secrets. Existing valid mappings retain their exact keys and values. Authentication and rate-limit code remain unchanged because a valid mapping makes their current behavior unambiguous.

### Frontend test discovery

Vitest will collect only the current worktree's root application tests matching `src/**/*.test.ts` and `src/**/*.test.tsx`. Nested `.temp/worktrees` content is excluded by construction rather than by enumerating transient directories.

### Hermetic test configuration

The timeout-fallback test will explicitly remove Supabase credentials before constructing `DataLoader`. This preserves the test's stated coordinate-mode precondition and does not change production provider selection.

### Local Bildiri artifacts

The ignored `academic_benchmark/bildiri2026` directory in the original checkout is workspace residue, not tracked source. It will be copied first to a fresh staging directory below `C:\tmp\UniRide-local-artifacts-20260824`, then checked against a manifest containing relative path, SHA-256, and byte length. Only after complete verification will the original ignored directory be removed and the staging directory renamed to `academic_benchmark\bildiri2026`. The operation fails closed if the preservation destination already exists. No tracked Bildiri code is created, changed, or deleted.

### Documentation

`README.md`, `CURRENT_ARCHITECTURE.md`, `ACTIVE_ROADMAP.md`, and `UniRide_Ultimate_Audit.md` will state only post-remediation evidence. `WORKLOG.md` will receive a new dated entry; historical entries will not be rewritten. Open work such as hard request cancellation, durable jobs, GIS validation, lint debt, dependency-audit debt, and dead DouBus code remains explicitly open.

## Validation

Acceptance requires:

1. focused tenant validation tests pass after demonstrating RED failures;
2. the matrix repository test passes with Supabase variables present in the caller environment;
3. the two Bildiri quarantine boundary tests pass after the external move;
4. default Vitest execution collects only the current worktree's root `src` tests;
5. full Python, frontend test, TypeScript, ESLint, and production build commands all exit zero, with exact pass/skip/warning and route counts recorded where emitted;
6. `git diff --check` passes and the original checkout still contains untouched `opencode.json`;
7. documentation statements about feasibility certificates, compute controls, tenant/rate-limit configuration, and route rendering are tied to live-source inspection, passing tests, or the current build output; documentation updates stop if a required validation fails.

## Explicit Deferrals

- No DouBus deletion or broader refactor.
- No new server-side optimization timeout, process isolation, or durable job queue.
- No lint-warning sweep or dependency upgrade.
- No solver, fairness protocol, registry, database, or academic-result changes.
- No commit, merge, or push without separate authorization.
