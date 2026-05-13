from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Callable, Optional
import time

@dataclass
class ProblemInstance:
    """Unified representation of a TSP/ATSP problem."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]] = field(default_factory=list)
    optimal: Optional[float] = None
    category: str = "small"
    source: str = "tsplib"
    is_time_matrix: bool = False
    time_matrix: Optional[List[List[float]]] = None
    dist_matrix: Any = None
    knn_mask: Optional[Dict[int, List[int]]] = None
    
    def prepare_matrices(self, k: int = 20):
        import math
        
        # Build distance matrix if not present
        if self.dist_matrix is None and not self.is_time_matrix and self.coordinates:
            matrix = []
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
            self.knn_mask = {}
            for i, row in enumerate(matrix_to_use):
                # Get indices sorted by distance, excluding self (which is 0 distance)
                # Keep top K
                neighbors = sorted(
                    [(j, dist) for j, dist in enumerate(row) if i != j],
                    key=lambda x: x[1]
                )
                self.knn_mask[i] = [j for j, dist in neighbors[:k]]

@dataclass
class RunResult:
    """Standardized output from any algorithm strategy."""
    problem: str
    algorithm: str
    run: int
    seed: int
    dimension: int
    optimal: Optional[float]
    tour_cost: float
    gap_pct: Optional[float]
    elapsed_sec: float
    iterations: int = 0
    evaluations: int = 0
    convergence_profile: List[float] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class BenchmarkTask:
    """A single execution task defining problem, algorithm, and specific parameters."""
    problem_name: str
    algorithm: str
    run_idx: int
    seed: int
    params: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class BenchmarkConfig:
    """A collection of tasks that can be serialized to/from JSON."""
    name: str
    created_at: str
    tasks: List[BenchmarkTask]
    
    def to_json(self) -> str:
        import json
        data = {
            "name": self.name,
            "created_at": self.created_at,
            "tasks": [t.__dict__ for t in self.tasks]
        }
        return json.dumps(data, indent=4)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'BenchmarkConfig':
        import json
        data = json.loads(json_str)
        tasks = [BenchmarkTask(**t) for t in data["tasks"]]
        return cls(name=data.get("name", "Unnamed"), created_at=data.get("created_at", ""), tasks=tasks)

class AlgorithmRegistry:
    """Registry to route algorithm strings to their respective implementations."""
    _registry: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, name: str):
        def wrapper(func: Callable):
            cls._registry[name] = func
            return func
        return wrapper
    
    @classmethod
    def get_executor(cls, name: str) -> Callable:
        if name not in cls._registry:
            raise ValueError(f"Algorithm '{name}' not found in registry.")
        return cls._registry[name]
        
    @classmethod
    def list_algorithms(cls) -> List[str]:
        return list(cls._registry.keys())

# --- Basic Executor Signatures ---
# An executor function should look like this:
# def execute_algorithm(problem: ProblemInstance, params: Dict[str, Any], seed: int, run_idx: int) -> RunResult:
#     pass
