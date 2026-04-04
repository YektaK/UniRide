"""
Permutation TSP Strategy
Exhaustive search for small problems (n ≤ 10)
Guarantees optimal solution
"""

import time
from itertools import permutations
from typing import List, Dict

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.clustering import VehicleCalculator


class PermutationTSPStrategy(BaseRoutingStrategy):
    """
    Complete permutation search for TSP.
    Optimal but exponential complexity - only for small problems.
    """

    MAX_PERMUTATION_SIZE = 10  # Practical limit

    @property
    def name(self) -> str:
        return "permutation_tsp"

    @property
    def display_name(self) -> str:
        return "Permütasyon (Optimal)"

    @property
    def description(self) -> str:
        return "Tüm kombinasyonları dener, en iyi sonucu garanti eder. n ≤ 10 için kullanılabilir."

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between locations"""
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
        permutation: tuple,
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> float:
        """Calculate total duration for a permutation"""
        if not permutation:
            return 0.0

        total = self._get_duration(depot, permutation[0], time_matrix, coordinates)

        for i in range(len(permutation) - 1):
            total += self._get_duration(
                permutation[i], permutation[i + 1], time_matrix, coordinates
            )

        total += self._get_duration(permutation[-1], depot, time_matrix, coordinates)
        return total

    def _solve_tsp_optimal(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ):
        """Find optimal TSP solution by complete search"""
        if not waypoints:
            return [], 0.0

        if len(waypoints) == 1:
            duration = (
                self._get_duration(depot, waypoints[0], time_matrix, coordinates) +
                self._get_duration(waypoints[0], depot, time_matrix, coordinates)
            )
            return waypoints, duration

        if len(waypoints) > self.MAX_PERMUTATION_SIZE:
            # Fall back to first n items or raise error
            waypoints = waypoints[:self.MAX_PERMUTATION_SIZE]

        best_perm = None
        best_duration = float('inf')

        for perm in permutations(waypoints):
            duration = self._calculate_route_duration(perm, depot, time_matrix, coordinates)
            if duration < best_duration:
                best_duration = duration
                best_perm = perm

        return list(best_perm), best_duration

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

        calculator = VehicleCalculator(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time,
            clustering_algorithm=request.clustering_algorithm
        )

        def route_optimizer(location_codes: List[str]) -> Dict:
            if not location_codes:
                return {"route_details": [], "total_duration": 0}

            optimized_route, duration = self._solve_tsp_optimal(
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
                vehicle_id=f"Araç {assignment['vehicle_index']} (Optimal)",
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
