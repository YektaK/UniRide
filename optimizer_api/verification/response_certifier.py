"""Certify a strategy response against a ProblemInstance into a JSON-safe dict."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from uniride_core.algorithms.distance import tsplib_distance_by_type
from uniride_core.algorithms.feasibility_certificate import certify_problem_instance
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


__all__ = ["certify_benchmark_response"]