"""Missing arcs fail closed: no 15-minute default in core split helpers."""

from types import SimpleNamespace

import pytest

from uniride_core.algorithms.ga_split_engine import GAIndividual, educate_individual
from uniride_core.algorithms.meta_split_common import giant_tour_cost
from uniride_core.algorithms.route_metrics import TravelTimeUnavailableError, strict_arc
from uniride_core.algorithms.route_scheduling import calculate_scheduled_times

FULL = {
    "D": {"A": 5.0, "B": 6.0},
    "A": {"D": 7.0, "B": 3.0},
    "B": {"D": 8.0, "A": 4.0},
}
MISSING = {"D": {"A": 5.0}, "A": {"D": 7.0}}  # no A->B, D->B, B->*


def test_strict_arc_returns_directed_value_and_zero_diagonal():
    assert strict_arc(FULL, "A", "B") == 3.0
    assert strict_arc(FULL, "B", "A") == 4.0
    assert strict_arc(FULL, "A", "A") == 0.0


def test_strict_arc_raises_on_missing_arc():
    with pytest.raises(TravelTimeUnavailableError):
        strict_arc(MISSING, "A", "B")
    with pytest.raises(TravelTimeUnavailableError):
        strict_arc({}, "X", "Y")


def test_giant_tour_cost_complete_matrix_unchanged():
    assert giant_tour_cost(["A", "B"], "D", FULL) == 5.0 + 3.0 + 8.0


def test_giant_tour_cost_missing_arc_raises():
    with pytest.raises(TravelTimeUnavailableError):
        giant_tour_cost(["A", "B"], "D", MISSING)


def test_educate_individual_missing_arc_raises_instead_of_default_cost():
    individual = GAIndividual(
        chromosome=["A", "B", "C"], fitness=0.0, total_cost=0.0, num_vehicles=1, obj_key=None
    )
    with pytest.raises(TravelTimeUnavailableError):
        educate_individual(individual, "D", MISSING)


def _route(first, second):
    step = SimpleNamespace(location1=first, location2=second)
    return SimpleNamespace(route_details=[step], arrival_times={}, departure_time=None)


def _request(direction):
    return SimpleNamespace(
        use_time_windows=True,
        direction=direction,
        get_time_windows=lambda: {},
        target_time="09:00",
        offset_minutes=0,
    )


@pytest.mark.parametrize("direction", ["pickup", "dropoff"])
def test_scheduling_missing_arc_raises(direction):
    with pytest.raises(TravelTimeUnavailableError):
        calculate_scheduled_times([_route("A", "B")], _request(direction), MISSING)


@pytest.mark.parametrize("direction", ["pickup", "dropoff"])
def test_scheduling_with_arc_does_not_raise(direction):
    routes = calculate_scheduled_times([_route("A", "B")], _request(direction), FULL)
    assert routes[0].arrival_times
