"""PyVRP production strategy wrappers."""

from __future__ import annotations

import time

from models.schemas import OptimizationRequest, OptimizationResponse
from strategies.base_strategy import BaseRoutingStrategy
from strategies.holistic_response_builder import build_sequence_routes_response
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

    return build_sequence_routes_response(
        request=request,
        route_plans=solution.routes,
        duration_lookup=lambda origin, destination: strategy._get_duration(
            origin,
            destination,
            time_matrix,
            coordinates,
        ),
        distance_lookup=distance_lookup,
        algorithm_name=algorithm_name,
        vehicle_label=vehicle_label,
        execution_time_seconds=time.time() - start_time,
    )
