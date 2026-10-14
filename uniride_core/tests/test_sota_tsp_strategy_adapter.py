import itertools
import logging

import pytest

from uniride_core.adapters.sota_tsp_strategy_adapter import (
    GREEDY_FALLBACK_ALGORITHM,
    SOTA_DURATION_SCALE,
    build_solver_matrix,
    greedy_student_order,
    solve_student_order_with_sota_tsp,
)

DEPOT = "D"
STUDENTS = ["A", "B", "C"]

# Directed, deliberately asymmetric durations (minutes) between the depot and
# three students. This is the objective the response reports and certifies.
_DURATIONS = {
    ("D", "A"): 3.0, ("D", "B"): 1.0, ("D", "C"): 4.0,
    ("A", "D"): 2.0, ("B", "D"): 9.0, ("C", "D"): 1.0,
    ("A", "B"): 5.0, ("B", "A"): 1.0,
    ("A", "C"): 1.0, ("C", "A"): 6.0,
    ("B", "C"): 2.0, ("C", "B"): 7.0,
}


def _duration(origin, destination):
    return _DURATIONS[(origin, destination)]


def _cycle_cost(order):
    """Reported cost: depot -> students -> depot over directed durations."""
    path = [DEPOT, *order, DEPOT]
    return sum(_duration(a, b) for a, b in zip(path, path[1:]))


def _best_order():
    return min(itertools.permutations(STUDENTS), key=lambda o: _cycle_cost(list(o)))


class _BruteForceSolver:
    """Exact solver over whatever matrix it receives (cycle over all indices)."""

    seen_matrix = None

    def __init__(self, config):
        self.config = config

    def solve_with_matrix(self, matrix):
        type(self).seen_matrix = [list(row) for row in matrix]
        n = len(matrix)

        def cost(tour):
            return sum(matrix[tour[i]][tour[(i + 1) % n]] for i in range(n))

        best = min(
            ([0, *perm] for perm in itertools.permutations(range(1, n))),
            key=cost,
        )
        return type("R", (), {"tour": best})()


class _FixedTourSolver:
    tour = [0, 2, 1, 3]

    def __init__(self, config):
        pass

    def solve_with_matrix(self, matrix):
        return type("R", (), {"tour": list(type(self).tour)})()


class _FailingSolver:
    def __init__(self, config):
        self.config = config

    def solve_with_matrix(self, matrix):
        raise RuntimeError("solver failed: secret-internal-detail")


def test_solver_matrix_is_depot_anchored_directed_duration_scaled():
    matrix = build_solver_matrix(STUDENTS, DEPOT, _duration)
    nodes = [DEPOT, *STUDENTS]

    assert len(matrix) == 4 and all(len(row) == 4 for row in matrix)
    for i, origin in enumerate(nodes):
        for j, destination in enumerate(nodes):
            if i == j:
                assert matrix[i][j] == 0.0
            else:
                assert matrix[i][j] == pytest.approx(
                    _duration(origin, destination) * SOTA_DURATION_SCALE
                )
    # direction is preserved (asymmetric arcs are not symmetrised)
    assert matrix[1][2] != matrix[2][1]


def test_solver_matrix_keeps_zero_duration_arcs_between_distinct_nodes():
    zero = lambda a, b: 0.0
    matrix = build_solver_matrix(["A", "B"], DEPOT, zero)
    assert all(value == 0.0 for row in matrix for value in row)


def test_objective_parity_solver_optimum_equals_reported_duration_optimum():
    outcome = solve_student_order_with_sota_tsp(
        STUDENTS, DEPOT, _duration, _BruteForceSolver, object()
    )

    assert outcome.fallback_reason is None
    assert sorted(outcome.order) == sorted(STUDENTS)
    assert _cycle_cost(outcome.order) == pytest.approx(_cycle_cost(list(_best_order())))
    # the matrix the solver optimised, read back through the solver's own
    # cycle cost, equals the reported cost times the documented scale
    matrix = _BruteForceSolver.seen_matrix
    idx = {name: i for i, name in enumerate([DEPOT, *STUDENTS])}
    path = [DEPOT, *outcome.order, DEPOT]
    solver_cost = sum(matrix[idx[a]][idx[b]] for a, b in zip(path, path[1:]))
    assert solver_cost == pytest.approx(_cycle_cost(outcome.order) * SOTA_DURATION_SCALE)


def test_tour_is_rotated_to_start_at_depot_and_depot_is_dropped():
    _FixedTourSolver.tour = [2, 0, 1, 3]  # cycle 2 -> D -> A -> C -> back to 2
    outcome = solve_student_order_with_sota_tsp(
        STUDENTS, DEPOT, _duration, _FixedTourSolver, object()
    )

    assert outcome.fallback_reason is None
    assert outcome.order == ["A", "C", "B"]


@pytest.mark.parametrize("bad_tour", [[0, 1, 2], [0, 1, 1, 2], [0, 1, 2, 9]])
def test_invalid_solver_tour_is_labelled_fallback(bad_tour):
    _FixedTourSolver.tour = bad_tour
    outcome = solve_student_order_with_sota_tsp(
        STUDENTS, DEPOT, _duration, _FixedTourSolver, object()
    )

    assert outcome.fallback_reason == "invalid_solver_tour"
    assert outcome.order == greedy_student_order(STUDENTS, DEPOT, _duration)


def test_solver_exception_is_labelled_fallback_and_logged_not_returned(caplog):
    with caplog.at_level(logging.ERROR):
        outcome = solve_student_order_with_sota_tsp(
            STUDENTS, DEPOT, _duration, _FailingSolver, object()
        )

    assert outcome.fallback_reason == "solver_error"
    assert outcome.order == greedy_student_order(STUDENTS, DEPOT, _duration)
    assert "secret-internal-detail" not in repr(outcome)
    assert "secret-internal-detail" in caplog.text  # logged server-side
    assert GREEDY_FALLBACK_ALGORITHM == "greedy_fallback"


def test_empty_students_returns_empty_order_without_fallback():
    outcome = solve_student_order_with_sota_tsp([], DEPOT, _duration, _FailingSolver, object())
    assert outcome.order == [] and outcome.fallback_reason is None


def test_greedy_student_order_handles_empty_students():
    assert greedy_student_order([], "D", _duration) == []
