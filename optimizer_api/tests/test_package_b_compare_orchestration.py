"""Package B Task 5 RED tests for bounded comparison orchestration."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import replace
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from compute_policy import ComputePolicy, DEFAULT_COMPARE_ALGORITHMS, PolicyValidationError
from models import schemas
from routers import optimization
from strategies.canonical import (
    ResolvedStrategy,
    StrategyRegistryContractError,
    StrategyUnavailableError,
    UnknownStrategyError,
)


DEPOT = schemas.LocationNode(id="depot", lat=0.0, lng=0.0)
CERTIFIED = schemas.FeasibilityCertificateInfo(
    is_feasible=True, violation_count=0, violations=[]
)
UNCERTIFIED = None
INFEASIBLE = schemas.FeasibilityCertificateInfo(
    is_feasible=False,
    violation_count=1,
    violations=[
        schemas.FeasibilityViolationInfo(
            type="capacity", severity="error", details="over capacity"
        )
    ],
)


def _request(algorithms=None):
    return schemas.CompareRequest(students=[], depot=DEPOT, algorithms=algorithms)


def _resolution(requested, canonical=None, aliases=None, factory=None):
    canonical_name = canonical or requested
    if factory is None:
        factory = lambda: SimpleNamespace(name=canonical_name, time_limit_seconds=30.0)
    return ResolvedStrategy(
        requested=requested,
        canonical=canonical_name,
        factory=factory,
        requested_aliases=tuple(aliases or (requested,)),
    )


def _metadata(requested, canonical, mode="none"):
    return schemas.AppliedComputePolicyInfo(
        profile_id="production-conservative-v1",
        algorithm_requested=requested,
        algorithm_canonical=canonical,
        student_count=0,
        vehicle_count=0,
        cancellation_mode=mode,
        limits={},
    )


def _result(
    algorithm,
    *,
    success=True,
    duration=10.0,
    vehicles=1,
    seconds=1.0,
    certificate=CERTIFIED,
    requested=None,
    mode="none",
):
    return schemas.AlgorithmResult(
        algorithm=algorithm,
        algorithm_requested=requested or algorithm,
        success=success,
        total_vehicles=vehicles,
        total_duration_minutes=duration,
        execution_time_seconds=seconds,
        routes=[],
        feasibility_certificate=certificate,
        applied_policy=_metadata(requested or algorithm, algorithm, mode),
    )


def _install_policy(monkeypatch, **changes):
    policy = replace(ComputePolicy(), **changes)
    monkeypatch.setattr(optimization, "load_compute_policy", lambda: policy)
    return policy


def _install_resolutions(monkeypatch, resolutions):
    observed = []

    def resolve(keys):
        observed.append(tuple(keys))
        return list(resolutions)

    monkeypatch.setattr(optimization, "resolve_unique_strategies", resolve)
    return observed


def test_compare_default_is_exact_ordered_six_and_preserves_canonical_order(monkeypatch):
    resolutions = [_resolution(name) for name in DEFAULT_COMPARE_ALGORITHMS]
    observed = _install_resolutions(monkeypatch, resolutions)
    _install_policy(monkeypatch)
    executions = []

    def run(prepared):
        resolution = prepared.resolution
        executions.append(resolution.canonical)
        return _result(resolution.canonical)

    monkeypatch.setattr(optimization, "_run_single_algorithm", run)

    response = optimization.compare_algorithms(_request())

    assert observed == [DEFAULT_COMPARE_ALGORITHMS]
    assert sorted(executions) == sorted(DEFAULT_COMPARE_ALGORITHMS)
    assert [item.algorithm for item in response.results] == list(DEFAULT_COMPARE_ALGORITHMS)
    assert list(response.summary) == list(DEFAULT_COMPARE_ALGORITHMS)


def test_compare_deduplicates_aliases_once_and_retains_requested_aliases(monkeypatch):
    resolutions = [
        _resolution("ga", "genetic_algorithm", ("ga", "genetic_algorithm")),
        _resolution("nearest_neighbor", "greedy", ("nearest_neighbor", "greedy")),
    ]
    observed = _install_resolutions(monkeypatch, resolutions)
    _install_policy(monkeypatch)
    executions = []

    def run(prepared):
        resolution = prepared.resolution
        executions.append((resolution.canonical, resolution.requested_aliases))
        return _result(
            resolution.canonical,
            requested=resolution.requested,
            duration=1 if resolution.canonical == "genetic_algorithm" else 2,
        )

    monkeypatch.setattr(optimization, "_run_single_algorithm", run)

    response = optimization.compare_algorithms(
        _request(["ga", "genetic_algorithm", "nearest_neighbor", "greedy"])
    )

    assert observed == [(
        "ga", "genetic_algorithm", "nearest_neighbor", "greedy"
    )]
    assert executions == [
        ("genetic_algorithm", ("ga", "genetic_algorithm")),
        ("greedy", ("nearest_neighbor", "greedy")),
    ]
    assert [result.algorithm for result in response.results] == [
        "genetic_algorithm", "greedy"
    ]
    assert [result.algorithm_requested for result in response.results] == [
        "ga", "nearest_neighbor"
    ]


def test_compare_rejects_explicit_empty_list_before_resolution_or_executor(monkeypatch):
    monkeypatch.setattr(
        optimization,
        "resolve_unique_strategies",
        lambda keys: pytest.fail("empty explicit list must be rejected first"),
    )
    monkeypatch.setattr(
        optimization,
        "ThreadPoolExecutor",
        lambda **kwargs: pytest.fail("executor must not be created"),
    )

    with pytest.raises(HTTPException) as exc_info:
        optimization.compare_algorithms(_request([]))

    assert exc_info.value.status_code == 400


@pytest.mark.parametrize(
    "error",
    [
        optimization.UnknownStrategyError("Unknown algorithm 'missing'"),
        optimization.StrategyUnavailableError("Algorithm 'pyvrp' is unavailable"),
    ],
)
def test_compare_resolves_every_algorithm_before_submitting_any_work(monkeypatch, error):
    _install_policy(monkeypatch)
    monkeypatch.setattr(
        optimization,
        "resolve_unique_strategies",
        lambda keys: (_ for _ in ()).throw(error),
    )
    monkeypatch.setattr(
        optimization,
        "ThreadPoolExecutor",
        lambda **kwargs: pytest.fail("executor must not be created"),
    )

    with pytest.raises(HTTPException) as exc_info:
        optimization.compare_algorithms(_request(["greedy", "missing"]))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == str(error)


def test_compare_rejects_canonical_count_above_effective_limit_before_executor(monkeypatch):
    _install_policy(monkeypatch, max_algorithms=1)
    _install_resolutions(monkeypatch, [_resolution("greedy"), _resolution("two_opt")])
    monkeypatch.setattr(
        optimization,
        "ThreadPoolExecutor",
        lambda **kwargs: pytest.fail("executor must not be created"),
    )

    with pytest.raises(HTTPException) as exc_info:
        optimization.compare_algorithms(_request(["greedy", "two_opt"]))

    assert exc_info.value.status_code == 422
    assert "1" in str(exc_info.value.detail)


def test_compare_uses_two_workers_one_bounded_wait_and_nonblocking_shutdown(monkeypatch):
    resolutions = [_resolution("greedy"), _resolution("two_opt"), _resolution("ga", "genetic_algorithm")]
    _install_resolutions(monkeypatch, resolutions)
    policy = _install_policy(monkeypatch, max_workers=2, deadline_seconds=37)
    observed = {"wait": [], "shutdown": []}

    class Executor:
        def __init__(self, max_workers):
            observed["max_workers"] = max_workers

        def submit(self, function, *args):
            future = Future()
            future.set_result(function(*args))
            return future

        def shutdown(self, **kwargs):
            observed["shutdown"].append(kwargs)

    def one_wait(futures, *, timeout, return_when):
        observed["wait"].append((set(futures), timeout, return_when))
        return set(futures), set()

    monkeypatch.setattr(optimization, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(optimization, "wait", one_wait)
    monkeypatch.setattr(
        optimization,
        "_run_single_algorithm",
        lambda prepared: _result(prepared.resolution.canonical),
    )

    optimization.compare_algorithms(_request(["greedy", "two_opt", "ga"]))

    assert observed["max_workers"] == 2
    assert len(observed["wait"]) == 1
    assert observed["wait"][0][1] == policy.deadline_seconds
    assert observed["wait"][0][2] is optimization.ALL_COMPLETED
    assert observed["shutdown"] == [{"wait": False, "cancel_futures": True}]


def test_compare_deadline_returns_typed_soft_failures_in_requested_order(monkeypatch):
    resolutions = [_resolution("slow"), _resolution("fast")]
    _install_resolutions(monkeypatch, resolutions)
    _install_policy(monkeypatch, deadline_seconds=1)
    futures = []

    class Executor:
        def __init__(self, max_workers):
            pass

        def submit(self, function, prepared):
            resolution = prepared.resolution
            future = Future()
            if resolution.canonical == "fast":
                future.set_result(_result("fast", duration=2))
            futures.append(future)
            return future

        def shutdown(self, **kwargs):
            assert kwargs == {"wait": False, "cancel_futures": True}

    monkeypatch.setattr(optimization, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(
        optimization,
        "wait",
        lambda pending, **kwargs: ({futures[1]}, {futures[0]}),
    )

    response = optimization.compare_algorithms(_request(["slow", "fast"]))

    assert [result.algorithm for result in response.results] == ["slow", "fast"]
    timeout = response.results[0]
    assert timeout.success is False
    assert timeout.applied_policy.cancellation_mode == "soft_response_deadline"
    assert timeout.feasibility_certificate.is_feasible is False
    assert timeout.feasibility_certificate.certify_error
    assert response.best_algorithm == "fast"
    assert response.applied_policy.cancellation_mode == "soft_response_deadline"


def test_compare_ranks_only_certified_feasible_successes_with_deterministic_ties(monkeypatch):
    names = ["zeta", "alpha", "failed", "infeasible", "uncertified"]
    _install_resolutions(monkeypatch, [_resolution(name) for name in names])
    _install_policy(monkeypatch)
    results = {
        "zeta": _result("zeta", duration=10, vehicles=2, seconds=1),
        "alpha": _result("alpha", duration=10, vehicles=1, seconds=1),
        "failed": _result("failed", success=False, duration=0, seconds=0),
        "infeasible": _result("infeasible", duration=0, seconds=0, certificate=INFEASIBLE),
        "uncertified": _result("uncertified", duration=0, seconds=0, certificate=UNCERTIFIED),
    }
    monkeypatch.setattr(
        optimization,
        "_run_single_algorithm",
        lambda prepared: results[prepared.resolution.canonical],
    )

    response = optimization.compare_algorithms(_request(names))

    assert response.success is True
    assert response.best_algorithm == "alpha"
    assert response.fastest_algorithm == "alpha"


def test_compare_with_no_eligible_result_has_empty_rankings(monkeypatch):
    _install_resolutions(monkeypatch, [_resolution("failed"), _resolution("uncertified")])
    _install_policy(monkeypatch)
    monkeypatch.setattr(
        optimization,
        "_run_single_algorithm",
        lambda prepared: _result(
            prepared.resolution.canonical,
            success=False if prepared.resolution.canonical == "failed" else True,
            certificate=CERTIFIED if prepared.resolution.canonical == "failed" else None,
        ),
    )

    response = optimization.compare_algorithms(_request(["failed", "uncertified"]))

    assert response.success is False
    assert response.best_algorithm == ""
    assert response.fastest_algorithm == ""


def test_single_algorithm_execution_isolates_shared_request_and_strategy_instances(monkeypatch):
    barrier = Barrier(2)
    seen_request_ids = []

    class MutatingStrategy:
        name = "genetic_algorithm"
        config = {"max_iterations": 50}

        def optimize(self, request):
            seen_request_ids.append(id(request))
            request.ga_config["max_iterations"] = 1
            barrier.wait(timeout=5)
            return schemas.OptimizationResponse(
                algorithm_used=self.name, success=True, routes=[]
            )

    request = schemas.OptimizationRequest(
        algorithm="ga", students=[], depot=DEPOT, ga_config={"max_iterations": 7}
    )
    before = request.model_dump()
    first = _resolution("ga", "genetic_algorithm", factory=MutatingStrategy)
    second = _resolution("ga", "genetic_algorithm", factory=MutatingStrategy)
    policy = ComputePolicy()
    monkeypatch.setattr(
        optimization, "certify_optimization_response", lambda request, result: {
            "is_feasible": True, "violation_count": 0, "violations": []
        }
    )

    prepared = [
        optimization._prepare_comparison_run(resolution, request, policy)
        for resolution in (first, second)
    ]
    with optimization.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            optimization._run_single_algorithm,
            prepared,
        ))

    assert all(result.success for result in results)
    assert len(set(seen_request_ids)) == 2
    assert request.model_dump() == before


def test_compare_normalizes_package_dto_payloads_across_import_modes(monkeypatch):
    package_schemas = pytest.importorskip("optimizer_api.models.schemas")
    package_request = package_schemas.CompareRequest(
        students=[],
        depot=package_schemas.LocationNode(id="package-depot", lat=0.0, lng=0.0),
        algorithms=["greedy"],
    )
    _install_resolutions(monkeypatch, [_resolution("greedy")])
    _install_policy(monkeypatch)

    def run(prepared):
        assert isinstance(prepared.request, schemas.OptimizationRequest)
        assert isinstance(prepared.request.depot, schemas.LocationNode)
        assert prepared.request.depot.id == "package-depot"
        return _result("greedy")

    monkeypatch.setattr(optimization, "_run_single_algorithm", run)

    response = optimization.compare_algorithms(package_request)

    assert response.results[0].algorithm == "greedy"


@pytest.mark.parametrize("future_mode", ["timeout", "exception"])
def test_compare_prepares_truthful_policy_before_submit_for_non_success_outcomes(
    monkeypatch, future_mode
):
    created = []

    class Strategy:
        name = "genetic_algorithm"
        config = {"max_iterations": 50, "population_size": 100}

        def optimize(self, request):
            raise AssertionError("fake executor must not run the worker")

    def factory():
        strategy = Strategy()
        created.append(strategy)
        return strategy

    resolution = _resolution(
        "ga", "genetic_algorithm", ("ga", "genetic_algorithm"), factory=factory
    )
    _install_resolutions(monkeypatch, [resolution])
    policy = _install_policy(monkeypatch)
    request = schemas.CompareRequest(
        students=[], depot=DEPOT, algorithms=["ga"]
    )
    original_dump = request.model_dump()
    prepared_at_submit = []
    submitted = []

    def apply(request_copy, actual_resolution, strategy, actual_policy):
        assert actual_resolution is resolution
        assert actual_policy is policy
        assert request_copy is not request
        metadata = _metadata("ga", "genetic_algorithm")
        metadata.limits = {
            "max_iterations": schemas.AppliedPolicyLimitInfo(
                value=7, source="caller", enforcement="request-local ga_config.max_iterations"
            ),
            "population_size": schemas.AppliedPolicyLimitInfo(
                value=100,
                source="strategy_default",
                enforcement="request-local ga_config.population_size",
            ),
        }
        request_copy.ga_config = {"max_iterations": 7, "population_size": 100}
        prepared_at_submit.append((strategy, request_copy, metadata))
        return request_copy, metadata

    class Executor:
        def __init__(self, max_workers):
            assert max_workers == 1

        def submit(self, function, prepared):
            assert prepared_at_submit, "policy must be applied before submission"
            submitted.append(prepared)
            future = Future()
            if future_mode == "exception":
                future.set_exception(RuntimeError("future failed"))
            return future

        def shutdown(self, **kwargs):
            assert kwargs == {"wait": False, "cancel_futures": True}

    monkeypatch.setattr(optimization, "apply_compute_policy", apply)
    monkeypatch.setattr(optimization, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(
        optimization,
        "wait",
        lambda pending, **kwargs: (
            (set(pending), set())
            if future_mode == "exception"
            else (set(), set(pending))
        ),
    )

    response = optimization.compare_algorithms(request)

    assert len(created) == 1
    assert len(prepared_at_submit) == 1
    assert len(submitted) == 1
    assert request.model_dump() == original_dump
    result = response.results[0]
    assert result.success is False
    assert result.algorithm == "genetic_algorithm"
    assert result.algorithm_requested == "ga"
    assert result.applied_policy.algorithm_requested == "ga"
    assert result.applied_policy.algorithm_canonical == "genetic_algorithm"
    assert result.applied_policy.limits["max_iterations"].value == 7
    assert result.applied_policy.limits["max_iterations"].source == "caller"
    assert result.applied_policy.limits["population_size"].value == 100
    if future_mode == "timeout":
        assert result.applied_policy.cancellation_mode == "soft_response_deadline"
    else:
        assert result.applied_policy.cancellation_mode == "none"


def test_router_exposes_no_mutation_bridge_to_canonical_registries():
    assert not hasattr(optimization, "STRATEGY_REGISTRY")
    assert not hasattr(optimization, "_STRATEGY_REGISTRY")
    assert not hasattr(optimization, "_STRATEGY_FACTORIES")


def test_canonical_alias_dedup_remains_one_without_router_registry_stubs():
    from strategies.canonical import resolve_unique_strategies

    resolutions = resolve_unique_strategies(["ga", "genetic_algorithm"])

    assert len(resolutions) == 1
    assert resolutions[0].canonical == "genetic_algorithm"
    assert resolutions[0].requested_aliases == ("ga", "genetic_algorithm")


@pytest.mark.parametrize(
    "error_type",
    [
        optimization.UnknownStrategyError,
        optimization.StrategyUnavailableError,
        optimization.StrategyRegistryContractError,
    ],
)
def test_compare_maps_only_named_resolution_errors_to_400(monkeypatch, error_type):
    error = error_type("named resolver failure")
    monkeypatch.setattr(
        optimization,
        "resolve_unique_strategies",
        lambda keys: (_ for _ in ()).throw(error),
    )

    with pytest.raises(HTTPException) as exc_info:
        optimization.compare_algorithms(_request(["ga"]))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "named resolver failure"


def test_compare_does_not_convert_unexpected_resolution_value_error_to_400(monkeypatch):
    monkeypatch.setattr(
        optimization,
        "resolve_unique_strategies",
        lambda keys: (_ for _ in ()).throw(ValueError("resolver bug")),
    )

    with pytest.raises(ValueError, match="resolver bug"):
        optimization.compare_algorithms(_request(["ga"]))


def test_compare_policy_failure_happens_before_executor(monkeypatch):
    resolution = _resolution("ga", "genetic_algorithm")
    _install_resolutions(monkeypatch, [resolution])
    _install_policy(monkeypatch)
    monkeypatch.setattr(
        optimization,
        "apply_compute_policy",
        lambda *args: (_ for _ in ()).throw(
            optimization.PolicyValidationError("ga_config not applicable")
        ),
    )
    monkeypatch.setattr(
        optimization,
        "ThreadPoolExecutor",
        lambda **kwargs: pytest.fail("executor must not be created"),
    )

    with pytest.raises(HTTPException) as exc_info:
        optimization.compare_algorithms(_request(["ga"]))

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "ga_config not applicable"


# ---------------------------------------------------------------------------
# Task 6: oversized exact/permutation runs fail without touching the solver
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


def test_compare_oversize_exact_run_fails_while_eligible_runs_continue(monkeypatch):
    exact_calls = []

    class ExactStrategy:
        name = "permutation_tsp"
        config = {}

        def optimize(self, request):
            exact_calls.append(request)
            raise AssertionError("exact solver must never run for an oversized request")

    class GreedyStrategy:
        name = "greedy"
        config = {}

        def optimize(self, request):
            return schemas.OptimizationResponse(
                algorithm_used="greedy", success=True, routes=[]
            )

    exact_resolution = _resolution(
        "exact", "permutation_tsp", ("exact", "permutation_tsp"),
        factory=lambda: ExactStrategy(),
    )
    greedy_resolution = _resolution(
        "greedy", "greedy", ("greedy",), factory=lambda: GreedyStrategy()
    )
    monkeypatch.setattr(
        optimization,
        "resolve_unique_strategies",
        lambda keys: [exact_resolution, greedy_resolution],
    )
    monkeypatch.setattr(
        optimization,
        "certify_optimization_response",
        lambda request, result: {
            "is_feasible": True, "violation_count": 0, "violations": []
        },
    )
    _install_policy(monkeypatch)
    request = schemas.CompareRequest(
        students=_many_students(), depot=DEPOT, algorithms=["exact", "greedy"]
    )

    response = optimization.compare_algorithms(request)

    assert exact_calls == []
    assert [student.id for student in request.students] == [
        f"S{i}" for i in range(11)
    ]
    assert [result.algorithm for result in response.results] == [
        "permutation_tsp", "greedy"
    ]

    exact_result = response.results[0]
    assert exact_result.success is False
    assert exact_result.algorithm_requested == "exact"
    assert exact_result.applied_policy.algorithm_canonical == "permutation_tsp"
    assert exact_result.applied_policy.algorithm_requested == "exact"
    assert exact_result.applied_policy.student_count == 11
    assert (
        exact_result.feasibility_certificate.certify_error
        == optimization._UNAVAILABLE_CERTIFICATE_ERROR
    )
    error_text = exact_result.error_message or ""
    assert "S0" not in error_text
    assert "L0" not in error_text
    assert "Traceback" not in error_text

    greedy_result = response.results[1]
    assert greedy_result.success is True
    assert greedy_result.algorithm == "greedy"

    assert response.success is True
    assert response.best_algorithm == "greedy"
    assert response.fastest_algorithm == "greedy"
    assert "permutation_tsp" not in {
        response.best_algorithm, response.fastest_algorithm
    }


def test_compare_preflights_oversize_exact_queued_behind_saturated_workers(
    monkeypatch,
):
    resolutions = [
        _resolution("greedy"),
        _resolution("two_opt"),
        _resolution("exact", "permutation_tsp", ("exact", "permutation_tsp")),
    ]
    _install_resolutions(monkeypatch, resolutions)
    _install_policy(monkeypatch, max_workers=2, deadline_seconds=1)
    submitted = []

    class Executor:
        def __init__(self, max_workers):
            assert max_workers == 2

        def submit(self, function, prepared):
            submitted.append(prepared.resolution.canonical)
            future = Future()
            if len(submitted) <= 2:
                future.set_running_or_notify_cancel()
            return future

        def shutdown(self, **kwargs):
            assert kwargs == {"wait": False, "cancel_futures": True}

    monkeypatch.setattr(optimization, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(
        optimization,
        "wait",
        lambda pending, **kwargs: (set(), set(pending)),
    )

    response = optimization.compare_algorithms(
        schemas.CompareRequest(
            students=_many_students(),
            depot=DEPOT,
            algorithms=["greedy", "two_opt", "exact"],
        )
    )

    exact_result = response.results[2]
    assert exact_result.applied_policy.cancellation_mode == "none"
    assert submitted == ["greedy", "two_opt"]
    assert [result.algorithm for result in response.results] == [
        "greedy", "two_opt", "permutation_tsp"
    ]
    assert exact_result.success is False
    assert exact_result.applied_policy.student_count == 11
    assert response.best_algorithm == ""
    assert response.fastest_algorithm == ""


def test_compare_oversize_exact_only_does_not_create_executor(monkeypatch):
    exact_calls = []

    class ExactStrategy:
        name = "permutation_tsp"
        config = {}

        def optimize(self, request):
            exact_calls.append(request)
            raise AssertionError("oversized exact solver must not run")

    resolution = _resolution(
        "exact",
        "permutation_tsp",
        ("exact", "permutation_tsp"),
        factory=ExactStrategy,
    )
    _install_resolutions(monkeypatch, [resolution])
    _install_policy(monkeypatch, max_workers=2)
    monkeypatch.setattr(
        optimization,
        "ThreadPoolExecutor",
        lambda **kwargs: pytest.fail("executor must not be created"),
    )
    monkeypatch.setattr(
        optimization,
        "wait",
        lambda *args, **kwargs: pytest.fail("wait must not be called"),
    )

    response = optimization.compare_algorithms(
        schemas.CompareRequest(
            students=_many_students(), depot=DEPOT, algorithms=["exact"]
        )
    )

    assert exact_calls == []
    assert len(response.results) == 1
    result = response.results[0]
    assert result.algorithm == "permutation_tsp"
    assert result.success is False
    assert result.applied_policy.algorithm_requested == "exact"
    assert result.applied_policy.student_count == 11
    assert result.applied_policy.cancellation_mode == "none"
    assert response.success is False
    assert response.best_algorithm == ""
    assert response.fastest_algorithm == ""
