# Package C1 Task 6 Partial Evidence Report

**Status:** scientifically truthful partial completion; full Task 6 and Gate C1 are not complete.

## Claim and evidence matrix

| Canonical ID | Problem | Protocol | Backend profile | Exact evidence node | Result | Catalog action |
|---|---|---|---|---|---|---|
| `Core-TwoOpt-TSP` | TSP | fixed budget | `objective=python;polish=none` | `academic_benchmark/tests/test_algorithm_capability_evidence.py::test_core_two_opt_fixed_tsp_and_atsp_evidence` | PASS | promoted |
| `Core-TwoOpt-TSP` | ATSP | fixed budget | `objective=python;polish=none` | `academic_benchmark/tests/test_algorithm_capability_evidence.py::test_core_two_opt_fixed_tsp_and_atsp_evidence` | PASS | promoted |
| `Core-ThreeOpt-TSP` | TSP | fixed budget | `objective=python;polish=none` | `academic_benchmark/tests/test_algorithm_capability_evidence.py::test_core_three_opt_fixed_tsp_and_atsp_evidence` | PASS | promoted |
| `Core-ThreeOpt-TSP` | ATSP | fixed budget | `objective=python;polish=none` | `academic_benchmark/tests/test_algorithm_capability_evidence.py::test_core_three_opt_fixed_tsp_and_atsp_evidence` | PASS | promoted |
| `Core-TwoOpt-TSP` / `Core-ThreeOpt-TSP` | TSP / ATSP | native termination | `objective=python;polish=none` | none with canonical result identity | BLOCKED | withheld |
| `Core-GWO-TSP-Pure` / `Core-HHO-TSP-Pure` | TSP / ATSP | fixed and native | `objective=numba;polish=none` | no exact node completed under `.venv-jit` | BLOCKED | withheld; remain `CANDIDATE` |
| `Core-GWO-TSP-Memetic-2opt` / `Core-HHO-TSP-Memetic-2opt` | TSP / ATSP | fixed | `objective=numba;polish=python` | no exact node completed under `.venv-jit` | BLOCKED | withheld; remain `CANDIDATE` |
| OrOpt, GA, PSO, ALNS | any | any | any | none | NOT ATTEMPTED | remain `CANDIDATE` |

The two published evidence functions each execute a symmetric six-node TSP and a genuinely asymmetric six-node ATSP twice. They require a complete 1-indexed permutation, independently recompute the directed closed-cycle cost, verify paired fixed seed and replay equality, require an exact numeric objective-evaluation count with no overshoot, require the exact accepted termination reason, and require the exact full backend profile.

## Exact execution results

- Planned five-file Task 6 command under `.venv-jit`: **TIMEOUT at 60 seconds with no pytest result**. This is not evidence.
- `.venv-jit` TwoOpt exact evidence node: **TIMEOUT at 30 seconds with no pytest result**. This is not evidence.
- `.venv-jit` bounded registry import diagnostic: **TIMEOUT at 20 seconds with no completion**. This is not evidence.
- Task-owned processes started by those bounded calls were terminated by their exact newly observed PID/start-time pairs; no unrelated Python processes were stopped.
- Ordinary interpreter used only for Python-backend claims: Python 3.14.3, pytest 9.1.1, NumPy 2.5.1. It reported Numba unavailable and was not used for any Numba claim.
- `test_core_two_opt_fixed_tsp_and_atsp_evidence`: PASS independently, then PASS with catalog binding.
- `test_core_three_opt_fixed_tsp_and_atsp_evidence`: PASS independently, then PASS with catalog binding.
- Focused evidence plus catalog: `17 passed in 3.34s`.
- Changed canonical fair-local nodes: `8 passed in 2.43s`.
- Historical native local metadata function: `2 passed in 2.81s`; this proves native execution metadata but not canonical result identity.
- Fair validator compatibility RED: historical IDs failed while canonical IDs passed (`2 failed, 2 passed`).
- Fair validator compatibility GREEN: historical and canonical IDs both accepted (`4 passed in 2.33s`).
- Focused evidence, catalog, and compatibility regression: `21 passed in 2.63s`.
- AST parse over every Task 6 touched Python file: `AST_OK`.
- `git diff --check` and `git diff --cached --check`: clean (line-ending warnings only).

## Promotions withheld

