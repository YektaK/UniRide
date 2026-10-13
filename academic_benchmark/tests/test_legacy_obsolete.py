"""Legacy rule: every result stamped before LEGACY_CUTOFF (2026-10-13) is obsolete.

Pins DECISION_LOG A06/A07 behaviour unchanged and the new legacy rule: rule-based
(timestamp) filtering for best_solutions, benchmark_results and CSV directories,
plus the marking tool's ``--rule legacy``. Nothing is ever deleted.
"""

import csv
import json
import sqlite3

import pytest

from academic_benchmark import obsolete_results as orr
from academic_benchmark.dashboard_utils import load_csv_frames, load_tuning_frames
from academic_benchmark.obsolete_results import (
    LEGACY_CUTOFF,
    LEGACY_REASON,
    filter_obsolete_csv_rows,
    is_obsolete_row,
)
from academic_benchmark.promoted_configs import build_promoted_configs
from academic_benchmark.results_reader import get_benchmark_rows, get_best_result, get_leaderboard
from academic_benchmark.tools import mark_obsolete_ga_split_variant_results as tool
from academic_benchmark.tsplib_manager import (
    analyze_solution_patterns,
    get_best_solution,
    get_db,
    init_db,
    query_benchmark_results,
    query_best_solutions,
    save_benchmark_result,
    save_benchmark_run,
)

OLD = "2026-06-30T20:05:09.510851"
EDGE_BEFORE = "2026-10-12T23:59:59.999999"
NEW = "2026-10-13T00:00:00"
LATER = "2026-11-02T08:00:00"


@pytest.fixture(autouse=True)
def real_cutoff(monkeypatch):
    # pin the real 2026-10-13 cutoff (conftest neutralises it only for the A06 test module)
    monkeypatch.setattr(orr, "LEGACY_CUTOFF", "2026-10-13")


def test_constants():
    assert LEGACY_CUTOFF == "2026-10-13"
    assert "not evidence" in LEGACY_REASON and "do not pool" in LEGACY_REASON


@pytest.mark.parametrize("algo", ["Numba-HHO", "GA-Split", "test_algo", "ga_split", "anything"])
def test_rule_any_algorithm_before_cutoff(algo):
    assert is_obsolete_row({"algorithm": algo, "timestamp": OLD})
    assert is_obsolete_row({"algorithm": algo, "timestamp": EDGE_BEFORE})
    assert not is_obsolete_row({"algorithm": algo, "timestamp": NEW})
    assert not is_obsolete_row({"algorithm": algo, "timestamp": LATER})


def test_rule_absent_timestamp_column_is_not_legacy_but_metadata_still_works():
    assert not is_obsolete_row({"algorithm": "x"})
    # timestamp column present but empty: fail-closed, hidden like the SQL readers (NULL/empty >= cutoff is false)
    assert is_obsolete_row({"algorithm": "x", "timestamp": ""})
    assert is_obsolete_row({"algorithm": "x", "timestamp": NEW, "metadata": {"obsolete": True}})
    assert is_obsolete_row({"metadata_json": json.dumps({"obsolete": True}), "timestamp": LATER})


def test_a06_rule_unchanged():
    assert orr.OBSOLETE_CUTOFF == "2026-10-09"
    assert orr.is_affected("ga_split_hf", "2026-10-08") and not orr.is_affected("ga_split_hf", "2026-10-09")
    assert not orr.is_affected("ga_split", "2026-10-01")


def _best_db(tmp_path):
    db = str(tmp_path / "t.db")
    conn = get_db(db)
    init_db(conn)
    conn.execute("INSERT INTO problems (name, dimension, category) VALUES ('tiny', 3, 'small')")
    for algo, ts, length in [("GA-Split", OLD, 10.0), ("GA-Split", NEW, 12.0), ("test_algo", OLD, 1.0), ("SOTA-X", LATER, 9.0)]:
        conn.execute(
            "INSERT INTO best_solutions (problem_name, algorithm, params_json, tour_nodes, tour_length, gap, timestamp)"
            " VALUES ('tiny', ?, '{}', '[0,1,2]', ?, 0.0, ?)",
            (algo, length, ts),
        )
    conn.commit()
    conn.close()
    return db


