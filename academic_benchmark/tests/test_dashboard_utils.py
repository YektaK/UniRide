import json

import pandas as pd

from academic_benchmark.dashboard_utils import (
    available_routing_metrics,
    benchmark_rows_to_progress_frame,
    derive_filter_options,
)


def test_benchmark_rows_to_progress_frame_maps_sqlite_routing_fields():
    frame = benchmark_rows_to_progress_frame([
        {
            "timestamp": "2026-05-31T12:00:00",
            "problem": "tiny-cvrptw",
            "algorithm": "Core-Greedy-Routing",
            "problem_type": "cvrptw",
            "matrix_kind": "travel_time",
            "objective_cost": 42.5,
            "tour_cost": 42.5,
            "gap": 0.0,
            "elapsed_ms": 12.0,
            "tour": [0, 1, 2, 0],
            "routes": [[1, 2]],
            "route_loads": [[3]],
            "route_costs": [42.5],
            "num_vehicles": 1,
            "capacity_violations": 0,
            "tw_violations": 1,
            "params": {"seed": 7},
            "source": "web_matrix_native",
            "run_id": "run-1",
        }
    ])

    row = frame.iloc[0]
    assert row["strategy"] == "Core-Greedy-Routing"
    assert row["avg_length"] == 42.5
    assert row["objective_cost"] == 42.5
    assert row["problem_type"] == "cvrptw"
    assert row["matrix_kind"] == "travel_time"
    assert row["num_vehicles"] == 1
    assert row["tw_violations"] == 1
    assert json.loads(row["routes_json"]) == [[1, 2]]
    assert json.loads(row["params_json"]) == {"seed": 7}
    assert row["run_id"] == "run-1"


def test_available_routing_metrics_only_returns_populated_columns():
    frame = pd.DataFrame({
        "objective_cost": [42.0],
        "avg_gap": [None],
        "num_vehicles": [1],
        "tw_violations": [0],
    })

    assert available_routing_metrics(frame) == [
        "objective_cost",
        "num_vehicles",
        "tw_violations",
    ]


def test_derive_filter_options_uses_progress_when_summary_empty():
    progress = pd.DataFrame({
        "problem": ["p2", "p1"],
        "strategy": ["B", "A"],
    })

    problems, algorithms = derive_filter_options(pd.DataFrame(), progress)

    assert problems == ["p1", "p2"]
    assert algorithms == ["A", "B"]
