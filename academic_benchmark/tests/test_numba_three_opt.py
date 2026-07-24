import inspect
import sys

import pytest

from uniride_core.algorithms import numba_accel


def test_numba_three_opt_has_no_bildiri_import_ownership():
    source = inspect.getsource(sys.modules[__name__])
    assert "academic_benchmark." + "bildiri2026" not in source
    assert numba_accel.__name__ == "uniride_core.algorithms.numba_accel"


@pytest.mark.skipif(not numba_accel.NUMBA_AVAILABLE, reason="Numba not available")
def test_nb_three_opt_improves_simple_instance():
    n = 6
    high = 10.0
    low = 1.0

    dm = [[high for _ in range(n)] for _ in range(n)]
    for i in range(n):
        dm[i][i] = 0.0
    best_route = [0, 1, 2, 3, 4, 5]
    for i in range(n - 1):
        dm[best_route[i]][best_route[i + 1]] = low
    dm[best_route[-1]][best_route[0]] = low

    start_tour = [0, 2, 1, 3, 4, 5]

    def tour_cost(tour):
        return sum(dm[tour[i]][tour[(i + 1) % n]] for i in range(n))

    start_len = tour_cost(start_tour)
    improved_tour, improved_len = numba_accel.nb_three_opt(start_tour, dm, 50, False)

    assert improved_len < start_len
    assert sorted(improved_tour) == sorted(start_tour)
