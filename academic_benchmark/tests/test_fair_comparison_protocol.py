"""Regression tests for the academic TSP fair-comparison contract."""

from dataclasses import asdict

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import (
    FairComparisonManifest,
    FairRunResult,
    FairnessValidationError,
)
from uniride_core.models import ProblemInstance


FAIR_ALGORITHMS = (
    "Core-GWO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Pure",
    "Core-HHO-TSP-Memetic-2opt",
    "Numba-2-opt",
    "Numba-3-opt-bounded",
)


def _symmetric_problem() -> ProblemInstance:
    matrix = [
        [0.0 if i == j else float(abs(i - j) + 1) for j in range(8)]
        for i in range(8)
    ]
    return ProblemInstance(
        name="fair-symmetric-8",
        dimension=8,
        coordinates=[],
        problem_type="tsp",
        dist_matrix=matrix,
    )


def _asymmetric_problem() -> ProblemInstance:
    matrix = [
        [0.0 if i == j else float((i + 1) * 11 + (j + 1) * 3) for j in range(8)]
        for i in range(8)
    ]
    return ProblemInstance(
        name="fair-directed-8",
        dimension=8,
        coordinates=[],
        problem_type="atsp",
        dist_matrix=matrix,
    )


def _params(budget: int = 500) -> dict:
    return {
        "fair_comparison": {"evaluation_budget": budget, "base_seed": 77},
        "max_iterations": 2,
        "pack_size": 6,
        "hawks": 6,
        "polish_iters": 1,
        "final_polish_iters": 1,
        "dive_count": 2,
    }


def _run(algorithm: str, *, problem=None, run_idx: int = 0, supplied_seed: int = 999):
    executor = AlgorithmRegistry.get_executor(algorithm)
    return executor(
        problem or _symmetric_problem(),
        _params(),
        seed=supplied_seed,
        run_idx=run_idx,
    )


def _closed_cost(result, matrix) -> float:
    route = [node - 1 for node in result.tour]
    return sum(
        float(matrix[node][route[(idx + 1) % len(route)]])
        for idx, node in enumerate(route)
    )


def test_explicit_pure_and_memetic_variants_are_registered():
    assert set(FAIR_ALGORITHMS).issubset(AlgorithmRegistry.list_algorithms())


def test_all_algorithms_share_problem_replicate_seed_group():
    results = [_run(name, run_idx=3, supplied_seed=10_000 + idx) for idx, name in enumerate(FAIR_ALGORITHMS)]

    assert len({result.seed for result in results}) == 1
    assert len({result.seed_group for result in results}) == 1
    assert all(result.seed != 10_000 + idx for idx, result in enumerate(results))


@pytest.mark.parametrize("algorithm", FAIR_ALGORITHMS)
def test_fixed_seed_evaluation_counts_are_positive_deterministic_and_bounded(algorithm):
    first = _run(algorithm)
    second = _run(algorithm)

    assert first.evaluations == first.objective_evaluations
    assert first.evaluations == second.evaluations
    assert 0 < first.evaluations <= first.evaluation_budget == 500
    assert first.tour_cost == second.tour_cost
    assert set(first.tour) == set(range(1, 9))


@pytest.mark.parametrize(
    ("algorithm", "variant", "polished"),
    [
        ("Core-GWO-TSP-Pure", "pure", False),
        ("Core-GWO-TSP-Memetic-2opt", "memetic_2opt", True),
        ("Core-HHO-TSP-Pure", "pure", False),
        ("Core-HHO-TSP-Memetic-2opt", "memetic_2opt", True),
    ],
)
def test_gwo_hho_variant_and_polish_metadata_are_truthful(algorithm, variant, polished):
    result = _run(algorithm)

    assert result.algorithm_id == result.algorithm == algorithm
    assert result.variant == variant
    assert result.polish_policy["enabled"] is polished
    assert result.polish_policy["initial"] is polished
    assert result.polish_policy["periodic"] is polished
    assert result.polish_policy["final"] is polished


@pytest.mark.parametrize("algorithm", ("Numba-2-opt", "Numba-3-opt-bounded"))
def test_legacy_executor_never_emits_legacy_identity(algorithm):
    result = AlgorithmRegistry.get_executor(algorithm)(
        _symmetric_problem(),
        {"max_iterations": 1},
        seed=123,
        run_idx=0,
    )

    assert result.algorithm == algorithm
    assert result.algorithm != "legacy"


def test_directed_three_opt_reports_independently_recomputed_closed_cost():
    problem = _asymmetric_problem()
    result = _run("Numba-3-opt-bounded", problem=problem)

    assert result.algorithm_family == "3-opt"
    assert result.matrix_kind == "distance"
    assert result.tour_cost == pytest.approx(_closed_cost(result, problem.dist_matrix))


def test_manifest_rejects_incomplete_fairness_metadata():
    manifest = FairComparisonManifest(evaluation_budget=100, base_seed=77)
    seed = manifest.paired_seed("incomplete", 0)
    incomplete = FairRunResult(
        problem="incomplete",
        algorithm="Numba-2-opt",
        run=0,
        seed=seed,
        dimension=4,
        optimal=None,
        tour_cost=4.0,
        gap_pct=None,
        elapsed_sec=0.0,
        evaluations=1,
        objective_evaluations=1,
        evaluation_budget=100,
    )

    with pytest.raises(FairnessValidationError, match="missing fairness field"):
        manifest.validate_result(incomplete)


def test_fair_result_serialization_contains_complete_contract():
    result = _run("Core-GWO-TSP-Pure")
    serialized = asdict(result)

    required = set(FairComparisonManifest.REQUIRED_RESULT_FIELDS)
    assert required.issubset(serialized)
    assert all(serialized[field] not in (None, "", {}) for field in required)


@pytest.mark.parametrize(
    "algorithm",
    ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt"),
)
def test_atomic_population_initialization_rejects_too_small_budget(algorithm):
    params = _params(budget=5)
    with pytest.raises(ValueError, match="atomic population initialization"):
        AlgorithmRegistry.get_executor(algorithm)(
            _symmetric_problem(),
            params,
            seed=123,
            run_idx=0,
        )
