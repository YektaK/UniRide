from models.schemas import Direction, LocationNode, OptimizationRequest, RouteStep, StudentNode, VehicleRoute
from utils.scheduling import calculate_scheduled_times, minutes_to_time


def _request(direction: Direction) -> OptimizationRequest:
    return OptimizationRequest(
        algorithm="ga",
        depot=LocationNode(id="D", lat=0, lng=0),
        students=[
            StudentNode(
                id="S1",
                location_code="A",
                coordinates={"lat": 1, "lng": 1},
                disability_type="So",
                pickup_time="08:30",
                dropoff_time="17:00",
            ),
            StudentNode(
                id="S2",
                location_code="B",
                coordinates={"lat": 2, "lng": 2},
                disability_type="Sw",
                pickup_time="08:45",
                dropoff_time="17:15",
            ),
        ],
        direction=direction,
        use_time_windows=True,
        offset_minutes=10,
    )


def _route() -> VehicleRoute:
    return VehicleRoute(
        vehicle_id="V1",
        route_details=[
            RouteStep(location1="D", location2="A", duration=10),
            RouteStep(location1="A", location2="B", duration=15),
        ],
        total_duration_minutes=25,
        student_ids=["S1", "S2"],
    )


def test_minutes_to_time_clamps_to_valid_day_range():
    assert minutes_to_time(-10) == "00:00"
    assert minutes_to_time(9 * 60 + 5) == "09:05"
    assert minutes_to_time(24 * 60 + 30) == "23:59"


def test_pickup_scheduling_works_backward_from_latest_student_time():
    routes = calculate_scheduled_times(
        [_route()],
        _request(Direction.PICKUP),
        {"D": {"A": 10}, "A": {"B": 15}},
    )

    route = routes[0]
    assert route.arrival_times == {"B": "08:45", "A": "08:30", "D": "08:20"}
    assert route.departure_time == "08:10"


def test_dropoff_scheduling_works_forward_from_earliest_student_time():
    routes = calculate_scheduled_times(
        [_route()],
        _request(Direction.DROPOFF),
        {"D": {"A": 10}, "A": {"B": 15}},
    )

    route = routes[0]
    assert route.arrival_times == {"D": "17:00", "A": "17:10", "B": "17:25"}
    assert route.departure_time == "17:00"
