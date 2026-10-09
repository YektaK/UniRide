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


# ---- review round 1 ----
import csv as _csv
from types import SimpleNamespace

import pytest

from academic_benchmark.tsplib_manager import query_benchmark_results


def test_sql_filters_before_limit(tmp_path):
    db = str(tmp_path / "t.db")
    save_benchmark_run("r1", db_path=db)
    for i in range(1, 6):  # 5 newest rows obsolete, 3 older clean
        save_benchmark_result("r1", _row("ga_split_hf", f"2026-10-0{i}T10:00:00", i), db_path=db)
    for i in range(1, 4):
        save_benchmark_result("r1", _row("ga_split", f"2026-09-0{i}T10:00:00", i), db_path=db)
    mark_sqlite(db, dry_run=False)
    assert len(query_benchmark_results(limit=3, db_path=db)) == 3
    assert get_benchmark_rows(db_path=db, limit=3)["count"] == 3
    assert len(query_benchmark_results(limit=8, db_path=db, exclude_obsolete=False)) == 8


def test_csv_fallback_respects_include_obsolete(tmp_path):
    (tmp_path / "OBSOLETE.md").write_text("x", encoding="utf-8")
    with open(tmp_path / "benchmark_progress.csv", "w", newline="", encoding="utf-8") as h:
        w = _csv.writer(h)
        w.writerow(["problem", "strategy", "run", "tour_length"])
        w.writerow(["p", "ga_split_hf", 1, 5])
        w.writerow(["p", "ga_split", 1, 6])
    kw = dict(results_dir=str(tmp_path), db_path=str(tmp_path / "none.db"), prefer_db=False)
    assert [r["algorithm"] for r in get_benchmark_rows(**kw)["results"]] == ["ga_split"]
    assert get_benchmark_rows(include_obsolete=True, **kw)["count"] == 2


def test_mark_files_skips_production_path_manifest(tmp_path):
    (tmp_path / "run_manifest.json").write_text(
        json.dumps({"scenarios": [{"path": "/api/v1/optimize", "menu": "ga_split_hf"}]}), encoding="utf-8"
    )
    report = mark_files(str(tmp_path), dry_run=False)
    assert report["files"] == [] and report.get("skipped")
    assert not (tmp_path / "OBSOLETE.md").exists()


def test_invalid_or_non_dict_metadata_is_preserved(tmp_path):
    db = _seed(tmp_path)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE benchmark_results SET metadata_json='not json{' WHERE algorithm='ga_split_hf'")
    conn.execute("UPDATE benchmark_results SET metadata_json='[1,2]' WHERE algorithm='ga-split-enhanced'")
    conn.commit(); conn.close()
    mark_sqlite(db, dry_run=False)
    conn = sqlite3.connect(db)
    got = {a: json.loads(m) for a, m in conn.execute("SELECT algorithm, metadata_json FROM benchmark_results")}
    assert got["ga_split_hf"]["_original_metadata_json"] == "not json{" and got["ga_split_hf"]["obsolete"] is True
    assert got["ga-split-enhanced"]["_original_metadata_json"] == "[1,2]"


def test_cutoff_is_exact_iso(tmp_path):
    from academic_benchmark.obsolete_results import is_affected
    assert not is_affected("ga_split_hf", "2026-10-09T00:00:00")
    assert is_affected("ga_split_hf", "2026-10-09T00:00:00", "2026-10-09T12:00:00")


@pytest.mark.parametrize("module,cls,extra", [
    ("strategies.ga_split_strategy", "GAEnhancedSplitStrategy", {}),
    ("strategies.ga_split_hf_strategy", "GASplitHFStrategy",
     {"algorithm": "ga_split_hf", "vehicle_types": [{"type_id": "large", "sw_capacity": 4, "so_capacity": 5},
                        {"type_id": "car", "sw_capacity": 0, "so_capacity": 4}],
      "minimize_type": "car"}),
])
def test_runner_seed_reaches_make_rng(module, cls, extra, monkeypatch):
    """run_seed=7 -> _apply_algorithm_params -> strategy.optimize -> make_rng(seed=7)."""
    import importlib
    from models.schemas import LocationNode, OptimizationRequest, StudentNode
    mod = importlib.import_module(module)
    seen = {}

    class Stop(Exception):
        pass

    def fake(cfg, default=None):
        seen["seed"] = cfg.get("seed")
        raise Stop

    monkeypatch.setattr(mod, "make_rng", fake)
    request = OptimizationRequest(**{"algorithm": "x", **extra,
        "depot": LocationNode(id="D", lat=0.0, lng=0.0),
        "students": [StudentNode(id="S1", location_code="L1", disability_type="So",
                                 coordinates={"lat": 3.0, "lng": 4.0})],
        "sw_capacity": 4, "so_capacity": 5, "max_travel_time": 600})
    strategy = getattr(mod, cls)()
    runner_mod = importlib.import_module("benchmark_runner")
    runner_mod.BenchmarkRunner()._apply_algorithm_params(request, strategy.name, {}, run_seed=7)
    with pytest.raises(Stop):
        strategy.optimize(request)
    assert seen["seed"] == 7
