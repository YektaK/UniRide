"""WP3 tests for the typed GA engine (design 3.1/3.3, parity gate P4, section 9)."""

from __future__ import annotations

import random

import pytest

from uniride_core.algorithms.ga_split_engine import solve_ga_split
from uniride_core.algorithms.ga_split_typed_engine import (
    BASELINE_LABEL,
    solve_ga_split_typed,
    solve_typed_menu,
)
from uniride_core.algorithms.typed_split_decoder import VehicleType
from uniride_core.tests.test_split_parity_golden import DEPOT, _instance

CFG = {"population_size": 12, "max_iterations": 8, "local_search_interval": 3, "max_no_improvement": 6}
LARGE = VehicleType("large", 4, 5, 90.0, 50.0, 10)
CAR = VehicleType("car", 0, 4, 90.0, 50.0, 10)


@pytest.mark.parametrize("seed", [0, 42, 1234])
@pytest.mark.parametrize("n,asym,direction", [(9, False, "pickup"), (8, True, "dropoff"), (7, False, "pickup")])
def test_p4_single_type_no_quota_equals_untyped_engine(seed, n, asym, direction):
    wps, matrix, demands = _instance(n, asym)
    untyped = solve_ga_split(
        wps, DEPOT, matrix, demands, 4, 5, 90.0, CFG, random.Random(seed),
        direction=direction, is_asymmetric=asym, max_ride_time=50.0,
    )
    typed = solve_ga_split_typed(
        wps, DEPOT, matrix, demands, [VehicleType("large", 4, 5, 90.0, 50.0)], CFG,
        random.Random(seed), minimize_type="large", direction=direction, is_asymmetric=asym,
    )
    assert untyped.final_result["num_vehicles"] > 0 and typed.final_result.feasible
    assert typed.final_result.routes == untyped.final_result["routes"]
    assert typed.final_result.total_cost == untyped.final_result["total_cost"]
    assert typed.generations == untyped.generations
    assert typed.best_individual.chromosome == untyped.best_individual.chromosome


def test_typed_ga_is_deterministic_and_respects_quota_and_sw():
    wps, matrix, demands = _instance(9, False)
    runs = [
        solve_ga_split_typed(
            wps, DEPOT, matrix, demands, [LARGE, CAR], CFG, random.Random(42),
            minimize_type="car", quota_type="large", quota=3,
        )
        for _ in range(2)
    ]
    a, b = (r.final_result for r in runs)
    assert (a.routes, a.type_ids, a.total_cost) == (b.routes, b.type_ids, b.total_cost)
    assert runs[0].generations == runs[1].generations
    assert a.feasible and a.type_ids.count("large") <= 3
    for route, t in zip(a.routes, a.type_ids):
        if any(demands[s][0] for s in route):
            assert t == "large"


def test_infeasible_quota_is_reported_not_faked():
    wps, matrix, demands = _instance(9, False)  # contains Sw stops
    sol = solve_ga_split_typed(
        wps, DEPOT, matrix, demands, [LARGE, CAR], CFG, random.Random(1),
        minimize_type="car", quota_type="large", quota=0,
    )
    assert not sol.final_result.feasible and sol.final_result.routes == []


def test_menu_has_q0_to_q3_and_all_large_baseline():
    wps, matrix, demands = _instance(9, False)
    menu = solve_typed_menu(
        wps, DEPOT, matrix, demands, [LARGE, CAR], CFG, 42,
        minimize_type="car", quota_type="large", max_quota=3,
    )
    assert [o.label for o in menu] == ["q0", "q1", "q2", "q3", BASELINE_LABEL]
    assert not menu[0].feasible and menu[0].reason == "NO_FEASIBLE_TYPED_SPLIT"
    base = menu[-1]
    assert base.feasible and set(base.solution.final_result.type_ids) == {"large"}
    for opt in menu[1:4]:
        if opt.feasible:
            assert opt.solution.final_result.type_ids.count("large") <= opt.quota
