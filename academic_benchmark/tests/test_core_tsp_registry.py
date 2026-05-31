from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.models import ProblemInstance
import pytest


def _tiny_tsp_problem():
    return ProblemInstance(
        name="tiny4",
        dimension=4,
        coordinates=[],
        optimal=4.0,
        category="tiny",
        problem_type="tsp",
        dist_matrix=[
            [0, 1, 2, 1],
            [1, 0, 1, 2],
            [2, 1, 0, 1],
            [1, 2, 1, 0],
        ],
    )


def test_academic_registry_exposes_core_tsp_engines():
    algorithms = set(AlgorithmRegistry.list_algorithms())

    assert {
        "Core-TwoOpt-TSP",
        "Core-GA-TSP",
        "Core-PSO-TSP",
        "Core-GWO-TSP",
        "Core-HHO-TSP",
        "FCM-GA-TSP",
        "FCM-PSO-TSP",
        "FCM-GWO-TSP",
        "FCM-HHO-TSP",
    }.issubset(algorithms)


@pytest.mark.parametrize(
    ("algorithm", "params"),
    [
        ("Core-TwoOpt-TSP", {"max_iterations": 12}),
        (
            "Core-GA-TSP",
            {
                "population_size": 8,
                "max_iterations": 5,
                "crossover_rate": 0.8,
                "mutation_rate": 0.2,
                "elite_count": 2,
                "tournament_size": 3,
                "max_no_improvement": 4,
            },
        ),
        (
            "Core-PSO-TSP",
            {
                "num_particles": 8,
                "max_iterations": 5,
                "cognitive_weight": 1.2,
                "social_weight": 1.2,
                "inertia_weight": 0.7,
                "max_velocity_size": 3,
                "local_search_rate": 0.0,
            },
        ),
        (
            "Core-GWO-TSP",
            {
                "num_wolves": 8,
                "max_iterations": 5,
                "a_initial": 2.0,
                "local_search_rate": 0.0,
            },
        ),
        (
            "Core-HHO-TSP",
            {
                "num_hawks": 8,
                "max_iterations": 5,
                "escape_energy_factor": 2.0,
                "jump_probability": 0.5,
                "levy_beta": 1.5,
                "local_search_rate": 0.0,
            },
        ),
    ],
)
def test_core_tsp_executors_run_matrix_native_problem(algorithm, params):
    executor = AlgorithmRegistry.get_executor(algorithm)

    result = executor(
        _tiny_tsp_problem(),
        params,
        seed=123,
        run_idx=1,
    )

    assert result.algorithm == algorithm
    assert result.problem_type == "tsp"
    assert result.matrix_kind == "distance"
    assert result.objective_cost == result.tour_cost
    assert set(result.tour) == {1, 2, 3, 4}


def test_fcm_tsp_executor_runs_matrix_native_problem():
    executor = AlgorithmRegistry.get_executor("FCM-GA-TSP")

    result = executor(
        _tiny_tsp_problem(),
        {
            "population_size": 8,
            "max_iterations": 5,
            "elite_count": 2,
            "tournament_size": 3,
            "fcm_clusters": 2,
            "fcm_min_cluster_size": 2,
            "fcm_iterations": 8,
        },
        seed=123,
        run_idx=1,
    )

    assert result.algorithm == "FCM-GA-TSP"
    assert result.problem_type == "tsp"
    assert result.objective_cost == result.tour_cost
    assert set(result.tour) == {1, 2, 3, 4}
