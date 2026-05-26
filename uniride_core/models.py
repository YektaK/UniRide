from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional, Sequence

@dataclass
class ProblemInstance:
    """Unified representation of a TSP/ATSP/CVRPTW problem."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]] = field(default_factory=list)
    optimal: Optional[float] = None
    category: str = "small"
    source: str = "tsplib"
    problem_type: str = "tsp"  # e.g., "tsp", "cvrptw"
    is_time_matrix: bool = False
    time_matrix: Optional[List[List[float]]] = None
    dist_matrix: Any = None
    knn_mask: Optional[Dict[int, List[int]]] = None
    file_path: Optional[str] = None
    edge_weight_type: str = "EUC_2D"
    
    # CVRPTW specific fields
    capacity: Optional[int] = None
    num_vehicles: Optional[int] = None
    demands: Optional[List[Any]] = None
    capacities: Optional[List[int]] = None
    service_times: Optional[List[int]] = None
    num_vehicles_bks: Optional[int] = None
    max_route_duration: Optional[float] = None
    matrix_kind: str = "distance"
    direction: str = "pickup"
    time_windows: Optional[List[Tuple[int, int]]] = None
    depot_index: int = 0
    
    def prepare_matrices(self, k: int = 20):
        n = len(self.coordinates) if self.coordinates else 0
        # Build distance matrix if not present
        if self.dist_matrix is None and not self.is_time_matrix and self.coordinates:
            if n > 100:
                import numpy as np
                coords = np.array(self.coordinates, dtype=np.float64)
                diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
                dist = np.sqrt((diff ** 2).sum(axis=2))
                self.dist_matrix = dist.tolist()
            else:
                matrix = []
                import math
                for i, (x1, y1) in enumerate(self.coordinates):
                    row = []
                    for j, (x2, y2) in enumerate(self.coordinates):
                        if i == j:
                            row.append(0.0)
                        else:
                            row.append(math.sqrt((x1 - x2)**2 + (y1 - y2)**2))
                    matrix.append(row)
                self.dist_matrix = matrix

        # Build KNN mask
        matrix_to_use = self.time_matrix if self.is_time_matrix else self.dist_matrix
        if matrix_to_use and len(matrix_to_use) > 0 and self.knn_mask is None:
            m = len(matrix_to_use)
            if m > 100:
                import numpy as np
                arr = np.array(matrix_to_use, dtype=np.float64)
                indices = np.argsort(arr, axis=1)
                self.knn_mask = {}
                for i in range(m):
                    self.knn_mask[i] = indices[i, 1:k+1].tolist()
            else:
                self.knn_mask = {}
                for i, row in enumerate(matrix_to_use):
                    neighbors = sorted(
                        [(j, dist) for j, dist in enumerate(row) if i != j],
                        key=lambda x: x[1]
                    )
                    self.knn_mask[i] = [j for j, dist in neighbors[:k]]

@dataclass
class TSPResult:
    """Unified output from an optimization algorithm."""
    algorithm: str
    tour: List[int]
    tour_length: float
    time_ms: float = 0.0
    elapsed_ms: float = 0.0  # Legacy alias
    optimal_gap: Optional[float] = None
    convergence_curve: Optional[List[float]] = None
    history: Optional[List[float]] = None  # Legacy alias
    iterations: int = 0
    seed: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    extra_stats: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.elapsed_ms is not None and self.elapsed_ms != 0.0 and self.time_ms == 0.0:
            self.time_ms = self.elapsed_ms
        elif self.time_ms is not None and self.time_ms != 0.0 and self.elapsed_ms == 0.0:
            self.elapsed_ms = self.time_ms

        if self.history is not None and self.convergence_curve is None:
            self.convergence_curve = self.history
        elif self.convergence_curve is not None and self.history is None:
            self.history = self.convergence_curve


@dataclass
class CostMatrix:
    """Matrix-first representation used by all core solvers."""
    values: Any
    kind: str = "distance"  # distance | travel_time | synthetic_travel_time
    is_asymmetric: bool = False
    labels: Optional[List[str]] = None


@dataclass
class ConstraintProfile:
    """Routing constraints shared by academic and production problems.

    Demands and capacities are vector-valued. Standard CVRP maps to a one-item
    vector, while UniRide maps to [sw, so].
    """
    demands: Optional[List[Sequence[int]]] = None
    capacities: Optional[Sequence[int]] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
    service_times: Optional[List[int]] = None
    depot_index: int = 0
    max_route_duration: Optional[float] = None
    direction: str = "pickup"
    target_time: Optional[int] = None
    offset_minutes: int = 10


@dataclass
class RoutingProblem:
    """Core-first problem object for TSP, ATSP, CVRP, CVRPTW, and UniRide data."""
    name: str
    problem_type: str
    matrix: CostMatrix
    constraints: ConstraintProfile = field(default_factory=ConstraintProfile)
    coordinates: Optional[List[Tuple[float, float]]] = None
    optimal: Optional[float] = None
    category: str = "small"
    source: str = "core"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def dimension(self) -> int:
        try:
            return int(len(self.matrix.values))
        except TypeError:
            return 0


@dataclass
class PermutationResult:
    """Output from a permutation engine before problem-specific decoding."""
    algorithm: str
    permutation: List[int]
    cost: float
    time_ms: float = 0.0
    iterations: int = 0
    seed: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    convergence_curve: Optional[List[float]] = None


@dataclass
class RoutingResult:
    """Unified output for TSP, ATSP, CVRP, CVRPTW, and UniRide optimization."""
    algorithm: str
    problem_type: str
    objective_cost: float
    total_cost: Optional[float] = None
    routes: List[List[int]] = field(default_factory=list)
    tour: Optional[List[int]] = None
    num_vehicles: int = 0
    time_ms: float = 0.0
    optimal_gap: Optional[float] = None
    capacity_violations: int = 0
    tw_violations: int = 0
    route_costs: Optional[List[float]] = None
    route_loads: Optional[List[List[int]]] = None
    convergence_curve: Optional[List[float]] = None
    iterations: int = 0
    seed: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.total_cost is None:
            self.total_cost = self.objective_cost


@dataclass
class CVRPResult(RoutingResult):
    """Backward-compatible named result for CVRP/CVRPTW workflows."""
