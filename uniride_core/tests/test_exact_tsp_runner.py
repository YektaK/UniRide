"""WP-E7 (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 4, 5, 6, 8, 9; DECISION_LOG E04, E06, E09): the
GOAL 2 stage-1 runner ``scripts/run_exact_tsp_reference.py`` (16 TSPLIB TSP instances with n <= 100 and a
published optimum, plus ATSP ft53).

Everything here runs without AMPL and without the git-ignored TSPLIB data. Tests that read the local
``tsplib.db`` (git-ignored) or ``*.tsp`` files skip with a reason when they are absent (CI).
"""
from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import json
import math
import os
import random
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run_exact_tsp_reference.py"
# the data live in the main checkout (git-ignored there); a worktree reads them through this variable
DATA_DIR = Path(os.environ.get("UNIRIDE_TSPLIB_DATA_DIR", REPO / "academic_benchmark" / "tsplib_data"))
DB_PATH = DATA_DIR / "tsplib.db"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_exact_tsp_reference", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_exact_tsp_reference"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load_script()


def _tsp():
    from uniride_core.exact import tsp

    return tsp


# ---------------------------------------------------------------- independent TSPLIB95 distance transcription
def spec_euc2d(p, q):
    return int(math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) + 0.5)


def spec_att(p, q):
    rij = math.sqrt(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) / 10.0)
    tij = int(rij + 0.5)
    return tij + 1 if tij < rij else tij


def spec_geo(p, q, pi=math.pi):
    def ll(x):
        deg = int(x)
        return pi * (deg + 5.0 * (x - deg) / 3.0) / 180.0

    la1, lo1, la2, lo2 = ll(p[0]), ll(p[1]), ll(q[0]), ll(q[1])
    q1, q2, q3 = math.cos(lo1 - lo2), math.cos(la1 - la2), math.cos(la1 + la2)
    return int(6378.388 * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)


SPEC = {"EUC_2D": spec_euc2d, "ATT": spec_att, "GEO": spec_geo}


def _random_coords(ewt, n, seed):
    rng = random.Random(seed)
    if ewt == "GEO":  # DD.MM with minutes below 60
        return [(rng.randint(-60, 60) + rng.randint(0, 59) / 100.0, rng.randint(-170, 170) + rng.randint(0, 59) / 100.0)
                for _ in range(n)]
    return [(rng.randint(0, 40) / 2.0, rng.randint(0, 40) / 2.0) for _ in range(n)]  # many exact .5 distances


# ---------------------------------------------------------------- distance convention
def test_nint_rounds_half_up_not_down_and_not_to_even(runner):
    m = runner.build_matrix("EUC_2D", [(0.0, 0.0), (1.5, 2.0), (3.0, 4.0), (1.0, 1.0)])
    assert m[0][1] == 3, "2.5 rounds up to 3 (nint), not down to 2"
    assert m[0][2] == 5 and m[0][3] == 1
    assert runner.spec_distance("EUC_2D", (0.0, 0.0), (1.5, 2.0)) == 3
    assert runner.spec_distance("EUC_2D", (0.0, 0.0), (0.5, 0.0)) == 1  # 0.5 -> 1


def test_att_pseudo_euclidean_rule_rounds_up_when_nint_falls_short(runner):
    m = runner.build_matrix("ATT", [(0.0, 0.0), (10.0, 0.0)])
    assert m[0][1] == 4, "sqrt(100/10) = 3.162: nint 3 < 3.162, so the ATT rule gives 4"
    assert runner.spec_distance("ATT", (0.0, 0.0), (10.0, 0.0)) == 4


@pytest.mark.parametrize("ewt", ["EUC_2D", "ATT", "GEO"])
def test_every_arc_equals_the_independent_tsplib_transcription(runner, ewt):
    coords = _random_coords(ewt, 14, seed=3)
    m = runner.build_matrix(ewt, coords)
    for i in range(len(coords)):
        for j in range(len(coords)):
            want = 0 if i == j else SPEC[ewt](coords[i], coords[j])
            assert m[i][j] == want, (ewt, i, j)
    runner.assert_convention(ewt, coords, m)  # does not raise


@pytest.mark.parametrize("ewt", ["EUC_2D", "ATT", "GEO"])
def test_assert_convention_rejects_a_matrix_that_does_not_follow_the_convention(runner, ewt):
    coords = _random_coords(ewt, 14, seed=4)
    m = [list(r) for r in runner.build_matrix(ewt, coords)]
    m[2][5] += 1
    with pytest.raises(runner.ConventionError):
        runner.assert_convention(ewt, coords, tuple(tuple(r) for r in m))


def test_assert_convention_rejects_floor_rounding(runner):
    coords = _random_coords("EUC_2D", 14, seed=5)
    floor_m = tuple(tuple(0 if i == j else int(math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1]))
                          for j in range(14)) for i in range(14))
    with pytest.raises(runner.ConventionError):
        runner.assert_convention("EUC_2D", coords, floor_m)


def test_unsupported_edge_weight_type_is_refused(runner):
    with pytest.raises(ValueError):
        runner.build_matrix("CEIL_2D", [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)])


def test_explicit_atsp_matrix_is_the_file_matrix_row_major(runner):
    text = "NAME: t\nTYPE: ATSP\nDIMENSION: 3\nEDGE_WEIGHT_TYPE: EXPLICIT\nEDGE_WEIGHT_FORMAT: FULL_MATRIX\n" \
           "EDGE_WEIGHT_SECTION\n 9999999 5 7\n 2 9999999 11\n 13 17 9999999\nEOF\n"
    m = runner.load_atsp_matrix(text, "t")
    assert m[0][1] == 5 and m[1][0] == 2 and m[0][2] == 7 and m[2][0] == 13 and m[1][2] == 11 and m[2][1] == 17
    assert m[0][1] != m[1][0], "asymmetric entries are not symmetrised"


