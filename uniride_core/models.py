from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

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
    
    # CVRPTW specific fields
    capacity: Optional[int] = None
    num_vehicles: Optional[int] = None
    time_windows: Optional[List[Tuple[int, int]]] = None
    depot_index: int = 0
    
    def prepare_matrices(self, k: int = 20):
        # Build distance matrix if not present
        if self.dist_matrix is None and not self.is_time_matrix and self.coordinates:
            matrix = []
            import math
            for i, (x1, y1) in enumerate(self.coordinates):
                row = []
                for j, (x2, y2) in enumerate(self.coordinates):
                    if i == j:
                        row.append(0.0)
                    else:
                        dist = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                        row.append(dist)
                matrix.append(row)
            self.dist_matrix = matrix

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
        # Synchronize legacy fields with new fields
        if self.elapsed_ms and not self.time_ms:
            self.time_ms = self.elapsed_ms
        elif self.time_ms and not self.elapsed_ms:
            self.elapsed_ms = self.time_ms
            
        if self.history and not self.convergence_curve:
            self.convergence_curve = self.history
        elif self.convergence_curve and not self.history:
            self.history = self.convergence_curve
