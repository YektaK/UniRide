"""
Base solver interface for TSP optimization algorithms.
All algorithms implement this interface for uniform benchmarking.

Supports both:
- Euclidean coordinates (TSPLIB standard)
- Time/distance matrix (real-world data)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Optional
import time
import math
try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

from uniride_core.models import TSPResult
from uniride_core.algorithms import numba_accel as _nb


@dataclass
class BackendObservation:
    objective: set[str] = field(default_factory=set)
    polish: set[str] = field(default_factory=set)

    def reset(self) -> None:
        self.objective.clear()
        self.polish.clear()

    def label(self) -> str:
        objective = "+".join(sorted(self.objective)) or "unused"
        polish = "+".join(sorted(self.polish)) or "none"
        return "objective={};polish={}".format(objective, polish)


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
        self._matrix_as_closed_tsp: bool = False
        self._dist_matrix: Optional[List[List[float]]] = None  # cached for numba speedup
        # Gelistirme #1: Numpy önbelleği — matris bir kez np.ndarray'e dönüştürülür.
        # Bu, her nb_two_opt / tour_length çağrısındaki dönüşüm yükünü ortadan kaldırır.
        self._dist_matrix_np = None  # np.ndarray veya None
        self._backend_observation = BackendObservation()

    def _initial_tour_nodes(self) -> List[int]:
        """Return initial node list. For time matrix, exclude depot(0); for TSP use all nodes."""
        if self._exclude_depot or (self._use_time_matrix and not self._matrix_as_closed_tsp):
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
        # Gelistirme #1: Python list hazır olduktan sonra numpy önbelleğini bir kez oluştur.
        self._build_np_cache()

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
        # Gelistirme #1: Zaman matrisi yüklendiğinde numpy önbelleğini de hemen oluştur.
        self._build_np_cache()

    def _build_np_cache(self):
        """Gelistirme #1 — Numpy Veri Transferi Optimizasyonu.

        dist_matrix (Python list-of-lists) bir kez np.ndarray'e dönüştürülür ve
        _dist_matrix_np olarak önbelleklenir. Bu sayede her nb_two_opt / _tour_length_fast
        çağrısında tekrarlanan np.array() maliyeti ortadan kalkar.
        Numpy mevcut değilse sessizce atlanır; mevcut davranış korunur.
        """
        if _NUMPY_AVAILABLE and self._dist_matrix is not None:
            self._dist_matrix_np = np.array(self._dist_matrix, dtype=np.float64)
        else:
            self._dist_matrix_np = None

    @staticmethod
    def _runtime_backend(callable_obj: object) -> str:
        return (
            "numba"
            if getattr(callable_obj, "nopython_signatures", ())
            else "python"
        )

    def _invoke_objective_kernel(
        self, objective_kernel: Callable[..., object], tour: List[int]
    ) -> object:
        import numpy as _np
        # Closed TSP/ATSP cycles may place node 0 anywhere. Rotate the
        # cycle before the legacy kernel prepares its depot-shaped
        # representation; rotation preserves directed cycle cost.
        kernel_tour = list(tour)
        if not self._exclude_depot and 0 in kernel_tour and kernel_tour[0] != 0:
            zero_idx = kernel_tour.index(0)
            kernel_tour = kernel_tour[zero_idx:] + kernel_tour[:zero_idx]
        # _nb içindeki _prepare_route helper'ı bu dönüşümü yapıyor.
        route_np = _nb._prepare_route(kernel_tour)
        return objective_kernel(route_np, self._dist_matrix_np)

    def _tour_length_fast(self, tour: List[int]) -> float:
        """Gelistirme #2 — Hızlı Tur Uzunluğu Hesabı.

        Önce numpy önbelleği (_dist_matrix_np) ve numba_accel JIT kerneli kullanılmaya
        çalışılır. Başarısız olursa mevcut Python tabanlı hesaplamaya düşer (fallback).
        Bu sayede GA döngüsündeki her `self.tour_length(child)` çağrısı Numba ile hızlanır.
        Mevcut tour_length() metodu değişmeden korunur — geriye dönük uyumluluk sağlanır.
        """
        if self._dist_matrix_np is not None:
            objective_kernel: Optional[Callable[..., object]] = None
            kernel_succeeded = False
            try:
                objective_kernel = _nb._calculate_tour_length_atsp_numba
                result = float(self._invoke_objective_kernel(objective_kernel, tour))
            except Exception:
                pass  # Fallback: herhangi bir hata olursa yavaş yola dön
            else:
                kernel_succeeded = True
            if kernel_succeeded and objective_kernel is not None:
                backend = self._runtime_backend(objective_kernel)
                self._backend_observation.objective.add(backend)
                return result
        # Fallback: orijinal Python tabanlı hesaplama (güvenli)
        result = self.tour_length(tour)
        self._backend_observation.objective.add("python")
        return result

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
        if not tour:
            return 0.0
        if self._matrix_as_closed_tsp:
            return sum(
                float(self._time_matrix[node][tour[(idx + 1) % len(tour)]])
                for idx, node in enumerate(tour)
            )
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

    def solve_with_matrix(
        self,
        time_matrix: List[List[float]],
        recalculate: bool = True,
        closed_tsp: bool = False,
    ) -> TSPResult:
        """
        Solve using time/distance matrix instead of coordinates.

        Args:
            time_matrix: Square matrix where time_matrix[i][j] is the cost from i to j.
                         Index 0 is the depot.
            recalculate: If True, recalculate tour_length using the matrix after solving.
            closed_tsp: If True, optimize every matrix node as a closed TSP/ATSP
                        cycle. If False, preserve the historical fixed-depot mode.

        Returns:
            TSPResult with tour_length recalculated from time matrix if recalculate=True.
        """
        self._matrix_as_closed_tsp = bool(closed_tsp)
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