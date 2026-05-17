# TSPLIB SQLITE DATABASE — COMPLETE AGENT IMPLEMENTATION GUIDE
# FILE VERSION: 1.0 — Contains Part 1 (context) + Part 2 (code) + Part 3 (engine changes)
# ============================================================
# READ THIS ENTIRE FILE BEFORE TOUCHING ANY CODE.
# This guide is self-contained. You do NOT need to read any other file to implement this.

## WHY THIS WORK IS NEEDED (THE PROBLEM)

When `master_numba_engine.py` or `master_sota_engine.py` starts, it displays
"Loading TSP problems..." and hangs for 30-120 seconds. This happens because:

1. It opens `academic_benchmark/tsplib_problems/ALL_tsp.tar.gz` (a 2 MB archive
   containing 111 compressed `.tsp.gz` files) and decompresses + parses EVERY file
   from scratch on EVERY run.

2. During benchmarking, `create_np_distance_matrix(coordinates)` builds an n×n
   NumPy matrix from scratch for EVERY algorithm run, EVERY time. For pr1002
   (n=1002), this is a 1002×1002 matrix = 1,004,004 distance calculations, taking
   ~1.5 seconds per run. If you run 5 algorithms × 10 runs each, that's 75 seconds
   wasted just building matrices.

3. The distance matrix NEVER CHANGES for a given problem. It is 100% deterministic.

## THE SOLUTION

1. Create a SQLite database at `academic_benchmark/tsplib_data/tsplib.db` that stores:
   - All problem metadata (name, dimension, optimal tour length, edge weight type)
   - All node coordinates
   - Pre-computed distance matrices (compressed binary blobs)
   - Known optimal tours

2. Create `academic_benchmark/tsplib_manager.py` — a standalone CLI tool that:
   - Extracts all problems from the tar.gz into the database (run once)
   - Pre-computes all distance matrices and saves them (run once)

3. Modify `master_numba_engine.py` and `master_sota_engine.py` to:
   - Load problems from the SQLite DB instead of streaming the tar.gz
   - Load cached distance matrices instead of computing them

## CRITICAL FACTS ABOUT THE CODEBASE

### File locations (all paths relative to project root `FirebaseUniRide/UniRide/`):
- `academic_benchmark/tsplib_problems/ALL_tsp.tar.gz` — the archive (READ ONLY, do not delete)
- `academic_benchmark/tsplib_data/` — folder with 37 manually extracted `.tsp` files
- `academic_benchmark/tsplib_data/tsplib.db` — THE DATABASE YOU WILL CREATE (does not exist yet)
- `academic_benchmark/tsplib_manager.py` — THE SCRIPT YOU WILL CREATE (does not exist yet)
- `academic_benchmark/master_numba_engine.py` — modify this
- `academic_benchmark/master_sota_engine.py` — modify this
- `academic_benchmark/benchmark_db/` — folder with runtime metadata (DO NOT TOUCH)
- `optimizer_api/utils/tsplib_parser.py` — HAS DISTANCE FORMULAS (import from here, do not rewrite)

### The archive structure (IMPORTANT):
The tar.gz contains files named like `berlin52.tsp.gz` (gzip inside tar).
Each `.tsp.gz` must be decompressed with `gzip.decompress()` to get text.
There are also `.opt.tour.gz` files (optimal tour sequences) — we want those too.

### Edge Weight Types found in the archive:
- `EUC_2D` — 78 problems — standard Euclidean with NINT rounding
- `GEO` — 10 problems — great-circle distance (burma14, ulysses16, ulysses22, gr96, gr137, gr202, gr229, gr431, gr666, ali535)
- `EXPLICIT` — 17 problems — weight matrix in file, NO coordinates, SKIP THESE
- `CEIL_2D` — 4 problems — ceiling of Euclidean (dsj1000, pla7397, pla33810, pla85900)
- `ATT` — 2 problems — pseudo-Euclidean (att48, att532)

### The distance functions (from `optimizer_api/utils/tsplib_parser.py`):
```python
# This file already has: tsplib_euc_2d_distance, tsplib_ceil_2d_distance,
# tsplib_att_distance, tsplib_geo_distance, tsplib_distance_by_type
# IMPORT AND REUSE — do not rewrite these formulas
from optimizer_api.utils.tsplib_parser import tsplib_distance_by_type
```

