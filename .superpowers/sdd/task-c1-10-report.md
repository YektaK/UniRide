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

### Task 10 command traceability

These are the literal commands from the corresponding Task 10 plan steps: **Run focused gate**, **Run Package A/B/JIT regression**, and **Run full local suite and hygiene**. The drift/isolation command is the scoped verification of the Task 10 **Add drift tests** and **Strengthen production isolation** work.

```powershell
python -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task10-final --tb=short
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py academic_benchmark\tests\test_algorithm_resolution.py academic_benchmark\tests\test_algorithm_problem_validation.py academic_benchmark\tests\test_algorithm_preflight.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_algorithm_execution_gateway.py academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_smart_benchmark_preflight.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_bildiri_study_profile.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-focused --tb=short
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_bildiri_solver_parity.py academic_benchmark\tests\test_numba_jit_parity.py academic_benchmark\tests\test_solver_backend_reporting.py academic_benchmark\tests\test_fair_comparison_protocol.py academic_benchmark\tests\test_fair_comparison_scientific_integrity.py academic_benchmark\tests\test_native_termination_protocol.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_archive_manifest.py academic_benchmark\tests\test_yaem_quarantine_boundary.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-regression --tb=short
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests uniride_core\tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-full --tb=short
```

- Drift/isolation result: **24 passed in 10.10s**.
- Focused-gate result: **230 passed in 20.35s**; 22 expected deprecated-alias warnings; no promoted evidence node skipped.
- Package A/B/JIT regression result: **248 passed in 33.21s**.
- Full-suite result: **no output within the 60-second bound; process terminated**. This timeout is a blocker, not a pass.

### Post-review correction verification

```powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task10-traceability --tb=short
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py academic_benchmark\tests\test_algorithm_resolution.py academic_benchmark\tests\test_algorithm_problem_validation.py academic_benchmark\tests\test_algorithm_preflight.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_algorithm_execution_gateway.py academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_smart_benchmark_preflight.py academic_benchmark\tests\test_manifest_contracts.py academic_benchmark\tests\test_bildiri_study_profile.py academic_benchmark\tests\test_production_registry_snapshot.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-focused-traceability --tb=short
```

- Controlled RED: replacing the registry snapshot with an empty set produced `implemented CANDIDATE canonical IDs must retain academic executors` and named all eight missing candidate IDs.
- GREEN scoped drift/isolation result: **24 passed in 15.27s**.
- GREEN focused-gate result: **230 passed in 17.25s** with the same 22 expected deprecated-alias warnings.

### GWO/HHO evidence-gate closure (2026-07-29)

The formerly deferred GWO/HHO evidence action is now closed. Six exact `.venv-jit` nodes passed together (`6 passed in 2.32s`, no skips), covering symmetric TSP and directed ATSP across pure fixed/native and memetic-2opt fixed claims. The catalog/evidence/preflight set passed `74` tests, and backend/JIT/native/fair regression passed `82` tests. The current Task 10 status remains **PARTIAL** solely for its independent full-suite capacity and manifest-lifecycle gates; this result does not claim those gates complete.

### Manifest-lifecycle gate closure (2026-07-29)

The independent manifest-lifecycle gate is closed: `StudyManifestV1` and `NativeProtocolV1` accept only canonical `VERIFIED` IDs through `IdentifierSource.MANIFEST`, and canonical candidates fail Pydantic validation with stable `candidate_algorithm` semantics.
The unchanged Bildiri profile validates with its four verified declarations; no schema shape changed.
The exact Task 10 focused command was then bounded at 60 seconds and emitted no pytest output before termination, so it is not reported as a pass.
The directly relevant `.venv-jit` manifest/profile/resolution subset passed `102` tests in `1.61s`, and the schema check exited `0`.
**Task 10 remains PARTIAL:** the full suite is unrun and unclaimed.
