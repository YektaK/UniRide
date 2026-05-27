from dataclasses import asdict
import json
import sqlite3

import numpy as np

from academic_benchmark.tsplib_manager import (
    query_benchmark_results,
    save_benchmark_result,
    save_benchmark_run,
)
from uniride_core.algorithms.greedy_engine import GreedyMatrixEngine
from uniride_core.benchmark_runner import MatrixAlgorithmConfig, MatrixBenchmarkRunner
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem


def test_sqlite_matrix_native_smoke_all_problem_types(tmp_path):
    db_path = str(tmp_path / "academic-smoke.db")
    run_id = "sqlite-smoke"
    problems = _tiny_matrix_native_problems()
    runner = MatrixBenchmarkRunner(
        [
            MatrixAlgorithmConfig(
                name="Core-Greedy-Routing",
                engine=GreedyMatrixEngine(),
                params={"smoke": True},
            )
        ]
    )

    save_benchmark_run(
        run_id,
        source="sqlite_smoke",
        status="running",
        settings={"problem_types": [problem.problem_type for problem in problems]},
        db_path=db_path,
    )
    for idx, problem in enumerate(problems, start=1):
        result = runner.run_one(problem, runner.algorithms[0], run_number=idx, seed=100 + idx)
        save_benchmark_result(run_id, asdict(result), db_path=db_path)
    save_benchmark_run(run_id, source="sqlite_smoke", status="completed", db_path=db_path)

    rows = query_benchmark_results(run_id=run_id, limit=10, db_path=db_path)

    assert len(rows) == 5
    by_type = {row["problem_type"]: row for row in rows}
    assert {"tsp", "atsp", "cvrp", "cvrptw", "uniride"}.issubset(by_type)
    assert by_type["tsp"]["tour_cost"] == by_type["tsp"]["objective_cost"]
    assert by_type["atsp"]["matrix_kind"] == "travel_time"
    assert by_type["cvrp"]["routes"]
    assert by_type["cvrp"]["num_vehicles"] >= 1
    assert by_type["cvrptw"]["routes"]
    assert by_type["cvrptw"]["tw_violations"] >= 0
    assert by_type["uniride"]["route_loads"]
    assert by_type["uniride"]["capacity_violations"] == 0
    assert all(row["source"] == "sqlite_smoke" for row in rows)
    assert all(row["status"] == "completed" for row in rows)
    with sqlite3.connect(db_path) as conn:
        settings_json = conn.execute(
            "SELECT settings_json FROM benchmark_runs WHERE run_id=?",
            (run_id,),
        ).fetchone()[0]
    assert json.loads(settings_json)["problem_types"] == [
        "tsp",
        "atsp",
        "cvrp",
        "cvrptw",
        "uniride",
    ]


def _tiny_matrix_native_problems():
    tsp_matrix = np.array(
        [
            [0, 1, 2, 1],
            [1, 0, 1, 2],
            [2, 1, 0, 1],
            [1, 2, 1, 0],
        ],
        dtype=float,
    )
    atsp_matrix = np.array(
        [
            [0, 3, 1],
            [2, 0, 4],
            [5, 1, 0],
        ],
        dtype=float,
    )
    routing_matrix = np.array(
        [
            [0, 5, 6, 7],
            [5, 0, 1, 2],
            [6, 1, 0, 1],
            [7, 2, 1, 0],
        ],
        dtype=float,
    )
    return [
        RoutingProblem("smoke-tsp", "tsp", CostMatrix(tsp_matrix, kind="distance")),
        RoutingProblem("smoke-atsp", "atsp", CostMatrix(atsp_matrix, kind="travel_time")),
        RoutingProblem(
            "smoke-cvrp",
            "cvrp",
            CostMatrix(routing_matrix, kind="distance"),
            constraints=ConstraintProfile(demands=[[0], [1], [1], [1]], capacities=[2]),
        ),
        RoutingProblem(
            "smoke-cvrptw",
            "cvrptw",
            CostMatrix(routing_matrix, kind="travel_time"),
            constraints=ConstraintProfile(
                demands=[[0], [1], [1], [1]],
                capacities=[2],
                time_windows=[(0, 100), (0, 20), (0, 30), (0, 40)],
                service_times=[0, 0, 0, 0],
                direction="dropoff",
            ),
        ),
        RoutingProblem(
            "smoke-uniride",
            "uniride",
            CostMatrix(routing_matrix, kind="travel_time"),
            constraints=ConstraintProfile(
                demands=[[0, 0], [1, 0], [0, 1], [0, 1]],
                capacities=[1, 2],
                max_route_duration=30,
            ),
        ),
    ]
