"""Occurrence-identity tests for UniRide demand_builder and uniride_adapter.

Verifies that multiple customers at the same physical location_code remain
distinct solver nodes while preserving backward compatibility for
single-customer locations.
"""

from types import SimpleNamespace

from uniride_core.adapters.demand_builder import (
    build_student_demands,
    build_student_map,
    student_capacity_demand,
    student_occurrence_key,
    student_occurrence_keys,
)
from uniride_core.adapters.uniride_adapter import uniride_request_to_problem


# ── student_occurrence_key ────────────────────────────────────────────────────

def test_student_occurrence_key_returns_explicit_occurrence_id():
    s = SimpleNamespace(occurrence_id="REQ-7", id="S1", location_code="L1")
    assert student_occurrence_key(s) == "REQ-7"


def test_student_occurrence_key_falls_back_to_id():
    s = SimpleNamespace(id="S1", location_code="L1")
    assert student_occurrence_key(s) == "S1"


def test_student_occurrence_key_falls_back_to_location_code():
    s = SimpleNamespace(location_code="L1")
    assert student_occurrence_key(s) == "L1"


# ---------------------------------------------------------------------------
# student_occurrence_keys
# ---------------------------------------------------------------------------

def test_student_occurrence_keys_single_occurrence_is_location_code():
    students = [
        SimpleNamespace(location_code="a", id="s1"),
        SimpleNamespace(location_code="b", id="s2"),
        SimpleNamespace(location_code="c", id="s3"),
    ]
    assert student_occurrence_keys(students) == ["a", "b", "c"]


def test_student_occurrence_keys_multiple_occurrences_are_disambiguated():
    students = [
        SimpleNamespace(location_code="L1", id="s1"),
        SimpleNamespace(location_code="L1", id="s2"),
        SimpleNamespace(location_code="L2", id="s3"),
    ]
    keys = student_occurrence_keys(students)
    assert keys == ["L1#s1", "L1#s2", "L2"]
    assert len(set(keys)) == 3


def test_student_occurrence_keys_uses_occurrence_id_when_set():
    students = [
        SimpleNamespace(occurrence_id="REQ-A", location_code="L1"),
        SimpleNamespace(occurrence_id="REQ-B", location_code="L1"),
    ]
    keys = student_occurrence_keys(students)
    assert keys == ["L1#REQ-A", "L1#REQ-B"]


def test_student_occurrence_keys_mixed_single_and_multiple():
    students = [
        SimpleNamespace(location_code="a", id="s1"),
        SimpleNamespace(location_code="a", id="s2"),
        SimpleNamespace(location_code="b", id="s3"),
        SimpleNamespace(location_code="b", id="s4"),
        SimpleNamespace(location_code="c", id="s5"),
    ]
    keys = student_occurrence_keys(students)
    assert keys == ["a#s1", "a#s2", "b#s3", "b#s4", "c"]


def test_student_occurrence_keys_uses_index_fallback_when_id_equals_location():
    students = [
        SimpleNamespace(location_code="L", id="L"),
        SimpleNamespace(location_code="L", id="L"),
    ]
    keys = student_occurrence_keys(students)
    assert keys == ["L#0", "L#1"]
    assert len(set(keys)) == 2


# ---------------------------------------------------------------------------
# build_student_demands (occurrence-aware)
# ---------------------------------------------------------------------------

def test_build_student_demands_backward_compat_unique_locations():
    students = [
        SimpleNamespace(location_code="a", disability_type="Sw"),
        SimpleNamespace(location_code="b", disability_type="So"),
    ]
    assert build_student_demands(students) == {"a": (1, 0), "b": (0, 1)}


def test_build_student_demands_preserves_duplicate_locations():
    students = [
        SimpleNamespace(location_code="L1", id="s1", disability_type="Sw"),
        SimpleNamespace(location_code="L1", id="s2", disability_type="So"),
        SimpleNamespace(location_code="L2", id="s3", disability_type="Sw"),
    ]
    demands = build_student_demands(students)
    assert demands == {"L1#s1": (1, 0), "L1#s2": (0, 1), "L2": (1, 0)}
    assert len(demands) == 3


def test_build_student_demands_handles_empty():
    assert build_student_demands([]) == {}


# ---------------------------------------------------------------------------
# build_student_map (occurrence-aware)
# ---------------------------------------------------------------------------

def test_build_student_map_backward_compat_unique_locations():
    students = [
        SimpleNamespace(location_code="a", id="s1"),
        SimpleNamespace(location_code="b", id="s2"),
    ]
    result = build_student_map(students)
    assert result["a"] is students[0]
    assert result["b"] is students[1]
    assert len(result) == 2


def test_build_student_map_preserves_duplicate_locations():
    s1 = SimpleNamespace(location_code="L1", id="s1")
    s2 = SimpleNamespace(location_code="L1", id="s2")
    s3 = SimpleNamespace(location_code="L2", id="s3")
    result = build_student_map([s1, s2, s3])
    assert result["L1#s1"] is s1
    assert result["L1#s2"] is s2
    assert result["L2"] is s3
    assert len(result) == 3


# ---------------------------------------------------------------------------
# deterministic, collision-safe occurrence keys
# ---------------------------------------------------------------------------

