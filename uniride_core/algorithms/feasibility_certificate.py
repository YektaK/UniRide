"""Solver-independent feasibility certificate for routing results.

Provides structured violation reporting across all algorithm outputs,
reusing existing models and matrix helpers from uniride_core.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np

from uniride_core.algorithms.split_decoder import SplitResult, calculate_route_cost, route_load
from uniride_core.models import ConstraintProfile, CostMatrix, ProblemInstance, RoutingProblem, RoutingResult

OCCURRENCE_COVERAGE = "occurrence_coverage"
DEPOT_CLOSURE = "depot_closure"
CAPACITY_VIOLATION = "capacity_violation"
DURATION_VIOLATION = "duration_violation"
TIME_WINDOW_VIOLATION = "time_window_violation"
MATRIX_SHAPE = "matrix_shape"
MISSING_ARC = "missing_arc"
ROUTE_CONTINUITY = "route_continuity"
HARD_VIOLATION = "hard_violation"


@dataclass(frozen=True)
class Violation:
    type: str
    severity: str
    details: str
    route_index: Optional[int] = None
    node: Optional[int] = None


@dataclass
class FeasibilityCertificate:
    is_feasible: bool
    violations: List[Violation] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.violations)


def check_occurrence_coverage(
    routes: Sequence[Sequence[int]],
    dimension: int,
    depot: int,
    occurrence_ids: Optional[Sequence[str]] = None,
) -> List[Violation]:
    visited = [node for route in routes for node in route]
    expected = set(range(dimension)) - {depot}
    visited_set = set(visited)
    violations: List[Violation] = []

    missing = sorted(expected - visited_set)
    if missing:
        labels = _node_labels(missing, occurrence_ids)
        violations.append(Violation(
            type=OCCURRENCE_COVERAGE,
            severity="error",
            details=f"Missing nodes: {labels}",
        ))

    extra = sorted(visited_set - expected)
    if extra:
        labels = _node_labels(extra, occurrence_ids)
        violations.append(Violation(
            type=OCCURRENCE_COVERAGE,
            severity="error",
            details=f"Unexpected nodes: {labels}",
        ))

    seen: set = set()
    duplicates: set = set()
    for node in visited:
        if node in seen:
            duplicates.add(node)
        seen.add(node)
    if duplicates:
        labels = _node_labels(sorted(duplicates), occurrence_ids)
        violations.append(Violation(
            type=OCCURRENCE_COVERAGE,
            severity="error",
            details=f"Duplicate visits: {labels}",
        ))

    return violations


def check_depot_closure(
    routes: Sequence[Sequence[int]],
    depot: int,
    dimension: int,
) -> List[Violation]:
    violations: List[Violation] = []

    if not (0 <= depot < dimension):
        violations.append(Violation(
            type=DEPOT_CLOSURE,
            severity="error",
            details=f"Depot index {depot} out of range [0, {dimension})",
        ))

    if dimension > 1 and not routes:
        violations.append(Violation(
            type=DEPOT_CLOSURE,
            severity="error",
            details="No routes returned but problem has customers",
        ))

    for idx, route in enumerate(routes):
        if not route:
            violations.append(Violation(
                type=DEPOT_CLOSURE,
                severity="error",
                details=f"Route {idx} is empty",
                route_index=idx,
            ))

    return violations


def check_capacity_vectors(
    routes: Sequence[Sequence[int]],
    demands: Optional[Sequence],
    capacities: Optional[Sequence[int]],
) -> List[Violation]:
    if demands is None or capacities is None:
        return []

    demand_vectors = _normalize_demands(demands)
    capacity_vec = _normalize_capacity(capacities)
    violations: List[Violation] = []

    for idx, route in enumerate(routes):
        if not route:
            continue
        load = route_load(route, demand_vectors)
        for d in range(min(len(load), len(capacity_vec))):
            if load[d] > capacity_vec[d]:
                violations.append(Violation(
                    type=CAPACITY_VIOLATION,
                    severity="error",
                    details=f"Route {idx} load[{d}]={load[d]} exceeds capacity[{d}]={capacity_vec[d]}",
                    route_index=idx,
                ))

    return violations


def check_duration(
    routes: Sequence[Sequence[int]],
    matrix: Any,
    depot: int,
    max_route_duration: Optional[float],
    service_times: Optional[Sequence[int]] = None,
) -> List[Violation]:
    if max_route_duration is None or matrix is None:
        return []

    violations: List[Violation] = []
    for idx, route in enumerate(routes):
        if not route:
            continue
        cost = calculate_route_cost(route, matrix, depot)
        if service_times:
            cost += sum(
                service_times[node] for node in route if node < len(service_times)
            )
        if cost > max_route_duration:
            violations.append(Violation(
                type=DURATION_VIOLATION,
                severity="error",
                details=f"Route {idx} duration {cost:.1f} exceeds max {max_route_duration}",
                route_index=idx,
            ))

    return violations


def check_time_windows(
    routes: Sequence[Sequence[int]],
    matrix: Any,
    depot: int,
    time_windows: Optional[Sequence[Tuple[int, int]]],
    service_times: Optional[Sequence[int]] = None,
    direction: str = "pickup",
    target_time: Optional[int] = None,
    offset_minutes: int = 10,
) -> List[Violation]:
    if time_windows is None or matrix is None:
        return []

    mat = np.asarray(matrix, dtype=np.float64)
    service = list(service_times or [0] * len(time_windows))
    violations: List[Violation] = []

    for idx, route in enumerate(routes):
        if not route:
            continue

        if direction.lower() == "pickup":
            latest = (
                target_time
                if target_time is not None
                else max(time_windows[node][1] for node in route if node < len(time_windows))
            )
            route_cost = float(calculate_route_cost(route, mat, depot))
            if not math.isfinite(route_cost):
                violations.append(Violation(
                    type=TIME_WINDOW_VIOLATION,
                    severity="error",
                    details=f"Route {idx} has a non-finite travel duration",
                    route_index=idx,
                ))
                continue
            current = float(latest) - route_cost - float(offset_minutes)
            if current < 0:
                violations.append(Violation(
                    type=TIME_WINDOW_VIOLATION,
                    severity="error",
                    details=f"Route {idx} cannot start early enough for pickup direction",
                    route_index=idx,
                ))
                continue
        else:
            current = (
                target_time
                if target_time is not None
                else min(time_windows[node][0] for node in route if node < len(time_windows))
            )

        prev = depot
        for node in route:
            if node >= len(time_windows):
                prev = node
                continue
            travel_duration = float(mat[prev, node])
            if not math.isfinite(travel_duration):
                violations.append(Violation(
                    type=TIME_WINDOW_VIOLATION,
                    severity="error",
                    details=f"Route {idx} node {node} has a non-finite travel duration",
                    route_index=idx,
                    node=node,
                ))
                break
            current += travel_duration
            earliest, latest_tw = time_windows[node]
            if current > latest_tw:
                violations.append(Violation(
                    type=TIME_WINDOW_VIOLATION,
                    severity="error",
                    details=f"Route {idx} node {node} arrival {current} exceeds latest {latest_tw}",
                    route_index=idx,
                    node=node,
                ))
            elif current < earliest:
                current = earliest
            service_duration = float(service[node]) if node < len(service) else 0.0
            if not math.isfinite(service_duration):
                violations.append(Violation(
                    type=TIME_WINDOW_VIOLATION,
                    severity="error",
                    details=f"Route {idx} node {node} has a non-finite service duration",
                    route_index=idx,
                    node=node,
                ))
                break
            current += service_duration
            prev = node

    return violations


def check_matrix_shape(matrix: Any, dimension: int) -> List[Violation]:
    if matrix is None:
        return [Violation(
            type=MATRIX_SHAPE,
            severity="error",
            details="Matrix is None",
        )]

    try:
        arr = np.asarray(matrix)
    except (TypeError, ValueError):
        return [Violation(
            type=MATRIX_SHAPE,
            severity="error",
            details="Matrix cannot be converted to array",
        )]

    violations: List[Violation] = []

    if arr.ndim != 2:
        violations.append(Violation(
            type=MATRIX_SHAPE,
            severity="error",
            details=f"Matrix has {arr.ndim} dimensions, expected 2",
        ))
        return violations

    rows, cols = arr.shape
    if rows != cols:
        violations.append(Violation(
            type=MATRIX_SHAPE,
            severity="error",
            details=f"Matrix is not square: {rows}x{cols}",
        ))

    if rows != dimension:
        violations.append(Violation(
            type=MATRIX_SHAPE,
            severity="error",
            details=f"Matrix dimension {rows} does not match problem dimension {dimension}",
        ))

    return violations


def check_missing_arcs(
    routes: Sequence[Sequence[int]],
    matrix: Any,
    depot: int,
) -> List[Violation]:
    if matrix is None:
        return []

    mat = np.asarray(matrix, dtype=np.float64)
    violations: List[Violation] = []

    for idx, route in enumerate(routes):
        if not route:
            continue

        arcs = [(depot, route[0])]
        for i in range(len(route) - 1):
            arcs.append((route[i], route[i + 1]))
        arcs.append((route[-1], depot))

        for src, dst in arcs:
            if src < 0 or dst < 0 or src >= mat.shape[0] or dst >= mat.shape[1]:
                violations.append(Violation(
                    type=MISSING_ARC,
                    severity="error",
                    details=f"Route {idx} arc ({src},{dst}) out of matrix bounds",
                    route_index=idx,
                ))
                continue
            val = mat[src, dst]
            if not math.isfinite(val):
                violations.append(Violation(
                    type=MISSING_ARC,
                    severity="error",
                    details=f"Route {idx} arc ({src},{dst}) has non-finite value {val}",
                    route_index=idx,
                ))

    return violations


def check_route_continuity(
    routes: Sequence[Sequence[int]],
    dimension: int,
) -> List[Violation]:
    violations: List[Violation] = []

    for idx, route in enumerate(routes):
        seen: set = set()
        for node in route:
            if node < 0 or node >= dimension:
                violations.append(Violation(
                    type=ROUTE_CONTINUITY,
                    severity="error",
                    details=f"Route {idx} node {node} out of range [0, {dimension})",
                    route_index=idx,
                    node=node,
                ))
            elif node in seen:
                violations.append(Violation(
                    type=ROUTE_CONTINUITY,
                    severity="error",
                    details=f"Route {idx} visits node {node} more than once",
                    route_index=idx,
                    node=node,
                ))
            seen.add(node)

    return violations


def check_hard_violation_rejection(
    success: Optional[bool],
    violations: Sequence[Violation],
) -> List[Violation]:
    if success is True and len(violations) > 0:
        return [Violation(
            type=HARD_VIOLATION,
            severity="error",
            details=f"Result claims success=True but has {len(violations)} violation(s)",
        )]
    return []


def certify_routing_result(
    result: RoutingResult,
    problem: RoutingProblem,
    success: Optional[bool] = None,
) -> FeasibilityCertificate:
    matrix = problem.matrix.values
    dimension = problem.dimension
    constraints = problem.constraints
    depot = constraints.depot_index
    occurrence_ids = problem.matrix.occurrence_ids

    routes = result.routes if result.routes else ([result.tour] if result.tour else [])

    violations: List[Violation] = []
    violations.extend(check_matrix_shape(matrix, dimension))
    violations.extend(check_route_continuity(routes, dimension))
    violations.extend(check_depot_closure(routes, depot, dimension))
    violations.extend(check_missing_arcs(routes, matrix, depot))
    violations.extend(check_occurrence_coverage(routes, dimension, depot, occurrence_ids))
    violations.extend(check_capacity_vectors(routes, constraints.demands, constraints.capacities))
    violations.extend(check_duration(
        routes, matrix, depot, constraints.max_route_duration, constraints.service_times
    ))
    violations.extend(check_time_windows(
        routes, matrix, depot, constraints.time_windows, constraints.service_times,
        constraints.direction, constraints.target_time, constraints.offset_minutes,
    ))

    if success is None:
        success = (result.capacity_violations == 0 and result.tw_violations == 0)
    violations.extend(check_hard_violation_rejection(success, violations))

    return FeasibilityCertificate(is_feasible=len(violations) == 0, violations=violations)


def certify_split_result(
    result: SplitResult,
    problem: RoutingProblem,
    success: Optional[bool] = None,
) -> FeasibilityCertificate:
    matrix = problem.matrix.values
    dimension = problem.dimension
    constraints = problem.constraints
    depot = constraints.depot_index
    occurrence_ids = problem.matrix.occurrence_ids
    routes = result.routes

    violations: List[Violation] = []
    violations.extend(check_matrix_shape(matrix, dimension))
    violations.extend(check_route_continuity(routes, dimension))
    violations.extend(check_depot_closure(routes, depot, dimension))
    violations.extend(check_missing_arcs(routes, matrix, depot))
    violations.extend(check_occurrence_coverage(routes, dimension, depot, occurrence_ids))
    violations.extend(check_capacity_vectors(routes, constraints.demands, constraints.capacities))
    violations.extend(check_duration(
        routes, matrix, depot, constraints.max_route_duration, constraints.service_times
    ))
    violations.extend(check_time_windows(
        routes, matrix, depot, constraints.time_windows, constraints.service_times,
        constraints.direction, constraints.target_time, constraints.offset_minutes,
    ))

    if success is None:
        success = (result.capacity_violations == 0 and result.tw_violations == 0)
    violations.extend(check_hard_violation_rejection(success, violations))

    return FeasibilityCertificate(is_feasible=len(violations) == 0, violations=violations)


def certify_problem_instance(
    result: RoutingResult,
    instance: ProblemInstance,
    success: Optional[bool] = None,
) -> FeasibilityCertificate:
    matrix = instance.time_matrix if instance.is_time_matrix else instance.dist_matrix
    dimension = instance.dimension
    depot = instance.depot_index
    routes = result.routes if result.routes else ([result.tour] if result.tour else [])

    demands = instance.demands
    capacities = instance.capacities
    if capacities is None and instance.capacity is not None:
        capacities = [instance.capacity]

    violations: List[Violation] = []
    violations.extend(check_matrix_shape(matrix, dimension))
    violations.extend(check_route_continuity(routes, dimension))
    violations.extend(check_depot_closure(routes, depot, dimension))
    violations.extend(check_missing_arcs(routes, matrix, depot))
    violations.extend(check_occurrence_coverage(routes, dimension, depot))
    violations.extend(check_capacity_vectors(routes, demands, capacities))
    violations.extend(check_duration(
        routes, matrix, depot, instance.max_route_duration, instance.service_times
    ))
    violations.extend(check_time_windows(
        routes, matrix, depot, instance.time_windows, instance.service_times,
        instance.direction,
    ))

    if success is None:
        success = (result.capacity_violations == 0 and result.tw_violations == 0)
    violations.extend(check_hard_violation_rejection(success, violations))

    return FeasibilityCertificate(is_feasible=len(violations) == 0, violations=violations)


def _node_labels(nodes: Sequence[int], occurrence_ids: Optional[Sequence[str]]) -> str:
    if occurrence_ids:
        labels = []
        for n in nodes:
            if n < len(occurrence_ids):
                labels.append(f"{n}({occurrence_ids[n]})")
            else:
                labels.append(str(n))
        return ", ".join(labels)
    return ", ".join(str(n) for n in nodes)


def _normalize_demands(demands: Sequence) -> List[List[int]]:
    result: List[List[int]] = []
    for demand in demands:
        if isinstance(demand, (list, tuple)):
            result.append([int(x) for x in demand])
        else:
            result.append([int(demand)])
    return result


def _normalize_capacity(capacity: Any) -> List[int]:
    if isinstance(capacity, (list, tuple)):
        return [int(x) for x in capacity]
    return [int(capacity)]


__all__ = [
    "OCCURRENCE_COVERAGE",
    "DEPOT_CLOSURE",
    "CAPACITY_VIOLATION",
    "DURATION_VIOLATION",
    "TIME_WINDOW_VIOLATION",
    "MATRIX_SHAPE",
    "MISSING_ARC",
    "ROUTE_CONTINUITY",
    "HARD_VIOLATION",
    "Violation",
    "FeasibilityCertificate",
    "check_occurrence_coverage",
    "check_depot_closure",
    "check_capacity_vectors",
    "check_duration",
    "check_time_windows",
    "check_matrix_shape",
    "check_missing_arcs",
    "check_route_continuity",
    "check_hard_violation_rejection",
    "certify_routing_result",
    "certify_split_result",
    "certify_problem_instance",
]
