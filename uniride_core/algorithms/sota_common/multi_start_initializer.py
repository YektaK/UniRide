"""
Multi-Start Solution Initializer (DNA #6)

Generates diverse initial populations using four complementary heuristics:
  1. Nearest Neighbor (NN) with multiple starting points
  2. Clarke-Wright Savings with sorting variants
  3. Regret Insertion with TW urgency bonus
  4. Random + Perturbation (scramble, swap mutations)

Distribution: NN(1/4), CW(1/4), Regret(1/4), Random(1/4)

All methods are static and stateless — no external dependencies beyond
Python stdlib.  Each method accepts a :class:`random.Random` instance
so callers control reproducibility.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MultiStartInitializer:
    """Multi-start population generator for CVRPTW / TSP solvers."""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_population(
        waypoints: List[str],
        distance_matrix: Dict[str, Dict[str, float]],
        pop_size: int,
        rng: "random.Random",  # noqa: F821
        depot: Optional[str] = None,
        demands: Optional[Dict[str, float]] = None,
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> List[List[str]]:
        """Generate a diverse initial population.

        Args:
            waypoints: Customer / node identifiers (depot excluded).
            distance_matrix: Symmetric distance lookup ``matrix[a][b]``.
            pop_size: Number of solutions to produce.
            rng: Seeded :class:`random.Random` for reproducibility.
            depot: Depot node id (used by NN and CW heuristics).
            demands: Demand per node (used by Regret insertion).
            time_windows: ``(earliest, latest)`` per node (used by Regret).

        Returns:
            A list of *pop_size* tours, each a :class:`list` of node ids.
        """
        if pop_size <= 0:
            return []
        if not waypoints:
            return [[] for _ in range(pop_size)]

        # Effective demand / TW fallbacks
        _demands: Dict[str, float] = demands or {}
        _tw: Dict[str, Tuple[float, float]] = time_windows or {}

        population: List[List[str]] = []
        per_method = max(1, pop_size // 4)
        remainder = pop_size - 4 * per_method  # 0..3

        # --- Nearest Neighbor (1/4) ---
        nn_count = per_method + (1 if remainder > 0 else 0)
        for _ in range(nn_count):
            tour = MultiStartInitializer._nearest_neighbor(
                waypoints, distance_matrix, rng, depot
            )
            population.append(tour)
        logger.debug("NN generated %d tours", nn_count)

        # --- Clarke-Wright Savings (1/4) ---
        cw_count = per_method + (1 if remainder > 1 else 0)
        for _ in range(cw_count):
            tour = MultiStartInitializer._clarke_wright_savings(
                waypoints, distance_matrix, rng, depot
            )
            population.append(tour)
        logger.debug("CW generated %d tours", cw_count)

        # --- Regret Insertion (1/4) ---
        ri_count = per_method + (1 if remainder > 2 else 0)
        for _ in range(ri_count):
            tour = MultiStartInitializer._regret_insertion(
                waypoints, distance_matrix, rng, depot, _demands, _tw
            )
            population.append(tour)
        logger.debug("Regret generated %d tours", ri_count)

        # --- Random + Perturbation (remaining) ---
        random_count = pop_size - nn_count - cw_count - ri_count
        for _ in range(max(0, random_count)):
            tour = MultiStartInitializer._random_perturbation(
                waypoints, rng
            )
            population.append(tour)
        if random_count > 0:
            logger.debug("Random generated %d tours", random_count)

        return population

    # ------------------------------------------------------------------ #
    # 1. Nearest Neighbor
    # ------------------------------------------------------------------ #

    @staticmethod
    def _nearest_neighbor(
        waypoints: List[str],
        distance_matrix: Dict[str, Dict[str, float]],
        rng: "random.Random",  # noqa: F821
        depot: Optional[str] = None,
    ) -> List[str]:
        """Build a tour by always visiting the closest unvisited node.

        If *depot* is provided the tour starts from the depot; otherwise
        the starting node is chosen randomly among *waypoints*.

        Args:
            waypoints: Node ids to visit.
            distance_matrix: Distance lookup.
            rng: Random instance.
            depot: Optional starting depot.

        Returns:
            Ordered list of visited node ids.
        """
        if not waypoints:
            return []

        remaining = list(waypoints)
        # Choose starting node
        if depot and depot in distance_matrix:
            current = depot
        else:
            current = remaining.pop(rng.randint(0, len(remaining) - 1))

        tour: List[str] = []
        if current in remaining:
            remaining.remove(current)
        tour.append(current)

        while remaining:
            best_node = None
            best_dist = float("inf")
            for node in remaining:
                d = distance_matrix.get(current, {}).get(node, float("inf"))
                if d < best_dist:
                    best_dist = d
                    best_node = node
            if best_node is None:
                # Fallback: pick random
                best_node = remaining.pop(rng.randint(0, len(remaining) - 1))
            else:
                remaining.remove(best_node)
            tour.append(best_node)
            current = best_node

        return tour

    # ------------------------------------------------------------------ #
    # 2. Clarke-Wright Savings
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clarke_wright_savings(
        waypoints: List[str],
        distance_matrix: Dict[str, Dict[str, float]],
        rng: "random.Random",  # noqa: F821
        depot: Optional[str] = None,
    ) -> List[str]:
        """Construct a tour via the Clarke-Wright Savings heuristic.

        For every pair ``(i, j)`` the *savings* value is
        ``s(i,j) = d(depot,i) + d(depot,j) - d(i,j)``.
        Pairs are merged in descending savings order to form a giant
        tour.  A sorting variant (random tie-breaking) is applied to
        diversify outputs across calls.

        Args:
            waypoints: Node ids.
            distance_matrix: Distance lookup.
            rng: Random instance.
            depot: Depot node id.

        Returns:
            Ordered list of node ids forming a single tour.
        """
        if not waypoints:
            return []

        # Fallback depot: use first waypoint if no depot given
        _depot = depot if depot else waypoints[0]

        def _dist(a: str, b: str) -> float:
            return distance_matrix.get(a, {}).get(b, float("inf"))

        # Compute savings list
        savings: List[Tuple[float, str, str]] = []
        for i in waypoints:
            for j in waypoints:
                if i >= j:
                    continue
                s = _dist(_depot, i) + _dist(_depot, j) - _dist(i, j)
                savings.append((s, i, j))

        # Sort descending; break ties randomly for diversity
        savings.sort(key=lambda x: (-x[0], rng.random()))

        # Union-Find to build route segments
        parent: Dict[str, str] = {w: w for w in waypoints}
        # Track degree (endpoints) — max 2 connections per node
        degree: Dict[str, int] = {w: 0 for w in waypoints}
        # Adjacency list for final tour construction
        adj: Dict[str, List[str]] = {w: [] for w in waypoints}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> bool:
            """Try to merge edge (a,b). Returns True if accepted."""
            if degree[a] >= 2 or degree[b] >= 2:
                return False
            ra, rb = find(a), find(b)
            if ra == rb:
                # Would create a cycle (not allowed in giant tour)
                return False
            parent[ra] = rb
            degree[a] += 1
            degree[b] += 1
            adj[a].append(b)
            adj[b].append(a)
            return True

        for _s, i, j in savings:
            union(i, j)

        # Build tour from adjacency (follow degree-1 → degree-1 endpoints)
        # Find a starting endpoint (degree < 2)
        start = next((w for w in waypoints if degree[w] < 2), waypoints[0])
        visited = set()
        tour: List[str] = [start]
        visited.add(start)
        current = start
        while len(tour) < len(waypoints):
            next_node = None
            for nb in adj[current]:
                if nb not in visited:
                    next_node = nb
                    break
            if next_node is None:
                # Isolated node — pick any unvisited
                unvisited = [w for w in waypoints if w not in visited]
                if unvisited:
                    next_node = unvisited[0]
                else:
                    break
            tour.append(next_node)
            visited.add(next_node)
            current = next_node

        return tour

    # ------------------------------------------------------------------ #
    # 3. Regret Insertion
    # ------------------------------------------------------------------ #

    @staticmethod
    def _regret_insertion(
        waypoints: List[str],
        distance_matrix: Dict[str, Dict[str, float]],
        rng: "random.Random",  # noqa: F821
        depot: Optional[str] = None,
        demands: Optional[Dict[str, float]] = None,
        time_windows: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> List[str]:
        """Insert nodes one-by-one using a regret-2 criterion.

        At each step the *not-yet-inserted* node with the highest
        regret-2 value is inserted at its cheapest position.  Regret-2 is
        the difference between the 2nd-best and best insertion costs — a
        high regret means the node is "urgent" (its cheapest spot is
        much better than the next-best, so delaying insertion is costly).

        A time-window urgency bonus is added for CVRPTW: nodes with tight
        windows receive a higher regret score.

        Args:
            waypoints: Node ids.
            distance_matrix: Distance lookup.
            rng: Random instance.
            depot: Depot node id.
            demands: Demand per node.
            time_windows: ``(earliest, latest)`` per node.

        Returns:
            Ordered list of node ids.
        """
        if not waypoints:
            return []

        _demands = demands or {}
        _tw = time_windows or {}

        def _dist(a: str, b: str) -> float:
            return distance_matrix.get(a, {}).get(b, float("inf"))

        # Start with a random seed node
        remaining = list(waypoints)
        seed = remaining.pop(rng.randint(0, len(remaining) - 1))
        tour: List[str] = [seed]

        while remaining:
            best_node = None
            best_regret = -float("inf")
            best_position = 0

            for node in remaining:
                # Compute insertion cost at every position
                costs: List[float] = []
                for pos in range(len(tour) + 1):
                    cost = 0.0
                    if pos == 0:
                        cost = _dist(tour[0], node)
                        if len(tour) == 1:
                            pass  # just one edge
                    elif pos == len(tour):
                        cost = _dist(tour[-1], node)
                    else:
                        cost = (
                            _dist(tour[pos - 1], node)
                            + _dist(node, tour[pos])
                            - _dist(tour[pos - 1], tour[pos])
                        )
                    costs.append(cost)

                # Sort to get best and 2nd-best
                sorted_costs = sorted(costs)
                best_cost = sorted_costs[0]
                second_cost = sorted_costs[1] if len(sorted_costs) > 1 else best_cost
                regret = second_cost - best_cost

                # TW urgency bonus: tighter windows → higher regret
                if node in _tw:
                    tw_width = _tw[node][1] - _tw[node][0]
                    urgency = 1.0 / (1.0 + tw_width) if tw_width > 0 else 10.0
                    regret += urgency * best_cost * 0.5

                if regret > best_regret:
                    best_regret = regret
                    best_node = node
                    best_position = costs.index(best_cost)

            if best_node is None:
                # Fallback: random
                best_node = remaining.pop(rng.randint(0, len(remaining) - 1))
                tour.append(best_node)
            else:
                remaining.remove(best_node)
                tour.insert(best_position, best_node)

        return tour

    # ------------------------------------------------------------------ #
    # 4. Random + Perturbation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _random_perturbation(
        waypoints: List[str],
        rng: "random.Random",  # noqa: F821
    ) -> List[str]:
        """Generate a random tour, then apply perturbation operators.

        1. Shuffle waypoints randomly.
        2. Apply a random perturbation:
           - *Scramble*: reverse a random sub-segment.
           - *Swap*: swap two random positions.

        Args:
            waypoints: Node ids.
            rng: Random instance.

        Returns:
            Perturbed tour.
        """
        if not waypoints:
            return []

        tour = list(waypoints)
        rng.shuffle(tour)

        n = len(tour)
        if n < 2:
            return tour

        op = rng.choice(["scramble", "swap"])
        if op == "scramble" and n >= 3:
            i = rng.randint(0, n - 2)
            j = rng.randint(i + 1, n - 1)
            tour[i : j + 1] = reversed(tour[i : j + 1])
        elif op == "swap":
            i = rng.randint(0, n - 1)
            j = rng.randint(0, n - 1)
            tour[i], tour[j] = tour[j], tour[i]

        return tour
