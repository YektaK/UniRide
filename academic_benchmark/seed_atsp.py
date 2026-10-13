"""Seed the 19 TSPLIB95 ATSP instances into the unified SQLite DB.

Generalises ``seed_ft53.py``.  The instance list, checksums, optima and
provenance live in ``tsplib_data/atsp/MANIFEST.json`` (ft53 points at the
pre-existing ``tsplib_data/ft53.atsp``).  Each file's SHA-256 is verified
before anything is written.  Idempotent; never touches non-listed rows.

Usage:
    python -m academic_benchmark.seed_atsp --db /path/to.db [--dry-run] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Dict, Iterable, List, Optional

from academic_benchmark.tsplib_manager import (
    DB_PATH, get_db, init_db, load_routing_problem, store_academic_text,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "tsplib_data", "atsp", "MANIFEST.json")


def load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _read_verified(entry: dict) -> str:
    path = os.path.join(REPO_ROOT, entry["artifact_path"])
    if not os.path.isfile(path):
        raise ValueError(f"{entry['name']}: file not found at {path}")
    with open(path, "rb") as fh:
        data = fh.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry["sha256"]:
        raise ValueError(
            f"{entry['name']}: SHA-256 mismatch: expected {entry['sha256']}, got {digest}")
    return data.decode("utf-8")


def seed_atsp(*, db_path: str = DB_PATH, force: bool = False, dry_run: bool = False,
              names: Optional[Iterable[str]] = None) -> Dict[str, List[str]]:
    """Seed ATSP instances; returns {"stored": [...], "skipped": [...]}."""
    entries = load_manifest()["instances"]
    if names is not None:
        wanted = set(names)
        unknown = wanted - {e["name"] for e in entries}
        if unknown:
            raise ValueError(f"unknown instance(s): {sorted(unknown)}")
        entries = [e for e in entries if e["name"] in wanted]

    # Verify every file first so a bad file aborts before any write.
    texts = {e["name"]: _read_verified(e) for e in entries}

    stored: List[str] = []
    skipped: List[str] = []
    for e in entries:
        name = e["name"]
        if dry_run:
            exists = os.path.exists(db_path) and load_routing_problem(name, db_path=db_path) is not None
            (skipped if exists and not force else stored).append(name)
            continue
        if not force and load_routing_problem(name, db_path=db_path) is not None:
            skipped.append(name)
            continue
        store_academic_text(texts[name], "atsp", name=name, db_path=db_path,
                            source_file="seed_atsp")
        conn = get_db(db_path)
        try:
            init_db(conn)
            conn.execute("UPDATE problems SET optimal=? WHERE name=?", (e["optimal"], name))
            conn.commit()
        finally:
            conn.close()
        stored.append(name)
    return {"stored": stored, "skipped": skipped}


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Seed TSPLIB95 ATSP instances into a SQLite DB.")
    p.add_argument("--db", "--db-path", dest="db", default=DB_PATH,
                   help=f"Target SQLite DB (default: {DB_PATH})")
    p.add_argument("--dry-run", action="store_true", help="Verify files and report; write nothing")
    p.add_argument("--force", action="store_true", help="Re-insert even if present")
    p.add_argument("--only", help="Comma-separated instance names")
    a = p.parse_args(argv)
    try:
        res = seed_atsp(db_path=a.db, force=a.force, dry_run=a.dry_run,
                        names=a.only.split(",") if a.only else None)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    tag = "would store" if a.dry_run else "stored"
    if res["stored"]:
        print(f"{tag} ({len(res['stored'])}): {', '.join(res['stored'])}")
    if res["skipped"]:
        print(f"skipped (already present, {len(res['skipped'])}): {', '.join(res['skipped'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
