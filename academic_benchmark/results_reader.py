"""Read-only accessors for academic benchmark results."""

from __future__ import annotations

import csv
import json
import math
import os
from typing import Dict, List, Optional

from academic_benchmark.tsplib_manager import (
    DB_PATH,
    get_best_solution,
    query_benchmark_results,
    query_best_solutions,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NUMBA_RESULTS_DIR = os.path.join(_HERE, "numba_results")


def get_leaderboard(
    algorithm: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    db_path: str = DB_PATH,
) -> Dict[str, object]:
    safe_limit = max(1, min(int(limit), 1000))
    rows = query_best_solutions(
        algorithm=algorithm,
        category=category,
        limit=safe_limit,
        db_path=db_path,
    )
    return {
        "source": "academic_db",
        "count": len(rows),
        "limit": safe_limit,
        "results": rows,
    }


def get_best_result(problem: str, algorithm: str, db_path: str = DB_PATH) -> Dict[str, object]:
    row = get_best_solution(problem, algorithm, db_path=db_path)
    return {
        "source": "academic_db",
        "problem": problem,
        "algorithm": algorithm,
        "result": row,
    }


def get_benchmark_rows(
    results_dir: str = DEFAULT_NUMBA_RESULTS_DIR,
    filename: str = "benchmark_progress.csv",
    limit: int = 100,
    db_path: str = DB_PATH,
    prefer_db: bool = True,
) -> Dict[str, object]:
    """Read benchmark rows from SQLite source-of-truth, with CSV fallback."""
    safe_limit = max(1, min(int(limit), 5000))
    if prefer_db:
        db_rows = query_benchmark_results(limit=safe_limit, db_path=db_path)
        if db_rows:
            return {
                "source": "academic_db",
                "count": len(db_rows),
                "limit": safe_limit,
                "results": db_rows,
            }

    path = os.path.join(results_dir, filename)
    if not os.path.exists(path):
        return {"source": "academic_csv", "count": 0, "limit": safe_limit, "path": path, "results": []}

    with open(path, newline="", encoding="utf-8") as handle:
        rows = [_normalize_benchmark_row(row) for row in csv.DictReader(handle)]

    rows = rows[-safe_limit:]
    return {
        "source": "academic_csv",
        "count": len(rows),
        "limit": safe_limit,
        "path": path,
        "results": rows,
    }


def _normalize_benchmark_row(row: Dict[str, str]) -> Dict[str, object]:
    return {
        "timestamp": row.get("timestamp"),
        "problem": row.get("problem"),
        "algorithm": row.get("strategy"),
        "avg_length": _float_or_none(row.get("avg_length")),
        "objective_cost": _float_or_none(row.get("objective_cost")) or _float_or_none(row.get("avg_length")),
        "avg_gap": _float_or_none(row.get("avg_gap")),
        "avg_time_ms": _float_or_none(row.get("avg_time_ms")),
        "n_runs": _int_or_none(row.get("n_runs")),
        "problem_type": row.get("problem_type") or "tsp",
        "matrix_kind": row.get("matrix_kind") or "distance",
        "num_vehicles": _int_or_none(row.get("num_vehicles")),
        "capacity_violations": _int_or_zero(row.get("capacity_violations")),
        "tw_violations": _int_or_zero(row.get("tw_violations")),
        "routes": _json_or_none(row.get("routes_json")),
        "route_loads": _json_or_none(row.get("route_loads_json")),
        "route_costs": _json_or_none(row.get("route_costs_json")),
        "params": _json_or_none(row.get("params_json")),
        "gap_type": row.get("gap_type") or "unknown",
    }


def _float_or_none(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int_or_none(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _int_or_zero(value):
    parsed = _int_or_none(value)
    return 0 if parsed is None else parsed


def _json_or_none(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


__all__: List[str] = ["get_leaderboard", "get_best_result", "get_benchmark_rows"]
