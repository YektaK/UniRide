"""Regression: Numba-2-opt and Numba-3-opt-bounded must execute on matrix-native inputs.

The legacy executor used to ignore ``problem.dist_matrix`` and fall back to
a TSPLIB DB lookup or coordinates-only path.  For synthetic test problems
with an empty ``coordinates`` list this produced a ``(0, 0)`` numpy matrix,
causing ``IndexError: index 0 is out of bounds for axis 0 with size 0``.

This module verifies both registry entries accept a ``ProblemInstance`` that
carries an explicit ``dist_matrix`` and no coordinates, and that the reported
objective cost equals an independent closed-cycle recomputation.
"""
from __future__ import annotations

import math

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401 – trigger registration
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.models import ProblemInstance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _closed_tour_cost(tour: list[int], matrix: list[list]) -> float:
    """Sum every edge of *tour* including last→first (closed cycle)."""
    n = len(tour)
    total = 0.0
    for k in range(n):
        a = tour[k] - 1   # tour is 1-indexed
        b = tour[(k + 1) % n] - 1
        total += float(matrix[a][b])
    return total


def _assert_closed_tour_cost(result, matrix: list[list]) -> None:
    """Validate the tour is a complete 1-indexed permutation and its cost
    matches an independent closed-cycle sum over *matrix*."""
    dim = len(matrix)
    tour = result.tour

    assert tour is not None, "tour must not be None"
    assert len(tour) == dim, f"tour length {len(tour)} != dimension {dim}"
    assert set(tour) == set(range(1, dim + 1)), (
        f"tour {tour} is not a permutation of 1..{dim}"
    )

    expected = _closed_tour_cost(tour, matrix)
    assert result.tour_cost == pytest.approx(expected, abs=0.01), (
        f"tour_cost {result.tour_cost} != independent recomputation {expected}"
    )


def _asymmetric_8_problem() -> ProblemInstance:
    """8-node *genuinely asymmetric* distance matrix.

    Forward and reverse edges carry different costs so the solver cannot
    silently treat the problem as symmetric and still pass.
    """
    n = 8
    matrix: list[list[int]] = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            fwd = int(math.hypot(i * 3.1, j * 2.7) + 0.5) + i
            rev = int(math.hypot(j * 2.7, i * 3.1) + 0.5) + j
            matrix[i][j] = fwd
            matrix[j][i] = rev
    return ProblemInstance(
        name="n8_asym_matrix_only",
        dimension=n,
        coordinates=[],
        optimal=100.0,
        category="tiny",
        problem_type="tsp",
        dist_matrix=matrix,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algorithm", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_numba_registry_entry_works_on_dist_matrix_problem(algorithm):
    """Executor must complete on an asymmetric dist_matrix and report a
    correct closed-cycle cost."""
    problem = _asymmetric_8_problem()
    executor = AlgorithmRegistry.get_executor(algorithm)

    result = executor(problem, {"max_iterations": 50}, seed=7, run_idx=0)

    _assert_closed_tour_cost(result, problem.dist_matrix)
    assert result.problem_type == "tsp"


@pytest.mark.parametrize("algorithm", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_numba_registry_entry_handles_time_matrix(algorithm):
    """Executor must work on the time_matrix branch with correct cost."""
    matrix = [
        [0, 2, 5, 3],
        [2, 0, 4, 6],
        [5, 4, 0, 1],
        [3, 6, 1, 0],
    ]
    problem = ProblemInstance(
        name="tm_4",
        dimension=4,
        coordinates=[],
        optimal=10.0,
        category="tiny",
        problem_type="tsp",
        is_time_matrix=True,
        time_matrix=matrix,
    )
    executor = AlgorithmRegistry.get_executor(algorithm)

    result = executor(problem, {"max_iterations": 10}, seed=42, run_idx=0)

    _assert_closed_tour_cost(result, matrix)


@pytest.mark.parametrize("algorithm", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_numba_registry_entry_on_coord_only_problem(algorithm):
    """Executor must still work via the coordinates fallback."""
    executor = AlgorithmRegistry.get_executor(algorithm)

    problem = ProblemInstance(
        name="coord_4",
        dimension=4,
        coordinates=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        optimal=4.0,
        category="tiny",
        problem_type="tsp",
    )

    result = executor(problem, {"max_iterations": 10}, seed=99, run_idx=0)

    assert result.tour_cost > 0
    assert result.tour is not None
    assert len(result.tour) == 4
    assert set(result.tour) == {1, 2, 3, 4}
