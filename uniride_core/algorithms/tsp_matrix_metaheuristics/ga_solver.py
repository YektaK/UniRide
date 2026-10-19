"""
Canonical pure Genetic Algorithm for TSP/ATSP (C-16a)

Reference:
Holland, J. H. (1975). Adaptation in Natural and Artificial Systems.
Goldberg, D. E. (1989). Genetic Algorithms in Search, Optimization, and
Machine Learning.

Operators (tournament selection, order crossover, swap/inversion mutation, elitism)
follow the archived Bildiri GA as a reference only. Unlike that GA this solver has
NO local search: there is no 2-opt on the initial population and no final 2-opt. The
memetic variant is a separate algorithm identity (C-16c) and reuses the hooks below.

Objective accounting (fairness design, atomic phases):
- population initialization is one atomic phase of ``population_size`` evaluations;
- each generation is one atomic phase of ``population_size - elite_count`` offspring
  evaluations (the elites keep their cached cost and are not re-evaluated), started
  only when that exact upper bound fits the remaining budget;
- native mode uses ``ObjectiveEvaluationBudget(None)`` and reports the actual count.

Termination reasons: ``evaluation_budget_exhausted``, ``max_iterations``,
``max_no_improvement``.

Hooks reused by C-16c: :meth:`begin_run`, :meth:`initialize_population`,
:meth:`generation_evaluation_bound`, :meth:`breed_generation`, :meth:`best_of`.
"""

import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .base_solver import BaseTSPSolver, TSPResult
from uniride_core.algorithms.objective_budget import ObjectiveEvaluationBudget


@dataclass
class Individual:
    chromosome: List[int]
    fitness: float
    tour_length: float


