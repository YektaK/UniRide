"""
E²BSO-TSP — Enhanced Entropy-Balanced Swarm Optimization (TSP variant)

Adapted from optimizer_api/strategies/sota_common/e2bso.py for pure TSP.
Uses integer-indexed tours and Numba-accelerated distance matrix.

Core DNA:
  - Edge-based Shannon entropy for population diversity measurement
  - 3-phase adaptive: INJECT (low entropy) / NORMAL / COMPRESS (high entropy)
  - ALNS destroy/repair for diversity injection
  - Multi-layer local search (2-opt, or-opt)
  - LAHC acceptance criterion
  - Adaptive entropy thresholds (learning period + cooling schedule)
"""

import math
import random
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base_solver import BaseTSPSolver, TSPResult
from .ls_engine import MultiLayerLS, improve_2opt, _tour_cost
from .destroy_ops import RandomRemoval, WorstRemoval, ShawRemoval
from .repair_ops import GreedyInsertion, Regret2Insertion, Regret3Insertion

from academic_benchmark.benchmark_utils import compute_population_diversity


@dataclass
class E2BSOTSPConfig:
    population_size: int = 40
    max_iterations: int = 500
    h_start: float = 0.8
    h_end: float = 0.2
    gamma: float = 0.5
    entropy_check_interval: int = 10
    ls_intensity_normal: str = "light"
    ls_intensity_compress: str = "moderate"
    ls_time_limit: float = 0.5
    lahc_history: int = 200
    diversity_threshold: float = 0.3
    diversity_check_interval: int = 50
    injection_rate: float = 0.2
    learn_period: int = 100
    p_best: float = 0.3
    p_gbest: float = 0.4
    n_edges_normal: int = 3
    n_edges_aggressive: int = 5
    remove_ratio: float = 0.20
    seed: int = 42


class _LAHC:
    def __init__(self, history_length: int = 200):
        self._history: List[float] = [float("inf")] * history_length
        self._pos = 0
        self._warmup = 0

    def decide(self, current_cost: float, new_cost: float, iteration: int, rng: random.Random) -> bool:
        if new_cost < current_cost:
            return True
        idx = self._pos % len(self._history)
        if new_cost <= self._history[idx]:
            return True
        return False

    def update(self, cost: float):
        self._history[self._pos % len(self._history)] = cost
        self._pos += 1


