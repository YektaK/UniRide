"""Core-owned permutation metaheuristics used by academic benchmarks.

This module owns reusable GA, PSO, GWO, and HHO-style TSP permutation search.
It intentionally has no web/API dependencies.
"""

from __future__ import annotations

import math
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from uniride_core.algorithms.local_search_numba import LocalSearchType, apply_local_search
from uniride_core.algorithms.numba_utils import (
    convert_route_to_indices,
    create_np_distance_matrix,
    create_np_duration_func,
)


def _route_cost(route: List[str], duration_func: Callable[[List[str]], float]) -> float:
    return float(duration_func(route)) if route else 0.0


def _tune_meta_params(strategy_name: str, params: Dict[str, Any], n_nodes: int) -> Dict[str, Any]:
    tuned = dict(params or {})
    n = max(1, int(n_nodes))

    def cap(value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, value))

    upper = strategy_name.upper()
    if upper == "GA":
        tuned["pop_size"] = cap(int(tuned.get("pop_size", 120)), 40 if n <= 100 else 60, 200)
        tuned["generations"] = cap(int(tuned.get("generations", 300)), 80, 900)
        tuned["mutation_rate"] = float(tuned.get("mutation_rate", 0.12))
        tuned["elite_size"] = max(1, int(tuned.get("elite_size", 6)))
    elif upper == "PSO":
        tuned["swarm_size"] = cap(int(tuned.get("swarm_size", 80)), 30, 180)
        tuned["iterations"] = cap(int(tuned.get("iterations", 250)), 80, 900)
        tuned["w"] = float(tuned.get("w", 0.72))
        tuned["c1"] = float(tuned.get("c1", 1.6))
        tuned["c2"] = float(tuned.get("c2", 1.6))
    elif upper == "GWO":
        tuned["pack_size"] = cap(int(tuned.get("pack_size", 80)), 30, 180)
        tuned["iterations"] = cap(int(tuned.get("iterations", 250)), 80, 900)
    elif upper == "HHO":
        tuned["hawks"] = cap(int(tuned.get("hawks", 80)), 30, 180)
        tuned["iterations"] = cap(int(tuned.get("iterations", 250)), 80, 900)
    return tuned


def _ordered_crossover(parent_a: List[str], parent_b: List[str], rng: random.Random) -> List[str]:
    n = len(parent_a)
    if n < 3:
        return parent_a[:]
    i, j = sorted(rng.sample(range(n), 2))
    child: List[Optional[str]] = [None] * n
    child[i:j + 1] = parent_a[i:j + 1]
    fill = [x for x in parent_b if x not in child]
    pos = 0
    for idx in range(n):
        if child[idx] is None:
            child[idx] = fill[pos]
            pos += 1
    return [str(x) for x in child]


def _mutate_swap(route: List[str], rng: random.Random, rate: float) -> None:
    if len(route) < 2:
        return
    if rng.random() < rate:
        i, j = rng.sample(range(len(route)), 2)
        route[i], route[j] = route[j], route[i]


def _apply_2opt_to_route(
    route: List[str],
    duration_func: Callable[[List[str]], float],
    max_iter: int = 100,
) -> List[str]:
    try:
        improved, _ = apply_local_search(
            route, duration_func, LocalSearchType.TWO_OPT, max_iterations=max_iter
        )
        return improved
    except TypeError:
        improved, _ = apply_local_search(route, duration_func, LocalSearchType.TWO_OPT)
        return improved


def _run_ga(
    initial_route: List[str],
    duration_func: Callable[[List[str]], float],
    params: Dict[str, Any],
    seed: int,
) -> List[str]:
    rng = random.Random(seed)
    n = len(initial_route)
    pop_size = int(params.get("pop_size", 120))
    generations = int(params.get("generations", 300))
    mutation_rate = float(params.get("mutation_rate", 0.12))
    elite_size = max(1, min(int(params.get("elite_size", 6)), pop_size))

    population = []
    for _ in range(pop_size):
        route = initial_route[:]
        rng.shuffle(route)
        population.append(route)
    population[0] = initial_route[:]

    def tournament() -> List[str]:
        sample = rng.sample(population, min(3, len(population)))
        return min(sample, key=lambda r: _route_cost(r, duration_func))

    for gen in range(generations):
        population.sort(key=lambda r: _route_cost(r, duration_func))
        next_population = [p[:] for p in population[:elite_size]]
        while len(next_population) < pop_size:
            child = _ordered_crossover(tournament(), tournament(), rng)
            _mutate_swap(child, rng, mutation_rate)
            next_population.append(child)
        population = next_population
        if gen > 0 and gen % 25 == 0:
            population[0] = _apply_2opt_to_route(population[0], duration_func, max_iter=40)

    best = min(population, key=lambda r: _route_cost(r, duration_func))
    return _apply_2opt_to_route(best, duration_func, max_iter=300)


