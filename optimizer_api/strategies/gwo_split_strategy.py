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

import random
import time
from typing import List, Dict, Tuple, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.hybrid_base_strategy import HybridSplitBaseStrategy
from utils.data_loader import DataLoader
from uniride_core.adapters.demand_builder import build_student_demands, build_student_map
from uniride_core.algorithms.gwo_split_engine import (
    Wolf,
    apply_swaps,
    difference_swaps,
    evaluate_wolf,
    initialize_pack,
    solve_gwo_split,
    update_position,
)
from uniride_core.algorithms.meta_split_common import (
    giant_tour_cost,
    local_search_improve,
    shuffle_permutation,
    split_penalized_cost,
)
from uniride_core.algorithms.string_split_decoder import Direction


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

    def _shuffle(self, items: List, rng: random.Random) -> List:
        """Shuffle list using provided RNG (Fisher-Yates)"""
        return shuffle_permutation(items, rng)

    def _initialize_pack(self, waypoints: List[str], rng: random.Random) -> List[Wolf]:
        """Initialize wolf pack with random positions"""
        return initialize_pack(waypoints, self.config, rng)


    def _get_difference_swaps(self, current: List[str], leader: List[str],
                                a: float, rng: random.Random) -> List[Tuple[int, int]]:
        """
        Calculate swaps to move wolf toward leader.
        In continuous GWO, this would be a vector difference.
        For TSP (permutation), we use swap operations weighted by 'a'.
        """
        return difference_swaps(current, leader, a, rng)

    def _apply_swaps(self, position: List[str], swaps: List[Tuple[int, int]]) -> List[str]:
        """Apply swap operations to position"""
        return apply_swaps(position, swaps)

    def _update_position(self, wolf: Wolf, alpha: Wolf, beta: Wolf, delta: Wolf,
                         a: float, rng: random.Random) -> List[str]:
        """
        Update wolf position based on alpha, beta, delta.
        
        In GWO, each wolf updates its position based on the three best wolves:
        X(t+1) = (X1 + X2 + X3) / 3
        
        For permutation problems, we combine swap suggestions from each leader
        with different weights (alpha > beta > delta).
        """
        return update_position(wolf, alpha, beta, delta, a, rng)

    def _calculate_giant_tour_cost(self, tour: List[str], depot: str,
                                    distance_matrix: Dict) -> float:
        """Calculate approximate cost of giant tour"""
        return giant_tour_cost(tour, depot, distance_matrix)

    def _evaluate_wolf(self, wolf: Wolf, depot: str,
                       distance_matrix: Dict, demands: Dict,
                       sw_capacity: int, so_capacity: int,
                       max_tour_duration: float) -> float:
        """Evaluate wolf using Split Decoder"""
        return split_penalized_cost(
            wolf.position,
            depot,
            distance_matrix,
            demands,
            sw_capacity,
            so_capacity,
            max_tour_duration,
        )

    def _local_search_improve(self, tour: List[str], depot: str,
                               distance_matrix: Dict) -> List[str]:
        """Apply configurable local search to giant tour"""
        return local_search_improve(tour, depot, distance_matrix, str(self.config.get("local_search_type", "hybrid")))

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
        if hasattr(request, 'gwo_config') and request.gwo_config:
            effective_config = {**self.config, **request.gwo_config}
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
        demands = build_student_demands(students)
        student_map = build_student_map(students)
        
        # Customer locations (without depot)
        waypoints = [s.location_code for s in students]
        
        tw_tuples = {}
        if use_time_windows and time_windows:
            for loc, tw in time_windows.items():
                tw_tuples[loc] = (tw.earliest, tw.latest)

        solution = solve_gwo_split(
            waypoints=waypoints,
            depot=depot.id,
            distance_matrix=distance_matrix,
            demands=demands,
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_duration=request.max_travel_time,
            config=effective_config,
            rng=rng,
            use_time_windows=use_time_windows,
            time_windows=tw_tuples,
            direction=direction,
            target_time=target_time_minutes,
            offset_minutes=offset_minutes,
            is_asymmetric=request.is_asymmetric,
        )
        final_result = solution.final_result
        
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
