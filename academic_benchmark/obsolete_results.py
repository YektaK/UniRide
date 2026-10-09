"""Obsolete-result marker contract shared by the marking tool and result readers.

OWNER DECISION 2026-10-09 (DECISION_LOG A06): on the benchmark-runner path
``ga_split_enhanced`` and ``ga_split_hf`` now receive their params and the
per-run seed. Results produced before that change ignored the params and used
seed 42 for every run; they are marked obsolete (never deleted) and readers
exclude them unless the caller explicitly opts in. Old and new results must
never be pooled.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Mapping

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
