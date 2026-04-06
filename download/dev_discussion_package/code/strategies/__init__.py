"""
Strategy Registry
Exports all routing strategies and provides registry for lookup.

Available algorithms:
Pipeline A (Cluster-First, Route-Second):
- genetic_algorithm (ga): Population-based metaheuristic
- pso: Particle Swarm Optimization
- gwo: Grey Wolf Optimizer
- hho: Harris Hawks Optimizer
- two_opt: Two-Opt Local Search (standalone)
- greedy: Greedy/Nearest Neighbor heuristic
- permutation_tsp: Complete Permutation Search (optimal for n≤10)

Pipeline B (Route-First, Cluster-Second):
- ga_split: GA + Split Decoder
- ga_split_enhanced: GA-Split with HGS features
- pso_split: PSO + Split Decoder ✅ NEW
- hho_split: HHO + Split Decoder ✅ NEW
- gwo_split: GWO + Split Decoder ✅ NEW

Bağımsız (Holistik) Çözücüler:
- ortools_cvrp: Google OR-Tools solver
- vroom: Ultra-fast C++ solver (N>100, canli rota)
- pyvrp: DIMACS 2021 winner HGS (kalite kritik)
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

# Import new holistic solvers
try:
    from strategies.vroom_strategy import VROOMStrategy, VROOMFallbackStrategy
    VROOM_AVAILABLE = True
except ImportError:
    VROOM_AVAILABLE = False
    VROOMStrategy = None
    VROOMFallbackStrategy = None

try:
    from strategies.pyvrp_strategy import PyVRPStrategy, PyVRPAlternativeStrategy
    PYVRP_AVAILABLE = True
except ImportError:
    PYVRP_AVAILABLE = False
    PyVRPStrategy = None
    PyVRPAlternativeStrategy = None

# Import Pipeline B strategies
try:
    from strategies.ga_split_strategy import GASplitStrategy, GAEnhancedSplitStrategy
    GA_SPLIT_AVAILABLE = True
except ImportError:
    GA_SPLIT_AVAILABLE = False
    GASplitStrategy = None
    GAEnhancedSplitStrategy = None

# Import Metaheuristic Split strategies (PSO, HHO, GWO)
try:
    from strategies.metaheuristic_split_strategies import (
        PSOSplitStrategy, HHOSplitStrategy, GWOSplitStrategy
    )
    META_SPLIT_AVAILABLE = True
except ImportError:
    META_SPLIT_AVAILABLE = False
    PSOSplitStrategy = None
    HHOSplitStrategy = None
    GWOSplitStrategy = None

# Strategy instances - Pipeline A
_ga_strategy = GeneticAlgorithmStrategy()
_pso_strategy = PSOStrategy()
_gwo_strategy = GreyWolfOptimizerStrategy()
_hho_strategy = HarrisHawksOptimizerStrategy()
_two_opt_strategy = TwoOptStrategy()
_greedy_strategy = GreedyHeuristicStrategy()
_permutation_strategy = PermutationTSPStrategy()
_ortools_strategy = ORToolsCVRPStrategy()

# Strategy instances - Bağımsız Çözücüler
_vroom_strategy = VROOMStrategy() if VROOM_AVAILABLE else None
_vroom_fallback_strategy = VROOMFallbackStrategy() if VROOM_AVAILABLE else None
_pyvrp_strategy = PyVRPStrategy() if PYVRP_AVAILABLE else None
_pyvrp_alt_strategy = PyVRPAlternativeStrategy() if PYVRP_AVAILABLE else None

# Strategy instances - Pipeline B (Route-First, Cluster-Second)
_ga_split_strategy = GASplitStrategy() if GA_SPLIT_AVAILABLE else None
_ga_split_enhanced_strategy = GAEnhancedSplitStrategy() if GA_SPLIT_AVAILABLE else None
_pso_split_strategy = PSOSplitStrategy() if META_SPLIT_AVAILABLE else None
_hho_split_strategy = HHOSplitStrategy() if META_SPLIT_AVAILABLE else None
_gwo_split_strategy = GWOSplitStrategy() if META_SPLIT_AVAILABLE else None

# Registry mapping name -> instance
STRATEGY_REGISTRY: Dict[str, BaseRoutingStrategy] = {
    # =====================
    # Pipeline A (Mevcut)
    # =====================
    
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

    # OR-Tools (Bağımsız referans)
    "ortools_cvrp": _ortools_strategy,
    "ortools": _ortools_strategy,  # Alias
}

# Add VROOM if available
if _vroom_strategy:
    STRATEGY_REGISTRY["vroom"] = _vroom_strategy
    STRATEGY_REGISTRY["vroom_fallback"] = _vroom_fallback_strategy

# Add PyVRP if available
if _pyvrp_strategy:
    STRATEGY_REGISTRY["pyvrp"] = _pyvrp_strategy
    STRATEGY_REGISTRY["pyvrp_alt"] = _pyvrp_alt_strategy
    STRATEGY_REGISTRY["hgs"] = _pyvrp_strategy  # Alias (HGS = Hybrid Genetic Search)

# Add Pipeline B strategies if available
if _ga_split_strategy:
    STRATEGY_REGISTRY["ga_split"] = _ga_split_strategy
    STRATEGY_REGISTRY["ga_split_enhanced"] = _ga_split_enhanced_strategy

if _pso_split_strategy:
    STRATEGY_REGISTRY["pso_split"] = _pso_split_strategy

if _hho_split_strategy:
    STRATEGY_REGISTRY["hho_split"] = _hho_split_strategy

if _gwo_split_strategy:
    STRATEGY_REGISTRY["gwo_split"] = _gwo_split_strategy


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


def get_available_solvers() -> dict:
    """
    Get availability status of all solvers.
    Useful for checking which optional libraries are installed.
    """
    return {
        "ortools": True,  # Always available
        "vroom": VROOM_AVAILABLE,
        "pyvrp": PYVRP_AVAILABLE,
        "ga": True,
        "ga_split": GA_SPLIT_AVAILABLE,
        "pso": True,
        "pso_split": META_SPLIT_AVAILABLE,
        "gwo": True,
        "gwo_split": META_SPLIT_AVAILABLE,
        "hho": True,
        "hho_split": META_SPLIT_AVAILABLE,
        "greedy": True,
        "two_opt": True,
        "permutation_tsp": True,
    }


def get_recommended_strategy(n_students: int, priority: str = "balanced") -> str:
    """
    Get recommended strategy based on problem size and priority.
    
    Args:
        n_students: Number of students to route
        priority: "speed", "quality", or "balanced"
    
    Returns:
        Strategy name
    """
    if n_students <= 10:
        if priority == "quality":
            return "permutation_tsp"  # Exact solution
        return "greedy"
    
    elif n_students <= 30:
        if priority == "speed":
            return "ortools_cvrp"
        elif priority == "quality":
            return "pyvrp" if PYVRP_AVAILABLE else "ga_split"
        return "ga_split" if GA_SPLIT_AVAILABLE else "pso"
    
    elif n_students <= 100:
        if priority == "speed":
            return "vroom" if VROOM_AVAILABLE else "ortools_cvrp"
        elif priority == "quality":
            return "pyvrp" if PYVRP_AVAILABLE else "ga_split_enhanced"
        return "ga_split" if GA_SPLIT_AVAILABLE else "hho"
    
    else:  # n_students > 100
        if priority == "speed":
            return "vroom" if VROOM_AVAILABLE else "ortools_cvrp"
        elif priority == "quality":
            return "pyvrp" if PYVRP_AVAILABLE else "ga_split_enhanced"
        return "vroom" if VROOM_AVAILABLE else "ga_split"


# Export all
__all__ = [
    # Base
    'BaseRoutingStrategy',
    
    # Pipeline A (Cluster-First, Route-Second)
    'GeneticAlgorithmStrategy',
    'PSOStrategy',
    'GreyWolfOptimizerStrategy',
    'HarrisHawksOptimizerStrategy',
    'TwoOptStrategy',
    'GreedyHeuristicStrategy',
    'PermutationTSPStrategy',
    
    # Pipeline B (Route-First, Cluster-Second)
    'GASplitStrategy',
    'GAEnhancedSplitStrategy',
    'PSOSplitStrategy',
    'HHOSplitStrategy',
    'GWOSplitStrategy',
    
    # Bağımsız Çözücüler
    'ORToolsCVRPStrategy',
    'VROOMStrategy',
    'VROOMFallbackStrategy',
    'PyVRPStrategy',
    'PyVRPAlternativeStrategy',
    
    # Registry
    'STRATEGY_REGISTRY',
    'get_strategy',
    'get_all_strategies',
    'get_strategy_info',
    'get_available_solvers',
    'get_recommended_strategy',
]
