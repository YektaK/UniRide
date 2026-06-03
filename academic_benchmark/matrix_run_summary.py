"""Summarize persisted matrix-native benchmark runs."""

from __future__ import annotations

import argparse
import json
import math
from typing import Any, Dict, Iterable, Optional, Tuple

from academic_benchmark.tsplib_manager import DB_PATH, query_benchmark_results


def summarize_benchmark_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Return feasibility and hierarchical BKS counters for benchmark rows."""
    summary: Dict[str, Any] = {
        "total_rows": 0,
        "failed_rows": 0,
        "feasible_rows": 0,
        "capacity_violation_rows": 0,
        "tw_violation_rows": 0,
        "positive_vehicle_gap_rows": 0,
        "distance_gap_suppressed_rows": 0,
        "unexpected_distance_gap_with_vehicle_gap_rows": 0,
        "by_problem_type": {},
        "best_feasible": {},
    }

    for row in rows:
        summary["total_rows"] += 1
        metadata = row.get("metadata") or {}
        problem_type = str(row.get("problem_type") or "unknown").lower()
        failed = bool(metadata.get("execution_failed")) or bool(row.get("error"))
        capacity_violations = int(row.get("capacity_violations") or 0)
        tw_violations = int(row.get("tw_violations") or 0)
        feasible = not failed and capacity_violations == 0 and tw_violations == 0 and _finite(row.get("objective_cost"))

        type_bucket = summary["by_problem_type"].setdefault(
            problem_type,
            {"rows": 0, "feasible": 0, "failed": 0},
        )
        type_bucket["rows"] += 1

        if failed:
            summary["failed_rows"] += 1
            type_bucket["failed"] += 1
        if capacity_violations:
            summary["capacity_violation_rows"] += 1
        if tw_violations:
            summary["tw_violation_rows"] += 1
        if feasible:
            summary["feasible_rows"] += 1
            type_bucket["feasible"] += 1
            _update_best(summary["best_feasible"], row, metadata)

        vehicle_gap = _vehicle_gap(row, metadata)
        if vehicle_gap is not None and vehicle_gap > 0:
            summary["positive_vehicle_gap_rows"] += 1
            if row.get("gap") is None:
                summary["distance_gap_suppressed_rows"] += 1
            else:
                summary["unexpected_distance_gap_with_vehicle_gap_rows"] += 1

    return summary


def summarize_run(run_id: str, *, db_path: str = DB_PATH, limit: int = 10_000) -> Dict[str, Any]:
    """Load and summarize rows for a persisted benchmark run id."""
    rows = query_benchmark_results(run_id=run_id, db_path=db_path, limit=limit)
    summary = summarize_benchmark_rows(rows)
    summary["run_id"] = run_id
    return summary


def _update_best(best: Dict[Tuple[str, str], Dict[str, Any]], row: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    key = (str(row.get("problem")), str(row.get("algorithm")))
    current = best.get(key)
    objective = float(row["objective_cost"])
    if current is None or objective < current["objective_cost"]:
        best[key] = {
            "objective_cost": objective,
            "gap": row.get("gap"),
            "num_vehicles": row.get("num_vehicles"),
            "vehicle_gap": _vehicle_gap(row, metadata),
        }


def _vehicle_gap(row: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[int]:
    value = metadata.get("vehicle_gap", row.get("vehicle_gap"))
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def make_json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {_json_key(key): make_json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_ready(item) for item in value]
    return value


def _json_key(value: Any) -> str:
    if isinstance(value, tuple):
        return "::".join(str(item) for item in value)
    return str(value)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize a persisted matrix-native benchmark run")
    parser.add_argument("run_id")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--limit", type=int, default=10_000)
    args = parser.parse_args(argv)

    print(json.dumps(make_json_ready(summarize_run(args.run_id, db_path=args.db_path, limit=args.limit)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["make_json_ready", "summarize_benchmark_rows", "summarize_run"]
