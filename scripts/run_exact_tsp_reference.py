"""GOAL 2, stage 1 (WP-E7; DECISION_LOG E09; design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 5, 6, 8, 9):
reproduce the published TSPLIB optima of the 16 TSP instances with n <= 100 and ATSP ft53 with the exact DFJ
cut-loop solver, Gurobi primary and HiGHS re-solve.

Offline: reads the TSPLIB instance files of the active collection ``academic_benchmark/tsplib_data/tsp`` and the
published optimal tours of ``academic_benchmark/tsplib_data/opt_tours`` (both manifest-governed, sha256 checked, see
``academic_benchmark.exact_reference.inputs``), and the published optima and the instance list in ``problems.optimal``
of ``tsplib.db``; the database is opened strictly read-only and immutable (``mode=ro&immutable=1``: no write, no
-wal/-shm file) and gives no coordinates and no tours while the committed files exist. Any input path in the archive
directory is refused (exit 2). ``best_solutions`` (our own heuristic runs) is never read. Nothing is downloaded.

Each instance gets 600 s wall time in total (all cut-loop re-solves together), 1 thread, seed 0. The distance
convention (nint for EUC_2D, the ATT pseudo-Euclidean rule, the GEO rule) is asserted against an independent
transcription of TSPLIB95 before any solve. A published optimum must be reproduced (``optimal`` with that value) or
bracketed (LB <= optimum <= UB); anything else, and any HiGHS/MTZ contradiction, is a blocking defect (exit 1).
Exit codes: 0 all instances reproduced or bracketed; 1 blocking error; 2 refused (unsafe --out, dirty tree, bad
data); 3 AMPL, Gurobi or HiGHS unavailable.

Writes (strictly below docs/paper/results/, E04): reference.csv, tours.json, manifest.json, README.md. This is a
verification subset, not a paper instance set; exact rows are never pooled with heuristic rows; no superiority claim.
``--verify-tours DIR`` re-checks a tours.json without AMPL and without a database.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime
import hashlib
import json
import math
import os
import platform
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from academic_benchmark.exact_reference import inputs, protocol  # noqa: E402
from uniride_core.algorithms import tsplib_parser  # noqa: E402
from uniride_core.exact import ampl_backend as ab  # noqa: E402
from uniride_core.exact import tsp  # noqa: E402

RESULTS_REL = "docs/paper/results"
DEFAULT_OUT = REPO / RESULTS_REL / "tsplib-exact-reference" / "stage1-verification"
DEFAULT_DATA_DIR = Path(os.environ.get("UNIRIDE_TSPLIB_DATA_DIR") or REPO / "academic_benchmark" / "tsplib_data")
DB_NAME = "tsplib.db"
BUDGET_SECONDS = float(protocol.TSP_REFERENCE_TOTAL_SECONDS)
MTZ_MAX_N = 40
MTZ_SECONDS = 120.0
SEED = 0
SUPPORTED_EWT = ("EUC_2D", "ATT", "GEO")
EXPECTED_TSP_NAMES = ("burma14", "ulysses16", "ulysses22", "att48", "eil51", "berlin52", "st70", "eil76", "pr76", "gr96",
                      "kroa100", "krob100", "kroc100", "krod100", "kroe100", "rd100")
ATSP_NAMES = ("ft53",)
TSPLIB_GEO_PI = 3.141592  # the constant printed in the TSPLIB95 document; the repo's GEO function uses math.pi
TSP_DIR = inputs.TSP_DIR  # active instance collection (manifest-governed)
OPT_TOUR_DIR = inputs.OPT_TOUR_DIR  # active published-tour collection (manifest-governed)

REFERENCE_CSV_FIELDS = (
    "protocol", "instance", "problem_type", "n", "edge_weight_type", "reference_optimum", "reference_source", "exact_status",
    "stop_reason", "ub", "lb", "gap_to_reference", "reference_in_bracket", "verdict", "ub_source", "cut_rounds", "cuts",
    "solver", "solver_version", "wall_seconds", "timing_dependent", "highs_status", "highs_value", "highs_lb",
    "highs_wall_seconds", "highs_timing_dependent", "highs_agreement", "mtz_status", "mtz_value", "mtz_wall_seconds",
    "mtz_agreement")


class ConventionError(AssertionError):
    """The matrix does not follow the TSPLIB distance convention."""


@dataclasses.dataclass(frozen=True)
class InstanceSpec:
    name: str
    problem_type: str  # "TSP" or "ATSP"
    n: int
    edge_weight_type: str
    published_optimum: int
    published_source: str


# ---------------------------------------------------------------- distance convention
def spec_distance(ewt: str, p, q, pi: float = math.pi) -> int:
    """A second transcription of the TSPLIB95 distance rules, separate from ``uniride_core.algorithms.distance`` (it is
    not an independent check of the GEO constant). The GEO branch uses ``math.pi``, the same constant as the repository's
    TSPLIB distance code (DECISION_LOG E10), while the TSPLIB95 document prints PI = 3.141592; the effect of that
    difference is measured by the sensitivity re-solve (``geo_pi_sensitivity``)."""
    if ewt == "EUC_2D":
        return int(math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) + 0.5)  # nint
    if ewt == "ATT":
        rij = math.sqrt(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) / 10.0)
        tij = int(rij + 0.5)  # nint
        return tij + 1 if tij < rij else tij
    if ewt == "GEO":
        def lat_lon(x):
            deg = int(x)
            return pi * (deg + 5.0 * (x - deg) / 3.0) / 180.0  # DD.MM -> radians

        la1, lo1, la2, lo2 = lat_lon(p[0]), lat_lon(p[1]), lat_lon(q[0]), lat_lon(q[1])
        q1, q2, q3 = math.cos(lo1 - lo2), math.cos(la1 - la2), math.cos(la1 + la2)
        return int(6378.388 * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)
    raise ValueError(f"unsupported EDGE_WEIGHT_TYPE {ewt!r}")


def build_matrix(ewt: str, coords) -> tuple:
    """Integer distance matrix with the repo's TSPLIB functions (T06/O02: the metric is preserved); zero diagonal."""
    if ewt not in SUPPORTED_EWT:
        raise ValueError(f"unsupported EDGE_WEIGHT_TYPE {ewt!r} (supported: {SUPPORTED_EWT})")
    n = len(coords)
    return tuple(tuple(0 if i == j else int(tsplib_parser.tsplib_distance_by_type(ewt, coords[i], coords[j])) for j in range(n))
                 for i in range(n))


