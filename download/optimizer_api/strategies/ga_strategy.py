"""
Genetic Algorithm Strategy for TSP/CVRP
Based on Holland (1975) and Goldberg (1989)

Implements:
- Permutation encoding for TSP
- Order Crossover (OX1)
- Swap and Inversion Mutation
- Tournament Selection with Elitism
"""

import random
import time
from typing import List, Dict, Tuple, Callable, Optional
from dataclasses import dataclass

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep, StudentNode
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.clustering import VehicleCalculator, Point
from utils.local_search import apply_local_search, LocalSearchType


@dataclass
class Individual:
    """Individual in population representing a route permutation"""
    chromosome: List[str]  # Ordered location codes
    fitness: float  # 1 / total_duration
    total_duration: float


class GeneticAlgorithmStrategy(BaseRoutingStrategy):
    """
    Genetic Algorithm for Vehicle Routing Problem.
    Uses K-Means clustering for multi-vehicle problems, then GA for TSP.
    """

    # Default GA parameters
    DEFAULT_CONFIG = {
        "population_size": 50,
        "max_iterations": 100,
        "crossover_rate": 0.85,
        "mutation_rate": 0.15,
        "elite_count": 2,
        "tournament_size": 3,
        "max_no_improvement": 20,
        "local_search_rate": 0.2,  # Probability of applying local search
        "local_search_type": "2opt",  # "2opt", "3opt", "or_opt", "hybrid"
        "seed": None
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)
        self.rng = random.Random(self.seed)
        
    def _get_local_search_type(self) -> LocalSearchType:
        """Convert config string to LocalSearchType enum"""
        type_map = {
            "2opt": LocalSearchType.TWO_OPT,
            "3opt": LocalSearchType.THREE_OPT,
            "or_opt": LocalSearchType.OR_OPT,
            "hybrid": LocalSearchType.HYBRID
        }
        return type_map.get(
            self.config.get("local_search_type", "2opt"),
            LocalSearchType.TWO_OPT
        )

    @property
    def name(self) -> str:
        return "genetic_algorithm"

    @property
    def display_name(self) -> str:
        return "Genetik Algoritma"

    @property
    def description(self) -> str:
        return "Popülasyon tabanlı meta-sezgisel optimizasyon. Büyük problemler için ideal."

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between two locations"""
        # Try time matrix first
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]

        # Fall back to coordinate-based calculation
        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)

        # Default fallback
        return 15.0

    def _calculate_route_duration(
        self,
        chromosome: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> float:
        """Calculate total route duration for a chromosome"""
        if not chromosome:
            return 0.0

        total = 0.0

        # Depot to first
        total += self._get_duration(depot, chromosome[0], time_matrix, coordinates)

        # Between waypoints
        for i in range(len(chromosome) - 1):
            total += self._get_duration(chromosome[i], chromosome[i + 1], time_matrix, coordinates)

        # Last to depot
        total += self._get_duration(chromosome[-1], depot, time_matrix, coordinates)

        return total

    def _initialize_population(self, waypoints: List[str]) -> List[Individual]:
        """Initialize population with random permutations"""
        population = []

        for _ in range(self.config["population_size"]):
            chromosome = waypoints.copy()
            self.rng.shuffle(chromosome)
            population.append(Individual(
                chromosome=chromosome,
                fitness=0.0,
                total_duration=float('inf')
            ))

        return population

    def _evaluate_population(
        self,
        population: List[Individual],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> List[Individual]:
        """Evaluate fitness for all individuals"""
        evaluated = []

        for ind in population:
            duration = self._calculate_route_duration(
                ind.chromosome, depot, time_matrix, coordinates
            )
            fitness = 1.0 / duration if duration > 0 else 0.0
            evaluated.append(Individual(
                chromosome=ind.chromosome,
                fitness=fitness,
                total_duration=duration
            ))

        return evaluated

    def _tournament_selection(self, population: List[Individual]) -> Individual:
        """Select individual using tournament selection"""
        tournament = self.rng.sample(
            population,
            min(self.config["tournament_size"], len(population))
        )
        return max(tournament, key=lambda x: x.fitness)

    def _order_crossover(
        self,
        parent1: List[str],
        parent2: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Order Crossover (OX1) - preserves relative order.
        Davis, L. (1985). Applying Adaptive Algorithms to Epistatic Domains.
        """
        n = len(parent1)
        if n < 2:
            return parent1.copy(), parent2.copy()

        # Select random segment
        start = self.rng.randint(0, n - 1)
        end = self.rng.randint(start, n - 1)

        # Initialize children
        child1 = [None] * n
        child2 = [None] * n

        # Copy segment
        for i in range(start, end + 1):
            child1[i] = parent1[i]
            child2[i] = parent2[i]

        # Fill remaining positions
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

        return child1, child2

    def _mutate(self, chromosome: List[str]) -> List[str]:
        """Apply mutation (swap or inversion)"""
        mutated = chromosome.copy()

        if self.rng.random() < 0.5:
            # Swap mutation
            i, j = self.rng.sample(range(len(mutated)), 2)
            mutated[i], mutated[j] = mutated[j], mutated[i]
        else:
            # Inversion mutation
            i, j = self.rng.sample(range(len(mutated)), 2)
            start, end = min(i, j), max(i, j)
            mutated[start:end + 1] = reversed(mutated[start:end + 1])

        return mutated

    def _evolve(self, population: List[Individual]) -> List[Individual]:
        """Create next generation"""
        new_population = []

        # Sort by fitness
        sorted_pop = sorted(population, key=lambda x: x.fitness, reverse=True)

        # Elitism: preserve best
        for i in range(min(self.config["elite_count"], len(sorted_pop))):
            new_population.append(Individual(
                chromosome=sorted_pop[i].chromosome.copy(),
                fitness=sorted_pop[i].fitness,
                total_duration=sorted_pop[i].total_duration
            ))

        # Generate offspring
        while len(new_population) < self.config["population_size"]:
            parent1 = self._tournament_selection(sorted_pop)
            parent2 = self._tournament_selection(sorted_pop)

            # Crossover
            if self.rng.random() < self.config["crossover_rate"]:
                child1, child2 = self._order_crossover(
                    parent1.chromosome, parent2.chromosome
                )
            else:
                child1 = parent1.chromosome.copy()
                child2 = parent2.chromosome.copy()

            # Mutation
            if self.rng.random() < self.config["mutation_rate"]:
                child1 = self._mutate(child1)
            if self.rng.random() < self.config["mutation_rate"]:
                child2 = self._mutate(child2)

            new_population.append(Individual(
                chromosome=child1, fitness=0.0, total_duration=float('inf')
            ))
            if len(new_population) < self.config["population_size"]:
                new_population.append(Individual(
                    chromosome=child2, fitness=0.0, total_duration=float('inf')
                ))

        return new_population[:self.config["population_size"]]

    def _local_search(
        self,
        chromosome: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        max_iterations: int = 10
    ) -> Tuple[List[str], float]:
        """
        Local search using configurable search type.
        Supports: 2-opt, 3-opt, Or-opt, and Hybrid modes.
        """
        return apply_local_search(
            route=chromosome,
            depot=depot,
            time_matrix=time_matrix,
            coordinates=coordinates,
            search_type=self._get_local_search_type(),
            max_iterations=max_iterations,
            first_improvement=False
        )

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle"""
        if not waypoints:
            return [], 0.0

        if len(waypoints) == 1:
            duration = (
                self._get_duration(depot, waypoints[0], time_matrix, coordinates) +
                self._get_duration(waypoints[0], depot, time_matrix, coordinates)
            )
            return waypoints, duration

        # Initialize population
        population = self._initialize_population(waypoints)
        population = self._evaluate_population(population, depot, time_matrix, coordinates)

        best = min(population, key=lambda x: x.total_duration)
        no_improvement = 0

        for generation in range(self.config["max_iterations"]):
            population = self._evolve(population)
            population = self._evaluate_population(population, depot, time_matrix, coordinates)

            current_best = min(population, key=lambda x: x.total_duration)

            # Apply local search to best individual periodically
            if self.rng.random() < self.config["local_search_rate"]:
                improved_chromosome, improved_duration = self._local_search(
                    current_best.chromosome, depot, time_matrix, coordinates, max_iterations=5
                )
                if improved_duration < current_best.total_duration:
                    # Update the individual in population
                    for i, ind in enumerate(population):
                        if ind.chromosome == current_best.chromosome:
                            population[i] = Individual(
                                chromosome=improved_chromosome,
                                fitness=1.0 / improved_duration,
                                total_duration=improved_duration
                            )
                            current_best = population[i]
                            break

            if current_best.total_duration < best.total_duration:
                best = current_best
                no_improvement = 0
            else:
                no_improvement += 1

            if no_improvement >= self.config["max_no_improvement"]:
                break

        # Final local search on best solution
        final_chromosome, final_duration = self._local_search(
            best.chromosome, depot, time_matrix, coordinates, max_iterations=15
        )

        return final_chromosome, final_duration

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
        if request.ga_config:
            self.config.update(request.ga_config)
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

        # Build coordinates dict
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        # Convert students to dict format
        student_dicts = []
        for s in students:
            student_dicts.append({
                "id": s.id,
                "name": s.name,
                "location_code": s.location_code,
                "coordinates": s.coordinates or {"lat": 0, "lng": 0},
                "disability_type": s.disability_type
            })

        # Calculate vehicle assignments
        calculator = VehicleCalculator(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time
        )

        def route_optimizer(location_codes: List[str]) -> Dict:
            """Optimize single vehicle route"""
            if not location_codes:
                return {"route_details": [], "total_duration": 0}

            optimized_route, duration = self._solve_tsp(
                location_codes, depot.id, time_matrix, coordinates
            )

            # Build route details
            route_details = []
            current = depot.id
            total_duration = 0

            for loc in optimized_route:
                d = self._get_duration(current, loc, time_matrix, coordinates)
                route_details.append({
                    "location1": current,
                    "location2": loc,
                    "duration": d
                })
                total_duration += d
                current = loc

            # Return to depot
            d = self._get_duration(current, depot.id, time_matrix, coordinates)
            route_details.append({
                "location1": current,
                "location2": depot.id,
                "duration": d
            })
            total_duration += d

            return {"route_details": route_details, "total_duration": total_duration}

        result = calculator.calculate(student_dicts, route_optimizer)

        # Build response routes
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
                vehicle_id=f"Araç {assignment['vehicle_index']} (GA)",
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
