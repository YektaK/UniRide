"""
Destroy Operators for ALNS (DNA #1 + DNA #2)

Four destroy operators that remove nodes from a tour to create
partial solutions for subsequent repair:

  1. **RandomRemoval**     — uniformly random node removal
  2. **WorstRemoval**      — remove highest-cost-contribution nodes
  3. **ShawRemoval**       — Shaw-similarity based removal
  4. **RelatedRemoval**    — seed-node relatedness removal

Each operator implements :class:`DestroyOperator` and returns a tuple
``(removed_nodes, remaining_tour)``.

References:
    * Ropke, S. & Pisinger, D. (2006). An Adaptive Large Neighborhood
      Search Heuristic for the Pickup and Delivery Problem with Time
      Windows. *Transportation Science*, 40(4), 455–472.
"""

import logging
import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DestroyOperator(ABC):
    """Abstract base for ALNS destroy operators."""

    @abstractmethod
    def destroy(
        self,
        tour: List[str],
        num_remove: int,
        rng: "random.Random",  # noqa: F821
        **kwargs: Any,
    ) -> Tuple[List[str], List[str]]:
        """Remove *num_remove* nodes from *tour*.

        Args:
            tour:        Current complete tour (list of node ids).
            num_remove:  Number of nodes to remove.
            rng:         Seeded random generator.
            **kwargs:    Operator-specific parameters (e.g., distance
                         matrix, time windows, demands).

        Returns:
            ``(removed_nodes, remaining_tour)`` — the list of removed
            node ids and the tour with those nodes removed.
        """
        ...


class RandomRemoval(DestroyOperator):
    """Remove nodes uniformly at random.

    This is the simplest destroy operator.  It is effective at
    diversifying the search because it makes no assumptions about
    which nodes are "important" to the current solution.
    """

    def destroy(
        self,
        tour: List[str],
        num_remove: int,
        rng: "random.Random",  # noqa: F821
        **kwargs: Any,
    ) -> Tuple[List[str], List[str]]:
        """Randomly remove *num_remove* nodes.

        If *num_remove* exceeds the tour length, all nodes are removed.
        """
        n = min(num_remove, len(tour))
        indices = rng.sample(range(len(tour)), n)
        removed: List[str] = []
        remaining = list(tour)
        # Remove in reverse index order to keep indices valid
        for idx in sorted(indices, reverse=True):
            removed.append(remaining.pop(idx))
        return removed, remaining


class WorstRemoval(DestroyOperator):
    """Remove nodes with the highest cost contribution.

    For each node ``i`` in the tour, its *cost contribution* is
    computed as:

        ``c(i) = d(tour[i-1], tour[i]) + d(tour[i], tour[i+1]) - d(tour[i-1], tour[i+1])``

    i.e., the increase in routing cost if node *i* were removed
    (with depot considered at tour boundaries).  The nodes with the
    *largest* cost contribution are removed.

    A randomised selection is used: at each step the worst node is
    chosen with probability proportional to its rank, adding noise to
    diversify which nodes are selected across iterations.
    """

    def destroy(
        self,
        tour: List[str],
        num_remove: int,
        rng: "random.Random",  # noqa: F821
        **kwargs: Any,
    ) -> Tuple[List[str], List[str]]:
        """Remove the worst-cost nodes.

        Keyword Args:
            distance_matrix: ``Dict[str, Dict[str, float]]`` for cost
                             lookup.  Falls back to index-based cost if
                             not provided.
        """
        n = min(num_remove, len(tour))
        if n == 0:
            return [], list(tour)

        dist: Dict[str, Dict[str, float]] = kwargs.get("distance_matrix", {})

        remaining = list(tour)
        removed: List[str] = []

        for _ in range(n):
            if not remaining:
                break

            costs: List[Tuple[int, float]] = []
            for idx, node in enumerate(remaining):
                # Cost contribution of node at position idx
                prev_node = remaining[idx - 1] if idx > 0 else None
                next_node = remaining[idx + 1] if idx < len(remaining) - 1 else None

                cost_remove = 0.0
                if prev_node and next_node:
                    d_prev = dist.get(prev_node, {}).get(node, 0.0)
                    d_next = dist.get(node, {}).get(next_node, 0.0)
                    d_bypass = dist.get(prev_node, {}).get(next_node, 0.0)
                    cost_remove = d_prev + d_next - d_bypass
                elif prev_node:
                    cost_remove = dist.get(prev_node, {}).get(node, 0.0)
                elif next_node:
                    cost_remove = dist.get(node, {}).get(next_node, 0.0)

                costs.append((idx, cost_remove))

            # Sort by cost descending; pick with some randomness
            costs.sort(key=lambda x: -x[1])

            # Roulette-wheel selection biased toward worst
            weights = [max(0.1, c[1]) for c in costs]
            total_w = sum(weights)
            r = rng.random() * total_w
            cumulative = 0.0
            chosen_idx = costs[0][0]
            for ci, w in zip(costs, weights):
                cumulative += w
                if cumulative >= r:
                    chosen_idx = ci[0]
                    break

            removed.append(remaining.pop(chosen_idx))

        return removed, remaining


