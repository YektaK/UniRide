import random

from uniride_core.algorithms.ga_split_engine import (
    GAIndividual,
    evaluate_individual,
    solve_ga_split,
)


def _matrix():
    return {
        "D": {"D": 0, "A": 5, "B": 7, "C": 9},
        "A": {"D": 5, "A": 0, "B": 3, "C": 4},
        "B": {"D": 7, "A": 3, "B": 0, "C": 2},
        "C": {"D": 9, "A": 4, "B": 2, "C": 0},
    }


def test_evaluate_individual_uses_core_split_decoder():
    individual = evaluate_individual(
        GAIndividual(["A", "B", "C"]),
        depot="D",
        distance_matrix=_matrix(),
        demands={"A": (1, 0), "B": (0, 1), "C": (1, 0)},
        sw_capacity=2,
        so_capacity=1,
        max_tour_duration=60,
    )

    assert individual.total_cost < float("inf")
    assert individual.num_vehicles >= 1
    assert individual.fitness > 0


def test_solve_ga_split_returns_decoded_routes():
    solution = solve_ga_split(
        waypoints=["A", "B", "C"],
        depot="D",
        distance_matrix=_matrix(),
        demands={"A": (1, 0), "B": (0, 1), "C": (1, 0)},
        sw_capacity=2,
        so_capacity=1,
        max_tour_duration=60,
        config={
            "population_size": 8,
            "max_iterations": 5,
            "crossover_rate": 0.8,
            "mutation_rate": 0.2,
            "elite_count": 2,
            "tournament_size": 3,
            "max_no_improvement": 4,
            "local_search_interval": 10,
            "local_search_type": "two_opt",
            "diversify_threshold": 20,
        },
        rng=random.Random(123),
    )

    assert solution.final_result["num_vehicles"] >= 1
    assert sorted(location for route in solution.final_result["routes"] for location in route) == ["A", "B", "C"]
    assert solution.best_individual.total_cost < float("inf")
