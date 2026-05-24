"""
Linear-Time (Bounded O(N*B)) Split Decoder with Time-Warp & Capacity Penalties
Based on SOTA 2024 VRP hybrid algorithms (Vidal et al. HGS principles).

Features:
- Bounded inner loop: complexity O(N*B) where B is the max reasonable stops per vehicle (approximates O(N)).
- Time-Warp Penalty: Instead of throwing away routes that miss a TW, it applies a dynamic cost penalty (allows searching wider solution spaces).
- Soft Capacity: Allows slight multi-capacity overloads (Sw/So) parameterized by a heavy penalty, essential for Genetic Algorithm diversification.
"""

import copy
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from models.schemas import Direction

@dataclass
class PenaltyConfig:
    """Dynamic penalty configurations for soft constraint relaxation"""
    allow_time_warp: bool = True
    tw_penalty_rate: float = 10.0      # Cost per minute exactly outside the time window
    
    allow_capacity_overflow: bool = True
    sw_cap_penalty_rate: float = 100.0 # Huge penalty per extra wheelchair needed
    so_cap_penalty_rate: float = 50.0  # Penalty per extra walking student needed
    
    max_stops_bounded: int = 15        # (B parameter) Bounding the forward search to achieve O(N)


@dataclass
class LinearSplitResult:
    routes: List[List[str]]
    total_cost_: float             # Cost WITHOUT penalties 
    total_penalty_: float          # Just the applied penalties
    final_objective: float         # total_cost_ + total_penalty_
    time_window_violations: float  # Cumulative minutes of time warp
    capacity_violations: int       # Total passenger overflow
    num_vehicles: int
    schedules: List[Dict]          # Calculated departure times