def _diff_swaps(current: List[str], target: List[str]) -> List[Tuple[int, int]]:
    work = current[:]
    swaps: List[Tuple[int, int]] = []
    pos = {node: i for i, node in enumerate(work)}
    for i, desired in enumerate(target):
        j = pos[desired]
        if i != j:
            swaps.append((i, j))
            work[i], work[j] = work[j], work[i]
            pos[work[j]] = j
            pos[work[i]] = i
    return swaps


def _apply_swaps(position: List[str], swaps: List[Tuple[int, int]]) -> List[str]:
    result = position[:]
    for i, j in swaps:
        if 0 <= i < len(result) and 0 <= j < len(result):
            result[i], result[j] = result[j], result[i]
    return result


def _sample_swaps(swaps: List[Tuple[int, int]], rng: random.Random, scale: float) -> List[Tuple[int, int]]:
    if not swaps:
        return []
    k = max(1, min(len(swaps), int(math.ceil(len(swaps) * scale))))
    return rng.sample(swaps, k) if k < len(swaps) else swaps[:]


def _run_pso(
    initial_route: List[str],
    duration_func: Callable[[List[str]], float],
    params: Dict[str, Any],
    seed: int,
) -> List[str]:
    rng = random.Random(seed)
    swarm_size = int(params.get("swarm_size", 80))
    iterations = int(params.get("iterations", 250))
    c1 = float(params.get("c1", 1.6))
    c2 = float(params.get("c2", 1.6))

    positions = []
    for _ in range(swarm_size):
        route = initial_route[:]
        rng.shuffle(route)
        positions.append(route)
    pbests = [p[:] for p in positions]
    pbest_costs = [_route_cost(p, duration_func) for p in pbests]
    gbest = pbests[int(np.argmin(pbest_costs))][:]
    gbest_cost = min(pbest_costs)

    for it in range(iterations):
        for idx, pos in enumerate(positions):
            swaps = []
            swaps += _sample_swaps(_diff_swaps(pos, pbests[idx]), rng, min(0.35, c1 / 6.0))
            swaps += _sample_swaps(_diff_swaps(pos, gbest), rng, min(0.35, c2 / 6.0))
            if rng.random() < 0.10:
                i, j = rng.sample(range(len(pos)), 2)
                swaps.append((i, j))
            new_pos = _apply_swaps(pos, swaps)
            cost = _route_cost(new_pos, duration_func)
            positions[idx] = new_pos
            if cost < pbest_costs[idx]:
                pbests[idx] = new_pos[:]
                pbest_costs[idx] = cost
                if cost < gbest_cost:
                    gbest = new_pos[:]
                    gbest_cost = cost
        if it > 0 and it % 20 == 0:
            gbest = _apply_2opt_to_route(gbest, duration_func, max_iter=30)
            gbest_cost = _route_cost(gbest, duration_func)
    return _apply_2opt_to_route(gbest, duration_func, max_iter=300)


def _run_gwo(
    initial_route: List[str],
    duration_func: Callable[[List[str]], float],
    params: Dict[str, Any],
    seed: int,
) -> List[str]:
    rng = random.Random(seed)
    pack_size = int(params.get("pack_size", 80))
    iterations = int(params.get("iterations", 250))
    pack = []
    for _ in range(pack_size):
        route = initial_route[:]
        rng.shuffle(route)
        pack.append(route)

    for it in range(iterations):
        pack.sort(key=lambda r: _route_cost(r, duration_func))
        leaders = pack[:3]
        a = 2.0 * (1.0 - it / max(1, iterations))
        new_pack = [leader[:] for leader in leaders]
        for wolf in pack[3:]:
            candidate = wolf[:]
            for leader in leaders:
                scale = min(0.40, max(0.05, a * rng.random() / 3.0))
                candidate = _apply_swaps(candidate, _sample_swaps(_diff_swaps(candidate, leader), rng, scale))
            if rng.random() < 0.08:
                _mutate_swap(candidate, rng, 1.0)
            new_pack.append(candidate)
        pack = new_pack
        if it > 0 and it % 20 == 0:
            pack[0] = _apply_2opt_to_route(pack[0], duration_func, max_iter=30)
    return _apply_2opt_to_route(min(pack, key=lambda r: _route_cost(r, duration_func)), duration_func, 300)


def _levy_flight(route: List[str], rng: random.Random, scale: float = 0.3) -> List[str]:
    result = route[:]
    moves = max(1, int(len(result) * scale * rng.random()))
    for _ in range(moves):
        _mutate_swap(result, rng, 1.0)
    return result


