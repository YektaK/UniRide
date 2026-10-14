"""M26 / QW11: a SOTA greedy fallback must not count as the requested algorithm
in the legacy /benchmark runner. It is recorded through the runner's existing
failed-run path (NaN tour length, ``execution_failed``), so aggregates drop it.
"""

import math

from benchmark_runner import AlgorithmConfig, BenchmarkRunner
from models.schemas import OptimizationResponse, RouteStep, VehicleRoute
from uniride_core.models import ProblemInstance


def _problem():
    return ProblemInstance(
        name="tiny4", dimension=4, problem_type="tsp", edge_weight_type="EUC_2D",
        category="small",
        coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        depot_index=0,
    )


def _response(*, fallback_reason=None):
    order = ["depot", "loc_1", "loc_2", "loc_3", "depot"]
    steps = [
        RouteStep(location1=a, location2=b, duration=10.0, distance=10.0)
        for a, b in zip(order, order[1:])
    ]
    route = VehicleRoute(
        vehicle_id="v1", route_details=steps, total_duration_minutes=40.0,
        total_distance_km=40.0, sw_count=0, so_count=3,
        student_ids=["loc_1", "loc_2", "loc_3"],
    )
    return OptimizationResponse(
        algorithm_used="greedy_fallback" if fallback_reason else "e2bso",
        success=True, routes=[route], total_vehicles=1, total_duration_minutes=40.0,
        fallback_reason=fallback_reason,
    )


class _Stub:
    def __init__(self, response):
        self.response = response

    def optimize(self, request):
        return self.response


def _run(response):
    runner = BenchmarkRunner(strategies_registry={"e2bso": _Stub(response)})
    return runner._run_single_experiment(
        _problem(), AlgorithmConfig(name="E2BSO", algorithm_id="e2bso", params={}), 1
    )


def test_fallback_run_is_recorded_as_failed_not_as_the_requested_algorithm():
    result = _run(_response(fallback_reason="solver_error"))

    assert math.isnan(result.tour_length)
    assert result.gap_percent is None
    assert result.metadata["execution_failed"] is True
    assert result.metadata["error_reason"] == "sota_fallback:solver_error"


def test_normal_run_is_unaffected():
    result = _run(_response())

    assert not math.isnan(result.tour_length)
    assert result.metadata["execution_failed"] is False
    assert "error_reason" not in result.metadata


def test_failed_fallback_run_is_excluded_from_aggregates():
    failed = _run(_response(fallback_reason="solver_error"))
    ok = _run(_response())

    only_fallback = BenchmarkRunner().get_results_summary([failed])
    mixed = BenchmarkRunner().get_results_summary([failed, ok])

    assert only_fallback == {}  # no e2bso entry at all
    assert mixed["e2bso"]["n_runs"] == 1
    assert mixed["e2bso"]["success_rate"] == 0.5
