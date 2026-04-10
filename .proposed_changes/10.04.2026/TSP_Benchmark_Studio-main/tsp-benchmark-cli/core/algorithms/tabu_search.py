"""Tabu Search for TSP.

Maintains a short-term tabu list of recently performed moves to prevent
cycling, while exploring promising neighborhoods. Uses aspiration criteria
to accept tabu moves that improve the global best.
"""
import numpy as np
from typing import List, Tuple, Dict, Optional, Set
import time

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


def _2opt_move_key(i: int, j: int) -> Tuple[int, int]:
    """Normalised key for a 2-opt move (smaller index first)."""
    return (min(i, j), max(i, j))


def _swap_move_key(i: int, j: int) -> Tuple[int, int]:
    """Normalised key for a swap move."""
    return (min(i, j), max(i, j))


def _apply_2opt(route: np.ndarray, i: int, j: int) -> np.ndarray:
    """Apply 2-opt move: reverse segment [i+1 .. j]."""
    new_route = route.copy()
    left, right = i + 1, j
    while left < right:
        new_route[left], new_route[right] = new_route[right], new_route[left]
        left += 1
        right -= 1
    return new_route


def _2opt_delta(route: np.ndarray, dist_matrix: np.ndarray,
                i: int, j: int) -> float:
    """Delta for 2-opt move."""
    n = len(route)
    a = int(route[i])
    b = int(route[(i + 1) % n])
    c = int(route[j])
    d = int(route[(j + 1) % n])
    return (dist_matrix[a, c] + dist_matrix[b, d]) - (dist_matrix[a, b] + dist_matrix[c, d])


def _apply_swap(route: np.ndarray, i: int, j: int) -> np.ndarray:
    """Apply swap move."""
    new_route = route.copy()
    new_route[i], new_route[j] = new_route[j], new_route[i]
    return new_route


def _swap_delta(route: np.ndarray, dist_matrix: np.ndarray,
                i: int, j: int) -> float:
    """Delta for swap move."""
    n = len(route)
    prev_i = int(route[(i - 1) % n])
    next_i = int(route[(i + 1) % n])
    prev_j = int(route[(j - 1) % n])
    next_j = int(route[(j + 1) % n])
    vi = int(route[i])
    vj = int(route[j])
    old = dist_matrix[prev_i, vi] + dist_matrix[vi, next_i] + \
          dist_matrix[prev_j, vj] + dist_matrix[vj, next_j]
    new = dist_matrix[prev_i, vj] + dist_matrix[vj, next_i] + \
          dist_matrix[prev_j, vi] + dist_matrix[vi, next_j]
    return new - old


