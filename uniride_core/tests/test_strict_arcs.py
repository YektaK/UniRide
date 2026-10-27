"""Missing arcs fail closed: no 15-minute default in core split helpers."""

import pytest

from uniride_core.algorithms.ga_split_engine import GAIndividual, educate_individual
from uniride_core.algorithms.meta_split_common import giant_tour_cost, local_search_improve
from uniride_core.algorithms.route_metrics import TravelTimeUnavailableError, strict_arc

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


# MT1-03: the two calculate_scheduled_times missing-arc tests were removed with that
# function (it read a reported-duration matrix and raised). The router's schedule
# now leaves a route with an unanswered arc unscheduled and the certificate rejects
# it: see test_unanswered_arc_leaves_the_route_unscheduled_and_rejected in
# optimizer_api/tests/test_mt1_03_returned_schedule.py.


def test_local_search_improve_missing_arc_raises_instead_of_returning_tour():
    with pytest.raises(TravelTimeUnavailableError):
        local_search_improve(["A", "B", "C"], "D", MISSING)
