"""Core PSO-Split engine for string-keyed UniRide CVRP/CVRPTW problems."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from uniride_core.algorithms.ga_split_engine import nearest_neighbor_tour
from uniride_core.algorithms.objective_rank import FeasibleVehiclesCost, objective_key
from uniride_core.algorithms.meta_split_common import (
    decode_final_tour,
    local_search_improve,
    shuffle_permutation,
)
from uniride_core.algorithms.string_split_decoder import decode_giant_tour


@dataclass
class Particle:
    """Particle representing a giant tour permutation."""

    position: List[str]
    velocity: List[Tuple[int, int, float]]
    personal_best: List[str]
    personal_best_cost: float = float("inf")
    personal_best_key: Optional[FeasibleVehiclesCost] = None
    current_cost: float = float("inf")
    current_key: Optional[FeasibleVehiclesCost] = None


@dataclass
class PSOSplitSolution:
    """Result of the PSO-Split core search."""

    best_tour: Optional[List[str]]
    best_cost: float
    final_result: Dict[str, Any]
    iterations: int


def initialize_swarm(
    waypoints: List[str],
    config: Mapping[str, Any],
    rng: random.Random,
    distance_matrix: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[Particle]:
    """Initialize the PSO swarm with one heuristic and random particles."""
    swarm: List[Particle] = []
    nn_tour = nearest_neighbor_tour(waypoints, distance_matrix)
    if nn_tour:
        swarm.append(Particle(position=nn_tour, velocity=[], personal_best=nn_tour.copy()))

    for _ in range(max(0, int(config.get("swarm_size", 60)) - 1)):
        position = shuffle_permutation(waypoints, rng)
        swarm.append(Particle(position=position, velocity=[], personal_best=position.copy()))

    return swarm


def difference_swaps(
    current: List[str],
    target: List[str],
    weight: float,
    rng: random.Random,
) -> List[Tuple[int, int, float]]:
    """Return weighted swaps that move current toward target."""
    swaps: List[Tuple[int, int, float]] = []
    for idx in range(len(current)):
        if idx < len(target) and current[idx] != target[idx]:
            try:
                swap_idx = current.index(target[idx])
            except ValueError:
                continue
            if swap_idx != idx:
                swaps.append((idx, swap_idx, weight * rng.random()))
    return swaps


def apply_velocity(
    position: List[str],
    velocity: List[Tuple[int, int, float]],
    rng: random.Random,
) -> List[str]:
    """Apply probabilistic swap velocity to a permutation."""
    new_position = position.copy()
    n = len(new_position)
    for swap in velocity:
        if len(swap) >= 3 and rng.random() < swap[2]:
            i, j = swap[0], swap[1]
            if 0 <= i < n and 0 <= j < n:
                new_position[i], new_position[j] = new_position[j], new_position[i]
    return new_position


def update_velocity(
    particle: Particle,
    global_best: Optional[List[str]],
    config: Mapping[str, Any],
    inertia: float,
    rng: random.Random,
) -> List[Tuple[int, int, float]]:
    """Calculate PSO velocity for a permutation particle."""
    velocity_clamp = float(config.get("velocity_clamp", 0.7))
    new_velocity: List[Tuple[int, int, float]] = []

    for swap in particle.velocity:
        if len(swap) >= 3:
            adjusted_prob = swap[2] * inertia
            if adjusted_prob > 0.1:
                new_velocity.append((swap[0], swap[1], min(adjusted_prob, velocity_clamp)))

    new_velocity.extend(
        difference_swaps(
            particle.position,
            particle.personal_best,
            float(config.get("cognitive_weight", 2.0)),
            rng,
        )
    )
    if global_best is not None:
        new_velocity.extend(
            difference_swaps(
                particle.position,
                global_best,
                float(config.get("social_weight", 2.0)),
                rng,
            )
        )

    max_velocity = int(velocity_clamp * len(particle.position))
    return new_velocity[:max_velocity]


def _evaluate_position(
    position: List[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    sw_capacity: int,
    so_capacity: int,
    max_tour_duration: float,
    is_asymmetric: bool,
) -> Tuple[float, FeasibleVehiclesCost]:
    """Decode a position into (cost, lexicographic objective key)."""
    decoded = decode_giant_tour(
        giant_tour=position,
        depot=depot,
        distance_matrix=distance_matrix,
        demands=demands,
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
        max_tour_duration=max_tour_duration,
        is_asymmetric=is_asymmetric,
    )
    cost = float(decoded.get("total_cost", float("inf")))
    num_vehicles = int(decoded.get("num_vehicles", 0))
    return cost, objective_key({"num_vehicles": num_vehicles, "total_cost": cost})


def solve_pso_split(
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
) -> PSOSplitSolution:
    """Run PSO-Split and return the final decoded route result."""
    swarm = initialize_swarm(waypoints, config, rng, distance_matrix)
    global_best: Optional[List[str]] = None
    global_best_cost = float("inf")
    global_best_key: Optional[FeasibleVehiclesCost] = None

    for particle in swarm:
        cost, key = _evaluate_position(
            particle.position, depot, distance_matrix, demands,
            sw_capacity, so_capacity, max_tour_duration, is_asymmetric,
        )
        particle.current_cost = cost
        particle.current_key = key
        particle.personal_best_cost = cost
        particle.personal_best_key = key
        if key is not None and (global_best_key is None or key < global_best_key):
            global_best_key = key
            global_best_cost = cost
            global_best = particle.position.copy()

    no_improvement = 0
    iteration = 0
    max_iterations = int(config.get("max_iterations", 200))
    for iteration in range(max_iterations):
        inertia = float(config.get("inertia_weight", 0.9)) - (
            (float(config.get("inertia_weight", 0.9)) - float(config.get("inertia_min", 0.4)))
            * iteration / max_iterations
        )
        improved = False

        for particle in swarm:
            particle.velocity = update_velocity(particle, global_best, config, inertia, rng)
            new_position = apply_velocity(particle.position, particle.velocity, rng)

            if iteration % int(config.get("local_search_interval", 20)) == 0:
                new_position = local_search_improve(
                    new_position,
                    depot,
                    distance_matrix,
                    str(config.get("local_search_type", "hybrid")),
                )

            new_cost, new_key = _evaluate_position(
                new_position, depot, distance_matrix, demands,
                sw_capacity, so_capacity, max_tour_duration, is_asymmetric,
            )
            if new_key is not None and (
                particle.personal_best_key is None or new_key < particle.personal_best_key
            ):
                particle.personal_best = new_position.copy()
                particle.personal_best_cost = new_cost
                particle.personal_best_key = new_key

            particle.position = new_position
            particle.current_cost = new_cost
            particle.current_key = new_key

            if new_key is not None and (global_best_key is None or new_key < global_best_key):
                global_best = new_position.copy()
                global_best_cost = new_cost
                global_best_key = new_key
                improved = True

        no_improvement = 0 if improved else no_improvement + 1
        if no_improvement >= int(config.get("max_no_improvement", 40)):
            break

    final_result: Dict[str, Any] = {"routes": [], "num_vehicles": 0, "total_cost": float("inf")}
    if global_best is not None:
        final_result = decode_final_tour(
            global_best,
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

    return PSOSplitSolution(global_best, global_best_cost, final_result, iteration)


__all__ = [
    "Particle",
    "PSOSplitSolution",
    "apply_velocity",
    "difference_swaps",
    "initialize_swarm",
    "solve_pso_split",
    "update_velocity",
]