def test_real_ft53_matrix_arcs_equal_the_file_tokens():
    path = DATA_DIR / "ft53.atsp"
    if not path.is_file():
        pytest.skip("ft53.atsp not present in this checkout")
    runner = _load_script()
    text = path.read_text(encoding="utf-8")
    body = text.split("EDGE_WEIGHT_SECTION", 1)[1].split("EOF", 1)[0].split()
    m = runner.load_atsp_matrix(text, "ft53")
    assert len(m) == 53 and len(body) == 53 * 53
    for i, j in ((0, 1), (1, 0), (5, 40), (40, 5), (52, 0), (0, 52), (26, 27)):
        assert m[i][j] == int(body[i * 53 + j])
    assert any(m[i][j] != m[j][i] for i in range(53) for j in range(i))


@pytest.mark.parametrize("name,ewt", [("berlin52", "EUC_2D"), ("att48", "ATT"), ("burma14", "GEO"), ("gr96", "GEO")])
def test_real_instances_follow_the_convention(name, ewt):
    if not DB_PATH.is_file():
        pytest.skip("tsplib.db not present in this checkout (git-ignored)")
    runner = _load_script()
    conn = runner.open_db_readonly(DB_PATH)
    try:
        coords = runner.read_db_coordinates(conn, name)
        stored = conn.execute("select edge_weight_type from problems where name=?", (name,)).fetchone()[0]
    finally:
        conn.close()
    assert stored == ewt
    m = runner.build_matrix(ewt, coords)
    for i, j in ((0, 1), (1, 0), (3, 7), (7, 3), (len(coords) - 1, 0), (0, len(coords) - 1)):
        assert m[i][j] == SPEC[ewt](coords[i], coords[j])
    runner.assert_convention(ewt, coords, m)


# ---------------------------------------------------------------- tsplib.db is opened strictly read-only
def _make_wal_db(path: Path):
    conn = sqlite3.connect(path)
    conn.execute("pragma journal_mode=wal")
    conn.executescript("""
        create table problems (name text primary key, dimension integer not null, optimal integer, category text,
            edge_weight_type text not null default 'EUC_2D', problem_type text default 'TSP', source text default 'tsplib',
            coords_hash text, tsp_file text, extracted_at text);
        create table coordinates (problem_name text not null, node_idx integer not null, x real not null, y real not null,
            primary key (problem_name, node_idx));
    """)
    rows = [("a10", 10, 100, "EUC_2D", "TSP"), ("b99", 99, 500, "GEO", "TSP"), ("c99", 99, None, "EUC_2D", "TSP"),
            ("d101", 101, 700, "EUC_2D", "TSP"), ("ft53", 53, 6905, "EXPLICIT", "ATSP"), ("ftv33", 34, 1286, "EXPLICIT", "ATSP"),
            ("e5", 5, 9, "ATT", "TSP")]
    conn.executemany("insert into problems (name, dimension, optimal, edge_weight_type, problem_type) values (?,?,?,?,?)", rows)
    conn.executemany("insert into coordinates values ('a10', ?, ?, ?)", [(i, float(i), float(i * 2)) for i in range(3)])
    conn.commit()
    conn.close()


def _listing(directory: Path):
    return sorted(p.name for p in directory.iterdir())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_open_db_readonly_refuses_writes_and_leaves_no_file_behind(runner, tmp_path):
    db = tmp_path / "tsplib.db"
    _make_wal_db(db)
    before_listing, before_sha = _listing(tmp_path), _sha(db)
    conn = runner.open_db_readonly(db)
    try:
        assert conn.execute("select count(*) from problems").fetchone()[0] == 7
        for sql in ("create table z(a)", "insert into problems (name, dimension) values ('x', 3)",
                    "update problems set optimal = 1", "delete from problems"):
            with pytest.raises(sqlite3.OperationalError):
                conn.execute(sql)
                conn.commit()
    finally:
        conn.close()
    assert _listing(tmp_path) == before_listing, "a read-only open must not create -wal or -shm files"
    assert _sha(db) == before_sha


def test_open_db_readonly_does_not_use_the_default_read_write_mode(runner, tmp_path):
    db = tmp_path / "x.db"
    _make_wal_db(db)
    conn = runner.open_db_readonly(db)
    try:
        assert conn.execute("pragma query_only").fetchone() is not None
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("create table t(a)")
    finally:
        conn.close()


def test_read_instance_set_keeps_tsp_up_to_100_nodes_with_a_published_optimum_plus_ft53(runner, tmp_path):
    db = tmp_path / "t.db"
    _make_wal_db(db)
    conn = runner.open_db_readonly(db)
    try:
        specs = runner.read_instance_set(conn)
    finally:
        conn.close()
    assert [s.name for s in specs] == ["e5", "a10", "ft53", "b99"], "sorted by (dimension, name); no c99 (no optimum), no d101 (n > 100), only ft53 of the ATSP"
    by = {s.name: s for s in specs}
    assert (by["ft53"].problem_type, by["ft53"].published_optimum, by["ft53"].n) == ("ATSP", 6905, 53)
    assert (by["b99"].edge_weight_type, by["b99"].published_optimum, by["b99"].published_source) == ("GEO", 500, "tsplib")


