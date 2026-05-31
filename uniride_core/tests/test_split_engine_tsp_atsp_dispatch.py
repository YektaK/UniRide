import numpy as np
import pytest

from uniride_core.algorithms.engine_factory import create_matrix_engine
from uniride_core.models import CostMatrix, RoutingProblem, TSPResult


SPLIT_ENGINES = ["GA-Split", "PSO-Split", "GWO-Split", "HHO-Split"]


def _problem(problem_type: str) -> RoutingProblem:
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
    )


@pytest.mark.parametrize("engine_name", SPLIT_ENGINES)
@pytest.mark.parametrize("problem_type", ["tsp", "atsp"])
def test_split_engine_aliases_delegate_tsp_and_atsp_to_single_tour(engine_name, problem_type):
    engine = create_matrix_engine(engine_name)

    result = engine.solve_problem(
        _problem(problem_type),
        config={
            "population_size": 6,
            "num_particles": 6,
            "num_wolves": 6,
            "num_hawks": 6,
            "max_iterations": 2,
            "iterations": 2,
            "elite_count": 1,
            "tournament_size": 2,
            "local_search_rate": 0.0,
        },
        seed=123,
    )

    assert isinstance(result, TSPResult)
    assert result.algorithm == engine_name
    assert sorted(result.tour) == [0, 1, 2, 3]
    assert result.tour_length > 0.0
