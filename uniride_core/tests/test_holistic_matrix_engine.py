import numpy as np
import pytest

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
