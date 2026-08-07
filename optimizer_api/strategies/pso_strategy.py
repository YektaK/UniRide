"""
Particle Swarm Optimization Strategy for TSP/CVRP
Based on Kennedy & Eberhart (1995) and Clerc & Kennedy (2002)

Implements:
- Position as permutation
- Velocity as sequence of swap operations
- Clerc's Constriction Factor for convergence
- Optional local search (2-opt, 3-opt, Or-opt, Hybrid)
"""

import random
import time
from typing import List, Dict, Tuple, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, euclidean_distance
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator
from uniride_core.algorithms.tsp_meta_engines import (
    solve_pso_tsp,
)
from strategies.promoted_config_loader import get_promoted_strategy_params
from strategies.seed_utils import resolve_seed, make_rng
from uniride_core.adapters.demand_builder import student_occurrence_keys

class PSOStrategy(BaseRoutingStrategy):
    """
    Particle Swarm Optimization for Vehicle Routing Problem.
    Uses K-Means clustering for multi-vehicle, then PSO for TSP.
    """

    # Default PSO parameters (Clerc constriction, swap-sequence velocity)
    DEFAULT_CONFIG = {
        "swarm_size": 30,
        "max_iterations": 100,
        "inertia_weight": 0.729,      # Clerc's constriction
        "cognitive_weight": 1.49445,  # c1
        "social_weight": 1.49445,     # c2
        "max_velocity_size": 5,       # max swaps kept per particle
        "max_no_improvement": 25,
        "reinit_interval": 50,        # periodic diversity reinit (like bildiri2026)
        "seed": None,
        "local_search_type": "hybrid",
    }

    def __init__(self, config: Optional[Dict] = None):
        promoted = {} if config is not None else get_promoted_strategy_params(
            ("pso", "Numba-PSO", "Core-PSO-TSP")
        )
        self.config = {**self.DEFAULT_CONFIG, **promoted, **(config or {})}
        self.seed = resolve_seed(self.config)

    @property
    def name(self) -> str:
        return "pso"

    @property
    def display_name(self) -> str:
        return "Parçacık Sürü Optimizasyonu"

    @property
    def description(self) -> str:
        return "Sürü zekası tabanlı meta-sezgisel. Hızlı yakınsama özelliği."

    def _rng_for_config(self, config: Optional[Dict] = None) -> random.Random:
        return make_rng(config or self.config, default=self.seed)

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        config: Optional[Dict] = None,
        rng: Optional[random.Random] = None,
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using swap-sequence PSO (bildiri2026 pattern)."""
        def duration_func(route):
            return self._calculate_route_duration(route, depot, time_matrix, coordinates)

        return solve_pso_tsp(waypoints, duration_func, rng or self._rng_for_config(config), config or self.config)

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Main optimization entry point"""
        start_time = time.time()

        students = request.students
        depot = request.depot

        if not students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time
            )

        # Singleton self.config korunuyor; her istek icin local kopya
        effective_config = dict(self.config)
        rng = random.Random(self.seed)
        if request.pso_config:
            effective_config.update(request.pso_config)
            rng = make_rng(effective_config, default=self.seed)

        # Set local search type from request
        if request.local_search_type:
            effective_config["local_search_type"] = request.local_search_type

        # Build time matrix and coordinates
        data_loader = DataLoader.get_instance()

        # Occurrence-aware node keys: duplicate physical locations get
        # disambiguated keys (L1#S1, L1#S2) while single-customer locations
        # keep their location_code. The raw submatrix is fetched positionally
        # with physical codes (duplicates allowed), then re-keyed.
        occurrence_keys = list(student_occurrence_keys(students))
        node_keys = [depot.id] + occurrence_keys
        physical_ids = [depot.id] + [s.location_code for s in students]

        # Build coordinates BEFORE get_submatrix for euclidean distance fallback
        physical_coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            physical_coordinates[s.location_code] = coords

        raw_matrix = data_loader.get_submatrix(physical_ids, physical_coordinates)
        time_matrix = {
            node_keys[i]: {
                node_keys[j]: raw_matrix[i][j]
                for j in range(len(node_keys))
            }
            for i in range(len(node_keys))
        }
        coordinates = {
            node_keys[i]: physical_coordinates.get(physical_ids[i], {})
            for i in range(len(node_keys))
        }

        # Helper to compute euclidean distance between two location IDs
        def _dist(loc1: str, loc2: str) -> float:
            c1 = coordinates.get(loc1, {})
            c2 = coordinates.get(loc2, {})
            return round(euclidean_distance(c1.get("lat", 0), c1.get("lng", 0), c2.get("lat", 0), c2.get("lng", 0)), 2)

        # Convert students
        student_dicts = []
        for s, occurrence_key in zip(students, occurrence_keys):
            student_dicts.append({
                "id": s.id,
                "name": s.name,
                "location_code": s.location_code,
                "occurrence_key": occurrence_key,
                "coordinates": s.coordinates or {"lat": 0, "lng": 0},
                "disability_type": s.disability_type
            })

        # Calculate vehicle assignments - use request clustering_algorithm (default: sweep)
        calculator = VehicleCalculator(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time,
            clustering_algorithm=request.clustering_algorithm or "sweep"
        )

        def route_optimizer(location_codes: List[str]) -> Dict:
            if not location_codes:
                return {"route_details": [], "total_duration": 0}

            optimized_route, duration = self._solve_tsp(
                location_codes, depot.id, time_matrix, coordinates, effective_config, rng
            )

            route_details = []
            current = depot.id

            for loc in optimized_route:
                d = self._get_duration(current, loc, time_matrix, coordinates)
                route_details.append({
                    "location1": current,
                    "location2": loc,
                    "duration": d
                })
                current = loc

            d = self._get_duration(current, depot.id, time_matrix, coordinates)
            route_details.append({
                "location1": current,
                "location2": depot.id,
                "duration": d
            })

            return {"route_details": route_details, "total_duration": duration}

        result = calculator.calculate(student_dicts, route_optimizer)

        # Build response
        routes = []
        for assignment in result["assignments"]:
            route_steps = [
                RouteStep(
                    location1=step["location1"],
                    location2=step["location2"],
                    duration=round(step["duration"], 2),
                    distance=_dist(step["location1"], step["location2"])
                )
                for step in assignment["route"]
            ]

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {assignment['vehicle_index']} (PSO)",
                route_details=route_steps,
                total_duration_minutes=round(assignment["total_duration"], 2),
                total_distance_km=round(sum(s.distance for s in route_steps), 2),
                sw_count=assignment["sw_count"],
                so_count=assignment["so_count"],
                student_ids=[s["id"] for s in assignment["students"]]
            ))

        execution_time = time.time() - start_time

        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(r.total_duration_minutes for r in routes),
            execution_time_seconds=round(execution_time, 4)
        )
