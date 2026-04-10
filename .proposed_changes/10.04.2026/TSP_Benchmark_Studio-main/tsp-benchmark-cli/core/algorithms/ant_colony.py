"""Ant Colony Optimization for TSP.

Virtual ants build tours stochastically guided by pheromone trails and
heuristic information (inverse distance). Pheromone is updated after
each iteration using both evaporation and deposit steps.
"""
import numpy as np
from typing import List
import time
import math

from .base import TSPAlgorithm, AlgorithmResult

# Import numba utils with fallback
try:
    from ..numba_utils import (
        calc_tour_length_numba, two_opt_improve, NUMBA_AVAILABLE
    )
except ImportError:
    from .local_search import (
        calc_tour_length_numba, two_opt_improve
    )


class AntColonyOptimization(TSPAlgorithm):
    """Ant Colony Optimization (ACS variant) for TSP.

    Parameters
    ----------
    num_ants : int
        Number of ants per iteration.
    alpha : float
        Pheromone influence weight.
    beta : float
        Heuristic (1/distance) influence weight.
    evaporation_rate : float
        Fraction of pheromone that evaporates each iteration.
    q : float
        Pheromone deposit factor (total pheromone deposited by best ant).
    elite_factor : float
        Additional pheromone deposited on the global-best tour edges.
    max_iterations : int
        Maximum number of ant iterations.
    local_search_interval : int
        Apply 2-opt to the best-so-far tour every N iterations (0 = never).
    """

    def __init__(
        self,
        num_ants: int = 25,
        alpha: float = 1.0,
        beta: float = 3.0,
        evaporation_rate: float = 0.5,
        q: float = 100.0,
        elite_factor: float = 0.5,
        max_iterations: int = 500,
        local_search_interval: int = 25,
    ):
        self.num_ants = num_ants
        self.alpha = alpha
        self.beta = beta
        self.evaporation_rate = evaporation_rate
        self.q = q
        self.elite_factor = elite_factor
        self.max_iterations = max_iterations
        self.local_search_interval = local_search_interval

    @property
    def name(self) -> str:
        return "aco"

    @property
    def display_name(self) -> str:
        return "Ant Colony Optimization"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        rng = np.random.RandomState(seed)

        # --- heuristic information (inverse distance, 0 on diagonal) ---
        with np.errstate(divide='ignore', invalid='ignore'):
            heuristic = np.where(dist_matrix > 0, 1.0 / dist_matrix, 0.0)
        # Normalise so max = 1 (numerical stability)
        h_max = heuristic.max()
        if h_max > 0:
            heuristic /= h_max

        # --- pheromone matrix ---
        initial_pheromone = 1.0 / n
        pheromone = np.full((n, n), initial_pheromone, dtype=np.float64)

        best_route: np.ndarray = np.arange(n, dtype=np.int64)
        best_length = calc_tour_length_numba(best_route, dist_matrix)
        convergence: List[float] = [best_length]
        log_interval = max(1, self.max_iterations // 200)

        for iteration in range(1, self.max_iterations + 1):
            if iteration % log_interval == 0:
                convergence.append(best_length)
            if time.time() - start > time_limit:
                break

            # --- construct tours for all ants ---
            ant_tours: List[np.ndarray] = []
            ant_lengths: List[float] = []

            for _ in range(self.num_ants):
                visited = np.zeros(n, dtype=bool)
                tour = np.zeros(n, dtype=np.int64)
                current = rng.randint(0, n)
                visited[current] = True
                tour[0] = current

                for step in range(1, n):
                    # Compute transition probabilities for unvisited nodes
                    probs = np.zeros(n, dtype=np.float64)
                    unvisited = ~visited
                    if not np.any(unvisited):
                        break
                    tau = pheromone[current] ** self.alpha
                    eta = heuristic[current] ** self.beta
                    raw = tau * eta * unvisited
                    total = raw.sum()
                    if total <= 0:
                        # Fallback: choose randomly among unvisited
                        candidates = np.where(unvisited)[0]
                        next_node = candidates[rng.randint(len(candidates))]
                    else:
                        probs = raw / total
                        next_node = rng.choice(n, p=probs)

                    tour[step] = next_node
                    visited[next_node] = True
                    current = next_node

                length = calc_tour_length_numba(tour, dist_matrix)
                ant_tours.append(tour)
                ant_lengths.append(length)

            # --- find iteration-best ---
            iter_best_idx = int(np.argmin(ant_lengths))
            iter_best_route = ant_tours[iter_best_idx]
            iter_best_length = ant_lengths[iter_best_idx]

            if iter_best_length < best_length - 1e-10:
                best_route = iter_best_route.copy()
                best_length = iter_best_length

            # --- pheromone update ---
            # Evaporation
            pheromone *= (1.0 - self.evaporation_rate)
            # Deposit on iteration-best tour edges
            deposit = self.q / iter_best_length
            for k in range(n - 1):
                pheromone[int(iter_best_route[k]), int(iter_best_route[k + 1])] += deposit
            pheromone[int(iter_best_route[n - 1]), int(iter_best_route[0])] += deposit

            # Elite deposit on global-best tour edges
            elite_deposit = (self.q * self.elite_factor) / best_length
            for k in range(n - 1):
                pheromone[int(best_route[k]), int(best_route[k + 1])] += elite_deposit
            pheromone[int(best_route[n - 1]), int(best_route[0])] += elite_deposit

            # Clamp pheromone to avoid overflow / underflow
            np.clip(pheromone, 1e-6, 1e6, out=pheromone)

            # --- periodic local search ---
            if (self.local_search_interval > 0
                    and iteration % self.local_search_interval == 0
                    and time.time() - start < time_limit * 0.8):
                best_route, best_length = two_opt_improve(
                    best_route, dist_matrix, 50, False
                )

        convergence.append(best_length)
        tour = best_route.tolist() if hasattr(best_route, 'tolist') else list(best_route)
        exec_time = time.time() - start
        return self._create_result(tour, best_length, optimal_value, exec_time,
                                   iterations=iteration, convergence=convergence)
