"""Demand extraction helpers for UniRide-style student objects."""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Tuple


def _get_attribute(student, attr: str):
    """Read ``attr`` from a dict-like or object-like student."""
    if isinstance(student, dict):
        return student.get(attr)
    return getattr(student, attr, None)


def student_capacity_demand(student) -> Tuple[int, int]:
    """Return (SW, SO) demand for a request student-like object."""
    disability_type = _get_attribute(student, "disability_type")
    is_sw = disability_type == "Sw"
    return (1 if is_sw else 0, 0 if is_sw else 1)


def student_occurrence_key(student) -> str:
    """Return the base occurrence identity for a single student occurrence.

    Resolution order:
      1. explicit ``occurrence_id`` attribute (non-empty)
      2. ``id`` attribute (non-empty)
      3. ``location_code`` attribute (non-empty)
    """
    for attr in ("occurrence_id", "id", "location_code"):
        value = _get_attribute(student, attr)
        if value:
            return str(value)
    return ""


def student_occurrence_keys(students: Iterable) -> List[str]:
    """Return one unique node key per student occurrence.

    Backward compatible: when a physical ``location_code`` is served by
    exactly one student, the key equals the ``location_code`` so existing
    single-customer behavior and outputs are unchanged. When a location is
    served by multiple students, each occurrence is disambiguated to
    ``"<location_code>#<occurrence_id>"`` (falling back to a zero-based index
    when the occurrence id equals the location code or is empty).
    """
    keys = [student_occurrence_key(student) for student in students]
    locations = [_get_attribute(student, "location_code") for student in students]
    counts = Counter(locations)
    seen: Counter = Counter()
    result: List[str] = []
    for student, base_key, location in zip(students, keys, locations):
        if counts[location] == 1:
            result.append(location)
        else:
            idx = seen[location]
            seen[location] += 1
            suffix = base_key if base_key and base_key != location else str(idx)
            result.append(f"{location}#{suffix}")
    return result


def build_student_demands(students: Iterable) -> Dict[str, Tuple[int, int]]:
    """Build occurrence-keyed ``(SW, SO)`` demand mapping.

    Single-customer locations keep their ``location_code`` as the key;
    locations served by multiple customers get disambiguated occurrence keys.
    """
    demands: Dict[str, Tuple[int, int]] = {}
    for student, key in zip(students, student_occurrence_keys(students)):
        demands[key] = student_capacity_demand(student)
    return demands


def build_student_map(students: Iterable) -> Dict[str, object]:
    """Build occurrence-keyed ``key -> student`` mapping.

    Single-customer locations keep their ``location_code`` as the key;
    locations served by multiple customers get disambiguated occurrence keys.
    """
    return {key: student for student, key in zip(students, student_occurrence_keys(students))}


__all__ = [
    "build_student_demands",
    "build_student_map",
    "student_capacity_demand",
    "student_occurrence_key",
    "student_occurrence_keys",
]
