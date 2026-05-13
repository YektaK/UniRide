"""
Particle Swarm Optimization Strategy for TSP/CVRP
Based on Kennedy & Eberhart (1995) and Clerc & Kennedy (2002)

Implements:
- Position as permutation
- Velocity as sequence of swap operations
- Clerc's Constriction Factor for convergence
- Optional local search (2-opt, 3-opt, Or-opt, Hybrid)
"""

import logging
import random
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, euclidean_distance, haversine_distance, estimate_travel_time
from utils.clustering import VehicleCalculator
from utils.local_search import LocalSearchType, apply_local_search
from utils.patterns import SingletonMeta
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

logger = logging.getLogger(__name__)


@dataclass
class SwapOperation:
    """Represents a swap (i, j) in the velocity sequence."""
    i: int
    j: int
    # Note: probability field removed — Clerc combination handles stochasticity
    # at the velocity-combination level, not per-swap.


@dataclass
class Particle:
    """Particle in the swarm"""
    position: List[str]
    velocity: List[SwapOperation]   # deterministic swap sequence
    personal_best: List[str]
    personal_best_duration: float
    current_duration: float


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
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
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
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def _generate_random_velocity(self, n: int) -> List[SwapOperation]:
        """Generate random velocity (swap sequence) for initialization."""
        max_vel = int(self.config.get("max_velocity_size", 5))
        num_swaps = self.rng.randint(1, max(1, max_vel))
        velocity = []
        for _ in range(num_swaps):
            velocity.append(SwapOperation(
                i=self.rng.randint(0, n - 1),
                j=self.rng.randint(0, n - 1),
            ))
        return velocity

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
        swaps: List[SwapOperation] = []
        temp = current[:]
        for i in range(len(target)):
            if temp[i] != target[i]:
                try:
                    j = temp.index(target[i], i)
                except ValueError:
                    continue
                temp[i], temp[j] = temp[j], temp[i]
                swaps.append(SwapOperation(i=i, j=j))
        return swaps

    def _apply_swaps(self, position: List[str], swaps: List[SwapOperation]) -> List[str]:
        """Apply swap sequence deterministically."""
        new_pos = position[:]
        for swap in swaps:
            if 0 <= swap.i < len(new_pos) and 0 <= swap.j < len(new_pos):
                new_pos[swap.i], new_pos[swap.j] = new_pos[swap.j], new_pos[swap.i]
        return new_pos

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
        w = self.config["inertia_weight"]
        c1 = self.config["cognitive_weight"]
        c2 = self.config["social_weight"]
        max_vel = int(self.config.get("max_velocity_size", 5))

        new_v: List[SwapOperation] = []
        for swap in inertia_v:
            if self.rng.random() < w:
                new_v.append(swap)
        for swap in cog_v:
            if self.rng.random() < c1 / 3.0:
                new_v.append(swap)
        for swap in soc_v:
            if self.rng.random() < c2 / 3.0:
                new_v.append(swap)

        if len(new_v) > max_vel:
            new_v = self.rng.sample(new_v, max_vel)
        return new_v

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
        coordinates: Dict
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using swap-sequence PSO (bildiri2026 pattern)."""
        if not waypoints:
            return [], 0.0

        if len(waypoints) == 1:
            duration = (
                self._get_duration(depot, waypoints[0], time_matrix, coordinates) +
                self._get_duration(waypoints[0], depot, time_matrix, coordinates)
            )
            return waypoints, duration

        if len(waypoints) == 2:
            d1 = self._calculate_route_duration(waypoints, depot, time_matrix, coordinates)
            d2 = self._calculate_route_duration(
                [waypoints[1], waypoints[0]], depot, time_matrix, coordinates
            )
            if d1 <= d2:
                return waypoints, d1
            return [waypoints[1], waypoints[0]], d2

        reinit_interval = int(self.config.get("reinit_interval", 50))
        max_vel = int(self.config.get("max_velocity_size", 5))
        n = len(waypoints)

        # Initialize swarm
        swarm = self._initialize_swarm(waypoints)
        global_best = waypoints.copy()
        global_best_duration = float('inf')

        # Evaluate initial swarm
        for particle in swarm:
            duration = self._calculate_route_duration(
                particle.position, depot, time_matrix, coordinates
            )
            particle.current_duration = duration
            particle.personal_best_duration = duration

            if duration < global_best_duration:
                global_best = particle.position.copy()
                global_best_duration = duration

        no_improvement = 0

        # Main PSO loop — swap-sequence velocity (bildiri2026 pattern)
        for iteration in range(self.config["max_iterations"]):
            improved = False

            for particle in swarm:
                # Compute velocity components
                cog_v = self._diff_swaps(particle.position, particle.personal_best)
                soc_v = self._diff_swaps(particle.position, global_best)
                new_velocity = self._combine_velocities(particle.velocity, cog_v, soc_v)

                # Apply velocity (deterministic)
                new_position = self._apply_swaps(particle.position, new_velocity)

                # Evaluate
                duration = self._calculate_route_duration(
                    new_position, depot, time_matrix, coordinates
                )

                particle.position = new_position
                particle.velocity = new_velocity
                particle.current_duration = duration

                # Update personal best
                if duration < particle.personal_best_duration:
                    particle.personal_best = new_position.copy()
                    particle.personal_best_duration = duration

                    # Update global best
                    if duration < global_best_duration:
                        global_best = new_position.copy()
                        global_best_duration = duration
                        improved = True

            if improved:
                no_improvement = 0
            else:
                no_improvement += 1

            # Periodic swarm re-initialization for diversity (bildiri2026 pattern)
            if iteration > 0 and iteration % reinit_interval == 0:
                for particle in swarm:
                    if self.rng.random() < 0.9:
                        pos = particle.personal_best[:]
                        for _ in range(self.rng.randint(1, 3)):
                            a, b = self.rng.sample(range(n), 2)
                            pos[a], pos[b] = pos[b], pos[a]
                    else:
                        pos = global_best[:]
                        self.rng.shuffle(pos)
                    cost = self._calculate_route_duration(pos, depot, time_matrix, coordinates)
                    particle.position = pos
                    particle.velocity = self._generate_random_velocity(n)
                    if cost < particle.personal_best_duration:
                        particle.personal_best = pos[:]
                        particle.personal_best_duration = cost
                    if cost < global_best_duration:
                        global_best = pos[:]
                        global_best_duration = cost

            if no_improvement >= self.config["max_no_improvement"]:
                break

        # Apply local search to best solution
        best_route = global_best
        best_duration = global_best_duration

        ls_type_str = self.config.get("local_search_type", "two_opt")
        try:
            ls_type = LocalSearchType(ls_type_str)
        except ValueError:
            ls_type = LocalSearchType.TWO_OPT

        def duration_func(route):
            return self._calculate_route_duration(route, depot, time_matrix, coordinates)

        improved_route, improved_duration = apply_local_search(
            best_route, duration_func, ls_type
        )

        if improved_duration < best_duration:
            best_route = improved_route
            best_duration = improved_duration

        return best_route, best_duration

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
                location_codes, depot.id, time_matrix, coordinates
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
