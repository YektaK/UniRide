"""L11: the real optimizer_api enums go through the core adapter as plain strings.

Lives in optimizer_api/tests because uniride_core tests must not import the
application layer (test_architecture_boundaries).
"""

import pytest

from optimizer_api.models.schemas import DisabilityType, TripDirection
from uniride_core.adapters.uniride_adapter import uniride_request_to_problem


def _problem(direction, disability):
    return uniride_request_to_problem(
        {
            "students": [
                {"id": "S1", "location_code": "L1", "coordinates": {"lat": 1.0, "lng": 0.0}, "disability_type": disability}
            ],
            "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
            "direction": direction,
        }
    )


@pytest.mark.parametrize("direction, expected", [(TripDirection.PICKUP, "pickup"), (TripDirection.DROPOFF, "dropoff")])
def test_trip_direction_enum_becomes_plain_string(direction, expected):
    assert _problem(direction, "So").constraints.direction == expected


@pytest.mark.parametrize("disability, demand", [(DisabilityType.SW, [1, 0]), (DisabilityType.SO, [0, 1])])
def test_disability_type_enum_maps_to_demand(disability, demand):
    assert _problem(TripDirection.PICKUP, disability).constraints.demands[1] == demand
