"""Obsolete-result marker contract shared by the marking tool and result readers.

OWNER DECISION 2026-10-09 (DECISION_LOG A06): on the benchmark-runner path
``ga_split_enhanced`` and ``ga_split_hf`` now receive their params and the
per-run seed; before that they ignored params and used seed 42 for every run.
The benchmark-runner path keeps results in memory only (benchmark_state_manager)
and does not persist them to tsplib.db (0 rows for these algorithms on
2026-10-09, read-only check). This marker and the ``include_obsolete`` reader
filter are a guard for rows copied into tsplib.db and for result files.
Results exported before the fix (downloaded JSON, browser copies, POST /import)
cannot be marked automatically and must not be pooled with later results.
Marked data is never deleted.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Mapping

# The cutoff is the FIX date: rows stamped 2026-10-09 (any time) are NOT auto-marked,
# because the fix landed that day. Pass an exact ISO instant via --cutoff to mark
# part of that day.
OBSOLETE_CUTOFF = "2026-10-09"
OBSOLETE_REASON = (
    "pre-2026-10-09 benchmark-runner path ignored params and used seed 42 for every run "
    "(ga_split_enhanced/ga_split_hf); do not pool with later results"
)
AFFECTED_ALGORITHMS = frozenset({"ga_split_enhanced", "ga_split_hf"})


def normalize_algorithm(name: Any) -> str:
    return str(name or "").strip().lower().replace("-", "_").replace(" ", "_")


def is_affected(algorithm: Any, timestamp: Any, cutoff: str = OBSOLETE_CUTOFF) -> bool:
    """True when a row of this algorithm written before ``cutoff`` used the old path."""
    return normalize_algorithm(algorithm) in AFFECTED_ALGORITHMS and str(timestamp or "") < cutoff


def _metadata(row: Mapping[str, Any]) -> Mapping[str, Any]:
    if row.get("obsolete") in (True, "true", "True", "1", 1):
        return {"obsolete": True}
    meta = row.get("metadata")
    if meta is None and row.get("metadata_json"):
        meta = row["metadata_json"]
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return {}
    return meta if isinstance(meta, Mapping) else {}


def is_obsolete_row(row: Mapping[str, Any]) -> bool:
    return _metadata(row).get("obsolete") is True


def filter_obsolete_rows(rows: Iterable[Dict[str, Any]], include_obsolete: bool = False) -> List[Dict[str, Any]]:
    """Drop rows flagged obsolete unless ``include_obsolete`` is explicitly True."""
    rows = list(rows)
    if include_obsolete:
        return rows
    return [row for row in rows if not is_obsolete_row(row)]
