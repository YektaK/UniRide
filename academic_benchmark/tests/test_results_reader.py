import csv
import json

from academic_benchmark.results_reader import (
    get_academic_problems,
    get_benchmark_rows,
    get_best_result,
    get_leaderboard,
)
from academic_benchmark.tsplib_manager import get_db, init_db, save_best_solution
from academic_benchmark.tsplib_manager import save_benchmark_result, save_benchmark_run


def test_results_reader_returns_academic_leaderboard(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    conn = get_db(db_path)
    init_db(conn)
    conn.execute(
        "INSERT INTO problems (name, dimension, optimal, category, edge_weight_type, problem_type) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("tiny", 4, 10, "small", "EUC_2D", "TSP"),
    )
    conn.commit()
    conn.close()

    save_best_solution("tiny", "GA", {"population_size": 8}, [1, 2, 3, 4], 12.0, 20.0, db_path=db_path)

    leaderboard = get_leaderboard(limit=10, db_path=db_path)
    best = get_best_result("tiny", "GA", db_path=db_path)

    assert leaderboard["source"] == "academic_db"
    assert leaderboard["count"] == 1
    assert leaderboard["results"][0]["problem"] == "tiny"
    assert leaderboard["results"][0]["dimension"] == 4
    assert best["result"]["algorithm"] == "GA"


def test_results_reader_returns_routing_benchmark_rows(tmp_path):
    csv_path = tmp_path / "benchmark_progress.csv"
    fields = [
        "timestamp", "problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs",
        "problem_type", "matrix_kind", "objective_cost", "num_vehicles",
        "capacity_violations", "tw_violations", "routes_json", "route_loads_json",
        "route_costs_json", "params_json", "gap_type",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2026-05-26T00:00:00",
            "problem": "tiny-cvrptw",
            "strategy": "Core-Greedy-Routing",
            "avg_length": "40",
            "avg_gap": "0",
            "avg_time_ms": "12",
            "n_runs": "1",
            "problem_type": "cvrptw",
            "matrix_kind": "distance",
            "objective_cost": "40",
            "num_vehicles": "1",
            "capacity_violations": "0",
            "tw_violations": "1",
            "routes_json": json.dumps([[1, 2]]),
            "route_loads_json": json.dumps([[2]]),
            "route_costs_json": json.dumps([40]),
            "params_json": json.dumps({"alpha": 1}),
            "gap_type": "unknown",
        })

    rows = get_benchmark_rows(results_dir=str(tmp_path), limit=10, prefer_db=False)

    assert rows["source"] == "academic_csv"
    assert rows["count"] == 1
    result = rows["results"][0]
    assert result["problem_type"] == "cvrptw"
    assert result["routes"] == [[1, 2]]
    assert result["route_loads"] == [[2]]
    assert result["tw_violations"] == 1
    assert result["params"] == {"alpha": 1}


def test_results_reader_prefers_sqlite_benchmark_rows(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    save_benchmark_run("run-1", source="web_matrix_native", settings={"n_runs": 1}, db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "tiny-cvrp",
            "algorithm": "Core-Greedy-Routing",
            "run_number": 1,
            "problem_type": "cvrp",
            "matrix_kind": "distance",
            "objective_cost": 42.0,
            "tour_cost": 42.0,
            "gap": 0.0,
            "elapsed_ms": 5.0,
            "routes": [[1, 2]],
            "num_vehicles": 1,
            "capacity_violations": 0,
            "tw_violations": 0,
            "params": {"mode": "test"},
        },
        db_path=db_path,
    )

    rows = get_benchmark_rows(db_path=db_path, results_dir=str(tmp_path), limit=10)

    assert rows["source"] == "academic_db"
    assert rows["count"] == 1
    result = rows["results"][0]
    assert result["run_id"] == "run-1"
    assert result["problem_type"] == "cvrp"
    assert result["routes"] == [[1, 2]]
    assert result["params"] == {"mode": "test"}


def test_query_benchmark_results_filters_rows(tmp_path):
    from academic_benchmark.tsplib_manager import query_benchmark_results

    db_path = str(tmp_path / "tsplib.db")
    save_benchmark_run("run-1", db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "p1",
            "algorithm": "A",
            "problem_type": "tsp",
            "tour_cost": 10,
            "objective_cost": 10,
        },
        db_path=db_path,
    )
    save_benchmark_result(
        "run-1",
        {
            "problem": "p2",
            "algorithm": "B",
            "problem_type": "cvrp",
            "tour_cost": 20,
            "objective_cost": 20,
        },
        db_path=db_path,
    )

    rows = query_benchmark_results(problem_type="cvrp", db_path=db_path)

    assert len(rows) == 1
    assert rows[0]["problem"] == "p2"
    assert rows[0]["algorithm"] == "B"


def test_results_reader_returns_academic_problem_inventory(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    conn = get_db(db_path)
    init_db(conn)
    conn.execute(
        "INSERT INTO problems (name, dimension, optimal, category, edge_weight_type, problem_type) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("tiny-cvrp", 4, None, "synthetic", "EXPLICIT", "CVRP"),
    )
    conn.execute(
        "INSERT INTO routing_constraints "
        "(problem_name, demands_json, capacities_json, time_windows_json, service_times_json, "
        "depot_index, max_route_duration, matrix_kind, direction, num_vehicles, metadata_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("tiny-cvrp", "[0,1,2,3]", "[4]", None, None, 0, None, "distance", "pickup", 1, "{}"),
    )
    conn.commit()
    conn.close()

    result = get_academic_problems(problem_type="cvrp", db_path=db_path)

    assert result["source"] == "academic_db"
    assert result["count"] == 1
    row = result["results"][0]
    assert row["name"] == "tiny-cvrp"
    assert row["problem_type"] == "cvrp"
    assert row["has_demands"] is True
    assert row["has_capacities"] is True
    assert row["num_vehicles"] == 1
