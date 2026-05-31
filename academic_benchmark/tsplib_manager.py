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
    from uniride_core.algorithms.tsplib_parser import (
        tsplib_distance_by_type, parse_tsplib_text,
        parse_opt_tour_text, parse_atsp_text,
    )
    from uniride_core.adapters.matrix_builder import MatrixBuilder
    from uniride_core.models import CostMatrix, ConstraintProfile, ProblemInstance, RoutingProblem
    _DIST_OK = True
except ImportError:
    _DIST_OK = False
    def tsplib_distance_by_type(ewt, p1, p2):
        raise RuntimeError("tsplib_distance_by_type not available")
    def parse_tsplib_text(content, name_hint=""):
        raise RuntimeError("parse_tsplib_text not available")
    def parse_opt_tour_text(content):
        raise RuntimeError("parse_opt_tour_text not available")
    def parse_atsp_text(content, name_hint=""):
        raise RuntimeError("parse_atsp_text not available")
    MatrixBuilder = None
    CostMatrix = None
    ConstraintProfile = None
    ProblemInstance = None
    RoutingProblem = None

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
        CREATE TABLE IF NOT EXISTS routing_constraints (
            problem_name TEXT PRIMARY KEY,
            demands_json TEXT,
            capacities_json TEXT,
            time_windows_json TEXT,
            service_times_json TEXT,
            depot_index INTEGER NOT NULL DEFAULT 0,
            max_route_duration REAL,
            matrix_kind TEXT NOT NULL DEFAULT 'distance',
            direction TEXT NOT NULL DEFAULT 'pickup',
            num_vehicles INTEGER,
            metadata_json TEXT,
            FOREIGN KEY (problem_name) REFERENCES problems(name) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            run_id TEXT PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'academic',
            status TEXT NOT NULL DEFAULT 'completed',
            started_at TEXT NOT NULL,
            completed_at TEXT,
            settings_json TEXT,
            metadata_json TEXT
        );
        CREATE TABLE IF NOT EXISTS benchmark_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            problem_name TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            run_number INTEGER NOT NULL DEFAULT 1,
            problem_type TEXT NOT NULL DEFAULT 'tsp',
            matrix_kind TEXT NOT NULL DEFAULT 'distance',
            objective_cost REAL,
            tour_cost REAL,
            gap REAL,
            elapsed_ms REAL,
            tour_nodes TEXT,
            routes_json TEXT,
            route_loads_json TEXT,
            route_costs_json TEXT,
            num_vehicles INTEGER,
            capacity_violations INTEGER NOT NULL DEFAULT 0,
            tw_violations INTEGER NOT NULL DEFAULT 0,
            params_json TEXT,
            metadata_json TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_benchmark_results_problem_algo
            ON benchmark_results(problem_name, algorithm);
        CREATE INDEX IF NOT EXISTS idx_benchmark_results_run
            ON benchmark_results(run_id);
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
            "SELECT matrix_blob, shape_n, dtype FROM distance_matrices WHERE problem_name=?",
            (problem_name,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        flat = zlib.decompress(bytes(row["matrix_blob"]))
        n = row["shape_n"]
        dtype = np.dtype(row["dtype"] if "dtype" in row.keys() and row["dtype"] else "int32")
        return np.frombuffer(flat, dtype=dtype).reshape(n, n).copy()
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
                    "SELECT matrix_blob, shape_n, dtype FROM distance_matrices WHERE problem_name=?",
                    (name,)
                ).fetchone()
                if dm_row:
                    flat = zlib.decompress(bytes(dm_row["matrix_blob"]))
                    n = dm_row["shape_n"]
                    dtype = np.dtype(dm_row["dtype"] if "dtype" in dm_row.keys() else "int32")
                    entry["dist_matrix"] = np.frombuffer(flat, dtype=dtype).reshape(n, n).copy()
            c_row = conn.execute(
                "SELECT demands_json, capacities_json, time_windows_json, service_times_json, "
                "depot_index, max_route_duration, matrix_kind, direction, num_vehicles, metadata_json "
                "FROM routing_constraints WHERE problem_name=?",
                (name,),
            ).fetchone()
            if c_row:
                entry.update({
                    "demands": json.loads(c_row["demands_json"]) if c_row["demands_json"] else None,
                    "capacities": json.loads(c_row["capacities_json"]) if c_row["capacities_json"] else None,
                    "time_windows": [tuple(x) for x in json.loads(c_row["time_windows_json"])] if c_row["time_windows_json"] else None,
                    "service_times": json.loads(c_row["service_times_json"]) if c_row["service_times_json"] else None,
                    "depot_index": c_row["depot_index"],
                    "max_route_duration": c_row["max_route_duration"],
                    "matrix_kind": c_row["matrix_kind"],
                    "direction": c_row["direction"],
                    "num_vehicles": c_row["num_vehicles"],
                    "metadata": json.loads(c_row["metadata_json"]) if c_row["metadata_json"] else {},
                })
            out.append(entry)
        conn.close()
        return out
    except Exception as e:
        print(f"[WARN] get_all_problems: {e}", flush=True)
        return []


