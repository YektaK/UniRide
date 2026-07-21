from __future__ import annotations

import pytest

from academic_benchmark.bildiri2026.core.three_opt import ThreeOptSolver
from academic_benchmark.core import registry_setup  # noqa: F401 - register executors
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.models import ProblemInstance


def _asymmetric_matrix() -> list[list[float]]:
    return [
        [0, 7, 2, 9, 8, 6],
        [3, 0, 8, 2, 7, 9],
        [9, 4, 0, 7, 2, 8],
        [6, 9, 3, 0, 8, 2],
        [2, 7, 9, 4, 0, 6],
        [8, 2, 6, 9, 3, 0],
    ]


def _closed_cost(one_indexed_tour, matrix):
    return sum(
        matrix[node - 1][one_indexed_tour[(idx + 1) % len(one_indexed_tour)] - 1]
        for idx, node in enumerate(one_indexed_tour)
    )


def test_registry_three_opt_is_deterministic_and_preserves_directed_cost():
    matrix = _asymmetric_matrix()
    problem = ProblemInstance(
        name="canonical_atsp_6",
        dimension=6,
        coordinates=[],
        problem_type="atsp",
        dist_matrix=matrix,
    )
    executor = AlgorithmRegistry.get_executor("Numba-3-opt-bounded")

    first = executor(problem, {"max_iterations": 20}, seed=41, run_idx=0)
    second = executor(problem, {"max_iterations": 20}, seed=41, run_idx=1)

    assert first.tour == second.tour
    assert first.tour_cost == second.tour_cost
    assert set(first.tour) == set(range(1, 7))
    assert first.tour_cost == pytest.approx(_closed_cost(first.tour, matrix))


def test_bildiri_solver_uses_canonical_directed_mode_and_fixed_cycle_anchor():
    matrix = _asymmetric_matrix()
    solver = ThreeOptSolver(max_iterations=20, window=12, random_seed=41)

    result = solver.solve_with_matrix(matrix)
    full_tour = [0] + result.tour
    expected = sum(
        matrix[node][full_tour[(idx + 1) % len(full_tour)]]
        for idx, node in enumerate(full_tour)
    )

    assert set(full_tour) == set(range(6))
    assert result.tour_length == pytest.approx(expected)
    assert result.params["execution_backend"] == "canonical_python"
    assert result.params["neighborhood_mode"] == "directed_atsp"
    assert result.extra_stats["evaluations"] > 0


def test_bildiri_solver_is_deterministic_for_same_seed_and_matrix():
    matrix = _asymmetric_matrix()
    first = ThreeOptSolver(max_iterations=20, random_seed=73).solve_with_matrix(matrix)
    second = ThreeOptSolver(max_iterations=20, random_seed=73).solve_with_matrix(matrix)

    assert first.tour == second.tour
    assert first.tour_length == second.tour_length
    assert first.iterations == second.iterations
    assert first.extra_stats == second.extra_stats
