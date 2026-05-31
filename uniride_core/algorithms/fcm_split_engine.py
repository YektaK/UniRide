"""FCM split-route-stitch matrix engine for large TSP research runs."""

from __future__ import annotations

import random
import threading
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from uniride_core.algorithms.base_engine import UnifiedEngine
from uniride_core.algorithms.clustering import Point
from uniride_core.algorithms.clustering_strategies.fuzzy_cmeans_enhanced import (
    fuzzy_c_means_with_membership,
)
from uniride_core.algorithms.tsp_meta_engines import solve_two_opt_tsp
from uniride_core.algorithms.tsp_meta_matrix_engine import TSPSolver
from uniride_core.models import PermutationResult, RoutingProblem

_FCM_LOCK = threading.Lock()


class FCMSplitMatrixEngine(UnifiedEngine):
    """Divide large matrix-native TSPs into FCM clusters, solve, stitch, polish."""

    def __init__(self, name: str, solver: TSPSolver):
        self.name = name
        self._solver = solver

    def solve_problem(
        self,
        problem: RoutingProblem,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ):
        cfg = dict(config or {})
        if problem.coordinates and "coordinates" not in cfg:
            cfg["coordinates"] = list(problem.coordinates)
        return super().solve_problem(problem, config=cfg, seed=seed)

    def optimize_permutation(
        self,
        distance_matrix,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> PermutationResult:
        cfg = dict(config or {})
        dm = np.asarray(distance_matrix, dtype=np.float64)
        n = int(dm.shape[0])
        started = time.perf_counter()
        rng = random.Random(seed)

        problem_type = str(cfg.get("problem_type", "tsp")).lower()
        depot = int(cfg.get("depot_index", 0) or 0)
        routing_problem = problem_type in {"cvrp", "cvrptw", "uniride", "uniride_cvrp", "uniride_cvrptw"}
        node_indices = [idx for idx in range(n) if not routing_problem or idx != depot]

        if len(node_indices) <= 2:
            route = node_indices[:]
            cost = _index_route_cost(route, dm, depot=depot, routing_problem=routing_problem)
            return self._result(route, cost, started, cfg, seed)

        coordinates = _coordinates_from_config(cfg, n)
        min_cluster_size = max(2, int(cfg.get("fcm_min_cluster_size", 4) or 4))
        requested_k = int(cfg.get("fcm_clusters", 3) or 3)
        k = max(1, min(requested_k, max(1, len(node_indices) // min_cluster_size)))

        if k <= 1:
            route, cost = self._solve_full(node_indices, dm, cfg, rng, depot, routing_problem)
            return self._result(route, cost, started, cfg, seed)

        clusters = _cluster_node_indices(node_indices, coordinates, k, cfg, seed)
        cluster_routes = [
            self._solve_cluster(cluster, dm, cfg, rng, depot, routing_problem)
            for cluster in clusters
            if cluster
        ]
        stitched = _stitch_cluster_routes(cluster_routes, coordinates, dm, routing_problem=routing_problem, depot=depot)
        stitched = _sanitize_permutation(stitched, node_indices)

        if bool(cfg.get("fcm_polish", True)) and len(stitched) > 3:
            stitched, cost = self._polish(stitched, dm, cfg, rng, depot, routing_problem)
        else:
            cost = _index_route_cost(stitched, dm, depot=depot, routing_problem=routing_problem)

        return self._result(stitched, cost, started, cfg, seed)

    def _solve_full(
        self,
        node_indices: Sequence[int],
        dm: np.ndarray,
        cfg: Mapping[str, Any],
        rng: random.Random,
        depot: int,
        routing_problem: bool,
    ) -> Tuple[List[int], float]:
        labels = [_label(idx) for idx in node_indices]
        route, cost = self._solver(labels, _duration_func(dm, depot, routing_problem), rng, cfg)
        return [_parse_label(label) for label in route], float(cost)

    def _solve_cluster(
        self,
        cluster: Sequence[int],
        dm: np.ndarray,
        cfg: Mapping[str, Any],
        rng: random.Random,
        depot: int,
        routing_problem: bool,
    ) -> List[int]:
        if len(cluster) <= 1:
            return list(cluster)
        labels = [_label(idx) for idx in cluster]
        route, _ = self._solver(labels, _duration_func(dm, depot, routing_problem), rng, cfg)
        return _sanitize_permutation([_parse_label(label) for label in route], cluster)

    def _polish(
        self,
        route: List[int],
        dm: np.ndarray,
        cfg: Mapping[str, Any],
        rng: random.Random,
        depot: int,
        routing_problem: bool,
    ) -> Tuple[List[int], float]:
        labels = [_label(idx) for idx in route]
        polish_cfg = {
            "max_iterations": int(cfg.get("fcm_polish_iterations", 200) or 200),
            "multi_start": False,
        }
        polished, cost = solve_two_opt_tsp(
            labels,
            _duration_func(dm, depot, routing_problem),
            rng,
            polish_cfg,
            initial_route=labels,
        )
        return [_parse_label(label) for label in polished], float(cost)

    def _result(
        self,
        permutation: List[int],
        cost: float,
        started: float,
        cfg: Dict[str, Any],
        seed: Optional[int],
    ) -> PermutationResult:
        return PermutationResult(
            algorithm=self.name,
            permutation=permutation,
            cost=float(cost),
            time_ms=(time.perf_counter() - started) * 1000.0,
            iterations=int(cfg.get("max_iterations", cfg.get("iterations", 0)) or 0),
            seed=seed,
            params=cfg,
        )


def _cluster_node_indices(
    node_indices: Sequence[int],
    coordinates: Sequence[Tuple[float, float]],
    k: int,
    cfg: Mapping[str, Any],
    seed: Optional[int],
) -> List[List[int]]:
    points = [
        Point(
            id=str(idx),
            lat=float(coordinates[idx][1]),
            lng=float(coordinates[idx][0]),
            disability_type="So",
            location_code=_label(idx),
        )
        for idx in node_indices
    ]
    with _FCM_LOCK:
        state = random.getstate()
        random.seed(seed)
        try:
            _, _, assignments = fuzzy_c_means_with_membership(
                points,
                k=k,
                filter_limit=int(cfg.get("fcm_iterations", 100) or 100),
                m=float(cfg.get("fcm_m", 2.0) or 2.0),
            )
        finally:
            random.setstate(state)

    clusters: List[List[int]] = [[] for _ in range(k)]
    for idx, cluster_idx in zip(node_indices, assignments):
        clusters[int(cluster_idx)].append(int(idx))
    return [cluster for cluster in clusters if cluster]


def _stitch_cluster_routes(
    cluster_routes: Sequence[List[int]],
    coordinates: Sequence[Tuple[float, float]],
    dm: np.ndarray,
    *,
    routing_problem: bool,
    depot: int,
) -> List[int]:
    remaining = [route[:] for route in cluster_routes if route]
    if not remaining:
        return []

    centroids = [_centroid(route, coordinates) for route in remaining]
    current_idx = min(range(len(remaining)), key=lambda idx: (centroids[idx][0], centroids[idx][1], min(remaining[idx])))
    ordered: List[int] = []

    while remaining:
        route = remaining.pop(current_idx)
        centroids.pop(current_idx)
        route = _best_orientation(ordered[-1] if ordered else depot, route, dm, routing_problem)
        ordered.extend(route)

        if not remaining:
            break
        last = ordered[-1]
        current_idx = min(
            range(len(remaining)),
            key=lambda idx: min(float(dm[last, remaining[idx][0]]), float(dm[last, remaining[idx][-1]])),
        )

    return ordered


def _best_orientation(previous: int, route: List[int], dm: np.ndarray, routing_problem: bool) -> List[int]:
    if len(route) <= 1:
        return route
    forward = float(dm[previous, route[0]])
    reverse = float(dm[previous, route[-1]])
    return route[:] if forward <= reverse else list(reversed(route))


def _centroid(route: Sequence[int], coordinates: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    return (
        sum(float(coordinates[idx][0]) for idx in route) / len(route),
        sum(float(coordinates[idx][1]) for idx in route) / len(route),
    )


def _coordinates_from_config(cfg: Mapping[str, Any], n: int) -> List[Tuple[float, float]]:
    raw = cfg.get("coordinates")
    if raw and len(raw) >= n:
        return [(float(pair[0]), float(pair[1])) for pair in raw]
    return [(float(idx), 0.0) for idx in range(n)]


def _duration_func(dm: np.ndarray, depot: int, routing_problem: bool) -> Callable[[List[str]], float]:
    def duration(route: List[str]) -> float:
        return _index_route_cost([_parse_label(label) for label in route], dm, depot=depot, routing_problem=routing_problem)

    return duration


def _index_route_cost(route: Sequence[int], dm: np.ndarray, *, depot: int, routing_problem: bool) -> float:
    if not route:
        return 0.0
    total = 0.0
    if routing_problem:
        current = depot
        for node in route:
            total += float(dm[current, node])
            current = node
        total += float(dm[current, depot])
        return total
    for idx, current in enumerate(route):
        total += float(dm[current, route[(idx + 1) % len(route)]])
    return total


def _sanitize_permutation(route: Sequence[int], expected: Sequence[int]) -> List[int]:
    expected_list = [int(idx) for idx in expected]
    expected_set = set(expected_list)
    seen = set()
    cleaned = []
    for node in route:
        node = int(node)
        if node in expected_set and node not in seen:
            cleaned.append(node)
            seen.add(node)
    cleaned.extend(idx for idx in expected_list if idx not in seen)
    return cleaned


def _label(idx: int) -> str:
    return f"L{idx}"


def _parse_label(label: str) -> int:
    return int(label[1:]) if isinstance(label, str) and label.startswith("L") else int(label)


__all__ = ["FCMSplitMatrixEngine"]
