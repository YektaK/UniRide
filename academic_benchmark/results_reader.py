"""Read-only accessors for academic benchmark results."""

from __future__ import annotations

import csv
import json
import math
import os
from typing import Dict, List, Optional

from academic_benchmark.obsolete_results import (
    EVIDENCE_CURRENT,
    EVIDENCE_HISTORICAL,
    LEGACY_RESULTS_DIRNAME,
    filter_obsolete_csv_rows,
    filter_obsolete_rows,
)
from academic_benchmark.tsplib_manager import (
    DB_PATH,
    count_by_evidence,
    get_all_problems,
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
    include_obsolete: bool = False,
    include_historical: bool = False,
) -> Dict[str, object]:
    """Leaderboard of CURRENT evidence. HISTORICAL_UNVERIFIED rows (stamped before the legacy
    cutoff, A13) are never mixed into ``results``; ``include_historical`` adds them as a separate,
    labelled ``historical_unverified`` section."""
    safe_limit = max(1, min(int(limit), 1000))
    rows = query_best_solutions(
        algorithm=algorithm,
        category=category,
        limit=safe_limit,
        db_path=db_path,
        include_obsolete=include_obsolete,
    )
    out: Dict[str, object] = {
        "source": "academic_db",
        "evidence_class": EVIDENCE_CURRENT,
        "count": len(rows),
        "limit": safe_limit,
        "results": rows,
        "historical_unverified_available": count_by_evidence("best_solutions", db_path)["historical"] > 0,
    }
    if include_historical:
        hist = query_best_solutions(
            algorithm=algorithm, category=category, limit=safe_limit, db_path=db_path, evidence="historical"
        )
        out["historical_unverified"] = {"evidence_class": EVIDENCE_HISTORICAL, "count": len(hist), "results": hist}
    return out


def get_best_result(
    problem: str,
    algorithm: str,
    db_path: str = DB_PATH,
    include_obsolete: bool = False,
    include_historical: bool = False,
) -> Dict[str, object]:
    row = get_best_solution(problem, algorithm, db_path=db_path, include_obsolete=include_obsolete)
    hist = get_best_solution(problem, algorithm, db_path=db_path, evidence="historical")
    out: Dict[str, object] = {
        "source": "academic_db",
        "evidence_class": EVIDENCE_CURRENT,
        "problem": problem,
        "algorithm": algorithm,
        "result": row,
        "historical_unverified_available": hist is not None,
    }
    if include_historical:
        out["historical_unverified"] = {"evidence_class": EVIDENCE_HISTORICAL, "result": hist}
    return out


def get_benchmark_rows(
    results_dir: str = DEFAULT_NUMBA_RESULTS_DIR,
    filename: str = "benchmark_progress.csv",
    limit: int = 100,
    db_path: str = DB_PATH,
    prefer_db: bool = True,
    feasible_only: bool = False,
    include_obsolete: bool = False,
    include_historical: bool = False,
) -> Dict[str, object]:
    """Read benchmark rows from SQLite source-of-truth, with CSV fallback.

    The default view is CURRENT evidence only. INVALID rows (metadata.obsolete, A06) are excluded
    unless ``include_obsolete``. HISTORICAL_UNVERIFIED rows (A13) are never mixed in:
    ``include_historical`` adds a separate labelled ``historical_unverified`` section.
    """
    safe_limit = max(1, min(int(limit), 5000))
    common = dict(
        results_dir=results_dir, filename=filename, safe_limit=safe_limit, db_path=db_path,
        prefer_db=prefer_db, feasible_only=feasible_only, include_obsolete=include_obsolete,
    )
    out = _benchmark_view(evidence="current", **common)
    out["evidence_class"] = EVIDENCE_CURRENT
    if include_historical:
        hist = _benchmark_view(evidence="historical", **common)
        hist["evidence_class"] = EVIDENCE_HISTORICAL
        out["historical_unverified"] = hist
    else:
        has_db = prefer_db and count_by_evidence("benchmark_results", db_path)["historical"] > 0
        has_csv = os.path.exists(os.path.join(results_dir, LEGACY_RESULTS_DIRNAME, filename))
        out["historical_unverified_available"] = bool(has_db or has_csv)
    return out