def test_the_real_instance_set_is_the_16_tsp_plus_ft53():
    if not DB_PATH.is_file():
        pytest.skip("tsplib.db not present in this checkout (git-ignored)")
    runner = _load_script()
    conn = runner.open_db_readonly(DB_PATH)
    try:
        specs = runner.read_instance_set(conn)
    finally:
        conn.close()
    assert [s.name for s in specs if s.problem_type == "TSP"] == list(runner.EXPECTED_TSP_NAMES)
    assert len(runner.EXPECTED_TSP_NAMES) == 16 and [s.name for s in specs if s.problem_type == "ATSP"] == ["ft53"]
    runner.check_instance_set(specs)


def test_check_instance_set_refuses_a_changed_set(runner):
    specs = [runner.InstanceSpec("x", "TSP", 10, "EUC_2D", 5, "tsplib")]
    with pytest.raises(ValueError):
        runner.check_instance_set(specs)


# ---------------------------------------------------------------- published values: second source
def test_cross_check_of_published_optima_reports_every_discrepancy(runner):
    specs = [runner.InstanceSpec("eil51", "TSP", 51, "EUC_2D", 426, "tsplib"),
             runner.InstanceSpec("ft53", "ATSP", 53, "EXPLICIT", 6905, "tsplib")]
    ok = runner.cross_check_optima(specs, {"eil51": 426, "ft53": 6905}, {"ft53": 6905})
    assert ok == []
    bad = runner.cross_check_optima(specs, {"eil51": 427, "ft53": 6905}, {"ft53": 6900})
    assert any("eil51" in s and "427" in s for s in bad) and any("ft53" in s and "6900" in s for s in bad)
    missing = runner.cross_check_optima(specs, {"ft53": 6905}, {"ft53": 6905})
    assert any("eil51" in s for s in missing)


def test_the_repo_parser_table_agrees_with_the_database_for_the_verification_set():
    if not DB_PATH.is_file():
        pytest.skip("tsplib.db not present in this checkout (git-ignored)")
    runner = _load_script()
    conn = runner.open_db_readonly(DB_PATH)
    try:
        specs = runner.read_instance_set(conn)
    finally:
        conn.close()
    assert runner.cross_check_optima(specs, runner.parser_optima(), runner.atsp_manifest_optima()) == []


# ---------------------------------------------------------------- verdict and per-instance evaluation
def _mini():
    n = 6
    m = tuple(tuple(0 if i == j else (1 if (i < 3) == (j < 3) else 10) for j in range(n)) for i in range(n))
    return m


def _res(status="optimal", ub=24, lb=24, tour="auto", solver="gurobi", **kw):
    tsp = _tsp()
    if tour == "auto":  # a proven result carries its tour; a time-limited fake carries none unless given
        tour = (0, 1, 2, 3, 4, 5) if status == "optimal" else None
    kw.setdefault("stop_reason", "optimal" if status == "optimal" else "wall_limit")
    kw.setdefault("timing_dependent", status != "optimal")
    return tsp.TspResult(status=status, ub=ub, lb=lb, tour=tour, rounds=2, cuts=2, wall_seconds=0.5, solver=solver,
                         budget_seconds=600.0, **kw)


def _spec(runner, optimum=24):
    return runner.InstanceSpec("mini", "TSP", 6, "EUC_2D", optimum, "tsplib")


def test_verdict_reproduced_bracketed_and_defect(runner):
    assert runner.verdict(_res(), 24) == "reproduced"
    assert runner.verdict(_res(ub=25, lb=25), 24) == "defect", "an optimum that differs from the published value is a defect"
    assert runner.verdict(_res("feasible_with_gap", ub=30, lb=20), 24) == "bracketed"
    assert runner.verdict(_res("feasible_with_gap", ub=30, lb=25), 24) == "defect", "LB above the published optimum"
    assert runner.verdict(_res("feasible_with_gap", ub=23, lb=20), 24) == "defect", "a tour shorter than the published optimum"
    assert runner.verdict(_res("bound_only", ub=None, lb=20, tour=None), 24) == "not_bracketed"
    assert runner.verdict(_res("rejected", ub=None, lb=None, tour=None), 24) == "defect"


def test_a_proven_highs_difference_blocks_the_instance(runner):
    rec = runner.evaluate_instance(_spec(runner), _mini(), solve_primary=lambda m: _res(),
                                   solve_secondary=lambda m: _res(ub=25, lb=25, solver="highs", tour=None))
    assert rec["comparison"].label == "disagree"
    assert len(rec["blocking"]) == 1 and "HiGHS disagree" in rec["blocking"][0], rec["blocking"]  # the comparison alone blocks


def test_agreeing_highs_does_not_block_and_is_recorded(runner):
    rec = runner.evaluate_instance(_spec(runner), _mini(), solve_primary=lambda m: _res(),
                                   solve_secondary=lambda m: _res(solver="highs"))
    assert rec["blocking"] == [] and rec["comparison"].label == "agree" and rec["verdict"] == "reproduced"


def test_highs_is_run_for_every_optimal_primary_result_and_only_for_those(runner):
    calls = []

    def secondary(m):
        calls.append(1)
        return _res(solver="highs")

    runner.evaluate_instance(_spec(runner), _mini(), solve_primary=lambda m: _res(), solve_secondary=secondary)
    assert len(calls) == 1
    rec = runner.evaluate_instance(_spec(runner), _mini(),
                                   solve_primary=lambda m: _res("feasible_with_gap", ub=30, lb=20),
                                   solve_secondary=secondary)
    assert len(calls) == 1 and rec["comparison"] is None and rec["verdict"] == "bracketed"


def test_a_primary_optimum_different_from_the_published_value_is_a_blocking_defect(runner):
    rec = runner.evaluate_instance(_spec(runner, optimum=23), _mini(), solve_primary=lambda m: _res(),
                                   solve_secondary=lambda m: _res(solver="highs"))
    assert rec["verdict"] == "defect" and any("published" in b for b in rec["blocking"])


