"""
NUMBA-OPTIMIZED Local Search Module for TSP/CVRP/CVRPTW

This module provides Numba JIT-compiled versions of local search algorithms
for significant performance improvements (10-50x speedup).

Requirements:
    - numba package: pip install numba
    - numpy package: pip install numpy

Usage:
    Use this module the same way as local_search.py, but with significant
    performance improvements for large-scale problems.

Note:
    - First run will be slower due to JIT compilation
    - Subsequent runs will be much faster
    - Works with CPython only (not PyPy)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Callable, Any
from enum import Enum
import os
import random
import time
import numpy as np

# Numba imports with fallback
try:
    from numba import jit, prange, set_num_threads, get_num_threads
    import numba
    NUMBA_AVAILABLE = True
    # Set number of threads for parallel execution
    try:
        set_num_threads(min(4, numba.config.NUMBA_NUM_THREADS))
    except (AttributeError, RuntimeError):
        pass  # FIX-06: Numba config may not expose NUMBA_NUM_THREADS in all builds
    # Numba disk cache — use a stable, project-local directory so that
    # multiprocessing workers can share pre-compiled JIT artefacts.
    # Falls back gracefully when the directory cannot be created.
    _cache_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".numba_cache")
    try:
        os.makedirs(_cache_base, exist_ok=True)
    except (OSError, PermissionError):
        _cache_base = os.path.join(os.path.expanduser("~"), ".UniRide_numba_cache")
        os.makedirs(_cache_base, exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", _cache_base)
except ImportError:
    NUMBA_AVAILABLE = False
    # Fallback: create a no-op decorator
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    prange = range
    print("[WARNING] Numba not available. Using pure Python (slower). Install with: pip install numba")


# ============================================================
# DISTANCE MATRIX CACHE (module-level, shared across LS classes)
# ============================================================
# Key: (frozenset_of_location_strings, id_of_duration_func)
# Value: (index_map: dict, dist_matrix: np.ndarray, unique_locs: list)
#
# Motivation: _prepare_numba_inputs() rebuilds an O(n²) distance matrix
# on EVERY improve() call.  For metaheuristics that call improve() hundreds
# of times on the same problem instance this is the dominant overhead.
# Cache size is bounded in practice (one entry per problem × algorithm).
_DIST_MATRIX_CACHE: Dict[Tuple, Any] = {}
import threading as _threading
_DIST_MATRIX_CACHE_LOCK = _threading.Lock()


def _get_cached_matrix(key: Tuple):
    with _DIST_MATRIX_CACHE_LOCK:
        return _DIST_MATRIX_CACHE.get(key)


def _set_cached_matrix(key: Tuple, value: Any) -> None:
    with _DIST_MATRIX_CACHE_LOCK:
        _DIST_MATRIX_CACHE[key] = value


def _build_or_get_dist_matrix(
    route: List[str],
    duration_func: Callable
) -> Tuple[Dict[str, int], np.ndarray, List[str]]:
    """
    Build (or retrieve from cache) the distance matrix for `route`.

    Cache key is based on the *set* of locations in the route plus the
    identity of the duration_func object, so that different problems (or
    different function instances) never share a matrix.

    Fast path (Step 4): if the duration_func was built by create_np_duration_func()
    it carries a pre-built numpy array in _np_dist_matrix / _np_unique_locs.
    We reuse that array directly, avoiding the O(n²) call-by-call reconstruction.

    Returns:
        index_map  – {location: integer_index}
        dist_matrix – np.ndarray shape (n, n)
        unique_locs – ordered list matching index_map
    """
    unique_locs = list(dict.fromkeys(route))
    cache_key = (frozenset(unique_locs), id(duration_func))

    cached = _get_cached_matrix(cache_key)
    if cached is not None:
        return cached

    # Step 4 fast path: numpy-backed duration_func already has the matrix.
    if hasattr(duration_func, '_np_dist_matrix') and hasattr(duration_func, '_np_unique_locs'):
        prebuilt_locs: List[str] = duration_func._np_unique_locs  # type: ignore[attr-defined]
        prebuilt_dm: np.ndarray = duration_func._np_dist_matrix   # type: ignore[attr-defined]
        # Re-order if route's unique_locs ordering differs (e.g. shuffled route)
        if prebuilt_locs == unique_locs:
            index_map = {loc: i for i, loc in enumerate(unique_locs)}
            result = (index_map, prebuilt_dm, unique_locs)
        else:
            # Build a reordering view so indices match unique_locs
            src_map = {loc: i for i, loc in enumerate(prebuilt_locs)}
            index_map = {loc: i for i, loc in enumerate(unique_locs)}
            n = len(unique_locs)
            dist_matrix = np.zeros((n, n), dtype=np.float64)
            for i, loc_i in enumerate(unique_locs):
                for j, loc_j in enumerate(unique_locs):
                    if i != j:
                        dist_matrix[i, j] = prebuilt_dm[src_map[loc_i], src_map[loc_j]]
            result = (index_map, dist_matrix, unique_locs)
        _set_cached_matrix(cache_key, result)
        return result

    # Standard path: build matrix by querying the duration_func.
    n = len(unique_locs)
    index_map = {loc: i for i, loc in enumerate(unique_locs)}
    dist_matrix = np.zeros((n, n), dtype=np.float64)
    for i, loc_i in enumerate(unique_locs):
        for j, loc_j in enumerate(unique_locs):
            if i != j:
                dist_matrix[i, j] = duration_func([loc_i, loc_j]) - duration_func([loc_i])
    # Diagonal already 0 by np.zeros

    result = (index_map, dist_matrix, unique_locs)
    _set_cached_matrix(cache_key, result)
    return result




class LocalSearchType(str, Enum):
    """Available local search types"""
    NONE = "none"
    TWO_OPT = "two_opt"
    THREE_OPT = "three_opt"
    OR_OPT = "or_opt"
    SWAP = "swap"
    CROSS_EXCHANGE = "cross_exchange"
    TIME_WINDOW_AWARE = "time_window_aware"
    HYBRID = "hybrid"


# ============================================================
# NUMBA-OPTIMIZED CORE FUNCTIONS
# ============================================================

@jit(nopython=True, cache=True)
def _calculate_tour_length_numba(route: np.ndarray, dist_matrix: np.ndarray) -> float:
    """
    Calculate total tour length using precomputed distance matrix.
    
    Args:
        route: 1D array of node indices (0-based)
        dist_matrix: 2D distance matrix
    
    Returns:
        Total tour length (including return to start)
    """
    n = len(route)
    if n < 2:
        return 0.0
    
    total = 0.0
    for i in range(n - 1):
        total += dist_matrix[route[i], route[i + 1]]
    
    # Return to start
    total += dist_matrix[route[n - 1], route[0]]
    return total


@jit(nopython=True, cache=True)
def _two_opt_delta_numba(route: np.ndarray, dist_matrix: np.ndarray, i: int, j: int) -> float:
    """
    ATSP-aware 2-opt delta.
    
    Reverses segment route[i+1 : j+1]. For asymmetric distances, every
    internal edge inside the reversed segment must have its cost corrected
    (d[a,b] becomes d[b,a]). For symmetric distances the correction loop
    sums to zero, so the formula is safe for both TSP and ATSP.
    """
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
    """
    Apply 2-opt move: reverse segment between i+1 and j.
    """
    new_route = route.copy()
    # Reverse segment [i+1, j]
    left = i + 1
    right = j
    while left < right:
        new_route[left], new_route[right] = new_route[right], new_route[left]
        left += 1
        right -= 1
    return new_route


@jit(nopython=True, cache=True)
def _two_opt_improve_numba(route: np.ndarray, dist_matrix: np.ndarray, 
                           max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
    """
    Numba-optimized 2-opt local search.
    
    FIX: Removed unnecessary skip condition that was dead code.
    The loop structure (j starting at i+2) already prevents invalid moves.
    
    Returns:
        Tuple of (improved_route, best_length)
    """
    n = len(route)
    if n < 4:
        return route.copy(), _calculate_tour_length_numba(route, dist_matrix)
    
    best_route = route.copy()
    best_length = _calculate_tour_length_numba(best_route, dist_matrix)
    
    improved = True
    iterations = 0
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for i in range(n - 2):
            for j in range(i + 2, n):
                # FIX: Removed dead code condition: if j == n - 1 and i == 0: continue
                # The loop structure already prevents invalid moves
                
                delta = _two_opt_delta_numba(best_route, dist_matrix, i, j)
                
                if delta < -1e-10:  # Improvement found
                    best_route = _apply_two_opt_numba(best_route, i, j)
                    best_length += delta
                    improved = True
                    
                    if first_improvement:
                        break
            
            if improved and first_improvement:
                break
        
        # Periodically recalculate tour length unconditionally to correct any
        # floating-point error accumulated via best_length += delta (in either direction).
        if iterations % 10 == 0:
            best_length = _calculate_tour_length_numba(best_route, dist_matrix)
    
    return best_route, best_length


@jit(nopython=True, cache=True)
def _three_opt_cases_numba(route: np.ndarray, i: int, j: int, k: int) -> np.ndarray:
    """
    Generate all 7 3-opt reconnection patterns and return the best one.
    
    Returns:
        Array of shape (7, n) containing all candidate routes
    """
    n = len(route)
    
    # Segments
    A_end = i + 1
    B_start = i + 1
    B_end = j + 1
    C_start = j + 1
    C_end = k + 1
    D_start = k + 1
    
    candidates = np.zeros((7, n), dtype=np.int64)
    
    for idx in range(7):
        pos = 0
        # Segment A: [0, i+1]
        for p in range(i + 1):
            candidates[idx, pos] = route[p]
            pos += 1
        
        if idx == 0:
            # Case 1: A + B' + C' + D
            for p in range(j, i, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k, j, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k + 1, n):
                candidates[idx, pos] = route[p]
                pos += 1
        elif idx == 1:
            # Case 2: A + B' + C + D
            for p in range(j, i, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(j + 1, k + 1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k + 1, n):
                candidates[idx, pos] = route[p]
                pos += 1
        elif idx == 2:
            # Case 3: A + B + C' + D
            for p in range(i + 1, j + 1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k, j, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k + 1, n):
                candidates[idx, pos] = route[p]
                pos += 1
        elif idx == 3:
            # Case 4: A + B' + C + D'
            for p in range(j, i, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(j + 1, k + 1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(n - 1, k, -1):
                candidates[idx, pos] = route[p]
                pos += 1
        elif idx == 4:
            # Case 5: A + B + C' + D'
            for p in range(i + 1, j + 1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k, j, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(n - 1, k, -1):
                candidates[idx, pos] = route[p]
                pos += 1
        elif idx == 5:
            # Case 6: A + B' + C' + D'
            for p in range(j, i, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k, j, -1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(n - 1, k, -1):
                candidates[idx, pos] = route[p]
                pos += 1
        else:
            # Case 7: Original (A + B + C + D)
            for p in range(i + 1, j + 1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(j + 1, k + 1):
                candidates[idx, pos] = route[p]
                pos += 1
            for p in range(k + 1, n):
                candidates[idx, pos] = route[p]
                pos += 1
    
    return candidates


@jit(nopython=True, cache=True)
def _three_opt_improve_numba(route: np.ndarray, dist_matrix: np.ndarray,
                             max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
    """
    Numba-optimized 3-opt local search.
    """
    n = len(route)
    if n < 6:
        # Fall back to 2-opt
        return _two_opt_improve_numba(route, dist_matrix, max_iterations, first_improvement)
    
    best_route = route.copy()
    best_length = _calculate_tour_length_numba(best_route, dist_matrix)
    
    improved = True
    iterations = 0
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for i in range(n - 4):
            j_max = min(n - 2, i + 12)
            for j in range(i + 2, j_max + 1):
                k_max = min(n - 1, j + 12)
                for k in range(j + 2, k_max + 1):
                    candidates = _three_opt_cases_numba(best_route, i, j, k)
                    
                    for c in range(7):
                        cand_length = _calculate_tour_length_numba(candidates[c], dist_matrix)
                        
                        if cand_length < best_length - 1e-10 * max(1.0, best_length):
                            best_route = candidates[c].copy()
                            best_length = cand_length
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


@jit(nopython=True, cache=True)
def _or_opt_improve_numba(route: np.ndarray, dist_matrix: np.ndarray,
                          max_iterations: int, max_segment_size: int) -> Tuple[np.ndarray, float]:
    """
    Numba-optimized Or-opt local search.
    
    FIX: Corrected index mapping in insertion logic to properly handle relocated segments.
    """
    n = len(route)
    if n < 4:
        return route.copy(), _calculate_tour_length_numba(route, dist_matrix)
    
    best_route = route.copy()
    best_length = _calculate_tour_length_numba(best_route, dist_matrix)
    
    improved = True
    iterations = 0
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for seg_size in range(1, min(max_segment_size, n - 1) + 1):
            for i in range(n - seg_size + 1):
                # Extract segment
                segment = best_route[i:i + seg_size].copy()
                
                # Create route without segment
                remaining = np.zeros(n - seg_size, dtype=np.int64)
                pos = 0
                for p in range(i):
                    remaining[pos] = best_route[p]
                    pos += 1
                for p in range(i + seg_size, n):
                    remaining[pos] = best_route[p]
                    pos += 1
                
                # Try inserting at each position in remaining array
                for j in range(len(remaining) + 1):
                    # FIX: Calculate correct skip for original position
                    # After removing segment from positions [i, i+seg_size),
                    # the insertion should skip if j would recreate the original tour
                    if j == i:
                        continue
                    
                    # Create new route by inserting segment at position j in remaining
                    new_route = np.zeros(n, dtype=np.int64)
                    pos = 0
                    # Copy nodes before insertion point
                    for p in range(j):
                        new_route[pos] = remaining[p]
                        pos += 1
                    # Insert segment
                    for p in range(seg_size):
                        new_route[pos] = segment[p]
                        pos += 1
                    # Copy nodes after insertion point
                    for p in range(j, len(remaining)):
                        new_route[pos] = remaining[p]
                        pos += 1
                    
                    new_length = _calculate_tour_length_numba(new_route, dist_matrix)
                    
                    if new_length < best_length - 1e-10 * max(1.0, best_length):
                        best_route = new_route.copy()
                        best_length = new_length
                        improved = True
                        break
                
                if improved:
                    break
            if improved:
                break
    
    return best_route, best_length


@jit(nopython=True, cache=True)
def _swap_improve_numba(route: np.ndarray, dist_matrix: np.ndarray,
                        max_iterations: int, first_improvement: bool) -> Tuple[np.ndarray, float]:
    """
    Numba-optimized Swap local search.
    
    FIXED: Removed skip condition for adjacent swaps - these ARE valid moves in TSP
    and can lead to improvements, especially when combined with other operators.
    """
    n = len(route)
    if n < 3:
        return route.copy(), _calculate_tour_length_numba(route, dist_matrix)
    
    best_route = route.copy()
    best_length = _calculate_tour_length_numba(best_route, dist_matrix)
    
    improved = True
    iterations = 0
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for i in range(n):
            for j in range(i + 1, n):
                # FIX: Try ALL swap pairs, including adjacent ones
                # Removed: if j == i + 1: continue
                
                # Perform swap
                new_route = best_route.copy()
                new_route[i], new_route[j] = new_route[j], new_route[i]
                
                new_length = _calculate_tour_length_numba(new_route, dist_matrix)
                
                if new_length < best_length - 1e-10 * max(1.0, best_length):
                    best_route = new_route.copy()
                    best_length = new_length
                    improved = True
                    
                    if first_improvement:
                        break
            
            if improved and first_improvement:
                break
    
    return best_route, best_length


@jit(nopython=True, cache=True)
def _cross_exchange_improve_numba(route: np.ndarray, dist_matrix: np.ndarray,
                                  max_iterations: int, max_segment_size: int,
                                  first_improvement: bool) -> Tuple[np.ndarray, float]:
    """
    Numba-optimized Cross Exchange local search.
    """
    n = len(route)
    if n < 5:
        # Fall back to swap
        return _swap_improve_numba(route, dist_matrix, max_iterations, first_improvement)
    
    best_route = route.copy()
    best_length = _calculate_tour_length_numba(best_route, dist_matrix)
    
    improved = True
    iterations = 0
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for seg1_len in range(1, min(max_segment_size, n // 2) + 1):
            for seg2_len in range(1, min(max_segment_size, n // 2) + 1):
                for i in range(n - seg1_len):
                    for j in range(i + seg1_len, n - seg2_len + 1):
                        # Check overlap
                        if i + seg1_len > j:
                            continue
                        
                        # Extract segments
                        seg1 = best_route[i:i + seg1_len].copy()
                        seg2 = best_route[j:j + seg2_len].copy()
                        
                        # Build new route with exchanged segments.
                        # Note: swapping segments of different sizes preserves total length n
                        # because seg1_len nodes are replaced by seg2_len and vice-versa.
                        new_route = np.zeros(n, dtype=np.int64)
                        
                        # Different segment lengths need careful handling
                        if seg1_len == seg2_len:
                            new_route = best_route.copy()
                            for p in range(seg1_len):
                                new_route[i + p] = seg2[p]
                                new_route[j + p] = seg1[p]
                        else:
                            # Complex case - need to rebuild route
                            pos = 0
                            # Part before first segment
                            for p in range(i):
                                new_route[pos] = best_route[p]
                                pos += 1
                            # Insert second segment
                            for p in range(seg2_len):
                                new_route[pos] = seg2[p]
                                pos += 1
                            # Part between segments
                            for p in range(i + seg1_len, j):
                                new_route[pos] = best_route[p]
                                pos += 1
                            # Insert first segment
                            for p in range(seg1_len):
                                new_route[pos] = seg1[p]
                                pos += 1
                            # Part after second segment
                            for p in range(j + seg2_len, n):
                                new_route[pos] = best_route[p]
                                pos += 1
                            # pos == n is guaranteed: swapping segments keeps total length
                        
                        new_length = _calculate_tour_length_numba(new_route, dist_matrix)
                        
                        if new_length < best_length - 1e-10 * max(1.0, best_length):
                            best_route = new_route.copy()
                            best_length = new_length
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


# ============================================================
# WRAPPER CLASSES (Compatible with original API)
# ============================================================

class BaseLocalSearch(ABC):
    """Abstract base class for local search algorithms"""

    @abstractmethod
    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """
        Improve a route using local search.

        Args:
            route: Current route as list of location codes
            duration_func: Function that calculates route duration

        Returns:
            Tuple of (improved_route, improved_duration)
        """
        pass


class TwoOptLocalSearch(BaseLocalSearch):
    """
    2-opt Local Search - Numba Optimized Version.
    
    Performance: 10-50x faster than pure Python version.
    """

    def __init__(self, max_iterations: int = 1000, first_improvement: bool = False):
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self._index_map = None
        self._dist_matrix = None

    def _prepare_numba_inputs(self, route: List[str], duration_func: Callable) -> Tuple[np.ndarray, np.ndarray]:
        """Convert route and duration function to Numba-compatible format.

        Uses module-level _build_or_get_dist_matrix() to avoid O(n²) rebuild
        on every improve() call for the same problem (Step 3).

        Stores self._unique_locs so that _indices_to_route uses the same
        ordering as the cached distance matrix index_map.
        """
        self._index_map, self._dist_matrix, self._unique_locs = _build_or_get_dist_matrix(route, duration_func)
        route_indices = np.array([self._index_map[loc] for loc in route], dtype=np.int64)
        return route_indices, self._dist_matrix

    def _indices_to_route(self, route_indices: np.ndarray, original_route: List[str]) -> List[str]:
        """Convert indices back to route strings using cached location ordering."""
        return [self._unique_locs[idx] for idx in route_indices]

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using Numba-optimized 2-opt"""
        if len(route) < 3:
            return route, duration_func(route)
        
        # Prepare inputs
        route_indices, dist_matrix = self._prepare_numba_inputs(route, duration_func)
        
        # Run Numba-optimized algorithm
        improved_indices, _ = _two_opt_improve_numba(
            route_indices, dist_matrix, self.max_iterations, self.first_improvement
        )
        
        # Convert back
        improved_route = self._indices_to_route(improved_indices, route)
        improved_duration = duration_func(improved_route)
        
        return improved_route, improved_duration