def test_best_solutions_hidden_by_default(tmp_path):
    db = _best_db(tmp_path)
    default = query_best_solutions(db_path=db)
    assert sorted((r["algorithm"], r["timestamp"]) for r in default) == [("GA-Split", NEW), ("SOTA-X", LATER)]
    assert len(query_best_solutions(db_path=db, include_obsolete=True)) == 4
    # filter applies before LIMIT: lowest legacy length (1.0) must not fill the page
    assert [r["tour_length"] for r in query_best_solutions(db_path=db, limit=1)] == [9.0]
    assert get_best_solution("tiny", "GA-Split", db_path=db)["tour_length"] == 12.0  # legacy 10.0 hidden
    assert get_best_solution("tiny", "test_algo", db_path=db) is None
    assert get_best_solution("tiny", "test_algo", db_path=db, include_obsolete=True)["tour_length"] == 1.0
    assert get_best_solution("tiny", "GA-Split", db_path=db, include_obsolete=True)["tour_length"] == 10.0


def test_results_reader_and_patterns_and_promoted_best_solutions(tmp_path):
    db = _best_db(tmp_path)
    assert get_leaderboard(db_path=db)["count"] == 2
    assert get_leaderboard(db_path=db, include_obsolete=True)["count"] == 4
    assert get_best_result("tiny", "test_algo", db_path=db)["result"] is None
    assert get_best_result("tiny", "test_algo", db_path=db, include_obsolete=True)["result"] is not None
    assert "test_algo" not in analyze_solution_patterns(db_path=db)
    assert "test_algo" in analyze_solution_patterns(db_path=db, include_obsolete=True)
    algos = {c["algorithm"] for c in build_promoted_configs(db_path=db, include_empty_params=True)["configs"]}
    assert "test_algo" not in algos
    algos = {
        c["algorithm"]
        for c in build_promoted_configs(db_path=db, include_empty_params=True, include_obsolete=True)["configs"]
    }
    assert "test_algo" in algos


def _row(algorithm, ts, n=1, metadata=None):
    return {
        "problem": "tiny", "algorithm": algorithm, "run_number": n, "problem_type": "tsp",
        "objective_cost": 10.0 + n, "tour_cost": 10.0 + n, "params": {"k": 1},
        "metadata": metadata or {"keep": "me"}, "timestamp": ts,
    }


def _results_db(tmp_path):
    db = str(tmp_path / "r.db")
    save_benchmark_run("r1", source="web", db_path=db)
    for i, (algo, ts) in enumerate(
        [("Numba-HHO", OLD), ("Core-GWO-TSP", OLD), ("Numba-HHO", NEW), ("Numba-GWO", LATER)], 1
    ):
        save_benchmark_result("r1", _row(algo, ts, i), db_path=db)
    return db


def test_benchmark_results_hidden_by_default_before_limit(tmp_path):
    db = _results_db(tmp_path)
    assert len(query_benchmark_results(db_path=db)) == 2
    assert len(query_benchmark_results(db_path=db, exclude_obsolete=False)) == 4
    assert len(query_benchmark_results(db_path=db, limit=2)) == 2
    assert get_benchmark_rows(db_path=db)["count"] == 2
    assert get_benchmark_rows(db_path=db, include_obsolete=True)["count"] == 4


def test_marker_tool_legacy_dry_run_writes_nothing(tmp_path):
    db = _results_db(tmp_path)
    before = open(db, "rb").read()
    report = tool.mark_sqlite(db, dry_run=True, rule="legacy")
    assert report["to_mark"] == 2 and report["by_algorithm"] == {"Numba-HHO": 1, "Core-GWO-TSP": 1}
    assert open(db, "rb").read() == before
    assert tool.main(["--db", db, "--rule", "legacy", "--dry-run"]) == 0
    assert open(db, "rb").read() == before