def problem_row_to_instance(row: Dict):
    """Convert a DB problem row from get_all_problems into core ProblemInstance."""
    if RoutingProblem is None:
        raise RuntimeError("uniride_core is not available")
    problem_type = str(row.get("problem_type", "TSP") or "TSP").lower()
    matrix_kind = row.get("matrix_kind", "distance")
    dist_matrix = row.get("dist_matrix")
    time_matrix = row.get("time_matrix")
    is_time_matrix = bool(matrix_kind in {"travel_time", "synthetic_travel_time"} or time_matrix is not None)
    demands = row.get("demands")
    scalar_demands = None
    if demands is not None:
        scalar_demands = [
            int(item[0]) if isinstance(item, (list, tuple)) and item else int(item)
            for item in demands
        ]
    capacities = row.get("capacities")
    return ProblemInstance(
        name=row["name"],
        dimension=row["dimension"],
        coordinates=row.get("coordinates", []),
        optimal=row.get("optimal"),
        category=row.get("category") or _category(row["dimension"]),
        source=row.get("source", "academic_db"),
        problem_type=problem_type,
        is_time_matrix=is_time_matrix,
        time_matrix=time_matrix,
        dist_matrix=None if is_time_matrix else dist_matrix,
        edge_weight_type=row.get("edge_weight_type", "EUC_2D"),
        capacity=capacities[0] if capacities else row.get("capacity"),
        capacities=capacities,
        demands=scalar_demands,
        service_times=row.get("service_times"),
        num_vehicles=row.get("num_vehicles"),
        max_route_duration=row.get("max_route_duration"),
        matrix_kind=matrix_kind,
        direction=row.get("direction", "pickup"),
        time_windows=row.get("time_windows"),
        depot_index=row.get("depot_index", 0),
    )


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


def save_benchmark_run(
    run_id: str,
    source: str = "academic",
    status: str = "completed",
    settings: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    db_path: str = DB_PATH,
) -> str:
    """Create or update a benchmark run row."""
    now = datetime.now().isoformat()
    conn = get_db(db_path)
    init_db(conn)
    existing = conn.execute(
        "SELECT started_at, settings_json, metadata_json FROM benchmark_runs WHERE run_id=?",
        (run_id,),
    ).fetchone()
    started_at = existing["started_at"] if existing else now
    completed_at = now if status in {"completed", "failed", "stopped"} else None
    settings_json = (
        json.dumps(settings, sort_keys=True)
        if settings is not None
        else (existing["settings_json"] if existing else json.dumps({}, sort_keys=True))
    )
    metadata_json = (
        json.dumps(metadata, sort_keys=True)
        if metadata is not None
        else (existing["metadata_json"] if existing else json.dumps({}, sort_keys=True))
    )
    if existing:
        conn.execute(
            "UPDATE benchmark_runs "
            "SET source=?, status=?, completed_at=?, settings_json=?, metadata_json=? "
            "WHERE run_id=?",
            (source, status, completed_at, settings_json, metadata_json, run_id),
        )
    else:
        conn.execute(
            "INSERT INTO benchmark_runs "
            "(run_id, source, status, started_at, completed_at, settings_json, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, source, status, started_at, completed_at, settings_json, metadata_json),
        )
    conn.commit()
    conn.close()
    return run_id


