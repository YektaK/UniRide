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
- AST parse over every Task 6 touched Python file: `AST_OK`.
- `git diff --check` and `git diff --cached --check`: clean (line-ending warnings only).

## Promotions withheld

- No GWO/HHO claim was promoted. Import, collection, a prior report, or a timeout is not executable nopython evidence.
- No Python-objective GWO/HHO claim was added.
- No canonical local-search native claim was added. The current native pilot and approved algorithm set still use the historical `Numba-2-opt` and `Numba-3-opt-bounded` identities. Migrating that complete boundary belongs to Task 8; accepting both sets here would falsely make both identities scientifically canonical.
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

Historical registry keys remain registered. The fair protocol now uses canonical `Core-TwoOpt-TSP` / `Core-ThreeOpt-TSP` identities. Both fixed and historical native local-search result metadata now report exactly `objective=python;polish=none`.

## Remaining blockers and next action

1. Task 8 must migrate the native pilot's configuration schema, approved set, and result identity atomically before canonical local-search native evidence can be executed and published.
2. GWO/HHO exact evidence nodes must execute to completion under a working `.venv-jit` nopython environment. Each TSP/ATSP and fixed/native/memetic tuple must pass independently before promotion.
3. After those blockers close, rerun the exact Task 6 five-file command and the later Gate C1 suites. Do not infer full Task 6 completion from this partial commit.
