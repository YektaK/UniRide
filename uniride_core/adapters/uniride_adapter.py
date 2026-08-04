"""Adapters for normalizing UniRide request-like objects into core problems.

The functions here use duck typing so ``uniride_core`` never imports
application-layer schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.adapters.demand_builder import student_occurrence_keys
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


def _get(value: Any, key: str, default: Any = None) -> Any:
    data = _as_dict(value)
    if key in data:
        return data[key]
    return getattr(value, key, default)


def _minutes(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and ":" in value:
        hour, minute = value.split(":", 1)
        try:
            return int(hour) * 60 + int(minute)
        except ValueError:
            return None
    return None


def _student_demand(student: Any) -> List[int]:
    disability = str(_get(student, "disability_type", "So"))
    return [1, 0] if disability.lower() == "sw" else [0, 1]


def _student_location(student: Any) -> str:
    return str(_get(student, "location_code") or _get(student, "id"))


def _student_coordinates(student: Any) -> Tuple[float, float]:
    coords = _get(student, "coordinates") or {}
    return (float(coords.get("lat", 0.0)), float(coords.get("lng", 0.0)))


def _depot_coordinates(depot: Any) -> Tuple[float, float]:
    return (float(_get(depot, "lat", 0.0)), float(_get(depot, "lng", 0.0)))


def _extract_time_windows(request: Any, labels: Sequence[str]) -> Optional[List[Tuple[int, int]]]:
    if not hasattr(request, "get_time_windows"):
        return None
    raw_windows = request.get_time_windows()
    if not raw_windows:
        return None

    windows: List[Tuple[int, int]] = []
    for label in labels:
        window = raw_windows.get(label)
        if window is None:
            windows.append((0, 24 * 60))
            continue
        windows.append((int(_get(window, "earliest", 0)), int(_get(window, "latest", 24 * 60))))
    return windows


def uniride_request_to_problem(
    request: Any,
    matrix: Optional[Sequence[Sequence[float]]] = None,
    name: str = "uniride-request",
) -> RoutingProblem:
    """Convert a UniRide request-like object to a core ``RoutingProblem``.

    ``request`` can be an optimizer API model, a dict-like object, or a simple
    test double with ``students`` and ``depot`` attributes.
    """
    data = _as_dict(request)
    students = list(_get(request, "students", []) or [])
    depot = _get(request, "depot")
    occurrence_ids = student_occurrence_keys(students)
    labels = [str(_get(depot, "id", "depot"))] + occurrence_ids
    coords = [_depot_coordinates(depot)] + [_student_coordinates(student) for student in students]

    if matrix is None:
        explicit_matrix = _get(request, "time_matrix") or _get(request, "distance_matrix")
    else:
        explicit_matrix = matrix

    if explicit_matrix is not None:
        matrix_values = MatrixBuilder.from_travel_times(explicit_matrix)
        matrix_kind = "travel_time"
    else:
        matrix_values = MatrixBuilder.from_coordinates(coords, "EUC_2D")
        matrix_kind = "distance"

    demands = [[0, 0]] + [_student_demand(student) for student in students]
    capacities = [int(_get(request, "sw_capacity", 4)), int(_get(request, "so_capacity", 5))]
    time_windows = _extract_time_windows(request, labels)

    return RoutingProblem(
        name=name,
        problem_type="uniride_cvrptw" if time_windows else "uniride_cvrp",
        matrix=CostMatrix(
            values=matrix_values,
            kind=matrix_kind,
            is_asymmetric=bool(_get(request, "is_asymmetric", False)),
            labels=labels,
            occurrence_ids=occurrence_ids,
        ),
        constraints=ConstraintProfile(
            demands=demands,
            capacities=capacities,
            time_windows=time_windows,
            service_times=[0] * len(labels),
            depot_index=0,
            max_route_duration=float(_get(request, "max_travel_time", 120)),
            direction=str(_get(request, "direction", "pickup")),
            target_time=_minutes(_get(request, "target_time")),
            offset_minutes=int(_get(request, "offset_minutes", 15)),
        ),
        coordinates=coords,
        source="uniride",
        metadata={"students": len(students)},
    )


__all__ = ["uniride_request_to_problem"]
