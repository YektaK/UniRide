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

    Keys are deterministic and globally collision-safe: when an explicit
    ``occurrence_id`` collides with another occurrence or with a physical
    ``location_code``, the later occurrence is re-keyed to
    ``"<location_code>#<occurrence_id>#<n>"``. Physical location codes always
    take precedence over generated keys. The iterable is materialized once, so
    lists and generators behave identically.
    """
    students = list(students)
    locations = [_get_attribute(student, "location_code") for student in students]
    base_keys = [student_occurrence_key(student) for student in students]
    counts = Counter(locations)

    result: List[str] = [""] * len(students)
    taken = set()

    # Single-customer locations keep their physical code as the node key.
    for idx, location in enumerate(locations):
        if counts[location] == 1:
            result[idx] = location
            taken.add(location)

    # Multi-customer locations get "<loc>#<occurrence>" keys, skipping any
    # key already claimed by a physical code or an earlier occurrence.
    seen: Counter = Counter()
    for idx, (location, base_key) in enumerate(zip(locations, base_keys)):
        if counts[location] == 1:
            continue
        occurrence = seen[location]
        seen[location] += 1
        suffix = base_key if base_key and base_key != location else str(occurrence)
        candidate = f"{location}#{suffix}"
        counter = 1
        while candidate in taken:
            candidate = f"{location}#{suffix}#{counter}"
            counter += 1
        result[idx] = candidate
        taken.add(candidate)
    return result


def build_student_demands(students: Iterable) -> Dict[str, Tuple[int, int]]:
    """Build occurrence-keyed ``(SW, SO)`` demand mapping.

    Single-customer locations keep their ``location_code`` as the key;
    locations served by multiple customers get disambiguated occurrence keys.
    """
    students = list(students)
    demands: Dict[str, Tuple[int, int]] = {}
    for student, key in zip(students, student_occurrence_keys(students)):
        demands[key] = student_capacity_demand(student)
    return demands


def build_student_map(students: Iterable) -> Dict[str, object]:
    """Build occurrence-keyed ``key -> student`` mapping.

    Single-customer locations keep their ``location_code`` as the key;
    locations served by multiple customers get disambiguated occurrence keys.
    """
    students = list(students)
    return {key: student for student, key in zip(students, student_occurrence_keys(students))}


__all__ = [
    "build_student_demands",
    "build_student_map",
    "student_capacity_demand",
    "student_occurrence_key",
    "student_occurrence_keys",
]
