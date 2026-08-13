"""OR-Tools CVRP production strategy wrapper."""

from __future__ import annotations

import math
import time

from models.schemas import OptimizationRequest, OptimizationResponse
from strategies.base_strategy import BaseRoutingStrategy
from strategies.holistic_response_builder import build_indexed_step_routes_response
from strategies.sota_response_builder import build_sota_request_context
from uniride_core.algorithms.ortools_cvrp_engine import solve_ortools_cvrp


class ORToolsCVRPStrategy(BaseRoutingStrategy):
    """OR-Tools based CVRP solver wrapper for the UniRide API."""

    def __init__(self, time_limit_seconds: float = 30.0) -> None:
        if isinstance(time_limit_seconds, bool):
            raise ValueError("time_limit_seconds must be positive")
        try:
            value = float(time_limit_seconds)
        except (TypeError, ValueError):
            raise ValueError("time_limit_seconds must be positive") from None
        if not math.isfinite(value) or value <= 0:
            raise ValueError("time_limit_seconds must be positive")
        self.time_limit_seconds = value

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
            time_limit_seconds=self.time_limit_seconds,
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

        return build_indexed_step_routes_response(
            request=request,
            route_plans=solution.routes,
            location_ids=location_ids,
            distance_lookup=distance_lookup,
            algorithm_name=self.name,
            vehicle_label="OR-Tools",
            execution_time_seconds=time.time() - start_time,
        )
