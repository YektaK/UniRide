"""
Harris Hawks Optimization (HHO) Strategy for TSP/CVRP
Based on Heidari et al. (2019)

Implements:
- Exploration: Hawks search in different regions
- Transition: Escape energy determines exploitation
- Exploitation: Four siege strategies based on prey escape behavior
  - Soft besiege
  - Hard besiege
  - Soft besiege with progressive rapid dives
  - Hard besiege with progressive rapid dives

Reference:
Heidari, A. A., Mirjalili, S., Faris, H., Aljarah, I., Mafarja, M., & Chen, H. (2019).
Harris hawks optimization: Algorithm and applications.
Future Generation Computer Systems, 97, 849-872.
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
from uniride_core.algorithms.tsp_meta_engines import solve_hho_tsp
from strategies.promoted_config_loader import get_promoted_strategy_params

class HarrisHawksOptimizerStrategy(BaseRoutingStrategy):
    """
    Harris Hawks Optimizer for Vehicle Routing Problem.

    HHO mimics the cooperative hunting behavior of Harris hawks:
    1. Exploration: Hawks randomly perch and wait for prey
    2. Transition: Based on escape energy of prey (E)
    3. Exploitation: Four siege strategies based on:
       - Escape energy (E): |E| >= 1 exploration, |E| < 1 exploitation
       - Escape probability (r): r < 0.5 soft besiege, r >= 0.5 hard besiege

    The algorithm adaptively switches between exploration and exploitation
    based on the prey's escape energy, which decreases over iterations.
    """

    # Default HHO parameters
    DEFAULT_CONFIG = {
        "population_size": 30,
        "max_iterations": 100,
        "initial_energy": 1.0,  # Initial energy (decreases over time)
        "jump_probability": 0.5,  # Probability of prey escaping
        "max_no_improvement": 20,
        "seed": None,
        "local_search_type": "hybrid",  # Type of local search to apply (hybrid = 2-opt + 3-opt + or-opt + swap)
    }

    def __init__(self, config: Optional[Dict] = None):
        promoted = {} if config is not None else get_promoted_strategy_params(
            ("hho", "harris_hawks", "Numba-HHO", "Core-HHO-TSP")
        )
        self.config = {**self.DEFAULT_CONFIG, **promoted, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)

    @property
    def name(self) -> str:
        return "hho"

    @property
    def display_name(self) -> str:
        return "Harris Hawks Optimizasyonu"

    @property
    def description(self) -> str:
        return "Şahin avlanma davranışı tabanlı meta-sezgisel. Kaçış enerjisi ile adaptif arama."

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        rng: random.Random,
        config: Optional[Dict] = None,
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using HHO.

        Delegates to uniride_core.algorithms.tsp_meta_engines.solve_hho_tsp.
        """
        if not waypoints:
            return [], 0.0

        def duration_func(route: List[str]) -> float:
            return self._calculate_route_duration(route, depot, time_matrix, coordinates)

        return solve_hho_tsp(waypoints, duration_func, rng, config or self.config)

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
        if hasattr(request, 'hho_config') and request.hho_config:
            effective_config = {**self.config, **request.hho_config}
            rng = random.Random(effective_config.get("seed", self.seed))

        # Build time matrix and coordinates
        data_loader = DataLoader.get_instance()

        location_ids = [depot.id] + [s.location_code for s in students]

        # Build coordinates BEFORE get_submatrix for euclidean distance fallback
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

        # Helper to compute euclidean distance between two location IDs
        def _dist(loc1: str, loc2: str) -> float:
            c1 = coordinates.get(loc1, {})
            c2 = coordinates.get(loc2, {})
            return round(euclidean_distance(c1.get("lat", 0), c1.get("lng", 0), c2.get("lat", 0), c2.get("lng", 0)), 2)

        # Convert students
        student_dicts = []
        for s in students:
            student_dicts.append({
                "id": s.id,
                "name": s.name,
                "location_code": s.location_code,
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
                vehicle_id=f"Araç {assignment['vehicle_index']} (HHO)",
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