class E2BSO_TSP(BaseTSPSolver):

    def __init__(self, config: Optional[E2BSOTSPConfig] = None):
        super().__init__("E2BSO-TSP", config.seed if config else 42)
        self.cfg = config or E2BSOTSPConfig()

    def _edge_entropy(self, population: List[List[int]]) -> float:
        n = len(population[0]) if population else 0
        if n < 2:
            return 0.0
        edge_count: Dict[Tuple[int, int], int] = {}
        total_edges = 0
        for tour in population:
            for i in range(len(tour)):
                a, b = tour[i], tour[(i + 1) % len(tour)]
                edge = (min(a, b), max(a, b))
                edge_count[edge] = edge_count.get(edge, 0) + 1
                total_edges += 1
        if total_edges == 0:
            return 0.0
        entropy = 0.0
        for count in edge_count.values():
            p = count / total_edges
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(total_edges) if total_edges > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _random_tour(self, rng: random.Random) -> List[int]:
        nodes = list(range(self._n))
        rng.shuffle(nodes)
        return nodes

    def _nn_tour(self, rng: random.Random) -> List[int]:
        start = rng.randrange(self._n)
        visited = {start}
        tour = [start]
        for _ in range(self._n - 1):
            current = tour[-1]
            best_next = -1
            best_dist = float("inf")
            for j in range(self._n):
                if j not in visited and self._dist_matrix[current][j] < best_dist:
                    best_dist = self._dist_matrix[current][j]
                    best_next = j
            tour.append(best_next)
            visited.add(best_next)
        return tour

    def _init_population(self, rng: random.Random) -> List[List[int]]:
        pop = []
        for i in range(self.cfg.population_size):
            if i < self.cfg.population_size // 4:
                tour = self._nn_tour(rng)
            else:
                tour = self._random_tour(rng)
            dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None
            tour, _ = improve_2opt(tour, self._dist_matrix, dm_np, 50, True)
            pop.append(tour)
        return pop

    def _swarm_update(self, individual: List[int], pbest: List[int], gbest: List[int],
                      rng: random.Random, n_edges: int, p_best: float, p_gbest: float) -> List[int]:
        r = rng.random()
        if r < p_gbest:
            target = gbest
        elif r < p_gbest + p_best:
            target = pbest
        else:
            return self._perturb(individual, rng)
        target_edges = set()
        for i in range(len(target)):
            a, b = target[i], target[(i + 1) % len(target)]
            target_edges.add((min(a, b), max(a, b)))
        individual_edges = set()
        for i in range(len(individual)):
            a, b = individual[i], individual[(i + 1) % len(individual)]
            individual_edges.add((min(a, b), max(a, b)))
        shared = list(target_edges & individual_edges)
        new_edges = list(target_edges - individual_edges)
        rng.shuffle(new_edges)
        edges_to_force = new_edges[:n_edges]
        result = list(individual)
        for a, b in edges_to_force:
            try:
                ia = result.index(a)
                ib = result.index(b)
                if abs(ia - ib) != 1 and not (ia == 0 and ib == len(result) - 1):
                    if ia < ib:
                        result[ia + 1:ib + 1] = reversed(result[ia + 1:ib + 1])
            except ValueError:
                pass
        return result

    def _perturb(self, tour: List[int], rng: random.Random) -> List[int]:
        result = list(tour)
        n = len(result)
        if n < 4:
            return result
        op = rng.choice(["double_bridge", "swap", "scramble"])
        if op == "double_bridge":
            cuts = sorted(rng.sample(range(1, n), 3))
            i, j, k = cuts
            result = result[:i] + result[j:k] + result[i:j] + result[k:]
        elif op == "swap":
            a, b = rng.sample(range(n), 2)
            result[a], result[b] = result[b], result[a]
        else:
            i, j = sorted(rng.sample(range(n), 2))
            segment = result[i:j + 1]
            rng.shuffle(segment)
            result[i:j + 1] = segment
        return result

    def _inject_diversity(self, population: List[List[int]], pop_costs: List[float],
                          rng: random.Random) -> Tuple[List[List[int]], List[float]]:
        n_inject = max(1, int(self.cfg.injection_rate * len(population)))
        worst_indices = sorted(range(len(pop_costs)), key=lambda i: pop_costs[i], reverse=True)[:n_inject]
        destroy_ops = [RandomRemoval(), WorstRemoval(), ShawRemoval()]
        repair_ops = [GreedyInsertion(), Regret2Insertion(), Regret3Insertion()]
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None
        for idx in worst_indices:
            destroyer = rng.choice(destroy_ops)
            repairer = rng.choice(repair_ops)
            n_remove = max(2, int(self._n * self.cfg.remove_ratio))
            removed, remaining = destroyer.destroy(population[idx], n_remove, rng, self._dist_matrix)
            repaired = repairer.repair(remaining, removed, self._dist_matrix)
            repaired, _ = improve_2opt(repaired, self._dist_matrix, dm_np, 100, True)
            population[idx] = repaired
            pop_costs[idx] = _tour_cost(repaired, self._dist_matrix)
        return population, pop_costs

    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        rng = random.Random(self.cfg.seed)
        t_start = time.monotonic()
        dm_np = self._dist_matrix_np if self._dist_matrix_np is not None else None

        population = self._init_population(rng)
        pop_costs = [_tour_cost(t, self._dist_matrix) for t in population]
        pbest = [list(t) for t in population]
        pbest_costs = list(pop_costs)

        gbest_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
        gbest = list(population[gbest_idx])
        gbest_cost = pop_costs[gbest_idx]

        lahc = _LAHC(self.cfg.lahc_history)
        h_min = self.cfg.h_start * 0.5
        h_max = self.cfg.h_start
        entropy_ema_low = h_min
        entropy_ema_high = h_max
        improvement_entropies: deque = deque(maxlen=200)
        history: List[float] = []
        current_entropy = self._edge_entropy(population)

        for t in range(1, self.cfg.max_iterations + 1):
            prev_best = gbest_cost
            if t % self.cfg.entropy_check_interval == 0 or t == 1:
                current_entropy = self._edge_entropy(population)

            if t <= self.cfg.learn_period and improvement_entropies:
                alpha = 0.1
                recent = list(improvement_entropies)[-min(20, len(improvement_entropies)):]
                entropy_ema_low = (1 - alpha) * entropy_ema_low + alpha * min(recent)
                entropy_ema_high = (1 - alpha) * entropy_ema_high + alpha * max(recent)
                h_min = max(0.05, entropy_ema_low - 0.05)
                h_max = min(0.95, entropy_ema_high + 0.05)
            elif t > self.cfg.learn_period:
                progress = (t - self.cfg.learn_period) / max(1, self.cfg.max_iterations - self.cfg.learn_period)
                target = self.cfg.h_start * (1 - progress) ** self.cfg.gamma + self.cfg.h_end * (1 - (1 - progress) ** self.cfg.gamma)
                h_min = target * 0.4
                h_max = target * 1.4

            if current_entropy < h_min:
                phase = "inject"
                population, pop_costs = self._inject_diversity(population, pop_costs, rng)
            elif current_entropy > h_max:
                phase = "compress"
                n_edges = self.cfg.n_edges_aggressive
                ls_intensity = self.cfg.ls_intensity_compress
            else:
                phase = "normal"
                n_edges = self.cfg.n_edges_normal
                ls_intensity = self.cfg.ls_intensity_normal

            if phase != "inject":
                for i in range(len(population)):
                    candidate = self._swarm_update(population[i], pbest[i], gbest, rng,
                                                    n_edges, self.cfg.p_best, self.cfg.p_gbest)
                    candidate_cost = _tour_cost(candidate, self._dist_matrix)
                    candidate, candidate_cost, _ = MultiLayerLS.improve(
                        candidate, self._dist_matrix, dm_np, ls_intensity, 200, self.cfg.ls_time_limit)
                    if lahc.decide(pop_costs[i], candidate_cost, t, rng):
                        population[i] = candidate
                        pop_costs[i] = candidate_cost

            for i in range(len(population)):
                if pop_costs[i] < pbest_costs[i] - 1e-10:
                    pbest[i] = list(population[i])
                    pbest_costs[i] = pop_costs[i]

            best_idx = min(range(len(pop_costs)), key=lambda i: pop_costs[i])
            if pop_costs[best_idx] < gbest_cost - 1e-10:
                gbest = list(population[best_idx])
                gbest_cost = pop_costs[best_idx]
                improvement_entropies.append(current_entropy)

            lahc.update(gbest_cost)
            history.append(gbest_cost)

            if t % self.cfg.diversity_check_interval == 0:
                diversity = compute_population_diversity(population, self._n)
                if diversity < self.cfg.diversity_threshold:
                    population, pop_costs = self._inject_diversity(population, pop_costs, rng)

            if time.monotonic() - t_start > 300:
                break

        # dm_np zaten solve() başında atandı — yeniden atamaya gerek yok
        gbest, gbest_cost, _ = MultiLayerLS.improve(gbest, self._dist_matrix, dm_np, "full", 500, 5.0)

        elapsed_ms = (time.monotonic() - t_start) * 1000
        gap = float("nan")
        if hasattr(self, "_optimal") and self._optimal and self._optimal > 0:
            gap = (gbest_cost - self._optimal) / self._optimal * 100.0

        return TSPResult(
            algorithm="E2BSO-TSP",
            tour=gbest,
            tour_length=gbest_cost,
            elapsed_ms=elapsed_ms,
            iterations=t,
            params={"population_size": self.cfg.population_size, "max_iterations": self.cfg.max_iterations},
            history=history,
            seed=self.cfg.seed,
        )
