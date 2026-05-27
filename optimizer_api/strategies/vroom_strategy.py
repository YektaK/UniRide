"""VROOM production strategy wrappers."""

from __future__ import annotations

import time

from models.schemas import OptimizationRequest, OptimizationResponse, RouteStep, VehicleRoute
from strategies.base_strategy import BaseRoutingStrategy
from strategies.sota_response_builder import build_sota_request_context
from uniride_core.algorithms.vroom_cvrp_engine import (
    VROOMRoutePlan,
    solve_sweep_fallback_routes,
    solve_vroom_cvrp,
)


class VROOMStrategy(BaseRoutingStrategy):
    """VROOM based CVRP/CVRPTW solver wrapper."""

    @property
    def name(self) -> str:
        return "vroom"

    @property
    def display_name(self) -> str:
        return "VROOM (Ultra-Fast C++)"

    @property
    def description(self) -> str:
        return "C++ tabanlı ultra-hızlı VRP çözücü. Canlı rota planlama için optimize. PDPTW ve Multi-trip destekli."

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        start_time = time.time()
        if not request.students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time,
            )
        context_payload = _build_vroom_context(request)

        solution = solve_vroom_cvrp(
            duration_matrix=context_payload["duration_matrix"],
            disability_types=[student.disability_type for student in request.students],
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_route_duration=request.max_travel_time,
            num_vehicles=min(len(request.students), 15),
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

        return _routes_to_response(
            strategy=self,
            request=request,
            route_plans=solution.routes,
            context=context_payload,
            algorithm_name=self.name,
            vehicle_label="VROOM",
            execution_time_seconds=time.time() - start_time,
        )


class VROOMFallbackStrategy(BaseRoutingStrategy):
    """VROOM compatibility fallback using a core sweep heuristic."""

    @property
    def name(self) -> str:
        return "vroom_fallback"

    @property
    def display_name(self) -> str:
        return "VROOM Fallback"

    @property
    def description(self) -> str:
        return "VROOM fallback implementation using sweep heuristic."

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        start_time = time.time()
        if not request.students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time,
            )
        context_payload = _build_vroom_context(request)

        routes = solve_sweep_fallback_routes(
            customer_indices=list(range(len(request.students))),
            coordinates=context_payload["coordinates_list"],
            disability_types=[student.disability_type for student in request.students],
            depot_index=0,
            duration_lookup=lambda origin, destination: context_payload["duration_matrix"][origin][destination],
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_route_duration=request.max_travel_time,
        )
        return _routes_to_response(
            strategy=self,
            request=request,
            route_plans=routes,
            context=context_payload,
            algorithm_name=self.name,
            vehicle_label="VROOM-Fallback",
            execution_time_seconds=time.time() - start_time,
        )


def _build_vroom_context(request: OptimizationRequest) -> dict:
    students = request.students
    depot = request.depot
    context = build_sota_request_context(students, depot)
    location_ids = [depot.id] + context["student_ids"]
    duration_matrix = [
        [context["time_matrix"][origin][destination] for destination in location_ids]
        for origin in location_ids
    ]
    return {
        **context,
        "location_ids": location_ids,
        "duration_matrix": duration_matrix,
        "coordinates_list": [context["coordinates"][location_id] for location_id in location_ids],
    }


def _routes_to_response(
    *,
    strategy: BaseRoutingStrategy,
    request: OptimizationRequest,
    route_plans: list[VROOMRoutePlan],
    context: dict,
    algorithm_name: str,
    vehicle_label: str,
    execution_time_seconds: float,
) -> OptimizationResponse:
    depot = request.depot
    students = request.students
    time_matrix = context["time_matrix"]
    coordinates = context["coordinates"]
    distance_lookup = context["distance_lookup"]
    routes = []

    for route_plan in route_plans:
        route_details = []
        route_students = []
        total_duration = 0.0
        previous_location = depot.id

        for customer_idx in route_plan.customer_indices:
            student = students[customer_idx]
            current_location = student.location_code
            duration = strategy._get_duration(previous_location, current_location, time_matrix, coordinates)
            total_duration += duration
            route_details.append(
                RouteStep(
                    location1=previous_location,
                    location2=current_location,
                    duration=round(duration, 2),
                    distance=distance_lookup(previous_location, current_location),
                )
            )
            route_students.append(student)
            previous_location = current_location

        if not route_students:
            continue

        return_duration = strategy._get_duration(previous_location, depot.id, time_matrix, coordinates)
        total_duration += return_duration
        route_details.append(
            RouteStep(
                location1=previous_location,
                location2=depot.id,
                duration=round(return_duration, 2),
                distance=distance_lookup(previous_location, depot.id),
            )
        )
        routes.append(
            VehicleRoute(
                vehicle_id=f"Araç {len(routes) + 1} ({vehicle_label})",
                route_details=route_details,
                total_duration_minutes=round(total_duration, 2),
                total_distance_km=round(sum(step.distance for step in route_details), 2),
                sw_count=route_plan.sw_count,
                so_count=route_plan.so_count,
                student_ids=[student.id for student in route_students],
            )
        )

    return OptimizationResponse(
        algorithm_used=algorithm_name,
        success=True,
        routes=routes,
        total_vehicles=len(routes),
        total_duration_minutes=sum(route.total_duration_minutes for route in routes),
        execution_time_seconds=round(execution_time_seconds, 4),
    )
