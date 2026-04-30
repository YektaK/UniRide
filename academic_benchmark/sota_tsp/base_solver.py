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

    def _set_problem(self, coordinates: List[Tuple[float, float]]):
        self._coordinates = coordinates
        self._n = len(coordinates)
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
