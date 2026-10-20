"""
Canonical pure Particle Swarm Optimization for TSP/ATSP (C-16b)

Reference:
Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization.
Proceedings of ICNN'95, 1942-1948.
Clerc, M., & Kennedy, J. (2002). The particle swarm - explosion, stability, and
convergence in a multidimensional complex space. IEEE TEC, 6(1), 58-73.

Operators (discrete permutation positions, swap-sequence velocity, probabilistic
Clerc-style velocity combination, optional diversity re-initialization) follow the
archived Bildiri PSO as a reference only. Unlike that PSO this solver has NO local
search: there is no 2-opt on the initial swarm, none inside the re-initialization and
no final 2-opt. The archived algorithm was memetic; this identity is the pure one.

Objective accounting (fairness design, atomic phases):
- swarm initialization is one atomic phase of ``swarm_size`` evaluations;
- each iteration is one atomic phase of ``swarm_size`` evaluations (every particle moves
  once and is evaluated once), started only when that exact upper bound fits the
  remaining budget;
- the optional diversity re-initialization (``reinit_interval`` > 0) is its OWN atomic
  phase of ``swarm_size`` evaluations, run after every ``reinit_interval``-th completed
  iteration, only while the run continues (not after the last iteration and not after
  a stagnation stop), and only when that exact bound fits. It never spends from inside
  an iteration phase, so an iteration is always complete or not started;
- native mode uses ``ObjectiveEvaluationBudget(None)`` and reports the actual count.

Termination reasons: ``evaluation_budget_exhausted``, ``max_iterations``,
``max_no_improvement``.

Hooks reusable by other compositions: :meth:`begin_run`, :meth:`initialize_swarm`,
:meth:`move_swarm`, :meth:`reinitialize_swarm`.
"""

import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .base_solver import BaseTSPSolver, TSPResult
from uniride_core.algorithms.objective_budget import ObjectiveEvaluationBudget


@dataclass
class _Particle:
    position: List[int]
    velocity: List[Tuple[int, int]]
    personal_best: List[int]
    personal_best_len: float
    current_len: float


@dataclass
class SwarmState:
    swarm: List[_Particle] = field(default_factory=list)
    global_best: List[int] = field(default_factory=list)
    global_best_len: float = float("inf")


