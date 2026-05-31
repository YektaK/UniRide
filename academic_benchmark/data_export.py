#!/usr/bin/env python3
"""Export anonymized UniRide data into the academic benchmark DB.

The pure builder in this module accepts UniRide-style request data and returns a
core RoutingProblem. Optional CLI paths can read that payload from JSON or fetch
best-effort data from Supabase when credentials are available.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np

from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem

try:
    from academic_benchmark.tsplib_manager import DB_PATH, store_routing_problem
except ImportError:  # pragma: no cover - direct script execution fallback
    from tsplib_manager import DB_PATH, store_routing_problem


DEFAULT_DEPOT_LABEL = "depot"


def build_uniride_export_problem(
    payload: Mapping[str, Any],
    *,
    name: str | None = None,
    slack_window_minutes: int | None = None,
    service_time_minutes: int | None = None,
    include_coordinates: bool = False,
) -> RoutingProblem:
    """Build an anonymized CVRPTW RoutingProblem from UniRide-style data."""

    students = list(payload.get("students") or [])
    depot = dict(payload.get("depot") or {})
    if not depot:
        raise ValueError("payload.depot is required")
    if not students:
        raise ValueError("payload.students must contain at least one student")

    original_labels = _original_labels(depot, students)
    anonymous_labels = [DEFAULT_DEPOT_LABEL] + [
        f"student_{idx:03d}" for idx in range(1, len(students) + 1)
    ]
    matrix = _matrix_from_payload(payload.get("time_matrix"), original_labels)

    direction = str(payload.get("direction") or "pickup").lower()
    slack = int(slack_window_minutes if slack_window_minutes is not None else payload.get("slack_window_minutes", 30))
    service_time = int(service_time_minutes if service_time_minutes is not None else payload.get("service_time_minutes", 0))

    demands = [[0, 0]]
    for student in students:
        disability = str(student.get("disability_type") or student.get("disabilityType") or "So")
        demands.append([1, 0] if disability.lower() == "sw" else [0, 1])

    constraints = ConstraintProfile(
        demands=demands,
        capacities=[
            int(payload.get("sw_capacity", payload.get("wheelchair_capacity", 4))),
            int(payload.get("so_capacity", payload.get("seat_capacity", 5))),
        ],
        time_windows=_time_windows(students, direction, slack),
        service_times=[0] + [service_time] * len(students),
        depot_index=0,
        max_route_duration=payload.get("max_travel_time", payload.get("max_route_duration")),
        direction=direction,
        offset_minutes=slack,
    )

    coordinates = _coordinates_from_payload(depot, students) if include_coordinates else None
    problem_name = name or str(payload.get("name") or f"uniride_export_{datetime.now():%Y%m%d_%H%M%S}")
    return RoutingProblem(
        name=problem_name,
        problem_type="cvrptw",
        matrix=CostMatrix(
            matrix,
            kind="travel_time",
            is_asymmetric=_is_asymmetric(matrix),
            labels=anonymous_labels,
        ),
        constraints=constraints,
        coordinates=coordinates,
        category=_category(len(anonymous_labels)),
        source="uniride_export",
        metadata={
            "anonymized": True,
            "exported_at": datetime.now().isoformat(),
            "matrix_kind": "travel_time",
            "vehicles": _vehicle_count(payload.get("num_vehicles") or payload.get("vehicles")),
            "student_count": len(students),
            "sw_count": sum(1 for demand in demands if demand == [1, 0]),
            "so_count": sum(1 for demand in demands if demand == [0, 1]),
        },
    )


def store_uniride_export(problem: RoutingProblem, *, db_path: str = DB_PATH) -> RoutingProblem:
    """Store an exported UniRide RoutingProblem in the academic SQLite DB."""

    store_routing_problem(problem, db_path=db_path, source_file="uniride_export")
    return problem


def export_json_payload(
    input_path: str | os.PathLike[str],
    *,
    db_path: str = DB_PATH,
    name: str | None = None,
    slack_window_minutes: int | None = None,
    include_coordinates: bool = False,
) -> RoutingProblem:
    """Load a UniRide JSON payload, anonymize it, and store it."""

    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    problem = build_uniride_export_problem(
        payload,
        name=name,
        slack_window_minutes=slack_window_minutes,
        include_coordinates=include_coordinates,
    )
    return store_uniride_export(problem, db_path=db_path)


def fetch_supabase_payload(
    *,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
    students_table: str = "users",
    matrix_table: str = "time_matrix",
    student_limit: int | None = None,
    direction: str = "pickup",
    name: str | None = None,
) -> Dict[str, Any]:
    """Fetch a best-effort UniRide payload from Supabase.

    Expected tables are intentionally conservative:
    - `users` rows with role/student fields and location_code/coordinates.
    - `time_matrix` rows with origin_code, destination_code, duration_minutes.
    """

    url = supabase_url or os.environ.get("SUPABASE_URL")
    key = supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    from supabase import create_client

    client = create_client(url, key)
    query = client.table(students_table).select("*")
    try:
        query = query.eq("role", "student")
    except Exception:
        pass
    if student_limit:
        query = query.limit(int(student_limit))
    student_rows = query.execute().data or []
    students = [_normalize_student(row) for row in student_rows if _student_location_code(row)]

    matrix_rows = client.table(matrix_table).select(
        "origin_code, destination_code, duration_minutes"
    ).execute().data or []
    time_matrix = _matrix_dict_from_rows(matrix_rows)
    depot_code = _infer_depot_code(time_matrix) or "D.Kampus"
    return {
        "name": name or f"uniride_supabase_{datetime.now():%Y%m%d_%H%M%S}",
        "depot": {"id": depot_code},
        "students": students,
        "time_matrix": time_matrix,
        "direction": direction,
    }


def export_supabase(
    *,
    db_path: str = DB_PATH,
    name: str | None = None,
    student_limit: int | None = None,
    direction: str = "pickup",
    slack_window_minutes: int | None = None,
) -> RoutingProblem:
    """Fetch from Supabase, anonymize, and store in the academic DB."""

    payload = fetch_supabase_payload(
        name=name,
        student_limit=student_limit,
        direction=direction,
    )
    problem = build_uniride_export_problem(
        payload,
        slack_window_minutes=slack_window_minutes,
    )
    return store_uniride_export(problem, db_path=db_path)


def _original_labels(depot: Mapping[str, Any], students: Sequence[Mapping[str, Any]]) -> List[str]:
    return [_node_code(depot, fallback=DEFAULT_DEPOT_LABEL)] + [
        _node_code(student, fallback=f"student_{idx:03d}")
        for idx, student in enumerate(students, start=1)
    ]


def _node_code(node: Mapping[str, Any], *, fallback: str) -> str:
    return str(
        node.get("location_code")
        or node.get("locationCode")
        or node.get("id")
        or fallback
    )


def _matrix_from_payload(matrix_data: Any, labels: Sequence[str]) -> np.ndarray:
    if matrix_data is None:
        raise ValueError("payload.time_matrix is required")
    if isinstance(matrix_data, Mapping):
        values = [
            [
                float((matrix_data.get(origin) or {}).get(destination, 0.0))
                for destination in labels
            ]
            for origin in labels
        ]
    else:
        values = matrix_data
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("time_matrix must be square")
    if matrix.shape[0] != len(labels):
        raise ValueError("time_matrix size must match depot + students")
    return matrix


def _time_windows(
    students: Sequence[Mapping[str, Any]],
    direction: str,
    slack_window_minutes: int,
) -> List[tuple[int, int]]:
    windows: List[tuple[int, int]] = [(0, 1440)]
    for student in students:
        time_text = _student_time(student, direction)
        if not time_text:
            windows.append((0, 1440))
            continue
        minutes = _parse_hhmm(time_text)
        if direction == "dropoff":
            windows.append((minutes, min(1440, minutes + slack_window_minutes)))
        else:
            windows.append((max(0, minutes - slack_window_minutes), minutes))
    return windows


def _student_time(student: Mapping[str, Any], direction: str) -> str | None:
    if direction == "dropoff":
        return student.get("dropoff_time") or student.get("dropoffTime") or student.get("pickup_time")
    return student.get("pickup_time") or student.get("pickupTime") or student.get("dropoff_time")


def _parse_hhmm(value: str) -> int:
    hour, minute = str(value).strip().split(":", 1)
    return int(hour) * 60 + int(minute)


def _coordinates_from_payload(
    depot: Mapping[str, Any],
    students: Sequence[Mapping[str, Any]],
) -> List[tuple[float, float]]:
    return [_node_coordinates(depot)] + [_node_coordinates(student) for student in students]


def _node_coordinates(node: Mapping[str, Any]) -> tuple[float, float]:
    coords = node.get("coordinates") if isinstance(node.get("coordinates"), Mapping) else node
    return (float(coords.get("lat", 0.0)), float(coords.get("lng", 0.0)))


def _is_asymmetric(matrix: np.ndarray) -> bool:
    return not np.allclose(matrix, matrix.T)


def _category(dimension: int) -> str:
    if dimension <= 100:
        return "small"
    if dimension <= 500:
        return "medium"
    return "large"


def _vehicle_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return len(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _student_location_code(row: Mapping[str, Any]) -> str | None:
    value = row.get("location_code") or row.get("locationCode")
    return str(value) if value else None


def _normalize_student(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id") or row.get("student_id") or _student_location_code(row),
        "location_code": _student_location_code(row),
        "disability_type": row.get("disability_type") or row.get("disabilityType") or "So",
        "pickup_time": row.get("pickup_time") or row.get("pickupTime"),
        "dropoff_time": row.get("dropoff_time") or row.get("dropoffTime"),
        "coordinates": row.get("coordinates"),
    }


def _matrix_dict_from_rows(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    matrix: Dict[str, Dict[str, float]] = {}
    for row in rows:
        origin = str(row.get("origin_code"))
        destination = str(row.get("destination_code"))
        if not origin or not destination:
            continue
        matrix.setdefault(origin, {})[destination] = float(row.get("duration_minutes", 0.0))
    return matrix


def _infer_depot_code(matrix: Mapping[str, Mapping[str, float]]) -> str | None:
    for label in matrix:
        lower = label.lower()
        if "kampus" in lower or "campus" in lower or lower.startswith("d."):
            return label
    return next(iter(matrix), None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export anonymized UniRide data to academic SQLite DB")
    parser.add_argument("--input-json", help="UniRide JSON payload to export")
    parser.add_argument("--from-supabase", action="store_true", help="Fetch users/time_matrix from Supabase")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--name")
    parser.add_argument("--direction", default="pickup", choices=["pickup", "dropoff"])
    parser.add_argument("--student-limit", type=int)
    parser.add_argument("--slack-window-minutes", type=int)
    parser.add_argument("--include-coordinates", action="store_true")
    args = parser.parse_args()

    if args.from_supabase:
        problem = export_supabase(
            db_path=args.db_path,
            name=args.name,
            student_limit=args.student_limit,
            direction=args.direction,
            slack_window_minutes=args.slack_window_minutes,
        )
    elif args.input_json:
        problem = export_json_payload(
            args.input_json,
            db_path=args.db_path,
            name=args.name,
            slack_window_minutes=args.slack_window_minutes,
            include_coordinates=args.include_coordinates,
        )
    else:
        parser.error("Provide --input-json or --from-supabase")

    print(f"[OK] Exported {problem.name} ({problem.dimension} nodes) to {args.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "build_uniride_export_problem",
    "store_uniride_export",
    "export_json_payload",
    "fetch_supabase_payload",
    "export_supabase",
]
