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

import logging
import time
from typing import Dict, List, Optional

from models.schemas import (
    OptimizationRequest,
    OptimizationResponse,
    VehicleRoute,
    RouteStep,
)
from strategies.base_strategy import BaseRoutingStrategy
from uniride_core.algorithms.sota_tsp import E2BSO_TSP, E2BSOTSPConfig
from utils.data_loader import DataLoader, euclidean_distance

logger = logging.getLogger(__name__)


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

        # Build distance data
        data_loader = DataLoader.get_instance()
        location_ids = [depot.id] + [s.location_code for s in students]

        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        raw_matrix = data_loader.get_submatrix(location_ids, coordinates)
        time_matrix = {
            location_ids[i]: {
                location_ids[j]: raw_matrix[i][j]
                for j in range(len(location_ids))
            }
            for i in range(len(location_ids))
        }

        # Helper for euclidean distance
        def _dist(loc1: str, loc2: str) -> float:
            c1 = coordinates.get(loc1, {})
            c2 = coordinates.get(loc2, {})
            return round(
                euclidean_distance(
                    c1.get("lat", 0), c1.get("lng", 0),
                    c2.get("lat", 0), c2.get("lng", 0),
                ),
                2,
            )

        # ── Build E²BSO-compatible problem wrapper ──
        # E²BSO expects: node_names (List[str]), dist_matrix (int→int→int),
        # cost_fn (tour→float), optimal, dimension

        # Student location codes as node names
        student_ids = [s.location_code for s in students]
        n = len(student_ids)

        # Build integer distance matrix (rounded euclidean)
        int_dm: Dict[int, Dict[int, int]] = {}
        for i in range(n):
            int_dm[i] = {}
            for j in range(n):
                if i != j:
                    d = _dist(student_ids[i], student_ids[j])
                    int_dm[i][j] = max(1, int(d * 1000))  # meters
                else:
                    int_dm[i][j] = 0

        # ── Run E²BSO ──
        try:
            e2bso = E2BSO_TSP(self._config)
            matrix = [[float(int_dm[i][j]) for j in range(n)] for i in range(n)]
            result = e2bso.solve_with_matrix(matrix)

            # Convert E²BSO result tour to student order
            best_order = [student_ids[idx] for idx in result.tour]
        except Exception as e:
            logger.error(f"E²BSO optimization failed: {e}")
            # Fallback to greedy
            best_order = self._greedy_fallback(students, depot, time_matrix, coordinates)

        # ── Build route steps ──
        route_details = []
        route_distance = 0.0

        current = depot.id
        for student_id in best_order:
            duration = self._get_duration(current, student_id, time_matrix, coordinates)
            dist = _dist(current, student_id)
            route_details.append(
                RouteStep(
                    location1=current,
                    location2=student_id,
                    duration=round(duration, 2),
                    distance=dist,
                )
            )
            route_distance += dist
            current = student_id

        # Return to depot
        ret_duration = self._get_duration(current, depot.id, time_matrix, coordinates)
        ret_dist = _dist(current, depot.id)
        route_details.append(
            RouteStep(
                location1=current,
                location2=depot.id,
                duration=round(ret_duration, 2),
                distance=ret_dist,
            )
        )
        route_distance += ret_dist

        total_duration = sum(
            step.duration for step in route_details
        )

        route = VehicleRoute(
            vehicle_id="Araç 1 (E²BSO)",
            route_details=route_details,
            total_duration_minutes=round(total_duration, 2),
            total_distance_km=round(route_distance, 2),
            sw_count=sum(1 for s in best_order if any(st.location_code == s for st in students if st.disability_type == "Sw")),
            so_count=sum(1 for s in best_order if any(st.location_code == s for st in students if st.disability_type == "So")),
            student_ids=best_order,
        )

        execution_time = time.time() - start_time

        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=[route],
            total_vehicles=1,
            total_duration_minutes=round(total_duration, 2),
            execution_time_seconds=round(execution_time, 4),
        )

    def _greedy_fallback(self, students, depot, time_matrix, coordinates):
        """Simple greedy fallback if E²BSO fails."""
        from uniride_core.algorithms.sota_tsp import E2BSO_TSP

        unassigned = list(students)
        order = []

        current = depot.id
        while unassigned:
            best = None
            best_time = float("inf")
            best_idx = -1

            for idx, student in enumerate(unassigned):
                t = self._get_duration(current, student.location_code, time_matrix, coordinates)
                if t < best_time:
                    best_time = t
                    best = student
                    best_idx = idx

            if best is None:
                break

            order.append(best.location_code)
            unassigned.pop(best_idx)
            current = best.location_code

        return order