def assert_convention(ewt: str, coords, matrix) -> None:
    """Every arc equals the independent TSPLIB transcription; raises ConventionError otherwise."""
    n = len(coords)
    if len(matrix) != n:
        raise ConventionError(f"matrix has {len(matrix)} rows for {n} nodes")
    bad = [(i, j, matrix[i][j], spec_distance(ewt, coords[i], coords[j])) for i in range(n) for j in range(n)
           if i != j and matrix[i][j] != spec_distance(ewt, coords[i], coords[j])]
    if bad:
        raise ConventionError(f"{ewt}: {len(bad)} arcs differ from the TSPLIB transcription, first (i, j, got, want): {bad[:3]}")


def geo_pi_variant_matrix(coords, pi: float) -> tuple:
    n = len(coords)
    return tuple(tuple(0 if i == j else spec_distance("GEO", coords[i], coords[j], pi) for j in range(n)) for i in range(n))


def count_differing_arcs(a, b) -> int:
    n = len(a)
    return sum(1 for i in range(n) for j in range(n) if i != j and a[i][j] != b[i][j])


def load_atsp_matrix(text: str, name: str) -> tuple:
    data = tsplib_parser.parse_atsp_text(text, name)
    if data is None:
        raise ValueError(f"{name}: not a parsable explicit ATSP file")
    return tuple(tuple(int(v) for v in row) for row in data["explicit_matrix"])


def matrix_sha256(matrix) -> str:
    return hashlib.sha256(json.dumps([list(map(int, r)) for r in matrix], separators=(",", ":")).encode("ascii")).hexdigest()


def utc_stamp(now=None) -> str:
    """UTC time as ``YYYY-MM-DDTHH:MM:SSZ``."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def coordinate_text_record() -> dict:
    """The canonical coordinate text behind ``sha256`` of an instance with data_source ``tsplib_db_coordinates``."""
    return {"line_format": "{i} {x!r} {y!r}\\n", "encoding": "ASCII", "index_base": 0,
            "description": "one line per node in database order: 0-based index, repr() of the x and y floats, separated by "
                           "single spaces, terminated by a line feed; no header; sha256 of those bytes"}


def coordinate_text_sha256(coords) -> str:
    return inputs.coordinate_text_sha256(coords)


def convention_record(*, geo_pi_blocking: bool) -> dict:
    return {"EUC_2D": "nint", "ATT": "pseudo-Euclidean (TSPLIB95)", "GEO": "TSPLIB95 GEO with math.pi (T06/O02, E10)",
            "asserted": "every arc against a second transcription of the TSPLIB95 rules written for this runner "
                        "(spec_distance); both it and the repository code use math.pi for GEO, so the pi choice is shared and "
                        "not independently checked; a re-solve with pi = 3.141592 (the value printed in TSPLIB95) is recorded "
                        "in geo_pi_sensitivity",
            "geo_pi_sensitivity_blocking": bool(geo_pi_blocking)}


# ---------------------------------------------------------------- tsplib.db (strictly read-only) and published optima
def wal_refusal(db_path) -> str:
    """Refusal message when a non-empty ``-wal`` file sits next to the database, else ''. The immutable read-only open
    ignores that file, so its frames (committed but not yet checkpointed data) would be silently left out."""
    wal = Path(str(db_path) + "-wal")
    if wal.is_file() and wal.stat().st_size > 0:
        return (f"{wal.name} next to the database is not empty ({wal.stat().st_size} bytes); the read-only immutable open "
                f"ignores it, so the data read could differ from the database as its writer sees it. Checkpoint the "
                f"database outside this runner (or move the -wal file away) and run again")
    return ""


def database_record(db_path) -> dict:
    """File name, size and sha256 of the database file as read (recorded in the manifest)."""
    path = Path(db_path)
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return {"file": path.name, "size_bytes": path.stat().st_size, "sha256": h.hexdigest()}


def open_db_readonly(path) -> sqlite3.Connection:
    """Read-only and immutable: writes fail and no -wal/-shm file is created next to the database."""
    uri = Path(path).resolve().as_uri() + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("pragma query_only=on")
    return conn


def read_db_coordinates(conn, name: str) -> list:
    rows = conn.execute("select x, y from coordinates where problem_name=? order by node_idx", (name,)).fetchall()
    if not rows:
        raise ValueError(f"{name}: no coordinates in the database")
    return [(float(x), float(y)) for x, y in rows]


def read_instance_set(conn) -> list:
    """TSP instances with n <= 100 and a published optimum (``problems.optimal``), plus ATSP ft53."""
    rows = conn.execute(
        "select name, dimension, optimal, edge_weight_type, problem_type, source from problems "
        "where optimal is not null and ((problem_type = 'TSP' and dimension <= 100) or name in ({})) "
        "order by dimension, name".format(",".join("?" * len(ATSP_NAMES))), ATSP_NAMES).fetchall()
    specs = []
    for name, dim, opt, ewt, ptype, source in rows:
        if source != "tsplib":
            raise ValueError(f"{name}: problems.source is {source!r}, not 'tsplib'")
        specs.append(InstanceSpec(name, ptype, int(dim), ewt, int(opt), "tsplib"))
    return specs


def check_instance_set(specs) -> None:
    tsp_names = [s.name for s in specs if s.problem_type == "TSP"]
    atsp_names = [s.name for s in specs if s.problem_type == "ATSP"]
    if tsp_names != list(EXPECTED_TSP_NAMES) or atsp_names != list(ATSP_NAMES):
        raise ValueError(f"the instance set changed: TSP {tsp_names}, ATSP {atsp_names}; expected {list(EXPECTED_TSP_NAMES)} "
                         f"and {list(ATSP_NAMES)} (DECISION_LOG E09)")


def parser_optima() -> dict:
    """Second source 1: ``TSPLIB_OPTIMALS`` in the repo's TSPLIB parser module."""
    return dict(tsplib_parser.TSPLIB_OPTIMALS)


