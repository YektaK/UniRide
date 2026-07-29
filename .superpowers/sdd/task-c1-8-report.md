# Package C1 Task 8 Phase A Report

**Status:** Phase A implemented and ready for orchestrator-led claim promotion. The
capability catalog was not edited and no pilot success claim is made.

## Phase A outcome

- Fair and native pilot configuration/stored local-search identities are now
  `Core-TwoOpt-TSP` and `Core-ThreeOpt-TSP`.
- Historical `Numba-2-opt` and `Numba-3-opt-bounded` registry/result-family keys
  remain compatibility-only in `native_protocol.py`.
- Both pilots take one runtime-backend probe and one registered-ID snapshot per
  pilot, then call `execute_preflighted` for every primary and replay run.
- GWO/HHO callers declare `REQUIRE_NUMBA_OBJECTIVE`; local-search callers declare
  `PYTHON_ONLY`.
- Persisted rows include backend policy/profile, fallback status/reason, executor
  registry ID, and capability evidence IDs from the immutable gateway decision.
- Duplicate pilot-local backend assertions were removed where gateway postflight
  now owns the exact backend-profile check.
- No capability claim, lifecycle, solver mathematics, seed, move, budget, or
  termination behavior was changed.

## Direct canonical native evidence bridge

The following exact nodes call canonical executors directly, as permitted before
native claim publication:

1. `academic_benchmark/tests/test_native_termination_protocol.py::test_core_two_opt_direct_native_tsp_and_atsp_evidence`
2. `academic_benchmark/tests/test_native_termination_protocol.py::test_core_three_opt_direct_native_tsp_and_atsp_evidence`

Each node covers symmetric TSP and directed ATSP, exact canonical identity,
complete 1-indexed routes, independent directed closed-cycle cost, deterministic
same-seed replay, positive exact objective accounting, native termination reason,
and `objective=python;polish=none`.

RED command (ordinary Python):

```powershell
python -m pytest academic_benchmark\tests\test_native_termination_protocol.py::test_core_two_opt_direct_native_tsp_and_atsp_evidence academic_benchmark\tests\test_native_termination_protocol.py::test_core_three_opt_direct_native_tsp_and_atsp_evidence -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task8-native-evidence-red2 --tb=short
```

RED result: `2 failed in 3.08s`; both failed with
`FairnessValidationError: unsupported native algorithm_id`.

GREEN command: the same two exact nodes with basetemp
`C:\tmp\pytest-c1-task8-native-evidence-green`.

GREEN result: `2 passed in 3.05s`.

## No-bypass RED/GREEN

RED command:

```powershell
python -m pytest academic_benchmark\tests\test_algorithm_preflight_boundaries.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task8-boundary-red --tb=short
```

RED result: collection failed because `_execute_preflighted_run` did not exist.

GREEN result: `7 passed in 3.12s`. The exploding getter remained unreachable for
candidate, planned, wrong problem, missing fixed budget, forbidden native budget,
unavailable backend, and missing executor requests.

## Final deterministic Phase A gate

```powershell
python -c "import ast,pathlib; files=['academic_benchmark/fair_pilot.py','academic_benchmark/native_pilot.py','academic_benchmark/native_protocol.py','academic_benchmark/tests/test_algorithm_preflight_boundaries.py','academic_benchmark/tests/test_fair_pilot_cli.py','academic_benchmark/tests/test_native_termination_protocol.py']; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8'), filename=p) for p in files]; print('AST_OK')"
python -m pytest academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_fair_pilot_cli.py::test_fair_pilot_writes_only_validated_external_artifacts academic_benchmark\tests\test_native_termination_protocol.py::test_native_config_is_strict academic_benchmark\tests\test_native_termination_protocol.py::test_core_two_opt_direct_native_tsp_and_atsp_evidence academic_benchmark\tests\test_native_termination_protocol.py::test_core_three_opt_direct_native_tsp_and_atsp_evidence -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task8-phase-a-final --tb=short
```

Result: `AST_OK`; `14 passed in 1.87s`.

## One bounded exact Task 8 command

The exact three-file command was run once with ordinary Python and a 60-second
bound. Result: `28 passed, 7 failed in 4.70s`.

- Two GWO/HHO executor-evidence nodes reported
  `objective=python;polish=none` because this ordinary Python environment has no
  Numba backend. This is not Numba evidence and was not rerun.
- Four stale pilot-local inexact-backend tests failed after the ad hoc check moved
  to gateway postflight; those duplicate tests were then removed.
- The end-to-end native pilot failed before registry lookup because
  `Core-GWO-TSP-Pure` is correctly still `CANDIDATE`.

The exact broad command was not repeated after cleanup, per the bounded-JIT rule.

## Current blocked claims

- `Core-GWO-TSP-Pure` and `Core-HHO-TSP-Pure` remain `CANDIDATE` and must fail
  before executor lookup. Phase A adds no exemption or promotion.
- `Core-TwoOpt-TSP` and `Core-ThreeOpt-TSP` currently publish fixed-budget claims
  only. Their canonical native executors now have direct evidence, but native
  preflight remains blocked until the orchestrator promotes the exact native
  TSP/ATSP claims in the capability catalog.
