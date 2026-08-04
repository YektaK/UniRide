"""
GA-Split Hybrid Strategy for CVRPTW
Route-First, Cluster-Second Approach

Combines:
1. Genetic Algorithm for TSP (giant tour optimization)
2. Split Decoder for optimal partitioning into vehicle routes

This approach is often superior to cluster-first methods because:
- The GA optimizes the overall route sequence
- Split decoder guarantees optimal partitioning for a given tour
- Better explores the solution space

Reference:
Prins, C. (2004). A simple and effective evolutionary algorithm for VRP.
Computers & Operations Research, 31(12), 1985-2002.
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
from uniride_core.algorithms.ga_split_engine import solve_ga_split
from uniride_core.algorithms.string_split_decoder import Direction


class GASplitStrategy(HybridSplitBaseStrategy):
    """
    GA-Split Hybrid Strategy for CVRPTW.
    
    Workflow:
    1. GA evolves permutations of all customers (giant tours)
    2. Split Decoder optimally partitions each tour into feasible routes
    3. Fitness is the total cost after optimal splitting
    
    Advantages over cluster-first approaches:
    - Better exploration of solution space
    - Optimal partitioning guaranteed for each tour
    - Simpler representation (single permutation)
    - Often finds better solutions with fewer vehicles
    
    Based on Prins (2004) Evolutionary Algorithm for VRP.
    """

    DEFAULT_CONFIG = {
        "population_size": 50,
        "max_iterations": 100,
        "crossover_rate": 0.85,
        "mutation_rate": 0.20,
        "elite_count": 3,
        "tournament_size": 4,
        "max_no_improvement": 25,
        "seed": None,
        "local_search_type": "hybrid",  # Options: two_opt, three_opt, or_opt, swap, cross_exchange, time_window_aware, hybrid
        "local_search_interval": 10,  # Apply local search every N generations
        "diversify_threshold": 30,    # Diversify after N generations without improvement
    }

    def __init__(self, config: Optional[Dict] = None):
        promoted = {} if config is not None else get_promoted_strategy_params(
            ("ga_split", "ga-split", "GA-Split", "CVRPTW-GA-Split", "CVRP-GA-Split"),
            problem_type="cvrptw",
            matrix_kind="travel_time",
        )
        self.config = {**self.DEFAULT_CONFIG, **promoted, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self._best_individual = None
        self._generation_stats = []

    @property
    def name(self) -> str:
        return "ga_split"

    @property
    def display_name(self) -> str:
        return "GA-Split Hybrid"

    @property
    def description(self) -> str:
        return "Route-first yaklaşımı. GA giant tour + Optimal Split decoder."



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
                direction=request.direction,
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
        
        # Override config
        # Singleton self.config korunuyor; her istek icin local kopya
        effective_config = dict(self.config)
        if request.ga_config:
            effective_config = {**self.config, **request.ga_config}
            rng = random.Random(effective_config.get("seed", self.seed))
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
        
        # Build distance matrix for all locations
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

        solution = solve_ga_split(
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
                vehicle_id=f"Araç {route_idx + 1} (GA-Split)",
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


class GAEnhancedSplitStrategy(GASplitStrategy):
    """
    Enhanced GA-Split with additional features from HGS (Hybrid Genetic Search):
    
    Features:
    - Population diversity management
    - Intensification/diversification balance
    - Adaptive parameters
    - Multiple crossover operators
    """
    
    @property
    def name(self) -> str:
        return "ga_split_enhanced"
    
    @property
    def display_name(self) -> str:
        return "GA-Split Enhanced (HGS-style)"
