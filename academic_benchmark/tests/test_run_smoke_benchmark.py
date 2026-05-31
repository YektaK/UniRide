from academic_benchmark.run_smoke_benchmark import run_smoke_benchmark
from academic_benchmark.tsplib_manager import query_benchmark_results


def test_run_smoke_benchmark_persists_all_seeded_problem_types(tmp_path):
    db_path = str(tmp_path / "academic.db")

    result = run_smoke_benchmark(db_path=db_path, run_id="smoke-test")
    rows = query_benchmark_results(run_id="smoke-test", limit=10, db_path=db_path)
    by_type = {row["problem_type"]: row for row in rows}

    assert result == {"run_id": "smoke-test", "saved_results": 5, "errors": []}
    assert {"tsp", "atsp", "cvrp", "cvrptw", "uniride"}.issubset(by_type)
    assert all(row["source"] == "academic_matrix_smoke" for row in rows)
    assert all(row["status"] == "completed" for row in rows)
    assert by_type["uniride"]["matrix_kind"] == "travel_time"
    assert by_type["uniride"]["route_loads"]
