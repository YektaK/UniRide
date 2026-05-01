"""
R²DMA-TSP — Resonance-Reinforced Destroy-and-Merge Algorithm (TSP variant)

Adapted from optimizer_api/strategies/sota_common/r2dma.py for pure TSP.
Uses integer-indexed tours and Numba-accelerated distance matrix.

Core DNA:
  - 6-dim resonance metric between solution pairs (edge overlap, segment similarity)
  - 3-mode crossover: CONSTRUCTIVE (R>=0.7) / MODERATE (0.3<=R<0.7) / DESTRUCTIVE (R<0.3)
  - OX crossover for moderate mode
  - ALNS destroy/repair for destructive mode
  - SA acceptance with dissonance filter
  - Adaptive theta threshold (success-rate tracking in segments)
  - Diversity pulse injection on entropy drop
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


@dataclass
class R2DMATSPConfig:
    population_size: int = 60
    max_iterations: int = 500
    theta_base: float = 0.5
    segment_size: int = 50
    remove_ratio: float = 0.20
    ls_intensity_constructive: str = "moderate"
    ls_intensity_moderate: str = "light"
    ls_intensity_destructive: str = "moderate"
    ls_time_limit: float = 0.5
    sa_start_temp_factor: float = 0.4
    sa_end_temp: float = 0.0001
    sa_cooling_rate: float = 0.9995
    delta_threshold: float = 0.02
    entropy_threshold: float = 0.15
    pulse_injection_rate: float = 0.25
    diversity_check_interval: int = 50
    seed: int = 42


class _SA:
    def __init__(self, start_temp: float, end_temp: float, cooling_rate: float, max_iter: int):
        self._temp = start_temp
        self._end = end_temp
        self._cooling = cooling_rate
        self._max_iter = max_iter

    def decide(self, current: float, new_cost: float, rng: random.Random) -> bool:
        if new_cost < current:
            return True
        if self._temp < 1e-12:
            return False
        delta = new_cost - current
        prob = math.exp(-delta / self._temp)
        return rng.random() < prob

    def cool(self):
        self._temp *= self._cooling
        if self._temp < self._end:
            self._temp = self._end


def _compute_resonance(t1: List[int], t2: List[int], n: int, dm: Optional[List[List[float]]] = None) -> float:
    # Build undirected edge sets once — O(n) each
    edges1 = set()
    for i in range(n):
        a, b = t1[i], t1[(i + 1) % n]
        edges1.add((min(a, b), max(a, b)))
    edges2 = set()
    for i in range(n):
        a, b = t2[i], t2[(i + 1) % n]
        edges2.add((min(a, b), max(a, b)))
    # Edge similarity: Jaccard on undirected edge sets — O(n)
    common = len(edges1 & edges2)
    total = len(edges1 | edges2)
    edge_sim = common / total if total > 0 else 0.0
    # Position match: fraction of positions with same city — O(n)
    pos_match = sum(1 for i in range(n) if t1[i] == t2[i]) / n if n > 0 else 0.0
    # Distance-profile similarity: compares relative edge lengths of both tours.
    dist_sim = 0.5
    if dm is not None:
        try:
            d1 = [dm[t1[i]][t1[(i + 1) % n]] for i in range(n)]
            d2 = [dm[t2[i]][t2[(i + 1) % n]] for i in range(n)]
            avg1 = sum(d1) / len(d1)
            avg2 = sum(d2) / len(d2)
            if avg1 > 1e-12 and avg2 > 1e-12:
                norm_diff = sum(abs((a / avg1) - (b / avg2)) for a, b in zip(d1, d2)) / n
                dist_sim = max(0.0, 1.0 - norm_diff / 2.0)
        except Exception:
            dist_sim = 0.5
    # Keep primary structure from TSP adaptation while borrowing extra signal from source design.
    return 0.45 * edge_sim + 0.35 * pos_match + 0.20 * dist_sim


class R2DMA_TSP(BaseTSPSolver):

    def __init__(self, config: Optional[R2DMATSPConfig] = None):
        super().__init__("R2DMA-TSP", config.seed if config else 42)
        self.cfg = config or R2DMATSPConfig()

    def _init_population(self, rng: random.Random) -> List[List[int]]:
        pop = []
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None
        for i in range(self.cfg.population_size):
            if i < self.cfg.population_size // 4:
                start = rng.randrange(self._n)
                visited = {start}
                tour = [start]
                for _ in range(self._n - 1):
                    cur = tour[-1]
                    best_j = min((j for j in range(self._n) if j not in visited),
                                 key=lambda j: self._dist_matrix[cur][j])
                    tour.append(best_j)
                    visited.add(best_j)
            else:
                tour = list(range(self._n))
                rng.shuffle(tour)
            tour, _ = improve_2opt(tour, self._dist_matrix, dm_np, 50, True)
            pop.append(tour)
        return pop

    def _ox_crossover(self, p1: List[int], p2: List[int], rng: random.Random) -> List[int]:
        n = len(p1)
        a, b = sorted(rng.sample(range(n), 2))
        child = [None] * n
        child[a:b + 1] = p1[a:b + 1]
        segment = set(child[a:b + 1])
        idx = (b + 1) % n
        for gene in p2:
            if gene not in segment:
                while child[idx] is not None:
                    idx = (idx + 1) % n
                child[idx] = gene
        return child

    def _constructive_crossover(self, p1: List[int], p2: List[int], rng: random.Random) -> List[int]:
        edges1 = set()
        for i in range(len(p1)):
            a, b = p1[i], p1[(i + 1) % len(p1)]
            edges1.add((a, b))
        edges2 = set()
        for i in range(len(p2)):
            a, b = p2[i], p2[(i + 1) % len(p2)]
            edges2.add((a, b))
        common = list(edges1 & edges2)
        rng.shuffle(common)
        if not common:
            return self._ox_crossover(p1, p2, rng)
        adj: Dict[int, List[int]] = {}
        used = set()
        result = []
        for a, b in common:
            if a in used and b in used:
                continue
            if a not in used:
                result.append(a)
                used.add(a)
            if b not in used:
                result.append(b)
                used.add(b)
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        remaining = [x for x in range(self._n) if x not in used]
        rng.shuffle(remaining)
        result.extend(remaining)
        return result

    def _destructive_crossover(self, tour: List[int], rng: random.Random) -> List[int]:
        destroy_ops = [RandomRemoval(), WorstRemoval(), ShawRemoval(), RelatedRemoval()]
        repair_ops = [GreedyInsertion(), Regret2Insertion(), Regret3Insertion()]
        destroyer = rng.choice(destroy_ops)
        repairer = rng.choice(repair_ops)
        n_remove = max(2, int(self._n * self.cfg.remove_ratio))
        removed, remaining = destroyer.destroy(tour, n_remove, rng, self._dist_matrix)
        repaired = repairer.repair(remaining, removed, self._dist_matrix)
        return repaired

    def _perturb(self, tour: List[int], rng: random.Random) -> List[int]:
        result = list(tour)
        n = len(result)
        if n < 4:
            return result
        a, b = rng.sample(range(n), 2)
        result[a], result[b] = result[b], result[a]
        return result

    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        rng = random.Random(self.cfg.seed)
        t_start = time.monotonic()
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None

        population = self._init_population(rng)
        pop_costs = [_tour_cost(t, self._dist_matrix) for t in population]

        gbest_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
        gbest = list(population[gbest_idx])
        gbest_cost = pop_costs[gbest_idx]

        sa = _SA(gbest_cost * self.cfg.sa_start_temp_factor,
                 self.cfg.sa_end_temp, self.cfg.sa_cooling_rate, self.cfg.max_iterations)

        theta = self.cfg.theta_base
        segment_results: List[bool] = []
        history: List[float] = []
        construct_count = moderate_count = destruct_count = 0

        for t in range(1, self.cfg.max_iterations + 1):
            prev_best = gbest_cost
            offspring = []
            offspring_costs = []

            for i in range(len(population)):
                best_partner = None
                best_resonance = -1.0
                for j in range(len(population)):
                    if i == j:
                        continue
                    r = _compute_resonance(population[i], population[j], self._n, self._dist_matrix)
                    if r > best_resonance:
                        best_resonance = r
                        best_partner = j

                if best_partner is None or best_resonance < theta:
                    child = self._perturb(population[i], rng)
                    mode = "perturb"
                elif best_resonance >= 0.7:
                    child = self._constructive_crossover(population[i], population[best_partner], rng)
                    construct_count += 1
                    mode = "constructive"
                elif best_resonance >= 0.3:
                    child = self._ox_crossover(population[i], population[best_partner], rng)
                    moderate_count += 1
                    mode = "moderate"
                else:
                    child = self._destructive_crossover(population[i], rng)
                    destruct_count += 1
                    mode = "destructive"

                child_cost = _tour_cost(child, self._dist_matrix)

                if mode == "constructive":
                    child, child_cost, _ = MultiLayerLS.improve(
                        child, self._dist_matrix, dm_np, self.cfg.ls_intensity_constructive, 200, self.cfg.ls_time_limit)
                elif mode == "moderate":
                    child, child_cost, _ = MultiLayerLS.improve(
                        child, self._dist_matrix, dm_np, self.cfg.ls_intensity_moderate, 100, self.cfg.ls_time_limit)
                elif mode == "destructive":
                    child, child_cost, _ = MultiLayerLS.improve(
                        child, self._dist_matrix, dm_np, self.cfg.ls_intensity_destructive, 200, self.cfg.ls_time_limit)

                worse_parent = max(pop_costs[i], pop_costs[best_partner] if best_partner is not None else pop_costs[i])
                is_dissonant = child_cost > worse_parent * (1 + self.cfg.delta_threshold)
                accepted = sa.decide(pop_costs[i], child_cost, rng) and not is_dissonant

                if accepted:
                    offspring.append(child)
                    offspring_costs.append(child_cost)
                    if mode == "constructive":
                        segment_results.append(child_cost < worse_parent - 1e-10)
                else:
                    offspring.append(list(population[i]))
                    offspring_costs.append(pop_costs[i])

            population = offspring
            pop_costs = offspring_costs

            best_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
            if pop_costs[best_idx] < gbest_cost - 1e-10:
                gbest = list(population[best_idx])
                gbest_cost = pop_costs[best_idx]

            sa.cool()

            if t % self.cfg.segment_size == 0 and segment_results:
                success_rate = sum(segment_results) / len(segment_results)
                if success_rate > 0.6:
                    theta = max(0.2, theta - 0.05)
                elif success_rate < 0.3:
                    theta = min(0.8, theta + 0.05)
                segment_results = []

            if t % self.cfg.diversity_check_interval == 0:
                entropy = 0.0
                for i in range(min(5, len(population))):
                    for j in range(i + 1, min(5, len(population))):
                        common = sum(1 for k in range(self._n)
                                     if population[i][(k + 1) % self._n] == population[j][(k + 1) % self._n])
                        entropy += 1.0 - common / self._n
                if entropy < self.cfg.entropy_threshold:
                    n_inject = max(1, int(self.cfg.pulse_injection_rate * len(population)))
                    worst = sorted(range(len(pop_costs)), key=lambda i: pop_costs[i], reverse=True)[:n_inject]
                    for idx in worst:
                        population[idx] = self._destructive_crossover(population[idx], rng)
                        pop_costs[idx] = _tour_cost(population[idx], self._dist_matrix)

            history.append(gbest_cost)
            if time.monotonic() - t_start > 300:
                break

        gbest, gbest_cost, _ = MultiLayerLS.improve(gbest, self._dist_matrix, dm_np, "full", 500, 5.0)

        elapsed_ms = (time.monotonic() - t_start) * 1000
        return TSPResult(
            algorithm="R2DMA-TSP",
            tour=gbest,
            tour_length=gbest_cost,
            elapsed_ms=elapsed_ms,
            iterations=t,
            params={"population_size": self.cfg.population_size, "constructive": construct_count,
                    "moderate": moderate_count, "destructive": destruct_count},
            history=history,
            seed=self.cfg.seed,
        )
