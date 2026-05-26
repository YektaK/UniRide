import academic_benchmark.core.registry_setup  # noqa: F401
from academic_benchmark.cli_engine import _all_strategy_specs, _evaluate_param_combo, _make_problem_dict
from academic_benchmark.core.registry_setup import _run_core_routing_executor
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.engine_core import ProblemInstance


def test_core_routing_executor_returns_cvrp_routes():
    problem = ProblemInstance(
        name="tiny-cvrp",
        dimension=4,
        coordinates=[],
        problem_type="cvrp",
        dist_matrix=[
            [0, 10, 10, 10],
            [10, 0, 1, 1],
            [10, 1, 0, 1],
            [10, 1, 1, 0],
        ],
        demands=[0, 1, 1, 1],
        capacities=[2],
        capacity=2,
    )

    result = _run_core_routing_executor(problem, {}, seed=42, run_idx=1, algorithm_name="core-greedy-routing")

    assert result.problem_type == "cvrp"
    assert result.objective_cost == result.tour_cost
    assert result.routes
    assert result.num_vehicles == 2
    assert result.capacity_violations == 0


def test_core_routing_executor_returns_cvrptw_violations():
    problem = ProblemInstance(
        name="tiny-cvrptw",
        dimension=3,
        coordinates=[],
        problem_type="cvrptw",
        dist_matrix=[
            [0, 10, 10],
            [10, 0, 10],
            [10, 10, 0],
        ],
        demands=[0, 1, 1],
        capacities=[2],
        capacity=2,
        time_windows=[(0, 999), (0, 5), (0, 999)],
        service_times=[0, 0, 0],
        direction="dropoff",
    )

    result = _run_core_routing_executor(problem, {}, seed=42, run_idx=1, algorithm_name="core-greedy-routing")

    assert result.problem_type == "cvrptw"
    assert result.routes == [[1, 2]]
    assert result.tw_violations == 1


def test_core_greedy_routing_is_registered_for_academic_selection():
    names = AlgorithmRegistry.list_algorithms()
    specs = {spec.name: spec for spec in _all_strategy_specs()}

    assert "Core-Greedy-Routing" in names
    assert specs["Core-Greedy-Routing"].algorithm_type == "matrix_routing"


def test_cli_evaluate_param_combo_preserves_routing_result_fields():
    problem = ProblemInstance(
        name="tiny-cvrp",
        dimension=4,
        coordinates=[],
        problem_type="cvrp",
        dist_matrix=[
            [0, 10, 10, 10],
            [10, 0, 1, 1],
            [10, 1, 0, 1],
            [10, 1, 1, 0],
        ],
        demands=[0, 1, 1, 1],
        capacities=[2],
        capacity=2,
    )

    result = _evaluate_param_combo(
        (_make_problem_dict(problem), "Core-Greedy-Routing", "Core-Greedy-Routing", {}, 0, 1)
    )

    assert result["problem_type"] == "cvrp"
    assert result["routes"]
    assert result["num_vehicles"] == 2
    assert result["capacity_violations"] == 0
    assert result["objective_cost"] == result["avg_length"]
