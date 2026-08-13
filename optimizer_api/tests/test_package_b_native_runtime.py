"""Task 4: native solver runtime is request-local and forwarded truthfully."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest

from optimizer_api.compute_policy import HARD_CEILINGS, apply_compute_policy, load_compute_policy
from optimizer_api.models.schemas import OptimizationRequest, PolicyValueSource
from optimizer_api.strategies.canonical import resolve_strategy
from optimizer_api.strategies.ortools_cvrp import ORToolsCVRPStrategy
from optimizer_api.strategies.pyvrp_strategy import PyVRPAlternativeStrategy, PyVRPStrategy
from optimizer_api.strategies.sota_config_utils import merge_sota_config
from uniride_core.algorithms.sota_tsp import (
    E2BSO_TSP,
    E2BSOTSPConfig,
    PAOEA_TSP,
    PAOEAConfig,
    R2DMA_TSP,
    R2DMATSPConfig,
)
from uniride_core.algorithms.sota_tsp.e2bso_tsp import (
    E2BSO_TSP_CPSO,
    E2BSOCPSPConfig,
)
from uniride_core.algorithms.sota_tsp import e2bso_tsp, paoea_tsp, r2dma_tsp


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


@pytest.mark.parametrize("seconds", [30, 10])
def test_ortools_forwards_exact_request_local_runtime(monkeypatch, seconds):
    calls = []
    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.build_sota_request_context",
        lambda students, depot: _context(),
    )
    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.solve_ortools_cvrp",
        lambda **kwargs: calls.append(kwargs) or SimpleNamespace(success=False, error_message="stop"),
    )

    ORToolsCVRPStrategy(time_limit_seconds=seconds).optimize(_request("ortools_cvrp"))

    assert calls[0]["time_limit_seconds"] == float(seconds)


@pytest.mark.parametrize(
    ("strategy_cls", "algorithm"),
    [(PyVRPStrategy, "pyvrp"), (PyVRPAlternativeStrategy, "pyvrp_alt")],
)
@pytest.mark.parametrize("seconds", [30, 10])
def test_pyvrp_forwards_exact_request_local_runtime(
    monkeypatch, strategy_cls, algorithm, seconds
):
    calls = []
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.build_sota_request_context",
        lambda students, depot: _context(),
    )
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.solve_pyvrp_cvrp",
        lambda **kwargs: calls.append(kwargs) or SimpleNamespace(success=False, error_message="stop"),
    )

    strategy_cls(time_limit_seconds=seconds).optimize(_request(algorithm))

    assert calls[0]["time_limit_seconds"] == float(seconds)


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


@pytest.mark.parametrize(
    ("strategy_cls", "algorithm"),
    [(PyVRPStrategy, "pyvrp"), (PyVRPAlternativeStrategy, "pyvrp_alt")],
)
def test_two_fresh_pyvrp_instances_keep_independent_runtime_during_calls(
    monkeypatch, strategy_cls, algorithm
):
    calls = []
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.build_sota_request_context",
        lambda students, depot: _context(),
    )
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.solve_pyvrp_cvrp",
        lambda **kwargs: calls.append(kwargs["time_limit_seconds"])
        or SimpleNamespace(success=False, error_message="stop"),
    )
    first = strategy_cls(time_limit_seconds=5)
    second = strategy_cls(time_limit_seconds=15)

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda item: item.optimize(_request(algorithm)), (first, second)))

    assert sorted(calls) == [5.0, 15.0]
    assert first.time_limit_seconds == 5.0
    assert second.time_limit_seconds == 15.0


def test_engines_without_native_clock_do_not_claim_solver_seconds():
    resolution = resolve_strategy("ga")
    _, metadata = apply_compute_policy(
        _request("ga"), resolution, resolution.create(), HARD_CEILINGS
    )
    assert "solver_seconds" not in metadata.limits


SOTA_FINAL_LS_VARIANTS = (
    ("e2bso", e2bso_tsp, E2BSO_TSP, E2BSOTSPConfig),
    ("e2bso_cpso", e2bso_tsp, E2BSO_TSP_CPSO, E2BSOCPSPConfig),
    ("r2dma", r2dma_tsp, R2DMA_TSP, R2DMATSPConfig),
    ("paoea", paoea_tsp, PAOEA_TSP, PAOEAConfig),
)


class _Clock:
    def __init__(self, values):
        self.values = list(values)
        self.index = 0

    def __call__(self):
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


def _small_sota_config(config_type, **overrides):
    common = {"population_size": 4, "max_iterations": 1}
    if config_type is PAOEAConfig:
        common["genome_population_size"] = 2
    common.update(overrides)
    return replace(config_type(), **common)


def _run_sota_and_capture_final_ls(
    monkeypatch, module, solver_type, config, clock_values
):
    calls = []

    def fake_improve(tour, dm, dm_np, intensity, max_iterations, time_limit, window):
        calls.append((intensity, max_iterations, time_limit))
        cost = sum(dm[tour[i]][tour[(i + 1) % len(tour)]] for i in range(len(tour)))
        return list(tour), cost, {}

    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=_Clock(clock_values)))
    monkeypatch.setattr(module, "MultiLayerLS", SimpleNamespace(improve=fake_improve))
    matrix = [
        [0.0 if i == j else float(abs(i - j) + 1) for j in range(6)]
        for i in range(6)
    ]
    solver_type(config).solve_with_matrix(matrix)
    return [limit for intensity, iterations, limit in calls if intensity == "full" and iterations == 500]


@pytest.mark.parametrize(
    ("name", "module", "solver_type", "config_type"),
    SOTA_FINAL_LS_VARIANTS,
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_every_sota_final_local_search_uses_configured_default_budget(
    monkeypatch, name, module, solver_type, config_type
):
    config = _small_sota_config(config_type, time_limit=10.0)

    calls = _run_sota_and_capture_final_ls(
        monkeypatch, module, solver_type, config, [0.0]
    )

    assert calls == [config.ls_time_limit]


@pytest.mark.parametrize(
    ("name", "module", "solver_type", "config_type"),
    SOTA_FINAL_LS_VARIANTS,
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_sota_final_local_search_never_exceeds_remaining_overall_budget(
    monkeypatch, name, module, solver_type, config_type
):
    config = _small_sota_config(
        config_type, ls_time_limit=0.8, time_limit=1.0
    )

    calls = _run_sota_and_capture_final_ls(
        monkeypatch, module, solver_type, config, [0.0, 0.75]
    )

    assert calls == [pytest.approx(0.25)]


@pytest.mark.parametrize(
    ("name", "module", "solver_type", "config_type"),
    SOTA_FINAL_LS_VARIANTS,
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_sota_skips_final_local_search_when_overall_budget_is_exhausted(
    monkeypatch, name, module, solver_type, config_type
):
    config = _small_sota_config(
        config_type, ls_time_limit=0.8, time_limit=1.0
    )

    calls = _run_sota_and_capture_final_ls(
        monkeypatch, module, solver_type, config, [0.0, 1.1]
    )

    assert calls == []


@pytest.mark.parametrize(
    ("canonical", "module", "solver_type"),
    [
        ("e2bso", e2bso_tsp, E2BSO_TSP),
        ("r2dma", r2dma_tsp, R2DMA_TSP),
        ("paoea", paoea_tsp, PAOEA_TSP),
    ],
)
def test_sota_policy_metadata_matches_final_local_search_enforcement(
    monkeypatch, canonical, module, solver_type
):
    caller = {
        "population_size": 4,
        "max_iterations": 1,
        "ls_time_limit": 0.25,
        "time_limit": 1.0,
    }
    if canonical == "r2dma":
        caller["tournament_k"] = 2
    if canonical == "paoea":
        caller["genome_population_size"] = 2
    request = _request(canonical).model_copy(update={"sota_config": caller})
    resolution = resolve_strategy(canonical)
    strategy = resolution.create()
    registered = strategy._config
    effective, metadata = apply_compute_policy(
        request, resolution, strategy, HARD_CEILINGS
    )
    config = merge_sota_config(registered, effective.sota_config)

    calls = _run_sota_and_capture_final_ls(
        monkeypatch, module, solver_type, config, [0.0]
    )

    assert calls == [metadata.limits["ls_time_limit"].value]
    assert metadata.limits["ls_time_limit"].source is PolicyValueSource.CALLER
    assert strategy._config is registered
    assert strategy._config.ls_time_limit == 0.5
