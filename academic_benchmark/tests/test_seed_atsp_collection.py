"""Tests for the 19-instance TSPLIB ATSP collection and its generalised loader.

Hermetic: every database is a tmp_path SQLite file.
Source: https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ (optima:
ATSP-BEST.html, cross-checked against the TSPLib.Net bestSolutions.txt mirror).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3

import numpy as np
import pytest

from academic_benchmark import seed_atsp
from academic_benchmark.seed_atsp import MANIFEST_PATH, REPO_ROOT, load_manifest, seed_atsp as run_seed

EXPECTED_OPTIMA = {
    "br17": 39, "ft53": 6905, "ft70": 38673, "ftv33": 1286, "ftv35": 1473,
    "ftv38": 1530, "ftv44": 1613, "ftv47": 1776, "ftv55": 1608, "ftv64": 1839,
    "ftv70": 1950, "ftv170": 2755, "kro124p": 36230, "p43": 5620,
    "rbg323": 1326, "rbg358": 1163, "rbg403": 2465, "rbg443": 2720,
    "ry48p": 14422,
}


def _entries():
    return {e["name"]: e for e in load_manifest()["instances"]}


def _abs(entry):
    return os.path.join(REPO_ROOT, entry["artifact_path"])


def _tsp_db(tmp_path, count=3):
    from academic_benchmark.tsplib_manager import store_academic_text
    db = str(tmp_path / "t.db")
    tpl = ("NAME : {n}\nTYPE : TSP\nDIMENSION : 4\nEDGE_WEIGHT_TYPE : EUC_2D\n"
           "NODE_COORD_SECTION\n1 {x} 0\n2 1 0\n3 1 1\n4 0 1\nEOF\n")
    for i in range(count):
        store_academic_text(tpl.format(n=f"_t{i}", x=i), "tsp", name=f"_t{i}",
                            db_path=db, source_file="test")
    return db


def _rows(db, where="1=1"):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT * FROM problems WHERE {where} ORDER BY name").fetchall()
    finally:
        conn.close()


class TestManifest:
    def test_has_19_entries_with_expected_names(self):
        assert set(_entries()) == set(EXPECTED_OPTIMA)
        assert len(load_manifest()["instances"]) == 19

    def test_optima_match_official_list(self):
        assert {n: e["optimal"] for n, e in _entries().items()} == EXPECTED_OPTIMA

    def test_required_fields(self):
        for e in _entries().values():
            for k in ("name", "dimension", "edge_weight_type", "edge_weight_format",
                      "optimal", "authority_url", "mirror_url", "sha256_gz",
                      "sha256", "retrieved_on", "artifact_path"):
                assert e.get(k) not in (None, ""), (e["name"], k)
            assert e["authority_url"].startswith("https://comopt.ifi.uni-heidelberg.de/")

    def test_sha256_matches_files(self):
        for e in _entries().values():
            with open(_abs(e), "rb") as fh:
                assert hashlib.sha256(fh.read()).hexdigest() == e["sha256"], e["name"]

    def test_ft53_points_to_existing_file(self):
        assert _entries()["ft53"]["artifact_path"] == "academic_benchmark/tsplib_data/ft53.atsp"
        assert not os.path.exists(os.path.join(os.path.dirname(MANIFEST_PATH), "ft53.atsp"))

    def test_parse_dimension_and_matrix_shape(self):
        from uniride_core.algorithms.tsplib_parser import parse_atsp_text
        for e in _entries().values():
            with open(_abs(e), encoding="utf-8") as fh:
                info = parse_atsp_text(fh.read(), e["name"])
            assert info is not None, e["name"]
            m = np.asarray(info["explicit_matrix"])
            assert m.shape == (e["dimension"], e["dimension"]), e["name"]


class TestLoader:
    def test_loads_19_atsp_and_leaves_tsp_alone(self, tmp_path):
        db = _tsp_db(tmp_path)
        before = _rows(db)
        res = run_seed(db_path=db)
        assert sorted(res["stored"]) == sorted(EXPECTED_OPTIMA)
        assert res["skipped"] == []
        rows = _rows(db)
        assert len(rows) == len(before) + 19
        assert [r for r in rows if r[0].startswith("_t")] == before
        conn = sqlite3.connect(db)
        got = dict(conn.execute("SELECT name, optimal FROM problems WHERE name NOT LIKE '!_t%' ESCAPE '!'").fetchall())
        conn.close()
        assert got == EXPECTED_OPTIMA

    def test_idempotent(self, tmp_path):
        db = _tsp_db(tmp_path)
        run_seed(db_path=db)
        snap = _rows(db)
        res = run_seed(db_path=db)
        assert res["stored"] == []
        assert sorted(res["skipped"]) == sorted(EXPECTED_OPTIMA)
        assert _rows(db) == snap

    def test_dry_run_writes_nothing(self, tmp_path):
        db = str(tmp_path / "dry.db")
        res = run_seed(db_path=db, dry_run=True)
        assert sorted(res["stored"]) == sorted(EXPECTED_OPTIMA)
        assert not os.path.exists(db)

    def test_p43_uses_official_optimum(self, tmp_path):
        db = str(tmp_path / "p.db")
        run_seed(db_path=db, names=["p43"])
        assert _rows(db, "name='p43'")
        conn = sqlite3.connect(db)
        assert conn.execute("SELECT optimal FROM problems WHERE name='p43'").fetchone()[0] == 5620
        conn.close()

    def test_corrupt_file_is_rejected(self, tmp_path, monkeypatch):
        bad = tmp_path / "br17.atsp"
        bad.write_text("garbage")
        entries = _entries()
        entries["br17"] = dict(entries["br17"], artifact_path=str(bad))
        monkeypatch.setattr(seed_atsp, "REPO_ROOT", "")
        monkeypatch.setattr(seed_atsp, "load_manifest",
                            lambda: {"instances": list(entries.values())})
        with pytest.raises(ValueError, match="SHA-256"):
            run_seed(db_path=str(tmp_path / "c.db"), names=["br17"])
        assert not os.path.exists(str(tmp_path / "c.db"))

    def test_ft53_identical_to_legacy_seed(self, tmp_path):
        from academic_benchmark.seed_ft53 import seed_ft53
        a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
        seed_ft53(db_path=a)
        run_seed(db_path=b, names=["ft53"])
        ra, rb = _rows(a, "name='ft53'"), _rows(b, "name='ft53'")
        assert len(ra) == len(rb) == 1
        # compare everything except timestamps and the tsp_file tag (seed_ft53 vs seed_atsp)
        conn = sqlite3.connect(a)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(problems)")]
        conn.close()
        keep = [i for i, c in enumerate(cols) if "extracted" not in c and c != "tsp_file" and "created" not in c and "updated" not in c]
        assert [ra[0][i] for i in keep] == [rb[0][i] for i in keep]
