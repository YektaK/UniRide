"""
Numba-optimized core functions for TSP.

Provides JIT-compiled implementations of local search operators,
construction heuristics, and utility routines.

A pure-Python fallback is activated automatically when ``numba`` is
not installed in the environment.
"""

import numpy as np
from typing import Tuple

# ---------------------------------------------------------------------------
# Numba import with graceful fallback
# ---------------------------------------------------------------------------

try:
    from numba import jit  # noqa: F401
    import numba  # noqa: F401

    NUMBA_AVAILABLE = True
    # Disable caching — the package may be imported via symlink
    # which causes path mismatches in numba's pickle-based cache
    try:
        numba.config.DISABLE_JIT = False
    except Exception:
        pass
except ImportError:
    NUMBA_AVAILABLE = False

    # No-op decorator that preserves the original function unchanged
    def jit(*args, **kwargs):  # type: ignore[misc]
        """Fallback decorator when numba is not available."""
        def decorator(func):
            return func

        if len(args) == 1 and callable(args[0]):
            # Called without parentheses: @jit
            return args[0]
        # Called with parentheses: @jit(...)
        return decorator


# ===================================================================
# JIT-compiled functions
# ===================================================================

@jit(nopython=True)
def calc_tour_length_numba(route: np.ndarray, dist_matrix: np.ndarray) -> float:
    """Calculate total tour length including return to start.

    Args:
        route: 1-D array of 0-based node indices (dtype int64).
        dist_matrix: 2-D symmetric distance matrix (dtype float64).

    Returns:
        Total tour length as float.
    """
    n = len(route)
    if n < 2:
        return 0.0

    total = 0.0
    for i in range(n - 1):
        total += dist_matrix[route[i], route[i + 1]]
    total += dist_matrix[route[n - 1], route[0]]
    return total


@jit(nopython=True)
def two_opt_delta(route: np.ndarray, dist_matrix: np.ndarray,
                  i: int, j: int) -> float:
    """Compute the delta (change in cost) for a 2-opt reversal.

    Original edges:  A -> B  ...  C -> D
    After reversal:  A -> C  ...  B -> D

    Returns:
        ``new_cost - original_cost`` (negative ⇒ improvement).
    """
    n = len(route)
    a = route[i]
    b = route[(i + 1) % n]
    c = route[j]
    d = route[(j + 1) % n]

    original = dist_matrix[a, b] + dist_matrix[c, d]
    new_cost = dist_matrix[a, c] + dist_matrix[b, d]
    return new_cost - original


@jit(nopython=True)
def apply_two_opt(route: np.ndarray, i: int, j: int) -> np.ndarray:
    """Apply a 2-opt move by reversing the segment between ``i+1`` and ``j``.

    Returns:
        A new route array (the input is **not** modified).
    """
    new_route = route.copy()
    left = i + 1
    right = j
    while left < right:
        new_route[left], new_route[right] = new_route[right], new_route[left]
        left += 1
        right -= 1
    return new_route


@jit(nopython=True)
def two_opt_improve(route: np.ndarray, dist_matrix: np.ndarray,
                    max_iter: int, first_improvement: bool
                    ) -> Tuple[np.ndarray, float]:
    """Iterative 2-opt local search.

    Args:
        route: Initial tour (0-based, dtype int64).
        dist_matrix: Pairwise distance matrix (dtype float64).
        max_iter: Maximum outer-loop iterations.
        first_improvement: If True restart scanning after first improving move.

    Returns:
        ``(best_route, best_length)`` tuple.
    """
    n = len(route)
    if n < 4:
        return route.copy(), calc_tour_length_numba(route, dist_matrix)

    best_route = route.copy()
    best_length = calc_tour_length_numba(best_route, dist_matrix)

    improved = True
    iters = 0

    while improved and iters < max_iter:
        improved = False
        iters += 1

        for i in range(n - 2):
            for j in range(i + 2, n):
                # Skip the pair that would simply rotate the whole tour
                if j == n - 1 and i == 0:
                    continue

                delta = two_opt_delta(best_route, dist_matrix, i, j)

                if delta < -1e-10:
                    best_route = apply_two_opt(best_route, i, j)
                    best_length += delta
                    improved = True
                    if first_improvement:
                        break

            if improved and first_improvement:
                break

    return best_route, best_length


