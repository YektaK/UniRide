"""
Harris Hawks Optimization for TSP

Reference:
Heidari, A. A., Mirjalili, S., Faris, H., Aljarah, I., Mafarja, M., & Chen, H.
(2019). Harris hawks optimization: Algorithm and applications. Future
Generation Computer Systems, 97, 849-872.

Hybrid HHO (memetic):
- Permutation-based discrete encoding
- Adaptive switch between exploration (perching / Lévy flights) and
  exploitation (soft/hard besiege with optional rapid dives) driven by
  linearly-decreasing escape energy
- Periodic 2-opt polish on the prey (Numba-accelerated)
- Final aggressive 2-opt on best
- Numba-accelerated tour-length evaluation (cached matrix + JIT kernel)
"""

import math
import time
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .base_solver import BaseTSPSolver, TSPResult
from . import numba_accel as _nb


@dataclass
class _Hawk:
    position: List[int]
    fitness: float
    tour_length: float


class HHOOptimizer(BaseTSPSolver):
    """Discrete Harris Hawks Optimizer — memetic, Numba-accelerated.

    Models a swarm of hawks chasing a prey (best-so-far solution). The
    escape-energy ``E`` decreases linearly; ``|E| >= 1`` triggers
    exploration (perching / Lévy flights) while ``|E| < 1`` triggers
    exploitation with soft/hard besiege and progressive rapid dives.

    Tour-length evaluation is done via ``self._tour_length_fast`` (cached
    numpy matrix + Numba JIT kernel), making each candidate cost evaluation
    an inexpensive array-backed computation rather than a Python loop.
    """

    def __init__(
        self,
        hawks: int = 50,
        max_iterations: int = 250,
        initial_energy: float = 1.0,
        jump_probability: float = 0.5,
        max_no_improvement: int = 75,
        dive_count: int = 3,
        levy_scale: float = 0.3,
        polish_interval: int = 25,
        polish_iters: int = 10,
        final_polish_iters: int = 300,
        random_seed: Optional[int] = None,
    ):
        super().__init__("HHO", random_seed)
        self.hawks = hawks
        self.max_iterations = max_iterations
        self.initial_energy = initial_energy
        self.jump_probability = jump_probability
        self.max_no_improvement = max_no_improvement
        self.dive_count = dive_count
        self.levy_scale = levy_scale
        self.polish_interval = polish_interval
        self.polish_iters = polish_iters
        self.final_polish_iters = final_polish_iters
        self._rng = random.Random(self.random_seed)

    # ----- Discrete Lévy flight (Mantegna) -------------------------
    def _levy_flight(self, route: List[int], scale: float = 0.3) -> List[int]:
        """Apply a Lévy-distributed number of random swaps to a route.

        Uses Mantegna's algorithm with beta = 1.5 to draw step lengths from a
        stable distribution, then applies that many disjoint random swaps.
        This is the discrete analogue of continuous-space Lévy flights.
        """
        new_pos = route[:]
        n = len(new_pos)
        if n < 2:
            return new_pos
        beta = 1.5
        sigma = (
            math.gamma(1 + beta) * math.sin(math.pi * beta / 2)
            / (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))
        ) ** (1 / beta)
        u = self._rng.gauss(0, sigma)
        v = self._rng.gauss(0, 1)
        step = u / (abs(v) ** (1 / beta)) if v != 0 else 0.0
        num_swaps = max(1, min(int(abs(step) * scale * n), n // 2))
        for _ in range(num_swaps):
            i, j = self._rng.sample(range(n), 2)
            new_pos[i], new_pos[j] = new_pos[j], new_pos[i]
        return new_pos

    # ----- Swap helpers (discrete velocity) ------------------------
    def _diff_swaps(self, current: List[int], target: List[int]) -> List[Tuple[int, int]]:
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

    # ----- Besiege strategies --------------------------------------
    def _soft_besiege(
        self, hawk: List[int], prey: List[int], escape_energy: float
    ) -> List[int]:
        J = 2 * (1 - self._rng.random())
        intensity = abs(escape_energy * J)
        swaps = self._diff_swaps(hawk, prey)
        kept = [s for s in swaps if self._rng.random() < intensity]
        return self._apply_swaps(hawk, kept)

    def _hard_besiege(
        self, hawk: List[int], prey: List[int], escape_energy: float
    ) -> List[int]:
        intensity = abs(escape_energy)
        swaps = self._diff_swaps(hawk, prey)
        kept = [s for s in swaps if self._rng.random() < intensity]
        return self._apply_swaps(hawk, kept)

    def _soft_besiege_with_dives(
        self, hawk: List[int], prey: List[int], escape_energy: float
    ) -> List[int]:
        """Progressive rapid dives: try ``dive_count`` Lévy-perturbed candidates."""
        best_pos = hawk[:]
        best_len = self._tour_length_fast(hawk)
        for _ in range(self.dive_count):
            intensity = abs(escape_energy) * self._rng.random()
            swaps = self._diff_swaps(hawk, prey)
            kept = [s for s in swaps if self._rng.random() < intensity]
            candidate = self._apply_swaps(hawk, kept)
            candidate = self._levy_flight(candidate, scale=self.levy_scale)
            clen = self._tour_length_fast(candidate)
            if clen < best_len:
                best_pos = candidate
                best_len = clen
        return best_pos

    def _hard_besiege_with_dives(
        self, hawk: List[int], prey: List[int], escape_energy: float
    ) -> List[int]:
        intensity = abs(escape_energy)
        swaps = self._diff_swaps(hawk, prey)
        kept = [s for s in swaps if self._rng.random() < intensity]
        candidate = self._apply_swaps(hawk, kept)
        return self._levy_flight(candidate, scale=self.levy_scale * 0.7)

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

    @staticmethod
    def _escape_energy(e0: float, iteration: int, max_iterations: int) -> float:
        return 2 * e0 * (1 - iteration / max(1, max_iterations))

    # ----- Main solve ---------------------------------------------
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        t0 = time.perf_counter()

        base = self._initial_tour_nodes()
        population: List[_Hawk] = []
        for _ in range(self.hawks):
            perm = base[:]
            self._rng.shuffle(perm)
            polished, plen = self._polish(perm, self.polish_iters)
            population.append(_Hawk(polished, 1.0 / (plen + 1e-10), plen))

        prey = min(population, key=lambda h: h.tour_length)
        prey = _Hawk(prey.position[:], prey.fitness, prey.tour_length)
        best_len = prey.tour_length
        best_chrom = prey.position[:]
        no_improve = 0
        history: List[float] = []
        last_iter = 0

        for it in range(self.max_iterations):
            last_iter = it
            history.append(float(best_len))
            e0 = 2 * self._rng.random() - 1
            E = self._escape_energy(e0, it, self.max_iterations) * self.initial_energy
            improved = False

            for hawk in population:
                r = self._rng.random()
                if abs(E) >= 1.0:
                    # Exploration
                    if self._rng.random() < 0.5:
                        intensity = self._rng.random()
                        swaps = self._diff_swaps(hawk.position, prey.position)
                        kept = [s for s in swaps if self._rng.random() < intensity]
                        new_pos = self._apply_swaps(hawk.position, kept)
                    else:
                        new_pos = self._levy_flight(hawk.position, scale=self.levy_scale)
                else:
                    # Exploitation
                    direct = r >= self.jump_probability
                    if abs(E) >= 0.5:
                        if direct:
                            new_pos = self._soft_besiege(hawk.position, prey.position, E)
                        else:
                            new_pos = self._soft_besiege_with_dives(
                                hawk.position, prey.position, E
                            )
                    else:
                        if direct:
                            new_pos = self._hard_besiege(hawk.position, prey.position, E)
                        else:
                            new_pos = self._hard_besiege_with_dives(
                                hawk.position, prey.position, E
                            )

                clen = self._tour_length_fast(new_pos)
                if clen < hawk.tour_length:
                    hawk.position = new_pos
                    hawk.tour_length = clen
                    hawk.fitness = 1.0 / (clen + 1e-10)
                    if clen < prey.tour_length:
                        prey = _Hawk(new_pos[:], hawk.fitness, clen)
                        improved = True

            if prey.tour_length < best_len:
                best_len = prey.tour_length
                best_chrom = prey.position[:]
                no_improve = 0
            else:
                no_improve += 1

            # Periodic memetic polish on the prey.
            if it > 0 and it % self.polish_interval == 0:
                polished, plen = self._polish(prey.position, self.polish_iters)
                if plen < prey.tour_length:
                    prey = _Hawk(polished[:], 1.0 / (plen + 1e-10), plen)
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
            algorithm="HHO",
            tour=best_chrom,
            tour_length=best_len,
            elapsed_ms=elapsed_ms,
            iterations=last_iter + 1,
            params={
                "hawks": self.hawks,
                "iterations": last_iter + 1,
                "initial_energy": self.initial_energy,
                "jump_probability": self.jump_probability,
                "dive_count": self.dive_count,
                "memetic": True,
                "levy_flight": True,
                "polish_interval": self.polish_interval,
            },
            history=history,
            seed=self.random_seed,
        )