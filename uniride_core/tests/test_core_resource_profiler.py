from __future__ import annotations

from dataclasses import dataclass

from uniride_core.algorithms.resource_profiler import (
    ResourceProfiler,
    minutes_to_time_str,
    time_str_to_minutes,
)


@dataclass
class _Student:
    id: str
    disability_type: str
    pickup_time: str | None = None
    dropoff_time: str | None = None


@dataclass
class _Vehicle:
    id: str
    sw_capacity: int
    so_capacity: int


def test_standard_vehicle_needs_use_sw_so_capacities():
    profiler = ResourceProfiler(standard_sw_capacity=4, standard_so_capacity=5)
    students = [
        *[_Student(id=f"sw-{idx}", disability_type="Sw") for idx in range(9)],
        *[_Student(id=f"so-{idx}", disability_type="So") for idx in range(6)],
    ]

    result = profiler.calculate_standard_vehicle_needs(students)

    assert result["total_students"] == 15
    assert result["sw_count"] == 9
    assert result["so_count"] == 6
    assert result["by_capacity"]["by_sw"] == 3
    assert result["by_capacity"]["by_so"] == 2
    assert result["by_capacity"]["max_needed"] == 3
    assert result["standard_vehicles_needed"] == 3


def test_resource_profiler_time_conversion_helpers():
    assert minutes_to_time_str(9 * 60 + 5) == "09:05"
    assert time_str_to_minutes("09:05") == 9 * 60 + 5


def test_identify_bottlenecks_uses_structural_vehicle_objects():
    profiler = ResourceProfiler(standard_sw_capacity=4, standard_so_capacity=5)
    students = [
        _Student(id="sw-1", disability_type="Sw"),
        _Student(id="sw-2", disability_type="Sw"),
        _Student(id="so-1", disability_type="So"),
    ]
    demand = profiler.generate_hourly_demand(
        students,
        pickup_times={"sw-1": "09:00", "sw-2": "09:05", "so-1": "09:10"},
    )

    bottlenecks = profiler.identify_bottlenecks(
        hourly_demand=demand,
        available_vehicles=[_Vehicle(id="v1", sw_capacity=1, so_capacity=1)],
    )

    assert any(b.hour == "09:00" and b.type == "infeasible" for b in bottlenecks)