### Known optimal tour lengths (hardcoded dict — same as in benchmark_utils.py):
These are already in `academic_benchmark/benchmark_utils.py` as `TSPLIB_OPTIMALS`.
Do NOT rewrite this dict. Import it:
```python
from benchmark_utils import TSPLIB_OPTIMALS
# or
from academic_benchmark.benchmark_utils import TSPLIB_OPTIMALS
```

## DATABASE SCHEMA — EXACT SQL

Create the database with EXACTLY these 4 tables:

```sql
CREATE TABLE IF NOT EXISTS problems (
    name              TEXT PRIMARY KEY,
    dimension         INTEGER NOT NULL,
    optimal           INTEGER,
    category          TEXT,
    edge_weight_type  TEXT NOT NULL DEFAULT 'EUC_2D',
    problem_type      TEXT DEFAULT 'TSP',
    source            TEXT DEFAULT 'tsplib',
    coords_hash       TEXT,
    tsp_file          TEXT,
    extracted_at      TEXT
);

CREATE TABLE IF NOT EXISTS coordinates (
    problem_name  TEXT NOT NULL,
    node_idx      INTEGER NOT NULL,
    x             REAL NOT NULL,
    y             REAL NOT NULL,
    PRIMARY KEY (problem_name, node_idx),
    FOREIGN KEY (problem_name) REFERENCES problems(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS distance_matrices (
    problem_name      TEXT PRIMARY KEY,
    matrix_blob       BLOB NOT NULL,
    dtype             TEXT NOT NULL DEFAULT 'int32',
    shape_n           INTEGER NOT NULL,
    edge_weight_type  TEXT NOT NULL,
    computed_at       TEXT NOT NULL,
    version           INTEGER DEFAULT 1,
    FOREIGN KEY (problem_name) REFERENCES problems(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS opt_tours (
    problem_name  TEXT PRIMARY KEY,
    tour_nodes    TEXT NOT NULL,
    tour_length   REAL,
    source        TEXT,
    added_at      TEXT NOT NULL,
    FOREIGN KEY (problem_name) REFERENCES problems(name) ON DELETE CASCADE
);
```

Enable WAL mode and foreign keys at connection time:
```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
conn.commit()
```

## HOW TO STORE AND RETRIEVE A DISTANCE MATRIX

### Storing (numpy array → SQLite BLOB):
```python
import numpy as np
import zlib

dm = np.array(...)  # shape (n, n), dtype int32
flat_bytes = dm.astype(np.int32).tobytes()       # convert to raw bytes
compressed = zlib.compress(flat_bytes, level=6)  # compress to save space
# store compressed as BLOB
cursor.execute(
    "INSERT OR REPLACE INTO distance_matrices VALUES (?,?,?,?,?,?,?)",
    (problem_name, compressed, 'int32', n, edge_weight_type, datetime.now().isoformat(), 1)
)
```

### Retrieving (SQLite BLOB → numpy array):
```python
import numpy as np
import zlib

row = cursor.execute(
    "SELECT matrix_blob, shape_n FROM distance_matrices WHERE problem_name=?",
    (problem_name,)
).fetchone()
if row is None:
    return None
blob, n = row
flat_bytes = zlib.decompress(blob)
dm = np.frombuffer(flat_bytes, dtype=np.int32).reshape(n, n).copy()
return dm
```

## HOW TO BUILD A DISTANCE MATRIX FROM COORDINATES

```python
import sys, os
# Add project root to sys.path so we can import optimizer_api
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from optimizer_api.utils.tsplib_parser import tsplib_distance_by_type
import numpy as np

def build_distance_matrix(coords, ewt):
    """
    coords: list of (x, y) tuples, 0-indexed
    ewt: string like 'EUC_2D', 'ATT', 'GEO', 'CEIL_2D'
    returns: numpy int32 array of shape (n, n)
    """
    n = len(coords)
    dm = np.zeros((n, n), dtype=np.int32)
    for i in range(n):
        for j in range(i + 1, n):
            d = tsplib_distance_by_type(ewt, coords[i], coords[j])
            dm[i, j] = d
            dm[j, i] = d
    return dm
```

## HOW TO PARSE A .TSP FILE TEXT

Use this function. It handles CRLF line endings and finds the NODE_COORD_SECTION:

```python
import re

def parse_tsp_text(content, name_hint=""):
    """
    Parse TSPLIB file text. Returns dict or None if unsupported.
    Skips EXPLICIT type (no coordinates).
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Find coordinates section
    coord_match = re.search(
        r"NODE_COORD_SECTION\s*\n(.*?)(?:\n(?:EOF|DISPLAY_DATA_SECTION)|\Z)",
        content, re.DOTALL | re.IGNORECASE
    )
    if not coord_match:
        return None  # EXPLICIT type or unsupported — skip

    header = content[:coord_match.start()]

    dim_m = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", header, re.IGNORECASE)
    ewt_m = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    name_m = re.findall(r"^NAME\s*[:\s]\s*(\S+)", header, re.IGNORECASE | re.MULTILINE)
    type_m = re.search(r"TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)

    if not dim_m:
        return None

    raw_name = name_m[-1] if name_m else name_hint
    name = raw_name.lower().strip()
    for suffix in (".opt.tour", ".opt", ".tsp"):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    name = name.split("/")[-1].split("\\")[-1]
    if not name:
        name = name_hint.lower().replace(".tsp", "").split("/")[-1].split("\\")[-1]

    dimension = int(dim_m.group(1))
    ewt = ewt_m.group(1).upper() if ewt_m else "EUC_2D"
    problem_type = type_m.group(1).upper() if type_m else "TSP"

    # We only support these types (EXPLICIT has no coords)
    supported = ("EUC_2D", "EUC_3D", "CEIL_2D", "ATT", "GEO", "GEOM", "NEU_2D")
    if ewt not in supported:
        return None

    coords = []
    for line in coord_match.group(1).strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                coords.append((float(parts[1]), float(parts[2])))
            except ValueError:
                pass

    if not coords:
        return None

    return {
        "name": name,
        "dimension": dimension,
        "edge_weight_type": ewt,
        "problem_type": problem_type,
        "coordinates": coords,
    }
```

## HOW TO PARSE A .OPT.TOUR FILE TEXT

```python
def parse_opt_tour_text(content):
    """
    Parse TSPLIB .opt.tour file. Returns list of 1-based node indices or None.
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    tour_match = re.search(
        r"TOUR_SECTION\s*\n(.*?)(?:\n-1|\nEOF|\Z)",
        content, re.DOTALL | re.IGNORECASE
    )
    if not tour_match:
        return None
    nodes = []
    for tok in tour_match.group(1).split():
        try:
            v = int(tok)
            if v == -1:
                break
            nodes.append(v)
        except ValueError:
            pass
    return nodes if nodes else None
```

## HOW TO READ THE TAR.GZ ARCHIVE

```python
import tarfile, gzip

def iter_archive(archive_path):
    """
    Yields (raw_name, content_text, is_opt_tour) for each .tsp.gz and .opt.tour.gz
    in the archive.
    raw_name is the basename without extensions, e.g. 'berlin52'
    """
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            fname = member.name.lower()
            if fname.endswith(".tsp.gz"):
                raw_name = os.path.basename(fname).replace(".tsp.gz", "")
                fobj = tar.extractfile(member)
                if fobj is None:
                    continue
                try:
                    text = gzip.decompress(fobj.read()).decode("latin-1")
                    yield raw_name, text, False
                except Exception:
                    continue
            elif fname.endswith(".opt.tour.gz"):
                raw_name = os.path.basename(fname).replace(".opt.tour.gz", "")
                fobj = tar.extractfile(member)
                if fobj is None:
                    continue
                try:
                    text = gzip.decompress(fobj.read()).decode("latin-1")
                    yield raw_name, text, True
                except Exception:
                    continue
```


---

## PART 2: CREATE academic_benchmark/tsplib_manager.py (COMPLETE FILE)

Create this file at: academic_benchmark/tsplib_manager.py
Copy EXACTLY as written below.

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tsplib_manager.py - TSPLIB SQLite Database Manager

Usage (run from project root FirebaseUniRide/UniRide/):
    python academic_benchmark/tsplib_manager.py extract
    python academic_benchmark/tsplib_manager.py compute-dm
    python academic_benchmark/tsplib_manager.py status
