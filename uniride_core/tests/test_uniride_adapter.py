from uniride_core.adapters.uniride_adapter import uniride_request_to_problem


class DummyWindow:
    earliest = 450
    latest = 480


class DummyRequest:
    students = [
        {
            "id": "S1",
            "location_code": "L1",
            "coordinates": {"lat": 1.0, "lng": 0.0},
            "disability_type": "Sw",
        },
        {
            "id": "S2",
            "location_code": "L2",
            "coordinates": {"lat": 2.0, "lng": 0.0},
            "disability_type": "So",
        },
    ]
    depot = {"id": "D", "lat": 0.0, "lng": 0.0}
    sw_capacity = 1
    so_capacity = 2
    max_travel_time = 90
    direction = "pickup"
    target_time = "08:00"
    offset_minutes = 10
    is_asymmetric = True

    def get_time_windows(self):
        return {"L1": DummyWindow(), "L2": {"earliest": 460, "latest": 500}}


def test_uniride_request_adapter_builds_vector_capacity_problem():
    matrix = [
        [0, 5, 9],
        [6, 0, 3],
        [8, 4, 0],
    ]

    problem = uniride_request_to_problem(DummyRequest(), matrix=matrix)

    assert problem.problem_type == "uniride_cvrptw"
    assert problem.matrix.kind == "travel_time"
    assert problem.matrix.is_asymmetric is True
    assert problem.matrix.labels == ["D", "L1", "L2"]
    assert problem.constraints.demands == [[0, 0], [1, 0], [0, 1]]
    assert problem.constraints.capacities == [1, 2]
    assert problem.constraints.time_windows == [(0, 1440), (450, 480), (460, 500)]
    assert problem.constraints.target_time == 480
