"""
Grey Wolf Optimizer (GWO) Strategy for TSP/CVRP
Based on Mirjalili et al. (2014)

Implements:
- Social hierarchy (alpha, beta, delta, omega)
- Encircling prey mechanism
- Hunting behavior simulation
- Exploration and exploitation balance

Reference:
Mirjalili, S., Mirjalili, S. M., & Lewis, A. (2014).
Grey wolf optimizer. Advances in Engineering Software, 69, 46-61.
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
    solve_gwo_tsp,
)
from strategies.promoted_config_loader import get_promoted_strategy_params
from uniride_core.adapters.demand_builder import student_occurrence_keys
from strategies.seed_utils import resolve_seed, make_rng

class GreyWolfOptimizerStrategy(BaseRoutingStrategy):
    """
    Grey Wolf Optimizer for Vehicle Routing Problem.

    GWO mimics the social hierarchy and hunting behavior of grey wolves:
    - Alpha (α): Best solution, leads the pack
    - Beta (β): Second best, assists alpha
    - Delta (δ): Third best, assists alpha and beta
    - Omega (ω): Rest of the pack, follows the leaders

    The algorithm balances exploration (searching new areas) and
    exploitation (refining good solutions) through the parameter 'a'
    which decreases linearly from 2 to 0.
    """

    # Default GWO parameters
    DEFAULT_CONFIG = {
        "population_size": 30,
        "max_iterations": 100,
        "initial_a": 2.0,  # Initial value of a (decreases to 0)
        "exploration_rate": 0.5,  # Probability of random exploration
        "max_no_improvement": 20,
        "seed": None,
        "local_search_type": "two_opt",  # Type of local search to apply
    }

    def __init__(self, config: Optional[Dict] = None):
        promoted = {} if config is not None else get_promoted_strategy_params(
            ("gwo", "grey_wolf", "Numba-GWO", "Core-GWO-TSP")
        )
        self.config = {**self.DEFAULT_CONFIG, **promoted, **(config or {})}
        self.seed = resolve_seed(self.config)

    @property
    def name(self) -> str:
        return "gwo"

    @property
    def display_name(self) -> str:
        return "Gri Kurt Optimizasyonu"

    @property
    def description(self) -> str:
        return "Sosyal hiyerarşi tabanlı meta-sezgisel. Keşif-sömürü dengesi güçlü."

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        rng: random.Random,
        config: Optional[Dict] = None,
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using GWO"""
        def duration_func(route):
            return self._calculate_route_duration(route, depot, time_matrix, coordinates)

        return solve_gwo_tsp(waypoints, duration_func, rng, config or self.config)

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
        if hasattr(request, 'gwo_config') and request.gwo_config:
            effective_config = {**self.config, **request.gwo_config}
            rng = make_rng(effective_config, default=self.seed)
        else:
            rng = random.Random(self.seed)

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
                location_codes, depot.id, time_matrix, coordinates, rng, effective_config
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
                vehicle_id=f"Araç {assignment['vehicle_index']} (GWO)",
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
