# Task 4 report: strict ALNS pilot admission

## Outcome

- Added `ALNS-TSP` to the exact fair and native pilot admission sets while retaining the existing native Or-opt extension.
- Fair protocol v2 rejects local-search policy fields for ALNS and delegates its scientific parameter contract to `validate_scientific_alns_params`.
- Native admission derives ALNS required and allowed keys directly from `ALNS_REQUIRED_PARAMS` and `ALNS_OPTIONAL_PARAMS`, then invokes the same shared validator after exact algorithm-set admission.
- Added fair-v2 and native loader tests for exact canonical ALNS blocks and byte-identical shared-validator errors for invalid ALNS parameters.
- Existing pilot record/replay coverage and C3 ALNS evidence remain green. ALNS gateway/preflight capability admission is deliberately not changed here; capability claims are Task 5 scope.

## Evidence

Red command (before production change):

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_fair_pilot_cli.py academic_benchmark/tests/test_native_termination_protocol.py -k "config or schema or replay or record" -q -p no:cacheprovider --tb=short
```

Result: 8 failed, 3 passed, 22 deselected; failures were exact-set admission because `ALNS-TSP` was absent.

Green command:

```powershell
& C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests/test_fair_pilot_cli.py academic_benchmark/tests/test_native_termination_protocol.py academic_benchmark/tests/test_alns_c3_evidence.py -q -p no:cacheprovider --tb=short
```

## Review follow-up evidence

After native exact-key-first validation, restored lexical execution ordering, and ALNS fair-pilot record/replay provenance assertions, the required focused suite passed: **87 passed in 4.51s**.
The ALNS candidate capability admission remains explicitly deferred to Task 5; no capability claims were changed.

Final fixture correction: added canonical `resolution` provenance to the native ALNS record helper fixture.
Final required focused suite: **88 passed in 4.41s**.
