"""
Greedy (Nearest Neighbor) Heuristic Strategy
Constructs routes by always visiting the nearest valid student
"""

import time

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from strategies.sota_response_builder import build_sota_request_context
from uniride_core.adapters.demand_builder import student_occurrence_keys
from uniride_core.algorithms.string_greedy_routing import solve_string_greedy_routes


class GreedyHeuristicStrategy(BaseRoutingStrategy):
    """
    Greedy Nearest Neighbor Heuristic.
    Fast but may not find optimal solution.
    """

    @property
    def name(self) -> str:
        return "greedy"

    @property
    def display_name(self) -> str:
        return "Greedy (En Yakın Komşu)"

    @property
    def description(self) -> str:
        return "Hızlı sezgisel algoritma. En yakın öğrenciyi her adımda seçer."

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute greedy optimization"""
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
        duration_lookup = lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates)
        occurrence_keys = student_occurrence_keys(students)
        student_by_key = {key: student for student, key in zip(students, occurrence_keys)}
        route_plans = solve_string_greedy_routes(
            customer_locations=context["student_ids"],
            disability_types={key: student.disability_type for student, key in zip(students, occurrence_keys)},
            depot_id=depot.id,
            duration_lookup=duration_lookup,
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_route_duration=request.max_travel_time,
        )

        routes = []
        for vehicle_idx, route_plan in enumerate(route_plans, start=1):
            route_details = []
            route_distance = 0.0
            for step in route_plan.steps:
                step_dist = distance_lookup(step.location1, step.location2)
                route_details.append(RouteStep(
                    location1=step.location1,
                    location2=step.location2,
                    duration=step.duration,
                    distance=step_dist
                ))
                route_distance += step_dist

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {vehicle_idx} (Greedy)",
                route_details=route_details,
                total_duration_minutes=route_plan.total_duration,
                total_distance_km=round(route_distance, 2),
                sw_count=route_plan.sw_count,
                so_count=route_plan.so_count,
                student_ids=[student_by_key[location].id for location in route_plan.student_locations]
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
