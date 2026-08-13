"""Exact string-keyed TSP search for small production-compatible routes."""

from __future__ import annotations

from itertools import permutations
from typing import Callable, List, Sequence

DurationLookup = Callable[[str, str], float]


class ExactTSPSizeError(ValueError):
    """Raised before factorial work when an exact TSP request exceeds its limit."""


def solve_exact_tsp_route(
    waypoints: Sequence[str],
    depot: str,
    duration_lookup: DurationLookup,
    *,
    max_permutation_size: int = 10,
) -> tuple[List[str], float]:
    """Find the best depot-closed route by complete permutation search."""
    search_waypoints = list(waypoints)
    if not search_waypoints:
        return [], 0.0

    if len(search_waypoints) > max_permutation_size:
        raise ExactTSPSizeError(
            f"{len(search_waypoints)} waypoints exceeds exact-search limit {max_permutation_size}"
        )

    if len(search_waypoints) == 1:
        only = search_waypoints[0]
        return search_waypoints, float(duration_lookup(depot, only) + duration_lookup(only, depot))

    best_route: List[str] = []
    best_duration = float("inf")
    for permutation in permutations(search_waypoints):
        duration = route_duration(permutation, depot, duration_lookup)
        if duration < best_duration:
            best_duration = duration
            best_route = list(permutation)

    return best_route, best_duration


def route_duration(route: Sequence[str], depot: str, duration_lookup: DurationLookup) -> float:
    """Calculate a depot-closed route duration."""
    if not route:
        return 0.0
    total = float(duration_lookup(depot, route[0]))
    for idx in range(len(route) - 1):
        total += float(duration_lookup(route[idx], route[idx + 1]))
    total += float(duration_lookup(route[-1], depot))
    return total


__all__ = ["route_duration", "solve_exact_tsp_route", "ExactTSPSizeError"]