class ThreeOptLocalSearch(BaseLocalSearch):
    """
    3-opt Local Search - Numba Optimized Version.
    
    Performance: 10-50x faster than pure Python version.
    """

    def __init__(self, max_iterations: int = 500, first_improvement: bool = False):
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self._index_map = None

    def _prepare_numba_inputs(self, route: List[str], duration_func: Callable) -> Tuple[np.ndarray, np.ndarray]:
        """Convert route and duration function to Numba-compatible format (cached)."""
        self._index_map, self._dist_matrix, self._unique_locs = _build_or_get_dist_matrix(route, duration_func)
        route_indices = np.array([self._index_map[loc] for loc in route], dtype=np.int64)
        return route_indices, self._dist_matrix

    def _indices_to_route(self, route_indices: np.ndarray, original_route: List[str]) -> List[str]:
        return [self._unique_locs[idx] for idx in route_indices]

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        """Improve route using Numba-optimized 3-opt"""
        if len(route) < 4:
            two_opt = TwoOptLocalSearch(self.max_iterations)
            return two_opt.improve(route, duration_func)
        
        route_indices, dist_matrix = self._prepare_numba_inputs(route, duration_func)
        
        improved_indices, _ = _three_opt_improve_numba(
            route_indices, dist_matrix, self.max_iterations, self.first_improvement
        )
        
        improved_route = self._indices_to_route(improved_indices, route)
        improved_duration = duration_func(improved_route)
        
        return improved_route, improved_duration


