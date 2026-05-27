from uniride_core.adapters.sota_tsp_strategy_adapter import (
    build_solver_matrix,
    greedy_student_order,
    solve_student_order_with_sota_tsp,
)


class _Result:
    tour = [1, 0, 2]


class _FakeSolver:
    def __init__(self, config):
        self.config = config

    def solve_with_matrix(self, matrix):
        return _Result()


class _FailingSolver:
    def __init__(self, config):
        self.config = config

    def solve_with_matrix(self, matrix):
        raise RuntimeError("solver failed")


def _distance(origin, destination):
    values = {
        ("A", "B"): 2.0,
        ("A", "C"): 4.0,
        ("B", "A"): 2.0,
        ("B", "C"): 1.0,
        ("C", "A"): 4.0,
        ("C", "B"): 1.0,
    }
    return values[(origin, destination)]


def _duration(origin, destination):
    values = {
        ("D", "A"): 3.0,
        ("D", "B"): 1.0,
        ("D", "C"): 4.0,
        ("B", "A"): 1.0,
        ("B", "C"): 2.0,
        ("A", "C"): 1.0,
    }
    return values[(origin, destination)]


def test_build_solver_matrix_uses_meter_scaled_distances():
    matrix = build_solver_matrix(["A", "B", "C"], _distance)

    assert matrix == [
        [0.0, 2000.0, 4000.0],
        [2000.0, 0.0, 1000.0],
        [4000.0, 1000.0, 0.0],
    ]


def test_solve_student_order_with_sota_solver_maps_tour_indices_to_ids():
    order = solve_student_order_with_sota_tsp(["A", "B", "C"], "D", _distance, _duration, _FakeSolver, object())

    assert order == ["B", "A", "C"]


def test_solve_student_order_with_sota_solver_falls_back_to_greedy():
    order = solve_student_order_with_sota_tsp(["A", "B", "C"], "D", _distance, _duration, _FailingSolver, object())

    assert order == ["B", "A", "C"]


def test_greedy_student_order_handles_empty_students():
    assert greedy_student_order([], "D", _duration) == []
