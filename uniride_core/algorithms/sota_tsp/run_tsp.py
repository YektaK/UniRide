"""
RUN-TSP — Runge Kutta Optimizer (TSP variant)

Adapted from Ahmadianfar et al. (2021) "RUN: Beyond the Metaphor: An Efficient
Optimization Algorithm Based on Runge Kutta Method" for discrete TSP space.

Core DNA:
  - RK4 numerical method: 4-stage slope evaluation (k1, k2, k3, k4)
  - Enhanced Solution Quality (ESQ): local optima escape mechanism
  - Adaptive exploration/exploitation controlled by solution quality ranking
  - Metaphor-free: mathematical foundation, not biology-inspired
  - Only 3 parameters: population size, max iterations, beta

Discrete TSP Adaptation:
  - Continuous slope computation → discrete move operator evaluation
  - k1 → 2-opt move (shallow gradient)
  - k2 → 3-opt-bounded move (deeper gradient)
  - k3 → swap move (different direction)
  - k4 → insert move (another direction)
  - RK4 weighted average → weighted selection of best move result
  - ESQ → random k-opt perturbation with best-tour guidance
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base_solver import BaseTSPSolver, TSPResult
from .ls_engine import MultiLayerLS


@dataclass
class RUNConfig:
    population_size: int = 40
    max_iterations: int = 500
    beta: float = 0.5           # Control factor for exploration/exploitation balance
    esq_probability: float = 0.2 # Probability of applying ESQ mechanism
    ls_time_limit: float = 0.5
    three_opt_window: int = 12
    time_limit: float = 300.0
    seed: int = 42


def _random_tour(n: int, rng: random.Random) -> List[int]:
    """Generate a random permutation tour."""
    tour = list(range(n))
    rng.shuffle(tour)
    return tour


def _greedy_tour(dist_matrix: List[List[float]], start: int, n: int) -> List[int]:
    """Build a greedy tour starting from a given node."""
    visited = [False] * n
    visited[start] = True
    tour = [start]
    current = start
    for _ in range(n - 1):
        best_next = -1
        best_dist = float("inf")
        for j in range(n):
            if not visited[j] and dist_matrix[current][j] < best_dist:
                best_dist = dist_matrix[current][j]
                best_next = j
        visited[best_next] = True
        tour.append(best_next)
        current = best_next
    return tour


def _apply_2opt(tour: List[int], dist_matrix: List[List[float]],
                rng: random.Random, window: int = 12) -> List[int]:
    """Apply a single 2-opt move (k1 slope — shallow gradient)."""
    result = tour[:]
    n = len(result)
    if n < 4:
        return result
    i = rng.randint(0, n - 3)
    j = rng.randint(i + 2, min(i + window, n - 1))
    result[i:j + 1] = result[i:j + 1][::-1]
    return result


def _apply_3opt_bounded(tour: List[int], dist_matrix: List[List[float]],
                        rng: random.Random, window: int = 12) -> List[int]:
    """Apply a single 3-opt-bounded move (k2 slope — deeper gradient)."""
    result = tour[:]
    n = len(result)
    if n < 6:
        return result
    # Select three cut points within bounded window
    i = rng.randint(0, n - 4)
    j = rng.randint(i + 1, min(i + window, n - 2))
    k = rng.randint(j + 1, min(j + window, n - 1))

    # Try all 7 Lin-Kernighan reconnection patterns, pick best
    candidates = []

    # Case 0: no change (baseline)
    candidates.append(result[:])

    # Case 1: reverse segment [i+1..j]
    c1 = result[:]
    c1[i + 1:j + 1] = c1[i + 1:j + 1][::-1]
    candidates.append(c1)

    # Case 2: reverse segment [j+1..k]
    c2 = result[:]
    c2[j + 1:k + 1] = c2[j + 1:k + 1][::-1]
    candidates.append(c2)

    # Case 3: reverse both [i+1..j] and [j+1..k]
    c3 = result[:]
    c3[i + 1:j + 1] = c3[i + 1:j + 1][::-1]
    c3[j + 1:k + 1] = c3[j + 1:k + 1][::-1]
    candidates.append(c3)

    # Case 4: move segment [i+1..j] after k
    c4 = result[:i + 1] + result[j + 1:k + 1] + result[i + 1:j + 1] + result[k + 1:]
    candidates.append(c4)

    # Case 5: move segment [j+1..k] before i+1
    c5 = result[:i + 1] + result[j + 1:k + 1] + result[i + 1:j + 1] + result[k + 1:]
    candidates.append(c5)

    # Case 6: reverse [i+1..j], move after k
    c6 = result[:i + 1] + result[j + 1:k + 1] + list(reversed(result[i + 1:j + 1])) + result[k + 1:]
    candidates.append(c6)

    best = min(candidates, key=lambda t: _tour_cost(t, dist_matrix))
    return best


def _apply_swap(tour: List[int], dist_matrix: List[List[float]],
                rng: random.Random) -> List[int]:
    """Apply a single swap move (k3 slope — different direction)."""
    result = tour[:]
    n = len(result)
    if n < 2:
        return result
    i, j = rng.sample(range(n), 2)
    result[i], result[j] = result[j], result[i]
    return result


def _apply_insert(tour: List[int], dist_matrix: List[List[float]],
                  rng: random.Random) -> List[int]:
    """Apply a single insert move (k4 slope — another direction)."""
    result = tour[:]
    n = len(result)
    if n < 3:
        return result
    i = rng.randint(0, n - 1)
    j = rng.randint(0, n - 2)
    if j >= i:
        j += 1
    city = result.pop(i)
    result.insert(j, city)
    return result


def _tour_cost(tour: List[int], dist_matrix: List[List[float]]) -> float:
    """Calculate tour length."""
    cost = 0.0
    n = len(tour)
    for i in range(n):
        cost += dist_matrix[tour[i]][tour[(i + 1) % n]]
    return cost


def _select_weighted(candidates: List[List[int]], weights: List[float],
                     dist_matrix: List[List[float]], rng: random.Random) -> List[int]:
    """Select a candidate using RK4-inspired weighted selection.

    Instead of arithmetic averaging (impossible for permutations),
    we use weights as selection probabilities, biased toward better solutions.
    """
    costs = [_tour_cost(c, dist_matrix) for c in candidates]
    n = len(candidates)

    # Combine RK4 weights with solution quality (lower cost = higher probability)
    max_cost = max(costs) if costs else 1.0
    quality_scores = [(max_cost - c + 1e-6) for c in costs]

    # Combined score: RK4 weight × quality
    combined = [weights[i] * quality_scores[i] for i in range(n)]
    total = sum(combined)
    if total <= 0:
        return candidates[0]

    probs = [s / total for s in combined]
    r = rng.random()
    cumulative = 0.0
    for i, p in enumerate(probs):
        cumulative += p
        if r <= cumulative:
            return candidates[i]
    return candidates[-1]


def _esq_perturbation(tour: List[int], best_tour: List[int],
                      dist_matrix: List[List[float]], rng: random.Random,
                      intensity: float = 0.1) -> List[int]:
    """Enhanced Solution Quality (ESQ) mechanism for local optima escape.

    Combines random perturbation with best-solution guidance.
    """
    n = len(tour)
    result = tour[:]
    n_swaps = max(1, int(n * intensity))

    # Phase 1: random perturbation
    for _ in range(n_swaps):
        i, j = rng.sample(range(n), 2)
        result[i], result[j] = result[j], result[i]

    # Phase 2: inject edges from best tour (guidance)
    if rng.random() < 0.5 and best_tour:
        # Copy a random subsequence from best tour
        start = rng.randint(0, n - 3)
        length = rng.randint(2, min(6, n - start))
        result[start:start + length] = best_tour[start:start + length]
        # Repair duplicates
        seen = set()
        cleaned = []
        for city in result:
            if city not in seen:
                seen.add(city)
                cleaned.append(city)
        missing = [c for c in range(n) if c not in seen]
        rng.shuffle(missing)
        cleaned.extend(missing)
        result = cleaned

    return result


class RUN_TSP(BaseTSPSolver):
    """Runge Kutta Optimizer for TSP.

    Uses 4-stage RK4 move evaluation + ESQ mechanism for local optima escape.
    """

    def __init__(self, config: Optional[RUNConfig] = None):
        super().__init__("RUN-TSP", config.seed if config else 42)
        self.cfg = config or RUNConfig()
        self._rng = random.Random(self.cfg.seed)

    def _init_population(self, n: int) -> List[List[int]]:
        """Initialize population with greedy + random tours."""
        pop = []
        # 50% greedy tours from random starts
        for _ in range(self.cfg.population_size // 2):
            start = self._rng.randint(0, n - 1)
            pop.append(_greedy_tour(self._dist_matrix, start, n))
        # 50% random tours
        for _ in range(self.cfg.population_size - len(pop)):
            pop.append(_random_tour(n, self._rng))
        return pop

    def _compute_rk4_moves(self, tour: List[int]) -> List[List[int]]:
        """Compute 4 RK4 slope stages as discrete TSP moves.

        k1: 2-opt (shallow gradient)
        k2: 3-opt-bounded (deeper gradient)
        k3: swap (different direction)
        k4: insert (another direction)
        """
        k1 = _apply_2opt(tour, self._dist_matrix, self._rng, self.cfg.three_opt_window)
        k2 = _apply_3opt_bounded(k1, self._dist_matrix, self._rng, self.cfg.three_opt_window)
        k3 = _apply_swap(k2, self._dist_matrix, self._rng)
        k4 = _apply_insert(k3, self._dist_matrix, self._rng)
        return [k1, k2, k3, k4]

    def _run_update(self, tour: List[int], best_tour: List[int],
                    worst_tour: List[int], iteration: int, max_iter: int) -> List[int]:
        """Apply RUN position update rule for discrete TSP.

        Continuous: X_new = X + SF * SM * beta * (X_best - X_random)
                                 + SF * SM * (1 - beta) * (X_random - X_worst)

        Discrete: Use RK4 moves + guided perturbation toward best, away from worst.
        """
        # Compute adaptive scaling factor (decreases over iterations)
        sf = 1.0 - (iteration / max_iter)  # Linear decay: 1.0 → 0.0

        # Phase 1: RK4 move evaluation
        moves = self._compute_rk4_moves(tour)
        # RK4 weights: [1, 2, 2, 1]
        rk4_weights = [1.0, 2.0, 2.0, 1.0]
        candidate = _select_weighted(moves, rk4_weights, self._dist_matrix, self._rng)

        # Phase 2: Best-solution guidance (exploitation)
        if self._rng.random() < sf * self.cfg.beta:
            # Guided 2-opt: prefer edges from best tour
            guided = self._guided_2opt(candidate, best_tour)
            if _tour_cost(guided, self._dist_matrix) < _tour_cost(candidate, self._dist_matrix):
                candidate = guided

        # Phase 3: Worst-solution avoidance (exploration)
        if self._rng.random() < sf * (1.0 - self.cfg.beta):
            # Avoid edges from worst tour
            avoided = self._avoid_worst_edges(candidate, worst_tour)
            if _tour_cost(avoided, self._dist_matrix) < _tour_cost(candidate, self._dist_matrix):
                candidate = avoided

        return candidate

    def _guided_2opt(self, tour: List[int], guide_tour: List[int]) -> List[int]:
        """Apply 2-opt moves that align edges with the guide tour."""
        n = len(tour)
        if n < 4:
            return tour[:]

        # Build edge set from guide tour
        guide_edges = set()
        for i in range(n):
            a, b = guide_tour[i], guide_tour[(i + 1) % n]
            guide_edges.add((min(a, b), max(a, b)))

        result = tour[:]
        improved = True
        max_passes = 5
        passes = 0

        while improved and passes < max_passes:
            improved = False
            passes += 1
            for i in range(n - 2):
                for j in range(i + 2, min(i + self.cfg.three_opt_window, n)):
                    # Check if reversing [i..j] creates more guide edges
                    current_edges = 0
                    new_edges = 0
                    for k in range(n):
                        a, b = result[k], result[(k + 1) % n]
                        edge = (min(a, b), max(a, b))
                        current_edges += (1 if edge in guide_edges else 0)

                    # Simulate reversal
                    new_tour = result[:i] + result[i:j + 1][::-1] + result[j + 1:]
                    for k in range(n):
                        a, b = new_tour[k], new_tour[(k + 1) % n]
                        edge = (min(a, b), max(a, b))
                        new_edges += (1 if edge in guide_edges else 0)

                    if new_edges > current_edges:
                        result = new_tour
                        improved = True
                        break
                if improved:
                    break

        return result

    def _avoid_worst_edges(self, tour: List[int], worst_tour: List[int]) -> List[int]:
        """Apply moves that avoid edges present in the worst tour."""
        n = len(tour)
        if n < 4:
            return tour[:]

        # Build edge set from worst tour
        worst_edges = set()
        for i in range(n):
            a, b = worst_tour[i], worst_tour[(i + 1) % n]
            worst_edges.add((min(a, b), max(a, b)))

        result = tour[:]
        # Try random 2-opt moves that remove worst edges
        for _ in range(min(10, n)):
            i = self._rng.randint(0, n - 3)
            j = self._rng.randint(i + 2, min(i + self.cfg.three_opt_window, n - 1))

            # Check if reversal removes worst edges
            old_worst_count = 0
            for k in range(i, j):
                a, b = result[k], result[k + 1]
                edge = (min(a, b), max(a, b))
                if edge in worst_edges:
                    old_worst_count += 1

            new_tour = result[:i] + result[i:j + 1][::-1] + result[j + 1:]
            new_worst_count = 0
            for k in range(i, j):
                a, b = new_tour[k], new_tour[k + 1]
                edge = (min(a, b), max(a, b))
                if edge in worst_edges:
                    new_worst_count += 1

            if new_worst_count < old_worst_count:
                result = new_tour

        return result

    def _solve(self) -> TSPResult:
        t_start = time.perf_counter()
        n = self._n

        if n < 3:
            tour = list(range(n))
            return TSPResult(
                algorithm=self.name, tour=tour,
                tour_length=self.tour_length(tour),
                elapsed_ms=(time.perf_counter() - t_start) * 1000,
                iterations=0, params={"population_size": self.cfg.population_size},
                seed=self.cfg.seed,
            )

        # Initialize population
        population = self._init_population(n)
        fitness = [_tour_cost(t, self._dist_matrix) for t in population]

        best_tour = min(population, key=lambda t: _tour_cost(t, self._dist_matrix))
        best_cost = _tour_cost(best_tour, self._dist_matrix)
        history = [best_cost]

        # Main loop
        max_iter = self.cfg.max_iterations
        time_limit = self.cfg.time_limit

        for iteration in range(max_iter):
            # Check time limit
            if time.perf_counter() - t_start > time_limit:
                break

            # Sort population by fitness
            sorted_indices = sorted(range(len(fitness)), key=lambda i: fitness[i])
            sorted_pop = [population[i] for i in sorted_indices]
            sorted_fit = [fitness[i] for i in sorted_indices]

            # Elitism: keep best tour
            elite = sorted_pop[0]
            elite_cost = sorted_fit[0]

            if elite_cost < best_cost:
                best_tour = elite[:]
                best_cost = elite_cost

            # Generate new population using RUN update rule
            new_population = [elite[:]]  # Keep elite
            new_fitness = [elite_cost]

            for i in range(1, self.cfg.population_size):
                # Select current, best, worst for RUN update
                current = sorted_pop[i]
                worst = sorted_pop[-1]

                # Apply RUN position update
                candidate = self._run_update(current, best_tour, worst, iteration, max_iter)

                # ESQ mechanism: stochastic local optima escape
                if self._rng.random() < self.cfg.esq_probability:
                    intensity = 0.05 + 0.15 * (1.0 - iteration / max_iter)  # Decay from 0.2 to 0.05
                    candidate = _esq_perturbation(candidate, best_tour, self._dist_matrix,
                                                  self._rng, intensity)

                # Local search refinement (lightweight)
                candidate, _, _ = MultiLayerLS.improve(
                    candidate, self._dist_matrix, dm_np=None, intensity="light",
                    time_limit=self.cfg.ls_time_limit,
                    three_opt_window=self.cfg.three_opt_window,
                )

                candidate_cost = _tour_cost(candidate, self._dist_matrix)
                new_population.append(candidate)
                new_fitness.append(candidate_cost)

            population = new_population
            fitness = new_fitness

            # Update best
            iter_best = min(fitness)
            if iter_best < best_cost:
                best_idx = fitness.index(iter_best)
                best_tour = population[best_idx][:]
                best_cost = iter_best

            history.append(best_cost)

            # Stagnation detection: apply ESQ on best if no improvement
            if iteration > 0 and abs(history[-1] - history[-2]) < 1e-6:
                perturbed = _esq_perturbation(best_tour, best_tour, self._dist_matrix,
                                              self._rng, intensity=0.15)
                perturbed, _, _ = MultiLayerLS.improve(
                    perturbed, self._dist_matrix, dm_np=None, intensity="light",
                    time_limit=self.cfg.ls_time_limit,
                    three_opt_window=self.cfg.three_opt_window,
                )
                perturbed_cost = _tour_cost(perturbed, self._dist_matrix)
                if perturbed_cost <= best_cost:
                    best_tour = perturbed[:]
                    best_cost = perturbed_cost

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        return TSPResult(
            algorithm=self.name,
            tour=best_tour,
            tour_length=best_cost,
            elapsed_ms=elapsed_ms,
            iterations=len(history) - 1,
            params={
                "population_size": self.cfg.population_size,
                "max_iterations": self.cfg.max_iterations,
                "beta": self.cfg.beta,
            },
            history=history,
            seed=self.cfg.seed,
        )
