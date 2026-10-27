"""MT6F-07 (audit L10-f): pin the contract of the Numba-module 3-opt wrapper.

These tests document existing behaviour (OQ-F5 a, no behaviour change); the only
new behaviour is the clearer duplicate-code error message.

  * location codes must be unique (duplicates raise ValueError naming them);
  * with a prebuilt matrix the result is exactly improve_three_opt on that matrix;
  * without one, the fallback matrix duration_func([a, b]) - duration_func([a])
    optimises the closed cycle over the waypoints; depot terms cancel.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from uniride_core.algorithms import local_search_numba as lsn
from uniride_core.algorithms.local_search_numba import ThreeOptLocalSearch
from uniride_core.algorithms.numba_utils import create_np_duration_func
from uniride_core.algorithms.three_opt import improve_three_opt

N = 9


def _points(seed: int):
    rng = np.random.default_rng(seed)
    return rng.random((N + 1, 2)) * 100.0  # index 0 is the depot


def _euclid(pts) -> np.ndarray:
    return np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))


def _closed_cost(route, cost) -> float:
    return float(sum(cost(route[k], route[(k + 1) % len(route)]) for k in range(len(route))))


def test_duplicate_location_codes_raise_value_error_naming_them():
    matrix = _euclid(_points(1))[1:, 1:]
    locs = [f"L{i}" for i in range(1, N + 1)]
    func = create_np_duration_func(matrix, locs)
    route = locs[:6] + ["L2", "L5", "L5"]  # L2 and L5 repeated

    with pytest.raises(ValueError) as excinfo:
        ThreeOptLocalSearch().improve(route, func)

    message = str(excinfo.value)
    assert "L2" in message and "L5" in message
    assert "L1" not in message and "L3" not in message  # only the duplicates are named


def test_unique_codes_do_not_raise():
    matrix = _euclid(_points(2))[1:, 1:]
    locs = [f"L{i}" for i in range(1, N + 1)]
    func = create_np_duration_func(matrix, locs)
    route, duration = ThreeOptLocalSearch().improve(locs, func)
    assert sorted(route) == sorted(locs)
    assert duration == pytest.approx(func(route))


def test_prebuilt_matrix_result_equals_improve_three_opt_on_that_matrix():
    rng = np.random.default_rng(3)
    matrix = rng.random((N, N)) * 100.0  # asymmetric: directed 3-opt
    np.fill_diagonal(matrix, 0.0)
    locs = [f"L{i}" for i in range(N)]
    func = create_np_duration_func(matrix, locs)
    route = locs[:]
    random.Random(4).shuffle(route)

    got_route, got_duration = ThreeOptLocalSearch(max_iterations=50).improve(route, func)

    # Independent expectation: the route's own sub-matrix, canonical 3-opt, mapped back.
    label = {loc: i for i, loc in enumerate(locs)}
    ids = [label[loc] for loc in route]
    sub = matrix[np.ix_(ids, ids)].tolist()
    expected = improve_three_opt(list(range(N)), sub, max_iterations=50, window=12)
    expected_route = [route[i] for i in expected.route]

    assert got_route == expected_route
    got_ids = [label[loc] for loc in got_route]
    assert expected.cost == pytest.approx(_closed_cost(got_ids, lambda a, b: matrix[a, b]))
    assert got_duration == pytest.approx(func(got_route))


def _depot_costed_func(pts):
    """Plain duration_func (no prebuilt-matrix attributes): depot -> route -> depot."""
    dist = _euclid(pts)
    calls = {"n": 0}

    def duration(route):
        calls["n"] += 1
        ids = [int(loc[1:]) for loc in route]
        total = dist[0, ids[0]] + dist[ids[-1], 0]
        total += sum(dist[ids[k], ids[k + 1]] for k in range(len(ids) - 1))
        return float(total)

    return duration, dist


def test_fallback_matrix_cycle_equals_closed_waypoint_cycle_despite_depot_costs():
    pts = _points(5)
    duration, dist = _depot_costed_func(pts)
    locs = [f"L{i}" for i in range(1, N + 1)]

    index_map, matrix, unique_locs = lsn._build_or_get_dist_matrix(locs, duration)

    # Entries carry depot terms (matrix is asymmetric even though dist is symmetric)...
    assert not np.allclose(matrix, matrix.T)
    # ...but they cancel in the sum over any closed cycle.
    rng = random.Random(6)
    for _ in range(10):
        perm = locs[:]
        rng.shuffle(perm)
        ids = [index_map[loc] for loc in perm]
        waypoint_cycle = _closed_cost([int(loc[1:]) for loc in perm], lambda a, b: dist[a, b])
        assert _closed_cost(ids, lambda a, b: matrix[a, b]) == pytest.approx(waypoint_cycle)


def test_fallback_improve_optimises_closed_waypoint_cycle():
    pts = _points(7)
    duration, dist = _depot_costed_func(pts)
    locs = [f"L{i}" for i in range(1, N + 1)]
    route = locs[:]
    random.Random(8).shuffle(route)

    def cycle(r):
        return _closed_cost([int(loc[1:]) for loc in r], lambda a, b: dist[a, b])

    got_route, got_duration = ThreeOptLocalSearch(max_iterations=50).improve(route, duration)

    assert sorted(got_route) == sorted(locs)
    assert cycle(got_route) <= cycle(route) + 1e-9
    assert got_duration == pytest.approx(duration(got_route))  # open depot path, not the cycle

    # Same matrix, same engine => same route (the wrapper adds nothing else).
    index_map, matrix, unique_locs = lsn._build_or_get_dist_matrix(route, duration)
    expected = improve_three_opt(
        [index_map[loc] for loc in route], matrix.tolist(), max_iterations=50, window=12
    )
    assert got_route == [unique_locs[i] for i in expected.route]

    # A local optimum of the 3-opt neighbourhood cannot be improved by a rerun.
    again, _ = ThreeOptLocalSearch(max_iterations=50).improve(got_route, duration)
    assert cycle(again) <= cycle(got_route) + 1e-9
