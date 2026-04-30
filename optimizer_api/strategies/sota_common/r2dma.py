"""
R²DMA — Resonance-Reinforced Destroy-and-Merge Algorithm (FAZ 2)

A memetic algorithm for TSP solving that uses a **resonance metric** between
parent solutions to decide how to combine them.  The resonance is a
6-dimensional composite measuring structural similarity across edge sets,
sub-tour sequences, Hamiltonian completeness, Shaw similarity, and
constraint satisfaction patterns.

Core Concept:
    * **High resonance (R >= 0.7)**: CONSTRUCTIVE mode — Build common
      edge skeleton + NN completion + moderate LS.
    * **Moderate resonance (0.3 <= R < 0.7)**: MODERATE mode — OX
      crossover + resonance bias + light LS.
    * **Low resonance (R < 0.3)**: DESTRUCTIVE mode — ALNS destroy/repair
      (Shaw / Worst removal + Regret / Greedy insertion) + moderate LS.

Algorithm Flow:
    1. MultiStartInitializer generates a diverse initial population.
    2. Pre-improve each initial solution with light local search.
    3. Compute initial resonance matrix for all pairs.
    4. Main loop (t = 1..T_max):
       a. For each individual Si, find best partner Sj with R >= theta.
       b. Adaptive theta: track success rates in segments, adjust.
       c. Crossover based on resonance level (constructive/moderate/destructive).
       d. SA acceptance + dissonance filter.
       e. Penalty manager update (for future CVRPTW extension).
       f. Resonance matrix update (successful children boost, unsuccessful reduce).
       g. Harmonic convergence: inject diversity if entropy drops.
    5. Final polish with full MultiLayerLS.

All internal tours use ``List[str]`` node names.  Only the final result is
converted to ``List[int]`` indices.
"""

import logging
import math
import random
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Tuple

from .acceptance_criteria import AcceptResult, SimulatedAnnealing
from .destroy_operators import (
    RandomRemoval,
    RelatedRemoval,
    ShawRemoval,
    WorstRemoval,
)
from .diversity_controller import DiversityController
from .multi_layer_ls import MultiLayerLS
from .multi_start_initializer import MultiStartInitializer
from .penalty_manager import PenaltyManager
from .repair_operators import GreedyInsertion, Regret2Insertion, Regret3Insertion

logger = logging.getLogger(__name__)


# ====================================================================== #
# Configuration
# ====================================================================== #


@dataclass
class R2DMAConfig:
    """All configurable parameters for R²DMA.

    Attributes:
        population_size: Number of solutions in the population.
        max_iterations: Main loop iteration count.
        resonance_weights: 6-tuple of weights for the resonance metric
            (E_common, S_sub, H_comp, Shaw_sim, TW_res, CAP_res).
        theta_base: Minimum resonance threshold for partner matching.
        segment_size: Window size for adaptive theta adjustment.
        alns_destroy_operators: Names of ALNS destroy operators.
        alns_repair_operators: Names of ALNS repair operators.
        remove_ratio_range: (min, max) fraction of nodes to remove.
        ls_constructive: LS intensity for constructive crossover children.
        ls_moderate: LS intensity for moderate crossover children.
        ls_destructive: LS intensity for destructive crossover children.
        ls_final: LS intensity for final polish.
        ls_time_limit: Per-individual LS time limit (seconds).
        sa_start_temp_factor: SA start temperature = best_cost * this factor.
        sa_end_temp: SA minimum temperature.
        sa_cooling_rate: SA geometric cooling factor per iteration.
        delta_threshold: Dissonance tolerance (fraction of parent cost).
        entropy_threshold: Entropy threshold for diversity injection.
        pulse_injection_rate: Fraction of population to inject.
        diversity_check_interval: Iterations between diversity checks.
        initial_alpha_tw: Initial time-window penalty weight.
        initial_alpha_cap: Initial capacity penalty weight.
        seed: Random seed for reproducibility.
    """

    population_size: int = 60
    max_iterations: int = 2000
    resonance_weights: Tuple[float, ...] = (0.25, 0.20, 0.15, 0.15, 0.15, 0.10)
    theta_base: float = 0.5
    segment_size: int = 100
    # ALNS
    alns_destroy_operators: Tuple[str, ...] = ("random", "worst", "shaw", "related")
    alns_repair_operators: Tuple[str, ...] = ("greedy", "regret2", "regret3")
    remove_ratio_range: Tuple[float, float] = (0.15, 0.30)
    # LS intensities
    ls_constructive: str = "moderate"
    ls_moderate: str = "light"
    ls_destructive: str = "moderate"
    ls_final: str = "full"
    ls_time_limit: float = 2.0
    # SA acceptance
    sa_start_temp_factor: float = 0.4
    sa_end_temp: float = 0.0001
    sa_cooling_rate: float = 0.9995
    # Dissonance
    delta_threshold: float = 0.02
    # Diversity
    entropy_threshold: float = 0.15
    pulse_injection_rate: float = 0.25
    diversity_check_interval: int = 50
    # Penalty
    initial_alpha_tw: float = 10.0
    initial_alpha_cap: float = 5.0
    # Misc
    seed: int = 42


