"""FCM-*-TSP matrix engines refuse CVRP/CVRPTW problems at the engine layer too.

The academic registry refuses routing for these IDs (owner decision 2026-10-23). The
matrix-native benchmark paths (optimizer_api matrix_native mode, run_matrix_benchmark) build the
engine directly with create_matrix_engine and bypass the registry, so the engine refuses as well.
"""
import numpy as np
import pytest

from uniride_core.algorithms.engine_factory import create_matrix_engine
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem

FCM_IDS = ["FCM-GA-TSP", "FCM-PSO-TSP", "FCM-GWO-TSP", "FCM-HHO-TSP"]
CONFIG = {
    "population_size": 6, "max_iterations": 3, "elite_count": 2, "tournament_size": 3,
    "fcm_clusters": 2, "fcm_min_cluster_size": 2, "fcm_iterations": 4,
    "fcm_polish_iterations": 5, "max_no_improvement": 3,
}


def _routing_problem(problem_type: str) -> RoutingProblem:
    n = 7
    rng = np.random.default_rng(3)
    pts = rng.integers(0, 50, size=(n, 2))
    dm = np.array([[float(np.hypot(*(a - b))) for b in pts] for a in pts])
    return RoutingProblem(
        name=f"tiny-{problem_type}",
        problem_type=problem_type,
        matrix=CostMatrix(dm),
        coordinates=[(float(x), float(y)) for x, y in pts],
        constraints=ConstraintProfile(
            demands=[[0]] + [[1]] * (n - 1),
            capacities=[3],
            time_windows=[(0, 999)] * n if problem_type == "cvrptw" else None,
            service_times=[0] * n if problem_type == "cvrptw" else None,
        ),
    )


@pytest.mark.parametrize("problem_type", ["cvrp", "cvrptw"])
@pytest.mark.parametrize("algorithm_id", FCM_IDS)
def test_engine_refuses_routing_problems(algorithm_id, problem_type) -> None:
    engine = create_matrix_engine(algorithm_id)
    with pytest.raises(ValueError) as excinfo:
        engine.solve_problem(_routing_problem(problem_type), config=dict(CONFIG), seed=1)
    message = str(excinfo.value)
    assert algorithm_id in message
    assert f"refuses {problem_type.upper()} routing problems before any evaluation" in message


@pytest.mark.parametrize("algorithm_id", FCM_IDS)
def test_raw_permutation_entry_also_refuses_routing(algorithm_id) -> None:
    engine = create_matrix_engine(algorithm_id)
    dm = _routing_problem("cvrp").matrix.values
    with pytest.raises(ValueError, match="refuses CVRP routing problems"):
        engine.optimize_permutation(dm, config={**CONFIG, "problem_type": "cvrp"}, seed=1)


@pytest.mark.parametrize("problem_type", ["tsp", "atsp"])
@pytest.mark.parametrize("algorithm_id", FCM_IDS)
def test_engine_still_solves_tsp_and_atsp(algorithm_id, problem_type) -> None:
    problem = _routing_problem(problem_type)
    problem.constraints = ConstraintProfile()
    result = create_matrix_engine(algorithm_id).solve_problem(problem, config=dict(CONFIG), seed=1)
    assert sorted(result.tour) == list(range(problem.dimension))
