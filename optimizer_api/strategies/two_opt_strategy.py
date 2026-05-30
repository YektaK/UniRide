"""
Two-Opt Strategy for TSP/CVRP
Standalone strategy using 2-opt local search as the primary algorithm.

This strategy provides the classic 2-opt algorithm as a standalone
optimization method, which can be useful for:
- Small problems where meta-heuristics are overkill
- Baseline comparison with other algorithms
- Educational purposes
- Multi-start optimization

Reference:
Croes, G. (1958). A method for solving traveling salesman problems.
Operations Research, 6(6), 791-812.
"""

import random
import time
from typing import List, Dict, Tuple, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, euclidean_distance
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator
from uniride_core.algorithms.meta_split_common import shuffle_permutation
from uniride_core.algorithms.tsp_meta_engines import nearest_neighbor_route, solve_two_opt_tsp

class TwoOptStrategy(BaseRoutingStrategy):
    """
    Two-Opt Strategy for Vehicle Routing Problem.

    This strategy uses 2-opt local search as the primary optimization
    algorithm. It can operate in two modes:
    1. Single-run: Apply 2-opt once from an initial solution
    2. Multi-start: Run 2-opt from multiple random starts and pick best

    The multi-start approach helps escape local optima and often produces
    better solutions at the cost of longer execution time.
    """

    # Default Two-Opt parameters
    DEFAULT_CONFIG = {
        "max_iterations": 2000,  # Max 2-opt iterations
        "multi_start": True,  # Use multi-start optimization
        "num_starts": 10,  # Number of random starts
        "first_improvement": False,  # Use first improvement strategy
        "seed": None,
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)

    @property
    def name(self) -> str:
        return "two_opt"

    @property
    def display_name(self) -> str:
        return "Two-Opt Local Search"

    @property
    def description(self) -> str:
        return "Klasik 2-opt yerel arama algoritması. Küçük-orta ölçekli problemler için ideal."

    def _shuffle(self, items: List, rng: random.Random) -> List:
        """Shuffle list using provided RNG"""
        return shuffle_permutation(items, rng)

    def _nearest_neighbor_initial(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> List[str]:
        """
        Generate initial solution using nearest neighbor heuristic.

        This provides a good starting point for 2-opt.
        """
        return nearest_neighbor_route(
            waypoints,
            depot,
            lambda current, location: self._get_duration(current, location, time_matrix, coordinates),
        )

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        config: Dict,
        rng: random.Random,
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using 2-opt"""
        def duration_func(route):
            return self._calculate_route_duration(route, depot, time_matrix, coordinates)

        initial_route = self._nearest_neighbor_initial(waypoints, depot, time_matrix, coordinates)
        return solve_two_opt_tsp(waypoints, duration_func, rng, config, initial_route=initial_route)

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

        # Per-request local config & RNG (singleton-safe)
        effective_config = dict(self.config)
        if hasattr(request, 'two_opt_config') and request.two_opt_config:
            effective_config = {**self.config, **request.two_opt_config}
            rng = random.Random(effective_config.get("seed", self.seed))
        else:
            rng = random.Random(self.seed)

        # Build time matrix and coordinates
        data_loader = DataLoader.get_instance()

        location_ids = [depot.id] + [s.location_code for s in students]

        # Build coordinates BEFORE get_submatrix for euclidean distance fallback
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        raw_matrix = data_loader.get_submatrix(location_ids, coordinates)
        time_matrix = {
            location_ids[i]: {
                location_ids[j]: raw_matrix[i][j]
                for j in range(len(location_ids))
            }
            for i in range(len(location_ids))
        }

        # Helper to compute euclidean distance between two location IDs
        def _dist(loc1: str, loc2: str) -> float:
            c1 = coordinates.get(loc1, {})
            c2 = coordinates.get(loc2, {})
            return round(euclidean_distance(c1.get("lat", 0), c1.get("lng", 0), c2.get("lat", 0), c2.get("lng", 0)), 2)

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

        # Calculate vehicle assignments - use request clustering_algorithm (default: sweep)
        calculator = VehicleCalculator(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time,
            clustering_algorithm=request.clustering_algorithm or "sweep"
        )

        def route_optimizer(location_codes: List[str]) -> Dict:
            if not location_codes:
                return {"route_details": [], "total_duration": 0}

            optimized_route, duration = self._solve_tsp(
                location_codes, depot.id, time_matrix, coordinates, effective_config, rng
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
                    distance=_dist(step["location1"], step["location2"])
                )
                for step in assignment["route"]
            ]

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {assignment['vehicle_index']} (Two-Opt)",
                route_details=route_steps,
                total_duration_minutes=round(assignment["total_duration"], 2),
                total_distance_km=round(sum(s.distance for s in route_steps), 2),
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
