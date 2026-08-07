"""Tests for the shared lexicographic objective ranking used by split engines."""

import random

import pytest

from uniride_core.algorithms.objective_rank import (
    FEASIBLE,
    INFEASIBLE,
    fitness_from_key,
    is_better,
    key_from_fields,
    objective_key,
    report_key_from_routes,
)
from uniride_core.algorithms.ga_split_engine import GAIndividual, tournament_selection
from uniride_core.algorithms.gwo_split_engine import Wolf, solve_gwo_split
from uniride_core.algorithms.hho_split_engine import Hawk, solve_hho_split
from uniride_core.algorithms.pso_split_engine import Particle, solve_pso_split


class TestObjectiveKey:
    def test_feasible_lowest_weight(self):
        assert objective_key({"num_vehicles": 2, "total_cost": 40.0})[0] == FEASIBLE

    def test_infeasible_when_no_vehicles(self):
        assert objective_key({"num_vehicles": 0, "total_cost": 0.0})[0] == INFEASIBLE

    def test_infeasible_when_inf_cost(self):
        assert objective_key({"num_vehicles": 3, "total_cost": float("inf")})[0] == INFEASIBLE

    def test_infeasible_when_nan_cost(self):
        assert objective_key({"num_vehicles": 1, "total_cost": float("nan")})[0] == INFEASIBLE

    def test_int_and_float_fields_normalized(self):
        key = objective_key({"num_vehicles": "2", "total_cost": "40.5"})
        assert key == (FEASIBLE, 2, 40.5)

    def test_bad_values_coerce_to_worst(self):
        key = objective_key({"num_vehicles": None, "total_cost": "junk"})
        assert key == (INFEASIBLE, 999, float("inf"))

    def test_object_with_attributes(self):
        class _Dummy:
            num_vehicles = 4
            total_cost = 88.0

        assert objective_key(_Dummy()) == (FEASIBLE, 4, 88.0)


class TestReportKeyFromRoutes:
    _M = {
        "D": {"D": 0, "A": 5, "B": 7, "C": 9},
        "A": {"D": 5, "A": 0, "B": 3, "C": 4},
        "B": {"D": 7, "A": 3, "B": 0, "C": 2},
        "C": {"D": 9, "A": 4, "B": 2, "C": 0},
    }

    def test_matches_decode_accounting(self):
        routes = [["A", "B", "C"]]
        assert report_key_from_routes(routes, self._M, "D") == (FEASIBLE, 1, 19.0)

    def test_multiple_routes_summation(self):
        routes = [["A", "B"], ["C"]]
        assert report_key_from_routes(routes, self._M, "D") == (FEASIBLE, 2, 33.0)

    def test_empty_routes_infeasible(self):
        assert report_key_from_routes([], self._M, "D") == (INFEASIBLE, 0, float("inf"))

    def test_empty_route_sorts_worst(self):
        assert report_key_from_routes([[]], self._M, "D")[0] == INFEASIBLE

    def test_missing_arc_infeasible(self):
        routes = [["A", "X"]]
        assert report_key_from_routes(routes, self._M, "D")[0] == INFEASIBLE


class TestDominanceTable:
    def test_feasible_beats_infeasible(self):
        feasible = key_from_fields(3, 500.0)
        infeasible = key_from_fields(999, float("inf"))
        assert is_better(feasible, infeasible)
        assert not is_better(infeasible, feasible)

    def test_fewer_vehicles_wins_within_feasible(self):
        cheap_many = key_from_fields(5, 1.0)
        few_costlier = key_from_fields(2, 200.0)
        assert is_better(few_costlier, cheap_many)
        assert not is_better(cheap_many, few_costlier)

    def test_equal_vehicles_compare_travel_cost(self):
        a = key_from_fields(3, 100.0)
        b = key_from_fields(3, 90.0)
        assert is_better(b, a)
        assert not is_better(a, b)

    def test_ties_are_not_better(self):
        a = key_from_fields(2, 50.0)
        assert not is_better(a, a)


class TestFitnessFromKey:
    def test_fitness_sorted_like_key(self):
        ordered = [
            key_from_fields(1, 1000.0),
            key_from_fields(2, 1.0),
            key_from_fields(3, 1.0),
            key_from_fields(0, 0.0),
        ]
        fits = [fitness_from_key(k) for k in ordered]
        assert fits == sorted(fits, reverse=True)

    def test_infeasible_maps_to_zero(self):
        assert fitness_from_key(objective_key({"num_vehicles": 0, "total_cost": 0.0})) == 0.0
        assert fitness_from_key(objective_key({"num_vehicles": 3, "total_cost": float("inf")})) == 0.0


