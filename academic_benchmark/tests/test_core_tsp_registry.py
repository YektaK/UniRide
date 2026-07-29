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
        "Core-ThreeOpt-TSP",
        "Core-OrOpt-TSP",
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


def _coord_only_problem():
    """ProblemInstance with coordinates but no pre-computed dist_matrix.

    This forces _problem_matrix → prepare_matrices() path that the CLI
    worker uses when no TSPLIB DB cache entry exists.
    """
    return ProblemInstance(
        name="coord_only_4",
        dimension=4,
        coordinates=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        optimal=4.0,
        category="tiny",
        problem_type="tsp",
    )


@pytest.mark.parametrize(
    "algorithm",
    ["Core-GWO-TSP", "Core-HHO-TSP", "Numba-GWO", "Numba-HHO"],
)
def test_bildiri2026_registry_executors_run_coordinate_only_problem(algorithm):
    """Regression: GWO/HHO via registry must work when dist_matrix is not pre-set.

    The CLI worker (_evaluate_param_combo) builds a _Problem wrapper from a
    problem_dict that typically has no dist_matrix.  The registry executor
    calls _problem_matrix → prepare_matrices() which was missing from _Problem.
    This test exercises the same path through the real ProblemInstance.
    """
    algorithms = set(AlgorithmRegistry.list_algorithms())
    if algorithm not in algorithms:
        pytest.skip(f"{algorithm} not registered (missing bildiri2026 deps?)")

    executor = AlgorithmRegistry.get_executor(algorithm)
    result = executor(
        _coord_only_problem(),
        {
            "max_iterations": 3,
            "pack_size": 4,
            "hawks": 4,
            "polish_iters": 1,
            "final_polish_iters": 1,
            "fair_comparison": {"evaluation_budget": 500, "base_seed": 1000},
        },
        seed=42,
        run_idx=0,
    )

    assert result.tour_cost > 0
    assert result.tour is not None
    assert len(result.tour) == 4
    assert result.problem_type == "tsp"


@pytest.mark.parametrize(
    "algorithm",
    ["Core-GWO-TSP", "Core-HHO-TSP", "Numba-GWO", "Numba-HHO"],
)
def test_bildiri2026_registry_executors_run_problem_dict_wrapper(algorithm):
    """Regression: exercise the exact _Problem wrapper path from cli_engine.

    Simulates what _evaluate_param_combo does: build a _Problem from a dict
    with no dist_matrix, call prepare_matrices(), then pass to the registry.
    """
    algorithms = set(AlgorithmRegistry.list_algorithms())
    if algorithm not in algorithms:
        pytest.skip(f"{algorithm} not registered (missing bildiri2026 deps?)")

    from academic_benchmark.cli_engine import _evaluate_param_combo
    from academic_benchmark.core.algorithm_resolution import (
        IdentifierSource,
        resolve_algorithm_id,
    )
    from academic_benchmark.engine_core import GovernedExecutionRequest
    from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol
    import math

    problem_dict = {
        "name": "cli_wrap_4",
        "dimension": 4,
        "optimal": 4.0,
        "coordinates": [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        "category": "tiny",
        "source": "test",
        "is_time_matrix": False,
        "time_matrix": None,
        "problem_type": "tsp",
        "dist_matrix": None,
    }

    resolution = resolve_algorithm_id(algorithm, IdentifierSource.CLI)
    request = GovernedExecutionRequest(
        requested_algorithm_id=resolution.requested_id,
        canonical_algorithm_id=resolution.canonical_id,
        protocol=ExecutionProtocol.FIXED_BUDGET,
        evaluation_budget=500,
        backend_policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE,
    )
    task = (
        problem_dict,
        resolution.canonical_id,
        resolution.canonical_id,
        {
            "max_iterations": 3,
            "pack_size": 4,
            "hawks": 4,
            "polish_iters": 1,
            "final_polish_iters": 1,
            "fair_comparison": {"evaluation_budget": 500, "base_seed": 1000},
        },
        1,
        1,
        request,
    )
    result = _evaluate_param_combo(task)

    assert result["avg_length"] > 0
    assert not math.isnan(result["avg_gap"])
