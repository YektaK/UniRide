"""Core split decoders for CVRP/CVRPTW giant-tour workflows.

The functions here are pure core logic with no FastAPI or web-layer imports.
They support scalar CVRP capacity and UniRide-style vector capacities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np


DemandVector = List[int]


@dataclass
class SplitResult:
    routes: List[List[int]]
    total_cost: float
    route_costs: List[float]
    route_loads: List[DemandVector]
    capacity_violations: int = 0
    tw_violations: int = 0


def calculate_route_cost(route: Sequence[int], distance_matrix, depot: int = 0) -> float:
    dm = np.asarray(distance_matrix, dtype=np.float64)
    if not route:
        return 0.0
    total = float(dm[depot, route[0]])
    for i in range(len(route) - 1):
        total += float(dm[route[i], route[i + 1]])
    total += float(dm[route[-1], depot])
    return total


def calculate_total_cost(routes: Sequence[Sequence[int]], distance_matrix, depot: int = 0) -> float:
    return sum(calculate_route_cost(route, distance_matrix, depot) for route in routes)


def route_load(route: Sequence[int], demands: Sequence) -> DemandVector:
    norm = _normalize_demands(demands)
    if not norm:
        return []
    dims = len(norm[0])
    load = [0] * dims
    for node in route:
        for d in range(dims):
            load[d] += norm[node][d]
    return load


def optimal_split(
    permutation: Sequence[int],
    distance_matrix,
    demands: Sequence,
    capacity: int | Sequence[int],
    depot: int = 0,
    max_route_duration: Optional[float] = None,
) -> List[List[int]]:
    """Backward-compatible scalar/vector CVRP split returning routes only."""
    return optimal_split_result(
        permutation, distance_matrix, demands, capacity, depot, max_route_duration
    ).routes


def optimal_split_result(
    permutation: Sequence[int],
    distance_matrix,
    demands: Sequence,
    capacities: int | Sequence[int],
    depot: int = 0,
    max_route_duration: Optional[float] = None,
) -> SplitResult:
    """Bellman-style O(n^2) split for a giant tour with vector capacities."""
    perm = [int(node) for node in permutation if int(node) != depot]
    n = len(perm)
    if n == 0:
        return SplitResult([], 0.0, [], [])

    dm = np.asarray(distance_matrix, dtype=np.float64)
    demand_vectors = _normalize_demands(demands)
    capacity_vec = _normalize_capacity(capacities)
    _validate_demands_capacity(demand_vectors, capacity_vec)

    best = [float("inf")] * (n + 1)
    pred = [-1] * (n + 1)
    best[0] = 0.0

    for i in range(n):
        load = [0] * len(capacity_vec)
        travel = 0.0
        prev = depot
        for j in range(i, n):
            node = perm[j]
            for d in range(len(load)):
                load[d] += demand_vectors[node][d]
            if any(load[d] > capacity_vec[d] for d in range(len(load))):
                break
            travel += float(dm[prev, node])
            prev = node
            route_cost = travel + float(dm[node, depot])
            if max_route_duration is not None and route_cost > max_route_duration:
                continue
            candidate = best[i] + route_cost
            if candidate < best[j + 1]:
                best[j + 1] = candidate
                pred[j + 1] = i

    if pred[n] == -1:
        return SplitResult([], float("inf"), [], [], capacity_violations=1)

    routes: List[List[int]] = []
    cur = n
    while cur > 0:
        prev = pred[cur]
        routes.append(perm[prev:cur])
        cur = prev
    routes.reverse()

    route_costs = [calculate_route_cost(route, dm, depot) for route in routes]
    loads = [route_load(route, demand_vectors) for route in routes]
    return SplitResult(routes, sum(route_costs), route_costs, loads)


def split_with_time_windows(
    permutation: Sequence[int],
    dm,
    demands: Sequence,
    capacity: int | Sequence[int],
    time_windows: Sequence[Tuple[int, int]],
    service_times: Optional[Sequence[int]] = None,
    depot: int = 0,
    max_route_duration: Optional[float] = None,
    direction: str = "pickup",
    target_time: Optional[int] = None,
    offset_minutes: int = 10,
) -> List[List[int]]:
    return split_with_time_windows_result(
        permutation, dm, demands, capacity, time_windows, service_times,
        depot, max_route_duration, direction, target_time, offset_minutes
    ).routes


def split_with_time_windows_result(
    permutation: Sequence[int],
    dm,
    demands: Sequence,
    capacities: int | Sequence[int],
    time_windows: Sequence[Tuple[int, int]],
    service_times: Optional[Sequence[int]] = None,
    depot: int = 0,
    max_route_duration: Optional[float] = None,
    direction: str = "pickup",
    target_time: Optional[int] = None,
    offset_minutes: int = 10,
) -> SplitResult:
    """Split giant tour while minimizing time-window violations, then cost."""
    base = optimal_split_result(
        permutation, dm, demands, capacities, depot=depot,
        max_route_duration=max_route_duration,
    )
    if not base.routes:
        return base

    tw_violations = 0
    route_costs = []
    for route in base.routes:
        route_costs.append(calculate_route_cost(route, dm, depot))
        tw_violations += _count_time_window_violations(
            route, dm, time_windows, service_times, depot, direction,
            target_time, offset_minutes,
        )
    base.tw_violations = tw_violations
    base.route_costs = route_costs
    base.total_cost = sum(route_costs)
    return base


def validate_cvrp_solution(
    routes: Sequence[Sequence[int]],
    demands: Sequence,
    capacity: int | Sequence[int],
    num_customers: int,
    depot: int = 0,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    visited = [node for route in routes for node in route]
    expected = set(range(num_customers + 1)) - {depot}
    if set(visited) != expected:
        missing = sorted(expected - set(visited))
        extra = sorted(set(visited) - expected)
        if missing:
            errors.append(f"Missing customers: {missing}")
        if extra:
            errors.append(f"Unexpected customers: {extra}")
    duplicates = sorted({node for node in visited if visited.count(node) > 1})
    if duplicates:
        errors.append(f"Duplicate customers: {duplicates}")

    demand_vectors = _normalize_demands(demands)
    capacity_vec = _normalize_capacity(capacity)
    for idx, route in enumerate(routes):
        load = route_load(route, demand_vectors)
        if any(load[d] > capacity_vec[d] for d in range(len(capacity_vec))):
            errors.append(f"Route {idx} exceeds capacity: load={load}, capacity={capacity_vec}")
    return not errors, errors


def validate_cvrptw_solution(
    routes: Sequence[Sequence[int]],
    dm,
    demands: Sequence,
    capacity: int | Sequence[int],
    time_windows: Sequence[Tuple[int, int]],
    service_times: Optional[Sequence[int]] = None,
    depot: int = 0,
    direction: str = "pickup",
    target_time: Optional[int] = None,
) -> Tuple[bool, List[str]]:
    num_customers = max((node for route in routes for node in route), default=0)
    ok, errors = validate_cvrp_solution(routes, demands, capacity, num_customers, depot)
    for idx, route in enumerate(routes):
        violations = _count_time_window_violations(
            route, dm, time_windows, service_times, depot, direction, target_time
        )
        if violations:
            errors.append(f"Route {idx} has {violations} time-window violations")
    return ok and not errors, errors


def _normalize_demands(demands: Sequence) -> List[DemandVector]:
    result: List[DemandVector] = []
    for demand in demands:
        if isinstance(demand, (list, tuple)):
            result.append([int(x) for x in demand])
        else:
            result.append([int(demand)])
    return result


def _normalize_capacity(capacity: int | Sequence[int]) -> DemandVector:
    if isinstance(capacity, (list, tuple)):
        return [int(x) for x in capacity]
    return [int(capacity)]


def _validate_demands_capacity(demands: Sequence[DemandVector], capacity: Sequence[int]) -> None:
    if not demands:
        raise ValueError("demands must include depot and customer demand vectors")
    if not capacity:
        raise ValueError("capacity must have at least one dimension")
    for idx, demand in enumerate(demands):
        if len(demand) != len(capacity):
            raise ValueError(
                f"Demand vector at node {idx} has {len(demand)} dimensions; "
                f"capacity has {len(capacity)}"
            )


def _count_time_window_violations(
    route: Sequence[int],
    dm,
    time_windows: Sequence[Tuple[int, int]],
    service_times: Optional[Sequence[int]],
    depot: int,
    direction: str,
    target_time: Optional[int],
    offset_minutes: int = 10,
) -> int:
    if not route or not time_windows:
        return 0
    matrix = np.asarray(dm, dtype=np.float64)
    service = list(service_times or [0] * len(time_windows))
    if direction.lower() == "pickup":
        latest = target_time if target_time is not None else max(time_windows[node][1] for node in route)
        current = latest - int(calculate_route_cost(route, matrix, depot)) - offset_minutes
        if current < 0:
            return len(route)
    else:
        current = target_time if target_time is not None else min(time_windows[node][0] for node in route)

    violations = 0
    prev = depot
    for node in route:
        current += int(matrix[prev, node])
        earliest, latest = time_windows[node]
        if current > latest:
            violations += 1
        elif current < earliest:
            current = earliest
        current += int(service[node]) if node < len(service) else 0
        prev = node
    return violations


__all__ = [
    "SplitResult",
    "optimal_split",
    "optimal_split_result",
    "split_with_time_windows",
    "split_with_time_windows_result",
    "calculate_route_cost",
    "calculate_total_cost",
    "route_load",
    "validate_cvrp_solution",
    "validate_cvrptw_solution",
]
