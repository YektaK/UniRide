"""
Genetic Algorithm Strategy for TSP/CVRP
Based on Holland (1975) and Goldberg (1989)

Implements:
- Permutation encoding for TSP
- Order Crossover (OX1)
- Swap and Inversion Mutation
- Tournament Selection with Elitism
- Optional local search (2-opt, 3-opt, Or-opt, Hybrid)
"""

import random
import time
from typing import List, Dict, Tuple, Optional

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, euclidean_distance
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator
from uniride_core.algorithms.ga_operators import mutate_permutation, order_crossover
from uniride_core.algorithms.tsp_meta_engines import (
    TSPIndividual as Individual,
    solve_ga_tsp,
    tournament_selection,
)
from strategies.promoted_config_loader import get_promoted_strategy_params

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
        "max_no_improvement": 50,  # bildiri2026: 100; keep 50 for routing responsiveness
        "seed": None,
        "local_search_type": "two_opt",  # Local search to apply after GA
    }

    def __init__(self, config: Optional[Dict] = None):
        promoted = {} if config is not None else get_promoted_strategy_params(
            ("genetic_algorithm", "ga", "Numba-GA", "Core-GA-TSP")
        )
        self.config = {**self.DEFAULT_CONFIG, **promoted, **(config or {})}
        self.seed = self.config.get("seed") or int(time.time() * 1000)

    @property
    def name(self) -> str:
        return "genetic_algorithm"

    @property
    def display_name(self) -> str:
        return "Genetik Algoritma"

    @property
    def description(self) -> str:
        return "Popülasyon tabanlı meta-sezgisel optimizasyon. Büyük problemler için ideal."

    def _initialize_population(self, waypoints: List[str], rng: random.Random) -> List[Individual]:
        """Initialize population with random permutations"""
        population = []

        for _ in range(self.config["population_size"]):
            chromosome = waypoints.copy()
            rng.shuffle(chromosome)
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

    def _tournament_selection(self, population: List[Individual], rng: random.Random) -> Individual:
        """Select individual using tournament selection"""
        return tournament_selection(population, self.config["tournament_size"], rng)

    def _order_crossover(
        self,
        parent1: List[str],
        parent2: List[str],
        rng: random.Random,
    ) -> Tuple[List[str], List[str]]:
        """
        Order Crossover (OX1) - preserves relative order.
        Davis, L. (1985). Applying Adaptive Algorithms to Epistatic Domains.
        """
        return order_crossover(parent1, parent2, rng)

    def _mutate(self, chromosome: List[str], rng: random.Random) -> List[str]:
        """Apply mutation (swap or inversion)"""
        return mutate_permutation(chromosome, rng, mutation_type="swap" if rng.random() < 0.5 else "inversion")

    def _evolve(self, population: List[Individual], rng: random.Random) -> List[Individual]:
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
            parent1 = self._tournament_selection(sorted_pop, rng)
            parent2 = self._tournament_selection(sorted_pop, rng)

            # Crossover
            if rng.random() < self.config["crossover_rate"]:
                child1, child2 = self._order_crossover(
                    parent1.chromosome, parent2.chromosome, rng
                )
            else:
                child1 = parent1.chromosome.copy()
                child2 = parent2.chromosome.copy()

            # Mutation
            if rng.random() < self.config["mutation_rate"]:
                child1 = self._mutate(child1, rng)
            if rng.random() < self.config["mutation_rate"]:
                child2 = self._mutate(child2, rng)

            new_population.append(Individual(
                chromosome=child1, fitness=0.0, total_duration=float('inf')
            ))
            if len(new_population) < self.config["population_size"]:
                new_population.append(Individual(
                    chromosome=child2, fitness=0.0, total_duration=float('inf')
                ))

        return new_population[:self.config["population_size"]]

    def _solve_tsp(
        self,
        waypoints: List[str],
        depot: str,
        time_matrix: Dict,
        coordinates: Dict,
        rng: random.Random,
        config: Optional[Dict] = None,
    ) -> Tuple[List[str], float]:
        """Solve TSP for a single vehicle.

        Upgraded to match bildiri2026 GAOptimizer logic:
        - Memetic 2-opt initialization (10 iter per individual)
        - Elites carried without re-evaluation
        - New children evaluated immediately
        - Early stop via max_no_improvement
        - Final 300-iter 2-opt polish (bildiri2026 canonical)
        """
        if not waypoints:
            return [], 0.0

        def duration_func(route: List[str]) -> float:
            return self._calculate_route_duration(route, depot, time_matrix, coordinates)

        return solve_ga_tsp(waypoints, duration_func, rng, config or self.config)

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

        # Singleton self.config korunuyor; her istek icin local kopya
        effective_config = dict(self.config)
        if request.ga_config:
            effective_config.update(request.ga_config)
            rng = random.Random(effective_config.get("seed", self.seed))
        else:
            rng = random.Random(self.seed)

        # Set local search type from request
        if request.local_search_type:
            effective_config["local_search_type"] = request.local_search_type

        # Build time matrix and coordinates
        data_loader = DataLoader.get_instance()

        location_ids = [depot.id] + [s.location_code for s in students]

        # Build coordinates BEFORE get_submatrix for euclidean distance fallback
        # When Supabase is unavailable, this enables proper distance computation
        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        raw_matrix = data_loader.get_submatrix(location_ids, coordinates)
        time_matrix = {
            location_ids[i]: {
                location_ids[j]: raw_matrix[i][j]
                for j in range(len(location_ids))
            }
            for i in range(len(location_ids))
        }

        # Helper to compute euclidean distance between two location IDs
        def _dist(loc1: str, loc2: str) -> float:
            c1 = coordinates.get(loc1, {})
            c2 = coordinates.get(loc2, {})
            return round(euclidean_distance(c1.get("lat", 0), c1.get("lng", 0), c2.get("lat", 0), c2.get("lng", 0)), 2)

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

        # Calculate vehicle assignments - use request clustering_algorithm (default: sweep)
        calculator = VehicleCalculator(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time,
            clustering_algorithm=request.clustering_algorithm or "sweep"
        )

        def route_optimizer(location_codes: List[str]) -> Dict:
            """Optimize single vehicle route"""
            if not location_codes:
                return {"route_details": [], "total_duration": 0}

            optimized_route, duration = self._solve_tsp(
                location_codes, depot.id, time_matrix, coordinates, rng, effective_config
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
                    distance=_dist(step["location1"], step["location2"])
                )
                for step in assignment["route"]
            ]

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {assignment['vehicle_index']} (GA)",
                route_details=route_steps,
                total_duration_minutes=round(assignment["total_duration"], 2),
                total_distance_km=round(sum(s.distance for s in route_steps), 2),
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
