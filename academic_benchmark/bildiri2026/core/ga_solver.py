
"""
Genetic Algorithm for TSP

Reference:
Holland, J. H. (1975). Adaptation in Natural and Artificial Systems.
University of Michigan Press.

Goldberg, D. E. (1989). Genetic Algorithms in Search, Optimization,
and Machine Learning. Addison-Wesley.

Hybrid GA:
- 2-opt on initial population + final result only
- Keeps runtime reasonable
"""

import time
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .base_solver import BaseTSPSolver, TSPResult


@dataclass
class Individual:
    chromosome: List[int]
    fitness: float
    tour_length: float


class GAOptimizer(BaseTSPSolver):
    def __init__(
        self,
        population_size: int = 100,
        generations: int = 500,
        crossover_rate: float = 0.85,
        mutation_rate: float = 0.15,
        elite_count: int = 2,
        tournament_size: int = 3,
        max_no_improvement: int = 100,
        random_seed: Optional[int] = None,
    ):
        super().__init__("GA", random_seed)
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count
        self.tournament_size = tournament_size
        self.max_no_improvement = max_no_improvement
        self._rng = random.Random(self.random_seed)

    def _two_opt_fast(self, tour: List[int], max_iter: int = 200) -> Tuple[List[int], float]:
        best = tour[:]
        best_len = self.tour_length(best)
        improved = True
        itr = 0
        n = len(best)
        while improved and itr < max_iter and n > 3:
            improved = False
            for i in range(n - 1):
                for j in range(i + 2, n):
                    new_tour = best[:i + 1] + best[i + 1:j + 1][::-1] + best[j + 1:]
                    new_len = self.tour_length(new_tour)
                    if new_len < best_len:
                        best = new_tour
                        best_len = new_len
                        improved = True
                        break
                if improved:
                    break
            itr += 1
        return best, best_len

    def _init_population(self) -> List[Individual]:
        pop = []
        base = self._initial_tour_nodes()
        for _ in range(self.population_size):
            perm = base[:]
            self._rng.shuffle(perm)
            # Only 10 iters on init to save time
            perm, length = self._two_opt_fast(perm, max_iter=10)
            pop.append(Individual(perm, 1.0 / (length + 1e-10), length))
        return pop

    def _tournament(self, pop: List[Individual]) -> Individual:
        k = min(self.tournament_size, len(pop))
        return min(self._rng.sample(pop, k), key=lambda x: x.tour_length)

    def _ox(self, p1: List[int], p2: List[int]) -> List[int]:
        sz = len(p1)
        if sz < 2:
            return p1[:]
        a, b = sorted(self._rng.sample(range(sz), 2))
        child = [None] * sz
        child[a:b] = p1[a:b]
        segment = set(child[a:b])
        idx = b % sz
        for gene in p2:
            if gene not in segment:
                while child[idx] is not None:
                    idx = (idx + 1) % sz
                child[idx] = gene
        return child  # type: ignore

    def _mutate(self, chrom: List[int]) -> List[int]:
        c = chrom[:]
        if self._rng.random() < 0.5:
            i, j = self._rng.sample(range(len(c)), 2)
            c[i], c[j] = c[j], c[i]
        else:
            i, j = sorted(self._rng.sample(range(len(c)), 2))
            c[i:j + 1] = reversed(c[i:j + 1])
        return c

    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        t0 = time.perf_counter()

        pop = self._init_population()
        pop.sort(key=lambda x: x.tour_length)

        best_len = pop[0].tour_length
        best_chrom = pop[0].chromosome[:]
        no_improve = 0

        for gen in range(self.generations):
            pop.sort(key=lambda x: x.tour_length)

            if pop[0].tour_length < best_len:
                best_len = pop[0].tour_length
                best_chrom = pop[0].chromosome[:]
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= self.max_no_improvement:
                break

            new_pop = []
            # Elites carried forward
            new_pop.extend(Individual(e.chromosome[:], e.fitness, e.tour_length) for e in pop[:self.elite_count])

            while len(new_pop) < self.population_size:
                p1 = self._tournament(pop)
                p2 = self._tournament(pop)
                child = self._ox(p1.chromosome, p2.chromosome) if self._rng.random() < self.crossover_rate else p1.chromosome[:]
                if self._rng.random() < self.mutation_rate:
                    child = self._mutate(child)
                clen = self.tour_length(child)
                new_pop.append(Individual(child, 1.0 / (clen + 1e-10), clen))

            pop = new_pop

        # Final aggressive 2-opt on best
        best_chrom, best_len = self._two_opt_fast(best_chrom, max_iter=300)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="GA",
            tour=best_chrom,
            tour_length=best_len,
            elapsed_ms=elapsed_ms,
            iterations=gen + 1,
            params={
                "population_size": self.population_size,
                "generations": gen + 1,
                "crossover_rate": self.crossover_rate,
                "mutation_rate": self.mutation_rate,
                "elite_count": self.elite_count,
                "hybrid_2opt": True,
            },
            seed=self.random_seed,
        )
