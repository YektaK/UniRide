"""String-keyed matrix helpers for legacy-compatible route wrappers."""

from __future__ import annotations

from typing import Callable, Dict, List

DurationLookup = Callable[[str, str], float]


def build_string_distance_matrix(
    location_ids: List[str],
    duration_lookup: DurationLookup,
) -> Dict[str, Dict[str, float]]:
    """Build a complete string-keyed distance/time matrix."""
    matrix: Dict[str, Dict[str, float]] = {}
    for origin in location_ids:
        matrix[origin] = {}
        for destination in location_ids:
            matrix[origin][destination] = 0.0 if origin == destination else float(duration_lookup(origin, destination))
    return matrix


__all__ = ["build_string_distance_matrix"]
