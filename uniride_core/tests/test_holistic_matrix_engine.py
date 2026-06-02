import numpy as np
import pytest

from uniride_core.algorithms.holistic_matrix_engine import _time_window_violations
from uniride_core.algorithms.engine_factory import create_matrix_engine
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem, RoutingResult, TSPResult


HOLISTIC_ENGINES = ["OR-Tools", "PyVRP", "VROOM"]


def _tsp_problem(problem_type: str = "tsp") -> RoutingProblem:
    matrix = np.array(
        [
            [0.0, 2.0, 9.0, 10.0],
            [1.0, 0.0, 6.0, 4.0],
            [15.0, 7.0, 0.0, 8.0],
            [6.0, 3.0, 12.0, 0.0],
        ],
        dtype=float,
    )
    return RoutingProblem(
        name=f"tiny-{problem_type}",
        problem_type=problem_type,
        matrix=CostMatrix(matrix, kind="travel_time", is_asymmetric=problem_type == "atsp"),
        coordinates=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
    )


def _cvrp_problem() -> RoutingProblem:
    return RoutingProblem(
        name="tiny-cvrp",
        problem_type="cvrp",
        matrix=CostMatrix(
            np.array(
                [
                    [0.0, 2.0, 3.0],
                    [2.0, 0.0, 1.0],
                    [3.0, 1.0, 0.0],
                ],
                dtype=float,
            ),
            kind="travel_time",
        ),
        constraints=ConstraintProfile(
            demands=[[0, 0], [1, 0], [0, 1]],
            capacities=[1, 1],
            depot_index=0,
            max_route_duration=20,
        ),
        coordinates=[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)],
    )


def _scalar_demand_cvrp_problem() -> RoutingProblem:
    return RoutingProblem(
        name="scalar-demand-cvrp",
        problem_type="cvrp",
        matrix=CostMatrix(
            np.array(
                [
                    [0.0, 1.0, 1.0],
                    [1.0, 0.0, 1.0],
                    [1.0, 1.0, 0.0],
                ],
                dtype=float,
            ),
            kind="distance",
        ),
        constraints=ConstraintProfile(
            demands=[[0], [4], [4]],
            capacities=[5],
            depot_index=0,
            max_route_duration=20,
        ),
        coordinates=[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)],
        metadata={"vehicles": 2},
    )


@pytest.mark.parametrize("engine_name", HOLISTIC_ENGINES)
@pytest.mark.parametrize("problem_type", ["tsp", "atsp"])
def test_holistic_engines_solve_tsp_and_atsp_as_single_vehicle_routes(engine_name, problem_type):
    engine = create_matrix_engine(engine_name)

    result = engine.solve_problem(_tsp_problem(problem_type), config={"time_limit_seconds": 1})

    assert isinstance(result, TSPResult)
    assert result.algorithm == engine_name
    assert sorted(result.tour) == [0, 1, 2, 3]
    assert result.tour_length > 0.0


@pytest.mark.parametrize("engine_name", HOLISTIC_ENGINES)
def test_holistic_engines_solve_cvrp_as_routing_result(engine_name):
    engine = create_matrix_engine(engine_name)

    result = engine.solve_problem(_cvrp_problem(), config={"time_limit_seconds": 1})

    assert isinstance(result, RoutingResult)
    assert result.algorithm == engine_name
    assert sorted(node for route in result.routes for node in route) == [1, 2]
    assert result.num_vehicles >= 1


@pytest.mark.parametrize("engine_name", HOLISTIC_ENGINES)
def test_holistic_engines_enforce_scalar_cvrp_demands(engine_name):
    engine = create_matrix_engine(engine_name)

    result = engine.solve_problem(_scalar_demand_cvrp_problem(), config={"time_limit_seconds": 1})

    assert isinstance(result, RoutingResult)
    assert sorted(node for route in result.routes for node in route) == [1, 2]
    assert all(load[0] <= 5 for load in result.route_loads)
    assert result.num_vehicles == 2


def test_holistic_ortools_preserves_search_and_scale_params():
    engine = create_matrix_engine("OR-Tools")
    config = {
        "time_limit_seconds": 1,
        "scale": 100,
        "first_solution_strategy": "PARALLEL_CHEAPEST_INSERTION",
        "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
    }

    result = engine.solve_problem(_cvrp_problem(), config=config)

    assert isinstance(result, RoutingResult)
    assert result.params == config
    assert sorted(node for route in result.routes for node in route) == [1, 2]


def test_holistic_time_window_post_validation_counts_late_arrivals():
    problem = RoutingProblem(
        name="tw-check",
        problem_type="cvrptw",
        matrix=CostMatrix(
            np.array(
                [
                    [0.0, 10.0, 10.0],
                    [10.0, 0.0, 10.0],
                    [10.0, 10.0, 0.0],
                ],
                dtype=float,
            )
        ),
        constraints=ConstraintProfile(
            demands=[[0], [1], [1]],
            capacities=[2],
            time_windows=[(0, 999), (0, 5), (0, 999)],
            service_times=[0, 0, 0],
        ),
    )

    assert _time_window_violations([[1, 2]], problem.matrix.values, problem) == 1
