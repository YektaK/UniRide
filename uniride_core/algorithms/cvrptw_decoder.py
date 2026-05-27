"""Core CVRPTW decoder compatibility layer.

This module keeps the public decoder helpers used by the API while ensuring
the split-decoder selection and time-window helpers are owned by uniride_core.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from uniride_core.algorithms.linear_split_decoder import LinearSplitDecoder, PenaltyConfig
from uniride_core.algorithms.string_split_decoder import Direction, SplitDecoder


class CVRPTWDecoder:
    """CVRPTW decoder that delegates to the stable or bounded core split decoder."""

    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_duration: float = 120.0,
        time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        use_time_windows: bool = True,
        use_sota_engine: bool = False,
        direction: Direction = Direction.PICKUP,
        is_asymmetric: bool = False,
    ):
        self.time_windows = time_windows or {}
        self.use_time_windows = use_time_windows
        self.use_sota_engine = use_sota_engine

        if use_sota_engine:
            self.decoder = LinearSplitDecoder(
                sw_capacity=sw_capacity,
                so_capacity=so_capacity,
                max_tour_duration=max_tour_duration,
                time_windows=time_windows,
                direction=direction,
                penalty_config=PenaltyConfig(allow_time_warp=True, allow_capacity_overflow=True),
            )
        else:
            self.decoder = SplitDecoder(
                sw_capacity=sw_capacity,
                so_capacity=so_capacity,
                max_tour_duration=max_tour_duration,
                time_windows=time_windows,
                use_time_windows=use_time_windows,
                direction=direction,
                is_asymmetric=is_asymmetric,
            )

    def decode(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]],
    ) -> Dict:
        """Decode a giant tour into CVRPTW-compatible route fields."""
        if self.use_sota_engine:
            res = self.decoder.decode(giant_tour, depot, distance_matrix, demands)
            return {
                "routes": res.routes,
                "total_cost": res.final_objective,
                "num_vehicles": res.num_vehicles,
                "time_window_violations": res.time_window_violations,
                "capacity_violations": getattr(res, "capacity_violations", 0),
                "schedules": getattr(res, "schedules", []),
            }

        res = self.decoder.decode(giant_tour, depot, distance_matrix, demands)
        return {
            "routes": res.get("routes", []),
            "total_cost": res.get("total_cost", float("inf")),
            "num_vehicles": res.get("num_vehicles", 0),
            "time_window_violations": res.get("time_window_violations", 0),
            "capacity_violations": res.get("capacity_violations", 0),
            "schedules": res.get("schedules", []),
        }

    def is_feasible(
        self,
        route: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
    ) -> Tuple[bool, str]:
        """Check whether a route satisfies configured time windows."""
        if not self.use_time_windows:
            return True, ""

        current_time = 0.0
        prev = depot

        for loc in route:
            if loc == depot:
                continue

            travel_time = 0.0
            if prev in distance_matrix and loc in distance_matrix[prev]:
                travel_time = distance_matrix[prev][loc]
            current_time += travel_time

            if loc in self.time_windows:
                earliest, latest = self.time_windows[loc]
                if current_time > latest:
                    return False, f"Arrival at {loc} at {current_time:.0f}min exceeds latest {latest}min"
                if current_time < earliest:
                    current_time = earliest

            prev = loc

        if prev in distance_matrix and depot in distance_matrix[prev]:
            current_time += distance_matrix[prev][depot]

        return True, f"Feasible (total time: {current_time:.0f}min)"


def parse_time_windows(
    pickup_times: List[str],
    dropoff_times: List[str],
) -> Dict[str, Tuple[int, int]]:
    """Parse HH:MM times into 30-minute time windows."""

    def parse_time(time_str: str) -> int:
        try:
            parts = time_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0

    time_windows = {}
    for t in pickup_times:
        time_windows[t] = (parse_time(t), parse_time(t) + 30)
    for t in dropoff_times:
        time_windows[t] = (parse_time(t), parse_time(t) + 30)
    return time_windows


def create_time_windows_from_students(
    students: List[Dict],
    time_column: str = "pickup_time",
) -> Dict[str, Tuple[int, int]]:
    """Create location-keyed 30-minute time windows from student dictionaries."""
    time_windows: Dict[str, Tuple[int, int]] = {}

    for student in students:
        location = student.get("location_code", "")
        if not location:
            continue

        time_str = student.get(time_column, "")
        if not time_str:
            continue

        try:
            minutes = int(time_str.split(":")[0]) * 60 + int(time_str.split(":")[1])
        except (ValueError, IndexError, KeyError):
            continue

        if location in time_windows:
            existing = time_windows[location]
            time_windows[location] = (min(existing[0], minutes), max(existing[1], minutes + 30))
        else:
            time_windows[location] = (minutes, minutes + 30)

    return time_windows


__all__ = [
    "CVRPTWDecoder",
    "Direction",
    "LinearSplitDecoder",
    "PenaltyConfig",
    "SplitDecoder",
    "create_time_windows_from_students",
    "parse_time_windows",
]
