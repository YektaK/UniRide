"""OR-Tools CVRP production strategy wrapper."""

from __future__ import annotations

import time

from models.schemas import OptimizationRequest, OptimizationResponse, RouteStep, VehicleRoute
from strategies.base_strategy import BaseRoutingStrategy
from strategies.sota_response_builder import build_sota_request_context
from uniride_core.algorithms.ortools_cvrp_engine import solve_ortools_cvrp


class ORToolsCVRPStrategy(BaseRoutingStrategy):
    """OR-Tools based CVRP solver wrapper for the UniRide API."""

    @property
    def name(self) -> str:
        return "ortools_cvrp"

    @property
    def display_name(self) -> str:
        return "OR-Tools CVRP"

    @property
    def description(self) -> str:
        return "Google OR-Tools kütüphanesi ile endüstri standardı VRP çözümü."

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute OR-Tools optimization."""
        start_time = time.time()
        students = request.students
        depot = request.depot

        if not students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time,
            )

        context = build_sota_request_context(students, depot)
        location_ids = [depot.id] + context["student_ids"]
        raw_matrix = [
            [context["time_matrix"][origin][destination] for destination in location_ids]
            for origin in location_ids
        ]
        distance_lookup = context["distance_lookup"]

        solution = solve_ortools_cvrp(
            time_matrix=raw_matrix,
            disability_types=[student.disability_type for student in students],
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_route_duration=request.max_travel_time,
            num_vehicles=min(len(students), 10),
            time_limit_seconds=30,
        )

        if not solution.success:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                error_message=solution.error_message,
                execution_time_seconds=time.time() - start_time,
            )

        routes = []
        for route_plan in solution.routes:
            route_details = [
                RouteStep(
                    location1=location_ids[step.from_index],
                    location2=location_ids[step.to_index],
                    duration=step.duration,
                    distance=distance_lookup(location_ids[step.from_index], location_ids[step.to_index]),
                )
                for step in route_plan.steps
            ]
            routes.append(
                VehicleRoute(
                    vehicle_id=f"Araç {route_plan.vehicle_index} (OR-Tools)",
                    route_details=route_details,
                    total_duration_minutes=route_plan.total_duration,
                    total_distance_km=round(sum(step.distance for step in route_details), 2),
                    sw_count=route_plan.sw_count,
                    so_count=route_plan.so_count,
                    student_ids=[students[idx].id for idx in route_plan.customer_indices],
                )
            )

        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(route.total_duration_minutes for route in routes),
            execution_time_seconds=round(time.time() - start_time, 4),
        )
