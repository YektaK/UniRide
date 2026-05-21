from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class MetaHeuristicConfig:
    """Base class for all heuristic configurations with built-in validation."""
    population_size: int = 36
    max_iterations: int = 300
    
    def __post_init__(self):
        if self.population_size < 4:
            raise ValueError(f"population_size must be >= 4, got {self.population_size}")
        if self.max_iterations < 1:
            raise ValueError(f"max_iterations must be >= 1, got {self.max_iterations}")

@dataclass
class E2BSOConfig(MetaHeuristicConfig):
    """Configuration for E2BSO algorithm."""
    gamma: float = 0.20
    injection_rate: float = 0.12
    h_start: float = 1.0
    h_end: float = 0.1
    
    def __post_init__(self):
        super().__post_init__()
        if not (0.0 < self.gamma < 1.0):
            raise ValueError(f"gamma must be in (0, 1), got {self.gamma}")
        if not (0.0 < self.injection_rate < 1.0):
            raise ValueError(f"injection_rate must be in (0, 1), got {self.injection_rate}")