class LinearSplitDecoder:
    """
    O(N) Split Algorithm through bounded sequence (Max Stops = B).
    Includes Time-Warp (Infeasibility Relaxation) enabling Genetic Algorithms to cross the "infeasible valley".
    """
    
    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_duration: float = 120.0,
        time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        direction: Direction = Direction.PICKUP,
        target_time: Optional[int] = None,
        offset_minutes: int = 10,
        penalty_config: Optional[PenaltyConfig] = None
    ):
        self.sw_cap = sw_capacity
        self.so_cap = so_capacity
        self.max_duration = max_tour_duration
        self.time_windows = time_windows or {}
        self.direction = direction
        self.target_time = target_time
        self.offset_minutes = offset_minutes
        self.penalties = penalty_config or PenaltyConfig()

    def _get_distance(self, dist_matrix: dict, fr: str, to: str) -> float:
        return dist_matrix.get(fr, {}).get(to, 15.0)

    def decode(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> LinearSplitResult:
        if not giant_tour:
            return LinearSplitResult([], 0, 0, 0, 0, 0, 0, [])

        n = len(giant_tour)
        
        # Bellman DP Arrays
        # V[i] is the minimum objective (cost + penalties) to route the first i nodes of the giant tour.
        V = [float('inf')] * (n + 1)
        V[0] = 0.0
        
        # Keep track of pure base costs and pure penalties to reconstruct route data
        BaseCost = [0.0] * (n + 1)
        PenaltyCost = [0.0] * (n + 1)
        
        # For route reconstruction
        predecessor = [-1] * (n + 1)
        
        # Detailed tracking for each node
        tw_viols_arr = [0.0] * (n + 1)
        cap_viols_arr = [0] * (n + 1)
        best_sched_arr = [None] * (n + 1)

        # O(N) bounded loop: for each node i in the giant tour...
        for i in range(n):
            if V[i] == float('inf'):
                continue
                
            curr_sw, curr_so = 0, 0
            curr_travel_time = 0.0
            prev_loc = depot
            
            # Forward simulation variables for Time Windows
            # For simplicity in this O(N*B) forward DP, we accumulate Forward Time Warp
            current_time_forward = 480  # Default 08:00 if no time target
            if self.direction == Direction.DROPOFF and self.target_time:
                current_time_forward = self.target_time
            
            # Bound the forward look by max stops (B) -> O(N*B) ~ O(N)
            limit = min(n, i + self.penalties.max_stops_bounded)
            
            for j in range(i, limit):
                loc = giant_tour[j]
                d_sw, d_so = demands.get(loc, (0, 0))
                
                curr_sw += d_sw
                curr_so += d_so
                
                leg_dist = self._get_distance(distance_matrix, prev_loc, loc)
                curr_travel_time += leg_dist
                current_time_forward += int(leg_dist)
                
                # Capacity Penalties
                cap_over_sw = max(0, curr_sw - self.sw_cap)
                cap_over_so = max(0, curr_so - self.so_cap)
                
                if not self.penalties.allow_capacity_overflow and (cap_over_sw > 0 or cap_over_so > 0):
                    break # Strict mode: edge is completely infeasible, stop extending
                    
                cap_penalty = (cap_over_sw * self.penalties.sw_cap_penalty_rate) + \
                              (cap_over_so * self.penalties.so_cap_penalty_rate)
                total_cap_violations = cap_over_sw + cap_over_so
                
                # Time Warp Penalty Calculation (Forward approximation for DP)
                tw_penalty = 0.0
                time_warp_mins = 0.0
                
                if loc in self.time_windows:
                    earliest, latest = self.time_windows[loc]
                    if current_time_forward > latest:
                        # We are late! This is a time-warp gap
                        warp = current_time_forward - latest
                        if not self.penalties.allow_time_warp:
                            break # Strict mode: abort extension
                        time_warp_mins += warp
                        tw_penalty += warp * self.penalties.tw_penalty_rate
                        # In time-warp, we mathematically 'warp' time back to the upper bound
                        # to allow visiting future nodes without cascading infinite delay
                        current_time_forward = latest 
                    elif current_time_forward < earliest:
                        # Wait time (not a penalty, just operational idle time)
                        current_time_forward = earliest
                
                # Add return to depot to finalize the sub-route (i to j)
                return_dur = self._get_distance(distance_matrix, loc, depot)
                total_route_dur = curr_travel_time + return_dur
                
                # Max Duration Check limits the size of the route
                if total_route_dur > self.max_duration:
                    if self.penalties.allow_time_warp:
                        duration_warp = total_route_dur - self.max_duration
                        time_warp_mins += duration_warp
                        tw_penalty += duration_warp * self.penalties.tw_penalty_rate
                    else:
                        break # Strict abort
                
                # Total Objective for this sub-route
                trip_base_cost = total_route_dur
                trip_penalty = cap_penalty + tw_penalty
                trip_objective = trip_base_cost + trip_penalty
                
                new_total_objective = V[i] + trip_objective
                
                # Bellman optimal substructure update
                if new_total_objective < V[j + 1]:
                    V[j + 1] = new_total_objective
                    BaseCost[j + 1] = BaseCost[i] + trip_base_cost
                    PenaltyCost[j + 1] = PenaltyCost[i] + trip_penalty
                    predecessor[j + 1] = i
                    tw_viols_arr[j + 1] = tw_viols_arr[i] + time_warp_mins
                    cap_viols_arr[j + 1] = cap_viols_arr[i] + total_cap_violations
                    
                    # Schedule tracking (Simplified Departure Approximation)
                    dep_time = 0
                    if self.direction == Direction.PICKUP and self.target_time:
                        dep_time = self.target_time - int(total_route_dur) - self.offset_minutes
                    else:
                        dep_time = 480 # 08:00
                    
                    best_sched_arr[j + 1] = {
                        "departure_time": max(0, dep_time),
                        "tw_violations": time_warp_mins,
                        "cap_violations": total_cap_violations
                    }

                prev_loc = loc

        # DP Resolution / Route Construction
        routes = []
        schedules = []
        curr = n
        
        while curr > 0:
            prev = predecessor[curr]
            if prev == -1:
                # Failed to completely decode (should not happen if soft penalties are active)
                # Fallback return structure
                return LinearSplitResult([], float('inf'), float('inf'), float('inf'), -1, -1, 0, [])
                
            sub_route = giant_tour[prev:curr]
            routes.append(sub_route)
            
            if best_sched_arr[curr]:
                sched = copy.deepcopy(best_sched_arr[curr])
                sched["locations"] = sub_route
                schedules.append(sched)
                
            curr = prev
            
        # The Bellman builds it backwards (last node to first node)
        routes.reverse()
        schedules.reverse()
        
        return LinearSplitResult(
            routes=routes,
            total_cost_=BaseCost[n],
            total_penalty_=PenaltyCost[n],
            final_objective=V[n],
            time_window_violations=tw_viols_arr[n],
            capacity_violations=cap_viols_arr[n],
            num_vehicles=len(routes),
            schedules=schedules
        )
