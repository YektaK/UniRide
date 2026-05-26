import numpy as np

from uniride_core.algorithms.base_engine import StaticPermutationEngine
from uniride_core.benchmark_runner import MatrixAlgorithmConfig, MatrixBenchmarkRunner
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem


def test_matrix_benchmark_runner_solves_tsp_without_production_request():
    problem = RoutingProblem(
        name="tiny-tsp",
        problem_type="tsp",
        matrix=CostMatrix(np.array([[0, 1, 9], [4, 0, 2], [3, 8, 0]], dtype=np.float64)),
        optimal=6,
    )
    runner = MatrixBenchmarkRunner([
        MatrixAlgorithmConfig("static", StaticPermutationEngine([0, 1, 2]), params={"demo": True})
    ])

    results = runner.run([problem], n_runs=1, seed=7)

    assert len(results) == 1
    result = results[0]
    assert result.algorithm == "static"
    assert result.problem_type == "tsp"
    assert result.objective_cost == 6
    assert result.routes == [[0, 1, 2]]
    assert result.gap_percent == 0
    assert result.metadata["algorithm_params"] == {"demo": True}


def test_matrix_benchmark_runner_solves_cvrptw_with_routes_and_violations():
    problem = RoutingProblem(
        name="tiny-cvrptw",
        problem_type="cvrptw",
        matrix=CostMatrix(
            np.array(
                [
                    [0, 10, 10],
                    [10, 0, 10],
                    [10, 10, 0],
                ],
                dtype=np.float64,
            )
        ),
        constraints=ConstraintProfile(
            demands=[[0], [1], [1]],
            capacities=[2],
            time_windows=[(0, 999), (0, 5), (0, 999)],
            service_times=[0, 0, 0],
            direction="dropoff",
            target_time=0,
        ),
    )
    runner = MatrixBenchmarkRunner({"static": StaticPermutationEngine([1, 2])})

    result = runner.run([problem])[0]

    assert result.problem_type == "cvrptw"
    assert result.routes == [[1, 2]]
    assert result.num_vehicles == 1
    assert result.tw_violations == 1
    assert result.error is None


def test_matrix_benchmark_runner_returns_error_rows_for_invalid_instances():
    problem = RoutingProblem(
        name="bad-cvrp",
        problem_type="cvrp",
        matrix=CostMatrix(np.zeros((2, 2), dtype=np.float64)),
    )
    runner = MatrixBenchmarkRunner({"static": StaticPermutationEngine([1])})

    result = runner.run([problem])[0]

    assert result.error is not None
    assert "requires demands" in result.error
    assert result.metadata["execution_failed"] is True
