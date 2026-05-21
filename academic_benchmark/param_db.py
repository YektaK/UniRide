#!/usr/bin/env python3
"""
param_db.py — Persistent Parameter Database for Numba Engine.

Stores best parameter sets per (problem, algorithm) across tuning runs.
Supports querying patterns across problems (e.g. "most common best params
for GA on small problems").

Schema:
    entries: List[ParamEntry]
    Each entry has:
        id, timestamp, problem, algorithm, params (dict),
        best_score, gap, runs, dimension, problem_category (small/medium/large)
"""

import json
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

_PARAM_DB_PATH = None

def set_db_path(path: str) -> None:
    global _PARAM_DB_PATH
    _PARAM_DB_PATH = path

def get_db_path() -> str:
    return _PARAM_DB_PATH or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "benchmark_db", "param_db.json"
    )

def _load() -> List[Dict[str, Any]]:
    path = get_db_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def _save(db: List[Dict[str, Any]]) -> None:
    path = get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def save_entry(problem: str, algorithm: str, params: Dict[str, Any],
               best_score: float, gap: float, runs: int,
               dimension: int, category: str = "small") -> int:
    db = _load()
    entry = {
        "id": max((e["id"] for e in db), default=0) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "problem": problem,
        "algorithm": algorithm,
        "params": params,
        "best_score": best_score,
        "gap": gap,
        "runs": runs,
        "dimension": dimension,
        "category": category,
    }
    db.append(entry)
    _save(db)
    return entry["id"]

def get_best_for(problem: str, algorithm: str) -> Optional[Dict[str, Any]]:
    db = _load()
    matches = [e for e in db if e["problem"] == problem and e["algorithm"] == algorithm]
    if not matches:
        return None
    valid = [e for e in matches if e.get("best_score") is not None and not math.isinf(e["best_score"])]
    if valid:
        return min(valid, key=lambda e: e["best_score"])
    # Fallback: best_score inf/null ise gap'e göre seç
    finite_gap = [e for e in matches if e.get("gap") is not None and not math.isinf(e.get("gap", 0))]
    if finite_gap:
        return min(finite_gap, key=lambda e: e["gap"])
    return matches[0]

def list_entries() -> List[Dict[str, Any]]:
    return _load()

def delete_entry(entry_id: int) -> bool:
    db = _load()
    before = len(db)
    db = [e for e in db if e["id"] != entry_id]
    if len(db) < before:
        _save(db)
        return True
    return False

def get_problems_for(algorithm: str) -> List[str]:
    return list(set(e["problem"] for e in _load() if e["algorithm"] == algorithm))

def analyze_patterns() -> str:
    """Return a Markdown analysis of parameter patterns across problem sizes."""
    from collections import Counter
    db = _load()
    if not db:
        return "No parameter entries found."

    lines = ["# Parameter Database Analysis", ""]
    categories = {"small": [], "medium": [], "large": []}
    for e in db:
        categories.get(e.get("category", "small"), []).append(e)

    for cat, entries in categories.items():
        if not entries:
            continue
        lines.append(f"## {cat.upper()} Problems ({len(entries)} entries)")
        algos = set(e["algorithm"] for e in entries)
        for algo in sorted(algos):
            algo_entries = [e for e in entries if e["algorithm"] == algo]
            lines.append(f"\n### {algo}")
            # Find common param values
            param_keys = set()
            for e in algo_entries:
                param_keys.update(e["params"].keys())
            for key in sorted(param_keys):
                vals = [str(e["params"].get(key)) for e in algo_entries if key in e["params"]]
                if vals:
                    counter = Counter(vals)
                    most_common = counter.most_common(3)
                    common_str = ", ".join(f"{v} ({c}x)" for v, c in most_common)
                    lines.append(f"- **{key}**: {common_str}")
            avg_gap = sum(e.get("gap", 0) for e in algo_entries) / len(algo_entries)
            lines.append(f"- **avg gap**: {avg_gap:.2f}%")
        lines.append("")

    return "\n".join(lines)
