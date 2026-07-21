"""Seed one real ATSP benchmark instance (ft53) into the unified SQLite DB.

This makes a genuinely asymmetric TSPLIB ATSP problem available through
``load_problems()`` without downloading anything at runtime — the raw
``.atsp`` file ships in ``tsplib_data/``.

Provenance
----------
- Authoritative URL (single-instance gzip):
    https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ft53.atsp.gz
- Mirror used during initial acquisition (Heidelberg was offline):
    https://raw.githubusercontent.com/pdrozdowski/TSPLib.Net/master/TSPLIB95/atsp/ft53.atsp
- Verification / retrieval date: 2026-07-20
- Decompressed SHA-256: 692ae545e226d88aa095e3e726c8a1dadf4ecc9b97852d0cdbb2ca2a98dd2634
- Canonical optimum (Heidelberg ATSP table): 6905
- TSPLIB metadata: TYPE=ATSP, DIMENSION=53, EDGE_WEIGHT_TYPE=EXPLICIT,
  EDGE_WEIGHT_FORMAT=FULL_MATRIX
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from typing import Dict, List

from academic_benchmark.tsplib_manager import (
    DB_PATH, get_db, init_db, load_routing_problem, store_academic_text,
)
from uniride_core.algorithms.tsplib_parser import TSPLIB_OPTIMALS

# ── Provenance constants ─────────────────────────────────────────────────────

FT53_AUTHORITY_URL = "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ft53.atsp.gz"
FT53_MIRROR_URL = "https://raw.githubusercontent.com/pdrozdowski/TSPLib.Net/master/TSPLIB95/atsp/ft53.atsp"
FT53_RETRIEVAL_DATE = "2026-07-20"
FT53_SHA256 = "692ae545e226d88aa095e3e726c8a1dadf4ecc9b97852d0cdbb2ca2a98dd2634"
FT53_OPTIMAL = 6905
FT53_DIMENSION = 53
FT53_PROBLEM_TYPE = "ATSP"
FT53_EDGE_WEIGHT_TYPE = "EXPLICIT"

FT53_ATSP_PATH = os.path.join(
    os.path.dirname(__file__), "tsplib_data", "ft53.atsp"
)

FT53_RAW_TEXT: str | None = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_ft53_text() -> str:
    global FT53_RAW_TEXT
    if FT53_RAW_TEXT is None:
        with open(FT53_ATSP_PATH, encoding="utf-8") as fh:
            FT53_RAW_TEXT = fh.read()
    return FT53_RAW_TEXT


def _verify_file_integrity() -> None:
    """Raise ValueError if the shipped .atsp file is missing or corrupt."""
    if not os.path.isfile(FT53_ATSP_PATH):
        raise ValueError(f"ft53.atsp not found at {FT53_ATSP_PATH}")
    with open(FT53_ATSP_PATH, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    if digest != FT53_SHA256:
        raise ValueError(
            f"SHA-256 mismatch: expected {FT53_SHA256}, got {digest}"
        )


# ── Public API ────────────────────────────────────────────────────────────────

def seed_ft53(*, db_path: str = DB_PATH, force: bool = False) -> Dict[str, List[str]]:
    """Seed the ft53 ATSP instance into the DB if not already present.

    Idempotent: calling twice with the same ``db_path`` skips on the second
    call (unless *force* is True).
    """
    stored: List[str] = []
    skipped: List[str] = []
    name = "ft53"

    _verify_file_integrity()

    if not force and load_routing_problem(name, db_path=db_path) is not None:
        skipped.append(name)
        return {"stored": stored, "skipped": skipped}

    text = _load_ft53_text()
    store_academic_text(text, "atsp", name=name, db_path=db_path, source_file="seed_ft53")

    optimal = TSPLIB_OPTIMALS.get(name)
    if optimal is not None:
        conn = get_db(db_path)
        init_db(conn)
        conn.execute("UPDATE problems SET optimal=? WHERE name=?", (optimal, name))
        conn.commit()
        conn.close()

    stored.append(name)
    return {"stored": stored, "skipped": skipped}


# ── CLI entry point ───────────────────────────────────────────────────────────

def main(argv: List[str] | None = None) -> int:
    """CLI entry point.  Returns 0 on success, 1 on failure."""
    parser = argparse.ArgumentParser(
        description="Seed the ft53 ATSP benchmark instance into a SQLite DB.",
    )
    parser.add_argument(
        "--db-path", default=DB_PATH,
        help=f"Target SQLite database path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-insert even if ft53 already exists",
    )
    args = parser.parse_args(argv)

    try:
        result = seed_ft53(db_path=args.db_path, force=args.force)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if result["stored"]:
        print(f"stored: {', '.join(result['stored'])}")
    if result["skipped"]:
        print(f"skipped (already present): {', '.join(result['skipped'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
