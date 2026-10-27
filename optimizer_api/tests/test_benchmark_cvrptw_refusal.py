"""MT1-08 follow-up: legacy /benchmark runner refuses CVRPTW rows explicitly.

A windowed request now needs target_time (OQ-MT1-14). The runner has none for
Solomon-style rows, so until MT1-11 (audit H16) it refuses them up front instead
of failing with a validation error hidden behind the generic except.
"""

import math

import pytest

from benchmark_runner import AlgorithmConfig, BenchmarkRunner
from uniride_core.models import ProblemInstance

REFUSAL = "CVRPTW rows are refused until MT1-11 (audit H16)"


def _cvrptw():
    return ProblemInstance(
        name="tinyw4", dimension=4, problem_type="cvrptw", edge_weight_type="EUC_2D",
        category="small",
        coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        depot_index=0, capacity=10, demands=[0, 1, 1, 1],
        time_windows=[(0, 100), (0, 50), (0, 50), (0, 50)],
        service_times=[0, 1, 1, 1],
    )


def _tsp():
    return ProblemInstance(
        name="tiny4", dimension=4, problem_type="tsp", edge_weight_type="EUC_2D",
        category="small",
        coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        depot_index=0,
    )


class _Spy:
    def __init__(self):
        self.calls = 0

    def optimize(self, request):
        self.calls += 1
        raise AssertionError("strategy must not be called for a refused row")


def _run(problem, strategy):
    runner = BenchmarkRunner(strategies_registry={"ga_split": strategy})
    return runner._run_single_experiment(
        problem, AlgorithmConfig(name="GA", algorithm_id="ga_split", params={}), 1
    )


def test_conversion_refuses_cvrptw_with_time_windows():
    runner = BenchmarkRunner()
    with pytest.raises(Exception, match=REFUSAL):
        runner._benchmark_problem_to_optimization_request(_cvrptw(), "ga_split")


def test_cvrptw_row_is_nan_failed_with_reason_and_strategy_not_called():
    spy = _Spy()
    result = _run(_cvrptw(), spy)

    assert spy.calls == 0
    assert math.isnan(result.tour_length)
    assert result.metadata["execution_failed"] is True
    assert result.metadata["error_reason"] == "cvrptw_refused_h16_mt1_11"


def test_tsp_problem_still_converts_and_runs():
    request = BenchmarkRunner()._benchmark_problem_to_optimization_request(_tsp(), "ga_split")
    assert request.use_time_windows is False
    assert len(request.students) == 3
