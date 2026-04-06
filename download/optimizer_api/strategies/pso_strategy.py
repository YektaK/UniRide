"""
Particle Swarm Optimization Strategy for TSP/CVRP
Based on Kennedy & Eberhart (1995) and Clerc & Kennedy (2002)

Implements:
- Position as permutation
- Velocity as sequence of swap operations
- Clerc's Constriction Factor for convergence
"""

import random
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.clustering import VehicleCalculator
from utils.local_search import apply_local_search, LocalSearchType


@dataclass
class SwapOperation:
    """Represents a swap in velocity"""
    i: int
    j: int
    probability: float


@dataclass
class Particle:
    """Particle in the swarm"""
    position: List[str]
    velocity: List[SwapOperation]
    personal_best: List[str]
    personal_best_duration: float
    current_duration: float


class PSOStrategy(BaseRoutingStrategy):
    """
    Particle Swarm Optimization for Vehicle Routing Problem.
    Uses K-Means clustering for multi-vehicle, then PSO for TSP.
    """

    # Default PSO parameters (based on Clerc's constriction)
    DEFAULT_CONFIG = {
        "swarm_size": 30,
        "max_iterations": 100,
        "inertia_weight": 0.729,  # Clerc's constriction
        "cognitive_weight": 1.49445,  # c1
        "social_weight": 1.49445,  # c2
        "velocity_clamp": 0.9,
        "max_no_improvement": 25,
        "local_search_rate": 0.15,  # Probability of applying local search
        "seed": None
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

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between two locations"""
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]

        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)

        return 15.0

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

    def _generate_random_velocity(self, n: int) -> List[SwapOperation]:
        """Generate random velocity for initialization"""
        velocity = []
        num_swaps = min(self.rng.randint(1, max(1, n // 2)), 5)

        for _ in range(num_swaps):
            velocity.append(SwapOperation(
                i=self.rng.randint(0, n - 1),
                j=self.rng.randint(0, n - 1),
                probability=self.rng.random() * 0.5
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

    def _get_difference_swaps(
        self,
        current: List[str],
        target: List[str],
        weight: float
    ) -> List[SwapOperation]:
        """Get swaps to transform current toward target"""
        swaps = []
        n = len(current)

        for i in range(n):
            if i < len(current) and i < len(target) and current[i] != target[i]:
                try:
                    j = current.index(target[i])
                    if j != i:
                        swaps.append(SwapOperation(
                            i=i,
                            j=j,
                            probability=weight * self.rng.random()
                        ))
                except ValueError:
                    pass

        return swaps

    def _apply_velocity(self, position: List[str], velocity: List[SwapOperation]) -> List[str]:
        """Apply velocity swaps probabilistically"""
        new_position = position.copy()
        n = len(new_position)

        for swap in velocity:
            if self.rng.random() < swap.probability:
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]

        return new_position

    def _update_velocity(
        self,
        current_velocity: List[SwapOperation],
        current_position: List[str],
        personal_best: List[str],
        global_best: List[str]
    ) -> List[SwapOperation]:
        """
        Calculate new velocity using PSO equation:
        v(t+1) = w*v(t) + c1*r1*(pbest-x) + c2*r2*(gbest-x)
        """
        new_velocity = []

        # Inertia: retain part of old velocity
        for swap in current_velocity:
            adjusted_prob = swap.probability * self.config["inertia_weight"]
            if adjusted_prob > 0.1:  # Threshold to prevent vanishing
                new_velocity.append(SwapOperation(
                    i=swap.i,
                    j=swap.j,
                    probability=min(adjusted_prob, self.config["velocity_clamp"])
                ))

        # Cognitive component: toward personal best
        pbest_swaps = self._get_difference_swaps(
            current_position, personal_best,
            self.config["cognitive_weight"]
        )
        new_velocity.extend(pbest_swaps)

        # Social component: toward global best
        gbest_swaps = self._get_difference_swaps(
            current_position, global_best,
            self.config["social_weight"]
        )
        new_velocity.extend(gbest_swaps)

        # Limit velocity size
        max_velocity = int(self.config["velocity_clamp"] * len(current_position) * 2)
        return new_velocity[:max_velocity]

    def _local_search(
        self,
        position: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        max_iterations: int = 10
    ) -> Tuple[List[str], float]:
        """
        Local search using shared 2-opt implementation.
        Provides exploitation capability to improve solutions.
        """
        return apply_local_search(
            route=position,
            depot=depot,
            time_matrix=time_matrix,
            coordinates=coordinates,
            search_type=LocalSearchType.TWO_OPT,
            max_iterations=max_iterations,
            first_improvement=False
        )

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle using PSO"""
        if not waypoints:
            return [], 0.0

        if len(waypoints) == 1:
            duration = (
                self._get_duration(depot, waypoints[0], time_matrix, coordinates) +
                self._get_duration(waypoints[0], depot, time_matrix, coordinates)
            )
            return waypoints, duration

        if len(waypoints) == 2:
            # Only 2 permutations possible
            d1 = self._calculate_route_duration(waypoints, depot, time_matrix, coordinates)
            d2 = self._calculate_route_duration(
                [waypoints[1], waypoints[0]], depot, time_matrix, coordinates
            )
            if d1 <= d2:
                return waypoints, d1
            return [waypoints[1], waypoints[0]], d2

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

        # Main PSO loop
        for iteration in range(self.config["max_iterations"]):
            improved = False

            for particle in swarm:
                # Update velocity
                new_velocity = self._update_velocity(
                    particle.velocity,
                    particle.position,
                    particle.personal_best,
                    global_best
                )

                # Apply velocity
                new_position = self._apply_velocity(particle.position, new_velocity)

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

            # Apply local search to global best periodically
            if self.rng.random() < self.config["local_search_rate"]:
                improved_position, improved_duration = self._local_search(
                    global_best, depot, time_matrix, coordinates, max_iterations=5
                )
                if improved_duration < global_best_duration:
                    global_best = improved_position
                    global_best_duration = improved_duration
                    improved = True

            if improved:
                no_improvement = 0
            else:
                no_improvement += 1

            if no_improvement >= self.config["max_no_improvement"]:
                break

        # Final local search on best solution
        final_position, final_duration = self._local_search(
            global_best, depot, time_matrix, coordinates, max_iterations=15
        )

        return final_position, final_duration

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
        if request.pso_config:
            self.config.update(request.pso_config)
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

        # Calculate vehicle assignments
        calculator = VehicleCalculator(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time
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
                vehicle_id=f"Araç {assignment['vehicle_index']} (PSO)",
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