def test_marker_tool_legacy_marks_only_metadata_and_is_idempotent(tmp_path):
    db = _results_db(tmp_path)
    conn = sqlite3.connect(db)

    def snap():
        return conn.execute(
            "SELECT id, run_id, problem_name, algorithm, run_number, objective_cost, tour_cost, params_json, timestamp"
            " FROM benchmark_results ORDER BY id"
        ).fetchall()

    cols_before = snap()
    assert tool.mark_sqlite(db, dry_run=False, rule="legacy", now="T0")["to_mark"] == 2
    again = tool.mark_sqlite(db, dry_run=False, rule="legacy", now="T1")
    assert again["to_mark"] == 0 and again["already_marked"] == 2
    assert snap() == cols_before
    meta = {r[0]: json.loads(r[1]) for r in conn.execute("SELECT id, metadata_json FROM benchmark_results")}
    marked = [m for m in meta.values() if m.get("obsolete")]
    assert len(marked) == 2 and all(m["keep"] == "me" and m["obsolete_reason"] == LEGACY_REASON for m in marked)
    assert all(m["obsolete_marked_at"] == "T0" for m in marked)
    assert conn.execute("SELECT COUNT(*) FROM benchmark_results").fetchone()[0] == 4
    assert len(query_benchmark_results(db_path=db)) == 2


def test_marker_tool_default_rule_is_a06_and_ignores_legacy(tmp_path):
    db = _results_db(tmp_path)
    assert tool.mark_sqlite(db, dry_run=True)["to_mark"] == 0


def test_opt_tours_untouched(tmp_path):
    db = _results_db(tmp_path)
    conn = get_db(db)
    init_db(conn)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("INSERT INTO opt_tours VALUES ('tiny','[0,1,2]',3.0,'tsplib','2026-05-01T00:00:00')")
    conn.commit()
    conn.close()
    tool.mark_sqlite(db, dry_run=False, rule="legacy")
    c = sqlite3.connect(db)
    assert c.execute("SELECT * FROM opt_tours").fetchall() == [("tiny", "[0,1,2]", 3.0, "tsplib", "2026-05-01T00:00:00")]


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        w = csv.DictWriter(handle, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_csv_marker_hides_legacy_rows_in_readers(tmp_path):
    d = tmp_path
    tool.mark_legacy_files(str(d), dry_run=False, now="2026-10-13")
    marker = (d / "OBSOLETE.md").read_text(encoding="utf-8")
    assert "Legacy-Cutoff: 2026-10-13" in marker and "not deleted" in marker
    _write(d / "benchmark_progress.csv", [
        {"timestamp": OLD, "problem": "p", "strategy": "Numba-HHO", "avg_length": 1},
        {"timestamp": NEW, "problem": "p", "strategy": "Numba-HHO", "avg_length": 2},
    ])
    _write(d / "benchmark_summary.csv", [{"problem": "p", "strategy": "Numba-HHO", "avg_length": 1}])
    _write(d / "tuning_progress.csv", [
        {"timestamp": OLD, "problem": "p", "strategy": "A"}, {"timestamp": LATER, "problem": "p", "strategy": "B"},
    ])
    summ, prog, _ = load_csv_frames([str(d)])
    assert len(prog[0]) == 1 and prog[0].iloc[0]["avg_length"] == 2
    assert len(summ[0]) == 0  # summary has no timestamp: whole file is legacy under the marker
    assert [len(f) for f in load_tuning_frames([str(d)])[0]] == [1]
    assert load_csv_frames([str(d)], include_obsolete=True)[1][0].shape[0] == 2
    rows = get_benchmark_rows(results_dir=str(d), db_path=str(d / "none.db"))
    assert rows["count"] == 1
    assert get_benchmark_rows(results_dir=str(d), db_path=str(d / "none.db"), include_obsolete=True)["count"] == 2


def test_a06_style_marker_still_only_affects_algorithms(tmp_path):
    (tmp_path / "OBSOLETE.md").write_text("obsolete", encoding="utf-8")
    rows = [{"algorithm": "ga_split", "problem": "a"}, {"algorithm": "ga_split_hf", "problem": "b"}]
    assert filter_obsolete_csv_rows(rows, str(tmp_path)) == [rows[0]]


def test_mark_legacy_files_dry_run_and_append(tmp_path):
    assert tool.mark_legacy_files(str(tmp_path), dry_run=True)["written"] is False
    assert not (tmp_path / "OBSOLETE.md").exists()
    (tmp_path / "OBSOLETE.md").write_text("A06 note\n", encoding="utf-8")
    tool.mark_legacy_files(str(tmp_path), dry_run=False, now="2026-10-13")
    text = (tmp_path / "OBSOLETE.md").read_text(encoding="utf-8")
    assert text.startswith("A06 note") and "Legacy-Cutoff" in text
    tool.mark_legacy_files(str(tmp_path), dry_run=False, now="2026-10-13")
    assert (tmp_path / "OBSOLETE.md").read_text(encoding="utf-8") == text  # idempotent


# ---- legacy subfolder layout (user decision: old CSVs moved to legacy_pre_2026-10-13/) ----
import os
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]


