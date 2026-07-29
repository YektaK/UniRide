"""Task C1.9: Smart Benchmark and CLI governed entrypoint preflight."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from academic_benchmark import cli_engine, smart_benchmark
from academic_benchmark.core.algorithm_errors import CandidateAlgorithmError, ResultContractViolation
from academic_benchmark.engine_core import BenchmarkTask, GovernedExecutionRequest, RunResult
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol


@dataclass
class _Problem:
    name: str = "entrypoint-atsp"
    problem_type: str = "atsp"
    dimension: int = 3
    optimal: float | None = None
    dist_matrix: list[list[float]] | None = None
    coordinates: list[tuple[float, float]] | None = None
    category: str = "test"
    source: str = "task9-fixture"
    is_time_matrix: bool = False

    def __post_init__(self) -> None:
        if self.dist_matrix is None:
            self.dist_matrix = [[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]]
        if self.coordinates is None:
            self.coordinates = [(0.0, 0.0), (2.0, 0.0), (0.0, 3.0)]


def _request(**changes: object) -> GovernedExecutionRequest:
    values = {
        "requested_algorithm_id": "Core-TwoOpt-TSP",
        "canonical_algorithm_id": "Core-TwoOpt-TSP",
        "protocol": ExecutionProtocol.FIXED_BUDGET,
        "evaluation_budget": 10,
        "backend_policy": BackendPolicy.PYTHON_ONLY,
    }
    values.update(changes)
    return GovernedExecutionRequest(**values)


def _valid_result() -> RunResult:
    result = RunResult(
        problem="entrypoint-atsp", algorithm="Core-TwoOpt-TSP", run=0, seed=1000,
        dimension=3, optimal=None, tour_cost=9.0, objective_cost=9.0,
        gap_pct=None, elapsed_sec=0.01, evaluations=7, tour=[1, 2, 3],
    )
    result.algorithm_id = "Core-TwoOpt-TSP"
    result.objective_evaluations = 7
    result.evaluation_budget = 10
    result.budget_terminated = False
    result.termination_reason = "no_improving_move"
    result.execution_backend = "objective=python;polish=none"
    return result


def test_governed_request_and_task_are_picklable() -> None:
    request = _request()
    task = BenchmarkTask("p", "Core-TwoOpt-TSP", 1, 42, {}, request)

    restored = pickle.loads(pickle.dumps(task))

    assert restored.governed_request == request
    assert restored.governed_request.canonical_algorithm_id == "Core-TwoOpt-TSP"


def test_cli_governed_task_uses_gateway_without_legacy_direct_fallback(monkeypatch) -> None:
    def direct_fallback(*_args, **_kwargs):
        raise AssertionError("governed TSP reached direct run_single_test fallback")

    from uniride_core.algorithms import numba_metaheuristics

    monkeypatch.setattr(numba_metaheuristics, "run_single_test", direct_fallback)
    observed = {}

    def gateway(**kwargs):
        observed.update(kwargs)
        return _valid_result(), SimpleNamespace()

    monkeypatch.setattr(cli_engine, "execute_preflighted", gateway)
    task = (
        cli_engine._make_problem_dict(_Problem()), "Core-TwoOpt-TSP", "Core-TwoOpt-TSP",
        {}, 0, 1, _request(),
    )

    result = cli_engine._evaluate_param_combo(task)

    assert result["algorithm_id"] == "Core-TwoOpt-TSP"
    assert observed["requested_algorithm_id"] == "Core-TwoOpt-TSP"
    assert observed["evaluation_budget"] == 10


def test_cli_governed_candidate_rejects_before_registry_or_direct_fallback(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("candidate reached registry enumeration")

    monkeypatch.setattr(cli_engine, "_AlgoReg", ExplodingRegistry)
    monkeypatch.setattr(cli_engine, "_HAS_NUMBA_REGISTRY", True)
    task = (
        cli_engine._make_problem_dict(_Problem()), "Core-GWO-TSP-Pure", "Core-GWO-TSP-Pure",
        {}, 0, 1, _request(
            requested_algorithm_id="Core-GWO-TSP-Pure",
            canonical_algorithm_id="Core-GWO-TSP-Pure",
        ),
    )

    with pytest.raises(CandidateAlgorithmError):
        cli_engine._evaluate_param_combo(task)


@pytest.mark.parametrize(
    "argv",
    [
        ["--mode", "default", "--algos", "Core-TwoOpt-TSP"],
        ["--mode", "default", "--algos", "Core-TwoOpt-TSP", "--execution-protocol", "fixed_evaluation_budget", "--backend-policy", "python_only"],
        ["--mode", "default", "--algos", "Core-TwoOpt-TSP", "--execution-protocol", "algorithm_native_termination", "--evaluation-budget", "10", "--backend-policy", "python_only"],
    ],
)
def test_cli_governed_configuration_fails_exit_2_before_setup(monkeypatch, argv) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("governed CLI validation reached setup")

    monkeypatch.setattr(cli_engine, "_ensure_dirs", explode)
    monkeypatch.setattr(cli_engine, "_all_strategy_specs", explode)

    assert cli_engine.main(argv) == 2


def test_cli_governed_configuration_resolves_before_registry_enumeration(monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("forbidden identifier reached setup")

    monkeypatch.setattr(cli_engine, "_ensure_dirs", explode)
    monkeypatch.setattr(cli_engine, "_all_strategy_specs", explode)

    assert cli_engine.main([
        "--mode", "default", "--algos", "GWO-LKH",
        "--execution-protocol", "fixed_evaluation_budget", "--evaluation-budget", "10",
        "--backend-policy", "python_only",
    ]) == 2


def test_smart_worker_postflight_violation_raises_and_is_not_converted_to_error(monkeypatch) -> None:
    class Registry:
        @staticmethod
        def list_algorithms():
            return ["Core-TwoOpt-TSP"]

        @staticmethod
        def get_executor(_algorithm_id):
            return lambda *_args: RunResult(
                problem="entrypoint-atsp", algorithm="Core-TwoOpt-TSP", run=0, seed=42,
                dimension=3, optimal=None, tour_cost=999.0, objective_cost=999.0,
                gap_pct=None, elapsed_sec=0.0, evaluations=1, tour=[1, 2, 3],
            )

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", Registry)
    task = BenchmarkTask("entrypoint-atsp", "Core-TwoOpt-TSP", 0, 42, {}, _request())

    with pytest.raises(ResultContractViolation):
        smart_benchmark._run_single_task((task, _Problem()))


def test_smart_selection_excludes_candidate_catalog_ids(monkeypatch) -> None:
    class Registry:
        @staticmethod
        def list_algorithms():
            return ["Core-TwoOpt-TSP", "Core-ThreeOpt-TSP", "Core-GWO-TSP-Pure", "Core-Greedy-Routing"]

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", Registry)

    assert smart_benchmark._selectable_algorithm_ids() == [
        "Core-TwoOpt-TSP", "Core-ThreeOpt-TSP", "Core-Greedy-Routing"
    ]


def test_cli_task_builder_preserves_legacy_tuple_and_adds_governed_request() -> None:
    legacy = cli_engine.StrategySpec("Core-Greedy-Routing", "Core-Greedy-Routing", {}, "routing")
    governed = cli_engine.StrategySpec("Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {}, "local_search", _request())

    assert len(cli_engine._make_param_combo_task(_Problem(), legacy, {}, 1, 1)) == 6
    task = cli_engine._make_param_combo_task(_Problem(), governed, {}, 1, 1)
    assert task[6] == governed.governed_request