def atsp_manifest_optima(path=None) -> dict:
    """Second source 2: the ATSP collection manifest (optimum with its authority URL recorded)."""
    path = Path(path) if path else REPO / "academic_benchmark" / "tsplib_data" / "atsp" / "MANIFEST.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {i["name"]: int(i["optimal"]) for i in doc.get("instances", ()) if i.get("optimal") is not None}


def cross_check_optima(specs, parser_values: dict, atsp_values: dict) -> list:
    """Discrepancies between ``problems.optimal`` and the other sources in the repo (empty list: all agree)."""
    out = []
    for s in specs:
        other = parser_values.get(s.name)
        if other is None:
            out.append(f"{s.name}: no value in the parser table to compare with problems.optimal {s.published_optimum}")
        elif other != s.published_optimum:
            out.append(f"{s.name}: problems.optimal {s.published_optimum} differs from the parser table {other}")
        if s.problem_type == "ATSP":
            m = atsp_values.get(s.name)
            if m is None:
                out.append(f"{s.name}: no value in the ATSP manifest")
            elif m != s.published_optimum:
                out.append(f"{s.name}: problems.optimal {s.published_optimum} differs from the ATSP manifest {m}")
    return out


def cross_check_manifest_specs(db_specs, collection: dict) -> list:
    """Disagreements between the DB instance specs (``problems``: dimension, published optimum) and the committed
    manifest-governed collections (``collection_specs``). Empty list: they agree. An instance the collections do not list
    is not compared here (the older database-coordinates rule applies to it). A disagreement blocks the run (exit 2)."""
    out = []
    for s in db_specs:
        c = collection.get(s.name)
        if c is None:
            continue
        if c.n != s.n:
            out.append(f"{s.name}: manifest dimension {c.n} differs from problems.dimension {s.n}")
        if c.published_optimum != s.published_optimum:
            out.append(f"{s.name}: manifest published_optimum {c.published_optimum} differs from problems.optimal "
                       f"{s.published_optimum}")
    return out


class PublishedTourError(ValueError):
    """The published optimal tour does not have the published length on the used data."""


def _parse_tour_file(text: str) -> list:
    return inputs.parse_tour_text(text)


def check_published_tour(spec, matrix, tour_one_based) -> list:
    """Errors when the published tour is not a Hamiltonian cycle of the used matrix or its length differs from the
    published optimum (empty list: the used coordinates reproduce the published optimum)."""
    return [f"{spec.name}: published tour: {e}"
            for e in tsp.validate_tour(matrix, [int(v) - 1 for v in tour_one_based], spec.published_optimum)]


def _attach_published_tour_check(rec: dict, spec, matrix, tour_dir) -> None:
    pub = inputs.read_collection_tour(spec.name, tour_dir) if tour_dir is not None else None
    if pub is None:
        rec["published_tour_check"] = {"source": "none", "tour_length": None, "equals_published_optimum": None}
        return
    nodes, source = pub
    errors = check_published_tour(spec, matrix, nodes)
    if errors:
        raise PublishedTourError("; ".join(errors))
    rec["published_tour_check"] = {"source": source, "tour_length": tsp.tour_length(matrix, tuple(v - 1 for v in nodes)),
                                   "equals_published_optimum": True}