def test_repo_layout_old_csvs_moved_markers_only_in_legacy_dirs():
    for top in ("numba_results", "sota_results"):
        assert not (BENCH / top / "OBSOLETE.md").exists()
        legacy = BENCH / top / orr.LEGACY_RESULTS_DIRNAME
        assert (legacy / "OBSOLETE.md").exists()
        assert (legacy / "benchmark_progress.csv").exists() and (legacy / "benchmark_summary.csv").exists()
        assert not (BENCH / top / "benchmark_progress.csv").exists()
    assert (BENCH / "numba_results" / orr.LEGACY_RESULTS_DIRNAME / "bildiri_import" / "OBSOLETE.md").exists()
    assert (BENCH / "sota_results" / orr.LEGACY_RESULTS_DIRNAME / "doe_sota" / "OBSOLETE.md").exists()
    assert (BENCH / "sota_results" / orr.LEGACY_RESULTS_DIRNAME / "doe_sota" / "tuning_progress.csv").exists()


def test_real_result_dirs_show_no_legacy_data_by_default_and_all_with_opt_in():
    dirs = [str(BENCH / "sota_results"), str(BENCH / "numba_results")]
    s, p, _ = load_csv_frames(dirs)
    t, _ = load_tuning_frames(dirs)
    assert s == [] and p == [] and t == [] or all(len(f) == 0 for f in s + p + t)
    s, p, _ = load_csv_frames(dirs, include_obsolete=True)
    t, _ = load_tuning_frames(dirs, include_obsolete=True)
    assert sum(len(f) for f in p) > 0 and sum(len(f) for f in s) > 0 and sum(len(f) for f in t) > 0


def test_new_rows_in_main_dir_visible_next_to_legacy_subdir(tmp_path):
    legacy = tmp_path / orr.LEGACY_RESULTS_DIRNAME
    legacy.mkdir()
    tool.mark_legacy_files(str(legacy), dry_run=False, now="2026-10-13")
    _write(legacy / "benchmark_progress.csv", [{"timestamp": OLD, "problem": "p", "strategy": "Old", "avg_length": 1}])
    _write(legacy / "tuning_progress.csv", [{"timestamp": OLD, "problem": "p", "strategy": "Old"}])
    # a new run writes into the main directory: no marker there, summary has no timestamp
    _write(tmp_path / "benchmark_progress.csv", [{"timestamp": LATER, "problem": "p", "strategy": "New", "avg_length": 2}])
    _write(tmp_path / "benchmark_summary.csv", [{"problem": "p", "strategy": "New", "avg_length": 2}])
    _write(tmp_path / "tuning_progress.csv", [{"timestamp": LATER, "problem": "p", "strategy": "New"}])
    s, p, _ = load_csv_frames([str(tmp_path)])
    t, _ = load_tuning_frames([str(tmp_path)])
    assert [list(f["strategy"]) for f in s + p + t if len(f)] == [["New"], ["New"], ["New"]]
    rows = get_benchmark_rows(results_dir=str(tmp_path), db_path=str(tmp_path / "none.db"))
    assert [r["algorithm"] if "algorithm" in r else r.get("strategy") for r in rows["results"]] == ["New"]
    s, p, _ = load_csv_frames([str(tmp_path)], include_obsolete=True)
    t, _ = load_tuning_frames([str(tmp_path)], include_obsolete=True)
    assert sorted(x for f in p for x in f["strategy"]) == ["New", "Old"]
    assert sorted(x for f in t for x in f["strategy"]) == ["New", "Old"]


def test_warmup_does_not_use_legacy_parameters(tmp_path):
    """DECISION 2026-10-13: legacy parameters are not used for warm start."""
    from academic_benchmark.benchmark_utils import load_best_params

    db = _best_db(tmp_path)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE best_solutions SET params_json='{\"k\": 7}'")
    conn.commit()
    conn.close()
    assert load_best_params("tiny", "test_algo", db) is None
    assert get_best_solution("tiny", "test_algo", db_path=db) is None
    assert load_best_params("tiny", "GA-Split", db) == {"k": 7}  # the post-cutoff row of the same algorithm
