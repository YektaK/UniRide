"""String-keyed greedy routing for production-compatible CVRP heuristics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Sequence

DurationLookup = Callable[[str, str], float]


@dataclass
class GreedyRouteStep:
    location1: str
    location2: str
    duration: float


@dataclass
class GreedyRoutePlan:
    steps: List[GreedyRouteStep] = field(default_factory=list)
    student_locations: List[str] = field(default_factory=list)
    total_duration: float = 0.0
    sw_count: int = 0
    so_count: int = 0


def solve_string_greedy_routes(
    *,
    customer_locations: Sequence[str],
    disability_types: Mapping[str, str],
    depot_id: str,
    duration_lookup: DurationLookup,
    sw_capacity: int,
    so_capacity: int,
    max_route_duration: float,
) -> List[GreedyRoutePlan]:
    """Build feasible greedy routes using nearest valid customer selection."""
    unassigned = list(customer_locations)
    routes: List[GreedyRoutePlan] = []

    while unassigned:
        current_location = depot_id
        current_sw = 0
        current_so = 0
        current_duration = 0.0
        route = GreedyRoutePlan()

        while unassigned:
            best_location = None
            best_duration = float("inf")

            for location in unassigned:
                sw_needed, so_needed = _demand(disability_types.get(location, "So"))
                if current_sw + sw_needed > sw_capacity:
                    continue
                if current_so + so_needed > so_capacity:
                    continue

                travel_duration = duration_lookup(current_location, location)
                return_duration = duration_lookup(location, depot_id)
                if current_duration + travel_duration + return_duration > max_route_duration:
                    continue

                if travel_duration < best_duration:
                    best_duration = travel_duration
                    best_location = location

            if best_location is None:
                break

            route.steps.append(
                GreedyRouteStep(
                    location1=current_location,
                    location2=best_location,
                    duration=round(float(best_duration), 2),
                )
            )
            route.student_locations.append(best_location)
            current_duration += float(best_duration)
            current_location = best_location
            sw_needed, so_needed = _demand(disability_types.get(best_location, "So"))
            current_sw += sw_needed
            current_so += so_needed
            route.sw_count += sw_needed
            route.so_count += so_needed
            unassigned.remove(best_location)

        if not route.student_locations:
            break

        return_duration = duration_lookup(current_location, depot_id)
        route.steps.append(
            GreedyRouteStep(
                location1=current_location,
                location2=depot_id,
                duration=round(float(return_duration), 2),
            )
        )
        route.total_duration = round(current_duration + float(return_duration), 2)
        routes.append(route)

    return routes


def _demand(disability_type: str) -> tuple[int, int]:
    return (1, 0) if disability_type == "Sw" else (0, 1)


__all__ = ["GreedyRoutePlan", "GreedyRouteStep", "solve_string_greedy_routes"]