# ---------------------------------------------------------------- instance data
def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_instance(spec: InstanceSpec, data_dir: Path, conn, tour_dir=OPT_TOUR_DIR, tsp_dir=None) -> tuple:
    """(matrix, coordinates or None, data record). With ``tsp_dir`` (the active collection) the committed, manifest-checked
    instance file is used and ``conn`` may be None: no database read. Without it, or for an instance the collection does not
    list, the older rule applies: instance file in ``data_dir``, otherwise the node coordinates in the read-only database
    (recorded as such). The published tour comes from ``tour_dir`` (manifest-governed collection). The convention is
    asserted here."""
    if spec.problem_type == "ATSP":
        found = inputs.read_atsp_file(spec.name) if tsp_dir is not None else None
        if found is not None:
            matrix = load_atsp_matrix(found[0], spec.name)
            if len(matrix) != spec.n:
                raise ValueError(f"{spec.name}: file has {len(matrix)} nodes, expected {spec.n}")
            rec = {"data_source": "atsp_file", "file": Path(found[1]["artifact_path"]).name, "sha256": found[1]["sha256"]}
            _attach_published_tour_check(rec, spec, matrix, tour_dir)
            return matrix, None, rec
        for cand in (data_dir / f"{spec.name}.atsp", data_dir / "atsp" / f"{spec.name}.atsp"):
            if cand.is_file():
                matrix = load_atsp_matrix(cand.read_text(encoding="utf-8"), spec.name)
                if len(matrix) != spec.n:
                    raise ValueError(f"{spec.name}: file has {len(matrix)} nodes, database says {spec.n}")
                rec = {"data_source": "atsp_file", "file": cand.name, "sha256": _sha256_file(cand)}
                _attach_published_tour_check(rec, spec, matrix, tour_dir)
                return matrix, None, rec
        raise FileNotFoundError(f"{spec.name}: no .atsp file in the data directory")
    committed = inputs.read_tsp_file(spec.name, tsp_dir) if tsp_dir is not None else None
    if committed is not None:
        text, entry = committed
        data = tsplib_parser.parse_tsplib_text(text, spec.name)
        if data is None or data["edge_weight_type"] != spec.edge_weight_type or len(data["coordinates"]) != spec.n:
            raise ValueError(f"{spec.name}: committed instance file disagrees with the instance spec (type or node count)")
        coords = data["coordinates"]
        if coordinate_text_sha256(coords) != entry["coordinate_text_sha256"]:
            raise ValueError(f"{spec.name}: coordinates of the committed instance file differ from the manifest fingerprint")
        matrix = build_matrix(spec.edge_weight_type, coords)
        assert_convention(spec.edge_weight_type, coords, matrix)
        rec = {"data_source": "tsp_file", "file": entry["file_name"], "sha256": entry["sha256"]}
        _attach_published_tour_check(rec, spec, matrix, tour_dir)
        return matrix, coords, rec
    path = data_dir / f"{spec.name}.tsp"
    db_coords = read_db_coordinates(conn, spec.name)
    if path.is_file():
        data = tsplib_parser.parse_tsplib_text(path.read_text(encoding="utf-8"), spec.name)
        if data is None or data["edge_weight_type"] != spec.edge_weight_type or len(data["coordinates"]) != spec.n:
            raise ValueError(f"{spec.name}: instance file disagrees with the database (type or node count)")
        coords = data["coordinates"]
        if len(db_coords) == len(coords) and any(abs(a - c) > 1e-9 or abs(b - d) > 1e-9 for (a, b), (c, d) in zip(coords, db_coords)):
            raise ValueError(f"{spec.name}: instance file coordinates differ from the database coordinates")
        rec = {"data_source": "tsp_file", "file": path.name, "sha256": _sha256_file(path)}
    else:
        if len(db_coords) != spec.n:
            raise ValueError(f"{spec.name}: database has {len(db_coords)} coordinates, expected {spec.n}")
        coords = db_coords
        rec = {"data_source": "tsplib_db_coordinates", "file": None, "sha256": coordinate_text_sha256(coords)}
    matrix = build_matrix(spec.edge_weight_type, coords)
    assert_convention(spec.edge_weight_type, coords, matrix)
    _attach_published_tour_check(rec, spec, matrix, tour_dir)
    return matrix, coords, rec


# ---------------------------------------------------------------- evaluation
def verdict(result, reference: int) -> str:
    """reproduced (proven optimum equals the published value), bracketed (LB <= published <= UB), not_bracketed
    (no tour found), defect (anything else)."""
    if result.status == "optimal":
        return "reproduced" if result.ub == reference else "defect"
    if result.status == "feasible_with_gap":
        return "bracketed" if result.lb is not None and result.ub is not None and result.lb <= reference <= result.ub else "defect"
    if result.status == "bound_only":
        return "not_bracketed"
    return "defect"


def _tour_errors(matrix, result) -> list:
    if result.tour is None:
        return []
    return tsp.validate_tour(matrix, result.tour, result.ub)


def evaluate_instance(spec: InstanceSpec, matrix, *, solve_primary, solve_secondary=None, solve_mtz=None) -> dict:
    """Solve one instance and judge it. ``solve_*`` map a matrix to a ``TspResult``. HiGHS (the second solver) and
    MTZ are run only for a proven primary result; a proven difference or contradiction is a blocking error."""
    blocking = []
    primary = solve_primary(matrix)
    for e in _tour_errors(matrix, primary):
        blocking.append(f"{spec.name}: primary tour invalid: {e}")
    v = verdict(primary, spec.published_optimum)
    if v in ("defect", "not_bracketed"):
        note = f"; {primary.note}" if primary.note else ""
        blocking.append(f"{spec.name}: published optimum {spec.published_optimum} neither reproduced nor bracketed "
                        f"(status {primary.status}, LB {primary.lb}, UB {primary.ub}{note})")
    secondary = comparison = mtz = mtz_comparison = None
    if primary.status == "optimal" and solve_secondary is not None:
        secondary = solve_secondary(matrix)
        comparison = tsp.compare_solvers(primary, secondary)
        if comparison.blocking:
            blocking.append(f"{spec.name}: HiGHS {comparison.label}: {comparison.reason}")
        for e in _tour_errors(matrix, secondary):
            blocking.append(f"{spec.name}: HiGHS tour invalid: {e}")
    if primary.status == "optimal" and solve_mtz is not None:
        mtz = solve_mtz(matrix)
        mtz_comparison = tsp.compare_solvers(primary, mtz)
        if mtz_comparison.blocking:
            blocking.append(f"{spec.name}: MTZ cross-check {mtz_comparison.label}: {mtz_comparison.reason}")
        for e in _tour_errors(matrix, mtz):
            blocking.append(f"{spec.name}: MTZ tour invalid: {e}")
    return {"instance": spec.name, "spec": spec, "primary": primary, "secondary": secondary, "comparison": comparison,
            "mtz": mtz, "mtz_comparison": mtz_comparison, "verdict": v, "blocking": blocking}


# ---------------------------------------------------------------- outputs
def _opt(value):
    return "" if value is None else value


