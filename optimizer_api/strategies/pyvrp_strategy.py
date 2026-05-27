"""PyVRP production strategy wrappers."""

from __future__ import annotations

import time

from models.schemas import OptimizationRequest, OptimizationResponse, RouteStep, VehicleRoute
from strategies.base_strategy import BaseRoutingStrategy
from strategies.sota_response_builder import build_sota_request_context
from uniride_core.algorithms.pyvrp_cvrp_engine import solve_pyvrp_cvrp


class PyVRPStrategy(BaseRoutingStrategy):
    """PyVRP based CVRP/CVRPTW solver using Hybrid Genetic Search."""

    @property
    def name(self) -> str:
        return "pyvrp"

    @property
    def display_name(self) -> str:
        return "PyVRP (HGS - DIMACS Winner)"

    @property
    def description(self) -> str:
        return "DIMACS 2021 birincisi Hybrid Genetic Search algoritması. En yüksek çözüm kalitesi."

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        return _optimize_with_pyvrp(self, request, algorithm_name=self.name, vehicle_label="PyVRP")


class PyVRPAlternativeStrategy(BaseRoutingStrategy):
    """Compatibility alias for the PyVRP production solver."""

    @property
    def name(self) -> str:
        return "pyvrp_alt"

    @property
    def display_name(self) -> str:
        return "PyVRP Alternative"

    @property
    def description(self) -> str:
        return "PyVRP alternatif implementasyon (core Model tabanlı)."

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        return _optimize_with_pyvrp(self, request, algorithm_name=self.name, vehicle_label="PyVRP-Alt")


def _optimize_with_pyvrp(
    strategy: BaseRoutingStrategy,
    request: OptimizationRequest,
    *,
    algorithm_name: str,
    vehicle_label: str,
) -> OptimizationResponse:
    start_time = time.time()
    students = request.students
    depot = request.depot

    if not students:
        return OptimizationResponse(
            algorithm_used=algorithm_name,
            success=True,
            routes=[],
            total_vehicles=0,
            execution_time_seconds=time.time() - start_time,
        )

    context = build_sota_request_context(students, depot)
    location_ids = [depot.id] + context["student_ids"]
    time_matrix = context["time_matrix"]
    coordinates = context["coordinates"]
    distance_lookup = context["distance_lookup"]
    duration_matrix = [
        [time_matrix[origin][destination] for destination in location_ids]
        for origin in location_ids
    ]
    coordinate_list = [coordinates[location_id] for location_id in location_ids]

    solution = solve_pyvrp_cvrp(
        duration_matrix=duration_matrix,
        coordinates=coordinate_list,
        disability_types=[student.disability_type for student in students],
        sw_capacity=request.sw_capacity,
        so_capacity=request.so_capacity,
        num_vehicles=min(len(students), 15),
        time_limit_seconds=30,
    )
    if not solution.success:
        return OptimizationResponse(
            algorithm_used=algorithm_name,
            success=False,
            routes=[],
            total_vehicles=0,
            error_message=solution.error_message,
            execution_time_seconds=time.time() - start_time,
        )

    routes = []
    for route_plan in solution.routes:
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
        execution_time_seconds=round(time.time() - start_time, 4),
    )