# -------------------------------------------------------------------
# 3-opt  (7 reconnection cases)
# -------------------------------------------------------------------

@jit(nopython=True)
def _three_opt_eval(route: np.ndarray, dist_matrix: np.ndarray,
                    i: int, j: int, k: int, case: int) -> float:
    """Evaluate one of the 7 3-opt reconnection cases and return its length.

    The tour is split into four segments:
        A = route[0 : i+1]
        B = route[i+1 : j+1]
        C = route[j+1 : k+1]
        D = route[k+1 : n]

    The 7 cases enumerate feasible reconnections (case 0 = original).
    """
    n = len(route)

    # Segment boundaries
    A_end = i + 1
    B_end = j + 1
    C_end = k + 1

    # Helper: compute cost for four-segment reconnection
    # Pre-compute the key transition costs
    # Segment starts / ends
    a_last = route[i]
    b_first = route[i + 1]
    b_last = route[j]
    c_first = route[j + 1]
    c_last = route[k]
    d_first = route[(k + 1) % n]

    # Original edges
    d_ab = dist_matrix[a_last, b_first]
    d_cd = dist_matrix[c_last, d_first]

    # Reversed edges
    d_ac = dist_matrix[a_last, c_first]
    d_bc = dist_matrix[b_last, c_first]
    d_bd = dist_matrix[b_last, d_first]
    d_ad = dist_matrix[a_last, d_first]

    # Compute segment-internal costs (these stay the same for B/C reversed)
    cost_A = 0.0
    for p in range(A_end):
        cost_A += dist_matrix[route[p], route[p + 1]]

    cost_B = 0.0
    for p in range(i + 1, B_end):
        cost_B += dist_matrix[route[p], route[p + 1]]

    cost_B_rev = 0.0
    for p in range(B_end - 1, i + 1, -1):
        cost_B_rev += dist_matrix[route[p], route[p - 1]]

    cost_C = 0.0
    for p in range(j + 1, C_end):
        cost_C += dist_matrix[route[p], route[p + 1]]

    cost_C_rev = 0.0
    for p in range(C_end - 1, j + 1, -1):
        cost_C_rev += dist_matrix[route[p], route[p - 1]]

    cost_D = 0.0
    for p in range(k + 1, n):
        cost_D += dist_matrix[route[p], route[(p + 1) % n]]
    # Closing edge of D back to start
    if n > 0:
        cost_D += dist_matrix[route[n - 1], route[0]]

    # Now evaluate each case using precomputed segment costs
    if case == 0:
        # A + B + C + D  (original)
        return cost_A + d_ab + cost_B + d_cd + cost_C + dist_matrix[c_last, d_first] + cost_D
    elif case == 1:
        # A + B' + C' + D
        return cost_A + d_ac + cost_B_rev + dist_matrix[b_last, d_first] + cost_C_rev + dist_matrix[d_first, route[0]] + cost_D
    elif case == 2:
        # A + B' + C + D
        return cost_A + d_ac + cost_B_rev + d_cd + cost_C + cost_D
    elif case == 3:
        # A + B + C' + D
        return cost_A + d_ab + cost_B + d_bd + cost_C_rev + cost_D
    elif case == 4:
        # A + B' + C + D'  (reverse D too)
        # Simplified: evaluate by building the route inline
        pass
    elif case == 5:
        # A + B + C' + D'  (reverse D too)
        pass
    elif case == 6:
        # A + B' + C' + D'  (reverse D too)
        pass

    # For cases 4-6 (which involve reversing D), fall back to full evaluation
    # Build candidate and compute length directly
    candidate = np.empty(n, dtype=np.int64)
    pos = 0

    # Segment A always first
    for p in range(A_end):
        candidate[pos] = route[p]
        pos += 1

    if case == 4:
        # A + B' + C + D'
        for p in range(B_end - 1, i, -1):
            candidate[pos] = route[p]
            pos += 1
        for p in range(j + 1, C_end):
            candidate[pos] = route[p]
            pos += 1
        for p in range(n - 1, k, -1):
            candidate[pos] = route[p]
            pos += 1
    elif case == 5:
        # A + B + C' + D'
        for p in range(i + 1, B_end):
            candidate[pos] = route[p]
            pos += 1
        for p in range(C_end - 1, j, -1):
            candidate[pos] = route[p]
            pos += 1
        for p in range(n - 1, k, -1):
            candidate[pos] = route[p]
            pos += 1
    elif case == 6:
        # A + B' + C' + D'
        for p in range(B_end - 1, i, -1):
            candidate[pos] = route[p]
            pos += 1
        for p in range(C_end - 1, j, -1):
            candidate[pos] = route[p]
            pos += 1
        for p in range(n - 1, k, -1):
            candidate[pos] = route[p]
            pos += 1

    return calc_tour_length_numba(candidate, dist_matrix)


