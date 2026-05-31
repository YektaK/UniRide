from __future__ import annotations

import json
from typing import Iterable, List, Tuple

import pandas as pd


ROUTING_METRIC_COLUMNS = [
    "objective_cost",
    "tour_cost",
    "avg_length",
    "avg_gap",
    "elapsed_ms",
    "avg_time_ms",
    "num_vehicles",
    "capacity_violations",
    "tw_violations",
]


def derive_filter_options(
    summary_df: pd.DataFrame,
    progress_df: pd.DataFrame,
) -> Tuple[List[str], List[str]]:
    source_df = summary_df if not summary_df.empty else progress_df
    if source_df.empty:
        return [], []

    probs = sorted([p for p in source_df["problem"].unique() if pd.notna(p)])
    algos = sorted([a for a in source_df["strategy"].unique() if pd.notna(a)])
    return probs, algos


def benchmark_rows_to_progress_frame(rows: Iterable[dict]) -> pd.DataFrame:
    """Normalize SQLite benchmark rows into the dashboard progress schema."""
    normalized = []
    for row in rows:
        objective = row.get("objective_cost")
        tour_cost = row.get("tour_cost")
        elapsed = row.get("elapsed_ms")
        normalized.append({
            "timestamp": row.get("timestamp"),
            "problem": row.get("problem"),
            "strategy": row.get("algorithm"),
            "avg_length": objective if objective is not None else tour_cost,
            "objective_cost": objective if objective is not None else tour_cost,
            "tour_cost": tour_cost,
            "avg_gap": row.get("gap"),
            "elapsed_ms": elapsed,
            "avg_time_ms": elapsed,
            "n_runs": 1,
            "result_type": "raw",
            "problem_type": row.get("problem_type") or "tsp",
            "matrix_kind": row.get("matrix_kind") or "distance",
            "num_vehicles": row.get("num_vehicles"),
            "capacity_violations": row.get("capacity_violations", 0),
            "tw_violations": row.get("tw_violations", 0),
            "tour": _json_text(row.get("tour")),
            "routes_json": _json_text(row.get("routes")),
            "route_loads_json": _json_text(row.get("route_loads")),
            "route_costs_json": _json_text(row.get("route_costs")),
            "params_json": _json_text(row.get("params") or {}),
            "source": row.get("source") or "academic_db",
            "run_id": row.get("run_id"),
        })
    return pd.DataFrame(normalized)


def available_routing_metrics(df: pd.DataFrame) -> List[str]:
    """Return dashboard metrics that exist and contain at least one value."""
    if df.empty:
        return []
    metrics = []
    for column in ROUTING_METRIC_COLUMNS:
        if column in df.columns and df[column].notna().any():
            metrics.append(column)
    return metrics


def _json_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)
