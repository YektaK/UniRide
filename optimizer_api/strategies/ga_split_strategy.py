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
from typing import List, Dict, Tuple, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.hybrid_base_strategy import HybridSplitBaseStrategy
from utils.data_loader import DataLoader
from uniride_core.adapters.demand_builder import build_student_demands, build_student_map
from uniride_core.algorithms.ga_operators import (
    cycle_crossover_2,
    mutate_permutation,
    order_crossover,
    partially_mapped_crossover,
)
from uniride_core.algorithms.ga_split_engine import (
    GAIndividual as Individual,
    diversify_population,
    educate_individual,
    evaluate_individual,
    evaluate_population,
    evolve_population,
    initialize_population,
    solve_ga_split,
    tournament_selection,
)
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
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
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



    def _initialize_population(self, waypoints: List[str], rng: random.Random) -> List[Individual]:
        """Initialize population with random and heuristic permutations"""
        return initialize_population(waypoints, self.config, rng)


    def _evaluate_individual(
        self,
        individual: Individual,
        depot: str,
        distance_matrix: Dict,
        demands: Dict,
        sw_capacity: int,
        so_capacity: int,
        max_tour_duration: float
    ) -> Individual:
        """Evaluate fitness using Split Decoder"""
        return evaluate_individual(
            individual,
            depot,
            distance_matrix,
            demands,
            sw_capacity,
            so_capacity,
            max_tour_duration,
        )

    def _evaluate_population(
        self,
        population: List[Individual],
        depot: str,
        distance_matrix: Dict,
        demands: Dict,
        sw_capacity: int,
        so_capacity: int,
        max_tour_duration: float
    ) -> List[Individual]:
        """Evaluate all individuals"""
        return evaluate_population(
            population,
            depot,
            distance_matrix,
            demands,
            sw_capacity,
            so_capacity,
            max_tour_duration,
        )

    def _tournament_selection(self, population: List[Individual], rng: random.Random) -> Individual:
        """Tournament selection"""
        return tournament_selection(population, self.config["tournament_size"], rng)

    def _order_crossover(self, parent1: List[str], parent2: List[str], rng: random.Random) -> Tuple[List[str], List[str]]:
        """Order Crossover (OX1)"""
        return order_crossover(parent1, parent2, rng)

    def _mutate(self, chromosome: List[str], rng: random.Random) -> List[str]:
        """Apply mutation operators"""
        return mutate_permutation(chromosome, rng)

    def _educate(self, individual: Individual, depot: str, 
                 distance_matrix: Dict) -> Individual:
        """
        Local search education (improvement).
        Apply 2-opt or similar to the giant tour.
        """
        return educate_individual(
            individual,
            depot,
            distance_matrix,
            str(self.config.get("local_search_type", "two_opt")),
        )

    def _diversify(self, population: List[Individual], rng: random.Random) -> List[Individual]:
        """
        Diversification when stuck.
        Keep best, replace worst with new random individuals.
        """
        return diversify_population(population, rng)

    def _evolve(self, population: List[Individual], rng: random.Random) -> List[Individual]:
        """Create next generation"""
        return evolve_population(population, self.config, rng)

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
        
        # Build distance matrix for all locations
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
    
    def _crossover_pmx(self, parent1: List[str], parent2: List[str], rng: random.Random) -> List[str]:
        """Partially Mapped Crossover (PMX)."""
        return partially_mapped_crossover(parent1, parent2, rng)
    
    def _crossover_cx2(self, parent1: List[str], parent2: List[str], rng: random.Random) -> List[str]:
        """Cycle Crossover 2 (CX2)."""
        return cycle_crossover_2(parent1, parent2, rng)
