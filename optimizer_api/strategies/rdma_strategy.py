"""
R²DMA Strategy — Resonance-Supported Destroy-and-Merge Algorithm (FAZ 2)

Web-facing BaseRoutingStrategy wrapper for the R²DMA meta-heuristic.
Wraps the standalone R²DMA solver to work with the UniRide optimization API.

The R²DMA algorithm integrates:
- 6-dimensional resonance metrics for partner selection
- Adaptive crossover: Constructive, Moderate, Destructive
- Simulated Annealing acceptance
- Multi-layer local search
- ALNS-inspired destroy/repair
"""

import time
from typing import Optional

from models.schemas import (
    OptimizationRequest,
    OptimizationResponse,
)
from strategies.base_strategy import BaseRoutingStrategy
from strategies.sota_config_utils import merge_sota_config
from strategies.sota_response_builder import build_single_route_response, build_sota_request_context
from uniride_core.algorithms.sota_tsp import R2DMA_TSP, R2DMATSPConfig
from uniride_core.adapters.sota_tsp_strategy_adapter import solve_student_order_with_sota_tsp


class R2DMAStrategy(BaseRoutingStrategy):
    """Resonance-Supported Destroy-and-Merge Algorithm strategy.

    A memetic algorithm that uses 6D resonance metrics to guide
    adaptive crossover and partner selection for TSP/CVRP solving.

    Key features:
    - 6-dimensional resonance: fitness, diversity, edge, segment, entropy, phase
    - Three crossover modes: Constructive, Moderate, Destructive
    - Simulated Annealing acceptance with adaptive cooling
    - Multi-layer local search (2-opt, 3-opt, or-opt, hybrid)
    - Adaptive theta mechanism for crossover mode selection
    """

    def __init__(self, config: Optional[R2DMATSPConfig] = None):
        self._config = config or R2DMATSPConfig(population_size=24, max_iterations=200)

    @property
    def name(self) -> str:
        return "r2dma"

    @property
    def display_name(self) -> str:
        return "R²DMA (Rezonans-Destekli Memetik)"

    @property
    def description(self) -> str:
        return (
            "Rezonans-Destekli Destroy-and-Merge Algoritması. "
            "6 boyutlu rezonans metriği, ALNS + SA + çok katmanlı LS."
        )

    # _get_duration inherited from BaseRoutingStrategy

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute R²DMA optimization on the routing problem."""
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
        effective_config = merge_sota_config(self._config, request.sota_config)
        time_matrix = context["time_matrix"]
        coordinates = context["coordinates"]
        distance_lookup = context["distance_lookup"]
        best_order = solve_student_order_with_sota_tsp(
            context["student_ids"],
            depot.id,
            distance_lookup,
            lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates),
            R2DMA_TSP,
            effective_config,
        )

        return build_single_route_response(
            algorithm_name=self.name,
            vehicle_label="R²DMA",
            students=students,
            depot_id=depot.id,
            best_order=best_order,
            duration_lookup=lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates),
            distance_lookup=distance_lookup,
            execution_time_seconds=time.time() - start_time,
        )

