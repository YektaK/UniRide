"""
Strategy Registry
Exports all routing strategies and provides registry for lookup.

Available algorithms:
- genetic_algorithm (ga): Population-based metaheuristic
- pso: Particle Swarm Optimization
- gwo: Grey Wolf Optimizer
- hho: Harris Hawks Optimizer
- two_opt: Two-Opt Local Search (standalone)
- greedy: Greedy/Nearest Neighbor heuristic
- permutation_tsp: Complete Permutation Search (optimal for n≤10)
- ortools_cvrp: Google OR-Tools solver
"""

from typing import Dict, List, Type

from strategies.base_strategy import BaseRoutingStrategy
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.gwo_strategy import GreyWolfOptimizerStrategy
from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.two_opt_strategy import TwoOptStrategy
from strategies.greedy_heuristic import GreedyHeuristicStrategy
from strategies.permutation_tsp import PermutationTSPStrategy
from strategies.ortools_cvrp import ORToolsCVRPStrategy

# Strategy instances
_ga_strategy = GeneticAlgorithmStrategy()
_pso_strategy = PSOStrategy()
_gwo_strategy = GreyWolfOptimizerStrategy()
_hho_strategy = HarrisHawksOptimizerStrategy()
_two_opt_strategy = TwoOptStrategy()
_greedy_strategy = GreedyHeuristicStrategy()
_permutation_strategy = PermutationTSPStrategy()
_ortools_strategy = ORToolsCVRPStrategy()

# Registry mapping name -> instance
STRATEGY_REGISTRY: Dict[str, BaseRoutingStrategy] = {
    # Genetic Algorithm
    "genetic_algorithm": _ga_strategy,
    "ga": _ga_strategy,  # Alias

    # Particle Swarm Optimization
    "pso": _pso_strategy,

    # Grey Wolf Optimizer
    "gwo": _gwo_strategy,
    "grey_wolf": _gwo_strategy,  # Alias

    # Harris Hawks Optimizer
    "hho": _hho_strategy,
    "harris_hawks": _hho_strategy,  # Alias

    # Two-Opt Local Search
    "two_opt": _two_opt_strategy,
    "2opt": _two_opt_strategy,  # Alias

    # Greedy / Nearest Neighbor
    "greedy": _greedy_strategy,
    "nearest_neighbor": _greedy_strategy,  # Alias

    # Permutation TSP
    "permutation_tsp": _permutation_strategy,
    "permutation": _permutation_strategy,  # Alias

    # OR-Tools
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
    'GreyWolfOptimizerStrategy',
    'HarrisHawksOptimizerStrategy',
    'TwoOptStrategy',
    'GreedyHeuristicStrategy',
    'PermutationTSPStrategy',
    'ORToolsCVRPStrategy',
    'STRATEGY_REGISTRY',
    'get_strategy',
    'get_all_strategies',
    'get_strategy_info'
]