class OrOptLocalSearch(BaseLocalSearch):
    """
    Or-opt Local Search - Numba Optimized Version.
    """

    def __init__(self, max_iterations: int = 500, max_segment_size: int = 3):
        self.max_iterations = max_iterations
        self.max_segment_size = min(max_segment_size, 3)
        self._index_map = None

    def _prepare_numba_inputs(self, route: List[str], duration_func: Callable) -> Tuple[np.ndarray, np.ndarray]:
        """Convert route and duration function to Numba-compatible format (cached)."""
        self._index_map, self._dist_matrix, self._unique_locs = _build_or_get_dist_matrix(route, duration_func)
        return np.array([self._index_map[loc] for loc in route], dtype=np.int64), self._dist_matrix

    def _indices_to_route(self, route_indices: np.ndarray, original_route: List[str]) -> List[str]:
        return [self._unique_locs[idx] for idx in route_indices]

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        if len(route) < 4:
            return route, duration_func(route)
        
        route_indices, dist_matrix = self._prepare_numba_inputs(route, duration_func)
        
        improved_indices, _ = _or_opt_improve_numba(
            route_indices, dist_matrix, self.max_iterations, self.max_segment_size
        )
        
        improved_route = self._indices_to_route(improved_indices, route)
        improved_duration = duration_func(improved_route)
        
        return improved_route, improved_duration


