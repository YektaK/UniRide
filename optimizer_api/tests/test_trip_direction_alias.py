from models.schemas import Direction, OptimizationRequest, TripDirection


def test_trip_direction_is_canonical_and_direction_alias_remains():
    assert Direction is TripDirection
    assert TripDirection.PICKUP.value == "pickup"
    assert TripDirection.DROPOFF.value == "dropoff"


def test_optimization_request_accepts_trip_direction_values():
    request = OptimizationRequest(
        depot={"id": "A", "lat": 0.0, "lng": 0.0},
        students=[],
        direction=TripDirection.DROPOFF,
    )

    assert request.direction == TripDirection.DROPOFF
    assert request.direction == Direction.DROPOFF
