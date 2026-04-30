"""
P-AOEA — Production Adaptive Operator Evolution Algorithm (FAZ 3)

A meta-evolutionary algorithm for TSP solving where each solution in the
population carries an associated **Operator Genome** — a strategy vector
encoding which destroy, repair, and acceptance operators to use, along
with their weights and parameters.  Genomes themselves evolve over time
based on their success rates.

Core Concept:
    * Each individual **Si** carries a genome **Gi** that controls which
      destroy operator, repair operator, and acceptance criterion to apply.
    * Genomes **compete**: successful genomes are selected, crossed over,
      and mutated to produce offspring strategies.
    * **Adaptive destroy intensity** transitions from broad exploration
      (30-40 % removal) in early iterations to fine-tuning (10-15 %) late.
    * **Structured injection**: new genomes are mutations of the best
      existing genomes (90 %) with a small fully-random fraction (10 %).

Algorithm Flow:
    1. MultiStartInitializer generates an initial solution population.
    2. Pre-improve each solution with light local search.
    3. Create a population of operator genomes (randomly initialised).
    4. Main loop (t = 1 .. T_max):
       a. For each individual Si with genome Gi:
          - Compute adaptive destroy intensity based on progress.
          - Apply Gi's weighted-random destroy operator.
          - Apply Gi's weighted-random repair operator.
          - Apply MultiLayerLS with Gi's intensity setting.
          - Accept / reject using Gi's acceptance criterion.
          - Track success → update Gi fitness.
       b. Every *meta_evolution_interval* iterations:
          - Tournament selection of top genomes.
          - Crossover: combine operator sets from two parents.
          - Mutate: swap / add / remove operators, mutate weights.
          - Inject structured new genomes (mutations of best + 10 % random).
          - Replace worst genomes with offspring.
       c. Periodic diversity check via DiversityController.
       d. PenaltyManager update.
       e. Track global best.
    5. Final polish with full MultiLayerLS.

All internal tours use ``List[str]`` node names.  Only the final result
is converted to ``List[int]`` indices.
"""

import logging
import math
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .acceptance_criteria import (
    AcceptResult,
    AcceptanceCriterion,
    LateAcceptanceHC,
    RecordToRecordTravel,
    SimulatedAnnealing,
)
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
class PAOEAConfig:
    """All configurable parameters for P-AOEA.

    Attributes:
        population_size: Number of solution individuals.
        max_iterations: Main loop iteration count.
        genome_population_size: Number of operator genomes.
        meta_evolution_interval: Evolve genomes every N iterations.
        tournament_size: Individuals per tournament selection round.
        crossover_rate: Probability of performing genome crossover.
        mutation_rate: Probability of mutating a genome gene.
        genome_injection_rate: Fraction of genomes replaced each evolution.
        destroy_ops_pool: Available destroy operator names.
        repair_ops_pool: Available repair operator names.
        acceptance_types: Available acceptance criterion names.
        ls_time_limit: Per-individual LS time limit in seconds.
        ls_normal_intensity: LS intensity for normal iterations.
        ls_aggressive_intensity: LS intensity for late-stage tuning.
        remove_ratio_range: (min, max) fraction of nodes to remove.
        sa_start_temp_factor: SA start temperature = best_cost * this.
        sa_end_temp: SA minimum temperature.
        sa_cooling_rate: SA geometric cooling factor per iteration.
        entropy_threshold: Entropy threshold for diversity injection.
        diversity_check_interval: Iterations between diversity checks.
        diversity_injection_rate: Fraction of population to inject.
        initial_alpha_tw: Initial time-window penalty weight.
        initial_alpha_cap: Initial capacity penalty weight.
        seed: Random seed for reproducibility.
    """

    population_size: int = 50
    max_iterations: int = 1500
    genome_population_size: int = 15
    meta_evolution_interval: int = 100
    tournament_size: int = 3
    crossover_rate: float = 0.7
    mutation_rate: float = 0.3
    genome_injection_rate: float = 0.2
    destroy_ops_pool: Tuple[str, ...] = ("random", "worst", "shaw", "related")
    repair_ops_pool: Tuple[str, ...] = ("greedy", "regret2", "regret3")
    acceptance_types: Tuple[str, ...] = ("sa", "lahc", "rtr")
    ls_time_limit: float = 1.0
    ls_normal_intensity: str = "light"
    ls_aggressive_intensity: str = "moderate"
    remove_ratio_range: Tuple[float, float] = (0.10, 0.40)
    sa_start_temp_factor: float = 0.4
    sa_end_temp: float = 0.0001
    sa_cooling_rate: float = 0.9995
    entropy_threshold: float = 0.15
    diversity_check_interval: int = 50
    diversity_injection_rate: float = 0.2
    initial_alpha_tw: float = 10.0
    initial_alpha_cap: float = 5.0
    seed: int = 42


# ====================================================================== #
# Operator Genome
# ====================================================================== #


