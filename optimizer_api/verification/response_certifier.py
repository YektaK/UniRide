"""Certify a strategy response against a ProblemInstance into a JSON-safe dict.

Boundary certificates are produced from the response's own reported data
(route_details chains, durations, counts, ids); they attest internal
consistency and constraint satisfaction, not equivalence with any
authoritative source matrix. Source/unit/provenance validation of the
synthesized matrix against Package E-derived sources is deferred.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Optional

from uniride_core.adapters.demand_builder import (
    student_capacity_demand,
    student_occurrence_keys,
)
from uniride_core.algorithms.distance import tsplib_distance_by_type
from uniride_core.algorithms.feasibility_certificate import (
    Violation,
    check_capacity_vectors,
    check_depot_closure,
    check_duration,
    check_hard_violation_rejection,
    check_occurrence_coverage,
    check_time_windows,
    certify_problem_instance,
)
from uniride_core.models import ProblemInstance, RoutingResult


def _build_location_map(problem: ProblemInstance) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for i, _coord in enumerate(problem.coordinates):
        if i == problem.depot_index:
            mapping["depot"] = i
        mapping[f"loc_{i}"] = i
        mapping[f"student_{i}"] = i
    return mapping


def _build_matrix(problem: ProblemInstance) -> Any:
    matrix = problem.dist_matrix
    if matrix is not None:
        return matrix
    n = len(problem.coordinates)
    ewt = problem.edge_weight_type or "EUC_2D"
    built = []
    for i in range(n):
        row = []
        p1 = problem.coordinates[i]
        for j in range(n):
            if i == j:
                row.append(0.0)
            else:
                p2 = problem.coordinates[j]
                row.append(float(tsplib_distance_by_type(ewt, p1, p2)))
        built.append(row)
    return built


def _extract_route_keys(route: Any) -> List[str]:
    locations = getattr(route, "locations", None)
    if isinstance(locations, list) and locations:
        return [str(key) for key in locations]
    steps = list(getattr(route, "route_details", None) or [])
    if not steps:
        return []
    keys = [str(steps[0].location1)]
    keys.extend(str(step.location2) for step in steps)
    return keys


def _keys_to_nodes(
    keys: List[str],
    loc_map: Dict[str, int],
    dimension: int,
    depot: int,
    route_index: int,
    violations: List[Dict[str, Any]],
) -> List[int]:
    nodes: List[int] = []
    for key in keys:
        if isinstance(key, int) and 0 <= key < dimension:
            node = key
        else:
            node = loc_map.get(key)
        if node is None:
            violations.append({
                "type": "missing_arc",
                "severity": "error",
                "details": f"Route {route_index} location key {key!r} not in coordinate map",
                "route_index": route_index,
            })
            nodes.append(-1)
        elif node != depot:
            nodes.append(node)
    return nodes


def _violation_to_dict(violation: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "type": violation.type,
        "severity": violation.severity,
        "details": violation.details,
    }
    if violation.route_index is not None:
        out["route_index"] = violation.route_index
    if violation.node is not None:
        out["node"] = violation.node
    return out


_ROUNDING_TOLERANCE_STEP = 0.005


def _sanitize_certify_error(exc: Exception) -> str:
    """Sanitize a certification failure into a bounded, single-line summary.

    The returned string is independent of the raw exception message: it never
    embeds exception text, markers, or newlines, so internal details cannot
    leak across the production boundary.
    """
    return (
        "certification aborted: internal certificate construction failure "
        f"({type(exc).__name__})"
    )


def _route_duration_tolerance(num_steps: int) -> float:
    return _ROUNDING_TOLERANCE_STEP * (num_steps + 1)


def _fleet_assignment_violations(
    routes: List[List[int]], demands: List[List[int]], vehicles: List[Any]
) -> List[Dict[str, Any]]:
    """Certify the returned routes fit the configured vehicle fleet one-to-one.

    Deterministic Kuhn (augmenting-path) bipartite matching: vehicles are
    considered in ascending (sw_capacity, so_capacity, vehicle_id) order and
    every returned route must be assignable to a distinct vehicle whose SW/SO
    capacities cover the route's total load. When no vehicles are configured
    the global capacity vectors rule (handled by the caller).
    """
    if not vehicles:
        return []
    loads: List[List[int]] = [
        [
            sum(demands[node][0] for node in route),
            sum(demands[node][1] for node in route),
        ]
        for route in routes
    ]
    vehicles_sorted = sorted(
        vehicles, key=lambda v: (v.sw_capacity, v.so_capacity, v.vehicle_id)
    )
    if len(routes) > len(vehicles_sorted):
        return [Violation(
            type="fleet_size_violation",
            severity="error",
            details=(
                f"{len(routes)} returned route(s) but only {len(vehicles_sorted)} "
                f"configured vehicle(s)"
            ),
        )]

    match: List[int] = [-1] * len(vehicles_sorted)

    def _try_assign(route_idx: int, seen: set) -> bool:
        sw_load, so_load = loads[route_idx]
        for vehicle_idx, vehicle in enumerate(vehicles_sorted):
            if vehicle_idx in seen:
                continue
            if sw_load <= vehicle.sw_capacity and so_load <= vehicle.so_capacity:
                seen.add(vehicle_idx)
                if match[vehicle_idx] == -1 or _try_assign(match[vehicle_idx], seen):
                    match[vehicle_idx] = route_idx
                    return True
        return False

    for route_idx in range(len(routes)):
        if not _try_assign(route_idx, set()):
            return [Violation(
                type="fleet_capacity_violation",
                severity="error",
                details=(
                    "No feasible one-to-one SW/SO capacity assignment of the "
                    "returned routes to the configured vehicles"
                ),
            )]
    return []


def certify_optimization_response(request: Any, response: Any) -> dict:
    """Public fail-closed boundary for ``/optimize`` and ``/compare`` responses.

    Solver-independent final certificate. Never raises: any internal failure
    yields an ``is_feasible=False`` certificate carrying only a sanitized
    ``certify_error`` summary. See ``_certify_optimization_response`` for the
    checks performed.
    """
    try:
        return _certify_optimization_response(request, response)
    except Exception as exc:  # noqa: BLE001 - fail-closed certification
        return {
            "is_feasible": False,
            "violation_count": 0,
            "violations": [],
            "certify_error": _sanitize_certify_error(exc),
        }


def _certify_optimization_response(request: Any, response: Any) -> dict:
    """Certify a production ``OptimizationResponse`` against its request.

    Rebuilds the integer-node route representation from the response's own
    ``route_details`` chains (validating chain continuity, depot closure, and
    per-step arc validity), then runs the shared core feasibility checks under
    the request's hard constraints, in addition to response/request
    consistency checks: route ``total_duration_minutes`` against the reported
    step durations and the response total against the route totals (2-decimal
    rounding tolerance), ``sw_count``/``so_count`` against the occurrence
    loads of the visited nodes, ``student_ids`` against the ordered
    occurrence nodes (positional match against each node's student id or
    occurrence key), ``total_vehicles`` against the non-empty route count, and
    the heterogeneous fleet when ``request.vehicles`` is set (deterministic
    one-to-one SW/SO capacity assignment, superseding global caps).

    Matrix provenance: the arc matrix is synthesized from the response's own
    route_details. It attests internal consistency of the reported chain
    (finite, non-negative for any arc, chain-continuous,
    depot-closed) but does NOT claim equivalence with the authoritative source
    travel-time matrix; source/unit/provenance validation is deferred to
    Package E. This bound certifies constraint satisfaction, not optimality.
    """
    occurrence_keys = student_occurrence_keys(request.students)
    node_keys = [request.depot.id] + occurrence_keys
    loc_to_node = {key: idx for idx, key in enumerate(node_keys)}
    dimension = len(node_keys)
    depot = 0

    demands = [[0, 0]] + [
        list(student_capacity_demand(student)) for student in request.students
    ]
    student_by_key = {
        key: student for student, key in zip(request.students, occurrence_keys)
    }
    fleet = list(getattr(request, "vehicles", None) or [])
    capacities = None if fleet else [request.sw_capacity, request.so_capacity]

    routes: List[List[int]] = []
    pre_violations: List[Dict[str, Any]] = []

    for route_index, route in enumerate(getattr(response, "routes", None) or []):
        steps = list(getattr(route, "route_details", None) or [])
        if not steps:
            pre_violations.append({
                "type": "depot_closure", "severity": "error",
                "details": f"Route {route_index} has no route details",
                "route_index": route_index,
            })
            routes.append([])
            continue

        for step, next_step in zip(steps, steps[1:]):
            if step.location2 != next_step.location1:
                pre_violations.append({
                    "type": "route_continuity", "severity": "error",
                    "details": f"Route {route_index} broken chain: {step.location2!r} != {next_step.location1!r}",
                    "route_index": route_index,
                })

        if steps[0].location1 != request.depot.id:
            pre_violations.append({
                "type": "depot_closure", "severity": "error",
                "details": f"Route {route_index} does not start at depot {request.depot.id!r}",
                "route_index": route_index,
            })

        if steps[-1].location2 != request.depot.id:
            pre_violations.append({
                "type": "depot_closure", "severity": "error",
                "details": f"Route {route_index} does not end at depot {request.depot.id!r}",
                "route_index": route_index,
            })

        keys = [steps[0].location1] + [step.location2 for step in steps]
        nodes: List[int] = []
        for key in keys:
            node = loc_to_node.get(str(key)) if not isinstance(key, int) else (key if 0 <= key < dimension else None)
            if node is None:
                pre_violations.append({
                    "type": "missing_arc", "severity": "error",
                    "details": f"Route {route_index} location key {key!r} not in request",
                    "route_index": route_index,
                })
                continue
            if node != depot:
                nodes.append(node)
        routes.append(nodes)

        reported_total = float(getattr(route, "total_duration_minutes", 0.0) or 0.0)
        steps_sum = sum(float(step.duration) for step in steps)
        if not math.isfinite(reported_total) or not math.isfinite(steps_sum):
            pre_violations.append({
                "type": "non_finite_duration", "severity": "error",
                "details": (
                    f"Route {route_index} has a non-finite duration total: "
                    f"reported {reported_total}, step sum {steps_sum}"
                ),
                "route_index": route_index,
            })
        elif abs(reported_total - steps_sum) > _route_duration_tolerance(len(steps)):
            pre_violations.append({
                "type": "route_duration_mismatch", "severity": "error",
                "details": (
                    f"Route {route_index} total_duration_minutes {reported_total} "
                    f"differs from step durations sum {steps_sum}"
                ),
                "route_index": route_index,
            })

        sw_load = sum(demands[node][0] for node in nodes)
        so_load = sum(demands[node][1] for node in nodes)
        reported_sw = int(getattr(route, "sw_count", 0) or 0)
        reported_so = int(getattr(route, "so_count", 0) or 0)
        if reported_sw != sw_load or reported_so != so_load:
            pre_violations.append({
                "type": "load_count_mismatch", "severity": "error",
                "details": (
                    f"Route {route_index} sw_count/so_count {reported_sw}/{reported_so} "
                    f"differs from occurrence loads {sw_load}/{so_load}"
                ),
                "route_index": route_index,
            })

        expected_tokens: List[Any] = []
        for node in nodes:
            key = occurrence_keys[node - 1]
            student = student_by_key[key]
            expected_tokens.append((student.id, key))
        reported_ids = list(getattr(route, "student_ids", None) or [])
        if len(reported_ids) != len(nodes):
            pre_violations.append({
                "type": "student_id_mismatch", "severity": "error",
                "details": (
                    f"Route {route_index} student_ids has {len(reported_ids)} entries "
                    f"but the route visits {len(nodes)} student(s)"
                ),
                "route_index": route_index,
            })
        else:
            for position, (reported, (student_id, key)) in enumerate(zip(reported_ids, expected_tokens)):
                if reported != student_id and reported != key:
                    pre_violations.append({
                        "type": "student_id_mismatch", "severity": "error",
                        "details": (
                            f"Route {route_index} student_ids[{position}] {reported!r} "
                            f"does not match visited node {student_id!r} (key {key!r})"
                        ),
                        "route_index": route_index,
                    })

    matrix = [[0.0] * dimension for _ in range(dimension)]
    for route_index, route in enumerate(getattr(response, "routes", None) or []):
        for step in getattr(route, "route_details", None) or []:
            src = loc_to_node.get(str(step.location1))
            dst = loc_to_node.get(str(step.location2))
            if src is None or dst is None:
                continue
            duration = float(step.duration)
            valid = math.isfinite(duration) and duration >= 0.0
            if not valid:
                pre_violations.append({
                    "type": "missing_arc", "severity": "error",
                    "details": f"Route {route_index} arc {step.location1!r}->{step.location2!r} has invalid duration {step.duration!r}",
                    "route_index": route_index,
                })
                continue
            matrix[src][dst] = duration

    routed_totals = [
        float(getattr(route, "total_duration_minutes", 0.0) or 0.0)
        for route in (getattr(response, "routes", None) or [])
    ]
    reported_total = float(getattr(response, "total_duration_minutes", 0.0) or 0.0)
    routed_sum = sum(routed_totals)
    if not math.isfinite(reported_total) or not math.isfinite(routed_sum):
        pre_violations.append({
            "type": "non_finite_duration", "severity": "error",
            "details": (
                f"Response has a non-finite duration total: reported "
                f"{reported_total}, route totals sum {routed_sum}"
            ),
        })
    elif abs(reported_total - routed_sum) > _ROUNDING_TOLERANCE_STEP * (len(routed_totals) + 1):
        pre_violations.append({
            "type": "response_duration_mismatch", "severity": "error",
            "details": (
                f"Response total_duration_minutes {reported_total} differs from "
                f"route totals sum {routed_sum}"
            ),
        })

    nonempty_routes = [r for r in routes if r]
    reported_total_vehicles = int(getattr(response, "total_vehicles", 0) or 0)
    if reported_total_vehicles != len(nonempty_routes):
        pre_violations.append({
            "type": "vehicle_count_mismatch", "severity": "error",
            "details": (
                f"Response total_vehicles {reported_total_vehicles} differs from "
                f"{len(nonempty_routes)} non-empty route(s)"
            ),
        })

    time_windows = None
    target_minutes = None
    if getattr(request, "use_time_windows", False):
        tw_by_key = request.get_time_windows()
        time_windows = [(0, 1440)]
        for key in occurrence_keys:
            window = tw_by_key.get(key)
            time_windows.append((window.earliest, window.latest) if window else (0, 1440))
        if request.target_time:
            try:
                hours, minutes = request.target_time.split(":")
                target_minutes = int(hours) * 60 + int(minutes)
            except (ValueError, AttributeError):
                target_minutes = None

    violations = []
    violations.extend(check_depot_closure(routes, depot, dimension))
    violations.extend(check_occurrence_coverage(routes, dimension, depot, ["depot"] + occurrence_keys))
    violations.extend(_fleet_assignment_violations(routes, demands, fleet))
    if capacities is not None:
        violations.extend(check_capacity_vectors(routes, demands, capacities))
    violations.extend(check_duration(
        routes, matrix, depot, float(request.max_travel_time), None
    ))
    if time_windows is not None:
        violations.extend(check_time_windows(
            routes, matrix, depot, time_windows, None,
            getattr(request.direction, "value", request.direction),
            target_minutes, getattr(request, "offset_minutes", 15),
        ))
    violations.extend(check_hard_violation_rejection(
        getattr(response, "success", None), violations
    ))

    all_violations = pre_violations + [_violation_to_dict(v) for v in violations]
    return {
        "is_feasible": not all_violations,
        "violation_count": len(all_violations),
        "violations": all_violations,
    }


def certify_benchmark_response(problem: ProblemInstance, response: Any) -> dict:
    loc_map = _build_location_map(problem)
    dimension = problem.dimension
    depot = problem.depot_index
    pre_violations: List[Dict[str, Any]] = []
    int_routes: List[List[int]] = []

    for route in getattr(response, "routes", None) or []:
        route_index = len(int_routes)
        keys = _extract_route_keys(route)
        int_routes.append(_keys_to_nodes(keys, loc_map, dimension, depot, route_index, pre_violations))

    problem_copy = copy.copy(problem)
    problem_copy.dist_matrix = _build_matrix(problem)

    result = RoutingResult(
        algorithm=getattr(response, "algorithm_used", "unknown"),
        problem_type=problem.problem_type,
        objective_cost=getattr(response, "total_duration_minutes", 0.0) or 0.0,
        routes=int_routes,
        capacity_violations=int(getattr(response, "capacity_violations", 0) or 0),
        tw_violations=int(getattr(response, "total_time_window_violations", 0) or 0),
    )

    try:
        certificate = certify_problem_instance(
            result, problem_copy, success=getattr(response, "success", None)
        )
    except Exception as exc:
        return {
            "is_feasible": False,
            "violation_count": 0,
            "violations": [],
            "certify_error": str(exc),
        }

    violations = pre_violations + [_violation_to_dict(v) for v in certificate.violations]
    return {
        "is_feasible": certificate.is_feasible and not pre_violations,
        "violation_count": len(violations),
        "violations": violations,
    }


__all__ = ["certify_optimization_response", "certify_benchmark_response"]