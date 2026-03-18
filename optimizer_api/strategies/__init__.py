"""
Strategy Registry
Exports all routing strategies and provides registry for lookup
"""

from typing import Dict, List, Type

from strategies.base_strategy import BaseRoutingStrategy
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.greedy_heuristic import GreedyHeuristicStrategy
from strategies.permutation_tsp import PermutationTSPStrategy
from strategies.ortools_cvrp import ORToolsCVRPStrategy

# Strategy instances
_ga_strategy = GeneticAlgorithmStrategy()
_pso_strategy = PSOStrategy()
_greedy_strategy = GreedyHeuristicStrategy()
_permutation_strategy = PermutationTSPStrategy()
_ortools_strategy = ORToolsCVRPStrategy()

# Registry mapping name -> instance
STRATEGY_REGISTRY: Dict[str, BaseRoutingStrategy] = {
    "genetic_algorithm": _ga_strategy,
    "ga": _ga_strategy,  # Alias
    "pso": _pso_strategy,
    "greedy": _greedy_strategy,
    "nearest_neighbor": _greedy_strategy,  # Alias
    "permutation_tsp": _permutation_strategy,
    "permutation": _permutation_strategy,  # Alias
    "ortools_cvrp": _ortools_strategy,
    "ortools": _ortools_strategy,  # Alias
}


def get_strategy(name: str) -> BaseRoutingStrategy:
    """Get strategy by name"""
    return STRATEGY_REGISTRY.get(name.lower())


def get_all_strategies() -> List[BaseRoutingStrategy]:
    """Get list of all unique strategy instances"""
    return list(set(STRATEGY_REGISTRY.values()))


def get_strategy_info() -> List[dict]:
    """Get information about all strategies"""
    seen = set()
    info = []

    for name, strategy in STRATEGY_REGISTRY.items():
        if strategy.name not in seen:
            seen.add(strategy.name)
            info.append({
                "name": strategy.name,
                "display_name": strategy.display_name,
                "description": strategy.description
            })

    return info


# Export all
__all__ = [
    'BaseRoutingStrategy',
    'GeneticAlgorithmStrategy',
    'PSOStrategy',
    'GreedyHeuristicStrategy',
    'PermutationTSPStrategy',
    'ORToolsCVRPStrategy',
    'STRATEGY_REGISTRY',
    'get_strategy',
    'get_all_strategies',
    'get_strategy_info'
]