def test_a_primary_tour_that_is_invalid_for_the_matrix_blocks(runner):
    rec = runner.evaluate_instance(_spec(runner), _mini(), solve_primary=lambda m: _res(tour=(0, 1, 2, 3, 4, 4)),
                                   solve_secondary=lambda m: _res(solver="highs"))
    assert any("tour" in b for b in rec["blocking"])
    rec2 = runner.evaluate_instance(_spec(runner), _mini(), solve_primary=lambda m: _res(ub=23, lb=23),
                                    solve_secondary=lambda m: _res(solver="highs"))
    assert any("tour" in b for b in rec2["blocking"]), "reported length 23 differs from the recomputed 24"


def test_a_proven_mtz_difference_blocks_but_a_time_limited_mtz_does_not(runner):
    base = dict(solve_primary=lambda m: _res(), solve_secondary=lambda m: _res(solver="highs"))
    bad = runner.evaluate_instance(_spec(runner), _mini(), solve_mtz=lambda m: _res(ub=25, lb=25, tour=None), **base)
    assert len(bad["blocking"]) == 1 and "MTZ" in bad["blocking"][0], bad["blocking"]
    slow = runner.evaluate_instance(_spec(runner), _mini(),
                                    solve_mtz=lambda m: _res("feasible_with_gap", ub=30, lb=10), **base)
    assert slow["blocking"] == [] and slow["mtz_comparison"].label == "secondary_time_limited"


# ---------------------------------------------------------------- CSV and manifest
def _record(runner, name="mini", **kw):
    spec = runner.InstanceSpec(name, "TSP", 6, "EUC_2D", 24, "tsplib")
    return runner.evaluate_instance(spec, _mini(), solve_primary=lambda m: _res(**kw),
                                    solve_secondary=lambda m: _res(solver="highs"), solve_mtz=lambda m: _res())


def test_csv_schema_and_row_values(runner, tmp_path):
    recs = [_record(runner, "mini"), _record(runner, "other")]
    rows = runner.reference_rows(recs)
    assert list(rows[0]) == list(runner.REFERENCE_CSV_FIELDS)
    required = ("instance", "problem_type", "n", "edge_weight_type", "reference_optimum", "reference_source", "exact_status",
                "ub", "lb", "gap_to_reference", "cut_rounds", "cuts", "solver", "wall_seconds", "highs_status", "highs_value",
                "timing_dependent")
    for field in required:
        assert field in runner.REFERENCE_CSV_FIELDS, field
    r = rows[0]
    assert (r["instance"], r["reference_optimum"], r["reference_source"], r["exact_status"], r["ub"], r["lb"],
            r["gap_to_reference"], r["highs_status"], r["highs_value"], r["timing_dependent"], r["protocol"]) == \
        ("mini", 24, "tsplib", "optimal", 24, 24, 0, "optimal", 24, False, "exact_reference_v1")
    path = tmp_path / "reference.csv"
    runner.write_reference_csv(path, rows)
    back = list(csv.DictReader(path.open(encoding="utf-8")))
    assert [b["instance"] for b in back] == ["mini", "other"] and list(back[0]) == list(runner.REFERENCE_CSV_FIELDS)


def test_reference_value_is_never_labelled_optimal_unless_proven(runner):
    rec = runner.evaluate_instance(_spec(runner), _mini(), solve_primary=lambda m: _res("feasible_with_gap", ub=30, lb=20))
    row = runner.reference_rows([rec])[0]
    assert row["exact_status"] == "feasible_with_gap" and row["reference_optimum"] == 24 and row["gap_to_reference"] == 6
    assert row["timing_dependent"] is True and row["verdict"] == "bracketed"


def _manifest(runner, recs=None):
    recs = recs or [_record(runner)]
    inst = {"mini": {"data_source": "tsp_file", "file": "mini.tsp", "sha256": "a" * 64, "matrix_sha256": "b" * 64}}
    return runner.build_manifest(
        recs, instances=inst, git={"commit": "0123456789abcdef0123456789abcdef01234567", "dirty": False},
        versions={"ampl": "AMPL 20260809", "amplpy": "0.18.0", "gurobi": "Gurobi 13.0.3", "highs": "HiGHS 1.15.1",
                  "ampl_location": "local AMPL installation used"},
        provenance={"uniride_core": "uniride_core/__init__.py"}, total_wall_seconds=12.5, mtz_limit_seconds=120.0,
        published_source={"table": "problems.optimal", "cross_checks": ["x"], "discrepancies": []},
        started_utc="2026-10-18T10:00:00Z", ended_utc="2026-10-18T10:00:13Z")


def test_manifest_validates_and_has_no_private_data(runner):
    protocol = runner.protocol  # the script's own import: uniride_core tests never import academic_benchmark

    manifest = _manifest(runner)
    assert protocol.validate_tsp_reference_manifest(manifest) == []
    assert protocol.private_data_errors(manifest) == []
    text = json.dumps(manifest)
    assert "\\\\" not in text and ":/" not in text and "@" not in text
    assert manifest["limits"]["total_seconds_per_instance"] == 600 and manifest["limits"]["threads"] == 1
    assert "hamiltonian_cycle" in text and manifest["claim"]
    assert manifest["solvers"]["gurobi"]["seed"] == 0 and "tech:seed=0" in manifest["solvers"]["gurobi"]["option_string"]


def test_manifest_records_a_dirty_tree_and_blocking_errors(runner):
    rec = runner.evaluate_instance(_spec(runner, optimum=23), _mini(), solve_primary=lambda m: _res(),
                                   solve_secondary=lambda m: _res(solver="highs"))
    manifest = _manifest(runner, [rec])
    assert manifest["blocking_errors"] and "mini" in manifest["blocking_errors"][0]


