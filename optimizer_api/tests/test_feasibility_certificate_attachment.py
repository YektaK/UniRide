import json
from copy import deepcopy

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from models import schemas
from routers import optimization

class _StubStrategy:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def optimize(self, request):
        if self.error is not None:
            raise self.error
        return self.response


def _install_strategy(monkeypatch, key, strategy):
    installed = getattr(optimization, "_test_strategies", None)
    if installed is None:
        installed = {}
        monkeypatch.setattr(
            optimization, "_test_strategies", installed, raising=False
        )
    installed[key] = strategy

    def resolve(requested):
        requested = requested.strip().lower()
        if requested not in installed:
            raise optimization.UnknownStrategyError(
                f"Unknown algorithm '{requested}'"
            )
        template = installed[requested]

        def factory():
            instance = deepcopy(template)
            instance.name = requested
            return instance

        return optimization.ResolvedStrategy(
            requested, requested, factory, (requested,)
        )

    def resolve_unique(keys):
        unique = {}
        for requested in keys:
            item = resolve(requested)
            unique.setdefault(item.canonical, item)
        return list(unique.values())

    monkeypatch.setattr(optimization, "resolve_strategy", resolve)
    monkeypatch.setattr(optimization, "resolve_unique_strategies", resolve_unique)


def _run_installed_algorithm(key, request):
    resolution = optimization.resolve_strategy(key)
    prepared = optimization._prepare_comparison_run(
        resolution, request, optimization.load_compute_policy()
    )
    return optimization._run_single_algorithm(prepared)


def _request(algorithm="stub"):
    return schemas.OptimizationRequest(
        algorithm=algorithm,
        students=[],
        depot=schemas.LocationNode(id="depot", lat=0.0, lng=0.0),
    )


def _response(success=True):
    return schemas.OptimizationResponse(
        algorithm_used="stub",
        success=success,
        routes=[],
    )


def _payload(is_feasible=True):
    return {
        "is_feasible": is_feasible,
        "violation_count": 0 if is_feasible else 1,
        "violations": [] if is_feasible else [
            {"type": "capacity", "severity": "error", "details": "over capacity"}
        ],
    }


def _certificate_model():
    model = getattr(schemas, "FeasibilityCertificateInfo", None)
    assert model is not None, "typed certificate model is missing"
    return model


def test_certificate_model_enforces_invariants():
    model = _certificate_model()
    valid = model(is_feasible=True, violation_count=0, violations=[])
    assert valid.is_feasible is True

    with pytest.raises(ValidationError):
        model(is_feasible=False, violation_count=2, violations=[])
    with pytest.raises(ValidationError):
        model(
            is_feasible=True,
            violation_count=1,
            violations=[{"type": "x", "severity": "error", "details": "x"}],
        )
    with pytest.raises(ValidationError):
        model(
            is_feasible=True,
            violation_count=0,
            violations=[],
            certify_error="must fail closed",
        )


def test_violation_info_defaults_optional_context_to_none_in_serialization():
    violation = schemas.FeasibilityViolationInfo(
        type="x", severity="error", details="x"
    )

    assert violation.route_index is None
    assert violation.node is None
    assert violation.model_dump()["route_index"] is None
    assert violation.model_dump()["node"] is None


def test_legacy_response_models_default_certificate_to_none_and_serialize_it():
    optimization_response = schemas.OptimizationResponse(
        algorithm_used="test", success=True, routes=[]
    )
    algorithm_result = schemas.AlgorithmResult(
        algorithm="test",
        success=True,
        total_vehicles=0,
        total_duration_minutes=0.0,
        execution_time_seconds=0.0,
        routes=[],
    )

    for response in (optimization_response, algorithm_result):
        assert response.feasibility_certificate is None
        assert response.model_dump()["feasibility_certificate"] is None
def test_certificate_field_is_optional_and_typed_in_openapi():
    assert "feasibility_certificate" in schemas.OptimizationResponse.model_fields
    assert "feasibility_certificate" in schemas.AlgorithmResult.model_fields

    app = FastAPI()
    app.include_router(optimization.router)
    components = app.openapi()["components"]["schemas"]
    for response_name in ("OptimizationResponse", "AlgorithmResult"):
        prop = components[response_name]["properties"]["feasibility_certificate"]
        assert {"$ref": "#/components/schemas/FeasibilityCertificateInfo"} in prop["anyOf"]


def test_optimize_attaches_the_single_feasible_typed_certificate(monkeypatch):
    payload = _payload()
    calls = 0

    def certify(request, result):
        nonlocal calls
        calls += 1
        return payload

    _install_strategy(monkeypatch, "stub", _StubStrategy(_response()))
    monkeypatch.setattr(optimization, "certify_optimization_response", certify)

    result = optimization.optimize_route(_request())

    assert calls == 1
    assert result.feasibility_certificate.model_dump(exclude_none=True) == payload
    assert result.success is payload["is_feasible"]
    assert result.error_message is None


def test_optimize_attaches_infeasible_certificate_and_legacy_json(monkeypatch):
    payload = _payload(is_feasible=False)
    calls = 0

    def certify(request, result):
        nonlocal calls
        calls += 1
        return payload

    _install_strategy(monkeypatch, "stub", _StubStrategy(_response()))
    monkeypatch.setattr(optimization, "certify_optimization_response", certify)

    result = optimization.optimize_route(_request())

    assert calls == 1
    assert result.feasibility_certificate.model_dump(exclude_none=True) == payload
    assert result.success is payload["is_feasible"]
    assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)


