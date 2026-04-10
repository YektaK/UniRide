"""Simulated Annealing for TSP.

Uses a temperature schedule that gradually reduces the probability of
accepting worsening moves, allowing escape from local optima.
"""
import numpy as np
from typing import List, Optional, Tuple
import time
import math

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


def _tour_delta_2opt(route: np.ndarray, dist_matrix: np.ndarray,
                     i: int, j: int) -> float:
    """Fast delta calculation for a 2-opt move."""
    n = len(route)
    a = int(route[i])
    b = int(route[(i + 1) % n])
    c = int(route[j])
    d = int(route[(j + 1) % n])
    return (dist_matrix[a, c] + dist_matrix[b, d]) - (dist_matrix[a, b] + dist_matrix[c, d])


def _tour_delta_swap(route: np.ndarray, dist_matrix: np.ndarray,
                     i: int, j: int) -> float:
    """Fast delta calculation for a swap move."""
    n = len(route)
    # Before swap: ...prev_i -> i -> next_i... and ...prev_j -> j -> next_j...
    # After swap:  ...prev_i -> j -> next_i... and ...prev_j -> i -> next_j...
    prev_i = int(route[(i - 1) % n])
    next_i = int(route[(i + 1) % n])
    prev_j = int(route[(j - 1) % n])
    next_j = int(route[(j + 1) % n])
    vi = int(route[i])
    vj = int(route[j])

    # Remove old edges touching i and j, add new ones
    old = dist_matrix[prev_i, vi] + dist_matrix[vi, next_i] + \
          dist_matrix[prev_j, vj] + dist_matrix[vj, next_j]
    new = dist_matrix[prev_i, vj] + dist_matrix[vj, next_i] + \
          dist_matrix[prev_j, vi] + dist_matrix[vi, next_j]
    return new - old


def _apply_2opt(route: np.ndarray, i: int, j: int) -> np.ndarray:
    """Apply 2-opt move in-place."""
    left, right = i + 1, j
    while left < right:
        route[left], route[right] = route[right], route[left]
        left += 1
        right -= 1
    return route


class SimulatedAnnealing(TSPAlgorithm):
    """Simulated Annealing: probabilistic acceptance of worsening moves.

    Parameters
    ----------
    initial_temp : float
        Starting temperature. Should be proportional to expected deltas.
    cooling_rate : float
        Multiplicative cooling factor applied per iteration (e.g. 0.9995).
    min_temp : float
        Temperature floor — stop cooling below this.
    reheat_interval : int
        Re-heat to *initial_temp* every this many iterations without improvement.
    neighborhood : str
        ``"2opt"`` (default) or ``"swap"``.
    max_iterations : int
        Hard iteration limit.
    construction : str
        ``"nearest"`` or ``"random"`` initial tour.
    local_search_final : bool
        If True, run a final 2-opt pass on the best solution found.
    """

    def __init__(
        self,
        initial_temp: float = 10000.0,
        cooling_rate: float = 0.9995,
        min_temp: float = 0.01,
        reheat_interval: int = 10000,
        neighborhood: str = "2opt",
        max_iterations: int = 500000,
        construction: str = "nearest",
        local_search_final: bool = True,
    ):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.reheat_interval = reheat_interval
        self.neighborhood = neighborhood
        self.max_iterations = max_iterations
        self.construction = construction
        self.local_search_final = local_search_final

    @property
    def name(self) -> str:
        return "sa"

    @property
    def display_name(self) -> str:
        return "Simulated Annealing"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        rng = np.random.RandomState(seed)

        # --- construction ---
        if self.construction == "nearest":
            route = nearest_neighbor_route(dist_matrix, seed % n)
        else:
            route = random_route(n, seed)

        route = route.copy()
        best_route = route.copy()
        best_length = calc_tour_length_numba(route, dist_matrix)
        current_length = best_length

        temp = self.initial_temp
        no_improve_count = 0
        convergence: List[float] = [best_length]
        log_interval = max(1, self.max_iterations // 200)  # ~200 data points

        for iteration in range(1, self.max_iterations + 1):
            if iteration % log_interval == 0:
                convergence.append(best_length)
            if time.time() - start > time_limit:
                break

            # --- choose move ---
            if self.neighborhood == "swap":
                i, j = rng.randint(0, n, size=2)
                while i == j:
                    j = rng.randint(0, n)
                if i > j:
                    i, j = j, i
                if j - i == 1 or (i == 0 and j == n - 1):
                    continue  # skip adjacent
                delta = _tour_delta_swap(route, dist_matrix, i, j)
                if delta < 0 or rng.rand() < math.exp(-delta / temp):
                    route[i], route[j] = route[j], route[i]
                    current_length += delta
            else:
                # 2-opt
                i = rng.randint(0, n - 2)
                j = rng.randint(i + 2, n)
                if j == n - 1 and i == 0:
                    continue
                delta = _tour_delta_2opt(route, dist_matrix, i, j)
                if delta < 0 or rng.rand() < math.exp(-delta / temp):
                    route = _apply_2opt(route, i, j)
                    current_length += delta

            # --- track best ---
            if current_length < best_length - 1e-10:
                best_route = route.copy()
                best_length = current_length
                no_improve_count = 0
            else:
                no_improve_count += 1

            # --- cooling & reheat ---
            temp = max(temp * self.cooling_rate, self.min_temp)
            if no_improve_count >= self.reheat_interval:
                temp = self.initial_temp
                route = best_route.copy()
                current_length = best_length
                no_improve_count = 0

        # --- optional final local search ---
        if self.local_search_final and time.time() - start < time_limit:
            best_route, best_length = two_opt_improve(
                best_route, dist_matrix, 200, False
            )

        convergence.append(best_length)
        tour = best_route.tolist() if hasattr(best_route, 'tolist') else list(best_route)
        exec_time = time.time() - start
        return self._create_result(tour, best_length, optimal_value, exec_time,
                                   iterations=iteration, convergence=convergence)
