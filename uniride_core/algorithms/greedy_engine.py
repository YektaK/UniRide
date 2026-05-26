"""Simple matrix-native greedy engine for core routing benchmarks."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from uniride_core.algorithms.base_engine import UnifiedEngine
from uniride_core.models import PermutationResult


class GreedyMatrixEngine(UnifiedEngine):
    """Nearest-neighbor permutation engine over explicit matrices."""

    name = "Greedy"

    def optimize_permutation(
        self,
        distance_matrix,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> PermutationResult:
        del seed
        cfg = dict(config or {})
        dm = np.asarray(distance_matrix, dtype=np.float64)
        n = dm.shape[0]
        depot = int(cfg.get("depot_index", 0))
        problem_type = str(cfg.get("problem_type", "tsp")).lower()

        if problem_type in {"cvrp", "cvrptw", "uniride", "uniride_cvrp", "uniride_cvrptw"}:
            unvisited = set(range(n))
            unvisited.discard(depot)
            current = depot
        else:
            unvisited = set(range(n))
            current = depot if 0 <= depot < n else 0

        permutation = []
        while unvisited:
            nxt = min(unvisited, key=lambda node: float(dm[current, node]))
            permutation.append(nxt)
            unvisited.remove(nxt)
            current = nxt

        cost = 0.0
        if permutation:
            if problem_type in {"cvrp", "cvrptw", "uniride", "uniride_cvrp", "uniride_cvrptw"}:
                current = depot
                for node in permutation:
                    cost += float(dm[current, node])
                    current = node
                cost += float(dm[current, depot])
            else:
                for idx, node in enumerate(permutation):
                    cost += float(dm[node, permutation[(idx + 1) % len(permutation)]])

        return PermutationResult(
            algorithm=self.name,
            permutation=permutation,
            cost=cost,
            params=cfg,
        )


__all__ = ["GreedyMatrixEngine"]
