"""Package B Task 5 RED tests for the production optimize boundary."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from compute_policy import ComputePolicy, PolicyValidationError
from models import schemas
from routers import optimization
from strategies.canonical import (
    ResolvedStrategy,
    StrategyRegistryContractError,
    StrategyUnavailableError,
    UnknownStrategyError,
)


DEPOT = schemas.LocationNode(id="depot", lat=0.0, lng=0.0)
FEASIBLE = {"is_feasible": True, "violation_count": 0, "violations": []}
INFEASIBLE = {
    "is_feasible": False,
    "violation_count": 1,
    "violations": [
        {"type": "capacity", "severity": "error", "details": "over capacity"}
    ],
}


def _request(algorithm: str = "ga", **overrides) -> schemas.OptimizationRequest:
    values = {"algorithm": algorithm, "students": [], "depot": DEPOT}
    values.update(overrides)
    return schemas.OptimizationRequest(**values)


def _response(*, success: bool = True) -> schemas.OptimizationResponse:
    return schemas.OptimizationResponse(
        algorithm_used="wrong-singleton-label", success=success, routes=[]
    )


@dataclass
class _Strategy:
    name: str = "genetic_algorithm"
    response: schemas.OptimizationResponse | None = None
    error: Exception | None = None
    optimize_calls: int = 0
    seen_request: schemas.OptimizationRequest | None = None

    def optimize(self, request):
        self.optimize_calls += 1
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return self.response


def _metadata(requested="ga", canonical="genetic_algorithm"):
    return schemas.AppliedComputePolicyInfo(
        profile_id="production-conservative-v1",
        algorithm_requested=requested,
        algorithm_canonical=canonical,
        student_count=0,
        vehicle_count=0,
        cancellation_mode="none",
        limits={},
    )


def _install(
    monkeypatch,
    strategies,
    *,
    requested="ga",
    canonical="genetic_algorithm",
    policy_error: Exception | None = None,
):
    created = []

    def factory():
        strategy = strategies[len(created)] if isinstance(strategies, list) else strategies
        created.append(strategy)
        return strategy

    resolution = ResolvedStrategy(requested, canonical, factory, (requested,))
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(optimization, "load_compute_policy", lambda: ComputePolicy())

    def apply(request, actual_resolution, strategy, policy):
        assert actual_resolution is resolution
        assert strategy is created[-1]
        assert strategy.optimize_calls == 0, "policy must apply before execution"
        if policy_error is not None:
            raise policy_error
        return request.model_copy(deep=True), _metadata(requested, canonical)

    monkeypatch.setattr(optimization, "apply_compute_policy", apply)
    monkeypatch.setattr(
        optimization, "certify_optimization_response", lambda request, result: FEASIBLE
    )
    return created


def test_optimize_resolves_alias_uses_fresh_instance_and_preserves_request(monkeypatch):
    first = _Strategy(response=_response())
    second = _Strategy(response=_response())
    created = _install(monkeypatch, [first, second])
    request = _request(ga_config={"max_iterations": 7})
    before = request.model_dump()

    first_result = optimization.optimize_route(request)
    second_result = optimization.optimize_route(request)

    assert created == [first, second]
    assert first is not second
    assert request.model_dump() == before
    assert first.seen_request is not request
    assert first.seen_request.ga_config is not request.ga_config
    for result in (first_result, second_result):
        assert result.algorithm_used == "genetic_algorithm"
        assert result.algorithm_requested == "ga"
        assert result.applied_policy == _metadata()


@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (optimization.UnknownStrategyError("Unknown algorithm 'missing'"), "Unknown algorithm 'missing'"),
        (
            optimization.StrategyUnavailableError("Algorithm 'pyvrp' is unavailable"),
            "Algorithm 'pyvrp' is unavailable",
        ),
    ],
)
def test_optimize_maps_resolution_failures_to_sanitized_400_before_work(
    monkeypatch, error, detail
):
    monkeypatch.setattr(
        optimization, "resolve_strategy", lambda key: (_ for _ in ()).throw(error)
    )
    monkeypatch.setattr(
        optimization,
        "apply_compute_policy",
        lambda *args: pytest.fail("policy must not run after resolution failure"),
    )

    with pytest.raises(HTTPException) as exc_info:
        optimization.optimize_route(_request("missing"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == detail
    assert "applied_policy" not in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "message",
    [
        "ga_config does not apply to greedy",
        "max_iterations must be in [1, 2000]",
    ],
)
def test_optimize_maps_policy_applicability_and_limit_failures_to_422_before_work(
    monkeypatch, message
):
    strategy = _Strategy(response=_response())
    _install(monkeypatch, strategy, policy_error=optimization.PolicyValidationError(message))

    with pytest.raises(HTTPException) as exc_info:
        optimization.optimize_route(_request())

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == message
    assert strategy.optimize_calls == 0
    assert "applied_policy" not in str(exc_info.value.detail)


@pytest.mark.parametrize("solver_success", [True, False])
def test_optimize_attaches_identity_policy_and_certificate_to_solver_outcome(
    monkeypatch, solver_success
):
    _install(monkeypatch, _Strategy(response=_response(success=solver_success)))

    result = optimization.optimize_route(_request())

    assert result.success is solver_success
    assert result.algorithm_used == "genetic_algorithm"
    assert result.algorithm_requested == "ga"
    assert result.applied_policy == _metadata()
    assert result.feasibility_certificate.is_feasible is True


def test_optimize_keeps_package_a_fail_closed_certificate_after_policy(monkeypatch):
    _install(monkeypatch, _Strategy(response=_response()))
    monkeypatch.setattr(
        optimization, "certify_optimization_response", lambda request, result: INFEASIBLE
    )

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert result.feasibility_certificate.is_feasible is False
    assert result.algorithm_used == "genetic_algorithm"
    assert result.algorithm_requested == "ga"
    assert result.applied_policy == _metadata()
    assert "capacity" in result.error_message


def test_optimize_none_outcome_is_typed_and_policy_annotated(monkeypatch):
    _install(monkeypatch, _Strategy(response=None))

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert result.feasibility_certificate.certify_error == optimization._UNAVAILABLE_CERTIFICATE_ERROR
    assert result.algorithm_used == "genetic_algorithm"
    assert result.algorithm_requested == "ga"
    assert result.applied_policy == _metadata()


def test_optimize_exception_becomes_sanitized_typed_failure_with_policy(monkeypatch):
    _install(monkeypatch, _Strategy(error=RuntimeError("secret solver detail")))

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert result.feasibility_certificate.certify_error == optimization._UNAVAILABLE_CERTIFICATE_ERROR
    assert result.algorithm_used == "genetic_algorithm"
    assert result.algorithm_requested == "ga"
    assert result.applied_policy == _metadata()
    assert "secret solver detail" not in (result.error_message or "")


def test_optimize_maps_only_named_resolution_errors_to_400(monkeypatch):
    monkeypatch.setattr(
        optimization,
        "resolve_strategy",
        lambda key: (_ for _ in ()).throw(RuntimeError("resolver bug")),
    )

    with pytest.raises(RuntimeError, match="resolver bug"):
        optimization.optimize_route(_request())


def test_optimize_does_not_convert_unexpected_policy_value_error_to_422(monkeypatch):
    resolution = ResolvedStrategy(
        "ga", "genetic_algorithm", lambda: _Strategy(response=_response()), ("ga",)
    )
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(optimization, "load_compute_policy", lambda: ComputePolicy())
    monkeypatch.setattr(
        optimization,
        "apply_compute_policy",
        lambda *args: (_ for _ in ()).throw(ValueError("policy bug")),
    )

    with pytest.raises(ValueError, match="policy bug"):
        optimization.optimize_route(_request())


def test_optimize_named_registry_contract_error_is_deterministic_400(monkeypatch):
    error = optimization.StrategyRegistryContractError("registry contract mismatch")
    monkeypatch.setattr(
        optimization,
        "resolve_strategy",
        lambda key: (_ for _ in ()).throw(error),
    )

    with pytest.raises(HTTPException) as exc_info:
        optimization.optimize_route(_request())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "registry contract mismatch"


# ---------------------------------------------------------------------------
# Task 6: oversized exact/permutation requests must fail before solver work
# ---------------------------------------------------------------------------

def _many_students(count=11):
    return [
        schemas.StudentNode(
            id=f"S{i}",
            name=f"S{i}",
            location_code=f"L{i}",
            coordinates={"lat": float(i), "lng": 0.0},
            disability_type="So",
        )
        for i in range(count)
    ]


def _install_permutation(monkeypatch, requested, strategy):
    resolution = ResolvedStrategy(
        requested, "permutation_tsp", lambda: strategy, (requested,)
    )
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(optimization, "load_compute_policy", lambda: ComputePolicy())
    monkeypatch.setattr(
        optimization,
        "certify_optimization_response",
        lambda request, result: FEASIBLE,
    )

    def apply(request, actual_resolution, actual_strategy, policy):
        assert actual_resolution is resolution
        assert actual_strategy is strategy
        effective = request.model_copy(deep=True)
        return effective, schemas.AppliedComputePolicyInfo(
            profile_id="production-conservative-v1",
            algorithm_requested=requested,
            algorithm_canonical="permutation_tsp",
            student_count=len(effective.students),
            vehicle_count=0,
            cancellation_mode="none",
            limits={},
        )

    monkeypatch.setattr(optimization, "apply_compute_policy", apply)
    return resolution


@pytest.mark.parametrize("requested", ["permutation_tsp", "exact"])
def test_optimize_rejects_oversize_exact_before_solver_with_sanitized_failure(
    monkeypatch, requested
):
    strategy = _Strategy(name="permutation_tsp", response=_response())
    _install_permutation(monkeypatch, requested, strategy)
    request = _request(requested, students=_many_students())
    before = request.model_dump()

    result = optimization.optimize_route(request)

    assert strategy.optimize_calls == 0
    assert request.model_dump() == before
    assert [student.id for student in request.students] == [
        f"S{i}" for i in range(11)
    ]
    assert result.success is False
    assert result.algorithm_used == "permutation_tsp"
    assert result.algorithm_requested == requested
    assert result.applied_policy.algorithm_canonical == "permutation_tsp"
    assert result.applied_policy.algorithm_requested == requested
    assert result.applied_policy.student_count == 11
    assert (
        result.feasibility_certificate.certify_error
        == optimization._UNAVAILABLE_CERTIFICATE_ERROR
    )
    error_text = result.error_message or ""
    assert "S0" not in error_text
    assert "L0" not in error_text
    assert "Traceback" not in error_text


def test_optimize_allows_exact_at_limit_with_solver_invocation(monkeypatch):
    strategy = _Strategy(name="permutation_tsp", response=_response())
    _install_permutation(monkeypatch, "permutation_tsp", strategy)
    request = _request("permutation_tsp", students=_many_students(10))

    result = optimization.optimize_route(request)

    assert strategy.optimize_calls == 1
    assert result.success is True
    assert result.algorithm_used == "permutation_tsp"
