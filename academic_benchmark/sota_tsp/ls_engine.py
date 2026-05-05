"""
Multi-Layer Local Search Engine — TSP variant.

Chains (by intensity):
  light    : 2-opt
  moderate : 2-opt → Or-opt
  full     : 2-opt → Or-opt → Swap

Adapted from optimizer_api/strategies/sota_common/multi_layer_ls.py
but operates on List[int] tours with Numba-accelerated kernels.
"""

import os
import time
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

try:
    # sys.path hack: bildiri2026/core is not a pip-installable package,
    # so we add its parent to the path for Numba-accelerated kernels.
    import sys as _sys
    _ls_dir = os.path.dirname(os.path.abspath(__file__))
    _ab_dir = os.path.join(_ls_dir, "..", "bildiri2026")
    if os.path.isdir(_ab_dir):
        _sys.path.insert(0, _ab_dir)
    from core import numba_accel as _nb
    _NUMBA_OK = _nb.NUMBA_AVAILABLE
except Exception:
    _NUMBA_OK = False
    _nb = None


def _two_opt_swap(tour: List[int], i: int, j: int) -> List[int]:
    new_tour = tour[:i]
    new_tour.extend(reversed(tour[i:j + 1]))
    new_tour.extend(tour[j + 1:])
    return new_tour


def _tour_cost(tour: List[int], dm: List[List[float]]) -> float:
    n = len(tour)
    total = 0.0
    for i in range(n):
        total += dm[tour[i]][tour[(i + 1) % n]]
    return total


def improve_2opt(tour: List[int], dm: List[List[float]], dm_np=None,
                 max_iterations: int = 1000, first_improvement: bool = False) -> Tuple[List[int], float]:
    if _NUMBA_OK and dm_np is not None:
        route_np = _nb._prepare_route(tour)
        improved_np, length = _nb._two_opt_improve_atsp_numba(route_np, dm_np, max_iterations, first_improvement)
        return _nb._extract_route(improved_np, tour), float(length)
    if _NUMBA_OK and dm is not None:
        improved, length = _nb.nb_two_opt(tour, dm, max_iterations, first_improvement)
        return improved, float(length)
    best_tour = tour[:]
    best_length = _tour_cost(best_tour, dm)
    improved = True
    iters = 0
    while improved and iters < max_iterations:
        improved = False
        iters += 1
        for i in range(len(best_tour) - 1):
            for j in range(i + 1, len(best_tour)):
                new_tour = _two_opt_swap(best_tour, i, j)
                new_length = _tour_cost(new_tour, dm)
                if new_length < best_length:
                    best_tour = new_tour
                    best_length = new_length
                    improved = True
                    if first_improvement:
                        break
            if improved and first_improvement:
                break
    return best_tour, best_length


def improve_or_opt(tour: List[int], dm: List[List[float]], dm_np=None,
                   max_iterations: int = 500, segment_size: int = 3) -> Tuple[List[int], float]:
    if _NUMBA_OK and dm_np is not None:
        route_np = _nb._prepare_route(tour)
        improved_np, length = _nb._or_opt_improve_atsp_numba(route_np, dm_np, max_iterations, segment_size)
        return _nb._extract_route(improved_np, tour), float(length)
    best_tour = tour[:]
    best_length = _tour_cost(best_tour, dm)
    n = len(best_tour)
    improved = True
    iters = 0
    while improved and iters < max_iterations:
        improved = False
        iters += 1
        for seg_len in range(1, min(segment_size + 1, n)):
            for i in range(n - seg_len + 1):
                segment = best_tour[i:i + seg_len]
                remaining = best_tour[:i] + best_tour[i + seg_len:]
                for j in range(len(remaining) + 1):
                    new_tour = remaining[:j] + segment + remaining[j:]
                    new_length = _tour_cost(new_tour, dm)
                    if new_length < best_length - 1e-10:
                        best_tour = new_tour
                        best_length = new_length
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break
    return best_tour, best_length


