import random

import pytest

from uniride_core.algorithms.gwo_split_engine import solve_gwo_split
from uniride_core.algorithms.hho_split_engine import levy_flight, solve_hho_split
from uniride_core.algorithms.pso_split_engine import solve_pso_split


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
def test_meta_split_engines_return_decoded_routes(solver, config):
    solution = solver(**_base_kwargs(), config=config, rng=random.Random(123))

    assert solution.final_result["num_vehicles"] >= 1
    assert sorted(location for route in solution.final_result["routes"] for location in route) == ["A", "B", "C"]


def test_levy_flight_preserves_permutation_contents():
    chromosome = ["A", "B", "C", "D"]

    mutated = levy_flight(chromosome, random.Random(4), scale=0.3)

    assert set(mutated) == set(chromosome)
    assert len(mutated) == len(chromosome)