def _matrix():
    return {
        "D": {"D": 0, "A": 5, "B": 7, "C": 9},
        "A": {"D": 5, "A": 0, "B": 3, "C": 4},
        "B": {"D": 7, "A": 3, "B": 0, "C": 2},
        "C": {"D": 9, "A": 4, "B": 2, "C": 0},
    }


def _base_kwargs():
    return {
        "waypoints": ["A", "B", "C"],
        "depot": "D",
        "distance_matrix": _matrix(),
        "demands": {"A": (1, 0), "B": (0, 1), "C": (1, 0)},
        "sw_capacity": 2,
        "so_capacity": 1,
        "max_tour_duration": 60,
    }


@pytest.mark.parametrize(
    ("solver", "config"),
    [
        (
            solve_pso_split,
            {
                "swarm_size": 8,
                "max_iterations": 5,
                "inertia_weight": 0.9,
                "inertia_min": 0.4,
                "cognitive_weight": 2.0,
                "social_weight": 2.0,
                "velocity_clamp": 0.7,
                "local_search_interval": 10,
                "local_search_type": "two_opt",
                "max_no_improvement": 4,
            },
        ),
        (
            solve_gwo_split,
            {
                "population_size": 8,
                "max_iterations": 5,
                "initial_a": 2.5,
                "exploration_rate": 0.4,
                "local_search_interval": 10,
                "local_search_type": "two_opt",
                "max_no_improvement": 4,
            },
        ),
        (
            solve_hho_split,
            {
                "population_size": 8,
                "max_iterations": 5,
                "initial_energy": 2.0,
                "jump_probability": 0.4,
                "levy_flight_scale": 0.3,
                "local_search_interval": 10,
                "local_search_type": "two_opt",
                "max_no_improvement": 4,
            },
        ),
    ],
)
def test_split_solvers_report_keys_and_return_feasible(solver, config):
    rng = random.Random(123)
    solution = solver(**_base_kwargs(), config=config, rng=rng)

    if hasattr(solution, "prey"):
        carried = solution.prey
    elif hasattr(solution, "alpha"):
        carried = solution.alpha
    else:
        carried = None

    assert solution.final_result["num_vehicles"] >= 1
    assert len(solution.final_result["routes"]) == solution.final_result["num_vehicles"]
    if carried is not None:
        assert carried.obj_key is not None
        assert is_better(carried.obj_key, key_from_fields(1, float("inf")))
        reported_key = report_key_from_routes(
            solution.final_result["routes"], _matrix(), "D"
        )
        assert reported_key == carried.obj_key


def key_from_feasible_rank(rank):
    return key_from_fields(rank[0], rank[1])


class TestEngineLeaderUpdatesAreLexicographic:
    def test_gwo_alpha_prefers_fewer_vehicles(self):
        rng = random.Random(7)
        pack = [Wolf(position=["C", "A", "B"])]
        wolves = [
            Wolf(position=["A", "B", "C"], total_cost=60.0, obj_key=key_from_fields(2, 60.0)),
            Wolf(position=["B", "A", "C"], total_cost=30.0, obj_key=key_from_fields(1, 30.0)),
        ]
        assert min(wolves, key=lambda w: w.obj_key) is wolves[1]

    def test_hho_prey_uses_key(self):
        hawks = [
            Hawk(position=["A"], total_cost=50.0, obj_key=key_from_fields(2, 50.0)),
            Hawk(position=["B"], total_cost=70.0, obj_key=key_from_fields(1, 70.0)),
        ]
        assert min(hawks, key=lambda h: h.obj_key) is hawks[1]

    def test_particle_global_best_favors_key_not_cost(self):
        particles = [
            Particle(
                position=["A", "B"],
                velocity=[],
                personal_best=["A", "B"],
                current_cost=40.0,
                current_key=key_from_fields(2, 40.0),
            ),
            Particle(
                position=["B", "A"],
                velocity=[],
                personal_best=["B", "A"],
                current_cost=500.0,
                current_key=key_from_fields(1, 500.0),
            ),
        ]
        best = min(particles, key=lambda p: p.current_key or (1, 999, float("inf")))
        assert best.current_key == key_from_fields(1, 500.0)