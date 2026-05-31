import numpy as np

from academic_benchmark.tsplib_manager import load_routing_problem


def test_build_uniride_export_problem_anonymizes_students_and_constraints():
    from academic_benchmark.data_export import build_uniride_export_problem

    payload = {
        "name": "real-morning",
        "depot": {"id": "D.Kampus", "lat": 41.0, "lng": 29.0},
        "students": [
            {
                "id": "real-user-1",
                "name": "Private Name",
                "location_code": "HOME-A",
                "disability_type": "Sw",
                "pickup_time": "08:30",
            },
            {
                "id": "real-user-2",
                "location_code": "HOME-B",
                "disability_type": "So",
                "pickup_time": "08:45",
            },
        ],
        "time_matrix": {
            "D.Kampus": {"D.Kampus": 0, "HOME-A": 10, "HOME-B": 20},
            "HOME-A": {"D.Kampus": 11, "HOME-A": 0, "HOME-B": 7},
            "HOME-B": {"D.Kampus": 19, "HOME-A": 8, "HOME-B": 0},
        },
        "sw_capacity": 1,
        "so_capacity": 3,
        "direction": "pickup",
        "max_travel_time": 90,
    }

    problem = build_uniride_export_problem(payload, slack_window_minutes=30)

    assert problem.name == "real-morning"
    assert problem.problem_type == "cvrptw"
    assert problem.source == "uniride_export"
    assert problem.matrix.kind == "travel_time"
    assert problem.matrix.is_asymmetric is True
    assert problem.matrix.labels == ["depot", "student_001", "student_002"]
    assert np.asarray(problem.matrix.values).tolist() == [
        [0.0, 10.0, 20.0],
        [11.0, 0.0, 7.0],
        [19.0, 8.0, 0.0],
    ]
    assert problem.constraints.demands == [[0, 0], [1, 0], [0, 1]]
    assert problem.constraints.capacities == [1, 3]
    assert problem.constraints.time_windows == [(0, 1440), (480, 510), (495, 525)]
    assert problem.constraints.service_times == [0, 0, 0]
    assert problem.constraints.max_route_duration == 90
    assert "real-user-1" not in str(problem.metadata)
    assert "Private Name" not in str(problem.metadata)


def test_store_uniride_export_problem_in_academic_db(tmp_path):
    from academic_benchmark.data_export import build_uniride_export_problem, store_uniride_export

    payload = {
        "name": "stored-uniride",
        "depot": {"id": "campus"},
        "students": [
            {"id": "a", "location_code": "A", "disability_type": "So", "dropoff_time": "17:00"},
        ],
        "time_matrix": [[0, 12], [13, 0]],
        "direction": "dropoff",
    }
    db_path = tmp_path / "export.db"

    problem = build_uniride_export_problem(payload)
    stored = store_uniride_export(problem, db_path=str(db_path))
    loaded = load_routing_problem(stored.name, db_path=str(db_path))

    assert loaded is not None
    assert loaded.name == "stored-uniride"
    assert loaded.problem_type == "cvrptw"
    assert loaded.matrix.kind == "travel_time"
    assert loaded.constraints.demands == [[0, 0], [0, 1]]
    assert loaded.constraints.time_windows == [(0, 1440), (1020, 1050)]
