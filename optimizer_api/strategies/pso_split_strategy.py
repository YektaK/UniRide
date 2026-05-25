"""
PSO-Split Hybrid Strategy for CVRPTW
Route-First, Cluster-Second Approach

Combines:
1. Particle Swarm Optimization (PSO) for giant tour optimization
2. Split Decoder for optimal partitioning into vehicle routes

Literature-based Configuration (Clerc & Kennedy, 2002; PSO for VRP Survey, 2024):
- Swarm Size: 60 (VRP optimal range: 50-80)
- Max Iterations: 200 (Split decoder overhead compensation)
- Inertia Weight: [0.4, 0.9] linear decay (exploration to exploitation)
- Cognitive/Social Weights: 2.0 each (balanced personal and social learning)
- Velocity Clamp: 0.7 (permutation problem constraint)
- Local Search Interval: Every 20 generations

References:
- Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization. IEEE ICNN.
- Clerc, M., & Kennedy, J. (2002). The particle swarm-explosion, stability, and convergence.
- PSO for VRP: A Survey and Comparative Analysis (Springer, 2024)
"""

import logging
import random
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

logger = logging.getLogger(__name__)

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from strategies.hybrid_base_strategy import HybridSplitBaseStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.split_decoder import decode_giant_tour, decode_with_time_windows, Direction
from utils.local_search import LocalSearchType, apply_local_search


@dataclass
class Particle:
    """Particle representing a giant tour (TSP permutation)"""
    position: List[str]  # Permutation of all customer locations
    velocity: List[Tuple[int, int, float]]  # Swap operations (i, j, probability)
    personal_best: List[str]
    personal_best_cost: float
    current_cost: float


