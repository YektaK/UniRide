from academic_benchmark.run_matrix_benchmark import run_matrix_benchmark
from academic_benchmark.tsplib_manager import query_benchmark_results


def test_run_matrix_benchmark_selects_problem_types_and_persists_results(tmp_path):
    db_path = str(tmp_path / "academic.db")

    result = run_matrix_benchmark(
        db_path=db_path,
        run_id="matrix-cli-test",
        algorithms=["Core-Greedy-Routing"],
        problem_types=["cvrp", "cvrptw"],
        seed_missing_smoke=True,
    )

    rows = query_benchmark_results(run_id="matrix-cli-test", limit=10, db_path=db_path)
    by_problem = {row["problem"]: row for row in rows}

    assert result == {"run_id": "matrix-cli-test", "saved_results": 2, "errors": []}
    assert set(by_problem) == {"smoke-cvrp", "smoke-solomon"}
    assert {row["problem_type"] for row in rows} == {"cvrp", "cvrptw"}
    assert all(row["source"] == "academic_matrix_cli" for row in rows)


def test_run_matrix_benchmark_persists_multiple_algorithms(tmp_path):
    db_path = str(tmp_path / "academic.db")

    result = run_matrix_benchmark(
        db_path=db_path,
        run_id="matrix-cli-error-test",
        algorithms=["Core-Greedy-Routing", "Core-TwoOpt-TSP"],
        problem_types=["cvrp"],
        seed_missing_smoke=True,
    )

    rows = query_benchmark_results(run_id="matrix-cli-error-test", limit=10, db_path=db_path)

    assert result == {"run_id": "matrix-cli-error-test", "saved_results": 2, "errors": []}
    assert {row["algorithm"] for row in rows} == {"Core-Greedy-Routing", "Core-TwoOpt-TSP"}
    assert {row["status"] for row in rows} == {"completed"}
