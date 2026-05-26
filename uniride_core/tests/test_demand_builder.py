from types import SimpleNamespace

from uniride_core.adapters.demand_builder import build_student_demands, build_student_map, student_capacity_demand


def test_student_capacity_demand_maps_sw_so_dimensions():
    assert student_capacity_demand(SimpleNamespace(disability_type="Sw")) == (1, 0)
    assert student_capacity_demand(SimpleNamespace(disability_type="So")) == (0, 1)


def test_build_student_demands_and_map_use_location_code():
    students = [
        SimpleNamespace(location_code="a", disability_type="Sw"),
        SimpleNamespace(location_code="b", disability_type="So"),
    ]

    assert build_student_demands(students) == {"a": (1, 0), "b": (0, 1)}
    assert build_student_map(students)["a"] is students[0]
