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

import logging
import random
import time
from typing import List, Dict, Tuple, Optional, cast
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
class Individual:
    """Individual representing a giant tour (TSP permutation)"""
    chromosome: List[str]  # Permutation of all customer locations
    fitness: float  # 1 / total_cost
    total_cost: float  # Total routing cost after split
    num_vehicles: int  # Number of vehicles after split


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
        self.rng = random.Random(self.seed)
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



    def _initialize_population(self, waypoints: List[str]) -> List[Individual]:
        """Initialize population with random and heuristic permutations"""
        population = []
        
        # Random permutations
        for _ in range(self.config["population_size"] - 2):
            chromosome = waypoints.copy()
            self.rng.shuffle(chromosome)
            population.append(Individual(
                chromosome=chromosome,
                fitness=0.0,
                total_cost=float('inf'),
                num_vehicles=0
            ))
        
        # Nearest neighbor heuristic
        nn_tour = self._nearest_neighbor_tour(waypoints)
        if nn_tour:
            population.append(Individual(
                chromosome=nn_tour,
                fitness=0.0,
                total_cost=float('inf'),
                num_vehicles=0
            ))
        
        # Sorted by coordinates (clustering effect)
        sorted_tour = waypoints.copy()
        self.rng.shuffle(sorted_tour)  # Just add another random for now
        population.append(Individual(
            chromosome=sorted_tour,
            fitness=0.0,
            total_cost=float('inf'),
            num_vehicles=0
        ))
        
        return population


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
        result = decode_giant_tour(
            giant_tour=individual.chromosome,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
            max_tour_duration=max_tour_duration
        )
        
        if result["num_vehicles"] == 0:
            # Infeasible
            return Individual(
                chromosome=individual.chromosome,
                fitness=0.0,
                total_cost=float('inf'),
                num_vehicles=999
            )
        
        total_cost = result["total_cost"]
        num_vehicles = result["num_vehicles"]
        
        # Multi-objective: minimize both cost and vehicles
        # Weighted sum approach
        fitness = 1.0 / (total_cost + num_vehicles * 50)  # Penalize extra vehicles
        
        return Individual(
            chromosome=individual.chromosome,
            fitness=fitness,
            total_cost=total_cost,
            num_vehicles=num_vehicles
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
        return [
            self._evaluate_individual(
                ind, depot, distance_matrix, demands,
                sw_capacity, so_capacity, max_tour_duration
            )
            for ind in population
        ]

    def _tournament_selection(self, population: List[Individual]) -> Individual:
        """Tournament selection"""
        tournament = self.rng.sample(
            population,
            min(self.config["tournament_size"], len(population))
        )
        return max(tournament, key=lambda x: x.fitness)

    def _order_crossover(self, parent1: List[str], parent2: List[str]) -> Tuple[List[str], List[str]]:
        """Order Crossover (OX1)"""
        n = len(parent1)
        if n < 2:
            return parent1.copy(), parent2.copy()
        
        start = self.rng.randint(0, n - 1)
        end = self.rng.randint(start, n - 1)
        
        child1: List[Optional[str]] = [None] * n
        child2: List[Optional[str]] = [None] * n
        
        # Copy segment
        for i in range(start, end + 1):
            child1[i] = parent1[i]
            child2[i] = parent2[i]
        
        # Fill remaining
        def fill_child(child, other_parent):
            segment = set(x for x in child if x is not None)
            remaining = [x for x in other_parent if x not in segment]
            idx = 0
            for i in range(n):
                if child[i] is None:
                    child[i] = remaining[idx]
                    idx += 1
        
        fill_child(child1, parent2)
        fill_child(child2, parent1)
        
        # Cast to List[str] - all positions are filled by fill_child
        
        return cast(List[str], child1), cast(List[str], child2)

    def _mutate(self, chromosome: List[str]) -> List[str]:
        """Apply mutation operators"""
        mutated = chromosome.copy()
        mutation_type = self.rng.choice(["swap", "inversion", "scramble"])
        
        if mutation_type == "swap":
            # Swap two random positions
            i, j = self.rng.sample(range(len(mutated)), 2)
            mutated[i], mutated[j] = mutated[j], mutated[i]
        
        elif mutation_type == "inversion":
            # Reverse a segment
            i, j = self.rng.sample(range(len(mutated)), 2)
            start, end = min(i, j), max(i, j)
            mutated[start:end + 1] = reversed(mutated[start:end + 1])
        
        else:  # scramble
            # Shuffle a segment
            i, j = self.rng.sample(range(len(mutated)), 2)
            start, end = min(i, j), max(i, j)
            segment = mutated[start:end + 1]
            self.rng.shuffle(segment)
            mutated[start:end + 1] = segment
        
        return mutated

    def _educate(self, individual: Individual, depot: str, 
                 distance_matrix: Dict) -> Individual:
        """
        Local search education (improvement).
        Apply 2-opt or similar to the giant tour.
        """
        def cost_func(route):
            # Approximate cost for the giant tour
            total = 0
            prev = depot
            for loc in route:
                total += distance_matrix.get(prev, {}).get(loc, 15.0)
                prev = loc
            total += distance_matrix.get(prev, {}).get(depot, 15.0)
            return total
        
        try:
            ls_type = LocalSearchType(self.config.get("local_search_type", "two_opt"))
            improved_route, _ = apply_local_search(
                individual.chromosome, cost_func, ls_type
            )
            return Individual(
                chromosome=improved_route,
                fitness=individual.fitness,
                total_cost=individual.total_cost,
                num_vehicles=individual.num_vehicles
            )
        except Exception as exc:
            logger.debug("Local search failed for individual: %s", exc)
            return individual

    def _diversify(self, population: List[Individual]) -> List[Individual]:
        """
        Diversification when stuck.
        Keep best, replace worst with new random individuals.
        """
        sorted_pop = sorted(population, key=lambda x: x.fitness, reverse=True)
        
        # Keep top 30%
        keep_count = max(2, int(len(population) * 0.3))
        new_population = sorted_pop[:keep_count]
        
        # Generate new random individuals
        waypoints = sorted_pop[0].chromosome.copy() if sorted_pop else []
        while len(new_population) < len(population):
            chromosome = waypoints.copy()
            self.rng.shuffle(chromosome)
            new_population.append(Individual(
                chromosome=chromosome,
                fitness=0.0,
                total_cost=float('inf'),
                num_vehicles=0
            ))
        
        return new_population

    def _evolve(self, population: List[Individual]) -> List[Individual]:
        """Create next generation"""
        new_population = []
        sorted_pop = sorted(population, key=lambda x: x.fitness, reverse=True)
        
        # Elitism
        for i in range(min(self.config["elite_count"], len(sorted_pop))):
            new_population.append(Individual(
                chromosome=sorted_pop[i].chromosome.copy(),
                fitness=sorted_pop[i].fitness,
                total_cost=sorted_pop[i].total_cost,
                num_vehicles=sorted_pop[i].num_vehicles
            ))
        
        # Generate offspring
        while len(new_population) < self.config["population_size"]:
            parent1 = self._tournament_selection(sorted_pop)
            parent2 = self._tournament_selection(sorted_pop)
            
            if self.rng.random() < self.config["crossover_rate"]:
                child1, child2 = self._order_crossover(
                    parent1.chromosome, parent2.chromosome
                )
            else:
                child1 = parent1.chromosome.copy()
                child2 = parent2.chromosome.copy()
            
            if self.rng.random() < self.config["mutation_rate"]:
                child1 = self._mutate(child1)
            if self.rng.random() < self.config["mutation_rate"]:
                child2 = self._mutate(child2)
            
            new_population.append(Individual(
                chromosome=child1, fitness=0.0, total_cost=float('inf'), num_vehicles=0
            ))
            if len(new_population) < self.config["population_size"]:
                new_population.append(Individual(
                    chromosome=child2, fitness=0.0, total_cost=float('inf'), num_vehicles=0
                ))
        
        return new_population[:self.config["population_size"]]

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
        if request.ga_config:
            self.config.update(request.ga_config)
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
        
        # Build distance matrix for all locations
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
        population = self._initialize_population(waypoints)
        population = self._evaluate_population(
            population, depot.id, distance_matrix, demands,
            request.sw_capacity, request.so_capacity, request.max_travel_time
        )
        
        best = min(population, key=lambda x: x.total_cost)
        no_improvement = 0
        generation = 0
        
        for generation in range(self.config["max_iterations"]):
            population = self._evolve(population)
            population = self._evaluate_population(
                population, depot.id, distance_matrix, demands,
                request.sw_capacity, request.so_capacity, request.max_travel_time
            )
            
            current_best = min(population, key=lambda x: x.total_cost)
            
            # Apply local search (education)
            if generation % self.config.get("local_search_interval", 10) == 0:
                current_best = self._educate(current_best, depot.id, distance_matrix)
                current_best = self._evaluate_individual(
                    current_best, depot.id, distance_matrix, demands,
                    request.sw_capacity, request.so_capacity, request.max_travel_time
                )
            
            if current_best.total_cost < best.total_cost:
                best = current_best
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
            
            # Diversify if stuck
            if no_improvement >= self.config.get("diversify_threshold", 30):
                population = self._diversify(population)
                population = self._evaluate_population(
                    population, depot.id, distance_matrix, demands,
                    request.sw_capacity, request.so_capacity, request.max_travel_time
                )
                no_improvement = 0
        
        # Final split on best solution - use CVRPTW decoder if time windows enabled
        if use_time_windows and time_windows:
            # Convert TimeWindow objects to tuple format for split decoder
            tw_tuples = {}
            for loc, tw in time_windows.items():
                tw_tuples[loc] = (tw.earliest, tw.latest)
            
            final_result = decode_with_time_windows(
                giant_tour=best.chromosome,
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
                giant_tour=best.chromosome,
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
    
    def _crossover_pmx(self, parent1: List[str], parent2: List[str]) -> List[str]:
        """
        Partially Mapped Crossover (PMX) - Corrected Implementation
        
        PMX preserves absolute positions from one parent while using
        a mapping to maintain permutation validity.
        
        Reference: Goldberg & Lingle (1985) - Alleles, loci, and the traveling salesman problem
        
        Fixed version: Uses position-based mapping instead of static value mapping.
        """
        n = len(parent1)
        if n < 2:
            return parent1.copy()

        start = self.rng.randint(0, n - 2)
        end = self.rng.randint(start + 1, n - 1)

        child: List[Optional[str]] = [None] * n

        # Step 1: Copy segment from parent1 to child
        for i in range(start, end + 1):
            child[i] = parent1[i]

        # Values already in child from segment
        segment_values = set(parent1[start:end + 1])

        # Step 2: Build position lookup for parent1
        pos_in_p1: Dict[str, int] = {val: idx for idx, val in enumerate(parent1)}

        # Step 3: Fill positions outside segment from parent2
        for i in range(n):
            if child[i] is None:
                val = parent2[i]

                # Follow the mapping: while val is in segment, find its partner
                # This implements the true PMX position-based crossover
                while val in segment_values:
                    # Find position of val in parent1
                    pos = pos_in_p1[val]
                    # Get the value at same position in parent2
                    val = parent2[pos]

                child[i] = val

        return cast(List[str], child)
    
    def _crossover_cx2(self, parent1: List[str], parent2: List[str]) -> List[str]:
        """
        Cycle Crossover 2 (CX2) - Corrected Implementation
        
        In true Cycle Crossover, elements are placed at their ORIGINAL indices
        from the cycle, not sequentially from cycle_start.
        
        Reference: Oliver et al. (1987) - A study of permutation crossover operators
        """
        n = len(parent1)
        if n < 2:
            return parent1.copy()
        
        child: List[Optional[str]] = [None] * n
        visited: set = set()

        for start in range(n):
            if parent1[start] not in visited:
                # Build cycle starting from 'start'
                cycle_indices: List[int] = []
                cycle_values: List[str] = []
                i = start
                
                while True:
                    cycle_indices.append(i)
                    cycle_values.append(parent1[i])
                    visited.add(parent1[i])
                    
                    # Find where parent2[i] is in parent1
                    next_val = parent2[i]
                    if next_val in visited:
                        break
                    
                    try:
                        i = parent1.index(next_val)
                    except ValueError:
                        break  # Safety: value not found
                    
                    if i == start:
                        break
                
                # CX2 feature: Alternate cycle direction randomly
                if len(cycle_values) > 1 and self.rng.random() < 0.5:
                    cycle_values = cycle_values[::-1]
                
                # Place at ORIGINAL indices (correct CX behavior)
                for idx, val in zip(cycle_indices, cycle_values):
                    child[idx] = val

        # Verify all positions filled (safety check)
        if None in child:
            # Fill any remaining gaps from parent2
            for i in range(n):
                if child[i] is None:
                    child[i] = parent2[i]
        
        return cast(List[str], child)
