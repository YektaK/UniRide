"""GOAL 2, stage 1 (WP-E7; DECISION_LOG E09; design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 5, 6, 8, 9):
reproduce the published TSPLIB optima of the 16 TSP instances with n <= 100 and ATSP ft53 with the exact DFJ
cut-loop solver, Gurobi primary and HiGHS re-solve.

Offline: reads the TSPLIB instance files (or, for instances without a file in the checkout, the node coordinates
in ``tsplib.db``) and the published optima in ``problems.optimal``; the database is opened strictly read-only and
immutable (``mode=ro&immutable=1``: no write, no -wal/-shm file). ``best_solutions`` (our own heuristic runs) is
never read. Nothing is downloaded.

Each instance gets 600 s wall time in total (all cut-loop re-solves together), 1 thread, seed 0. The distance
convention (nint for EUC_2D, the ATT pseudo-Euclidean rule, the GEO rule) is asserted against an independent
transcription of TSPLIB95 before any solve. A published optimum must be reproduced (``optimal`` with that value) or
bracketed (LB <= optimum <= UB); anything else, and any HiGHS/MTZ contradiction, is a blocking defect (exit 1).
Exit codes: 0 all instances reproduced or bracketed; 1 blocking error; 2 refused (unsafe --out, dirty tree, bad
data); 3 AMPL, Gurobi or HiGHS unavailable.

Writes (strictly below docs/paper/results/, E04): reference.csv, tours.json, manifest.json, README.md. This is a
verification subset, not a paper instance set; exact rows are never pooled with heuristic rows; no superiority claim.
``--verify-tours DIR`` re-checks a tours.json without AMPL.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
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

from academic_benchmark.exact_reference import protocol  # noqa: E402
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
    """TSPLIB95 distance written from the document, independent of ``uniride_core.algorithms.distance``."""
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


# ---------------------------------------------------------------- tsplib.db (strictly read-only) and published optima
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


# ---------------------------------------------------------------- instance data
def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_instance(spec: InstanceSpec, data_dir: Path, conn) -> tuple:
    """(matrix, coordinates or None, data record). Instance files are used when present; otherwise the node
    coordinates in the read-only database (recorded as such). The convention is asserted here."""
    if spec.problem_type == "ATSP":
        for cand in (data_dir / f"{spec.name}.atsp", data_dir / "atsp" / f"{spec.name}.atsp"):
            if cand.is_file():
                matrix = load_atsp_matrix(cand.read_text(encoding="utf-8"), spec.name)
                if len(matrix) != spec.n:
                    raise ValueError(f"{spec.name}: file has {len(matrix)} nodes, database says {spec.n}")
                rec = {"data_source": "atsp_file", "file": cand.name, "sha256": _sha256_file(cand)}
                return matrix, None, rec
        raise FileNotFoundError(f"{spec.name}: no .atsp file in the data directory")
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
        canonical = "".join(f"{i} {x!r} {y!r}\n" for i, (x, y) in enumerate(coords)).encode("ascii")
        rec = {"data_source": "tsplib_db_coordinates", "file": None, "sha256": hashlib.sha256(canonical).hexdigest()}
    matrix = build_matrix(spec.edge_weight_type, coords)
    assert_convention(spec.edge_weight_type, coords, matrix)
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


def verify_tours(doc: dict, matrix_for) -> list:
    """Re-check a tours.json without a solver: every tour is a Hamiltonian cycle whose recomputed length equals
    the recorded one. ``matrix_for(name)`` returns the instance matrix."""
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
    return errors


def build_manifest(records, *, instances, git, versions, provenance, total_wall_seconds, mtz_limit_seconds, published_source,
                   budget_seconds=BUDGET_SECONDS, extra=None) -> dict:
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
        "instances": instances, "published_optimum_source": published_source, "python_provenance": provenance,
        "python_version": platform.python_version(), "host_os": f"{platform.system()}-{platform.release()}",
        "claim": protocol.TSP_REFERENCE_CLAIM, "blocking_errors": blocking, "total_wall_seconds": round(total_wall_seconds, 1),
        "verdicts": counts,
    }
    manifest.update(extra or {})
    return manifest


def build_readme(records, manifest) -> str:
    rows = reference_rows(records)
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


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="directory with tsplib.db and the instance files")
    ap.add_argument("--instances", default="", help="comma list of instance names (default: the whole verification set)")
    ap.add_argument("--allow-dirty", action="store_true", help="development runs only; the manifest records the dirty flag")
    ap.add_argument("--highs-verify", action=argparse.BooleanOptionalAction, default=True,
                    help="re-solve every Gurobi-optimal instance with HiGHS (default: on)")
    ap.add_argument("--budget-seconds", type=float, default=BUDGET_SECONDS,
                    help="total wall time per instance and solver (the protocol value is 600; another value makes the manifest invalid)")
    ap.add_argument("--verify-tours", default="", metavar="DIR", help="re-check DIR/tours.json against the instance data; no AMPL")
    return ap.parse_args(argv)


def _verify_tours_cli(args) -> int:
    data_dir = Path(args.data_dir)
    doc = json.loads((Path(args.verify_tours) / "tours.json").read_text(encoding="utf-8"))
    conn = open_db_readonly(data_dir / DB_NAME)
    try:
        specs = {s.name: s for s in read_instance_set(conn)}
        cache = {}

        def matrix_for(name):
            if name not in cache:
                cache[name] = load_instance(specs[name], data_dir, conn)[0]
            return cache[name]

        errors = verify_tours(doc, matrix_for)
    finally:
        conn.close()
    print(f"tours checked: {len(doc.get('tours', {}))}; errors: {len(errors)}")
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    return 1 if errors else 0


def main(argv=None) -> int:
    args = parse_args(argv)
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
        discrepancies = cross_check_optima(specs, parser_optima(), atsp_manifest_optima())
        specs = [s for s in specs if not wanted or s.name in wanted]
        loaded = {}
        for s in specs:
            try:
                loaded[s.name] = load_instance(s, data_dir, conn)
            except (ValueError, FileNotFoundError, ConventionError) as exc:
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
        if s.edge_weight_type == "GEO" and coords is not None:  # informational: the TSPLIB95 document prints PI = 3.141592
            variant = geo_pi_variant_matrix(coords, TSPLIB_GEO_PI)
            differing = count_differing_arcs(matrix, variant)
            note = {"pi": TSPLIB_GEO_PI, "arcs_differing": differing, "arcs_total": s.n * (s.n - 1)}
            if differing:
                alt = tsp.solve_tsp(variant, session=gurobi, budget_seconds=budget)
                note.update({"status": alt.status, "ub": alt.ub, "lb": alt.lb})
            geo_notes[s.name] = note

    versions = {"ampl": gurobi.ampl_version, "amplpy": gurobi.amplpy_version, "ampl_location": gurobi.location,
                "gurobi": gurobi.solver_version, "highs": highs.solver_version if highs is not None else "not run"}
    published = {"table": "problems.optimal (read-only, immutable open)", "second_sources":
                 ["TSPLIB_OPTIMALS in uniride_core/algorithms/tsplib_parser.py", "academic_benchmark/tsplib_data/atsp/MANIFEST.json (ft53)"],
                 "cross_checks": ["problems.optimal vs the parser table for every instance", "ft53 vs the ATSP manifest"],
                 "discrepancies": discrepancies, "best_solutions_used": False}
    manifest = build_manifest(
        records, instances=instances, git={"commit": commit, "dirty": dirty}, versions=versions, provenance=provenance(),
        total_wall_seconds=time.perf_counter() - t_start, mtz_limit_seconds=MTZ_SECONDS, published_source=published,
        budget_seconds=budget,
        extra={"geo_pi_sensitivity": geo_notes,
               "convention": {"EUC_2D": "nint", "ATT": "pseudo-Euclidean (TSPLIB95)", "GEO": "TSPLIB95 GEO with math.pi (T06/O02)",
                              "asserted": "every arc against an independent transcription, before any solve"},
               "highs_verify": highs is not None, "instance_filter": [s.name for s in specs]})
    problems = protocol.validate_tsp_reference_manifest(manifest)
    manifest["blocking_errors"] = list(manifest["blocking_errors"]) + [f"manifest: {p}" for p in problems] \
        + [f"published optimum discrepancy: {d}" for d in discrepancies]
    write_outputs(out, records, manifest, build_readme(records, manifest))
    print(json.dumps({"verdicts": manifest["verdicts"], "blocking_errors": len(manifest["blocking_errors"])}, sort_keys=True))
    return 1 if manifest["blocking_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
