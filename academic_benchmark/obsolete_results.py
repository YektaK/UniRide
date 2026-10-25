"""Evidence classes for stored benchmark results: INVALID (A06/A07) vs HISTORICAL_UNVERIFIED (A13).

Two different classes, two different rules; never mix them up.

1. INVALID / obsolete (DECISION_LOG A06, A07; owner decision 2026-10-09). On the
   benchmark-runner path ``ga_split_enhanced`` and ``ga_split_hf`` now receive their params and
   the per-run seed; before that they ignored params and used seed 42 for every run. Rows carry
   ``metadata.obsolete`` (or sit next to an ``OBSOLETE.md`` and name an affected algorithm) and
   are HIDDEN by default; ``include_obsolete=True`` shows them. The benchmark-runner path keeps
   results in memory only and does not persist them to tsplib.db (0 rows on 2026-10-09).
   Results exported before the fix (downloaded JSON, browser copies, POST /import) cannot be
   marked automatically and must not be pooled with later results.

2. HISTORICAL_UNVERIFIED (DECISION_LOG A13; owner decision 2026-10-14, following the
   "Evidence Quarantine" contract of ACADEMIC_STUDY_UNIFICATION_DESIGN.md). Independent of
   algorithm, every result stamped before ``LEGACY_CUTOFF`` lacks a complete provenance,
   fair-budget and validation chain. It is NOT deleted and NOT hidden: it stays visible in an
   explicitly labelled view (``evidence="historical"``, ``evidence_class`` on every row), but it
   is NEVER pooled with current results (default views and aggregations contain current rows
   only). The rule is timestamp based, so ``best_solutions`` (no metadata column) needs no schema
   change. Result files live in ``legacy_pre_2026-10-13/`` folders that carry ``QUARANTINE.md``
   and a SHA-256 manifest (``QUARANTINE_MANIFEST.json``). Old tuned parameters are not used for
   warm start but are kept (``legacy_best_params``).
"""

from __future__ import annotations

import hashlib
import json
import os
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

# Historical rule: rows stamped on/after this date are NOT historical. Readers resolve the
# module attribute at call time (see ``legacy_cutoff``); writers stamp ISO instants.
# Rationale (owner-confirmed 2026-10-15, DECISION_LOG A13): 2026-10-13 is the day the second of two
# evidence fixes landed (2026-10-09 merge 62673ca: ga_split params+seed; 2026-10-13 merge 2e157a1:
# Science-review label/identity fixes), so every earlier result is missing at least one of them.
LEGACY_CUTOFF = "2026-10-13"
LEGACY_REASON = (
    "pre-2026-10-13 result: produced before the fairness protocol was enforced and before the "
    "Science-review label/identity fixes; classified HISTORICAL_UNVERIFIED by DECISION_LOG A13 "
    "(visible and labelled, never pooled with current results, never deleted)"
)
# Old result files live in this subfolder of each results directory (QUARANTINE.md there).
LEGACY_RESULTS_DIRNAME = "legacy_pre_2026-10-13"
QUARANTINE_MARKER_FILE = "QUARANTINE.md"
QUARANTINE_MANIFEST_FILE = "QUARANTINE_MANIFEST.json"
OBSOLETE_MARKER_FILE = "OBSOLETE.md"  # INVALID class (A06) only

EVIDENCE_CURRENT = "current"
EVIDENCE_HISTORICAL = "historical_unverified"  # label written on rows and API sections
EVIDENCE_VIEWS = ("current", "historical")  # values of the ``evidence`` parameter
HISTORICAL_MANIFEST_CLASS = "HISTORICAL_UNVERIFIED"


def legacy_cutoff() -> str:
    return LEGACY_CUTOFF


