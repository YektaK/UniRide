"""
CGO-TSP — Chaos Game Optimization (TSP variant)

Adapted from Talatahari & Azizi (2021) "Chaos Game Optimization: a novel
metaheuristic algorithm" for discrete TSP permutation space.

Core DNA:
  - Chaos game: iterative point placement using deterministic rules + chaos
  - Seed-based construction: partial tours (seeds) merged via chaos-controlled interleaving
  - Self-similarity: seeds double in length each iteration until full tour
  - Logistic map: chaos factor controls merge randomness and exploration
  - Lightweight: only 3 parameters (population, chaos_rate, max_iterations)

Discrete TSP Adaptation:
  - Continuous seed placement → discrete partial tour construction
  - Continuous averaging → chaos-controlled tour merge (interleaving)
  - Self-similarity → hierarchical merge (subtours → full tour)
  - Chaos map → logistic map x_{t+1} = r * x_t * (1 - x_t)
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base_solver import BaseTSPSolver, TSPResult
from .ls_engine import MultiLayerLS


@dataclass
class CGOConfig:
    population_size: int = 40
    max_iterations: int = 500
    chaos_rate: float = 3.99        # Logistic map r parameter (3.57–4.0 for chaos)
    seed_length_ratio: float = 0.25 # Initial seed length as fraction of n
    ls_time_limit: float = 0.5
    three_opt_window: int = 12
    time_limit: float = 300.0
    seed: int = 42


def _logistic_map(x: float, r: float = 3.99) -> float:
    """Logistic map: x_{t+1} = r * x_t * (1 - x_t)."""
    return r * x * (1.0 - x)


def _chaos_sequence(length: int, r: float, rng: random.Random) -> List[float]:
    """Generate chaos sequence using logistic map."""
    x = rng.uniform(0.1, 0.9)  # Avoid fixed points 0 and 1
    seq = []
    for _ in range(length):
        x = _logistic_map(x, r)
        seq.append(x)
    return seq


def _greedy_tour(dist_matrix: List[List[float]], start: int, n: int) -> List[int]:
    """Build a greedy tour starting from a given node."""
    visited = [False] * n
    visited[start] = True
    tour = [start]
    current = start
    for _ in range(n - 1):
        best_next = -1
        best_dist = float("inf")
        for j in range(n):
            if not visited[j] and dist_matrix[current][j] < best_dist:
                best_dist = dist_matrix[current][j]
                best_next = j
        visited[best_next] = True
        tour.append(best_next)
        current = best_next
    return tour


def _random_tour(n: int, rng: random.Random) -> List[int]:
    """Generate a random permutation tour."""
    tour = list(range(n))
    rng.shuffle(tour)
    return tour


def _chaos_merge(tour_a: List[int], tour_b: List[int], chaos_seq: List[float],
                 dist_matrix: List[List[float]], rng: random.Random) -> List[int]:
    """Merge two partial tours by interleaving cities with chaos-controlled randomness.

    Uses chaos values to decide which tour to pick next city from,
    then applies greedy repair to fix duplicates and missing cities.
    """
    n_total = len(dist_matrix)
    merged = []
    idx_a, idx_b = 0, 0
    chaos_idx = 0
    seq_len = len(chaos_seq) if chaos_seq else 1

    # Interleave using chaos sequence
    while idx_a < len(tour_a) and idx_b < len(tour_b):
        c = chaos_seq[chaos_idx % seq_len]
        chaos_idx += 1

        if c > 0.5:
            merged.append(tour_a[idx_a])
            idx_a += 1
        else:
            merged.append(tour_b[idx_b])
            idx_b += 1

    # Append remaining
    merged.extend(tour_a[idx_a:])
    merged.extend(tour_b[idx_b:])

    # Repair: remove duplicates, add missing cities
    seen = set()
    cleaned = []
    for city in merged:
        if city not in seen and city < n_total:
            seen.add(city)
            cleaned.append(city)

    # Add missing cities
    missing = [c for c in range(n_total) if c not in seen]
    rng.shuffle(missing)
    cleaned.extend(missing)

    return cleaned


def _crossover_ox(parent_a: List[int], parent_b: List[int],
                   rng: random.Random) -> Tuple[List[int], List[int]]:
    """Order crossover (OX) for TSP."""
    n = len(parent_a)
    if n < 3:
        return parent_a[:], parent_b[:]

    # Select two crossover points
    cp1 = rng.randint(0, n - 2)
    cp2 = rng.randint(cp1 + 1, n - 1)

    # Child 1: segment from parent_a, fill from parent_b
    child1 = [-1] * n
    child1[cp1:cp2 + 1] = parent_a[cp1:cp2 + 1]
    segment_a = set(child1[cp1:cp2 + 1])

    fill_pos = (cp2 + 1) % n
    for i in range(n):
        idx = (cp2 + 1 + i) % n
        if parent_b[idx] not in segment_a:
            while child1[fill_pos] != -1:
                fill_pos = (fill_pos + 1) % n
            child1[fill_pos] = parent_b[idx]

    # Child 2: segment from parent_b, fill from parent_a
    child2 = [-1] * n
    child2[cp1:cp2 + 1] = parent_b[cp1:cp2 + 1]
    segment_b = set(child2[cp1:cp2 + 1])

    fill_pos = (cp2 + 1) % n
    for i in range(n):
        idx = (cp2 + 1 + i) % n
        if parent_a[idx] not in segment_b:
            while child2[fill_pos] != -1:
                fill_pos = (fill_pos + 1) % n
            child2[fill_pos] = parent_a[idx]

    return child1, child2


def _mutate_swap(tour: List[int], rng: random.Random, n_swaps: int = 1) -> List[int]:
    """Apply random swap mutations."""
    result = tour[:]
    n = len(result)
    for _ in range(n_swaps):
        i, j = rng.sample(range(n), 2)
        result[i], result[j] = result[j], result[i]
    return result


def _mutate_2opt(tour: List[int], rng: random.Random) -> List[int]:
    """Apply a single 2-opt move."""
    result = tour[:]
    n = len(result)
    if n < 4:
        return result
    i = rng.randint(0, n - 3)
    j = rng.randint(i + 2, min(i + 12, n - 1))  # Bounded window
    result[i:j + 1] = result[i:j + 1][::-1]
    return result


class CGO_TSP(BaseTSPSolver):
    """Chaos Game Optimization for TSP.

    Construction-based approach: seeds (partial tours) are merged using
    chaos-controlled interleaving, then refined with local search.
    """

    def __init__(self, config: Optional[CGOConfig] = None):
        super().__init__("CGO-TSP", config.seed if config else 42)
        self.cfg = config or CGOConfig()
        self._rng = random.Random(self.cfg.seed)

    def _init_population(self, n: int) -> List[List[int]]:
        """Initialize population with greedy + random tours."""
        pop = []
        # 50% greedy tours from random starts
        for _ in range(self.cfg.population_size // 2):
            start = self._rng.randint(0, n - 1)
            pop.append(_greedy_tour(self._dist_matrix, start, n))
        # 50% random tours
        for _ in range(self.cfg.population_size - len(pop)):
            pop.append(_random_tour(n, self._rng))
        return pop

    def _create_seeds(self, tour: List[int], n: int) -> List[List[int]]:
        """Create partial tour seeds from a full tour.

        Seeds are subsequences of the tour, length controlled by seed_length_ratio.
        """
        seed_len = max(3, int(n * self.cfg.seed_length_ratio))
        seeds = []
        # Sliding window seeds
        step = max(1, n // 4)
        for start in range(0, n, step):
            seed = []
            for k in range(seed_len):
                seed.append(tour[(start + k) % n])
            seeds.append(seed)
        return seeds

    def _expand_seeds(self, seeds: List[List[int]], chaos_seq: List[float],
                      n: int) -> List[List[int]]:
        """Expand seeds by merging pairs using chaos-controlled interleaving."""
        new_seeds = []
        for i in range(0, len(seeds) - 1, 2):
            merged = _chaos_merge(seeds[i], seeds[i + 1], chaos_seq, self._dist_matrix, self._rng)
            new_seeds.append(merged)
        # If odd number, keep last seed
        if len(seeds) % 2 == 1:
            new_seeds.append(seeds[-1])
        return new_seeds

    def _seed_to_full_tour(self, seed: List[int], n: int) -> List[int]:
        """Expand a partial seed to a full tour by adding missing cities greedily."""
        seen = set(seed)
        missing = [c for c in range(n) if c not in seen]

        if not missing:
            return seed[:n]  # Already full

        tour = seed[:]
        for city in missing:
            best_pos = len(tour)
            best_delta = float("inf")
            n_t = len(tour)
            for pos in range(n_t + 1):
                pred = tour[(pos - 1) % n_t]
                succ = tour[pos % n_t]
                delta = self._dist_matrix[pred][city] + self._dist_matrix[city][succ] - self._dist_matrix[pred][succ]
                if delta < best_delta:
                    best_delta = delta
                    best_pos = pos
            tour = tour[:best_pos] + [city] + tour[best_pos:]

        return tour

    def _solve(self) -> TSPResult:
        t_start = time.perf_counter()
        n = self._n

        if n < 3:
            tour = list(range(n))
            return TSPResult(
                algorithm=self.name, tour=tour,
                tour_length=self.tour_length(tour),
                elapsed_ms=(time.perf_counter() - t_start) * 1000,
                iterations=0, params={"population_size": self.cfg.population_size},
                seed=self.cfg.seed,
            )

        # Initialize population
        population = self._init_population(n)
        fitness = [self.tour_length(t) for t in population]

        best_tour = min(population, key=self.tour_length)
        best_cost = self.tour_length(best_tour)
        history = [best_cost]

        # Main loop
        max_iter = self.cfg.max_iterations
        time_limit = self.cfg.time_limit

        for iteration in range(max_iter):
            # Check time limit
            if time.perf_counter() - t_start > time_limit:
                break

            # Get current chaos value for this iteration
            c_val = _logistic_map(iteration / max_iter, self.cfg.chaos_rate)
            c_val = max(0.0, min(1.0, c_val))  # Clamp to [0, 1]

            # Sort population by fitness
            sorted_indices = sorted(range(len(fitness)), key=lambda i: fitness[i])
            sorted_pop = [population[i] for i in sorted_indices]
            sorted_fit = [fitness[i] for i in sorted_indices]

            # Elitism: keep best tour
            elite = sorted_pop[0]
            elite_cost = sorted_fit[0]

            if elite_cost < best_cost:
                best_tour = elite[:]
                best_cost = elite_cost

            # Generate new population using chaos game operators
            new_population = [elite[:]]  # Keep elite

            for i in range(1, self.cfg.population_size):
                # Select two parents (tournament selection, k=3)
                p1_idx = min(self._rng.sample(range(len(sorted_pop)), 3), key=lambda i: sorted_fit[i])
                p2_idx = min(self._rng.sample(range(len(sorted_pop)), 3), key=lambda i: sorted_fit[i])
                parent_a = sorted_pop[p1_idx]
                parent_b = sorted_pop[p2_idx]

                # Chaos game operator: choose between merge, crossover, or mutation
                if c_val > 0.7:
                    # Chaos merge: create seeds and merge
                    seeds_a = self._create_seeds(parent_a, n)
                    seeds_b = self._create_seeds(parent_b, n)
                    iter_chaos = _chaos_sequence(n, self.cfg.chaos_rate, self._rng)
                    merged = _chaos_merge(seeds_a[0], seeds_b[0], iter_chaos, self._dist_matrix, self._rng)
                    child = self._seed_to_full_tour(merged, n)
                elif c_val > 0.3:
                    # OX crossover
                    child_a, child_b = _crossover_ox(parent_a, parent_b, self._rng)
                    child = child_a if self.tour_length(child_a) < self.tour_length(child_b) else child_b
                else:
                    # Mutation (swap or 2-opt)
                    if self._rng.random() > 0.5:
                        n_swaps = max(1, int(n * 0.05))
                        child = _mutate_swap(parent_a, self._rng, n_swaps)
                    else:
                        child = _mutate_2opt(parent_a, self._rng)

                # Local search refinement (lightweight)
                child, _, _ = MultiLayerLS.improve(child, self._dist_matrix, dm_np=None, intensity="light", time_limit=self.cfg.ls_time_limit, three_opt_window=self.cfg.three_opt_window)
                child_cost = self.tour_length(child)

                new_population.append(child)
                fitness[i - 1] = child_cost  # Will be recalculated next iteration

            population = new_population
            fitness = [self.tour_length(t) for t in population]

            # Update best
            iter_best = min(fitness)
            if iter_best < best_cost:
                best_idx = fitness.index(iter_best)
                best_tour = population[best_idx][:]
                best_cost = iter_best

            history.append(best_cost)

            # Chaos-guided perturbation on best if stagnation
            if iteration > 0 and abs(history[-1] - history[-2]) < 1e-6:
                # Stagnation: apply chaos-based perturbation
                perturbed = _mutate_swap(best_tour, self._rng, max(1, int(n * 0.1)))
                perturbed, _, _ = MultiLayerLS.improve(perturbed, self._dist_matrix, dm_np=None, intensity="light", time_limit=self.cfg.ls_time_limit, three_opt_window=self.cfg.three_opt_window)
                perturbed_cost = self.tour_length(perturbed)
                if perturbed_cost <= best_cost:
                    best_tour = perturbed[:]
                    best_cost = perturbed_cost

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        return TSPResult(
            algorithm=self.name,
            tour=best_tour,
            tour_length=best_cost,
            elapsed_ms=elapsed_ms,
            iterations=len(history) - 1,
            params={
                "population_size": self.cfg.population_size,
                "max_iterations": self.cfg.max_iterations,
                "chaos_rate": self.cfg.chaos_rate,
            },
            history=history,
            seed=self.cfg.seed,
        )