def _run_hho(
    initial_route: List[str],
    duration_func: Callable[[List[str]], float],
    params: Dict[str, Any],
    seed: int,
) -> List[str]:
    rng = random.Random(seed)
    hawks = int(params.get("hawks", 80))
    iterations = int(params.get("iterations", 250))
    population = []
    for _ in range(hawks):
        route = initial_route[:]
        rng.shuffle(route)
        population.append(route)

    best = min(population, key=lambda r: _route_cost(r, duration_func))
    best_cost = _route_cost(best, duration_func)
    for it in range(iterations):
        escape = 2.0 * (1.0 - it / max(1, iterations))
        updated = []
        for hawk in population:
            if abs(escape) >= 1.0:
                target = rng.choice(population)
                candidate = _apply_swaps(hawk, _sample_swaps(_diff_swaps(hawk, target), rng, 0.20))
                candidate = _levy_flight(candidate, rng, scale=0.08)
            else:
                candidate = _apply_swaps(hawk, _sample_swaps(_diff_swaps(hawk, best), rng, 0.35))
                if rng.random() < 0.20:
                    candidate = _levy_flight(candidate, rng, scale=0.05)
            if _route_cost(candidate, duration_func) < _route_cost(hawk, duration_func):
                updated.append(candidate)
            else:
                updated.append(hawk)
        population = updated
        current_best = min(population, key=lambda r: _route_cost(r, duration_func))
        current_cost = _route_cost(current_best, duration_func)
        if current_cost < best_cost:
            best, best_cost = current_best[:], current_cost
        if it > 0 and it % 20 == 0:
            best = _apply_2opt_to_route(best, duration_func, max_iter=30)
            best_cost = _route_cost(best, duration_func)
    return _apply_2opt_to_route(best, duration_func, max_iter=300)


def run_meta_heuristic(
    strategy_name: str,
    initial_route: List[str],
    duration_func: Callable[[List[str]], float],
    params: Dict[str, Any],
    seed: int,
) -> List[str]:
    tuned = _tune_meta_params(strategy_name, params, len(initial_route))
    upper = strategy_name.upper()
    if upper == "GA":
        return _run_ga(initial_route, duration_func, tuned, seed)
    if upper == "PSO":
        return _run_pso(initial_route, duration_func, tuned, seed)
    if upper == "GWO":
        return _run_gwo(initial_route, duration_func, tuned, seed)
    if upper == "HHO":
        return _run_hho(initial_route, duration_func, tuned, seed)
    raise ValueError(f"Unknown meta-heuristic strategy: {strategy_name}")


_run_meta_heuristic = run_meta_heuristic


def calculate_tour_length(tour: List[int], coordinates, dist_matrix: Optional[Any] = None) -> float:
    if not tour:
        return 0.0
    if dist_matrix is not None:
        dm = np.asarray(dist_matrix, dtype=np.float64)
        total = 0.0
        for idx, node in enumerate(tour):
            nxt = tour[(idx + 1) % len(tour)]
            total += float(dm[node - 1, nxt - 1])
        return total
    dm = create_np_distance_matrix(coordinates)
    return calculate_tour_length(tour, coordinates, dm)


def run_single_test(
    problem,
    strategy_instance: Union[LocalSearchType, str],
    seed: int,
    params: Union[Dict[str, Any], int, None] = None,
    dist_matrix: Optional[Any] = None,
) -> Dict[str, Any]:
    run_params: Dict[str, Any] = dict(params or {}) if isinstance(params, dict) else {}
    if isinstance(params, int):
        run_params = {"max_iterations": params}

    dimension = int(problem.dimension)
    unique_locs = [f"L{i + 1}" for i in range(dimension)]
    if dist_matrix is not None:
        np_matrix = np.asarray(dist_matrix, dtype=np.float64)
    else:
        np_matrix = create_np_distance_matrix(problem.coordinates)
    duration_func = create_np_duration_func(np_matrix, unique_locs)

    indices = list(range(1, dimension + 1))
    rng = random.Random(seed)
    rng.shuffle(indices)
    initial_route = [f"L{i}" for i in indices]

    start_time = time.time()
    if isinstance(strategy_instance, LocalSearchType):
        improved_route, _ = apply_local_search(
            initial_route,
            duration_func,
            strategy_instance,
            max_iterations=int(run_params.get("max_iterations", 1000)),
        )
        algorithm_type = "local_search"
    else:
        improved_route = run_meta_heuristic(
            str(strategy_instance), initial_route, duration_func, run_params, seed
        )
        algorithm_type = "meta_heuristic"
    elapsed = time.time() - start_time

    tour_indices = convert_route_to_indices(improved_route)
    tour_length = calculate_tour_length(tour_indices, problem.coordinates, dist_matrix=np_matrix)
    optimal = getattr(problem, "optimal", None)
    gap = ((tour_length - optimal) / optimal) * 100 if optimal and optimal > 0 else float("nan")
    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
        "algorithm_type": algorithm_type,
        "tour": tour_indices,
    }


__all__ = [
    "run_meta_heuristic",
    "_run_meta_heuristic",
    "run_single_test",
    "calculate_tour_length",
]
