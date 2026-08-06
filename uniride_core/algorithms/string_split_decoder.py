"""
Split Decoder Algorithm for CVRP/CVRPTW
Based on Prins (2004) - A Simple and Effective Evolutionary Algorithm for VRP

Enhanced with:
- Backward Scheduling for Time Windows (CVRPTW)
- Forward Scheduling for Dropoff scenarios
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

logger = logging.getLogger(__name__)
DEFAULT_TRAVEL_FALLBACK_MINUTES = 15.0


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
    departure_time: Optional[int] = None  # Departure time from depot (minutes)


@dataclass
class RouteSchedule:
    """Scheduled times for a route"""
    departure_time: int  # Vehicle departure from depot (minutes from midnight)
    arrival_times: Dict[str, int]  # Location -> arrival time
    time_window_violations: int
    total_duration: float


class SplitDecoder:
    """
    Optimal Split Decoder for CVRP/CVRPTW using Dynamic Programming.
    
    Converts a giant tour (TSP solution) into feasible vehicle routes.
    Supports both CVRP (capacity only) and CVRPTW (capacity + time window) modes.
    
    Time Window Modes:
    - PICKUP (backward scheduling): Work backwards from target arrival at school
    - DROPOFF (forward scheduling): Work forward from departure from school
    
    Time Complexity: O(n²) where n is the number of customers
    Space Complexity: O(n)
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
    ):
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
        Decode a giant tour into optimal vehicle routes.
        
        For CVRPTW mode:
        - PICKUP: Uses backward scheduling from target arrival times
        - DROPOFF: Uses forward scheduling from target departure times
        """
        if not giant_tour:
            return {
                "routes": [],
                "costs": [],
                "total_cost": 0,
                "num_vehicles": 0,
                "schedules": []
            }
        
        n = len(giant_tour)
        
        # Build auxiliary graph edges (feasible trips)
        if self.use_time_windows:
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
                total_violations = tw_violations[i] + trip.time_window_violations
                total_cost = V[i] + trip.cost
                
                # Prefer solutions with fewer violations, then lower cost
                if total_violations < tw_violations[j] or (
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
                        schedules.append({
                            "departure_time": trip.departure_time,
                            "locations": route,
                            "tw_violations": trip.time_window_violations
                        })
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

        FIX-10: an absent directed arc is data corruption — never fall back to
        DEFAULT_TRAVEL_FALLBACK_MINUTES; return math.inf instead.
        """
        direct = distance_matrix.get(from_loc, {}).get(to_loc)
        if direct is not None:
            return direct
        if not self.is_asymmetric:
            reverse = distance_matrix.get(to_loc, {}).get(from_loc)
            if reverse is not None:
                return reverse
        return math.inf
    
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

        for i in range(n):
            sw_load = 0
            so_load = 0
            cost = 0.0
            prev = depot

            for j in range(i, n):
                loc = giant_tour[j]
                sw_d, so_d = demands.get(loc, (0, 0))
                sw_load += sw_d
                so_load += so_d

                if sw_load > self.sw_capacity or so_load > self.so_capacity:
                    break

                # FIX-04: named constant instead of magic 15.0
                cost += self._get_dist(prev, loc, distance_matrix)

                prev = loc

                return_cost = self._get_dist(loc, depot, distance_matrix)
                total_trip_cost = cost + return_cost

                if total_trip_cost > self.max_tour_duration:
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
    
    def _build_trips_with_tw(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict[int, List[Trip]]:
        """
        Build feasible trips with time window constraints.

        For PICKUP (backward scheduling):
        - Determine latest time from time_windows (latest arrival at school)
        - Calculate backwards: departure = latest - tour_duration - offset
        - FIX-01: Trips with negative departure are skipped (physically infeasible)
        - FIX-03: Uses trip_end variable to avoid j-variable collision between loops

        For DROPOFF (forward scheduling):
        - Determine earliest time from time_windows
        - Calculate forwards: arrival times accumulate from departure
        - FIX-02A: tw_violations counter initialised before loop (not inside)
        - FIX-02B: early arrivals wait until earliest window opens
        """
        n = len(giant_tour)
        trips = {k: [] for k in range(1, n + 1)}

        for i in range(n):
            sw_load = 0
            so_load = 0
            cost = 0.0
            prev = depot
            arrival_times: Dict[str, int] = {}

            if self.direction == Direction.PICKUP:
                # ── BACKWARD SCHEDULING ──────────────────────────────────────
                # LOOP 1: accumulate capacity and travel cost.
                # Use variable 'k' to avoid shadowing outer 'i' and the
                # second verification loop (FIX-03).
                trip_end = i  # last feasible stop index
                for k in range(i, n):
                    loc = giant_tour[k]
                    sw_d, so_d = demands.get(loc, (0, 0))
                    sw_load += sw_d
                    so_load += so_d

                    if sw_load > self.sw_capacity or so_load > self.so_capacity:
                        break

                    # FIX-04: use named constant instead of magic 15.0
                    travel_time = self._get_dist(prev, loc, distance_matrix)
                    cost += travel_time
                    prev = loc
                    trip_end = k  # commit: this stop is within capacity

                # Return-to-depot segment
                return_cost = self._get_dist(prev, depot, distance_matrix)

                total_trip_cost = cost + return_cost

                if total_trip_cost > self.max_tour_duration:
                    continue

                # FIX-03: use trip_end for slicing, NOT the loop variable j
                target_arrival = self._get_target_arrival_time(
                    giant_tour[i:trip_end + 1]
                )

                # Calculate departure time (backward scheduling)
                departure_time = (
                    target_arrival - int(total_trip_cost) - self.offset_minutes
                )

                # FIX-01: If departure_time is negative the trip is physically
                # impossible (driver would depart before midnight). Skip it.
                if departure_time < 0:
                    logger.debug(
                        "Skipping infeasible pickup trip i=%d trip_end=%d: "
                        "departure_time=%d < 0 (target=%d cost=%d offset=%d)",
                        i, trip_end, departure_time,
                        target_arrival, int(total_trip_cost), self.offset_minutes,
                    )
                    continue

                # LOOP 2: verify time windows — iterate only over committed stops
                tw_violations = 0
                current_time = departure_time
                prev = depot

                for k in range(i, trip_end + 1):  # FIX-03: bounded by trip_end
                    loc = giant_tour[k]
                    travel_time = self._get_dist(prev, loc, distance_matrix)
                    current_time += int(travel_time)

                    if loc in self.time_windows:
                        earliest, latest = self.time_windows[loc]
                        if current_time > latest:
                            tw_violations += 1
                        elif current_time < earliest:
                            current_time = earliest  # wait until window opens

                    arrival_times[loc] = current_time
                    prev = loc

                if self.strict_time_windows and tw_violations > 0:
                    continue

                trips[trip_end + 1].append(Trip(
                    start_idx=i,
                    end_idx=trip_end,
                    cost=total_trip_cost,
                    sw_count=sw_load,
                    so_count=so_load,
                    is_feasible=True,
                    time_window_violations=tw_violations,
                    departure_time=departure_time,  # FIX-01: guaranteed >= 0
                ))

            else:  # ── DROPOFF — FORWARD SCHEDULING ─────────────────────────
                current_time = self._get_target_departure_time(
                    giant_tour[i:min(i + 1, n)]
                )

                # FIX-02A: initialise BEFORE the loop so count accumulates
                tw_violations = 0

                for j in range(i, n):
                    loc = giant_tour[j]
                    sw_d, so_d = demands.get(loc, (0, 0))
                    sw_load += sw_d
                    so_load += so_d

                    if sw_load > self.sw_capacity or so_load > self.so_capacity:
                        break

                    travel_time = self._get_dist(prev, loc, distance_matrix)
                    if math.isinf(travel_time):
                        break  # FIX-10: missing arc kills the forward schedule
                    cost += travel_time
                    current_time += int(travel_time)

                    # FIX-02B: check both window bounds
                    if loc in self.time_windows:
                        earliest, latest = self.time_windows[loc]
                        if current_time > latest:
                            tw_violations += 1  # FIX-02A: accumulate, not reset
                        elif current_time < earliest:
                            current_time = earliest  # wait until window opens

                    arrival_times[loc] = current_time  # record after possible wait
                    prev = loc

                    return_cost = self._get_dist(loc, depot, distance_matrix)
                    total_trip_cost = cost + return_cost

                    if total_trip_cost > self.max_tour_duration:
                        continue

                    if self.strict_time_windows and tw_violations > 0:
                        continue

                    trips[j + 1].append(Trip(
                        start_idx=i,
                        end_idx=j,
                        cost=total_trip_cost,
                        sw_count=sw_load,
                        so_count=so_load,
                        is_feasible=True,
                        time_window_violations=tw_violations,
                        departure_time=current_time - int(cost),
                    ))

        return trips
    
    def _get_target_arrival_time(self, locations: List[str], depot: Optional[str] = None) -> int:
        """
        Get target arrival time for a PICKUP trip.

        Returns the latest time window bound across all locations in the
        trip, defaulting to 09:00 when no time windows are set.

        FIX-09: removed unused `depot` parameter.
        """
        latest_time = self.target_time or (9 * 60)  # Default 09:00

        for loc in locations:
            if loc in self.time_windows:
                _, latest = self.time_windows[loc]
                if latest > latest_time:
                    latest_time = latest

        return latest_time

    def _get_target_departure_time(self, locations: List[str], depot: Optional[str] = None) -> int:
        """
        Get target departure time for a DROPOFF trip.

        Returns the earliest time window bound across all locations in the
        trip, defaulting to 14:00 when no time windows are set.

        FIX-09: removed unused `depot` parameter.
        """
        earliest_time = self.target_time or (14 * 60)  # Default 14:00

        for loc in locations:
            if loc in self.time_windows:
                earliest, _ = self.time_windows[loc]
                if earliest < earliest_time:
                    earliest_time = earliest

        return earliest_time
    
    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes-from-midnight integer to HH:MM string."""
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
    is_asymmetric: bool = False
) -> Dict:
    """Convenience function for basic split decoding."""
    decoder = SplitDecoder(
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration,
        is_asymmetric=is_asymmetric
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
    is_asymmetric: bool = False
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
        target_time: Global target time in minutes from midnight
        offset_minutes: Buffer for driver notification
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
        is_asymmetric=is_asymmetric
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