def save_benchmark_result(
    run_id: str,
    result: Dict,
    db_path: str = DB_PATH,
) -> int:
    """Persist one benchmark result row with routing-general fields."""
    conn = get_db(db_path)
    init_db(conn)
    timestamp = result.get("timestamp") or datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO benchmark_results "
        "(run_id, problem_name, algorithm, run_number, problem_type, matrix_kind, objective_cost, "
        " tour_cost, gap, elapsed_ms, tour_nodes, routes_json, route_loads_json, route_costs_json, "
        " num_vehicles, capacity_violations, tw_violations, params_json, metadata_json, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            result.get("problem") or result.get("problem_name"),
            result.get("algorithm") or result.get("strategy"),
            int(result.get("run_number", result.get("run", 1)) or 1),
            result.get("problem_type", "tsp"),
            result.get("matrix_kind", "distance"),
            result.get("objective_cost", result.get("tour_cost", result.get("tour_length"))),
            result.get("tour_cost", result.get("tour_length", result.get("objective_cost"))),
            result.get("gap", result.get("gap_pct", result.get("gap_percent"))),
            result.get("elapsed_ms", result.get("avg_time_ms")),
            json.dumps(result.get("tour")) if result.get("tour") is not None else None,
            json.dumps(result.get("routes")) if result.get("routes") is not None else None,
            json.dumps(result.get("route_loads")) if result.get("route_loads") is not None else None,
            json.dumps(result.get("route_costs")) if result.get("route_costs") is not None else None,
            result.get("num_vehicles"),
            int(result.get("capacity_violations", 0) or 0),
            int(result.get("tw_violations", 0) or 0),
            json.dumps(result.get("params", {}), sort_keys=True),
            json.dumps(result.get("metadata", {}), sort_keys=True),
            timestamp,
        ),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def query_benchmark_results(
    run_id: Optional[str] = None,
    problem: Optional[str] = None,
    algorithm: Optional[str] = None,
    problem_type: Optional[str] = None,
    limit: int = 100,
    db_path: str = DB_PATH,
) -> List[Dict]:
    """Query persisted benchmark run rows."""
    conn = get_db(db_path)
    init_db(conn)
    where = ["1=1"]
    params = []
    if run_id:
        where.append("r.run_id=?")
        params.append(run_id)
    if problem:
        where.append("r.problem_name=?")
        params.append(problem)
    if algorithm:
        where.append("r.algorithm=?")
        params.append(algorithm)
    if problem_type:
        where.append("r.problem_type=?")
        params.append(problem_type)
    sql = (
        "SELECT r.*, b.source, b.status "
        "FROM benchmark_results r "
        "LEFT JOIN benchmark_runs b ON r.run_id = b.run_id "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY r.timestamp DESC, r.id DESC LIMIT ?"
    )
    params.append(max(1, int(limit)))
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_benchmark_result_row_to_dict(row) for row in rows]


