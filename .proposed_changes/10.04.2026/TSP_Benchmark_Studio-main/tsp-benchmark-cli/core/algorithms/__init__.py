"""TSP Optimization Algorithms."""
from .base import TSPAlgorithm, AlgorithmResult
from .local_search import TwoOpt, ThreeOpt, OrOpt, Swap, HybridLocalSearch
from .simulated_annealing import SimulatedAnnealing
from .genetic_algorithm import GeneticAlgorithm
from .ant_colony import AntColonyOptimization
from .tabu_search import TabuSearch

ALGORITHM_REGISTRY = {
    "2-opt": TwoOpt,
    "3-opt": ThreeOpt,
    "or-opt": OrOpt,
    "swap": Swap,
    "hybrid": HybridLocalSearch,
    "sa": SimulatedAnnealing,
    "ga": GeneticAlgorithm,
    "aco": AntColonyOptimization,
    "ts": TabuSearch,
}


def get_algorithm(name: str, **kwargs) -> TSPAlgorithm:
    """Factory function to get algorithm by name."""
    cls = ALGORITHM_REGISTRY.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown algorithm: {name}. Available: {list(ALGORITHM_REGISTRY.keys())}"
        )
    return cls(**kwargs)