class PSOOptimizer(BaseTSPSolver):
    """Pure discrete PSO with exact objective-evaluation accounting."""

    # Fixed parts of the diversity step (taken from the archived re-initialization).
    REINIT_RANDOM_FRACTION = 0.1
    REINIT_MAX_SWAPS = 3

    def __init__(
        self,
        swarm_size: int = 50,
        max_iterations: int = 500,
        inertia_weight: float = 0.729,
        cognitive_coeff: float = 1.49445,
        social_coeff: float = 1.49445,
        max_velocity_size: int = 5,
        max_no_improvement: int = 100,
        reinit_interval: int = 50,
        random_seed: Optional[int] = None,
        evaluation_budget: Optional[int] = None,
    ):
        super().__init__("PSO", random_seed)
        if swarm_size < 2:
            raise ValueError("PSO swarm_size must be at least 2")
        if max_velocity_size < 1:
            raise ValueError("PSO max_velocity_size must be at least 1")
        if reinit_interval < 0:
            raise ValueError("PSO reinit_interval must be >= 0 (0 disables re-initialization)")
        self.swarm_size = swarm_size
        self.max_iterations = max_iterations
        self.inertia_weight = inertia_weight
        self.cognitive_coeff = cognitive_coeff
        self.social_coeff = social_coeff
        self.max_velocity_size = max_velocity_size
        self.max_no_improvement = max_no_improvement
        self.reinit_interval = reinit_interval
        self._rng = random.Random(self.random_seed)
        self._fair_mode = evaluation_budget is not None
        self._objective_budget = ObjectiveEvaluationBudget(evaluation_budget)

    # ----- Accounted evaluation ------------------------------------
    def _evaluate(self, route: List[int]) -> float:
        self._objective_budget.consume()
        return self._tour_length_fast(route)

    # ----- Velocity helpers (no objective evaluation) --------------
    def _random_velocity(self, size: int) -> List[Tuple[int, int]]:
        return [
            (self._rng.randint(0, size - 1), self._rng.randint(0, size - 1))
            for _ in range(self.max_velocity_size)
        ]

    @staticmethod
    def _diff_swaps(current: List[int], target: List[int]) -> List[Tuple[int, int]]:
        """Swap operations that transform ``current`` into ``target``."""
        swaps = []
        temp = current[:]
        for i in range(len(target)):
            if temp[i] != target[i]:
                try:
                    j = temp.index(target[i], i)
                except ValueError:
                    continue
                temp[i], temp[j] = temp[j], temp[i]
                swaps.append((i, j))
        return swaps

    @staticmethod
    def _apply_swaps(position: List[int], swaps: List[Tuple[int, int]]) -> List[int]:
        new_pos = position[:]
        for i, j in swaps:
            new_pos[i], new_pos[j] = new_pos[j], new_pos[i]
        return new_pos

    def _combine_velocities(
        self,
        inertia_v: List[Tuple[int, int]],
        cog_v: List[Tuple[int, int]],
        soc_v: List[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """Clerc-style probabilistic combination of the three swap sequences."""
        new_v = []
        for swap in inertia_v:
            if self._rng.random() < self.inertia_weight:
                new_v.append(swap)
        for swap in cog_v:
            if self._rng.random() < self.cognitive_coeff / 3.0:
                new_v.append(swap)
        for swap in soc_v:
            if self._rng.random() < self.social_coeff / 3.0:
                new_v.append(swap)
        if len(new_v) > self.max_velocity_size:
            new_v = self._rng.sample(new_v, self.max_velocity_size)
        return new_v

    # ----- Phase bounds --------------------------------------------
    def initialization_evaluation_bound(self) -> int:
        """Exact evaluations of the atomic swarm-initialization phase."""
        return self.swarm_size

    def iteration_evaluation_bound(self) -> int:
        """Exact evaluations of one atomic iteration phase (one per particle)."""
        return self.swarm_size

    def reinit_evaluation_bound(self) -> int:
        """Exact evaluations of one atomic diversity re-initialization phase."""
        return self.swarm_size

    # ----- Hooks ---------------------------------------------------
    def begin_run(self, coordinates: List[Tuple[float, float]]) -> None:
        """Reset the per-run state and load the problem."""
        self._backend_observation.reset()
        self._rng = random.Random(self.random_seed)
        self._objective_budget.used = 0
        self._set_problem(coordinates)

    def initialize_swarm(self) -> SwarmState:
        """Random permutation swarm, one evaluation per particle, no local search."""
        state = SwarmState(global_best=self._initial_tour_nodes())
        base = self._initial_tour_nodes()
        for _ in range(self.swarm_size):
            pos = base[:]
            self._rng.shuffle(pos)
            length = self._evaluate(pos)
            vel = self._random_velocity(len(pos))
            state.swarm.append(_Particle(pos, vel, pos[:], length, length))
            if length < state.global_best_len:
                state.global_best_len = length
                state.global_best = pos[:]
        return state

    def move_swarm(self, state: SwarmState) -> bool:
        """One iteration: every particle moves and is evaluated once.

        Returns True when the global best improved during the iteration.
        """
        improved = False
        for p in state.swarm:
            cog_v = self._diff_swaps(p.position, p.personal_best)
            soc_v = self._diff_swaps(p.position, state.global_best)
            p.velocity = self._combine_velocities(p.velocity, cog_v, soc_v)
            p.position = self._apply_swaps(p.position, p.velocity)
            p.current_len = self._evaluate(p.position)
            if p.current_len < p.personal_best_len:
                p.personal_best = p.position[:]
                p.personal_best_len = p.current_len
            if p.current_len < state.global_best_len:
                state.global_best_len = p.current_len
                state.global_best = p.position[:]
                improved = True
        return improved

    def reinitialize_swarm(self, state: SwarmState) -> bool:
        """Diversity step (no 2-opt): restart every particle near its personal best.

        Each particle restarts from its personal best with 1..REINIT_MAX_SWAPS random
        swaps (or, with probability REINIT_RANDOM_FRACTION, from a fresh random
        permutation), gets a new random velocity and is evaluated once. Personal and
        global bests are kept and only replaced by a strictly better evaluation.
        Returns True when the global best improved.
        """
        improved = False
        for p in state.swarm:
            if self._rng.random() < 1.0 - self.REINIT_RANDOM_FRACTION:
                pos = p.personal_best[:]
                if len(pos) >= 2:
                    for _ in range(self._rng.randint(1, self.REINIT_MAX_SWAPS)):
                        i, j = self._rng.sample(range(len(pos)), 2)
                        pos[i], pos[j] = pos[j], pos[i]
            else:
                pos = self._initial_tour_nodes()
                self._rng.shuffle(pos)
            p.position = pos
            p.velocity = self._random_velocity(len(pos))
            p.current_len = self._evaluate(pos)
            if p.current_len < p.personal_best_len:
                p.personal_best = pos[:]
                p.personal_best_len = p.current_len
            if p.current_len < state.global_best_len:
                state.global_best_len = p.current_len
                state.global_best = pos[:]
                improved = True
        return improved

    # ----- Main solve ----------------------------------------------
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self.begin_run(coordinates)
        t0 = time.perf_counter()

        if self._fair_mode:
            init_required = self.initialization_evaluation_bound()
            if not self._objective_budget.can_spend(init_required):
                raise ValueError(
                    "fair PSO budget cannot complete atomic swarm initialization: "
                    f"required_upper_bound={init_required}, "
                    f"budget={self._objective_budget.limit}"
                )

        state = self.initialize_swarm()
        no_improve = 0
        history: List[float] = []
        iterations_completed = 0
        reinit_phases = 0
        termination_reason = "max_iterations"
        iteration_bound = self.iteration_evaluation_bound()
        reinit_bound = self.reinit_evaluation_bound()

        for _ in range(self.max_iterations):
            if not self._objective_budget.can_spend(iteration_bound):
                termination_reason = "evaluation_budget_exhausted"
                break
            history.append(float(state.global_best_len))
            improved = self.move_swarm(state)
            iterations_completed += 1
            no_improve = 0 if improved else no_improve + 1
            if no_improve >= self.max_no_improvement:
                termination_reason = "max_no_improvement"
                break
            if (
                self.reinit_interval > 0
                and iterations_completed % self.reinit_interval == 0
                and iterations_completed < self.max_iterations
                and self._objective_budget.can_spend(reinit_bound)
            ):
                reinit_phases += 1
                if self.reinitialize_swarm(state):
                    no_improve = 0
        history.append(float(state.global_best_len))

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="PSO",
            tour=state.global_best,
            tour_length=state.global_best_len,
            elapsed_ms=elapsed_ms,
            iterations=iterations_completed,
            params={
                "swarm_size": self.swarm_size,
                "iterations": iterations_completed,
                "inertia_weight": self.inertia_weight,
                "cognitive_coeff": self.cognitive_coeff,
                "social_coeff": self.social_coeff,
                "max_velocity_size": self.max_velocity_size,
                "reinit_interval": self.reinit_interval,
                "memetic": False,
            },
            extra_stats={
                "objective_evaluations": self._objective_budget.used,
                "evaluation_budget": self._objective_budget.limit,
                "budget_terminated": termination_reason == "evaluation_budget_exhausted",
                "termination_reason": termination_reason,
                "variant": "pure",
                "polish_executed": {"initial": 0, "periodic": 0, "final": 0},
                "polish_evaluations": (
                    {"initial": 0, "periodic": 0, "final": 0} if self._fair_mode else None
                ),
                "diversity_reinit_phases": reinit_phases,
                "diversity_reinit_evaluations": reinit_phases * reinit_bound,
                "execution_backend": self._backend_observation.label(),
            },
            history=history,
            seed=self.random_seed,
        )
