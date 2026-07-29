# Package C1 Task 10 Gate Report

## Status: PARTIAL (2026-07-29)

### Completed checks

- Catalog drift tests prove each VERIFIED canonical ID has a direct academic registry executor; all implemented CANDIDATE IDs have executors; and all PLANNED IDs have none.
- Lifecycle truth is frozen: TwoOpt and ThreeOpt are VERIFIED; OrOpt, GA, PSO, GWO/HHO pure and memetic-2opt, and ALNS are CANDIDATE; four 3-opt/ALNS hybrids are PLANNED.
- Every published claim evidence ID must name an exact `test_` function in its declared source file and is executed in a subprocess. All promoted evidence nodes passed without skipping.
- Both production mappings retain the exact 38-key snapshot. A fresh subprocess import of `optimizer_api.strategies` leaves `uniride_core.algorithms.capabilities` unloaded.

### Verification

- New drift/isolation subset using ordinary Python: 24 passed in 10.08s. The initial sandboxed run failed only because it could not create `C:\tmp\pytest-c1-task10-new`; the elevated rerun passed.
- Focused `.venv-jit` gate: 230 passed in 20.35s. It emitted 22 expected deprecated-alias warnings. No promoted evidence node skipped.
- Package A/B/JIT regression: 248 passed in 33.21s.
- Full `.venv-jit` suite command was started with a 60-second bound, emitted no output, and was terminated. It is an unresolved no-output/capacity blocker, not a pass.
- `git diff --check` was clean before this status note; rerun after adding it is required before commit.

### Deferred gates

- `StudyManifestV1` still permits canonical CANDIDATE IDs structurally; their rejection remains at preflight. Moving lifecycle rejection into manifest validation is deferred because it conflicts with the JIT-promotion recovery path. No Bildiri-specific special case was added.
- Gate C1 is not closed until the full suite completes and the manifest-lifecycle conflict is resolved.

### Next evidence action

- Run separately bounded GWO/HHO native JIT evidence for each requested problem/protocol/backend tuple, then review the resulting exact accounting, termination, route, and backend data before any lifecycle promotion. Task 10 makes no promotion.

### Scope

- No production registry, capability catalog, solver, manifest-contract, or study-profile implementation changed.
- No generated benchmark/report/database artifacts were created.