class GAOptimizer(BaseTSPSolver):
    """Pure generational elitist GA with exact objective-evaluation accounting."""

    def __init__(
        self,
        population_size: int = 100,
        max_iterations: int = 500,
        crossover_rate: float = 0.85,
        mutation_rate: float = 0.15,
        elite_count: int = 2,
        tournament_size: int = 3,
        max_no_improvement: int = 100,
        random_seed: Optional[int] = None,
        evaluation_budget: Optional[int] = None,
    ):
        super().__init__("GA", random_seed)
        if population_size < 2:
            raise ValueError("GA population_size must be at least 2")
        if not 0 <= elite_count < population_size:
            raise ValueError("GA elite_count must satisfy 0 <= elite_count < population_size")
        if tournament_size < 1:
            raise ValueError("GA tournament_size must be at least 1")
        self.population_size = population_size
        self.max_iterations = max_iterations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count
        self.tournament_size = tournament_size
        self.max_no_improvement = max_no_improvement
        self._rng = random.Random(self.random_seed)
        self._fair_mode = evaluation_budget is not None
        self._objective_budget = ObjectiveEvaluationBudget(evaluation_budget)

    # ----- Accounted evaluation ------------------------------------
    def _evaluate(self, route: List[int]) -> float:
        self._objective_budget.consume()
        return self._tour_length_fast(route)

    # ----- Operators ------------------------------------------------
    def _tournament(self, pop: List[Individual]) -> Individual:
        k = min(self.tournament_size, len(pop))
        return min(self._rng.sample(pop, k), key=lambda x: x.tour_length)

    def _ox(self, p1: List[int], p2: List[int]) -> List[int]:
        sz = len(p1)
        if sz < 2:
            return p1[:]
        a, b = sorted(self._rng.sample(range(sz), 2))
        child: List[Optional[int]] = [None] * sz
        child[a:b] = p1[a:b]
        segment = set(p1[a:b])
        idx = b % sz
        for gene in p2:
            if gene not in segment:
                while child[idx] is not None:
                    idx = (idx + 1) % sz
                child[idx] = gene
        return child  # type: ignore[return-value]

    def _mutate(self, chrom: List[int]) -> List[int]:
        c = chrom[:]
        if len(c) < 2:
            return c
        if self._rng.random() < 0.5:
            i, j = self._rng.sample(range(len(c)), 2)
            c[i], c[j] = c[j], c[i]
        else:
            i, j = sorted(self._rng.sample(range(len(c)), 2))
            c[i:j + 1] = reversed(c[i:j + 1])
        return c

    # ----- Hooks (C-16c reuses these without copying) --------------
    def begin_run(self, coordinates: List[Tuple[float, float]]) -> None:
        """Reset the per-run state and load the problem."""
        self._backend_observation.reset()
        self._rng = random.Random(self.random_seed)
        self._objective_budget.used = 0
        self._set_problem(coordinates)

    def initialization_evaluation_bound(self) -> int:
        """Exact evaluations of the atomic population-initialization phase."""
        return self.population_size

    def generation_evaluation_bound(self) -> int:
        """Exact evaluations of one atomic generation phase (the offspring)."""
        return self.population_size - self.elite_count

    def initialize_population(self) -> List[Individual]:
        """Random permutation population, one evaluation per individual, sorted."""
        base = self._initial_tour_nodes()
        pop: List[Individual] = []
        for _ in range(self.population_size):
            perm = base[:]
            self._rng.shuffle(perm)
            length = self._evaluate(perm)
            pop.append(Individual(perm, 1.0 / (length + 1e-10), length))
        pop.sort(key=lambda x: x.tour_length)
        return pop

    def breed_generation(self, population: List[Individual]) -> List[Individual]:
        """Elites carried over uncounted, then offspring evaluated one by one.

        ``population`` must be sorted by ``tour_length``; the result is sorted too.
        """
        new_pop = [
            Individual(e.chromosome[:], e.fitness, e.tour_length)
            for e in population[: self.elite_count]
        ]
        while len(new_pop) < self.population_size:
            p1 = self._tournament(population)
            p2 = self._tournament(population)
            child = (
                self._ox(p1.chromosome, p2.chromosome)
                if self._rng.random() < self.crossover_rate
                else p1.chromosome[:]
            )
            if self._rng.random() < self.mutation_rate:
                child = self._mutate(child)
            clen = self._evaluate(child)
            new_pop.append(Individual(child, 1.0 / (clen + 1e-10), clen))
        new_pop.sort(key=lambda x: x.tour_length)
        return new_pop

    @staticmethod
    def best_of(population: List[Individual]) -> Individual:
        """The best individual (lowest tour length) of a population."""
        return min(population, key=lambda x: x.tour_length)

    # ----- Main solve ----------------------------------------------
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self.begin_run(coordinates)
        t0 = time.perf_counter()

        if self._fair_mode:
            init_required = self.initialization_evaluation_bound()
            if not self._objective_budget.can_spend(init_required):
                raise ValueError(
                    "fair GA budget cannot complete atomic population initialization: "
                    f"required_upper_bound={init_required}, "
                    f"budget={self._objective_budget.limit}"
                )

        pop = self.initialize_population()
        best = self.best_of(pop)
        best_len = best.tour_length
        best_chrom = best.chromosome[:]
        no_improve = 0
        history: List[float] = []
        iterations_completed = 0
        termination_reason = "max_iterations"
        phase_evaluations = self.generation_evaluation_bound()

        for _ in range(self.max_iterations):
            if not self._objective_budget.can_spend(phase_evaluations):
                termination_reason = "evaluation_budget_exhausted"
                break
            history.append(float(best_len))
            pop = self.breed_generation(pop)
            iterations_completed += 1
            if pop[0].tour_length < best_len:
                best_len = pop[0].tour_length
                best_chrom = pop[0].chromosome[:]
                no_improve = 0
            else:
                no_improve += 1
            if no_improve >= self.max_no_improvement:
                termination_reason = "max_no_improvement"
                break
        history.append(float(best_len))

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="GA",
            tour=best_chrom,
            tour_length=best_len,
            elapsed_ms=elapsed_ms,
            iterations=iterations_completed,
            params={
                "population_size": self.population_size,
                "generations": iterations_completed,
                "crossover_rate": self.crossover_rate,
                "mutation_rate": self.mutation_rate,
                "elite_count": self.elite_count,
                "tournament_size": self.tournament_size,
                "memetic": False,
            },
            extra_stats={
                "objective_evaluations": self._objective_budget.used,
                "evaluation_budget": self._objective_budget.limit,
                "budget_terminated": termination_reason == "evaluation_budget_exhausted",
                "termination_reason": termination_reason,
                "variant": "pure",
                "polish_executed": {"initial": 0, "periodic": 0, "final": 0},
                "polish_evaluations": (
                    {"initial": 0, "periodic": 0, "final": 0} if self._fair_mode else None
                ),
                "execution_backend": self._backend_observation.label(),
            },
            history=history,
            seed=self.random_seed,
        )
