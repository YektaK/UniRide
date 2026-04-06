"""
Grey Wolf Optimizer Strategy for TSP/CVRP
Based on Mirjalili et al. (2014) - "Grey Wolf Optimizer"

Implements:
- Social hierarchy: Alpha (α), Beta (β), Delta (δ), Omega (ω)
- Hunting behavior: Encircling prey, hunting, attacking prey
- Discrete adaptation for permutation-based TSP using swap operations
- Exploration vs exploitation balance through adaptive parameters

Reference:
Mirjalili, S., Mirjalili, S. M., & Lewis, A. (2014). 
Grey wolf optimizer. Advances in engineering software, 69, 46-61.
"""

import random
import time
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.clustering import VehicleCalculator


@dataclass
class Wolf:
    """Represents a grey wolf in the population"""
    position: List[str]  # Permutation of locations
    fitness: float = float('inf')


@dataclass
class SwapOperation:
    """Represents a swap operation for discrete GWO"""
    i: int
    j: int
    intensity: float  # How strong the swap tendency is


class GWOStrategy(BaseRoutingStrategy):
    """
    Grey Wolf Optimizer for Vehicle Routing Problem.
    
    Uses K-Means clustering for multi-vehicle routing,
    then GWO for TSP optimization within each cluster.
    
    Algorithm Phases:
    1. Social Hierarchy: Sort population by fitness (Alpha > Beta > Delta > Omega)
    2. Encircling Prey: Move toward better solutions
    3. Hunting: Guided by Alpha, Beta, Delta
    4. Exploitation: Local search around best solutions
    5. Exploration: Random movements to escape local optima
    """
    
    # Default GWO parameters
    DEFAULT_CONFIG = {
        "population_size": 30,          # Number of wolves
        "max_iterations": 100,          # Maximum iterations
        "initial_a": 2.0,               # Initial value for 'a' (decreases linearly)
        "exploration_rate": 0.5,        # Probability of exploration moves
        "local_search_probability": 0.3, # Probability of local search
        "max_no_improvement": 25,       # Early stopping threshold
        "elite_preservation": True,     # Keep best solutions
        "seed": None
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)
        
    @property
    def name(self) -> str:
        return "gwo"
    
    @property
    def display_name(self) -> str:
        return "Gri Kurt Optimizasyonu"
    
    @property
    def description(self) -> str:
        return "Sosyal hiyerarşi tabanlı meta-sezgisel. Keşif-sömürü dengesi güçlü."
    
    def _get_duration(self, from_loc: str, to_loc: str, 
                      time_matrix: Dict, coordinates: Dict) -> float:
        """Get travel duration between two locations"""
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
        """Calculate total route duration for a position (permutation)"""
        if not position:
            return 0.0
        
        total = self._get_duration(depot, position[0], time_matrix, coordinates)
        
        for i in range(len(position) - 1):
            total += self._get_duration(
                position[i], position[i + 1], time_matrix, coordinates
            )
        
        total += self._get_duration(position[-1], depot, time_matrix, coordinates)
        return total
    
    def _shuffle(self, items: List) -> List:
        """Fisher-Yates shuffle using internal RNG"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result
    
    def _initialize_population(self, waypoints: List[str]) -> List[Wolf]:
        """Initialize wolf population with random permutations"""
        population = []
        
        for _ in range(self.config["population_size"]):
            position = self._shuffle(waypoints)
            population.append(Wolf(position=position))
        
        return population
    
    def _evaluate_population(
        self,
        population: List[Wolf],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> None:
        """Evaluate fitness for all wolves in population"""
        for wolf in population:
            wolf.fitness = self._calculate_route_duration(
                wolf.position, depot, time_matrix, coordinates
            )
    
    def _sort_hierarchy(self, population: List[Wolf]) -> Tuple[Wolf, Wolf, Wolf]:
        """
        Sort population and return Alpha, Beta, Delta.
        Alpha = best, Beta = second best, Delta = third best
        """
        sorted_pop = sorted(population, key=lambda w: w.fitness)
        return sorted_pop[0], sorted_pop[1], sorted_pop[2]
    
    def _calculate_distance_vectors(
        self,
        wolf: Wolf,
        leader: Wolf,
        a: float
    ) -> List[SwapOperation]:
        """
        Calculate distance vector between wolf and leader (Alpha/Beta/Delta).
        In discrete space, this becomes a series of swap operations.
        
        The parameter 'a' controls exploration (high a) vs exploitation (low a).
        """
        swaps = []
        n = len(wolf.position)
        
        # Calculate C = 2 * r2 (random weight)
        C = 2 * self.rng.random()
        
        # Calculate A = 2a * r1 - a (controls movement intensity)
        A = 2 * a * self.rng.random() - a
        
        # Calculate absolute distance coefficient
        distance_coef = abs(C * A)
        
        for i in range(n):
            if wolf.position[i] != leader.position[i]:
                # Find where the leader's element at position i is in wolf
                try:
                    j = wolf.position.index(leader.position[i])
                    if j != i:
                        # Calculate swap intensity based on A
                        intensity = distance_coef * self.rng.random()
                        swaps.append(SwapOperation(i=i, j=j, intensity=intensity))
                except ValueError:
                    pass
        
        return swaps
    
    def _apply_swaps(
        self,
        position: List[str],
        swaps: List[SwapOperation],
        a: float
    ) -> List[str]:
        """
        Apply swap operations to position.
        The parameter 'a' controls probability of applying swaps.
        """
        new_position = position.copy()
        n = len(new_position)
        
        for swap in swaps:
            # Higher intensity + lower a = higher probability of swap
            prob = swap.intensity * (1 - a / 2)  # Adaptive probability
            
            if self.rng.random() < prob:
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]
        
        return new_position
    
    def _update_position(
        self,
        wolf: Wolf,
        alpha: Wolf,
        beta: Wolf,
        delta: Wolf,
        a: float
    ) -> List[str]:
        """
        Update wolf position based on Alpha, Beta, Delta guidance.
        
        In continuous GWO:
        X(t+1) = (X1 + X2 + X3) / 3
        
        In discrete TSP-GWO:
        We combine swap vectors from all three leaders
        """
        new_position = wolf.position.copy()
        
        # Get distance vectors to each leader
        alpha_swaps = self._calculate_distance_vectors(wolf, alpha, a)
        beta_swaps = self._calculate_distance_vectors(wolf, beta, a)
        delta_swaps = self._calculate_distance_vectors(wolf, delta, a)
        
        # Apply swaps from each leader with weights
        # Alpha has most influence, then Beta, then Delta
        alpha_weight = 0.5  # 50% Alpha influence
        beta_weight = 0.3   # 30% Beta influence
        delta_weight = 0.2  # 20% Delta influence
        
        # Apply Alpha swaps
        for swap in alpha_swaps:
            if self.rng.random() < alpha_weight:
                n = len(new_position)
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]
        
        # Apply Beta swaps
        for swap in beta_swaps:
            if self.rng.random() < beta_weight:
                n = len(new_position)
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]
        
        # Apply Delta swaps
        for swap in delta_swaps:
            if self.rng.random() < delta_weight:
                n = len(new_position)
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]
        
        return new_position
    
    def _exploration_move(self, position: List[str], a: float) -> List[str]:
        """
        Random exploration move for diversity.
        More exploration when 'a' is high (early iterations).
        """
        new_position = position.copy()
        n = len(new_position)
        
        if n < 2:
            return new_position
        
        # Number of random swaps based on 'a'
        num_swaps = max(1, int(a * 2))
        
        for _ in range(num_swaps):
            if self.rng.random() < self.config["exploration_rate"]:
                i = self.rng.randint(0, n - 1)
                j = self.rng.randint(0, n - 1)
                if i != j:
                    new_position[i], new_position[j] = new_position[j], new_position[i]
        
        return new_position
    
    def _local_search(
        self,
        position: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        max_attempts: int = 10
    ) -> Tuple[List[str], float]:
        """
        2-opt local search for exploitation.
        Improves the solution by reversing segments.
        """
        best_position = position.copy()
        best_fitness = self._calculate_route_duration(
            best_position, depot, time_matrix, coordinates
        )
        
        improved = True
        attempts = 0
        
        while improved and attempts < max_attempts:
            improved = False
            attempts += 1
            n = len(best_position)
            
            for i in range(n - 1):
                for j in range(i + 2, n):
                    # Try reversing segment [i+1:j]
                    new_position = (
                        best_position[:i + 1] +
                        best_position[i + 1:j + 1][::-1] +
                        best_position[j + 1:]
                    )
                    
                    new_fitness = self._calculate_route_duration(
                        new_position, depot, time_matrix, coordinates
                    )
                    
                    if new_fitness < best_fitness:
                        best_position = new_position
                        best_fitness = new_fitness
                        improved = True
        
        return best_position, best_fitness
    
    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> Tuple[List[str], float]:
        """
        Solve TSP for a single vehicle using Grey Wolf Optimizer.
        """
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
        
        # Initialize population
        population = self._initialize_population(waypoints)
        
        # Evaluate initial population
        self._evaluate_population(population, depot, time_matrix, coordinates)
        
        # Get initial hierarchy
        alpha, beta, delta = self._sort_hierarchy(population)
        
        # Track best solution
        best_position = alpha.position.copy()
        best_fitness = alpha.fitness
        no_improvement = 0
        
        # Main GWO loop
        for iteration in range(self.config["max_iterations"]):
            # Calculate 'a' - linearly decreasing from 2 to 0
            a = self.config["initial_a"] * (
                1 - iteration / self.config["max_iterations"]
            )
            
            improved = False
            
            # Update each wolf's position
            for wolf in population:
                # Skip Alpha, Beta, Delta (elite preservation)
                if self.config["elite_preservation"]:
                    if wolf.position == alpha.position or \
                       wolf.position == beta.position or \
                       wolf.position == delta.position:
                        continue
                
                # Update position based on leaders
                new_position = self._update_position(wolf, alpha, beta, delta, a)
                
                # Apply exploration move (more in early iterations)
                if a > 1.0:  # High 'a' means early iterations
                    new_position = self._exploration_move(new_position, a)
                
                # Apply local search with some probability (more in late iterations)
                if self.rng.random() < self.config["local_search_probability"] * (1 - a/2):
                    new_position, _ = self._local_search(
                        new_position, depot, time_matrix, coordinates, max_attempts=5
                    )
                
                # Update wolf
                wolf.position = new_position
                wolf.fitness = self._calculate_route_duration(
                    wolf.position, depot, time_matrix, coordinates
                )
            
            # Re-evaluate and update hierarchy
            self._evaluate_population(population, depot, time_matrix, coordinates)
            alpha, beta, delta = self._sort_hierarchy(population)
            
            # Update best solution
            if alpha.fitness < best_fitness:
                best_position = alpha.position.copy()
                best_fitness = alpha.fitness
                improved = True
            
            # Early stopping check
            if improved:
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
        
        # Final local search on best solution
        best_position, best_fitness = self._local_search(
            best_position, depot, time_matrix, coordinates, max_attempts=20
        )
        
        return best_position, best_fitness
    
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
        if hasattr(request, 'gwo_config') and request.gwo_config:
            self.config.update(request.gwo_config)
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
        
        # Calculate vehicle assignments using VehicleCalculator
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
                vehicle_id=f"Araç {assignment['vehicle_index']} (GWO)",
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
