"""CVRPLIB/Solomon facade over the unified academic SQLite store.

This module intentionally does not own a separate schema.  It provides
CVRP/CVRPTW-friendly names while delegating storage and loading to
``academic_benchmark.tsplib_manager``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from academic_benchmark.tsplib_manager import (
    DB_PATH,
    get_all_problems,
    load_routing_problem,
    problem_row_to_instance,
    store_academic_text,
)


def import_cvrplib_text(
    text: str,
    *,
    name: str = "cvrplib",
    db_path: str = DB_PATH,
    source_file: Optional[str] = None,
):
    """Parse and store CVRPLIB text as a core ``RoutingProblem``."""
    return store_academic_text(text, "cvrplib", name=name, db_path=db_path, source_file=source_file)


def import_solomon_text(
    text: str,
    *,
    name: str = "solomon",
    db_path: str = DB_PATH,
    source_file: Optional[str] = None,
):
    """Parse and store Solomon CVRPTW text as a core ``RoutingProblem``."""
    return store_academic_text(text, "solomon", name=name, db_path=db_path, source_file=source_file)


def import_cvrplib_file(path: str | Path, *, db_path: str = DB_PATH):
    """Read and store a CVRPLIB file using the unified academic DB."""
    file_path = Path(path)
    return import_cvrplib_text(
        file_path.read_text(encoding="utf-8"),
        name=file_path.stem,
        db_path=db_path,
        source_file=str(file_path),
    )


def import_solomon_file(path: str | Path, *, db_path: str = DB_PATH):
    """Read and store a Solomon CVRPTW file using the unified academic DB."""
    file_path = Path(path)
    return import_solomon_text(
        file_path.read_text(encoding="utf-8"),
        name=file_path.stem,
        db_path=db_path,
        source_file=str(file_path),
    )


def load_cvrp_problem(name: str, *, db_path: str = DB_PATH):
    """Load a CVRP/CVRPTW academic problem as a core ``RoutingProblem``."""
    problem = load_routing_problem(name, db_path=db_path)
    if problem is None:
        return None
    if problem.problem_type not in {"cvrp", "cvrptw"}:
        raise ValueError(f"Problem {name!r} is {problem.problem_type!r}, not CVRP/CVRPTW")
    return problem


def get_cvrp_problems(*, db_path: str = DB_PATH, max_dim: int = 10_000, as_legacy: bool = False):
    """List stored CVRP/CVRPTW problems from the unified academic DB."""
    rows = [
        row
        for row in get_all_problems(db_path=db_path, max_dim=max_dim, exclude_explicit=False)
        if str(row.get("problem_type", "")).upper() in {"CVRP", "CVRPTW"}
    ]
    if as_legacy:
        return [problem_row_to_instance(row) for row in rows]
    return rows


def get_cvrp_problem_as_instance(name: str, *, db_path: str = DB_PATH):
    """Load a CVRP/CVRPTW problem through the legacy benchmark instance shape."""
    rows = [row for row in get_cvrp_problems(db_path=db_path, as_legacy=False) if row["name"] == name]
    if not rows:
        return None
    return problem_row_to_instance(rows[0])


__all__ = [
    "import_cvrplib_file",
    "import_cvrplib_text",
    "import_solomon_file",
    "import_solomon_text",
    "load_cvrp_problem",
    "get_cvrp_problem_as_instance",
    "get_cvrp_problems",
]
