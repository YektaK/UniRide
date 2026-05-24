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
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

logger = logging.getLogger(__name__)


@dataclass
class Wolf:
    """Wolf individual in the pack"""
    position: List[str]  # Route permutation
    fitness: float  # 1 / total_duration
    total_duration: float


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
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)

    @property
    def name(self) -> str:
        return "gwo"

    @property
    def display_name(self) -> str:
        return "Gri Kurt Optimizasyonu"

    @property
    def description(self) -> str:
        return "Sosyal hiyerarşi tabanlı meta-sezgisel. Keşif-sömürü dengesi güçlü."

    def _shuffle(self, items: List, rng: random.Random) -> List:
        """Shuffle list using provided RNG"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def _initialize_pack(self, waypoints: List[str], rng: random.Random) -> List[Wolf]:
        """Initialize wolf pack with random positions"""
        pack = []

        for _ in range(self.config["population_size"]):
            position = self._shuffle(waypoints, rng)
            pack.append(Wolf(
                position=position,
                fitness=0.0,
                total_duration=float('inf')
            ))

        return pack

    def _get_difference_vector(self, leader: List[str], wolf: List[str], a: float, rng: random.Random) -> List[Tuple[int, int]]:
        """
        Calculate swaps to move wolf toward leader.

        In continuous GWO, this would be a vector difference.
        For TSP (permutation), we use swap operations.
        """
        swaps = []
        n = len(wolf)

        for i in range(n):
            if wolf[i] != leader[i]:
                try:
                    j = wolf.index(leader[i])
                    # Random factor based on 'a'
                    if rng.random() < a / 2:
                        swaps.append((i, j))
                except ValueError:
                    pass

        return swaps

    def _apply_swaps(self, position: List[str], swaps: List[Tuple[int, int]]) -> List[str]:
        """Apply swap operations to position"""
        new_position = position.copy()

        for i, j in swaps:
            if 0 <= i < len(new_position) and 0 <= j < len(new_position):
                new_position[i], new_position[j] = new_position[j], new_position[i]

        return new_position

    def _update_position(
        self,
        wolf: Wolf,
        alpha: Wolf,
        beta: Wolf,
        delta: Wolf,
        a: float,
        rng: random.Random
    ) -> List[str]:
        """
        Update wolf position based on alpha, beta, delta.

        In GWO, each wolf updates its position based on the three best wolves:
        X(t+1) = (X1 + X2 + X3) / 3

        For permutation problems, we combine swap suggestions from each leader.
        """
        new_position = wolf.position.copy()

        # Get swap suggestions from each leader
        alpha_swaps = self._get_difference_vector(alpha.position, wolf.position, a, rng)
        beta_swaps = self._get_difference_vector(beta.position, wolf.position, a, rng)
        delta_swaps = self._get_difference_vector(delta.position, wolf.position, a, rng)

        # Combine swaps with weights
        all_swaps = []

        # Alpha has highest weight
        for swap in alpha_swaps:
            if rng.random() < 0.7:
                all_swaps.append(swap)

        # Beta has medium weight
        for swap in beta_swaps:
            if rng.random() < 0.5:
                all_swaps.append(swap)

        # Delta has lower weight
        for swap in delta_swaps:
            if rng.random() < 0.3:
                all_swaps.append(swap)

        # Apply swaps
        if all_swaps:
            # Apply only a subset of swaps to maintain diversity
            num_swaps = min(len(all_swaps), max(1, int(len(all_swaps) * a / 2)))
            selected_swaps = rng.sample(all_swaps, min(num_swaps, len(all_swaps)))
            new_position = self._apply_swaps(wolf.position, selected_swaps)

        return new_position

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        rng: random.Random,
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using GWO"""
        if not waypoints:
            return [], 0.0

        if len(waypoints) == 1:
            duration = (
                self._get_duration(depot, waypoints[0], time_matrix, coordinates) +
                self._get_duration(waypoints[0], depot, time_matrix, coordinates)
            )
            return waypoints, duration

        # Initialize pack
        pack = self._initialize_pack(waypoints, rng)

        # Evaluate initial pack
        for wolf in pack:
            duration = self._calculate_route_duration(wolf.position, depot, time_matrix, coordinates)
            wolf.total_duration = duration
            wolf.fitness = 1.0 / duration if duration > 0 else 0.0

        # Sort and identify alpha, beta, delta
        pack.sort(key=lambda w: w.total_duration)
        alpha = Wolf(position=pack[0].position.copy(), fitness=pack[0].fitness, total_duration=pack[0].total_duration)
        beta = Wolf(position=pack[1].position.copy(), fitness=pack[1].fitness, total_duration=pack[1].total_duration) if len(pack) > 1 else alpha
        delta = Wolf(position=pack[2].position.copy(), fitness=pack[2].fitness, total_duration=pack[2].total_duration) if len(pack) > 2 else beta

        no_improvement = 0

        # Main GWO loop
        for iteration in range(self.config["max_iterations"]):
            # Calculate 'a' (decreases linearly from initial_a to 0)
            a = self.config["initial_a"] * (1 - iteration / self.config["max_iterations"])

            improved = False

            for wolf in pack:
                # Exploration: random search
                if rng.random() < self.config["exploration_rate"] * a / self.config["initial_a"]:
                    # Random perturbation
                    new_position = self._shuffle(wolf.position, rng)
                else:
                    # Exploitation: move toward leaders
                    new_position = self._update_position(wolf, alpha, beta, delta, a, rng)

                # Evaluate new position
                duration = self._calculate_route_duration(new_position, depot, time_matrix, coordinates)

                # Update if better
                if duration < wolf.total_duration:
                    wolf.position = new_position
                    wolf.total_duration = duration
                    wolf.fitness = 1.0 / duration if duration > 0 else 0.0

                # Update leaders
                if wolf.total_duration < alpha.total_duration:
                    delta = Wolf(position=beta.position.copy(), fitness=beta.fitness, total_duration=beta.total_duration)
                    beta = Wolf(position=alpha.position.copy(), fitness=alpha.fitness, total_duration=alpha.total_duration)
                    alpha = Wolf(position=wolf.position.copy(), fitness=wolf.fitness, total_duration=wolf.total_duration)
                    improved = True
                elif wolf.total_duration < beta.total_duration:
                    delta = Wolf(position=beta.position.copy(), fitness=beta.fitness, total_duration=beta.total_duration)
                    beta = Wolf(position=wolf.position.copy(), fitness=wolf.fitness, total_duration=wolf.total_duration)
                    improved = True
                elif wolf.total_duration < delta.total_duration:
                    delta = Wolf(position=wolf.position.copy(), fitness=wolf.fitness, total_duration=wolf.total_duration)
                    improved = True

            if improved:
                no_improvement = 0
            else:
                no_improvement += 1

            if no_improvement >= self.config["max_no_improvement"]:
                break

        # Apply local search to best solution
        best_route = alpha.position
        best_duration = alpha.total_duration

        # Get local search type
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
        if hasattr(request, 'gwo_config') and request.gwo_config:
            effective_config = {**self.config, **request.gwo_config}
            rng = random.Random(effective_config.get("seed", self.seed))
        else:
            rng = random.Random(self.seed)

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
                location_codes, depot.id, time_matrix, coordinates, rng
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