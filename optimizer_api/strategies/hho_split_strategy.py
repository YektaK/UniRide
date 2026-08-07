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

import random
import time
from typing import List, Dict, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.hybrid_base_strategy import HybridSplitBaseStrategy
from strategies.promoted_config_loader import get_promoted_strategy_params
from utils.data_loader import DataLoader
from uniride_core.adapters.demand_builder import (
    build_student_demands,
    build_student_map,
    student_occurrence_keys,
)
from uniride_core.algorithms.hho_split_engine import solve_hho_split
from uniride_core.algorithms.string_split_decoder import Direction
from strategies.seed_utils import resolve_seed, make_rng


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
        promoted = {} if config is not None else get_promoted_strategy_params(
            ("hho_split", "hho-split", "HHO-Split", "CVRPTW-HHO-Split", "CVRP-HHO-Split"),
            problem_type="cvrptw",
            matrix_kind="travel_time",
        )
        self.config = {**self.DEFAULT_CONFIG, **promoted, **(config or {})}
        self.seed = resolve_seed(self.config)
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
        if hasattr(request, 'hho_config') and request.hho_config:
            effective_config = {**self.config, **request.hho_config}
            rng = make_rng(effective_config, default=self.seed)
        else:
            rng = random.Random(self.seed)

        # Load data
        data_loader = DataLoader.get_instance()
        occurrence_keys = student_occurrence_keys(students)
        node_keys = [depot.id] + occurrence_keys
        physical_ids = [depot.id] + [s.location_code for s in students]
        raw_matrix = data_loader.get_submatrix(physical_ids)
        
        # Build time matrix (re-key positional submatrix to occurrence nodes)
        time_matrix = {}
        for i, from_loc in enumerate(node_keys):
            time_matrix[from_loc] = {}
            for j, to_loc in enumerate(node_keys):
                time_matrix[from_loc][to_loc] = raw_matrix[i][j]
        
        # Build coordinates
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s, key in zip(students, occurrence_keys):
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[key] = coords
        
        # Build distance matrix
        all_locations = node_keys
        distance_matrix = self._build_distance_matrix(all_locations, time_matrix, coordinates)
        
        # Build demands
        demands = build_student_demands(students)
        student_map = build_student_map(students)
        
        # Customer locations (without depot)
        waypoints = occurrence_keys
        
        tw_tuples = {}
        if use_time_windows and time_windows:
            for loc, tw in time_windows.items():
                tw_tuples[loc] = (tw.earliest, tw.latest)

        solution = solve_hho_split(
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