def reference_rows(records) -> list:
    rows = []
    for rec in records:
        s, p, h, m = rec["spec"], rec["primary"], rec["secondary"], rec["mtz"]
        rows.append({
            "protocol": protocol.PROTOCOL_ID, "instance": s.name, "problem_type": s.problem_type, "n": s.n,
            "edge_weight_type": s.edge_weight_type, "reference_optimum": s.published_optimum,
            "reference_source": s.published_source, "exact_status": p.status, "stop_reason": _opt(p.stop_reason),
            "ub": _opt(p.ub), "lb": _opt(p.lb), "gap_to_reference": "" if p.ub is None else p.ub - s.published_optimum,
            "reference_in_bracket": p.lb is not None and p.ub is not None and p.lb <= s.published_optimum <= p.ub,
            "verdict": rec["verdict"], "ub_source": _opt(p.ub_source), "cut_rounds": p.rounds, "cuts": p.cuts,
            "solver": _opt(p.solver), "solver_version": _opt(p.solver_version), "wall_seconds": round(p.wall_seconds, 3),
            "timing_dependent": bool(p.timing_dependent),
            "highs_status": "" if h is None else h.status, "highs_value": "" if h is None else _opt(h.ub),
            "highs_lb": "" if h is None else _opt(h.lb), "highs_wall_seconds": "" if h is None else round(h.wall_seconds, 3),
            "highs_timing_dependent": "" if h is None else bool(h.timing_dependent),
            "highs_agreement": "" if rec["comparison"] is None else rec["comparison"].label,
            "mtz_status": "" if m is None else m.status, "mtz_value": "" if m is None else _opt(m.ub),
            "mtz_wall_seconds": "" if m is None else round(m.wall_seconds, 3),
            "mtz_agreement": "" if rec["mtz_comparison"] is None else rec["mtz_comparison"].label,
        })
    return rows


def _cell(v):
    return str(v).lower() if isinstance(v, bool) else v


def write_reference_csv(path, rows) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(REFERENCE_CSV_FIELDS), lineterminator="\n", extrasaction="raise")
        wr.writeheader()
        wr.writerows({k: _cell(v) for k, v in r.items()} for r in rows)


def tours_document(records) -> dict:
    tours = {}
    for rec in records:
        p, s = rec["primary"], rec["spec"]
        if p.tour is not None:
            tours[s.name] = {"n": s.n, "length": p.ub, "status": p.status, "solver": p.solver,
                             "tour": [v + 1 for v in p.tour]}
    return {"schema_version": 1, "solution_kind": protocol.TSP_REFERENCE_SOLUTION_KIND, "node_base": 1,
            "note": "Node ids as in the TSPLIB files (1-based); the cycle is closed from the last node to the first.",
            "tours": tours}


def verify_tours(doc: dict, matrix_for, optimum_for=None) -> list:
    """Re-check a tours.json without a solver: every tour is a Hamiltonian cycle whose recomputed length equals
    the recorded one. ``matrix_for(name)`` returns the instance matrix. With ``optimum_for(name)`` (the published
    optimum) a proven (``optimal``) tour must have exactly that length and no tour may be shorter than it."""
    errors = []
    if doc.get("node_base") != 1:
        errors.append("node_base must be 1")
    for name, t in sorted(doc.get("tours", {}).items()):
        matrix = matrix_for(name)
        if len(matrix) != t.get("n"):
            errors.append(f"{name}: n {t.get('n')} differs from the instance size {len(matrix)}")
            continue
        zero_based = [v - 1 for v in t["tour"]]
        errors.extend(f"{name}: {e}" for e in tsp.validate_tour(matrix, zero_based, t.get("length")))
        if optimum_for is not None:
            published = optimum_for(name)
            length = t.get("length")
            if published is None:
                errors.append(f"{name}: no published optimum to compare the tour length with")
            elif t.get("status", "optimal") == "optimal" and length != published:
                errors.append(f"{name}: tour length {length} differs from the published optimum {published}")
            elif length is not None and length < published:
                errors.append(f"{name}: tour length {length} is shorter than the published optimum {published}")
    return errors


def geo_pi_sensitivity(name: str, matrix, coords, primary, *, solve, blocking: bool) -> tuple:
    """Re-solve a GEO instance with pi = 3.141592 (the TSPLIB95 printed value) when that changes any arc. Returns
    (note, blocking errors): a proven optimum that differs from the primary proven optimum, or a failed re-solve, blocks
    when ``blocking``; an unproven re-solve is recorded and does not block."""
    variant = geo_pi_variant_matrix(coords, TSPLIB_GEO_PI)
    differing = count_differing_arcs(matrix, variant)
    n = len(matrix)
    note = {"pi": TSPLIB_GEO_PI, "arcs_differing": differing, "arcs_total": n * (n - 1)}
    if not differing:
        note["outcome"] = "identical_matrix"
        return note, []
    alt = solve(variant)
    note.update({"status": alt.status, "ub": alt.ub, "lb": alt.lb})
    problem = None
    if alt.status in ("rejected", "infeasible_proven", "backend_unavailable", "not_run"):
        note["outcome"] = "failed"
        problem = f"{name}: GEO pi {TSPLIB_GEO_PI} sensitivity re-solve failed (status {alt.status}; {alt.note or 'no note'})"
    elif alt.status == "optimal" and primary.status == "optimal":
        if alt.ub == primary.ub:
            note["outcome"] = "same_optimum"
        else:
            note["outcome"] = "different_optimum"
            problem = (f"{name}: GEO pi {TSPLIB_GEO_PI} gives the proven optimum {alt.ub}, math.pi gives {primary.ub}: "
                       "the result depends on the constant")
    else:
        note["outcome"] = "unproven"
    return note, ([problem] if problem and blocking else [])


