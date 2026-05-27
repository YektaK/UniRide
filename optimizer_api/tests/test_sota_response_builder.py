from types import SimpleNamespace

from strategies.sota_response_builder import build_single_route_response


def test_build_single_route_response_counts_students_and_route_metrics():
    students = [
        SimpleNamespace(location_code="S1", disability_type="Sw"),
        SimpleNamespace(location_code="S2", disability_type="So"),
    ]
    durations = {
        ("D", "S1"): 5.0,
        ("S1", "S2"): 7.0,
        ("S2", "D"): 9.0,
    }
    distances = {
        ("D", "S1"): 1.5,
        ("S1", "S2"): 2.5,
        ("S2", "D"): 3.5,
    }

    response = build_single_route_response(
        algorithm_name="sota",
        vehicle_label="SOTA",
        students=students,
        depot_id="D",
        best_order=["S1", "S2"],
        duration_lookup=lambda origin, destination: durations[(origin, destination)],
        distance_lookup=lambda origin, destination: distances[(origin, destination)],
        execution_time_seconds=1.23456,
    )

    assert response.algorithm_used == "sota"
    assert response.success is True
    assert response.total_vehicles == 1
    assert response.total_duration_minutes == 21.0
    assert response.execution_time_seconds == 1.2346

    route = response.routes[0]
    assert route.vehicle_id == "Araç 1 (SOTA)"
    assert route.total_distance_km == 7.5
    assert route.sw_count == 1
    assert route.so_count == 1
    assert route.student_ids == ["S1", "S2"]
    assert [(step.location1, step.location2) for step in route.route_details] == [
        ("D", "S1"),
        ("S1", "S2"),
        ("S2", "D"),
    ]
