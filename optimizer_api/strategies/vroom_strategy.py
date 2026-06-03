"""VROOM production strategy wrappers."""

from __future__ import annotations

import time

from models.schemas import OptimizationRequest, OptimizationResponse
from strategies.base_strategy import BaseRoutingStrategy
from strategies.holistic_response_builder import build_sequence_routes_response
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
    time_matrix = context["time_matrix"]
    coordinates = context["coordinates"]
    distance_lookup = context["distance_lookup"]

    return build_sequence_routes_response(
        request=request,
        route_plans=route_plans,
        duration_lookup=lambda origin, destination: strategy._get_duration(
            origin,
            destination,
            time_matrix,
            coordinates,
        ),
        distance_lookup=distance_lookup,
        algorithm_name=algorithm_name,
        vehicle_label=vehicle_label,
        execution_time_seconds=execution_time_seconds,
    )