"""

import argparse, gzip, hashlib, json, os, re, sqlite3, struct, sys, tarfile, zlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ARCHIVE_PATH    = os.path.join(_HERE, "tsplib_problems", "ALL_tsp.tar.gz")
TSPLIB_DATA_DIR = os.path.join(_HERE, "tsplib_data")
DB_PATH         = os.path.join(TSPLIB_DATA_DIR, "tsplib.db")

try:
    from benchmark_utils import TSPLIB_OPTIMALS
except ImportError:
    from academic_benchmark.benchmark_utils import TSPLIB_OPTIMALS

try:
    from optimizer_api.utils.tsplib_parser import tsplib_distance_by_type
    _DIST_OK = True
except ImportError:
    _DIST_OK = False
    def tsplib_distance_by_type(ewt, p1, p2):
        raise RuntimeError("tsplib_distance_by_type not available")

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db(path=DB_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS problems (
            name TEXT PRIMARY KEY, dimension INTEGER NOT NULL,
            optimal INTEGER, category TEXT,
            edge_weight_type TEXT NOT NULL DEFAULT 'EUC_2D',
            problem_type TEXT DEFAULT 'TSP', source TEXT DEFAULT 'tsplib',
            coords_hash TEXT, tsp_file TEXT, extracted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS coordinates (
            problem_name TEXT NOT NULL, node_idx INTEGER NOT NULL,
            x REAL NOT NULL, y REAL NOT NULL,
            PRIMARY KEY (problem_name, node_idx),
            FOREIGN KEY (problem_name) REFERENCES problems(name) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS distance_matrices (
            problem_name TEXT PRIMARY KEY, matrix_blob BLOB NOT NULL,
            dtype TEXT NOT NULL DEFAULT 'int32', shape_n INTEGER NOT NULL,
            edge_weight_type TEXT NOT NULL, computed_at TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            FOREIGN KEY (problem_name) REFERENCES problems(name) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS opt_tours (
            problem_name TEXT PRIMARY KEY, tour_nodes TEXT NOT NULL,
            tour_length REAL, source TEXT, added_at TEXT NOT NULL,
            FOREIGN KEY (problem_name) REFERENCES problems(name) ON DELETE CASCADE
        );
    """)
    conn.commit()

# ── Public API (imported by engines) ─────────────────────────────────────────

