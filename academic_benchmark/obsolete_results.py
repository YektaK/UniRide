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

LEGACY RULE (DECISION_LOG A10/A11 and the 2026-10-13 legacy decision): independent of
algorithm, every result stamped before ``LEGACY_CUTOFF`` is obsolete. It is rule based
(timestamp comparison), so tables without a metadata column (``best_solutions``) need no
schema change. Directory markers carry a ``Legacy-Cutoff:`` line; a bare A06 marker still
only affects the A06 algorithms.
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

# Legacy rule: rows stamped on/after this date are NOT legacy. Readers resolve the
# module attribute at call time (see ``legacy_cutoff``); writers stamp ISO instants.
LEGACY_CUTOFF = "2026-10-13"
LEGACY_REASON = (
    "pre-2026-10-13 legacy result: produced before the fairness protocol was enforced and before "
    "the Science-review label/identity fixes (DECISION_LOG A10/A11); not evidence; do not pool"
)
LEGACY_MARKER_KEY = "Legacy-Cutoff:"


def legacy_cutoff() -> str:
    return LEGACY_CUTOFF


def is_legacy_timestamp(timestamp: Any, cutoff: Any = None) -> bool:
    """True for a non-empty ISO timestamp string strictly before the legacy cutoff."""
    if not isinstance(timestamp, str) or not timestamp.strip():
        return False
    return timestamp.strip() < (cutoff or legacy_cutoff())


def normalize_algorithm(name: Any) -> str:
    return str(name or "").strip().lower().replace("-", "_").replace(" ", "_")


def is_affected(algorithm: Any, timestamp: Any, cutoff: str = OBSOLETE_CUTOFF) -> bool:
    """True when a row of this algorithm written before ``cutoff`` used the old path."""
    return normalize_algorithm(algorithm) in AFFECTED_ALGORITHMS and str(timestamp or "") < cutoff


def _metadata(row: Mapping[str, Any]) -> Mapping[str, Any]:
    if row.get("obsolete") in (True, "true", "True", "1", 1):
        return {"obsolete": True}
    meta = row.get("metadata")
    if not isinstance(meta, (Mapping, str)) or meta == "":
        # absent, NaN or empty metadata column: fall back to metadata_json
        meta = row.get("metadata_json") or None
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return {}
    return meta if isinstance(meta, Mapping) else {}


def is_obsolete_row(row: Mapping[str, Any]) -> bool:
    """A06 metadata flag OR legacy rule (timestamp before ``LEGACY_CUTOFF``)."""
    return _metadata(row).get("obsolete") is True or is_legacy_timestamp(row.get("timestamp"))


def filter_obsolete_rows(rows: Iterable[Dict[str, Any]], include_obsolete: bool = False) -> List[Dict[str, Any]]:
    """Drop rows flagged obsolete unless ``include_obsolete`` is explicitly True."""
    rows = list(rows)
    if include_obsolete:
        return rows
    return [row for row in rows if not is_obsolete_row(row)]


OBSOLETE_MARKER_FILE = "OBSOLETE.md"
_ALGORITHM_COLUMNS = ("algorithm", "strategy", "algorithm_id")


def marker_legacy_cutoff(results_dir: str) -> Any:
    """Cutoff from a ``Legacy-Cutoff:`` line of the sibling OBSOLETE.md, else None."""
    import os

    path = os.path.join(results_dir, OBSOLETE_MARKER_FILE)
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith(LEGACY_MARKER_KEY):
                    return line[len(LEGACY_MARKER_KEY):].strip() or legacy_cutoff()
    except OSError:
        pass
    return None


def _row_is_excluded(row: Mapping[str, Any], marker_present: bool, marker_cutoff: Any = None) -> bool:
    """CSV row exclusion: row metadata/legacy timestamp, or sibling marker plus an affected
    algorithm; a legacy marker also hides rows without a timestamp or older than its cutoff."""
    if is_obsolete_row(row):
        return True
    if marker_present:
        if any(normalize_algorithm(row.get(col)) in AFFECTED_ALGORITHMS for col in _ALGORITHM_COLUMNS):
            return True
        if marker_cutoff:
            ts = row.get("timestamp")
            return not (isinstance(ts, str) and ts.strip()) or is_legacy_timestamp(ts, marker_cutoff)
    return False


def filter_obsolete_csv_rows(
    rows: Iterable[Dict[str, Any]], results_dir: str, include_obsolete: bool = False
) -> List[Dict[str, Any]]:
    """Shared CSV filter: OBSOLETE.md sibling marker, affected algorithm identity, row metadata,
    legacy timestamp rule."""
    import os

    rows = list(rows)
    if include_obsolete:
        return rows
    marker = os.path.exists(os.path.join(results_dir, OBSOLETE_MARKER_FILE))
    cutoff = marker_legacy_cutoff(results_dir) if marker else None
    return [row for row in rows if not _row_is_excluded(row, marker, cutoff)]


def filter_obsolete_frame(frame: Any, results_dir: str, include_obsolete: bool = False) -> Any:
    """DataFrame form of :func:`filter_obsolete_csv_rows`; call BEFORE concatenation/aggregation."""
    import os

    if include_obsolete or frame is None or len(frame) == 0:
        return frame
    marker = os.path.exists(os.path.join(results_dir, OBSOLETE_MARKER_FILE))
    cutoff = marker_legacy_cutoff(results_dir) if marker else None
    keep = [not _row_is_excluded(row, marker, cutoff) for row in frame.to_dict("records")]
    return frame[keep].reset_index(drop=True)
