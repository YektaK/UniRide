"""Core TSP metaheuristic engines for string-keyed route optimization."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Optional, Tuple

from uniride_core.algorithms.ga_operators import mutate_permutation, order_crossover
from uniride_core.algorithms.local_search import LocalSearchType, TwoOptLocalSearch, apply_local_search
from uniride_core.algorithms.meta_split_common import shuffle_permutation

DurationFunc = Callable[[List[str]], float]


@dataclass
class TSPIndividual:
    """GA individual representing a route permutation."""

    chromosome: List[str]
    fitness: float = 0.0
    total_duration: float = float("inf")


@dataclass
class SwapOperation:
    """Swap operation used as PSO velocity."""

    i: int
    j: int


@dataclass
class TSPParticle:
    """PSO particle representing a route permutation."""

    position: List[str]
    velocity: List[SwapOperation]
    personal_best: List[str]
    personal_best_duration: float = float("inf")
    current_duration: float = float("inf")


@dataclass
class TSPWolf:
    """GWO wolf representing a route permutation."""

    position: List[str]
    fitness: float = 0.0
    total_duration: float = float("inf")


def nearest_neighbor_route(
    waypoints: List[str],
    depot: str,
    distance_lookup: Callable[[str, str], float],
) -> List[str]:
    """Build a nearest-neighbor route with string location ids."""
    if not waypoints:
        return []

    remaining = waypoints.copy()
    route: List[str] = []
    current = depot
    while remaining:
        nearest = min(remaining, key=lambda location: distance_lookup(current, location))
        route.append(nearest)
        remaining.remove(nearest)
        current = nearest
    return route


def solve_two_opt_tsp(
    waypoints: List[str],
    duration_func: DurationFunc,
    rng: random.Random,
    config: Mapping[str, object],
    *,
    initial_route: Optional[List[str]] = None,
) -> Tuple[List[str], float]:
    """Solve a single-vehicle TSP route using 2-opt, optionally multi-start."""
    if not waypoints:
        return [], 0.0
    if len(waypoints) == 1:
        return waypoints.copy(), duration_func(waypoints)
    if len(waypoints) == 2:
        reversed_route = [waypoints[1], waypoints[0]]
        forward_cost = duration_func(waypoints)
        reverse_cost = duration_func(reversed_route)
        return (waypoints.copy(), forward_cost) if forward_cost <= reverse_cost else (reversed_route, reverse_cost)

    two_opt = TwoOptLocalSearch(
        max_iterations=int(config.get("max_iterations", 2000)),
        first_improvement=bool(config.get("first_improvement", False)),
    )
    best_route: Optional[List[str]] = None
    best_duration = float("inf")

    starts: List[List[str]] = []
    if initial_route:
        starts.append(initial_route.copy())
    if bool(config.get("multi_start", True)):
        while len(starts) < int(config.get("num_starts", 10)):
            starts.append(shuffle_permutation(waypoints, rng))
    elif not starts:
        starts.append(waypoints.copy())

    for start in starts:
        improved_route, improved_duration = two_opt.improve(start, duration_func)
        if improved_duration < best_duration:
            best_route = improved_route
            best_duration = improved_duration

    assert best_route is not None
    return best_route, best_duration


def _evaluate_individual(individual: TSPIndividual, duration_func: DurationFunc) -> TSPIndividual:
    duration = duration_func(individual.chromosome)
    return TSPIndividual(
        chromosome=individual.chromosome,
        fitness=1.0 / (duration + 1e-10) if duration > 0 else 0.0,
        total_duration=duration,
    )


def tournament_selection(
    population: List[TSPIndividual],
    tournament_size: int,
    rng: random.Random,
) -> TSPIndividual:
    """Select a GA individual using tournament selection."""
    tournament = rng.sample(population, min(tournament_size, len(population)))
    return max(tournament, key=lambda individual: individual.fitness)


def solve_ga_tsp(
    waypoints: List[str],
    duration_func: DurationFunc,
    rng: random.Random,
    config: Mapping[str, object],
) -> Tuple[List[str], float]:
    """Solve a single-vehicle TSP route using a memetic permutation GA."""
    if not waypoints:
        return [], 0.0
    if len(waypoints) == 1:
        return waypoints.copy(), duration_func(waypoints)
    if len(waypoints) == 2:
        reversed_route = [waypoints[1], waypoints[0]]
        forward_cost = duration_func(waypoints)
        reverse_cost = duration_func(reversed_route)
        return (waypoints.copy(), forward_cost) if forward_cost <= reverse_cost else (reversed_route, reverse_cost)

    def two_opt(route: List[str], max_iter: int = 10) -> List[str]:
        try:
            improved, _ = apply_local_search(
                route,
                duration_func,
                LocalSearchType.TWO_OPT,
                max_iterations=max_iter,
            )
            return improved
        except Exception:
            return route

    population_size = int(config.get("population_size", 50))
    population: List[TSPIndividual] = []
    for _ in range(population_size):
        chromosome = shuffle_permutation(waypoints, rng)
        chromosome = two_opt(chromosome, max_iter=10)
        population.append(_evaluate_individual(TSPIndividual(chromosome), duration_func))

    population.sort(key=lambda individual: individual.total_duration)
    best = TSPIndividual(population[0].chromosome[:], population[0].fitness, population[0].total_duration)
    no_improvement = 0
    elite_count = min(int(config.get("elite_count", 2)), population_size)

    for _ in range(int(config.get("max_iterations", 100))):
        population.sort(key=lambda individual: individual.total_duration)
        if population[0].total_duration < best.total_duration:
            best = TSPIndividual(population[0].chromosome[:], population[0].fitness, population[0].total_duration)
            no_improvement = 0
        else:
            no_improvement += 1
        if no_improvement >= int(config.get("max_no_improvement", 50)):
            break

        new_population = [
            TSPIndividual(individual.chromosome[:], individual.fitness, individual.total_duration)
            for individual in population[:elite_count]
        ]
        while len(new_population) < population_size:
            parent1 = tournament_selection(population, int(config.get("tournament_size", 3)), rng)
            parent2 = tournament_selection(population, int(config.get("tournament_size", 3)), rng)
            if rng.random() < float(config.get("crossover_rate", 0.85)):
                child, _ = order_crossover(parent1.chromosome, parent2.chromosome, rng)
            else:
                child = parent1.chromosome[:]
            if rng.random() < float(config.get("mutation_rate", 0.15)):
                child = mutate_permutation(child, rng, mutation_type="swap" if rng.random() < 0.5 else "inversion")
            new_population.append(_evaluate_individual(TSPIndividual(child), duration_func))
        population = new_population

    polished = two_opt(best.chromosome, max_iter=300)
    polished_duration = duration_func(polished)
    if polished_duration < best.total_duration:
        return polished, polished_duration
    return best.chromosome, best.total_duration


def generate_random_velocity(n: int, max_velocity_size: int, rng: random.Random) -> List[SwapOperation]:
    """Generate a random PSO swap velocity."""
    if n < 1:
        return []
    return [
        SwapOperation(i=rng.randint(0, n - 1), j=rng.randint(0, n - 1))
        for _ in range(rng.randint(1, max(1, max_velocity_size)))
    ]


def diff_swaps(current: List[str], target: List[str]) -> List[SwapOperation]:
    """Return swaps that transform current into target."""
    swaps: List[SwapOperation] = []
    temp = current[:]
    for idx in range(len(target)):
        if temp[idx] != target[idx]:
            try:
                swap_idx = temp.index(target[idx], idx)
            except ValueError:
                continue
            temp[idx], temp[swap_idx] = temp[swap_idx], temp[idx]
            swaps.append(SwapOperation(idx, swap_idx))
    return swaps


def apply_swaps(position: List[str], swaps: List[SwapOperation]) -> List[str]:
    """Apply swap sequence deterministically."""
    new_position = position[:]
    for swap in swaps:
        if 0 <= swap.i < len(new_position) and 0 <= swap.j < len(new_position):
            new_position[swap.i], new_position[swap.j] = new_position[swap.j], new_position[swap.i]
    return new_position


def combine_velocities(
    inertia_velocity: List[SwapOperation],
    cognitive_velocity: List[SwapOperation],
    social_velocity: List[SwapOperation],
    config: Mapping[str, object],
    rng: random.Random,
) -> List[SwapOperation]:
    """Combine PSO velocity components with Clerc-style probabilities."""
    combined: List[SwapOperation] = []
    for swap in inertia_velocity:
        if rng.random() < float(config.get("inertia_weight", 0.729)):
            combined.append(swap)
    for swap in cognitive_velocity:
        if rng.random() < float(config.get("cognitive_weight", 1.49445)) / 3.0:
            combined.append(swap)
    for swap in social_velocity:
        if rng.random() < float(config.get("social_weight", 1.49445)) / 3.0:
            combined.append(swap)

    max_velocity = int(config.get("max_velocity_size", 5))
    if len(combined) > max_velocity:
        combined = rng.sample(combined, max_velocity)
    return combined


def gwo_difference_swaps(
    leader: List[str],
    wolf: List[str],
    a: float,
    rng: random.Random,
) -> List[Tuple[int, int]]:
    """Calculate swaps to move a wolf route toward a leader route."""
    swaps: List[Tuple[int, int]] = []
    for idx in range(len(wolf)):
        if wolf[idx] == leader[idx]:
            continue
        try:
            swap_idx = wolf.index(leader[idx])
        except ValueError:
            continue
        if rng.random() < a / 2:
            swaps.append((idx, swap_idx))
    return swaps


def apply_tuple_swaps(position: List[str], swaps: List[Tuple[int, int]]) -> List[str]:
    """Apply tuple-based swap operations to a route permutation."""
    new_position = position.copy()
    for left, right in swaps:
        if 0 <= left < len(new_position) and 0 <= right < len(new_position):
            new_position[left], new_position[right] = new_position[right], new_position[left]
    return new_position


def update_gwo_position(
    wolf: TSPWolf,
    alpha: TSPWolf,
    beta: TSPWolf,
    delta: TSPWolf,
    a: float,
    rng: random.Random,
) -> List[str]:
    """Update a GWO wolf route from alpha, beta, and delta leaders."""
    alpha_swaps = gwo_difference_swaps(alpha.position, wolf.position, a, rng)
    beta_swaps = gwo_difference_swaps(beta.position, wolf.position, a, rng)
    delta_swaps = gwo_difference_swaps(delta.position, wolf.position, a, rng)

    all_swaps: List[Tuple[int, int]] = []
    all_swaps.extend(swap for swap in alpha_swaps if rng.random() < 0.7)
    all_swaps.extend(swap for swap in beta_swaps if rng.random() < 0.5)
    all_swaps.extend(swap for swap in delta_swaps if rng.random() < 0.3)

    if not all_swaps:
        return wolf.position.copy()

    num_swaps = min(len(all_swaps), max(1, int(len(all_swaps) * a / 2)))
    return apply_tuple_swaps(wolf.position, rng.sample(all_swaps, min(num_swaps, len(all_swaps))))


def _evaluate_wolf(wolf: TSPWolf, duration_func: DurationFunc) -> TSPWolf:
    duration = duration_func(wolf.position)
    return TSPWolf(
        position=wolf.position,
        fitness=1.0 / duration if duration > 0 else 0.0,
        total_duration=duration,
    )


def solve_gwo_tsp(
    waypoints: List[str],
    duration_func: DurationFunc,
    rng: random.Random,
    config: Mapping[str, object],
) -> Tuple[List[str], float]:
    """Solve a single-vehicle TSP route using Grey Wolf Optimizer."""
    if not waypoints:
        return [], 0.0
    if len(waypoints) == 1:
        return waypoints.copy(), duration_func(waypoints)
    if len(waypoints) == 2:
        reversed_route = [waypoints[1], waypoints[0]]
        forward_cost = duration_func(waypoints)
        reverse_cost = duration_func(reversed_route)
        return (waypoints.copy(), forward_cost) if forward_cost <= reverse_cost else (reversed_route, reverse_cost)

    pack = [
        _evaluate_wolf(TSPWolf(shuffle_permutation(waypoints, rng)), duration_func)
        for _ in range(int(config.get("population_size", 30)))
    ]
    pack.sort(key=lambda wolf: wolf.total_duration)
    alpha = TSPWolf(pack[0].position.copy(), pack[0].fitness, pack[0].total_duration)
    beta = TSPWolf(pack[1].position.copy(), pack[1].fitness, pack[1].total_duration) if len(pack) > 1 else alpha
    delta = TSPWolf(pack[2].position.copy(), pack[2].fitness, pack[2].total_duration) if len(pack) > 2 else beta

    no_improvement = 0
    max_iterations = int(config.get("max_iterations", 100))
    initial_a = float(config.get("initial_a", 2.0))
    exploration_rate = float(config.get("exploration_rate", 0.5))
    for iteration in range(max_iterations):
        a = initial_a * (1 - iteration / max_iterations)
        improved = False

        for wolf in pack:
            if rng.random() < exploration_rate * a / initial_a:
                new_position = shuffle_permutation(wolf.position, rng)
            else:
                new_position = update_gwo_position(wolf, alpha, beta, delta, a, rng)

            candidate = _evaluate_wolf(TSPWolf(new_position), duration_func)
            if candidate.total_duration < wolf.total_duration:
                wolf.position = candidate.position
                wolf.total_duration = candidate.total_duration
                wolf.fitness = candidate.fitness

            if wolf.total_duration < alpha.total_duration:
                delta = TSPWolf(beta.position.copy(), beta.fitness, beta.total_duration)
                beta = TSPWolf(alpha.position.copy(), alpha.fitness, alpha.total_duration)
                alpha = TSPWolf(wolf.position.copy(), wolf.fitness, wolf.total_duration)
                improved = True
            elif wolf.total_duration < beta.total_duration:
                delta = TSPWolf(beta.position.copy(), beta.fitness, beta.total_duration)
                beta = TSPWolf(wolf.position.copy(), wolf.fitness, wolf.total_duration)
                improved = True
            elif wolf.total_duration < delta.total_duration:
                delta = TSPWolf(wolf.position.copy(), wolf.fitness, wolf.total_duration)
                improved = True

        no_improvement = 0 if improved else no_improvement + 1
        if no_improvement >= int(config.get("max_no_improvement", 20)):
            break

    best_route = alpha.position
    best_duration = alpha.total_duration
    try:
        local_search_type = LocalSearchType(str(config.get("local_search_type", "two_opt")))
    except ValueError:
        local_search_type = LocalSearchType.TWO_OPT
    improved_route, improved_duration = apply_local_search(best_route, duration_func, local_search_type)
    if improved_duration < best_duration:
        return improved_route, improved_duration
    return best_route, best_duration


def solve_pso_tsp(
    waypoints: List[str],
    duration_func: DurationFunc,
    rng: random.Random,
    config: Mapping[str, object],
) -> Tuple[List[str], float]:
    """Solve a single-vehicle TSP route using swap-sequence PSO."""
    if not waypoints:
        return [], 0.0
    if len(waypoints) == 1:
        return waypoints.copy(), duration_func(waypoints)
    if len(waypoints) == 2:
        reversed_route = [waypoints[1], waypoints[0]]
        forward_cost = duration_func(waypoints)
        reverse_cost = duration_func(reversed_route)
        return (waypoints.copy(), forward_cost) if forward_cost <= reverse_cost else (reversed_route, reverse_cost)

    max_velocity = int(config.get("max_velocity_size", 5))
    reinit_interval = int(config.get("reinit_interval", 50))
    n = len(waypoints)
    swarm: List[TSPParticle] = []
    for _ in range(int(config.get("swarm_size", 30))):
        position = shuffle_permutation(waypoints, rng)
        swarm.append(
            TSPParticle(
                position=position,
                velocity=generate_random_velocity(n, max_velocity, rng),
                personal_best=position.copy(),
            )
        )

    global_best = waypoints.copy()
    global_best_duration = float("inf")
    for particle in swarm:
        duration = duration_func(particle.position)
        particle.current_duration = duration
        particle.personal_best_duration = duration
        if duration < global_best_duration:
            global_best = particle.position.copy()
            global_best_duration = duration

    no_improvement = 0
    for iteration in range(int(config.get("max_iterations", 100))):
        improved = False
        for particle in swarm:
            cognitive_velocity = diff_swaps(particle.position, particle.personal_best)
            social_velocity = diff_swaps(particle.position, global_best)
            new_velocity = combine_velocities(
                particle.velocity,
                cognitive_velocity,
                social_velocity,
                config,
                rng,
            )
            new_position = apply_swaps(particle.position, new_velocity)
            duration = duration_func(new_position)

            particle.position = new_position
            particle.velocity = new_velocity
            particle.current_duration = duration

            if duration < particle.personal_best_duration:
                particle.personal_best = new_position.copy()
                particle.personal_best_duration = duration
                if duration < global_best_duration:
                    global_best = new_position.copy()
                    global_best_duration = duration
                    improved = True

        no_improvement = 0 if improved else no_improvement + 1

        if iteration > 0 and iteration % reinit_interval == 0:
            for particle in swarm:
                if rng.random() < 0.9:
                    position = particle.personal_best[:]
                    for _ in range(rng.randint(1, 3)):
                        left, right = rng.sample(range(n), 2)
                        position[left], position[right] = position[right], position[left]
                else:
                    position = global_best[:]
                    rng.shuffle(position)
                duration = duration_func(position)
                particle.position = position
                particle.velocity = generate_random_velocity(n, max_velocity, rng)
                if duration < particle.personal_best_duration:
                    particle.personal_best = position[:]
                    particle.personal_best_duration = duration
                if duration < global_best_duration:
                    global_best = position[:]
                    global_best_duration = duration

        if no_improvement >= int(config.get("max_no_improvement", 25)):
            break

    best_route = global_best
    best_duration = global_best_duration
    try:
        local_search_type = LocalSearchType(str(config.get("local_search_type", "two_opt")))
    except ValueError:
        local_search_type = LocalSearchType.TWO_OPT
    improved_route, improved_duration = apply_local_search(best_route, duration_func, local_search_type)
    if improved_duration < best_duration:
        return improved_route, improved_duration
    return best_route, best_duration


# ---------------------------------------------------------------------------
# Harris Hawks Optimization (HHO) — Heidari et al. (2019)
# ---------------------------------------------------------------------------


@dataclass
class TSPHawk:
    """HHO hawk individual representing a route permutation."""

    position: List[str]
    fitness: float = 0.0
    total_duration: float = float("inf")


def levy_flight_permutation(
    position: List[str],
    rng: random.Random,
    scale: float = 0.5,
) -> List[str]:
    """Mutate a permutation via Lévy flight (occasional long jumps).

    Uses Mantegna's algorithm with beta = 1.5 to draw step lengths from
    a stable distribution, then applies that many random swaps.
    """
    new_position = position[:]
    n = len(new_position)
    if n < 2:
        return new_position

    beta = 1.5
    sigma = (
        math.gamma(1 + beta) * math.sin(math.pi * beta / 2)
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


def _hho_soft_besiege(
    hawk_position: List[str],
    prey_position: List[str],
    escape_energy: float,
    rng: random.Random,
) -> List[str]:
    """Soft besiege: move toward prey with probabilistic swap subset."""
    J = 2 * (1 - rng.random())
    intensity = abs(escape_energy * J)
    swaps = diff_swaps(hawk_position, prey_position)
    filtered = [s for s in swaps if rng.random() < intensity]
    return apply_swaps(hawk_position, filtered)


def _hho_hard_besiege(
    hawk_position: List[str],
    prey_position: List[str],
    escape_energy: float,
    rng: random.Random,
) -> List[str]:
    """Hard besiege: tightly move toward prey."""
    intensity = abs(escape_energy)
    swaps = diff_swaps(hawk_position, prey_position)
    filtered = [s for s in swaps if rng.random() < intensity]
    return apply_swaps(hawk_position, filtered)


def _hho_soft_besiege_with_dives(
    hawk_position: List[str],
    prey_position: List[str],
    escape_energy: float,
    duration_func: DurationFunc,
    rng: random.Random,
) -> List[str]:
    """Soft besiege with progressive rapid dives (Lévy flight perturbations).

    Tries 3 independent dives from the original hawk position and returns
    the best candidate that improves over the hawk's current cost.
    """
    best_position = hawk_position[:]
    best_duration = duration_func(hawk_position)

    for _ in range(3):
        intensity = abs(escape_energy) * rng.random()
        swaps = diff_swaps(hawk_position, prey_position)
        filtered = [s for s in swaps if rng.random() < intensity]
        candidate = apply_swaps(hawk_position, filtered)
        candidate = levy_flight_permutation(candidate, rng, scale=0.3)
        duration = duration_func(candidate)
        if duration < best_duration:
            best_position = candidate
            best_duration = duration

    return best_position


def _hho_hard_besiege_with_dives(
    hawk_position: List[str],
    prey_position: List[str],
    escape_energy: float,
    rng: random.Random,
) -> List[str]:
    """Hard besiege with progressive rapid dives (strong Lévy flight)."""
    intensity = abs(escape_energy)
    swaps = diff_swaps(hawk_position, prey_position)
    filtered = [s for s in swaps if rng.random() < intensity]
    candidate = apply_swaps(hawk_position, filtered)
    return levy_flight_permutation(candidate, rng, scale=0.2)


def hho_escape_energy(
    e0: float,
    iteration: int,
    max_iterations: int,
    initial_energy: float,
) -> float:
    """Calculate HHO escape energy with configurable initial energy."""
    return 2 * e0 * (1 - iteration / max_iterations) * initial_energy


def hho_use_direct_besiege(r: float, jump_probability: float) -> bool:
    """Return True for the original direct soft/hard besiege branch."""
    return r >= jump_probability


def solve_hho_tsp(
    waypoints: List[str],
    duration_func: DurationFunc,
    rng: random.Random,
    config: Mapping[str, object],
) -> Tuple[List[str], float]:
    """Solve a single-vehicle TSP route using Harris Hawks Optimization.

    Based on Heidari et al. (2019).  The algorithm adaptively switches
    between exploration (random perching, Lévy flights) and exploitation
    (soft/hard besiege with optional rapid dives) driven by a linearly
    decreasing escape-energy parameter.

    Returns ``(best_route, best_duration)``.
    """
    if not waypoints:
        return [], 0.0
    if len(waypoints) == 1:
        return waypoints.copy(), duration_func(waypoints)
    if len(waypoints) == 2:
        reversed_route = [waypoints[1], waypoints[0]]
        forward_cost = duration_func(waypoints)
        reverse_cost = duration_func(reversed_route)
        return (waypoints.copy(), forward_cost) if forward_cost <= reverse_cost else (reversed_route, reverse_cost)

    population_size = int(config.get("population_size", 30))
    max_iterations = int(config.get("max_iterations", 100))
    initial_energy = float(config.get("initial_energy", 1.0))
    jump_probability = float(config.get("jump_probability", 0.5))
    max_no_improvement = int(config.get("max_no_improvement", 20))

    hawks: List[TSPHawk] = []
    for _ in range(population_size):
        position = shuffle_permutation(waypoints, rng)
        duration = duration_func(position)
        hawks.append(TSPHawk(
            position=position,
            fitness=1.0 / duration if duration > 0 else 0.0,
            total_duration=duration,
        ))

    prey = min(hawks, key=lambda h: h.total_duration)
    prey = TSPHawk(position=prey.position[:], fitness=prey.fitness, total_duration=prey.total_duration)

    no_improvement = 0

    for iteration in range(max_iterations):
        E0 = 2 * rng.random() - 1
        E = hho_escape_energy(E0, iteration, max_iterations, initial_energy)

        improved = False

        for hawk in hawks:
            r = rng.random()

            if abs(E) >= 1:
                # Exploration
                if rng.random() < 0.5:
                    intensity = rng.random()
                    swaps = diff_swaps(hawk.position, prey.position)
                    filtered = [s for s in swaps if rng.random() < intensity]
                    new_position = apply_swaps(hawk.position, filtered)
                else:
                    new_position = levy_flight_permutation(hawk.position, rng)
            else:
                # Exploitation
                if hho_use_direct_besiege(r, jump_probability):
                    if abs(E) >= 0.5:
                        new_position = _hho_soft_besiege(hawk.position, prey.position, E, rng)
                    else:
                        new_position = _hho_hard_besiege(hawk.position, prey.position, E, rng)
                else:
                    if abs(E) >= 0.5:
                        new_position = _hho_soft_besiege_with_dives(
                            hawk.position, prey.position, E, duration_func, rng,
                        )
                    else:
                        new_position = _hho_hard_besiege_with_dives(
                            hawk.position, prey.position, E, rng,
                        )

            duration = duration_func(new_position)

            if duration < hawk.total_duration:
                hawk.position = new_position
                hawk.total_duration = duration
                hawk.fitness = 1.0 / duration if duration > 0 else 0.0

            if hawk.total_duration < prey.total_duration:
                prey = TSPHawk(position=hawk.position[:], fitness=hawk.fitness, total_duration=hawk.total_duration)
                improved = True

        no_improvement = 0 if improved else no_improvement + 1
        if no_improvement >= max_no_improvement:
            break

    best_route = prey.position
    best_duration = prey.total_duration

    try:
        ls_type = LocalSearchType(str(config.get("local_search_type", "two_opt")))
    except ValueError:
        ls_type = LocalSearchType.TWO_OPT

    improved_route, improved_duration = apply_local_search(best_route, duration_func, ls_type)
    if improved_duration < best_duration:
        return improved_route, improved_duration
    return best_route, best_duration


__all__ = [
    "SwapOperation",
    "TSPHawk",
    "TSPIndividual",
    "TSPParticle",
    "TSPWolf",
    "apply_swaps",
    "apply_tuple_swaps",
    "combine_velocities",
    "diff_swaps",
    "generate_random_velocity",
    "gwo_difference_swaps",
    "hho_escape_energy",
    "hho_use_direct_besiege",
    "levy_flight_permutation",
    "nearest_neighbor_route",
    "solve_ga_tsp",
    "solve_gwo_tsp",
    "solve_hho_tsp",
    "solve_pso_tsp",
    "solve_two_opt_tsp",
    "tournament_selection",
    "update_gwo_position",
]
