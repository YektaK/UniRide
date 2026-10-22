"""
Grey Wolf Optimizer for TSP

Reference:
Mirjalili, S., Mirjalili, S. M., & Lewis, A. (2014). Grey Wolf Optimizer.
Advances in Engineering Software, 69, 46-61.

Hybrid GWO (memetic):
- Permutation-based discrete encoding (swap-sequence movement toward leaders)
- Periodic 2-opt polish on the alpha wolf (Numba-accelerated)
- Final aggressive 2-opt on best
- Numba-accelerated tour-length evaluation (delta-friendly via cached matrix)
"""

import time
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .base_solver import BaseTSPSolver, TSPResult
from uniride_core.algorithms import numba_accel as _nb
from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    StageCappedBudget,
    budget_share_spent,
    improve_two_opt_budgeted,
    two_opt_evaluation_upper_bound,
)


@dataclass
class _Wolf:
    position: List[int]
    fitness: float
    tour_length: float


class GWOOptimizer(BaseTSPSolver):
    """Discrete Grey Wolf Optimizer — memetic, Numba-accelerated.

    Social hierarchy of three leaders (alpha, beta, delta) guides the pack
    through swap-sequence moves. An exponentially-decaying coefficient
    ``a`` shifts the balance from exploration to exploitation.

    Tour-length evaluation uses ``self._tour_length_fast`` (cached numpy
    matrix + Numba JIT kernel), so each candidate's cost is evaluated as
    cheaply as an O(1) delta against the prebuilt array would be.

    Injected counter (C-05): pass ``shared_budget`` (an
    ``ObjectiveEvaluationBudget`` owned by the caller) to spend on a shared
    counter that ``solve()`` never resets. ``stage_cap`` is an ABSOLUTE ceiling
    on the shared ``used`` value, not a per-stage allowance: the stage stops
    before ``shared_budget.used`` would exceed it or the shared total limit,
    whichever is smaller. C-06 passes ``floor(B * global_fraction)`` with the
    counter starting at 0, so there the absolute cap equals the stage
    allowance. ``stage_cap`` requires ``shared_budget`` and cannot be combined
    with ``evaluation_budget``.

    Schedule (owner decision 2026-10-22). In FIXED-BUDGET runs (a finite
    objective-evaluation limit: ``evaluation_budget`` or an injected counter
    with a stage cap or total limit) the coefficient ``a`` decays with the share
    of the budget spent, ``a = initial_a * (1 - p)`` with ``p = (used - start) /
    (limit - start)``, so every instance and budget gets the full arc from
    ``initial_a`` down to 0 when the budget is used up; ``max_iterations`` then
    only stops a run. ``used`` is the counter the run spends on, so a memetic
    run counts its polish evaluations (init, periodic, final) in the arc, which
    spans the whole run. ``limit`` is the effective ceiling, the smaller of the
    stage cap and the shared total limit: a composite hybrid's global stage
    therefore spans its own ``global_stage_cap``, not the run budget, and the
    arc ends when the global stage ends. ``start`` is the counter value when
    ``solve()`` begins (0 unless an injected counter was spent on before). In
    NATIVE runs (no limit) the schedule is unchanged,
    ``a = initial_a * (1 - iteration / max_iterations)``.
    """

    def __init__(
        self,
        pack_size: int = 50,
        max_iterations: int = 250,
        initial_a: float = 2.0,
        exploration_rate: float = 0.4,
        max_no_improvement: int = 75,
        polish_interval: int = 25,
        polish_iters: int = 10,
        final_polish_iters: int = 300,
        random_seed: Optional[int] = None,
        polish_enabled: bool = True,
        evaluation_budget: Optional[int] = None,
        shared_budget: Optional[ObjectiveEvaluationBudget] = None,
        stage_cap: Optional[int] = None,
        count_polish: bool = False,
    ):
        super().__init__("GWO", random_seed)
        self.pack_size = pack_size
        self.max_iterations = max_iterations
        self.initial_a = initial_a
        self.exploration_rate = exploration_rate
        self.max_no_improvement = max_no_improvement
        self.polish_interval = polish_interval
        self.polish_iters = polish_iters
        self.final_polish_iters = final_polish_iters
        self._rng = random.Random(self.random_seed)
        self.polish_enabled = polish_enabled
        self._polish_executed = {"initial": 0, "periodic": 0, "final": 0}
        self._polish_evaluations = {"initial": 0, "periodic": 0, "final": 0}
        if shared_budget is None and stage_cap is not None:
            raise ValueError("stage_cap requires an injected shared_budget")
        if shared_budget is not None and evaluation_budget is not None:
            raise ValueError(
                "pass either evaluation_budget (own counter) or shared_budget "
                "(injected counter), not both"
            )
        # Injected counter (C-05): the solver spends on a stage-capped view of
        # a counter owned by the caller and never resets it. Without injection
        # the solver owns its counter and solve() resets it, as before.
        self._injected_budget = shared_budget is not None
        self._fair_mode = evaluation_budget is not None or self._injected_budget
        # C-10: a governed native run has no cap but must still count its polish.
        # ``count_polish`` routes the 2-opt polish through the budgeted Python
        # 2-opt (one unit per candidate tour, unlimited counter), exactly as the
        # fixed-budget mode does; the uncounted Numba kernel is only taken by
        # ungoverned runs.
        self._count_polish = self._fair_mode or bool(count_polish)
        if self._injected_budget:
            self._objective_budget = StageCappedBudget(shared_budget, stage_cap)
            if self._objective_budget.limit is None:
                raise ValueError(
                    "an injected counter needs a stage cap or a total limit"
                )
        else:
            self._objective_budget = ObjectiveEvaluationBudget(evaluation_budget)

    # ----- Swap-sequence movement (discrete GWO velocity) ----------
    def _diff_swaps(self, current: List[int], target: List[int]) -> List[Tuple[int, int]]:
        """Swaps that transform ``current`` into ``target`` (chronological)."""
        swaps: List[Tuple[int, int]] = []
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

    def _move_toward_leader(
        self, wolf: List[int], leader: List[int], a: float
    ) -> List[int]:
        """GWO position update: probabilistic swap subset toward a leader."""
        swaps = self._diff_swaps(wolf, leader)
        if not swaps:
            return wolf[:]
        # Sample a fraction of the diff swaps proportional to |a|.
        intensity = max(0.0, min(1.0, abs(a) / self.initial_a))
        keep = [s for s in swaps if self._rng.random() < intensity]
        if not keep:
            keep = [self._rng.choice(swaps)]
        return self._apply_swaps(wolf, keep)

    def _schedule_decay(self, iteration: int, start_used: int) -> float:
        """Decay factor of ``a``: ``1 - share of the budget spent`` in fixed mode,
        ``1 - iteration / max_iterations`` in native mode (see the class docstring)."""
        share = budget_share_spent(self._objective_budget, start_used)
        if share is None:
            return 1.0 - iteration / max(1, self.max_iterations)
        return 1.0 - share

    def _evaluate(self, route: List[int]) -> float:
        self._objective_budget.consume()
        return self._tour_length_fast(route)

    # ----- Two-opt polish helper (Numba-accelerated) ---------------
    def _polish(
        self,
        route: List[int],
        iters: int,
        initial_cost: Optional[float] = None,
        phase: Optional[str] = None,
    ) -> Tuple[List[int], float, bool]:
        if self._count_polish:
            result = improve_two_opt_budgeted(
                route, self._dist_matrix, self._objective_budget,
                max_iterations=iters, first_improvement=False,
                initial_cost=initial_cost,
            )
            if phase is not None:
                # Candidate evaluations only: the one evaluation that prices the
                # starting tour (initial_cost is None) is not polish work.
                self._polish_evaluations[phase] += result.evaluations - (
                    1 if initial_cost is None else 0
                )
            polished = result.route, result.cost, result.budget_exhausted
            self._backend_observation.polish.add("python")
            return polished
        if self._dist_matrix_np is not None:
            polish_kernel = _nb._two_opt_improve_atsp_numba
            route_np = _nb._prepare_route(route)
            improved_np, length = polish_kernel(
                route_np, self._dist_matrix_np, iters, False
            )
            polished = _nb._extract_route(improved_np, route), float(length), False
            backend = self._runtime_backend(polish_kernel)
            self._backend_observation.polish.add(backend)
            return polished
        if self._dist_matrix is not None:
            polish_kernel = _nb._two_opt_improve_atsp_numba
            improved, length = _nb.nb_two_opt(route, self._dist_matrix, iters, False)
            polished = improved, float(length), False
            backend = self._runtime_backend(polish_kernel)
            self._backend_observation.polish.add(backend)
            return polished
        polished = route[:], self.tour_length(route), False
        self._backend_observation.polish.add("python")
        return polished

    # ----- Main solve ---------------------------------------------
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._backend_observation.reset()
        self._rng = random.Random(self.random_seed)
        self._polish_executed = {"initial": 0, "periodic": 0, "final": 0}
        self._polish_evaluations = {"initial": 0, "periodic": 0, "final": 0}
        if not self._injected_budget:
            self._objective_budget.used = 0
        start_used = self._objective_budget.used
        self._set_problem(coordinates)
        t0 = time.perf_counter()

        base = self._initial_tour_nodes()
        if self._fair_mode:
            init_required = self.pack_size
            if self.polish_enabled:
                init_required = self.pack_size * two_opt_evaluation_upper_bound(
                    len(base), self.polish_iters
                )
            if not self._objective_budget.can_spend(init_required):
                raise ValueError(
                    "fair GWO budget cannot complete atomic population initialization: "
                    f"required_upper_bound={init_required}, "
                    f"budget={self._objective_budget.limit}"
                )
        budget_terminated = False
        pack: List[_Wolf] = []
        for _ in range(self.pack_size):
            perm = base[:]
            self._rng.shuffle(perm)
            if self.polish_enabled:
                polished, plen, polish_exhausted = self._polish(
                    perm, self.polish_iters, phase="initial"
                )
                if self.polish_iters > 0:
                    self._polish_executed["initial"] += 1
                budget_terminated = budget_terminated or polish_exhausted
            else:
                polished, plen = perm, self._evaluate(perm)
            pack.append(_Wolf(polished, 1.0 / (plen + 1e-10), plen))

        pack.sort(key=lambda w: w.tour_length)
        alpha = _Wolf(pack[0].position[:], pack[0].fitness, pack[0].tour_length)
        beta = (
            _Wolf(pack[1].position[:], pack[1].fitness, pack[1].tour_length)
            if len(pack) > 1
            else _Wolf(alpha.position[:], alpha.fitness, alpha.tour_length)
        )
        delta = (
            _Wolf(pack[2].position[:], pack[2].fitness, pack[2].tour_length)
            if len(pack) > 2
            else _Wolf(beta.position[:], beta.fitness, beta.tour_length)
        )

        best_len = alpha.tour_length
        best_chrom = alpha.position[:]
        no_improve = 0
        history: List[float] = []
        iterations_completed = 0

        for it in range(self.max_iterations):
            phase_evaluations = max(0, len(pack) - 3)
            if not self._objective_budget.can_spend(phase_evaluations):
                budget_terminated = True
                break
            history.append(float(best_len))
            a = self.initial_a * self._schedule_decay(it, start_used)
            improved = False

            # Replace leaders in the working pack so the loop iterates over a
            # stable view; reinsert at the end before re-ranking.
            new_pack: List[_Wolf] = [
                _Wolf(alpha.position[:], alpha.fitness, alpha.tour_length),
                _Wolf(beta.position[:], beta.fitness, beta.tour_length),
                _Wolf(delta.position[:], delta.fitness, delta.tour_length),
            ]

            for wolf in pack[3:]:
                if self._rng.random() < self.exploration_rate * (a / self.initial_a if self.initial_a else 0):
                    # Exploration: random perturbation around current position.
                    candidate = wolf.position[:]
                    for _ in range(self._rng.randint(1, 3)):
                        i, j = self._rng.sample(range(len(candidate)), 2)
                        candidate[i], candidate[j] = candidate[j], candidate[i]
                else:
                    # Exploitation: move toward alpha, then beta, then delta.
                    candidate = self._move_toward_leader(wolf.position, alpha.position, a)
                    candidate = self._move_toward_leader(candidate, beta.position, a)
                    candidate = self._move_toward_leader(candidate, delta.position, a)

                clen = self._evaluate(candidate)
                new_pack.append(_Wolf(candidate, 1.0 / (clen + 1e-10), clen))

                if clen < wolf.tour_length:
                    if clen < alpha.tour_length:
                        delta = _Wolf(beta.position[:], beta.fitness, beta.tour_length)
                        beta = _Wolf(alpha.position[:], alpha.fitness, alpha.tour_length)
                        alpha = _Wolf(candidate[:], 1.0 / (clen + 1e-10), clen)
                        improved = True
                    elif clen < beta.tour_length:
                        delta = _Wolf(beta.position[:], beta.fitness, beta.tour_length)
                        beta = _Wolf(candidate[:], 1.0 / (clen + 1e-10), clen)
                        improved = True
                    elif clen < delta.tour_length:
                        delta = _Wolf(candidate[:], 1.0 / (clen + 1e-10), clen)
                        improved = True

            new_pack.sort(key=lambda w: w.tour_length)
            pack = new_pack

            if alpha.tour_length < best_len:
                best_len = alpha.tour_length
                best_chrom = alpha.position[:]
                no_improve = 0
            else:
                no_improve += 1

            # Periodic memetic polish on the alpha wolf.
            if self.polish_enabled and self.polish_interval > 0 and it > 0 and it % self.polish_interval == 0:
                polished, plen, polish_exhausted = self._polish(
                    alpha.position, self.polish_iters, alpha.tour_length, phase="periodic"
                )
                if self.polish_iters > 0:
                    self._polish_executed["periodic"] += 1
                budget_terminated = budget_terminated or polish_exhausted
                if plen < alpha.tour_length:
                    alpha = _Wolf(polished[:], 1.0 / (plen + 1e-10), plen)
                    pack[0] = alpha
                    if plen < best_len:
                        best_len = plen
                        best_chrom = polished[:]
                        no_improve = 0
                if polish_exhausted:
                    break

            iterations_completed += 1
            if no_improve >= self.max_no_improvement:
                break

        # Final aggressive 2-opt on best.
        if self.polish_enabled:
            best_chrom, best_len, polish_exhausted = self._polish(
                best_chrom, self.final_polish_iters, best_len, phase="final"
            )
            if self.final_polish_iters > 0:
                self._polish_executed["final"] += 1
            budget_terminated = budget_terminated or polish_exhausted

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="GWO",
            tour=best_chrom,
            tour_length=best_len,
            elapsed_ms=elapsed_ms,
            iterations=iterations_completed,
            params={
                "pack_size": self.pack_size,
                "iterations": iterations_completed,
                "initial_a": self.initial_a,
                "exploration_rate": self.exploration_rate,
                "memetic": self.polish_enabled,
                "polish_interval": self.polish_interval,
            },
            extra_stats={
                "objective_evaluations": self._objective_budget.used - start_used,
                "evaluation_budget": (
                    self._objective_budget.limit
                    if self._objective_budget.limit is None
                    else self._objective_budget.limit - start_used
                ),
                "budget_terminated": budget_terminated,
                "variant": "memetic_2opt" if self.polish_enabled else "pure",
                "polish_executed": dict(self._polish_executed),
                # Candidate evaluations spent by each polish phase (counted polish:
                # fixed-budget mode and governed native runs; None for ungoverned runs).
                "polish_evaluations": (
                    dict(self._polish_evaluations) if self._count_polish else None
                ),
                "execution_backend": self._backend_observation.label(),
                **(
                    {
                        "shared_counter_used": self._objective_budget.used,
                        "stage_cap": self._objective_budget.stage_cap,
                    }
                    if self._injected_budget
                    else {}
                ),
            },
            history=history,
            seed=self.random_seed,
        )