@dataclass
class OperatorGenome:
    """A strategy genome encoding an operator configuration.

    Each genome specifies which destroy / repair / acceptance operators
    an individual should use, with associated selection weights.  The
    genome evolves over time based on the success rate of solutions
    that carry it.

    Attributes:
        destroy_ops: Names of destroy operators in this genome.
        repair_ops: Names of repair operators in this genome.
        acceptance_type: Name of the acceptance criterion.
        destroy_weights: Selection weights for each destroy operator.
        repair_weights: Selection weights for each repair operator.
        destroy_intensity: Custom destroy intensity override (0 means
            use the global adaptive intensity).
        ls_intensity: MultiLayerLS intensity string.
        fitness: Accumulated fitness score (higher is better).
        age: Number of iterations this genome has existed.
        success_count: Number of successful improvements.
        total_trials: Total number of times the genome was applied.
    """

    destroy_ops: List[str] = field(default_factory=lambda: ["random", "worst"])
    repair_ops: List[str] = field(default_factory=lambda: ["greedy", "regret2"])
    acceptance_type: str = "sa"
    destroy_weights: List[float] = field(default_factory=lambda: [1.0, 1.0])
    repair_weights: List[float] = field(default_factory=lambda: [1.0, 1.0])
    destroy_intensity: float = 0.0  # 0 = use adaptive
    ls_intensity: str = "light"
    fitness: float = 0.0
    age: int = 0
    success_count: int = 0
    total_trials: int = 0

    # ------------------------------------------------------------------ #
    # Derived helpers
    # ------------------------------------------------------------------ #

    def success_rate(self) -> float:
        """Return the observed success rate of this genome.

        Returns:
            Fraction of trials that resulted in improvement, or 0.0
            if the genome has not been tried yet.
        """
        if self.total_trials == 0:
            return 0.0
        return self.success_count / self.total_trials

    def record_trial(self, improved: bool) -> None:
        """Record the outcome of one application of this genome.

        Args:
            improved: Whether the genome produced a cost improvement.
        """
        self.total_trials += 1
        if improved:
            self.success_count += 1
            self.fitness += 1.0

    def normalize_weights(self) -> None:
        """Normalize destroy and repair weights to sum to 1.0.

        If all weights are zero, they are set to uniform.  This is a
        no-op if the weights are already valid.
        """
        self.destroy_weights = self._normalize(self.destroy_weights, len(self.destroy_ops))
        self.repair_weights = self._normalize(self.repair_weights, len(self.repair_ops))

    @staticmethod
    def _normalize(weights: List[float], n: int) -> List[float]:
        """Normalize a weight vector to sum to 1.0.

        Args:
            weights: Raw weight values.
            n: Expected length of the output vector.

        Returns:
            Normalized weight list of length *n*.
        """
        w = list(weights[:n])
        while len(w) < n:
            w.append(1.0)
        total = sum(w)
        if total < 1e-12:
            return [1.0 / n] * n
        return [x / total for x in w]

    def select_destroy(self, rng: random.Random) -> str:
        """Select a destroy operator by weighted random choice.

        Args:
            rng: Seeded random generator.

        Returns:
            Name of the selected destroy operator.
        """
        if not self.destroy_ops:
            return "random"
        return rng.choices(self.destroy_ops, weights=self.destroy_weights, k=1)[0]

    def select_repair(self, rng: random.Random) -> str:
        """Select a repair operator by weighted random choice.

        Args:
            rng: Seeded random generator.

        Returns:
            Name of the selected repair operator.
        """
        if not self.repair_ops:
            return "greedy"
        return rng.choices(self.repair_ops, weights=self.repair_weights, k=1)[0]


# ====================================================================== #
# Result
# ====================================================================== #


