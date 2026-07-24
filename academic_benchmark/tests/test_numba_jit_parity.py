"""Deterministic JIT-versus-Python parity for GWO/HHO matrix objectives.

The normal solver path retains a safe Python fallback when Numba cannot be
imported.  These tests deliberately skip only in that genuine no-JIT state.
When Numba is present, a compiled nopython kernel is mandatory and any
compilation, objective, route, or accounting mismatch is a test failure.
"""
from __future__ import annotations

from typing import Callable, Type

import numpy as np
import pytest

from academic_benchmark import fair_pilot
from academic_benchmark.fair_pilot import FairPilotError
from uniride_core.algorithms import numba_accel as _nb
from uniride_core.algorithms.tsp_matrix_metaheuristics.base_solver import BaseTSPSolver
from uniride_core.algorithms.tsp_matrix_metaheuristics.gwo_solver import GWOOptimizer
from uniride_core.algorithms.tsp_matrix_metaheuristics.hho_solver import HHOOptimizer
from uniride_core.algorithms import numba_accel as _canonical_nb


SolverType = Type[GWOOptimizer] | Type[HHOOptimizer]


def test_jit_parity_uses_canonical_gwo_hho_and_numba_helpers() -> None:
    assert _nb.__name__ == "uniride_core.algorithms.numba_accel"
    assert BaseTSPSolver.__module__.startswith(
        "uniride_core.algorithms.tsp_matrix_metaheuristics"
    )
    assert GWOOptimizer.__module__.startswith(
        "uniride_core.algorithms.tsp_matrix_metaheuristics"
    )
    assert HHOOptimizer.__module__.startswith(
        "uniride_core.algorithms.tsp_matrix_metaheuristics"
    )


def test_fair_pilot_preflight_uses_canonical_numba_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_canonical_nb, "NUMBA_AVAILABLE", False)

    with pytest.raises(FairPilotError, match="Numba is unavailable"):
        fair_pilot.preflight_numba_objective()


def _symmetric_matrix() -> list[list[float]]:
    return [
        [0, 7, 9, 11, 8, 10],
        [7, 0, 6, 5, 12, 9],
        [9, 6, 0, 4, 7, 13],
        [11, 5, 4, 0, 6, 8],
        [8, 12, 7, 6, 0, 5],
        [10, 9, 13, 8, 5, 0],
    ]


def _asymmetric_matrix() -> list[list[float]]:
    return [
        [0, 9, 4, 12, 7, 15],
        [3, 0, 11, 5, 14, 6],
        [13, 8, 0, 10, 2, 9],
        [6, 16, 3, 0, 8, 4],
        [11, 5, 17, 1, 0, 12],
        [7, 14, 6, 13, 3, 0],
    ]


def _independent_closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    return sum(
        float(matrix[node][tour[(index + 1) % len(tour)]])
        for index, node in enumerate(tour)
    )


def _require_working_jit() -> None:
    """Skip only before JIT is available; compilation problems must fail."""
    if not _nb.NUMBA_AVAILABLE:
        pytest.skip("Numba JIT unavailable: parity is not JIT-validated in this interpreter")

    matrix = np.ascontiguousarray(
        np.array([[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]]),
        dtype=np.float64,
    )
    route = np.ascontiguousarray(np.array([0, 1, 2], dtype=np.int64))
    assert _nb._calculate_tour_length_atsp_numba(route, matrix) == pytest.approx(9.0)
    assert _nb._calculate_tour_length_atsp_numba.nopython_signatures, (
        "Numba reported available but the matrix objective did not compile in nopython mode"
    )


def _solver_factory(solver_type: SolverType) -> Callable[[], BaseTSPSolver]:
    if solver_type is GWOOptimizer:
        return lambda: GWOOptimizer(
            pack_size=4,
            max_iterations=1,
            random_seed=1729,
            polish_enabled=False,
            evaluation_budget=100,
        )
    return lambda: HHOOptimizer(
        hawks=4,
        max_iterations=1,
        dive_count=0,
        random_seed=1729,
        polish_enabled=False,
        evaluation_budget=100,
    )


def _solve_matrix(factory: Callable[[], BaseTSPSolver], matrix: list[list[float]]):
    # recalculate=False keeps the observed result on _tour_length_fast rather
    # than overwriting it with the pure-Python matrix calculation after solve.
    return factory().solve_with_matrix(matrix, closed_tsp=True, recalculate=False)


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
@pytest.mark.parametrize(
    ("matrix_factory", "matrix_kind"),
    [(_symmetric_matrix, "symmetric-tsp"), (_asymmetric_matrix, "directed-atsp")],
)
def test_fixed_seed_matrix_objective_python_fallback_matches_jit(
    monkeypatch: pytest.MonkeyPatch,
    solver_type: SolverType,
    matrix_factory: Callable[[], list[list[float]]],
    matrix_kind: str,
) -> None:
    """GWO/HHO must produce identical matrix-search results across backends."""
    del matrix_kind  # Retained as the parametrized case identifier in pytest output.
    _require_working_jit()
    matrix = matrix_factory()
    factory = _solver_factory(solver_type)

    jit_result = _solve_matrix(factory, matrix)

    def _force_python_fallback(*_args, **_kwargs):
        raise RuntimeError("test-local forced Python objective fallback")

    monkeypatch.setattr(_nb, "_calculate_tour_length_atsp_numba", _force_python_fallback)
    python_result = _solve_matrix(factory, matrix)

    expected_nodes = set(range(len(matrix)))
    for result in (jit_result, python_result):
        assert len(result.tour) == len(matrix)
        assert set(result.tour) == expected_nodes
        assert result.tour_length == pytest.approx(
            _independent_closed_cost(result.tour, matrix), abs=0.0
        )
        assert result.extra_stats["objective_evaluations"] > 0
        assert result.extra_stats["budget_terminated"] is False

    assert jit_result.tour == python_result.tour
    assert jit_result.tour_length == pytest.approx(python_result.tour_length, abs=0.0)
    assert (
        jit_result.extra_stats["objective_evaluations"]
        == python_result.extra_stats["objective_evaluations"]
    )
