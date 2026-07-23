"""
2-opt Local Search Algorithm for TSP (with optional Numba JIT)

Reference:
Croes, G. (1958). A method for solving traveling salesman problems.
Operations Research, 6(6), 791-812.
"""

import time
import random
from typing import List, Tuple, Optional
from .base_solver import BaseTSPSolver, TSPResult

from . import numba_accel as _nb
_NUMBA_OK = _nb.NUMBA_AVAILABLE


class TwoOptSolver(BaseTSPSolver):
    """
    2-opt Local Search for TSP.
    Uses Numba JIT if available for 10-50x speedup.
    """
    
    def __init__(
        self,
        max_iterations: int = 10000,
        first_improvement: bool = False,
        multi_start: bool = True,
        num_starts: int = 10,
        random_seed: Optional[int] = None
    ):
        super().__init__("2-opt", random_seed)
        self.max_iterations = max_iterations
        self.first_improvement = first_improvement
        self.multi_start = multi_start
        self.num_starts = num_starts
    
    def _two_opt_swap(self, tour: List[int], i: int, j: int) -> List[int]:
        new_tour = tour[:i]
        new_tour.extend(reversed(tour[i:j + 1]))
        new_tour.extend(tour[j + 1:])
        return new_tour
    
    def _improve_tour(self, tour: List[int]) -> Tuple[List[int], float, int]:
        if _NUMBA_OK and self._dist_matrix is not None:
            improved, length = _nb.nb_two_opt(
                tour, self._dist_matrix,
                self.max_iterations, self.first_improvement
            )
            return improved, length, 0

        best_tour = tour.copy()
        best_length = self.tour_length(best_tour)
        improved = True
        iterations = 0
        
        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1
            
            for i in range(len(best_tour) - 1):
                for j in range(i + 1, len(best_tour)):
                    new_tour = self._two_opt_swap(best_tour, i, j)
                    new_length = self.tour_length(new_tour)
                    
                    if new_length < best_length:
                        best_tour = new_tour
                        best_length = new_length
                        improved = True
                        
                        if self.first_improvement:
                            break
                
                if improved and self.first_improvement:
                    break
        
        return best_tour, best_length, iterations
    
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        self._set_problem(coordinates)
        rng = random.Random(self.random_seed)
        
        start_time = time.perf_counter()
        
        if self.multi_start:
            best_overall_tour = None
            best_overall_length = float('inf')
            total_iterations = 0
            
            for start_idx in range(self.num_starts):
                nodes = self._initial_tour_nodes()
                rng.shuffle(nodes)
                
                improved_tour, length, iters = self._improve_tour(nodes)
                total_iterations += iters
                
                if length < best_overall_length:
                    best_overall_length = length
                    best_overall_tour = improved_tour
            
            final_tour = best_overall_tour
            final_length = best_overall_length
            iterations = total_iterations
        else:
            nodes = self._initial_tour_nodes()
            rng.shuffle(nodes)
            final_tour, final_length, iterations = self._improve_tour(nodes)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return TSPResult(
            algorithm="2-opt",
            tour=final_tour,
            tour_length=final_length,
            elapsed_ms=elapsed_ms,
            iterations=iterations,
            params={
                "max_iterations": self.max_iterations,
                "first_improvement": self.first_improvement,
                "multi_start": self.multi_start,
                "num_starts": self.num_starts if self.multi_start else 1,
            },
            seed=self.random_seed
        )