def improve_swap(tour: List[int], dm: List[List[float]],
                 max_iterations: int = 500) -> Tuple[List[int], float]:
    best_tour = tour[:]
    best_length = _tour_cost(best_tour, dm)
    n = len(best_tour)
    improved = True
    iters = 0
    while improved and iters < max_iterations:
        improved = False
        iters += 1
        for i in range(n - 1):
            for j in range(i + 1, n):
                new_tour = best_tour[:]
                new_tour[i], new_tour[j] = new_tour[j], new_tour[i]
                new_length = _tour_cost(new_tour, dm)
                if new_length < best_length - 1e-10:
                    best_tour = new_tour
                    best_length = new_length
                    improved = True
                    break
            if improved:
                break
    return best_tour, best_length


def improve_3opt(tour: List[int], dm: List[List[float]],
                 max_iterations: int = 200) -> Tuple[List[int], float]:
    """Simple bounded 3-opt style improvement (reverse-middle neighborhood)."""
    best_tour = tour[:]
    best_length = _tour_cost(best_tour, dm)
    n = len(best_tour)
    if n < 5:
        return best_tour, best_length
    improved = True
    iters = 0
    while improved and iters < max_iterations:
        improved = False
        iters += 1
        for i in range(0, n - 3):
            # Bound inner scan to keep runtime under control.
            j_max = min(n - 2, i + 12)
            for j in range(i + 2, j_max + 1):
                k_max = min(n - 1, j + 12)
                for k in range(j + 1, k_max + 1):
                    # 3-opt inspired reconnect: keep prefix/suffix, reverse middle chunks.
                    cand = (
                        best_tour[:i + 1]
                        + best_tour[i + 1:j + 1][::-1]
                        + best_tour[j + 1:k + 1][::-1]
                        + best_tour[k + 1:]
                    )
                    cand_len = _tour_cost(cand, dm)
                    if cand_len < best_length - 1e-10:
                        best_tour = cand
                        best_length = cand_len
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break
    return best_tour, best_length


class MultiLayerLS:

    @staticmethod
    def improve(
        tour: List[int],
        dm: List[List[float]],
        dm_np=None,
        intensity: str = "full",
        max_iterations: int = 1000,
        time_limit: float = 5.0,
    ) -> Tuple[List[int], float, Dict[str, Any]]:
        current_tour = list(tour)
        current_cost = _tour_cost(current_tour, dm)
        initial_cost = current_cost
        stats: Dict[str, Any] = {"improves_per_layer": {}, "total_time_ms": 0.0, "improvement_pct": 0.0}
        t0 = time.monotonic()

        layers = [("2-opt", improve_2opt)]
        if intensity in ("moderate", "full"):
            layers.append(("or-opt", improve_or_opt))
        if intensity == "full":
            layers.append(("3-opt", improve_3opt))
            layers.append(("swap", improve_swap))

        for layer_name, layer_fn in layers:
            if time.monotonic() - t0 > time_limit:
                break
            if layer_name == "2-opt":
                new_tour, new_cost = layer_fn(current_tour, dm, dm_np, max_iterations)
            elif layer_name == "or-opt":
                new_tour, new_cost = layer_fn(current_tour, dm, dm_np, max_iterations)
            elif layer_name == "3-opt":
                new_tour, new_cost = layer_fn(current_tour, dm, max_iterations)
            else:
                new_tour, new_cost = layer_fn(current_tour, dm, max_iterations)
            if new_cost < current_cost - 1e-10:
                stats["improves_per_layer"][layer_name] = current_cost - new_cost
                current_tour = new_tour
                current_cost = new_cost

        elapsed = (time.monotonic() - t0) * 1000
        stats["total_time_ms"] = elapsed
        if initial_cost > 0:
            stats["improvement_pct"] = (initial_cost - current_cost) / initial_cost * 100
        return current_tour, current_cost, stats
