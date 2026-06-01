import numpy as np
from dataclasses import asdict

from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.algorithms.base_engine import StaticPermutationEngine
from uniride_core.algorithms.numba_metaheuristics import run_single_test
from uniride_core.algorithms.split_decoder import (
    calculate_route_cost,
    optimal_split,
    split_with_time_windows_result,
    validate_cvrp_solution,
)
from uniride_core.models import CVRPResult, ConstraintProfile, CostMatrix, RoutingProblem, RoutingResult


def test_matrix_builder_from_coordinates_uses_tsplib_rounding():
    dm = MatrixBuilder.from_coordinates([(0, 0), (3, 4), (6, 8)], "EUC_2D")

    assert dm.dtype == np.int32
    assert dm.shape == (3, 3)
    assert dm[0, 1] == 5
    assert dm[1, 2] == 5


def test_matrix_builder_from_euclidean_coordinates_keeps_float_precision():
    dm = MatrixBuilder.from_euclidean_coordinates([(0, 0), (1, 1)])

    assert dm.dtype == np.float64
    assert dm[0, 1] == np.sqrt(2)


def test_matrix_builder_parses_tsplib_text_into_routing_problem():
    text = """
NAME : tiny-tsp
TYPE : TSP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EUC_2D
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
EOF
"""

    problem = MatrixBuilder.from_tsplib_text(text)

    assert problem.name == "tiny-tsp"
    assert problem.problem_type == "tsp"
    assert problem.matrix.kind == "distance"
    assert problem.matrix.labels == ["1", "2", "3"]
    assert problem.matrix.values[0, 1] == 5


def test_matrix_builder_parses_atsp_text_into_routing_problem():
    text = """
NAME : tiny-atsp
TYPE : ATSP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EXPLICIT
EDGE_WEIGHT_FORMAT : FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 9
4 0 2
3 8 0
EOF
"""

    problem = MatrixBuilder.from_atsp_text(text)

    assert problem.name == "tiny-atsp"
    assert problem.problem_type == "atsp"
    assert problem.matrix.is_asymmetric is True
    assert problem.matrix.values[0, 2] == 9
    assert problem.matrix.values[2, 0] == 3


def test_matrix_builder_parses_cvrplib_into_unified_problem():
    text = """
NAME : tiny-cvrp
TYPE : CVRP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 5
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
DEMAND_SECTION
1 0
2 2
3 3
DEPOT_SECTION
1
-1
EOF
"""

    problem = MatrixBuilder.from_cvrplib_text(text)

    assert problem.problem_type == "cvrp"
    assert problem.matrix.values.shape == (3, 3)
    assert problem.constraints.capacities == [5]
    assert problem.constraints.demands == [[0], [2], [3]]
    assert problem.constraints.depot_index == 0


def test_matrix_builder_parses_solomon_into_unified_problem():
    text = """
R101
VEHICLE
NUMBER     CAPACITY
2          10
CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0         0        0        0       0           1000      0
1         3        4        2       10          50        5
2         6        8        3       20          70        5
"""

    problem = MatrixBuilder.from_solomon_text(text)

    assert problem.problem_type == "cvrptw"
    assert problem.matrix.values.shape == (3, 3)
    assert problem.matrix.values.dtype == np.float64
    assert problem.matrix.values[0, 1] == 5.0
    assert problem.matrix.values[1, 2] == 5.0
    assert problem.constraints.capacities == [10]
    assert problem.constraints.time_windows == [(0, 1000), (10, 50), (20, 70)]
    assert problem.constraints.service_times == [0, 5, 5]
    assert problem.metadata["vehicles"] == 2


def test_matrix_builder_converts_routing_problem_to_legacy_problem_instance():
    text = """
R101
VEHICLE
NUMBER     CAPACITY
2          10
CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0         0        0        0       0           1000      0
1         3        4        2       10          50        5
2         6        8        3       20          70        5
"""

    routing_problem = MatrixBuilder.from_solomon_text(text)
    legacy = MatrixBuilder.to_problem_instance(routing_problem)

    assert legacy.name == "R101"
    assert legacy.problem_type == "cvrptw"
    assert legacy.dist_matrix[0][1] == 5.0
    assert legacy.demands == [0, 2, 3]
    assert legacy.capacity == 10
    assert legacy.capacities == [10]
    assert legacy.num_vehicles == 2
    assert legacy.time_windows == [(0, 1000), (10, 50), (20, 70)]
    assert legacy.service_times == [0, 5, 5]


def test_matrix_builder_converts_legacy_problem_instance_to_routing_problem():
    routing_problem = MatrixBuilder.from_cvrplib_text(
        """
NAME : tiny-cvrp
TYPE : CVRP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 5
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
DEMAND_SECTION
1 0
2 2
3 3
DEPOT_SECTION
1
-1
EOF
"""
    )
    legacy = MatrixBuilder.to_problem_instance(routing_problem)

    converted = MatrixBuilder.to_routing_problem(legacy)

    assert converted.problem_type == "cvrp"
    assert converted.matrix.values[0, 1] == 5
    assert converted.constraints.demands == [[0], [2], [3]]
    assert converted.constraints.capacities == [5]


def test_scalar_cvrp_split_validates_capacity():
    dm = np.array(
        [
            [0, 10, 20, 30, 40, 50],
            [10, 0, 15, 25, 35, 45],
            [20, 15, 0, 10, 20, 30],
            [30, 25, 10, 0, 10, 20],
            [40, 35, 20, 10, 0, 10],
            [50, 45, 30, 20, 10, 0],
        ],
        dtype=np.float64,
    )

    routes = optimal_split([1, 2, 3, 4, 5], dm, [0, 3, 4, 3, 4, 3], capacity=8)
    ok, errors = validate_cvrp_solution(routes, [0, 3, 4, 3, 4, 3], 8, 5)

    assert ok, errors
    assert len(routes) == 3