def _benchmark_view(
    *, results_dir, filename, safe_limit, db_path, prefer_db, feasible_only, include_obsolete, evidence
) -> Dict[str, object]:
    if prefer_db:
        db_rows = filter_obsolete_rows(
            query_benchmark_results(
                limit=safe_limit, db_path=db_path, exclude_obsolete=not include_obsolete, evidence=evidence
            ),
            include_obsolete,
            evidence,
        )
        if feasible_only:
            db_rows = [row for row in db_rows if is_feasible_benchmark_row(row)]
        if db_rows:
            return {
                "source": "academic_db",
                "count": len(db_rows),
                "limit": safe_limit,
                "results": db_rows,
            }

    path = os.path.join(results_dir, filename)
    # the quarantine folder legacy_pre_2026-10-13/ is read by the historical view only
    legacy_path = os.path.join(results_dir, LEGACY_RESULTS_DIRNAME, filename)
    scan = [(path, results_dir)]
    if evidence == "historical":  # older rows first so the newest-last limit keeps the latest
        scan.insert(0, (legacy_path, os.path.dirname(legacy_path)))
    scan = [(p, d) for p, d in scan if os.path.exists(p)]
    if not scan:
        return {"source": "academic_csv", "count": 0, "limit": safe_limit, "path": path, "results": []}

    raw_rows = []
    for csv_path, csv_dir in scan:
        with open(csv_path, newline="", encoding="utf-8") as handle:
            # Filter the raw rows: _normalize_benchmark_row drops the metadata columns.
            raw_rows.extend(filter_obsolete_csv_rows(list(csv.DictReader(handle)), csv_dir, include_obsolete, evidence))
    rows = [_normalize_benchmark_row(row) for row in raw_rows]
    if feasible_only:
        rows = [row for row in rows if is_feasible_benchmark_row(row)]

    rows = rows[-safe_limit:]
    return {
        "source": "academic_csv",
        "count": len(rows),
        "limit": safe_limit,
        "path": path,
        "results": rows,
    }


def get_academic_problems(
    problem_type: Optional[str] = None,
    category: Optional[str] = None,
    max_dim: int = 0,
    limit: int = 1000,
    db_path: str = DB_PATH,
) -> Dict[str, object]:
    """Read academic problem inventory from SQLite source-of-truth."""
    safe_limit = max(1, min(int(limit), 5000))
    rows = get_all_problems(db_path=db_path, max_dim=max(0, int(max_dim)), exclude_explicit=False)
    if problem_type:
        requested_type = problem_type.lower()
        rows = [row for row in rows if str(row.get("problem_type", "")).lower() == requested_type]
    if category:
        rows = [row for row in rows if row.get("category") == category]

    return {
        "source": "academic_db",
        "count": min(len(rows), safe_limit),
        "limit": safe_limit,
        "results": [_normalize_problem_row(row) for row in rows[:safe_limit]],
    }


def _normalize_benchmark_row(row: Dict[str, str]) -> Dict[str, object]:
    label = {"evidence_class": row["evidence_class"]} if row.get("evidence_class") else {}
    return {
        **label,
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


def _normalize_problem_row(row: Dict[str, object]) -> Dict[str, object]:
    demands = row.get("demands")
    capacities = row.get("capacities")
    time_windows = row.get("time_windows")
    service_times = row.get("service_times")
    return {
        "name": row.get("name"),
        "dimension": _int_or_none(row.get("dimension")),
        "optimal": _float_or_none(row.get("optimal")),
        "category": row.get("category"),
        "edge_weight_type": row.get("edge_weight_type"),
        "problem_type": str(row.get("problem_type") or "tsp").lower(),
        "matrix_kind": row.get("matrix_kind") or "distance",
        "has_coordinates": bool(row.get("coordinates")),
        "has_matrix": bool(row.get("dist_matrix") is not None or row.get("time_matrix") is not None),
        "has_demands": demands is not None,
        "has_capacities": capacities is not None,
        "has_time_windows": time_windows is not None,
        "has_service_times": service_times is not None,
        "num_vehicles": _int_or_none(row.get("num_vehicles")),
        "direction": row.get("direction"),
        "depot_index": _int_or_none(row.get("depot_index")),
        "max_route_duration": _float_or_none(row.get("max_route_duration")),
    }


def is_feasible_benchmark_row(row: Dict[str, object]) -> bool:
    """Return True when a benchmark row is safe for ranking/promotion."""
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = _json_or_none(metadata) or {}
    if isinstance(metadata, dict) and metadata.get("execution_failed"):
        return False
    if _int_or_zero(row.get("capacity_violations")) != 0:
        return False
    if _int_or_zero(row.get("tw_violations")) != 0:
        return False
    objective = _float_or_none(row.get("objective_cost"))
    tour_cost = _float_or_none(row.get("tour_cost"))
    return objective is not None or tour_cost is not None


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


__all__: List[str] = [
    "get_academic_problems",
    "get_leaderboard",
    "get_best_result",
    "get_benchmark_rows",
    "is_feasible_benchmark_row",
]
