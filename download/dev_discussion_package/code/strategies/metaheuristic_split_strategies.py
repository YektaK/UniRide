"""
Metaheuristic Split Strategies for Pipeline B (Route-First, Cluster-Second)
Combines metaheuristic algorithms with Split Decoder for CVRPTW

Available Strategies:
- PSO-Split: Particle Swarm Optimization + Split Decoder
- HHO-Split: Harris Hawks Optimization + Split Decoder
- GWO-Split: Grey Wolf Optimizer + Split Decoder

All strategies follow the same pattern:
1. Optimize giant tour (permutation of all customers)
2. Split into optimal vehicle routes using Split Decoder

Reference:
Prins, C. (2004). A simple and effective evolutionary algorithm for VRP.
"""

import random
import time
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.split_decoder import SplitDecoder, decode_giant_tour
from utils.local_search import LocalSearchType, apply_local_search


@dataclass
class Solution:
    """Represents a solution (giant tour)"""
    tour: List[str]  # Permutation of all customer locations
    fitness: float  # 1 / total_cost
    total_cost: float  # Total routing cost after split
    num_vehicles: int  # Number of vehicles after split


class BaseSplitStrategy(BaseRoutingStrategy):
    """
    Base class for Pipeline B strategies.
    
    Implements the common functionality for route-first, cluster-second approach:
    1. Build time matrix and coordinates
    2. Optimize giant tour using metaheuristic
    3. Split giant tour using Split Decoder
    4. Build response routes
    """
    
    # Default config - override in subclasses
    DEFAULT_CONFIG = {
        "population_size": 30,
        "max_iterations": 100,
        "max_no_improvement": 25,
        "seed": None,
        "local_search_type": "two_opt",
        "local_search_interval": 10,  # Apply local search every N iterations
        "diversify_threshold": 30,    # Diversify after N iterations without improvement
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    def _optimize_giant_tour(
        self,
        waypoints: List[str],
        depot: str,
        distance_matrix: Dict,
        demands: Dict,
        sw_capacity: int,
        so_capacity: int,
        max_tour_duration: float
    ) -> Solution:
        """Optimize giant tour using specific metaheuristic"""
        pass
    
    def _get_duration(self, from_loc: str, to_loc: str,
                      time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between two locations"""
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]
        
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)
        
        return 15.0
    
    def _build_distance_matrix(self, location_ids: List[str],
                                time_matrix: Dict, coordinates: Dict) -> Dict[str, Dict[str, float]]:
        """Build complete distance matrix"""
        matrix = {}
        for loc1 in location_ids:
            matrix[loc1] = {}
            for loc2 in location_ids:
                if loc1 == loc2:
                    matrix[loc1][loc2] = 0.0
                else:
                    matrix[loc1][loc2] = self._get_duration(loc1, loc2, time_matrix, coordinates)
        return matrix
    
    def _shuffle(self, items: List) -> List:
        """Shuffle list using internal RNG"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result
    
    def _evaluate_solution(
        self,
        tour: List[str],
        depot: str,
        distance_matrix: Dict,
        demands: Dict,
        sw_capacity: int,
        so_capacity: int,
        max_tour_duration: float
    ) -> Solution:
        """Evaluate a giant tour using Split Decoder"""
        result = decode_giant_tour(
            giant_tour=tour,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
            max_tour_duration=max_tour_duration
        )
        
        if result["num_vehicles"] == 0:
            return Solution(
                tour=tour,
                fitness=0.0,
                total_cost=float('inf'),
                num_vehicles=999
            )
        
        total_cost = result["total_cost"]
        num_vehicles = result["num_vehicles"]
        
        # Multi-objective: minimize both cost and vehicles
        fitness = 1.0 / (total_cost + num_vehicles * 50)
        
        return Solution(
            tour=tour,
            fitness=fitness,
            total_cost=total_cost,
            num_vehicles=num_vehicles
        )
    
    def _educate(self, solution: Solution, depot: str,
                 distance_matrix: Dict) -> Solution:
        """Local search education"""
        def cost_func(route):
            total = 0
            prev = depot
            for loc in route:
                total += distance_matrix.get(prev, {}).get(loc, 15.0)
                prev = loc
            total += distance_matrix.get(prev, {}).get(depot, 15.0)
            return total
        
        try:
            ls_type = LocalSearchType(self.config.get("local_search_type", "two_opt"))
            improved_tour, _ = apply_local_search(solution.tour, cost_func, ls_type)
            return Solution(
                tour=improved_tour,
                fitness=solution.fitness,
                total_cost=solution.total_cost,
                num_vehicles=solution.num_vehicles
            )
        except:
            return solution
    
    def _diversify(self, population: List[Solution]) -> List[Solution]:
        """Diversification when stuck"""
        sorted_pop = sorted(population, key=lambda x: x.fitness, reverse=True)
        keep_count = max(2, int(len(population) * 0.3))
        new_population = sorted_pop[:keep_count]
        
        waypoints = sorted_pop[0].tour.copy() if sorted_pop else []
        while len(new_population) < len(population):
            tour = waypoints.copy()
            self.rng.shuffle(tour)
            new_population.append(Solution(
                tour=tour,
                fitness=0.0,
                total_cost=float('inf'),
                num_vehicles=0
            ))
        
        return new_population
    
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
        
        # Optimize giant tour using specific metaheuristic
        best = self._optimize_giant_tour(
            waypoints, depot.id, distance_matrix, demands,
            request.sw_capacity, request.so_capacity, request.max_travel_time
        )
        
        # Final split on best solution
        final_result = decode_giant_tour(
            giant_tour=best.tour,
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
                vehicle_id=f"Araç {route_idx + 1} ({self.name.upper()})",
                route_details=route_steps,
                total_duration_minutes=round(total_duration, 2),
                total_distance_km=0.0,
                sw_count=sw_count,
                so_count=so_count,
                student_ids=route_student_ids
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


# =============================================================================
# PSO-SPLIT STRATEGY
# =============================================================================

@dataclass
class Particle:
    """Particle for PSO"""
    position: List[str]
    velocity: List[Tuple[int, int, float]]  # (i, j, probability)
    personal_best: List[str]
    personal_best_cost: float
    current_cost: float


class PSOSplitStrategy(BaseSplitStrategy):
    """
    PSO + Split Decoder for CVRPTW.
    
    Uses PSO for giant tour optimization:
    - Position: permutation of customers
    - Velocity: sequence of swap operations
    - Personal best + Global best guide
    """
    
    DEFAULT_CONFIG = {
        "population_size": 30,
        "max_iterations": 100,
        "inertia_weight": 0.729,
        "cognitive_weight": 1.49445,
        "social_weight": 1.49445,
        "velocity_clamp": 0.9,
        "max_no_improvement": 25,
        "seed": None,
        "local_search_type": "two_opt",
    }
    
    @property
    def name(self) -> str:
        return "pso_split"
    
    @property
    def display_name(self) -> str:
        return "PSO-Split Hybrid"
    
    @property
    def description(self) -> str:
        return "Route-first: PSO giant tour + Optimal Split decoder"
    
    def _generate_random_velocity(self, n: int) -> List[Tuple[int, int, float]]:
        """Generate random velocity"""
        velocity = []
        num_swaps = min(self.rng.randint(1, max(1, n // 2)), 5)
        for _ in range(num_swaps):
            velocity.append((
                self.rng.randint(0, n - 1),
                self.rng.randint(0, n - 1),
                self.rng.random() * 0.5
            ))
        return velocity
    
    def _get_difference_swaps(self, current: List[str], target: List[str],
                               weight: float) -> List[Tuple[int, int, float]]:
        """Get swaps to transform current toward target"""
        swaps = []
        n = len(current)
        for i in range(n):
            if current[i] != target[i]:
                try:
                    j = current.index(target[i])
                    swaps.append((i, j, weight * self.rng.random()))
                except ValueError:
                    pass
        return swaps
    
    def _apply_velocity(self, position: List[str],
                        velocity: List[Tuple[int, int, float]]) -> List[str]:
        """Apply velocity swaps probabilistically"""
        new_position = position.copy()
        n = len(new_position)
        for i, j, prob in velocity:
            if self.rng.random() < prob:
                if 0 <= i < n and 0 <= j < n:
                    new_position[i], new_position[j] = new_position[j], new_position[i]
        return new_position
    
    def _update_velocity(self, current_velocity: List[Tuple[int, int, float]],
                         current_position: List[str],
                         personal_best: List[str],
                         global_best: List[str]) -> List[Tuple[int, int, float]]:
        """Update velocity using PSO equation"""
        new_velocity = []
        
        # Inertia
        for i, j, prob in current_velocity:
            adjusted = prob * self.config["inertia_weight"]
            if adjusted > 0.1:
                new_velocity.append((i, j, min(adjusted, self.config["velocity_clamp"])))
        
        # Cognitive
        pbest_swaps = self._get_difference_swaps(
            current_position, personal_best, self.config["cognitive_weight"]
        )
        new_velocity.extend(pbest_swaps)
        
        # Social
        gbest_swaps = self._get_difference_swaps(
            current_position, global_best, self.config["social_weight"]
        )
        new_velocity.extend(gbest_swaps)
        
        # Limit size
        max_vel = int(self.config["velocity_clamp"] * len(current_position) * 2)
        return new_velocity[:max_vel]
    
    def _optimize_giant_tour(self, waypoints, depot, distance_matrix, demands,
                             sw_capacity, so_capacity, max_tour_duration) -> Solution:
        """PSO optimization for giant tour"""
        if not waypoints:
            return Solution(tour=[], fitness=0, total_cost=0, num_vehicles=0)
        
        n = len(waypoints)
        
        # Initialize swarm
        swarm = []
        for _ in range(self.config["population_size"]):
            position = self._shuffle(waypoints)
            velocity = self._generate_random_velocity(n)
            swarm.append(Particle(
                position=position,
                velocity=velocity,
                personal_best=position.copy(),
                personal_best_cost=float('inf'),
                current_cost=float('inf')
            ))
        
        # Evaluate initial
        for particle in swarm:
            sol = self._evaluate_solution(
                particle.position, depot, distance_matrix, demands,
                sw_capacity, so_capacity, max_tour_duration
            )
            particle.current_cost = sol.total_cost
            particle.personal_best_cost = sol.total_cost
        
        global_best = self._shuffle(waypoints)
        global_best_cost = float('inf')
        for particle in swarm:
            if particle.personal_best_cost < global_best_cost:
                global_best = particle.personal_best.copy()
                global_best_cost = particle.personal_best_cost
        
        no_improvement = 0
        
        for iteration in range(self.config["max_iterations"]):
            improved = False
            
            for particle in swarm:
                new_velocity = self._update_velocity(
                    particle.velocity, particle.position,
                    particle.personal_best, global_best
                )
                new_position = self._apply_velocity(particle.position, new_velocity)
                
                sol = self._evaluate_solution(
                    new_position, depot, distance_matrix, demands,
                    sw_capacity, so_capacity, max_tour_duration
                )
                
                particle.position = new_position
                particle.velocity = new_velocity
                particle.current_cost = sol.total_cost
                
                if sol.total_cost < particle.personal_best_cost:
                    particle.personal_best = new_position.copy()
                    particle.personal_best_cost = sol.total_cost
                    
                    if sol.total_cost < global_best_cost:
                        global_best = new_position.copy()
                        global_best_cost = sol.total_cost
                        improved = True
            
            if improved:
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
        
        return Solution(
            tour=global_best,
            fitness=1.0 / global_best_cost if global_best_cost > 0 else 0,
            total_cost=global_best_cost,
            num_vehicles=0
        )


# =============================================================================
# HHO-SPLIT STRATEGY
# =============================================================================

@dataclass
class Hawk:
    """Hawk for HHO"""
    position: List[str]
    cost: float


class HHOSplitStrategy(BaseSplitStrategy):
    """
    Harris Hawks Optimization + Split Decoder for CVRPTW.
    
    Uses HHO for giant tour optimization:
    - Exploration: random perching
    - Exploitation: soft/hard besiege with progressive rapid dives
    """
    
    DEFAULT_CONFIG = {
        "population_size": 30,
        "max_iterations": 100,
        "initial_energy": 1.0,
        "jump_probability": 0.5,
        "max_no_improvement": 20,
        "seed": None,
        "local_search_type": "two_opt",
    }
    
    @property
    def name(self) -> str:
        return "hho_split"
    
    @property
    def display_name(self) -> str:
        return "HHO-Split Hybrid"
    
    @property
    def description(self) -> str:
        return "Route-first: HHO giant tour + Optimal Split decoder"
    
    def _levy_flight(self, position: List[str], scale: float = 0.5) -> List[str]:
        """Lévy flight mutation"""
        new_position = position.copy()
        n = len(new_position)
        
        beta = 1.5
        sigma = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2) /
                 (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
        
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
        """Get swaps toward target"""
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
        """Apply swap operations"""
        new_position = position.copy()
        for i, j in swaps:
            if 0 <= i < len(new_position) and 0 <= j < len(new_position):
                new_position[i], new_position[j] = new_position[j], new_position[i]
        return new_position
    
    def _optimize_giant_tour(self, waypoints, depot, distance_matrix, demands,
                             sw_capacity, so_capacity, max_tour_duration) -> Solution:
        """HHO optimization for giant tour"""
        if not waypoints:
            return Solution(tour=[], fitness=0, total_cost=0, num_vehicles=0)
        
        # Initialize hawks
        hawks = []
        for _ in range(self.config["population_size"]):
            position = self._shuffle(waypoints)
            hawks.append(Hawk(position=position, cost=float('inf')))
        
        # Evaluate initial
        for hawk in hawks:
            sol = self._evaluate_solution(
                hawk.position, depot, distance_matrix, demands,
                sw_capacity, so_capacity, max_tour_duration
            )
            hawk.cost = sol.total_cost
        
        # Find prey (best)
        prey = min(hawks, key=lambda h: h.cost)
        prey_position = prey.position.copy()
        prey_cost = prey.cost
        
        no_improvement = 0
        
        for iteration in range(self.config["max_iterations"]):
            E0 = 2 * self.rng.random() - 1
            E = 2 * E0 * (1 - iteration / self.config["max_iterations"])
            
            improved = False
            
            for hawk in hawks:
                r = self.rng.random()
                
                # Exploration
                if abs(E) >= 1:
                    if self.rng.random() < 0.5:
                        intensity = self.rng.random()
                        swaps = self._get_difference_swaps(hawk.position, prey_position, intensity)
                        new_position = self._apply_swaps(hawk.position, swaps)
                    else:
                        new_position = self._levy_flight(hawk.position)
                
                # Exploitation
                else:
                    if r < self.config["jump_probability"]:
                        if abs(E) >= 0.5:
                            intensity = abs(E) * 2 * (1 - self.rng.random())
                            swaps = self._get_difference_swaps(hawk.position, prey_position, intensity)
                            new_position = self._apply_swaps(hawk.position, swaps)
                        else:
                            intensity = abs(E)
                            swaps = self._get_difference_swaps(hawk.position, prey_position, intensity)
                            new_position = self._apply_swaps(hawk.position, swaps)
                    else:
                        intensity = abs(E) * self.rng.random()
                        swaps = self._get_difference_swaps(hawk.position, prey_position, intensity)
                        new_position = self._apply_swaps(hawk.position, swaps)
                        new_position = self._levy_flight(new_position, scale=0.3)
                
                # Evaluate
                sol = self._evaluate_solution(
                    new_position, depot, distance_matrix, demands,
                    sw_capacity, so_capacity, max_tour_duration
                )
                
                if sol.total_cost < hawk.cost:
                    hawk.position = new_position
                    hawk.cost = sol.total_cost
                
                if hawk.cost < prey_cost:
                    prey_position = hawk.position.copy()
                    prey_cost = hawk.cost
                    improved = True
            
            if improved:
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
        
        return Solution(
            tour=prey_position,
            fitness=1.0 / prey_cost if prey_cost > 0 else 0,
            total_cost=prey_cost,
            num_vehicles=0
        )


# =============================================================================
# GWO-SPLIT STRATEGY
# =============================================================================

@dataclass
class Wolf:
    """Wolf for GWO"""
    position: List[str]
    cost: float


class GWOSplitStrategy(BaseSplitStrategy):
    """
    Grey Wolf Optimizer + Split Decoder for CVRPTW.
    
    Uses GWO for giant tour optimization:
    - Alpha, Beta, Delta hierarchy
    - Encircling prey mechanism
    - Exploration/Exploitation balance
    """
    
    DEFAULT_CONFIG = {
        "population_size": 30,
        "max_iterations": 100,
        "initial_a": 2.0,
        "exploration_rate": 0.5,
        "max_no_improvement": 20,
        "seed": None,
        "local_search_type": "two_opt",
    }
    
    @property
    def name(self) -> str:
        return "gwo_split"
    
    @property
    def display_name(self) -> str:
        return "GWO-Split Hybrid"
    
    @property
    def description(self) -> str:
        return "Route-first: GWO giant tour + Optimal Split decoder"
    
    def _get_difference_swaps(self, leader: List[str], wolf: List[str],
                               a: float) -> List[Tuple[int, int]]:
        """Calculate swaps toward leader"""
        swaps = []
        n = len(wolf)
        for i in range(n):
            if wolf[i] != leader[i]:
                try:
                    j = wolf.index(leader[i])
                    if self.rng.random() < a / 2:
                        swaps.append((i, j))
                except ValueError:
                    pass
        return swaps
    
    def _apply_swaps(self, position: List[str], swaps: List[Tuple[int, int]]) -> List[str]:
        """Apply swap operations"""
        new_position = position.copy()
        for i, j in swaps:
            if 0 <= i < len(new_position) and 0 <= j < len(new_position):
                new_position[i], new_position[j] = new_position[j], new_position[i]
        return new_position
    
    def _update_position(self, wolf: Wolf, alpha: Wolf, beta: Wolf, delta: Wolf, a: float) -> List[str]:
        """Update wolf position based on leaders"""
        alpha_swaps = self._get_difference_swaps(alpha.position, wolf.position, a)
        beta_swaps = self._get_difference_swaps(beta.position, wolf.position, a)
        delta_swaps = self._get_difference_swaps(delta.position, wolf.position, a)
        
        all_swaps = []
        
        for swap in alpha_swaps:
            if self.rng.random() < 0.7:
                all_swaps.append(swap)
        
        for swap in beta_swaps:
            if self.rng.random() < 0.5:
                all_swaps.append(swap)
        
        for swap in delta_swaps:
            if self.rng.random() < 0.3:
                all_swaps.append(swap)
        
        if all_swaps:
            num_swaps = min(len(all_swaps), max(1, int(len(all_swaps) * a / 2)))
            selected = self.rng.sample(all_swaps, min(num_swaps, len(all_swaps)))
            return self._apply_swaps(wolf.position, selected)
        
        return wolf.position.copy()
    
    def _optimize_giant_tour(self, waypoints, depot, distance_matrix, demands,
                             sw_capacity, so_capacity, max_tour_duration) -> Solution:
        """GWO optimization for giant tour"""
        if not waypoints:
            return Solution(tour=[], fitness=0, total_cost=0, num_vehicles=0)
        
        # Initialize pack
        pack = []
        for _ in range(self.config["population_size"]):
            position = self._shuffle(waypoints)
            pack.append(Wolf(position=position, cost=float('inf')))
        
        # Evaluate initial
        for wolf in pack:
            sol = self._evaluate_solution(
                wolf.position, depot, distance_matrix, demands,
                sw_capacity, so_capacity, max_tour_duration
            )
            wolf.cost = sol.total_cost
        
        # Sort and identify leaders
        pack.sort(key=lambda w: w.cost)
        alpha = Wolf(position=pack[0].position.copy(), cost=pack[0].cost)
        beta = Wolf(position=pack[1].position.copy(), cost=pack[1].cost) if len(pack) > 1 else alpha
        delta = Wolf(position=pack[2].position.copy(), cost=pack[2].cost) if len(pack) > 2 else beta
        
        no_improvement = 0
        
        for iteration in range(self.config["max_iterations"]):
            a = self.config["initial_a"] * (1 - iteration / self.config["max_iterations"])
            
            improved = False
            
            for wolf in pack:
                if self.rng.random() < self.config["exploration_rate"] * a / self.config["initial_a"]:
                    new_position = self._shuffle(wolf.position)
                else:
                    new_position = self._update_position(wolf, alpha, beta, delta, a)
                
                sol = self._evaluate_solution(
                    new_position, depot, distance_matrix, demands,
                    sw_capacity, so_capacity, max_tour_duration
                )
                
                if sol.total_cost < wolf.cost:
                    wolf.position = new_position
                    wolf.cost = sol.total_cost
                
                # Update leaders
                if wolf.cost < alpha.cost:
                    delta = Wolf(position=beta.position.copy(), cost=beta.cost)
                    beta = Wolf(position=alpha.position.copy(), cost=alpha.cost)
                    alpha = Wolf(position=wolf.position.copy(), cost=wolf.cost)
                    improved = True
                elif wolf.cost < beta.cost:
                    delta = Wolf(position=beta.position.copy(), cost=beta.cost)
                    beta = Wolf(position=wolf.position.copy(), cost=wolf.cost)
                    improved = True
                elif wolf.cost < delta.cost:
                    delta = Wolf(position=wolf.position.copy(), cost=wolf.cost)
                    improved = True
            
            if improved:
                no_improvement = 0
            else:
                no_improvement += 1
            
            if no_improvement >= self.config["max_no_improvement"]:
                break
        
        return Solution(
            tour=alpha.position,
            fitness=1.0 / alpha.cost if alpha.cost > 0 else 0,
            total_cost=alpha.cost,
            num_vehicles=0
        )


# Convenience exports
__all__ = [
    'BaseSplitStrategy',
    'PSOSplitStrategy',
    'HHOSplitStrategy',
    'GWOSplitStrategy',
]
