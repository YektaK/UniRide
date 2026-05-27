"""
P-AOEA Strategy — Production Adaptive Operator Evolution Algorithm (FAZ 3)

Web-facing BaseRoutingStrategy wrapper for the P-AOEA meta-heuristic.
Wraps the standalone PAOEA solver to work with the UniRide optimization API.

The P-AOEA algorithm integrates:
- Operator genome evolution with meta-evolution
- Structured injection of elite genetic material
- Adaptive destroy density control
- Multi-layer local search
- Diversity management via entropy tracking
"""

import time
from typing import Optional

from models.schemas import (
    OptimizationRequest,
    OptimizationResponse,
)
from strategies.base_strategy import BaseRoutingStrategy
from strategies.sota_response_builder import build_single_route_response, build_sota_request_context
from uniride_core.algorithms.sota_tsp import PAOEA_TSP, PAOEAConfig
from uniride_core.adapters.sota_tsp_strategy_adapter import solve_student_order_with_sota_tsp


class PAOEAStrategy(BaseRoutingStrategy):
    """Production Adaptive Operator Evolution Algorithm strategy.

    An evolutionary algorithm that evolves operator genomes (selection
    probabilities for destroy/repair/local-search operators) using
    meta-evolution and structured injection.

    Key features:
    - Operator genome meta-evolution (operators themselves evolve)
    - Structured injection of elite genetic material
    - Adaptive destroy density control
    - Phase-based LS intensity (exploration → exploitation)
    - Entropy-based diversity monitoring
    """

    def __init__(self, config: Optional[PAOEAConfig] = None):
        self._config = config or PAOEAConfig(population_size=24, max_iterations=200)

    @property
    def name(self) -> str:
        return "paoea"

    @property
    def display_name(self) -> str:
        return "P-AOEA (Adaptif Operatör Evrimi)"

    @property
    def description(self) -> str:
        return (
            "Production Adaptif Operatör Evrim Algoritması. "
            "Operatör genomlarının meta-evrimi, yapılandırılmış enjeksiyon."
        )

    # _get_duration inherited from BaseRoutingStrategy

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute P-AOEA optimization on the routing problem."""
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
        time_matrix = context["time_matrix"]
        coordinates = context["coordinates"]
        distance_lookup = context["distance_lookup"]
        best_order = solve_student_order_with_sota_tsp(
            context["student_ids"],
            depot.id,
            distance_lookup,
            lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates),
            PAOEA_TSP,
            self._config,
        )

        return build_single_route_response(
            algorithm_name=self.name,
            vehicle_label="P-AOEA",
            students=students,
            depot_id=depot.id,
            best_order=best_order,
            duration_lookup=lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates),
            distance_lookup=distance_lookup,
            execution_time_seconds=time.time() - start_time,
        )

