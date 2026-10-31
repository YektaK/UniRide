"""
Split Decoder Algorithm for CVRP/CVRPTW
Based on Prins (2004) - A Simple and Effective Evolutionary Algorithm for VRP

Enhanced with:
- Time windows (CVRPTW) timed by the route simulator ``route_schedule`` (MT1-05):
  pickup departs as late as possible and must reach the school by
  ``target_time - offset_minutes``; drop-off leaves the school at
  ``target_time + offset_minutes``; waits and service count in tour and ride time
- Direction-aware route planning

Reference:
Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem.
Computers & Operations Research, 31(12), 1985-2002.
"""

import logging
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from uniride_core.algorithms.route_schedule import (
    DEADLINE,
    WINDOW,
    RouteSchedule as SimulatedSchedule,
    simulate_school_dropoff,
    simulate_school_pickup,
)

logger = logging.getLogger(__name__)


def _is_depot(node: object, depot: object) -> bool:
    try:
        return int(node) == int(depot)
    except (TypeError, ValueError):
        return str(node) == str(depot)


def _split_depot_segments(giant_tour: List[str], depot: object) -> List[List[str]]:
    """Split a giant tour at interior depot occurrences into depot-free segments.

    A depot revisit marks a route boundary: the vehicle returns to base, so the
    next directed arc must begin at the depot. The depot node itself is never a
    route stop.
    """
    segments: List[List[str]] = []
    current: List[str] = []
    for node in giant_tour:
        if _is_depot(node, depot):
            if current:
                segments.append(current)
                current = []
        else:
            current.append(node)
    if current:
        segments.append(current)
    return segments


def _merge_segment_results(results: List[Dict]) -> Dict:
    """Merge the decode() dicts of depot-separated sub-tours."""
    routes: List[List[str]] = []
    costs: List[float] = []
    schedules: List[Dict] = []
    total_cost = 0.0
    num_vehicles = 0
    tw_violations = 0
    for res in results:
        routes.extend(res.get("routes", []))
        costs.extend(res.get("costs", []))
        schedules.extend(res.get("schedules", []))
        total_cost += res.get("total_cost", 0) if res.get("total_cost") is not None else 0
        num_vehicles += res.get("num_vehicles", 0)
        tw_violations += res.get("time_window_violations", 0)
    merged = {
        "routes": routes,
        "costs": costs,
        "total_cost": total_cost,
        "num_vehicles": num_vehicles,
        "time_window_violations": tw_violations,
    }
    if schedules:
        merged["schedules"] = schedules
    return merged


