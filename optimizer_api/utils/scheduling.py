"""Route scheduling helpers for optimization responses."""

from __future__ import annotations

from typing import Dict, List

from models.schemas import OptimizationRequest, TripDirection, VehicleRoute
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES


def calculate_scheduled_times(
    routes: List[VehicleRoute],
    request: OptimizationRequest,
    distance_matrix: Dict[str, Dict[str, float]],
) -> List[VehicleRoute]:
    if not request.use_time_windows:
        return routes

    time_windows = request.get_time_windows()

    for route in routes:
        if not route.route_details:
            continue

        locations = []
        for step in route.route_details:
            if step.location1 not in locations:
                locations.append(step.location1)
            if step.location2 not in locations:
                locations.append(step.location2)

        if len(locations) > 2 and locations[0] == locations[-1]:
            locations = locations[:-1]

        arrival_times = {}

        if request.direction == TripDirection.PICKUP:
            target_minutes = None
            for loc in reversed(locations):
                if loc in time_windows:
                    target_minutes = time_windows[loc].latest
                    break

            if target_minutes is None and request.target_time:
                target_minutes = _parse_hhmm(request.target_time)

            if target_minutes is None:
                target_minutes = 9 * 60

            current_minutes = target_minutes
            arrival_times[locations[-1]] = minutes_to_time(current_minutes)

            for i in range(len(locations) - 2, -1, -1):
                from_loc = locations[i]
                to_loc = locations[i + 1]

                travel_time = distance_matrix.get(from_loc, {}).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
                current_minutes -= travel_time
                arrival_times[from_loc] = minutes_to_time(current_minutes)

            departure_minutes = current_minutes - request.offset_minutes
            route.departure_time = minutes_to_time(max(0, departure_minutes))

        else:
            start_minutes = None
            for loc in locations:
                if loc in time_windows:
                    start_minutes = time_windows[loc].earliest
                    break

            if start_minutes is None and request.target_time:
                start_minutes = _parse_hhmm(request.target_time)

            if start_minutes is None:
                start_minutes = 14 * 60

            current_minutes = start_minutes
            arrival_times[locations[0]] = minutes_to_time(current_minutes)
            route.departure_time = minutes_to_time(current_minutes)

            for i in range(len(locations) - 1):
                from_loc = locations[i]
                to_loc = locations[i + 1]

                travel_time = distance_matrix.get(from_loc, {}).get(to_loc, DEFAULT_TRAVEL_FALLBACK_MINUTES)
                current_minutes += travel_time
                arrival_times[to_loc] = minutes_to_time(current_minutes)

        route.arrival_times = arrival_times

    return routes


def minutes_to_time(minutes: float) -> str:
    """Convert minutes from midnight to a clamped HH:MM string."""
    total = max(0, min(int(minutes), 23 * 60 + 59))
    hours = total // 60
    mins = total % 60
    return f"{hours:02d}:{mins:02d}"


def _parse_hhmm(value: str) -> int:
    parts = value.split(":")
    return int(parts[0]) * 60 + int(parts[1])


__all__ = ["calculate_scheduled_times", "minutes_to_time"]
