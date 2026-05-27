import numpy as np

from uniride_core.algorithms.tsp_meta_engines import solve_ga_tsp
from uniride_core.algorithms.tsp_meta_matrix_engine import TSPMetaMatrixEngine
from uniride_core.models import CostMatrix, RoutingProblem


def test_tsp_meta_matrix_engine_solves_tsp_problem():
    problem = RoutingProblem(
        name="tiny-tsp",
        problem_type="tsp",
        matrix=CostMatrix(
            np.array(
                [
                    [0, 1, 2, 1],
                    [1, 0, 1, 2],
                    [2, 1, 0, 1],
                    [1, 2, 1, 0],
                ],
                dtype=float,
            )
        ),
        optimal=4.0,
    )
    engine = TSPMetaMatrixEngine("Core-GA-TSP", solve_ga_tsp)

    result = engine.solve_problem(
        problem,
        config={
            "population_size": 8,
            "max_iterations": 5,
            "crossover_rate": 0.8,
            "mutation_rate": 0.2,
            "elite_count": 2,
            "tournament_size": 3,
            "max_no_improvement": 4,
        },
        seed=123,
    )

    assert result.algorithm == "Core-GA-TSP"
    assert result.tour_length >= 4.0
    assert set(result.tour) == {0, 1, 2, 3}
