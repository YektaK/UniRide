"""Unit tests for ``check_ride_time`` (per-student maximum ride time).

Route = depot -> s1 .. sk -> depot.
  pickup : ride of stop m = arcs stop m -> ... -> sk -> depot (longest: s1)
  dropoff: ride of stop m = arcs depot -> s1 -> ... -> stop m (longest: sk)
"""

import numpy as np

from uniride_core.algorithms.feasibility_certificate import (
    RIDE_TIME_VIOLATION,
    Violation,
    check_ride_time,
)

#            0 (depot)  1     2     3
MATRIX = np.array(
    [
        [0.0, 5.0, 40.0, 40.0],
        [20.0, 0.0, 10.0, 40.0],
        [20.0, 40.0, 0.0, 10.0],
        [20.0, 40.0, 40.0, 0.0],
    ]
)
# route [1, 2, 3]: arcs 5, 10, 10, closing 20
#   pickup rides   : node1 = 10+10+20 = 40, node2 = 30, node3 = 20
#   dropoff rides  : node1 = 5, node2 = 15, node3 = 25


def test_constant_value():
    assert RIDE_TIME_VIOLATION == "ride_time_violation"


def test_pickup_boundary_exactly_at_limit_passes_and_plus_one_fails():
    assert check_ride_time([[1, 2, 3]], MATRIX, 0, 40, "pickup") == []
    violations = check_ride_time([[1, 2, 3]], MATRIX, 0, 39, "pickup")
    assert len(violations) == 1
    violation = violations[0]
    assert isinstance(violation, Violation)
    assert violation.type == RIDE_TIME_VIOLATION
    assert violation.severity == "error"
    assert violation.route_index == 0
    assert violation.node == 1  # first student rides longest when picking up
    assert "40" in violation.details and "39" in violation.details


def test_dropoff_boundary_exactly_at_limit_passes_and_plus_one_fails():
    assert check_ride_time([[1, 2, 3]], MATRIX, 0, 25, "dropoff") == []
    violations = check_ride_time([[1, 2, 3]], MATRIX, 0, 24, "dropoff")
    assert len(violations) == 1
    assert violations[0].type == RIDE_TIME_VIOLATION
    assert violations[0].node == 3  # last student rides longest when dropping off


def test_directions_are_distinguished():
    # at 30: pickup (40) violates, dropoff (25) does not
    assert len(check_ride_time([[1, 2, 3]], MATRIX, 0, 30, "pickup")) == 1
    assert check_ride_time([[1, 2, 3]], MATRIX, 0, 30, "dropoff") == []


def test_direction_is_case_insensitive_and_defaults_to_pickup():
    assert len(check_ride_time([[1, 2, 3]], MATRIX, 0, 30, "PICKUP")) == 1
    assert check_ride_time([[1, 2, 3]], MATRIX, 0, 30, "Dropoff") == []
    assert len(check_ride_time([[1, 2, 3]], MATRIX, 0, 30)) == 1


def test_no_limit_or_no_matrix_is_a_noop():
    assert check_ride_time([[1, 2, 3]], MATRIX, 0, None, "pickup") == []
    assert check_ride_time([[1, 2, 3]], None, 0, 1, "pickup") == []


def test_single_stop_route_ride_is_the_direct_arc():
    # node 2 alone: pickup = closing arc 20, dropoff = outbound arc 40
    assert check_ride_time([[2]], MATRIX, 0, 20, "pickup") == []
    assert len(check_ride_time([[2]], MATRIX, 0, 19, "pickup")) == 1
    assert check_ride_time([[2]], MATRIX, 0, 40, "dropoff") == []
    assert len(check_ride_time([[2]], MATRIX, 0, 39, "dropoff")) == 1


def test_only_violating_routes_are_reported_with_their_index():
    violations = check_ride_time([[1], [1, 2, 3], [3]], MATRIX, 0, 25, "pickup")
    assert [v.route_index for v in violations] == [1]


def test_empty_routes_are_skipped():
    assert check_ride_time([[]], MATRIX, 0, 1, "pickup") == []


def test_non_finite_arc_fails_closed():
    matrix = MATRIX.copy()
    matrix[3, 0] = np.inf
    violations = check_ride_time([[1, 2, 3]], matrix, 0, 600, "pickup")
    assert len(violations) == 1
    assert violations[0].type == RIDE_TIME_VIOLATION


def test_tolerance_absorbs_rounding_but_not_real_violations():
    # 40 > 39.99 only by 0.01: tolerated at 0.02, still rejected at 0.0
    assert len(check_ride_time([[1, 2, 3]], MATRIX, 0, 39.99, "pickup")) == 1
    assert check_ride_time([[1, 2, 3]], MATRIX, 0, 39.99, "pickup", tolerance=0.02) == []
    assert len(check_ride_time([[1, 2, 3]], MATRIX, 0, 39, "pickup", tolerance=0.02)) == 1


def test_non_zero_depot_index():
    # depot is node 3: route [0, 1] -> arcs 3->0, 0->1, 1->3
    matrix = np.array(
        [
            [0.0, 7.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 11.0],
            [0.0, 0.0, 0.0, 0.0],
            [4.0, 0.0, 0.0, 0.0],
        ]
    )
    # pickup: node 0 rides 7 + 11 = 18 ; dropoff: node 1 rides 4 + 7 = 11
    assert check_ride_time([[0, 1]], matrix, 3, 18, "pickup") == []
    assert len(check_ride_time([[0, 1]], matrix, 3, 17, "pickup")) == 1
    assert check_ride_time([[0, 1]], matrix, 3, 11, "dropoff") == []
    assert len(check_ride_time([[0, 1]], matrix, 3, 10, "dropoff")) == 1
