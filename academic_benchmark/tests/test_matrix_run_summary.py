from __future__ import annotations

from academic_benchmark import matrix_run_summary
from academic_benchmark.matrix_run_summary import summarize_benchmark_rows


def test_summarize_benchmark_rows_counts_feasibility_and_hierarchical_gaps():
    rows = [
        {
            "problem": "C101",
            "algorithm": "OR-Tools",
            "problem_type": "CVRPTW",
            "objective_cost": 828.9,
            "gap": 0.0,
            "num_vehicles": 10,
            "capacity_violations": 0,
            "tw_violations": 0,
            "metadata": {"bks_vehicles": 10, "vehicle_gap": 0, "execution_failed": False},
        },
        {
            "problem": "R101",
            "algorithm": "PyVRP",
            "problem_type": "CVRPTW",
            "objective_cost": 1642.8,
            "gap": None,
            "num_vehicles": 20,
            "capacity_violations": 0,
            "tw_violations": 0,
            "metadata": {"bks_vehicles": 19, "vehicle_gap": 1, "execution_failed": False},
        },
        {
            "problem": "A-n32-k5",
            "algorithm": "VROOM",
            "problem_type": "CVRP",
            "objective_cost": None,
            "gap": None,
            "num_vehicles": None,
            "capacity_violations": 0,
            "tw_violations": 0,
            "metadata": {"execution_failed": True},
        },
    ]

    summary = summarize_benchmark_rows(rows)

    assert summary["total_rows"] == 3
    assert summary["failed_rows"] == 1
    assert summary["feasible_rows"] == 2
    assert summary["capacity_violation_rows"] == 0
    assert summary["tw_violation_rows"] == 0
    assert summary["positive_vehicle_gap_rows"] == 1
    assert summary["distance_gap_suppressed_rows"] == 1
    assert summary["unexpected_distance_gap_with_vehicle_gap_rows"] == 0
    assert summary["by_problem_type"] == {
        "cvrp": {"rows": 1, "feasible": 0, "failed": 1},
        "cvrptw": {"rows": 2, "feasible": 2, "failed": 0},
    }


def test_summarize_benchmark_rows_tracks_best_feasible_rows_by_problem_algorithm():
    rows = [
        {
            "problem": "A-n32-k5",
            "algorithm": "OR-Tools",
            "problem_type": "CVRP",
            "objective_cost": 800.0,
            "gap": 2.0,
            "num_vehicles": 5,
            "capacity_violations": 0,
            "tw_violations": 0,
            "metadata": {"execution_failed": False},
        },
        {
            "problem": "A-n32-k5",
            "algorithm": "OR-Tools",
            "problem_type": "CVRP",
            "objective_cost": 784.0,
            "gap": 0.0,
            "num_vehicles": 5,
            "capacity_violations": 0,
            "tw_violations": 0,
            "metadata": {"execution_failed": False},
        },
        {
            "problem": "A-n32-k5",
            "algorithm": "PyVRP",
            "problem_type": "CVRP",
            "objective_cost": 790.0,
            "gap": 0.8,
            "num_vehicles": 5,
            "capacity_violations": 1,
            "tw_violations": 0,
            "metadata": {"execution_failed": False},
        },
    ]

    summary = summarize_benchmark_rows(rows)

    assert summary["best_feasible"][("A-n32-k5", "OR-Tools")] == {
        "objective_cost": 784.0,
        "gap": 0.0,
        "num_vehicles": 5,
        "vehicle_gap": None,
    }
    assert ("A-n32-k5", "PyVRP") not in summary["best_feasible"]


def test_main_prints_json_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        matrix_run_summary,
        "summarize_run",
        lambda run_id, db_path, limit: {
            "run_id": run_id,
            "total_rows": 1,
            "best_feasible": {("A-n32-k5", "OR-Tools"): {"objective_cost": 784.0}},
        },
    )

    exit_code = matrix_run_summary.main(["run-1", "--db-path", "test.db", "--limit", "5"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"run_id": "run-1"' in output
    assert '"A-n32-k5::OR-Tools"' in output
