"""Guard: mark pre-2026-10-09 ga_split_enhanced / ga_split_hf rows and files obsolete.

The benchmark-runner path keeps results in memory and does not persist to tsplib.db
(0 rows on 2026-10-09, read-only check); this guards rows copied into tsplib.db and
result files. Exports made before the fix (downloaded JSON, browser copies,
POST /import) cannot be marked automatically and must not be pooled with later results.
Directories whose run_manifest.json records "path": "/api/v1/optimize" (production
path, unaffected) are skipped. Never deletes. SQLite rows get ``obsolete`` keys merged into ``metadata_json``
(existing metadata preserved). File-based results get a sibling OBSOLETE.md.
Idempotent: already-marked rows are skipped. See DECISION_LOG A06.

``--rule legacy`` (DECISION_LOG A13, HISTORICAL_UNVERIFIED) does NOT flag any database row: the
class is rule based (timestamp before 2026-10-13), so it only COUNTS the historical
benchmark_results rows. It writes QUARANTINE.md plus a SHA-256 QUARANTINE_MANIFEST.json into each
``--files-dir`` (a ``legacy_pre_2026-10-13`` folder; production-path directories are skipped).
Nothing is edited or deleted. INVALID (A06) and HISTORICAL_UNVERIFIED (A13) are different classes.

Usage:
    python -m academic_benchmark.tools.mark_obsolete_ga_split_variant_results --db PATH [--dry-run]
        [--files-dir DIR ...] [--cutoff 2026-10-09] [--rule a06|legacy]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from academic_benchmark.obsolete_results import (
    AFFECTED_ALGORITHMS,
    OBSOLETE_CUTOFF,
    LEGACY_CUTOFF,
    LEGACY_REASON,
    QUARANTINE_MANIFEST_FILE,
    QUARANTINE_MARKER_FILE,
    build_quarantine_manifest,
    OBSOLETE_REASON,
    is_affected,
    is_legacy_timestamp,
)

_FILE_PATTERN = re.compile(r"ga[_ \-]split[_ \-](enhanced|hf)", re.IGNORECASE)
_FILE_SUFFIXES = (".csv", ".json", ".jsonl", ".md", ".txt")


def mark_sqlite(
    db_path: str,
    *,
    dry_run: bool,
    cutoff: Optional[str] = None,
    now: Optional[str] = None,
    rule: str = "a06",
) -> Dict[str, Any]:
    """Mark matching benchmark_results rows. Returns counts per algorithm/problem/run.

    ``rule="a06"`` (default): ga_split_enhanced/ga_split_hf rows before ``cutoff``.
    ``rule="legacy"``: any algorithm, rows before ``cutoff`` (default LEGACY_CUTOFF).
    """
    if rule not in ("a06", "legacy"):
        raise ValueError(f"unknown rule {rule!r}")
    legacy = rule == "legacy"
    cutoff = cutoff or (LEGACY_CUTOFF if legacy else OBSOLETE_CUTOFF)
    reason = LEGACY_REASON if legacy else OBSOLETE_REASON
    marked_at = now or datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, run_id, problem_name, algorithm, timestamp, metadata_json FROM benchmark_results"
        ).fetchall()
        by_algorithm: Counter = Counter()
        by_problem: Counter = Counter()
        by_run: Counter = Counter()
        updates: List[tuple] = []
        already = 0
        historical = 0
        for row_id, run_id, problem, algorithm, timestamp, metadata_json in rows:
            if legacy:  # A13: rule-based class, nothing is written to the row
                if is_legacy_timestamp(timestamp, cutoff):
                    historical += 1
                continue
            if not is_affected(algorithm, timestamp, cutoff):
                continue
            try:
                meta = json.loads(metadata_json) if metadata_json else {}
            except ValueError:
                meta = None
            if not isinstance(meta, dict):
                meta = {"_original_metadata_json": metadata_json} if metadata_json else {}
            if meta.get("obsolete") is True:
                already += 1
                continue
            meta.update(obsolete=True, obsolete_reason=reason, obsolete_marked_at=marked_at)
            by_algorithm[algorithm] += 1
            by_problem[problem] += 1
            by_run[run_id] += 1
            updates.append((json.dumps(meta, sort_keys=True), row_id))
        if updates and not dry_run:
            with conn:
                conn.executemany("UPDATE benchmark_results SET metadata_json=? WHERE id=?", updates)
        return {
            "to_mark": len(updates),
            "already_marked": already,
            "historical_unverified_rows": historical if legacy else None,
            "by_algorithm": dict(by_algorithm),
            "by_problem": dict(by_problem),
            "by_run": dict(by_run),
            "dry_run": dry_run,
            "rule": rule,
            "cutoff": cutoff,
        }
    finally:
        conn.close()


def _has_production_path(node: Any) -> bool:
    if isinstance(node, dict):
        return node.get("path") == "/api/v1/optimize" or any(_has_production_path(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_production_path(v) for v in node)
    return False


def _is_production_path(manifest_path: str) -> bool:
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            return _has_production_path(json.load(handle))
    except (OSError, ValueError):
        return False


def mark_files(directory: str, *, dry_run: bool, now: Optional[str] = None) -> Dict[str, Any]:
    """Write OBSOLETE.md next to result files that mention the affected algorithms."""
    marked_at = now or datetime.now(timezone.utc).isoformat()
    manifest = os.path.join(directory, "run_manifest.json")
    if os.path.isfile(manifest) and _is_production_path(manifest):
        return {"directory": directory, "files": [], "skipped": "production path /api/v1/optimize", "dry_run": dry_run}
    matches: List[str] = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if name.lower().endswith(_FILE_SUFFIXES) and name != "OBSOLETE.md" and os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                if _FILE_PATTERN.search(handle.read()):
                    matches.append(name)
    if matches and not dry_run:
        body = (
            "# OBSOLETE results\n\n"
            f"Marked at: {marked_at}\n\n"
            f"Reason: {OBSOLETE_REASON}\n\n"
            "Files (mention ga_split_enhanced / ga_split_hf; nothing was deleted):\n\n"
            + "".join(f"- {name}\n" for name in matches)
        )
        with open(os.path.join(directory, "OBSOLETE.md"), "w", encoding="utf-8") as handle:
            handle.write(body)
    return {"directory": directory, "files": matches, "dry_run": dry_run}


def mark_legacy_files(
    directory: str, *, dry_run: bool, now: Optional[str] = None, cutoff: str = LEGACY_CUTOFF
) -> Dict[str, Any]:
    """Write QUARANTINE.md and a SHA-256 manifest into a legacy folder (A13). Idempotent.

    Same production-path skip as :func:`mark_files` (A06): a directory whose run_manifest.json
    records ``/api/v1/optimize`` is untouched.
    """
    manifest = os.path.join(directory, "run_manifest.json")
    if os.path.isfile(manifest) and _is_production_path(manifest):
        return {"directory": directory, "written": False, "skipped": "production path /api/v1/optimize", "dry_run": dry_run}
    marked_at = now or datetime.now(timezone.utc).isoformat()
    path = os.path.join(directory, QUARANTINE_MARKER_FILE)
    if os.path.isfile(path):
        return {"directory": directory, "written": False, "already_marked": True, "dry_run": dry_run}
    body = (
        "# QUARANTINE: HISTORICAL_UNVERIFIED results\n\n"
        f"Cutoff: {cutoff}\n\n"
        f"Marked at: {marked_at}\n\n"
        f"Evidence class: HISTORICAL_UNVERIFIED (DECISION_LOG A13)\n\n"
        f"Reason: {LEGACY_REASON}\n\n"
        "Permitted use: provenance and engineering history, shown only in the explicitly labelled "
        "historical view (`evidence=\"historical\"` / `include_historical=true`). "
        "Never pooled with current results, never used as warm start, never cited as evidence. "
        "Nothing here is deleted. "
        f"Every file is listed with its SHA-256 in `{QUARANTINE_MANIFEST_FILE}`. "
        "New runs write to the parent folder.\n"
    )
    if not dry_run:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        build_quarantine_manifest(directory, _repo_root(directory), now=marked_at, cutoff=cutoff)
    return {"directory": directory, "written": not dry_run, "already_marked": False, "dry_run": dry_run}


def _repo_root(directory: str) -> str:
    """Nearest ancestor holding ``.git`` (file or folder); else the parent of ``directory``."""
    current = os.path.abspath(directory)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.dirname(os.path.abspath(directory))
        current = parent


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="path to tsplib.db (use a COPY for dry runs)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rule", choices=("a06", "legacy"), default="a06", help="a06 (default): ga_split_enhanced/ga_split_hf rows before the cutoff; legacy: HISTORICAL_UNVERIFIED quarantine for files, count-only for rows (A13)")
    parser.add_argument("--cutoff", default=None, help="exact ISO date or instant; rows with timestamp < it are marked (default is the fix date, so rows stamped 2026-10-09 are not auto-marked)")
    parser.add_argument("--files-dir", action="append", default=[], help="result directory to flag with OBSOLETE.md (a06) or QUARANTINE.md (legacy) (skipped when its run_manifest.json has path /api/v1/optimize, the unaffected production path)")
    args = parser.parse_args(argv)

    report = {
        "algorithms": sorted(AFFECTED_ALGORITHMS) if args.rule == "a06" else "ALL (legacy rule)",
        "sqlite": mark_sqlite(args.db, dry_run=args.dry_run, cutoff=args.cutoff, rule=args.rule),
    }
    if args.rule == "legacy":
        report["files"] = [
            mark_legacy_files(d, dry_run=args.dry_run, cutoff=args.cutoff or LEGACY_CUTOFF) for d in args.files_dir
        ]
    else:
        report["files"] = [mark_files(d, dry_run=args.dry_run) for d in args.files_dir]
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