- Consequently, end-to-end canonical native pilot success is intentionally not a
  Phase A result. Phase B must follow catalog promotion and rerun pilot-level
  end-to-end tests without bypassing preflight.

## Files

- `academic_benchmark/fair_pilot.py`
- `academic_benchmark/native_pilot.py`
- `academic_benchmark/native_protocol.py`
- `academic_benchmark/tests/test_algorithm_preflight_boundaries.py`
- `academic_benchmark/tests/test_fair_pilot_cli.py`
- `academic_benchmark/tests/test_native_termination_protocol.py`
- `.superpowers/sdd/task-c1-8-report.md`

No generated benchmark CSV, database, capability-catalog edit, or unrelated
working-tree change is included.


## Phase B - canonical pilot preflight closure

Phase B began from commit 6d42be7, which promoted the exact canonical native
TwoOpt/ThreeOpt TSP and ATSP claims backed by the two direct evidence nodes
above. Task 8 did not modify that catalog commit.

### Real gateway pilot-boundary integration

The following new tests use the real execute_preflighted gateway, real
canonical registry executors, and pilot record serializers:

1. academic_benchmark/tests/test_fair_pilot_cli.py::test_canonical_local_search_fixed_primary_and_replay_use_real_gateway
2. academic_benchmark/tests/test_native_termination_protocol.py::test_canonical_local_search_native_primary_and_replay_use_real_gateway

Both are parametrized for Core-TwoOpt-TSP and Core-ThreeOpt-TSP; each case
covers symmetric TSP and directed ATSP and executes both primary and replay.
They prove exact two-call registry lookup, canonical identity, independent
closed-cycle cost, replay equality, exact positive accounting, fixed/native
termination semantics, objective=python;polish=none, PYTHON_ONLY, no fallback,
canonical executor registry ID, and the exact persisted capability evidence ID.

Initial real-gateway command:

~~~powershell
python -m pytest academic_benchmark\tests\test_fair_pilot_cli.py::test_canonical_local_search_fixed_primary_and_replay_use_real_gateway academic_benchmark\tests\test_native_termination_protocol.py::test_canonical_local_search_native_primary_and_replay_use_real_gateway -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task8-phase-b-real-gateway-red --tb=short
~~~

Result: 4 passed in 0.73s. No production fix was required after claim
promotion.

The strict full native pilot test was corrected to assert the scientifically
current boundary: mandatory Core-GWO-TSP-Pure is still CANDIDATE, the exploding
registry getter is never called, and validation.json records the failed
candidate decision. The strict algorithm set was not weakened.

### Phase B bounded verification

Existing boundary plus direct evidence before new tests: 9 passed in 1.05s.

Ordinary-Python deterministic Task 8 command:

~~~powershell
python -m pytest academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_fair_pilot_cli.py academic_benchmark\tests\test_native_termination_protocol.py -k "not native_metaheuristics_use_numba_and_report_actual_counts" -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task8-phase-b-deterministic --tb=short
~~~

Result: 33 passed, 2 deselected in 0.82s. Only the two explicitly
Numba-specific GWO/HHO executor evidence cases were deselected.

The single permitted exact .venv-jit Task 8 attempt:

~~~powershell
C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe -m pytest academic_benchmark\tests\test_algorithm_preflight_boundaries.py academic_benchmark\tests\test_fair_pilot_cli.py academic_benchmark\tests\test_native_termination_protocol.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task8-phase-b-jit-exact --tb=short
~~~

Result: 35 passed in 3.83s. This exact JIT command was run once only.

Final focused command after strengthening explicit cost/backend/accounting
assertions covered the seven no-bypass cases, both fixed real-gateway cases,
the strict full-pilot candidate rejection, both native real-gateway cases, and
both direct evidence nodes.

Result: 14 passed in 0.70s; AST parse: AST_OK; git diff --check: clean.

### Remaining boundary

- GWO/HHO remain untouched CANDIDATE entries. Full strict fair/native pilot
  success remains blocked before registry lookup until separately evidenced
  and promoted; Task 8 grants no exemption.
- Canonical TwoOpt/ThreeOpt fixed and native local-search executions are now
  proven through the real gateway and pilot persistence boundary.
- Phase B changes only pilot tests and this report; no catalog, solver,
  production registry, protocol, or pilot implementation file changed.


### Phase B review coverage closure

The review-only follow-up added no production or catalog changes.

- Both real-gateway tests now serialize replay through the same pilot record
  helper with record_kind=replay and the replay decision. Replay records assert
  canonical algorithm and executor identity, python_only policy, the exact
  objective=python;polish=none profile, and the promoted capability evidence ID.
- The strict native full-pilot rejection now asserts both the raised error and
  validation.json identify Core-GWO-TSP-Pure as the CANDIDATE rejected before
  registry lookup.

Focused ordinary-Python review command result: 5 passed in 0.64s.

Bounded deterministic Task 8 result: 33 passed, 2 explicitly Numba-only
GWO/HHO evidence cases deselected, in 0.77s.

The single bounded exact .venv-jit Task 8 command for this follow-up passed:
35 passed in 1.16s.

Final syntax and hygiene: AST_OK; git diff --check clean.
