"""
HHO-Split Hybrid Strategy for CVRPTW
Route-First, Cluster-Second Approach

Combines:
1. Harris Hawks Optimization (HHO) for giant tour optimization
2. Split Decoder for optimal partitioning into vehicle routes

Literature-based Configuration (Heidari et al., 2019; HHO for VRP, 2022):
- Population Size: 50 (VRP optimal range: 40-60)
- Max Iterations: 180 (Split decoder overhead compensation)
- Initial Energy: 2.0 (Slower energy decay = better exploration)
- Jump Probability: 0.4 (Soft besiege selection)
- Lévy Flight Scale: 0.3 (Escape local optima)

References:
- Heidari, A.A., et al. (2019). Harris hawks optimization: Algorithm and applications.
  Future Generation Computer Systems, 97, 849-872.
- Vehicle routing problems based on Harris Hawks optimization (Journal of Big Data, 2022)
"""

import logging
import random
import time
import math
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
class Hawk:
    """Hawk individual representing a giant tour"""
    position: List[str]  # Permutation of all customer locations
    fitness: float
    total_cost: float


class HHOSplitStrategy(HybridSplitBaseStrategy):
    """
    HHO-Split Hybrid Strategy for CVRPTW.
    
    Workflow:
    1. HHO population evolves permutations of all customers (giant tours)
    2. Split Decoder optimally partitions each tour into feasible routes
    3. Fitness is the total cost after optimal splitting
    
    HHO Characteristics:
    - Exploration: Random perching and Lévy flight
    - Transition: Escape energy determines exploitation phase
    - Exploitation: Four siege strategies based on prey behavior
      * Soft besiege (|E| >= 0.5, r < 0.5)
      * Hard besiege (|E| < 0.5, r < 0.5)
      * Soft besiege with progressive rapid dives
      * Hard besiege with progressive rapid dives
    
    Literature-optimized parameters for VRP with Split Decoder.
    """

    # Literature-based default configuration for VRP
    DEFAULT_CONFIG = {
        # Population parameters (Literature: 40-60 for VRP)
        "population_size": 50,
        "max_iterations": 180,

        # HHO-specific parameters (Literature: Heidari et al., 2019)
        "initial_energy": 2.0,        # Slower energy decay
        "jump_probability": 0.4,      # Soft besiege selection threshold
        "levy_flight_scale": 0.3,     # Lévy flight perturbation scale

        # Local search configuration
        "local_search_type": "hybrid",  # Options: two_opt, three_opt, or_opt, swap, cross_exchange, time_window_aware, hybrid
        "local_search_interval": 15,  # Apply local search every N generations

        # Convergence parameters
        "max_no_improvement": 35,

        # Random seed
        "seed": None,
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize HHO-Split strategy.
        
        Args:
            config: Optional configuration override.
                   Example: {"population_size": 60, "max_iterations": 200}
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)
        self._prey: Optional[Hawk] = None  # Best solution
        self._generation_stats = []

    @property
    def name(self) -> str:
        return "hho_split"

    @property
    def display_name(self) -> str:
        return "HHO-Split (Route-First)"

    @property
    def description(self) -> str:
        return "Harris Hawks + Optimal Split. Kaçış enerjisi ile adaptif arama."



    def _shuffle(self, items: List) -> List:
        """Shuffle list using internal RNG (Fisher-Yates)"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def _initialize_population(self, waypoints: List[str]) -> List[Hawk]:
        """Initialize hawk population with random positions"""
        hawks = []
        
        # Heuristic initialization: nearest neighbor
        nn_tour = self._nearest_neighbor_tour(waypoints)
        if nn_tour:
            hawks.append(Hawk(
                position=nn_tour,
                fitness=0.0,
                total_cost=float('inf')
            ))
        
        # Random permutations
        for _ in range(self.config["population_size"] - 1):
            position = self._shuffle(waypoints)
            hawks.append(Hawk(
                position=position,
                fitness=0.0,
                total_cost=float('inf')
            ))
        
        return hawks


    def _levy_flight(self, position: List[str], scale: Optional[float] = None) -> List[str]:
        """
        Perform Lévy flight mutation for escaping local optima.
        
        Lévy distribution provides random walks with occasional long jumps,
        useful for exploration in permutation problems.
        """
        if scale is None:
            scale = self.config["levy_flight_scale"]
        
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

    def _get_difference_swaps(self, current: List[str], target: List[str],
                               intensity: float) -> List[Tuple[int, int]]:
        """Get swaps to move current toward target with given intensity"""
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

    def _soft_besiege(self, hawk: Hawk, prey: Hawk, escape_energy: float) -> List[str]:
        """
        Soft besiege: When prey has enough energy to escape but still gets caught.
        Position update: X(t+1) = ΔX(t) - E * |J * Prey - X(t)|
        """
        # J is random jump strength (2 * rand in [0,2])
        J = 2 * (1 - self.rng.random())
        
        # Calculate movement toward prey
        intensity = abs(escape_energy * J)
        swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)
        
        return self._apply_swaps(hawk.position, swaps)

    def _hard_besiege(self, hawk: Hawk, prey: Hawk, escape_energy: float) -> List[str]:
        """
        Hard besiege: When prey is exhausted, hawks tightly surround it.
        Position update: X(t+1) = Prey - E * |Prey - X(t)|
        """
        intensity = abs(escape_energy)
        swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)
        
        return self._apply_swaps(hawk.position, swaps)

    def _soft_besiege_with_dives(self, hawk: Hawk, prey: Hawk, escape_energy: float,
                                  depot: str, distance_matrix: Dict) -> List[str]:
        """
        Soft besiege with progressive rapid dives.
        Hawks make rapid dives toward prey with Lévy flight movements.
        """
        best_position = hawk.position.copy()
        best_cost = hawk.total_cost
        
        # Attempt multiple dives
        for _ in range(3):
            # Move toward prey
            intensity = abs(escape_energy) * self.rng.random()
            swaps = self._get_difference_swaps(hawk.position, prey.position, intensity)
            candidate = self._apply_swaps(hawk.position, swaps)
            
            # Add Lévy flight perturbation
            candidate = self._levy_flight(candidate, scale=0.3)
            
            # Evaluate using giant tour approximation
            cost = self._calculate_giant_tour_cost(candidate, depot, distance_matrix)
            
            if cost < best_cost:
                best_position = candidate
                best_cost = cost
        
        return best_position

    def _hard_besiege_with_dives(self, hawk: Hawk, prey: Hawk, escape_energy: float) -> List[str]:
        """
        Hard besiege with progressive rapid dives.
        Combined besiege with Lévy flights for final exploitation.
        """
        # Calculate mean position
        mean_intensity = abs(escape_energy)
        swaps = self._get_difference_swaps(hawk.position, prey.position, mean_intensity)
        candidate = self._apply_swaps(hawk.position, swaps)
        
        # Apply strong Lévy flight
        candidate = self._levy_flight(candidate, scale=0.2)
        
        return candidate

    def _calculate_giant_tour_cost(self, tour: List[str], depot: str,
                                    distance_matrix: Dict) -> float:
        """Calculate approximate cost of giant tour"""
        if not tour:
            return 0.0
        
        total = distance_matrix.get(depot, {}).get(tour[0], DEFAULT_TRAVEL_FALLBACK_MINUTES)
        for i in range(len(tour) - 1):
            total += distance_matrix.get(tour[i], {}).get(tour[i + 1], DEFAULT_TRAVEL_FALLBACK_MINUTES)
        total += distance_matrix.get(tour[-1], {}).get(depot, DEFAULT_TRAVEL_FALLBACK_MINUTES)
        return total

    def _evaluate_hawk(self, hawk: Hawk, depot: str,
                       distance_matrix: Dict, demands: Dict,
                       sw_capacity: int, so_capacity: int,
                       max_tour_duration: float) -> float:
        """Evaluate hawk using Split Decoder"""
        result = decode_giant_tour(
            giant_tour=hawk.position,
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
        if hasattr(request, 'hho_config') and request.hho_config:
            self.config.update(request.hho_config)
            self.rng = random.Random(self.config.get("seed", self.seed))
        
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
        
        # Initialize population
        hawks = self._initialize_population(waypoints)
        
        # Evaluate initial population
        for hawk in hawks:
            cost = self._evaluate_hawk(
                hawk, depot.id, distance_matrix, demands,
                request.sw_capacity, request.so_capacity, request.max_travel_time
            )
            hawk.total_cost = cost
            hawk.fitness = 1.0 / cost if cost > 0 else 0.0
        
        # Find prey (best solution)
        prey = min(hawks, key=lambda h: h.total_cost)
        prey = Hawk(position=prey.position.copy(), fitness=prey.fitness, total_cost=prey.total_cost)
        
        no_improvement = 0
        
        # Main HHO loop
        for iteration in range(self.config["max_iterations"]):
            # Calculate escape energy (decreases over iterations)
            E0 = 2 * self.rng.random() - 1  # In [-1, 1]
            energy_decay = iteration / self.config["max_iterations"]
            E = 2 * E0 * (1 - energy_decay) * self.config["initial_energy"]
            
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
                        new_position = self._levy_flight(hawk.position)
                
                # Exploitation phase (|E| < 1)
                else:
                    if r >= self.config["jump_probability"]:
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
                                hawk, prey, E, depot.id, distance_matrix
                            )
                        # Hard besiege with progressive rapid dives
                        else:
                            new_position = self._hard_besiege_with_dives(hawk, prey, E)
                
                # Local search (every N generations)
                if iteration % self.config.get("local_search_interval", 15) == 0:
                    new_position = self._local_search_improve(
                        new_position, depot.id, distance_matrix
                    )
                
                # Evaluate new position
                cost = self._evaluate_hawk(
                    Hawk(position=new_position, fitness=0.0, total_cost=float('inf')),
                    depot.id, distance_matrix, demands,
                    request.sw_capacity, request.so_capacity, request.max_travel_time
                )
                
                # Update hawk
                if cost < hawk.total_cost:
                    hawk.position = new_position
                    hawk.total_cost = cost
                    hawk.fitness = 1.0 / cost if cost > 0 else 0.0
                
                # Update prey
                if hawk.total_cost < prey.total_cost:
                    prey = Hawk(
                        position=hawk.position.copy(),
                        fitness=hawk.fitness,
                        total_cost=hawk.total_cost
                    )
                    improved = True
            
            if improved:
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
        
        # Final split on best solution - use CVRPTW decoder if time windows enabled
        if use_time_windows and time_windows:
            # Convert TimeWindow objects to tuple format for split decoder
            tw_tuples = {}
            for loc, tw in time_windows.items():
                tw_tuples[loc] = (tw.earliest, tw.latest)
            
            final_result = decode_with_time_windows(
                giant_tour=prey.position,
                depot=depot.id,
                distance_matrix=distance_matrix,
                demands=demands,
                time_windows=tw_tuples,
                direction=direction,
                target_time=target_time_minutes,
                offset_minutes=offset_minutes,
                sw_capacity=request.sw_capacity,
                so_capacity=request.so_capacity,
                max_tour_duration=request.max_travel_time
            )
        else:
            final_result = decode_giant_tour(
                giant_tour=prey.position,
                depot=depot.id,
                distance_matrix=distance_matrix,
                demands=demands,
                sw_capacity=request.sw_capacity,
                so_capacity=request.so_capacity,
                max_tour_duration=request.max_travel_time
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
                vehicle_id=f"Araç {route_idx + 1} (HHO-Split)",
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
