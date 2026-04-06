"""
Two-Opt Strategy for TSP/CVRP
Classic local search algorithm that can be used as standalone optimizer.

Based on Croes (1958) - "A method for solving traveling-salesman problems"
"""

import random
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.clustering import VehicleCalculator
from utils.local_search import apply_local_search, LocalSearchType


class TwoOptStrategy(BaseRoutingStrategy):
    """
    Two-Opt Strategy for Vehicle Routing Problem.
    
    A simple but effective local search algorithm that iteratively
    improves a route by removing two edges and reconnecting.
    
    Can be used as:
    1. Standalone optimizer (starts from random permutation)
    2. Multi-start optimizer (runs from multiple random starts)
    3. Final refinement after other algorithms
    
    Best for:
    - Small to medium instances (< 50 nodes)
    - Quick optimization when speed is priority
    - Final refinement of solutions from other algorithms
    """
    
    DEFAULT_CONFIG = {
        "max_iterations": 50,           # Max 2-opt iterations per run
        "multi_start": True,            # Use multi-start optimization
        "num_starts": 10,               # Number of random starts
        "first_improvement": False,     # Use first-improvement strategy
        "seed": None
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)
    
    @property
    def name(self) -> str:
        return "two_opt"
    
    @property
    def display_name(self) -> str:
        return "2-Opt Yerel Arama"
    
    @property
    def description(self) -> str:
        return "Klasik yerel arama algoritması. Hızlı ve etkili, küçük-orta ölçekli problemler için ideal."
    
    def _get_duration(self, from_loc: str, to_loc: str, 
                      time_matrix: Dict, coordinates: Dict) -> float:
        """Get travel duration between two locations"""
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)
        return 15.0
    
    def _calculate_route_duration(
        self,
        position: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> float:
        """Calculate total route duration"""
        if not position:
            return 0.0
        total = self._get_duration(depot, position[0], time_matrix, coordinates)
        for i in range(len(position) - 1):
            total += self._get_duration(position[i], position[i + 1], time_matrix, coordinates)
        total += self._get_duration(position[-1], depot, time_matrix, coordinates)
        return total
    
    def _shuffle(self, items: List) -> List:
        """Fisher-Yates shuffle"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result
    
    def _generate_initial_solution(self, waypoints: List[str]) -> List[str]:
        """Generate initial random solution"""
        return self._shuffle(waypoints)
    
    def _generate_nearest_neighbor_solution(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> List[str]:
        """Generate initial solution using nearest neighbor heuristic"""
        if not waypoints:
            return []
        
        remaining = waypoints.copy()
        route = []
        current = depot
        
        while remaining:
            nearest = min(remaining, key=lambda loc: self._get_duration(current, loc, time_matrix, coordinates))
            route.append(nearest)
            remaining.remove(nearest)
            current = nearest
        
        return route
    
    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> Tuple[List[str], float]:
        """Solve TSP using 2-opt"""
        if not waypoints:
            return [], 0.0
        
        if len(waypoints) == 1:
            duration = (
                self._get_duration(depot, waypoints[0], time_matrix, coordinates) +
                self._get_duration(waypoints[0], depot, time_matrix, coordinates)
            )
            return waypoints, duration
        
        if len(waypoints) == 2:
            d1 = self._calculate_route_duration(waypoints, depot, time_matrix, coordinates)
            d2 = self._calculate_route_duration([waypoints[1], waypoints[0]], depot, time_matrix, coordinates)
            if d1 <= d2:
                return waypoints, d1
            return [waypoints[1], waypoints[0]], d2
        
        # Multi-start optimization
        if self.config["multi_start"]:
            best_route = None
            best_cost = float('inf')
            
            for start_idx in range(self.config["num_starts"]):
                # Mix of random and nearest neighbor starts
                if start_idx == 0:
                    initial = self._generate_nearest_neighbor_solution(waypoints, depot, time_matrix, coordinates)
                else:
                    initial = self._generate_initial_solution(waypoints)
                
                # Apply 2-opt
                improved_route, improved_cost = apply_local_search(
                    route=initial,
                    depot=depot,
                    time_matrix=time_matrix,
                    coordinates=coordinates,
                    search_type=LocalSearchType.TWO_OPT,
                    max_iterations=self.config["max_iterations"],
                    first_improvement=self.config["first_improvement"]
                )
                
                if improved_cost < best_cost:
                    best_route = improved_route
                    best_cost = improved_cost
            
            return best_route, best_cost
        else:
            # Single start from nearest neighbor
            initial = self._generate_nearest_neighbor_solution(waypoints, depot, time_matrix, coordinates)
            return apply_local_search(
                route=initial,
                depot=depot,
                time_matrix=time_matrix,
                coordinates=coordinates,
                search_type=LocalSearchType.TWO_OPT,
                max_iterations=self.config["max_iterations"],
                first_improvement=self.config["first_improvement"]
            )
    
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Main optimization entry point"""
        start_time = time.time()
        
        students = request.students
        depot = request.depot
        
        if not students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time
            )
        
        # Override config if provided
        if hasattr(request, 'two_opt_config') and request.two_opt_config:
            self.config.update(request.two_opt_config)
            self.rng = random.Random(self.config.get("seed", self.seed))
        
        # Build time matrix and coordinates
        data_loader = DataLoader.get_instance()
        
        location_ids = [depot.id] + [s.location_code for s in students]
        raw_matrix = data_loader.get_submatrix(location_ids)
        time_matrix = {
            location_ids[i]: {
                location_ids[j]: raw_matrix[i][j]
                for j in range(len(location_ids))
            }
            for i in range(len(location_ids))
        }
        
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords
        
        # Convert students
        student_dicts = []
        for s in students:
            student_dicts.append({
                "id": s.id,
                "name": s.name,
                "location_code": s.location_code,
                "coordinates": s.coordinates or {"lat": 0, "lng": 0},
                "disability_type": s.disability_type
            })
        
        # Calculate vehicle assignments
        calculator = VehicleCalculator(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time
        )
        
        def route_optimizer(location_codes: List[str]) -> Dict:
            if not location_codes:
                return {"route_details": [], "total_duration": 0}
            
            optimized_route, duration = self._solve_tsp(
                location_codes, depot.id, time_matrix, coordinates
            )
            
            route_details = []
            current = depot.id
            
            for loc in optimized_route:
                d = self._get_duration(current, loc, time_matrix, coordinates)
                route_details.append({
                    "location1": current,
                    "location2": loc,
                    "duration": d
                })
                current = loc
            
            d = self._get_duration(current, depot.id, time_matrix, coordinates)
            route_details.append({
                "location1": current,
                "location2": depot.id,
                "duration": d
            })
            
            return {"route_details": route_details, "total_duration": duration}
        
        result = calculator.calculate(student_dicts, route_optimizer)
        
        # Build response
        routes = []
        for assignment in result["assignments"]:
            route_steps = [
                RouteStep(
                    location1=step["location1"],
                    location2=step["location2"],
                    duration=round(step["duration"], 2),
                    distance=0.0
                )
                for step in assignment["route"]
            ]
            
            routes.append(VehicleRoute(
                vehicle_id=f"Araç {assignment['vehicle_index']} (2-Opt)",
                route_details=route_steps,
                total_duration_minutes=round(assignment["total_duration"], 2),
                total_distance_km=0.0,
                sw_count=assignment["sw_count"],
                so_count=assignment["so_count"],
                student_ids=[s["id"] for s in assignment["students"]]
            ))
        
        execution_time = time.time() - start_time
        
        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(r.total_duration_minutes for r in routes),
            execution_time_seconds=round(execution_time, 4)
        )
