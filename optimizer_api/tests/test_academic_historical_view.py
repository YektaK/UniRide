"""A13: the three academic endpoints return labelled historical_unverified data on request
(include_historical=true), never pooled into the default (current) results, and are not empty."""

import pytest
from fastapi import HTTPException

from academic_benchmark import results_reader
from academic_benchmark.tsplib_manager import get_db, init_db, save_benchmark_result, save_benchmark_run
from optimizer_api.routers import benchmark

OLD = "2026-06-30T20:05:09"
NEW = "2026-10-14T09:00:00"


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    conn = get_db(path)
    init_db(conn)
    conn.execute("INSERT INTO problems (name, dimension, category) VALUES ('tiny', 3, 'small')")
    for algo, ts in (("Old", OLD), ("New", NEW)):
        conn.execute(
            "INSERT INTO best_solutions (problem_name, algorithm, params_json, tour_nodes, tour_length, gap, timestamp)"
            " VALUES ('tiny', ?, '{}', '[0,1,2]', 5.0, 0.0, ?)", (algo, ts))
    conn.commit()
    conn.close()
    save_benchmark_run("r1", source="web", db_path=path)
    for i, (algo, ts) in enumerate((("Old", OLD), ("New", NEW)), 1):
        save_benchmark_result("r1", {"problem": "tiny", "algorithm": algo, "run_number": i, "problem_type": "tsp",
                                     "objective_cost": 1.0, "tour_cost": 1.0, "params": {}, "metadata": {},
                                     "timestamp": ts}, db_path=path)
    for name in ("get_leaderboard", "get_best_result", "get_benchmark_rows"):
        real = getattr(results_reader, name)
        monkeypatch.setattr(results_reader, name, lambda *a, _real=real, **kw: _real(*a, db_path=path, **kw))
    return path


def test_leaderboard_default_current_only_and_historical_on_request(db):
    default = benchmark.get_academic_leaderboard()
    assert [r["algorithm"] for r in default["results"]] == ["New"]
    assert default["historical_unverified_available"] is True
    out = benchmark.get_academic_leaderboard(include_historical=True)
    assert [r["algorithm"] for r in out["results"]] == ["New"]
    assert [r["algorithm"] for r in out["historical_unverified"]["results"]] == ["Old"]
    assert out["historical_unverified"]["results"][0]["evidence_class"] == "historical_unverified"


def test_best_default_404_points_to_historical_view_and_historical_is_returned(db):
    with pytest.raises(HTTPException) as exc:
        benchmark.get_academic_best_result(problem="tiny", algorithm="Old")
    assert exc.value.status_code == 404 and "include_historical" in exc.value.detail
    out = benchmark.get_academic_best_result(problem="tiny", algorithm="Old", include_historical=True)
    assert out["historical_unverified"]["result"]["evidence_class"] == "historical_unverified"


def test_benchmark_results_historical_on_request(db):
    out = benchmark.get_academic_benchmark_results(limit=10, feasible_only=False, include_historical=True)
    assert [r["algorithm"] for r in out["results"]] == ["New"]
    assert [r["algorithm"] for r in out["historical_unverified"]["results"]] == ["Old"]
