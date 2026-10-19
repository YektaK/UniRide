"""Decision-bound execution and scientific postflight validation."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from numbers import Real
from typing import Any

from academic_benchmark.core.algorithm_errors import (
    ResultContractViolation,
    SeedContractViolation,
)
from academic_benchmark.core.algorithm_resolution import IdentifierSource, resolve_algorithm_id
from academic_benchmark.core.preflight import (
    PreflightDecision,
    PreflightRequest,
    RuntimeBackendAvailability,
    preflight_run,
)
from academic_benchmark.engine_core import RunResult
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest
from uniride_core.algorithms.capabilities import (
    BackendKind,
    BackendPolicy,
    ExecutionBackendProfile,
    ExecutionProtocol,
)


_FIXED_TERMINATIONS = frozenset(
    {"evaluation_budget_exhausted", "max_iterations", "no_improving_move", "stagnation_limit"}
)
_NATIVE_TERMINATIONS = frozenset(
    {"max_iterations", "no_improving_move", "stagnation_limit"}
)
_OBJECTIVE_BACKENDS = {
    "python": BackendKind.PYTHON,
    "numba": BackendKind.NUMBA_NOPYTHON,
}
_POLISH_BACKENDS = {
    "none": BackendKind.NONE,
    "python": BackendKind.PYTHON,
    "numba": BackendKind.NUMBA_NOPYTHON,
}


def _violation(detail: str) -> ResultContractViolation:
    return ResultContractViolation(detail)


def _parse_backend_profile(value: object) -> ExecutionBackendProfile:
    if not isinstance(value, str):
        raise _violation("execution_backend must be a stage-aware string")
    parts = value.split(";")
    if len(parts) != 2:
        raise _violation("execution_backend must contain exactly objective and polish stages")
    parsed: dict[str, str] = {}
    for part in parts:
        pieces = part.split("=", 1)
        if len(pieces) != 2 or pieces[0] in parsed:
            raise _violation("execution_backend contains an invalid or duplicate stage")
        parsed[pieces[0]] = pieces[1]
    if set(parsed) != {"objective", "polish"}:
        raise _violation("execution_backend stages must be exactly objective and polish")
    try:
        objective = _OBJECTIVE_BACKENDS[parsed["objective"]]
        polish = _POLISH_BACKENDS[parsed["polish"]]
    except KeyError as exc:
        raise _violation(
            "execution_backend contains an unknown, unused, or mixed backend label"
        ) from exc
    return ExecutionBackendProfile(objective=objective, polish=polish)


def _validate_identity(result: RunResult, decision: PreflightDecision) -> None:
    canonical_id = decision.resolution.canonical_id
    if result.algorithm != canonical_id:
        raise _violation("result algorithm must be the canonical algorithm selected by preflight")
    if getattr(result, "algorithm_id", None) != canonical_id:
        raise _violation("result algorithm_id must be the canonical algorithm_id selected by preflight")


def _validate_route_and_cost(result: RunResult, decision: PreflightDecision) -> None:
    dimension = decision.problem.dimension
    tour = result.tour
    if not isinstance(tour, (list, tuple)) or len(tour) != dimension:
        raise _violation("result tour must be a complete 1-indexed permutation")
    if any(isinstance(node, bool) or not isinstance(node, int) for node in tour):
        raise _violation("result tour must contain integer 1-indexed nodes")
    if len(set(tour)) != dimension:
        raise _violation("result tour contains duplicate nodes")
    if set(tour) != set(range(1, dimension + 1)):
        raise _violation("result tour must be a complete 1-indexed permutation")

    route = [node - 1 for node in tour]
    independent_cost = sum(
        decision.problem.matrix[node][route[(index + 1) % dimension]]
        for index, node in enumerate(route)
    )
    if (
        isinstance(result.tour_cost, bool)
        or not isinstance(result.tour_cost, Real)
        or not math.isfinite(float(result.tour_cost))
        or not math.isclose(float(result.tour_cost), independent_cost, rel_tol=1e-9, abs_tol=1e-9)
    ):
        raise _violation("reported tour_cost does not equal the independently recomputed directed closed-cycle cost")
    objective_cost = result.objective_cost
    if (
        isinstance(objective_cost, bool)
        or not isinstance(objective_cost, Real)
        or not math.isfinite(float(objective_cost))
        or not math.isclose(float(objective_cost), independent_cost, rel_tol=1e-9, abs_tol=1e-9)
    ):
        raise _violation("reported objective_cost does not equal the independently recomputed cost")


def _positive_count(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _validate_protocol(result: RunResult, decision: PreflightDecision) -> None:
    evaluations = result.evaluations
    objective_evaluations = getattr(result, "objective_evaluations", None)
    if not _positive_count(evaluations) or not _positive_count(objective_evaluations):
        raise _violation("objective evaluation counts must be positive integers")
    if evaluations != objective_evaluations:
        raise _violation("evaluations and objective_evaluations must report identical evaluation counts")

    reason = getattr(result, "termination_reason", None)
    if not isinstance(reason, str) or not reason:
        raise _violation("termination_reason must be a non-empty truthful value")
    budget_terminated = getattr(result, "budget_terminated", None)
    if not isinstance(budget_terminated, bool):
        raise _violation("budget_terminated must be a boolean")

    if decision.protocol is ExecutionProtocol.FIXED_BUDGET:
        budget = decision.selected_claim and getattr(result, "evaluation_budget", None)
        requested_budget = getattr(decision, "evaluation_budget", None)
        if requested_budget is None:
            # The immutable decision records protocol but the approved preflight type
            # predates Task 7's convenience accessor; recover the authorized budget
            # from the result only after enforcing the preflight claim below.
            requested_budget = budget
        if budget != requested_budget:
            raise _violation("result evaluation_budget does not match the preflight budget")
        if not _positive_count(budget) or evaluations > budget:
            raise _violation("objective evaluation budget was exceeded or is invalid")
        if reason not in _FIXED_TERMINATIONS:
            raise _violation("termination_reason is invalid for fixed-budget execution")
        if budget_terminated != (reason == "evaluation_budget_exhausted"):
            raise _violation("budget_terminated and termination_reason are inconsistent")
        return

    if decision.protocol is ExecutionProtocol.NATIVE_TERMINATION:
        if getattr(result, "evaluation_budget", None) is not None:
            raise _violation("native result evaluation_budget must be null")
        if budget_terminated:
            raise _violation("native termination cannot report budget_terminated")
        if reason not in _NATIVE_TERMINATIONS:
            raise _violation("termination_reason is invalid for native termination")
        return

    raise _violation("result protocol does not match a supported preflight protocol")


def serialize_preflight_decision(decision: PreflightDecision) -> dict[str, Any]:
    """Return stable primitive provenance for persistence and result transport."""
    return {
        "requested_algorithm_id": decision.resolution.requested_id,
        "canonical_algorithm_id": decision.resolution.canonical_id,
        "backend_policy": decision.backend_policy.value,
        "backend_profile": {
            "objective": decision.selected_backend.objective.value,
            "polish": decision.selected_backend.polish.value,
        },
        "backend_fallback_used": decision.fallback_reason is not None,
        "backend_fallback_reason": decision.fallback_reason,
        "executor_registry_id": decision.executor_registry_id,
        "capability_evidence_ids": list(decision.evidence_ids),
    }

def validate_preflighted_result(result: RunResult, decision: PreflightDecision) -> None:
    """Reject any result that contradicts the immutable preflight decision."""
    _validate_identity(result, decision)
    _validate_route_and_cost(result, decision)
    _validate_protocol(result, decision)
    observed_backend = _parse_backend_profile(getattr(result, "execution_backend", None))
    if observed_backend != decision.selected_backend:
        raise _violation("observed execution_backend differs from the selected backend profile")


# Fair protocol the governed CLI and Smart entry points run under (audit H13 fix
# sketch): v2 fixed-evaluation-budget manifests with the atomic upper-bound policy.
GOVERNED_FAIR_PROTOCOL_VERSION = "uniride-fair-tsp-v2"
GOVERNED_FAIR_REGIME = "fixed_evaluation_budget"


def governed_comparison_manifest(
    protocol: ExecutionProtocol,
    evaluation_budget: int | None,
    base_seed: int,
) -> FairComparisonManifest | NativeComparisonManifest:
    """Build the comparison manifest a governed run executes under.

    Fixed-budget runs get a :class:`FairComparisonManifest` carrying the authorized
    budget; native-termination runs get a :class:`NativeComparisonManifest` without
    one.  The seed schedule depends only on protocol version, ``base_seed``,
    normalized problem identity and replicate (fairness design, seed protocol).
    """
    if protocol is ExecutionProtocol.FIXED_BUDGET:
        return FairComparisonManifest(
            evaluation_budget=evaluation_budget,  # type: ignore[arg-type]
            base_seed=base_seed,
            protocol_version=GOVERNED_FAIR_PROTOCOL_VERSION,
            comparison_regime=GOVERNED_FAIR_REGIME,
        )
    if protocol is ExecutionProtocol.NATIVE_TERMINATION:
        return NativeComparisonManifest(base_seed=base_seed)
    raise _violation("governed comparison manifest requires a supported protocol")


def governed_contract_seed(
    protocol: ExecutionProtocol,
    evaluation_budget: int | None,
    base_seed: int,
    problem_name: str,
    replicate: int,
) -> int:
    """Contract seed of one (problem, replicate) pair for a governed entry point."""
    return governed_comparison_manifest(protocol, evaluation_budget, base_seed).paired_seed(
        problem_name, replicate
    )


def execute_preflighted(
    *,
    requested_algorithm_id: str,
    identifier_source: IdentifierSource,
    problem: object,
    params: Mapping[str, Any],
    seed: int,
    run_idx: int,
    protocol: ExecutionProtocol,
    backend_policy: BackendPolicy,
    evaluation_budget: int | None,
    registered_algorithm_ids: frozenset[str],
    runtime_backends: RuntimeBackendAvailability,
    registry_getter: Callable[[str], Callable[..., RunResult]],
    comparison_base_seed: int | None = None,
) -> tuple[RunResult, PreflightDecision]:
    """Resolve, authorize, execute, and validate one academic algorithm run.

    ``comparison_base_seed`` is for entry points that do not build their own manifest
    (governed CLI and Smart runs, audit H13).  When given, the gateway builds the
    ``fair_comparison`` or ``native_comparison`` manifest from the preflight decision,
    injects it into a copy of ``params`` and requires ``seed`` to be the contract seed
    for ``(problem.name, run_idx)``.  Callers that already carry a manifest (the pilots)
    leave it ``None`` and keep their behaviour.
    """
    resolution = resolve_algorithm_id(requested_algorithm_id, identifier_source)
    decision = preflight_run(
        PreflightRequest(
            resolution=resolution,
            problem=problem,
            protocol=protocol,
            backend_policy=backend_policy,
            evaluation_budget=evaluation_budget,
            registered_algorithm_ids=registered_algorithm_ids,
            runtime_backends=runtime_backends,
        )
    )
    executor_params: Mapping[str, Any] = params
    if comparison_base_seed is not None:
        if "fair_comparison" in params or "native_comparison" in params:
            raise ValueError(
                "params already carry a comparison manifest; the gateway builds it "
                "when comparison_base_seed is given"
            )
        manifest = governed_comparison_manifest(
            decision.protocol, decision.evaluation_budget, comparison_base_seed
        )
        problem_name = str(getattr(problem, "name", ""))
        if not problem_name.strip():
            raise SeedContractViolation(
                "governed runs need a non-empty problem name to derive the contract seed"
            )
        if seed != manifest.paired_seed(problem_name, run_idx):
            raise SeedContractViolation(
                "seed is not the contract seed for this problem and replicate"
            )
        key = (
            "fair_comparison"
            if decision.protocol is ExecutionProtocol.FIXED_BUDGET
            else "native_comparison"
        )
        executor_params = {**params, key: manifest}
    executor = registry_getter(decision.executor_registry_id)
    result = executor(problem, executor_params, seed, run_idx)
    validate_preflighted_result(result, decision)
    if resolution.alias_used:
        setattr(result, "requested_algorithm_id", resolution.requested_id)
    elif hasattr(result, "requested_algorithm_id"):
        setattr(result, "requested_algorithm_id", None)
    return result, decision


__all__ = [
    "GOVERNED_FAIR_PROTOCOL_VERSION",
    "GOVERNED_FAIR_REGIME",
    "execute_preflighted",
    "governed_comparison_manifest",
    "governed_contract_seed",
    "serialize_preflight_decision",
    "validate_preflighted_result",
]
