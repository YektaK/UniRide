"""DECISION_LOG A13 (owner decision 2026-10-14): results stamped before 2026-10-13 are
HISTORICAL_UNVERIFIED (ACADEMIC_STUDY_UNIFICATION_DESIGN.md "Evidence Quarantine"): visible in a
labelled view, never pooled with current results, never deleted. The A06/A07 ga_split rows are a
different class (INVALID) and stay hidden."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from academic_benchmark import obsolete_results as orr
from academic_benchmark.dashboard_utils import load_csv_frames
from academic_benchmark.results_reader import get_benchmark_rows, get_best_result, get_leaderboard
from academic_benchmark.tools import mark_obsolete_ga_split_variant_results as tool
from academic_benchmark.tsplib_manager import (
    get_db,
    init_db,
    query_benchmark_results,
    query_best_solutions,
    save_benchmark_result,
    save_benchmark_run,
)

OLD = "2026-06-30T20:05:09.510851"
NEW = "2026-10-14T09:00:00"
BENCH = Path(__file__).resolve().parents[1]
ROOT = BENCH.parent
HIST = "historical_unverified"


@pytest.fixture(autouse=True)
def real_cutoff(monkeypatch):
    monkeypatch.setattr(orr, "LEGACY_CUTOFF", "2026-10-13")


def _best_db(tmp_path, rows):
    db = str(tmp_path / "t.db")
    conn = get_db(db)
    init_db(conn)
    conn.execute("INSERT INTO problems (name, dimension, category) VALUES ('tiny', 3, 'small')")
    for algo, ts, length in rows:
        conn.execute(
            "INSERT INTO best_solutions (problem_name, algorithm, params_json, tour_nodes, tour_length, gap, timestamp)"
            " VALUES ('tiny', ?, '{}', '[0,1,2]', ?, 0.0, ?)",
            (algo, length, ts),
        )
    conn.commit()
    conn.close()
    return db


def _result(algo, ts, i=1, metadata=None):
    return {
        "problem": "tiny", "algorithm": algo, "run_number": i, "problem_type": "tsp",
        "objective_cost": 10.0, "tour_cost": 10.0, "params": {}, "metadata": metadata or {}, "timestamp": ts,
    }


# -- C4: SQL and Python must classify every stamp identically -------------------------------
EDGE = {
    "offset_minus5_current": "2026-10-12T23:30:00-05:00",  # 2026-10-13T04:30Z -> current
    "offset_plus3_legacy": "2026-10-13T01:00:00+03:00",  # 2026-10-12T22:00Z -> legacy
    "naive_cutoff": "2026-10-13T00:00:00",
    "naive_before": "2026-10-12T23:59:59",
    "garbage": "13.10.2026",
}


def test_sql_and_python_agree_on_cutoff_day(tmp_path):
    expected_current = {k for k, v in EDGE.items() if not orr.is_legacy_timestamp(v)}
    assert expected_current == {"offset_minus5_current", "naive_cutoff"}
    db = _best_db(tmp_path, [(k, v, 1.0 + i) for i, (k, v) in enumerate(EDGE.items())])
    cur = {r["algorithm"] for r in query_best_solutions(db_path=db)}
    his = {r["algorithm"] for r in query_best_solutions(db_path=db, evidence="historical")}
    assert cur == expected_current
    assert his == set(EDGE) - expected_current


def test_sql_and_python_agree_for_benchmark_results(tmp_path):
    db = str(tmp_path / "r.db")
    save_benchmark_run("r1", source="web", db_path=db)
    for i, (k, v) in enumerate(EDGE.items(), 1):
        save_benchmark_result("r1", _result(k, v, i), db_path=db)
    expected = {k for k, v in EDGE.items() if not orr.is_legacy_timestamp(v)}
    assert {r["algorithm"] for r in query_benchmark_results(db_path=db)} == expected
    his = query_benchmark_results(db_path=db, evidence="historical")
    assert {r["algorithm"] for r in his} == set(EDGE) - expected
    assert all(r["evidence_class"] == HIST for r in his)


# -- D1: visible, labelled, never pooled --------------------------------------------------
def test_historical_row_in_labelled_view_and_absent_from_default(tmp_path):
    db = _best_db(tmp_path, [("Old", OLD, 1.0), ("New", NEW, 9.0)])
    assert [r["algorithm"] for r in query_best_solutions(db_path=db)] == ["New"]
    # include_obsolete (INVALID class, A06) never lifts the historical exclusion
    assert [r["algorithm"] for r in query_best_solutions(db_path=db, include_obsolete=True)] == ["New"]
    hist = query_best_solutions(db_path=db, evidence="historical")
    assert [(r["algorithm"], r["evidence_class"]) for r in hist] == [("Old", HIST)]


def test_reader_sections_are_separate_and_labelled(tmp_path):
    db = _best_db(tmp_path, [("Old", OLD, 1.0), ("New", NEW, 9.0)])
    default = get_leaderboard(db_path=db)
    assert [r["algorithm"] for r in default["results"]] == ["New"]
    assert default["evidence_class"] == "current"
    assert default["historical_unverified_available"] is True
    assert "historical_unverified" not in default
    both = get_leaderboard(db_path=db, include_historical=True)
    assert [r["algorithm"] for r in both["results"]] == ["New"]  # never pooled
    section = both["historical_unverified"]
    assert section["evidence_class"] == HIST and section["count"] == 1
    assert [(r["algorithm"], r["evidence_class"]) for r in section["results"]] == [("Old", HIST)]
    best = get_best_result("tiny", "Old", db_path=db)
    assert best["result"] is None and best["historical_unverified_available"] is True
    best = get_best_result("tiny", "Old", db_path=db, include_historical=True)
    assert best["result"] is None and best["historical_unverified"]["result"]["evidence_class"] == HIST


def test_benchmark_rows_db_and_csv_historical_section(tmp_path):
    db = str(tmp_path / "r.db")
    save_benchmark_run("r1", source="web", db_path=db)
    for i, (algo, ts) in enumerate([("OldAlgo", OLD), ("NewAlgo", NEW)], 1):
        save_benchmark_result("r1", _result(algo, ts, i), db_path=db)
    out = get_benchmark_rows(db_path=db, results_dir=str(tmp_path))
    assert [r["algorithm"] for r in out["results"]] == ["NewAlgo"]
    out = get_benchmark_rows(db_path=db, results_dir=str(tmp_path), include_historical=True)
    assert [r["algorithm"] for r in out["results"]] == ["NewAlgo"]
    assert [(r["algorithm"], r["evidence_class"]) for r in out["historical_unverified"]["results"]] == [
        ("OldAlgo", HIST)
    ]
    # CSV fallback: rows live in legacy_pre_2026-10-13/ (QUARANTINE.md), none in the main directory
    csv_dir = tmp_path / "res"
    legacy = csv_dir / orr.LEGACY_RESULTS_DIRNAME
    legacy.mkdir(parents=True)
    (legacy / "QUARANTINE.md").write_text("# q\n", encoding="utf-8")
    with open(legacy / "benchmark_progress.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["timestamp", "problem", "algorithm", "avg_length"])
        w.writeheader()
        w.writerow({"timestamp": OLD, "problem": "p", "algorithm": "Old", "avg_length": 1})
    none = str(tmp_path / "none.db")
    out = get_benchmark_rows(db_path=none, results_dir=str(csv_dir), include_historical=True)
    assert out["results"] == []
    assert [r["evidence_class"] for r in out["historical_unverified"]["results"]] == [HIST]
    _, progress, _ = load_csv_frames([str(csv_dir)], evidence="historical")
    assert sum(len(f) for f in progress) == 1
    assert all((f["evidence_class"] == HIST).all() for f in progress if len(f))
    _, cur, _ = load_csv_frames([str(csv_dir)])
    assert all(len(f) == 0 for f in cur)


def test_legacy_rule_does_not_flag_rows_invalid(tmp_path):
    db = str(tmp_path / "r.db")
    save_benchmark_run("r1", source="web", db_path=db)
    save_benchmark_result("r1", _result("Old", OLD, metadata={"keep": "me"}), db_path=db)
    report = tool.mark_sqlite(db, dry_run=False, rule="legacy")
    assert report["to_mark"] == 0 and report["rule"] == "legacy"
    rows = query_benchmark_results(db_path=db, evidence="historical")
    assert len(rows) == 1  # not hidden as INVALID: it stays in the historical view
    assert "obsolete" not in json.dumps(rows[0]["metadata"])


# -- quarantine manifest (design: path, archive path, size, SHA-256, class) -------------------
def test_repo_quarantine_manifests_match_files():
    for top in ("numba_results", "sota_results"):
        legacy = BENCH / top / orr.LEGACY_RESULTS_DIRNAME
        assert (legacy / orr.QUARANTINE_MARKER_FILE).exists()
        assert not list(legacy.rglob("OBSOLETE.md"))
        manifest = json.loads((legacy / orr.QUARANTINE_MANIFEST_FILE).read_text(encoding="utf-8"))
        assert manifest["decision"] == "DECISION_LOG A13"
        listed = {e["archive_path"] for e in manifest["entries"]}
        on_disk = {
            p.relative_to(ROOT).as_posix()
            for p in legacy.rglob("*")
            if p.is_file() and p.name not in (orr.QUARANTINE_MARKER_FILE, orr.QUARANTINE_MANIFEST_FILE)
        }
        assert listed == on_disk and on_disk
        for e in manifest["entries"]:
            data = (ROOT / e["archive_path"]).read_bytes()
            assert e["sha256"] == hashlib.sha256(data).hexdigest()
            assert e["size_bytes"] == len(data)
            assert e["evidence_class"] == "HISTORICAL_UNVERIFIED"
            assert "legacy_pre_2026-10-13/" not in e["original_path"]
        assert orr.verify_quarantine_manifest(str(legacy), str(ROOT)) == []


def test_manifest_detects_tampering(tmp_path):
    legacy = tmp_path / "results" / orr.LEGACY_RESULTS_DIRNAME
    legacy.mkdir(parents=True)
    (legacy / "a.csv").write_text("x\n1\n", encoding="utf-8")
    orr.build_quarantine_manifest(str(legacy), str(tmp_path), now="2026-10-14")
    assert orr.verify_quarantine_manifest(str(legacy), str(tmp_path)) == []
    (legacy / "a.csv").write_text("x\n2\n", encoding="utf-8")
    problems = orr.verify_quarantine_manifest(str(legacy), str(tmp_path))
    assert problems and "a.csv" in problems[0]


def test_tool_writes_quarantine_md_and_manifest_and_skips_production_path(tmp_path):
    d = tmp_path / "a" / orr.LEGACY_RESULTS_DIRNAME
    d.mkdir(parents=True)
    (d / "r.csv").write_text("x\n", encoding="utf-8")
    out = tool.mark_legacy_files(str(d), dry_run=False, now="2026-10-14")
    assert out["written"] and (d / orr.QUARANTINE_MARKER_FILE).exists()
    assert (d / orr.QUARANTINE_MANIFEST_FILE).exists() and not (d / "OBSOLETE.md").exists()
    assert tool.mark_legacy_files(str(d), dry_run=False, now="2026-10-14")["already_marked"] is True
    prod = tmp_path / "prod"
    prod.mkdir()
    (prod / "r.csv").write_text("x\n", encoding="utf-8")
    (prod / "run_manifest.json").write_text(json.dumps({"request": {"path": "/api/v1/optimize"}}), encoding="utf-8")
    out = tool.mark_legacy_files(str(prod), dry_run=False)  # C5: A06 production-path skip
    assert "production" in out["skipped"] and not (prod / orr.QUARANTINE_MARKER_FILE).exists()


# -- E1: the cited decision must exist -----------------------------------------------------------
def test_no_dangling_a10_a11_citation_and_a13_exists():
    log = (ROOT / "docs" / "DECISION_LOG.md").read_text(encoding="utf-8")
    assert "A13" in log and "HISTORICAL_UNVERIFIED" in log
    for rel in ("obsolete_results.py", "tools/mark_obsolete_ga_split_variant_results.py", "tests/conftest.py"):
        assert "A10/A11" not in (BENCH / rel).read_text(encoding="utf-8"), rel


# -- C3: the active code path must not write to the old parent folder ---------------------------
def test_cli_engine_does_not_write_best_params_numba_json_to_results_root():
    src = (BENCH / "cli_engine.py").read_text(encoding="utf-8")
    assert 'os.path.join(RESULTS_DIR, "best_params_numba.json")' not in src
    assert 'os.path.join(RESULTS_DIR, "best_params_numba_current.json")' in src


# -- the Python-side filters never pool the two views either (the SQL layer is not the only guard) ----
def test_python_filters_keep_views_separate_and_label_historical(tmp_path):
    rows = [
        {"algorithm": "Old", "timestamp": OLD},
        {"algorithm": "New", "timestamp": NEW},
        {"algorithm": "Bad", "timestamp": NEW, "metadata": {"obsolete": True}},
    ]
    assert [r["algorithm"] for r in orr.filter_obsolete_rows(rows)] == ["New"]
    hist = orr.filter_obsolete_rows(rows, evidence="historical")
    assert [(r["algorithm"], r["evidence_class"]) for r in hist] == [("Old", HIST)]
    # INVALID rows stay hidden unless asked, independent of the evidence view
    assert [r["algorithm"] for r in orr.filter_obsolete_rows(rows, include_obsolete=True)] == ["New", "Bad"]
    csv_rows = [{"algorithm": "Old", "timestamp": OLD}, {"algorithm": "New", "timestamp": NEW}]
    assert [r["algorithm"] for r in orr.filter_obsolete_csv_rows(csv_rows, str(tmp_path))] == ["New"]
    assert [r["algorithm"] for r in orr.filter_obsolete_csv_rows(csv_rows, str(tmp_path), evidence="historical")] == ["Old"]
    with pytest.raises(ValueError):
        orr.filter_obsolete_rows(rows, evidence="all")
