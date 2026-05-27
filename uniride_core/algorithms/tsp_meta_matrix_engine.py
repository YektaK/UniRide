"""UnifiedEngine adapter for core TSP metaheuristic solver functions."""

from __future__ import annotations

import random
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import numpy as np

from uniride_core.algorithms.base_engine import UnifiedEngine
from uniride_core.models import PermutationResult

TSPSolver = Callable[
    [List[str], Callable[[List[str]], float], random.Random, Mapping[str, object]],
    Tuple[List[str], float],
]


class TSPMetaMatrixEngine(UnifiedEngine):
    """Expose string-keyed core TSP metaheuristics as matrix-native engines."""

    def __init__(self, name: str, solver: TSPSolver):
        self.name = name
        self._solver = solver

    def optimize_permutation(
        self,
        distance_matrix,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> PermutationResult:
        cfg = dict(config or {})
        dm = np.asarray(distance_matrix, dtype=np.float64)
        n = dm.shape[0]
        problem_type = str(cfg.get("problem_type", "tsp")).lower()
        depot = int(cfg.get("depot_index", 0) or 0)
        routing_problem = problem_type in {"cvrp", "cvrptw", "uniride", "uniride_cvrp", "uniride_cvrptw"}

        node_indices = [idx for idx in range(n) if not routing_problem or idx != depot]
        waypoints = [f"L{idx}" for idx in node_indices]

        def duration_func(route: List[str]) -> float:
            return _route_cost(route, dm, depot=depot, routing_problem=routing_problem)

        started = time.perf_counter()
        route, cost = self._solver(waypoints, duration_func, random.Random(seed), cfg)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        permutation = [int(location[1:]) if location.startswith("L") else int(location) for location in route]

        return PermutationResult(
            algorithm=self.name,
            permutation=permutation,
            cost=float(cost),
            time_ms=elapsed_ms,
            iterations=int(cfg.get("max_iterations", 0) or 0),
            seed=seed,
            params=cfg,
        )


def _route_cost(route: List[str], matrix: np.ndarray, *, depot: int, routing_problem: bool) -> float:
    if not route:
        return 0.0

    indices = [int(location[1:]) if location.startswith("L") else int(location) for location in route]
    total = 0.0

    if routing_problem:
        current = depot
        for node in indices:
            total += float(matrix[current, node])
            current = node
        total += float(matrix[current, depot])
        return total

    for idx, current in enumerate(indices):
        nxt = indices[(idx + 1) % len(indices)]
        total += float(matrix[current, nxt])
    return total


__all__ = ["TSPMetaMatrixEngine", "TSPSolver"]
