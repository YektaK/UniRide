"""Core helpers for production SOTA TSP strategy wrappers."""

from __future__ import annotations

from typing import Callable, List, Sequence, Type


DistanceLookup = Callable[[str, str], float]
DurationLookup = Callable[[str, str], float]


def build_solver_matrix(student_ids: Sequence[str], distance_lookup: DistanceLookup) -> List[List[float]]:
    """Build the student-only matrix consumed by SOTA TSP solvers."""
    matrix: List[List[float]] = []
    for origin in student_ids:
        row: List[float] = []
        for destination in student_ids:
            if origin == destination:
                row.append(0.0)
            else:
                row.append(float(max(1, int(distance_lookup(origin, destination) * 1000))))
        matrix.append(row)
    return matrix


def greedy_student_order(
    student_ids: Sequence[str],
    depot_id: str,
    duration_lookup: DurationLookup,
) -> List[str]:
    """Fallback nearest-neighbor order for production wrappers."""
    unassigned = list(student_ids)
    order: List[str] = []
    current = depot_id

    while unassigned:
        best = min(unassigned, key=lambda student_id: duration_lookup(current, student_id))
        order.append(best)
        unassigned.remove(best)
        current = best

    return order


def solve_student_order_with_sota_tsp(
    student_ids: Sequence[str],
    depot_id: str,
    distance_lookup: DistanceLookup,
    duration_lookup: DurationLookup,
    solver_cls: Type,
    config,
) -> List[str]:
    """Run a core SOTA TSP solver and return student ids in visit order.

    The fallback is intentionally here, not in the app layer, so wrappers do
    not own the algorithm-critical behavior.
    """
    if not student_ids:
        return []

    try:
        solver = solver_cls(config)
        matrix = build_solver_matrix(student_ids, distance_lookup)
        result = solver.solve_with_matrix(matrix)
        return [student_ids[idx] for idx in result.tour]
    except Exception:
        return greedy_student_order(student_ids, depot_id, duration_lookup)


__all__ = [
    "build_solver_matrix",
    "greedy_student_order",
    "solve_student_order_with_sota_tsp",
]
