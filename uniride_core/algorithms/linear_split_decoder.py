"""Bounded split decoder with soft capacity and time-window penalties.

This is the core-owned implementation used by compatibility layers that need
fast route-first decoding with infeasibility penalties.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class PenaltyConfig:
    """Dynamic penalty configuration for soft constraint relaxation."""
    allow_time_warp: bool = True
    tw_penalty_rate: float = 10.0
    allow_capacity_overflow: bool = True
    sw_cap_penalty_rate: float = 100.0
    so_cap_penalty_rate: float = 50.0
    max_stops_bounded: int = 15


@dataclass
class LinearSplitResult:
    routes: List[List[str]]
    total_cost_: float
    total_penalty_: float
    final_objective: float
    time_window_violations: float
    capacity_violations: int
    num_vehicles: int
    schedules: List[Dict]


class LinearSplitDecoder:
    """Bounded O(N*B) split decoder with soft penalties."""

    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_duration: float = 120.0,
        time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        direction: object = "pickup",
        target_time: Optional[int] = None,
        offset_minutes: int = 10,
        penalty_config: Optional[PenaltyConfig] = None,
    ):
        self.sw_cap = sw_capacity
        self.so_cap = so_capacity
        self.max_duration = max_tour_duration
        self.time_windows = time_windows or {}
        self.direction = _normalize_direction(direction)
        self.target_time = target_time
        self.offset_minutes = offset_minutes
        self.penalties = penalty_config or PenaltyConfig()

    def _get_distance(self, dist_matrix: dict, fr: str, to: str) -> float:
        return float(dist_matrix.get(fr, {}).get(to, 15.0))

    def decode(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]],
    ) -> LinearSplitResult:
        if not giant_tour:
            return LinearSplitResult([], 0, 0, 0, 0, 0, 0, [])

        n = len(giant_tour)
        objective = [float("inf")] * (n + 1)
        objective[0] = 0.0
        base_cost = [0.0] * (n + 1)
        penalty_cost = [0.0] * (n + 1)
        predecessor = [-1] * (n + 1)
        tw_violations = [0.0] * (n + 1)
        cap_violations = [0] * (n + 1)
        best_schedule = [None] * (n + 1)

        for i in range(n):
            if objective[i] == float("inf"):
                continue

            curr_sw, curr_so = 0, 0
            curr_travel_time = 0.0
            prev_loc = depot
            current_time_forward = self.target_time if self.direction == "dropoff" and self.target_time else 480
            limit = min(n, i + self.penalties.max_stops_bounded)

            for j in range(i, limit):
                loc = giant_tour[j]
                d_sw, d_so = demands.get(loc, (0, 0))
                curr_sw += d_sw
                curr_so += d_so

                leg_dist = self._get_distance(distance_matrix, prev_loc, loc)
                curr_travel_time += leg_dist
                current_time_forward += int(leg_dist)

                cap_over_sw = max(0, curr_sw - self.sw_cap)
                cap_over_so = max(0, curr_so - self.so_cap)
                if not self.penalties.allow_capacity_overflow and (cap_over_sw > 0 or cap_over_so > 0):
                    break

                cap_penalty = (
                    cap_over_sw * self.penalties.sw_cap_penalty_rate
                    + cap_over_so * self.penalties.so_cap_penalty_rate
                )
                total_cap_violations = cap_over_sw + cap_over_so

                tw_penalty = 0.0
                time_warp_mins = 0.0
                if loc in self.time_windows:
                    earliest, latest = self.time_windows[loc]
                    if current_time_forward > latest:
                        warp = current_time_forward - latest
                        if not self.penalties.allow_time_warp:
                            break
                        time_warp_mins += warp
                        tw_penalty += warp * self.penalties.tw_penalty_rate
                        current_time_forward = latest
                    elif current_time_forward < earliest:
                        current_time_forward = earliest

                return_dur = self._get_distance(distance_matrix, loc, depot)
                total_route_dur = curr_travel_time + return_dur
                if total_route_dur > self.max_duration:
                    if self.penalties.allow_time_warp:
                        duration_warp = total_route_dur - self.max_duration
                        time_warp_mins += duration_warp
                        tw_penalty += duration_warp * self.penalties.tw_penalty_rate
                    else:
                        break

                trip_base_cost = total_route_dur
                trip_penalty = cap_penalty + tw_penalty
                trip_objective = trip_base_cost + trip_penalty
                new_total_objective = objective[i] + trip_objective

                if new_total_objective < objective[j + 1]:
                    objective[j + 1] = new_total_objective
                    base_cost[j + 1] = base_cost[i] + trip_base_cost
                    penalty_cost[j + 1] = penalty_cost[i] + trip_penalty
                    predecessor[j + 1] = i
                    tw_violations[j + 1] = tw_violations[i] + time_warp_mins
                    cap_violations[j + 1] = cap_violations[i] + total_cap_violations
                    dep_time = 480
                    if self.direction == "pickup" and self.target_time:
                        dep_time = max(0, self.target_time - int(total_route_dur) - self.offset_minutes)
                    elif self.direction == "dropoff" and self.target_time:
                        dep_time = self.target_time
                    best_schedule[j + 1] = {
                        "departure_time": max(0, dep_time),
                        "tw_violations": time_warp_mins,
                        "cap_violations": total_cap_violations,
                    }

                prev_loc = loc

        routes: List[List[str]] = []
        schedules: List[Dict] = []
        curr = n
        while curr > 0:
            prev = predecessor[curr]
            if prev == -1:
                return LinearSplitResult([], float("inf"), float("inf"), float("inf"), -1, -1, 0, [])
            sub_route = giant_tour[prev:curr]
            routes.append(sub_route)
            if best_schedule[curr]:
                sched = copy.deepcopy(best_schedule[curr])
                sched["locations"] = sub_route
                schedules.append(sched)
            curr = prev

        routes.reverse()
        schedules.reverse()
        return LinearSplitResult(
            routes=routes,
            total_cost_=base_cost[n],
            total_penalty_=penalty_cost[n],
            final_objective=objective[n],
            time_window_violations=tw_violations[n],
            capacity_violations=cap_violations[n],
            num_vehicles=len(routes),
            schedules=schedules,
        )


def _normalize_direction(direction: object) -> str:
    raw = getattr(direction, "value", None) or getattr(direction, "name", None) or str(direction)
    raw = str(raw).lower()
    return "dropoff" if "drop" in raw else "pickup"


__all__ = ["PenaltyConfig", "LinearSplitResult", "LinearSplitDecoder"]
