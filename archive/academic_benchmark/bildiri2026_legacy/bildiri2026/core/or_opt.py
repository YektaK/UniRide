"""Or-opt Local Search Algorithm for TSP (with optional Numba JIT)."""
import time
import random
import warnings
from typing import List, Tuple, Optional
from .base_solver import BaseTSPSolver, TSPResult
from . import numba_accel as _nb
_NUMBA_OK = _nb.NUMBA_AVAILABLE


class OrOptSolver(BaseTSPSolver):
    """Or-opt Local Search for TSP. Uses Numba JIT if available."""

    def __init__(
        self,
        max_iterations: int = 1000,
        max_segment_size: int = 3,
        first_improvement: bool = True,
        multi_start: bool = False,
        num_starts: int = 10,
        random_seed: Optional[int] = None
    ):
        super().__init__("Or-opt", random_seed)
        if max_segment_size > 3:
            warnings.warn(
                f"Or-opt: max_segment_size={max_segment_size} capped to 3 (algorithm limitation)",
                UserWarning
            )
        self.max_iterations = max_iterations
        self.max_segment_size = min(max_segment_size, 3)
        self.first_improvement = first_improvement
        self.multi_start = multi_start
        self.num_starts = num_starts

    def _relocate_segment(self, tour, start, segment_size, insert_pos):
        segment = tour[start:start + segment_size]
        remaining = tour[:start] + tour[start + segment_size:]
        if insert_pos > start:
            insert_pos -= segment_size
        return remaining[:insert_pos] + segment + remaining[insert_pos:]

    def _improve_tour(self, tour):
        if _NUMBA_OK and self._dist_matrix is not None:
            improved, length = _nb.nb_or_opt(
                tour, self._dist_matrix,
                self.max_iterations, self.max_segment_size
            )
            return improved, length, 0

        best_tour = list(tour)
        best_length = self.tour_length(best_tour)
        n = len(best_tour)
        if n < 4:
            return best_tour, best_length, 0

        total_iterations = 0
        no_improve_count = 0
        max_no_improve = self.max_iterations

        while no_improve_count < max_no_improve and total_iterations < self.max_iterations * 2:
            improved_this_pass = False
            total_iterations += 1

            for segment_size in range(1, self.max_segment_size + 1):
                for start in range(n - segment_size + 1):
                    segment = best_tour[start:start + segment_size]
                    remaining = best_tour[:start] + best_tour[start + segment_size:]
                    for insert_pos in range(len(remaining) + 1):
                        if insert_pos == start:
                            continue
                        new_tour = remaining[:insert_pos] + segment + remaining[insert_pos:]
                        new_length = self.tour_length(new_tour)
                        if new_length < best_length - 1e-9:
                            best_tour = new_tour
                            best_length = new_length
                            improved_this_pass = True
                            no_improve_count = 0
                            if self.first_improvement:
                                break
                    if improved_this_pass and self.first_improvement:
                        break
                if improved_this_pass and self.first_improvement:
                    break

            if not improved_this_pass:
                no_improve_count += 1
            else:
                # Tur değişti, boyutu kontrol et
                n = len(best_tour)

        return best_tour, best_length, total_iterations
    
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        """Solve TSP using Or-opt local search."""
        self._set_problem(coordinates)
        rng = random.Random(self.random_seed)
        
        start_time = time.perf_counter()
        
        if self.multi_start:
            best_overall_tour = None
            best_overall_length = float('inf')
            total_iterations = 0
            
            for _ in range(self.num_starts):
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
            algorithm="Or-opt",
            tour=final_tour,
            tour_length=final_length,
            elapsed_ms=elapsed_ms,
            iterations=iterations,
            params={
                "max_iterations": self.max_iterations,
                "max_segment_size": self.max_segment_size,
                "multi_start": self.multi_start,
                "num_starts": self.num_starts if self.multi_start else 1,
            },
            seed=self.random_seed
        )