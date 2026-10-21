"""M18 follow-up: the other executors must also report unrounded cost.

Covers `_make_core_tsp_executor`, `_make_matrix_tsp_executor` (FCM engines) and
the time-matrix branch of the legacy executor. The execution gateway recomputes
the directed closed-cycle cost and accepts only 1e-9, so a reported cost rounded
to 2 decimals is rejected on fractional matrices. Integer instances must keep
identical values.
"""
from __future__ import annotations

import pytest

from academic_benchmark.core import registry_setup
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.algorithms.engine_factory import MATRIX_LEGACY_TSP_SOLVERS
from uniride_core.models import ProblemInstance


def _fractional_matrix(n: int = 7) -> list[list[float]]:
    return [
        [
            0.0 if i == j else ((i + 1) * 1.1237 + (j + 1) * 0.3141 + (i * j % 5) * 0.00713)
            for j in range(n)
        ]
        for i in range(n)
    ]


def _integer_matrix(n: int = 7) -> list[list[int]]:
    return [
        [0 if i == j else (i + 1) * 11 + (j + 1) * 3 + (i * j % 5) for j in range(n)]
        for i in range(n)
    ]


def _problem(matrix, *, time_matrix: bool, name: str = "m18-other") -> ProblemInstance:
    kwargs = (
        {"is_time_matrix": True, "time_matrix": matrix}
        if time_matrix
        else {"dist_matrix": matrix}
    )
    return ProblemInstance(
        name=name,
        dimension=len(matrix),
        coordinates=[],
        optimal=1.0,
        problem_type="atsp",
        **kwargs,
    )


def _cycle_cost(tour, matrix) -> float:
    route = [node - 1 for node in tour]
    return sum(matrix[route[i]][route[(i + 1) % len(route)]] for i in range(len(route)))


def _assert_exact(result, matrix) -> float:
    independent = _cycle_cost(result.tour, matrix)
    assert abs(result.tour_cost - independent) <= 1e-9
    assert abs(result.objective_cost - independent) <= 1e-9
    return independent


# -- Group A: _make_core_tsp_executor (registry_setup.py:129, 134) -----------

def test_core_tsp_executor_reports_unrounded_cost_with_deterministic_solver() -> None:
    def identity_solver(waypoints, duration_func, rng, params):
        route = list(waypoints)
        return route, duration_func(route)

    executor = registry_setup._make_core_tsp_executor("Core-Identity-Fixture", identity_solver)
    matrix = _fractional_matrix()
    result = executor(_problem(matrix, time_matrix=False), {}, 3, 0)
    independent = _assert_exact(result, matrix)
    assert abs(independent - round(independent, 2)) > 1e-6  # fixture is fractional


@pytest.mark.parametrize("algorithm", ["Matrix-GA-TSP-legacy", "Matrix-PSO-TSP-legacy"])
def test_core_tsp_executor_real_solvers_report_unrounded_cost(algorithm: str) -> None:
    executor = registry_setup._make_core_tsp_executor(algorithm, MATRIX_LEGACY_TSP_SOLVERS[algorithm])
    matrix = _fractional_matrix()
    result = executor(_problem(matrix, time_matrix=False), {"max_iterations": 3}, 3, 0)
    _assert_exact(result, matrix)


def test_core_tsp_executor_integer_instance_values_unchanged() -> None:
    def identity_solver(waypoints, duration_func, rng, params):
        route = list(waypoints)
        return route, duration_func(route)

    executor = registry_setup._make_core_tsp_executor("Core-Identity-Fixture", identity_solver)
    matrix = _integer_matrix()
    result = executor(_problem(matrix, time_matrix=False), {}, 3, 0)
    expected = float(_cycle_cost(result.tour, matrix))
    assert result.tour_cost == expected == round(expected, 2)
    assert result.objective_cost == expected


# -- Group B: _make_matrix_tsp_executor (registry_setup.py:166, 171) ---------

class _FakeResult:
    def __init__(self, tour, cost):
        self.tour = tour
        self.tour_length = cost


class _FakeEngine:
    def solve_problem(self, routing_problem, config=None, seed=None):
        data = routing_problem.matrix.values
        tour = list(range(len(data)))
        cost = sum(float(data[tour[i]][tour[(i + 1) % len(tour)]]) for i in range(len(tour)))
        return _FakeResult(tour, cost)


def test_matrix_tsp_executor_reports_unrounded_cost(monkeypatch) -> None:
    monkeypatch.setattr(registry_setup, "create_matrix_engine", lambda name: _FakeEngine())
    executor = registry_setup._make_matrix_tsp_executor("FCM-Fixture-TSP")
    matrix = _fractional_matrix()
    result = executor(_problem(matrix, time_matrix=False), {}, 3, 0)
    independent = _assert_exact(result, matrix)
    assert abs(independent - round(independent, 2)) > 1e-6


def test_matrix_tsp_executor_integer_instance_values_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(registry_setup, "create_matrix_engine", lambda name: _FakeEngine())
    executor = registry_setup._make_matrix_tsp_executor("FCM-Fixture-TSP")
    matrix = _integer_matrix()
    result = executor(_problem(matrix, time_matrix=False), {}, 3, 0)
    expected = float(_cycle_cost(result.tour, matrix))
    assert result.tour_cost == expected == round(expected, 2)
    assert result.objective_cost == expected


# -- Group C: legacy executor time-matrix branch (registry_setup.py:431) -----

@pytest.mark.parametrize("algorithm", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_legacy_executor_time_matrix_reports_unrounded_cost(algorithm: str) -> None:
    matrix = _fractional_matrix()
    result = AlgorithmRegistry.get_executor(algorithm)(
        _problem(matrix, time_matrix=True), {"max_iterations": 20}, 7, 0
    )
    independent = _assert_exact(result, matrix)
    assert abs(independent - round(independent, 2)) > 1e-6


@pytest.mark.parametrize("algorithm", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_legacy_executor_integer_instances_values_unchanged(algorithm: str) -> None:
    matrix = _integer_matrix()
    executor = AlgorithmRegistry.get_executor(algorithm)
    # Distance-matrix branch (int() branch, untouched): exact integer total.
    dist = executor(_problem(matrix, time_matrix=False), {"max_iterations": 20}, 7, 0)
    assert dist.tour_cost == _cycle_cost(dist.tour, matrix)
    assert isinstance(dist.tour_cost, int)
    # Time-matrix branch on integer data: equal to the 2-dp value it used to report.
    timed = executor(_problem(matrix, time_matrix=True), {"max_iterations": 20}, 7, 0)
    expected = float(_cycle_cost(timed.tour, matrix))
    assert timed.tour_cost == expected == round(expected, 2)
