"""Task 4: native solver runtime is request-local and forwarded truthfully."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from optimizer_api.compute_policy import HARD_CEILINGS, apply_compute_policy, load_compute_policy
from optimizer_api.models.schemas import OptimizationRequest, PolicyValueSource
from optimizer_api.strategies.canonical import resolve_strategy
from optimizer_api.strategies.ortools_cvrp import ORToolsCVRPStrategy
from optimizer_api.strategies.pyvrp_strategy import PyVRPAlternativeStrategy, PyVRPStrategy


def _request(algorithm: str) -> OptimizationRequest:
    return OptimizationRequest(
        algorithm=algorithm,
        depot={"id": "D", "lat": 0.0, "lng": 0.0},
        students=[{
            "id": "S1",
            "location_code": "S1",
            "coordinates": {"lat": 1.0, "lng": 0.0},
            "disability_type": "Sw",
        }],
    )


def _context():
    return {
        "student_ids": ["S1"],
        "time_matrix": {"D": {"D": 0, "S1": 1}, "S1": {"D": 1, "S1": 0}},
        "coordinates": {"D": {"lat": 0.0, "lng": 0.0}, "S1": {"lat": 1.0, "lng": 0.0}},
        "distance_lookup": lambda origin, destination: 0.0 if origin == destination else 1.0,
    }


@pytest.mark.parametrize(
    "strategy_cls",
    [ORToolsCVRPStrategy, PyVRPStrategy, PyVRPAlternativeStrategy],
)
def test_native_strategy_default_is_existing_thirty_seconds(strategy_cls):
    strategy = strategy_cls()
    assert strategy.time_limit_seconds == 30.0


@pytest.mark.parametrize(
    "strategy_cls",
    [ORToolsCVRPStrategy, PyVRPStrategy, PyVRPAlternativeStrategy],
)
@pytest.mark.parametrize("value", [0, -1])
def test_native_strategy_rejects_non_positive_runtime(strategy_cls, value):
    with pytest.raises(ValueError, match="positive"):
        strategy_cls(time_limit_seconds=value)


@pytest.mark.parametrize("canonical", ["ortools_cvrp", "pyvrp", "pyvrp_alt"])
def test_lower_server_policy_updates_only_fresh_native_instance(canonical):
    resolution = resolve_strategy(canonical)
    strategy = resolution.create()
    compatibility = resolve_strategy(canonical).create()
    request = _request(canonical)
    policy = load_compute_policy({"UNIRIDE_COMPUTE_SOLVER_SECONDS": "10"})

    effective, metadata = apply_compute_policy(request, resolution, strategy, policy)

    assert effective is not request
    assert strategy.time_limit_seconds == 10.0
    assert compatibility.time_limit_seconds == 30.0
    assert metadata.limits["solver_seconds"].value == 10.0
    assert metadata.limits["solver_seconds"].source is PolicyValueSource.SERVER_OVERRIDE


def test_ortools_forwards_exact_request_local_runtime(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.build_sota_request_context",
        lambda students, depot: _context(),
    )
    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.solve_ortools_cvrp",
        lambda **kwargs: calls.append(kwargs) or SimpleNamespace(success=False, error_message="stop"),
    )

    ORToolsCVRPStrategy(time_limit_seconds=10).optimize(_request("ortools_cvrp"))

    assert calls[0]["time_limit_seconds"] == 10.0


@pytest.mark.parametrize(
    ("strategy_cls", "algorithm"),
    [(PyVRPStrategy, "pyvrp"), (PyVRPAlternativeStrategy, "pyvrp_alt")],
)
def test_pyvrp_forwards_exact_request_local_runtime(monkeypatch, strategy_cls, algorithm):
    calls = []
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.build_sota_request_context",
        lambda students, depot: _context(),
    )
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.solve_pyvrp_cvrp",
        lambda **kwargs: calls.append(kwargs) or SimpleNamespace(success=False, error_message="stop"),
    )

    strategy_cls(time_limit_seconds=10).optimize(_request(algorithm))

    assert calls[0]["time_limit_seconds"] == 10.0


def test_two_fresh_native_instances_keep_independent_runtime_during_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.build_sota_request_context",
        lambda students, depot: _context(),
    )
    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.solve_ortools_cvrp",
        lambda **kwargs: calls.append(kwargs["time_limit_seconds"])
        or SimpleNamespace(success=False, error_message="stop"),
    )
    first = ORToolsCVRPStrategy(time_limit_seconds=5)
    second = ORToolsCVRPStrategy(time_limit_seconds=15)

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda item: item.optimize(_request("ortools_cvrp")), (first, second)))

    assert sorted(calls) == [5.0, 15.0]
    assert first.time_limit_seconds == 5.0
    assert second.time_limit_seconds == 15.0


def test_engines_without_native_clock_do_not_claim_solver_seconds():
    resolution = resolve_strategy("ga")
    _, metadata = apply_compute_policy(
        _request("ga"), resolution, resolution.create(), HARD_CEILINGS
    )
    assert "solver_seconds" not in metadata.limits
