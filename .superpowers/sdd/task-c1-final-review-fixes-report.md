# Package C1 Final Review Fixes Report

## Status: COMPLETE; READY TO COMMIT

Date: 2026-07-29
Branch: `codex/package-c1-capability-preflight-design`
Worktree: `C:\tmp\UniRide-wip-next`

## Outcome

The two Important findings from the whole-branch C1 review are remediated in live source:

1. CLI and Smart worker boundaries now fail closed when a catalog-governed TSP/ATSP task reaches them without a valid `GovernedExecutionRequest`; the rejection occurs before academic registry enumeration or executor lookup. Migration-specific retired-ID errors still take precedence.
2. The actual immutable `PreflightDecision` is serialized once and carried through CLI aggregates, Smart `RunResult` transport, fair-pilot records, CSV output, and database metadata. Persisted provenance includes requested and canonical IDs, backend policy, selected stage profile, fallback used/reason, executor registry ID, and capability evidence IDs.

The governed CLI aggregator also retains the established per-replicate fairness and route/feasibility fields. This prevents the safety fix from degrading the scientific result contract.

## Controlled RED evidence

### Missing request at worker boundaries

```powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_smart_benchmark_preflight.py::test_cli_worker_rejects_ungoverned_catalog_task_before_registry_access academic_benchmark/tests/test_smart_benchmark_preflight.py::test_smart_worker_rejects_ungoverned_catalog_task_before_registry_access -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-final-boundary-red --tb=short
```

Result before implementation: `2 failed`. CLI reached the exploding registry enumeration; Smart returned without the required rejection.

### Missing decision serializer/provenance

```powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_algorithm_execution_gateway.py::test_preflight_decision_serializer_preserves_complete_provenance academic_benchmark/tests/test_smart_benchmark_preflight.py::test_cli_governed_task_uses_gateway_without_legacy_direct_fallback academic_benchmark/tests/test_smart_benchmark_preflight.py::test_smart_governed_task_carries_prefer_numba_fallback_provenance academic_benchmark/tests/test_smart_benchmark_preflight.py::test_smart_persistence_includes_preflight_decision_metadata -q -p no:cacheprovider --tb=short
```

Result before implementation: collection error because `serialize_preflight_decision` did not exist.

## GREEN verification

### Boundary and provenance nodes

The six boundary/serializer/transport/persistence nodes passed together: `6 passed in 5.39s`.

The direct CLI database/CSV persistence regression passed separately: `1 passed in 2.41s`.

### Compatibility recovery

The first expanded focused run exposed two stale fixtures: a fair-pilot fake decision lacked identity resolution, and a six-item governed CLI fixture violated the new boundary. After converting them to truthful governed fixtures, the two nodes passed: `2 passed in 4.31s`.

The first complete academic run then exposed migration-order and four legacy-alias wrapper fixtures. Migration validation was restored before the missing-request guard, and each alias wrapper now resolves its requested alias, carries a canonical fixed-budget request, and uses bounded atomic initialization parameters. The four wrapper cases passed: `4 passed in 3.36s`.

### Focused C1 regression

```powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_smart_benchmark_preflight.py academic_benchmark/tests/test_algorithm_execution_gateway.py academic_benchmark/tests/test_fair_pilot_cli.py academic_benchmark/tests/test_fair_protocol_v2_metadata.py academic_benchmark/tests/test_fair_comparison_protocol.py academic_benchmark/tests/test_fair_comparison_scientific_integrity.py academic_benchmark/tests/test_algorithm_preflight.py academic_benchmark/tests/test_algorithm_preflight_boundaries.py academic_benchmark/tests/test_algorithm_resolution.py academic_benchmark/tests/test_cli_engine_param_db_save.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-final-focused-green-2 --tb=short
```

Result: `234 passed, 30 warnings in 6.32s`.

### Full academic gate

```powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-final-academic-2 --tb=short
```

Historical first-review result: `780 passed, 42 warnings in 120.03s`. A later independent review required additional binding and CSV compatibility hardening; see below.

## Files changed

Production:

- `academic_benchmark/core/execution_gateway.py`
- `academic_benchmark/cli_engine.py`
- `academic_benchmark/smart_benchmark.py`
- `academic_benchmark/fair_pilot.py`
- `academic_benchmark/benchmark_utils.py`

Tests:

- `academic_benchmark/tests/test_algorithm_execution_gateway.py`
- `academic_benchmark/tests/test_smart_benchmark_preflight.py`
- `academic_benchmark/tests/test_fair_pilot_cli.py`
- `academic_benchmark/tests/test_fair_comparison_scientific_integrity.py`
- `academic_benchmark/tests/test_core_tsp_registry.py`

Process artifacts:

- `docs/superpowers/plans/2026-07-29-c1-final-review-fixes.md`
- `.superpowers/sdd/task-c1-final-review-fixes-report.md`

## Compatibility and scope

- Genuine non-C1 routing tasks retain six-field/request-less compatibility.
- Retired/forbidden IDs retain their canonical replacement error before any registry access.
- Catalog-governed canonical IDs and approved aliases require the immutable request at worker boundaries.
- No solver equations, catalog claims, evidence IDs, manifests, production strategy registry, dependency files, databases, archives, frontend code, or generated benchmark outputs changed.
- The previously reported optional OR-Tools environment mismatch remains outside C1 and was not modified.

## Review and commit

Final independent re-review found no Critical, Important, or Minor issues and confirmed all prior blockers closed. The Git commit containing this report is its immutable commit identity.
## Second independent-review hardening

The original reviewer found two deeper gaps after the first fix set: request presence did not bind the request to the task identity, and appending a wider row to an existing progress CSV left the old header unchanged.

A controlled six-node RED run produced `6 failed in 7.15s`: mismatched CLI/Smart requests reached registry observation, governed requests attached to routing tasks were not rejected, Smart reordered a forbidden migration error, and the existing CSV header remained narrow.

The completed implementation now:

- resolves the task ID and requires its canonical ID to equal the request canonical ID before registry access;
- rejects governed requests attached to real non-C1 routing tasks;
- runs Smart migration validation before worker request validation;
- atomically rewrites an existing CSV to the merged header in the same directory, preserves all existing rows, and then appends the new row.

The same six nodes passed: `6 passed in 2.88s`.

Expanded focused verification passed `275 passed, 42 warnings in 6.55s`.

The first final full run found one quarantine-only test-source violation caused by a literal retired alias. The migration-order test now derives the alias from the authoritative migration map; the behavior and quarantine nodes passed `2 passed in 7.86s`.

Final exact academic gate:

```powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-final-academic-4 --tb=short
```

Result: `786 passed, 42 warnings in 149.58s`. No skips or failures.
## Final independent review

The original whole-branch reviewer re-inspected the completed diff and reported:

- Critical: none.
- Important: none.
- Minor: none.
- All request-binding, non-C1 rejection, migration-order, provenance-persistence, and existing-CSV compatibility blockers are closed.
- `git diff --check` exited 0.
- Ready to commit: yes.