def test_vector_capacity_split_supports_uniride_sw_so_loads():
    dm = np.array(
        [
            [0, 5, 6, 7],
            [5, 0, 2, 3],
            [6, 2, 0, 2],
            [7, 3, 2, 0],
        ],
        dtype=np.float64,
    )
    demands = [[0, 0], [1, 0], [0, 2], [1, 1]]

    routes = optimal_split([1, 2, 3], dm, demands, capacity=[1, 3])
    ok, errors = validate_cvrp_solution(routes, demands, [1, 3], 3)

    assert ok, errors
    assert len(routes) == 2


def test_time_window_split_reports_violations_without_api_dependency():
    dm = np.array(
        [
            [0, 10, 10],
            [10, 0, 10],
            [10, 10, 0],
        ],
        dtype=np.float64,
    )
    result = split_with_time_windows_result(
        [1, 2],
        dm,
        demands=[0, 1, 1],
        capacities=2,
        time_windows=[(0, 999), (0, 5), (0, 999)],
        service_times=[0, 0, 0],
        direction="dropoff",
        target_time=0,
    )

    assert result.routes == [[1, 2]]
    assert result.tw_violations == 1


def test_unified_engine_decodes_cvrp_routes():
    dm = np.array(
        [
            [0, 10, 10, 10],
            [10, 0, 1, 1],
            [10, 1, 0, 1],
            [10, 1, 1, 0],
        ],
        dtype=np.float64,
    )
    engine = StaticPermutationEngine([1, 2, 3])

    result = engine.solve_cvrp(dm, demands=[0, 1, 1, 1], capacities=2)

    assert result.problem_type == "CVRP"
    assert len(result.routes) == 2
    assert result.num_vehicles == 2
    assert result.objective_cost == sum(calculate_route_cost(r, dm) for r in result.routes)
    assert result.total_cost == result.objective_cost


def test_unified_engine_solve_problem_dispatches_tsp_and_atsp():
    tsp = MatrixBuilder.from_tsplib_text(
        """
NAME : tiny-tsp
TYPE : TSP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EUC_2D
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
EOF
"""
    )
    atsp = MatrixBuilder.from_atsp_text(
        """
NAME : tiny-atsp
TYPE : ATSP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EXPLICIT
EDGE_WEIGHT_FORMAT : FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 9
4 0 2
3 8 0
EOF
"""
    )
    engine = StaticPermutationEngine([0, 1, 2])

    tsp_result = engine.solve_problem(tsp, config={"x": 1}, seed=11)
    atsp_result = engine.solve_problem(atsp, seed=12)

    assert tsp_result.tour == [0, 1, 2]
    assert tsp_result.tour_length == 20
    assert tsp_result.params["x"] == 1
    assert tsp_result.params["problem_type"] == "tsp"
    assert atsp_result.tour == [0, 1, 2]
    assert atsp_result.tour_length == 6


def test_unified_engine_solve_problem_dispatches_cvrp():
    problem = RoutingProblem(
        name="tiny-cvrp",
        problem_type="cvrp",
        matrix=CostMatrix(
            np.array(
                [
                    [0, 10, 10, 10],
                    [10, 0, 1, 1],
                    [10, 1, 0, 1],
                    [10, 1, 1, 0],
                ],
                dtype=np.float64,
            )
        ),
        constraints=ConstraintProfile(
            demands=[[0], [1], [1], [1]],
            capacities=[2],
        ),
    )
    engine = StaticPermutationEngine([1, 2, 3])

    result = engine.solve_problem(problem)

    assert result.problem_type == "CVRP"
    assert result.num_vehicles == 2
    assert result.capacity_violations == 0


def test_unified_engine_solve_problem_dispatches_cvrptw():
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
    engine = StaticPermutationEngine([1, 2])

    result = engine.solve_problem(problem)

    assert result.problem_type == "CVRPTW"
    assert result.routes == [[1, 2]]
    assert result.tw_violations == 1


def test_unified_engine_solve_problem_validates_required_constraints():
    problem = RoutingProblem(
        name="bad-cvrp",
        problem_type="cvrp",
        matrix=CostMatrix(np.zeros((2, 2), dtype=np.float64)),
    )
    engine = StaticPermutationEngine([1])

    try:
        engine.solve_problem(problem)
    except ValueError as exc:
        assert "requires demands" in str(exc)
    else:
        raise AssertionError("Expected missing demands to fail")


def test_routing_results_expose_total_cost_alias():
    routing = RoutingResult(algorithm="test", problem_type="cvrp", objective_cost=123.5)
    cvrp = CVRPResult(algorithm="test", problem_type="cvrp", objective_cost=456.0)

    assert routing.total_cost == 123.5
    assert cvrp.total_cost == 456.0
    assert asdict(cvrp)["total_cost"] == 456.0


def test_core_numba_metaheuristic_runner_smoke():
    class Problem:
        name = "tiny"
        dimension = 5
        coordinates = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)]
        optimal = None

    result = run_single_test(
        Problem(),
        "GA",
        seed=7,
        params={"pop_size": 8, "generations": 2, "mutation_rate": 0.1, "elite_size": 2},
    )

    assert result["tour_length"] > 0
    assert len(result["tour"]) == 5
    assert result["algorithm_type"] == "meta_heuristic"
