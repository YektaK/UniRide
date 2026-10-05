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

    Raised by ``get_duration``/``calculate_route_duration`` (strict by
    default) when the time matrix cannot answer, so missing arcs fail closed
    instead of silently fabricating a haversine or generic estimate.
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


def strict_arc(
    distance_matrix: Mapping,
    from_loc: str,
    to_loc: str,
) -> float:
    """Directed arc from a nested ``{from: {to: minutes}}`` matrix, strictly.

    Never substitutes a default: a missing arc raises
    ``TravelTimeUnavailableError`` (operational travel times come only from
    the stored ``time_matrix``). ``from_loc == to_loc`` is 0.0 when the
    diagonal is absent.
    """
    row = distance_matrix.get(from_loc)
    if row is not None and to_loc in row:
        return float(row[to_loc])
    if from_loc == to_loc:
        return 0.0
    raise TravelTimeUnavailableError(
        f"No travel time for {from_loc!r} -> {to_loc!r}: "
        "missing from the time matrix."
    )


def get_duration(
    from_loc: str,
    to_loc: str,
    time_matrix: Mapping,
    coordinates: Mapping,
    fallback_minutes: float = DEFAULT_TRAVEL_FALLBACK_MINUTES,
    strict: bool = True,
    allow_coordinate_fallback: bool = False,
) -> float:
    """Get the directed travel duration from the time matrix.

    Operational contract (owner requirement, 2026-10-05): the stored
    ``time_matrix`` is the only source of travel times. A pair missing from
    ``time_matrix`` raises ``TravelTimeUnavailableError``; no haversine
    estimate and no generic default are substituted.

    ``allow_coordinate_fallback=True`` is the explicit development/test
    opt-in (the optimizer passes ``UNIRIDE_ALLOW_COORDINATE_FALLBACK``): a
    pair missing from the matrix but present in ``coordinates`` then gets a
    haversine estimate. ``strict=False`` is a legacy escape hatch for
    non-operational callers: it additionally returns ``fallback_minutes``
    instead of raising when neither source can answer.
    """
    if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
        return float(time_matrix[from_loc][to_loc])

    if allow_coordinate_fallback and from_loc in coordinates and to_loc in coordinates:
        c1 = coordinates[from_loc]
        c2 = coordinates[to_loc]
        dist = haversine_distance_km(float(c1["lat"]), float(c1["lng"]), float(c2["lat"]), float(c2["lng"]))
        return estimate_travel_time_minutes(dist)

    if strict:
        raise TravelTimeUnavailableError(
            f"No travel time for {from_loc!r} -> {to_loc!r}: "
            "missing from the time matrix."
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
    strict: bool = True,
    allow_coordinate_fallback: bool = False,
) -> float:
    """Compute depot -> route -> depot duration in minutes.

    ``strict`` and ``allow_coordinate_fallback`` are forwarded to
    ``get_duration`` (fail-closed on missing arcs; see
    ``TravelTimeUnavailableError``).
    """
    if not route:
        return 0.0

    def leg(origin: str, destination: str) -> float:
        return get_duration(
            origin,
            destination,
            time_matrix,
            coordinates,
            fallback_minutes,
            strict,
            allow_coordinate_fallback,
        )

    total = leg(depot, route[0])
    for idx in range(len(route) - 1):
        total += leg(route[idx], route[idx + 1])
    total += leg(route[-1], depot)
    return total


__all__ = [
    "DEFAULT_TRAVEL_FALLBACK_MINUTES",
    "TravelTimeUnavailableError",
    "calculate_route_duration",
    "estimate_travel_time_minutes",
    "get_duration",
    "strict_arc",
    "haversine_distance_km",
]
