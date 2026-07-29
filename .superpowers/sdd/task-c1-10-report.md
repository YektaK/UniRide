# Package C1 Task 10 Gate Report

## Status: COMPLETE (2026-07-29)

## Current executive state

- `406a1ab` promoted the evidenced GWO/HHO pure and memetic-2opt canonical IDs to `VERIFIED`.
- `15a45ff` closed the manifest-lifecycle gate: primary and native manifest lists accept only exact canonical `VERIFIED` IDs and reject all candidates, plans, aliases, forbidden IDs, and unknown IDs.
- The unchanged Bildiri profile validates with its four verified canonical declarations; no study-specific exception exists.
- The academic suite is green at 774 passed. The broader academic plus uniride_core command completed with 978 passed, 1 skipped, and 9 OR-Tools-only failures caused by OR-Tools being absent from .venv-jit; the same 12 OR-Tools integration tests pass in the system interpreter where OR-Tools is installed.

### Historical checkpoint (superseded by 406a1ab and 15a45ff)

- Catalog drift tests prove each VERIFIED canonical ID has a direct academic registry executor; all implemented CANDIDATE IDs have executors; and all PLANNED IDs have none.
- Historical lifecycle truth: TwoOpt and ThreeOpt were VERIFIED; OrOpt, GA, PSO, GWO/HHO pure and memetic-2opt, and ALNS were CANDIDATE; four 3-opt/ALNS hybrids were PLANNED.
- Every published claim evidence ID must name an exact `test_` function in its declared source file and is executed in a subprocess. All promoted evidence nodes passed without skipping.
- Both production mappings retain the exact 38-key snapshot. A fresh subprocess import of `optimizer_api.strategies` leaves `uniride_core.algorithms.capabilities` unloaded.

### Verification

- New drift/isolation subset using ordinary Python: 24 passed in 10.08s. The initial sandboxed run failed only because it could not create `C:\tmp\pytest-c1-task10-new`; the elevated rerun passed.
- Focused `.venv-jit` gate: 230 passed in 20.35s. It emitted 22 expected deprecated-alias warnings. No promoted evidence node skipped.
- Package A/B/JIT regression: 248 passed in 33.21s.
- Full `.venv-jit` suite command was started with a 60-second bound, emitted no output, and was terminated. It is an unresolved no-output/capacity blocker, not a pass.
- `git diff --check` was clean before this status note; rerun after adding it is required before commit.

### Historical deferred gates (superseded by 406a1ab and 15a45ff)

- Historical checkpoint: `StudyManifestV1` still permitted canonical CANDIDATE IDs structurally and deferred their rejection to preflight because of the JIT-promotion recovery path. No Bildiri-specific special case was added.
- Gate C1 is not closed until the full suite completes and the manifest-lifecycle conflict is resolved.

### Historical next evidence action (superseded by 406a1ab and 15a45ff)

- Run separately bounded GWO/HHO native JIT evidence for each requested problem/protocol/backend tuple, then review the resulting exact accounting, termination, route, and backend data before any lifecycle promotion. Task 10 makes no promotion.

### Historical scope (superseded by 406a1ab and 15a45ff)

- At this historical checkpoint, no production registry, capability catalog, solver, manifest-contract, or study-profile implementation changed.
- No generated benchmark/report/database artifacts were created.

### Historical Task 10 command traceability

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

The formerly deferred GWO/HHO evidence action is now closed. Six exact `.venv-jit` nodes passed together (`6 passed in 2.32s`, no skips), covering symmetric TSP and directed ATSP across pure fixed/native and memetic-2opt fixed claims. The catalog/evidence/preflight set passed `74` tests, and backend/JIT/native/fair regression passed `82` tests. At that historical checkpoint, Task 10 was **PARTIAL** for independent full-suite capacity and manifest-lifecycle gates; this result did not claim those gates complete.

### Manifest-lifecycle gate closure (2026-07-29)

The independent manifest-lifecycle gate is closed: `StudyManifestV1` and `NativeProtocolV1` accept only canonical `VERIFIED` IDs through `IdentifierSource.MANIFEST`, and canonical candidates fail Pydantic validation with stable `candidate_algorithm` semantics.
The unchanged Bildiri profile validates with its four verified declarations; no schema shape changed.
The exact Task 10 focused command was then bounded at 60 seconds and emitted no pytest output before termination, so it is not reported as a pass.
The directly relevant `.venv-jit` manifest/profile/resolution subset passed `102` tests in `1.61s`, and the schema check exited `0`.
**Task 10 remains PARTIAL:** the full suite is unrun and unclaimed.

### Final Gate C1 closure (2026-07-29)

Gate C1 is complete for its approved canonical academic TSP/ATSP scope.

- Compatibility closure commit b458cba migrated only historical V1 local-search IDs, preserved strict V2 canonical manifests, and passed 19 focused plus 89 related tests.
- Smart-policy closure commit f43d0fd replaced stale candidate fixtures, made Smart carry the caller-declared backend policy, and passed 35 Smart plus 117 resolver/preflight/gateway tests.
- Exact academic gate:
  C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short
  Result: 774 passed, 34 expected deprecated-alias warnings in 97.95s.
- Exact broader gate:
  C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests uniride_core\tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-full-final --tb=short
  Result: 978 passed, 1 skipped, 9 failed, 34 warnings in 115.53s. All nine failures report the single environment cause OR-Tools not installed; no C1 TSP/ATSP capability or preflight test failed.
- Optional-solver separation:
  python -m pytest uniride_core/tests/test_ortools_cvrp_engine.py uniride_core/tests/test_holistic_matrix_engine.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-ortools-system --tb=short
  Result: 12 passed, 3 upstream SWIG deprecation warnings in 10.36s using the system interpreter with OR-Tools 9.15.6755.
- pyproject.toml keeps OR-Tools in the excluded solvers extra rather than the .venv-jit test extra. This is a reproducibility follow-up outside C1, not a hidden test pass or a source defect.
- git diff --check and final branch hygiene are required immediately before the closure commit.

This closure follows the approved design requirement to separate optional-solver environment failures from source defects and its acceptance criterion that proportionate local suites pass with external environment blockers identified precisely.