def build_manifest(records, *, instances, git, versions, provenance, total_wall_seconds, mtz_limit_seconds, published_source,
                   started_utc, ended_utc, budget_seconds=BUDGET_SECONDS, extra=None) -> dict:
    def solver_block(name, label):
        settings = ab.SolverSettings(solver=name, seed=SEED, wall_limit=budget_seconds, work_limit=None, peak_work_limit=None)
        return {"name": name, "version": versions[label], "option_string": ab.solver_option_string(settings, peak=False),
                "threads": settings.threads, "seed": settings.seed, "time_limit_seconds": int(budget_seconds),
                "work_limit": None, "mip_gap": settings.mip_gap, "mip_gap_abs": settings.mip_gap_abs}

    instances = {r["spec"].name: {"problem_type": r["spec"].problem_type, "n": r["spec"].n,
                                  "edge_weight_type": r["spec"].edge_weight_type,
                                  "published_optimum": r["spec"].published_optimum,
                                  "published_source": r["spec"].published_source, **instances.get(r["spec"].name, {})}
                 for r in records}
    blocking = [b for r in records for b in r["blocking"]]
    counts = {}
    for r in records:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    manifest = {
        "protocol": protocol.PROTOCOL_ID, "manifest_kind": protocol.TSP_REFERENCE_KIND,
        "schema_version": protocol.TSP_REFERENCE_SCHEMA_VERSION, "work_package": "WP-E7",
        "solution_kind": protocol.TSP_REFERENCE_SOLUTION_KIND, "git_commit": git["commit"],
        "dirty_working_tree": bool(git["dirty"]),
        "ampl": {"version": versions["ampl"], "amplpy_version": versions["amplpy"], "location": versions["ampl_location"]},
        "solvers": {"gurobi": solver_block("gurobi", "gurobi"), "highs": solver_block("highs", "highs")},
        "limits": {"total_seconds_per_instance": int(budget_seconds), "threads": 1, "seed": SEED,
                   "mtz_limit_seconds": mtz_limit_seconds, "mtz_max_n": MTZ_MAX_N,
                   "budget_rule": "one wall-clock budget per instance and solver; every cut-loop re-solve gets the time "
                                  "that remains (lim:time in the option string is the first solve's value)",
                   "run_mode": "serial, one invocation, no cache"},
        "run_history": {"invocations_in_this_manifest": 1, "started_utc": started_utc, "ended_utc": ended_utc,
                        "serial": True, "cache": "none", "retries": 0},
        "instances": instances, "published_optimum_source": published_source, "python_provenance": provenance,
        "python_version": platform.python_version(), "host_os": f"{platform.system()}-{platform.release()}",
        "claim": protocol.TSP_REFERENCE_CLAIM, "blocking_errors": blocking, "total_wall_seconds": round(total_wall_seconds, 1),
        "verdicts": counts,
    }
    manifest.update(extra or {})
    return manifest


def build_readme(records, manifest) -> str:
    rows = reference_rows(records)
    sources = {}
    for inst in manifest["instances"].values():
        sources[inst["data_source"]] = sources.get(inst["data_source"], 0) + 1
    lines = ["# TSPLIB exact reference, stage 1 verification", "",
             "Facts of one run of `scripts/run_exact_tsp_reference.py` (WP-E7, DECISION_LOG E09). This is a verification "
             "subset, not a paper instance set: the 16 TSPLIB TSP instances with n <= 100 and a published optimum, plus the "
             "ATSP instance ft53. Its purpose is to check the exact cut-loop solver and the TSPLIB distance convention "
             "against published optima. No superiority claim is made.", "",
             f"- Commit `{manifest['git_commit'][:12]}`, working tree dirty: {str(manifest['dirty_working_tree']).lower()}.",
             f"- Solvers: {manifest['solvers']['gurobi']['version']} (primary), {manifest['solvers']['highs']['version']} "
             f"(re-solve of every instance Gurobi proved optimal), {manifest['ampl']['version']}, amplpy "
             f"{manifest['ampl']['amplpy_version']}.",
             f"- Limits: {manifest['limits']['total_seconds_per_instance']} s wall time in total per instance and solver (all cut-loop "
             "re-solves together), 1 thread, seed 0. MTZ (a single solve) cross-checks instances with n <= 40.",
             "- Model: DFJ subtour cuts added iteratively; edge variables for symmetric instances, arc variables for ft53.",
             "- The published value is a reference value (`reference_optimum`, source `tsplib`); a row is `optimal` only when the "
             "solver proved it. `reference.csv` has one row per instance; `tours.json` holds the tours "
             "(`--verify-tours` re-checks them without a solver); `manifest.json` holds versions, option strings, the sha256 of "
             "every instance input and the published-value sources.",
             f"- Instances in this run: {len(rows)}. Instance data: {sources.get('tsp_file', 0)} from `.tsp` files, "
             f"{sources.get('atsp_file', 0)} from `.atsp` files, {sources.get('tsplib_db_coordinates', 0)} from the node coordinates "
             "in the read-only database (no `.tsp` file in the checkout; the manifest records the sha256 of the canonical "
             "coordinate text instead of a file hash).",
             f"- Verdicts: {json.dumps(manifest['verdicts'], sort_keys=True)}; blocking errors: {len(manifest['blocking_errors'])}.", "",
             "| instance | n | published | status | UB | LB | verdict | HiGHS | rounds | cuts | wall s |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['instance']} | {r['n']} | {r['reference_optimum']} | {r['exact_status']} | {r['ub']} | {r['lb']} | "
                     f"{r['verdict']} | {r['highs_agreement'] or '-'} | {r['cut_rounds']} | {r['cuts']} | {r['wall_seconds']} |")
    if manifest["blocking_errors"]:
        lines += ["", "Blocking errors:"] + [f"- {b}" for b in manifest["blocking_errors"]]
    lines += ["", "Published-value sources: the table `problems.optimal` of the local TSPLIB database (read-only), cross-checked "
              "against `TSPLIB_OPTIMALS` in the repo's TSPLIB parser module and, for ft53, the ATSP collection manifest."]
    return "\n".join(lines) + "\n"


