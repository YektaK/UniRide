import random

from uniride_core.algorithms.tsp_meta_engines import (
    SwapOperation,
    TSPIndividual,
    TSPWolf,
    apply_swaps,
    apply_tuple_swaps,
    combine_velocities,
    diff_swaps,
    generate_random_velocity,
    gwo_difference_swaps,
    hho_escape_energy,
    hho_use_direct_besiege,
    levy_flight_permutation,
    nearest_neighbor_route,
    solve_ga_tsp,
    solve_gwo_tsp,
    solve_hho_tsp,
    solve_pso_tsp,
    solve_two_opt_tsp,
    tournament_selection,
    update_gwo_position,
)


def _duration(route):
    matrix = {
        "D": {"A": 5, "B": 7, "C": 9, "D": 0},
        "A": {"D": 5, "B": 3, "C": 4, "A": 0},
        "B": {"D": 7, "A": 3, "C": 2, "B": 0},
        "C": {"D": 9, "A": 4, "B": 2, "C": 0},
    }
    if not route:
        return 0.0
    total = matrix["D"][route[0]]
    for left, right in zip(route, route[1:]):
        total += matrix[left][right]
    total += matrix[route[-1]]["D"]
    return float(total)


def test_nearest_neighbor_route_uses_distance_lookup():
    route = nearest_neighbor_route(
        ["A", "B", "C"],
        "D",
        lambda left, right: _duration([right]) if left == "D" else 1.0,
    )

    assert route[0] == "A"
    assert set(route) == {"A", "B", "C"}


def test_solve_two_opt_tsp_returns_permutation_and_cost():
    route, cost = solve_two_opt_tsp(
        ["A", "B", "C"],
        _duration,
        random.Random(5),
        {"max_iterations": 50, "multi_start": True, "num_starts": 3, "first_improvement": False},
        initial_route=["A", "B", "C"],
    )

    assert set(route) == {"A", "B", "C"}
    assert cost == _duration(route)


def test_solve_ga_tsp_returns_permutation_and_cost():
    route, cost = solve_ga_tsp(
        ["A", "B", "C"],
        _duration,
        random.Random(8),
        {
            "population_size": 8,
            "max_iterations": 5,
            "crossover_rate": 0.8,
            "mutation_rate": 0.2,
            "elite_count": 2,
            "tournament_size": 3,
            "max_no_improvement": 4,
        },
    )

    assert set(route) == {"A", "B", "C"}
    assert cost == _duration(route)


def test_solve_pso_tsp_returns_permutation_and_cost():
    route, cost = solve_pso_tsp(
        ["A", "B", "C"],
        _duration,
        random.Random(9),
        {
            "swarm_size": 8,
            "max_iterations": 5,
            "inertia_weight": 0.729,
            "cognitive_weight": 1.49445,
            "social_weight": 1.49445,
            "max_velocity_size": 5,
            "max_no_improvement": 4,
            "reinit_interval": 50,
            "local_search_type": "two_opt",
        },
    )

    assert set(route) == {"A", "B", "C"}
    assert cost == _duration(route)


def test_solve_gwo_tsp_returns_permutation_and_cost():
    route, cost = solve_gwo_tsp(
        ["A", "B", "C"],
        _duration,
        random.Random(10),
        {
            "population_size": 8,
            "max_iterations": 5,
            "initial_a": 2.0,
            "exploration_rate": 0.5,
            "max_no_improvement": 4,
            "local_search_type": "two_opt",
        },
    )

    assert set(route) == {"A", "B", "C"}
    assert cost == _duration(route)


def test_diff_swaps_transform_current_to_target():
    current = ["A", "B", "C"]
    target = ["C", "A", "B"]

    swaps = diff_swaps(current, target)

    assert apply_swaps(current, swaps) == target


def test_solve_hho_tsp_returns_permutation_and_cost():
    route, cost = solve_hho_tsp(
        ["A", "B", "C"],
        _duration,
        random.Random(42),
        {
            "population_size": 8,
            "max_iterations": 5,
            "jump_probability": 0.5,
            "max_no_improvement": 4,
            "local_search_type": "two_opt",
        },
    )

    assert set(route) == {"A", "B", "C"}
    assert cost == _duration(route)


def test_hho_escape_energy_uses_initial_energy_parameter():
    assert hho_escape_energy(e0=0.5, iteration=2, max_iterations=10, initial_energy=2.0) == 1.6