class ShawRemoval(DestroyOperator):
    """Shaw-similarity based removal.

    Selects a random *seed* node, then repeatedly removes the node
    most *similar* to the seed according to a combined metric:

        ``similarity(i, j) = w_d · d_norm(i,j)
                           + w_tw · tw_norm(i,j)
                           + w_cap · cap_norm(i,j)``

    Lower similarity means more related.  Nodes are clustered around
    the seed, creating spatially / temporally coherent removal patterns.

    Keyword Args:
        distance_matrix: Distance lookup.
        time_windows:    ``Dict[str, Tuple[float, float]]``.
        demands:         ``Dict[str, float]``.
        shaw_weights:    ``(w_d, w_tw, w_cap)`` tuple (default 0.5, 0.3, 0.2).
    """

    def destroy(
        self,
        tour: List[str],
        num_remove: int,
        rng: "random.Random",  # noqa: F821
        **kwargs: Any,
    ) -> Tuple[List[str], List[str]]:
        """Remove nodes using Shaw similarity clustering.

        Keyword Args:
            distance_matrix: ``Dict[str, Dict[str, float]]``.
            time_windows:    ``Dict[str, Tuple[float, float]]``.
            demands:         ``Dict[str, float]``.
            shaw_weights:    ``(w_d, w_tw, w_cap)`` weights.
        """
        n = min(num_remove, len(tour))
        if n == 0:
            return [], list(tour)

        dist: Dict[str, Dict[str, float]] = kwargs.get("distance_matrix", {})
        tw: Dict[str, Tuple[float, float]] = kwargs.get("time_windows", {})
        dem: Dict[str, float] = kwargs.get("demands", {})
        w_d, w_tw, w_cap = kwargs.get("shaw_weights", (0.5, 0.3, 0.2))

        remaining = list(tour)
        removed: List[str] = []

        # Pick seed randomly
        seed_idx = rng.randint(0, len(remaining) - 1)
        seed_node = remaining[seed_idx]
        removed.append(seed_node)
        remaining.pop(seed_idx)

        # Normalisation ranges
        max_dist = 1.0
        for node in remaining:
            d = dist.get(seed_node, {}).get(node, 0.0)
            if d > max_dist:
                max_dist = d

        max_demand = max(dem.values()) if dem else 1.0

        while len(removed) < n and remaining:
            best_node = None
            best_sim = float("inf")

            for node in remaining:
                # Distance component
                d = dist.get(seed_node, {}).get(node, 0.0)
                d_norm = d / max_dist if max_dist > 0 else 0.0

                # Time window component
                tw_sim = 0.0
                if seed_node in tw and node in tw:
                    tw_diff = abs(
                        (tw[seed_node][0] + tw[seed_node][1]) / 2
                        - (tw[node][0] + tw[node][1]) / 2
                    )
                    max_tw = max(
                        abs(tw[seed_node][1] - tw[seed_node][0]),
                        abs(tw[node][1] - tw[node][0]),
                        1.0,
                    )
                    tw_sim = tw_diff / max_tw

                # Demand component
                cap_sim = 0.0
                if seed_node in dem and node in dem:
                    cap_diff = abs(dem[seed_node] - dem[node])
                    cap_sim = cap_diff / max_demand if max_demand > 0 else 0.0

                similarity = w_d * d_norm + w_tw * tw_sim + w_cap * cap_sim

                if similarity < best_sim:
                    best_sim = similarity
                    best_node = node

            if best_node is None:
                break

            remaining.remove(best_node)
            removed.append(best_node)

        return removed, remaining


class RelatedRemoval(DestroyOperator):
    """Remove nodes related to a randomly chosen seed node.

    Similar to Shaw removal but uses a simpler *relatedness* metric
    based primarily on distance.  A random seed is selected, then the
    ``num_remove`` closest nodes to the seed are removed.

    This operator is computationally cheaper than Shaw and is
    effective when distance is the primary structure in the problem.

    Keyword Args:
        distance_matrix: ``Dict[str, Dict[str, float]]`` for cost lookup.
    """

    def destroy(
        self,
        tour: List[str],
        num_remove: int,
        rng: "random.Random",  # noqa: F821
        **kwargs: Any,
    ) -> Tuple[List[str], List[str]]:
        """Remove nodes most related to a random seed.

        Keyword Args:
            distance_matrix: ``Dict[str, Dict[str, float]]``.
        """
        n = min(num_remove, len(tour))
        if n == 0:
            return [], list(tour)

        dist: Dict[str, Dict[str, float]] = kwargs.get("distance_matrix", {})

        remaining = list(tour)

        # Pick seed
        seed_idx = rng.randint(0, len(remaining) - 1)
        seed = remaining[seed_idx]
        removed: List[str] = [seed]
        remaining.pop(seed_idx)

        # Rank remaining by distance to seed
        dists: List[Tuple[float, str]] = []
        for node in remaining:
            d = dist.get(seed, {}).get(node, float("inf"))
            dists.append((d, node))
        dists.sort()

        # Remove the closest nodes
        for _, node in dists[: n - 1]:
            removed.append(node)
            remaining.remove(node)

        return removed, remaining
