"""Core GA-Split engine for string-keyed UniRide CVRP/CVRPTW problems."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from uniride_core.algorithms.ga_operators import mutate_permutation, order_crossover
from uniride_core.algorithms.local_search import LocalSearchType, apply_local_search
from uniride_core.algorithms.objective_rank import (
    FeasibleVehiclesCost,
    fitness_from_key,
    objective_key,
)
from uniride_core.algorithms.string_split_decoder import decode_giant_tour, decode_with_time_windows

logger = logging.getLogger(__name__)

DEFAULT_TRAVEL_FALLBACK_MINUTES = 15.0


@dataclass
class GAIndividual:
    """Individual representing a giant tour permutation."""

    chromosome: List[str]
    fitness: float = 0.0
    total_cost: float = float("inf")
    num_vehicles: int = 0
    obj_key: Optional[FeasibleVehiclesCost] = None


@dataclass
class GASplitSolution:
    """Result of the GA-Split core search."""

    best_individual: GAIndividual
    final_result: Dict[str, Any]
    generations: int


def nearest_neighbor_tour(
    waypoints: List[str],
    distance_matrix: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> List[str]:
    """Build an initial tour using nearest-neighbor over string location ids."""
    if not waypoints:
        return []

    tour: List[str] = []
    remaining = waypoints.copy()
    current = remaining.pop(0)
    tour.append(current)

    while remaining:
        if distance_matrix and current in distance_matrix:
            best_next = min(
                remaining,
                key=lambda location: distance_matrix[current].get(location, float("inf")),
            )
        else:
            best_next = remaining[0]
        tour.append(best_next)
        remaining.remove(best_next)
        current = best_next

    return tour


def initialize_population(
    waypoints: List[str],
    config: Mapping[str, Any],
    rng: random.Random,
    distance_matrix: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> List[GAIndividual]:
    """Initialize GA-Split population with random and heuristic permutations."""
    population: List[GAIndividual] = []
    population_size = int(config.get("population_size", 50))

    for _ in range(max(0, population_size - 2)):
        chromosome = waypoints.copy()
        rng.shuffle(chromosome)
        population.append(GAIndividual(chromosome=chromosome))

    nn_tour = nearest_neighbor_tour(waypoints, distance_matrix)
    if nn_tour:
        population.append(GAIndividual(chromosome=nn_tour))

    sorted_tour = waypoints.copy()
    rng.shuffle(sorted_tour)
    population.append(GAIndividual(chromosome=sorted_tour))

    return population[:population_size]


def evaluate_individual(
    individual: GAIndividual,
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    is_asymmetric: bool = False,
) -> GAIndividual:
    """Evaluate an individual by decoding its giant tour into feasible routes."""
    result = decode_giant_tour(
        giant_tour=individual.chromosome,
        depot=depot,
        distance_matrix=distance_matrix,
        demands=demands,
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration,
        is_asymmetric=is_asymmetric,
    )

    if result["num_vehicles"] == 0:
        key = (1, 999, float("inf"))
        return GAIndividual(
            chromosome=individual.chromosome,
            fitness=fitness_from_key(key),
            total_cost=float("inf"),
            num_vehicles=999,
            obj_key=key,
        )

    total_cost = float(result["total_cost"])
    num_vehicles = int(result["num_vehicles"])
    key = objective_key({"num_vehicles": num_vehicles, "total_cost": total_cost})
    fitness = fitness_from_key(key)

    return GAIndividual(
        chromosome=individual.chromosome,
        fitness=fitness,
        total_cost=total_cost,
        num_vehicles=num_vehicles,
        obj_key=key,
    )


def evaluate_population(
    population: List[GAIndividual],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    is_asymmetric: bool = False,
) -> List[GAIndividual]:
    """Evaluate all individuals in a population."""
    return [
        evaluate_individual(
            individual,
            depot,
            distance_matrix,
            demands,
            sw_capacity,
            so_capacity,
            max_tour_duration,
            is_asymmetric=is_asymmetric,
        )
        for individual in population
    ]


def tournament_selection(
    population: List[GAIndividual],
    tournament_size: int,
    rng: random.Random,
) -> GAIndividual:
    """Select an individual using tournament selection."""
    tournament = rng.sample(population, min(tournament_size, len(population)))
    return min(tournament, key=lambda individual: individual.obj_key or (1, 999, float("inf")))


def educate_individual(
    individual: GAIndividual,
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    local_search_type: str = "two_opt",
) -> GAIndividual:
    """Apply local-search education to a giant tour."""

    def cost_func(route: List[str]) -> float:
        total = 0.0
        previous = depot
        for location in route:
            total += distance_matrix.get(previous, {}).get(location, DEFAULT_TRAVEL_FALLBACK_MINUTES)
            previous = location
        total += distance_matrix.get(previous, {}).get(depot, DEFAULT_TRAVEL_FALLBACK_MINUTES)
        return total

    try:
        improved_route, _ = apply_local_search(
            individual.chromosome,
            cost_func,
            LocalSearchType(local_search_type),
        )
        return GAIndividual(
            chromosome=improved_route,
            fitness=individual.fitness,
            total_cost=individual.total_cost,
            num_vehicles=individual.num_vehicles,
            obj_key=individual.obj_key,
        )
    except Exception as exc:
        logger.debug("Local search failed for individual: %s", exc)
        return individual


def diversify_population(
    population: List[GAIndividual],
    rng: random.Random,
) -> List[GAIndividual]:
    """Keep the best 30 percent and refill the rest with random permutations."""
    sorted_population = sorted(population, key=lambda individual: individual.obj_key or (1, 999, float("inf")))
    keep_count = max(2, int(len(population) * 0.3))
    new_population = [
        GAIndividual(
            chromosome=individual.chromosome.copy(),
            fitness=individual.fitness,
            total_cost=individual.total_cost,
            num_vehicles=individual.num_vehicles,
            obj_key=individual.obj_key,
        )
        for individual in sorted_population[:keep_count]
    ]

    waypoints = sorted_population[0].chromosome.copy() if sorted_population else []
    while len(new_population) < len(population):
        chromosome = waypoints.copy()
        rng.shuffle(chromosome)
        new_population.append(GAIndividual(chromosome=chromosome))

    return new_population


def evolve_population(
    population: List[GAIndividual],
    config: Mapping[str, Any],
    rng: random.Random,
) -> List[GAIndividual]:
    """Create the next GA-Split generation."""
    new_population: List[GAIndividual] = []
    sorted_population = sorted(population, key=lambda individual: individual.obj_key or (1, 999, float("inf")))
    elite_count = int(config.get("elite_count", 3))
    population_size = int(config.get("population_size", 50))
    tournament_size = int(config.get("tournament_size", 4))
    crossover_rate = float(config.get("crossover_rate", 0.85))
    mutation_rate = float(config.get("mutation_rate", 0.20))

    for individual in sorted_population[:min(elite_count, len(sorted_population))]:
        new_population.append(
            GAIndividual(
                chromosome=individual.chromosome.copy(),
                fitness=individual.fitness,
                total_cost=individual.total_cost,
                num_vehicles=individual.num_vehicles,
                obj_key=individual.obj_key,
            )
        )

    while len(new_population) < population_size:
        parent1 = tournament_selection(sorted_population, tournament_size, rng)
        parent2 = tournament_selection(sorted_population, tournament_size, rng)

        if rng.random() < crossover_rate:
            child1, child2 = order_crossover(parent1.chromosome, parent2.chromosome, rng)
        else:
            child1 = parent1.chromosome.copy()
            child2 = parent2.chromosome.copy()

        if rng.random() < mutation_rate:
            child1 = mutate_permutation(child1, rng)
        if rng.random() < mutation_rate:
            child2 = mutate_permutation(child2, rng)

        new_population.append(GAIndividual(chromosome=child1))
        if len(new_population) < population_size:
            new_population.append(GAIndividual(chromosome=child2))

    return new_population[:population_size]


def solve_ga_split(
    waypoints: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    config: Mapping[str, Any],
    rng: random.Random,
    *,
    use_time_windows: bool = False,
    time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
    direction: Any = "pickup",
    target_time: Optional[int] = None,
    offset_minutes: int = 10,
    is_asymmetric: bool = False,
) -> GASplitSolution:
    """Run GA-Split and return the final decoded route result."""
    population = initialize_population(waypoints, config, rng, distance_matrix)
    population = evaluate_population(
        population,
        depot,
        distance_matrix,
        demands,
        sw_capacity,
        so_capacity,
        max_tour_duration,
        is_asymmetric=is_asymmetric,
    )

    best = min(population, key=lambda individual: individual.obj_key or (1, 999, float("inf")))
    no_improvement = 0
    generation = 0

    for generation in range(int(config.get("max_iterations", 100))):
        population = evolve_population(population, config, rng)
        population = evaluate_population(
            population,
            depot,
            distance_matrix,
            demands,
            sw_capacity,
            so_capacity,
            max_tour_duration,
            is_asymmetric=is_asymmetric,
        )

        current_best = min(population, key=lambda individual: individual.obj_key or (1, 999, float("inf")))
        if generation % int(config.get("local_search_interval", 10)) == 0:
            current_best = educate_individual(
                current_best,
                depot,
                distance_matrix,
                str(config.get("local_search_type", "two_opt")),
            )
            current_best = evaluate_individual(
                current_best,
                depot,
                distance_matrix,
                demands,
                sw_capacity,
                so_capacity,
                max_tour_duration,
                is_asymmetric=is_asymmetric,
            )

        if (current_best.obj_key or (1, 999, float("inf"))) < (best.obj_key or (1, 999, float("inf"))):
            best = current_best
            no_improvement = 0
        else:
            no_improvement += 1

        if no_improvement >= int(config.get("max_no_improvement", 25)):
            break

        if no_improvement >= int(config.get("diversify_threshold", 30)):
            population = diversify_population(population, rng)
            population = evaluate_population(
                population,
                depot,
                distance_matrix,
                demands,
                sw_capacity,
                so_capacity,
                max_tour_duration,
                is_asymmetric=is_asymmetric,
            )
            no_improvement = 0

    if use_time_windows and time_windows:
        final_result = decode_with_time_windows(
            giant_tour=best.chromosome,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            time_windows=time_windows,
            direction=direction,
            target_time=target_time,
            offset_minutes=offset_minutes,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
            max_tour_duration=max_tour_duration,
            is_asymmetric=is_asymmetric,
        )
    else:
        final_result = decode_giant_tour(
            giant_tour=best.chromosome,
            depot=depot,
            distance_matrix=distance_matrix,
            demands=demands,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
            max_tour_duration=max_tour_duration,
            is_asymmetric=is_asymmetric,
        )

    return GASplitSolution(
        best_individual=best,
        final_result=final_result,
        generations=generation,
    )


__all__ = [
    "GAIndividual",
    "GASplitSolution",
    "diversify_population",
    "educate_individual",
    "evaluate_individual",
    "evaluate_population",
    "evolve_population",
    "initialize_population",
    "nearest_neighbor_tour",
    "solve_ga_split",
    "tournament_selection",
]
