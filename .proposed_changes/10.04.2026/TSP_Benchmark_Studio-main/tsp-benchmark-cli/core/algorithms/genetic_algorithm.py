"""Genetic Algorithm for TSP.

Evolves a population of tours using selection, crossover (OX / PMX),
and mutation operators.
"""
import numpy as np
from typing import List, Tuple
import time

from .base import TSPAlgorithm, AlgorithmResult

# Import numba utils with fallback
try:
    from ..numba_utils import (
        calc_tour_length_numba, nearest_neighbor_route, random_route,
        two_opt_improve, NUMBA_AVAILABLE
    )
except ImportError:
    from .local_search import (
        calc_tour_length_numba, nearest_neighbor_route, random_route,
        two_opt_improve
    )


def _ox_crossover(parent1: np.ndarray, parent2: np.ndarray,
                  rng: np.random.RandomState) -> Tuple[np.ndarray, np.ndarray]:
    """Order Crossover (OX): preserves relative order from both parents.

    Returns two children.
    """
    n = len(parent1)
    if n < 4:
        return parent1.copy(), parent2.copy()

    # Choose two crossover points
    cx1 = rng.randint(0, n - 1)
    cx2 = rng.randint(cx1 + 1, n)

    def _ox(p1, p2):
        child = np.full(n, -1, dtype=np.int64)
        # Copy segment from p1
        child[cx1:cx2] = p1[cx1:cx2]
        # Fill remaining positions in order from p2, wrapping
        pos = cx2
        for idx in range(n):
            gene = int(p2[(cx2 + idx) % n])
            if gene not in child:
                child[pos % n] = gene
                pos += 1
        return child

    return _ox(parent1, parent2), _ox(parent2, parent1)


def _pmx_crossover(parent1: np.ndarray, parent2: np.ndarray,
                   rng: np.random.RandomState) -> Tuple[np.ndarray, np.ndarray]:
    """Partially Mapped Crossover (PMX).

    Returns two children.
    """
    n = len(parent1)
    if n < 4:
        return parent1.copy(), parent2.copy()

    cx1 = rng.randint(0, n - 1)
    cx2 = rng.randint(cx1 + 1, n)

    def _pmx(p1, p2):
        child = np.full(n, -1, dtype=np.int64)
        child[cx1:cx2] = p1[cx1:cx2]
        # Build mapping for conflict resolution
        mapping = {}
        for i in range(cx1, cx2):
            gene = int(p2[i])
            if gene not in child:
                # Find slot
                mapped = int(p1[i])
                visited = {mapped}
                while mapped in child and mapped not in visited:
                    mapped = int(p2[np.where(p1 == mapped)[0][0]])
                    visited.add(mapped)
                if mapped not in child:
                    child[np.where(child == -1)[0][0]] = mapped
        # Fill remaining -1s from p2 in order
        for i in range(n):
            if child[i] == -1:
                child[i] = p2[i]
        return child

    return _pmx(parent1, parent2), _pmx(parent2, parent1)