def _parse_instant(value: Any) -> Any:
    """Parse an ISO-8601 date/datetime string (``Z`` allowed) to a naive UTC-comparable datetime.

    Offset-aware values are converted to UTC; naive values are taken as written (the cutoff
    is naive too). Returns None when the value cannot be parsed.
    """
    from datetime import datetime, timezone

    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text[-1] in "zZ":
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, OverflowError):
        return None
    return parsed


def is_legacy_timestamp(timestamp: Any, cutoff: Any = None) -> bool:
    """True when ``timestamp`` is strictly before the legacy cutoff, FAIL-CLOSED.

    The timestamp is parsed as ISO-8601 (``Z``/offsets converted to UTC). Empty, missing or
    unparseable stamps (``2026/06/30``, ``13.10.2026``, epoch strings) cannot be shown to be
    new, so they count as historical. SQL readers call this very function through
    ``register_sql_functions`` (``uniride_is_legacy``), so SQL and Python agree by construction.
    """
    stamp = _parse_instant(timestamp)
    limit = _parse_instant(str(cutoff or legacy_cutoff()))
    if stamp is None or limit is None:
        return True
    return stamp < limit


def register_sql_functions(conn: Any) -> None:
    """Expose the Python cutoff rule to SQLite as ``uniride_is_legacy(timestamp)`` (A13/C4)."""
    conn.create_function("uniride_is_legacy", 1, lambda ts: 1 if is_legacy_timestamp(ts) else 0, deterministic=True)


def best_params_entry_timestamp(entry: Any) -> Any:
    return entry.get("timestamp") if isinstance(entry, Mapping) else None


LEGACY_BEST_PARAMS_KEY = "legacy_best_params"


