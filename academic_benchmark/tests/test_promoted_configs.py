from academic_benchmark.promoted_configs import (
    build_promoted_configs,
    load_promoted_configs,
    resolve_promoted_params,
    write_promoted_configs,
)
from academic_benchmark.tsplib_manager import (
    get_db,
    init_db,
    save_benchmark_result,
    save_benchmark_run,
    save_best_solution,
)


def test_build_promoted_configs_selects_best_per_algorithm_problem_type(tmp_path):
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
    save_best_solution("tiny", "GA", {"population_size": 16}, [1, 3, 2, 4], 11.0, 10.0, db_path=db_path)

    document = build_promoted_configs(db_path=db_path, generated_at="2026-05-31T12:00:00")

    assert document["schema_version"] == 1
    assert document["generated_at"] == "2026-05-31T12:00:00"
    assert resolve_promoted_params(document, "GA", problem_type="tsp") == {"population_size": 16}


def test_promoted_configs_include_routing_benchmark_result_params(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    save_benchmark_run("run-1", source="web_matrix_native", db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "tiny-cvrp",
            "algorithm": "Core-Greedy-Routing",
            "problem_type": "cvrp",
            "matrix_kind": "distance",
            "objective_cost": 50.0,
            "gap": 4.0,
            "params": {"split": "linear"},
        },
        db_path=db_path,
    )
    save_benchmark_result(
        "run-1",
        {
            "problem": "tiny-cvrp",
            "algorithm": "Core-Greedy-Routing",
            "problem_type": "cvrp",
            "matrix_kind": "distance",
            "objective_cost": 55.0,
            "gap": 8.0,
            "params": {"split": "string"},
        },
        db_path=db_path,
    )

    document = build_promoted_configs(db_path=db_path)

    assert resolve_promoted_params(document, "Core-Greedy-Routing", problem_type="cvrp") == {
        "split": "linear",
    }
    config = document["configs"][0]
    assert config["source_table"] == "benchmark_results"
    assert config["selected_from"]["run_id"] == "run-1"


def test_promoted_configs_can_include_empty_param_routing_results(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    save_benchmark_run("run-1", source="web_matrix_native", db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "tiny-cvrp",
            "algorithm": "OR-Tools",
            "problem_type": "cvrp",
            "matrix_kind": "distance",
            "objective_cost": 50.0,
            "capacity_violations": 0,
            "tw_violations": 0,
            "params": {},
        },
        db_path=db_path,
    )

    strict_document = build_promoted_configs(db_path=db_path)
    allowed_document = build_promoted_configs(db_path=db_path, include_empty_params=True)

    assert resolve_promoted_params(strict_document, "OR-Tools", problem_type="cvrp") is None
    assert resolve_promoted_params(allowed_document, "OR-Tools", problem_type="cvrp") == {}
    assert allowed_document["configs"][0]["source_table"] == "benchmark_results"


def test_promoted_configs_ignore_failed_or_infeasible_routing_results(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    save_benchmark_run("run-1", source="web_matrix_native", db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "bad-cvrptw",
            "algorithm": "OR-Tools",
            "problem_type": "cvrptw",
            "matrix_kind": "distance",
            "objective_cost": 10.0,
            "gap": -90.0,
            "tw_violations": 2,
            "params": {"time_limit_seconds": 1},
        },
        db_path=db_path,
    )
    save_benchmark_result(
        "run-1",
        {
            "problem": "failed-cvrptw",
            "algorithm": "OR-Tools",
            "problem_type": "cvrptw",
            "matrix_kind": "distance",
            "objective_cost": None,
            "metadata": {"execution_failed": True},
            "params": {"time_limit_seconds": 2},
        },
        db_path=db_path,
    )
    save_benchmark_result(
        "run-1",
        {
            "problem": "good-cvrptw",
            "algorithm": "OR-Tools",
            "problem_type": "cvrptw",
            "matrix_kind": "distance",
            "objective_cost": 100.0,
            "gap": 5.0,
            "capacity_violations": 0,
            "tw_violations": 0,
            "params": {"time_limit_seconds": 30},
        },
        db_path=db_path,
    )

    document = build_promoted_configs(db_path=db_path)

    assert resolve_promoted_params(document, "OR-Tools", problem_type="cvrptw") == {
        "time_limit_seconds": 30,
    }
    config = document["configs"][0]
    assert config["selected_from"]["problem"] == "good-cvrptw"


def test_write_and_load_promoted_configs_round_trip(tmp_path):
    db_path = str(tmp_path / "tsplib.db")
    output_path = str(tmp_path / "promoted_configs.json")
    save_benchmark_run("run-1", db_path=db_path)
    save_benchmark_result(
        "run-1",
        {
            "problem": "tiny-atsp",
            "algorithm": "Numba-Or-opt",
            "problem_type": "atsp",
            "matrix_kind": "travel_time",
            "objective_cost": 20.0,
            "params": {"max_passes": 2},
        },
        db_path=db_path,
    )

    written = write_promoted_configs(
        db_path=db_path,
        output_path=output_path,
        generated_at="2026-05-31T12:00:00",
    )
    loaded = load_promoted_configs(output_path)

    assert loaded == written
    assert resolve_promoted_params(
        loaded,
        "Numba-Or-opt",
        problem_type="atsp",
        matrix_kind="travel_time",
    ) == {"max_passes": 2}
