from academic_benchmark.run_fcm_srs_comparison import (
    build_synthetic_large_tsp,
    run_fcm_srs_comparison,
)
from academic_benchmark.tsplib_manager import query_benchmark_results


def test_build_synthetic_large_tsp_has_coordinates_and_matrix():
    problem = build_synthetic_large_tsp(12)

    assert problem.name == "synthetic-fcm-tsp-12"
    assert problem.problem_type == "tsp"
    assert problem.dimension == 12
    assert len(problem.coordinates) == 12
    assert problem.matrix.values.shape == (12, 12)


def test_run_fcm_srs_comparison_persists_core_and_fcm_results(tmp_path):
    db_path = str(tmp_path / "fcm-comparison.db")

    result = run_fcm_srs_comparison(
        db_path=db_path,
        run_id="fcm-comparison-test",
        dimension=12,
        algorithms=["Core-GA-TSP", "FCM-GA-TSP"],
        population_size=6,
        max_iterations=4,
        fcm_polish_iterations=10,
    )

    rows = query_benchmark_results(run_id="fcm-comparison-test", limit=10, db_path=db_path)

    assert result["saved_results"] == 2
    assert result["errors"] == []
    assert {row["algorithm"] for row in rows} == {"Core-GA-TSP", "FCM-GA-TSP"}
    assert all(row["source"] == "fcm_srs_comparison" for row in rows)
    assert all(row["status"] == "completed" for row in rows)
    assert all(row["objective_cost"] > 0 for row in rows)
    assert all(set(row["tour"]) == set(range(12)) for row in rows)
