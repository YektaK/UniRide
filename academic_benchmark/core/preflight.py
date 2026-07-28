"""Evidence-gated authorization for canonical academic TSP/ATSP execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from academic_benchmark.core.algorithm_errors import (
    BackendUnavailableError,
    CandidateAlgorithmError,
    CapabilityEvidenceError,
    ExecutorUnavailableError,
    PlannedAlgorithmError,
    UnknownAlgorithmError,
    UnsupportedProblemContractError,
    UnsupportedProtocolError,
)
from academic_benchmark.core.algorithm_resolution import ResolutionResult
from academic_benchmark.core.problem_validation import (
    ProblemValidationReport,
    validate_problem_for_preflight,
)
from uniride_core.algorithms.capabilities import (
    AlgorithmCapability,
    BackendKind,
    BackendPolicy,
    CapabilityClaim,
    ExecutionBackendProfile,
    ExecutionProtocol,
    LifecycleStatus,
    get_algorithm_capability,
)


@dataclass(frozen=True)
class RuntimeBackendAvailability:
    python: bool
    numba_nopython: bool
    detail: str


@dataclass(frozen=True)
class PreflightRequest:
    resolution: ResolutionResult
    problem: object
    protocol: ExecutionProtocol
    backend_policy: BackendPolicy
    evaluation_budget: int | None
    registered_algorithm_ids: frozenset[str]
    runtime_backends: RuntimeBackendAvailability


@dataclass(frozen=True)
class PreflightDecision:
    resolution: ResolutionResult
    problem: ProblemValidationReport
    protocol: ExecutionProtocol
    backend_policy: BackendPolicy
    selected_claim: CapabilityClaim
    selected_backend: ExecutionBackendProfile
    fallback_reason: str | None
    executor_registry_id: str
    evidence_ids: tuple[str, ...]


CapabilityLookup = Callable[[str], AlgorithmCapability | None]


def probe_runtime_backends() -> RuntimeBackendAvailability:
    """Execute the canonical tiny ATSP objective and report nopython truth."""
    try:
        import numpy as np
        from uniride_core.algorithms import numba_accel
    except Exception as exc:  # pragma: no cover - environment dependent
        return RuntimeBackendAvailability(
            python=True,
            numba_nopython=False,
            detail=f"Numba objective import failed: {type(exc).__name__}: {exc}",
        )

    if not getattr(numba_accel, "NUMBA_AVAILABLE", False):
        return RuntimeBackendAvailability(
            python=True,
            numba_nopython=False,
            detail="Numba is unavailable; the canonical ATSP objective was not executed.",
        )

    try:
        kernel = numba_accel._calculate_tour_length_atsp_numba
        matrix = np.ascontiguousarray(
            np.array(
                [[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]],
                dtype=np.float64,
            )
        )
        route = np.ascontiguousarray(np.array([0, 1, 2], dtype=np.int64))
        cost = float(kernel(route, matrix))
        if cost != 9.0:
            return RuntimeBackendAvailability(
                python=True,
                numba_nopython=False,
                detail=f"Numba ATSP objective returned {cost!r}; expected 9.0.",
            )
        if not getattr(kernel, "nopython_signatures", ()):
            return RuntimeBackendAvailability(
                python=True,
                numba_nopython=False,
                detail="Numba ATSP objective executed without a nopython signature.",
            )
    except Exception as exc:  # compilation/runtime failures are availability facts
        return RuntimeBackendAvailability(
            python=True,
            numba_nopython=False,
            detail=f"Numba ATSP objective probe failed: {type(exc).__name__}: {exc}",
        )

    return RuntimeBackendAvailability(
        python=True,
        numba_nopython=True,
        detail="Canonical Numba ATSP objective probe passed in nopython mode.",
    )


def _validate_protocol_budget(request: PreflightRequest) -> None:
    budget = request.evaluation_budget
    if request.protocol is ExecutionProtocol.FIXED_BUDGET:
        if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
            raise UnsupportedProtocolError(
                "fixed_budget requires a positive integer evaluation budget"
            )
        return
    if request.protocol is ExecutionProtocol.NATIVE_TERMINATION:
        if budget is not None:
            raise UnsupportedProtocolError(
                "native_termination must not include an evaluation budget"
            )
        return
    raise UnsupportedProtocolError(f"Unsupported execution protocol: {request.protocol!r}")


def _evidenced_claims(
    capability: AlgorithmCapability,
    report: ProblemValidationReport,
    protocol: ExecutionProtocol,
) -> tuple[CapabilityClaim, ...]:
    problem_claims = tuple(
        claim for claim in capability.claims if claim.problem is report.contract
    )
    if not problem_claims:
        raise UnsupportedProblemContractError(
            f"Algorithm '{capability.canonical_id}' has no evidenced "
            f"{report.contract.value} claim."
        )
    protocol_claims = tuple(
        claim for claim in problem_claims if claim.protocol is protocol
    )
    if not protocol_claims:
        raise UnsupportedProtocolError(
            f"Algorithm '{capability.canonical_id}' has no evidenced "
            f"{protocol.value} claim for {report.contract.value}."
        )
    evidenced = tuple(
        claim
        for claim in protocol_claims
        if claim.fixed_seed_deterministic
        and claim.truthful_result_reporting
        and (
            report.contract.value != "atsp" or claim.directed_cost_preserved
        )
        and (
            protocol is not ExecutionProtocol.FIXED_BUDGET
            or claim.exact_objective_accounting
        )
    )
    if not evidenced:
        raise CapabilityEvidenceError(
            f"Algorithm '{capability.canonical_id}' has no complete executable "
            "evidence for the requested problem and protocol."
        )
    return evidenced


def _claim_with_objective(
    claims: tuple[CapabilityClaim, ...], objective: BackendKind
) -> CapabilityClaim | None:
    return next(
        (claim for claim in claims if claim.backend_profile.objective is objective),
        None,
    )


def _select_backend_claim(
    request: PreflightRequest,
    claims: tuple[CapabilityClaim, ...],
) -> tuple[CapabilityClaim, str | None]:
    runtime = request.runtime_backends
    python_claim = _claim_with_objective(claims, BackendKind.PYTHON)
    numba_claim = _claim_with_objective(claims, BackendKind.NUMBA_NOPYTHON)

    if request.backend_policy is BackendPolicy.PYTHON_ONLY:
        if not runtime.python:
            raise BackendUnavailableError(
                f"Python objective runtime is unavailable: {runtime.detail}"
            )
        if python_claim is None:
            raise CapabilityEvidenceError(
                "No evidenced Python objective claim matches the exact request."
            )
        return python_claim, None

    if request.backend_policy is BackendPolicy.REQUIRE_NUMBA_OBJECTIVE:
        if not runtime.numba_nopython:
            raise BackendUnavailableError(
                f"Numba nopython objective is unavailable: {runtime.detail}"
            )
        if numba_claim is None:
            raise CapabilityEvidenceError(
                "No evidenced Numba nopython objective claim matches the exact request."
            )
        return numba_claim, None

    if request.backend_policy is BackendPolicy.PREFER_NUMBA_OBJECTIVE:
        if runtime.numba_nopython and numba_claim is not None:
            return numba_claim, None
        if not runtime.python:
            raise BackendUnavailableError(
                "Neither the preferred Numba objective nor Python fallback runtime "
                f"is available: {runtime.detail}"
            )
        if python_claim is None:
            raise CapabilityEvidenceError(
                "No evidenced Python objective claim is available for explicit fallback."
            )
        if runtime.numba_nopython:
            reason = (
                "No evidenced Numba nopython objective claim matched; selected the "
                "evidenced Python objective claim before execution."
            )
        else:
            reason = (
                f"Numba nopython objective unavailable ({runtime.detail}); selected "
                "the evidenced Python objective claim before execution."
            )
        return python_claim, reason

    raise BackendUnavailableError(
        f"Unsupported backend policy: {request.backend_policy!r}"
    )


def preflight_run(
    request: PreflightRequest,
    *,
    capability_lookup: CapabilityLookup = get_algorithm_capability,
) -> PreflightDecision:
    """Authorize one exact claim without constructing or looking up an executor."""
    canonical_id = request.resolution.canonical_id
    capability = capability_lookup(canonical_id)
    if capability is None:
        raise UnknownAlgorithmError(canonical_id)
    if capability.lifecycle is LifecycleStatus.CANDIDATE:
        raise CandidateAlgorithmError(canonical_id)
    if capability.lifecycle is LifecycleStatus.PLANNED:
        raise PlannedAlgorithmError(canonical_id)
    if capability.lifecycle is not LifecycleStatus.VERIFIED:
        raise CapabilityEvidenceError(
            f"Algorithm '{canonical_id}' has an unsupported lifecycle state."
        )

    try:
        report = validate_problem_for_preflight(request.problem)
    except ValueError as exc:
        raise UnsupportedProblemContractError(str(exc)) from exc

    _validate_protocol_budget(request)

    if canonical_id not in request.registered_algorithm_ids:
        raise ExecutorUnavailableError(
            f"Canonical executor '{canonical_id}' is not registered."
        )

    claims = _evidenced_claims(capability, report, request.protocol)
    selected_claim, fallback_reason = _select_backend_claim(request, claims)
    return PreflightDecision(
        resolution=request.resolution,
        problem=report,
        protocol=request.protocol,
        backend_policy=request.backend_policy,
        selected_claim=selected_claim,
        selected_backend=selected_claim.backend_profile,
        fallback_reason=fallback_reason,
        executor_registry_id=canonical_id,
        evidence_ids=tuple(selected_claim.evidence_ids),
    )
