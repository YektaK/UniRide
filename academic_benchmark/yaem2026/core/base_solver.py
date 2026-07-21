"""
Base solver interface for TSP optimization algorithms.
All algorithms implement this interface for uniform benchmarking.

Supports both:
- Euclidean coordinates (TSPLIB standard)
- Time/distance matrix (real-world data)
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import time
import math
try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

from academic_benchmark.engine_core import TSPResult


class BaseTSPSolver(ABC):
    """Abstract base class for all TSP solvers."""
    
    def __init__(self, name: str, random_seed: Optional[int] = None, exclude_depot: bool = False):
        self.name = name
        self.random_seed = random_seed
        self._exclude_depot = exclude_depot
        self._coordinates: List[Tuple[float, float]] = []
        self._n: int = 0
        self._time_matrix: Optional[List[List[float]]] = None
        self._use_time_matrix: bool = False
        self._dist_matrix: Optional[List[List[float]]] = None
        self._dist_matrix_np = None

    def _initial_tour_nodes(self) -> List[int]:
        if self._exclude_depot or self._use_time_matrix:
            return list(range(1, self._n))
        return list(range(self._n))
    
    def _set_problem(self, coordinates: List[Tuple[float, float]]):
        self._coordinates = coordinates
        self._n = len(coordinates)
        if self._use_time_matrix and self._time_matrix is not None:
            self._dist_matrix = self._time_matrix
        else:
            self._dist_matrix = self._build_dist_matrix(coordinates)
        self._build_np_cache()
    
    def _build_dist_matrix(self, coordinates: List[Tuple[float, float]]) -> List[List[float]]:
        n = len(coordinates)
        dm = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dm[i][j] = self.euclidean_distance(coordinates[i], coordinates[j])
        return dm
    
    def _set_time_matrix(self, time_matrix: List[List[float]]):
        self._time_matrix = time_matrix
        self._use_time_matrix = True
        self._n = len(time_matrix)
        self._coordinates = [(0.0, 0.0) for _ in range(self._n)]
        self._dist_matrix = time_matrix
        self._build_np_cache()
    
    def _build_np_cache(self):
        if _NUMPY_AVAILABLE and self._dist_matrix is not None:
            self._dist_matrix_np = np.array(self._dist_matrix, dtype=np.float64)
        else:
            self._dist_matrix_np = None

    def _tour_length_fast(self, tour: List[int]) -> float:
        if self._dist_matrix_np is not None:
            try:
                from . import numba_accel as _nb
                import numpy as _np
                route_np = _nb._prepare_route(tour)
                length = _nb._calculate_tour_length_atsp_numba(route_np, self._dist_matrix_np)
                return float(length)
            except Exception:
                pass
        return self.tour_length(tour)

    @staticmethod
    def _matrix_to_coordinates(time_matrix: List[List[float]]) -> List[Tuple[float, float]]:
        import numpy as np
        n = len(time_matrix)
        D = np.array(time_matrix, dtype=float)
        H = np.eye(n) - np.ones((n, n)) / n
        B = -0.5 * H @ (D ** 2) @ H
        eigenvalues, eigenvectors = np.linalg.eigh(B)
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        coords = eigenvectors[:, :2] * np.sqrt(np.maximum(eigenvalues[:2], 0))
        return [(float(coords[i, 0]), float(coords[i, 1])) for i in range(n)]
    
    @staticmethod
    def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return int(math.sqrt(dx * dx + dy * dy) + 0.5)
    
    def tour_length(self, tour: List[int]) -> float:
        if self._use_time_matrix and self._time_matrix is not None:
            return self._tour_length_matrix(tour)
        else:
            return self._tour_length_euclidean(tour)
    
    def _tour_length_euclidean(self, tour: List[int]) -> float:
        if not tour or len(tour) < 2:
            return 0.0
        total = 0.0
        for i in range(len(tour)):
            from_node = tour[i]
            to_node = tour[(i + 1) % len(tour)]
            total += self.euclidean_distance(
                self._coordinates[from_node],
                self._coordinates[to_node]
            )
        return total
    
    def _tour_length_matrix(self, tour: List[int]) -> float:
        total = 0.0
        nodes = [0] + tour + [0]
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            total += self._time_matrix[from_node][to_node]
        return total
    
    @abstractmethod
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        pass
    
    def solve_with_matrix(self, time_matrix: List[List[float]], recalculate: bool = True) -> TSPResult:
        self._set_time_matrix(time_matrix)
        result = self.solve(self._coordinates)
        if recalculate:
            result.tour_length = self._tour_length_matrix(result.tour)
        return result
    
    def _random_tour(self) -> List[int]:
        import random
        rng = random.Random(self.random_seed)
        nodes = list(range(1, self._n))
        rng.shuffle(nodes)
        return nodes
