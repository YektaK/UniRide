# Package C1 Task 7 Partial Report

**Status:** scientifically truthful partial completion. The decision-bound gateway,
postflight checks, canonical manifest structure, run provenance contracts, and schema
snapshot are complete. Manifest lifecycle rejection remains partial because the
current Bildiri GWO/HHO declarations are canonical `CANDIDATE` IDs pending the Task 6
JIT evidence gate.

## Outcome matrix

| Requirement | Result | Evidence |
|---|---|---|
| Resolve/preflight before registry lookup | PASS | Exploding-getter tests reject unknown IDs, candidate IDs, and invalid problem contracts before lookup. |
| Exact gateway order and signature | PASS | `execute_preflighted` performs resolve, preflight, canonical lookup, execute, then postflight using the approved keyword-only boundary. |
| Complete 1-indexed tour and duplicate rejection | PASS | Gateway unit tests cover incomplete and duplicate routes. |
| Independent directed closed-cycle objective | PASS | The gateway recomputes every directed arc, including the closing arc, and checks both `tour_cost` and `objective_cost`. |
| Protocol accounting and termination | PASS | Positive equal counts, fixed-budget no-overshoot/budget identity, termination consistency, and native uncapped termination are validated. |
| Backend observation parser | PASS | Only objective `python`/`numba` and polish `none`/`python`/`numba` parse; unknown, unused, mixed, combined `numba+python`, and decision-profile mismatch fail. |
| Canonical result identity and alias provenance | PASS | `algorithm` and `algorithm_id` must equal the decision's canonical ID; requested input is attached only for a resolved alias and stale provenance is cleared for canonical requests. |
| Strict run contract provenance | PASS | `requested_algorithm_id` is optional; backend policy is exactly `python_only`, `prefer_numba`, or `require_numba`; backend profile is a closed two-stage mapping; evidence is a non-empty strict list. |
| Canonical manifest spelling | PASS | Primary and secondary lists reject aliases and unknown identifiers through `IdentifierSource.MANIFEST`; planned canonical IDs are rejected. |
| Candidate manifest lifecycle rejection | DEFERRED | Canonical candidate IDs remain structurally valid so the unchanged Bildiri profile stays truthful; execution preflight rejects them with `CandidateAlgorithmError`. |
| Bildiri profile | PASS | Existing four primary and two secondary GWO/HHO IDs remain unchanged and structurally valid as canonical candidate declarations. |
| Fairness provenance field | PASS | Ordinary Python direct dataclass check printed `FAIR_PROVENANCE_OK`. The registry-heavy fairness pytest module did not complete in the bounded JIT run. |

## TDD and verification

Interpreter facts:

- Exact `.venv-jit` interpreter: `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe`.
- Ordinary interpreter: Python 3.14.3. It was usable for the direct fairness dataclass check but its installed Pydantic 2.12.5 / pydantic-core 2.47.0 combination is incompatible, so it was not used for contract claims.

RED:

- Exact Task 7 three-file command failed at collection with one expected error: `ModuleNotFoundError: academic_benchmark.core.execution_gateway` (`1 error in 2.66s`).
- Stale canonical provenance regression failed as intended: `requested_algorithm_id` remained `stale-alias` (`1 failed in 1.44s`).

GREEN:

- Exact focused command over `test_algorithm_execution_gateway.py`, `test_manifest_contracts.py`, and `test_bildiri_study_profile.py`: **66 passed in 2.40s**.
- Stale provenance node after implementation: **1 passed in 1.08s**.
- Deterministic schema check: `python -m academic_benchmark.contracts.export_schemas check` exited 0.
- Direct fairness provenance check under ordinary Python: `FAIR_PROVENANCE_OK`.
- `git diff --check`: PASS.

Bounded/non-claiming checks:

- Gateway + preflight + contracts + Bildiri: **104 passed, 1 failed in 1.93s**. The failure is a pre-existing stale Task 5 assertion in `test_algorithm_preflight.py::test_production_catalog_entries_remain_non_selectable_in_task_five`, which still expects `Core-TwoOpt-TSP` to be `CANDIDATE` after Task 6 truthfully promoted its fixed claims. Task 7 did not alter that test.
- Adding the registry-heavy fairness module to the adjacent run produced no pytest output for 45 seconds and was terminated before 60 seconds. No fairness-registry suite pass is claimed.

## Schema generation

The schema exporter was run with the working `.venv-jit` interpreter using the
required explicit `write` action. The first sandboxed write was denied; the approved
rerun completed. A following `check` returned no stale schema names. Only
`run-v1.schema.json` changed because study lifecycle rules are runtime validators and
do not change its JSON shape.

## Changed files

- `academic_benchmark/core/execution_gateway.py`
- `academic_benchmark/core/preflight.py`
- `academic_benchmark/fairness.py`
- `academic_benchmark/contracts/run.py`
- `academic_benchmark/contracts/study.py`
- `academic_benchmark/schemas/run-v1.schema.json`
- `academic_benchmark/tests/test_algorithm_execution_gateway.py`
- `academic_benchmark/tests/test_manifest_contracts.py`
- `academic_benchmark/tests/test_bildiri_study_profile.py`
- `academic_benchmark/tests/test_fair_comparison_protocol.py`
- `.superpowers/sdd/task-c1-7-report.md`

No solver mathematics, study algorithms, production registry, dependencies, datasets,
archives, generated benchmark results, or unrelated files changed.

## Conflict and next gate

The approved global constraint says candidates are non-selectable and manifests reject
candidates, while the current canonical Bildiri manifest names four GWO/HHO candidates.
Task 6 explicitly withheld their promotion because the exact `.venv-jit` evidence nodes
did not execute. This implementation does not special-case Bildiri, fabricate evidence,
promote GWO/HHO, or rewrite the study. It enforces canonical spelling and planned/alias/
unknown rejection now, allows canonical candidates only as structural declarations, and
proves they still fail execution preflight.

The next gate is Task 6 JIT evidence: execute the exact GWO/HHO TSP/ATSP, fixed/native,
and pure/memetic evidence nodes to completion. Promote only the exact passing claims;
then enable candidate lifecycle rejection in `StudyManifestV1`, regenerate schemas if
the model shape changes, and rerun the complete Task 7 and Gate C1 suites.

## Manifest lifecycle closure (2026-07-29)

**Status update:** the deferred manifest-lifecycle item is now complete. This does
not change the report's broader partial status: the registry-heavy fairness run and
the bounded full suite remain unclaimed.

- Primary `algorithm_ids` and `secondary_protocol.algorithm_ids` resolve as manifest identifiers and now reject every canonical `CANDIDATE` with the stable `candidate_algorithm` Pydantic error.
- `PLANNED`, unknown, forbidden, and alias IDs remain rejected by the resolver/validator; parameter-key equality remains exact.
- The unchanged Bildiri profile validates because all four declared canonical algorithms are now `VERIFIED`; no study or ID special case exists.
- The deterministic schema check passed; runtime validators changed no JSON schema shape, so no schema regeneration was needed.