def test_write_outputs_writes_the_four_files_and_the_tours_in_one_based_form(runner, tmp_path):
    recs = [_record(runner)]
    manifest = _manifest(runner, recs)
    out = tmp_path / "o"
    runner.write_outputs(out, recs, manifest, readme=runner.build_readme(recs, manifest))
    assert sorted(p.name for p in out.iterdir()) == ["README.md", "manifest.json", "reference.csv", "tours.json"]
    tours = json.loads((out / "tours.json").read_text(encoding="utf-8"))
    assert tours["node_base"] == 1 and tours["tours"]["mini"]["tour"] == [1, 2, 3, 4, 5, 6]
    assert tours["tours"]["mini"]["length"] == 24
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "verification subset" in readme.lower() and "not a paper instance set" in readme.lower()
    assert "superior" not in readme.lower().replace("no superiority claim", "")
    protocol = runner.protocol  # the script's own import: uniride_core tests never import academic_benchmark

    assert protocol.private_data_errors({"readme": readme, "csv": (out / "reference.csv").read_text(encoding="utf-8")}) == []


def test_tours_can_be_rechecked_without_a_licence(runner):
    tsp = _tsp()
    m = _mini()
    doc = {"node_base": 1, "tours": {"mini": {"n": 6, "length": 24, "tour": [1, 2, 3, 4, 5, 6]}}}
    assert runner.verify_tours(doc, lambda name: m) == []
    wrong_len = {"node_base": 1, "tours": {"mini": {"n": 6, "length": 23, "tour": [1, 2, 3, 4, 5, 6]}}}
    assert runner.verify_tours(wrong_len, lambda name: m)
    swapped = {"node_base": 1, "tours": {"mini": {"n": 6, "length": 24, "tour": [1, 2, 4, 3, 5, 6]}}}
    assert runner.verify_tours(swapped, lambda name: m)
    repeated = {"node_base": 1, "tours": {"mini": {"n": 6, "length": 24, "tour": [1, 2, 3, 4, 5, 5]}}}
    assert runner.verify_tours(repeated, lambda name: m)
    assert tsp.tour_length(m, (0, 1, 2, 3, 4, 5)) == 24


# ---------------------------------------------------------------- output directory and git state (E04, E06)
def test_out_directory_must_lie_strictly_below_docs_paper_results(runner):
    ok = REPO / "docs" / "paper" / "results" / "tsplib-exact-reference" / "stage1-verification"
    assert runner.check_out_dir(ok) == ""
    for bad in (REPO, REPO / "docs", REPO / "docs" / "paper" / "results", REPO / "scripts", REPO / "uniride_core",
                REPO.parent / "elsewhere"):
        assert runner.check_out_dir(bad), bad


def test_git_state_flags_dirty_trees_and_ignores_the_output_directory(runner, tmp_path):
    def git(*a):
        return subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, text=True, check=True).stdout

    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-q", "-m", "init")
    out = tmp_path / "docs" / "paper" / "results" / "x"
    commit, dirty = runner.git_state(out, repo=tmp_path)
    assert len(commit) == 40 and dirty is False
    out.mkdir(parents=True)
    (out / "reference.csv").write_text("x\n", encoding="utf-8")
    assert runner.git_state(out, repo=tmp_path)[1] is False, "files under --out do not make the tree dirty"
    (tmp_path / "a.txt").write_text("changed\n", encoding="utf-8")
    assert runner.git_state(out, repo=tmp_path)[1] is True


# ---------------------------------------------------------------- command line
def _run_cli(*args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONSTARTUP", None)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=REPO, env=env, capture_output=True, text=True,
                          timeout=120)


def test_without_ampl_the_runner_exits_with_code_3_and_writes_nothing(tmp_path):
    out = REPO / "docs" / "paper" / "results" / "tsplib-exact-reference" / "_test_no_ampl_exit3"
    res = _run_cli("--allow-dirty", "--out", str(out), env_extra={"UNIRIDE_AMPL_DIR": str(tmp_path)})
    assert res.returncode == 3, (res.stdout[-400:], res.stderr[-400:])
    assert "AMPL" in res.stderr
    assert not out.exists()


def test_the_runner_refuses_an_unsafe_out_directory_with_code_2(tmp_path):
    res = _run_cli("--allow-dirty", "--out", str(tmp_path / "somewhere"), env_extra={"UNIRIDE_AMPL_DIR": str(tmp_path)})
    assert res.returncode == 2, res.stderr[-400:]
    assert "docs/paper/results" in res.stderr


def test_the_runner_refuses_a_dirty_tree_unless_allowed(runner):
    assert runner.dirty_refusal(dirty=True, allow_dirty=False)
    assert runner.dirty_refusal(dirty=True, allow_dirty=True) == ""
    assert runner.dirty_refusal(dirty=False, allow_dirty=False) == ""