- No GWO/HHO claim was promoted. Import, collection, a prior report, or a timeout is not executable nopython evidence.
- No Python-objective GWO/HHO claim was added.
- No canonical local-search native claim was added. The current native pilot and approved algorithm set still use the historical `Numba-2-opt` and `Numba-3-opt-bounded` identities. Migrating that complete boundary belongs to Task 8; adding both identity sets to the scientific native approved set here would falsely make both identities canonical.
- `Core-OrOpt-TSP`, `Core-GA-TSP`, `Core-PSO-TSP`, and `ALNS-TSP` remain `CANDIDATE`.

## Changed files

- `uniride_core/algorithms/capabilities.py`
- `academic_benchmark/core/registry_setup.py`
- `academic_benchmark/fairness.py`
- `academic_benchmark/tests/test_algorithm_capability_catalog.py`
- `academic_benchmark/tests/test_algorithm_capability_evidence.py`
- `academic_benchmark/tests/test_fair_comparison_protocol.py`
- `academic_benchmark/tests/test_fair_comparison_scientific_integrity.py`
- `academic_benchmark/tests/test_native_termination_protocol.py`
- `.superpowers/sdd/task-c1-6-report.md`

Historical registry keys remain registered. Evidence and canonical callers use `Core-TwoOpt-TSP` / `Core-ThreeOpt-TSP`; `FairComparisonManifest` also accepts the current fair-pilot result identities `Numba-2-opt` / `Numba-3-opt-bounded` as a temporary compatibility boundary until Task 8. Those validator entries do not create catalog claims, resolver aliases, or scientific selectability. Both fixed and historical native local-search result metadata report exactly `objective=python;polish=none`.

## Remaining blockers and next action

1. Task 8 must migrate the native pilot's configuration schema, approved set, and result identity atomically before canonical local-search native evidence can be executed and published.
2. GWO/HHO exact evidence nodes must execute to completion under a working `.venv-jit` nopython environment. Each TSP/ATSP and fixed/native/memetic tuple must pass independently before promotion.
3. After those blockers close, rerun the exact Task 6 five-file command and the later Gate C1 suites. Do not infer full Task 6 completion from this partial commit.

## Canonical native local-search promotion follow-up

The Task 8 Phase A direct canonical evidence bridge has closed the prior local-search
native-claim identity blocker. The immutable catalog now publishes, for both
`Core-TwoOpt-TSP` and `Core-ThreeOpt-TSP`, TSP and ATSP
`NATIVE_TERMINATION` claims with `objective=python;polish=none` and
`LOCAL_SEARCH` composition. Each claim names its exact direct evidence node:

- `academic_benchmark/tests/test_native_termination_protocol.py::test_core_two_opt_direct_native_tsp_and_atsp_evidence`
- `academic_benchmark/tests/test_native_termination_protocol.py::test_core_three_opt_direct_native_tsp_and_atsp_evidence`

The published flags match the direct evidence: ATSP claims preserve directed
costs; all four claims have exact objective accounting, fixed-seed deterministic
replay, and truthful result reporting. The fixed-budget claims remain unchanged.
No GWO/HHO, OrOpt, GA, PSO, or ALNS claim was changed.

### TDD and verification

- RED: the new catalog native-claim expectation failed as intended with `2 failed
  in 2.45s`, because neither canonical local-search capability had a native
  claim.
- GREEN:
  `python -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_native_termination_protocol.py::test_core_two_opt_direct_native_tsp_and_atsp_evidence academic_benchmark\tests\test_native_termination_protocol.py::test_core_three_opt_direct_native_tsp_and_atsp_evidence -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-task6-native-promotion-green --tb=short`
  returned `21 passed in 0.92s`.
- Static parse of the changed Python files returned `AST_OK`; `git diff --check`
  was clean.

## GWO/HHO executable-evidence closure (2026-07-29)

**Status:** complete for the six requested canonical GWO/HHO tuples. All claims below executed through the production academic registry under `.venv-jit`; none used monkeypatched backend labels, objective functions, accounting, or claims.

### Exact claim matrix

