"""Core GWO-Split engine for string-keyed UniRide CVRP/CVRPTW problems."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from uniride_core.algorithms.ga_split_engine import nearest_neighbor_tour
from uniride_core.algorithms.meta_split_common import (
    decode_final_tour,
    local_search_improve,
    shuffle_permutation,
    split_penalized_cost,
)


@dataclass
class Wolf:
    """Wolf individual in the GWO social hierarchy."""

    position: List[str]
    fitness: float = 0.0
    total_cost: float = float("inf")


@dataclass
class GWOSplitSolution:
    """Result of the GWO-Split core search."""

    alpha: Wolf
    beta: Wolf
    delta: Wolf
    final_result: Dict[str, Any]
    iterations: int


def initialize_pack(
    waypoints: List[str],
    config: Mapping[str, Any],
    rng: random.Random,
    distance_matrix: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[Wolf]:
    """Initialize the wolf pack with one heuristic and random wolves."""
    pack: List[Wolf] = []
    nn_tour = nearest_neighbor_tour(waypoints, distance_matrix)
    if nn_tour:
        pack.append(Wolf(position=nn_tour))

    for _ in range(max(0, int(config.get("population_size", 50)) - 1)):
        pack.append(Wolf(position=shuffle_permutation(waypoints, rng)))

    return pack


def difference_swaps(
    current: List[str],
    leader: List[str],
    a: float,
    rng: random.Random,
) -> List[Tuple[int, int]]:
    """Calculate swaps to move a wolf toward a leader."""
    swaps: List[Tuple[int, int]] = []
    for idx in range(len(current)):
        if current[idx] == leader[idx]:
            continue
        try:
            swap_idx = current.index(leader[idx])
        except ValueError:
            continue
        if rng.random() < a / 2:
            swaps.append((idx, swap_idx))
    return swaps


def apply_swaps(position: List[str], swaps: List[Tuple[int, int]]) -> List[str]:
    """Apply swap operations to a permutation."""
    new_position = position.copy()
    for i, j in swaps:
        if 0 <= i < len(new_position) and 0 <= j < len(new_position):
            new_position[i], new_position[j] = new_position[j], new_position[i]
    return new_position


def update_position(
    wolf: Wolf,
    alpha: Wolf,
    beta: Wolf,
    delta: Wolf,
    a: float,
    rng: random.Random,
) -> List[str]:
    """Update a wolf position from alpha, beta, and delta leaders."""
    alpha_swaps = difference_swaps(wolf.position, alpha.position, a, rng)
    beta_swaps = difference_swaps(wolf.position, beta.position, a, rng)
    delta_swaps = difference_swaps(wolf.position, delta.position, a, rng)
    all_swaps: List[Tuple[int, int]] = []

    all_swaps.extend(swap for swap in alpha_swaps if rng.random() < 0.7)
    all_swaps.extend(swap for swap in beta_swaps if rng.random() < 0.5)
    all_swaps.extend(swap for swap in delta_swaps if rng.random() < 0.3)

    if not all_swaps:
        return wolf.position.copy()

    num_swaps = min(len(all_swaps), max(1, int(len(all_swaps) * a / 2)))
    return apply_swaps(wolf.position, rng.sample(all_swaps, min(num_swaps, len(all_swaps))))


def evaluate_wolf(
    wolf: Wolf,
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    is_asymmetric: bool = False,
) -> Wolf:
    """Evaluate a wolf with split-decoded penalized route cost."""
    cost = split_penalized_cost(
        wolf.position,
        depot,
        distance_matrix,
        demands,
        sw_capacity,
        so_capacity,
        max_tour_duration,
        is_asymmetric,
    )
    return Wolf(position=wolf.position, total_cost=cost, fitness=1.0 / cost if cost > 0 else 0.0)


def solve_gwo_split(
    waypoints: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    config: Mapping[str, Any],
    rng: random.Random,
    *,
    use_time_windows: bool = False,
    time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
    direction: Any = "pickup",
    target_time: Optional[int] = None,
    offset_minutes: int = 10,
    is_asymmetric: bool = False,
) -> GWOSplitSolution:
    """Run GWO-Split and return the final decoded route result."""
    pack = [
        evaluate_wolf(wolf, depot, distance_matrix, demands, sw_capacity, so_capacity, max_tour_duration, is_asymmetric)
        for wolf in initialize_pack(waypoints, config, rng, distance_matrix)
    ]
    pack.sort(key=lambda wolf: wolf.total_cost)
    alpha = Wolf(pack[0].position.copy(), pack[0].fitness, pack[0].total_cost)
    beta = Wolf(pack[1].position.copy(), pack[1].fitness, pack[1].total_cost) if len(pack) > 1 else alpha
    delta = Wolf(pack[2].position.copy(), pack[2].fitness, pack[2].total_cost) if len(pack) > 2 else beta

    no_improvement = 0
    iteration = 0
    max_iterations = int(config.get("max_iterations", 180))
    initial_a = float(config.get("initial_a", 2.5))
    for iteration in range(max_iterations):
        a = initial_a * (1 - iteration / max_iterations)
        improved = False

        for wolf in pack:
            if rng.random() < float(config.get("exploration_rate", 0.4)) * a / initial_a:
                new_position = shuffle_permutation(wolf.position, rng)
            else:
                new_position = update_position(wolf, alpha, beta, delta, a, rng)

            if iteration % int(config.get("local_search_interval", 15)) == 0:
                new_position = local_search_improve(
                    new_position,
                    depot,
                    distance_matrix,
                    str(config.get("local_search_type", "hybrid")),
                )

            candidate = evaluate_wolf(
                Wolf(new_position),
                depot,
                distance_matrix,
                demands,
                sw_capacity,
                so_capacity,
                max_tour_duration,
                is_asymmetric,
            )
            if candidate.total_cost < wolf.total_cost:
                wolf.position = candidate.position
                wolf.total_cost = candidate.total_cost
                wolf.fitness = candidate.fitness

            if wolf.total_cost < alpha.total_cost:
                delta = Wolf(beta.position.copy(), beta.fitness, beta.total_cost)
                beta = Wolf(alpha.position.copy(), alpha.fitness, alpha.total_cost)
                alpha = Wolf(wolf.position.copy(), wolf.fitness, wolf.total_cost)
                improved = True
            elif wolf.total_cost < beta.total_cost:
                delta = Wolf(beta.position.copy(), beta.fitness, beta.total_cost)
                beta = Wolf(wolf.position.copy(), wolf.fitness, wolf.total_cost)
                improved = True
            elif wolf.total_cost < delta.total_cost:
                delta = Wolf(wolf.position.copy(), wolf.fitness, wolf.total_cost)
                improved = True

        no_improvement = 0 if improved else no_improvement + 1
        if no_improvement >= int(config.get("max_no_improvement", 35)):
            break

    final_result = decode_final_tour(
        alpha.position,
        depot,
        distance_matrix,
        demands,
        sw_capacity,
        so_capacity,
        max_tour_duration,
        use_time_windows=use_time_windows,
        time_windows=time_windows,
        direction=direction,
        target_time=target_time,
        offset_minutes=offset_minutes,
        is_asymmetric=is_asymmetric,
    )
    return GWOSplitSolution(alpha, beta, delta, final_result, iteration)


__all__ = [
    "GWOSplitSolution",
    "Wolf",
    "apply_swaps",
    "difference_swaps",
    "evaluate_wolf",
    "initialize_pack",
    "solve_gwo_split",
    "update_position",
]
