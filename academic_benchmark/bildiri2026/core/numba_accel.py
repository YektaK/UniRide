"""
Numba JIT Acceleration for Bildiri 2026 Solvers

Provides ATSP-aware Local Search algorithms specifically optimized 
for time-matrix and School Bus Routing problems where the depot (0) is fixed.
"""
import sys, os
import numpy as np
from typing import Tuple, List

try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator

@jit(nopython=True, cache=True)
def _calculate_tour_length_atsp_numba(route: np.ndarray, dist_matrix: np.ndarray) -> float:
    """Calculate total tour length for a closed loop."""
    n = len(route)
    if n < 2:
        return 0.0
    total = 0.0
    for i in range(n - 1):
        total += dist_matrix[route[i], route[i + 1]]
    total += dist_matrix[route[n - 1], route[0]]
    return total

@jit(nopython=True, cache=True)
def _two_opt_delta_atsp_numba(route: np.ndarray, dist_matrix: np.ndarray, i: int, j: int) -> float:
    """Calculate the change in ATSP tour length for reversing the segment route[i+1 : j+1]."""
    n = len(route)
    a = route[i]
    b = route[(i + 1) % n]
    c = route[j]
    d = route[(j + 1) % n]
    
    original_cost = dist_matrix[a, b] + dist_matrix[c, d]
    new_cost = dist_matrix[a, c] + dist_matrix[b, d]
    
    delta = new_cost - original_cost
    for k in range(i + 1, j):
        delta += dist_matrix[route[k + 1], route[k]] - dist_matrix[route[k], route[k + 1]]
        
    return delta

@jit(nopython=True, cache=True)
def _apply_two_opt_numba(route: np.ndarray, i: int, j: int) -> np.ndarray:
    new_route = route.copy()
    left, right = i + 1, j
    while left < right:
        new_route[left], new_route[right] = new_route[right], new_route[left]
        left += 1
        right -= 1
    return new_route

@jit(nopython=True, cache=True)
def _two_opt_improve_atsp_numba(route: np.ndarray, dist_matrix: np.ndarray,
                                max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
    n = len(route)
    if n < 4:
        return route.copy(), _calculate_tour_length_atsp_numba(route, dist_matrix)
        
    best_route = route.copy()
    best_length = _calculate_tour_length_atsp_numba(best_route, dist_matrix)
    improved = True
    iters = 0
    
    while improved and iters < max_iterations:
        improved = False
        iters += 1
        
        for i in range(n - 2):
            for j in range(i + 2, n):
                delta = _two_opt_delta_atsp_numba(best_route, dist_matrix, i, j)
                if delta < -1e-8:
                    best_route = _apply_two_opt_numba(best_route, i, j)
                    best_length += delta
                    improved = True
                    if first_improvement:
                        break
            if improved and first_improvement:
                break
                
        if iters % 10 == 0:
            best_length = _calculate_tour_length_atsp_numba(best_route, dist_matrix)
            
    return best_route, best_length


@jit(nopython=True, cache=True)
def _or_opt_improve_atsp_numba(route: np.ndarray, dist_matrix: np.ndarray,
                          max_iterations: int, max_segment_size: int) -> Tuple[np.ndarray, float]:
    n = len(route)
    if n < 4:
        return route.copy(), _calculate_tour_length_atsp_numba(route, dist_matrix)
    
    best_route = route.copy()
    best_length = _calculate_tour_length_atsp_numba(best_route, dist_matrix)
    improved = True
    iterations = 0
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for seg_size in range(1, min(max_segment_size, n - 2) + 1):
            for i in range(1, n - seg_size + 1):
                segment = best_route[i:i + seg_size].copy()
                
                remaining = np.zeros(n - seg_size, dtype=np.int64)
                pos = 0
                for p in range(i):
                    remaining[pos] = best_route[p]
                    pos += 1
                for p in range(i + seg_size, n):
                    remaining[pos] = best_route[p]
                    pos += 1
                
                for j in range(1, len(remaining) + 1):
                    if j == i:
                        continue
                    
                    new_route = np.zeros(n, dtype=np.int64)
                    pos = 0
                    for p in range(j):
                        new_route[pos] = remaining[p]
                        pos += 1
                    for p in range(seg_size):
                        new_route[pos] = segment[p]
                        pos += 1
                    for p in range(j, len(remaining)):
                        new_route[pos] = remaining[p]
                        pos += 1
                    
                    new_length = _calculate_tour_length_atsp_numba(new_route, dist_matrix)
                    if new_length < best_length - 1e-8:
                        best_route = new_route.copy()
                        best_length = new_length
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break
    return best_route, best_length

# ----- Convenience wrappers that accept Python lists -----
def _prepare_route(route_list: List[int]) -> np.ndarray:
    """Prepares route for ATSP. If 0 is missing, prepend it. If present, rotate to index 0."""
    if 0 not in route_list:
        return np.array([0] + route_list, dtype=np.int64)
    
    idx = route_list.index(0)
    rotated = route_list[idx:] + route_list[:idx]
    return np.array(rotated, dtype=np.int64)

def _extract_route(improved_route: np.ndarray, original_list: List[int]) -> List[int]:
    """Returns route in the same format as it was given."""
    if 0 not in original_list:
        return improved_route[1:].tolist()
    return improved_route.tolist()

def nb_two_opt(student_nodes: List[int], dist_matrix_2d: List[List[float]],
               max_iterations: int, first_improvement: bool) -> Tuple[List[int], float]:
    route = _prepare_route(student_nodes)
    dm = np.array(dist_matrix_2d, dtype=np.float64)
    improved_route, length = _two_opt_improve_atsp_numba(route, dm, max_iterations, first_improvement)
    return _extract_route(improved_route, student_nodes), float(length)

def nb_three_opt(student_nodes: List[int], dist_matrix_2d: List[List[float]],
                 max_iterations: int, first_improvement: bool) -> Tuple[List[int], float]:
    return nb_two_opt(student_nodes, dist_matrix_2d, max_iterations, first_improvement)

def nb_or_opt(student_nodes: List[int], dist_matrix_2d: List[List[float]],
              max_iterations: int, max_segment_size: int) -> Tuple[List[int], float]:
    route = _prepare_route(student_nodes)
    dm = np.array(dist_matrix_2d, dtype=np.float64)
    improved_route, length = _or_opt_improve_atsp_numba(route, dm, max_iterations, max_segment_size)
    return _extract_route(improved_route, student_nodes), float(length)

