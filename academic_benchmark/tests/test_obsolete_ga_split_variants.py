import json
import sqlite3

from academic_benchmark.matrix_run_summary import summarize_run
from academic_benchmark.promoted_configs import build_promoted_configs
from academic_benchmark.results_reader import get_benchmark_rows
from academic_benchmark.tools.mark_obsolete_ga_split_variant_results import main, mark_files, mark_sqlite
from academic_benchmark.tsplib_manager import save_benchmark_result, save_benchmark_run


def _row(algorithm, ts, run_number=1, metadata=None):
    return {
        "problem": "tiny", "algorithm": algorithm, "run_number": run_number,
        "problem_type": "cvrp", "objective_cost": 10.0 + run_number, "tour_cost": 10.0,
        "params": {"max_iterations": 5}, "metadata": metadata or {"keep": "me"}, "timestamp": ts,
    }


def _seed(tmp_path):
    db = str(tmp_path / "t.db")
    save_benchmark_run("r1", source="web", db_path=db)
    for algo, ts in [
        ("ga_split_enhanced", "2026-10-05T10:00:00"),
        ("ga-split-enhanced", "2026-10-06T10:00:00"),
        ("ga_split_hf", "2026-10-07T10:00:00"),
        ("ga_split_enhanced", "2026-10-10T10:00:00"),  # new path, after the decision
        ("ga_split", "2026-10-05T10:00:00"),            # other algorithm
    ]:
        save_benchmark_result("r1", _row(algo, ts), db_path=db)
    return db


def test_dry_run_counts_and_does_not_write(tmp_path):
    db = _seed(tmp_path)
    report = mark_sqlite(db, dry_run=True)
    assert report["to_mark"] == 3
    assert report["by_algorithm"] == {"ga_split_enhanced": 1, "ga-split-enhanced": 1, "ga_split_hf": 1}
    assert report["by_run"] == {"r1": 3} and report["by_problem"] == {"tiny": 3}
    assert mark_sqlite(db, dry_run=True)["to_mark"] == 3  # still nothing written


def test_mark_preserves_metadata_is_idempotent_and_scoped(tmp_path):
    db = _seed(tmp_path)
    assert mark_sqlite(db, dry_run=False, now="T0")["to_mark"] == 3
    again = mark_sqlite(db, dry_run=False, now="T1")
    assert again["to_mark"] == 0 and again["already_marked"] == 3
    conn = sqlite3.connect(db)
    marked = {r[0]: json.loads(r[1]) for r in conn.execute("SELECT id, metadata_json FROM benchmark_results")}
    assert sum(1 for m in marked.values() if m.get("obsolete")) == 3
    assert all(m["keep"] == "me" for m in marked.values())
    assert [m["obsolete_marked_at"] for m in marked.values() if m.get("obsolete")] == ["T0"] * 3
    assert conn.execute("SELECT COUNT(*) FROM benchmark_results").fetchone()[0] == 5


def test_readers_exclude_obsolete_by_default_with_opt_in(tmp_path):
    db = _seed(tmp_path)
    mark_sqlite(db, dry_run=False)
    default = get_benchmark_rows(db_path=db)
    assert sorted(r["algorithm"] for r in default["results"]) == ["ga_split", "ga_split_enhanced"]
    assert get_benchmark_rows(db_path=db, include_obsolete=True)["count"] == 5
    assert summarize_run("r1", db_path=db)["total_rows"] == 2
    assert summarize_run("r1", db_path=db, include_obsolete=True)["total_rows"] == 5
    default_cfg = build_promoted_configs(db_path=db, include_empty_params=True)
    assert all(c["algorithm"] != "ga_split_hf" for c in default_cfg["configs"])
    opt_in = build_promoted_configs(db_path=db, include_empty_params=True, include_obsolete=True)
    assert any(c["algorithm"] == "ga_split_hf" for c in opt_in["configs"])


def test_mark_files_writes_sibling_note_and_deletes_nothing(tmp_path):
    (tmp_path / "a.csv").write_text("algorithm\nga_split_hf\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("algorithm\nga_split\n", encoding="utf-8")
    assert mark_files(str(tmp_path), dry_run=True)["files"] == ["a.csv"]
    assert not (tmp_path / "OBSOLETE.md").exists()
    mark_files(str(tmp_path), dry_run=False)
    assert "a.csv" in (tmp_path / "OBSOLETE.md").read_text(encoding="utf-8")
    assert (tmp_path / "a.csv").exists() and (tmp_path / "b.csv").exists()


def test_cli_dry_run_prints_report(tmp_path, capsys):
    db = _seed(tmp_path)
    assert main(["--db", db, "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["sqlite"]["to_mark"] == 3
