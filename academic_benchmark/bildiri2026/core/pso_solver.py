
"""
Particle Swarm Optimization for TSP

Reference:
Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization.
Proceedings of ICNN'95 - International Conference on Neural Networks, 1942-1948.

Clerc, M., & Kennedy, J. (2002). The particle swarm - explosion,
stability, and convergence in a multidimensional complex space.
IEEE Transactions on Evolutionary Computation, 6(1), 58-73.

Memetic PSO Features:
- Discrete permutation-based representation
- Swap-sequence velocity
- Clerc's constriction factor
- Periodic re-initialization for diversity
- Final 2-opt polishing (Memetic)
"""

import time
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .base_solver import BaseTSPSolver, TSPResult


@dataclass
class _Particle:
    position: List[int]
    velocity: List[Tuple[int, int]]
    personal_best: List[int]
    personal_best_len: float
    current_len: float


class PSOOptimizer(BaseTSPSolver):
    """Memetic Discrete PSO for TSP."""

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
    ):
        super().__init__("PSO", random_seed)
        self.swarm_size = swarm_size
        self.max_iterations = max_iterations
        self.inertia_weight = inertia_weight
        self.cognitive_coeff = cognitive_coeff
        self.social_coeff = social_coeff
        self.max_velocity_size = max_velocity_size
        self.max_no_improvement = max_no_improvement
        self.reinit_interval = reinit_interval
        self._rng = random.Random(self.random_seed)

    # ----- Local search ------------------------------------------
    def _two_opt_fast(self, tour: List[int], max_iter: int = 200) -> Tuple[List[int], float]:
        best = tour[:]
        best_len = self.tour_length(best)
        improved = True
        itr = 0
        n = len(best)
        while improved and itr < max_iter and n > 3:
            improved = False
            for i in range(n - 1):
                for j in range(i + 2, n):
                    new_tour = best[:i + 1] + best[i + 1:j + 1][::-1] + best[j + 1:]
                    new_len = self.tour_length(new_tour)
                    if new_len < best_len:
                        best = new_tour
                        best_len = new_len
                        improved = True
                        break
                if improved:
                    break
            itr += 1
        return best, best_len

    # ----- Velocity helpers --------------------------------------
    def _diff_swaps(self, current: List[int], target: List[int]) -> List[Tuple[int, int]]:
        """List of swap ops to transform current into target."""
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

    def _apply_swaps(self, position: List[int], swaps: List[Tuple[int, int]]) -> List[int]:
        new_pos = position[:]
        for i, j in swaps:
            new_pos[i], new_pos[j] = new_pos[j], new_pos[i]
        return new_pos

    def _combine_velocities(
        self, inertia_v: List[Tuple[int, int]], cog_v: List[Tuple[int, int]], soc_v: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Clerc-style probabilistic combination."""
        new_v = []
        # Inertia component
        for swap in inertia_v:
            if self._rng.random() < self.inertia_weight:
                new_v.append(swap)
        # Cognitive
        for swap in cog_v:
            if self._rng.random() < self.cognitive_coeff / 3.0:
                new_v.append(swap)
        # Social
        for swap in soc_v:
            if self._rng.random() < self.social_coeff / 3.0:
                new_v.append(swap)
        # Limit size
        if len(new_v) > self.max_velocity_size:
            new_v = self._rng.sample(new_v, self.max_velocity_size)
        return new_v

    # ----- Diversity: periodic re-initialization -----------------
    def _reinit_swarm(self, swarm: List[_Particle], global_best: List[int]) -> List[_Particle]:
        new_swarm = []
        for p in swarm:
            # Keep personal best; re-init current position around best
            if self._rng.random() < 0.9:
                pos = p.personal_best[:]
                # Small perturbation
                for _ in range(self._rng.randint(1, 3)):
                    i, j = self._rng.sample(range(len(pos)), 2)
                    pos[i], pos[j] = pos[j], pos[i]
            else:
                pos = self._initial_tour_nodes()
                self._rng.shuffle(pos)
            pos, plen = self._two_opt_fast(pos, max_iter=30)
            vel = [(self._rng.randint(0, len(pos)-1), self._rng.randint(0, len(pos)-1)) for _ in range(self.max_velocity_size)]
            new_swarm.append(_Particle(pos, vel, p.personal_best, p.personal_best_len, plen))
        return new_swarm

    # ----- Main solve --------------------------------------------
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        t0 = time.perf_counter()

        # Initialize swarm
        swarm = []
        global_best = self._initial_tour_nodes()
        global_best_len = float("inf")

        for _ in range(self.swarm_size):
            pos = self._initial_tour_nodes()
            self._rng.shuffle(pos)
            pos, plen = self._two_opt_fast(pos, max_iter=30)
            vel = [(self._rng.randint(0, len(pos)-1), self._rng.randint(0, len(pos)-1)) for _ in range(self.max_velocity_size)]
            p = _Particle(pos, vel, pos[:], plen, plen)
            swarm.append(p)
            if plen < global_best_len:
                global_best_len = plen
                global_best = pos[:]

        no_improve_count = 0

        for iteration in range(self.max_iterations):
            improved = False

            for p in swarm:
                # Update velocity
                cog_v = self._diff_swaps(p.position, p.personal_best)
                soc_v = self._diff_swaps(p.position, global_best)
                p.velocity = self._combine_velocities(p.velocity, cog_v, soc_v)

                # Update position
                p.position = self._apply_swaps(p.position, p.velocity)
                p.current_len = self.tour_length(p.position)

                # Update personal best
                if p.current_len < p.personal_best_len:
                    p.personal_best = p.position[:]
                    p.personal_best_len = p.current_len

                # Update global best
                if p.current_len < global_best_len:
                    global_best_len = p.current_len
                    global_best = p.position[:]
                    improved = True

            if improved:
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Re-initialize swarm periodically to maintain diversity
            if iteration > 0 and iteration % self.reinit_interval == 0:
                swarm = self._reinit_swarm(swarm, global_best)
                # Evaluate re-initialized swarm
                for p in swarm:
                    p.current_len = self.tour_length(p.position)
                    if p.current_len < p.personal_best_len:
                        p.personal_best = p.position[:]
                        p.personal_best_len = p.current_len
                    if p.current_len < global_best_len:
                        global_best_len = p.current_len
                        global_best = p.position[:]

            if no_improve_count >= self.max_no_improvement:
                break

        # Final aggressive 2-opt on global best
        global_best, global_best_len = self._two_opt_fast(global_best, max_iter=300)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm="PSO",
            tour=global_best,
            tour_length=global_best_len,
            elapsed_ms=elapsed_ms,
            iterations=iteration + 1,
            params={
                "swarm_size": self.swarm_size,
                "iterations": iteration + 1,
                "inertia_weight": self.inertia_weight,
                "cognitive_coeff": self.cognitive_coeff,
                "social_coeff": self.social_coeff,
                "memetic": True,
                "reinit_interval": self.reinit_interval,
            },
            seed=self.random_seed,
        )
