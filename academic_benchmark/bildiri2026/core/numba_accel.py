"""
Numba JIT Acceleration for Bildiri 2026 Solvers

Wraps optimizer_api/utils/local_search_numba.py functions
or provides pure-Python fallback.
"""
import sys, os, numpy as np
from typing import Tuple, List

# ----- Try to import optimizer_api numba utilities -----
# bildiri2026/core/numba_accel.py -> bildiri2026/ -> academic_benchmark/ -> UniRide/ -> optimizer_api/utils
OPTIMIZER_API_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "optimizer_api", "utils"
)
if os.path.isdir(OPTIMIZER_API_PATH) and OPTIMIZER_API_PATH not in sys.path:
    sys.path.insert(0, OPTIMIZER_API_PATH)

try:
    from local_search_numba import (
        _calculate_tour_length_numba,
        _two_opt_delta_numba,
        _apply_two_opt_numba,
        _two_opt_improve_numba,
        _three_opt_improve_numba,
        _or_opt_improve_numba,
        NUMBA_AVAILABLE,
    )
except Exception:
    NUMBA_AVAILABLE = False

# ----- Fallback pure-Python implementations (never used if numba works) -----
if not NUMBA_AVAILABLE:
    def _calculate_tour_length_numba(route: np.ndarray, dist_matrix: np.ndarray) -> float:
        n = len(route)
        if n < 2:
            return 0.0
        total = 0.0
        for i in range(n - 1):
            total += dist_matrix[route[i], route[i + 1]]
        total += dist_matrix[route[n - 1], route[0]]
        return total

    def _two_opt_delta_numba(route: np.ndarray, dist_matrix: np.ndarray, i: int, j: int) -> float:
        n = len(route)
        a = route[i]
        b = route[(i + 1) % n]
        c = route[j]
        d = route[(j + 1) % n]
        return (dist_matrix[a, c] + dist_matrix[b, d]) - (dist_matrix[a, b] + dist_matrix[c, d])

    def _apply_two_opt_numba(route: np.ndarray, i: int, j: int) -> np.ndarray:
        new_route = route.copy()
        left, right = i + 1, j
        while left < right:
            new_route[left], new_route[right] = new_route[right], new_route[left]
            left += 1
            right -= 1
        return new_route

    def _two_opt_improve_numba(route: np.ndarray, dist_matrix: np.ndarray,
                               max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
        n = len(route)
        if n < 4:
            return route.copy(), _calculate_tour_length_numba(route, dist_matrix)
        best_route = route.copy()
        best_length = _calculate_tour_length_numba(best_route, dist_matrix)
        improved = True
        iters = 0
        while improved and iters < max_iterations:
            improved = False
            iters += 1
            for i in range(n - 2):
                for j in range(i + 2, n):
                    delta = _two_opt_delta_numba(best_route, dist_matrix, i, j)
                    if delta < -1e-10:
                        best_route = _apply_two_opt_numba(best_route, i, j)
                        best_length += delta
                        improved = True
                        if first_improvement:
                            break
                if improved and first_improvement:
                    break
        return best_route, best_length

    def _three_opt_improve_numba(route, dist_matrix, max_iterations, first_improvement):
        # pure-python stub—kept minimal, real version lives in optimizer_api
        return _two_opt_improve_numba(route, dist_matrix, max_iterations, first_improvement)

    def _or_opt_improve_numba(route, dist_matrix, max_iterations, max_segment_size):
        # pure-python stub
        return _two_opt_improve_numba(route, dist_matrix, max_iterations, False)


# ----- Convenience wrappers that accept Python lists -----
def _to_ndarray(lst: List[int]) -> np.ndarray:
    return np.array(lst, dtype=np.int64)


def nb_two_opt(route_list: List[int], dist_matrix_2d: List[List[float]],
               max_iterations: int, first_improvement: bool) -> Tuple[List[int], float]:
    """Numba-accelerated 2-opt returning Python list."""
    route = _to_ndarray(route_list)
    dm = np.array(dist_matrix_2d, dtype=np.float64)
    improved_route, length = _two_opt_improve_numba(route, dm, max_iterations, first_improvement)
    return improved_route.tolist(), float(length)


def nb_three_opt(route_list: List[int], dist_matrix_2d: List[List[float]],
                 max_iterations: int, first_improvement: bool) -> Tuple[List[int], float]:
    """Numba-accelerated 3-opt returning Python list."""
    route = _to_ndarray(route_list)
    dm = np.array(dist_matrix_2d, dtype=np.float64)
    improved_route, length = _three_opt_improve_numba(route, dm, max_iterations, first_improvement)
    return improved_route.tolist(), float(length)


def nb_or_opt(route_list: List[int], dist_matrix_2d: List[List[float]],
              max_iterations: int, max_segment_size: int) -> Tuple[List[int], float]:
    """Numba-accelerated Or-opt returning Python list."""
    route = _to_ndarray(route_list)
    dm = np.array(dist_matrix_2d, dtype=np.float64)
    improved_route, length = _or_opt_improve_numba(route, dm, max_iterations, max_segment_size)
    return improved_route.tolist(), float(length)
