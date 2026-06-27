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
from . import numba_accel as _nb


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

    # ----- Two-opt polish helper (Numba-accelerated) ---------------
    def _polish(self, route: List[int], iters: int) -> Tuple[List[int], float]:
        if self._dist_matrix_np is not None:
            route_np = _nb._prepare_route(route)
            improved_np, length = _nb._two_opt_improve_atsp_numba(
                route_np, self._dist_matrix_np, iters, False
            )
            return _nb._extract_route(improved_np, route), float(length)
        if self._dist_matrix is not None:
            improved, length = _nb.nb_two_opt(route, self._dist_matrix, iters, False)
            return improved, float(length)
        return route[:], self.tour_length(route)

    # ----- Main solve ---------------------------------------------
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        t0 = time.perf_counter()

        base = self._initial_tour_nodes()
        pack: List[_Wolf] = []
        for _ in range(self.pack_size):
            perm = base[:]
            self._rng.shuffle(perm)
            polished, plen = self._polish(perm, self.polish_iters)
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
        last_iter = 0

        for it in range(self.max_iterations):
            last_iter = it
            history.append(float(best_len))
            a = self.initial_a * (1.0 - it / max(1, self.max_iterations))
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

                clen = self._tour_length_fast(candidate)
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
            if it > 0 and it % self.polish_interval == 0:
                polished, plen = self._polish(alpha.position, self.polish_iters)
                if plen < alpha.tour_length:
                    alpha = _Wolf(polished[:], 1.0 / (plen + 1e-10), plen)
                    pack[0] = alpha
                    if plen < best_len:
                        best_len = plen
                        best_chrom = polished[:]
                        no_improve = 0

            if no_improve >= self.max_no_improvement:
                break

        # Final aggressive 2-opt on best.
        if self._dist_matrix_np is not None:
            route_np = _nb._prepare_route(best_chrom)
            improved_np, best_len = _nb._two_opt_improve_atsp_numba(
                route_np, self._dist_matrix_np, self.final_polish_iters, False
            )
            best_chrom = _nb._extract_route(improved_np, best_chrom)
        elif self._dist_matrix is not None:
            best_chrom, best_len = _nb.nb_two_opt(
                best_chrom, self._dist_matrix, self.final_polish_iters, False
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="GWO",
            tour=best_chrom,
            tour_length=best_len,
            elapsed_ms=elapsed_ms,
            iterations=last_iter + 1,
            params={
                "pack_size": self.pack_size,
                "iterations": last_iter + 1,
                "initial_a": self.initial_a,
                "exploration_rate": self.exploration_rate,
                "memetic": True,
                "polish_interval": self.polish_interval,
            },
            history=history,
            seed=self.random_seed,
        )