def _mutate_swap(route: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Swap two random positions."""
    child = route.copy()
    i, j = rng.randint(0, len(child), size=2)
    while i == j:
        j = rng.randint(0, len(child))
    child[i], child[j] = child[j], child[i]
    return child


def _mutate_inversion(route: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Invert a random subsequence (2-opt-like mutation)."""
    child = route.copy()
    i = rng.randint(0, len(child) - 1)
    j = rng.randint(i + 1, len(child))
    child[i:j] = child[i:j][::-1]
    return child


def _mutate_insert(route: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Remove a node and insert it at a random position."""
    child = route.copy()
    n = len(child)
    i = rng.randint(0, n)
    gene = child[i]
    child = np.delete(child, i)
    j = rng.randint(0, n - 1)
    child = np.insert(child, j, gene)
    return child


class GeneticAlgorithm(TSPAlgorithm):
    """Genetic Algorithm for TSP.

    Parameters
    ----------
    population_size : int
        Number of individuals in the population.
    generations : int
        Maximum number of generations.
    elite_count : int
        Number of best individuals carried over unchanged.
    tournament_size : int
        Tournament selection size.
    crossover_method : str
        ``"ox"`` (order crossover) or ``"pmx"`` (partially mapped).
    mutation_rate : float
        Probability of applying mutation to an offspring.
    mutation_method : str
        ``"swap"``, ``"inversion"``, or ``"insert"``.
    local_search_interval : int
        Apply 2-opt to best individual every N generations (0 = never).
    construction : str
        ``"nearest"`` or ``"random"`` for initial population seeding.
    """

    def __init__(
        self,
        population_size: int = 60,
        generations: int = 500,
        elite_count: int = 4,
        tournament_size: int = 5,
        crossover_method: str = "ox",
        mutation_rate: float = 0.2,
        mutation_method: str = "inversion",
        local_search_interval: int = 20,
        construction: str = "random",
    ):
        self.population_size = population_size
        self.generations = generations
        self.elite_count = min(elite_count, population_size // 2)
        self.tournament_size = tournament_size
        self.crossover_method = crossover_method
        self.mutation_rate = mutation_rate
        self.mutation_method = mutation_method
        self.local_search_interval = local_search_interval
        self.construction = construction

    @property
    def name(self) -> str:
        return "ga"

    @property
    def display_name(self) -> str:
        return "Genetic Algorithm"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        rng = np.random.RandomState(seed)

        crossover_fn = _ox_crossover if self.crossover_method == "ox" else _pmx_crossover
        mutation_fn = {
            "swap": _mutate_swap,
            "inversion": _mutate_inversion,
            "insert": _mutate_insert,
        }.get(self.mutation_method, _mutate_inversion)

        # --- initialise population ---
        population: List[np.ndarray] = []
        # Seed one individual with nearest neighbor
        population.append(nearest_neighbor_route(dist_matrix, seed % n))
        # Fill the rest randomly
        for _ in range(self.population_size - 1):
            population.append(random_route(n, rng.randint(0, 2**31)))

        # Evaluate fitness
        fitness = np.array([
            calc_tour_length_numba(ind, dist_matrix) for ind in population
        ])
        best_idx = int(np.argmin(fitness))
        best_route = population[best_idx].copy()
        best_length = float(fitness[best_idx])
        convergence: List[float] = [best_length]
        log_interval = max(1, self.generations // 200)

        for gen in range(1, self.generations + 1):
            if gen % log_interval == 0:
                convergence.append(best_length)
            if time.time() - start > time_limit:
                break

            # --- sort by fitness ---
            order = np.argsort(fitness)
            population = [population[i] for i in order]
            fitness = fitness[order]

            # --- elitism ---
            new_population = [population[i].copy() for i in range(self.elite_count)]

            # --- reproduce ---
            while len(new_population) < self.population_size:
                # Tournament selection
                def _select():
                    candidates = rng.choice(self.population_size,
                                            size=min(self.tournament_size, self.population_size),
                                            replace=False)
                    return int(candidates[np.argmin(fitness[candidates])])
                p1_idx = _select()
                p2_idx = _select()
                child1, child2 = crossover_fn(population[p1_idx], population[p2_idx], rng)

                for child in (child1, child2):
                    if len(new_population) >= self.population_size:
                        break
                    if rng.rand() < self.mutation_rate:
                        child = mutation_fn(child, rng)
                    new_population.append(child)

            population = new_population[:self.population_size]
            fitness = np.array([
                calc_tour_length_numba(ind, dist_matrix) for ind in population
            ])

            gen_best_idx = int(np.argmin(fitness))
            if fitness[gen_best_idx] < best_length - 1e-10:
                best_length = float(fitness[gen_best_idx])
                best_route = population[gen_best_idx].copy()

            # --- periodic local search on best ---
            if (self.local_search_interval > 0
                    and gen % self.local_search_interval == 0
                    and time.time() - start < time_limit * 0.8):
                best_route, best_length = two_opt_improve(
                    best_route, dist_matrix, 50, False
                )
                # Inject back
                population[0] = best_route.copy()
                fitness[0] = best_length

        convergence.append(best_length)
        tour = best_route.tolist() if hasattr(best_route, 'tolist') else list(best_route)
        exec_time = time.time() - start
        return self._create_result(tour, best_length, optimal_value, exec_time,
                                   iterations=gen, convergence=convergence)
