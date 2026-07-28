"""Cross-path scientific-integrity checks for fair TSP/ATSP experiments."""

import pytest

from academic_benchmark.cli_engine import _evaluate_param_combo
from academic_benchmark.core import registry_setup  # noqa: F401
from uniride_core.algorithms.tsp_matrix_metaheuristics.gwo_solver import GWOOptimizer
from uniride_core.algorithms.tsp_matrix_metaheuristics.hho_solver import HHOOptimizer
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import (
    FairComparisonManifest,
    FairnessValidationError,
    ObjectiveEvaluationBudget,
    improve_two_opt_budgeted,
)
from uniride_core.models import ProblemInstance


EXPLICIT_VARIANTS = (
    "Core-GWO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Pure",
    "Core-HHO-TSP-Memetic-2opt",
    "Core-TwoOpt-TSP",
    "Core-ThreeOpt-TSP",
)


def test_scientific_integrity_uses_canonical_gwo_hho_classes():
    assert GWOOptimizer.__module__.startswith(
        "uniride_core.algorithms.tsp_matrix_metaheuristics"
    )
    assert HHOOptimizer.__module__.startswith(
        "uniride_core.algorithms.tsp_matrix_metaheuristics"
    )


def _asymmetric_matrix(n=8):
    return [
        [0.0 if i == j else float((i + 1) * 17 + (j + 1) * 5 + i * j) for j in range(n)]
        for i in range(n)
    ]


def _problem():
    matrix = _asymmetric_matrix()
    return ProblemInstance(
        name="fair-integrity-atsp-8",
        dimension=8,
        coordinates=[],
        problem_type="atsp",
        dist_matrix=matrix,
    )


def _params():
    return {
        "fair_comparison": {"evaluation_budget": 500, "base_seed": 91},
        "max_iterations": 2,
        "pack_size": 6,
        "hawks": 6,
        "polish_iters": 1,
        "final_polish_iters": 1,
        "dive_count": 2,
    }


def _closed_cost(result, matrix):
    route = [node - 1 for node in result.tour]
    return sum(
        float(matrix[node][route[(idx + 1) % len(route)]])
        for idx, node in enumerate(route)
    )


@pytest.mark.parametrize("algorithm", EXPLICIT_VARIANTS)
def test_every_fair_variant_reports_exact_directed_closed_tour_cost(algorithm):
    problem = _problem()
    result = AlgorithmRegistry.get_executor(algorithm)(
        problem, _params(), seed=999, run_idx=0
    )

    assert result.tour_cost == pytest.approx(_closed_cost(result, problem.dist_matrix))
    assert set(result.tour) == set(range(1, 9))
    assert 0 < result.objective_evaluations <= result.evaluation_budget


@pytest.mark.parametrize(
    "algorithm",
    ("Core-GWO-TSP", "Core-HHO-TSP", "Numba-GWO", "Numba-HHO"),
)
def test_backward_compatible_gwo_hho_aliases_disclose_memetic_policy(algorithm):
    result = AlgorithmRegistry.get_executor(algorithm)(
        _problem(), _params(), seed=1, run_idx=1
    )

    assert result.algorithm_id == algorithm
    assert result.variant == "memetic_2opt"
    assert result.polish_policy == {
        "enabled": True,
        "initial": True,
        "periodic": True,
        "final": True,
        "operator": "2-opt",
    }


def test_budgeted_search_result_includes_initial_objective_evaluation():
    matrix = [
        [0.0, 1.0, 2.0, 1.0],
        [1.0, 0.0, 1.0, 2.0],
        [2.0, 1.0, 0.0, 1.0],
        [1.0, 2.0, 1.0, 0.0],
    ]
    budget = ObjectiveEvaluationBudget(10)
    result = improve_two_opt_budgeted(
        [0, 1, 2, 3], matrix, budget, max_iterations=0
    )

    assert result.evaluations == 1
    assert budget.used == 1


def test_manifest_rejects_variant_polish_contradiction():
    result = AlgorithmRegistry.get_executor("Core-GWO-TSP-Pure")(
        _problem(), _params(), seed=1, run_idx=0
    )
    manifest = FairComparisonManifest.from_value(_params()["fair_comparison"])
    result.polish_policy["enabled"] = True

    with pytest.raises(FairnessValidationError, match="pure variant cannot enable polishing"):
        manifest.validate_result(result)


@pytest.mark.parametrize(
    ("algorithm", "wrong_family"),
    (
        ("Core-GWO-TSP-Pure", "HHO"),
        ("Core-HHO-TSP-Pure", "GWO"),
        ("Core-TwoOpt-TSP", "3-opt"),
        ("Core-ThreeOpt-TSP", "2-opt"),
    ),
)
def test_manifest_rejects_algorithm_family_mismatches(algorithm, wrong_family):
    result = AlgorithmRegistry.get_executor(algorithm)(
        _problem(), _params(), seed=1, run_idx=0
    )
    manifest = FairComparisonManifest.from_value(_params()["fair_comparison"])
    result.algorithm_family = wrong_family

    with pytest.raises(FairnessValidationError, match="does not match the expected family"):
        manifest.validate_result(result)