def test_the_script_imports_amplpy_only_lazily_and_core_never_imports_it(runner):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert not any(a.name.split(".")[0] == "amplpy" for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "amplpy"


def test_geo_pi_sensitivity_counts_the_arcs_that_differ_between_the_two_pi_values(runner):
    coords = _random_coords("GEO", 40, seed=11)
    base = runner.build_matrix("GEO", coords)
    assert runner.geo_pi_variant_matrix(coords, math.pi) == base
    variant = runner.geo_pi_variant_matrix(coords, 3.141592)
    expected = sum(1 for i in range(40) for j in range(40) if i != j and variant[i][j] != base[i][j])
    assert runner.count_differing_arcs(base, variant) == expected


# ================================================================ WP-E7 polish (review items 1-6)
# ---------------------------------------------------------------- item 1: measured run history
def _manifest_with(runner, **kw):
    recs = [_record(runner)]
    inst = {"mini": {"data_source": "tsp_file", "file": "mini.tsp", "sha256": "a" * 64, "matrix_sha256": "b" * 64}}
    args = dict(
        instances=inst, git={"commit": "0123456789abcdef0123456789abcdef01234567", "dirty": False},
        versions={"ampl": "AMPL 20260809", "amplpy": "0.18.0", "gurobi": "Gurobi 13.0.3", "highs": "HiGHS 1.15.1",
                  "ampl_location": "local AMPL installation used"},
        provenance={"uniride_core": "uniride_core/__init__.py"}, total_wall_seconds=12.5, mtz_limit_seconds=120.0,
        published_source={"table": "problems.optimal", "cross_checks": ["x"], "discrepancies": []},
        started_utc="2026-10-18T10:00:00Z", ended_utc="2026-10-18T10:00:13Z")
    args.update(kw)
    return runner.build_manifest(recs, **args)


def test_run_history_records_measured_timestamps_and_this_runs_invocation_count(runner):
    h = _manifest_with(runner)["run_history"]
    assert h["started_utc"] == "2026-10-18T10:00:00Z" and h["ended_utc"] == "2026-10-18T10:00:13Z"
    assert h["invocations_in_this_manifest"] == 1
    assert "invocations_at_this_commit" not in h, "the old field claimed a count across the commit that nothing measured"
    assert h["serial"] is True and h["cache"] == "none" and h["retries"] == 0


def test_run_history_takes_the_timestamps_it_is_given_not_a_literal(runner):
    h = _manifest_with(runner, started_utc="2030-01-02T03:04:05Z", ended_utc="2030-01-02T03:05:00Z")["run_history"]
    assert (h["started_utc"], h["ended_utc"]) == ("2030-01-02T03:04:05Z", "2030-01-02T03:05:00Z")


def test_utc_stamp_is_iso_utc_with_z(runner):
    import datetime

    stamp = runner.utc_stamp(datetime.datetime(2026, 10, 18, 10, 0, 7, 999999, tzinfo=datetime.timezone.utc))
    assert stamp == "2026-10-18T10:00:07Z"
    assert runner.utc_stamp().endswith("Z") and len(runner.utc_stamp()) == 20


# ---------------------------------------------------------------- item 2: a non-empty -wal is refused
def test_a_non_empty_wal_next_to_the_database_is_refused(runner, tmp_path):
    db = tmp_path / "tsplib.db"
    _make_wal_db(db)
    assert runner.wal_refusal(db) == "", "no -wal file: nothing to refuse"
    (tmp_path / "tsplib.db-wal").write_bytes(b"")
    assert runner.wal_refusal(db) == "", "an EMPTY -wal file (as next to the real database) must not trip the check"
    (tmp_path / "tsplib.db-wal").write_bytes(b"\x37\x7f\x06\x82 uncheckpointed frames")
    msg = runner.wal_refusal(db)
    assert "tsplib.db-wal" in msg and "immutable" in msg


def test_the_runner_exits_2_before_any_solver_when_a_non_empty_wal_exists(tmp_path):
    db = tmp_path / "tsplib.db"
    _make_wal_db(db)
    (tmp_path / "tsplib.db-wal").write_bytes(b"not empty")
    out = REPO / "docs" / "paper" / "results" / "tsplib-exact-reference" / "_test_wal_refused"
    # UNIRIDE_AMPL_DIR points at an empty directory: if the WAL check came after the backend start the exit code would be 3
    res = _run_cli("--allow-dirty", "--data-dir", str(tmp_path), "--out", str(out), env_extra={"UNIRIDE_AMPL_DIR": str(tmp_path)})
    assert res.returncode == 2, (res.returncode, res.stderr[-400:])
    assert "tsplib.db-wal" in res.stderr
    assert not out.exists()


def test_verify_tours_cli_does_not_read_the_database_so_a_wal_next_to_it_is_irrelevant(tmp_path):
    # WP-E8 companion: --verify-tours takes instances, optima and tours from the active manifest-governed folders
    (tmp_path / "tsplib.db").write_bytes(b"this is not a database")
    (tmp_path / "tsplib.db-wal").write_bytes(b"not empty")
    tours = tmp_path / "t"
    tours.mkdir()
    (tours / "tours.json").write_text(json.dumps({"node_base": 1, "tours": {}}), encoding="utf-8")
    res = _run_cli("--data-dir", str(tmp_path), "--verify-tours", str(tours))
    assert res.returncode == 0 and "tours checked: 0; errors: 0" in res.stdout, (res.returncode, res.stderr[-300:])


def test_database_record_has_file_name_size_and_sha256_of_a_copy(runner, tmp_path):
    db = tmp_path / "tsplib.db"
    _make_wal_db(db)
    rec = runner.database_record(db)
    assert rec == {"file": "tsplib.db", "size_bytes": db.stat().st_size, "sha256": _sha(db)}


# ---------------------------------------------------------------- item 3: GEO wording and a blocking sensitivity re-solve
def test_spec_distance_docstring_states_the_pi_choice_instead_of_claiming_independence(runner):
    doc = runner.spec_distance.__doc__
    assert "math.pi" in doc and "3.141592" in doc and "E10" in doc
    assert "written from the document" not in doc


def test_manifest_convention_wording_says_the_pi_choice_is_shared(runner):
    c = runner.convention_record(geo_pi_blocking=True)
    text = json.dumps(c)
    assert "independent transcription" not in text, "the old wording suggested an independent check of pi"
    assert "math.pi" in c["GEO"] and "shared" in c["asserted"] and "3.141592" in c["asserted"]
    assert c["geo_pi_sensitivity_blocking"] is True
    assert runner.convention_record(geo_pi_blocking=False)["geo_pi_sensitivity_blocking"] is False


def _geo_primary(ub=100, status="optimal"):
    return _res(status=status, ub=ub, lb=ub if status == "optimal" else ub - 5)


def test_a_differing_optimum_under_the_other_pi_blocks_when_the_flag_is_on(runner):
    coords = _random_coords("GEO", 40, seed=11)
    matrix = runner.build_matrix("GEO", coords)
    assert runner.count_differing_arcs(matrix, runner.geo_pi_variant_matrix(coords, runner.TSPLIB_GEO_PI)) > 0
    alt = lambda m: _res(ub=101, lb=101, tour=None)  # noqa: E731
    note, blocking = runner.geo_pi_sensitivity("mini", matrix, coords, _geo_primary(), solve=alt, blocking=True)
    assert note["outcome"] == "different_optimum" and note["ub"] == 101
    assert len(blocking) == 1 and "mini" in blocking[0] and "3.141592" in blocking[0]
    note, blocking = runner.geo_pi_sensitivity("mini", matrix, coords, _geo_primary(), solve=alt, blocking=False)
    assert note["outcome"] == "different_optimum" and blocking == [], "flag off: recorded only, as in stage 1"


def test_the_same_optimum_unproven_and_identical_matrices_do_not_block(runner):
    coords = _random_coords("GEO", 40, seed=11)
    matrix = runner.build_matrix("GEO", coords)
    note, blocking = runner.geo_pi_sensitivity("mini", matrix, coords, _geo_primary(),
                                               solve=lambda m: _res(ub=100, lb=100, tour=None), blocking=True)
    assert (note["outcome"], blocking) == ("same_optimum", [])
    note, blocking = runner.geo_pi_sensitivity("mini", matrix, coords, _geo_primary(),
                                               solve=lambda m: _res("feasible_with_gap", ub=110, lb=90), blocking=True)
    assert (note["outcome"], blocking) == ("unproven", [])
    calls = []
    same = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]  # integer degrees: both pi values give the same arcs
    m3 = runner.build_matrix("GEO", same)
    assert runner.count_differing_arcs(m3, runner.geo_pi_variant_matrix(same, runner.TSPLIB_GEO_PI)) == 0
    note, blocking = runner.geo_pi_sensitivity("mini", m3, same, _geo_primary(), solve=lambda m: calls.append(1), blocking=True)
    assert note["outcome"] == "identical_matrix" and blocking == [] and calls == []


