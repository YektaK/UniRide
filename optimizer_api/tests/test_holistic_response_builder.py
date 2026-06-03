from types import SimpleNamespace

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from strategies.holistic_response_builder import (
    build_indexed_step_routes_response,
    build_sequence_routes_response,
)


def _request() -> OptimizationRequest:
    return OptimizationRequest(
        algorithm="pyvrp",
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=[
            StudentNode(
                id="student-1",
                location_code="S1",
                coordinates={"lat": 1.0, "lng": 0.0},
                disability_type="Sw",
            ),
            StudentNode(
                id="student-2",
                location_code="S2",
                coordinates={"lat": 2.0, "lng": 0.0},
                disability_type="So",
            ),
        ],
    )


def test_build_sequence_routes_response_maps_core_customer_indices_to_api_routes():
    request = _request()
    route_plan = SimpleNamespace(customer_indices=[0, 1], sw_count=1, so_count=1)
    durations = {("D", "S1"): 5.0, ("S1", "S2"): 7.0, ("S2", "D"): 9.0}
    distances = {("D", "S1"): 1.5, ("S1", "S2"): 2.5, ("S2", "D"): 3.5}

    response = build_sequence_routes_response(
        request=request,
        route_plans=[route_plan],
        duration_lookup=lambda origin, destination: durations[(origin, destination)],
        distance_lookup=lambda origin, destination: distances[(origin, destination)],
        algorithm_name="pyvrp",
        vehicle_label="PyVRP",
        execution_time_seconds=1.23456,
    )

    assert response.algorithm_used == "pyvrp"
    assert response.success is True
    assert response.total_vehicles == 1
    assert response.total_duration_minutes == 21.0
    assert response.execution_time_seconds == 1.2346
    route = response.routes[0]
    assert route.vehicle_id == "Araç 1 (PyVRP)"
    assert route.student_ids == ["student-1", "student-2"]
    assert route.sw_count == 1
    assert route.so_count == 1
    assert route.total_distance_km == 7.5
    assert [(step.location1, step.location2, step.duration, step.distance) for step in route.route_details] == [
        ("D", "S1", 5.0, 1.5),
        ("S1", "S2", 7.0, 2.5),
        ("S2", "D", 9.0, 3.5),
    ]


def test_build_indexed_step_routes_response_maps_core_steps_to_api_routes():
    request = _request()
    route_plan = SimpleNamespace(
        vehicle_index=3,
        customer_indices=[0, 1],
        sw_count=1,
        so_count=1,
        total_duration=12.0,
        steps=[
            SimpleNamespace(from_index=0, to_index=1, duration=4.0),
            SimpleNamespace(from_index=1, to_index=2, duration=5.0),
            SimpleNamespace(from_index=2, to_index=0, duration=3.0),
        ],
    )
    distances = {("D", "S1"): 1.0, ("S1", "S2"): 2.0, ("S2", "D"): 3.0}

    response = build_indexed_step_routes_response(
        request=request,
        route_plans=[route_plan],
        location_ids=["D", "S1", "S2"],
        distance_lookup=lambda origin, destination: distances[(origin, destination)],
        algorithm_name="ortools_cvrp",
        vehicle_label="OR-Tools",
        execution_time_seconds=2.0,
    )

    route = response.routes[0]
    assert response.algorithm_used == "ortools_cvrp"
    assert response.total_vehicles == 1
    assert route.vehicle_id == "Araç 3 (OR-Tools)"
    assert route.total_duration_minutes == 12.0
    assert route.total_distance_km == 6.0
    assert route.student_ids == ["student-1", "student-2"]
    assert [(step.location1, step.location2, step.duration, step.distance) for step in route.route_details] == [
        ("D", "S1", 4.0, 1.0),
        ("S1", "S2", 5.0, 2.0),
        ("S2", "D", 3.0, 3.0),
    ]