def test_student_occurrence_keys_disambiguates_colliding_explicit_ids():
    students = [
        SimpleNamespace(occurrence_id="REQ-A", id="s1", location_code="L1"),
        SimpleNamespace(occurrence_id="REQ-A", id="s2", location_code="L1"),
    ]
    keys = student_occurrence_keys(students)
    assert len(set(keys)) == 2
    assert keys[0] == "L1#REQ-A"
    assert keys[1].startswith("L1#REQ-A")
    assert keys[1] != keys[0]


def test_student_occurrence_keys_generated_key_does_not_collide_with_physical_code():
    # s2's generated key "L1#L2" equals s3's physical location code; the
    # physical code must win and the generated key must be disambiguated.
    students = [
        SimpleNamespace(location_code="L1", id="s1"),
        SimpleNamespace(location_code="L1", occurrence_id="L2", id="s2"),
        SimpleNamespace(location_code="L1#L2", id="s3"),
    ]
    keys = student_occurrence_keys(students)
    assert len(set(keys)) == 3
    assert keys[0] == "L1#s1"
    assert keys[1].startswith("L1#L2")
    assert keys[1] != "L1#L2"
    assert keys[2] == "L1#L2"


def test_student_occurrence_keys_deterministic_for_same_input():
    students = [
        SimpleNamespace(occurrence_id="REQ-A", id="s1", location_code="L1"),
        SimpleNamespace(occurrence_id="REQ-A", id="s2", location_code="L1"),
        SimpleNamespace(location_code="L1", occurrence_id="L2", id="s3"),
    ]
    first = student_occurrence_keys(students)
    second = student_occurrence_keys(list(students))
    assert first == second
    assert len(set(first)) == len(first)


def test_build_student_map_preserves_colliding_explicit_ids():
    s1 = SimpleNamespace(occurrence_id="REQ-A", id="s1", location_code="L1")
    s2 = SimpleNamespace(occurrence_id="REQ-A", id="s2", location_code="L1")
    result = build_student_map([s1, s2])
    assert len(result) == 2
    assert s1 in result.values()
    assert s2 in result.values()


# ---------------------------------------------------------------------------
# generator inputs behave identically to lists
# ---------------------------------------------------------------------------

def test_student_occurrence_keys_accepts_generator():
    students = [
        SimpleNamespace(location_code="a", id="s1"),
        SimpleNamespace(location_code="a", id="s2"),
        SimpleNamespace(location_code="b", id="s3"),
    ]
    expected = student_occurrence_keys(students)
    assert student_occurrence_keys(iter(students)) == expected


def test_build_student_demands_accepts_generator():
    students = [
        SimpleNamespace(location_code="L1", id="s1", disability_type="Sw"),
        SimpleNamespace(location_code="L1", id="s2", disability_type="So"),
        SimpleNamespace(location_code="L2", id="s3", disability_type="Sw"),
    ]
    expected = build_student_demands(students)
    assert build_student_demands(iter(students)) == expected


def test_build_student_map_accepts_generator():
    s1 = SimpleNamespace(location_code="a", id="s1")
    s2 = SimpleNamespace(location_code="a", id="s2")
    s3 = SimpleNamespace(location_code="b", id="s3")
    expected = build_student_map([s1, s2, s3])
    assert build_student_map(iter([s1, s2, s3])) == expected


# ---------------------------------------------------------------------------
# uniride_adapter occurrence_ids
# ---------------------------------------------------------------------------

def test_uniride_adapter_occurrence_ids_for_duplicates():
    class DummyRequest:
        students = [
            {"id": "S1", "location_code": "L1", "coordinates": {"lat": 0, "lng": 0}, "disability_type": "Sw"},
            {"id": "S2", "location_code": "L1", "coordinates": {"lat": 0, "lng": 0}, "disability_type": "So"},
        ]
        depot = {"id": "D"}
        sw_capacity = 2
        so_capacity = 2
        max_travel_time = 60
        direction = "pickup"
        target_time = None
        offset_minutes = 10
        is_asymmetric = False

    matrix = [[0, 5, 5], [5, 0, 1], [5, 1, 0]]
    problem = uniride_request_to_problem(DummyRequest(), matrix=matrix)
    labels = problem.matrix.labels
    assert labels is not None
    assert labels == ["D", "L1#S1", "L1#S2"], f"got {labels}"
    occ_ids = problem.matrix.occurrence_ids
    assert occ_ids is not None
    assert occ_ids == ["L1#S1", "L1#S2"]


def test_uniride_adapter_backward_compat_single_per_location():
    class DummyRequest:
        students = [
            {"id": "S1", "location_code": "L1", "coordinates": {"lat": 1, "lng": 0}, "disability_type": "Sw"},
            {"id": "S2", "location_code": "L2", "coordinates": {"lat": 2, "lng": 0}, "disability_type": "So"},
        ]
        depot = {"id": "D"}
        sw_capacity = 1
        so_capacity = 2
        max_travel_time = 90
        direction = "pickup"
        target_time = None
        offset_minutes = 10
        is_asymmetric = False

    matrix = [[0, 5, 9], [6, 0, 3], [8, 4, 0]]
    problem = uniride_request_to_problem(DummyRequest(), matrix=matrix)
    assert problem.matrix.labels == ["D", "L1", "L2"]
    assert problem.matrix.kind == "travel_time"