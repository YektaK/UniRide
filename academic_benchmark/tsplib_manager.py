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
        CREATE TABLE IF NOT EXISTS best_solutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_name TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            params_json TEXT NOT NULL,
            tour_nodes TEXT NOT NULL,
            tour_length REAL,
            gap REAL,
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_best_solutions_algo
            ON best_solutions(problem_name, algorithm);
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
    ATSP problems return empty coordinates list (no coordinates available).
    Returns [] if DB does not exist.
    """
    if not os.path.exists(db_path):
        return []
    try:
        conn = get_db(db_path)
        where = ["1=1"]
        params = []
        if max_dim > 0:
            where.append("p.dimension <= ?")
            params.append(max_dim)
        if exclude_explicit:
            where.append("(p.edge_weight_type != 'EXPLICIT' OR p.problem_type = 'ATSP')")
        sql = ("SELECT p.name, p.dimension, p.optimal, p.category, p.edge_weight_type, p.problem_type "
               f"FROM problems p WHERE {' AND '.join(where)} ORDER BY p.dimension")
        rows = conn.execute(sql, params).fetchall()
        out = []
        for row in rows:
            name = row["name"]
            ptype = row["problem_type"] or "TSP"
            coords = []
            if ptype != "ATSP":
                crows = conn.execute(
                    "SELECT x, y FROM coordinates WHERE problem_name=? ORDER BY node_idx",
                    (name,)
                ).fetchall()
                coords = [(r["x"], r["y"]) for r in crows]
            entry = {
                "name": name, "dimension": row["dimension"], "optimal": row["optimal"],
                "category": row["category"], "edge_weight_type": row["edge_weight_type"],
                "problem_type": ptype,
                "coordinates": coords,
            }
            if ptype == "ATSP":
                dm_row = conn.execute(
                    "SELECT matrix_blob, shape_n FROM distance_matrices WHERE problem_name=?",
                    (name,)
                ).fetchone()
                if dm_row:
                    flat = zlib.decompress(bytes(dm_row["matrix_blob"]))
                    n = dm_row["shape_n"]
                    entry["dist_matrix"] = np.frombuffer(flat, dtype=np.int32).reshape(n, n).copy()
            out.append(entry)
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


# ── Best Solutions API ─────────────────────────────────────────────────────────

def save_best_solution(
    problem_name: str,
    algorithm: str,
    params: dict,
    tour: List[int],
    tour_length: float,
    gap: float,
    db_path: str = DB_PATH,
) -> int:
    """Save a best-known solution (params + tour) to the database.
    Returns the new row id.
    """
    conn = get_db(db_path)
    init_db(conn)
    cur = conn.execute(
        "INSERT INTO best_solutions "
        "(problem_name, algorithm, params_json, tour_nodes, tour_length, gap, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (problem_name, algorithm, json.dumps(params, sort_keys=True),
         json.dumps(tour), tour_length, gap, datetime.now().isoformat())
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_best_solution(
    problem_name: str,
    algorithm: str,
    db_path: str = DB_PATH,
) -> Optional[dict]:
    """Return the best (lowest tour_length) solution for (problem, algorithm).
    Returns None if no solution exists.
    """
    conn = get_db(db_path)
    row = conn.execute(
        "SELECT id, problem_name, algorithm, params_json, tour_nodes, "
        "       tour_length, gap, timestamp "
        "FROM best_solutions "
        "WHERE problem_name=? AND algorithm=? "
        "ORDER BY tour_length ASC LIMIT 1",
        (problem_name, algorithm)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "problem": row["problem_name"],
        "algorithm": row["algorithm"],
        "params": json.loads(row["params_json"]),
        "tour": json.loads(row["tour_nodes"]),
        "tour_length": row["tour_length"],
        "gap": row["gap"],
        "timestamp": row["timestamp"],
    }


def query_best_solutions(
    algorithm: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    db_path: str = DB_PATH,
) -> List[dict]:
    """Query best solutions with optional filters.
    Returns list sorted by tour_length ASC.
    """
    conn = get_db(db_path)
    where = ["1=1"]
    params = []
    if algorithm:
        where.append("algorithm=?")
        params.append(algorithm)
    if category:
        where.append("p.category=?")
        params.append(category)
    sql = (
        "SELECT s.id, s.problem_name, s.algorithm, s.params_json, s.tour_nodes, "
        "       s.tour_length, s.gap, s.timestamp, p.dimension, p.category "
        "FROM best_solutions s "
        "LEFT JOIN problems p ON s.problem_name = p.name "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY s.tour_length ASC LIMIT ?"
    )
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    out = []
    for row in rows:
        out.append({
            "id": row["id"],
            "problem": row["problem_name"],
            "algorithm": row["algorithm"],
            "params": json.loads(row["params_json"]),
            "tour": json.loads(row["tour_nodes"]),
            "tour_length": row["tour_length"],
            "gap": row["gap"],
            "dimension": row["dimension"],
            "category": row["category"],
            "timestamp": row["timestamp"],
        })
    return out


def analyze_solution_patterns(db_path: str = DB_PATH) -> str:
    """Cross-problem analysis: most common best params per algorithm and category.
    Returns Markdown-formatted string.
    """
    from collections import Counter
    rows = query_best_solutions(limit=5000, db_path=db_path)
    if not rows:
        return "No best solutions found in database."

    lines = ["# Best Solution Analysis", ""]
    by_cat = {}
    for r in rows:
        cat = r.get("category", "unknown")
        by_cat.setdefault(cat, []).append(r)

    for cat in ("small", "medium", "large", "unknown"):
        entries = by_cat.get(cat, [])
        if not entries:
            continue
        lines.append(f"## {cat.upper()} Problems ({len(entries)} solutions)")
        algos = sorted(set(e["algorithm"] for e in entries))
        for algo in algos:
            algo_entries = [e for e in entries if e["algorithm"] == algo]
            lines.append(f"\n### {algo}")
            param_keys = set()
            for e in algo_entries:
                param_keys.update(e["params"].keys())
            for key in sorted(param_keys):
                vals = [str(e["params"].get(key)) for e in algo_entries if key in e["params"]]
                if vals:
                    counter = Counter(vals)
                    common = counter.most_common(3)
                    lines.append("- **{}**: {}".format(key, ", ".join(f"{v} ({c}x)" for v, c in common)))
            avg_gap = sum(e.get("gap", 0) or 0 for e in algo_entries) / len(algo_entries)
            lines.append(f"- **avg gap**: {avg_gap:.2f}%")
            avg_dim = sum(e.get("dimension", 0) for e in algo_entries) / len(algo_entries)
            lines.append(f"- **avg dimension**: {avg_dim:.0f}")
        lines.append("")
    return "\n".join(lines)


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


def _parse_atsp_text(content: str, name_hint: str = ""):
    """Parse ATSP (.atsp) file with EXPLICIT edge weight type.
    Supports EDGE_WEIGHT_FORMAT: FULL_MATRIX (most common).
    Returns dict with keys: name, dimension, edge_weight_type, problem_type,
    explicit_matrix (n x n list of ints).
    Returns None if parsing fails.
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    header_end = re.search(
        r"EDGE_WEIGHT_SECTION\s*\n", content, re.IGNORECASE
    )
    if not header_end:
        return None
    header = content[:header_end.start()]
    dm = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", header, re.IGNORECASE)
    if not dm:
        return None
    dimension = int(dm.group(1))
    nm = re.findall(r"^NAME\s*[:\s]\s*(\S+)", header, re.IGNORECASE | re.MULTILINE)
    em = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    ef = re.search(r"EDGE_WEIGHT_FORMAT\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    tm = re.search(r"TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    ewt = em.group(1).upper() if em else "EXPLICIT"
    fmt = ef.group(1).upper() if ef else "FULL_MATRIX"
    raw_name = (nm[-1] if nm else name_hint).lower().strip()
    for sfx in (".atsp", ".tsp"):
        if raw_name.endswith(sfx):
            raw_name = raw_name[:-len(sfx)]
    name = raw_name.split("/")[-1].split("\\")[-1]
    if not name:
        name = name_hint.lower().replace(".atsp", "").replace(".tsp", "").split("/")[-1].split("\\")[-1]
    if not name:
        return None
    matrix_section = content[header_end.end():]
    eof_m = re.search(r"\bEOF\b", matrix_section, re.IGNORECASE)
    if eof_m:
        matrix_section = matrix_section[:eof_m.start()]
    tokens = matrix_section.split()
    n_expected = dimension * dimension
    if fmt == "FULL_MATRIX":
        if len(tokens) < n_expected:
            return None
        vals = []
        for tok in tokens[:n_expected]:
            try:
                vals.append(int(tok))
            except ValueError:
                return None
        matrix = [vals[i * dimension:(i + 1) * dimension] for i in range(dimension)]
    elif fmt == "UPPER_ROW":
        n_vals = dimension * (dimension - 1) // 2
        if len(tokens) < n_vals:
            return None
        vals = []
        for tok in tokens[:n_vals]:
            try:
                vals.append(int(tok))
            except ValueError:
                return None
        matrix = [[0] * dimension for _ in range(dimension)]
        idx = 0
        for i in range(dimension):
            for j in range(i + 1, dimension):
                matrix[i][j] = vals[idx]
                matrix[j][i] = vals[idx]
                idx += 1
    elif fmt == "LOWER_ROW":
        n_vals = dimension * (dimension - 1) // 2
        if len(tokens) < n_vals:
            return None
        vals = []
        for tok in tokens[:n_vals]:
            try:
                vals.append(int(tok))
            except ValueError:
                return None
        matrix = [[0] * dimension for _ in range(dimension)]
        idx = 0
        for i in range(dimension):
            for j in range(i):
                matrix[i][j] = vals[idx]
                matrix[j][i] = vals[idx]
                idx += 1
    else:
        return None
    return {
        "name": name,
        "dimension": dimension,
        "edge_weight_type": ewt,
        "problem_type": tm.group(1).upper() if tm else "ATSP",
        "explicit_matrix": matrix,
    }


def _category(n: int) -> str:
    return "small" if n <= 100 else ("medium" if n <= 500 else "large")


def _coords_hash(coords) -> str:
    raw = b"".join(struct.pack("dd", x, y) for x, y in coords)
    return hashlib.sha256(raw).hexdigest()


def build_distance_matrix(coords, ewt: str):
    """Public wrapper for _build_matrix. Computes distance matrix using tsplib_distance_by_type."""
    return _build_matrix(coords, ewt)


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


def _store_explicit_matrix(conn, name: str, matrix: List[List[int]], ewt: str):
    """Store an EXPLICIT matrix (from ATSP parsing) into distance_matrices table."""
    dm = np.array(matrix, dtype=np.int32)
    _store_matrix(conn, name, dm, ewt)

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

    def upsert_atsp(info, atsp_file=None):
        name = info["name"]
        if only and name not in only:
            return False
        if args.size_limit and info["dimension"] > args.size_limit:
            return False
        conn.execute(
            "INSERT OR REPLACE INTO problems "
            "(name, dimension, optimal, category, edge_weight_type, "
            " problem_type, source, coords_hash, tsp_file, extracted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, info["dimension"], TSPLIB_OPTIMALS.get(name),
             _category(info["dimension"]), info["edge_weight_type"],
             info["problem_type"], "tsplib", "",
             atsp_file, datetime.now().isoformat())
        )
        _store_explicit_matrix(conn, name, info["explicit_matrix"], info["edge_weight_type"])
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

    # Source 2: tsplib_data/*.tsp and *.atsp flat files
    if os.path.isdir(TSPLIB_DATA_DIR):
        for fname in sorted(os.listdir(TSPLIB_DATA_DIR)):
            fp = os.path.join(TSPLIB_DATA_DIR, fname)
            fname_lower = fname.lower()
            if fname_lower.endswith(".tsp"):
                try:
                    text = open(fp, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                rn = fname_lower.replace(".tsp", "")
                info = _parse_tsp_text(text, rn)
                if info and upsert(info, os.path.relpath(fp, TSPLIB_DATA_DIR)):
                    inserted += 1
                opt_p = fp.replace(".tsp", ".opt.tour")
                if os.path.exists(opt_p) and info:
                    tour = _parse_opt_tour_text(open(opt_p, encoding="utf-8", errors="replace").read())
                    if tour:
                        pending_tours[info["name"]] = tour
            elif fname_lower.endswith(".atsp"):
                try:
                    text = open(fp, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                rn = fname_lower.replace(".atsp", "")
                info = _parse_atsp_text(text, rn)
                if info and upsert_atsp(info, os.path.relpath(fp, TSPLIB_DATA_DIR)):
                    inserted += 1
                    print(f"  +{info['name']} n={info['dimension']} ATSP", flush=True)
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
