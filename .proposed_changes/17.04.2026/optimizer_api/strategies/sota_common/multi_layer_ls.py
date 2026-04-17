"""
Multi-Layer Local Search Engine (DNA #3)

Chains four neighbourhood search layers until no further improvement
is found:

    2-opt  →  Or-opt  →  3-opt  →  Swap  →  (repeat)

Intensity levels control which layers are active:

  * **full**     — all four layers
  * **moderate** — 2-opt + Or-opt + Swap
  * **light**    — 2-opt only

Each layer uses the best-improvement strategy (full scan of the
neighbourhood) except for 3-opt which is limited to a search range
of ``j + 10`` to keep runtimes bounded.

Public entry point:
    ``MultiLayerLS.improve(tour, cost_func, rng, intensity) -> (tour, cost, stats)``
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Type alias for a cost function
CostFunc = Callable[[List[str]], float]


class MultiLayerLS:
    """Multi-layer local search with configurable intensity."""

    # Default time limits (seconds) per layer and overall
    LAYER_TIME_LIMIT: float = 5.0
    OVERALL_TIME_LIMIT: float = 30.0

    @staticmethod
    def improve(
        tour: List[str],
        cost_func: CostFunc,
        rng: "random.Random",  # noqa: F821
        intensity: str = "full",
        layer_time_limit: Optional[float] = None,
        overall_time_limit: Optional[float] = None,
    ) -> Tuple[List[str], float, Dict[str, Any]]:
        """Run multi-layer local search on a tour.

        Args:
            tour: Initial tour (list of node ids).
            cost_func: Callable that returns the cost of a tour.
            rng: Seeded :class:`random.Random` (used for tie-breaking).
            intensity: One of ``"full"``, ``"moderate"``, ``"light"``.
            layer_time_limit: Max seconds per layer (default 5.0).
            overall_time_limit: Max total seconds (default 30.0).

        Returns:
            A tuple ``(improved_tour, final_cost, stats)`` where *stats*
            is a dict with keys ``improves_per_layer``, ``total_time_ms``,
            ``improvement_pct``, ``iterations``.
        """
        _layer_tl = layer_time_limit or MultiLayerLS.LAYER_TIME_LIMIT
        _overall_tl = overall_time_limit or MultiLayerLS.OVERALL_TIME_LIMIT

        current_tour = list(tour)
        current_cost = cost_func(current_tour)
        initial_cost = current_cost

        stats: Dict[str, Any] = {
            "improves_per_layer": {},
            "total_time_ms": 0.0,
            "improvement_pct": 0.0,
            "iterations": 0,
        }

        # Define active layers based on intensity
        layers: List[Tuple[str, Callable]] = [
            ("2-opt", MultiLayerLS._layer_2opt),
            ("or-opt", MultiLayerLS._layer_or_opt),
            ("3-opt", MultiLayerLS._layer_3opt),
            ("swap", MultiLayerLS._layer_swap),
        ]

        if intensity == "light":
            layers = layers[:1]
        elif intensity == "moderate":
            layers = layers[:2] + [layers[3]]  # 2-opt, or-opt, swap

        overall_start = time.monotonic()
        global_improved = True

        while global_improved:
            global_improved = False

            # Check overall time budget
            if time.monotonic() - overall_start > _overall_tl:
                logger.debug("Overall time limit reached, stopping LS.")
                break

            for layer_name, layer_func in layers:
                if time.monotonic() - overall_start > _overall_tl:
                    break

                layer_start = time.monotonic()
                new_tour, new_cost, improved = layer_func(
                    current_tour, cost_func, rng, time_limit=_layer_tl
                )

                layer_time_ms = (time.monotonic() - layer_start) * 1000.0

                if improved:
                    current_tour = new_tour
                    current_cost = new_cost
                    global_improved = True
                    stats["improves_per_layer"][layer_name] = (
                        stats["improves_per_layer"].get(layer_name, 0) + 1
                    )
                    logger.debug(
                        "%s improved cost to %.4f (%.1f ms)",
                        layer_name,
                        current_cost,
                        layer_time_ms,
                    )

                stats["iterations"] += 1

        stats["total_time_ms"] = (time.monotonic() - overall_start) * 1000.0
        if initial_cost > 0:
            stats["improvement_pct"] = (
                (initial_cost - current_cost) / initial_cost * 100.0
            )
        else:
            stats["improvement_pct"] = 0.0

        return current_tour, current_cost, stats

    # ------------------------------------------------------------------ #
    # Layer 1: 2-opt (best-improvement, full scan)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _layer_2opt(
        tour: List[str],
        cost_func: CostFunc,
        rng: "random.Random",  # noqa: F821
        time_limit: float = 5.0,
    ) -> Tuple[List[str], float, bool]:
        """2-opt: reverse a sub-segment and check improvement.

        Best-improvement: scans all ``(i, j)`` pairs and applies the
        single best reversal.

        Args:
            tour: Current tour.
            cost_func: Cost callable.
            rng: Random (unused, kept for API consistency).
            time_limit: Max seconds for this layer.

        Returns:
            ``(new_tour, new_cost, improved)``.
        """
        start = time.monotonic()
        n = len(tour)
        if n < 4:
            return list(tour), cost_func(tour), False

        best_i, best_j = -1, -1
        best_delta = 0.0

        for i in range(n - 1):
            if time.monotonic() - start > time_limit:
                break
            for j in range(i + 2, n):
                # Compute delta of reversing segment [i+1 .. j]
                # delta = -d(i,i+1) - d(j,j+1) + d(i,j) + d(i+1,j+1)
                # Use cost_func delta approximation
                new_tour = tour[: i + 1] + list(reversed(tour[i + 1 : j + 1])) + tour[j + 1 :]
                new_cost = cost_func(new_tour)
                delta = cost_func(tour) - new_cost
                if delta > best_delta:
                    best_delta = delta
                    best_i = i
                    best_j = j

        if best_delta > 0 and best_i >= 0:
            result = tour[: best_i + 1] + list(reversed(tour[best_i + 1 : best_j + 1])) + tour[best_j + 1 :]
            return result, cost_func(result), True

        return list(tour), cost_func(tour), False

    # ------------------------------------------------------------------ #
    # Layer 2: Or-opt (single node + 2-node segment relocate)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _layer_or_opt(
        tour: List[str],
        cost_func: CostFunc,
        rng: "random.Random",  # noqa: F821
        time_limit: float = 5.0,
    ) -> Tuple[List[str], float, bool]:
        """Or-opt: relocate a single node or a 2-node segment.

        Tries every possible relocation of each node (and each adjacent
        pair of nodes) and applies the best-improvement move.

        Args:
            tour: Current tour.
            cost_func: Cost callable.
            rng: Random (unused).
            time_limit: Max seconds for this layer.

        Returns:
            ``(new_tour, new_cost, improved)``.
        """
        start = time.monotonic()
        n = len(tour)
        if n < 3:
            return list(tour), cost_func(tour), False

        best_tour = None
        best_cost = cost_func(tour)
        improved = False

        # Single node relocation
        for i in range(n):
            if time.monotonic() - start > time_limit:
                break
            node = tour[i]
            remaining = tour[:i] + tour[i + 1:]
            for pos in range(len(remaining) + 1):
                new_tour = remaining[:pos] + [node] + remaining[pos:]
                new_cost = cost_func(new_tour)
                if new_cost < best_cost - 1e-10:
                    best_cost = new_cost
                    best_tour = new_tour
                    improved = True

        # 2-node segment relocation
        for i in range(n - 1):
            if time.monotonic() - start > time_limit:
                break
            segment = tour[i : i + 2]
            remaining = tour[:i] + tour[i + 2 :]
            for pos in range(len(remaining) + 1):
                new_tour = remaining[:pos] + segment + remaining[pos:]
                new_cost = cost_func(new_tour)
                if new_cost < best_cost - 1e-10:
                    best_cost = new_cost
                    best_tour = new_tour
                    improved = True

        if best_tour is not None:
            return best_tour, best_cost, True
        return list(tour), cost_func(tour), False

    # ------------------------------------------------------------------ #
    # Layer 3: 3-opt (reverse-middle, limited search range)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _layer_3opt(
        tour: List[str],
        cost_func: CostFunc,
        rng: "random.Random",  # noqa: F821
        time_limit: float = 5.0,
        max_search_range: int = 10,
    ) -> Tuple[List[str], float, bool]:
        """3-opt with reverse-middle schema.

        For each ``(i, j)`` pair, reverses the segment ``[i+1 .. j]``
        and evaluates the cost change.  The search range for ``j`` is
        limited to ``i + max_search_range`` to bound runtime.

        This is the classic *reverse-middle* 3-opt move, which is a
        generalisation of 2-opt.

        Args:
            tour: Current tour.
            cost_func: Cost callable.
            rng: Random (unused).
            time_limit: Max seconds.
            max_search_range: Max distance between ``i`` and ``j``.

        Returns:
            ``(new_tour, new_cost, improved)``.
        """
        start = time.monotonic()
        n = len(tour)
        if n < 4:
            return list(tour), cost_func(tour), False

        base_cost = cost_func(tour)
        best_tour = None
        best_cost = base_cost

        for i in range(n - 2):
            if time.monotonic() - start > time_limit:
                break
            j_max = min(n - 1, i + max_search_range)
            for j in range(i + 2, j_max + 1):
                # Reverse-middle: reverse segment [i+1 .. j]
                new_tour = tour[: i + 1] + list(reversed(tour[i + 1 : j + 1])) + tour[j + 1 :]
                new_cost = cost_func(new_tour)
                if new_cost < best_cost - 1e-10:
                    best_cost = new_cost
                    best_tour = new_tour

        if best_tour is not None:
            return best_tour, best_cost, True
        return list(tour), base_cost, False

    # ------------------------------------------------------------------ #
    # Layer 4: Swap (inter-node swap, best-improvement)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _layer_swap(
        tour: List[str],
        cost_func: CostFunc,
        rng: "random.Random",  # noqa: F821
        time_limit: float = 5.0,
    ) -> Tuple[List[str], float, bool]:
        """Swap: exchange the positions of two nodes.

        Best-improvement: scans all ``(i, j)`` pairs and applies the
        swap that yields the largest cost reduction.

        Args:
            tour: Current tour.
            cost_func: Cost callable.
            rng: Random (unused).
            time_limit: Max seconds.

        Returns:
            ``(new_tour, new_cost, improved)``.
        """
        start = time.monotonic()
        n = len(tour)
        if n < 2:
            return list(tour), cost_func(tour), False

        base_cost = cost_func(tour)
        best_tour = None
        best_cost = base_cost

        for i in range(n):
            if time.monotonic() - start > time_limit:
                break
            for j in range(i + 1, n):
                new_tour = list(tour)
                new_tour[i], new_tour[j] = new_tour[j], new_tour[i]
                new_cost = cost_func(new_tour)
                if new_cost < best_cost - 1e-10:
                    best_cost = new_cost
                    best_tour = new_tour

        if best_tour is not None:
            return best_tour, best_cost, True
        return list(tour), base_cost, False