def _benchmark_result_row_to_dict(row) -> Dict:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "source": row["source"],
        "status": row["status"],
        "problem": row["problem_name"],
        "algorithm": row["algorithm"],
        "run_number": row["run_number"],
        "problem_type": row["problem_type"],
        "matrix_kind": row["matrix_kind"],
        "objective_cost": row["objective_cost"],
        "tour_cost": row["tour_cost"],
        "gap": row["gap"],
        "elapsed_ms": row["elapsed_ms"],
        "tour": json.loads(row["tour_nodes"]) if row["tour_nodes"] else None,
        "routes": json.loads(row["routes_json"]) if row["routes_json"] else None,
        "route_loads": json.loads(row["route_loads_json"]) if row["route_loads_json"] else None,
        "route_costs": json.loads(row["route_costs_json"]) if row["route_costs_json"] else None,
        "num_vehicles": row["num_vehicles"],
        "capacity_violations": row["capacity_violations"],
        "tw_violations": row["tw_violations"],
        "params": json.loads(row["params_json"]) if row["params_json"] else {},
        "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
        "timestamp": row["timestamp"],
    }


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


# ── Parsing helpers — delegated to canonical parser ─────────────────────────

# All TSPLIB parsing now lives in uniride_core.algorithms.tsplib_parser.
# The local _parse_tsp_text / _parse_opt_tour_text / _parse_atsp_text functions
# were removed in the P3-4 consolidation.  Use the imported canonical versions:


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


def _store_numeric_matrix(conn, name: str, matrix, ewt: str):
    """Store a core matrix while preserving integer or floating dtype."""
    dm = np.asarray(matrix)
    if not np.issubdtype(dm.dtype, np.number):
        dm = dm.astype(np.float64)
    if np.issubdtype(dm.dtype, np.integer):
        dm = dm.astype(np.int32, copy=False)
    else:
        dm = dm.astype(np.float64, copy=False)
    blob = zlib.compress(dm.tobytes(), level=6)
    conn.execute(
        "INSERT OR REPLACE INTO distance_matrices "
        "(problem_name, matrix_blob, dtype, shape_n, edge_weight_type, computed_at, version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, blob, str(dm.dtype), dm.shape[0], ewt, datetime.now().isoformat(), 1),
    )


