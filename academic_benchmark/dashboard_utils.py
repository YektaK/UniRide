from __future__ import annotations

import json
import os
from typing import Iterable, List, Tuple

import pandas as pd

try:
    from academic_benchmark.obsolete_results import filter_obsolete_frame
except ImportError:  # dashboard launched from academic_benchmark/ without the package installed
    from obsolete_results import filter_obsolete_frame


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


def read_progress_csv(progress_path: str) -> pd.DataFrame:
    """Read benchmark_progress.csv, tolerating inconsistent column counts."""
    try:
        df = pd.read_csv(progress_path)
    except pd.errors.ParserError:
        # Handle inconsistent column counts (e.g. result_type added mid-file)
        import csv
        import io
        with open(progress_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if rows:
            header = rows[0]
            ncols = len(header)
            # Detect if any row has more columns — if so, expand header
            max_cols = max(len(r) for r in rows)
            if max_cols > ncols:
                # Insert missing column names (result_type, etc.)
                extra = max_cols - ncols
                # Insert before params_json (last column)
                insert_at = ncols - 1
                for i in range(extra):
                    header.insert(insert_at + i, f"extra_col_{i}")
                ncols = len(header)
            # Pad or trim each row to match header length
            fixed = [header]
            for row in rows[1:]:
                if len(row) != ncols:
                    row = (row + [""] * ncols)[:ncols]
                fixed.append(row)
            buf = io.StringIO()
            writer = csv.writer(buf)
            for row in fixed:
                writer.writerow(row)
            buf.seek(0)
            df = pd.read_csv(buf)
        else:
            df = pd.DataFrame()
    return df


def load_csv_frames(result_dirs: Iterable[str], include_obsolete: bool = False):
    """Read summary/progress CSVs, filtering obsolete rows per directory before concatenation.

    Returns ``(summary_frames, progress_frames, loaded_sources)``. The OBSOLETE.md sibling
    marker, affected-algorithm identity and row ``obsolete`` metadata are applied to BOTH
    frames (CX-02); ``include_obsolete=True`` is the explicit override.
    """
    summaries: List[pd.DataFrame] = []
    progress: List[pd.DataFrame] = []
    sources = {"summary": [], "progress": []}
    for d in result_dirs:
        summary_path = os.path.join(d, "benchmark_summary.csv")
        progress_path = os.path.join(d, "benchmark_progress.csv")
        if os.path.exists(summary_path):
            summaries.append(filter_obsolete_frame(pd.read_csv(summary_path), d, include_obsolete))
            sources["summary"].append(summary_path)
        if os.path.exists(progress_path):
            progress.append(filter_obsolete_frame(read_progress_csv(progress_path), d, include_obsolete))
            sources["progress"].append(progress_path)
    return summaries, progress, sources