def test_boundaries_fail_closed_for_invalid_certificate_payload(monkeypatch):
    invalid_payload = {"is_feasible": True, "violation_count": 1, "violations": []}
    _install_strategy(monkeypatch, "stub", _StubStrategy(_response()))
    monkeypatch.setattr(optimization, "certify_optimization_response", lambda request, result: invalid_payload)

    optimize_result = optimization.optimize_route(_request())
    compare_result = _run_installed_algorithm("stub", _request())

    for result in (optimize_result, compare_result):
        assert result.success is False
        assert result.feasibility_certificate.certify_error == optimization._INVALID_CERTIFICATE_ERROR
        assert "validation error" not in result.error_message.lower()
        assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)


def test_compare_no_result_boundaries_attach_sanitized_unavailable_certificate(monkeypatch):
    _install_strategy(monkeypatch, "broken", _StubStrategy(error=RuntimeError("secret strategy failure")))

    with pytest.raises(optimization.UnknownStrategyError):
        optimization.resolve_strategy("missing")
    broken = _run_installed_algorithm("broken", _request("broken"))

    for result in (broken,):
        assert result.success is False
        assert result.feasibility_certificate.certify_error == optimization._UNAVAILABLE_CERTIFICATE_ERROR
        assert "secret strategy failure" not in result.error_message
        assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)


def test_optimize_preserves_solver_failure_with_feasible_certificate(monkeypatch):
    payload = _payload()
    calls = 0

    def certify(request, result):
        nonlocal calls
        calls += 1
        return payload

    _install_strategy(monkeypatch, "stub", _StubStrategy(_response(success=False)))
    monkeypatch.setattr(optimization, "certify_optimization_response", certify)

    result = optimization.optimize_route(_request())

    assert calls == 1
    assert result.success is False
    assert result.feasibility_certificate.model_dump(exclude_none=True) == payload
    assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)


def test_single_algorithm_preserves_solver_failure_with_feasible_certificate(monkeypatch):
    payload = _payload()
    calls = 0

    def certify(request, result):
        nonlocal calls
        calls += 1
        return payload

    _install_strategy(monkeypatch, "stub", _StubStrategy(_response(success=False)))
    monkeypatch.setattr(optimization, "certify_optimization_response", certify)

    result = _run_installed_algorithm("stub", _request())

    assert calls == 1
    assert result.success is False
    assert result.feasibility_certificate.model_dump(exclude_none=True) == payload
    assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)


def test_single_algorithm_attaches_the_single_feasible_typed_certificate(monkeypatch):
    payload = _payload()
    calls = 0

    def certify(request, result):
        nonlocal calls
        calls += 1
        return payload

    _install_strategy(monkeypatch, "stub", _StubStrategy(_response()))
    monkeypatch.setattr(optimization, "certify_optimization_response", certify)

    result = _run_installed_algorithm("stub", _request())

    assert calls == 1
    assert result.success is True
    assert result.feasibility_certificate.model_dump(exclude_none=True) == payload


def test_optimize_no_result_attaches_sanitized_unavailable_certificate(monkeypatch):
    calls = 0

    def certify(request, result):
        nonlocal calls
        calls += 1
        return _payload()

    _install_strategy(monkeypatch, "stub", _StubStrategy())
    monkeypatch.setattr(optimization, "certify_optimization_response", certify)

    result = optimization.optimize_route(_request())

    assert calls == 0
    assert result.success is False
    assert result.feasibility_certificate.certify_error == optimization._UNAVAILABLE_CERTIFICATE_ERROR
    assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)


def test_compare_timeout_attaches_sanitized_unavailable_certificate(monkeypatch):
    class _TimeoutFuture:
        def cancel(self):
            return True

    class _TimeoutExecutor:
        def __init__(self, max_workers):
            self.max_workers = max_workers

        def submit(self, function, *args):
            return _TimeoutFuture()

        def shutdown(self, *, wait, cancel_futures):
            assert wait is False
            assert cancel_futures is True

    calls = 0

    def certify(request, result):
        nonlocal calls
        calls += 1
        return _payload()

    _install_strategy(monkeypatch, "timeout", _StubStrategy(_response()))
    monkeypatch.setattr(optimization, "ThreadPoolExecutor", _TimeoutExecutor)
    monkeypatch.setattr(optimization, "certify_optimization_response", certify)

    monkeypatch.setattr(
        optimization, "wait",
        lambda pending, **kwargs: (set(), set(pending)),
    )


    response = optimization.compare_algorithms(
        schemas.CompareRequest(
            students=[],
            depot=schemas.LocationNode(id="depot", lat=0.0, lng=0.0),
            algorithms=["timeout"],
        )
    )
    result = response.results[0]

    assert calls == 0
    assert result.success is False
    assert result.feasibility_certificate.certify_error == optimization._UNAVAILABLE_CERTIFICATE_ERROR
    assert json.loads(result.error_message) == result.feasibility_certificate.model_dump(exclude_none=True)