class PSOSplitStrategy(HybridSplitBaseStrategy):
    """
    PSO-Split Hybrid Strategy for CVRPTW.
    
    Workflow:
    1. PSO swarm evolves permutations of all customers (giant tours)
    2. Split Decoder optimally partitions each tour into feasible routes
    3. Fitness is the total cost after optimal splitting
    
    Advantages:
    - Fast convergence due to PSO's social learning
    - Optimal partitioning guaranteed for each tour
    - Good balance of exploration and exploitation
    
    Literature-optimized parameters for VRP with Split Decoder.
    """

    # Literature-based default configuration for VRP
    DEFAULT_CONFIG = {
        # Population parameters (Literature: 50-80 for VRP)
        "swarm_size": 60,
        "max_iterations": 200,

        # PSO coefficients (Literature: Clerc's constriction with modifications)
        "inertia_weight": 0.9,      # Starting value, linear decay to inertia_min
        "inertia_min": 0.4,         # Ending inertia value
        "cognitive_weight": 2.0,    # c1: personal best attraction
        "social_weight": 2.0,       # c2: global best attraction
        "velocity_clamp": 0.7,      # Permutation problems: 0.5-0.8

        # Local search configuration
        "local_search_type": "hybrid",  # Options: two_opt, three_opt, or_opt, swap, cross_exchange, time_window_aware, hybrid
        "local_search_interval": 20,  # Apply local search every N generations

        # Convergence parameters
        "max_no_improvement": 40,

        # Random seed
        "seed": None,
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize PSO-Split strategy.
        
        Args:
            config: Optional configuration override.
                   Example: {"swarm_size": 80, "max_iterations": 250}
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self._global_best: Optional[List[str]] = None
        self._generation_stats = []

    @property
    def name(self) -> str:
        return "pso_split"

    @property
    def display_name(self) -> str:
        return "PSO-Split (Route-First)"

    @property
    def description(self) -> str:
        return "Parçacık Sürü + Optimal Split. Hızlı yakınsama, yüksek kalite."

    def _shuffle(self, items: List, rng: random.Random) -> List:
        """Shuffle list using provided RNG (Fisher-Yates)"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def _initialize_swarm(self, waypoints: List[str], rng: random.Random) -> List[Particle]:
        """Initialize swarm with random positions and empty velocities"""
        swarm = []
        
        # Heuristic initialization: nearest neighbor
        nn_tour = self._nearest_neighbor_tour(waypoints)
        if nn_tour:
            swarm.append(Particle(
                position=nn_tour,
                velocity=[],
                personal_best=nn_tour.copy(),
                personal_best_cost=float('inf'),
                current_cost=float('inf')
            ))
        
        # Random permutations
        for _ in range(self.config["swarm_size"] - 1):
            position = self._shuffle(waypoints, rng)
            swarm.append(Particle(
                position=position,
                velocity=[],
                personal_best=position.copy(),
                personal_best_cost=float('inf'),
                current_cost=float('inf')
            ))
        
        return swarm


    def _calculate_giant_tour_cost(self, tour: List[str], depot: str,
                                    distance_matrix: Dict) -> float:
        """Calculate approximate cost of giant tour (for velocity updates)"""
        if not tour:
            return 0.0
        
        total = distance_matrix.get(depot, {}).get(tour[0], DEFAULT_TRAVEL_FALLBACK_MINUTES)
        for i in range(len(tour) - 1):
            total += distance_matrix.get(tour[i], {}).get(tour[i + 1], DEFAULT_TRAVEL_FALLBACK_MINUTES)
        total += distance_matrix.get(tour[-1], {}).get(depot, DEFAULT_TRAVEL_FALLBACK_MINUTES)
        return total

    def _get_difference_swaps(self, current: List[str], target: List[str],
                                weight: float, rng: random.Random) -> List[Tuple[int, int, float]]:
        """
        Get weighted swaps to transform current toward target.
        Returns: List of (i, j, probability) tuples.
        """
        swaps = []
        n = len(current)
        
        for i in range(n):
            if i < len(current) and i < len(target) and current[i] != target[i]:
                try:
                    j = current.index(target[i])
                    if j != i:
                        swaps.append((i, j, weight * rng.random()))
                except ValueError:
                    pass
        
        return swaps

    def _apply_velocity(self, position: List[str],
                        velocity: List[Tuple[int, int, float]], rng: random.Random) -> List[str]:
        """Apply velocity swaps probabilistically"""
        new_position = position.copy()
        n = len(new_position)

        for swap in velocity:
            if len(swap) >= 3 and rng.random() < swap[2]:
                i, j = swap[0], swap[1]
                if 0 <= i < n and 0 <= j < n:
                    new_position[i], new_position[j] = new_position[j], new_position[i]
        
        return new_position

    def _update_velocity(self, particle: Particle, global_best: Optional[List[str]],
                         inertia: float, rng: random.Random) -> List[Tuple[int, int, float]]:
        """
        Calculate new velocity using PSO equation:
        v(t+1) = w*v(t) + c1*r1*(pbest-x) + c2*r2*(gbest-x)
        """
        new_velocity = []
        
        # Inertia: retain part of old velocity (weighted by inertia)
        for swap in particle.velocity:
            if len(swap) >= 3:
                adjusted_prob = swap[2] * inertia
                if adjusted_prob > 0.1:  # Threshold to prevent vanishing
                    new_velocity.append((swap[0], swap[1], 
                                        min(adjusted_prob, self.config["velocity_clamp"])))
        
        # Cognitive component: toward personal best
        c1_swaps = self._get_difference_swaps(
            particle.position, particle.personal_best,
            self.config["cognitive_weight"], rng
        )
        new_velocity.extend(c1_swaps)

        # Social component: toward global best
        if global_best is not None:
            c2_swaps = self._get_difference_swaps(
                particle.position, global_best,
                self.config["social_weight"], rng
            )
            new_velocity.extend(c2_swaps)
        
        # Limit velocity size
        max_velocity = int(self.config["velocity_clamp"] * len(particle.position))
        return new_velocity[:max_velocity]

    def _evaluate_particle(self, particle: Particle, depot: str,
                           distance_matrix: Dict, demands: Dict,
                           sw_capacity: int, so_capacity: int,
                           max_tour_duration: float) -> float:
        """Evaluate particle using Split Decoder"""
        result = decode_giant_tour(
            giant_tour=particle.position,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
            max_tour_duration=max_tour_duration
        )
        
        if result["num_vehicles"] == 0:
            return float('inf')
        
        # Multi-objective: minimize both cost and vehicles
        total_cost = result["total_cost"]
        num_vehicles = result["num_vehicles"]
        return total_cost + num_vehicles * 50  # Vehicle penalty

    def _local_search_improve(self, tour: List[str], depot: str,
                               distance_matrix: Dict) -> List[str]:
        """Apply configurable local search to giant tour"""
        def cost_func(route):
            return self._calculate_giant_tour_cost(route, depot, distance_matrix)

        try:
            ls_type_str = self.config.get("local_search_type", "hybrid")
            ls_type = LocalSearchType(ls_type_str)
            improved_route, _ = apply_local_search(tour, cost_func, ls_type)
            return improved_route
        except Exception as exc:
            logger.debug("Local search failed, returning original tour: %s", exc)
            return tour

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Main optimization entry point with CVRPTW support"""
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
                direction=getattr(request, 'direction', Direction.PICKUP),
                time_windows_used=False
            )
        
        # CVRPTW: Extract time windows if enabled
        use_time_windows = getattr(request, 'use_time_windows', False)
        time_windows = {}
        target_time_minutes = None
        direction = getattr(request, 'direction', Direction.PICKUP)
        offset_minutes = getattr(request, 'offset_minutes', 10)
        
        if use_time_windows:
            time_windows = request.get_time_windows()
            if request.target_time:
                parts = request.target_time.split(":")
                target_time_minutes = int(parts[0]) * 60 + int(parts[1])
        
        # Override config if provided (user-customizable)
        # Singleton self.config korunuyor; her istek icin local kopya
        effective_config = dict(self.config)
        if request.pso_config:
            effective_config = {**self.config, **request.pso_config}
            rng = random.Random(effective_config.get("seed", self.seed))
        else:
            rng = random.Random(self.seed)

        # Load data
        data_loader = DataLoader.get_instance()
        location_ids = [depot.id] + [s.location_code for s in students]
        raw_matrix = data_loader.get_submatrix(location_ids)
        
        # Build time matrix
        time_matrix = {}
        for i, from_loc in enumerate(location_ids):
            time_matrix[from_loc] = {}
            for j, to_loc in enumerate(location_ids):
                time_matrix[from_loc][to_loc] = raw_matrix[i][j]
        
        # Build coordinates
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords
        
        # Build distance matrix
        all_locations = [depot.id] + [s.location_code for s in students]
        distance_matrix = self._build_distance_matrix(all_locations, time_matrix, coordinates)
        
        # Build demands
        demands = {}
        student_map = {}
        for s in students:
            sw_d = 1 if s.disability_type == "Sw" else 0
            so_d = 1 if s.disability_type != "Sw" else 0
            demands[s.location_code] = (sw_d, so_d)
            student_map[s.location_code] = s
        
        # Customer locations (without depot)
        waypoints = [s.location_code for s in students]
        
        # Initialize swarm
        swarm = self._initialize_swarm(waypoints, rng)
        
        # Evaluate initial swarm
        global_best = None
        global_best_cost = float('inf')
        
        for particle in swarm:
            cost = self._evaluate_particle(
                particle, depot.id, distance_matrix, demands,
                request.sw_capacity, request.so_capacity, request.max_travel_time
            )
            particle.current_cost = cost
            particle.personal_best_cost = cost
            
            if cost < global_best_cost:
                global_best_cost = cost
                global_best = particle.position.copy()
        
        no_improvement = 0
        
        # Main PSO loop
        for iteration in range(self.config["max_iterations"]):
            # Linear inertia decay
            inertia = self.config["inertia_weight"] - (
                (self.config["inertia_weight"] - self.config["inertia_min"]) * 
                iteration / self.config["max_iterations"]
            )
            
            improved = False
            
            for particle in swarm:
                # Update velocity
                particle.velocity = self._update_velocity(particle, global_best, inertia, rng)

                # Apply velocity
                new_position = self._apply_velocity(particle.position, particle.velocity, rng)
                
                # Local search (every N generations)
                if iteration % self.config.get("local_search_interval", 20) == 0:
                    new_position = self._local_search_improve(
                        new_position, depot.id, distance_matrix
                    )
                
                # Evaluate
                new_cost = self._evaluate_particle(
                    particle, depot.id, distance_matrix, demands,
                    request.sw_capacity, request.so_capacity, request.max_travel_time
                )
                
                # Update personal best
                if new_cost < particle.personal_best_cost:
                    particle.personal_best = new_position.copy()
                    particle.personal_best_cost = new_cost
                
                particle.position = new_position
                particle.current_cost = new_cost
                
                # Update global best
                if new_cost < global_best_cost:
                    global_best = new_position.copy()
                    global_best_cost = new_cost
                    improved = True
            
            if improved:
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
        
        # Final split on best solution
        if global_best is None:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=False,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time
            )

        # Type assertion for LSP - we've already checked for None above
        assert global_best is not None

        # Final split on best solution - use CVRPTW decoder if time windows enabled
        if use_time_windows and time_windows:
            # Convert TimeWindow objects to tuple format for split decoder
            tw_tuples = {}
            for loc, tw in time_windows.items():
                tw_tuples[loc] = (tw.earliest, tw.latest)
            
            final_result = decode_with_time_windows(
                giant_tour=global_best,
                depot=depot.id,
                distance_matrix=distance_matrix,
                demands=demands,
                time_windows=tw_tuples,
                direction=direction,
                target_time=target_time_minutes,
                offset_minutes=offset_minutes,
                sw_capacity=request.sw_capacity,
                so_capacity=request.so_capacity,
                max_tour_duration=request.max_travel_time,
                is_asymmetric=request.is_asymmetric
            )
        else:
            final_result = decode_giant_tour(
                giant_tour=global_best,
                depot=depot.id,
                distance_matrix=distance_matrix,
                demands=demands,
                sw_capacity=request.sw_capacity,
                so_capacity=request.so_capacity,
                max_tour_duration=request.max_travel_time,
                is_asymmetric=request.is_asymmetric
            )
        
        # Build response routes
        routes = []
        for route_idx, route_locations in enumerate(final_result["routes"]):
            route_steps = []
            total_duration = 0
            sw_count = 0
            so_count = 0
            route_student_ids = []
            prev = depot.id
            
            for loc in route_locations:
                duration = self._get_duration(prev, loc, time_matrix, coordinates)
                total_duration += duration
                
                route_steps.append(RouteStep(
                    location1=prev,
                    location2=loc,
                    duration=round(duration, 2),
                    distance=0.0
                ))
                
                if loc in student_map:
                    s = student_map[loc]
                    route_student_ids.append(s.id)
                    if s.disability_type == "Sw":
                        sw_count += 1
                    else:
                        so_count += 1
                
                prev = loc
            
            # Return to depot
            duration = self._get_duration(prev, depot.id, time_matrix, coordinates)
            total_duration += duration
            route_steps.append(RouteStep(
                location1=prev,
                location2=depot.id,
                duration=round(duration, 2),
                distance=0.0
            ))
            
            routes.append(VehicleRoute(
                vehicle_id=f"Araç {route_idx + 1} (PSO-Split)",
                route_details=route_steps,
                total_duration_minutes=round(total_duration, 2),
                total_distance_km=0.0,
                sw_count=sw_count,
                so_count=so_count,
                student_ids=route_student_ids
            ))
        
        execution_time = time.time() - start_time
        
        # Calculate total time window violations
        total_tw_violations = final_result.get('time_window_violations', 0)
        
        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(r.total_duration_minutes for r in routes),
            execution_time_seconds=round(execution_time, 4),
            direction=direction,
            time_windows_used=use_time_windows and len(time_windows) > 0,
            total_time_window_violations=total_tw_violations
        )