def get_distance_matrix(problem_name: str, db_path: str = DB_PATH):
    """Load cached n x n int32 matrix. Returns None on miss."""
    if not os.path.exists(db_path):
        return None
    try:
        conn = get_db(db_path)
        row = conn.execute(
            "SELECT matrix_blob, shape_n FROM distance_matrices WHERE problem_name=?",
            (problem_name,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        flat = zlib.decompress(bytes(row["matrix_blob"]))
        n = row["shape_n"]
        return np.frombuffer(flat, dtype=np.int32).reshape(n, n).copy()
    except Exception:
        return None


def get_all_problems(db_path: str = DB_PATH, max_dim: int = 0, exclude_explicit: bool = True):
    """
    Return list of dicts with keys:
      name, dimension, optimal, category, edge_weight_type, coordinates
    coordinates is a list of (x, y) tuples.
    Returns [] if DB does not exist.
    """
    if not os.path.exists(db_path):
        return []
    try:
        conn = get_db(db_path)
        where = "WHERE 1=1"
        params = []
        if max_dim > 0:
            where += " AND p.dimension <= ?"
            params.append(max_dim)
        if exclude_explicit:
            where += " AND p.edge_weight_type != 'EXPLICIT'"
        sql = (f"SELECT p.name, p.dimension, p.optimal, p.category, p.edge_weight_type "
               f"FROM problems p {where} ORDER BY p.dimension")
        rows = conn.execute(sql, params).fetchall()
        out = []
        for row in rows:
            name = row["name"]
            crows = conn.execute(
                "SELECT x, y FROM coordinates WHERE problem_name=? ORDER BY node_idx",
                (name,)
            ).fetchall()
            out.append({
                "name": name, "dimension": row["dimension"], "optimal": row["optimal"],
                "category": row["category"], "edge_weight_type": row["edge_weight_type"],
                "coordinates": [(r["x"], r["y"]) for r in crows],
            })
        conn.close()
        return out
    except Exception as e:
        print(f"[WARN] get_all_problems: {e}", flush=True)
        return []


def is_db_populated(db_path: str = DB_PATH) -> bool:
    """Returns True if DB exists and has at least 10 problems."""
    if not os.path.exists(db_path):
        return False
    try:
        conn = get_db(db_path)
        count = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        conn.close()
        return count >= 10
    except Exception:
        return False

# ── Parsing helpers ───────────────────────────────────────────────────────────

def _parse_tsp_text(content: str, name_hint: str = ""):
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(
        r"NODE_COORD_SECTION\s*\n(.*?)(?:\n(?:EOF|DISPLAY_DATA_SECTION)|\Z)",
        content, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return None  # EXPLICIT type - skip
    header = content[:m.start()]
    dm = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", header, re.IGNORECASE)
    em = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    nm = re.findall(r"^NAME\s*[:\s]\s*(\S+)", header, re.IGNORECASE | re.MULTILINE)
    tm = re.search(r"TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    if not dm:
        return None
    raw = (nm[-1] if nm else name_hint).lower().strip()
    for sfx in (".opt.tour", ".opt", ".tsp"):
        if raw.endswith(sfx):
            raw = raw[:-len(sfx)]
    name = raw.split("/")[-1].split("\\")[-1]
    if not name:
        name = name_hint.lower().replace(".tsp", "").split("/")[-1].split("\\")[-1]
    if not name:
        return None
    ewt = em.group(1).upper() if em else "EUC_2D"
    supported = ("EUC_2D", "EUC_3D", "CEIL_2D", "ATT", "GEO", "GEOM", "NEU_2D")
    if ewt not in supported:
        return None
    coords = []
    for line in m.group(1).strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                coords.append((float(parts[1]), float(parts[2])))
            except ValueError:
                pass
    if not coords:
        return None
    return {
        "name": name, "dimension": int(dm.group(1)),
        "edge_weight_type": ewt,
        "problem_type": tm.group(1).upper() if tm else "TSP",
        "coordinates": coords,
    }


def _parse_opt_tour_text(content: str):
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(r"TOUR_SECTION\s*\n(.*?)(?:\n-1|\nEOF|\Z)", content, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    nodes = []
    for tok in m.group(1).split():
        try:
            v = int(tok)
            if v == -1:
                break
            nodes.append(v)
        except ValueError:
            pass
    return nodes if nodes else None


def _category(n: int) -> str:
    return "small" if n <= 100 else ("medium" if n <= 500 else "large")


def _coords_hash(coords) -> str:
    raw = b"".join(struct.pack("dd", x, y) for x, y in coords)
    return hashlib.sha256(raw).hexdigest()


def _build_matrix(coords, ewt: str):
    n = len(coords)
    dm = np.zeros((n, n), dtype=np.int32)
    for i in range(n):
        for j in range(i + 1, n):
            d = tsplib_distance_by_type(ewt, coords[i], coords[j])
            dm[i, j] = d
            dm[j, i] = d
    return dm


def _store_matrix(conn, name: str, dm, ewt: str):
    blob = zlib.compress(dm.astype(np.int32).tobytes(), level=6)
    conn.execute(
        "INSERT OR REPLACE INTO distance_matrices "
        "(problem_name, matrix_blob, dtype, shape_n, edge_weight_type, computed_at, version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, blob, "int32", dm.shape[0], ewt, datetime.now().isoformat(), 1)
    )

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_extract(args):
    conn = get_db()
    init_db(conn)
    only = set(args.problems.lower().split(",")) if args.problems else set()
    inserted = skipped = 0
    pending_tours = {}

    def upsert(info, tsp_file=None):
        name = info["name"]
        if only and name not in only:
            return False
        if args.size_limit and info["dimension"] > args.size_limit:
            return False
        nhash = _coords_hash(info["coordinates"])
        ex = conn.execute("SELECT coords_hash FROM problems WHERE name=?", (name,)).fetchone()
        if ex and not args.force and ex["coords_hash"] == nhash:
            return False
        conn.execute(
            "INSERT OR REPLACE INTO problems "
            "(name, dimension, optimal, category, edge_weight_type, "
            " problem_type, source, coords_hash, tsp_file, extracted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, info["dimension"], TSPLIB_OPTIMALS.get(name),
             _category(info["dimension"]), info["edge_weight_type"],
             info["problem_type"], "tsplib", nhash,
             tsp_file, datetime.now().isoformat())
        )
        conn.execute("DELETE FROM coordinates WHERE problem_name=?", (name,))
        conn.executemany(
            "INSERT INTO coordinates (problem_name, node_idx, x, y) VALUES (?, ?, ?, ?)",
            [(name, idx, x, y) for idx, (x, y) in enumerate(info["coordinates"])]
        )
        return True

    # Source 1: ALL_tsp.tar.gz
    if os.path.exists(ARCHIVE_PATH):
        print(f"[EXTRACT] Reading {ARCHIVE_PATH} ...", flush=True)
        with tarfile.open(ARCHIVE_PATH, "r:gz") as tar:
            for member in tar.getmembers():
                fname = member.name.lower()
                fobj = tar.extractfile(member)
                if not fobj:
                    continue
                try:
                    text = gzip.decompress(fobj.read()).decode("latin-1")
                except Exception:
                    continue
                if fname.endswith(".tsp.gz"):
                    rn = os.path.basename(fname).replace(".tsp.gz", "")
                    info = _parse_tsp_text(text, rn)
                    if info and upsert(info):
                        inserted += 1
                        print(f"  +{info['name']} n={info['dimension']} {info['edge_weight_type']}", flush=True)
                    else:
                        skipped += 1
                elif fname.endswith(".opt.tour.gz"):
                    rn = os.path.basename(fname).replace(".opt.tour.gz", "")
                    tour = _parse_opt_tour_text(text)
                    if tour:
                        pending_tours[rn] = tour
        conn.commit()

    # Source 2: tsplib_data/*.tsp flat files
    if os.path.isdir(TSPLIB_DATA_DIR):
        for fname in sorted(os.listdir(TSPLIB_DATA_DIR)):
            if not fname.lower().endswith(".tsp"):
                continue
            fp = os.path.join(TSPLIB_DATA_DIR, fname)
            try:
                text = open(fp, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            rn = fname.lower().replace(".tsp", "")
            info = _parse_tsp_text(text, rn)
            if info and upsert(info, os.path.relpath(fp, TSPLIB_DATA_DIR)):
                inserted += 1
            opt_p = fp.replace(".tsp", ".opt.tour")
            if os.path.exists(opt_p) and info:
                tour = _parse_opt_tour_text(open(opt_p, encoding="utf-8", errors="replace").read())
                if tour:
                    pending_tours[info["name"]] = tour
        conn.commit()

    # Insert pending optimal tours
    for tname, tnodes in pending_tours.items():
        if not conn.execute("SELECT 1 FROM problems WHERE name=?", (tname,)).fetchone():
            continue
        conn.execute(
            "INSERT OR REPLACE INTO opt_tours (problem_name, tour_nodes, source, added_at) "
            "VALUES (?, ?, ?, ?)",
            (tname, json.dumps(tnodes), "tsplib_file", datetime.now().isoformat())
        )
    conn.commit()
    conn.close()
    print(f"[DONE] inserted={inserted} skipped={skipped} tours={len(pending_tours)}", flush=True)


def cmd_compute_dm(args):
    if not _DIST_OK:
        print("[ERROR] tsplib_distance_by_type not importable. Cannot compute matrices.")
        sys.exit(1)
    conn = get_db()
    init_db(conn)
    import time
    only = set(args.problems.lower().split(",")) if args.problems else set()
    sql = "SELECT name, dimension, edge_weight_type FROM problems WHERE edge_weight_type != 'EXPLICIT'"
    if args.size_limit:
        sql += f" AND dimension <= {args.size_limit}"
    sql += " ORDER BY dimension"
    rows = conn.execute(sql).fetchall()
    total = len(rows)
    for i, row in enumerate(rows, 1):
        name, n, ewt = row["name"], row["dimension"], row["edge_weight_type"]
        if only and name not in only:
            continue
        if not args.force:
            if conn.execute("SELECT 1 FROM distance_matrices WHERE problem_name=?", (name,)).fetchone():
                print(f"  [{i}/{total}] SKIP {name} (cached)", flush=True)
                continue
        crows = conn.execute(
            "SELECT x, y FROM coordinates WHERE problem_name=? ORDER BY node_idx", (name,)
        ).fetchall()
        if not crows:
            print(f"  [{i}/{total}] SKIP {name} (no coords)", flush=True)
            continue
        coords = [(r["x"], r["y"]) for r in crows]
        t0 = time.perf_counter()
        try:
            dm = _build_matrix(coords, ewt)
        except Exception as e:
            print(f"  [{i}/{total}] ERROR {name}: {e}", flush=True)
            continue
        _store_matrix(conn, name, dm, ewt)
        conn.commit()
        print(f"  [{i}/{total}] +{name} n={n} ewt={ewt} {time.perf_counter()-t0:.2f}s", flush=True)
    conn.close()
    print("[DONE]", flush=True)


def cmd_status(args):
    if not os.path.exists(DB_PATH):
        print("DB not found. Run: python academic_benchmark/tsplib_manager.py extract")
        return
    conn = get_db()
    np_ = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
    nm  = conn.execute("SELECT COUNT(*) FROM distance_matrices").fetchone()[0]
    nt  = conn.execute("SELECT COUNT(*) FROM opt_tours").fetchone()[0]
    miss = conn.execute(
        "SELECT COUNT(*) FROM problems p WHERE p.edge_weight_type != 'EXPLICIT' "
        "AND NOT EXISTS (SELECT 1 FROM distance_matrices d WHERE d.problem_name=p.name)"
    ).fetchone()[0]
    ewts = dict(conn.execute(
        "SELECT edge_weight_type, COUNT(*) FROM problems GROUP BY edge_weight_type"
    ).fetchall())
    conn.close()
    print("=" * 55)
    print(f"  DB:       {DB_PATH}")
    print(f"  Problems: {np_}  |  Matrices: {nm} (missing:{miss})  |  Tours: {nt}")
    print(f"  EWT:      {ewts}")
    if miss:
        print(f"  !! Run compute-dm to cache {miss} missing matrices.")
    print("=" * 55)


def main():
    p = argparse.ArgumentParser(description="TSPLIB SQLite Database Manager")
    p.add_argument("command", choices=["extract", "compute-dm", "add-tours", "status", "export"])
    p.add_argument("--force",      action="store_true", help="Re-insert even if cached")
    p.add_argument("--size-limit", type=int, default=0, metavar="N")
    p.add_argument("--problems",   type=str, default="", help="Comma-separated names")
    p.add_argument("--problem",    type=str, default="")
    args = p.parse_args()
    if   args.command == "extract":    cmd_extract(args)
    elif args.command == "compute-dm": cmd_compute_dm(args)
    elif args.command == "status":     cmd_status(args)
    else: print(f"[SKIP] {args.command} not yet implemented via this path.")

if __name__ == "__main__":
    main()
```

---

## PART 3: MODIFY master_numba_engine.py

### 3A — Add import block AFTER line containing `from optimizer_api.utils.local_search_numba import LocalSearchType`

Insert these lines immediately after that import:

```python
# --- DB cache integration ---
try:
    from tsplib_manager import (
        get_distance_matrix as _dm_from_cache,
        get_all_problems    as _problems_from_db,
        is_db_populated     as _db_ready,
    )
except ImportError:
    try:
        from academic_benchmark.tsplib_manager import (
            get_distance_matrix as _dm_from_cache,
            get_all_problems    as _problems_from_db,
            is_db_populated     as _db_ready,
        )
    except ImportError:
        _dm_from_cache   = lambda name, **kw: None
        _problems_from_db = lambda **kw: []
        _db_ready        = lambda **kw: False

TSPLIB_DB = os.path.join(_ENGINE_DIR, "tsplib_data", "tsplib.db")
```

### 3B — Modify load_problems() in master_numba_engine.py

The function signature is: `def load_problems(size_limit: int = 0) -> List[DOEProblem]:`

Insert this block as the FIRST lines inside the function body (before `problems: Dict[str, DOEProblem] = {}`):

```python
    # --- DB fast path ---
    if _db_ready(TSPLIB_DB):
        rows = _problems_from_db(db_path=TSPLIB_DB,
                                 max_dim=size_limit if size_limit > 0 else 99999)
        if rows:
            out = []
            for r in rows:
                dim = r["dimension"]
                cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                out.append(DOEProblem(
                    name=r["name"], dimension=dim, coordinates=r["coordinates"],
                    optimal=r["optimal"], category=cat, source="tsplib"
                ))
            # Append time_matrix JSON problems (existing logic)
            data_dir = os.path.join(_ENGINE_DIR, "data")
            if os.path.exists(data_dir):
                for f in os.listdir(data_dir):
                    if f.endswith(".json") and f != "tuned_parameters_db.json":
                        try:
                            with open(os.path.join(data_dir, f), encoding="utf-8") as fh:
                                data = json.load(fh)
                            if "time_matrix" in data:
                                matrix = data["time_matrix"]
                                name = data.get("name", f.replace(".json", ""))
                                dim = len(matrix)
                                cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                                out.append(DOEProblem(
                                    name=name, dimension=dim,
                                    coordinates=[(0.0, 0.0)] * dim,
                                    optimal=data.get("optimal"), category=cat,
                                    source="time_matrix", is_time_matrix=True,
                                    time_matrix=matrix
                                ))
                        except Exception:
                            continue
            return sorted(out, key=lambda p: p.dimension)
    # --- END DB fast path: fall through to tar.gz logic below ---
```

### 3C — Fix the matrix call inside _run_bildiri_solver()

Find this line in master_numba_engine.py (inside function `_run_bildiri_solver`, around line 673):
```python
        np_dm = create_np_distance_matrix(coords)
```

Replace ONLY that line with:
```python
        np_dm = _dm_from_cache(problem_dict.get("name", ""), db_path=TSPLIB_DB)
        if np_dm is None:
            np_dm = create_np_distance_matrix(coords)
```

---

## PART 4: MODIFY master_sota_engine.py

### 4A — Add import block AFTER the line `VERSION = "2.0.0"` (around line 124)

Insert the SAME block as Part 3A, plus:
```python
TSPLIB_DB = os.path.join(_ENGINE_DIR, "tsplib_data", "tsplib.db")
```

### 4B — Modify load_problems() in master_sota_engine.py

The function signature is: `def load_problems(size_limit: int = 500) -> List[TSPProblem]:`

Insert this block as the FIRST lines inside the function body (before `problems: Dict[str, TSPProblem] = {}`):

```python
    # --- DB fast path ---
    if _db_ready(TSPLIB_DB):
        rows = _problems_from_db(db_path=TSPLIB_DB,
                                 max_dim=size_limit if size_limit > 0 else 99999)
        if rows:
            return sorted([
                TSPProblem(
                    name=r["name"], dimension=r["dimension"],
                    coordinates=r["coordinates"], optimal=r["optimal"],
                    category=r["category"]
                )
                for r in rows
            ], key=lambda p: p.dimension)
    # --- END DB fast path ---
```

---

## PART 5: HOW TO RUN (from project root FirebaseUniRide/UniRide/)

```bash
# Step 1 — Populate DB from archive (one-time, ~30 seconds):
python academic_benchmark/tsplib_manager.py extract

# Step 2 — Pre-compute ALL distance matrices (one-time, ~5-15 minutes):
python academic_benchmark/tsplib_manager.py compute-dm

# Step 3 — Verify:
python academic_benchmark/tsplib_manager.py status

# Quick test:
python -c "
import sys; sys.path.insert(0, '.')
from academic_benchmark.tsplib_manager import get_distance_matrix, get_all_problems
dm = get_distance_matrix('berlin52')
print('berlin52 matrix shape:', dm.shape if dm is not None else 'NOT CACHED')
probs = get_all_problems(max_dim=100)
print('Small problems loaded:', [p['name'] for p in probs])
"
```

---

## PART 6: DO NOT TOUCH

- academic_benchmark/tsplib_problems/ALL_tsp.tar.gz  (keep as backup source)
- academic_benchmark/benchmark_utils.py
- optimizer_api/utils/tsplib_parser.py
- academic_benchmark/benchmark_db/*.json  (runtime state)
- academic_benchmark/numba_results/*.csv
- academic_benchmark/sota_results/*.csv
- The 37 .tsp files in tsplib_data/ stay as-is

---

## PART 7: COMMON ERRORS

**ImportError: No module named tsplib_manager**
-> Run from project root, NOT from inside academic_benchmark/
-> Or ensure the try/except import block in Step 3A is present

**get_all_problems returns []**
-> DB not populated yet. Run extract command first.

**Matrix comes back None from _dm_from_cache**
-> Run compute-dm command. Check status for missing count.

**RuntimeError: tsplib_distance_by_type not available**
-> Run from project root so optimizer_api is on sys.path
-> Check that optimizer_api/utils/tsplib_parser.py exists

**Wrong tour length for att48 (ATT type) or ulysses16 (GEO type)**
-> These need special distance formulas. The DB uses tsplib_distance_by_type
   which applies the correct formula per EWT. The old create_np_distance_matrix()
   always used EUC_2D and was wrong for these problems.
-> After Step 3C, the engines use cached matrices with correct formulas.

**Memory error on large problems (pr2392, n=2392)**
-> pr2392 matrix is 2392x2392 int32 = ~23 MB uncompressed, ~3 MB compressed.
-> Should be fine. If not, use --size-limit 1500 in compute-dm.
