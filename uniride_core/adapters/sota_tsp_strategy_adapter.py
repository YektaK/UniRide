"""Core helpers for production SOTA TSP strategy wrappers.

Objective contract (audit M26 / QW11): the matrix handed to the SOTA solver is
built from the *same* depot-anchored, directed travel-time the response reports
and the certifier checks, scaled by ``SOTA_DURATION_SCALE`` (the solver
objective is 1000x the arc durations, unrounded). The response publishes each
step as ``round(x, 2)`` and sums those steps, so with more precise durations
the reported total can differ from the exact cycle cost by up to
``(n + 1) * 0.005`` minutes. The reported route is the closed cycle
``depot -> s1 -> ... -> sk -> depot``; the solver therefore receives an
``(n + 1) x (n + 1)`` matrix whose index 0 is the depot, and the cycle it
returns is rotated so that it starts at the depot. The response recomputes
its cost from the real durations of the chosen order, never from the solver's
reported length.

Failure contract: a solver failure never silently turns into a different
algorithm. The caller receives the greedy order *together with* a short reason
code, and is expected to surface it (``algorithm_used="greedy_fallback"``).
The exception text is logged server-side only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Type

logger = logging.getLogger(__name__)

DistanceLookup = Callable[[str, str], float]
DurationLookup = Callable[[str, str], float]

#: ``algorithm_used`` value of a response whose SOTA solver failed.
GREEDY_FALLBACK_ALGORITHM = "greedy_fallback"
FALLBACK_REASON_SOLVER_ERROR = "solver_error"
FALLBACK_REASON_INVALID_TOUR = "invalid_solver_tour"

#: Minutes -> solver units. Kept at 1000 (the historical solver magnitude, so
#: absolute LS epsilons keep their meaning). Values are scaled, never rounded:
#: the solver objective is exactly ``SOTA_DURATION_SCALE`` times the reported
#: duration, so no tie can be created or broken by quantisation.
SOTA_DURATION_SCALE = 1000.0


@dataclass(frozen=True)
class SotaOrderOutcome:
    """Student visit order plus, when the SOTA solver did not run, why."""

    order: List[str]
    fallback_reason: Optional[str] = None
    #: Why the solver stopped ("iteration_limit" or "wall_clock_deadline", MT6-03/H11);
    #: None when no solver ran (empty request or fallback).
    termination_reason: Optional[str] = None
    #: False only when an optional wall-clock deadline ended the run early.
    reproducible: bool = True


def build_solver_matrix(
    student_ids: Sequence[str],
    depot_id: str,
    duration_lookup: DurationLookup,
) -> List[List[float]]:
    """Depot-anchored directed duration matrix consumed by SOTA TSP solvers.

    Index 0 is the depot, indices 1..n are ``student_ids`` in order. Entry
    ``[i][j]`` is ``duration_lookup(node_i, node_j) * SOTA_DURATION_SCALE``
    (asymmetry preserved); the diagonal is 0.
    """
    nodes = [depot_id, *student_ids]
    matrix: List[List[float]] = []
    for origin in nodes:
        row: List[float] = []
        for destination in nodes:
            if origin == destination:
                row.append(0.0)
            else:
                row.append(float(duration_lookup(origin, destination)) * SOTA_DURATION_SCALE)
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


def _order_from_cycle(tour: Sequence[int], student_ids: Sequence[str]) -> Optional[List[str]]:
    """Rotate a solver cycle to start at the depot (index 0) and map to ids."""
    try:
        cycle = [int(index) for index in tour]
    except (TypeError, ValueError):
        return None
    if sorted(cycle) != list(range(len(student_ids) + 1)):
        return None
    start = cycle.index(0)
    rotated = cycle[start + 1:] + cycle[:start]
    return [student_ids[index - 1] for index in rotated]


def solve_student_order_with_sota_tsp(
    student_ids: Sequence[str],
    depot_id: str,
    duration_lookup: DurationLookup,
    solver_cls: Type,
    config,
) -> SotaOrderOutcome:
    """Run a core SOTA TSP solver and return student ids in visit order.

    On solver failure the greedy order is returned with a ``fallback_reason``
    code so the response layer can label it truthfully. The fallback lives
    here, not in the app layer, so wrappers do not own the algorithm-critical
    behavior.
    """
    if not student_ids:
        return SotaOrderOutcome(order=[])

    # Built outside the try: a travel-time (matrix) error must fail the request
    # closed, not be relabelled as a solver error and served as a greedy order.
    matrix = build_solver_matrix(student_ids, depot_id, duration_lookup)

    try:
        solver = solver_cls(config)
        result = solver.solve_with_matrix(matrix)
        order = _order_from_cycle(result.tour, student_ids)
    except Exception:
        logger.exception(
            "SOTA TSP solver %s failed; serving greedy_fallback order",
            getattr(solver_cls, "__name__", solver_cls),
        )
        return SotaOrderOutcome(
            order=greedy_student_order(student_ids, depot_id, duration_lookup),
            fallback_reason=FALLBACK_REASON_SOLVER_ERROR,
        )

    if order is None:
        logger.error(
            "SOTA TSP solver %s returned an invalid tour; serving greedy_fallback order",
            getattr(solver_cls, "__name__", solver_cls),
        )
        return SotaOrderOutcome(
            order=greedy_student_order(student_ids, depot_id, duration_lookup),
            fallback_reason=FALLBACK_REASON_INVALID_TOUR,
        )
    stats = getattr(result, "extra_stats", None) or {}
    reproducible = stats.get("reproducible", True) is not False
    if not reproducible:
        logger.warning(
            "SOTA TSP solver %s stopped at its wall-clock deadline (%s s); result is not reproducible",
            getattr(solver_cls, "__name__", solver_cls),
            stats.get("deadline_seconds"),
        )
    return SotaOrderOutcome(
        order=order,
        termination_reason=stats.get("termination_reason"),
        reproducible=reproducible,
    )


__all__ = [
    "FALLBACK_REASON_INVALID_TOUR",
    "FALLBACK_REASON_SOLVER_ERROR",
    "GREEDY_FALLBACK_ALGORITHM",
    "SOTA_DURATION_SCALE",
    "SotaOrderOutcome",
    "build_solver_matrix",
    "greedy_student_order",
    "solve_student_order_with_sota_tsp",
]
