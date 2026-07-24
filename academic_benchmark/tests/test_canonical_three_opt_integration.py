from __future__ import annotations

import inspect
import sys

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401 - register executors
from uniride_core.algorithms.three_opt import improve_three_opt
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.models import ProblemInstance


def test_three_opt_integration_has_no_bildiri_import_ownership():
    source = inspect.getsource(sys.modules[__name__])
    assert "academic_benchmark." + "bildiri2026" not in source


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


def test_canonical_three_opt_preserves_directed_cost_and_fixed_cycle_anchor():
    matrix = _asymmetric_matrix()
    result = improve_three_opt(
        list(range(6)), matrix, max_iterations=20, window=12
    )
    expected = sum(
        matrix[node][result.route[(idx + 1) % len(result.route)]]
        for idx, node in enumerate(result.route)
    )

    assert set(result.route) == set(range(6))
    assert result.cost == pytest.approx(expected)
    assert result.mode == "directed_atsp"
    assert result.evaluations > 0


def test_canonical_three_opt_is_deterministic_for_same_matrix():
    matrix = _asymmetric_matrix()
    first = improve_three_opt(list(range(6)), matrix, max_iterations=20, window=12)
    second = improve_three_opt(list(range(6)), matrix, max_iterations=20, window=12)

    assert first == second
