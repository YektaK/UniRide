"""Canonical bounded 3-opt local search for TSP and directed ATSP."""
import time
import random
from typing import Optional

from .base_solver import BaseTSPSolver, TSPResult
from uniride_core.algorithms.three_opt import improve_three_opt


class ThreeOptSolver(BaseTSPSolver):
    """Correctness-first bounded 3-opt for symmetric TSP and directed ATSP.

    The window bounds the separation between successive cut positions. Every
    admissible symmetric reconnection or directed three-arc exchange is still
    evaluated for an admitted cut triple. The historical Numba kernel is not
    used until it passes semantic-parity tests against the canonical core.
    """

    def __init__(
        self,
        max_iterations: int = 1000,
        first_improvement: bool = False,
        multi_start: bool = False,
        num_starts: int = 5,
        window: int = 12,
        random_seed: Optional[int] = None,
    ):
        super().__init__("3-opt-bounded", random_seed)
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self.multi_start = multi_start
        self.num_starts = num_starts
        self.window = window
        self._last_mode = "unknown"
        self._evaluations_total = 0

    def _improve_tour(self, tour):
        if self._dist_matrix is None:
            raise RuntimeError("3-opt requires a prepared distance matrix")

        full_tour = list(tour)
        depot_anchored = (
            self._use_time_matrix
            and len(full_tour) + 1 == len(self._dist_matrix)
            and 0 not in full_tour
        )
        if depot_anchored:
            full_tour = [0] + full_tour

        result = improve_three_opt(
            full_tour,
            self._dist_matrix,
            max_iterations=self.max_iterations,
            first_improvement=self.first_improvement,
            window=self.window,
        )
        self._last_mode = result.mode
        self._evaluations_total += result.evaluations

        improved = result.route
        if depot_anchored:
            depot_pos = improved.index(0)
            improved = improved[depot_pos:] + improved[:depot_pos]
            improved = improved[1:]

        return improved, result.cost, result.iterations

    def solve(self, coordinates):
        self._set_problem(coordinates)
        rng = random.Random(self.random_seed)
        self._evaluations_total = 0
        t0 = time.perf_counter()
        if self.multi_start:
            best_t, best_l = None, float("inf")
            total_i = 0
            for _ in range(self.num_starts):
                nodes = self._initial_tour_nodes()
                rng.shuffle(nodes)
                candidate_tour, candidate_length, iterations = self._improve_tour(nodes)
                total_i += iterations
                if candidate_length < best_l:
                    best_l, best_t = candidate_length, candidate_tour
            final_t, final_l, iters = best_t, best_l, total_i
        else:
            nodes = self._initial_tour_nodes()
            rng.shuffle(nodes)
            final_t, final_l, iters = self._improve_tour(nodes)

        elapsed = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="3-opt-bounded",
            tour=final_t,
            tour_length=final_l,
            elapsed_ms=elapsed,
            iterations=iters,
            params={
                "max_iterations": self.max_iterations,
                "first_improvement": self.first_improvement,
                "multi_start": self.multi_start,
                "num_starts": self.num_starts,
                "window": self.window,
                "execution_backend": "canonical_python",
                "neighborhood_mode": self._last_mode,
            },
            seed=self.random_seed,
            extra_stats={"evaluations": self._evaluations_total},
        )
