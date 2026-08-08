"""Core route duration helpers shared by production and academic solvers."""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Mapping

logger = logging.getLogger(__name__)

DEFAULT_TRAVEL_FALLBACK_MINUTES = 15.0
DEFAULT_SPEED_KMH = 30.0


class TravelTimeUnavailableError(LookupError):
    """No travel time available for a (source, target) pair.

    Raised by ``get_duration``/``calculate_route_duration`` when ``strict``
    is enabled and neither the time matrix nor the coordinates can answer.
    Production strategy code enables strict mode so missing arcs fail closed
    instead of silently fabricating the generic fallback estimate.
    """


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2.0) ** 2
    )
    return radius_km * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def estimate_travel_time_minutes(distance_km: float, speed_kmh: float = DEFAULT_SPEED_KMH) -> float:
    if speed_kmh <= 0:
        return DEFAULT_TRAVEL_FALLBACK_MINUTES
    return (distance_km / speed_kmh) * 60.0


def get_duration(
    from_loc: str,
    to_loc: str,
    time_matrix: Mapping,
    coordinates: Mapping,
    fallback_minutes: float = DEFAULT_TRAVEL_FALLBACK_MINUTES,
    strict: bool = False,
) -> float:
    """Get travel duration from matrix first, coordinate fallback second.

    With ``strict=True``, a pair missing from both the matrix and the
    coordinates raises ``TravelTimeUnavailableError`` instead of returning
    the generic fallback estimate (fail-closed; used by production code).
    """
    if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
        return float(time_matrix[from_loc][to_loc])

    if from_loc in coordinates and to_loc in coordinates:
        c1 = coordinates[from_loc]
        c2 = coordinates[to_loc]
        dist = haversine_distance_km(float(c1["lat"]), float(c1["lng"]), float(c2["lat"]), float(c2["lng"]))
        return estimate_travel_time_minutes(dist)

    if strict:
        raise TravelTimeUnavailableError(
            f"No travel time for {from_loc!r} -> {to_loc!r}: "
            "missing from both the time matrix and the coordinates."
        )

    logger.warning(
        "Distance matrix miss for %s to %s. Using default fallback: %s mins",
        from_loc,
        to_loc,
        fallback_minutes,
    )
    return float(fallback_minutes)


def calculate_route_duration(
    route: List[str],
    depot: str,
    time_matrix: Dict,
    coordinates: Dict,
    fallback_minutes: float = DEFAULT_TRAVEL_FALLBACK_MINUTES,
    strict: bool = False,
) -> float:
    """Compute depot -> route -> depot duration in minutes.

    ``strict`` is forwarded to ``get_duration`` (fail-closed on missing
    arcs; see ``TravelTimeUnavailableError``).
    """
    if not route:
        return 0.0

    total = get_duration(depot, route[0], time_matrix, coordinates, fallback_minutes, strict)
    for idx in range(len(route) - 1):
        total += get_duration(route[idx], route[idx + 1], time_matrix, coordinates, fallback_minutes, strict)
    total += get_duration(route[-1], depot, time_matrix, coordinates, fallback_minutes, strict)
    return total


__all__ = [
    "DEFAULT_TRAVEL_FALLBACK_MINUTES",
    "TravelTimeUnavailableError",
    "calculate_route_duration",
    "estimate_travel_time_minutes",
    "get_duration",
    "haversine_distance_km",
]
