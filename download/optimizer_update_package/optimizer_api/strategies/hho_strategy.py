"""
Harris Hawks Optimization Strategy for TSP/CVRP
Based on Heidari et al. (2019) - "Harris Hawks Optimization: Algorithm and Applications"

Implements:
- Escape Energy (E): Controls exploration vs exploitation
- Diverse Hunting Strategies: Soft besiege, Hard besiege, Rapid dives
- Adaptive search behavior based on prey's escape probability
- Discrete adaptation for permutation-based TSP using swap operations

Reference:
Heidari, A. A., Mirjalili, S., Faris, H., Aljarah, I., Mafarja, M., & Chen, H. (2019).
Harris hawks optimization: Algorithm and applications. Future Generation Computer Systems, 97, 849-872.
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
class Hawk:
    """Represents a hawk in the population"""
    position: List[str]  # Permutation of locations
    fitness: float = float('inf')
    escape_energy: float = 0.0  # E parameter


@dataclass
class SwapOperation:
    """Represents a swap operation for discrete HHO"""
    i: int
    j: int
    intensity: float  # How strong the swap tendency is


class HHOStrategy(BaseRoutingStrategy):
    """
    Harris Hawks Optimizer for Vehicle Routing Problem.
    
    Uses K-Means clustering for multi-vehicle routing,
    then HHO for TSP optimization within each cluster.
    
    Algorithm Phases:
    1. Global Exploration: Hawks search widely (E > 1 or E < -1)
    2. Exploitation Phase: Hawks surround prey (-1 ≤ E ≤ 1)
       - Soft Besiege (E ≥ 0.5): Gradual approach
       - Hard Besiege (E < 0.5): Aggressive attack
       - Rapid Dives: Sudden movements with levy flight
    
    Key Parameters:
    - E (Escape Energy): Decreases as iterations progress
    - r (Escape Probability): Random value for strategy selection
    - Jumping probability: Controls sudden movements
    """
    
    # Default HHO parameters
    DEFAULT_CONFIG = {
        "population_size": 30,              # Number of hawks
        "max_iterations": 100,              # Maximum iterations
        "initial_energy": 2.0,              # Initial max escape energy (E0)
        "energy_decay_rate": 1.0,           # How fast E decreases
        "levy_flight_beta": 1.5,            # Levy flight parameter
        "jump_probability": 0.5,            # Probability of rapid dives
        "local_search_intensity": 0.3,      # Local search frequency
        "max_no_improvement": 25,           # Early stopping threshold
        "adaptive_energy": True,            # Adaptive escape energy formula
        "seed": None
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)
        
    @property
    def name(self) -> str:
        return "hho"
    
    @property
    def display_name(self) -> str:
        return "Harris Hawks Optimizasyonu"
    
    @property
    def description(self) -> str:
        return "Şahin avlanma davranışı tabanlı meta-sezgisel. Kaçış enerjisi ile adaptif arama."
    
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
    
    def _initialize_population(self, waypoints: List[str]) -> List[Hawk]:
        """Initialize hawk population with random permutations"""
        population = []
        
        for _ in range(self.config["population_size"]):
            position = self._shuffle(waypoints)
            population.append(Hawk(position=position))
        
        return population
    
    def _evaluate_population(
        self,
        population: List[Hawk],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> None:
        """Evaluate fitness for all hawks in population"""
        for hawk in population:
            hawk.fitness = self._calculate_route_duration(
                hawk.position, depot, time_matrix, coordinates
            )
    
    def _calculate_escape_energy(self, iteration: int, max_iterations: int) -> float:
        """
        Calculate escape energy E.
        
        E = 2 * E0 * (1 - t/T)
        
        Where:
        - E0: Initial energy (random in [-1, 1])
        - t: Current iteration
        - T: Maximum iterations
        
        E decreases from ~2 to 0 as iterations progress.
        """
        # Random initial energy in range [0, 1]
        E0 = self.rng.random()
        
        # Linear decrease factor
        t_ratio = iteration / max_iterations
        
        if self.config["adaptive_energy"]:
            # Adaptive formula from original HHO paper
            E = 2 * E0 * (1 - t_ratio)
        else:
            # Simple linear decay
            E = self.config["initial_energy"] * (1 - t_ratio)
        
        return E
    
    def _levy_flight(self, x: float, beta: float = 1.5) -> float:
        """
        Levy flight function for random walk.
        Used in rapid dive strategies.
        """
        # Levi distribution numerator and denominator
        num = math.gamma(1 + beta) * math.sin(math.pi * beta / 2)
        den = math.gamma((1 + beta) / 2) * beta * math.pow(2, (beta - 1) / 2)
        sigma = math.pow(num / den, 1 / beta)
        
        u = self.rng.gauss(0, sigma)
        v = self.rng.gauss(0, 1)
        
        step = u / math.pow(abs(v), 1 / beta)
        
        return x * step
    
    def _get_difference_swaps(
        self,
        current: List[str],
        target: List[str],
        intensity: float
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
                            intensity=intensity * self.rng.random()
                        ))
                except ValueError:
                    pass
        
        return swaps
    
    def _apply_swaps(
        self,
        position: List[str],
        swaps: List[SwapOperation],
        probability: float = 0.5
    ) -> List[str]:
        """Apply swap operations probabilistically"""
        new_position = position.copy()
        n = len(new_position)
        
        for swap in swaps:
            if self.rng.random() < probability * swap.intensity:
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]
        
        return new_position
    
    def _soft_besiege(
        self,
        hawk: Hawk,
        rabbit: Hawk,
        E: float
    ) -> List[str]:
        """
        Soft besiege: Hawks encircle prey gradually.
        Used when escape energy is high (E ≥ 0.5).
        
        Jumps toward rabbit with moderation.
        """
        new_position = hawk.position.copy()
        n = len(new_position)
        
        # Calculate jump size based on energy
        jump_size = abs(E)
        
        # Get difference swaps toward rabbit
        swaps = self._get_difference_swaps(hawk.position, rabbit.position, jump_size)
        
        # Apply partial moves toward rabbit
        for swap in swaps:
            # Soft approach: only apply some swaps
            if self.rng.random() < 0.5 * jump_size:
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]
        
        return new_position
    
    def _hard_besiege(
        self,
        hawk: Hawk,
        rabbit: Hawk,
        E: float
    ) -> List[str]:
        """
        Hard besiege: Aggressive attack on prey.
        Used when escape energy is low (E < 0.5).
        
        Rapid, decisive moves toward rabbit.
        """
        new_position = hawk.position.copy()
        n = len(new_position)
        
        # Calculate attack intensity (inverse of energy)
        attack_intensity = 1 - abs(E)
        
        # Get difference swaps toward rabbit
        swaps = self._get_difference_swaps(hawk.position, rabbit.position, attack_intensity)
        
        # Apply aggressive moves toward rabbit
        for swap in swaps:
            # Hard approach: apply most swaps aggressively
            if self.rng.random() < attack_intensity:
                if 0 <= swap.i < n and 0 <= swap.j < n:
                    new_position[swap.i], new_position[swap.j] = \
                        new_position[swap.j], new_position[swap.i]
        
        return new_position
    
    def _soft_besiege_with_dives(
        self,
        hawk: Hawk,
        rabbit: Hawk,
        E: float,
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> List[str]:
        """
        Soft besiege with progressive rapid dives.
        Combines soft approach with levy flight jumps.
        """
        # Start with soft besiege
        new_position = self._soft_besiege(hawk, rabbit, E)
        
        # Try levy flight perturbation
        if self.rng.random() < self.config["jump_probability"]:
            # Apply levy flight based perturbation
            n = len(new_position)
            levy_steps = int(abs(self._levy_flight(1, self.config["levy_flight_beta"])))
            levy_steps = max(1, min(levy_steps, n // 2))
            
            for _ in range(levy_steps):
                i = self.rng.randint(0, n - 1)
                j = self.rng.randint(0, n - 1)
                if i != j:
                    new_position[i], new_position[j] = new_position[j], new_position[i]
        
        # Evaluate and keep better solution
        new_fitness = self._calculate_route_duration(new_position, depot, time_matrix, coordinates)
        
        if new_fitness < hawk.fitness:
            return new_position
        else:
            # Try alternative with different perturbation
            alt_position = self._soft_besiege(hawk, rabbit, E * 0.5)
            alt_fitness = self._calculate_route_duration(alt_position, depot, time_matrix, coordinates)
            
            if alt_fitness < hawk.fitness:
                return alt_position
        
        return hawk.position
    
    def _hard_besiege_with_dives(
        self,
        hawk: Hawk,
        rabbit: Hawk,
        avg_position: List[str],
        E: float,
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> List[str]:
        """
        Hard besiege with progressive rapid dives.
        Most aggressive strategy - combines attack with population information.
        """
        # Start with hard besiege toward rabbit
        new_position = self._hard_besiege(hawk, rabbit, E)
        
        # Also consider average position of population
        if self.rng.random() < 0.5:
            avg_swaps = self._get_difference_swaps(new_position, avg_position, 0.3)
            new_position = self._apply_swaps(new_position, avg_swaps, 0.3)
        
        # Apply aggressive levy flight
        if self.rng.random() < self.config["jump_probability"] * 0.5:
            n = len(new_position)
            levy_steps = int(abs(self._levy_flight(2, self.config["levy_flight_beta"])))
            levy_steps = max(1, min(levy_steps, n // 3))
            
            for _ in range(levy_steps):
                i = self.rng.randint(0, n - 1)
                j = self.rng.randint(0, n - 1)
                if i != j:
                    new_position[i], new_position[j] = new_position[j], new_position[i]
        
        # Evaluate
        new_fitness = self._calculate_route_duration(new_position, depot, time_matrix, coordinates)
        
        if new_fitness < hawk.fitness:
            return new_position
        
        return hawk.position
    
    def _exploration_phase(
        self,
        hawk: Hawk,
        rabbit: Hawk,
        E: float
    ) -> List[str]:
        """
        Global exploration phase.
        Hawks search widely when |E| >= 1.
        """
        new_position = hawk.position.copy()
        n = len(new_position)
        
        if n < 2:
            return new_position
        
        # Random exploration moves
        q = self.rng.random()
        
        if q < 0.5:
            # Random position based on rabbit with perturbation
            perturbation = int(abs(E))
            for _ in range(max(1, perturbation)):
                i = self.rng.randint(0, n - 1)
                j = self.rng.randint(0, n - 1)
                if i != j:
                    new_position[i], new_position[j] = new_position[j], new_position[i]
        else:
            # Random swap based on another hawk's position (diversity)
            num_swaps = self.rng.randint(1, max(1, n // 4))
            for _ in range(num_swaps):
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
    
    def _calculate_average_position(self, population: List[Hawk]) -> List[str]:
        """
        Calculate 'average' position for hard besiege with dives.
        In discrete space, we take the best position from a random sample.
        """
        # Sample a subset and return the best
        sample_size = min(5, len(population))
        sample = self.rng.sample(population, sample_size)
        best_in_sample = min(sample, key=lambda h: h.fitness)
        return best_in_sample.position.copy()
    
    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> Tuple[List[str], float]:
        """
        Solve TSP for a single vehicle using Harris Hawks Optimization.
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
        
        # Find rabbit (prey = best solution)
        rabbit = min(population, key=lambda h: h.fitness)
        
        # Track best solution
        best_position = rabbit.position.copy()
        best_fitness = rabbit.fitness
        no_improvement = 0
        
        # Main HHO loop
        for iteration in range(self.config["max_iterations"]):
            # Calculate escape energy
            E = self._calculate_escape_energy(iteration, self.config["max_iterations"])
            
            # Calculate average position for hard besiege
            avg_position = self._calculate_average_position(population)
            
            improved = False
            
            for hawk in population:
                # Skip if this is the rabbit (best solution)
                if hawk.position == rabbit.position:
                    continue
                
                # Generate random escape probability
                r = self.rng.random()
                
                # Select strategy based on E and r
                if abs(E) >= 1:
                    # EXPLORATION PHASE
                    new_position = self._exploration_phase(hawk, rabbit, E)
                else:
                    # EXPLOITATION PHASE
                    if r >= 0.5:
                        # Soft besiege
                        if abs(E) >= 0.5:
                            # Soft besiege with progressive rapid dives
                            new_position = self._soft_besiege_with_dives(
                                hawk, rabbit, E, depot, time_matrix, coordinates
                            )
                        else:
                            # Hard besiege with progressive rapid dives
                            new_position = self._hard_besiege_with_dives(
                                hawk, rabbit, avg_position, E, 
                                depot, time_matrix, coordinates
                            )
                    else:
                        # Hard besiege
                        if abs(E) >= 0.5:
                            # Soft besiege
                            new_position = self._soft_besiege(hawk, rabbit, E)
                        else:
                            # Hard besiege
                            new_position = self._hard_besiege(hawk, rabbit, E)
                
                # Apply local search occasionally
                if self.rng.random() < self.config["local_search_intensity"]:
                    new_position, _ = self._local_search(
                        new_position, depot, time_matrix, coordinates, max_attempts=3
                    )
                
                # Update hawk
                hawk.position = new_position
                hawk.fitness = self._calculate_route_duration(
                    hawk.position, depot, time_matrix, coordinates
                )
                hawk.escape_energy = E
            
            # Re-evaluate population
            self._evaluate_population(population, depot, time_matrix, coordinates)
            
            # Update rabbit (best solution found so far)
            current_rabbit = min(population, key=lambda h: h.fitness)
            
            if current_rabbit.fitness < rabbit.fitness:
                rabbit = current_rabbit
                # Make a copy to prevent reference issues
                rabbit = Hawk(
                    position=current_rabbit.position.copy(),
                    fitness=current_rabbit.fitness
                )
            
            # Update global best
            if rabbit.fitness < best_fitness:
                best_position = rabbit.position.copy()
                best_fitness = rabbit.fitness
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
        if hasattr(request, 'hho_config') and request.hho_config:
            self.config.update(request.hho_config)
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
                vehicle_id=f"Araç {assignment['vehicle_index']} (HHO)",
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