class SwapLocalSearch(BaseLocalSearch):
    """
    Swap Local Search - Numba Optimized Version.
    """

    def __init__(self, max_iterations: int = 500, first_improvement: bool = False):
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self._index_map = None

    def _prepare_numba_inputs(self, route: List[str], duration_func: Callable) -> Tuple[np.ndarray, np.ndarray]:
        """Convert route and duration function to Numba-compatible format (cached)."""
        self._index_map, self._dist_matrix, self._unique_locs = _build_or_get_dist_matrix(route, duration_func)
        return np.array([self._index_map[loc] for loc in route], dtype=np.int64), self._dist_matrix

    def _indices_to_route(self, route_indices: np.ndarray, original_route: List[str]) -> List[str]:
        return [self._unique_locs[idx] for idx in route_indices]

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        if len(route) < 3:
            return route, duration_func(route)
        
        route_indices, dist_matrix = self._prepare_numba_inputs(route, duration_func)
        
        improved_indices, _ = _swap_improve_numba(
            route_indices, dist_matrix, self.max_iterations, self.first_improvement
        )
        
        improved_route = self._indices_to_route(improved_indices, route)
        improved_duration = duration_func(improved_route)
        
        return improved_route, improved_duration


class CrossExchangeLocalSearch(BaseLocalSearch):
    """
    Cross Exchange Local Search - Numba Optimized Version.
    """

    def __init__(
        self,
        max_iterations: int = 300,
        max_segment_size: int = 2,
        first_improvement: bool = False
    ):
        self.max_iterations = max_iterations
        self.max_segment_size = min(max_segment_size, 3)
        self.first_improvement = first_improvement
        self._index_map = None

    def _prepare_numba_inputs(self, route: List[str], duration_func: Callable) -> Tuple[np.ndarray, np.ndarray]:
        """Convert route and duration function to Numba-compatible format (cached)."""
        self._index_map, self._dist_matrix, self._unique_locs = _build_or_get_dist_matrix(route, duration_func)
        return np.array([self._index_map[loc] for loc in route], dtype=np.int64), self._dist_matrix

    def _indices_to_route(self, route_indices: np.ndarray, original_route: List[str]) -> List[str]:
        return [self._unique_locs[idx] for idx in route_indices]

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float]
    ) -> Tuple[List[str], float]:
        if len(route) < 5:
            swap_ls = SwapLocalSearch(self.max_iterations)
            return swap_ls.improve(route, duration_func)
        
        route_indices, dist_matrix = self._prepare_numba_inputs(route, duration_func)
        
        improved_indices, _ = _cross_exchange_improve_numba(
            route_indices, dist_matrix, self.max_iterations, self.max_segment_size, self.first_improvement
        )
        
        improved_route = self._indices_to_route(improved_indices, route)
        improved_duration = duration_func(improved_route)
        
        return improved_route, improved_duration