@jit(nopython=True)
def three_opt_improve(route: np.ndarray, dist_matrix: np.ndarray,
                      max_iter: int, first_improvement: bool
                      ) -> Tuple[np.ndarray, float]:
    """Iterative 3-opt local search (7 reconnection cases).

    Falls back to 2-opt when ``n < 6``.

    Returns:
        ``(best_route, best_length)`` tuple.
    """
    n = len(route)
    if n < 6:
        return two_opt_improve(route, dist_matrix, max_iter, first_improvement)

    best_route = route.copy()
    best_length = calc_tour_length_numba(best_route, dist_matrix)

    improved = True
    iters = 0

    while improved and iters < max_iter:
        improved = False
        iters += 1

        for i in range(n - 4):
            for j in range(i + 2, n - 2):
                for k in range(j + 2, n):

                    # Try all 7 reconnection cases (case 0 = original, skip)
                    for case in range(1, 7):
                        cand_len = _three_opt_eval(
                            best_route, dist_matrix, i, j, k, case
                        )
                        if cand_len < best_length - 1e-10:
                            # Build the best candidate route
                            candidate = np.empty(n, dtype=np.int64)
                            pos = 0

                            A_end = i + 1
                            B_end = j + 1
                            C_end = k + 1

                            for p in range(A_end):
                                candidate[pos] = best_route[p]
                                pos += 1

                            if case == 1:
                                for p in range(B_end - 1, i, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(C_end - 1, j, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(k + 1, n):
                                    candidate[pos] = best_route[p]; pos += 1
                            elif case == 2:
                                for p in range(B_end - 1, i, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(j + 1, C_end):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(k + 1, n):
                                    candidate[pos] = best_route[p]; pos += 1
                            elif case == 3:
                                for p in range(i + 1, B_end):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(C_end - 1, j, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(k + 1, n):
                                    candidate[pos] = best_route[p]; pos += 1
                            elif case == 4:
                                for p in range(B_end - 1, i, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(j + 1, C_end):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(n - 1, k, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                            elif case == 5:
                                for p in range(i + 1, B_end):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(C_end - 1, j, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(n - 1, k, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                            elif case == 6:
                                for p in range(B_end - 1, i, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(C_end - 1, j, -1):
                                    candidate[pos] = best_route[p]; pos += 1
                                for p in range(n - 1, k, -1):
                                    candidate[pos] = best_route[p]; pos += 1

                            best_route = candidate.copy()
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


# -------------------------------------------------------------------
# Or-opt  (move 1-3 consecutive node segments)
# -------------------------------------------------------------------

@jit(nopython=True)
def or_opt_improve(route: np.ndarray, dist_matrix: np.ndarray,
                   max_iter: int, max_segment_size: int
                   ) -> Tuple[np.ndarray, float]:
    """Or-opt local search: relocate a short consecutive segment.

    Tries moving segments of length 1, 2, …, ``max_segment_size`` to
    every other position in the tour and keeps the first improving move
    per iteration.

    Returns:
        ``(best_route, best_length)`` tuple.
    """
    n = len(route)
    if n < 4:
        return route.copy(), calc_tour_length_numba(route, dist_matrix)

    best_route = route.copy()
    best_length = calc_tour_length_numba(best_route, dist_matrix)

    improved = True
    iters = 0

    while improved and iters < max_iter:
        improved = False
        iters += 1

        for seg_size in range(1, min(max_segment_size, n - 1) + 1):
            if improved:
                break
            for i in range(n - seg_size + 1):
                if improved:
                    break

                # Extract segment
                segment = best_route[i:i + seg_size].copy()

                # Remaining nodes
                remaining = np.empty(n - seg_size, dtype=np.int64)
                pos = 0
                for p in range(i):
                    remaining[pos] = best_route[p]; pos += 1
                for p in range(i + seg_size, n):
                    remaining[pos] = best_route[p]; pos += 1

                # Try every insertion position
                for j in range(len(remaining) + 1):
                    if j == i:
                        continue

                    new_route = np.empty(n, dtype=np.int64)
                    pos = 0
                    for p in range(j):
                        new_route[pos] = remaining[p]; pos += 1
                    for p in range(seg_size):
                        new_route[pos] = segment[p]; pos += 1
                    for p in range(j, len(remaining)):
                        new_route[pos] = remaining[p]; pos += 1

                    new_length = calc_tour_length_numba(new_route, dist_matrix)

                    if new_length < best_length - 1e-10:
                        best_route = new_route.copy()
                        best_length = new_length
                        improved = True
                        break

    return best_route, best_length


# -------------------------------------------------------------------
# Swap (exchange two non-adjacent nodes)
# -------------------------------------------------------------------

@jit(nopython=True)
def swap_improve(route: np.ndarray, dist_matrix: np.ndarray,
                 max_iter: int, first_improvement: bool
                 ) -> Tuple[np.ndarray, float]:
    """Swap (pairwise exchange) local search.

    Swaps non-adjacent node pairs; skips directly adjacent swaps.

    Returns:
        ``(best_route, best_length)`` tuple.
    """
    n = len(route)
    if n < 3:
        return route.copy(), calc_tour_length_numba(route, dist_matrix)

    best_route = route.copy()
    best_length = calc_tour_length_numba(best_route, dist_matrix)

    improved = True
    iters = 0

    while improved and iters < max_iter:
        improved = False
        iters += 1

        for i in range(n):
            for j in range(i + 1, n):
                # Skip adjacent
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


# -------------------------------------------------------------------
# Construction heuristics
# -------------------------------------------------------------------

@jit(nopython=True)
def nearest_neighbor_route(dist_matrix: np.ndarray, start: int) -> np.ndarray:
    """Greedy nearest-neighbour construction heuristic.

    Starting from ``start``, repeatedly visits the closest unvisited city.

    Args:
        dist_matrix: ``n x n`` distance matrix (dtype float64).
        start: Index of the starting city (0-based).

    Returns:
        1-D array of node indices (dtype int64) forming a tour.
    """
    n = len(dist_matrix)
    visited = np.zeros(n, dtype=np.bool_)
    route = np.empty(n, dtype=np.int64)

    visited[start] = True
    route[0] = start
    current = start

    for pos in range(1, n):
        best_dist = np.inf
        best_city = -1
        for city in range(n):
            if not visited[city] and dist_matrix[current, city] < best_dist:
                best_dist = dist_matrix[current, city]
                best_city = city

        visited[best_city] = True
        route[pos] = best_city
        current = best_city

    return route


@jit(nopython=True)
def random_route(n: int, seed: int) -> np.ndarray:
    """Generate a random permutation of ``0 .. n-1``.

    Uses a simple LCG seeded with ``seed`` so that the result is
    deterministic and reproducible inside the JIT-compiled function.

    Args:
        n: Number of cities.
        seed: Random seed value.

    Returns:
        1-D array of shuffled indices (dtype int64).
    """
    route = np.arange(n, dtype=np.int64)

    # Simple Fisher-Yates shuffle with LCG PRNG
    rng_state = np.uint64(seed & 0xFFFFFFFF)
    for i in range(n - 1, 0, -1):
        rng_state = rng_state * np.uint64(6364136223846793005) + np.uint64(1)
        j = int(rng_state % np.uint64(i + 1))
        route[i], route[j] = route[j], route[i]

    return route
