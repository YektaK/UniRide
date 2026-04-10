"""
Base classes for TSP algorithms.

Provides the abstract base class TSPAlgorithm and the result dataclass AlgorithmResult
that all concrete algorithm implementations must use.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np
import time


@dataclass
class AlgorithmResult:
    """Result returned by a TSP algorithm solve() call."""
    tour: List[int]                          # Ordered list of city indices
    tour_length: float                       # Total tour distance
    gap: float = 0.0                         # Gap to optimal (%), 0 if unknown
    execution_time_ms: float = 0.0           # Wall-clock time in milliseconds
    iterations: int = 0                      # Number of iterations / generations
    convergence_history: List[float] = field(default_factory=list)  # Best at each logged step
    algorithm_name: str = ""                 # Name of the algorithm used
    extra: Optional[dict] = None             # Optional extra metadata


class TSPAlgorithm(ABC):
    """Abstract base class for TSP solving algorithms."""

    @abstractmethod
    def solve(
        self,
        dist_matrix: np.ndarray,
        optimal_value: float = -1.0,
        seed: int = 42,
        time_limit: float = 300.0,
        **kwargs,
    ) -> AlgorithmResult:
        """
        Solve a TSP instance.

        Parameters
        ----------
        dist_matrix : np.ndarray
            Symmetric distance matrix of shape (n, n).
        optimal_value : float
            Known optimal tour length (-1 if unknown) for gap calculation.
        seed : int
            Random seed for reproducibility.
        time_limit : float
            Maximum wall-clock seconds allowed.

        Returns
        -------
        AlgorithmResult
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Short algorithm identifier (e.g. 'sa', 'ga')."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable display name. Defaults to ``name``."""
        return self.name

    def _create_result(
        self,
        tour: List[int],
        tour_length: float,
        optimal_value: float,
        exec_time: float,
        iterations: int = 0,
        convergence: Optional[List[float]] = None,
    ) -> AlgorithmResult:
        """Convenience helper to build an ``AlgorithmResult``.

        Subclasses may call ``return self._create_result(...)`` at the end of
        ``solve()`` instead of constructing ``AlgorithmResult`` manually.
        """
        gap = 0.0
        if optimal_value > 0:
            gap = ((tour_length - optimal_value) / optimal_value) * 100.0
        return AlgorithmResult(
            tour=tour,
            tour_length=float(tour_length),
            gap=gap,
            execution_time_ms=exec_time * 1000.0,
            iterations=iterations,
            convergence_history=convergence or [],
            algorithm_name=self.name,
        )