class TimeWindowAwareLocalSearch(BaseLocalSearch):
    """
    Time Window Aware Local Search for CVRPTW.
    
    Note: Uses hybrid approach with Numba-optimized 2-opt and swap.
    """

    def __init__(
        self,
        max_iterations: int = 500,
        tw_penalty: float = 100.0,
        first_improvement: bool = False
    ):
        self.max_iterations = max_iterations
        self.tw_penalty = tw_penalty
        self.first_improvement = first_improvement

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float],
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
        arrival_times: Optional[Dict[str, float]] = None
    ) -> Tuple[List[str], float]:
        """Improve route considering time windows."""
        if len(route) < 3:
            return route, duration_func(route)

        # If no time window info, fall back to regular 2-opt
        if time_windows is None or arrival_times is None:
            two_opt = TwoOptLocalSearch(self.max_iterations)
            return two_opt.improve(route, duration_func)

        # Use pure Python for time window aware optimization
        # (Numba doesn't handle this well)
        best_route = route.copy()
        best_duration = duration_func(best_route)

        improved = True
        iterations = 0

        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1

            # Try 2-opt moves
            for i in range(len(best_route) - 1):
                for j in range(i + 2, len(best_route)):
                    new_route = best_route[:i]
                    new_route.extend(reversed(best_route[i:j + 1]))
                    new_route.extend(best_route[j + 1:])

                    new_duration = duration_func(new_route)

                    if new_duration < best_duration:
                        best_route = new_route
                        best_duration = new_duration
                        improved = True

                        if self.first_improvement:
                            break

                if improved and self.first_improvement:
                    break

        return best_route, best_duration


