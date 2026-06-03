"""Compatibility response builders for holistic core route plans."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from models.schemas import OptimizationRequest, OptimizationResponse, RouteStep, VehicleRoute


def build_sequence_routes_response(
    *,
    request: OptimizationRequest,
    route_plans: Sequence[Any],
    duration_lookup: Callable[[str, str], float],
    distance_lookup: Callable[[str, str], float],
    algorithm_name: str,
    vehicle_label: str,
    execution_time_seconds: float,
) -> OptimizationResponse:
    """Map core routes expressed as customer-index sequences to API routes."""
    depot = request.depot
    students = request.students
    routes: list[VehicleRoute] = []

    for route_plan in route_plans:
        route_details: list[RouteStep] = []
        route_students = []
        total_duration = 0.0
        previous_location = depot.id

        for customer_idx in route_plan.customer_indices:
            student = students[customer_idx]
            current_location = student.location_code
            duration = duration_lookup(previous_location, current_location)
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

        return_duration = duration_lookup(previous_location, depot.id)
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

    return _success_response(algorithm_name, routes, execution_time_seconds)


def build_indexed_step_routes_response(
    *,
    request: OptimizationRequest,
    route_plans: Sequence[Any],
    location_ids: Sequence[str],
    distance_lookup: Callable[[str, str], float],
    algorithm_name: str,
    vehicle_label: str,
    execution_time_seconds: float,
) -> OptimizationResponse:
    """Map core routes expressed as indexed route steps to API routes."""
    routes: list[VehicleRoute] = []

    for route_plan in route_plans:
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
                vehicle_id=f"Araç {route_plan.vehicle_index} ({vehicle_label})",
                route_details=route_details,
                total_duration_minutes=route_plan.total_duration,
                total_distance_km=round(sum(step.distance for step in route_details), 2),
                sw_count=route_plan.sw_count,
                so_count=route_plan.so_count,
                student_ids=[request.students[idx].id for idx in route_plan.customer_indices],
            )
        )

    return _success_response(algorithm_name, routes, execution_time_seconds)


def _success_response(
    algorithm_name: str,
    routes: Sequence[VehicleRoute],
    execution_time_seconds: float,
) -> OptimizationResponse:
    return OptimizationResponse(
        algorithm_used=algorithm_name,
        success=True,
        routes=list(routes),
        total_vehicles=len(routes),
        total_duration_minutes=sum(route.total_duration_minutes for route in routes),
        execution_time_seconds=round(execution_time_seconds, 4),
    )


__all__ = [
    "build_indexed_step_routes_response",
    "build_sequence_routes_response",
]
