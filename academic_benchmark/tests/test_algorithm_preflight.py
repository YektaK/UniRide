"""Evidence-gated algorithm preflight decisions."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from typing import Callable, Iterable

import pytest

from academic_benchmark.core.algorithm_errors import (
    BackendUnavailableError,
    CandidateAlgorithmError,
    CapabilityEvidenceError,
    ExecutorUnavailableError,
    PlannedAlgorithmError,
    UnsupportedProblemContractError,
    UnsupportedProtocolError,
    UnknownAlgorithmError,
)
from academic_benchmark.core.algorithm_resolution import IdentifierSource, ResolutionResult
from academic_benchmark.core.preflight import (
    PreflightRequest,
    RuntimeBackendAvailability,
    preflight_run,
)
from uniride_core.algorithms.capabilities import (
    AlgorithmCapability,
    BackendKind,
    BackendPolicy,
    CapabilityClaim,
    CompositionKind,
    ExecutionBackendProfile,
    ExecutionProtocol,
    LifecycleStatus,
    ProblemContract,
    build_capability_catalog,
)


@dataclass
class _Problem:
    name: str
    problem_type: str
    dimension: int
    dist_matrix: list[list[float]]


_TSP = _Problem(
    "tiny-tsp", "tsp", 3,
    [[0.0, 2.0, 4.0], [2.0, 0.0, 3.0], [4.0, 3.0, 0.0]],
)
_ATSP = _Problem(
    "tiny-atsp", "atsp", 3,
    [[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]],
)
_ID = "Synthetic-Solver-TSP"


def _resolution(canonical_id: str = _ID) -> ResolutionResult:
    return ResolutionResult(
        requested_id=canonical_id,
        canonical_id=canonical_id,
        source=IdentifierSource.INTERNAL,
        alias_used=False,
        alias_policy=None,
        warning_code=None,
        warning_message=None,
    )


def _claim(
    *,
    problem: ProblemContract = ProblemContract.TSP,
    protocol: ExecutionProtocol = ExecutionProtocol.FIXED_BUDGET,
    objective: BackendKind = BackendKind.PYTHON,
    polish: BackendKind = BackendKind.NONE,
    composition: CompositionKind = CompositionKind.PURE,
    evidence_id: str = "test_synthetic_evidence",
) -> CapabilityClaim:
    return CapabilityClaim(
        problem=problem,
        protocol=protocol,
        backend_profile=ExecutionBackendProfile(objective, polish),
        composition=composition,
        directed_cost_preserved=True,
        exact_objective_accounting=True,
        fixed_seed_deterministic=True,
        truthful_result_reporting=True,
        evidence_ids=(evidence_id,),
    )


def _capability(
    claims: Iterable[CapabilityClaim] = (),
    *,
    lifecycle: LifecycleStatus = LifecycleStatus.VERIFIED,
) -> AlgorithmCapability:
    return AlgorithmCapability(
        canonical_id=_ID,
        family="Synthetic",
        label="Synthetic solver",
        lifecycle=lifecycle,
        claims=tuple(claims),
        planning_note="Reserved by test" if lifecycle is LifecycleStatus.PLANNED else None,
    )


def _lookup_for(
    capability: AlgorithmCapability,
) -> Callable[[str], AlgorithmCapability | None]:
    catalog = build_capability_catalog((capability,))
    return catalog.get


def _request(
    *,
    problem: object = _TSP,
    protocol: ExecutionProtocol = ExecutionProtocol.FIXED_BUDGET,
    policy: BackendPolicy = BackendPolicy.PYTHON_ONLY,
    budget: object = 10,
    registered: frozenset[str] = frozenset({_ID}),
    python: bool = True,
    numba: bool = False,
) -> PreflightRequest:
    return PreflightRequest(
        resolution=_resolution(),
        problem=problem,
        protocol=protocol,
        backend_policy=policy,
        evaluation_budget=budget,  # type: ignore[arg-type]
        registered_algorithm_ids=registered,
        runtime_backends=RuntimeBackendAvailability(
            python=python,
            numba_nopython=numba,
            detail="synthetic runtime detail",
        ),
    )


@pytest.mark.parametrize(
    ("lifecycle", "error_type", "code"),
    [
        (LifecycleStatus.CANDIDATE, CandidateAlgorithmError, "candidate_algorithm"),
        (LifecycleStatus.PLANNED, PlannedAlgorithmError, "planned_algorithm"),
    ],
)
def test_non_verified_lifecycles_raise_typed_errors(
    lifecycle: LifecycleStatus,
    error_type: type[Exception],
    code: str,
) -> None:
    lookup = _lookup_for(_capability(lifecycle=lifecycle))
    with pytest.raises(error_type) as caught:
        preflight_run(_request(problem=object()), capability_lookup=lookup)
    assert getattr(caught.value, "code") == code


@pytest.mark.parametrize("budget", [None, 0, -1, True, False, 1.5])
def test_fixed_budget_requires_a_positive_non_boolean_integer(budget: object) -> None:
    lookup = _lookup_for(_capability((_claim(),)))
    with pytest.raises(UnsupportedProtocolError, match="positive integer"):
        preflight_run(_request(budget=budget), capability_lookup=lookup)


@pytest.mark.parametrize("budget", [0, 1, True])
def test_native_termination_forbids_an_evaluation_budget(budget: object) -> None:
    native = _claim(protocol=ExecutionProtocol.NATIVE_TERMINATION)
    lookup = _lookup_for(_capability((native,)))
    with pytest.raises(UnsupportedProtocolError, match="must not include"):
        preflight_run(
            _request(protocol=ExecutionProtocol.NATIVE_TERMINATION, budget=budget),
            capability_lookup=lookup,
        )


@pytest.mark.parametrize(
    ("problem", "contract"),
    [(_TSP, ProblemContract.TSP), (_ATSP, ProblemContract.ATSP)],
)
def test_preflight_selects_only_the_exact_problem_contract_claim(
    problem: _Problem,
    contract: ProblemContract,
) -> None:
    tsp = _claim(problem=ProblemContract.TSP, evidence_id="tsp-evidence")
    atsp = _claim(problem=ProblemContract.ATSP, evidence_id="atsp-evidence")
    lookup = _lookup_for(_capability((tsp, atsp)))
    decision = preflight_run(_request(problem=problem), capability_lookup=lookup)
    assert decision.problem.contract is contract
    assert decision.selected_claim is (tsp if contract is ProblemContract.TSP else atsp)
    assert decision.evidence_ids == decision.selected_claim.evidence_ids


def test_tsp_evidence_does_not_authorize_atsp() -> None:
    lookup = _lookup_for(_capability((_claim(problem=ProblemContract.TSP),)))
    with pytest.raises(UnsupportedProblemContractError, match="atsp"):
        preflight_run(_request(problem=_ATSP), capability_lookup=lookup)


def test_fixed_evidence_does_not_authorize_native_termination() -> None:
    lookup = _lookup_for(_capability((_claim(),)))
    with pytest.raises(UnsupportedProtocolError, match="native_termination"):
        preflight_run(
            _request(protocol=ExecutionProtocol.NATIVE_TERMINATION, budget=None),
            capability_lookup=lookup,
        )


def test_python_only_selects_an_exact_evidenced_python_profile() -> None:
    numba = _claim(
        objective=BackendKind.NUMBA_NOPYTHON,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="numba",
    )
    python = _claim(
        objective=BackendKind.PYTHON,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="python-memetic",
    )
    lookup = _lookup_for(_capability((numba, python)))
    decision = preflight_run(
        _request(policy=BackendPolicy.PYTHON_ONLY, numba=True),
        capability_lookup=lookup,
    )
    assert decision.selected_claim is python
    assert decision.selected_backend == python.backend_profile
    assert decision.selected_claim.composition is CompositionKind.MEMETIC_2OPT
    assert decision.fallback_reason is None


def test_python_only_never_fabricates_a_python_claim() -> None:
    lookup = _lookup_for(_capability((_claim(objective=BackendKind.NUMBA_NOPYTHON),)))
    with pytest.raises(CapabilityEvidenceError, match="Python objective"):
        preflight_run(_request(), capability_lookup=lookup)


def test_python_only_requires_python_runtime_availability() -> None:
    lookup = _lookup_for(_capability((_claim(),)))
    with pytest.raises(BackendUnavailableError, match="Python"):
        preflight_run(_request(python=False), capability_lookup=lookup)


def test_prefer_numba_selects_exact_evidenced_numba_profile_when_available() -> None:
    python = _claim(
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="python",
    )
    numba_memetic = _claim(
        objective=BackendKind.NUMBA_NOPYTHON,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="numba-objective-python-polish",
    )
    lookup = _lookup_for(_capability((python, numba_memetic)))
    decision = preflight_run(
        _request(policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE, numba=True),
        capability_lookup=lookup,
    )
    assert decision.selected_claim is numba_memetic
    assert decision.selected_backend == ExecutionBackendProfile(
        BackendKind.NUMBA_NOPYTHON, BackendKind.PYTHON
    )
    assert decision.selected_claim.composition is CompositionKind.MEMETIC_2OPT
    assert decision.fallback_reason is None


@pytest.mark.parametrize("numba_available", [False, True])
def test_prefer_numba_falls_back_only_to_evidenced_python_with_reason(
    numba_available: bool,
) -> None:
    python = _claim(evidence_id="python-fallback")
    claims = (python,) if numba_available else (
        _claim(objective=BackendKind.NUMBA_NOPYTHON, evidence_id="numba"),
        python,
    )
    lookup = _lookup_for(_capability(claims))
    decision = preflight_run(
        _request(policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE, numba=numba_available),
        capability_lookup=lookup,
    )
    assert decision.selected_claim is python
    assert decision.selected_backend.objective is BackendKind.PYTHON
    assert decision.fallback_reason
    assert "Numba" in decision.fallback_reason


def test_prefer_numba_never_fabricates_a_fallback_claim() -> None:
    lookup = _lookup_for(_capability((_claim(objective=BackendKind.NUMBA_NOPYTHON),)))
    with pytest.raises(CapabilityEvidenceError, match="Python objective"):
        preflight_run(
            _request(policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE, numba=False),
            capability_lookup=lookup,
        )


def test_require_numba_requires_runtime_nopython_availability() -> None:
    lookup = _lookup_for(_capability((_claim(objective=BackendKind.NUMBA_NOPYTHON),)))
    with pytest.raises(BackendUnavailableError, match="nopython"):
        preflight_run(
            _request(policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE, numba=False),
            capability_lookup=lookup,
        )


def test_require_numba_requires_matching_evidenced_numba_claim() -> None:
    lookup = _lookup_for(_capability((_claim(),)))
    with pytest.raises(CapabilityEvidenceError, match="Numba nopython objective"):
        preflight_run(
            _request(policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE, numba=True),
            capability_lookup=lookup,
        )


def test_require_numba_supports_evidenced_python_polish_stage() -> None:
    mixed = _claim(
        objective=BackendKind.NUMBA_NOPYTHON,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="mixed-stage-evidence",
    )
    lookup = _lookup_for(_capability((mixed,)))
    decision = preflight_run(
        _request(policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE, numba=True),
        capability_lookup=lookup,
    )
    assert decision.selected_claim is mixed
    assert decision.selected_backend.objective is BackendKind.NUMBA_NOPYTHON
    assert decision.selected_backend.polish is BackendKind.PYTHON


def test_missing_executor_fails_before_exact_backend_claim_selection() -> None:
    lookup = _lookup_for(_capability((_claim(),)))
    with pytest.raises(ExecutorUnavailableError, match=_ID):
        preflight_run(
            _request(
                policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE,
                numba=False,
                registered=frozenset(),
            ),
            capability_lookup=lookup,
        )


def test_validation_order_is_lifecycle_problem_protocol_registration_then_claim() -> None:
    candidate = _lookup_for(_capability(lifecycle=LifecycleStatus.CANDIDATE))
    with pytest.raises(CandidateAlgorithmError):
        preflight_run(
            _request(problem=object(), budget=None, registered=frozenset()),
            capability_lookup=candidate,
        )
    verified = _lookup_for(_capability((_claim(),)))
    with pytest.raises(UnsupportedProblemContractError):
        preflight_run(
            _request(problem=object(), budget=None, registered=frozenset()),
            capability_lookup=verified,
        )
    with pytest.raises(UnsupportedProtocolError):
        preflight_run(
            _request(budget=None, registered=frozenset()),
            capability_lookup=verified,
        )
    with pytest.raises(ExecutorUnavailableError):
        preflight_run(
            _request(
                registered=frozenset(),
                policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE,
                numba=False,
            ),
            capability_lookup=verified,
        )
    with pytest.raises(BackendUnavailableError):
        preflight_run(
            _request(policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE, numba=False),
            capability_lookup=verified,
        )


def test_decision_and_provenance_are_immutable() -> None:
    claim = _claim(evidence_id="immutable-evidence")
    lookup = _lookup_for(_capability((claim,)))
    request = _request()
    decision = preflight_run(request, capability_lookup=lookup)
    assert decision.resolution is request.resolution
    assert decision.executor_registry_id == _ID
    assert decision.evidence_ids == ("immutable-evidence",)
    assert isinstance(decision.evidence_ids, tuple)
    with pytest.raises(FrozenInstanceError):
        decision.fallback_reason = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        decision.problem.matrix[0][0] = 99.0  # type: ignore[index]


def test_current_candidate_catalog_entry_remains_non_selectable() -> None:
    with pytest.raises(CandidateAlgorithmError):
        preflight_run(
            PreflightRequest(
                resolution=_resolution("Core-OrOpt-TSP"),
                problem=_TSP,
                protocol=ExecutionProtocol.FIXED_BUDGET,
                backend_policy=BackendPolicy.PYTHON_ONLY,
                evaluation_budget=10,
                registered_algorithm_ids=frozenset({"Core-OrOpt-TSP"}),
                runtime_backends=RuntimeBackendAvailability(True, False, "test"),
            )
        )


def test_unknown_algorithm_error_precedes_problem_validation() -> None:
    empty_lookup = build_capability_catalog(()).get

    with pytest.raises(UnknownAlgorithmError) as caught:
        preflight_run(
            _request(problem=object()),
            capability_lookup=empty_lookup,
        )

    assert caught.value.code == "unknown_algorithm"


def test_mixed_composition_claims_are_rejected_before_backend_selection() -> None:
    pure_python = _claim(
        objective=BackendKind.PYTHON,
        composition=CompositionKind.PURE,
        evidence_id="pure-python",
    )
    memetic_numba = _claim(
        objective=BackendKind.NUMBA_NOPYTHON,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="memetic-numba",
    )
    lookup = _lookup_for(_capability((pure_python, memetic_numba)))

    with pytest.raises(CapabilityEvidenceError, match="mixed composition"):
        preflight_run(
            _request(policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE, numba=True),
            capability_lookup=lookup,
        )


def test_python_only_rejects_numba_polish_even_when_numba_is_available() -> None:
    python_objective_numba_polish = _claim(
        objective=BackendKind.PYTHON,
        polish=BackendKind.NUMBA_NOPYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
    )
    lookup = _lookup_for(_capability((python_objective_numba_polish,)))

    with pytest.raises(CapabilityEvidenceError, match="Python objective"):
        preflight_run(
            _request(policy=BackendPolicy.PYTHON_ONLY, numba=True),
            capability_lookup=lookup,
        )


def test_prefer_numba_python_fallback_rejects_numba_polish() -> None:
    python_objective_numba_polish = _claim(
        objective=BackendKind.PYTHON,
        polish=BackendKind.NUMBA_NOPYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
    )
    lookup = _lookup_for(_capability((python_objective_numba_polish,)))

    with pytest.raises(CapabilityEvidenceError, match="Python objective"):
        preflight_run(
            _request(policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE, numba=False),
            capability_lookup=lookup,
        )


@pytest.mark.parametrize(
    "policy",
    [
        BackendPolicy.PREFER_NUMBA_OBJECTIVE,
        BackendPolicy.REQUIRE_NUMBA_OBJECTIVE,
    ],
)
def test_numba_objective_with_python_polish_requires_python_runtime(
    policy: BackendPolicy,
) -> None:
    numba_objective_python_polish = _claim(
        objective=BackendKind.NUMBA_NOPYTHON,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
    )
    lookup = _lookup_for(_capability((numba_objective_python_polish,)))

    with pytest.raises(BackendUnavailableError, match="Python polish"):
        preflight_run(
            _request(policy=policy, python=False, numba=True),
            capability_lookup=lookup,
        )


def test_mixed_composition_across_protocols_is_rejected_capability_wide() -> None:
    fixed_pure = _claim(
        protocol=ExecutionProtocol.FIXED_BUDGET,
        composition=CompositionKind.PURE,
        evidence_id="fixed-pure",
    )
    native_memetic = _claim(
        protocol=ExecutionProtocol.NATIVE_TERMINATION,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="native-memetic",
    )
    lookup = _lookup_for(_capability((fixed_pure, native_memetic)))

    with pytest.raises(CapabilityEvidenceError, match="mixed composition"):
        preflight_run(_request(), capability_lookup=lookup)


def test_mixed_composition_across_problems_is_rejected_capability_wide() -> None:
    tsp_pure = _claim(
        problem=ProblemContract.TSP,
        composition=CompositionKind.PURE,
        evidence_id="tsp-pure",
    )
    atsp_memetic = _claim(
        problem=ProblemContract.ATSP,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="atsp-memetic",
    )
    lookup = _lookup_for(_capability((tsp_pure, atsp_memetic)))

    with pytest.raises(CapabilityEvidenceError, match="mixed composition"):
        preflight_run(_request(problem=_TSP), capability_lookup=lookup)


def test_invalid_problem_precedes_global_mixed_composition_error() -> None:
    fixed_pure = _claim(
        protocol=ExecutionProtocol.FIXED_BUDGET,
        composition=CompositionKind.PURE,
        evidence_id="fixed-pure",
    )
    native_memetic = _claim(
        protocol=ExecutionProtocol.NATIVE_TERMINATION,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="native-memetic",
    )
    lookup = _lookup_for(_capability((fixed_pure, native_memetic)))

    with pytest.raises(UnsupportedProblemContractError):
        preflight_run(
            _request(problem=object()),
            capability_lookup=lookup,
        )


def test_missing_executor_precedes_global_mixed_composition_error() -> None:
    tsp_pure = _claim(
        problem=ProblemContract.TSP,
        composition=CompositionKind.PURE,
        evidence_id="tsp-pure",
    )
    atsp_memetic = _claim(
        problem=ProblemContract.ATSP,
        polish=BackendKind.PYTHON,
        composition=CompositionKind.MEMETIC_2OPT,
        evidence_id="atsp-memetic",
    )
    lookup = _lookup_for(_capability((tsp_pure, atsp_memetic)))

    with pytest.raises(ExecutorUnavailableError):
        preflight_run(
            _request(problem=_TSP, registered=frozenset()),
            capability_lookup=lookup,
        )
