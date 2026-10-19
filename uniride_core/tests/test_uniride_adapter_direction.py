"""L11: the request adapter must normalise an enum direction to a plain string.

``str(TripDirection.PICKUP)`` is ``'TripDirection.PICKUP'`` for a ``(str, Enum)``,
which downstream ``== "pickup"`` / ``== "dropoff"`` checks never match.
"""

from enum import Enum

import pytest

from uniride_core.adapters.uniride_adapter import uniride_request_to_problem


class _TripDirection(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"


class _PlainEnum(Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"


def _request(direction):
    return {
        "students": [
            {"id": "S1", "location_code": "L1", "coordinates": {"lat": 1.0, "lng": 0.0}, "disability_type": "So"}
        ],
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
        "direction": direction,
    }


def _direction(direction):
    return uniride_request_to_problem(_request(direction)).constraints.direction


@pytest.mark.parametrize("enum_cls", [_TripDirection, _PlainEnum])
def test_enum_directions_become_plain_strings(enum_cls):
    assert _direction(enum_cls.PICKUP) == "pickup"
    assert _direction(enum_cls.DROPOFF) == "dropoff"


def test_optimizer_api_trip_direction_enum_is_normalised():
    from optimizer_api.models.schemas import TripDirection

    assert _direction(TripDirection.PICKUP) == "pickup"
    assert _direction(TripDirection.DROPOFF) == "dropoff"


@pytest.mark.parametrize("raw, expected", [("pickup", "pickup"), ("DropOff", "dropoff"), (" PICKUP ", "pickup")])
def test_plain_strings_are_normalised(raw, expected):
    assert _direction(raw) == expected


def test_missing_direction_defaults_to_pickup():
    request = _request("pickup")
    del request["direction"]
    assert uniride_request_to_problem(request).constraints.direction == "pickup"


@pytest.mark.parametrize("disability, expected", [("Sw", [1, 0]), ("So", [0, 1]), ("sw", [1, 0])])
def test_disability_enum_and_string_map_to_the_same_demand(disability, expected):
    """Same ``str(enum)`` pattern as L11, in ``_student_demand``."""
    from optimizer_api.models.schemas import DisabilityType

    value = {"Sw": DisabilityType.SW, "So": DisabilityType.SO, "sw": "sw"}[disability]
    request = _request("pickup")
    request["students"][0]["disability_type"] = value
    problem = uniride_request_to_problem(request)
    assert problem.constraints.demands[1] == expected
