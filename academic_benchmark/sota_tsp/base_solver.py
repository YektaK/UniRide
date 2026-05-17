"""
Base solver interface for TSP — SOTA TSP variants.

Same interface as bildiri2026/core/base_solver.py so solvers are
interchangeable in the benchmark runner.
"""

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False


@dataclass
class TSPResult:
    algorithm: str
    tour: List[int]
    tour_length: float
    elapsed_ms: float
    iterations: int
    params: dict
    history: Optional[List[float]] = None
    seed: Optional[int] = None


class BaseTSPSolver(ABC):

    def __init__(self, name: str, random_seed: Optional[int] = None):
        self.name = name
        self.random_seed = random_seed
        self._coordinates: List[Tuple[float, float]] = []
        self._n: int = 0
        self._dist_matrix: Optional[List[List[float]]] = None
        self._dist_matrix_np = None
        self._precomputed_matrix: Optional[object] = None

    def set_dist_matrix(self, dm: object) -> None:
        """Inject precomputed distance matrix (correct for all edge weight types).

        Call BEFORE solve(). When set, _set_problem() uses this matrix
        directly instead of building a Euclidean distance matrix from coordinates.
        Pass None to clear and revert to default Euclidean build.

        Args:
            dm: numpy array (n, n) or list-of-lists of distances. Must match
                the problem dimension. The solver will convert to its internal
                format (List[List[float]] + optional np.ndarray).
        """
        self._precomputed_matrix = dm

    def _set_problem(self, coordinates: List[Tuple[float, float]]):
        self._coordinates = coordinates
        self._n = len(coordinates)
        if self._precomputed_matrix is not None:
            pm = self._precomputed_matrix
            if _NUMPY_AVAILABLE and hasattr(pm, 'dtype'):
                self._dist_matrix_np = pm.astype(np.float64, copy=False)
                self._dist_matrix = pm.tolist()
            elif _NUMPY_AVAILABLE:
                self._dist_matrix_np = np.array(pm, dtype=np.float64)
                self._dist_matrix = pm
            else:
                self._dist_matrix = pm
                self._dist_matrix_np = None
            return
        self._dist_matrix = self._build_dist_matrix(coordinates)
        if _NUMPY_AVAILABLE and self._dist_matrix is not None:
            self._dist_matrix_np = np.array(self._dist_matrix, dtype=np.float64)

    def _build_dist_matrix(self, coordinates: List[Tuple[float, float]]) -> List[List[float]]:
        n = len(coordinates)
        dm = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dm[i][j] = self.euclidean_distance(coordinates[i], coordinates[j])
        return dm

    @staticmethod
    def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return int(math.sqrt(dx * dx + dy * dy) + 0.5)

    def tour_length(self, tour: List[int]) -> float:
        if not tour or len(tour) < 2:
            return 0.0
        total = 0.0
        n = len(tour)
        for i in range(n):
            total += self._dist_matrix[tour[i]][tour[(i + 1) % n]]
        return total

    @abstractmethod
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        pass