def store_routing_problem(problem, db_path: str = DB_PATH, source_file: Optional[str] = None) -> None:
    """Store a core RoutingProblem in the academic SQLite DB."""
    if RoutingProblem is None:
        raise RuntimeError("uniride_core is not available")
    conn = get_db(db_path)
    init_db(conn)
    try:
        name = problem.name
        coords = list(problem.coordinates or [])
        matrix_values = np.asarray(problem.matrix.values)
        ewt = str(problem.metadata.get("edge_weight_type", "EXPLICIT" if problem.matrix.is_asymmetric else "EUC_2D"))
        metadata = dict(problem.metadata or {})
        if problem.matrix.kind:
            metadata.setdefault("matrix_kind", problem.matrix.kind)

        conn.execute(
            "INSERT OR REPLACE INTO problems "
            "(name, dimension, optimal, category, edge_weight_type, "
            " problem_type, source, coords_hash, tsp_file, extracted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                problem.dimension,
                problem.optimal,
                problem.category,
                ewt,
                problem.problem_type.upper(),
                problem.source,
                _coords_hash(coords) if coords else "",
                source_file,
                datetime.now().isoformat(),
            ),
        )
        conn.execute("DELETE FROM coordinates WHERE problem_name=?", (name,))
        if coords:
            conn.executemany(
                "INSERT INTO coordinates (problem_name, node_idx, x, y) VALUES (?, ?, ?, ?)",
                [(name, idx, x, y) for idx, (x, y) in enumerate(coords)],
            )
        _store_numeric_matrix(conn, name, matrix_values, ewt)

        constraints = problem.constraints
        conn.execute(
            "INSERT OR REPLACE INTO routing_constraints "
            "(problem_name, demands_json, capacities_json, time_windows_json, service_times_json, "
            " depot_index, max_route_duration, matrix_kind, direction, num_vehicles, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                json.dumps(constraints.demands) if constraints.demands is not None else None,
                json.dumps(list(constraints.capacities)) if constraints.capacities is not None else None,
                json.dumps(constraints.time_windows) if constraints.time_windows is not None else None,
                json.dumps(list(constraints.service_times)) if constraints.service_times is not None else None,
                constraints.depot_index,
                constraints.max_route_duration,
                problem.matrix.kind,
                constraints.direction,
                metadata.get("vehicles"),
                json.dumps(metadata, sort_keys=True),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_routing_problem(problem_name: str, db_path: str = DB_PATH):
    """Load a stored academic problem as a core RoutingProblem."""
    if RoutingProblem is None:
        raise RuntimeError("uniride_core is not available")
    conn = get_db(db_path)
    init_db(conn)
    try:
        row = conn.execute(
            "SELECT name, dimension, optimal, category, edge_weight_type, problem_type, source "
            "FROM problems WHERE name=?",
            (problem_name,),
        ).fetchone()
        if not row:
            return None
        coords = [
            (r["x"], r["y"])
            for r in conn.execute(
                "SELECT x, y FROM coordinates WHERE problem_name=? ORDER BY node_idx",
                (problem_name,),
            ).fetchall()
        ]
        matrix = get_distance_matrix(problem_name, db_path=db_path)
        c_row = conn.execute(
            "SELECT demands_json, capacities_json, time_windows_json, service_times_json, "
            "depot_index, max_route_duration, matrix_kind, direction, metadata_json "
            "FROM routing_constraints WHERE problem_name=?",
            (problem_name,),
        ).fetchone()
        metadata = json.loads(c_row["metadata_json"]) if c_row and c_row["metadata_json"] else {}
        matrix_kind = c_row["matrix_kind"] if c_row else metadata.get("matrix_kind", "distance")
        demands = json.loads(c_row["demands_json"]) if c_row and c_row["demands_json"] else None
        capacities = json.loads(c_row["capacities_json"]) if c_row and c_row["capacities_json"] else None
        time_windows = [tuple(x) for x in json.loads(c_row["time_windows_json"])] if c_row and c_row["time_windows_json"] else None
        service_times = json.loads(c_row["service_times_json"]) if c_row and c_row["service_times_json"] else None
        constraints = ConstraintProfile(
            demands=demands,
            capacities=capacities,
            time_windows=time_windows,
            service_times=service_times,
            depot_index=c_row["depot_index"] if c_row else 0,
            max_route_duration=c_row["max_route_duration"] if c_row else None,
            direction=c_row["direction"] if c_row else "pickup",
        )
        if matrix is None:
            matrix = MatrixBuilder.from_coordinates(coords, row["edge_weight_type"]) if coords else np.zeros((row["dimension"], row["dimension"]))
        return RoutingProblem(
            name=row["name"],
            problem_type=str(row["problem_type"]).lower(),
            matrix=CostMatrix(
                matrix,
                kind=matrix_kind,
                is_asymmetric=str(row["problem_type"]).upper() == "ATSP" or not np.allclose(matrix, np.asarray(matrix).T),
            ),
            constraints=constraints,
            coordinates=coords,
            optimal=row["optimal"],
            category=row["category"] or _category(row["dimension"]),
            source=row["source"] or "academic_db",
            metadata={**metadata, "edge_weight_type": row["edge_weight_type"]},
        )
    finally:
        conn.close()


def store_academic_text(text: str, kind: str, name: str = "academic", db_path: str = DB_PATH, source_file: Optional[str] = None):
    """Parse and store CVRPLIB/Solomon/TSPLIB text through core adapters."""
    if MatrixBuilder is None:
        raise RuntimeError("uniride_core is not available")
    kind_key = kind.lower()
    if kind_key in {"cvrp", "cvrplib"}:
        problem = MatrixBuilder.from_cvrplib_text(text, name=name)
    elif kind_key in {"cvrptw", "solomon"}:
        problem = MatrixBuilder.from_solomon_text(text, name=name)
    elif kind_key in {"tsp", "tsplib"}:
        problem = MatrixBuilder.from_tsplib_text(text, name=name)
    elif kind_key == "atsp":
        problem = MatrixBuilder.from_atsp_text(text, name=name)
    else:
        raise ValueError(f"Unsupported academic problem kind: {kind}")
    store_routing_problem(problem, db_path=db_path, source_file=source_file)
    return problem

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
                    info = parse_tsplib_text(text, rn)
                    if info and upsert(info):
                        inserted += 1
                        print(f"  +{info['name']} n={info['dimension']} {info['edge_weight_type']}", flush=True)
                    else:
                        skipped += 1
                elif fname.endswith(".opt.tour.gz"):
                    rn = os.path.basename(fname).replace(".opt.tour.gz", "")
                    tour = parse_opt_tour_text(text)
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
                info = parse_tsplib_text(text, rn)
                if info and upsert(info, os.path.relpath(fp, TSPLIB_DATA_DIR)):
                    inserted += 1
                opt_p = fp.replace(".tsp", ".opt.tour")
                if os.path.exists(opt_p) and info:
                    tour = parse_opt_tour_text(open(opt_p, encoding="utf-8", errors="replace").read())
                    if tour:
                        pending_tours[info["name"]] = tour
            elif fname_lower.endswith(".atsp"):
                try:
                    text = open(fp, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                rn = fname_lower.replace(".atsp", "")
                info = parse_atsp_text(text, rn)
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


def cmd_import_academic(args):
    paths = [p for p in args.path.split(",") if p] if getattr(args, "path", "") else []
    if not paths:
        print("[ERROR] --path is required for import-academic")
        sys.exit(1)
    inserted = 0
    for path in paths:
        if not os.path.exists(path):
            print(f"  ! missing {path}", flush=True)
            continue
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
            kind = args.kind
            if kind == "auto":
                lower = path.lower()
                if lower.endswith((".vrp", ".cvrp")):
                    kind = "cvrplib"
                elif lower.endswith((".sol", ".txt")):
                    kind = "solomon"
                elif lower.endswith(".atsp"):
                    kind = "atsp"
                else:
                    kind = "tsplib"
            problem = store_academic_text(
                text,
                kind=kind,
                name=os.path.basename(path),
                db_path=DB_PATH,
                source_file=os.path.relpath(path, TSPLIB_DATA_DIR) if os.path.commonpath([os.path.abspath(path), TSPLIB_DATA_DIR]) == TSPLIB_DATA_DIR else path,
            )
            inserted += 1
            print(f"  +{problem.name} type={problem.problem_type} n={problem.dimension}", flush=True)
        except Exception as exc:
            print(f"  ! {path}: {exc}", flush=True)
    print(f"[DONE] imported={inserted}", flush=True)
    print(f"  DB:       {DB_PATH}")
    print(f"  Problems: {np_}  |  Matrices: {nm} (missing:{miss})  |  Tours: {nt}")
    print(f"  EWT:      {ewts}")
    if miss:
        print(f"  !! Run compute-dm to cache {miss} missing matrices.")
    print("=" * 55)


def main():
    p = argparse.ArgumentParser(description="TSPLIB SQLite Database Manager")
    p.add_argument("command", choices=["extract", "compute-dm", "add-tours", "status", "export", "import-academic"])
    p.add_argument("--force",      action="store_true", help="Re-insert even if cached")
    p.add_argument("--size-limit", type=int, default=0, metavar="N")
    p.add_argument("--problems",   type=str, default="", help="Comma-separated names")
    p.add_argument("--problem",    type=str, default="")
    p.add_argument("--path",       type=str, default="", help="Academic instance file path, or comma-separated paths")
    p.add_argument("--kind",       type=str, default="auto", choices=["auto", "cvrplib", "solomon", "tsplib", "atsp"])
    args = p.parse_args()
    if   args.command == "extract":    cmd_extract(args)
    elif args.command == "compute-dm": cmd_compute_dm(args)
    elif args.command == "status":     cmd_status(args)
    elif args.command == "import-academic": cmd_import_academic(args)
    else: print(f"[SKIP] {args.command} not yet implemented via this path.")

if __name__ == "__main__":
    main()
