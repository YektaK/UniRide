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

ROUTING_PROBLEM_TYPES = {"cvrp", "cvrptw", "uniride"}


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
        metadata = row.get("metadata") or {}
        bks_cost = row.get("bks_cost", metadata.get("bks_cost"))
        bks_vehicles = row.get("bks_vehicles", metadata.get("bks_vehicles"))
        vehicle_gap = row.get("vehicle_gap", metadata.get("vehicle_gap"))
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
            "bks_cost": bks_cost,
            "bks_vehicles": bks_vehicles,
            "num_vehicles_bks": row.get("num_vehicles_bks", bks_vehicles),
            "vehicle_gap": vehicle_gap,
            "bks_source": row.get("bks_source", metadata.get("bks_source")),
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


def add_routing_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add CVRP/CVRPTW/UniRide dashboard helper columns without mutating input."""
    if df.empty:
        return df.copy()

    enriched = df.copy()
    if "problem_type" not in enriched.columns:
        enriched["problem_type"] = "tsp"
    enriched["problem_type"] = enriched["problem_type"].fillna("tsp").astype(str).str.lower()
    problems = enriched["problem"] if "problem" in enriched.columns else pd.Series([""] * len(enriched), index=enriched.index)
    enriched["dataset_family"] = [
        infer_dataset_family(problem, problem_type)
        for problem, problem_type in zip(problems, enriched["problem_type"])
    ]
    enriched["is_routing_problem"] = enriched["problem_type"].isin(ROUTING_PROBLEM_TYPES)
    capacity_violations = _numeric_series(enriched, "capacity_violations", 0)
    tw_violations = _numeric_series(enriched, "tw_violations", 0)
    enriched["is_feasible"] = (
        capacity_violations.fillna(0).astype(float).eq(0)
        & tw_violations.fillna(0).astype(float).eq(0)
    )
    enriched["constraint_status"] = [
        _constraint_status(cap, tw)
        for cap, tw in zip(capacity_violations.fillna(0), tw_violations.fillna(0))
    ]
    if "num_vehicles_bks" in enriched.columns and "num_vehicles" in enriched.columns:
        enriched["vehicle_gap"] = enriched["num_vehicles"] - enriched["num_vehicles_bks"]
    elif "bks_vehicles" in enriched.columns and "num_vehicles" in enriched.columns:
        enriched["vehicle_gap"] = enriched["num_vehicles"] - enriched["bks_vehicles"]
    else:
        enriched["vehicle_gap"] = pd.NA
    return enriched


def infer_dataset_family(problem: object, problem_type: object = None) -> str:
    """Infer a compact dataset family label for dashboard grouping."""
    name = str(problem or "").strip()
    lower = name.lower()
    ptype = str(problem_type or "").lower()
    if not name:
        return "unknown"
    if lower.startswith("smoke-"):
        return "smoke"
    if ptype == "uniride" or lower.startswith("uniride"):
        return "uniride"
    if ptype == "cvrptw":
        prefix = "".join(ch for ch in name.upper() if ch.isalpha())
        if prefix.startswith("RC"):
            return "Solomon-RC"
        if prefix.startswith("R"):
            return "Solomon-R"
        if prefix.startswith("C"):
            return "Solomon-C"
        return "CVRPTW"
    if ptype == "cvrp":
        return name.split("-", 1)[0].upper() if "-" in name else "CVRP"
    if ptype == "atsp":
        return "ATSP"
    return "TSP"


def routing_dashboard_columns(df: pd.DataFrame) -> List[str]:
    """Return existing columns useful for the routing diagnostics table."""
    preferred = [
        "problem",
        "dataset_family",
        "problem_type",
        "matrix_kind",
        "strategy",
        "objective_cost",
        "num_vehicles",
        "vehicle_gap",
        "capacity_violations",
        "tw_violations",
        "constraint_status",
        "is_feasible",
        "route_loads_json",
        "route_costs_json",
        "routes_json",
        "run_id",
        "source",
    ]
    return [column for column in preferred if column in df.columns]


def _json_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _numeric_series(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series([default] * len(df), index=df.index)


def _constraint_status(capacity_violations, tw_violations) -> str:
    cap = int(capacity_violations or 0)
    tw = int(tw_violations or 0)
    if cap == 0 and tw == 0:
        return "feasible"
    parts = []
    if cap:
        parts.append(f"capacity={cap}")
    if tw:
        parts.append(f"time_window={tw}")
    return ", ".join(parts)
