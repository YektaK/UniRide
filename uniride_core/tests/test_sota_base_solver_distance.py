import math

from uniride_core.algorithms.distance import euclidean_distance_2d, tsplib_euc_2d_distance
from uniride_core.algorithms.sota_tsp.base_solver import BaseTSPSolver


class _DummySolver(BaseTSPSolver):
    def _solve(self):
        raise AssertionError("not used")


def test_base_solver_euclidean_distance_uses_tsplib_nint_rounding():
    p1 = (0.0, 0.0)
    p2 = (1.0, 1.0)

    # SOTA base solver must use NINT rounding (int(x+0.5)) for TSPLIB compatibility,
    # matching tsplib_euc_2d_distance — NOT raw Euclidean.
    assert _DummySolver.euclidean_distance(p1, p2) == tsplib_euc_2d_distance(p1, p2)
    assert _DummySolver.euclidean_distance(p1, p2) == 1.0  # NINT(sqrt(2)) = 1


def test_base_solver_euclidean_distance_delegates_to_canonical_helper(monkeypatch):
    calls = []

    def fake_distance(p1, p2):
        calls.append((p1, p2))
        return 123.5  # raw distance

    monkeypatch.setattr(
        "uniride_core.algorithms.sota_tsp.base_solver.euclidean_distance_2d",
        fake_distance,
    )

    # NINT rounding: int(123.5 + 0.5) = int(124.0) = 124
    assert _DummySolver.euclidean_distance((2.0, 3.0), (5.0, 7.0)) == 124.0
    assert calls == [((2.0, 3.0), (5.0, 7.0))]


def test_base_solver_build_distance_matrix_uses_nint_euclidean_distance():
    solver = _DummySolver("dummy")

    matrix = solver._build_dist_matrix([(0.0, 0.0), (1.0, 1.0)])

    assert matrix[0][0] == 0.0
    assert matrix[1][1] == 0.0
    # NINT(sqrt(2)) = int(1.414... + 0.5) = int(1.914...) = 1
    assert matrix[0][1] == 1.0
    assert matrix[1][0] == 1.0
