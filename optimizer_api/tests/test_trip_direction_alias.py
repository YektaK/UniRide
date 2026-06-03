from models.schemas import Direction, OptimizationRequest, TripDirection
from uniride_core.algorithms.linear_split_decoder import LinearSplitDecoder


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


def test_core_split_decoder_normalizes_api_trip_direction_values():
    pickup_decoder = LinearSplitDecoder(direction=Direction.PICKUP)
    dropoff_decoder = LinearSplitDecoder(direction=TripDirection.DROPOFF)

    assert pickup_decoder.direction == "pickup"
    assert dropoff_decoder.direction == "dropoff"
