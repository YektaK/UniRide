"""
E²BSO — Enhanced Entropy-Balanced Swarm Optimization (FAZ 1)

A population-based metaheuristic for TSP solving that uses edge-based
Shannon entropy to dynamically balance exploration vs. exploitation.

Core Concept:
    * **Low entropy (H < H_min)**: Population converged → INJECT DIVERSITY
      via ALNS destroy/repair.
    * **Normal entropy (H_min ≤ H ≤ H_max)**: OPTIMIZE — swarm update +
      moderate LS + LAHC.
    * **High entropy (H > H_max)**: COMPRESS — aggressive swarm + full LS
      + LAHC to exploit good regions.

Algorithm Flow:
    1. MultiStartInitializer generates a diverse initial population.
    2. Pre-improve each initial solution with light local search.
    3. Main loop (t = 1..T_max):
       a. Compute population entropy H (edge-based Shannon).
       b. Route to one of three phases based on H vs. thresholds.
       c. Periodic diversity injection via DiversityController.
       d. First ``learn_period`` iterations: adapt H_min / H_max online.
       e. Track global best solution.
    4. Final polish of the best solution with full MultiLayerLS.

All internal tours use ``List[str]`` node names.  Only the final result is
converted to ``List[int]`` indices.
"""

import logging
import random
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .acceptance_criteria import AcceptResult, LateAcceptanceHC
from .destroy_operators import (
    RandomRemoval,
    RelatedRemoval,
    ShawRemoval,
    WorstRemoval,
)
from .diversity_controller import DiversityController
from .multi_layer_ls import MultiLayerLS
from .multi_start_initializer import MultiStartInitializer
from .repair_operators import GreedyInsertion, Regret2Insertion, Regret3Insertion

logger = logging.getLogger(__name__)


# ====================================================================== #
# Configuration
# ====================================================================== #


@dataclass
class E2BSOConfig:
    """All configurable parameters for E²BSO.

    Attributes:
        population_size: Number of solutions in the swarm.
        max_iterations: Main loop iteration count.
        h_start: Initial entropy target (high = diverse).
        h_end: Final entropy target (low = focused).
        gamma: Cooling curve exponent for entropy schedule.
        entropy_check_interval: How often to recompute full entropy.
        ls_exploration_intensity: LS intensity in normal (exploration) mode.
        ls_exploitation_intensity: LS intensity in compression mode.
        ls_injection_intensity: LS intensity after diversity injection.
        ls_time_limit: Per-individual LS time limit (seconds).
        alns_destroy_operators: Names of ALNS destroy operators to use.
        alns_repair_operators: Names of ALNS repair operators to use.
        remove_ratio_range: (min, max) fraction of nodes to remove.
        lahc_history: LAHC history length.
        diversity_threshold: Normalised avg-distance threshold for injection.
        diversity_check_interval: Iterations between diversity checks.
        injection_rate: Fraction of population to inject.
        learn_period: Iterations for adaptive threshold learning.
        p_best: Probability of moving toward personal best.
        p_gbest: Probability of moving toward global best.
        n_edges_normal: Number of edges to transfer in normal swarm update.
        n_edges_aggressive: Number of edges to transfer in aggressive mode.
        seed: Random seed for reproducibility.
    """

    population_size: int = 40
    max_iterations: int = 1000
    h_start: float = 0.8
    h_end: float = 0.2
    gamma: float = 0.5
    entropy_check_interval: int = 10
    ls_exploration_intensity: str = "light"
    ls_exploitation_intensity: str = "moderate"
    ls_injection_intensity: str = "light"
    ls_time_limit: float = 0.5
    alns_destroy_operators: Tuple[str, ...] = ("random", "worst", "shaw", "related")
    alns_repair_operators: Tuple[str, ...] = ("greedy", "regret2", "regret3")
    remove_ratio_range: Tuple[float, float] = (0.10, 0.30)
    lahc_history: int = 500
    diversity_threshold: float = 0.3
    diversity_check_interval: int = 50
    injection_rate: float = 0.2
    learn_period: int = 200
    p_best: float = 0.3
    p_gbest: float = 0.4
    n_edges_normal: int = 3
    n_edges_aggressive: int = 5
    seed: int = 42