| Canonical ID | Protocol | TSP + ATSP backend | Polish/composition | Exact evidence node | Result |
|---|---|---|---|---|---|
| `Core-GWO-TSP-Pure` | fixed budget | `objective=numba;polish=none` | `pure` | `test_core_gwo_pure_fixed_tsp_and_atsp_numba_evidence` | PASS |
| `Core-HHO-TSP-Pure` | fixed budget | `objective=numba;polish=none` | `pure` | `test_core_hho_pure_fixed_tsp_and_atsp_numba_evidence` | PASS |
| `Core-GWO-TSP-Pure` | native termination | `objective=numba;polish=none` | `pure` | `test_core_gwo_pure_native_tsp_and_atsp_numba_evidence` | PASS |
| `Core-HHO-TSP-Pure` | native termination | `objective=numba;polish=none` | `pure` | `test_core_hho_pure_native_tsp_and_atsp_numba_evidence` | PASS |
| `Core-GWO-TSP-Memetic-2opt` | fixed budget | `objective=numba;polish=python` | `memetic_2opt` | `test_core_gwo_memetic_2opt_fixed_tsp_and_atsp_numba_evidence` | PASS |
| `Core-HHO-TSP-Memetic-2opt` | fixed budget | `objective=numba;polish=python` | `memetic_2opt` | `test_core_hho_memetic_2opt_fixed_tsp_and_atsp_numba_evidence` | PASS |

Each node executes a symmetric TSP and genuinely directed ATSP twice, requires the canonical identity and complete 1-indexed tour, independently recomputes the directed closed cycle, checks deterministic paired-seed replay, exact positive evaluation counts with no fixed-budget overshoot, truthful termination, composition/polish flags, and a live Numba nopython objective probe. A missing nopython signature fails the evidence test; it does not skip.

### TDD and literal command results

RED nodes each reached their final lifecycle assertion only after the real executor completed its scientific assertions: GWO fixed `1 failed in 3.61s`; HHO fixed `1 failed in 2.25s`; GWO native `1 failed in 2.70s`; HHO native `1 failed in 2.44s`; GWO memetic fixed `1 failed in 1.87s`; HHO memetic fixed `1 failed in 2.33s`. Every RED failure was the intended `CANDIDATE` lifecycle mismatch, with no earlier solver/backend/cost/accounting/termination failure.

```powershell
$env:NUMBA_CACHE_DIR='C:\tmp\uniride-numba-cache-c1-gwo-hho'; & 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m pytest academic_benchmark\tests\test_algorithm_capability_evidence.py::test_core_gwo_pure_fixed_tsp_and_atsp_numba_evidence academic_benchmark\tests\test_algorithm_capability_evidence.py::test_core_hho_pure_fixed_tsp_and_atsp_numba_evidence academic_benchmark\tests\test_algorithm_capability_evidence.py::test_core_gwo_pure_native_tsp_and_atsp_numba_evidence academic_benchmark\tests\test_algorithm_capability_evidence.py::test_core_hho_pure_native_tsp_and_atsp_numba_evidence academic_benchmark\tests\test_algorithm_capability_evidence.py::test_core_gwo_memetic_2opt_fixed_tsp_and_atsp_numba_evidence academic_benchmark\tests\test_algorithm_capability_evidence.py::test_core_hho_memetic_2opt_fixed_tsp_and_atsp_numba_evidence -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-gwo-hho-green --tb=short
```

Result: `6 passed in 2.32s`; no skipped tests.

```powershell
$env:NUMBA_CACHE_DIR='C:\tmp\uniride-numba-cache-c1-gwo-hho'; & 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m pytest academic_benchmark\tests\test_algorithm_capability_catalog.py academic_benchmark\tests\test_algorithm_capability_evidence.py academic_benchmark\tests\test_algorithm_preflight.py academic_benchmark\tests\test_algorithm_preflight_boundaries.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-gwo-hho-catalog-green --tb=short
```

Result: `74 passed in 31.64s`.

```powershell
$env:NUMBA_CACHE_DIR='C:\tmp\uniride-numba-cache-c1-gwo-hho'; & 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe' -m pytest academic_benchmark\tests\test_solver_backend_reporting.py academic_benchmark\tests\test_numba_jit_parity.py academic_benchmark\tests\test_native_termination_protocol.py academic_benchmark\tests\test_fair_comparison_protocol.py -q -p no:cacheprovider --basetemp C:\tmp\pytest-c1-gwo-hho-regression-green --tb=short
```

Result: `82 passed in 2.75s`.

The catalog promotes only the six rows above. OrOpt, GA, PSO, ALNS, and the 3-opt/ALNS reservations retain their previous lifecycle states. Task 10 remains partial for its independent full-suite and manifest-lifecycle gates.