class HybridLocalSearch(BaseLocalSearch):
    """
    Hybrid Local Search - Numba Optimized Version.
    
    Applies multiple local search methods in sequence.
    Uses Numba-optimized implementations for each method.
    
    UPDATED (2024-04):
        - Changed to cycle-based approach (max_iterations = number of cycles)
        - Updated internal iteration limits for better performance
    """

    DEFAULT_ITERATION_LIMITS: Dict[LocalSearchType, int] = {
        LocalSearchType.SWAP: 100,
        LocalSearchType.TWO_OPT: 80,
        LocalSearchType.OR_OPT: 60,
        LocalSearchType.CROSS_EXCHANGE: 40,
        LocalSearchType.THREE_OPT: 25,
        LocalSearchType.TIME_WINDOW_AWARE: 50,
    }

    def __init__(
        self,
        methods: Optional[List[LocalSearchType]] = None,
        max_iterations: int = 5,
        use_random_order: bool = False,
        include_cross_exchange: bool = True,
        include_time_window: bool = True,
        iteration_limits: Optional[Dict[LocalSearchType, int]] = None,
    ):
        if methods is None:
            self.methods = [
                LocalSearchType.SWAP,
                LocalSearchType.TWO_OPT,
                LocalSearchType.OR_OPT,
                LocalSearchType.CROSS_EXCHANGE,
                LocalSearchType.THREE_OPT,
            ]
            if include_time_window:
                self.methods.append(LocalSearchType.TIME_WINDOW_AWARE)
        else:
            self.methods = methods
        self.max_iterations = max_iterations
        self.use_random_order = use_random_order
        self.include_cross_exchange = include_cross_exchange
        self.include_time_window = include_time_window
        self.iteration_limits = {**self.DEFAULT_ITERATION_LIMITS, **(iteration_limits or {})}
        self.rng = random.Random()

    def improve(
        self,
        route: List[str],
        duration_func: Callable[[List[str]], float],
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
        arrival_times: Optional[Dict[str, float]] = None
    ) -> Tuple[List[str], float]:
        if len(route) < 3:
            return route, duration_func(route)

        current_route = route.copy()
        current_duration = duration_func(current_route)

        methods = list(self.methods)
        has_time_windows = time_windows is not None and arrival_times is not None

        if not has_time_windows:
            methods = [m for m in methods if m != LocalSearchType.TIME_WINDOW_AWARE]

        if self.use_random_order:
            self.rng.shuffle(methods)

        for iteration in range(self.max_iterations):
            improved_this_round = False

            for method in methods:
                max_iter = self.iteration_limits.get(method, 30)

                if method == LocalSearchType.TWO_OPT:
                    ls = TwoOptLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.THREE_OPT:
                    ls = ThreeOptLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.OR_OPT:
                    ls = OrOptLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.SWAP:
                    ls = SwapLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.CROSS_EXCHANGE:
                    ls = CrossExchangeLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(current_route, duration_func)
                elif method == LocalSearchType.TIME_WINDOW_AWARE:
                    ls = TimeWindowAwareLocalSearch(max_iterations=max_iter)
                    new_route, new_duration = ls.improve(
                        current_route, duration_func, time_windows, arrival_times
                    )
                else:
                    continue

                if new_duration < current_duration:
                    current_route = new_route
                    current_duration = new_duration
                    improved_this_round = True

            if not improved_this_round:
                break

        return current_route, current_duration


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def get_local_search(
    local_search_type: LocalSearchType = LocalSearchType.TWO_OPT,
    **kwargs
) -> Optional[BaseLocalSearch]:
    """
    Factory function to get local search instance.
    """
    ls_map = {
        LocalSearchType.NONE: None,
        LocalSearchType.TWO_OPT: TwoOptLocalSearch,
        LocalSearchType.THREE_OPT: ThreeOptLocalSearch,
        LocalSearchType.OR_OPT: OrOptLocalSearch,
        LocalSearchType.SWAP: SwapLocalSearch,
        LocalSearchType.CROSS_EXCHANGE: CrossExchangeLocalSearch,
        LocalSearchType.TIME_WINDOW_AWARE: TimeWindowAwareLocalSearch,
        LocalSearchType.HYBRID: HybridLocalSearch,
    }

    ls_class = ls_map.get(local_search_type)

    if ls_class is None:
        return None

    return ls_class(**kwargs)