@dataclass
class PAOEAResult:
    """Result of P-AOEA optimization.

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
# P-AOEA Solver
# ====================================================================== #


class PAOEA:
    """Production Adaptive Operator Evolution Algorithm.

    A meta-evolutionary algorithm where each solution carries an
    *Operator Genome* that determines which destroy / repair / acceptance
    operators to apply.  Genomes evolve via tournament selection,
    crossover, and mutation based on their empirical success rates.

    Usage::

        paoea = PAOEA(PAOEAConfig(population_size=50, max_iterations=1500))
        result = paoea.solve(problem_instance)
        print(result.cost, result.gap)
    """

    def __init__(self, config: Optional[PAOEAConfig] = None) -> None:
        """Initialise P-AOEA with optional configuration.

        Args:
            config: Configuration dataclass.  Uses defaults if ``None``.
        """
        self.cfg = config or PAOEAConfig()

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def solve(
        self,
        prob: Any,
        progress_callback: Optional[Callable[[int, float, float, str], None]] = None,
    ) -> PAOEAResult:
        """Solve a TSP problem instance.

        Args:
            prob: A ``ProblemInstance``-like object with attributes:
                  ``node_names``, ``dist_matrix``, ``cost_fn``, ``optimal``,
                  ``dimension``, and ``tour_cost``.
            progress_callback: Optional callable
                ``(iteration, best_cost, avg_genome_fitness, phase) -> None``
                invoked after each main-loop iteration.

        Returns:
            :class:`PAOEAResult` with the best tour and statistics.
        """
        t_start = time.monotonic()
        rng = random.Random(self.cfg.seed)

        # ---- Build internal data structures ----
        node_names: List[str] = prob.node_names
        dm: Dict[str, Dict[str, float]] = self._build_str_distance_matrix(prob)
        waypoints = list(node_names)

        cost_fn: Callable[[List[str]], float] = self._make_cost_fn(dm)

        logger.info(
            "P-AOEA starting: n=%d, pop=%d, genomes=%d, iter=%d",
            prob.dimension,
            self.cfg.population_size,
            self.cfg.genome_population_size,
            self.cfg.max_iterations,
        )

        # ---- Operator pools ----
        destroy_ops = self._build_destroy_operators()
        repair_ops = self._build_repair_operators()

        # ---- Initialise solution population ----
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

        # ---- Initialise genome population ----
        genomes = self._initialise_genomes(rng)

        # ---- Assign genomes to individuals (round-robin) ----
        individual_genomes: List[OperatorGenome] = []
        for i in range(self.cfg.population_size):
            individual_genomes.append(genomes[i % len(genomes)])

        # ---- SA acceptance instance (used when genome says "sa") ----
        sa_start_temp = global_best_cost * self.cfg.sa_start_temp_factor
        sa_acceptance = SimulatedAnnealing(
            start_temp=sa_start_temp,
            end_temp=self.cfg.sa_end_temp,
            cooling_rate=self.cfg.sa_cooling_rate,
            max_iteration=self.cfg.max_iterations,
        )

        # ---- LAHC acceptance instance (used when genome says "lahc") ----
        lahc_acceptance = LateAcceptanceHC(history_length=500, warmup=10)

        # ---- RTR acceptance instance (used when genome says "rtr") ----
        rtr_acceptance = RecordToRecordTravel(
            initial_deviation=global_best_cost * self.cfg.sa_start_temp_factor,
            min_deviation=0.001,
            decay_rate=self.cfg.sa_cooling_rate,
        )

        # ---- Penalty manager (for CVRPTW extension) ----
        penalty_mgr = PenaltyManager(
            initial_alpha_tw=self.cfg.initial_alpha_tw,
            initial_alpha_cap=self.cfg.initial_alpha_cap,
        )

        # ---- Diversity controller ----
        diversity_ctrl = DiversityController()

        # ---- Stats ----
        stats: Dict[str, Any] = {
            "cost_history": [],
            "genome_fitness_history": [],
            "destroy_operator_usage": Counter(),
            "repair_operator_usage": Counter(),
            "acceptance_usage": Counter(),
            "improvement_log": [],
            "injection_count": 0,
            "meta_evolution_count": 0,
            "destroy_success_rates": {},
            "repair_success_rates": {},
            "avg_genome_age_history": [],
            "genome_diversity_history": [],
            "final_ls_improvement": 0.0,
        }

        current_phase = "exploration"

        # ================================================================ #
        # Main Loop
        # ================================================================ #
        for t in range(1, self.cfg.max_iterations + 1):
            prev_best = global_best_cost
            progress = t / self.cfg.max_iterations

            # ---- Determine search phase based on progress ----
            if progress < 0.30:
                current_phase = "exploration"
            elif progress < 0.70:
                current_phase = "balanced"
            else:
                current_phase = "exploitation"

            # ---- Compute adaptive destroy intensity ----
            adaptive_intensity = self._adaptive_destroy_intensity(progress)

            # ---- Process each individual ----
            for i in range(len(population)):
                genome = individual_genomes[i]

                # Determine actual destroy intensity
                if genome.destroy_intensity > 0:
                    d_intensity = genome.destroy_intensity
                else:
                    d_intensity = adaptive_intensity

                n_tour = len(population[i])
                n_destroy = max(2, int(n_tour * d_intensity))

                # Select destroy operator
                d_name = genome.select_destroy(rng)
                stats["destroy_operator_usage"][d_name] += 1
                destroyer = destroy_ops.get(d_name)
                if destroyer is None:
                    d_name = "random"
                    destroyer = destroy_ops["random"]

                # Destroy
                removed, remaining = destroyer.destroy(
                    population[i], n_destroy, rng, distance_matrix=dm
                )

                # Select repair operator
                r_name = genome.select_repair(rng)
                stats["repair_operator_usage"][r_name] += 1
                repairer = repair_ops.get(r_name)
                if repairer is None:
                    r_name = "greedy"
                    repairer = repair_ops["greedy"]

                # Repair
                candidate = repairer.repair(remaining, removed, distance_matrix=dm)
                candidate = self._fix_tour(candidate, waypoints, dm)
                candidate_cost = cost_fn(candidate)

                # Apply local search with genome's intensity
                ls_int = genome.ls_intensity
                if current_phase == "exploitation" and ls_int == "light":
                    ls_int = self.cfg.ls_normal_intensity

                candidate, candidate_cost, _ = MultiLayerLS.improve(
                    candidate,
                    cost_fn,
                    rng,
                    intensity=ls_int,
                    overall_time_limit=self.cfg.ls_time_limit,
                )

                # Accept / reject using genome's acceptance criterion
                accept_result = self._genome_accept(
                    genome,
                    pop_costs[i],
                    candidate_cost,
                    global_best_cost,
                    t,
                    rng,
                    sa_acceptance,
                    lahc_acceptance,
                    rtr_acceptance,
                )

                stats["acceptance_usage"][genome.acceptance_type] += 1

                improved = candidate_cost < pop_costs[i] - 1e-10
                genome.record_trial(improved)
                genome.age += 1

                if accept_result.accepted or improved:
                    population[i] = candidate
                    pop_costs[i] = candidate_cost

                    if candidate_cost < global_best_cost - 1e-10:
                        global_best = list(candidate)
                        global_best_cost = candidate_cost

            # ---- Update global best ----
            best_idx = int(min(range(len(pop_costs)), key=lambda i: pop_costs[i]))
            if pop_costs[best_idx] < global_best_cost - 1e-10:
                global_best = list(population[best_idx])
                global_best_cost = pop_costs[best_idx]

            # ---- Penalty manager update ----
            penalty_mgr.update(iteration=t, current_cost=global_best_cost, is_feasible=True)

            # ---- Meta-evolution of genomes ----
            if t % self.cfg.meta_evolution_interval == 0:
                genomes = self._meta_evolve(genomes, rng, t)
                # Re-assign genomes to individuals
                individual_genomes = []
                for i in range(self.cfg.population_size):
                    individual_genomes.append(genomes[i % len(genomes)])
                stats["meta_evolution_count"] += 1
                logger.debug(
                    "Meta-evolution at iter %d: %d genomes evolved",
                    t, len(genomes),
                )

            # ---- Periodic diversity check ----
            if t % self.cfg.diversity_check_interval == 0:
                if diversity_ctrl.should_inject_diversity(population, self.cfg.entropy_threshold):
                    inject_count = max(
                        1, int(self.cfg.diversity_injection_rate * len(population))
                    )
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

            # ---- Record stats ----
            stats["cost_history"].append(global_best_cost)
            avg_fitness = (
                sum(g.fitness for g in genomes) / len(genomes) if genomes else 0.0
            )
            stats["genome_fitness_history"].append(avg_fitness)
            stats["avg_genome_age_history"].append(
                sum(g.age for g in genomes) / len(genomes) if genomes else 0.0
            )
            # Track genome diversity (unique acceptance types used)
            unique_acceptance = set(g.acceptance_type for g in genomes)
            stats["genome_diversity_history"].append(len(unique_acceptance))

            # ---- Track improvements ----
            if global_best_cost < prev_best - 1e-10:
                stats["improvement_log"].append(
                    {"iter": t, "cost": global_best_cost, "phase": current_phase}
                )

            # ---- Progress callback ----
            if progress_callback is not None:
                progress_callback(t, global_best_cost, avg_fitness, current_phase)

            # ---- Time guard (10 minutes) ----
            elapsed_s = time.monotonic() - t_start
            if elapsed_s > 600:
                logger.info("P-AOEA time budget reached at iteration %d", t)
                break

        # ================================================================ #
        # Final Polish
        # ================================================================ #
        polished_tour, polished_cost, ls_stats = MultiLayerLS.improve(
            global_best,
            cost_fn,
            rng,
            intensity="full",
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
        stats["destroy_success_rates"] = dict(stats["destroy_operator_usage"])
        stats["repair_success_rates"] = dict(stats["repair_operator_usage"])
        stats["acceptance_distribution"] = dict(stats["acceptance_usage"])
        # Per-genome final stats
        stats["genome_final_stats"] = [
            {
                "destroy_ops": g.destroy_ops,
                "repair_ops": g.repair_ops,
                "acceptance_type": g.acceptance_type,
                "fitness": g.fitness,
                "success_rate": g.success_rate(),
                "age": g.age,
            }
            for g in genomes
        ]
        penalty_state = penalty_mgr.get_state()
        stats["penalty_state"] = {
            "alpha_tw": penalty_state.alpha_tw,
            "alpha_cap": penalty_state.alpha_cap,
            "phase": penalty_state.phase,
        }

        logger.info(
            "P-AOEA finished: cost=%d, gap=%.2f%%, time=%.0fms, iters=%d",
            best_cost_int,
            gap if gap == gap else -1,  # handle NaN
            elapsed_ms,
            t,
        )

        return PAOEAResult(
            tour=best_int_tour,
            cost=best_cost_int,
            gap=gap,
            time_ms=elapsed_ms,
            iterations=t,
            stats=stats,
        )

    # ------------------------------------------------------------------ #
    # Adaptive Destroy Intensity
    # ------------------------------------------------------------------ #

    def _adaptive_destroy_intensity(self, progress: float) -> float:
        """Compute the global adaptive destroy intensity.

        The intensity follows a schedule that transitions from broad
        exploration (30-40 % removal) to fine-tuning (10-15 % removal)::

            Early   (0-30%):   30-40% removal  -> Broad exploration
            Middle  (30-70%):  15-25% removal  -> Balanced
            Late    (70-100%): 10-15% removal  -> Fine-tuning

        The value is interpolated smoothly within each phase and is
        jittered slightly for additional stochasticity.

        Args:
            progress: Fraction of total iterations completed [0, 1].

        Returns:
            Destroy intensity in [0.10, 0.40].
        """
        if progress < 0.30:
            # Early phase: 0.30 → 0.40, linearly interpolated by sub-progress
            sub = progress / 0.30  # 0..1 within early phase
            intensity = 0.30 + 0.10 * sub
        elif progress < 0.70:
            # Middle phase: 0.25 → 0.15
            sub = (progress - 0.30) / 0.40  # 0..1 within middle phase
            intensity = 0.25 - 0.10 * sub
        else:
            # Late phase: 0.15 → 0.10
            sub = (progress - 0.70) / 0.30  # 0..1 within late phase
            intensity = 0.15 - 0.05 * sub

        # Clamp to valid range
        lo, hi = self.cfg.remove_ratio_range
        intensity = max(lo, min(hi, intensity))
        return intensity

    # ------------------------------------------------------------------ #
    # Genome Initialisation
    # ------------------------------------------------------------------ #

    def _initialise_genomes(self, rng: random.Random) -> List[OperatorGenome]:
        """Create an initial population of operator genomes.

        Each genome is initialised with a random subset of destroy and
        repair operators from the available pools, random weights, and
        a random acceptance type.  At least one operator of each category
        is always included.

        Args:
            rng: Seeded random generator.

        Returns:
            List of :class:`OperatorGenome` instances.
        """
        genomes: List[OperatorGenome] = []

        for _ in range(self.cfg.genome_population_size):
            # Select 1-3 destroy operators
            n_destroy = rng.randint(1, min(3, len(self.cfg.destroy_ops_pool)))
            d_ops = list(rng.sample(self.cfg.destroy_ops_pool, n_destroy))
            rng.shuffle(d_ops)

            # Select 1-2 repair operators
            n_repair = rng.randint(1, min(2, len(self.cfg.repair_ops_pool)))
            r_ops = list(rng.sample(self.cfg.repair_ops_pool, n_repair))
            rng.shuffle(r_ops)

            # Random acceptance type
            a_type = rng.choice(self.cfg.acceptance_types)

            # Random weights
            d_weights = [rng.random() + 0.1 for _ in d_ops]
            r_weights = [rng.random() + 0.1 for _ in r_ops]

            # Random LS intensity
            ls_int = rng.choice(["light", "light", "light", "moderate"])

            genome = OperatorGenome(
                destroy_ops=d_ops,
                repair_ops=r_ops,
                acceptance_type=a_type,
                destroy_weights=d_weights,
                repair_weights=r_weights,
                destroy_intensity=0.0,
                ls_intensity=ls_int,
            )
            genome.normalize_weights()
            genomes.append(genome)

        return genomes

    # ------------------------------------------------------------------ #
    # Meta-Evolution
    # ------------------------------------------------------------------ #

    def _meta_evolve(
        self,
        genomes: List[OperatorGenome],
        rng: random.Random,
        iteration: int,
    ) -> List[OperatorGenome]:
        """Evolve the genome population via selection, crossover, mutation.

        1. **Tournament selection**: pick the fittest genomes.
        2. **Crossover**: combine operator sets from two parent genomes.
        3. **Mutation**: swap / add / remove operators, perturb weights.
        4. **Structured injection**: 90 % mutations of best genomes +
           10 % fully random new genomes.
        5. **Replacement**: replace worst genomes with offspring.

        Args:
            genomes: Current genome population.
            rng: Seeded random generator.
            iteration: Current iteration number.

        Returns:
            Evolved genome population (same length as input).
        """
        n = len(genomes)
        if n < 2:
            return genomes

        # Sort genomes by fitness (descending)
        sorted_genomes = sorted(genomes, key=lambda g: g.fitness, reverse=True)

        # Number of genomes to replace
        n_replace = max(1, int(self.cfg.genome_injection_rate * n))

        offspring: List[OperatorGenome] = []

        # ---- Generate offspring ----
        while len(offspring) < n_replace:
            if rng.random() < self.cfg.crossover_rate and len(sorted_genomes) >= 2:
                # Tournament selection for two parents
                p1 = self._tournament_select(sorted_genomes, rng)
                p2 = self._tournament_select(sorted_genomes, rng)

                # Ensure different parents
                attempts = 0
                while p2 is p1 and attempts < 10:
                    p2 = self._tournament_select(sorted_genomes, rng)
                    attempts += 1

                # Crossover
                child = self._crossover_genomes(p1, p2, rng)
            else:
                # Mutation of a selected genome
                parent = self._tournament_select(sorted_genomes, rng)
                child = self._mutate_genome(parent, rng)

            # Apply mutation with probability
            if rng.random() < self.cfg.mutation_rate:
                child = self._mutate_genome(child, rng)

            child.normalize_weights()
            offspring.append(child)

        # ---- Structured injection: mix of mutated-best and random ----
        # The offspring list is already populated; now add structured
        # genomes: 90 % are mutations of top genomes, 10 % are random.
        final_offspring: List[OperatorGenome] = []
        n_structured = max(1, int(0.9 * n_replace))
        n_random = n_replace - n_structured

        for i in range(min(n_structured, len(offspring))):
            # Mutate the best genome for structured diversity
            best_genome = sorted_genomes[i % len(sorted_genomes)]
            mutated = self._mutate_genome(best_genome, rng)
            mutated.normalize_weights()
            final_offspring.append(mutated)

        for _ in range(n_random):
            # Fully random genome
            random_genome = self._create_random_genome(rng)
            final_offspring.append(random_genome)

        # Pad or trim to exact n_replace
        while len(final_offspring) < n_replace:
            final_offspring.append(self._create_random_genome(rng))
        final_offspring = final_offspring[:n_replace]

        # ---- Replace worst genomes with offspring ----
        new_genomes = list(sorted_genomes[: n - n_replace])  # keep the best
        new_genomes.extend(final_offspring)

        # Age all genomes
        for g in new_genomes:
            g.age += 1

        logger.debug(
            "Meta-evolution: replaced %d/%d genomes at iter %d",
            n_replace, n, iteration,
        )

        return new_genomes

    def _tournament_select(
        self,
        genomes: List[OperatorGenome],
        rng: random.Random,
    ) -> OperatorGenome:
        """Select a genome via tournament selection.

        Pick *tournament_size* genomes uniformly at random and return
        the one with the highest fitness.  Ties are broken randomly.

        Args:
            genomes: Genome population (assumed sorted by fitness desc).
            rng: Seeded random generator.

        Returns:
            The winning genome.
        """
        k = min(self.cfg.tournament_size, len(genomes))
        candidates = rng.sample(genomes, k)
        # Sort by fitness descending, then by success_rate for ties
        candidates.sort(key=lambda g: (g.fitness, g.success_rate()), reverse=True)
        return candidates[0]

    def _crossover_genomes(
        self,
        p1: OperatorGenome,
        p2: OperatorGenome,
        rng: random.Random,
    ) -> OperatorGenome:
        """Crossover two parent genomes to produce a child genome.

        The child inherits:
        * Union of destroy operators from both parents (deduplicated).
        * Union of repair operators from both parents (deduplicated).
        * Acceptance type from the fitter parent (80 %) or random (20 %).
        * Averaged weights (normalized).

        Args:
            p1: First parent genome.
            p2: Second parent genome.
            rng: Seeded random generator.

        Returns:
            Child :class:`OperatorGenome`.
        """
        # Destroy ops: union of both parents
        child_destroy = list(dict.fromkeys(p1.destroy_ops + p2.destroy_ops))
        if not child_destroy:
            child_destroy = ["random"]

        # Repair ops: union of both parents
        child_repair = list(dict.fromkeys(p1.repair_ops + p2.repair_ops))
        if not child_repair:
            child_repair = ["greedy"]

        # Acceptance type: from fitter parent with high probability
        if p1.fitness >= p2.fitness:
            fitter, weaker = p1, p2
        else:
            fitter, weaker = p2, p1

        if rng.random() < 0.8:
            child_acceptance = fitter.acceptance_type
        else:
            child_acceptance = weaker.acceptance_type

        # Weights: average corresponding operators where possible,
        # otherwise inherit from the parent that has them
        child_d_weights = self._crossover_weights(
            child_destroy, p1.destroy_ops, p1.destroy_weights,
            p2.destroy_ops, p2.destroy_weights, rng,
        )
        child_r_weights = self._crossover_weights(
            child_repair, p1.repair_ops, p1.repair_weights,
            p2.repair_ops, p2.repair_weights, rng,
        )

        # LS intensity: from fitter parent
        child_ls = fitter.ls_intensity

        # Destroy intensity: 0 (use adaptive) with 70 % chance
        child_d_intensity = 0.0 if rng.random() < 0.7 else rng.uniform(
            self.cfg.remove_ratio_range[0], self.cfg.remove_ratio_range[1],
        )

        child = OperatorGenome(
            destroy_ops=child_destroy,
            repair_ops=child_repair,
            acceptance_type=child_acceptance,
            destroy_weights=child_d_weights,
            repair_weights=child_r_weights,
            destroy_intensity=child_d_intensity,
            ls_intensity=child_ls,
        )
        return child

    def _crossover_weights(
        self,
        child_ops: List[str],
        p1_ops: List[str],
        p1_weights: List[float],
        p2_ops: List[str],
        p2_weights: List[float],
        rng: random.Random,
    ) -> List[float]:
        """Compute child weights by averaging parent weights.

        For each operator in *child_ops*, if both parents have it,
        average their weights.  If only one parent has it, use that
        weight (with slight perturbation).  Otherwise, assign a default.

        Args:
            child_ops: Operator names in the child genome.
            p1_ops: Operator names in parent 1.
            p1_weights: Weights for parent 1's operators.
            p2_ops: Operator names in parent 2.
            p2_weights: Weights for parent 2's operators.
            rng: Seeded random generator.

        Returns:
            Weight list corresponding to *child_ops*.
        """
        p1_map = dict(zip(p1_ops, p1_weights))
        p2_map = dict(zip(p2_ops, p2_weights))

        weights: List[float] = []
        for op in child_ops:
            w1 = p1_map.get(op)
            w2 = p2_map.get(op)
            if w1 is not None and w2 is not None:
                # Average with slight noise
                avg = (w1 + w2) / 2.0
                weights.append(max(0.1, avg + rng.gauss(0, 0.05)))
            elif w1 is not None:
                weights.append(max(0.1, w1 + rng.gauss(0, 0.1)))
            elif w2 is not None:
                weights.append(max(0.1, w2 + rng.gauss(0, 0.1)))
            else:
                weights.append(rng.random() + 0.5)

        return weights

    def _mutate_genome(
        self,
        genome: OperatorGenome,
        rng: random.Random,
    ) -> OperatorGenome:
        """Mutate a genome by randomly altering its genes.

        Possible mutations (each applied with some probability):

        * **Swap destroy operator**: replace one destroy operator with
          another from the pool.
        * **Add destroy operator**: add a new destroy operator (if room).
        * **Remove destroy operator**: remove one (keep at least 1).
        * Same for repair operators.
        * **Change acceptance type**: switch to a different type.
        * **Perturb weights**: add Gaussian noise to all weights.
        * **Change LS intensity**: switch between light / moderate.
        * **Set destroy intensity**: enable custom intensity.

        Args:
            genome: Genome to mutate (not modified in-place).
            rng: Seeded random generator.

        Returns:
            A new mutated :class:`OperatorGenome`.
        """
        child = OperatorGenome(
            destroy_ops=list(genome.destroy_ops),
            repair_ops=list(genome.repair_ops),
            acceptance_type=genome.acceptance_type,
            destroy_weights=list(genome.destroy_weights),
            repair_weights=list(genome.repair_weights),
            destroy_intensity=genome.destroy_intensity,
            ls_intensity=genome.ls_intensity,
            fitness=0.0,  # reset fitness for new genome
            age=0,
        )

        # ---- Mutate destroy operators ----
        roll = rng.random()
        if roll < 0.15:
            # Swap one destroy operator
            if child.destroy_ops:
                idx = rng.randint(0, len(child.destroy_ops) - 1)
                available = [
                    op for op in self.cfg.destroy_ops_pool
                    if op not in child.destroy_ops
                ]
                if available:
                    child.destroy_ops[idx] = rng.choice(available)
        elif roll < 0.25:
            # Add a destroy operator
            available = [
                op for op in self.cfg.destroy_ops_pool
                if op not in child.destroy_ops
            ]
            if available and len(child.destroy_ops) < len(self.cfg.destroy_ops_pool):
                new_op = rng.choice(available)
                child.destroy_ops.append(new_op)
                child.destroy_weights.append(rng.random() + 0.5)
        elif roll < 0.35:
            # Remove a destroy operator (keep at least 1)
            if len(child.destroy_ops) > 1:
                idx = rng.randint(0, len(child.destroy_ops) - 1)
                child.destroy_ops.pop(idx)
                if idx < len(child.destroy_weights):
                    child.destroy_weights.pop(idx)

        # ---- Mutate repair operators ----
        roll = rng.random()
        if roll < 0.15:
            if child.repair_ops:
                idx = rng.randint(0, len(child.repair_ops) - 1)
                available = [
                    op for op in self.cfg.repair_ops_pool
                    if op not in child.repair_ops
                ]
                if available:
                    child.repair_ops[idx] = rng.choice(available)
        elif roll < 0.25:
            available = [
                op for op in self.cfg.repair_ops_pool
                if op not in child.repair_ops
            ]
            if available and len(child.repair_ops) < len(self.cfg.repair_ops_pool):
                new_op = rng.choice(available)
                child.repair_ops.append(new_op)
                child.repair_weights.append(rng.random() + 0.5)
        elif roll < 0.35:
            if len(child.repair_ops) > 1:
                idx = rng.randint(0, len(child.repair_ops) - 1)
                child.repair_ops.pop(idx)
                if idx < len(child.repair_weights):
                    child.repair_weights.pop(idx)

        # ---- Mutate acceptance type ----
        if rng.random() < 0.2:
            others = [
                a for a in self.cfg.acceptance_types
                if a != child.acceptance_type
            ]
            if others:
                child.acceptance_type = rng.choice(others)

        # ---- Perturb weights ----
        if rng.random() < 0.4:
            child.destroy_weights = [
                max(0.05, w + rng.gauss(0, 0.2))
                for w in child.destroy_weights
            ]
        if rng.random() < 0.4:
            child.repair_weights = [
                max(0.05, w + rng.gauss(0, 0.2))
                for w in child.repair_weights
            ]

        # ---- Mutate LS intensity ----
        if rng.random() < 0.15:
            child.ls_intensity = rng.choice(["light", "moderate"])

        # ---- Mutate destroy intensity ----
        if rng.random() < 0.15:
            if rng.random() < 0.5:
                child.destroy_intensity = 0.0  # back to adaptive
            else:
                child.destroy_intensity = rng.uniform(
                    self.cfg.remove_ratio_range[0],
                    self.cfg.remove_ratio_range[1],
                )

        child.normalize_weights()
        return child

    def _create_random_genome(self, rng: random.Random) -> OperatorGenome:
        """Create a fully random genome.

        Args:
            rng: Seeded random generator.

        Returns:
            A new random :class:`OperatorGenome`.
        """
        n_destroy = rng.randint(1, min(3, len(self.cfg.destroy_ops_pool)))
        d_ops = list(rng.sample(self.cfg.destroy_ops_pool, n_destroy))
        d_weights = [rng.random() + 0.5 for _ in d_ops]

        n_repair = rng.randint(1, min(2, len(self.cfg.repair_ops_pool)))
        r_ops = list(rng.sample(self.cfg.repair_ops_pool, n_repair))
        r_weights = [rng.random() + 0.5 for _ in r_ops]

        genome = OperatorGenome(
            destroy_ops=d_ops,
            repair_ops=r_ops,
            acceptance_type=rng.choice(self.cfg.acceptance_types),
            destroy_weights=d_weights,
            repair_weights=r_weights,
            ls_intensity=rng.choice(["light", "light", "moderate"]),
        )
        genome.normalize_weights()
        return genome

    # ------------------------------------------------------------------ #
    # Genome-based Acceptance
    # ------------------------------------------------------------------ #

    def _genome_accept(
        self,
        genome: OperatorGenome,
        current_cost: float,
        new_cost: float,
        best_cost: float,
        iteration: int,
        rng: random.Random,
        sa: SimulatedAnnealing,
        lahc: LateAcceptanceHC,
        rtr: RecordToRecordTravel,
    ) -> AcceptResult:
        """Apply the genome's acceptance criterion.

        Routes to the appropriate acceptance strategy based on the
        genome's ``acceptance_type``.  If the type is ``"improving"``,
        only strictly improving moves are accepted.

        Args:
            genome: Operator genome specifying acceptance type.
            current_cost: Cost of the incumbent solution.
            new_cost: Cost of the candidate solution.
            best_cost: Best cost observed so far.
            iteration: Current iteration number.
            rng: Seeded random generator.
            sa: SimulatedAnnealing instance.
            lahc: LateAcceptanceHC instance.
            rtr: RecordToRecordTravel instance.

        Returns:
            :class:`AcceptResult` from the selected criterion.
        """
        # Always accept strict improvements regardless of criterion
        if new_cost < current_cost - 1e-10:
            is_new_best = new_cost < best_cost - 1e-10
            return AcceptResult(accepted=True, improved=True, is_new_best=is_new_best)

        if genome.acceptance_type == "sa":
            return sa.decide(current_cost, new_cost, best_cost, iteration, rng)
        elif genome.acceptance_type == "lahc":
            return lahc.decide(current_cost, new_cost, best_cost, iteration, rng)
        elif genome.acceptance_type == "rtr":
            return rtr.decide(current_cost, new_cost, best_cost, iteration, rng)
        else:
            # "improving" or unknown: only accept if improving
            return AcceptResult(accepted=False, improved=False, is_new_best=False)

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
        improved: List[List[str]] = []
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
    # Utility helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_str_distance_matrix(prob: Any) -> Dict[str, Dict[str, float]]:
        """Convert int-keyed distance matrix to str-keyed.

        Args:
            prob: Problem instance with ``dist_matrix`` (int->int->int)
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
            Dict mapping name -> operator instance.
        """
        ops: Dict[str, Any] = {}
        name_to_cls = {
            "random": RandomRemoval,
            "worst": WorstRemoval,
            "shaw": ShawRemoval,
            "related": RelatedRemoval,
        }
        for name in self.cfg.destroy_ops_pool:
            cls = name_to_cls.get(name)
            if cls is not None:
                ops[name] = cls()
        return ops

    def _build_repair_operators(self) -> Dict[str, Any]:
        """Instantiate repair operators by name.

        Returns:
            Dict mapping name -> operator instance.
        """
        ops: Dict[str, Any] = {}
        name_to_cls = {
            "greedy": GreedyInsertion,
            "regret2": Regret2Insertion,
            "regret3": Regret3Insertion,
        }
        for name in self.cfg.repair_ops_pool:
            cls = name_to_cls.get(name)
            if cls is not None:
                ops[name] = cls()
        return ops

    @staticmethod
    def _fix_tour(
        tour: List[str],
        waypoints: List[str],
        dm: Dict[str, Dict[str, float]],
    ) -> List[str]:
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

        This avoids repeated int<->str conversion that would occur when
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