def test_a_failed_sensitivity_re_solve_blocks_only_when_the_flag_is_on(runner):
    coords = _random_coords("GEO", 40, seed=11)
    matrix = runner.build_matrix("GEO", coords)
    bad = lambda m: _res("rejected", ub=None, lb=None, tour=None, note="solver failed")  # noqa: E731
    note, blocking = runner.geo_pi_sensitivity("mini", matrix, coords, _geo_primary(), solve=bad, blocking=True)
    assert note["outcome"] == "failed" and len(blocking) == 1 and "solver failed" in blocking[0]
    assert runner.geo_pi_sensitivity("mini", matrix, coords, _geo_primary(), solve=bad, blocking=False)[1] == []


def test_the_sensitivity_flag_defaults_to_on(runner):
    assert runner.parse_args([]).geo_pi_blocking is True
    assert runner.parse_args(["--no-geo-pi-blocking"]).geo_pi_blocking is False


# ---------------------------------------------------------------- item 4: the canonical coordinate text is documented
def test_manifest_states_the_canonical_coordinate_text_format(runner):
    fmt = runner.coordinate_text_record()
    assert fmt["line_format"] == "{i} {x!r} {y!r}\\n" and fmt["encoding"] == "ASCII" and fmt["index_base"] == 0
    # the documented format is the one the hash is computed over
    coords = [(1.5, 2.0), (3.0, 4.25)]
    canonical = "".join(f"{i} {x!r} {y!r}\n" for i, (x, y) in enumerate(coords)).encode("ascii")
    assert runner.coordinate_text_sha256(coords) == hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------- item 5: published tours cross-check the coordinates
def _tour_db(path: Path, tours):
    conn = sqlite3.connect(path)
    conn.execute("create table if not exists opt_tours (problem_name text primary key, tour_nodes text not null, "
                 "tour_length real, source text, added_at text not null)")
    conn.executemany("insert into opt_tours values (?, ?, null, 'tsplib_file', '2026-01-01')",
                     [(k, json.dumps(v)) for k, v in tours.items()])
    conn.commit()
    conn.close()


def _line4_db(path: Path, tours=None):
    """The fixture database plus ``line4``: four nodes on the x axis, tour length 6."""
    _make_wal_db(path)
    conn = sqlite3.connect(path)
    conn.execute("insert into problems (name, dimension, optimal, edge_weight_type, problem_type) "
                 "values ('line4', 4, 6, 'EUC_2D', 'TSP')")
    conn.executemany("insert into coordinates values ('line4', ?, ?, 0.0)", [(i, float(i)) for i in range(4)])
    conn.commit()
    conn.close()
    _tour_db(path, tours or {})


def test_published_tour_length_on_the_used_coordinates_must_equal_the_published_optimum(runner):
    m = _mini()
    spec = _spec(runner, optimum=24)
    assert runner.check_published_tour(spec, m, [1, 2, 3, 4, 5, 6]) == []
    assert runner.check_published_tour(_spec(runner, optimum=23), m, [1, 2, 3, 4, 5, 6]), "length 24 != published 23"
    assert runner.check_published_tour(spec, m, [1, 2, 4, 3, 5, 6]), "a different tour with another length"
    assert runner.check_published_tour(spec, m, [1, 2, 3, 4, 5, 5]), "not a permutation"
    assert runner.check_published_tour(spec, m, [1, 2, 3, 4, 5]), "wrong size"