def apply_local_search(
    route: List[str],
    duration_func: Callable[[List[str]], float],
    local_search_type: LocalSearchType = LocalSearchType.TWO_OPT,
    time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
    arrival_times: Optional[Dict[str, float]] = None,
    **kwargs
) -> Tuple[List[str], float]:
    """
    Convenience function to apply local search to a route.
    """
    if local_search_type == LocalSearchType.NONE:
        return route, duration_func(route)

    ls = get_local_search(local_search_type, **kwargs)

    if ls is None:
        return route, duration_func(route)

    if local_search_type == LocalSearchType.TIME_WINDOW_AWARE:
        return ls.improve(route, duration_func, time_windows, arrival_times)
    elif local_search_type == LocalSearchType.HYBRID:
        return ls.improve(route, duration_func, time_windows, arrival_times)

    return ls.improve(route, duration_func)


# ============================================================
# DIRECT NUMBA FUNCTIONS (for maximum performance)
# ============================================================

def improve_route_numba(
    route: np.ndarray,
    dist_matrix: np.ndarray,
    ls_type: str = "two_opt",
    max_iterations: int = 500
) -> Tuple[np.ndarray, float]:
    """
    Direct Numba function for maximum performance.
    
    Args:
        route: 1D numpy array of node indices (0-based)
        dist_matrix: 2D numpy array distance matrix
        ls_type: "two_opt", "three_opt", "or_opt", "swap", or "hybrid"
        max_iterations: Maximum iterations
    
    Returns:
        Tuple of (improved_route, tour_length)
    
    Example:
        >>> route = np.array([0, 1, 2, 3, 4, 5])
        >>> dist_matrix = np.random.rand(6, 6)
        >>> improved, length = improve_route_numba(route, dist_matrix, "two_opt")
    """
    if ls_type == "two_opt":
        return _two_opt_improve_numba(route, dist_matrix, max_iterations, False)
    elif ls_type == "three_opt":
        return _three_opt_improve_numba(route, dist_matrix, max_iterations, False)
    elif ls_type == "or_opt":
        return _or_opt_improve_numba(route, dist_matrix, max_iterations, 3)
    elif ls_type == "swap":
        return _swap_improve_numba(route, dist_matrix, max_iterations, False)
    elif ls_type == "hybrid":
        # Apply methods in sequence
        best_route, best_length = _two_opt_improve_numba(route, dist_matrix, max_iterations // 3, False)
        best_route, best_length = _or_opt_improve_numba(best_route, dist_matrix, max_iterations // 3, 3)
        best_route, best_length = _three_opt_improve_numba(best_route, dist_matrix, max_iterations // 3, False)
        return best_route, best_length
    else:
        return _two_opt_improve_numba(route, dist_matrix, max_iterations, False)
