"""
Base solver interface for TSP optimization algorithms.
All algorithms implement this interface for uniform benchmarking.

Supports both:
- Euclidean coordinates (TSPLIB standard)
- Time/distance matrix (real-world data)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional
import time
import math


@dataclass
class TSPResult:
    """Standardized result format for all TSP solvers."""
    algorithm: str
    tour: List[int]           # Node indices in visit order (0 = depot)
    tour_length: float        # Total distance or time
    elapsed_ms: float         # Execution time in milliseconds
    iterations: int           # Number of iterations/generations
    params: dict              # Algorithm parameters used
    seed: Optional[int] = None


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
        self._dist_matrix: Optional[List[List[float]]] = None  # cached for numba speedup

    def _initial_tour_nodes(self) -> List[int]:
        """Return initial node list. For time matrix, exclude depot(0); for TSP use all nodes."""
        if self._exclude_depot or self._use_time_matrix:
            return list(range(1, self._n))
        return list(range(self._n))
    
    def _set_problem(self, coordinates: List[Tuple[float, float]]):
        """Load problem coordinates and cache distance matrix."""
        self._coordinates = coordinates
        self._n = len(coordinates)
        # Keep the original matrix when solving matrix-based problems.
        # Otherwise, pseudo-coordinates would rebuild a zero Euclidean matrix.
        if self._use_time_matrix and self._time_matrix is not None:
            self._dist_matrix = self._time_matrix
        else:
            self._dist_matrix = self._build_dist_matrix(coordinates)
    
    def _build_dist_matrix(self, coordinates: List[Tuple[float, float]]) -> List[List[float]]:
        """Pre-compute full Euclidean distance matrix for numba JIT."""
        n = len(coordinates)
        dm = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dm[i][j] = self.euclidean_distance(coordinates[i], coordinates[j])
        return dm
    
    def _set_time_matrix(self, time_matrix: List[List[float]]):
        """
        Load problem as time/distance matrix.
        Do NOT overwrite self._coordinates with pseudo-coordinates unless we want to bypass.
        We keep empty coordinates and rely strictly on _dist_matrix.
        """
        self._time_matrix = time_matrix
        self._use_time_matrix = True
        self._n = len(time_matrix)
        # Avoid generating pseudo-coordinates to prevent accidental use of Euclidean distances
        self._coordinates = [(0.0, 0.0) for _ in range(self._n)]
        self._dist_matrix = time_matrix
    
    @staticmethod
    def _matrix_to_coordinates(time_matrix: List[List[float]]) -> List[Tuple[float, float]]:
        """
        Convert distance/time matrix to approximate 2D coordinates using MDS.
        This allows matrix-based problems to work with coordinate-based solvers.
        """
        import numpy as np
        n = len(time_matrix)
        D = np.array(time_matrix, dtype=float)
        # Classical MDS
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
        """Calculate NINT Euclidean distance (TSPLIB EUC_2D standard).
        
        TSPLIB standard: d(i,j) = NINT( sqrt( (xi-xj)^2 + (yi-yj)^2 ) )
        Uses int(x + 0.5) NOT round() — Python round() uses banker's rounding
        which rounds 0.5 to the nearest EVEN integer, causing incorrect distances.
        """
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return int(math.sqrt(dx * dx + dy * dy) + 0.5)
    
    def tour_length(self, tour: List[int]) -> float:
        """Calculate total tour length (Euclidean) or duration (time matrix)."""
        if self._use_time_matrix and self._time_matrix is not None:
            return self._tour_length_matrix(tour)
        else:
            return self._tour_length_euclidean(tour)
    
    def _tour_length_euclidean(self, tour: List[int]) -> float:
        """Calculate total tour length for a given tour using Euclidean distances."""
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
        """Calculate total tour duration using time matrix."""
        total = 0.0
        nodes = [0] + tour + [0]  # Start and end at depot (0)
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            total += self._time_matrix[from_node][to_node]
        return total
    
    @abstractmethod
    def solve(self, coordinates: List[Tuple[float, float]]) -> TSPResult:
        """
        Solve a TSP instance.
        
        Args:
            coordinates: List of (x, y) coordinates. Index 0 is the depot.
            
        Returns:
            TSPResult with standardized output format.
        """
        pass
    
    def solve_with_matrix(self, time_matrix: List[List[float]], recalculate: bool = True) -> TSPResult:
        """
        Solve using time/distance matrix instead of coordinates.
        
        Args:
            time_matrix: Square matrix where time_matrix[i][j] is the cost from i to j.
                         Index 0 is the depot.
            recalculate: If True, recalculate tour_length using the matrix after solving.
        
        Returns:
            TSPResult with tour_length recalculated from time matrix if recalculate=True.
        """
        self._set_time_matrix(time_matrix)
        result = self.solve(self._coordinates)
        if recalculate:
            result.tour_length = self._tour_length_matrix(result.tour)
        return result
    
    def _random_tour(self) -> List[int]:
        """Generate a random tour starting and ending at depot (0)."""
        import random
        rng = random.Random(self.random_seed)
        nodes = list(range(1, self._n))
        rng.shuffle(nodes)
        return nodes  # Returns tour without depot duplicates