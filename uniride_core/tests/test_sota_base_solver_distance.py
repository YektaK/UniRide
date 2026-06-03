import math

from uniride_core.algorithms.distance import euclidean_distance_2d
from uniride_core.algorithms.sota_tsp.base_solver import BaseTSPSolver


class _DummySolver(BaseTSPSolver):
    def _solve(self):
        raise AssertionError("not used")


def test_base_solver_euclidean_distance_uses_canonical_raw_helper():
    p1 = (0.0, 0.0)
    p2 = (1.0, 1.0)

    assert _DummySolver.euclidean_distance(p1, p2) == euclidean_distance_2d(p1, p2)
    assert math.isclose(_DummySolver.euclidean_distance(p1, p2), math.sqrt(2.0))


def test_base_solver_euclidean_distance_delegates_to_canonical_helper(monkeypatch):
    calls = []

    def fake_distance(p1, p2):
        calls.append((p1, p2))
        return 123.5

    monkeypatch.setattr(
        "uniride_core.algorithms.sota_tsp.base_solver.euclidean_distance_2d",
        fake_distance,
    )

    assert _DummySolver.euclidean_distance((2.0, 3.0), (5.0, 7.0)) == 123.5
    assert calls == [((2.0, 3.0), (5.0, 7.0))]


def test_base_solver_build_distance_matrix_uses_raw_euclidean_distance():
    solver = _DummySolver("dummy")

    matrix = solver._build_dist_matrix([(0.0, 0.0), (1.0, 1.0)])

    assert matrix[0][0] == 0.0
    assert matrix[1][1] == 0.0
    assert math.isclose(matrix[0][1], math.sqrt(2.0))
    assert math.isclose(matrix[1][0], math.sqrt(2.0))
