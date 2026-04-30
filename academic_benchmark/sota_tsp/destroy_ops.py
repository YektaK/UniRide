"""
ALNS Destroy Operators — TSP variant.

Adapted from optimizer_api/strategies/sota_common/destroy_operators.py.
Works on List[int] tours with List[List[float]] distance matrix.
"""

import random
from typing import List, Tuple, Optional


class RandomRemoval:
    def destroy(self, tour: List[int], n_remove: int, rng: random.Random,
                dm: Optional[List[List[float]]] = None) -> Tuple[List[int], List[int]]:
        indices = rng.sample(range(len(tour)), min(n_remove, len(tour)))
        removed = [tour[i] for i in sorted(indices, reverse=True)]
        remaining = [tour[i] for i in range(len(tour)) if i not in set(indices)]
        return removed, remaining


class WorstRemoval:
    def destroy(self, tour: List[int], n_remove: int, rng: random.Random,
                dm: Optional[List[List[float]]] = None) -> Tuple[List[int], List[int]]:
        if dm is None or len(tour) < 3:
            return RandomRemoval().destroy(tour, n_remove, rng, dm)
        remaining = list(tour)
        removed = []
        for _ in range(min(n_remove, len(tour) - 2)):
            worst_idx = -1
            worst_cost = -1.0
            n = len(remaining)
            for i in range(n):
                prev_node = remaining[(i - 1) % n]
                curr_node = remaining[i]
                next_node = remaining[(i + 1) % n]
                edge_cost = dm[prev_node][curr_node] + dm[curr_node][next_node]
                bypass_cost = dm[prev_node][next_node]
                cost_delta = edge_cost - bypass_cost
                if cost_delta > worst_cost:
                    worst_cost = cost_delta
                    worst_idx = i
            if worst_idx >= 0:
                removed.append(remaining.pop(worst_idx))
        return removed, remaining


class ShawRemoval:
    def destroy(self, tour: List[int], n_remove: int, rng: random.Random,
                dm: Optional[List[List[float]]] = None) -> Tuple[List[int], List[int]]:
        if dm is None or len(tour) < 3:
            return RandomRemoval().destroy(tour, n_remove, rng, dm)
        remaining = list(tour)
        removed = []
        seed_idx = rng.randrange(len(remaining))
        removed.append(remaining.pop(seed_idx))
        for _ in range(min(n_remove - 1, len(remaining) - 2)):
            if not remaining:
                break
            ref = removed[-1]
            sims = [(dm[ref][n], i, n) for i, n in enumerate(remaining)]
            sims.sort(key=lambda x: x[0])
            pick = sims[rng.randint(0, min(2, len(sims) - 1))]
            removed.append(remaining.pop(pick[1]))
        return removed, remaining


class RelatedRemoval:
    def destroy(self, tour: List[int], n_remove: int, rng: random.Random,
                dm: Optional[List[List[float]]] = None) -> Tuple[List[int], List[int]]:
        if dm is None or len(tour) < 3:
            return RandomRemoval().destroy(tour, n_remove, rng, dm)
        remaining = list(tour)
        removed = []
        seed_idx = rng.randrange(len(remaining))
        seed_node = remaining.pop(seed_idx)
        removed.append(seed_node)
        for _ in range(min(n_remove - 1, len(remaining) - 2)):
            if not remaining:
                break
            best_idx = -1
            best_dist = float("inf")
            for i, node in enumerate(remaining):
                d = dm[seed_node][node]
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            if best_idx >= 0:
                removed.append(remaining.pop(best_idx))
        return removed, remaining
