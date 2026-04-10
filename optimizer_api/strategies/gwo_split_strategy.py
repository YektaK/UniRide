"""
GWO-Split Hybrid Strategy for CVRPTW
Route-First, Cluster-Second Approach

Combines:
1. Grey Wolf Optimizer (GWO) for giant tour optimization
2. Split Decoder for optimal partitioning into vehicle routes

Literature-based Configuration (Mirjalili et al., 2014; GWO for VRP, 2021):
- Population Size: 50 (VRP optimal range: 40-60)
- Max Iterations: 180 (Split decoder overhead compensation)
- Initial 'a': 2.5 (Slower decrease = better exploration-exploitation balance)
- Exploration Rate: 0.4 (Probability of random search)

References:
- Mirjalili, S., Mirjalili, S.M., & Lewis, A. (2014). Grey wolf optimizer.
  Advances in Engineering Software, 69, 46-61.
- Grey Wolf Optimizer for Green Vehicle Routing Problem (IJIES, 2023)
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
class Wolf:
    """Wolf individual in the pack (social hierarchy)"""
    position: List[str]  # Permutation of all customer locations
    fitness: float
    total_cost: float


class GWOSplitStrategy(HybridSplitBaseStrategy):
    """
    GWO-Split Hybrid Strategy for CVRPTW.
    
    Workflow:
    1. GWO pack evolves permutations of all customers (giant tours)
    2. Split Decoder optimally partitions each tour into feasible routes
    3. Fitness is the total cost after optimal splitting
    
    GWO Characteristics (Social Hierarchy):
    - Alpha (α): Best solution, leads the pack
    - Beta (β): Second best, assists alpha
    - Delta (δ): Third best, assists alpha and beta
    - Omega (ω): Rest of pack, follows leaders
    
    The algorithm balances exploration (searching new areas) and
    exploitation (refining good solutions) through parameter 'a'
    which decreases linearly from initial_a to 0.
    
    Literature-optimized parameters for VRP with Split Decoder.
    """

    # Literature-based default configuration for VRP
    DEFAULT_CONFIG = {
        # Population parameters (Literature: 40-60 for VRP)
        "population_size": 50,
        "max_iterations": 180,

        # GWO-specific parameters (Literature: Mirjalili et al., 2014)
        "initial_a": 2.5,           # Starting value of a (decreases to 0)
        "exploration_rate": 0.4,    # Probability of random exploration

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
        Initialize GWO-Split strategy.
        
        Args:
            config: Optional configuration override.
                   Example: {"population_size": 60, "initial_a": 3.0}
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)
        self._alpha: Optional[Wolf] = None  # Best solution
        self._beta: Optional[Wolf] = None   # Second best
        self._delta: Optional[Wolf] = None  # Third best
        self._generation_stats = []

    @property
    def name(self) -> str:
        return "gwo_split"

    @property
    def display_name(self) -> str:
        return "GWO-Split (Route-First)"

    @property
    def description(self) -> str:
        return "Gri Kurt + Optimal Split. Sosyal hiyerarşi ile arama."

    def _shuffle(self, items: List) -> List:
        """Shuffle list using internal RNG (Fisher-Yates)"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def _initialize_pack(self, waypoints: List[str]) -> List[Wolf]:
        """Initialize wolf pack with random positions"""
        pack = []
        
        # Heuristic initialization: nearest neighbor
        nn_tour = self._nearest_neighbor_tour(waypoints)
        if nn_tour:
            pack.append(Wolf(
                position=nn_tour,
                fitness=0.0,
                total_cost=float('inf')
            ))
        
        # Random permutations
        for _ in range(self.config["population_size"] - 1):
            position = self._shuffle(waypoints)
            pack.append(Wolf(
                position=position,
                fitness=0.0,
                total_cost=float('inf')
            ))
        
        return pack


    def _get_difference_swaps(self, current: List[str], leader: List[str], 
                               a: float) -> List[Tuple[int, int]]:
        """
        Calculate swaps to move wolf toward leader.
        In continuous GWO, this would be a vector difference.
        For TSP (permutation), we use swap operations weighted by 'a'.
        """
        swaps = []
        n = len(current)
        
        for i in range(n):
            if current[i] != leader[i]:
                try:
                    j = current.index(leader[i])
                    # Random factor based on 'a' (exploration-exploitation balance)
                    if self.rng.random() < a / 2:
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

    def _update_position(self, wolf: Wolf, alpha: Wolf, beta: Wolf, delta: Wolf, 
                         a: float) -> List[str]:
        """
        Update wolf position based on alpha, beta, delta.
        
        In GWO, each wolf updates its position based on the three best wolves:
        X(t+1) = (X1 + X2 + X3) / 3
        
        For permutation problems, we combine swap suggestions from each leader
        with different weights (alpha > beta > delta).
        """
        new_position = wolf.position.copy()
        
        # Get swap suggestions from each leader
        alpha_swaps = self._get_difference_swaps(wolf.position, alpha.position, a)
        beta_swaps = self._get_difference_swaps(wolf.position, beta.position, a)
        delta_swaps = self._get_difference_swaps(wolf.position, delta.position, a)
        
        # Combine swaps with weights (alpha has highest weight)
        all_swaps = []
        
        # Alpha has highest weight (0.7 probability)
        for swap in alpha_swaps:
            if self.rng.random() < 0.7:
                all_swaps.append(swap)
        
        # Beta has medium weight (0.5 probability)
        for swap in beta_swaps:
            if self.rng.random() < 0.5:
                all_swaps.append(swap)
        
        # Delta has lower weight (0.3 probability)
        for swap in delta_swaps:
            if self.rng.random() < 0.3:
                all_swaps.append(swap)
        
        # Apply swaps
        if all_swaps:
            # Apply only a subset of swaps to maintain diversity
            num_swaps = min(len(all_swaps), max(1, int(len(all_swaps) * a / 2)))
            selected_swaps = self.rng.sample(all_swaps, min(num_swaps, len(all_swaps)))
            new_position = self._apply_swaps(wolf.position, selected_swaps)
        
        return new_position

    def _calculate_giant_tour_cost(self, tour: List[str], depot: str,
                                    distance_matrix: Dict) -> float:
        """Calculate approximate cost of giant tour"""
        if not tour:
            return 0.0
        
        total = distance_matrix.get(depot, {}).get(tour[0], 15.0)
        for i in range(len(tour) - 1):
            total += distance_matrix.get(tour[i], {}).get(tour[i + 1], 15.0)
        total += distance_matrix.get(tour[-1], {}).get(depot, 15.0)
        return total

    def _evaluate_wolf(self, wolf: Wolf, depot: str,
                       distance_matrix: Dict, demands: Dict,
                       sw_capacity: int, so_capacity: int,
                       max_tour_duration: float) -> float:
        """Evaluate wolf using Split Decoder"""
        result = decode_giant_tour(
            giant_tour=wolf.position,
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
        if hasattr(request, 'gwo_config') and request.gwo_config:
            self.config.update(request.gwo_config)
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
        
        # Initialize pack
        pack = self._initialize_pack(waypoints)
        
        # Evaluate initial pack and identify leaders
        for wolf in pack:
            cost = self._evaluate_wolf(
                wolf, depot.id, distance_matrix, demands,
                request.sw_capacity, request.so_capacity, request.max_travel_time
            )
            wolf.total_cost = cost
            wolf.fitness = 1.0 / cost if cost > 0 else 0.0
        
        # Sort and identify alpha, beta, delta
        pack.sort(key=lambda w: w.total_cost)
        alpha = Wolf(position=pack[0].position.copy(), fitness=pack[0].fitness, total_cost=pack[0].total_cost)
        beta = Wolf(position=pack[1].position.copy(), fitness=pack[1].fitness, total_cost=pack[1].total_cost) if len(pack) > 1 else alpha
        delta = Wolf(position=pack[2].position.copy(), fitness=pack[2].fitness, total_cost=pack[2].total_cost) if len(pack) > 2 else beta
        
        no_improvement = 0
        
        # Main GWO loop
        for iteration in range(self.config["max_iterations"]):
            # Calculate 'a' (decreases linearly from initial_a to 0)
            a = self.config["initial_a"] * (1 - iteration / self.config["max_iterations"])
            
            improved = False
            
            for wolf in pack:
                # Exploration: random search
                if self.rng.random() < self.config["exploration_rate"] * a / self.config["initial_a"]:
                    # Random perturbation
                    new_position = self._shuffle(wolf.position)
                else:
                    # Exploitation: move toward leaders
                    new_position = self._update_position(wolf, alpha, beta, delta, a)
                
                # Local search (every N generations)
                if iteration % self.config.get("local_search_interval", 15) == 0:
                    new_position = self._local_search_improve(
                        new_position, depot.id, distance_matrix
                    )
                
                # Evaluate new position
                cost = self._evaluate_wolf(
                    Wolf(position=new_position, fitness=0.0, total_cost=float('inf')),
                    depot.id, distance_matrix, demands,
                    request.sw_capacity, request.so_capacity, request.max_travel_time
                )
                
                # Update wolf if better
                if cost < wolf.total_cost:
                    wolf.position = new_position
                    wolf.total_cost = cost
                    wolf.fitness = 1.0 / cost if cost > 0 else 0.0
                
                # Update leaders
                if wolf.total_cost < alpha.total_cost:
                    delta = Wolf(position=beta.position.copy(), fitness=beta.fitness, total_cost=beta.total_cost)
                    beta = Wolf(position=alpha.position.copy(), fitness=alpha.fitness, total_cost=alpha.total_cost)
                    alpha = Wolf(position=wolf.position.copy(), fitness=wolf.fitness, total_cost=wolf.total_cost)
                    improved = True
                elif wolf.total_cost < beta.total_cost:
                    delta = Wolf(position=beta.position.copy(), fitness=beta.fitness, total_cost=beta.total_cost)
                    beta = Wolf(position=wolf.position.copy(), fitness=wolf.fitness, total_cost=wolf.total_cost)
                    improved = True
                elif wolf.total_cost < delta.total_cost:
                    delta = Wolf(position=wolf.position.copy(), fitness=wolf.fitness, total_cost=wolf.total_cost)
                    improved = True
            
            if improved:
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
        
        # Final split on best solution (alpha) - use CVRPTW decoder if time windows enabled
        if use_time_windows and time_windows:
            # Convert TimeWindow objects to tuple format for split decoder
            tw_tuples = {}
            for loc, tw in time_windows.items():
                tw_tuples[loc] = (tw.earliest, tw.latest)
            
            final_result = decode_with_time_windows(
                giant_tour=alpha.position,
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
                giant_tour=alpha.position,
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
                vehicle_id=f"Araç {route_idx + 1} (GWO-Split)",
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
