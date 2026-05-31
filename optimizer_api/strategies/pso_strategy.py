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
from uniride_core.algorithms.meta_split_common import shuffle_permutation
from uniride_core.algorithms.tsp_meta_engines import (
    SwapOperation,
    TSPParticle as Particle,
    apply_swaps,
    combine_velocities,
    diff_swaps,
    generate_random_velocity,
    solve_pso_tsp,
)
from strategies.promoted_config_loader import get_promoted_strategy_params

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
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)

    @property
    def name(self) -> str:
        return "pso"

    @property
    def display_name(self) -> str:
        return "Parçacık Sürü Optimizasyonu"

    @property
    def description(self) -> str:
        return "Sürü zekası tabanlı meta-sezgisel. Hızlı yakınsama özelliği."

    def _shuffle(self, items: List) -> List:
        """Shuffle list using internal RNG"""
        return shuffle_permutation(items, self.rng)

    def _generate_random_velocity(self, n: int) -> List[SwapOperation]:
        """Generate random velocity (swap sequence) for initialization."""
        return generate_random_velocity(n, int(self.config.get("max_velocity_size", 5)), self.rng)

    def _initialize_swarm(self, waypoints: List[str]) -> List[Particle]:
        """Initialize swarm with random positions and velocities"""
        swarm = []

        for _ in range(self.config["swarm_size"]):
            position = self._shuffle(waypoints)
            velocity = self._generate_random_velocity(len(waypoints))

            swarm.append(Particle(
                position=position,
                velocity=velocity,
                personal_best=position.copy(),
                personal_best_duration=float('inf'),
                current_duration=float('inf')
            ))

        return swarm

    # ----------------------------------------------------------------
    # Swap-sequence velocity helpers (bildiri2026 pattern)
    # ----------------------------------------------------------------

    def _diff_swaps(self, current: List[str], target: List[str]) -> List[SwapOperation]:
        """Return the deterministic list of swaps that transforms `current` into `target`.

        This is the exact algorithm from bildiri2026/core/pso_solver.py: walk positions
        left-to-right; whenever current[i] != target[i], find target[i] in the tail of
        current and swap it into position i.
        """
        return diff_swaps(current, target)

    def _apply_swaps(self, position: List[str], swaps: List[SwapOperation]) -> List[str]:
        """Apply swap sequence deterministically."""
        return apply_swaps(position, swaps)

    def _combine_velocities(
        self,
        inertia_v: List[SwapOperation],
        cog_v: List[SwapOperation],
        soc_v: List[SwapOperation],
    ) -> List[SwapOperation]:
        """Clerc-style probabilistic combination of velocity components.

        Each component swap is included with probability equal to the
        corresponding weight / 3.0, mirroring bildiri2026 _combine_velocities.
        """
        return combine_velocities(inertia_v, cog_v, soc_v, self.config, self.rng)

    # ----------------------------------------------------------------
    # Legacy helpers (kept for backward compat, no longer used in PSO loop)
    # ----------------------------------------------------------------

    def _get_difference_swaps(
        self,
        current: List[str],
        target: List[str],
        weight: float
    ) -> List[SwapOperation]:
        """Legacy probabilistic-weight version (superseded by _diff_swaps)."""
        return self._diff_swaps(current, target)

    def _apply_velocity(self, position: List[str], velocity: List[SwapOperation]) -> List[str]:
        """Legacy API: apply velocity (delegates to _apply_swaps)."""
        return self._apply_swaps(position, velocity)

    def _update_velocity(
        self,
        current_velocity: List[SwapOperation],
        current_position: List[str],
        personal_best: List[str],
        global_best: List[str],
    ) -> List[SwapOperation]:
        """Legacy API: compute new velocity (delegates to _combine_velocities)."""
        cog_v = self._diff_swaps(current_position, personal_best)
        soc_v = self._diff_swaps(current_position, global_best)
        return self._combine_velocities(current_velocity, cog_v, soc_v)


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

        return solve_pso_tsp(waypoints, duration_func, rng or self.rng, config or self.config)

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
            rng = random.Random(effective_config.get("seed", self.seed))

        # Set local search type from request
        if request.local_search_type:
            effective_config["local_search_type"] = request.local_search_type

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
