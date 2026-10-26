"""
Multi-Layer Local Search Engine — TSP variant.

Chains (by intensity):
  light    : 2-opt
  moderate : 2-opt → Or-opt
  full     : 2-opt → Or-opt → canonical 3-opt (uniride_core.algorithms.three_opt) → Swap

Core multi-layer local search helpers for SOTA algorithms. Operates on
List[int] tours. The 2-opt, Or-opt and swap layers use Numba-accelerated kernels
when available; the 3-opt layer is the canonical windowed 3-opt
(``uniride_core.algorithms.three_opt``), not a Numba kernel (audit H10).
Local search is bounded by iteration limits only, never by wall-clock time (H11).
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
    from uniride_core.algorithms import numba_accel as _nb
    _NUMBA_OK = _nb.NUMBA_AVAILABLE
except ImportError:
    _NUMBA_OK = False
    _nb = None

from uniride_core.algorithms.three_opt import improve_three_opt


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


def improve_swap(tour: List[int], dm: List[List[float]], dm_np=None,
                 max_iterations: int = 500) -> Tuple[List[int], float]:
    if _NUMBA_OK and dm_np is not None:
        route_np = _nb._prepare_route(tour)
        improved_np, length = _nb._swap_improve_atsp_numba(route_np, dm_np, max_iterations)
        return _nb._extract_route(improved_np, tour), float(length)
    if _NUMBA_OK and dm is not None:
        return _nb.nb_swap(tour, dm, max_iterations)
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


def improve_3opt(tour: List[int], dm: List[List[float]], dm_np=None,
                 max_iterations: int = 200, window: int = 12) -> Tuple[List[int], float]:
    """Canonical windowed 3-opt (``uniride_core.algorithms.three_opt``), audit H10.

    Symmetric matrices use the symmetric 3-opt neighbourhood, asymmetric ones the
    directed (segment-exchange) neighbourhood; the mode is auto-detected from ``dm``.
    ``dm_np`` is accepted for signature compatibility with the other layers and is
    ignored. The old Numba kernel and the Python reverse-middle fallback are not
    used here (``CANONICAL_THREE_OPT_DESIGN.md``). ``tour`` must be a permutation of
    ``0..n-1`` with ``n == len(dm)``; tours shorter than 6 nodes are returned unchanged.
    """
    matrix = dm.tolist() if hasattr(dm, "tolist") else dm
    result = improve_three_opt(tour, matrix, max_iterations=max_iterations, window=window)
    return list(result.route), float(result.cost)


class MultiLayerLS:

    @staticmethod
    def improve(
        tour: List[int],
        dm: List[List[float]],
        dm_np=None,
        intensity: str = "full",
        max_iterations: int = 1000,
        three_opt_window: int = 12,
    ) -> Tuple[List[int], float, Dict[str, Any]]:
        """Chain the layers for ``intensity``; work is bounded by iteration limits only.

        At most ``max_ls_pass_iterations`` passes, each layer capped by
        ``max_iterations``; there is no wall-clock check (audit H11), so the result
        is a function of the inputs. Elapsed time is measured for ``stats`` only.
        """
        current_tour = list(tour)
        current_cost = _tour_cost(current_tour, dm)
        initial_cost = current_cost
        stats: Dict[str, Any] = {"improves_per_layer": {}, "total_time_ms": 0.0, "improvement_pct": 0.0}
        t0 = time.monotonic()

        layers = [("2-opt", improve_2opt)]
        if intensity in ("moderate", "full"):
            layers.append(("or-opt", improve_or_opt))
        if intensity == "full":
            layers.append(("3-opt-bounded", improve_3opt))
            layers.append(("swap", improve_swap))

        max_ls_pass_iterations = 5
        for ls_pass in range(max_ls_pass_iterations):
            any_improved = False
            for layer_name, layer_fn in layers:
                if layer_name == "3-opt-bounded":
                    new_tour, new_cost = layer_fn(current_tour, dm, dm_np, max_iterations, three_opt_window)
                elif layer_name in ("2-opt", "or-opt", "swap"):
                    new_tour, new_cost = layer_fn(current_tour, dm, dm_np, max_iterations)
                else:
                    new_tour, new_cost = layer_fn(current_tour, dm, max_iterations)
                if new_cost < current_cost - 1e-10:
                    stats["improves_per_layer"][layer_name] = current_cost - new_cost
                    current_tour = new_tour
                    current_cost = new_cost
                    any_improved = True
            if not any_improved:
                break

        elapsed = (time.monotonic() - t0) * 1000
        stats["total_time_ms"] = elapsed
        if initial_cost > 0:
            stats["improvement_pct"] = (initial_cost - current_cost) / initial_cost * 100
        return current_tour, current_cost, stats
