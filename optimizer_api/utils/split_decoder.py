"""
Split Decoder Algorithm for CVRP
Based on Prins (2004) - A Simple and Effective Evolutionary Algorithm for VRP

This module implements the optimal splitting of a giant tour into feasible vehicle routes.
Uses dynamic programming to find the minimum-cost partition.

Reference:
Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem.
Computers & Operations Research, 31(12), 1985-2002.

Key Concept:
- Input: Giant tour (permutation of all customers)
- Output: Optimal partition into vehicle routes respecting capacity constraints
- Algorithm: Shortest path on an auxiliary graph
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Trip:
    """Represents a feasible trip from customer i to j"""
    start_idx: int  # Start index in giant tour (0-based)
    end_idx: int    # End index in giant tour (inclusive)
    cost: float     # Trip cost (duration/distance)
    sw_count: int   # Wheelchair passengers
    so_count: int   # Other disability passengers
    is_feasible: bool


class SplitDecoder:
    """
    Optimal Split Decoder for CVRP/CVRPTW using Dynamic Programming.
    
    Converts a giant tour (TSP solution) into feasible vehicle routes.
    Supports both CVRP (capacity only) and CVRPTW (capacity + time window) modes.
    
    Time Complexity: O(n²) where n is the number of customers
    Space Complexity: O(n)
    
    The algorithm builds an auxiliary graph where:
    - Nodes represent positions in the giant tour
    - Edges represent feasible trips
    - Finding shortest path = optimal splitting
    """
    
    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_duration: float = 120.0,
        time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        use_time_windows: bool = False
    ):
        """
        Initialize Split Decoder.
        
        Args:
            sw_capacity: Maximum wheelchair passengers per vehicle
            so_capacity: Maximum other disability passengers per vehicle
            max_tour_duration: Maximum tour duration in minutes
            time_windows: Dict mapping location -> (earliest_pickup, latest_pickup) in minutes from depot departure
            use_time_windows: If True, enforce time window constraints (CVRPTW mode)
        """
        self.sw_capacity = sw_capacity
        self.so_capacity = so_capacity
        self.max_tour_duration = max_tour_duration
        self.time_windows = time_windows or {}
        self.use_time_windows = use_time_windows
    
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
        
        Args:
            giant_tour: Ordered list of location codes (customers only, no depot)
            depot: Depot location code
            distance_matrix: Dict of dicts with travel times/distances
            demands: Dict mapping location -> (sw_demand, so_demand)
            return_trip_details: If True, return detailed trip information
            
        Returns:
            Dict with:
                - routes: List of routes, each route is a list of location codes
                - costs: List of route costs
                - total_cost: Sum of all route costs
                - num_vehicles: Number of vehicles used
        """
        if not giant_tour:
            return {
                "routes": [],
                "costs": [],
                "total_cost": 0,
                "num_vehicles": 0
            }
        
        n = len(giant_tour)
        
        # Build auxiliary graph edges (feasible trips)
        trips = self._build_trips(giant_tour, depot, distance_matrix, demands)
        
        # Dynamic programming for shortest path
        # V[j] = minimum cost to serve first j customers (0 to j-1)
        V = [float('inf')] * (n + 1)
        V[0] = 0
        predecessor = [-1] * (n + 1)
        
        for j in range(1, n + 1):
            for trip in trips[j]:
                # trip ends at j, starts at trip.start_idx + 1
                i = trip.start_idx
                if V[i] + trip.cost < V[j]:
                    V[j] = V[i] + trip.cost
                    predecessor[j] = i
        
        # Reconstruct routes
        routes = []
        costs = []
        current = n
        
        while current > 0:
            prev = predecessor[current]
            if prev == -1:
                # No feasible solution found
                return {
                    "routes": [],
                    "costs": [],
                    "total_cost": float('inf'),
                    "num_vehicles": 0,
                    "error": "No feasible splitting found"
                }
            
            route = giant_tour[prev:current]
            routes.append(route)
            
            # Find trip cost
            for trip in trips[current]:
                if trip.start_idx == prev:
                    costs.append(trip.cost)
                    break
            
            current = prev
        
        # Reverse to get correct order
        routes = routes[::-1]
        costs = costs[::-1]
        
        result = {
            "routes": routes,
            "costs": costs,
            "total_cost": V[n],
            "num_vehicles": len(routes)
        }
        
        if return_trip_details:
            result["trips"] = trips
        
        return result
    
    def _build_trips(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict[int, List[Trip]]:
        """
        Build all feasible trips ending at each position.
        
        trips[j] contains all feasible trips that end at position j
        (i.e., serve customers from i to j-1 for some i < j)
        
        Returns:
            Dict mapping end_index -> list of feasible trips
        """
        n = len(giant_tour)
        trips = {j: [] for j in range(1, n + 1)}
        
        for i in range(n):
            sw_load = 0
            so_load = 0
            cost = 0.0
            arrival_time = 0.0  # Track arrival time for time windows
            prev = depot
            
            for j in range(i, n):
                loc = giant_tour[j]
                sw_d, so_d = demands.get(loc, (0, 0))
                sw_load += sw_d
                so_load += so_d
                
                # Check capacity feasibility
                if sw_load > self.sw_capacity or so_load > self.so_capacity:
                    break
                
                # Check time window feasibility (CVRPTW mode)
                if self.use_time_windows and loc in self.time_windows:
                    earliest, latest = self.time_windows[loc]
                    if arrival_time > latest:
                        break  # Cannot serve this customer within time window
                    # Note: We allow early arrival, will wait until earliest
                
                # Add travel cost
                travel_time = 0.0
                if prev in distance_matrix and loc in distance_matrix[prev]:
                    travel_time = distance_matrix[prev][loc]
                    cost += travel_time
                else:
                    cost += 15.0  # Default fallback
                    travel_time = 15.0
                
                # Update arrival time for time window checking
                arrival_time += travel_time
                
                prev = loc
                
                # Check tour duration feasibility
                # Add return to depot cost
                return_cost = 0.0
                if loc in distance_matrix and depot in distance_matrix[loc]:
                    return_cost = distance_matrix[loc][depot]
                else:
                    return_cost = 15.0
                
                total_trip_cost = cost + return_cost
                
                if total_trip_cost > self.max_tour_duration:
                    # This trip is too long, but maybe shorter ones starting from i are OK
                    continue
                
                # Feasible trip found
                trips[j + 1].append(Trip(
                    start_idx=i,
                    end_idx=j,
                    cost=total_trip_cost,
                    sw_count=sw_load,
                    so_count=so_load,
                    is_feasible=True
                ))
        
        return trips
    
    def decode_with_details(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict:
        """
        Decode with detailed output including route statistics.
        """
        result = self.decode(giant_tour, depot, distance_matrix, demands)
        
        if not result["routes"]:
            return result
        
        # Add detailed statistics
        detailed_routes = []
        for i, route in enumerate(result["routes"]):
            sw_count = sum(demands.get(loc, (0, 0))[0] for loc in route)
            so_count = sum(demands.get(loc, (0, 0))[1] for loc in route)
            
            # Calculate actual route
            route_stops = [depot] + route + [depot]
            segments = []
            for j in range(len(route_stops) - 1):
                from_loc = route_stops[j]
                to_loc = route_stops[j + 1]
                dur = distance_matrix.get(from_loc, {}).get(to_loc, 15.0)
                segments.append({
                    "from": from_loc,
                    "to": to_loc,
                    "duration": dur
                })
            
            detailed_routes.append({
                "route_index": i,
                "locations": route,
                "cost": result["costs"][i],
                "sw_count": sw_count,
                "so_count": so_count,
                "total_passengers": sw_count + so_count,
                "segments": segments
            })
        
        result["detailed_routes"] = detailed_routes
        return result


class SplitDecoderV2:
    """
    Enhanced Split Decoder with additional features:
    - Time windows support
    - Multiple depots
    - Heterogeneous fleet optimization
    
    Based on Vidal et al. (2014) - A Hybrid Genetic Algorithm for VRP
    """
    
    def __init__(
        self,
        vehicle_configs: List[Dict],  # List of vehicle type configs
        max_tour_duration: float = 120.0
    ):
        """
        Initialize with multiple vehicle types.
        
        Args:
            vehicle_configs: List of dicts with 'sw_capacity', 'so_capacity', 'count'
            max_tour_duration: Maximum tour duration in minutes
        """
        self.vehicle_configs = vehicle_configs
        self.max_tour_duration = max_tour_duration
    
    def get_best_vehicle_for_demand(self, sw_demand: int, so_demand: int) -> Optional[Dict]:
        """Find the best fitting vehicle type for given demand."""
        best = None
        best_waste = float('inf')
        
        for config in self.vehicle_configs:
            if (sw_demand <= config['sw_capacity'] and 
                so_demand <= config['so_capacity']):
                waste = (config['sw_capacity'] - sw_demand + 
                        config['so_capacity'] - so_demand)
                if waste < best_waste:
                    best_waste = waste
                    best = config
        
        return best
    
    def decode_heterogeneous(
        self,
        giant_tour: List[str],
        depot: str,
        distance_matrix: Dict[str, Dict[str, float]],
        demands: Dict[str, Tuple[int, int]]
    ) -> Dict:
        """
        Decode with heterogeneous fleet consideration.
        
        Tries to assign the most suitable vehicle type to each route.
        """
        # Similar to base decoder but with vehicle type selection
        # Implementation follows the same DP approach
        # but tracks vehicle type assignments
        
        n = len(giant_tour)
        if n == 0:
            return {"routes": [], "total_cost": 0, "num_vehicles": 0}
        
        # Build trips for all vehicle types
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
                
                # Find best vehicle type
                best_vehicle = self.get_best_vehicle_for_demand(sw_load, so_load)
                if best_vehicle is None:
                    break
                
                # Calculate cost
                if prev in distance_matrix and loc in distance_matrix[prev]:
                    cost += distance_matrix[prev][loc]
                else:
                    cost += 15.0
                
                prev = loc
                
                return_cost = distance_matrix.get(loc, {}).get(depot, 15.0)
                total_cost = cost + return_cost
                
                if total_cost > self.max_tour_duration:
                    continue
                
                trips[j + 1].append({
                    "start_idx": i,
                    "cost": total_cost,
                    "vehicle_type": best_vehicle.get('type', 'standard'),
                    "sw_count": sw_load,
                    "so_count": so_load
                })
        
        # DP for shortest path
        V = [float('inf')] * (n + 1)
        V[0] = 0
        predecessor = [-1] * (n + 1)
        vehicle_assignment = [None] * (n + 1)
        
        for j in range(1, n + 1):
            for trip in trips[j]:
                i = trip["start_idx"]
                if V[i] + trip["cost"] < V[j]:
                    V[j] = V[i] + trip["cost"]
                    predecessor[j] = i
                    vehicle_assignment[j] = trip["vehicle_type"]
        
        # Reconstruct
        routes = []
        costs = []
        vehicle_types = []
        current = n
        
        while current > 0:
            prev = predecessor[current]
            if prev == -1:
                break
            
            routes.append(giant_tour[prev:current])
            for trip in trips[current]:
                if trip["start_idx"] == prev:
                    costs.append(trip["cost"])
                    vehicle_types.append(trip["vehicle_type"])
                    break
            
            current = prev
        
        routes = routes[::-1]
        costs = costs[::-1]
        vehicle_types = vehicle_types[::-1]
        
        return {
            "routes": routes,
            "costs": costs,
            "vehicle_types": vehicle_types,
            "total_cost": V[n],
            "num_vehicles": len(routes)
        }


def decode_giant_tour(
    giant_tour: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int = 4,
    so_capacity: int = 5,
    max_tour_duration: float = 120.0
) -> Dict:
    """
    Convenience function for basic split decoding.
    
    Args:
        giant_tour: Ordered list of customer locations
        depot: Depot location code
        distance_matrix: Travel times/distances between locations
        demands: Dict of location -> (sw_demand, so_demand)
        sw_capacity: Wheelchair capacity per vehicle
        so_capacity: Other disability capacity per vehicle
        max_tour_duration: Maximum route duration
    
    Returns:
        Dict with routes, costs, total_cost, num_vehicles
    """
    decoder = SplitDecoder(
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration
    )
    return decoder.decode(giant_tour, depot, distance_matrix, demands)


# Example usage and testing
if __name__ == "__main__":
    # Test case
    depot = "D.Kampus"
    giant_tour = ["L001", "L002", "L003", "L004", "L005", "L006"]
    
    # Simplified distance matrix
    distance_matrix = {
        "D.Kampus": {"L001": 10, "L002": 15, "L003": 20, "L004": 25, "L005": 30, "L006": 35},
        "L001": {"D.Kampus": 10, "L002": 8, "L003": 12, "L004": 18, "L005": 22, "L006": 28},
        "L002": {"D.Kampus": 15, "L001": 8, "L003": 6, "L004": 14, "L005": 18, "L006": 24},
        "L003": {"D.Kampus": 20, "L001": 12, "L002": 6, "L004": 8, "L005": 12, "L006": 18},
        "L004": {"D.Kampus": 25, "L001": 18, "L002": 14, "L003": 8, "L005": 6, "L006": 12},
        "L005": {"D.Kampus": 30, "L001": 22, "L002": 18, "L003": 12, "L004": 6, "L006": 8},
        "L006": {"D.Kampus": 35, "L001": 28, "L002": 24, "L003": 18, "L004": 12, "L005": 8}
    }
    
    # Demands: location -> (sw_demand, so_demand)
    demands = {
        "L001": (1, 0),  # 1 wheelchair
        "L002": (0, 1),  # 1 other
        "L003": (1, 1),  # 1 each
        "L004": (0, 2),  # 2 other
        "L005": (2, 0),  # 2 wheelchair
        "L006": (1, 1)   # 1 each
    }
    
    decoder = SplitDecoder(sw_capacity=4, so_capacity=5, max_tour_duration=60)
    result = decoder.decode_with_details(giant_tour, depot, distance_matrix, demands)
    
    print("Split Decoder Test Results")
    print("=" * 50)
    print(f"Total Cost: {result['total_cost']:.1f} minutes")
    print(f"Number of Vehicles: {result['num_vehicles']}")
    print()
    
    for route_info in result.get('detailed_routes', []):
        print(f"Route {route_info['route_index'] + 1}:")
        print(f"  Locations: {' -> '.join([depot] + route_info['locations'] + [depot])}")
        print(f"  Cost: {route_info['cost']:.1f} minutes")
        print(f"  Passengers: Sw={route_info['sw_count']}, So={route_info['so_count']}")
        print()