def quarantine_legacy_best_params(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Warm-start guard (A13, owner decision D2): historical parameters must not seed new runs.

    Entries of ``metadata["best_params"]`` with no/old/unparseable ``timestamp`` are MOVED (not
    deleted) to ``metadata["legacy_best_params"]``; the dict is mutated in place and returned.
    There is deliberately NO opt-out (no flag, no environment variable): a way to put old
    parameters back into warm start would defeat owner decision D2.
    """
    best = metadata.get("best_params")
    if not isinstance(best, dict):
        return metadata
    stale = {k: v for k, v in best.items() if is_legacy_timestamp(best_params_entry_timestamp(v))}
    if stale:
        legacy = metadata.get(LEGACY_BEST_PARAMS_KEY)
        if not isinstance(legacy, dict):
            legacy = metadata[LEGACY_BEST_PARAMS_KEY] = {}
        for key, value in stale.items():
            del best[key]
            target, n = key, 1
            # never overwrite an already-quarantined record: keep both under distinct keys
            while target in legacy and legacy[target] != value:
                n += 1
                target = f"{key}#{n}"
            legacy[target] = value
    return metadata


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
    """INVALID class (A06): the row carries ``metadata.obsolete``. The timestamp rule is NOT here."""
    return _metadata(row).get("obsolete") is True


def row_evidence_class(row: Mapping[str, Any], in_quarantine: bool = False) -> str:
    """``"historical_unverified"`` or ``"current"`` for one row.

    A row in a quarantine folder is always historical. Otherwise a row with a timestamp column but
    an empty/unparseable value is historical (fail-closed, like SQL); a row with no timestamp
    column at all (e.g. a summary CSV) cannot be judged by this rule and counts as current.
    """
    if in_quarantine or ("timestamp" in row and is_legacy_timestamp(row.get("timestamp"))):
        return EVIDENCE_HISTORICAL
    return EVIDENCE_CURRENT


def _view_class(evidence: str) -> str:
    if evidence not in EVIDENCE_VIEWS:
        raise ValueError(f"evidence must be one of {EVIDENCE_VIEWS}, got {evidence!r}")
    return EVIDENCE_HISTORICAL if evidence == "historical" else EVIDENCE_CURRENT


def filter_obsolete_rows(
    rows: Iterable[Dict[str, Any]], include_obsolete: bool = False, evidence: str = "current"
) -> List[Dict[str, Any]]:
    """Select one evidence view; drop INVALID (A06) rows unless ``include_obsolete`` is True.

    Historical rows come back labelled (``evidence_class``). The views are never merged.
    """
    wanted = _view_class(evidence)
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not include_obsolete and is_obsolete_row(row):
            continue
        if row_evidence_class(row) != wanted:
            continue
        out.append(dict(row, evidence_class=wanted) if wanted == EVIDENCE_HISTORICAL else row)
    return out


_CURRENT_LABELS = (None, EVIDENCE_CURRENT, "CURRENT")


def evidence_refusal(row: Mapping[str, Any], allow_obsolete: bool = False) -> Any:
    """Why ``row`` must not enter an aggregate, statistic or report, or ``None`` when it may (Gate D, D-08b).

    Aggregation entry points (``matrix_run_summary``, the analysis statistics and report services) call this on every row they are given:
    a row labelled anything but current (``historical_unverified``, ``invalid``, ...; A13) is refused, and so is an INVALID row marked
    ``metadata.obsolete`` (A06) unless ``allow_obsolete`` (the explicit INVALID switch of ``summarize_run``)."""
    label = row.get("evidence_class") if isinstance(row, Mapping) else None
    if label not in _CURRENT_LABELS:
        return f"evidence_class {label!r}: historical_unverified and invalid rows are never aggregated, analysed or reported (A13)"
    if not allow_obsolete and isinstance(row, Mapping) and is_obsolete_row(row):
        return "obsolete row (INVALID, A06): rows marked metadata.obsolete are never aggregated, analysed or reported"
    return None


_ALGORITHM_COLUMNS = ("algorithm", "strategy", "algorithm_id")


def in_quarantine_dir(results_dir: str) -> bool:
    """True for ``legacy_pre_2026-10-13/`` folders (and subfolders) or any folder with QUARANTINE.md."""
    parts = os.path.normpath(os.path.abspath(results_dir)).split(os.sep)
    return LEGACY_RESULTS_DIRNAME in parts or os.path.exists(os.path.join(results_dir, QUARANTINE_MARKER_FILE))


def _csv_row_invalid(row: Mapping[str, Any], a06_marker: bool) -> bool:
    if is_obsolete_row(row):
        return True
    return a06_marker and any(normalize_algorithm(row.get(col)) in AFFECTED_ALGORITHMS for col in _ALGORITHM_COLUMNS)


def filter_obsolete_csv_rows(
    rows: Iterable[Dict[str, Any]], results_dir: str, include_obsolete: bool = False, evidence: str = "current"
) -> List[Dict[str, Any]]:
    """Shared CSV filter: INVALID class (OBSOLETE.md sibling marker + affected algorithm, row
    metadata) unless ``include_obsolete``; then the evidence view (quarantine folder or timestamp)."""
    wanted = _view_class(evidence)
    a06_marker = os.path.exists(os.path.join(results_dir, OBSOLETE_MARKER_FILE))
    quarantined = in_quarantine_dir(results_dir)
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not include_obsolete and _csv_row_invalid(row, a06_marker):
            continue
        if row_evidence_class(row, quarantined) != wanted:
            continue
        out.append(dict(row, evidence_class=wanted) if wanted == EVIDENCE_HISTORICAL else row)
    return out


def filter_obsolete_frame(frame: Any, results_dir: str, include_obsolete: bool = False, evidence: str = "current") -> Any:
    """DataFrame form of :func:`filter_obsolete_csv_rows`; call BEFORE concatenation/aggregation."""
    wanted = _view_class(evidence)
    if frame is None or len(frame) == 0:
        return frame
    a06_marker = os.path.exists(os.path.join(results_dir, OBSOLETE_MARKER_FILE))
    quarantined = in_quarantine_dir(results_dir)
    keep = [
        (include_obsolete or not _csv_row_invalid(row, a06_marker)) and row_evidence_class(row, quarantined) == wanted
        for row in frame.to_dict("records")
    ]
    result = frame[keep].reset_index(drop=True)
    if wanted == EVIDENCE_HISTORICAL:
        result = result.assign(evidence_class=EVIDENCE_HISTORICAL)
    return result


# -- quarantine manifest (ACADEMIC_STUDY_UNIFICATION_DESIGN.md "Evidence Quarantine") ---------
def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _committed_bytes(path: str, root: str) -> bytes:
    """Canonical bytes of ``path``: the blob stored in git (``git cat-file blob :<path>``) when the
    file is tracked, else the bytes on disk (with a logged warning: no git, not a repository, or
    untracked). A working copy with ``core.autocrlf`` line-ending conversion therefore cannot
    change the manifest (the CRLF/LF mismatch of 2026-10-14). ``.gitattributes`` marks the
    quarantine folders ``-text`` so a checkout writes those same bytes. The spec is ``./``-relative
    to ``root``, so a ``root`` below the repository top level is handled too. Shared helper:
    ``academic_benchmark.committed_bytes``."""
    from academic_benchmark.committed_bytes import committed_bytes

    rel = os.path.relpath(path, root).replace(os.sep, "/")
    return committed_bytes(path, git_cwd=root, index_spec=f"./{rel}")


def _manifest_files(legacy_dir: str) -> List[str]:
    skip = {QUARANTINE_MARKER_FILE, QUARANTINE_MANIFEST_FILE}
    found = []
    for base, _dirs, names in os.walk(legacy_dir):
        found.extend(os.path.join(base, n) for n in names if n not in skip)
    return sorted(found)


def build_quarantine_manifest(
    legacy_dir: str, root: str, now: Any = None, cutoff: Any = None, write: bool = True
) -> Dict[str, Any]:
    """Machine-readable manifest of every file in ``legacy_dir``: original path, archive path,
    byte size, SHA-256 and evidence class (HISTORICAL_UNVERIFIED). Paths are relative to ``root``."""
    from datetime import datetime, timezone

    entries = []
    for path in _manifest_files(legacy_dir):
        archive = os.path.relpath(path, root).replace(os.sep, "/")
        original = archive.replace(f"/{LEGACY_RESULTS_DIRNAME}/", "/", 1)
        data = _committed_bytes(path, root)
        entries.append({
            "original_path": original,
            "archive_path": archive,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "evidence_class": HISTORICAL_MANIFEST_CLASS,
        })
    manifest = {
        "schema_version": 1,
        "decision": "DECISION_LOG A13",
        "evidence_class": HISTORICAL_MANIFEST_CLASS,
        "cutoff": str(cutoff or legacy_cutoff()),
        "generated_at": now or datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }
    if write:
        with open(os.path.join(legacy_dir, QUARANTINE_MANIFEST_FILE), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return manifest


def verify_quarantine_manifest(legacy_dir: str, root: str) -> List[str]:
    """Return a list of problems (empty = OK): missing files, size/SHA-256 mismatch, unlisted files."""
    with open(os.path.join(legacy_dir, QUARANTINE_MANIFEST_FILE), encoding="utf-8") as handle:
        manifest = json.load(handle)
    problems: List[str] = []
    listed = set()
    for entry in manifest.get("entries", []):
        archive = entry["archive_path"]
        listed.add(os.path.normpath(os.path.join(root, archive)))
        path = os.path.join(root, archive)
        if not os.path.isfile(path):
            problems.append(f"missing: {archive}")
        elif os.path.getsize(path) != entry["size_bytes"] or _sha256_file(path) != entry["sha256"]:
            problems.append(f"sha256 mismatch: {archive}")
    for path in _manifest_files(legacy_dir):
        if os.path.normpath(path) not in listed:
            problems.append(f"unlisted: {os.path.relpath(path, root).replace(os.sep, '/')}")
    return problems
