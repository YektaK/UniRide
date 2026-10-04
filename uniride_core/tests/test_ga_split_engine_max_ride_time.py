"""GA-Split engine threads ``max_ride_time`` through every decode path."""

import random

import pytest

from uniride_core.algorithms.ga_split_engine import (
    GAIndividual,
    evaluate_individual,
    solve_ga_split,
)

DEPOT = "D"
STOPS = ["A", "B", "C", "E", "F"]
CONFIG = {"population_size": 12, "max_iterations": 6, "max_no_improvement": 6}


def _star():
    """D->x 12, x->D 10, x->y 15 (directed star)."""
    dm = {DEPOT: {s: 12.0 for s in STOPS}}
    for s in STOPS:
        dm[s] = {DEPOT: 10.0, **{t: 15.0 for t in STOPS if t != s}}
    return dm


def _solve(direction, limit, use_time_windows=False):
    return solve_ga_split(
        waypoints=list(STOPS),
        depot=DEPOT,
        distance_matrix=_star(),
        demands={s: (0, 1) for s in STOPS},
        sw_capacity=4,
        so_capacity=10,
        max_tour_duration=120,
        config=CONFIG,
        rng=random.Random(3),
        use_time_windows=use_time_windows,
        time_windows={s: (0, 1440) for s in STOPS} if use_time_windows else None,
        direction=direction,
        target_time=600 if direction == "pickup" else 900,
        offset_minutes=0,
        is_asymmetric=True,
        max_ride_time=limit,
    ).final_result


@pytest.mark.parametrize("use_tw", [False, True])
@pytest.mark.parametrize(
    "direction,limit,routes",
    [
        ("pickup", None, 1),
        ("pickup", 40, 2),   # ride = 10 + 15 (k-1) -> k <= 3
        ("pickup", 25, 3),   # k <= 2
        ("dropoff", 40, 3),  # ride = 12 + 15 (k-1) -> k <= 2
        ("dropoff", 25, 5),  # k <= 1
    ],
)
def test_final_decode_respects_limit(direction, limit, routes, use_tw):
    result = _solve(direction, limit, use_time_windows=use_tw)
    assert len(result["routes"]) == routes
    assert sorted(s for r in result["routes"] for s in r) == sorted(STOPS)


def test_evaluate_individual_default_is_unlimited():
    individual = GAIndividual(chromosome=list(STOPS))
    args = (DEPOT, _star(), {s: (0, 1) for s in STOPS}, 4, 10, 120)
    unlimited = evaluate_individual(individual, *args, is_asymmetric=True)
    limited = evaluate_individual(
        individual, *args, is_asymmetric=True, max_ride_time=25, direction="pickup"
    )
    assert unlimited.num_vehicles == 1
    assert limited.num_vehicles == 3
