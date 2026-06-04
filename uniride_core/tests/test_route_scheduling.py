from __future__ import annotations

from dataclasses import dataclass, field

from uniride_core.algorithms.route_scheduling import calculate_scheduled_times, minutes_to_time


@dataclass
class _Window:
    earliest: int
    latest: int


@dataclass
class _Step:
    location1: str
    location2: str


@dataclass
class _Route:
    route_details: list[_Step]
    departure_time: str | None = None
    arrival_times: dict[str, str] = field(default_factory=dict)


class _Request:
    def __init__(self, direction: str):
        self.use_time_windows = True
        self.direction = direction
        self.target_time = None
        self.offset_minutes = 10

    def get_time_windows(self):
        return {
            "A": _Window(earliest=17 * 60, latest=8 * 60 + 30),
            "B": _Window(earliest=17 * 60 + 15, latest=8 * 60 + 45),
        }


def _route() -> _Route:
    return _Route(route_details=[_Step("D", "A"), _Step("A", "B")])


def test_minutes_to_time_clamps_to_valid_day_range():
    assert minutes_to_time(-10) == "00:00"
    assert minutes_to_time(9 * 60 + 5) == "09:05"
    assert minutes_to_time(24 * 60 + 30) == "23:59"


def test_pickup_scheduling_works_backward_from_latest_time():
    routes = calculate_scheduled_times(
        [_route()],
        _Request("pickup"),
        {"D": {"A": 10}, "A": {"B": 15}},
    )

    assert routes[0].arrival_times == {"B": "08:45", "A": "08:30", "D": "08:20"}
    assert routes[0].departure_time == "08:10"


def test_dropoff_scheduling_works_forward_from_earliest_time():
    routes = calculate_scheduled_times(
        [_route()],
        _Request("dropoff"),
        {"D": {"A": 10}, "A": {"B": 15}},
    )

    assert routes[0].arrival_times == {"D": "17:00", "A": "17:10", "B": "17:25"}
    assert routes[0].departure_time == "17:00"
