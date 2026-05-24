"""
Adaptive Large Neighborhood Search (ALNS) for TSP.

Standalone solver wrapping the destroy/repair operators from
destroy_ops.py and repair_ops.py with adaptive weight updating,
roulette-wheel selection, and simulated annealing acceptance.

References:
  Ropke & Pisinger (2006). "An Adaptive Large Neighborhood Search
  Heuristic for the Pickup and Delivery Problem with Time Windows."
  Transportation Science, 40(4), 455-472.
"""

import math
import time
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from uniride_core.models import TSPResult
from uniride_core.algorithms.sota_tsp.base_solver import BaseTSPSolver
from uniride_core.algorithms.sota_tsp.destroy_ops import (
    RandomRemoval, WorstRemoval, ShawRemoval, RelatedRemoval,
)
from uniride_core.algorithms.sota_tsp.repair_ops import (
    GreedyInsertion, Regret2Insertion, Regret3Insertion,
)

DESTROY_OPERATORS = [
    ("random", RandomRemoval()),
    ("worst", WorstRemoval()),
    ("shaw", ShawRemoval()),
    ("related", RelatedRemoval()),
]

REPAIR_OPERATORS = [
    ("greedy", GreedyInsertion()),
    ("regret2", Regret2Insertion()),
    ("regret3", Regret3Insertion()),
]


@dataclass
class ALNSConfig:
    iterations: int = 5000
    max_no_improve: int = 500
    remove_ratio: float = 0.2
    min_remove: int = 2
    segment_length: int = 100
    weight_update_factor: float = 0.8
    noise_scale: float = 0.05
    use_sa: bool = True
    sa_start_temp: float = 100.0
    sa_cooling_rate: float = 0.995
    seed: int = 42


class ALNS_TSP(BaseTSPSolver):
    """Adaptive Large Neighborhood Search for TSP.

    Uses a set of destroy and repair operators, adaptively selecting
    which to apply based on their historical performance.  Accepts new
    solutions via simulated annealing.
    """

    def __init__(self, config: Optional[ALNSConfig] = None):
        super().__init__(name="ALNS-TSP")
        self.config = config or ALNSConfig()
        self.rng = random.Random(self.config.seed)
        self._destroy_names, self._destroy_ops = zip(*DESTROY_OPERATORS)
        self._repair_names, self._repair_ops = zip(*REPAIR_OPERATORS)
        self._nd = len(self._destroy_ops)
        self._nr = len(self._repair_ops)

    def _init_weights(self):
        n_scores = 3
        self._destroy_weights = [1.0] * self._nd
        self._repair_weights = [1.0] * self._nr
        self._destroy_scores = [0.0] * self._nd
        self._repair_scores = [0.0] * self._nr
        self._destroy_counts = [0] * self._nd
        self._repair_counts = [0] * self._nr

    def _roulette_select(self, weights: List[float]) -> int:
        total = sum(weights)
        r = self.rng.random() * total
        cum = 0.0
        for i, w in enumerate(weights):
            cum += w
            if r <= cum:
                return i
        return len(weights) - 1

    def _nearest_neighbor_tour(self) -> List[int]:
        n = self._n
        visited = [False] * n
        tour = [0]
        visited[0] = True
        for _ in range(1, n):
            last = tour[-1]
            best = -1
            best_d = float("inf")
            for j in range(n):
                if not visited[j] and self._dist_matrix[last][j] < best_d:
                    best_d = self._dist_matrix[last][j]
                    best = j
            tour.append(best)
            visited[best] = True
        return tour

    def _tour_cost(self, tour: List[int]) -> float:
        if not tour or len(tour) < 2:
            return 0.0
        total = 0.0
        for i in range(len(tour)):
            total += self._dist_matrix[tour[i]][tour[(i + 1) % len(tour)]]
        return total

    def _accept(self, current_cost: float, new_cost: float, temp: float) -> bool:
        if new_cost < current_cost:
            return True
        if self.config.use_sa and temp > 1e-10:
            delta = new_cost - current_cost
            prob = math.exp(-delta / temp)
            return self.rng.random() < prob
        return False

    def _update_segment(self, destroy_idx: int, repair_idx: int, sigma: int):
        scores = {0: 0.0, 1: 1.0, 2: 3.0, 3: 5.0}
        self._destroy_scores[destroy_idx] += scores.get(sigma, 0.0)
        self._repair_scores[repair_idx] += scores.get(sigma, 0.0)
        self._destroy_counts[destroy_idx] += 1
        self._repair_counts[repair_idx] += 1

    def _apply_weights(self):
        rho = self.config.weight_update_factor
        for i in range(self._nd):
            cnt = self._destroy_counts[i]
            if cnt > 0:
                self._destroy_weights[i] = (
                    self._destroy_weights[i] * (1 - rho)
                    + rho * self._destroy_scores[i] / cnt
                )
            self._destroy_scores[i] = 0.0
            self._destroy_counts[i] = 0
        for i in range(self._nr):
            cnt = self._repair_counts[i]
            if cnt > 0:
                self._repair_weights[i] = (
                    self._repair_weights[i] * (1 - rho)
                    + rho * self._repair_scores[i] / cnt
                )
            self._repair_scores[i] = 0.0
            self._repair_counts[i] = 0

    def _solve(self) -> TSPResult:
        cfg = self.config
        self.rng = random.Random(cfg.seed)
        self._init_weights()
        n = self._n

        current = self._nearest_neighbor_tour()
        current_cost = self._tour_cost(current)
        best = list(current)
        best_cost = current_cost

        temp = cfg.sa_start_temp if cfg.use_sa else 0.0
        no_improve = 0
        start_time = time.perf_counter()

        for iteration in range(1, cfg.iterations + 1):
            d_idx = self._roulette_select(self._destroy_weights)
            r_idx = self._roulette_select(self._repair_weights)

            n_remove = max(cfg.min_remove, int(n * cfg.remove_ratio))
            n_remove = min(n_remove, n - 2)

            removed, partial = self._destroy_ops[d_idx].destroy(
                current, n_remove, self.rng, self._dist_matrix
            )
            candidate = self._repair_ops[r_idx].repair(
                partial, removed, self._dist_matrix
            )
            candidate_cost = self._tour_cost(candidate)

            if self._accept(current_cost, candidate_cost, temp):
                current = candidate
                current_cost = candidate_cost
                if candidate_cost < best_cost:
                    best = list(candidate)
                    best_cost = candidate_cost
                    no_improve = 0
                    sigma = 3
                else:
                    sigma = 2
            else:
                sigma = 0
                no_improve += 1

            self._update_segment(d_idx, r_idx, sigma)

            if iteration % cfg.segment_length == 0:
                self._apply_weights()

            if cfg.use_sa:
                temp *= cfg.sa_cooling_rate

            if no_improve >= cfg.max_no_improve:
                break

        elapsed = (time.perf_counter() - start_time) * 1000.0

        return TSPResult(
            algorithm=self.name,
            tour=best,
            tour_length=best_cost,
            time_ms=elapsed,
            iterations=iteration,
            seed=cfg.seed,
        )