def test_hho_jump_probability_uses_original_branch_direction():
    assert hho_use_direct_besiege(r=0.6, jump_probability=0.5) is True
    assert hho_use_direct_besiege(r=0.4, jump_probability=0.5) is False


def test_nearest_neighbor_route_empty_input():
    assert nearest_neighbor_route([], "D", lambda a, b: 1.0) == []


def test_tournament_selection_returns_fittest():
    pop = [
        TSPIndividual(chromosome=["A"], fitness=0.1, total_duration=10.0),
        TSPIndividual(chromosome=["B"], fitness=0.9, total_duration=1.0),
        TSPIndividual(chromosome=["C"], fitness=0.5, total_duration=2.0),
    ]
    winner = tournament_selection(pop, tournament_size=3, rng=random.Random(0))
    assert winner.chromosome == ["B"]


def test_tournament_selection_can_select_from_sampled_subset():
    pop = [
        TSPIndividual(chromosome=["A"], fitness=0.1, total_duration=10.0),
        TSPIndividual(chromosome=["B"], fitness=0.9, total_duration=1.0),
        TSPIndividual(chromosome=["C"], fitness=0.5, total_duration=2.0),
    ]
    results = {tournament_selection(pop, tournament_size=2, rng=random.Random(i)).chromosome[0] for i in range(50)}
    assert "A" in results or "C" in results


def test_generate_random_velocity_returns_swap_operations():
    rng = random.Random(7)
    velocity = generate_random_velocity(n=5, max_velocity_size=3, rng=rng)
    assert 1 <= len(velocity) <= 3
    assert all(isinstance(s, SwapOperation) for s in velocity)
    assert all(0 <= s.i < 5 and 0 <= s.j < 5 for s in velocity)


def test_generate_random_velocity_empty_for_zero_nodes():
    assert generate_random_velocity(n=0, max_velocity_size=3, rng=random.Random(1)) == []


def test_combine_velocities_respects_max_velocity():
    inertia = [SwapOperation(0, 1), SwapOperation(1, 2)]
    cognitive = [SwapOperation(2, 3)]
    social = [SwapOperation(3, 4)]
    config = {
        "inertia_weight": 1.0,
        "cognitive_weight": 3.0,
        "social_weight": 3.0,
        "max_velocity_size": 2,
    }
    combined = combine_velocities(inertia, cognitive, social, config, random.Random(0))
    assert len(combined) <= 2


def test_gwo_difference_swaps_transforms_toward_leader():
    leader = ["C", "A", "B"]
    wolf = ["A", "B", "C"]
    rng = random.Random(42)
    swaps = gwo_difference_swaps(leader, wolf, a=2.0, rng=rng)
    result = apply_tuple_swaps(wolf, swaps)
    assert set(result) == set(wolf)
    assert len(result) == len(wolf)


def test_apply_tuple_swaps_preserves_items():
    position = ["A", "B", "C", "D"]
    swaps = [(0, 2), (1, 3)]
    result = apply_tuple_swaps(position, swaps)
    assert set(result) == {"A", "B", "C", "D"}
    assert result == ["C", "D", "A", "B"]


def test_apply_tuple_swaps_ignores_out_of_bounds():
    position = ["A", "B"]
    result = apply_tuple_swaps(position, [(0, 5)])
    assert result == ["A", "B"]


def test_update_gwo_position_preserves_permutation():
    wolf = TSPWolf(position=["A", "B", "C", "D"])
    alpha = TSPWolf(position=["D", "C", "B", "A"])
    beta = TSPWolf(position=["B", "A", "D", "C"])
    delta = TSPWolf(position=["C", "D", "A", "B"])
    result = update_gwo_position(wolf, alpha, beta, delta, a=2.0, rng=random.Random(99))
    assert set(result) == {"A", "B", "C", "D"}
    assert len(result) == 4


def test_update_gwo_position_returns_copy_when_no_swaps():
    wolf = TSPWolf(position=["A", "B", "C"])
    same = TSPWolf(position=["A", "B", "C"])
    result = update_gwo_position(wolf, same, same, same, a=0.0, rng=random.Random(0))
    assert result == ["A", "B", "C"]


def test_levy_flight_permutation_preserves_items():
    position = ["A", "B", "C", "D", "E"]
    result = levy_flight_permutation(position, random.Random(42), scale=0.5)
    assert set(result) == set(position)
    assert len(result) == len(position)


def test_levy_flight_permutation_single_element():
    assert levy_flight_permutation(["A"], random.Random(0)) == ["A"]