def test_manifest_rejects_incomplete_and_contradictory_polish_policies():
    manifest = FairComparisonManifest.from_value(_params()["fair_comparison"])
    pure = AlgorithmRegistry.get_executor("Core-GWO-TSP-Pure")(
        _problem(), _params(), seed=1, run_idx=0
    )
    pure.polish_policy = {"enabled": False}
    with pytest.raises(FairnessValidationError, match="polish_policy missing fields"):
        manifest.validate_result(pure)

    memetic = AlgorithmRegistry.get_executor("Core-HHO-TSP-Memetic-2opt")(
        _problem(), _params(), seed=1, run_idx=0
    )
    memetic.polish_policy["final"] = False
    with pytest.raises(FairnessValidationError, match="must enable every polish phase"):
        manifest.validate_result(memetic)


def _small_symmetric_matrix():
    return [
        [0.0, 1.0, 2.0, 1.0],
        [1.0, 0.0, 1.0, 2.0],
        [2.0, 1.0, 0.0, 1.0],
        [1.0, 2.0, 1.0, 0.0],
    ]


def _zero_indexed_closed_cost(tour, matrix):
    return sum(
        matrix[node][tour[(idx + 1) % len(tour)]]
        for idx, node in enumerate(tour)
    )


@pytest.mark.parametrize(
    ("solver_cls", "population_params"),
    (
        (GWOOptimizer, {"pack_size": 4}),
        (HHOOptimizer, {"hawks": 4, "dive_count": 0}),
    ),
)
def test_final_polish_budget_exhaustion_is_exposed(solver_cls, population_params):
    matrix = _small_symmetric_matrix()
    solver = solver_cls(
        **population_params,
        max_iterations=0,
        polish_iters=0,
        final_polish_iters=10,
        random_seed=7,
        polish_enabled=True,
        evaluation_budget=5,
    )
    result = solver.solve_with_matrix(matrix, recalculate=False, closed_tsp=True)

    assert result.extra_stats["objective_evaluations"] == 5
    assert result.extra_stats["evaluation_budget"] == 5
    assert result.extra_stats["budget_terminated"] is True
    assert result.tour_length == pytest.approx(
        _zero_indexed_closed_cost(result.tour, matrix)
    )


@pytest.mark.parametrize(
    ("solver_cls", "population_params", "budget"),
    (
        (GWOOptimizer, {"pack_size": 4}, 31),
        (HHOOptimizer, {"hawks": 4, "dive_count": 0}, 40),
    ),
)
def test_periodic_polish_budget_exhaustion_is_exposed(
    solver_cls, population_params, budget
):
    solver = solver_cls(
        **population_params,
        max_iterations=2,
        polish_interval=1,
        polish_iters=1,
        final_polish_iters=0,
        random_seed=7,
        polish_enabled=True,
        evaluation_budget=budget,
    )
    result = solver.solve_with_matrix(
        _small_symmetric_matrix(), recalculate=False, closed_tsp=True
    )

    assert result.extra_stats["objective_evaluations"] == budget
    assert result.extra_stats["budget_terminated"] is True


def test_public_fair_result_exposes_budget_termination():
    params = _params()
    params["fair_comparison"]["evaluation_budget"] = 5
    params.update(
        {"max_iterations": 0, "pack_size": 4, "polish_iters": 0, "final_polish_iters": 10}
    )
    result = AlgorithmRegistry.get_executor("Core-GWO-TSP-Memetic-2opt")(
        _problem(), params, seed=1, run_idx=0
    )

    assert result.objective_evaluations == 5
    assert result.budget_terminated is True


def test_cli_aggregate_preserves_full_contract_for_every_replicate():
    problem = _problem()
    problem_dict = {
        "name": problem.name,
        "dimension": problem.dimension,
        "optimal": None,
        "coordinates": [],
        "category": "tiny",
        "source": "test",
        "is_time_matrix": False,
        "time_matrix": None,
        "problem_type": "atsp",
        "dist_matrix": problem.dist_matrix,
    }
    params = _params()
    params.update({"max_iterations": 1, "pack_size": 4})
    aggregate = _evaluate_param_combo(
        (problem_dict, "Core-GWO-TSP-Pure", "Core-GWO-TSP-Pure", params, 9, 2)
    )

    required = {
        "algorithm_id",
        "algorithm_family",
        "variant",
        "seed",
        "seed_group",
        "objective_evaluations",
        "evaluation_budget",
        "budget_terminated",
        "initialization_policy",
        "termination_policy",
        "execution_backend",
        "polish_policy",
    }
    assert len(aggregate["per_run_fairness"]) == 2
    assert all(required == set(item) for item in aggregate["per_run_fairness"])
    assert len({item["seed"] for item in aggregate["per_run_fairness"]}) == 2
