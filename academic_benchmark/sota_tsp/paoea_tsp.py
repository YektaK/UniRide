"""
P-AOEA-TSP — Production Adaptive Operator Evolution Algorithm (TSP variant)

Adapted from optimizer_api/strategies/sota_common/paoea.py for pure TSP.
Uses integer-indexed tours and Numba-accelerated distance matrix.

Core DNA:
  - Operator genomes: each individual carries a genome encoding which
    destroy/repair/acceptance operators to use
  - Genomes evolve via tournament selection, crossover, and mutation
  - Adaptive destroy intensity: broad exploration early, fine-tuning late
  - Structured genome injection (mutations of best + random)
  - SA/LAHC/RTR acceptance criteria
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base_solver import BaseTSPSolver, TSPResult
from .ls_engine import MultiLayerLS, improve_2opt, _tour_cost
from .destroy_ops import RandomRemoval, WorstRemoval, ShawRemoval, RelatedRemoval
from .repair_ops import GreedyInsertion, Regret2Insertion, Regret3Insertion

from academic_benchmark.benchmark_utils import compute_population_diversity


@dataclass
class OperatorGenome:
    destroy_ops: List[str] = field(default_factory=lambda: ["random", "worst"])
    repair_ops: List[str] = field(default_factory=lambda: ["greedy", "regret2"])
    acceptance_type: str = "sa"
    destroy_weights: List[float] = field(default_factory=lambda: [1.0, 1.0])
    repair_weights: List[float] = field(default_factory=lambda: [1.0, 1.0])
    ls_intensity: str = "light"
    fitness: float = 0.0
    success_count: int = 0
    total_trials: int = 0

    def success_rate(self) -> float:
        return self.success_count / self.total_trials if self.total_trials > 0 else 0.0

    def record_trial(self, improved: bool):
        self.total_trials += 1
        if improved:
            self.success_count += 1
            self.fitness += 1.0

    def select_destroy(self, rng: random.Random) -> str:
        if not self.destroy_ops:
            return "random"
        total = sum(self.destroy_weights[:len(self.destroy_ops)])
        if total < 1e-12:
            return rng.choice(self.destroy_ops)
        weights = [w / total for w in self.destroy_weights[:len(self.destroy_ops)]]
        return rng.choices(self.destroy_ops, weights=weights, k=1)[0]

    def select_repair(self, rng: random.Random) -> str:
        if not self.repair_ops:
            return "greedy"
        total = sum(self.repair_weights[:len(self.repair_ops)])
        if total < 1e-12:
            return rng.choice(self.repair_ops)
        weights = [w / total for w in self.repair_weights[:len(self.repair_ops)]]
        return rng.choices(self.repair_ops, weights=weights, k=1)[0]

    def copy(self) -> "OperatorGenome":
        return OperatorGenome(
            destroy_ops=self.destroy_ops[:], repair_ops=self.repair_ops[:],
            acceptance_type=self.acceptance_type,
            destroy_weights=self.destroy_weights[:], repair_weights=self.repair_weights[:],
            ls_intensity=self.ls_intensity, fitness=self.fitness,
            success_count=self.success_count, total_trials=self.total_trials)


@dataclass
class PAOEAConfig:
    population_size: int = 50
    max_iterations: int = 500
    genome_population_size: int = 10
    meta_evolution_interval: int = 50
    tournament_size: int = 3
    crossover_rate: float = 0.7
    mutation_rate: float = 0.3
    genome_injection_rate: float = 0.2
    destroy_ops_pool: Tuple[str, ...] = ("random", "worst", "shaw", "related")
    repair_ops_pool: Tuple[str, ...] = ("greedy", "regret2", "regret3")
    acceptance_types: Tuple[str, ...] = ("sa", "lahc")
    ls_time_limit: float = 0.5
    remove_ratio_range: Tuple[float, float] = (0.10, 0.30)
    sa_start_temp_factor: float = 0.4
    sa_end_temp: float = 0.0001
    sa_cooling_rate: float = 0.9995
    diversity_check_interval: int = 50
    entropy_threshold: float = 0.15
    diversity_injection_rate: float = 0.2
    seed: int = 42


_DESTROY_MAP = {"random": RandomRemoval, "worst": WorstRemoval, "shaw": ShawRemoval, "related": RelatedRemoval}
_REPAIR_MAP = {"greedy": GreedyInsertion, "regret2": Regret2Insertion, "regret3": Regret3Insertion}


class _LAHC:
    def __init__(self, history_length: int = 100):
        self._history = [float("inf")] * history_length
        self._pos = 0

    def decide(self, current: float, new_cost: float) -> bool:
        if new_cost < current:
            return True
        if new_cost <= self._history[self._pos % len(self._history)]:
            return True
        return False

    def update(self, cost: float):
        self._history[self._pos % len(self._history)] = cost
        self._pos += 1


class _SA:
    def __init__(self, start_temp: float, end_temp: float, cooling_rate: float):
        self._temp = start_temp
        self._end = end_temp
        self._cooling = cooling_rate

    def decide(self, current: float, new_cost: float, rng: random.Random) -> bool:
        if new_cost < current:
            return True
        if self._temp < 1e-12:
            return False
        return rng.random() < math.exp(-(new_cost - current) / self._temp)

    def cool(self):
        self._temp = max(self._end, self._temp * self._cooling)


class PAOEA_TSP(BaseTSPSolver):

    def __init__(self, config: Optional[PAOEAConfig] = None):
        super().__init__("P-AOEA-TSP", config.seed if config else 42)
        self.cfg = config or PAOEAConfig()

    def _random_genome(self, rng: random.Random) -> OperatorGenome:
        n_d = rng.randint(1, min(3, len(self.cfg.destroy_ops_pool)))
        n_r = rng.randint(1, min(3, len(self.cfg.repair_ops_pool)))
        return OperatorGenome(
            destroy_ops=rng.sample(self.cfg.destroy_ops_pool, n_d),
            repair_ops=rng.sample(self.cfg.repair_ops_pool, n_r),
            acceptance_type=rng.choice(self.cfg.acceptance_types),
            destroy_weights=[rng.random() + 0.1 for _ in range(n_d)],
            repair_weights=[rng.random() + 0.1 for _ in range(n_r)],
            ls_intensity=rng.choice(["light", "moderate"]),
        )

    def _init_population(self, rng: random.Random) -> List[List[int]]:
        pop = []
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None
        for i in range(self.cfg.population_size):
            tour = list(range(self._n))
            rng.shuffle(tour)
            tour, _ = improve_2opt(tour, self._dist_matrix, dm_np, 30, True)
            pop.append(tour)
        return pop

    def _init_genomes(self, rng: random.Random) -> List[OperatorGenome]:
        return [self._random_genome(rng) for _ in range(self.cfg.genome_population_size)]

    def _apply_genome(self, tour: List[int], genome: OperatorGenome,
                      destroy_intensity: float, rng: random.Random) -> Tuple[List[int], float]:
        d_name = genome.select_destroy(rng)
        r_name = genome.select_repair(rng)
        destroyer_cls = _DESTROY_MAP.get(d_name, RandomRemoval)
        repairer_cls = _REPAIR_MAP.get(r_name, GreedyInsertion)
        destroyer = destroyer_cls()
        repairer = repairer_cls()
        n_remove = max(2, int(self._n * destroy_intensity))
        removed, remaining = destroyer.destroy(tour, n_remove, rng, self._dist_matrix)
        repaired = repairer.repair(remaining, removed, self._dist_matrix)
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None
        repaired, cost, _ = MultiLayerLS.improve(repaired, self._dist_matrix, dm_np,
                                                  genome.ls_intensity, 100, self.cfg.ls_time_limit)
        return repaired, cost

    def _evolve_genomes(self, genomes: List[OperatorGenome], rng: random.Random) -> List[OperatorGenome]:
        if len(genomes) < 2:
            return genomes
        scored = sorted(genomes, key=lambda g: g.fitness, reverse=True)
        new_genomes = list(scored[:max(2, len(scored) // 3)])
        while len(new_genomes) < self.cfg.genome_population_size:
            if rng.random() < self.cfg.crossover_rate and len(scored) >= 2:
                p1, p2 = rng.sample(scored[:max(2, len(scored) // 2)], 2)
                child = OperatorGenome(
                    destroy_ops=p1.destroy_ops[:max(1, len(p1.destroy_ops) // 2)] + p2.destroy_ops[max(1, len(p2.destroy_ops) // 2):],
                    repair_ops=p1.repair_ops[:max(1, len(p1.repair_ops) // 2)] + p2.repair_ops[max(1, len(p2.repair_ops) // 2):],
                    acceptance_type=rng.choice([p1.acceptance_type, p2.acceptance_type]),
                    ls_intensity=rng.choice([p1.ls_intensity, p2.ls_intensity]),
                )
                child.destroy_weights = [1.0] * len(child.destroy_ops)
                child.repair_weights = [1.0] * len(child.repair_ops)
            else:
                child = self._random_genome(rng)
            if rng.random() < self.cfg.mutation_rate:
                n_select = rng.randint(1, len(self.cfg.destroy_ops_pool))
                child.destroy_ops = list(rng.sample(self.cfg.destroy_ops_pool, n_select))
                child.destroy_weights = [1.0] * len(child.destroy_ops)
            if rng.random() < self.cfg.mutation_rate:
                child.acceptance_type = rng.choice(self.cfg.acceptance_types)
            new_genomes.append(child)
        return new_genomes[:self.cfg.genome_population_size]

    def _inject_diversity(self, population: List[List[int]], pop_costs: List[float],
                          rng: random.Random) -> Tuple[List[List[int]], List[float]]:
        n_inject = max(1, int(self.cfg.diversity_injection_rate * len(population)))
        worst = sorted(range(len(pop_costs)), key=lambda i: pop_costs[i], reverse=True)[:n_inject]
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None
        for idx in worst:
            tour = list(range(self._n))
            rng.shuffle(tour)
            tour, _ = improve_2opt(tour, self._dist_matrix, dm_np, 50, True)
            population[idx] = tour
            pop_costs[idx] = _tour_cost(tour, self._dist_matrix)
        return population, pop_costs

    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        rng = random.Random(self.cfg.seed)
        t_start = time.monotonic()
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None

        population = self._init_population(rng)
        pop_costs = [_tour_cost(t, self._dist_matrix) for t in population]
        genomes = self._init_genomes(rng)

        gbest_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
        gbest = list(population[gbest_idx])
        gbest_cost = pop_costs[gbest_idx]

        sa = _SA(gbest_cost * self.cfg.sa_start_temp_factor,
                 self.cfg.sa_end_temp, self.cfg.sa_cooling_rate)
        lahc = _LAHC(100)

        history: List[float] = []
        genome_assignments = [rng.choice(genomes) for _ in range(len(population))]

        for t in range(1, self.cfg.max_iterations + 1):
            progress = t / self.cfg.max_iterations
            destroy_intensity = 0.30 * (1 - progress) + 0.10 * progress

            for i in range(len(population)):
                genome = genome_assignments[i]
                child, child_cost = self._apply_genome(population[i], genome, destroy_intensity, rng)
                if genome.acceptance_type == "sa":
                    accepted = sa.decide(pop_costs[i], child_cost, rng)
                else:
                    accepted = lahc.decide(pop_costs[i], child_cost)
                improved = child_cost < pop_costs[i] - 1e-10
                genome.record_trial(improved)
                if accepted:
                    population[i] = child
                    pop_costs[i] = child_cost

            sa.cool()
            lahc.update(min(pop_costs))

            best_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
            if pop_costs[best_idx] < gbest_cost - 1e-10:
                gbest = list(population[best_idx])
                gbest_cost = pop_costs[best_idx]

            if t % self.cfg.meta_evolution_interval == 0:
                genomes = self._evolve_genomes(genomes, rng)
                genome_assignments = [rng.choice(genomes) for _ in range(len(population))]

            if t % self.cfg.diversity_check_interval == 0:
                diversity = compute_population_diversity(population, self._n)
                if diversity < self.cfg.entropy_threshold:
                    population, pop_costs = self._inject_diversity(population, pop_costs, rng)

            history.append(gbest_cost)
            if time.monotonic() - t_start > 300:
                break

        gbest, gbest_cost, _ = MultiLayerLS.improve(gbest, self._dist_matrix, dm_np, "full", 500, 5.0)

        elapsed_ms = (time.monotonic() - t_start) * 1000
        return TSPResult(
            algorithm="P-AOEA-TSP",
            tour=gbest,
            tour_length=gbest_cost,
            elapsed_ms=elapsed_ms,
            iterations=t,
            params={"population_size": self.cfg.population_size, "genomes": self.cfg.genome_population_size},
            history=history,
            seed=self.cfg.seed,
        )