class Direction(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"


@dataclass
class Trip:
    """Represents a feasible trip from customer i to j"""
    start_idx: int  # Start index in giant tour (0-based)
    end_idx: int    # End index in giant tour (inclusive)
    cost: float     # Trip cost (duration/distance)
    sw_count: int   # Wheelchair passengers
    so_count: int   # Other disability passengers
    is_feasible: bool
    time_window_violations: int = 0  # Number of TW violations
    departure_time: Optional[float] = None  # Departure time from depot (minutes, exact)
    schedule: Optional[SimulatedSchedule] = None  # simulator result (time-window mode)


@dataclass
class RouteSchedule:
    """Scheduled times for a route"""
    departure_time: int  # Vehicle departure from depot (minutes from midnight)
    arrival_times: Dict[str, int]  # Location -> arrival time
    time_window_violations: int
    total_duration: float


class SplitDecoder:
    """
    Split Decoder for CVRP/CVRPTW using Dynamic Programming (Prins 2004).
    
    Converts a giant tour (TSP solution) into feasible vehicle routes.
    Supports both CVRP (capacity only) and CVRPTW (capacity + time window) modes.
    
    Time Window Modes (every candidate trip is timed by ``route_schedule``):
    - PICKUP: latest feasible departure; the school must be reached by
      ``target_time - offset_minutes`` (hard deadline)
    - DROPOFF: leave the school at ``target_time + offset_minutes``
    ``target_time`` is required in time-window mode (no 09:00 / 14:00 default).
    The tour limit (``max_tour_duration``) and the ride limit count waiting and
    service; the trip cost the DP minimises stays the pure travel time.

    Time Complexity (n = customers, L = max customers per route, bounded by
    capacity): CVRP mode O(n*L); time-window modes O(n*L^2) (one simulation per
    candidate trip), worst case O(n^3) when L ~ n. Space: O(n*L) for the
    candidate trips.

    Optimality: only in CVRP mode (no time windows) is the result the
    minimum-cost partition of the given order (order preserved) under
    capacity / duration / ride-time limits. In the time-window modes the DP
    prefers fewer time-window violations first, then lower cost; this is not
    claimed to be a globally optimal split.
    """
    
    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_duration: float = 120.0,
        time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        use_time_windows: bool = False,
        direction: Direction = Direction.PICKUP,
        target_time: Optional[int] = None,
        offset_minutes: int = 10,
        is_asymmetric: bool = False,
        strict_time_windows: bool = False,
        max_ride_time: Optional[float] = None,
        stop_dwell_minutes: float = 0.0,
        sw_boarding_minutes: float = 0.0,
    ):
        # Service time (OQ-MT1-5 b), time-window mode only: every giant-tour node is
        # one stop and takes ``stop_dwell_minutes`` plus ``sw_boarding_minutes`` when
        # its demand has a Sw part. Both default to 0 (no effect).
        for name, value in (
            ("stop_dwell_minutes", stop_dwell_minutes),
            ("sw_boarding_minutes", sw_boarding_minutes),
        ):
            if not (math.isfinite(value) and value >= 0):
                raise ValueError(f"{name} must be a finite number >= 0, got {value!r}")
        self.stop_dwell_minutes = float(stop_dwell_minutes)
        self.sw_boarding_minutes = float(sw_boarding_minutes)
        # Per-student maximum ride time (minutes).  ``None`` = no limit, which
        # leaves every pre-existing behaviour unchanged.  Definitions (route =
        # depot -> s1..sk -> depot, no waiting):
        #   pickup : longest ride = first student's = arcs s1->..->sk->depot
        #   dropoff: longest ride = last student's  = arcs depot->s1->..->sk
        # In the time-window path the simulator's ride time (waits and service
        # after boarding included) is used.
        if max_ride_time is not None and not (max_ride_time > 0):
            raise ValueError(f"max_ride_time must be positive, got {max_ride_time!r}")
        self.max_ride_time = max_ride_time
        self.sw_capacity = sw_capacity
        self.so_capacity = so_capacity
        self.max_tour_duration = max_tour_duration
        self.time_windows = time_windows or {}
        self.use_time_windows = use_time_windows
        self.direction = direction
        self.target_time = target_time
        self.offset_minutes = offset_minutes
        self.is_asymmetric = is_asymmetric
        self.strict_time_windows = strict_time_windows
    
    def decode(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]],  # location -> (sw_demand, so_demand)
        return_trip_details: bool = False
    ) -> Dict:
        """
        Decode a giant tour into vehicle routes (order preserved; optimal only in CVRP mode).
        
        For CVRPTW mode:
        - PICKUP: Uses backward scheduling from target arrival times
        - DROPOFF: Uses forward scheduling from target departure times
        """
        # FIX-12: split the giant tour at interior depot occurrences so a depot
        # revisit starts a new route whose first directed arc begins at the
        # depot (never a through-arc across the depot).
        segments = _split_depot_segments(giant_tour, depot)
        if len(segments) > 1:
            results = []
            merged_trips = {}
            offset = 0
            for seg in segments:
                res = self.decode(seg, depot, distance_matrix, demands, return_trip_details)
                results.append(res)
                if return_trip_details:
                    for k, v in res.get("trips", {}).items():
                        merged_trips[k + offset] = v
                offset += len(seg)
            merged = _merge_segment_results(results)
            if return_trip_details:
                merged["trips"] = merged_trips
            return merged

        giant_tour = segments[0] if segments else []
        if not giant_tour:
            return {
                "routes": [],
                "costs": [],
                "total_cost": 0,
                "num_vehicles": 0,
                "schedules": []
            }
        
        n = len(giant_tour)
        
        # Build auxiliary graph edges (feasible trips). Time-window mode needs an
        # anchor: windows without ``target_time`` raise ValueError in
        # ``_build_trips_with_tw``. With neither windows nor a target there is
        # nothing to enforce, so the capacity-only trips are used.
        if self.use_time_windows and (self.time_windows or self.target_time is not None):
            trips = self._build_trips_with_tw(giant_tour, depot, distance_matrix, demands)
        else:
            trips = self._build_trips(giant_tour, depot, distance_matrix, demands)
        
        # Dynamic programming for shortest path
        V = [float('inf')] * (n + 1)
        V[0] = 0
        predecessor = [-1] * (n + 1)
        tw_violations = [0] * (n + 1)
        
        for j in range(1, n + 1):
            for trip in trips[j]:
                i = trip.start_idx
                if not math.isfinite(V[i]):
                    continue
                total_violations = tw_violations[i] + trip.time_window_violations
                total_cost = V[i] + trip.cost
                
                # Prefer solutions with fewer violations, then lower cost
                if predecessor[j] == -1 or total_violations < tw_violations[j] or (
                    total_violations == tw_violations[j] and total_cost < V[j]
                ):
                    V[j] = total_cost
                    predecessor[j] = i
                    tw_violations[j] = total_violations
        
        # Reconstruct routes
        routes = []
        costs = []
        schedules = []
        current = n
        
        while current > 0:
            prev = predecessor[current]
            if prev == -1:
                fallback_routes = [[loc] for loc in giant_tour]
                return {
                    "routes": fallback_routes,
                    "costs": [float('inf')] * len(fallback_routes),
                    "total_cost": float('inf'),
                    "num_vehicles": len(fallback_routes),
                    "error": "No feasible splitting found",
                    "time_window_violations": tw_violations[n]
                }
            
            route = giant_tour[prev:current]
            routes.append(route)
            
            # Find trip details
            for trip in trips[current]:
                if trip.start_idx == prev:
                    costs.append(trip.cost)
                    if trip.departure_time is not None:
                        entry = {
                            "departure_time": trip.departure_time,
                            "locations": route,
                            "tw_violations": trip.time_window_violations
                        }
                        if trip.schedule is not None:
                            entry["end"] = trip.schedule.end
                            entry["arrivals"] = dict(zip(route, trip.schedule.arrivals))
                            entry["waits"] = dict(zip(route, trip.schedule.waits))
                        schedules.append(entry)
                    break
            
            current = prev
        
        # Reverse to get correct order
        routes = routes[::-1]
        costs = costs[::-1]
        schedules = schedules[::-1]
        
        result = {
            "routes": routes,
            "costs": costs,
            "total_cost": V[n],
            "num_vehicles": len(routes),
            "time_window_violations": tw_violations[n]
        }
        
        if schedules:
            result["schedules"] = schedules
        
        if return_trip_details:
            result["trips"] = trips
        
        return result

    def _get_dist(
        self,
        from_loc: str,
        to_loc: str,
        distance_matrix: Dict[str, Dict[str, float]],
    ) -> float:
        """Get distance between two locations, respecting ATSP asymmetry.

        FIX-10: an absent directed arc is data corruption — never substitute a
        default travel time; return math.inf instead.
        """
        direct = distance_matrix.get(from_loc, {}).get(to_loc)
        if direct is not None:
            return direct
        if not self.is_asymmetric:
            reverse = distance_matrix.get(to_loc, {}).get(from_loc)
            if reverse is not None:
                return reverse
        return math.inf
    
    def _ride_direction_is_dropoff(self) -> bool:
        value = getattr(self.direction, "value", self.direction)
        return str(value).strip().lower() == "dropoff"

    def _build_trips(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict[int, List[Trip]]:
        """Build all feasible trips (capacity only, no time windows)."""
        n = len(giant_tour)
        trips = {j: [] for j in range(1, n + 1)}

        dropoff = self._ride_direction_is_dropoff()

        for i in range(n):
            sw_load = 0
            so_load = 0
            cost = 0.0
            tail = 0.0  # arcs after the first stop (pickup: ride = tail + closing arc)
            prev = depot

            for j in range(i, n):
                loc = giant_tour[j]
                sw_d, so_d = demands.get(loc, (0, 0))
                sw_load += sw_d
                so_load += so_d

                if sw_load > self.sw_capacity or so_load > self.so_capacity:
                    break

                arc = self._get_dist(prev, loc, distance_matrix)
                cost += arc
                if j > i:
                    tail += arc

                prev = loc

                return_cost = self._get_dist(loc, depot, distance_matrix)
                total_trip_cost = cost + return_cost

                if total_trip_cost > self.max_tour_duration:
                    continue

                if self.max_ride_time is not None:
                    # pickup: first student rides s1->..->sk->depot;
                    # dropoff: last student rides depot->s1->..->sk.
                    longest_ride = cost if dropoff else tail + return_cost
                    if not (longest_ride <= self.max_ride_time):
                        continue

                trips[j + 1].append(Trip(
                    start_idx=i,
                    end_idx=j,
                    cost=total_trip_cost,
                    sw_count=sw_load,
                    so_count=so_load,
                    is_feasible=True,
                ))

        return trips
    
    def _service_inputs(
        self,
        nodes: List[str],
        demands: Dict[str, Tuple[int, int]],
    ) -> Tuple[Dict[str, float], Dict[str, int]]:
        """Per-stop service minutes and Sw counts for the simulator."""
        service = {node: self.stop_dwell_minutes for node in nodes}
        sw_counts = {node: 1 if demands.get(node, (0, 0))[0] > 0 else 0 for node in nodes}
        return service, sw_counts

    def _simulate_trip(
        self,
        nodes: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]],
    ) -> Tuple[SimulatedSchedule, int]:
        """Time one candidate trip on the route simulator.

        Returns the schedule and the number of violations it carries: window and
        deadline violations plus one per stop whose own window is empty (opens after
        it closes, so no schedule can meet it). Day-boundary violations are not
        counted here; the caller drops such a trip (physically impossible).
        """
        windows: Dict[str, Tuple[float, float]] = {}
        empty_windows = 0
        for node in nodes:
            if node in self.time_windows:
                earliest, latest = self.time_windows[node]
                if earliest > latest:
                    empty_windows += 1
                else:
                    windows[node] = (float(earliest), float(latest))
        service, sw_counts = self._service_inputs(nodes, demands)

        def arc(a: str, b: str) -> float:
            return self._get_dist(a, b, distance_matrix)

        target = float(self.target_time)
        offset = float(self.offset_minutes)
        if self.direction == Direction.PICKUP:
            schedule = simulate_school_pickup(
                nodes, arc, deadline=target - offset, windows=windows,
                service=service, sw_boarding=self.sw_boarding_minutes,
                sw_counts=sw_counts, depot=depot,
            )
        else:
            schedule = simulate_school_dropoff(
                nodes, arc, ready=target + offset, windows=windows,
                service=service, sw_boarding=self.sw_boarding_minutes,
                sw_counts=sw_counts, depot=depot,
            )
        counted = sum(1 for v in schedule.violations if v.kind in (WINDOW, DEADLINE))
        return schedule, counted + empty_windows

    def _build_trips_with_tw(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict[int, List[Trip]]:
        """
        Build candidate trips with time-window constraints (MT1-05).

        Every capacity-feasible trip i..k is timed by the route simulator
        (``simulate_school_pickup`` / ``simulate_school_dropoff``, exact floats, no
        truncation, return arc included):

        - PICKUP: depart as late as possible; the school must be reached by
          ``target_time - offset_minutes`` (hard deadline, counted as a violation).
        - DROPOFF: leave the school at ``target_time + offset_minutes`` and wait where
          a window opens later.

        A trip is dropped when its travel or its tour (waits and service included)
        exceeds ``max_tour_duration``, when a ride (waits and service after boarding
        included) exceeds ``max_ride_time``, when the schedule starts before 00:00 or
        ends after 24:00 (FIX-01), when an arc is missing (FIX-10), and in strict
        mode when it has any violation. In soft mode it is kept with its violation
        count. ``Trip.cost`` is the pure travel time including the return arc.

        ``target_time`` is required: without it the anchor would be invented, so a
        ``ValueError`` is raised.
        """
        if self.target_time is None:
            raise ValueError(
                "time-window decoding requires target_time (no default anchor)"
            )
        n = len(giant_tour)
        trips = {k: [] for k in range(1, n + 1)}
        tolerance = 1e-9

        for i in range(n):
            sw_load = 0
            so_load = 0
            cost = 0.0
            prev = depot

            for k in range(i, n):
                loc = giant_tour[k]
                sw_d, so_d = demands.get(loc, (0, 0))
                sw_load += sw_d
                so_load += so_d
                if sw_load > self.sw_capacity or so_load > self.so_capacity:
                    break
                travel_time = self._get_dist(prev, loc, distance_matrix)
                if math.isinf(travel_time):
                    break  # FIX-10: missing arc means this prefix is unusable
                cost += travel_time
                prev = loc

                closing_arc = self._get_dist(loc, depot, distance_matrix)
                if math.isinf(closing_arc):
                    continue
                total_trip_cost = cost + closing_arc
                if total_trip_cost > self.max_tour_duration:
                    continue

                schedule, tw_violations = self._simulate_trip(
                    giant_tour[i:k + 1], depot, distance_matrix, demands
                )
                if any(v.kind not in (WINDOW, DEADLINE) for v in schedule.violations):
                    continue  # FIX-01: before midnight / after the day end
                if schedule.tour > self.max_tour_duration + tolerance:
                    continue  # waits and service count in the tour
                if self.strict_time_windows and tw_violations > 0:
                    continue
                if self.max_ride_time is not None and not (
                    max(schedule.ride_times) <= self.max_ride_time + tolerance
                ):
                    continue

                trips[k + 1].append(Trip(
                    start_idx=i,
                    end_idx=k,
                    cost=total_trip_cost,
                    sw_count=sw_load,
                    so_count=so_load,
                    is_feasible=True,
                    time_window_violations=tw_violations,
                    departure_time=schedule.start,
                    schedule=schedule,
                ))

        return trips

    def _minutes_to_time(self, minutes: float) -> str:
        """Convert minutes from midnight to HH:MM (rounded down, OQ-MT1-10 b)."""
        minutes = int(math.floor(minutes + 1e-9))
        hours = (minutes // 60) % 24
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
    
    def decode_with_details(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict:
        """Decode with detailed output including route statistics and schedules."""
        result = self.decode(giant_tour, depot, distance_matrix, demands)
        
        if not result["routes"]:
            return result
        
        # Add detailed statistics
        detailed_routes = []
        for i, route in enumerate(result["routes"]):
            sw_count = sum(demands.get(loc, (0, 0))[0] for loc in route)
            so_count = sum(demands.get(loc, (0, 0))[1] for loc in route)
            
            # Calculate actual route segments
            route_stops = [depot] + route + [depot]
            segments = []
            for j in range(len(route_stops) - 1):
                from_loc = route_stops[j]
                to_loc = route_stops[j + 1]
                dur = self._get_dist(from_loc, to_loc, distance_matrix)
                segments.append({
                    "from": from_loc,
                    "to": to_loc,
                    "duration": dur
                })
            
            # Add schedule info if available
            schedule_info = {}
            if "schedules" in result and i < len(result["schedules"]):
                schedule = result["schedules"][i]
                schedule_info = {
                    "departure_time_minutes": schedule.get("departure_time"),
                    "departure_time_str": self._minutes_to_time(schedule.get("departure_time", 0))
                }
            
            detailed_routes.append({
                "route_index": i,
                "locations": route,
                "cost": result["costs"][i],
                "sw_count": sw_count,
                "so_count": so_count,
                "total_passengers": sw_count + so_count,
                "segments": segments,
                **schedule_info
            })
        
        result["detailed_routes"] = detailed_routes
        return result
        # FIX-05: second _minutes_to_time definition removed — single copy at line ~445


def decode_giant_tour(
    giant_tour: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int = 4,
    so_capacity: int = 5,
    max_tour_duration: float = 120.0,
    is_asymmetric: bool = False,
    max_ride_time: Optional[float] = None,
    direction: Direction = Direction.PICKUP,
) -> Dict:
    """Convenience function for basic split decoding.

    ``max_ride_time`` (minutes, ``None`` = unlimited) bounds every student's
    in-vehicle time; ``direction`` selects which end of the route is longest
    (see ``SplitDecoder.__init__``).
    """
    decoder = SplitDecoder(
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration,
        is_asymmetric=is_asymmetric,
        direction=direction,
        max_ride_time=max_ride_time,
    )
    return decoder.decode(giant_tour, depot, distance_matrix, demands)


def decode_with_time_windows(
    giant_tour: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    time_windows: Dict[str, Tuple[int, int]],
    direction: Direction = Direction.PICKUP,
    target_time: Optional[int] = None,
    offset_minutes: int = 10,
    sw_capacity: int = 4,
    so_capacity: int = 5,
    max_tour_duration: float = 120.0,
    is_asymmetric: bool = False,
    max_ride_time: Optional[float] = None,
    stop_dwell_minutes: float = 0.0,
    sw_boarding_minutes: float = 0.0,
) -> Dict:
    """
    Convenience function for CVRPTW decoding.
    
    Args:
        giant_tour: Ordered list of customer locations
        depot: Depot location code
        distance_matrix: Travel times/distances
        demands: Dict of location -> (sw_demand, so_demand)
        time_windows: Dict of location -> (earliest, latest) in minutes from midnight
        direction: PICKUP or DROPOFF
        target_time: Required. Anchor in minutes from midnight: pickup deadline is
            ``target_time - offset_minutes``, drop-off ready time ``target_time +
            offset_minutes``. ``None`` raises ``ValueError``.
        offset_minutes: Buffer (see target_time)
        stop_dwell_minutes / sw_boarding_minutes: service time per stop and extra
            per Sw stop (default 0)
        is_asymmetric: When True, respects asymmetric distance matrix (d(i,j) != d(j,i))
    
    Returns:
        Dict with routes, schedules, and time window info
    """
    decoder = SplitDecoder(
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration,
        time_windows=time_windows,
        use_time_windows=True,
        direction=direction,
        target_time=target_time,
        offset_minutes=offset_minutes,
        is_asymmetric=is_asymmetric,
        max_ride_time=max_ride_time,
        stop_dwell_minutes=stop_dwell_minutes,
        sw_boarding_minutes=sw_boarding_minutes,
    )
    return decoder.decode_with_details(giant_tour, depot, distance_matrix, demands)


# Test
if __name__ == "__main__":
    # Test CVRPTW
    depot = "D.Kampus"
    giant_tour = ["Sw1", "Sw2", "So1", "So2"]
    
    distance_matrix = {
        "D.Kampus": {"Sw1": 20, "Sw2": 25, "So1": 30, "So2": 35},
        "Sw1": {"D.Kampus": 20, "Sw2": 10, "So1": 15, "So2": 20},
        "Sw2": {"D.Kampus": 25, "Sw1": 10, "So1": 8, "So2": 12},
        "So1": {"D.Kampus": 30, "Sw1": 15, "Sw2": 8, "So2": 6},
        "So2": {"D.Kampus": 35, "Sw1": 20, "Sw2": 12, "So1": 6}
    }
    
    demands = {
        "Sw1": (1, 0), "Sw2": (1, 0), "So1": (0, 1), "So2": (0, 1)
    }
    
    time_windows = {
        "Sw1": (480, 540),  # 08:00 - 09:00
        "Sw2": (510, 540),  # 08:30 - 09:00
        "So1": (480, 540),
        "So2": (510, 540)
    }
    
    # Test PICKUP with backward scheduling
    result = decode_with_time_windows(
        giant_tour=giant_tour,
        depot=depot,
        distance_matrix=distance_matrix,
        demands=demands,
        time_windows=time_windows,
        direction=Direction.PICKUP,
        target_time=540,  # 09:00
        offset_minutes=10
    )
    
    print("CVRPTW Pickup Result")
    print("=" * 50)
    print(f"Total Cost: {result.get('total_cost', 0):.1f} minutes")
    print(f"Vehicles: {result.get('num_vehicles', 0)}")
    print(f"TW Violations: {result.get('time_window_violations', 0)}")
    
    for route in result.get('detailed_routes', []):
        print(f"\nRoute {route['route_index'] + 1}:")
        print(f"  Locations: {' -> '.join(route['locations'])}")
        print(f"  Departure: {route.get('departure_time_str', 'N/A')}")
        print(f"  Passengers: Sw={route['sw_count']}, So={route['so_count']}")
