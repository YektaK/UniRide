import numpy as np

from uniride_core.algorithms.engine_factory import create_matrix_engine, list_matrix_engine_names
from uniride_core.algorithms.fcm_split_engine import FCMSplitMatrixEngine
from uniride_core.models import CostMatrix, RoutingProblem


def _circle_problem(n: int = 10) -> RoutingProblem:
    coords = [
        (float(np.cos(2 * np.pi * idx / n)), float(np.sin(2 * np.pi * idx / n)))
        for idx in range(n)
    ]
    matrix = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            matrix[i, j] = float(np.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1]))
    return RoutingProblem(
        name="circle10",
        problem_type="tsp",
        matrix=CostMatrix(matrix),
        coordinates=coords,
    )


def test_fcm_split_engine_solves_tsp_permutation():
    engine = create_matrix_engine("FCM-GA-TSP")
    problem = _circle_problem()

    result = engine.solve_problem(
        problem,
        config={
            "population_size": 8,
            "max_iterations": 4,
            "elite_count": 2,
            "tournament_size": 3,
            "fcm_clusters": 3,
            "fcm_iterations": 8,
            "fcm_min_cluster_size": 2,
            "fcm_polish_iterations": 20,
        },
        seed=42,
    )

    assert isinstance(engine, FCMSplitMatrixEngine)
    assert result.algorithm == "FCM-GA-TSP"
    assert set(result.tour) == set(range(problem.dimension))
    assert len(result.tour) == problem.dimension
    assert result.tour_length > 0


def test_matrix_engine_factory_lists_fcm_srs_engines():
    names = set(list_matrix_engine_names())

    assert {"FCM-GA-TSP", "FCM-PSO-TSP", "FCM-GWO-TSP", "FCM-HHO-TSP"}.issubset(names)