class TabuSearch(TSPAlgorithm):
    """Tabu Search for TSP.

    Parameters
    ----------
    tabu_tenure : int
        Number of iterations a move stays tabu.
    max_iterations : int
        Hard iteration limit.
    neighborhood : str
        ``"2opt"``, ``"swap"``, or ``"mixed"`` (uses both).
    max_neighbors : int
        Maximum number of neighboring solutions evaluated per iteration
        (0 = evaluate all — can be slow for large n).
    intensification_interval : int
        Every N iterations without global improvement, restart from best.
    construction : str
        ``"nearest"`` or ``"random"`` for the initial tour.
    local_search_final : bool
        Apply final 2-opt pass on the best solution.
    """

    def __init__(
        self,
        tabu_tenure: int = 20,
        max_iterations: int = 10000,
        neighborhood: str = "2opt",
        max_neighbors: int = 0,        # 0 = all
        intensification_interval: int = 50,
        construction: str = "nearest",
        local_search_final: bool = True,
    ):
        self.tabu_tenure = tabu_tenure
        self.max_iterations = max_iterations
        self.neighborhood = neighborhood
        self.max_neighbors = max_neighbors
        self.intensification_interval = intensification_interval
        self.construction = construction
        self.local_search_final = local_search_final

    @property
    def name(self) -> str:
        return "ts"

    @property
    def display_name(self) -> str:
        return "Tabu Search"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        np.random.seed(seed)

        # --- initial solution ---
        if self.construction == "nearest":
            route = nearest_neighbor_route(dist_matrix, seed % n)
        else:
            route = random_route(n, seed)

        route = route.copy()
        current_length = calc_tour_length_numba(route, dist_matrix)
        best_route = route.copy()
        best_length = current_length

        # Tabu list: maps move_key -> iteration when it expires
        tabu_list: Dict[Tuple[int, int], int] = {}
        no_improve_count = 0
        convergence: List[float] = [best_length]
        log_interval = max(1, self.max_iterations // 200)

        use_2opt = self.neighborhood in ("2opt", "mixed")
        use_swap = self.neighborhood in ("swap", "mixed")

        for iteration in range(1, self.max_iterations + 1):
            if iteration % log_interval == 0:
                convergence.append(best_length)
            if time.time() - start > time_limit:
                break

            best_move_delta = np.inf
            best_move_key: Optional[Tuple[int, int]] = None
            best_move_type: Optional[str] = None
            best_move_i: int = 0
            best_move_j: int = 0

            # --- explore neighborhood ---
            neighbors_checked = 0

            if use_2opt:
                for i in range(n - 2):
                    for j in range(i + 2, n):
                        if j == n - 1 and i == 0:
                            continue
                        if self.max_neighbors > 0 and neighbors_checked >= self.max_neighbors:
                            break
                        neighbors_checked += 1

                        delta = _2opt_delta(route, dist_matrix, i, j)
                        key = ("2",) + _2opt_move_key(i, j)

                        is_tabu = key in tabu_list and tabu_list[key] > iteration
                        # Aspiration: accept if it improves global best
                        if is_tabu and current_length + delta >= best_length - 1e-10:
                            continue

                        if delta < best_move_delta - 1e-10:
                            best_move_delta = delta
                            best_move_key = key
                            best_move_type = "2opt"
                            best_move_i = i
                            best_move_j = j

                    if self.max_neighbors > 0 and neighbors_checked >= self.max_neighbors:
                        break

            if use_swap and (self.max_neighbors == 0 or neighbors_checked < self.max_neighbors):
                for i in range(n):
                    for j in range(i + 2, n):
                        if j == i + 1 or (i == 0 and j == n - 1):
                            continue
                        if self.max_neighbors > 0 and neighbors_checked >= self.max_neighbors:
                            break
                        neighbors_checked += 1

                        delta = _swap_delta(route, dist_matrix, i, j)
                        key = ("s",) + _swap_move_key(i, j)

                        is_tabu = key in tabu_list and tabu_list[key] > iteration
                        if is_tabu and current_length + delta >= best_length - 1e-10:
                            continue

                        if delta < best_move_delta - 1e-10:
                            best_move_delta = delta
                            best_move_key = key
                            best_move_type = "swap"
                            best_move_i = i
                            best_move_j = j

                    if self.max_neighbors > 0 and neighbors_checked >= self.max_neighbors:
                        break

            # --- apply best move ---
            if best_move_type == "2opt":
                route = _apply_2opt(route, best_move_i, best_move_j)
                current_length += best_move_delta
            elif best_move_type == "swap":
                route = _apply_swap(route, best_move_i, best_move_j)
                current_length += best_move_delta
            else:
                # No improving or non-tabu move found — diversify with random swap
                ri = np.random.randint(0, max(n - 1, 1))
                if ri + 2 < n:
                    rj = np.random.randint(ri + 2, n)
                    if rj == n - 1 and ri == 0:
                        rj = ri + 2
                    route = _apply_2opt(route, ri, rj)
                elif n >= 4:
                    # Fallback for small n: pick a valid pair
                    ri2, rj2 = sorted(np.random.choice(n, size=2, replace=False))
                    if rj2 - ri2 >= 2 and not (ri2 == 0 and rj2 == n - 1):
                        route = _apply_2opt(route, ri2, rj2)
                    else:
                        # Swap two non-adjacent cities as last resort
                        si, sj = np.random.choice(n, size=2, replace=False)
                        route[si], route[sj] = route[sj], route[si]
                    # Recalculate length after diversification
                    current_length = calc_tour_length_numba(route, dist_matrix)

            # --- update tabu list ---
            # Clean expired entries
            expired = [k for k, v in tabu_list.items() if v <= iteration]
            for k in expired:
                del tabu_list[k]
            # Add new tabu move
            if best_move_key is not None:
                tabu_list[best_move_key] = iteration + self.tabu_tenure

            # --- update global best ---
            if current_length < best_length - 1e-10:
                best_route = route.copy()
                best_length = current_length
                no_improve_count = 0
            else:
                no_improve_count += 1

            # --- intensification ---
            if no_improve_count >= self.intensification_interval:
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