# ====================================================================== #
# Result
# ====================================================================== #


@dataclass
class R2DMAResult:
    """Result of R²DMA optimization.

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
# R²DMA Solver
# ====================================================================== #


class R2DMA:
    """Resonance-Reinforced Destroy-and-Merge Algorithm.

    A memetic algorithm that measures structural *resonance* between
    solution pairs and selects the crossover strategy accordingly.

    Usage::

        r2dma = R2DMA(R2DMAConfig(population_size=60, max_iterations=2000))
        result = r2dma.solve(problem_instance)
        print(result.cost, result.gap)
    """

    def __init__(self, config: Optional[R2DMAConfig] = None) -> None:
        """Initialise R²DMA with optional configuration.

        Args:
            config: Configuration dataclass.  Uses defaults if ``None``.
        """
        self.cfg = config or R2DMAConfig()

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def solve(
        self,
        prob: Any,
        progress_callback: Optional[Callable[[int, float, float, str], None]] = None,
    ) -> R2DMAResult:
        """Solve a TSP problem instance.

        Args:
            prob: A ``ProblemInstance``-like object with attributes:
                  ``node_names``, ``dist_matrix``, ``cost_fn``, ``optimal``,
                  ``dimension``, and ``tour_cost``.
            progress_callback: Optional callable
                ``(iteration, best_cost, theta, mode) -> None``
                invoked after each main-loop iteration.

        Returns:
            :class:`R2DMAResult` with the best tour and statistics.
        """
        t_start = time.monotonic()
        rng = random.Random(self.cfg.seed)

        # ---- Build internal data structures ----
        node_names: List[str] = prob.node_names
        dm: Dict[str, Dict[str, float]] = self._build_str_distance_matrix(prob)
        waypoints = list(node_names)

        cost_fn: Callable[[List[str]], float] = self._make_cost_fn(dm)

        logger.info(
            "R²DMA starting: n=%d, pop=%d, iter=%d",
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
        population = [self._fix_tour(t, waypoints, dm) for t in population]

        # ---- Pre-improve with light LS ----
        population = self._pre_improve(population, cost_fn, rng)

        # ---- Evaluate costs ----
        pop_costs = [cost_fn(t) for t in population]

        # ---- Global best ----
        gbest_idx = int(min(range(len(pop_costs)), key=lambda i: pop_costs[i]))
        global_best: List[str] = list(population[gbest_idx])
        global_best_cost: float = pop_costs[gbest_idx]

        # ---- Compute initial resonance matrix ----
        resonance_matrix = self._compute_resonance_matrix(population, dm)

        # ---- SA acceptance criterion ----
        sa_start_temp = global_best_cost * self.cfg.sa_start_temp_factor
        sa = SimulatedAnnealing(
            start_temp=sa_start_temp,
            end_temp=self.cfg.sa_end_temp,
            cooling_rate=self.cfg.sa_cooling_rate,
            max_iteration=self.cfg.max_iterations,
        )

        # ---- Penalty manager (for CVRPTW extension) ----
        penalty_mgr = PenaltyManager(
            initial_alpha_tw=self.cfg.initial_alpha_tw,
            initial_alpha_cap=self.cfg.initial_alpha_cap,
        )

        # ---- Diversity controller ----
        diversity_ctrl = DiversityController()

        # ---- Adaptive theta ----
        theta = self.cfg.theta_base
        segment_results: List[bool] = []  # True = constructive child successful

        # ---- Stats ----
        stats: Dict[str, Any] = {
            "resonance_history": [],
            "mode_history": [],
            "cost_history": [],
            "theta_history": [],
            "improvement_log": [],
            "injection_count": 0,
            "constructive_count": 0,
            "moderate_count": 0,
            "destructive_count": 0,
            "sa_acceptances": 0,
            "sa_rejections": 0,
            "final_ls_improvement": 0.0,
            "theta_adjustments": 0,
        }

        # ================================================================ #
        # Main Loop
        # ================================================================ #
        for t in range(1, self.cfg.max_iterations + 1):
            prev_best = global_best_cost

            # ---- New offspring population ----
            offspring: List[List[str]] = []
            offspring_costs: List[float] = []

            # ---- Process each individual ----
            for i in range(len(population)):
                # Find best partner with R >= theta
                partner_idx = self._find_best_partner(i, resonance_matrix, theta)

                if partner_idx is None:
                    # No suitable partner; carry over with perturbation
                    child = self._random_perturbation(population[i], rng)
                    child = self._fix_tour(child, waypoints, dm)
                    child_cost = cost_fn(child)
                    mode = "carryover"
                else:
                    resonance = resonance_matrix[i][partner_idx]
                    parent1 = population[i]
                    parent2 = population[partner_idx]
                    parent_cost_worse = max(pop_costs[i], pop_costs[partner_idx])

                    if resonance >= 0.7:
                        # ---- CONSTRUCTIVE mode ----
                        child = self._crossover_constructive(
                            parent1, parent2, dm, rng, cost_fn
                        )
                        child = self._fix_tour(child, waypoints, dm)
                        child_cost = cost_fn(child)
                        # Apply moderate LS
                        child, child_cost, _ = MultiLayerLS.improve(
                            child, cost_fn, rng,
                            intensity=self.cfg.ls_constructive,
                            overall_time_limit=self.cfg.ls_time_limit,
                        )
                        stats["constructive_count"] += 1
                        mode = "constructive"

                    elif resonance >= 0.3:
                        # ---- MODERATE mode (OX crossover) ----
                        child = self._crossover_moderate(
                            parent1, parent2, rng, resonance
                        )
                        child = self._fix_tour(child, waypoints, dm)
                        child_cost = cost_fn(child)
                        # Apply light LS
                        child, child_cost, _ = MultiLayerLS.improve(
                            child, cost_fn, rng,
                            intensity=self.cfg.ls_moderate,
                            overall_time_limit=self.cfg.ls_time_limit,
                        )
                        stats["moderate_count"] += 1
                        mode = "moderate"

                    else:
                        # ---- DESTRUCTIVE mode (ALNS) ----
                        child = self._crossover_destructive(
                            population[i], dm, rng, cost_fn,
                            destroy_ops, repair_ops, waypoints,
                        )
                        child = self._fix_tour(child, waypoints, dm)
                        child_cost = cost_fn(child)
                        # Apply moderate LS
                        child, child_cost, _ = MultiLayerLS.improve(
                            child, cost_fn, rng,
                            intensity=self.cfg.ls_destructive,
                            overall_time_limit=self.cfg.ls_time_limit,
                        )
                        stats["destructive_count"] += 1
                        mode = "destructive"

                # ---- SA acceptance + dissonance filter ----
                accept_result = sa.decide(
                    current_cost=pop_costs[i],
                    new_cost=child_cost,
                    best_cost=global_best_cost,
                    iteration=t,
                    rng=rng,
                )

                # Dissonance filter: reject if child is much worse than both parents
                worse_parent_cost = max(pop_costs[i],
                                       pop_costs[partner_idx] if partner_idx is not None else pop_costs[i])
                delta_limit = worse_parent_cost * self.cfg.delta_threshold
                is_dissonant = child_cost > worse_parent_cost + delta_limit

                if accept_result.accepted and not is_dissonant:
                    offspring.append(child)
                    offspring_costs.append(child_cost)
                    stats["sa_acceptances"] += 1

                    # Track constructive offspring success for adaptive theta
                    if mode == "constructive":
                        is_success = child_cost < worse_parent_cost - 1e-10
                        segment_results.append(is_success)
                else:
                    # Keep parent
                    offspring.append(list(population[i]))
                    offspring_costs.append(pop_costs[i])
                    stats["sa_rejections"] += 1

            # ---- Update population ----
            population = offspring
            pop_costs = offspring_costs

            # ---- Update global best ----
            best_idx = int(min(range(len(pop_costs)), key=lambda i: pop_costs[i]))
            if pop_costs[best_idx] < global_best_cost - 1e-10:
                global_best = list(population[best_idx])
                global_best_cost = pop_costs[best_idx]

            # ---- Penalty manager update ----
            penalty_mgr.update(iteration=t, current_cost=global_best_cost, is_feasible=True)

            # ---- Resonance matrix update ----
            if t % max(1, self.cfg.segment_size // 4) == 0:
                resonance_matrix = self._compute_resonance_matrix(population, dm)

            # ---- Adaptive theta mechanism ----
            if len(segment_results) >= self.cfg.segment_size:
                success_rate = sum(1 for s in segment_results[-self.cfg.segment_size:] if s) / self.cfg.segment_size
                if success_rate > 0.6:
                    theta = max(0.2, theta - 0.05)
                    stats["theta_adjustments"] += 1
                elif success_rate < 0.3:
                    theta = min(0.8, theta + 0.05)
                    stats["theta_adjustments"] += 1
                # Trim segment_results to avoid unbounded growth
                segment_results = segment_results[-self.cfg.segment_size:]

            # ---- Periodic diversity check (harmonic convergence) ----
            if t % self.cfg.diversity_check_interval == 0:
                entropy = DiversityController.compute_population_entropy(population)
                if entropy < self.cfg.entropy_threshold:
                    inject_count = max(1, int(self.cfg.pulse_injection_rate * len(population)))
                    population = diversity_ctrl.inject_diverse_solutions(
                        population,
                        inject_count,
                        generator_func=lambda r: self._random_tour(waypoints, r),
                        rng=rng,
                    )
                    while len(population) > self.cfg.population_size:
                        population.pop()
                    while len(population) < self.cfg.population_size:
                        population.append(self._random_tour(waypoints, rng))
                    pop_costs = [cost_fn(t) for t in population]
                    stats["injection_count"] += inject_count
                    # Recompute resonance after injection
                    resonance_matrix = self._compute_resonance_matrix(population, dm)
                    logger.debug(
                        "Diversity pulse at iter %d: entropy=%.4f, injected %d",
                        t, entropy, inject_count,
                    )

            # ---- Record stats ----
            stats["cost_history"].append(global_best_cost)
            stats["theta_history"].append(theta)
            stats["mode_history"].append(mode if 'mode' in dir() else "unknown")

            # ---- Track improvements ----
            if global_best_cost < prev_best - 1e-10:
                stats["improvement_log"].append(
                    {"iter": t, "cost": global_best_cost, "theta": theta}
                )

            # ---- Progress callback ----
            if progress_callback is not None:
                progress_callback(t, global_best_cost, theta, mode)

            # ---- Time guard ----
            elapsed_s = time.monotonic() - t_start
            if elapsed_s > 600:
                logger.info("R²DMA time budget reached at iteration %d", t)
                break

        # ================================================================ #
        # Final Polish
        # ================================================================ #
        polished_tour, polished_cost, ls_stats = MultiLayerLS.improve(
            global_best,
            cost_fn,
            rng,
            intensity=self.cfg.ls_final,
            overall_time_limit=5.0,  # benchmark için kısaltıldı: 30s → 5s
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
        stats["theta_final"] = theta
        stats["mode_distribution"] = dict(Counter(stats["mode_history"]))
        penalty_state = penalty_mgr.get_state()
        stats["penalty_state"] = {
            "alpha_tw": penalty_state.alpha_tw,
            "alpha_cap": penalty_state.alpha_cap,
            "phase": penalty_state.phase,
        }

        logger.info(
            "R²DMA finished: cost=%d, gap=%.2f%%, time=%.0fms, iters=%d",
            best_cost_int,
            gap if not (gap != gap) else -1,  # handle NaN
            elapsed_ms,
            t,
        )

        return R2DMAResult(
            tour=best_int_tour,
            cost=best_cost_int,
            gap=gap,
            time_ms=elapsed_ms,
            iterations=t,
            stats=stats,
        )

    # ------------------------------------------------------------------ #
    # Resonance Metric (6-dimensional)
    # ------------------------------------------------------------------ #

    def _compute_resonance(
        self,
        tour1: List[str],
        tour2: List[str],
        dm: Dict[str, Dict[str, float]],
    ) -> float:
        """Compute the 6-dimensional resonance between two tours.

        R(P1,P2) = w1*E_common + w2*S_sub + w3*H_comp
                   + w4*Shaw_sim + w5*TW_res + w6*CAP_res

        Args:
            tour1: First tour (List[str]).
            tour2: Second tour (List[str]).
            dm: Str-keyed distance matrix.

        Returns:
            Resonance value in [0, 1].
        """
        w = self.cfg.resonance_weights
        assert len(w) == 6, "resonance_weights must have 6 elements"

        e_common = self._edge_similarity(tour1, tour2)
        s_sub = self._sequence_similarity(tour1, tour2)
        h_comp = self._hamiltonian_completeness(tour1, tour2)
        shaw_sim = self._shaw_similarity(tour1, tour2, dm)
        tw_res = self._tw_resonance()
        cap_res = self._capacity_resonance()

        resonance = (
            w[0] * e_common
            + w[1] * s_sub
            + w[2] * h_comp
            + w[3] * shaw_sim
            + w[4] * tw_res
            + w[5] * cap_res
        )

        return max(0.0, min(1.0, resonance))

    def _edge_similarity(self, tour1: List[str], tour2: List[str]) -> float:
        """Compute Jaccard similarity of edge sets.

        An edge is a directed pair (tour[i], tour[i+1]) plus the return
        edge (tour[-1], tour[0]).

        Args:
            tour1: First tour.
            tour2: Second tour.

        Returns:
            Jaccard index in [0, 1].
        """
        edges1 = set()
        if len(tour1) >= 2:
            for i in range(len(tour1) - 1):
                edges1.add((tour1[i], tour1[i + 1]))
            edges1.add((tour1[-1], tour1[0]))  # return edge

        edges2 = set()
        if len(tour2) >= 2:
            for i in range(len(tour2) - 1):
                edges2.add((tour2[i], tour2[i + 1]))
            edges2.add((tour2[-1], tour2[0]))  # return edge

        if not edges1 and not edges2:
            return 1.0
        if not edges1 or not edges2:
            return 0.0

        intersection = edges1 & edges2
        union = edges1 | edges2
        return len(intersection) / len(union)

    def _sequence_similarity(self, tour1: List[str], tour2: List[str]) -> float:
        """Compute LCS-based sub-tour similarity using SequenceMatcher.

        Args:
            tour1: First tour.
            tour2: Second tour.

        Returns:
            Normalised similarity ratio in [0, 1].
        """
        if not tour1 or not tour2:
            return 0.0
        matcher = SequenceMatcher(None, tour1, tour2)
        return matcher.ratio()

    def _hamiltonian_completeness(
        self, tour1: List[str], tour2: List[str]
    ) -> float:
        """Compute Hamiltonian completeness: common_edges / tour_length.

        Measures what fraction of the first tour's edges also appear in
        the second tour.

        Args:
            tour1: First tour.
            tour2: Second tour.

        Returns:
            Completeness ratio in [0, 1].
        """
        if len(tour1) < 2:
            return 1.0

        edges1 = set()
        for i in range(len(tour1) - 1):
            edges1.add((tour1[i], tour1[i + 1]))
        edges1.add((tour1[-1], tour1[0]))

        edges2 = set()
        for i in range(len(tour2) - 1):
            edges2.add((tour2[i], tour2[i + 1]))
        edges2.add((tour2[-1], tour2[0]))

        common = edges1 & edges2
        return len(common) / len(edges1)

    def _shaw_similarity(
        self,
        tour1: List[str],
        tour2: List[str],
        dm: Dict[str, Dict[str, float]],
    ) -> float:
        """Compute Shaw-like structural similarity between two tours.

        For each consecutive pair in tour1, find the most distance-similar
        pair in tour2 and aggregate.  Returns a value in [0, 1].

        Args:
            tour1: First tour.
            tour2: Second tour.
            dm: Str-keyed distance matrix.

        Returns:
            Similarity value in [0, 1].
        """
        if len(tour1) < 2 or len(tour2) < 2:
            return 0.5

        # Compute max distance in dm for normalisation
        max_dist = 0.0
        for a in dm:
            for b in dm:
                if dm[a][b] > max_dist:
                    max_dist = dm[a][b]
        if max_dist == 0.0:
            max_dist = 1.0

        # Extract consecutive pairs from each tour (as edges with distances)
        def _pair_distances(tour: List[str]) -> List[Tuple[str, str, float]]:
            pairs = []
            for i in range(len(tour) - 1):
                d = dm.get(tour[i], {}).get(tour[i + 1], 0.0)
                pairs.append((tour[i], tour[i + 1], d))
            # Return edge
            d = dm.get(tour[-1], {}).get(tour[0], 0.0)
            pairs.append((tour[-1], tour[0], d))
            return pairs

        pairs1 = _pair_distances(tour1)
        pairs2 = _pair_distances(tour2)

        if not pairs1 or not pairs2:
            return 0.5

        # For each pair in tour1, find the most similar pair in tour2
        # Similarity = 1 - normalised distance difference
        total_similarity = 0.0
        for a1, b1, d1 in pairs1:
            best_sim = 0.0
            for a2, b2, d2 in pairs2:
                # Structural similarity: same or reverse edge, plus distance proximity
                dist_diff = abs(d1 - d2) / max_dist
                edge_match = 0.0
                if (a1 == a2 and b1 == b2) or (a1 == b2 and b1 == a2):
                    edge_match = 1.0
                pair_sim = edge_match * 0.7 + (1.0 - dist_diff) * 0.3
                if pair_sim > best_sim:
                    best_sim = pair_sim
            total_similarity += best_sim

        return total_similarity / len(pairs1)

    @staticmethod
    def _tw_resonance() -> float:
        """Time-window satisfaction pattern similarity.

        For pure TSP (no time windows), returns 0.5 as default.

        Returns:
            0.5 (TSP has no TW constraints).
        """
        return 0.5

    @staticmethod
    def _capacity_resonance() -> float:
        """Capacity usage profile similarity.

        For pure TSP (no demands), returns 0.5 as default.

        Returns:
            0.5 (TSP has no capacity constraints).
        """
        return 0.5

    # ------------------------------------------------------------------ #
    # Resonance Matrix
    # ------------------------------------------------------------------ #

    def _compute_resonance_matrix(
        self,
        population: List[List[str]],
        dm: Dict[str, Dict[str, float]],
    ) -> List[List[float]]:
        """Compute pairwise resonance matrix for all population members.

        Args:
            population: List of tours.
            dm: Str-keyed distance matrix.

        Returns:
            N x N matrix of resonance values (diagonal = 1.0).
        """
        n = len(population)
        matrix: List[List[float]] = [[0.0] * n for _ in range(n)]
        for i in range(n):
            matrix[i][i] = 1.0
            for j in range(i + 1, n):
                r = self._compute_resonance(population[i], population[j], dm)
                matrix[i][j] = r
                matrix[j][i] = r
        return matrix

    def _find_best_partner(
        self,
        idx: int,
        resonance_matrix: List[List[float]],
        theta: float,
    ) -> Optional[int]:
        """Find the best partner for individual at *idx*.

        The best partner is the one with the highest resonance value
        that is >= theta.

        Args:
            idx: Index of the individual.
            resonance_matrix: Pairwise resonance matrix.
            theta: Current resonance threshold.

        Returns:
            Partner index, or ``None`` if no suitable partner found.
        """
        best_partner = None
        best_r = theta  # minimum threshold

        for j in range(len(resonance_matrix[idx])):
            if j == idx:
                continue
            r = resonance_matrix[idx][j]
            if r >= best_r:
                best_r = r
                best_partner = j

        return best_partner

    # ------------------------------------------------------------------ #
    # Crossover: CONSTRUCTIVE (high resonance, R >= 0.7)
    # ------------------------------------------------------------------ #

    def _crossover_constructive(
        self,
        parent1: List[str],
        parent2: List[str],
        dm: Dict[str, Dict[str, float]],
        rng: random.Random,
        cost_fn: Callable[[List[str]], float],
    ) -> List[str]:
        """Constructive crossover for high-resonance parents.

        1. Find common edges between parents.
        2. Build a skeleton from common edges.
        3. Complete the partial tour using NN-guided insertion.
        4. Caller applies MultiLayerLS(moderate).

        Args:
            parent1: First parent tour.
            parent2: Second parent tour.
            dm: Distance matrix.
            rng: Random instance.
            cost_fn: Cost callable.

        Returns:
            Child tour.
        """
        # Step 1: Find common edges
        edges1 = set()
        if len(parent1) >= 2:
            for i in range(len(parent1) - 1):
                edges1.add((parent1[i], parent1[i + 1]))
            edges1.add((parent1[-1], parent1[0]))

        edges2 = set()
        if len(parent2) >= 2:
            for i in range(len(parent2) - 1):
                edges2.add((parent2[i], parent2[i + 1]))
            edges2.add((parent2[-1], parent2[0]))

        common_edges = edges1 & edges2

        if not common_edges:
            # No common edges: fall back to moderate crossover
            return self._crossover_moderate(parent1, parent2, rng, 0.5)

        # Step 2: Build adjacency from common edges
        adj: Dict[str, List[str]] = {}
        for a, b in common_edges:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)

        # Build chain from common edges
        used_nodes: set = set()
        chain: List[str] = []

        # Find an endpoint (degree 1 in common edges)
        all_nodes = set(adj.keys())
        endpoints = [n for n in all_nodes if len(adj[n]) == 1]
        start = endpoints[0] if endpoints else next(iter(all_nodes))

        current = start
        while current is not None:
            chain.append(current)
            used_nodes.add(current)
            neighbours = [nb for nb in adj.get(current, []) if nb not in used_nodes]
            if neighbours:
                current = neighbours[0]
            else:
                current = None

        # Step 3: Complete with NN-guided insertion
        remaining = [n for n in parent1 if n not in used_nodes]
        # If some nodes are in parent2 but not parent1, add them too
        p2_extra = [n for n in parent2 if n not in used_nodes and n not in remaining]
        remaining.extend(p2_extra)

        if not chain and remaining:
            # Chain building failed; start with a random remaining node
            chain.append(remaining.pop(rng.randint(0, len(remaining) - 1)))

        while remaining:
            best_node = None
            best_dist = float("inf")
            # Try inserting at every position (both ends and best internal)
            for node in remaining:
                # Distance from end of chain
                d_end = dm.get(chain[-1], {}).get(node, float("inf"))
                # Distance from start of chain
                d_start = dm.get(chain[0], {}).get(node, float("inf"))
                best_d = min(d_end, d_start)

                if best_d < best_dist:
                    best_dist = best_d
                    best_node = node

            if best_node is None:
                best_node = remaining.pop(rng.randint(0, len(remaining) - 1))
            else:
                remaining.remove(best_node)

            # Insert at best end
            d_end = dm.get(chain[-1], {}).get(best_node, float("inf"))
            d_start = dm.get(chain[0], {}).get(best_node, float("inf"))

            if d_start < d_end:
                chain.insert(0, best_node)
            else:
                chain.append(best_node)

        return chain

    # ------------------------------------------------------------------ #
    # Crossover: MODERATE (moderate resonance, 0.3 <= R < 0.7)
    # ------------------------------------------------------------------ #

    def _crossover_moderate(
        self,
        parent1: List[str],
        parent2: List[str],
        rng: random.Random,
        resonance: float,
    ) -> List[str]:
        """OX (Order Crossover) with resonance bias.

        Takes a random segment from parent1, fills remaining positions
        from parent2 in order.  The segment size is biased by resonance
        (higher resonance → larger segment).

        Args:
            parent1: First parent tour.
            parent2: Second parent tour.
            rng: Random instance.
            resonance: Resonance value between parents.

        Returns:
            Child tour.
        """
        n = len(parent1)
        if n < 3:
            return list(parent1)

        # Segment size proportional to resonance (0.3..0.7 → ~20%..60%)
        seg_frac = 0.2 + (resonance - 0.3) / 0.4 * 0.4
        seg_size = max(2, min(n - 2, int(n * seg_frac)))

        # Select random segment from parent1
        start = rng.randint(0, n - 1)
        end = (start + seg_size) % n

        if start <= end:
            segment = parent1[start:end + 1]
        else:
            segment = parent1[start:] + parent1[:end + 1]

        segment_set = set(segment)

        # Fill remaining from parent2 in order
        remaining = [node for node in parent2 if node not in segment_set]

        # Combine: segment in place, fill rest
        if start <= end:
            child = remaining[:start] + segment + remaining[start:]
        else:
            # Wrap-around segment
            before = remaining[:start - len(segment)]
            child = parent1[:end + 1] + before + segment + remaining[start - len(segment):]
            # Simpler approach: rebuild from segment position
            child = list(segment)
            for node in remaining:
                # Insert at position that preserves parent2 order
                child.append(node)

        # Ensure all nodes are present
        child_set = set(child)
        all_nodes = set(parent1)
        missing = [n for n in all_nodes if n not in child_set]
        extra = [n for n in child if n not in all_nodes]
        child = [n for n in child if n in all_nodes] + missing

        return child

    # ------------------------------------------------------------------ #
    # Crossover: DESTRUCTIVE (low resonance, R < 0.3)
    # ------------------------------------------------------------------ #

    def _crossover_destructive(
        self,
        tour: List[str],
        dm: Dict[str, Dict[str, float]],
        rng: random.Random,
        cost_fn: Callable[[List[str]], float],
        destroy_ops: Dict[str, Any],
        repair_ops: Dict[str, Any],
        waypoints: List[str],
    ) -> List[str]:
        """Destructive crossover using ALNS destroy/repair.

        Apply Shaw/Worst removal (15-30% of tour) + Regret/Greedy repair.

        Args:
            tour: Current tour.
            dm: Distance matrix.
            rng: Random instance.
            cost_fn: Cost callable.
            destroy_ops: Dict of destroy operator instances.
            repair_ops: Dict of repair operator instances.
            waypoints: All nodes in the problem.

        Returns:
            Child tour.
        """
        n_tour = len(tour)
        n_destroy = max(2, int(n_tour * rng.uniform(*self.cfg.remove_ratio_range)))

        # Prefer Shaw or Worst removal for destructive mode
        preferred_destroy = ["shaw", "worst"]
        available_destroy = [n for n in preferred_destroy if n in destroy_ops]
        if not available_destroy:
            available_destroy = list(destroy_ops.keys())

        d_name = rng.choice(available_destroy)
        destroyer = destroy_ops[d_name]

        # Destroy
        removed, remaining = destroyer.destroy(tour, n_destroy, rng, distance_matrix=dm)

        # Prefer Regret-2 or Greedy repair
        preferred_repair = ["regret2", "greedy"]
        available_repair = [n for n in preferred_repair if n in repair_ops]
        if not available_repair:
            available_repair = list(repair_ops.keys())

        r_name = rng.choice(available_repair)
        repairer = repair_ops[r_name]

        # Repair
        child = repairer.repair(remaining, removed, distance_matrix=dm)

        return child

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
    # Perturbation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _random_perturbation(tour: List[str], rng: random.Random) -> List[str]:
        """Apply a random perturbation to a tour.

        Chooses uniformly among double-bridge, swap, or scramble.

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
    # Utility helpers (same as E²BSO)
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
