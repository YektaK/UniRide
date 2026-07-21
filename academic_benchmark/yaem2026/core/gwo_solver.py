"""
Grey Wolf Optimizer for TSP — with Continuous Random-Key (RK) encoding and Lamarckian Memetic polish.

Reference:
Mirjalili, S., Mirjalili, S. M., & Lewis, A. (2014). Grey Wolf Optimizer.
Advances in Engineering Software, 69, 46-61.

Pure vs Memetic:
  - Memetic (default): initial polish + periodic polish + final 2-opt, updated into continuous space (Lamarckian)
  - Pure: disable all three polish stages via enable_* flags
"""

import time
import random
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .base_solver import BaseTSPSolver, TSPResult
from . import numba_accel as _nb


@dataclass
class _Wolf:
    position: np.ndarray
    route: List[int]
    fitness: float
    tour_length: float


class GWOOptimizer(BaseTSPSolver):
    """Continuous Grey Wolf Optimizer mapped to TSP via Random Keys."""

    def __init__(
        self,
        pack_size: int = 50,
        max_iterations: int = 250,
        initial_a: float = 2.0,
        exploration_rate: float = 0.4, # No longer explicitly used in continuous form
        max_no_improvement: int = 75,
        polish_interval: int = 25,
        polish_iters: int = 10,
        final_polish_iters: int = 300,
        random_seed: Optional[int] = None,
        enable_initial_polish: bool = True,
        enable_periodic_polish: bool = True,
        enable_final_polish: bool = True,
        polish_type: str = "2opt",  # "2opt", "3opt" (LKH), or "alns"
        alns_iterations: int = 50,
        alns_remove_ratio: float = 0.15,
    ):
        super().__init__("GWO-2opt", random_seed)
        self.pack_size = pack_size
        self.max_iterations = max_iterations
        self.initial_a = initial_a
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
            # 2opt
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

    def _init_wolf(self, base: List[int]) -> _Wolf:
        pos = self._np_rng.uniform(-1.0, 1.0, size=len(base))
        route = self._rk_to_route(pos)
        
        if self.enable_initial_polish:
            route, plen = self._polish(route, self.polish_iters)
            pos = self._apply_lamarckian(pos, route)
        else:
            plen = self._tour_length_fast(route)
            
        return _Wolf(pos, route, 1.0 / (plen + 1e-10), plen)

    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        t0 = time.perf_counter()

        base = self._initial_tour_nodes()
        pack: List[_Wolf] = []
        for _ in range(self.pack_size):
            pack.append(self._init_wolf(base))

        pack.sort(key=lambda w: w.tour_length)
        alpha = _Wolf(pack[0].position.copy(), pack[0].route[:], pack[0].fitness, pack[0].tour_length)
        beta = (_Wolf(pack[1].position.copy(), pack[1].route[:], pack[1].fitness, pack[1].tour_length)
                if len(pack) > 1 else _Wolf(alpha.position.copy(), alpha.route[:], alpha.fitness, alpha.tour_length))
        delta = (_Wolf(pack[2].position.copy(), pack[2].route[:], pack[2].fitness, pack[2].tour_length)
                 if len(pack) > 2 else _Wolf(beta.position.copy(), beta.route[:], beta.fitness, beta.tour_length))

        best_len = alpha.tour_length
        best_chrom = alpha.route[:]
        no_improve = 0
        history: List[float] = []
        last_iter = 0

        for it in range(self.max_iterations):
            last_iter = it
            history.append(float(best_len))
            a = self.initial_a * (1.0 - it / max(1, self.max_iterations))

            new_pack: List[_Wolf] = [
                _Wolf(alpha.position.copy(), alpha.route[:], alpha.fitness, alpha.tour_length),
                _Wolf(beta.position.copy(), beta.route[:], beta.fitness, beta.tour_length),
                _Wolf(delta.position.copy(), delta.route[:], delta.fitness, delta.tour_length),
            ]

            for wolf in pack[3:]:
                r1_a = self._np_rng.uniform(0, 1, size=len(base))
                r2_a = self._np_rng.uniform(0, 1, size=len(base))
                A1 = 2.0 * a * r1_a - a
                C1 = 2.0 * r2_a
                D_alpha = np.abs(C1 * alpha.position - wolf.position)
                X1 = alpha.position - A1 * D_alpha
                
                r1_b = self._np_rng.uniform(0, 1, size=len(base))
                r2_b = self._np_rng.uniform(0, 1, size=len(base))
                A2 = 2.0 * a * r1_b - a
                C2 = 2.0 * r2_b
                D_beta = np.abs(C2 * beta.position - wolf.position)
                X2 = beta.position - A2 * D_beta
                
                r1_d = self._np_rng.uniform(0, 1, size=len(base))
                r2_d = self._np_rng.uniform(0, 1, size=len(base))
                A3 = 2.0 * a * r1_d - a
                C3 = 2.0 * r2_d
                D_delta = np.abs(C3 * delta.position - wolf.position)
                X3 = delta.position - A3 * D_delta
                
                new_pos = (X1 + X2 + X3) / 3.0
                new_pos = np.clip(new_pos, -10.0, 10.0)
                
                route = self._rk_to_route(new_pos)
                clen = self._tour_length_fast(route)
                
                if clen < alpha.tour_length:
                    delta = _Wolf(beta.position.copy(), beta.route[:], beta.fitness, beta.tour_length)
                    beta = _Wolf(alpha.position.copy(), alpha.route[:], alpha.fitness, alpha.tour_length)
                    alpha = _Wolf(new_pos.copy(), route[:], 1.0 / (clen + 1e-10), clen)
                elif clen < beta.tour_length:
                    delta = _Wolf(beta.position.copy(), beta.route[:], beta.fitness, beta.tour_length)
                    beta = _Wolf(new_pos.copy(), route[:], 1.0 / (clen + 1e-10), clen)
                elif clen < delta.tour_length:
                    delta = _Wolf(new_pos.copy(), route[:], 1.0 / (clen + 1e-10), clen)

                new_pack.append(_Wolf(new_pos, route, 1.0 / (clen + 1e-10), clen))

            new_pack.sort(key=lambda w: w.tour_length)
            pack = new_pack

            if alpha.tour_length < best_len:
                best_len = alpha.tour_length
                best_chrom = alpha.route[:]
                no_improve = 0
            else:
                no_improve += 1

            if self.enable_periodic_polish and it > 0 and it % self.polish_interval == 0:
                polished, plen = self._polish(alpha.route, self.polish_iters)
                if plen < alpha.tour_length:
                    new_pos = self._apply_lamarckian(alpha.position, polished)
                    alpha = _Wolf(new_pos, polished[:], 1.0 / (plen + 1e-10), plen)
                    pack[0] = alpha
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
                "pack_size": self.pack_size,
                "iterations": last_iter + 1,
                "initial_a": self.initial_a,
                "memetic": self.enable_initial_polish or self.enable_periodic_polish or self.enable_final_polish,
                "polish_type": self.polish_type,
                "polish_interval": self.polish_interval,
                "encoding": "random-key-lamarckian",
            },
            history=history,
            seed=self.random_seed,
        )


class PureGWOOptimizer(GWOOptimizer):
    """GWO without any 2-opt polish — pure metaheuristic."""

    def __init__(self, **kwargs):
        kwargs.setdefault('enable_initial_polish', False)
        kwargs.setdefault('enable_periodic_polish', False)
        kwargs.setdefault('enable_final_polish', False)
        super().__init__(**kwargs)
        self.name = "GWO-Pure"


class GWO_LKH_Optimizer(GWOOptimizer):
    """GWO with LKH-inspired 3-opt polish."""

    def __init__(self, **kwargs):
        kwargs.setdefault('polish_type', '3opt')
        super().__init__(**kwargs)
        self.name = "GWO-LKH"


class GWO_ALNS_Optimizer(GWOOptimizer):
    """GWO with Adaptive Large Neighborhood Search polish."""

    def __init__(self, **kwargs):
        kwargs.setdefault('polish_type', 'alns')
        super().__init__(**kwargs)
        self.name = "GWO-ALNS"
