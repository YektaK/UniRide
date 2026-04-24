"""3-opt Local Search Algorithm for TSP."""
import time
import random
from typing import List, Tuple, Optional
from .base_solver import BaseTSPSolver, TSPResult
from . import numba_accel as _nb

_NUMBA_OK = _nb.NUMBA_AVAILABLE


class ThreeOptSolver(BaseTSPSolver):
    """3-opt Local Search for TSP. Uses Numba JIT if available."""

    def __init__(self, max_iterations: int = 1000, first_improvement: bool = False,
                 multi_start: bool = False, num_starts: int = 5, random_seed: Optional[int] = None):
        super().__init__("3-opt", random_seed)
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self.multi_start = multi_start
        self.num_starts = num_starts

    def _three_opt_cases(self, tour, i, j, k):
        A = tour[:i + 1]
        B = tour[i + 1:j + 1]
        C = tour[j + 1:k + 1]
        D = tour[k + 1:]
        Br = list(reversed(B))
        Cr = list(reversed(C))
        Dr = list(reversed(D))
        return [
            A + Br + Cr + D,
            A + Br + C + Dr,
            A + B + Cr + Dr,
            A + Br + C + D,
            A + B + Cr + D,
            A + B + C + Dr,
            A + Br + Cr + Dr,
        ]

    def _improve_tour(self, tour):
        if _NUMBA_OK and self._dist_matrix is not None:
            improved, length = _nb.nb_three_opt(
                tour, self._dist_matrix,
                self.max_iterations, self.first_improvement
            )
            return improved, length, 0

        best = tour.copy()
        best_len = self.tour_length(best)
        imp = True
        iters = 0
        n = len(best)
        if n < 4:
            from .two_opt import TwoOptSolver
            t2 = TwoOptSolver(max_iterations=self.max_iterations)
            t2._set_problem(self._coordinates)
            return t2._improve_tour(tour)

        while imp and iters < self.max_iterations:
            imp = False
            iters += 1
            for i in range(n - 2):
                for j in range(i + 1, n - 1):
                    for k in range(j + 1, n):
                        for cand in self._three_opt_cases(best, i, j, k):
                            cl = self.tour_length(cand)
                            if cl < best_len:
                                best = cand
                                best_len = cl
                                imp = True
                                if self.first_improvement:
                                    break
                        if imp and self.first_improvement:
                            break
                    if imp and self.first_improvement:
                        break
                if imp and self.first_improvement:
                    break
        return best, best_len, iters

    def solve(self, coordinates):
        self._set_problem(coordinates)
        rng = random.Random(self.random_seed)
        t0 = time.perf_counter()
        if self.multi_start:
            best_t, best_l = None, float('inf')
            total_i = 0
            for _ in range(self.num_starts):
                nodes = self._initial_tour_nodes()
                rng.shuffle(nodes)
                t, l, i = self._improve_tour(nodes)
                total_i += i
                if l < best_l:
                    best_l, best_t = l, t
            final_t, final_l, iters = best_t, best_l, total_i
        else:
            nodes = self._initial_tour_nodes()
            rng.shuffle(nodes)
            final_t, final_l, iters = self._improve_tour(nodes)
        elapsed = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="3-opt", tour=final_t, tour_length=final_l,
            elapsed_ms=elapsed, iterations=iters,
            params={
                "max_iterations": self.max_iterations,
                "first_improvement": self.first_improvement,
                "multi_start": self.multi_start,
                "num_starts": self.num_starts,
            },
            seed=self.random_seed,
        )
