"""
Permutation TSP Strategy
Exhaustive search for small problems (n ≤ 10)
Guarantees optimal solution
"""

import time
from typing import List, Dict

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from strategies.sota_response_builder import build_sota_request_context
from uniride_core.algorithms.string_exact_tsp import solve_exact_tsp_route
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator


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

    def _solve_tsp_optimal(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ):
        """Find optimal TSP solution by complete search"""
        return solve_exact_tsp_route(
            waypoints,
            depot,
            lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates),
            max_permutation_size=self.MAX_PERMUTATION_SIZE,
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

        context = build_sota_request_context(students, depot)
        coordinates = context["coordinates"]
        time_matrix = context["time_matrix"]
        distance_lookup = context["distance_lookup"]

        # Convert students
        student_dicts = []
        for s, occurrence_key in zip(students, context["student_ids"]):
            student_dicts.append({
                "id": s.id,
                "name": s.name,
                "location_code": s.location_code,
                "occurrence_key": occurrence_key,
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
                    distance=distance_lookup(step["location1"], step["location2"])
                )
                for step in assignment["route"]
            ]

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {assignment['vehicle_index']} (Optimal)",
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
