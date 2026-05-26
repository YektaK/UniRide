"""Core HHO-Split engine for string-keyed UniRide CVRP/CVRPTW problems."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from uniride_core.algorithms.ga_split_engine import nearest_neighbor_tour
from uniride_core.algorithms.meta_split_common import (
    decode_final_tour,
    giant_tour_cost,
    local_search_improve,
    shuffle_permutation,
    split_penalized_cost,
)
from uniride_core.algorithms.gwo_split_engine import apply_swaps


@dataclass
class Hawk:
    """Hawk individual representing a giant tour permutation."""

    position: List[str]
    fitness: float = 0.0
    total_cost: float = float("inf")


@dataclass
class HHOSplitSolution:
    """Result of the HHO-Split core search."""

    prey: Hawk
    final_result: Dict[str, Any]
    iterations: int


def initialize_population(
    waypoints: List[str],
    config: Mapping[str, Any],
    rng: random.Random,
    distance_matrix: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[Hawk]:
    """Initialize the hawk population with one heuristic and random hawks."""
    hawks: List[Hawk] = []
    nn_tour = nearest_neighbor_tour(waypoints, distance_matrix)
    if nn_tour:
        hawks.append(Hawk(position=nn_tour))

    for _ in range(max(0, int(config.get("population_size", 50)) - 1)):
        hawks.append(Hawk(position=shuffle_permutation(waypoints, rng)))

    return hawks


def levy_flight(
    position: List[str],
    rng: random.Random,
    scale: float = 0.3,
) -> List[str]:
    """Perform Levy-flight mutation for permutation exploration."""
    new_position = position.copy()
    n = len(new_position)
    if n < 2:
        return new_position

    beta = 1.5
    sigma = (
        math.gamma(1 + beta)
        * math.sin(math.pi * beta / 2)
        / (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))
    ) ** (1 / beta)
    u = rng.gauss(0, sigma)
    v = rng.gauss(0, 1)
    step = u / (abs(v) ** (1 / beta))
    num_swaps = max(1, min(int(abs(step) * scale * n), n // 2))

    for _ in range(num_swaps):
        i, j = rng.sample(range(n), 2)
        new_position[i], new_position[j] = new_position[j], new_position[i]

    return new_position


def difference_swaps(
    current: List[str],
    target: List[str],
    intensity: float,
    rng: random.Random,
) -> List[Tuple[int, int]]:
    """Return swaps that move current toward target with the given intensity."""
    swaps: List[Tuple[int, int]] = []
    for idx in range(len(current)):
        if current[idx] == target[idx]:
            continue
        try:
            swap_idx = current.index(target[idx])
        except ValueError:
            continue
        if rng.random() < intensity:
            swaps.append((idx, swap_idx))
    return swaps


def soft_besiege(hawk: Hawk, prey: Hawk, escape_energy: float, rng: random.Random) -> List[str]:
    """Soft besiege update."""
    jump_strength = 2 * (1 - rng.random())
    intensity = abs(escape_energy * jump_strength)
    return apply_swaps(hawk.position, difference_swaps(hawk.position, prey.position, intensity, rng))


def hard_besiege(hawk: Hawk, prey: Hawk, escape_energy: float, rng: random.Random) -> List[str]:
    """Hard besiege update."""
    return apply_swaps(hawk.position, difference_swaps(hawk.position, prey.position, abs(escape_energy), rng))


def soft_besiege_with_dives(
    hawk: Hawk,
    prey: Hawk,
    escape_energy: float,
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    rng: random.Random,
) -> List[str]:
    """Soft besiege with progressive rapid dives."""
    best_position = hawk.position.copy()
    best_cost = hawk.total_cost

    for _ in range(3):
        intensity = abs(escape_energy) * rng.random()
        candidate = apply_swaps(hawk.position, difference_swaps(hawk.position, prey.position, intensity, rng))
        candidate = levy_flight(candidate, rng, scale=0.3)
        cost = giant_tour_cost(candidate, depot, distance_matrix)
        if cost < best_cost:
            best_position = candidate
            best_cost = cost

    return best_position


def hard_besiege_with_dives(hawk: Hawk, prey: Hawk, escape_energy: float, rng: random.Random) -> List[str]:
    """Hard besiege with progressive rapid dives."""
    candidate = apply_swaps(
        hawk.position,
        difference_swaps(hawk.position, prey.position, abs(escape_energy), rng),
    )
    return levy_flight(candidate, rng, scale=0.2)


def evaluate_hawk(
    hawk: Hawk,
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    is_asymmetric: bool = False,
) -> Hawk:
    """Evaluate a hawk with split-decoded penalized route cost."""
    cost = split_penalized_cost(
        hawk.position,
        depot,
        distance_matrix,
        demands,
        sw_capacity,
        so_capacity,
        max_tour_duration,
        is_asymmetric,
    )
    return Hawk(position=hawk.position, total_cost=cost, fitness=1.0 / cost if cost > 0 else 0.0)


def solve_hho_split(
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
) -> HHOSplitSolution:
    """Run HHO-Split and return the final decoded route result."""
    hawks = [
        evaluate_hawk(hawk, depot, distance_matrix, demands, sw_capacity, so_capacity, max_tour_duration, is_asymmetric)
        for hawk in initialize_population(waypoints, config, rng, distance_matrix)
    ]
    prey_seed = min(hawks, key=lambda hawk: hawk.total_cost)
    prey = Hawk(prey_seed.position.copy(), prey_seed.fitness, prey_seed.total_cost)

    no_improvement = 0
    iteration = 0
    max_iterations = int(config.get("max_iterations", 180))
    for iteration in range(max_iterations):
        e0 = 2 * rng.random() - 1
        energy_decay = iteration / max_iterations
        escape_energy = 2 * e0 * (1 - energy_decay) * float(config.get("initial_energy", 2.0))
        improved = False

        for hawk in hawks:
            if abs(escape_energy) >= 1:
                if rng.random() < 0.5:
                    new_position = apply_swaps(
                        hawk.position,
                        difference_swaps(hawk.position, prey.position, rng.random(), rng),
                    )
                else:
                    new_position = levy_flight(
                        hawk.position,
                        rng,
                        scale=float(config.get("levy_flight_scale", 0.3)),
                    )
            elif rng.random() >= float(config.get("jump_probability", 0.4)):
                if abs(escape_energy) >= 0.5:
                    new_position = soft_besiege(hawk, prey, escape_energy, rng)
                else:
                    new_position = hard_besiege(hawk, prey, escape_energy, rng)
            elif abs(escape_energy) >= 0.5:
                new_position = soft_besiege_with_dives(
                    hawk, prey, escape_energy, depot, distance_matrix, rng
                )
            else:
                new_position = hard_besiege_with_dives(hawk, prey, escape_energy, rng)

            if iteration % int(config.get("local_search_interval", 15)) == 0:
                new_position = local_search_improve(
                    new_position,
                    depot,
                    distance_matrix,
                    str(config.get("local_search_type", "hybrid")),
                )

            candidate = evaluate_hawk(
                Hawk(new_position),
                depot,
                distance_matrix,
                demands,
                sw_capacity,
                so_capacity,
                max_tour_duration,
                is_asymmetric,
            )
            if candidate.total_cost < hawk.total_cost:
                hawk.position = candidate.position
                hawk.total_cost = candidate.total_cost
                hawk.fitness = candidate.fitness

            if hawk.total_cost < prey.total_cost:
                prey = Hawk(hawk.position.copy(), hawk.fitness, hawk.total_cost)
                improved = True

        no_improvement = 0 if improved else no_improvement + 1
        if no_improvement >= int(config.get("max_no_improvement", 35)):
            break

    final_result = decode_final_tour(
        prey.position,
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
    return HHOSplitSolution(prey, final_result, iteration)


__all__ = [
    "HHOSplitSolution",
    "Hawk",
    "difference_swaps",
    "evaluate_hawk",
    "hard_besiege",
    "hard_besiege_with_dives",
    "initialize_population",
    "levy_flight",
    "soft_besiege",
    "soft_besiege_with_dives",
    "solve_hho_split",
]
