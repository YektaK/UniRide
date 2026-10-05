"""C2(b): OR-Tools integer scaling must never hide a ``max_route_duration`` breach."""

import pytest

from uniride_core.algorithms.ortools_cvrp_engine import (
    _scale_down,
    _scale_up,
    solve_ortools_cvrp,
)


def test_scaling_rounds_costs_up_and_limits_down():
    assert _scale_up(10.04, 10) == 101  # nearest-integer rounding gave 100
    assert _scale_up(0.7, 10) == 7  # float noise 7.000000000000001 must not become 8
    assert _scale_up(0.0, 10) == 0
    assert _scale_down(60, 10) == 600
    assert _scale_down(60.09, 10) == 600  # never allows more than the true limit
    assert _scale_down(0.3, 10) == 3  # 0.3 * 10 == 3.0000000000000004 stays 3


def _star_matrix(customers, arc):
    size = customers + 1
    return [[0.0 if i == j else arc for j in range(size)] for i in range(size)]


def test_true_route_duration_never_exceeds_the_limit():
    """Audit H.3: six 10.04 min arcs (60.24 true) under a 60 min limit."""
    pytest.importorskip("ortools")
    matrix = _star_matrix(5, 10.04)

    solution = solve_ortools_cvrp(
        time_matrix=matrix,
        disability_types=["So"] * 5,
        sw_capacity=4,
        so_capacity=5,
        max_route_duration=60,
        num_vehicles=5,
        time_limit_seconds=1,
        arc_rounding="conservative",
    )

    assert solution.success
    visited = sorted(i for route in solution.routes for i in route.customer_indices)
    assert visited == [0, 1, 2, 3, 4]
    for route in solution.routes:
        true_total = sum(matrix[s.from_index][s.to_index] for s in route.steps)
        assert true_total <= 60 + 1e-9, (true_total, route)
        # reported durations are the true arcs, not scaled-and-rounded ones
        assert [s.duration for s in route.steps] == [10.04] * len(route.steps)
        assert route.total_duration == pytest.approx(true_total, abs=0.005)


def test_default_is_the_historical_nearest_rounding_for_academic_callers():
    """Scientific parity: without ``arc_rounding`` the scaled values are unchanged.

    Nearest rounding scales 10.04 to 100, so six arcs look like exactly 60.0 and
    a single route is accepted; the step durations are the scaled values / scale.
    """
    pytest.importorskip("ortools")
    matrix = _star_matrix(5, 10.04)
    kwargs = dict(
        time_matrix=matrix,
        disability_types=["So"] * 5,
        sw_capacity=4,
        so_capacity=5,
        max_route_duration=60,
        num_vehicles=5,
        time_limit_seconds=1,
    )

    default = solve_ortools_cvrp(**kwargs)
    explicit = solve_ortools_cvrp(**kwargs, arc_rounding="nearest")

    for solution in (default, explicit):
        assert solution.success
        assert len(solution.routes) == 1
        route = solution.routes[0]
        assert [s.duration for s in route.steps] == [10.0] * 6
        assert route.total_duration == 60.0


def test_unknown_arc_rounding_is_rejected():
    solution = solve_ortools_cvrp(
        time_matrix=_star_matrix(1, 5.0), arc_rounding="round-ish"
    )
    assert not solution.success
    assert "arc_rounding" in solution.error_message