def _write_text(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def write_outputs(out: Path, records, manifest: dict, readme: str) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    _write_text(out / "tours.json", json.dumps(tours_document(records), indent=2, sort_keys=True) + "\n")
    write_reference_csv(out / "reference.csv", reference_rows(records))
    _write_text(out / "README.md", readme)
    manifest = dict(manifest)
    manifest["outputs"] = {name: _sha256_file(out / name) for name in ("README.md", "reference.csv", "tours.json")}
    _write_text(out / protocol.TSP_REFERENCE_MANIFEST_FILENAME, json.dumps(manifest, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------- run helpers
def check_out_dir(out, repo: Path = REPO) -> str:
    """Refusal message for an output directory that is not strictly below docs/paper/results (E04), else ''.
    The dirty-tree flag excludes the output directory, so it must not be able to hide real changes."""
    out_r, repo_r = Path(out).resolve(), Path(repo).resolve()
    results = repo_r / RESULTS_REL
    if out_r == results or results not in out_r.parents:
        return f"--out must lie strictly below {RESULTS_REL}/ inside the repository"
    return ""


def git_state(out, repo: Path = REPO) -> tuple:
    """(full commit, dirty flag); files under the output directory do not count."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout.strip()

    spec = ["status", "--porcelain", "--", ".", f":(exclude){Path(out).resolve().relative_to(Path(repo).resolve()).as_posix()}"]
    return git("rev-parse", "HEAD"), bool(git(*spec))


def dirty_refusal(*, dirty: bool, allow_dirty: bool) -> str:
    if dirty and not allow_dirty:
        return "the working tree is dirty; results must come from a clean commit (E06). --allow-dirty is for development runs only"
    return ""


def provenance() -> dict:
    """Repo-relative files of the packages that were imported (they must come from this checkout)."""
    import academic_benchmark
    import uniride_core

    out = {}
    for name, mod in (("uniride_core", uniride_core), ("academic_benchmark", academic_benchmark)):
        try:
            out[name] = Path(mod.__file__).resolve().relative_to(REPO).as_posix()
        except ValueError as exc:
            raise RuntimeError(f"{name} is imported from outside this checkout ({exc}); set PYTHONPATH to the repo root") from exc
    return out


_ARCHIVE_NOTE = "any path component named archive (any letter case) is refused, exit 2"


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help=f"directory with tsplib.db and the instance files; {_ARCHIVE_NOTE}")
    ap.add_argument("--instances", default="", help="comma list of instance names (default: the whole verification set)")
    ap.add_argument("--allow-dirty", action="store_true", help="development runs only; the manifest records the dirty flag")
    ap.add_argument("--highs-verify", action=argparse.BooleanOptionalAction, default=True,
                    help="re-solve every Gurobi-optimal instance with HiGHS (default: on)")
    ap.add_argument("--budget-seconds", type=float, default=BUDGET_SECONDS,
                    help="total wall time per instance and solver (the protocol value is 600; another value makes the manifest invalid)")
    ap.add_argument("--geo-pi-blocking", action=argparse.BooleanOptionalAction, default=True,
                    help="a proven optimum that differs under pi = 3.141592 is a blocking error (default: on)")
    ap.add_argument("--tsp-dir", default=str(TSP_DIR),
                    help=f"active instance collection (MANIFEST.json + .tsp files); {_ARCHIVE_NOTE}")
    ap.add_argument("--opt-tour-dir", default=str(OPT_TOUR_DIR),
                    help=f"active published-tour collection (MANIFEST.json + .opt.tour files); {_ARCHIVE_NOTE}")
    ap.add_argument("--verify-tours", default="", metavar="DIR",
                    help=f"re-check DIR/tours.json against the instance data; no AMPL; {_ARCHIVE_NOTE}")
    return ap.parse_args(argv)


def collection_specs(tsp_dir=TSP_DIR) -> dict:
    """Instance specs of the verification set from the manifests alone (no database): the TSP collection with its
    published optima, plus the ATSP instances of ``ATSP_NAMES`` from the ATSP collection manifest."""
    specs = {}
    for e in inputs.tsp_entries(tsp_dir):
        specs[e["name"]] = InstanceSpec(e["name"], e["problem_type"], int(e["dimension"]), e["edge_weight_type"],
                                        int(e["published_optimum"]), "tsplib")
    for e in inputs.atsp_entries():
        if e["name"] in ATSP_NAMES:
            specs[e["name"]] = InstanceSpec(e["name"], "ATSP", int(e["dimension"]), e["edge_weight_type"], int(e["optimal"]), "tsplib")
    return specs


def archive_input_refusal(args) -> str:
    """Refusal message when an input path of the command line lies in the archive directory, else ''."""
    for flag, value in (("--data-dir", args.data_dir), ("--tsp-dir", args.tsp_dir), ("--opt-tour-dir", args.opt_tour_dir),
                        ("--verify-tours", args.verify_tours)):
        if value:
            message = inputs.archive_refusal(value)
            if message:
                return f"{flag}: {message}"
    return ""


def _verify_tours_cli(args) -> int:
    """Re-check tours.json from the committed collections only: instances, published optima and tours come from the
    manifests; the database is never opened."""
    data_dir = Path(args.data_dir)
    doc = json.loads((Path(args.verify_tours) / "tours.json").read_text(encoding="utf-8"))
    tsp_dir, tour_dir = Path(args.tsp_dir), Path(args.opt_tour_dir)
    try:
        specs = collection_specs(tsp_dir)
    except (ValueError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    cache = {}

    def matrix_for(name):
        if name not in cache:
            cache[name] = load_instance(specs[name], data_dir, None, tour_dir, tsp_dir)[0]
        return cache[name]

    try:
        errors = verify_tours(doc, matrix_for,
                              optimum_for=lambda name: specs[name].published_optimum if name in specs else None)
    except (ValueError, ConventionError, KeyError, OSError) as exc:
        errors = [f"cannot verify: {exc}"]
    print(f"tours checked: {len(doc.get('tours', {}))}; errors: {len(errors)}")
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    return 1 if errors else 0


def main(argv=None) -> int:
    args = parse_args(argv)
    refusal = archive_input_refusal(args)
    if refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    if args.verify_tours:
        return _verify_tours_cli(args)
    out = Path(args.out)
    refusal = check_out_dir(out)
    if refusal:
        print(f"refused: {refusal} (got {out})", file=sys.stderr)
        return 2
    commit, dirty = git_state(out)
    refusal = dirty_refusal(dirty=dirty, allow_dirty=args.allow_dirty)
    if refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    refusal = wal_refusal(Path(args.data_dir) / DB_NAME)
    if refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    gurobi = ab.AmplSession(ab.SolverSettings(solver="gurobi", seed=SEED, work_limit=None, peak_work_limit=None))
    highs = ab.AmplSession(ab.SolverSettings(solver="highs", seed=SEED, work_limit=None, peak_work_limit=None)) \
        if args.highs_verify else None
    sessions = [s for s in (gurobi, highs) if s is not None]
    try:
        for s in sessions:
            try:
                s.open()
            except ab.ExactBackendUnavailable as exc:
                print(f"backend unavailable ({s.settings.solver}): {exc}; GOAL 2 needs AMPL with Gurobi and HiGHS "
                      f"(set UNIRIDE_AMPL_DIR)", file=sys.stderr)
                return 3
        return _run(args, out, commit, dirty, gurobi, highs)
    finally:
        for s in sessions:
            s.close()


def _run(args, out: Path, commit: str, dirty: bool, gurobi, highs) -> int:
    t_start = time.perf_counter()
    started_utc = utc_stamp()
    data_dir = Path(args.data_dir)
    db_path = data_dir / DB_NAME
    if not db_path.is_file():
        print("refused: tsplib.db not found in --data-dir", file=sys.stderr)
        return 2
    conn = open_db_readonly(db_path)
    try:
        specs = read_instance_set(conn)
        wanted = [w for w in args.instances.split(",") if w]
        if wanted:
            unknown = sorted(set(wanted) - {s.name for s in specs})
            if unknown:
                print(f"refused: unknown instances {unknown}", file=sys.stderr)
                return 2
        else:
            check_instance_set(specs)
        try:
            mismatches = cross_check_manifest_specs(specs, collection_specs(Path(args.tsp_dir)))
        except (ValueError, OSError) as exc:  # inputs.InputRefused is a ValueError
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        if mismatches:
            for m in mismatches:
                print(f"refused: {m}", file=sys.stderr)
            return 2
        discrepancies = cross_check_optima(specs, parser_optima(), atsp_manifest_optima())
        specs = [s for s in specs if not wanted or s.name in wanted]
        loaded = {}
        for s in specs:
            try:
                loaded[s.name] = load_instance(s, data_dir, conn, Path(args.opt_tour_dir), Path(args.tsp_dir))
            except (ValueError, FileNotFoundError, ConventionError) as exc:  # inputs.InputRefused is a ValueError
                print(f"refused: {s.name}: {exc}", file=sys.stderr)
                return 2
    finally:
        conn.close()

    budget = float(args.budget_seconds)
    records, instances, geo_notes = [], {}, {}
    for s in specs:
        matrix, coords, data_rec = loaded[s.name]
        instances[s.name] = {"matrix_sha256": matrix_sha256(matrix), **data_rec}
        rec = evaluate_instance(
            s, matrix,
            solve_primary=lambda m: tsp.solve_tsp(m, session=gurobi, budget_seconds=budget),
            solve_secondary=(lambda m: tsp.solve_tsp(m, session=highs, budget_seconds=budget)) if highs is not None else None,
            solve_mtz=(lambda m: tsp.solve_tsp_mtz(m, session=gurobi, time_limit=MTZ_SECONDS)) if s.n <= MTZ_MAX_N else None)
        records.append(rec)
        p = rec["primary"]
        print(f"{s.name:10s} n={s.n:3d} ref={s.published_optimum} {p.status} UB={p.ub} LB={p.lb} {rec['verdict']} "
              f"{p.wall_seconds:.1f}s highs={rec['comparison'].label if rec['comparison'] else '-'}", flush=True)
        if s.edge_weight_type == "GEO" and coords is not None:  # the TSPLIB95 document prints PI = 3.141592
            note, geo_blocking = geo_pi_sensitivity(
                s.name, matrix, coords, p, solve=lambda m: tsp.solve_tsp(m, session=gurobi, budget_seconds=budget),
                blocking=args.geo_pi_blocking)
            geo_notes[s.name] = note
            rec["blocking"].extend(geo_blocking)

    versions = {"ampl": gurobi.ampl_version, "amplpy": gurobi.amplpy_version, "ampl_location": gurobi.location,
                "gurobi": gurobi.solver_version, "highs": highs.solver_version if highs is not None else "not run"}
    published = {"table": "problems.optimal (read-only, immutable open)", "second_sources":
                 ["TSPLIB_OPTIMALS in uniride_core/algorithms/tsplib_parser.py", "academic_benchmark/tsplib_data/atsp/MANIFEST.json (ft53)"],
                 "cross_checks": ["problems.optimal vs the parser table for every instance", "ft53 vs the ATSP manifest"],
                 "discrepancies": discrepancies, "best_solutions_used": False,
                 "coordinate_cross_check": "the published optimal tour (committed opt_tours collection, sha256-checked) recomputed on the "
                                           "used coordinates equals problems.optimal; per instance in instances[].published_tour_check"}
    manifest = build_manifest(
        records, instances=instances, git={"commit": commit, "dirty": dirty}, versions=versions, provenance=provenance(),
        total_wall_seconds=time.perf_counter() - t_start, mtz_limit_seconds=MTZ_SECONDS, published_source=published,
        budget_seconds=budget, started_utc=started_utc, ended_utc=utc_stamp(),
        extra={"geo_pi_sensitivity": geo_notes, "database": database_record(db_path), "coordinate_text": coordinate_text_record(),
               "convention": convention_record(geo_pi_blocking=args.geo_pi_blocking),
               "highs_verify": highs is not None, "instance_filter": [s.name for s in specs]})
    problems = protocol.validate_tsp_reference_manifest(manifest)
    manifest["blocking_errors"] = list(manifest["blocking_errors"]) + [f"manifest: {p}" for p in problems] \
        + [f"published optimum discrepancy: {d}" for d in discrepancies]
    write_outputs(out, records, manifest, build_readme(records, manifest))
    print(json.dumps({"verdicts": manifest["verdicts"], "blocking_errors": len(manifest["blocking_errors"])}, sort_keys=True))
    return 1 if manifest["blocking_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
