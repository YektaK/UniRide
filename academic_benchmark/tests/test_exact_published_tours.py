"""Tests that need ``academic_benchmark.exact_reference`` for the published-tour reader (moved out of
``uniride_core/tests/test_exact_tsp_runner.py`` so that uniride_core tests never import academic_benchmark; the
architecture-boundary test enforces that). The assertions are unchanged.

The real-database test skips with a reason when the git-ignored ``tsplib.db`` is absent.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run_exact_tsp_reference.py"
# the data live in the main checkout (git-ignored there); a worktree reads them through this variable
DATA_DIR = Path(os.environ.get("UNIRIDE_TSPLIB_DATA_DIR", REPO / "academic_benchmark" / "tsplib_data"))
DB_PATH = DATA_DIR / "tsplib.db"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_exact_tsp_reference_published_tours", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load_script()


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


def _tour_db(path: Path, tours):
    conn = sqlite3.connect(path)
    conn.execute("create table if not exists opt_tours (problem_name text primary key, tour_nodes text not null, "
                 "tour_length real, source text, added_at text not null)")
    conn.executemany("insert into opt_tours values (?, ?, null, 'tsplib_file', '2026-01-01')",
                     [(k, json.dumps(v)) for k, v in tours.items()])
    conn.commit()
    conn.close()


def _read_published_tour(runner, conn, name, tour_dir):
    """TEST-ONLY helper (moved out of the runner, WP-E8 polish item a): reads a published tour from the ``opt_tours`` table
    of a read-only fixture database and then from an UNMANIFESTED folder. The runner never does this; it takes tours only
    from the manifest-governed collection (``inputs.read_collection_tour``). Kept here to exercise ``check_published_tour``
    against the real database tours; (1-based node list, source) or None."""
    has_table = conn.execute("select 1 from sqlite_master where type='table' and name='opt_tours'").fetchone()
    if has_table:
        row = conn.execute("select tour_nodes from opt_tours where problem_name=?", (name,)).fetchone()
        if row is not None:
            return [int(v) for v in json.loads(row[0])], "opt_tours"
    if tour_dir is not None and Path(tour_dir).is_dir():
        want = f"{name}.opt.tour".lower()
        for cand in sorted(Path(tour_dir).iterdir()):
            if cand.name.lower() == want and cand.is_file():
                from academic_benchmark.exact_reference import inputs

                return inputs.parse_tour_text(cand.read_text(encoding="utf-8")), "opt_tour_file"
    return None


def test_test_only_helper_reads_opt_tours_read_only_and_from_opt_tour_files(runner, tmp_path):
    db = tmp_path / "tsplib.db"
    _make_wal_db(db)
    _tour_db(db, {"a10": [1, 3, 2]})
    conn = runner.open_db_readonly(db)
    try:
        assert _read_published_tour(runner, conn, "a10", None) == ([1, 3, 2], "opt_tours")
        assert _read_published_tour(runner, conn, "b99", None) is None
        files = tmp_path / "tours"
        files.mkdir()
        (files / "kroA100.opt.tour").write_text(
            "NAME : kroA100.opt.tour\nCOMMENT : Optimal tour (21282)\nTYPE : TOUR\nDIMENSION : 4\nTOUR_SECTION\n1\n3\n2\n4\n-1\nEOF\n",
            encoding="utf-8")
        assert _read_published_tour(runner, conn, "kroa100", files) == ([1, 3, 2, 4], "opt_tour_file")
        assert _read_published_tour(runner, conn, "nothere", files) is None
    finally:
        conn.close()


def test_the_real_database_published_tours_match_the_coordinates_of_the_verification_set():
    if not DB_PATH.is_file():
        pytest.skip("tsplib.db not present in this checkout (git-ignored)")
    runner = _load_script()
    conn = runner.open_db_readonly(DB_PATH)
    try:
        specs = [s for s in runner.read_instance_set(conn) if s.problem_type == "TSP"]
        checked = []
        for s in specs:
            pub = _read_published_tour(runner, conn, s.name, None)
            if pub is None:
                continue
            matrix = runner.build_matrix(s.edge_weight_type, runner.read_db_coordinates(conn, s.name))
            assert runner.check_published_tour(s, matrix, pub[0]) == [], s.name
            checked.append(s.name)
    finally:
        conn.close()
    assert len(checked) >= 10, checked


def test_the_real_database_test_skips_on_an_empty_database_file(tmp_path, monkeypatch):
    """A first read in a fresh worktree creates an empty tsplib.db (audit M16); that must skip, not fail."""
    empty = tmp_path / "tsplib.db"
    sqlite3.connect(empty).close()
    monkeypatch.setattr(sys.modules[__name__], "DB_PATH", empty)
    with pytest.raises(pytest.skip.Exception):
        test_the_real_database_published_tours_match_the_coordinates_of_the_verification_set()
    # the guard opened the file read-only and immutable: no journal files appeared next to it
    assert sorted(path.name for path in tmp_path.iterdir()) == ["tsplib.db"]