def test_published_tour_is_read_from_opt_tours_read_only_and_from_opt_tour_files(runner, tmp_path):
    db = tmp_path / "tsplib.db"
    _make_wal_db(db)
    _tour_db(db, {"a10": [1, 3, 2]})
    conn = runner.open_db_readonly(db)
    try:
        assert runner.read_published_tour(conn, "a10", None) == ([1, 3, 2], "opt_tours")
        assert runner.read_published_tour(conn, "b99", None) is None
        files = tmp_path / "tours"
        files.mkdir()
        (files / "kroA100.opt.tour").write_text(
            "NAME : kroA100.opt.tour\nCOMMENT : Optimal tour (21282)\nTYPE : TOUR\nDIMENSION : 4\nTOUR_SECTION\n1\n3\n2\n4\n-1\nEOF\n",
            encoding="utf-8")
        assert runner.read_published_tour(conn, "kroa100", files) == ([1, 3, 2, 4], "opt_tour_file")
        assert runner.read_published_tour(conn, "nothere", files) is None
    finally:
        conn.close()


def test_a_published_tour_that_does_not_match_the_coordinates_blocks_the_instance(runner, tmp_path):
    db = tmp_path / "tsplib.db"
    _line4_db(db)
    tours = tmp_path / "tours"  # WP-E8 companion: published tours come from a manifest-governed folder, not from the database
    tours.mkdir()
    body = b"NAME : line4.opt.tour\nTYPE : TOUR\nDIMENSION : 4\nTOUR_SECTION\n1 2\n3 4\n-1\nEOF\n"
    (tours / "line4.opt.tour").write_bytes(body)
    (tours / "MANIFEST.json").write_text(json.dumps({"schema_version": "uniride-opt-tour-collection/v1", "instances": [
        {"name": "line4", "file_name": "line4.opt.tour", "source": "archive_copy", "sha256": hashlib.sha256(body).hexdigest()}]}),
        encoding="utf-8")
    ro = runner.open_db_readonly(db)
    try:
        spec = runner.InstanceSpec("line4", "TSP", 4, "EUC_2D", 6, "tsplib")
        rec = runner.load_instance(spec, tmp_path, ro, tours)[2]
        assert rec["published_tour_check"] == {"source": "opt_tour_file", "tour_length": 6, "equals_published_optimum": True}
        bad = runner.InstanceSpec("line4", "TSP", 4, "EUC_2D", 7, "tsplib")
        with pytest.raises(runner.PublishedTourError):
            runner.load_instance(bad, tmp_path, ro, tours)
    finally:
        ro.close()


def test_an_instance_without_a_published_tour_is_labelled_not_blocked(runner, tmp_path):
    db = tmp_path / "tsplib.db"
    _line4_db(db)
    ro = runner.open_db_readonly(db)
    try:
        spec = runner.InstanceSpec("line4", "TSP", 4, "EUC_2D", 6, "tsplib")
        rec = runner.load_instance(spec, tmp_path, ro)[2]
    finally:
        ro.close()
    assert rec["published_tour_check"] == {"source": "none", "tour_length": None, "equals_published_optimum": None}


def test_the_real_database_published_tours_match_the_coordinates_of_the_verification_set():
    if not DB_PATH.is_file():
        pytest.skip("tsplib.db not present in this checkout (git-ignored)")
    runner = _load_script()
    conn = runner.open_db_readonly(DB_PATH)
    try:
        specs = [s for s in runner.read_instance_set(conn) if s.problem_type == "TSP"]
        checked = []
        for s in specs:
            pub = runner.read_published_tour(conn, s.name, None)
            if pub is None:
                continue
            matrix = runner.build_matrix(s.edge_weight_type, runner.read_db_coordinates(conn, s.name))
            assert runner.check_published_tour(s, matrix, pub[0]) == [], s.name
            checked.append(s.name)
    finally:
        conn.close()
    assert len(checked) >= 10, checked


# ---------------------------------------------------------------- item 6: --verify-tours compares with the published optimum
def test_verify_tours_compares_every_tour_length_with_the_published_optimum(runner):
    m = _mini()
    doc = {"node_base": 1, "tours": {"mini": {"n": 6, "length": 24, "status": "optimal", "tour": [1, 2, 3, 4, 5, 6]}}}
    assert runner.verify_tours(doc, lambda name: m, optimum_for=lambda name: 24) == []
    errs = runner.verify_tours(doc, lambda name: m, optimum_for=lambda name: 23)
    assert errs and "published" in errs[0] and "23" in errs[0]
    bracket = {"node_base": 1, "tours": {"mini": {"n": 6, "length": 24, "status": "feasible_with_gap", "tour": [1, 2, 3, 4, 5, 6]}}}
    assert runner.verify_tours(bracket, lambda name: m, optimum_for=lambda name: 23) == [], "a non-proven tour may be longer"
    too_short = runner.verify_tours(bracket, lambda name: m, optimum_for=lambda name: 25)
    assert too_short and "shorter" in too_short[0], "no tour can be shorter than the published optimum"


def test_verify_tours_reports_an_instance_without_a_published_optimum(runner):
    m = _mini()
    doc = {"node_base": 1, "tours": {"mini": {"n": 6, "length": 24, "status": "optimal", "tour": [1, 2, 3, 4, 5, 6]}}}
    errs = runner.verify_tours(doc, lambda name: m, optimum_for=lambda name: None)
    assert errs and "no published optimum" in errs[0]
