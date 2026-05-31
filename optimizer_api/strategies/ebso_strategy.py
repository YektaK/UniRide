"""
E²BSO Strategy — Enhanced Entropy-Balanced Swarm Optimization (FAZ 1)

Web-facing BaseRoutingStrategy wrapper for the E²BSO meta-heuristic.
Wraps the standalone E²BSO solver to work with the UniRide optimization API.

The E²BSO algorithm integrates all 7 FAZ 0 infrastructure modules:
- MultiStartInitializer (DNA #6)
- MultiLayerLS (DNA #3)
- PenaltyManager (DNA #9) — available but not used in TSP mode
- LateAcceptanceHC (DNA #7)
- DestroyOperators: Random, Worst, Shaw, Related (DNA #1, #2)
- RepairOperators: Greedy, Regret-2, Regret-3 (DNA #1, #2)
- DiversityController (DNA #8)
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
from uniride_core.algorithms.sota_tsp import E2BSO_TSP, E2BSOTSPConfig
from uniride_core.adapters.sota_tsp_strategy_adapter import solve_student_order_with_sota_tsp


class E2BSoStrategy(BaseRoutingStrategy):
    """Enhanced Entropy-Balanced Swarm Optimization strategy.

    A population-based meta-heuristic that uses edge-based Shannon entropy
    to dynamically balance exploration vs. exploitation for TSP/CVRP solving.

    Key features:
    - Adaptive entropy-based phase switching (inject/normal/compress)
    - ALNS destroy/repair for diversity injection
    - Multi-layer local search (2-opt → Or-opt → 3-opt → Swap)
    - LAHC acceptance criterion
    - Multi-start initialization with 4 heuristics
    """

    def __init__(self, config: Optional[E2BSOTSPConfig] = None):
        self._config = config or E2BSOTSPConfig(population_size=24, max_iterations=200)

    @property
    def name(self) -> str:
        return "e2bso"

    @property
    def display_name(self) -> str:
        return "E²BSO (Entropy-Balanced Swarm)"

    @property
    def description(self) -> str:
        return (
            "Geliştirilmiş Entropi-Dengeli Swarm Optimizasyonu. "
            "Kenar entropisi ile keşif/sömürü dengesi, ALNS + çok katmanlı LS."
        )

    # _get_duration inherited from BaseRoutingStrategy

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute E²BSO optimization on the routing problem.

        For TSP-like problems (single vehicle), directly uses E²BSO on the
        tour of all students. For multi-vehicle CVRP, runs E²BSO on the
        giant-tour representation and keeps the best single-tour result
        as a single route.
        """
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
            E2BSO_TSP,
            effective_config,
        )

        return build_single_route_response(
            algorithm_name=self.name,
            vehicle_label="E²BSO",
            students=students,
            depot_id=depot.id,
            best_order=best_order,
            duration_lookup=lambda origin, destination: self._get_duration(origin, destination, time_matrix, coordinates),
            distance_lookup=distance_lookup,
            execution_time_seconds=time.time() - start_time,
        )

