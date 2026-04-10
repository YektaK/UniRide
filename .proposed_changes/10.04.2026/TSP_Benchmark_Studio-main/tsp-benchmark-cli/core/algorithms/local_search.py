"""Local Search algorithms: 2-opt, 3-opt, Or-opt, Swap, Hybrid.

These algorithms improve an initial tour using neighborhood moves.
They rely on Numba-compiled core functions from numba_utils for performance,
with pure-Python fallbacks when Numba is unavailable.
"""
import numpy as np
from typing import List, Optional, Tuple
import time

from .base import TSPAlgorithm, AlgorithmResult

# Forward reference for fallback deadline — set by _set_three_opt_deadline
_fallback_three_opt_deadline: float = float('inf')

# ---------------------------------------------------------------------------
# Import numba utils with graceful fallback
# ---------------------------------------------------------------------------
try:
    from ..numba_utils import (
        two_opt_improve, three_opt_improve, or_opt_improve,
        swap_improve, nearest_neighbor_route, random_route,
        calc_tour_length_numba, NUMBA_AVAILABLE
    )
except ImportError:
    NUMBA_AVAILABLE = False

    # ------------------------------------------------------------------
    # Pure-Python fallback implementations
    # ------------------------------------------------------------------
    def calc_tour_length_numba(route: np.ndarray, dist_matrix: np.ndarray) -> float:
        """Calculate total tour length (return to start included)."""
        n = len(route)
        total = 0.0
        for i in range(n - 1):
            total += dist_matrix[int(route[i]), int(route[i + 1])]
        total += dist_matrix[int(route[n - 1]), int(route[0])]
        return total

    def nearest_neighbor_route(dist_matrix: np.ndarray, start: int = 0) -> np.ndarray:
        """Build a nearest-neighbor tour starting from *start*."""
        n = len(dist_matrix)
        visited = np.zeros(n, dtype=bool)
        route = np.zeros(n, dtype=np.int64)
        current = start
        visited[start] = True
        for idx in range(n):
            route[idx] = current
            best_dist = np.inf
            best_next = -1
            for j in range(n):
                if not visited[j] and dist_matrix[current, j] < best_dist:
                    best_dist = dist_matrix[current, j]
                    best_next = j
            if best_next == -1:
                break  # all visited
            current = best_next
            visited[current] = True
        return route

    def random_route(n: int, seed: int) -> np.ndarray:
        """Return a random permutation of 0..n-1."""
        rng = np.random.RandomState(seed)
        route = np.arange(n, dtype=np.int64)
        rng.shuffle(route)
        return route

    def _two_opt_delta(route: np.ndarray, dist_matrix: np.ndarray,
                       i: int, j: int) -> float:
        """Delta for 2-opt move between positions i and j."""
        n = len(route)
        a, b = int(route[i]), int(route[(i + 1) % n])
        c, d = int(route[j]), int(route[(j + 1) % n])
        return (dist_matrix[a, c] + dist_matrix[b, d]) - (dist_matrix[a, b] + dist_matrix[c, d])

    def _apply_two_opt(route: np.ndarray, i: int, j: int) -> np.ndarray:
        """Apply 2-opt move: reverse segment [i+1 .. j]."""
        new_route = route.copy()
        left, right = i + 1, j
        while left < right:
            new_route[left], new_route[right] = new_route[right], new_route[left]
            left += 1
            right -= 1
        return new_route

    def two_opt_improve(route: np.ndarray, dist_matrix: np.ndarray,
                        max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
        """Pure-Python 2-opt local search."""
        n = len(route)
        if n < 4:
            return route.copy(), calc_tour_length_numba(route, dist_matrix)

        best_route = route.copy()
        best_length = calc_tour_length_numba(best_route, dist_matrix)
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            for i in range(n - 2):
                for j in range(i + 2, n):
                    if j == n - 1 and i == 0:
                        continue
                    delta = _two_opt_delta(best_route, dist_matrix, i, j)
                    if delta < -1e-10:
                        best_route = _apply_two_opt(best_route, i, j)
                        best_length += delta
                        improved = True
                        if first_improvement:
                            break
                if improved and first_improvement:
                    break
        return best_route, best_length

    def _three_opt_cases(route: np.ndarray, i: int, j: int, k: int) -> List[np.ndarray]:
        """Generate 7 reconnection candidates for 3-opt."""
        n = len(route)
        A = route[:i + 1]
        B = route[i + 1:j + 1]
        C = route[j + 1:k + 1]
        D = route[k + 1:]

        def _cat(*segs):
            return np.concatenate(segs)

        return [
            _cat(A, B[::-1], C[::-1], D),
            _cat(A, B[::-1], C, D),
            _cat(A, B, C[::-1], D),
            _cat(A, B[::-1], C, D[::-1]),
            _cat(A, B, C[::-1], D[::-1]),
            _cat(A, B[::-1], C[::-1], D[::-1]),
            _cat(A, B, C, D),  # original
        ]

    def three_opt_improve(route: np.ndarray, dist_matrix: np.ndarray,
                          max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
        """Pure-Python 3-opt local search."""
        n = len(route)
        if n < 6:
            return two_opt_improve(route, dist_matrix, max_iterations, first_improvement)

        best_route = route.copy()
        best_length = calc_tour_length_numba(best_route, dist_matrix)
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            for i in range(n - 4):
                if time.time() > _fallback_three_opt_deadline:
                    return best_route, best_length
                for j in range(i + 2, n - 2):
                    for k in range(j + 2, n):
                        candidates = _three_opt_cases(best_route, i, j, k)
                        for cand in candidates:
                            cand_len = calc_tour_length_numba(cand, dist_matrix)
                            if cand_len < best_length - 1e-10:
                                best_route = cand.copy()
                                best_length = cand_len
                                improved = True
                                if first_improvement:
                                    break
                        if improved and first_improvement:
                            break
                    if improved and first_improvement:
                        break
                if improved and first_improvement:
                    break
        return best_route, best_length



    def or_opt_improve(route: np.ndarray, dist_matrix: np.ndarray,
                       max_iterations: int, max_segment_size: int) -> Tuple[np.ndarray, float]:
        """Pure-Python Or-opt local search."""
        n = len(route)
        if n < 4:
            return route.copy(), calc_tour_length_numba(route, dist_matrix)

        best_route = route.copy()
        best_length = calc_tour_length_numba(best_route, dist_matrix)
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            for seg_size in range(1, min(max_segment_size, n - 1) + 1):
                for i in range(n - seg_size + 1):
                    segment = best_route[i:i + seg_size].copy()
                    remaining = np.concatenate([best_route[:i], best_route[i + seg_size:]])
                    for j in range(len(remaining) + 1):
                        if j == i:
                            continue
                        new_route = np.concatenate([remaining[:j], segment, remaining[j:]])
                        new_length = calc_tour_length_numba(new_route, dist_matrix)
                        if new_length < best_length - 1e-10:
                            best_route = new_route.copy()
                            best_length = new_length
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
        return best_route, best_length

    def swap_improve(route: np.ndarray, dist_matrix: np.ndarray,
                     max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
        """Pure-Python Swap local search."""
        n = len(route)
        if n < 3:
            return route.copy(), calc_tour_length_numba(route, dist_matrix)

        best_route = route.copy()
        best_length = calc_tour_length_numba(best_route, dist_matrix)
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            for i in range(n):
                for j in range(i + 1, n):
                    if j == i + 1:
                        continue
                    new_route = best_route.copy()
                    new_route[i], new_route[j] = new_route[j], new_route[i]
                    new_length = calc_tour_length_numba(new_route, dist_matrix)
                    if new_length < best_length - 1e-10:
                        best_route = new_route.copy()
                        best_length = new_length
                        improved = True
                        if first_improvement:
                            break
                if improved and first_improvement:
                    break
        return best_route, best_length


# ======================================================================
# Helper: set deadline on pure-Python three_opt for time_limit support
# ======================================================================
def _set_three_opt_deadline(deadline: float):
    """Set the global deadline for the pure-Python 3-opt fallback."""
    global _fallback_three_opt_deadline
    _fallback_three_opt_deadline = deadline


# ======================================================================
# Algorithm classes
# ======================================================================

class TwoOpt(TSPAlgorithm):
    """2-opt local search: reverses tour segments to remove crossings."""

    def __init__(self, max_iterations: int = 1000, first_improvement: bool = False,
                 construction: str = "nearest"):
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self.construction = construction  # "nearest" or "random"

    @property
    def name(self) -> str:
        return "2-opt"

    @property
    def display_name(self) -> str:
        return "2-opt Local Search"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        np.random.seed(seed)

        # Construction heuristic
        if self.construction == "nearest":
            initial = nearest_neighbor_route(dist_matrix, seed % n)
        else:
            initial = random_route(n, seed)

        # Run 2-opt improvement
        improved, length = two_opt_improve(
            initial, dist_matrix, self.max_iterations, self.first_improvement
        )

        tour = improved.tolist() if hasattr(improved, 'tolist') else list(improved)
        exec_time = time.time() - start
        return self._create_result(tour, length, optimal_value, exec_time)


# ======================================================================
# Pure-Python 3-opt (avoids Numba segfaults in some environments)
# ======================================================================
class _PurePythonThreeOpt:
    """Standalone pure-Python 3-opt that never touches Numba."""

    @staticmethod
    def _eval_cases(route, i, j, k):
        n = len(route)
        A = route[:i + 1]
        B = route[i + 1:j + 1]
        C = route[j + 1:k + 1]
        D = route[k + 1:]
        return [
            np.concatenate([A, B[::-1], C[::-1], D]),
            np.concatenate([A, B[::-1], C, D]),
            np.concatenate([A, B, C[::-1], D]),
            np.concatenate([A, B[::-1], C, D[::-1]]),
            np.concatenate([A, B, C[::-1], D[::-1]]),
            np.concatenate([A, B[::-1], C[::-1], D[::-1]]),
        ]

    @staticmethod
    def _tour_length(route, dist_matrix):
        n = len(route)
        total = 0.0
        for i in range(n - 1):
            total += dist_matrix[int(route[i]), int(route[i + 1])]
        total += dist_matrix[int(route[n - 1]), int(route[0])]
        return total

    def improve(self, route, dist_matrix, max_iterations, first_improvement):
        n = len(route)
        if n < 6:
            # Fall back to 2-opt for small instances
            return two_opt_improve(route, dist_matrix, max_iterations, first_improvement)

        best_route = route.copy()
        best_length = self._tour_length(best_route, dist_matrix)
        tl = self._tour_length
        improved = True
        iters = 0

        while improved and iters < max_iterations:
            improved = False
            iters += 1
            for i in range(n - 4):
                if time.time() > _fallback_three_opt_deadline:
                    break
                for j in range(i + 2, n - 2):
                    for k in range(j + 2, n):
                        for cand in self._eval_cases(best_route, i, j, k):
                            cl = tl(cand, dist_matrix)
                            if cl < best_length - 1e-10:
                                best_route = cand.copy()
                                best_length = cl
                                improved = True
                                if first_improvement:
                                    break
                        if improved and first_improvement:
                            break
                    if improved and first_improvement:
                        break
                if improved and first_improvement:
                    break
        return best_route, best_length


class ThreeOpt(TSPAlgorithm):
    """3-opt local search: removes 3 edges and tries 7 reconnections."""

    def __init__(self, max_iterations: int = 500, first_improvement: bool = False,
                 construction: str = "nearest"):
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self.construction = construction

    @property
    def name(self) -> str:
        return "3-opt"

    @property
    def display_name(self) -> str:
        return "3-opt Local Search"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        np.random.seed(seed)

        # Set deadline for pure-Python fallback
        _set_three_opt_deadline(start + time_limit)

        if self.construction == "nearest":
            initial = nearest_neighbor_route(dist_matrix, seed % n)
        else:
            initial = random_route(n, seed)

        # Use pure-Python 3-opt to avoid Numba segfaults in some environments
        _py_three_opt = _PurePythonThreeOpt()
        improved, length = _py_three_opt.improve(
            initial, dist_matrix, self.max_iterations, self.first_improvement
        )

        tour = improved.tolist() if hasattr(improved, 'tolist') else list(improved)
        exec_time = time.time() - start
        return self._create_result(tour, length, optimal_value, exec_time)


class OrOpt(TSPAlgorithm):
    """Or-opt: relocates 1-3 node segments to different positions."""

    def __init__(self, max_iterations: int = 500, max_segment_size: int = 3,
                 construction: str = "nearest"):
        self.max_iterations = max_iterations
        self.max_segment_size = max_segment_size
        self.construction = construction

    @property
    def name(self) -> str:
        return "or-opt"

    @property
    def display_name(self) -> str:
        return "Or-opt Local Search"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        np.random.seed(seed)

        if self.construction == "nearest":
            initial = nearest_neighbor_route(dist_matrix, seed % n)
        else:
            initial = random_route(n, seed)

        # Or-opt takes (route, dist_matrix, max_iterations, max_segment_size)
        improved, length = or_opt_improve(
            initial, dist_matrix, self.max_iterations, self.max_segment_size
        )

        tour = improved.tolist() if hasattr(improved, 'tolist') else list(improved)
        exec_time = time.time() - start
        return self._create_result(tour, length, optimal_value, exec_time)


class Swap(TSPAlgorithm):
    """Swap: exchanges positions of two nodes."""

    def __init__(self, max_iterations: int = 1000, first_improvement: bool = False,
                 construction: str = "nearest"):
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self.construction = construction

    @property
    def name(self) -> str:
        return "swap"

    @property
    def display_name(self) -> str:
        return "Swap Local Search"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        np.random.seed(seed)

        if self.construction == "nearest":
            initial = nearest_neighbor_route(dist_matrix, seed % n)
        else:
            initial = random_route(n, seed)

        improved, length = swap_improve(
            initial, dist_matrix, self.max_iterations, self.first_improvement
        )

        tour = improved.tolist() if hasattr(improved, 'tolist') else list(improved)
        exec_time = time.time() - start
        return self._create_result(tour, length, optimal_value, exec_time)


class HybridLocalSearch(TSPAlgorithm):
    """Hybrid: applies all local search methods in sequence for multiple cycles."""

    def __init__(self, max_cycles: int = 5, construction: str = "nearest"):
        self.max_cycles = max_cycles
        self.construction = construction

    @property
    def name(self) -> str:
        return "hybrid"

    @property
    def display_name(self) -> str:
        return "Hybrid Local Search"

    def solve(self, dist_matrix: np.ndarray, optimal_value: float = -1.0,
              seed: int = 42, time_limit: float = 300.0, **kwargs) -> AlgorithmResult:
        start = time.time()
        n = len(dist_matrix)
        np.random.seed(seed)

        # Set deadline for pure-Python 3-opt fallback
        _set_three_opt_deadline(start + time_limit)

        # Initial tour via nearest neighbor
        if self.construction == "nearest":
            route = nearest_neighbor_route(dist_matrix, seed % n)
        else:
            route = random_route(n, seed)

        best_length = calc_tour_length_numba(route, dist_matrix)
        convergence: List[float] = [best_length]
        cycles_done = 0

        for cycle in range(self.max_cycles):
            if time.time() - start > time_limit:
                break

            improved = False
            _py_3opt = _PurePythonThreeOpt()

            # Apply in sequence: swap -> 2-opt -> or-opt -> 3-opt(pure Python)
            # (swap, two_opt, three_opt) take (route, dist, max_iter, first_improvement)
            # (or_opt) takes (route, dist, max_iter, max_segment_size)
            for improve_fn, max_iter, extra_arg in [
                (swap_improve, 100, False),
                (two_opt_improve, 80, False),
                (or_opt_improve, 60, 3),       # max_segment_size=3
            ]:
                if time.time() - start > time_limit:
                    break
                new_route, new_length = improve_fn(route, dist_matrix, max_iter, extra_arg)
                if new_length < best_length - 1e-10:
                    route = new_route
                    best_length = new_length
                    improved = True

            # 3-opt: use pure Python to avoid Numba segfaults
            if time.time() - start < time_limit:
                new_route, new_length = _py_3opt.improve(route, dist_matrix, 25, False)
                if new_length < best_length - 1e-10:
                    route = new_route
                    best_length = new_length
                    improved = True

            cycles_done = cycle + 1
            convergence.append(best_length)
            if not improved:
                break

        tour = route.tolist() if hasattr(route, 'tolist') else list(route)
        exec_time = time.time() - start
        return self._create_result(tour, best_length, optimal_value, exec_time,
                                   iterations=cycles_done, convergence=convergence)
