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
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.patterns import SingletonMeta
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES
from utils.clustering import VehicleCalculator
from utils.local_search import LocalSearchType, apply_local_search

logger = logging.getLogger(__name__)


@dataclass
class Hawk:
    """Hawk individual in the population"""
    position: List[str]  # Route permutation
    fitness: float  # 1 / total_duration
    total_duration: float


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
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)

    @property
    def name(self) -> str:
        return "hho"

    @property
    def display_name(self) -> str:
        return "Harris Hawks Optimizasyonu"

    @property
    def description(self) -> str:
        return "Şahin avlanma davranışı tabanlı meta-sezgisel. Kaçış enerjisi ile adaptif arama."

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between two locations"""
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]

        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)

        logger.warning(f"Distance matrix miss for {from_loc} to {to_loc}. Using default fallback: {DEFAULT_TRAVEL_FALLBACK_MINUTES} mins")
        return DEFAULT_TRAVEL_FALLBACK_MINUTES

    def _calculate_route_duration(
        self,
        position: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> float:
        """Calculate total route duration for a position"""
        if not position:
            return 0.0

        total = 0.0
        total += self._get_duration(depot, position[0], time_matrix, coordinates)

        for i in range(len(position) - 1):
            total += self._get_duration(position[i], position[i + 1], time_matrix, coordinates)

        total += self._get_duration(position[-1], depot, time_matrix, coordinates)
        return total

    def _shuffle(self, items: List) -> List:
        """Shuffle list using internal RNG"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def _initialize_hawks(self, waypoints: List[str]) -> List[Hawk]:
        """Initialize hawk population with random positions"""
        hawks = []

        for _ in range(self.config["population_size"]):
            position = self._shuffle(waypoints)
            hawks.append(Hawk(
                position=position,
                fitness=0.0,
                total_duration=float('inf')
            ))

        return hawks

    def _levvy_flight(self, position: List[str], scale: float = 0.5) -> List[str]:
        """
        Perform Lévy flight mutation.

        Lévy flight provides random walks with occasional long jumps,
        useful for escaping local optima.
        """
        new_position = position.copy()
        n = len(new_position)

        # Lévy distribution parameter (beta = 1.5 is typical)
        beta = 1.5
        sigma = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2) /
                 (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)

        # Number of swaps based on Lévy distribution
        u = self.rng.gauss(0, sigma)
        v = self.rng.gauss(0, 1)
        step = u / (abs(v) ** (1 / beta))

        num_swaps = max(1, min(int(abs(step) * scale * n), n // 2))

        for _ in range(num_swaps):
            i, j = self.rng.sample(range(n), 2)
            new_position[i], new_position[j] = new_position[j], new_position[i]

        return new_position

    def _get_difference_swaps(
        self,
        current: List[str],
        target: List[str],
        intensity: float
    ) -> List[Tuple[int, int]]:
        """Get swaps to move current toward target"""
        swaps = []
        n = len(current)

        for i in range(n):
            if current[i] != target[i]:
                try:
                    j = current.index(target[i])
                    if self.rng.random() < intensity:
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

    def _soft_besiege(
        self,
        hawk: Hawk,
        prey: Hawk,
        escape_energy: float
    ) -> List[str]:
        """
        Soft besiege: When prey has enough energy to escape but still gets caught.

        Position update: X(t+1) = ΔX(t) - E * |J * Prey - X(t)|
        """
        # J is random jump strength (1.5 * rand in [0,2])
        J = 2 * (1 - self.rng.random())

        # Calculate movement toward prey
        intensity = abs(escape_energy * J)
        swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)

        return self._apply_swaps(hawk.position, swaps)

    def _hard_besiege(
        self,
        hawk: Hawk,
        prey: Hawk,
        escape_energy: float
    ) -> List[str]:
        """
        Hard besiege: When prey is exhausted, hawks tightly surround it.

        Position update: X(t+1) = Prey - E * |Prey - X(t)|
        """
        intensity = abs(escape_energy)
        swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)

        return self._apply_swaps(hawk.position, swaps)

    def _soft_besiege_with_dives(
        self,
        hawk: Hawk,
        prey: Hawk,
        escape_energy: float,
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> List[str]:
        """
        Soft besiege with progressive rapid dives.

        Hawks make rapid dives toward prey with Lévy flight movements.
        """
        # Attempt multiple dives
        best_position = hawk.position.copy()
        best_duration = hawk.total_duration

        for _ in range(3):  # Try 3 rapid dives
            # Move toward prey
            intensity = abs(escape_energy) * self.rng.random()
            swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)
            candidate = self._apply_swaps(hawk.position, swaps)

            # Add Lévy flight perturbation
            candidate = self._levvy_flight(candidate, scale=0.3)

            # Evaluate
            duration = self._calculate_route_duration(candidate, depot, time_matrix, coordinates)

            if duration < best_duration:
                best_position = candidate
                best_duration = duration

        return best_position

    def _hard_besiege_with_dives(
        self,
        hawk: Hawk,
        prey: Hawk,
        escape_energy: float,
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> List[str]:
        """
        Hard besiege with progressive rapid dives.

        Combined besiege with Lévy flights for final exploitation.
        """
        # Calculate mean position
        mean_intensity = abs(escape_energy)
        swaps = self._get_difference_swaps(hawk.position, prey.position, mean_intensity)
        candidate = self._apply_swaps(hawk.position, swaps)

        # Apply strong Lévy flight
        candidate = self._levvy_flight(candidate, scale=0.2)

        return candidate

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using HHO"""
        if not waypoints:
            return [], 0.0

        if len(waypoints) == 1:
            duration = (
                self._get_duration(depot, waypoints[0], time_matrix, coordinates) +
                self._get_duration(waypoints[0], depot, time_matrix, coordinates)
            )
            return waypoints, duration

        # Initialize hawks
        hawks = self._initialize_hawks(waypoints)

        # Evaluate initial hawks
        for hawk in hawks:
            duration = self._calculate_route_duration(hawk.position, depot, time_matrix, coordinates)
            hawk.total_duration = duration
            hawk.fitness = 1.0 / duration if duration > 0 else 0.0

        # Find prey (best solution)
        prey = min(hawks, key=lambda h: h.total_duration)
        prey = Hawk(position=prey.position.copy(), fitness=prey.fitness, total_duration=prey.total_duration)

        no_improvement = 0

        # Main HHO loop
        for iteration in range(self.config["max_iterations"]):
            # Calculate escape energy (decreases linearly)
            E0 = 2 * self.rng.random() - 1  # In [-1, 1]
            E = 2 * E0 * (1 - iteration / self.config["max_iterations"])

            improved = False

            for hawk in hawks:
                # Random escape probability
                r = self.rng.random()

                # Exploration phase (|E| >= 1)
                if abs(E) >= 1:
                    # Random perching
                    if self.rng.random() < 0.5:
                        # Perch near prey
                        intensity = self.rng.random()
                        swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)
                        new_position = self._apply_swaps(hawk.position, swaps)
                    else:
                        # Random perch (Lévy flight)
                        new_position = self._levvy_flight(hawk.position)

                # Exploitation phase (|E| < 1)
                else:
                    if r < self.config["jump_probability"]:
                        # Soft besiege
                        if abs(E) >= 0.5:
                            new_position = self._soft_besiege(hawk, prey, E)
                        # Hard besiege
                        else:
                            new_position = self._hard_besiege(hawk, prey, E)
                    else:
                        # Soft besiege with progressive rapid dives
                        if abs(E) >= 0.5:
                            new_position = self._soft_besiege_with_dives(
                                hawk, prey, E, depot, time_matrix, coordinates
                            )
                        # Hard besiege with progressive rapid dives
                        else:
                            new_position = self._hard_besiege_with_dives(
                                hawk, prey, E, depot, time_matrix, coordinates
                            )

                # Evaluate new position
                duration = self._calculate_route_duration(new_position, depot, time_matrix, coordinates)

                # Update if better
                if duration < hawk.total_duration:
                    hawk.position = new_position
                    hawk.total_duration = duration
                    hawk.fitness = 1.0 / duration if duration > 0 else 0.0

                # Update prey (best solution)
                if hawk.total_duration < prey.total_duration:
                    prey = Hawk(
                        position=hawk.position.copy(),
                        fitness=hawk.fitness,
                        total_duration=hawk.total_duration
                    )
                    improved = True

            if improved:
                no_improvement = 0
            else:
                no_improvement += 1

            if no_improvement >= self.config["max_no_improvement"]:
                break

        # Apply local search to best solution
        best_route = prey.position
        best_duration = prey.total_duration

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

        # Override config if provided
        if hasattr(request, 'hho_config') and request.hho_config:
            self.config.update(request.hho_config)
            self.rng = random.Random(self.config.get("seed", self.seed))

        # Build time matrix and coordinates
        data_loader = DataLoader.get_instance()

        location_ids = [depot.id] + [s.location_code for s in students]
        raw_matrix = data_loader.get_submatrix(location_ids)
        time_matrix = {
            location_ids[i]: {
                location_ids[j]: raw_matrix[i][j]
                for j in range(len(location_ids))
            }
            for i in range(len(location_ids))
        }

        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

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
                    distance=0.0
                )
                for step in assignment["route"]
            ]

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {assignment['vehicle_index']} (HHO)",
                route_details=route_steps,
                total_duration_minutes=round(assignment["total_duration"], 2),
                total_distance_km=0.0,
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