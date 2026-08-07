"""Shared lexicographic objective for split engines: feasibility > vehicles > travel cost."""

from __future__ import annotations

import math
from typing import Any, Dict, Tuple

FeasibleVehiclesCost = Tuple[int, int, float]

FEASIBLE = 0
INFEASIBLE = 1


def objective_key(result: Any) -> FeasibleVehiclesCost:
    """Build (feasible, num_vehicles, travel_cost) key from a decode result.

    Accepts a dict-like with ``num_vehicles``/``total_cost`` or an object with
    those attributes. Infeasible results (no routes, inf cost) sort worst.
    """
    if isinstance(result, dict):
        num_vehicles = result.get("num_vehicles", 0)
        total_cost = result.get("total_cost", float("inf"))
    else:
        num_vehicles = getattr(result, "num_vehicles", 0)
        total_cost = getattr(result, "total_cost", float("inf"))
    if total_cost is None:
        total_cost = float("inf")
    if num_vehicles is None:
        num_vehicles = 0
    try:
        num_vehicles_int = int(num_vehicles)
        total_cost_float = float(total_cost)
    except (TypeError, ValueError):
        num_vehicles_int = 999
        total_cost_float = float("inf")
    feasible = FEASIBLE if (num_vehicles_int > 0 and math.isfinite(total_cost_float)) else INFEASIBLE
    return (feasible, num_vehicles_int, total_cost_float)


def is_better(a_key: FeasibleVehiclesCost, b_key: FeasibleVehiclesCost) -> bool:
    """Strict lexicographic comparison: lower key is better."""
    return a_key < b_key


def fitness_from_key(key: FeasibleVehiclesCost, feasible_weight: float = 1000.0) -> float:
    """Monotone scalar preserving lexicographic order for GA-style sampling.

    Feasibility dominates via ``feasible_weight``; vehicle count dominates
    travel cost because the cost term is bounded to ``[0, 1)`` while each
    extra vehicle adds exactly ``1.0`` to the denominator.
    """
    feasible, vehicles, cost = key
    if not math.isfinite(cost) or vehicles <= 0:
        return 0.0
    bounded_cost = cost / (1.0 + cost)
    return 1.0 / (1.0 + feasible_weight * feasible + vehicles + bounded_cost)


def key_from_fields(num_vehicles: Any, total_cost: Any) -> FeasibleVehiclesCost:
    """Build a key directly from decoder fields."""
    return objective_key({"num_vehicles": num_vehicles, "total_cost": total_cost})


def report_key_from_routes(routes: Any, distance_matrix: Any, depot: Any) -> FeasibleVehiclesCost:
    """Build the ranking key from a reported route set.

    ``routes`` is a sequence of location sequences (strings); each route's
    travel cost is the sum of consecutive arcs plus the return arc to the
    depot, matching ``string_split_decoder`` accounting. Infeasible routes
    (not a list, empty, or no arcs) sort worst.
    """
    if not routes:
        return (INFEASIBLE, 0, float("inf"))
    try:
        num_vehicles = len(routes)
    except TypeError:
        return (INFEASIBLE, 0, float("inf"))
    total_cost = 0.0
    for route in routes:
        if len(route) == 0:
            return (INFEASIBLE, num_vehicles, float("inf"))
        prev = depot
        arc_cost = 0.0
        for location in route:
            cost = float(_arc_cost(distance_matrix, prev, location))
            if not math.isfinite(cost) or cost < 0:
                return (INFEASIBLE, num_vehicles, float("inf"))
            arc_cost += cost
            prev = location
        cost = float(_arc_cost(distance_matrix, prev, depot))
        if not math.isfinite(cost) or cost < 0:
            return (INFEASIBLE, num_vehicles, float("inf"))
        total_cost += arc_cost + cost
    return objective_key({"num_vehicles": num_vehicles, "total_cost": total_cost})


def _arc_cost(distance_matrix: Any, start: Any, end: Any) -> float:
    """Look up one directed arc, treating missing arcs as infinite."""
    try:
        row = distance_matrix[start]
    except (KeyError, TypeError):
        return float("inf")
    try:
        return float(row[end])
    except (KeyError, TypeError):
        return float("inf")
