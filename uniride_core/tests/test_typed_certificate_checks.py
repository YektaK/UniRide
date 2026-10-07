"""WP3 unit tests for the typed capacity and quota checks (design section 5)."""

from uniride_core.algorithms.feasibility_certificate import (
    TYPE_QUOTA_VIOLATION,
    TYPED_CAPACITY_VIOLATION,
    VEHICLE_TYPE_UNKNOWN,
    check_type_quota,
    check_typed_capacity,
)

# node 0 is the depot; demands are (Sw, So)
DEMANDS = [(0, 0), (1, 0), (0, 1), (0, 1), (0, 1), (0, 1), (0, 1)]
CAPS = {"large": (4, 5), "car": (0, 4)}


def _kinds(violations):
    return [v.type for v in violations]


def test_valid_typed_routes_pass():
    assert check_typed_capacity([[1, 2], [3, 4, 5, 6]], DEMANDS, ["large", "car"], CAPS) == []


def test_sw_on_zero_sw_type_is_a_violation():
    found = check_typed_capacity([[1, 2]], DEMANDS, ["car"], CAPS)
    assert _kinds(found) == [TYPED_CAPACITY_VIOLATION]
    assert found[0].route_index == 0


def test_so_over_type_capacity_is_a_violation():
    found = check_typed_capacity([[2, 3, 4, 5, 6]], DEMANDS, ["car"], CAPS)
    assert _kinds(found) == [TYPED_CAPACITY_VIOLATION]
    assert check_typed_capacity([[2, 3, 4, 5, 6]], DEMANDS, ["large"], CAPS) == []


def test_missing_unknown_or_nonstring_type_is_unknown_never_defaulted():
    for label in (None, "van", 3):
        found = check_typed_capacity([[2]], DEMANDS, [label], CAPS)
        assert _kinds(found) == [VEHICLE_TYPE_UNKNOWN]
    assert _kinds(check_typed_capacity([[2]], DEMANDS, [], CAPS)) == [VEHICLE_TYPE_UNKNOWN]


def test_empty_routes_are_ignored():
    assert check_typed_capacity([[]], DEMANDS, [None], CAPS) == []


def test_type_quota():
    labels = ["large", "car", "large"]
    assert check_type_quota(labels, {"large": 2}) == []
    assert _kinds(check_type_quota(labels, {"large": 1})) == [TYPE_QUOTA_VIOLATION]
    assert _kinds(check_type_quota(labels, {"car": 0})) == [TYPE_QUOTA_VIOLATION]
    # empty routes do not count against a quota
    assert check_type_quota(labels, {"large": 1}, routes=[[1], [2], []]) == []
