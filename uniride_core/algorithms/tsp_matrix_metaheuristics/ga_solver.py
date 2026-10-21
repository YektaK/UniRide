"""
Canonical pure Genetic Algorithm for TSP/ATSP (C-16a)

Reference:
Holland, J. H. (1975). Adaptation in Natural and Artificial Systems.
Goldberg, D. E. (1989). Genetic Algorithms in Search, Optimization, and
Machine Learning.

Operators (tournament selection, order crossover, swap/inversion mutation, elitism)
follow the archived Bildiri GA as a reference only. Unlike that GA this solver has
NO local search: there is no 2-opt on the initial population and no final 2-opt. The
memetic variant is a separate algorithm identity (C-16c, ``polish_enabled=True``) built on
the same hooks; with ``polish_enabled=False`` (the default) nothing below changes.

Objective accounting (fairness design, atomic phases):
- population initialization is one atomic phase of ``population_size`` evaluations;
- each generation is one atomic phase of ``population_size - elite_count`` offspring
  evaluations (the elites keep their cached cost and are not re-evaluated), started
  only when that exact upper bound fits the remaining budget;
- native mode uses ``ObjectiveEvaluationBudget(None)`` and reports the actual count.

Memetic option (C-16c, every polish evaluation goes through the same counter):
- after the atomic population phase, each chromosome gets a budgeted 2-opt with its known
  cost (``initial_polish_iters``), one unit per candidate tour; the polish stops without
  overshoot when the budget ends and the run then terminates normally;
- after the generations, the best chromosome gets one budgeted 2-opt with its known cost
  (``final_polish_iters``), also stopping without overshoot;
- there is no periodic polish; ``polish_executed``/``polish_evaluations`` report the work done.

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
from uniride_core.algorithms.objective_budget import (
    BudgetedSearchResult,
    ObjectiveEvaluationBudget,
    improve_two_opt_budgeted,
)


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
        polish_enabled: bool = False,
        initial_polish_iters: int = 0,
        final_polish_iters: int = 0,
    ):
        super().__init__("GA", random_seed)
        if population_size < 2:
            raise ValueError("GA population_size must be at least 2")
        if not 0 <= elite_count < population_size:
            raise ValueError("GA elite_count must satisfy 0 <= elite_count < population_size")
        if tournament_size < 1:
            raise ValueError("GA tournament_size must be at least 1")
        if polish_enabled and initial_polish_iters <= 0 and final_polish_iters <= 0:
            raise ValueError(
                "a memetic GA needs a positive initial_polish_iters or final_polish_iters"
            )
        self.polish_enabled = bool(polish_enabled)
        self.initial_polish_iters = int(initial_polish_iters)
        self.final_polish_iters = int(final_polish_iters)
        self._polish_executed = {"initial": 0, "periodic": 0, "final": 0}
        self._polish_evaluations = {"initial": 0, "periodic": 0, "final": 0}
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
        self._polish_executed = {"initial": 0, "periodic": 0, "final": 0}
        self._polish_evaluations = {"initial": 0, "periodic": 0, "final": 0}
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

    def _two_opt(
        self, route: List[int], known_cost: float, iters: int, phase: str
    ) -> Optional[BudgetedSearchResult]:
        """Budgeted 2-opt from a tour whose cost is already counted (not re-counted).

        Returns ``None`` when the budget cannot pay for even one candidate tour, so a
        polish that never started is not reported as executed.
        """
        if not self._objective_budget.can_spend():
            return None
        result = improve_two_opt_budgeted(
            route, self._dist_matrix, self._objective_budget,
            max_iterations=iters, first_improvement=False, initial_cost=known_cost,
        )
        self._polish_executed[phase] += 1
        self._polish_evaluations[phase] += result.evaluations
        self._backend_observation.polish.add("python")
        return result

    def polish_initial_population(self, population: List[Individual]) -> bool:
        """Initial 2-opt on every chromosome (list order); True when the budget ended.

        ``population`` is re-sorted by ``tour_length`` afterwards.
        """
        exhausted = False
        for individual in population:
            result = self._two_opt(
                individual.chromosome, individual.tour_length,
                self.initial_polish_iters, "initial",
            )
            if result is None:
                exhausted = True
                break
            individual.chromosome = list(result.route)
            individual.tour_length = float(result.cost)
            individual.fitness = 1.0 / (individual.tour_length + 1e-10)
            if result.budget_exhausted:
                exhausted = True
                break
        population.sort(key=lambda x: x.tour_length)
        return exhausted

    def polish_best(
        self, chromosome: List[int], known_cost: float
    ) -> Tuple[List[int], float, bool]:
        """Final 2-opt on the best chromosome with its known cost; (route, cost, exhausted)."""
        result = self._two_opt(chromosome, known_cost, self.final_polish_iters, "final")
        if result is None:
            return chromosome, known_cost, True
        return list(result.route), float(result.cost), result.budget_exhausted

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
        if self.polish_enabled and self.initial_polish_iters > 0:
            self.polish_initial_population(pop)
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
        if self.polish_enabled and self.final_polish_iters > 0:
            best_chrom, best_len, polish_exhausted = self.polish_best(best_chrom, best_len)
            if polish_exhausted:
                termination_reason = "evaluation_budget_exhausted"
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
                "memetic": self.polish_enabled,
                "initial_polish_iters": self.initial_polish_iters,
                "final_polish_iters": self.final_polish_iters,
            },
            extra_stats={
                "objective_evaluations": self._objective_budget.used,
                "evaluation_budget": self._objective_budget.limit,
                "budget_terminated": termination_reason == "evaluation_budget_exhausted",
                "termination_reason": termination_reason,
                "variant": "memetic_2opt" if self.polish_enabled else "pure",
                "polish_executed": dict(self._polish_executed),
                # Memetic polish is always counted (budgeted Python 2-opt, also in native
                # mode with an unlimited counter); the pure GA keeps its historical shape.
                "polish_evaluations": (
                    dict(self._polish_evaluations)
                    if (self._fair_mode or self.polish_enabled) else None
                ),
                "execution_backend": self._backend_observation.label(),
            },
            history=history,
            seed=self.random_seed,
        )
