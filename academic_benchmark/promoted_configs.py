"""Build and read core-consumable promoted algorithm configs."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from academic_benchmark.tsplib_manager import (
    DB_PATH,
    get_db,
    init_db,
    query_benchmark_results,
    query_best_solutions,
)
from academic_benchmark.results_reader import is_feasible_benchmark_row

DEFAULT_PROMOTED_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "benchmark_db",
    "promoted_configs.json",
)


def build_promoted_configs(
    *,
    db_path: str = DB_PATH,
    limit: int = 5000,
    generated_at: Optional[str] = None,
    include_empty_params: bool = False,
) -> Dict[str, object]:
    """Build a neutral promoted-config document from academic DB rows."""
    _ensure_db_schema(db_path)
    candidates = []
    candidates.extend(_best_solution_candidates(query_best_solutions(limit=limit, db_path=db_path)))
    candidates.extend(
        _benchmark_result_candidates(
            query_benchmark_results(limit=limit, db_path=db_path),
            include_empty_params=include_empty_params,
        )
    )

    selected = _select_best_candidates(candidates)
    return {
        "schema_version": 1,
        "source": "academic_db",
        "generated_at": generated_at or datetime.now().isoformat(timespec="seconds"),
        "selection_rule": (
            "prefer non-smoke evidence; use finite gap when present; otherwise prefer latest "
            "no-gap validation before objective/tour cost per algorithm/problem_type/matrix_kind"
        ),
        "configs": selected,
    }


def _ensure_db_schema(db_path: str) -> None:
    conn = get_db(db_path)
    init_db(conn)
    conn.close()


def write_promoted_configs(
    *,
    output_path: str = DEFAULT_PROMOTED_CONFIG_PATH,
    db_path: str = DB_PATH,
    limit: int = 5000,
    generated_at: Optional[str] = None,
    include_empty_params: bool = False,
) -> Dict[str, object]:
    """Write promoted configs and return the emitted document."""
    document = build_promoted_configs(
        db_path=db_path,
        limit=limit,
        generated_at=generated_at,
        include_empty_params=include_empty_params,
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False, sort_keys=True)
    return document


def load_promoted_configs(path: str = DEFAULT_PROMOTED_CONFIG_PATH) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_promoted_params(
    document: Dict[str, object],
    algorithm: str,
    *,
    problem_type: str = "tsp",
    matrix_kind: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    """Return promoted params for a core engine, or None when no match exists."""
    requested_type = problem_type.lower()
    requested_matrix = matrix_kind.lower() if matrix_kind else None
    for config in document.get("configs", []):
        if str(config.get("algorithm")) != algorithm:
            continue
        if str(config.get("problem_type", "tsp")).lower() != requested_type:
            continue
        if requested_matrix and str(config.get("matrix_kind", "distance")).lower() != requested_matrix:
            continue
        return dict(config.get("params") or {})
    return None


def _best_solution_candidates(rows: Iterable[Dict]) -> List[Dict]:
    candidates = []
    for row in rows:
        candidates.append({
            "algorithm": row.get("algorithm"),
            "problem_type": "tsp",
            "matrix_kind": "distance",
            "params": row.get("params") or {},
            "score": row.get("tour_length"),
            "gap": _normalize_gap(row.get("gap")),
            "source_table": "best_solutions",
            "selected_from": {
                "problem": row.get("problem"),
                "dimension": row.get("dimension"),
                "category": row.get("category"),
                "timestamp": row.get("timestamp"),
            },
        })
    return candidates


def _benchmark_result_candidates(rows: Iterable[Dict], *, include_empty_params: bool = False) -> List[Dict]:
    candidates = []
    for row in rows:
        if not is_feasible_benchmark_row(row):
            continue
        params = _benchmark_params(row)
        if not params and not include_empty_params:
            continue
        score = row.get("objective_cost")
        if score is None:
            score = row.get("tour_cost")
        candidates.append({
            "algorithm": row.get("algorithm"),
            "problem_type": str(row.get("problem_type") or "tsp").lower(),
            "matrix_kind": str(row.get("matrix_kind") or "distance").lower(),
            "params": params,
            "score": score,
            "gap": _normalize_gap(row.get("gap")),
            "source_table": "benchmark_results",
            "selected_from": {
                "problem": row.get("problem"),
                "run_id": row.get("run_id"),
                "run_number": row.get("run_number"),
                "timestamp": row.get("timestamp"),
            },
        })
    return candidates


def _benchmark_params(row: Dict) -> Dict:
    params = row.get("params") or {}
    if params:
        return dict(params)
    metadata = row.get("metadata") or {}
    algorithm_params = metadata.get("algorithm_params") or {}
    return dict(algorithm_params) if isinstance(algorithm_params, dict) else {}


def _select_best_candidates(candidates: Iterable[Dict]) -> List[Dict]:
    best_by_key: Dict[Tuple[str, str, str], Dict] = {}
    for candidate in candidates:
        algorithm = candidate.get("algorithm")
        if not algorithm:
            continue
        key = (
            str(algorithm),
            str(candidate.get("problem_type") or "tsp").lower(),
            str(candidate.get("matrix_kind") or "distance").lower(),
        )
        if key not in best_by_key or _rank(candidate) < _rank(best_by_key[key]):
            best_by_key[key] = candidate

    selected = []
    for (algorithm, problem_type, matrix_kind), candidate in sorted(best_by_key.items()):
        selected.append({
            "algorithm": algorithm,
            "problem_type": problem_type,
            "matrix_kind": matrix_kind,
            "params": dict(candidate.get("params") or {}),
            "score": _finite_or_none(candidate.get("score")),
            "gap": _finite_or_none(candidate.get("gap")),
            "source_table": candidate.get("source_table"),
            "selected_from": candidate.get("selected_from") or {},
        })
    return selected


def _rank(candidate: Dict) -> Tuple[float, float, float, float, float]:
    gap = _finite_or_inf(candidate.get("gap"))
    score = _finite_or_inf(candidate.get("score"))
    if math.isfinite(gap):
        quality = (0.0, gap, score, 0.0)
    else:
        quality = (1.0, 0.0, -_timestamp_value(candidate), score)
    return (1.0 if _is_smoke_candidate(candidate) else 0.0, *quality)


def _is_smoke_candidate(candidate: Dict) -> bool:
    selected_from = candidate.get("selected_from") or {}
    problem = str(selected_from.get("problem") or "").lower()
    run_id = str(selected_from.get("run_id") or "").lower()
    return problem.startswith("smoke-") or "smoke" in run_id


def _timestamp_value(candidate: Dict) -> float:
    selected_from = candidate.get("selected_from") or {}
    raw = selected_from.get("timestamp")
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _finite_or_inf(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.inf
    return number if math.isfinite(number) else math.inf


def _normalize_gap(value):
    number = _finite_or_inf(value)
    if math.isinf(number):
        return value
    return 0.0 if abs(number) < 1e-9 else number


def _finite_or_none(value):
    number = _finite_or_inf(value)
    return None if math.isinf(number) else number


__all__ = [
    "DEFAULT_PROMOTED_CONFIG_PATH",
    "build_promoted_configs",
    "load_promoted_configs",
    "resolve_promoted_params",
    "write_promoted_configs",
]
