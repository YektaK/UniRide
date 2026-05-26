"""Demand extraction helpers for UniRide-style student objects."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


def student_capacity_demand(student) -> Tuple[int, int]:
    """Return (SW, SO) demand for a request student-like object."""
    disability_type = getattr(student, "disability_type", None)
    is_sw = disability_type == "Sw"
    return (1 if is_sw else 0, 0 if is_sw else 1)


def build_student_demands(students: Iterable) -> Dict[str, Tuple[int, int]]:
    """Build location_code -> (SW, SO) demand mapping."""
    demands: Dict[str, Tuple[int, int]] = {}
    for student in students:
        demands[getattr(student, "location_code")] = student_capacity_demand(student)
    return demands


def build_student_map(students: Iterable) -> Dict[str, object]:
    """Build location_code -> student mapping."""
    return {getattr(student, "location_code"): student for student in students}


__all__ = ["build_student_demands", "build_student_map", "student_capacity_demand"]
