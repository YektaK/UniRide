"""
Harris Hawks Optimization for TSP — with Continuous Random-Key (RK) encoding and Lamarckian Memetic polish.
"""

import time
import random
import math
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .base_solver import BaseTSPSolver, TSPResult
from . import numba_accel as _nb


@dataclass
class _Hawk:
    position: np.ndarray
    route: List[int]
    fitness: float
    tour_length: float


class HHOOptimizer(BaseTSPSolver):
    """Continuous Harris Hawks Optimization mapped to TSP via Random Keys."""

    def __init__(
        self,
        hawks: int = 50,
        max_iterations: int = 250,
        max_no_improvement: int = 75,
        polish_interval: int = 25,
        polish_iters: int = 10,
        final_polish_iters: int = 300,
        random_seed: Optional[int] = None,
        enable_initial_polish: bool = True,
        enable_periodic_polish: bool = True,
        enable_final_polish: bool = True,
        polish_type: str = "2opt",
        alns_iterations: int = 50,
        alns_remove_ratio: float = 0.15,
        initial_energy: float = 1.0,
        jump_probability: float = 0.5,
        dive_count: int = 3,
        levy_scale: float = 0.3,
    ):
        super().__init__("HHO-2opt", random_seed)
        self.hawks_count = hawks
        self.max_iterations = max_iterations
        self.max_no_improvement = max_no_improvement
        self.polish_interval = polish_interval
        self.polish_iters = polish_iters
        self.final_polish_iters = final_polish_iters
        self.enable_initial_polish = enable_initial_polish
        self.enable_periodic_polish = enable_periodic_polish
        self.enable_final_polish = enable_final_polish
        self.polish_type = polish_type
        self.alns_iterations = alns_iterations
        self.alns_remove_ratio = alns_remove_ratio
        
        self.initial_energy = initial_energy
        self.jump_probability = jump_probability
        self.dive_count = dive_count
        self.levy_scale = levy_scale
        
        self._np_rng = np.random.RandomState(self.random_seed)

    def _rk_to_route(self, position: np.ndarray) -> List[int]:
        base = self._initial_tour_nodes()
        sorted_indices = np.argsort(position)
        return [base[i] for i in sorted_indices]

    def _apply_lamarckian(self, position: np.ndarray, polished_route: List[int]) -> np.ndarray:
        base = self._initial_tour_nodes()
        sorted_vals = np.sort(position)
        new_pos = np.zeros_like(position)
        base_indices = {node: i for i, node in enumerate(base)}
        for rank, node in enumerate(polished_route):
            idx_in_base = base_indices[node]
            new_pos[idx_in_base] = sorted_vals[rank]
        return new_pos

    def _polish(self, route: List[int], iters: int) -> Tuple[List[int], float]:
        if self.polish_type == "alns":
            try:
                from uniride_core.algorithms.sota_tsp.alns_tsp import ALNS_TSP, ALNSConfig
                cfg = ALNSConfig(iterations=self.alns_iterations, remove_ratio=self.alns_remove_ratio, use_sa=True, sa_start_temp=10.0, seed=self.random_seed or 42)
                alns = ALNS_TSP(cfg)
                if self._dist_matrix is not None:
                    alns._dist_matrix = self._dist_matrix
                    alns._n = len(self._dist_matrix)
                elif self._dist_matrix_np is not None:
                    alns._dist_matrix = self._dist_matrix_np.tolist()
                    alns._n = len(self._dist_matrix_np)
                
                # Prepare route (include 0)
                full_route = route[:]
                if 0 not in full_route:
                    full_route = [0] + full_route
                    
                alns._nearest_neighbor_tour = lambda: full_route[:]
                res = alns._solve()
                
                # Extract route back (remove 0)
                final_tour = res.tour
                if 0 not in route:
                    idx = final_tour.index(0)
                    rotated = final_tour[idx:] + final_tour[:idx]
                    return rotated[1:], float(res.tour_length)
                else:
                    return final_tour, float(res.tour_length)
            except Exception as e:
                print(f"ALNS polish error: {e}")
                return route[:], self.tour_length(route)
        elif self.polish_type == "3opt":
            if self._dist_matrix_np is not None:
                route_np = _nb._prepare_route(route)
                improved_np, length = _nb._three_opt_improve_atsp_numba(
                    route_np, self._dist_matrix_np, iters, False
                )
                return _nb._extract_route(improved_np, route), float(length)
            elif self._dist_matrix is not None:
                improved, length = _nb.nb_three_opt(route, self._dist_matrix, iters, False)
                return improved, float(length)
            return route[:], self.tour_length(route)
        else:
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

    def _init_hawk(self, base: List[int]) -> _Hawk:
        pos = self._np_rng.uniform(-1.0, 1.0, size=len(base))
        route = self._rk_to_route(pos)
        
        if self.enable_initial_polish:
            route, plen = self._polish(route, self.polish_iters)
            pos = self._apply_lamarckian(pos, route)
        else:
            plen = self._tour_length_fast(route)
            
        return _Hawk(pos, route, 1.0 / (plen + 1e-10), plen)

    def _levy(self, dim: int) -> np.ndarray:
        beta = 1.5
        sigma = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2) / 
                 (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
        u = self._np_rng.normal(0, sigma, size=dim)
        v = self._np_rng.normal(0, 1, size=dim)
        step = u / (np.abs(v) ** (1 / beta))
        return step

    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        t0 = time.perf_counter()

        base = self._initial_tour_nodes()
        dim = len(base)
        pack: List[_Hawk] = []
        for _ in range(self.hawks_count):
            pack.append(self._init_hawk(base))

        pack.sort(key=lambda h: h.tour_length)
        prey = _Hawk(pack[0].position.copy(), pack[0].route[:], pack[0].fitness, pack[0].tour_length)
        
        best_len = prey.tour_length
        best_chrom = prey.route[:]
        no_improve = 0
        history: List[float] = []
        last_iter = 0

        for it in range(self.max_iterations):
            last_iter = it
            history.append(float(best_len))

            E0 = 2 * self._np_rng.uniform() - 1
            E = 2 * E0 * (1 - it / max(1, self.max_iterations))
            abs_E = abs(E)
            
            mean_pos = np.mean([w.position for w in pack], axis=0)

            for hawk in pack:
                q = self._np_rng.uniform()
                if abs_E >= 1.0:
                    # Exploration phase
                    if q >= 0.5:
                        r_hawk = pack[self._np_rng.randint(0, len(pack))]
                        r1 = self._np_rng.uniform(0, 1, size=dim)
                        r2 = self._np_rng.uniform(0, 1, size=dim)
                        new_pos = r_hawk.position - r1 * np.abs(r_hawk.position - 2.0 * r2 * hawk.position)
                    else:
                        r3 = self._np_rng.uniform(0, 1, size=dim)
                        r4 = self._np_rng.uniform(0, 1, size=dim)
                        new_pos = (prey.position - mean_pos) - r3 * (-1.0 + r4 * 2.0)
                else:
                    # Exploitation phase
                    r = self._np_rng.uniform()
                    if r >= 0.5 and abs_E >= 0.5:
                        # Soft besiege
                        J = 2.0 * (1.0 - self._np_rng.uniform(0, 1, size=dim))
                        delta_X = prey.position - hawk.position
                        new_pos = prey.position - E * np.abs(J * prey.position - hawk.position)
                    elif r >= 0.5 and abs_E < 0.5:
                        # Hard besiege
                        delta_X = prey.position - hawk.position
                        new_pos = prey.position - E * np.abs(delta_X)
                    elif r < 0.5 and abs_E >= 0.5:
                        # Soft besiege with progressive rapid dives
                        J = 2.0 * (1.0 - self._np_rng.uniform(0, 1, size=dim))
                        Y = prey.position - E * np.abs(J * prey.position - hawk.position)
                        route_Y = self._rk_to_route(Y)
                        len_Y = self._tour_length_fast(route_Y)
                        if len_Y < hawk.tour_length:
                            new_pos = Y
                        else:
                            Z = Y + self._np_rng.uniform(size=dim) * self._levy(dim)
                            route_Z = self._rk_to_route(Z)
                            len_Z = self._tour_length_fast(route_Z)
                            if len_Z < hawk.tour_length:
                                new_pos = Z
                            else:
                                new_pos = hawk.position.copy()
                    elif r < 0.5 and abs_E < 0.5:
                        # Hard besiege with progressive rapid dives
                        J = 2.0 * (1.0 - self._np_rng.uniform(0, 1, size=dim))
                        Y = prey.position - E * np.abs(J * prey.position - mean_pos)
                        route_Y = self._rk_to_route(Y)
                        len_Y = self._tour_length_fast(route_Y)
                        if len_Y < hawk.tour_length:
                            new_pos = Y
                        else:
                            Z = Y + self._np_rng.uniform(size=dim) * self._levy(dim)
                            route_Z = self._rk_to_route(Z)
                            len_Z = self._tour_length_fast(route_Z)
                            if len_Z < hawk.tour_length:
                                new_pos = Z
                            else:
                                new_pos = hawk.position.copy()

                new_pos = np.clip(new_pos, -10.0, 10.0)
                route = self._rk_to_route(new_pos)
                clen = self._tour_length_fast(route)

                hawk.position = new_pos
                hawk.route = route
                hawk.tour_length = clen
                hawk.fitness = 1.0 / (clen + 1e-10)

                if clen < prey.tour_length:
                    prey = _Hawk(new_pos.copy(), route[:], hawk.fitness, clen)

            if prey.tour_length < best_len:
                best_len = prey.tour_length
                best_chrom = prey.route[:]
                no_improve = 0
            else:
                no_improve += 1

            if self.enable_periodic_polish and it > 0 and it % self.polish_interval == 0:
                polished, plen = self._polish(prey.route, self.polish_iters)
                if plen < prey.tour_length:
                    new_pos = self._apply_lamarckian(prey.position, polished)
                    prey = _Hawk(new_pos, polished[:], 1.0 / (plen + 1e-10), plen)
                    if plen < best_len:
                        best_len = plen
                        best_chrom = polished[:]
                        no_improve = 0

            if no_improve >= self.max_no_improvement:
                break

        if self.enable_final_polish:
            polished, best_len = self._polish(best_chrom, self.final_polish_iters)
            best_chrom = polished

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TSPResult(
            algorithm=self.name,
            tour=best_chrom,
            tour_length=best_len,
            elapsed_ms=elapsed_ms,
            iterations=last_iter + 1,
            params={
                "hawks": self.hawks_count,
                "iterations": last_iter + 1,
                "memetic": self.enable_initial_polish or self.enable_periodic_polish or self.enable_final_polish,
                "polish_type": self.polish_type,
                "polish_interval": self.polish_interval,
                "encoding": "random-key-lamarckian",
            },
            history=history,
            seed=self.random_seed,
        )


class PureHHOOptimizer(HHOOptimizer):
    """HHO without any 2-opt polish — pure metaheuristic."""

    def __init__(self, **kwargs):
        kwargs.setdefault('enable_initial_polish', False)
        kwargs.setdefault('enable_periodic_polish', False)
        kwargs.setdefault('enable_final_polish', False)
        super().__init__(**kwargs)
        self.name = "HHO-Pure"


class HHO_LKH_Optimizer(HHOOptimizer):
    """HHO with LKH-inspired 3-opt polish."""

    def __init__(self, **kwargs):
        kwargs.setdefault('polish_type', '3opt')
        super().__init__(**kwargs)
        self.name = "HHO-LKH"


class HHO_ALNS_Optimizer(HHOOptimizer):
    """HHO with Adaptive Large Neighborhood Search polish."""

    def __init__(self, **kwargs):
        kwargs.setdefault('polish_type', 'alns')
        super().__init__(**kwargs)
        self.name = "HHO-ALNS"
