#!/usr/bin/env python3
"""Losslessly convert cached TSPLIB matrices (distance_matrices) from v1 to v2.

v1 = zlib full matrix; v2 = lzma strict upper triangle (symmetric, zero-diagonal only).
Asymmetric or otherwise ineligible matrices stay v1. Every conversion is verified
(decode v2 == original, byte-exact, SHA-256 compared) before the row is replaced.
Idempotent and resumable: rows already at v2 are skipped.

    python academic_benchmark/tools/compress_tsplib_matrices.py --db <tsplib.db> [--dry-run]
"""
import argparse
import hashlib
import os
import shutil
import sqlite3
import sys
from collections import defaultdict

import numpy as np

_AB = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AB not in sys.path:
    sys.path.insert(0, _AB)

from tsplib_matrix_codec import V1, V2, decode_matrix, encode_matrix  # noqa: E402


def _check_backup(db_path: str, backup_path: str) -> None:
    if os.path.exists(backup_path):
        print(f"backup already exists, keeping it: {backup_path}")
        return
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    need = int(os.path.getsize(db_path) * 1.5)
    free = shutil.disk_usage(os.path.dirname(backup_path)).free
    if free < need:
        raise SystemExit(f"Not enough disk space for backup: need {need} B, free {free} B")
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    shutil.copy2(db_path, backup_path)
    if os.path.getsize(backup_path) != os.path.getsize(db_path):
        raise SystemExit("Backup size mismatch; aborting")
    print(f"backup written: {backup_path}")


def convert(db_path, dry_run=False, vacuum=True, backup_path=None, verbose=False):
    """Convert v1 rows to v2. Returns counters and a per-type size table."""
    if backup_path and not dry_run:
        _check_backup(db_path, backup_path)
    conn = sqlite3.connect(db_path, timeout=60)
    conn.row_factory = sqlite3.Row
    todo = conn.execute(
        "SELECT problem_name FROM distance_matrices WHERE version IS NULL OR version < 2 "
        "ORDER BY shape_n"
    ).fetchall()
    per_type = defaultdict(lambda: {"count": 0, "before": 0, "after": 0, "kept_v1": 0})
    res = {"converted": 0, "kept_v1": 0, "per_type": per_type}
    for (name,) in todo:
        row = conn.execute(
            "SELECT matrix_blob, shape_n, dtype, edge_weight_type, version "
            "FROM distance_matrices WHERE problem_name=?", (name,)
        ).fetchone()
        n, dtype, ewt = row["shape_n"], row["dtype"] or "int32", row["edge_weight_type"]
        before = len(row["matrix_blob"])
        dm = decode_matrix(row["matrix_blob"], n, dtype, V1)
        digest = hashlib.sha256(dm.tobytes()).hexdigest()
        blob, version = encode_matrix(dm)
        t = per_type[ewt]
        t["count"] += 1
        t["before"] += before
        if version != V2:
            t["after"] += before
            t["kept_v1"] += 1
            res["kept_v1"] += 1
            continue
        back = decode_matrix(blob, n, dtype, V2)
        if not np.array_equal(back, dm) or hashlib.sha256(back.tobytes()).hexdigest() != digest:
            raise RuntimeError(f"verification failed for {name}; nothing written for it")
        t["after"] += len(blob)
        res["converted"] += 1
        if not dry_run:
            with conn:
                conn.execute(
                    "UPDATE distance_matrices SET matrix_blob=?, version=2 WHERE problem_name=?",
                    (blob, name),
                )
        if verbose:
            print(f"{name}: {before} -> {len(blob)} B", flush=True)
        del dm, back
    if vacuum and not dry_run and res["converted"]:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
    conn.close()
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup", default=None, help="backup file path (default: <repo>/.temp/backup/tsplib.db.bak)")
    ap.add_argument("--no-vacuum", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    db = os.path.abspath(a.db)
    backup = a.backup or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(db))), ".temp", "backup", "tsplib.db.bak")
    size0 = os.path.getsize(db)
    res = convert(db, a.dry_run, not a.no_vacuum, backup, a.verbose)
    print(f"{'type':10} {'count':>6} {'kept_v1':>8} {'before MB':>10} {'after MB':>10}")
    for k, v in sorted(res["per_type"].items()):
        print(f"{k:10} {v['count']:6d} {v['kept_v1']:8d} {v['before']/1e6:10.1f} {v['after']/1e6:10.1f}")
    size1 = os.path.getsize(db)
    print(f"converted={res['converted']} kept_v1={res['kept_v1']}")
    print(f"file size: {size0/1e6:.1f} MB -> {size1/1e6:.1f} MB" + (" (dry run, unchanged)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