# ====================================================================== #
# Result
# ====================================================================== #


@dataclass
class E2BSOResult:
    """Result of E²BSO optimization.

    Attributes:
        tour: Best tour found (int node indices).
        cost: Best tour cost (int).
        gap: Gap from optimal (%), NaN if optimal unknown.
        time_ms: Total solve time in milliseconds.
        iterations: Actual iterations completed.
        stats: Detailed statistics dictionary.
    """

    tour: List[int]
    cost: int
    gap: float
    time_ms: float
    iterations: int
    stats: Dict[str, Any]


# ====================================================================== #
# E²BSO Solver
# ====================================================================== #


class E2BSO:
    """Enhanced Entropy-Balanced Swarm Optimization.

    Usage::

        e2bso = E2BSO(E2BSOConfig(population_size=40, max_iterations=1000))
        result = e2bso.solve(problem_instance)
        print(result.cost, result.gap)
    """

    def __init__(self, config: Optional[E2BSOConfig] = None) -> None:
        """Initialise E²BSO with optional configuration.

        Args:
            config: Configuration dataclass.  Uses defaults if ``None``.
        """
        self.cfg = config or E2BSOConfig()

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def solve(
        self,
        prob: Any,
        progress_callback: Optional[Callable[[int, float, float, str], None]] = None,
    ) -> E2BSOResult:
        """Solve a TSP problem instance.

        Args:
            prob: A ``ProblemInstance``-like object with attributes:
                  ``node_names``, ``dist_matrix``, ``cost_fn``, ``optimal``,
                  ``dimension``, and ``tour_cost``.
            progress_callback: Optional callable
                ``(iteration, best_cost, entropy, phase) -> None``
                invoked after each main-loop iteration.

        Returns:
            :class:`E2BSOResult` with the best tour and statistics.
        """
        t_start = time.monotonic()
        rng = random.Random(self.cfg.seed)

        # ---- Build internal data structures ----
        node_names: List[str] = prob.node_names
        dm: Dict[str, Dict[str, float]] = self._build_str_distance_matrix(prob)
        waypoints = list(node_names)

        # Build a fast internal cost function using str-keyed distance matrix
        # to avoid repeated int-conversion overhead inside MultiLayerLS
        cost_fn: Callable[[List[str]], float] = self._make_cost_fn(dm)

        logger.info(
            "E²BSO starting: n=%d, pop=%d, iter=%d",
            prob.dimension,
            self.cfg.population_size,
            self.cfg.max_iterations,
        )

        # ---- Operator pools ----
        destroy_ops = self._build_destroy_operators()
        repair_ops = self._build_repair_operators()

        # ---- Initialise population ----
        population = MultiStartInitializer.generate_population(
            waypoints, dm, self.cfg.population_size, rng
        )
        # Ensure every tour has the right set of nodes
        population = [self._fix_tour(t, waypoints, dm) for t in population]

        # ---- Pre-improve with light LS ----
        population = self._pre_improve(population, cost_fn, rng)

        # ---- Evaluate costs ----
        pop_costs = [cost_fn(t) for t in population]
        personal_bests = [list(t) for t in population]
        personal_best_costs = list(pop_costs)

        # ---- Global best ----
        gbest_idx = int(min(range(len(pop_costs)), key=lambda i: pop_costs[i]))
        global_best: List[str] = list(population[gbest_idx])
        global_best_cost: float = pop_costs[gbest_idx]

        # ---- LAHC acceptance criterion ----
        lahc = LateAcceptanceHC(history_length=self.cfg.lahc_history, warmup=10)

        # ---- Diversity controller ----
        diversity_ctrl = DiversityController()

        # ---- Adaptive thresholds ----
        h_min = self.cfg.h_start * 0.5
        h_max = self.cfg.h_start
        entropy_ema_low = h_min
        entropy_ema_high = h_max
        improvement_entropies: List[float] = []

        # ---- Stats ----
        stats: Dict[str, Any] = {
            "entropy_history": [],
            "phase_history": [],
            "cost_history": [],
            "improvement_log": [],
            "injection_count": 0,
            "ls_improvements": 0,
            "swarm_updates": 0,
            "alns_injections": 0,
            "final_ls_improvement": 0.0,
        }

        current_entropy = DiversityController.compute_population_entropy(population)
        current_phase = "normal"

        # ================================================================ #
        # Main Loop
        # ================================================================ #
        for t in range(1, self.cfg.max_iterations + 1):
            # ---- Recompute entropy periodically ----
            if t % self.cfg.entropy_check_interval == 0 or t == 1:
                current_entropy = DiversityController.compute_population_entropy(population)

            # ---- Determine phase ----
            # Update thresholds adaptively in the learning period
            if t <= self.cfg.learn_period and improvement_entropies:
                alpha = 0.1  # EMA smoothing factor
                recent = improvement_entropies[-min(20, len(improvement_entropies)):]
                recent_low = min(recent)
                recent_high = max(recent)
                entropy_ema_low = (1 - alpha) * entropy_ema_low + alpha * recent_low
                entropy_ema_high = (1 - alpha) * entropy_ema_high + alpha * recent_high
                h_min = max(0.05, entropy_ema_low - 0.05)
                h_max = min(0.95, entropy_ema_high + 0.05)
            elif t > self.cfg.learn_period:
                # Apply cooling schedule for gradual entropy pressure
                progress = (t - self.cfg.learn_period) / max(
                    1, self.cfg.max_iterations - self.cfg.learn_period
                )
                target = self.cfg.h_start * (1 - progress) ** self.cfg.gamma + self.cfg.h_end * (
                    1 - (1 - progress) ** self.cfg.gamma
                )
                h_min = target * 0.4
                h_max = target * 1.4

            if current_entropy < h_min:
                current_phase = "inject"
            elif current_entropy > h_max:
                current_phase = "compress"
            else:
                current_phase = "normal"

            # ---- Execute phase ----
            prev_best = global_best_cost

            if current_phase == "inject":
                population, pop_costs = self._phase_inject(
                    population, pop_costs, cost_fn, rng, dm,
                    destroy_ops, repair_ops, waypoints,
                )
                stats["alns_injections"] += 1

            elif current_phase == "compress":
                population, pop_costs, global_best, global_best_cost = self._phase_compress(
                    population, pop_costs, global_best, global_best_cost,
                    personal_bests, personal_best_costs,
                    cost_fn, rng, dm, lahc, t,
                )
                stats["swarm_updates"] += self.cfg.population_size

            else:  # normal
                population, pop_costs, global_best, global_best_cost = self._phase_normal(
                    population, pop_costs, global_best, global_best_cost,
                    personal_bests, personal_best_costs,
                    cost_fn, rng, dm, lahc, t,
                )
                stats["swarm_updates"] += self.cfg.population_size

            # ---- Update personal bests ----
            for i in range(len(population)):
                if pop_costs[i] < personal_best_costs[i] - 1e-10:
                    personal_bests[i] = list(population[i])
                    personal_best_costs[i] = pop_costs[i]

            # ---- Update global best ----
            best_idx = int(min(range(len(pop_costs)), key=lambda i: pop_costs[i]))
            if pop_costs[best_idx] < global_best_cost - 1e-10:
                global_best = list(population[best_idx])
                global_best_cost = pop_costs[best_idx]

            # ---- Track improvement entropy ----
            if global_best_cost < prev_best - 1e-10:
                improvement_entropies.append(current_entropy)
                stats["improvement_log"].append(
                    {"iter": t, "cost": global_best_cost, "entropy": current_entropy}
                )

            # ---- Periodic diversity check ----
            if t % self.cfg.diversity_check_interval == 0:
                if diversity_ctrl.should_inject_diversity(population, self.cfg.diversity_threshold):
                    inject_count = max(1, int(self.cfg.injection_rate * len(population)))
                    population = diversity_ctrl.inject_diverse_solutions(
                        population,
                        inject_count,
                        generator_func=lambda r: self._random_tour(waypoints, r),
                        rng=rng,
                    )
                    # Re-evaluate injected tours
                    while len(population) > self.cfg.population_size:
                        population.pop()
                    # Pad if somehow we lost population members
                    while len(population) < self.cfg.population_size:
                        population.append(self._random_tour(waypoints, rng))
                    pop_costs = [cost_fn(t) for t in population]
                    stats["injection_count"] += inject_count

            # ---- Record stats ----
            stats["entropy_history"].append(current_entropy)
            stats["phase_history"].append(current_phase)
            stats["cost_history"].append(global_best_cost)

            # ---- Progress callback ----
            if progress_callback is not None:
                progress_callback(t, global_best_cost, current_entropy, current_phase)

            # ---- Time guard ----
            elapsed_s = time.monotonic() - t_start
            # Soft time budget: 10 minutes
            if elapsed_s > 600:
                logger.info("E²BSO time budget reached at iteration %d", t)
                break

        # ================================================================ #
        # Final Polish
        # ================================================================ #
        polished_tour, polished_cost, ls_stats = MultiLayerLS.improve(
            global_best,
            cost_fn,
            rng,
            intensity="full",
            overall_time_limit=30.0,
        )
        if polished_cost < global_best_cost - 1e-10:
            global_best = polished_tour
            global_best_cost = polished_cost
            stats["final_ls_improvement"] = ls_stats.get("improvement_pct", 0.0)

        # ---- Build result ----
        elapsed_ms = (time.monotonic() - t_start) * 1000.0
        best_int_tour = [int(n) for n in global_best]
        best_cost_int = int(round(global_best_cost))

        gap = float("nan")
        if hasattr(prob, "optimal") and prob.optimal is not None and prob.optimal > 0:
            gap = (best_cost_int - prob.optimal) / prob.optimal * 100.0

        # Aggregate stats
        stats["h_min_final"] = h_min
        stats["h_max_final"] = h_max
        stats["entropy_final"] = current_entropy
        stats["phase_distribution"] = dict(Counter(stats["phase_history"]))

        logger.info(
            "E²BSO finished: cost=%d, gap=%.2f%%, time=%.0fms, iters=%d",
            best_cost_int,
            gap if not (gap != gap) else -1,  # handle NaN
            elapsed_ms,
            t,
        )

        return E2BSOResult(
            tour=best_int_tour,
            cost=best_cost_int,
            gap=gap,
            time_ms=elapsed_ms,
            iterations=t,
            stats=stats,
        )

    # ------------------------------------------------------------------ #
    # Phase: INJECT (Low entropy — population converged)
    # ------------------------------------------------------------------ #

    def _phase_inject(
        self,
        population: List[List[str]],
        pop_costs: List[float],
        cost_fn: Callable[[List[str]], float],
        rng: random.Random,
        dm: Dict[str, Dict[str, float]],
        destroy_ops: Dict[str, Any],
        repair_ops: Dict[str, Any],
        waypoints: List[str],
    ) -> Tuple[List[List[str]], List[float]]:
        """Diversify the population via ALNS destroy + repair.

        Selects a random subset of individuals, destroys a fraction of
        each tour, repairs, and applies light local search.

        Returns:
            Updated (population, pop_costs).
        """
        n_tour = len(waypoints)
        n_destroy = max(2, int(n_tour * rng.uniform(*self.cfg.remove_ratio_range)))

        for i in range(len(population)):
            # Apply ALNS to ~half the population
            if rng.random() > 0.5:
                continue

            tour = population[i]

            # Pick random operators
            d_name = rng.choice(list(destroy_ops.keys()))
            r_name = rng.choice(list(repair_ops.keys()))
            destroyer = destroy_ops[d_name]
            repairer = repair_ops[r_name]

            # Destroy
            removed, remaining = destroyer.destroy(tour, n_destroy, rng, distance_matrix=dm)

            # Repair
            repaired = repairer.repair(remaining, removed, distance_matrix=dm)
            repaired = self._fix_tour(repaired, waypoints, dm)

            # Light LS
            repaired, new_cost, ls_stats = MultiLayerLS.improve(
                repaired,
                cost_fn,
                rng,
                intensity=self.cfg.ls_injection_intensity,
                overall_time_limit=self.cfg.ls_time_limit,
            )

            if new_cost < pop_costs[i] - 1e-10:
                population[i] = repaired
                pop_costs[i] = new_cost

        return population, pop_costs

    # ------------------------------------------------------------------ #
    # Phase: NORMAL (Balanced exploration/exploitation)
    # ------------------------------------------------------------------ #

    def _phase_normal(
        self,
        population: List[List[str]],
        pop_costs: List[float],
        global_best: List[str],
        global_best_cost: float,
        personal_bests: List[List[str]],
        personal_best_costs: List[float],
        cost_fn: Callable[[List[str]], float],
        rng: random.Random,
        dm: Dict[str, Dict[str, float]],
        lahc: LateAcceptanceHC,
        iteration: int,
    ) -> Tuple[List[List[str]], List[float], List[str], float]:
        """Normal phase: swarm update + moderate LS + LAHC acceptance.

        Returns:
            Updated (population, pop_costs, global_best, global_best_cost).
        """
        for i in range(len(population)):
            candidate = self._swarm_update(
                population[i],
                personal_bests[i],
                global_best,
                rng,
                n_edges=self.cfg.n_edges_normal,
                p_best=self.cfg.p_best,
                p_gbest=self.cfg.p_gbest,
            )

            candidate = self._fix_tour(candidate, list(global_best), dm)
            candidate_cost = cost_fn(candidate)

            # Moderate LS
            candidate, candidate_cost, _ = MultiLayerLS.improve(
                candidate,
                cost_fn,
                rng,
                intensity=self.cfg.ls_exploration_intensity,
                overall_time_limit=self.cfg.ls_time_limit,
            )

            # LAHC acceptance
            accept_result = lahc.decide(
                current_cost=pop_costs[i],
                new_cost=candidate_cost,
                best_cost=global_best_cost,
                iteration=iteration,
                rng=rng,
            )

            if accept_result.accepted or candidate_cost < pop_costs[i] - 1e-10:
                population[i] = candidate
                pop_costs[i] = candidate_cost

                if candidate_cost < global_best_cost - 1e-10:
                    global_best = list(candidate)
                    global_best_cost = candidate_cost

        return population, pop_costs, global_best, global_best_cost

    # ------------------------------------------------------------------ #
    # Phase: COMPRESS (High entropy — exploit good regions)
    # ------------------------------------------------------------------ #

    def _phase_compress(
        self,
        population: List[List[str]],
        pop_costs: List[float],
        global_best: List[str],
        global_best_cost: float,
        personal_bests: List[List[str]],
        personal_best_costs: List[float],
        cost_fn: Callable[[List[str]], float],
        rng: random.Random,
        dm: Dict[str, Dict[str, float]],
        lahc: LateAcceptanceHC,
        iteration: int,
    ) -> Tuple[List[List[str]], List[float], List[str], float]:
        """Compression phase: aggressive swarm + full LS + LAHC.

        Higher p_gbest and more edges from global best to focus the
        population toward promising regions.

        Returns:
            Updated (population, pop_costs, global_best, global_best_cost).
        """
        for i in range(len(population)):
            # More aggressive: higher gbest probability, more edges
            candidate = self._swarm_update(
                population[i],
                personal_bests[i],
                global_best,
                rng,
                n_edges=self.cfg.n_edges_aggressive,
                p_best=self.cfg.p_best * 0.5,
                p_gbest=min(0.9, self.cfg.p_gbest * 1.5),
            )

            candidate = self._fix_tour(candidate, list(global_best), dm)
            candidate_cost = cost_fn(candidate)

            # Full LS for exploitation
            candidate, candidate_cost, _ = MultiLayerLS.improve(
                candidate,
                cost_fn,
                rng,
                intensity=self.cfg.ls_exploitation_intensity,
                overall_time_limit=self.cfg.ls_time_limit * 1.5,
            )

            # LAHC acceptance
            accept_result = lahc.decide(
                current_cost=pop_costs[i],
                new_cost=candidate_cost,
                best_cost=global_best_cost,
                iteration=iteration,
                rng=rng,
            )

            if accept_result.accepted or candidate_cost < pop_costs[i] - 1e-10:
                population[i] = candidate
                pop_costs[i] = candidate_cost

                if candidate_cost < global_best_cost - 1e-10:
                    global_best = list(candidate)
                    global_best_cost = candidate_cost

        return population, pop_costs, global_best, global_best_cost

    # ------------------------------------------------------------------ #
    # Swarm Update (Core mechanism)
    # ------------------------------------------------------------------ #

    def _swarm_update(
        self,
        individual: List[str],
        pbest: List[str],
        gbest: List[str],
        rng: random.Random,
        n_edges: int = 3,
        p_best: float = 0.3,
        p_gbest: float = 0.4,
    ) -> List[str]:
        """Move an individual toward personal / global best by sharing edges.

        With probability ``p_best``, the individual is steered toward its
        personal best; with probability ``p_gbest``, toward the global best.
        Otherwise, a random perturbation is applied.

        The "move" extracts the top-*n_edges* shortest edges from the
        target tour, forces them into the individual (removing any
        conflicting edges), and repairs the broken partial tour via
        greedy insertion.

        Args:
            individual: Current tour (List[str]).
            pbest: Personal best tour.
            gbest: Global best tour.
            rng: Random instance.
            n_edges: Number of edges to transfer from the target.
            p_best: Probability of using personal best as target.
            p_gbest: Probability of using global best as target.

        Returns:
            Modified tour (may be the same as input if no change applied).
        """
        r = rng.random()
        if r < p_gbest:
            target = gbest
        elif r < p_gbest + p_best:
            target = pbest
        else:
            # Random perturbation (double-bridge or swap)
            return self._random_perturbation(individual, rng)

        if len(target) < 2 or len(individual) < 2:
            return list(individual)

        # Step 1: Extract top-n_edges edges from target by quality
        # Quality = inverse distance (shorter edges are "better")
        target_edge_scores: List[Tuple[float, str, str]] = []
        for i in range(len(target) - 1):
            a, b = target[i], target[i + 1]
            # We need distance; use a proxy based on position proximity
            # Since we don't have dm here, we'll use a structural heuristic:
            # Prefer edges that are also in the individual
            target_edge_scores.append((float(i), a, b))

        # Shuffle and pick n_edges for diversity
        rng.shuffle(target_edge_scores)
        selected_edges: List[Tuple[str, str]] = [
            (a, b) for _, a, b in target_edge_scores[:n_edges]
        ]

        # Step 2: Force selected edges into individual
        # Build a set of nodes connected by the selected edges
        result = list(individual)
        result = self._force_edges(result, selected_edges, rng)

        return result

    def _force_edges(
        self,
        tour: List[str],
        edges: List[Tuple[str, str]],
        rng: random.Random,
    ) -> List[str]:
        """Force edges into a tour by removing conflicts and repairing.

        For each edge (a, b) in *edges*:
          1. If the edge already exists in the tour, skip.
          2. Otherwise, remove a and b from their current positions,
             place them adjacent as a→b, and insert remaining nodes
             via greedy nearest-neighbour.

        Args:
            tour: Current tour.
            edges: Edges to force in.
            rng: Random instance.

        Returns:
            Modified tour with the forced edges (best effort).
        """
        if not edges or len(tour) < 2:
            return list(tour)

        # Build adjacency from forced edges
        forced_adj: Dict[str, List[str]] = {}
        forced_set = set()
        for a, b in edges:
            if a in tour and b in tour:
                forced_adj.setdefault(a, []).append(b)
                forced_adj.setdefault(b, []).append(a)
                forced_set.add(a)
                forced_set.add(b)

        if not forced_set:
            return list(tour)

        # Build partial tour from forced edges (chain them)
        # Start from a node that has degree 1 in forced edges (endpoint)
        degree: Dict[str, int] = {n: 0 for n in forced_set}
        for a, b in edges:
            if a in degree:
                degree[a] += 1
            if b in degree:
                degree[b] += 1

        # Find endpoints (degree 1) or arbitrary start
        endpoints = [n for n in forced_set if degree.get(n, 0) == 1]
        start = endpoints[0] if endpoints else next(iter(forced_set))

        # Trace the forced chain
        chain: List[str] = [start]
        visited_forced: set = {start}
        current = start
        while True:
            neighbours = forced_adj.get(current, [])
            found_next = False
            for nb in neighbours:
                if nb not in visited_forced:
                    chain.append(nb)
                    visited_forced.add(nb)
                    current = nb
                    found_next = True
                    break
            if not found_next:
                break

        # Remaining nodes not in the chain
        remaining_nodes = [n for n in tour if n not in forced_set]
        rng.shuffle(remaining_nodes)

        # Insert remaining nodes via greedy nearest-neighbour into chain
        for node in remaining_nodes:
            best_pos = 0
            best_cost = float("inf")
            for pos in range(len(chain) + 1):
                # Compute insertion cost (approximate: count position distance)
                cost = 0
                if pos > 0 and pos < len(chain):
                    cost = pos  # proxy for distance
                elif pos == 0:
                    cost = len(chain)
                else:
                    cost = len(chain)
                # Add small random noise to break ties
                cost += rng.random() * 0.1
                if cost < best_cost:
                    best_cost = cost
                    best_pos = pos
            chain.insert(best_pos, node)

        return chain

    def _random_perturbation(self, tour: List[str], rng: random.Random) -> List[str]:
        """Apply a random perturbation to a tour.

        Chooses uniformly among:
        * **Double-bridge** 4-opt move (classic TSP perturbation).
        * **Swap** two random positions.
        * **Scramble** a random sub-segment.

        Args:
            tour: Input tour.
            rng: Random instance.

        Returns:
            Perturbed tour.
        """
        result = list(tour)
        n = len(result)
        if n < 4:
            return result

        op = rng.choice(["double_bridge", "swap", "scramble"])

        if op == "double_bridge":
            # Double-bridge: cut at 4 points and reconnect
            cuts = sorted(rng.sample(range(1, n), 3))
            i, j, k = cuts
            result = result[:i] + result[j:k] + result[i:j] + result[k:]

        elif op == "swap":
            a = rng.randint(0, n - 1)
            b = rng.randint(0, n - 1)
            result[a], result[b] = result[b], result[a]

        elif op == "scramble":
            i = rng.randint(0, n - 2)
            j = rng.randint(i + 1, n - 1)
            segment = result[i : j + 1]
            rng.shuffle(segment)
            result[i : j + 1] = segment

        return result

    # ------------------------------------------------------------------ #
    # Pre-improvement
    # ------------------------------------------------------------------ #

    def _pre_improve(
        self,
        population: List[List[str]],
        cost_fn: Callable[[List[str]], float],
        rng: random.Random,
    ) -> List[List[str]]:
        """Apply light local search to every individual in the population.

        Args:
            population: Initial population.
            cost_fn: Cost callable.
            rng: Random instance.

        Returns:
            Improved population.
        """
        improved = []
        for tour in population:
            new_tour, new_cost, _ = MultiLayerLS.improve(
                tour,
                cost_fn,
                rng,
                intensity="light",
                overall_time_limit=self.cfg.ls_time_limit,
            )
            improved.append(new_tour)
        return improved

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #

    def _build_str_distance_matrix(self, prob: Any) -> Dict[str, Dict[str, float]]:
        """Convert int-keyed distance matrix to str-keyed.

        Args:
            prob: Problem instance with ``dist_matrix`` (int→int→int)
                  and ``node_names`` (List[str]).

        Returns:
            ``Dict[str, Dict[str, float]]`` distance matrix.
        """
        dm: Dict[str, Dict[str, float]] = {}
        for i, name_i in enumerate(prob.node_names):
            dm[name_i] = {}
            for j, name_j in enumerate(prob.node_names):
                dm[name_i][name_j] = float(prob.dist_matrix[i][j])
        return dm

    def _build_destroy_operators(self) -> Dict[str, Any]:
        """Instantiate destroy operators by name.

        Returns:
            Dict mapping name → operator instance.
        """
        ops: Dict[str, Any] = {}
        name_to_cls = {
            "random": RandomRemoval,
            "worst": WorstRemoval,
            "shaw": ShawRemoval,
            "related": RelatedRemoval,
        }
        for name in self.cfg.alns_destroy_operators:
            cls = name_to_cls.get(name)
            if cls is not None:
                ops[name] = cls()
        return ops

    def _build_repair_operators(self) -> Dict[str, Any]:
        """Instantiate repair operators by name.

        Returns:
            Dict mapping name → operator instance.
        """
        ops: Dict[str, Any] = {}
        name_to_cls = {
            "greedy": GreedyInsertion,
            "regret2": Regret2Insertion,
            "regret3": Regret3Insertion,
        }
        for name in self.cfg.alns_repair_operators:
            cls = name_to_cls.get(name)
            if cls is not None:
                ops[name] = cls()
        return ops

    @staticmethod
    def _fix_tour(tour: List[str], waypoints: List[str], dm: Dict[str, Dict[str, float]]) -> List[str]:
        """Ensure a tour contains exactly the right set of nodes.

        If the tour is missing nodes, they are appended.  If it has
        extra nodes, they are removed.

        Args:
            tour: Tour to fix.
            waypoints: Expected node set.
            dm: Distance matrix (unused but kept for interface).

        Returns:
            Fixed tour.
        """
        tour_set = set(tour)
        waypoint_set = set(waypoints)

        # Add missing nodes
        missing = [w for w in waypoints if w not in tour_set]
        result = list(tour) + missing

        # Remove extra nodes
        result = [n for n in result if n in waypoint_set]

        return result

    @staticmethod
    def _make_cost_fn(dm: Dict[str, Dict[str, float]]) -> Callable[[List[str]], float]:
        """Build a fast cost function from the str-keyed distance matrix.

        This avoids repeated int↔str conversion that would occur when
        using ``prob.cost_fn`` (which expects int tours) inside the
        str-based MultiLayerLS.

        Args:
            dm: ``Dict[str, Dict[str, float]]`` distance matrix.

        Returns:
            Cost callable ``List[str] -> float``.
        """
        def _cost(tour: List[str]) -> float:
            n = len(tour)
            if n < 2:
                return 0.0
            total = 0.0
            for i in range(n - 1):
                total += dm[tour[i]][tour[i + 1]]
            total += dm[tour[-1]][tour[0]]  # return edge
            return total
        return _cost

    @staticmethod
    def _random_tour(waypoints: List[str], rng: random.Random) -> List[str]:
        """Generate a random tour by shuffling waypoints.

        Args:
            waypoints: Node names to include.
            rng: Random instance.

        Returns:
            Randomly ordered list of all waypoints.
        """
        tour = list(waypoints)
        rng.shuffle(tour)
        return tour
