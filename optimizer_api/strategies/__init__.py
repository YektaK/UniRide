"""
Strategy Registry
Exports all routing strategies and provides registry for lookup.

Available algorithms:

Cluster-First, Route-Second (Pipeline A — uses Sweep/CW clustering):
- genetic_algorithm (ga): GA optimization
- pso: PSO optimization
- gwo: GWO optimization
- hho: HHO optimization

Route-First, Cluster-Second (Pipeline B - Split):
- ga_split: GA + Optimal Split Decoder
- pso_split: PSO + Optimal Split Decoder
- gwo_split: GWO + Optimal Split Decoder
- hho_split: HHO + Optimal Split Decoder

Holistic Solvers:
- ortools_cvrp: Google OR-Tools CVRP solver
- pyvrp: PyVRP HGS (DIMACS 2021 Winner)
- vroom: VROOM ultra-fast C++ solver

Heuristics:
- two_opt: Two-Opt Local Search
- greedy: Greedy/Nearest Neighbor
- permutation_tsp: Complete Permutation Search (optimal for n≤10)

Archived (not registered):
- _archived/kmeans_tsp.py: Retired proof-of-concept K-Means+TSP skeleton
"""

from typing import Dict, List, Type, Optional, Union

from strategies.base_strategy import BaseRoutingStrategy
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.gwo_strategy import GreyWolfOptimizerStrategy
from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.two_opt_strategy import TwoOptStrategy
from strategies.greedy_heuristic import GreedyHeuristicStrategy
from strategies.permutation_tsp import PermutationTSPStrategy
from strategies.ortools_cvrp import ORToolsCVRPStrategy
from strategies.ebso_strategy import E2BSoStrategy
from strategies.rdma_strategy import R2DMAStrategy
from strategies.aoea_strategy import PAOEAStrategy

# Pipeline B: Split-based strategies
from strategies.ga_split_strategy import GASplitStrategy
from strategies.pso_split_strategy import PSOSplitStrategy
from strategies.hho_split_strategy import HHOSplitStrategy
from strategies.gwo_split_strategy import GWOSplitStrategy

# Holistic solvers (with graceful fallback)
# Type placeholders for optional strategies
PyVRPStrategy: Optional[Type] = None
PyVRPAlternativeStrategy: Optional[Type] = None
VROOMStrategy: Optional[Type] = None
VROOMFallbackStrategy: Optional[Type] = None

try:
    from strategies.pyvrp_strategy import PyVRPStrategy as _PyVRPStrategy, PyVRPAlternativeStrategy as _PyVRPAltStrategy
    PyVRPStrategy = _PyVRPStrategy
    PyVRPAlternativeStrategy = _PyVRPAltStrategy
    _PYVRP_AVAILABLE = True
except ImportError:
    _PYVRP_AVAILABLE = False

try:
    from strategies.vroom_strategy import VROOMStrategy as _VROOMStrategy, VROOMFallbackStrategy as _VROOMFallbackStrategy
    VROOMStrategy = _VROOMStrategy
    VROOMFallbackStrategy = _VROOMFallbackStrategy
    _VROOM_AVAILABLE = True
except ImportError:
    _VROOM_AVAILABLE = False


# Strategy instances (Singleton pattern for efficiency)
_ga_strategy = GeneticAlgorithmStrategy()
_pso_strategy = PSOStrategy()
_gwo_strategy = GreyWolfOptimizerStrategy()
_hho_strategy = HarrisHawksOptimizerStrategy()
_two_opt_strategy = TwoOptStrategy()
_greedy_strategy = GreedyHeuristicStrategy()
_permutation_strategy = PermutationTSPStrategy()
_ortools_strategy = ORToolsCVRPStrategy()

# Pipeline B instances
_ga_split_strategy = GASplitStrategy()
_pso_split_strategy = PSOSplitStrategy()
_hho_split_strategy = HHOSplitStrategy()
_gwo_split_strategy = GWOSplitStrategy()

# SOTA solver instances
_e2bso_strategy = E2BSoStrategy()
_r2dma_strategy = R2DMAStrategy()
_paoea_strategy = PAOEAStrategy()

# Holistic solver instances (only if available)
_pyvrp_strategy: Optional[BaseRoutingStrategy] = None
_pyvrp_alt_strategy: Optional[BaseRoutingStrategy] = None
_vroom_strategy: Optional[BaseRoutingStrategy] = None
_vroom_fallback_strategy: Optional[BaseRoutingStrategy] = None

if _PYVRP_AVAILABLE:
    if PyVRPStrategy is not None:
        _pyvrp_strategy = PyVRPStrategy()
    if PyVRPAlternativeStrategy is not None:
        _pyvrp_alt_strategy = PyVRPAlternativeStrategy()

if _VROOM_AVAILABLE:
    if VROOMStrategy is not None:
        _vroom_strategy = VROOMStrategy()
    if VROOMFallbackStrategy is not None:
        _vroom_fallback_strategy = VROOMFallbackStrategy()


# Registry mapping name -> instance
STRATEGY_REGISTRY: Dict[str, Optional[BaseRoutingStrategy]] = {
    # =====================================================
    # Pipeline A: Cluster-First, Route-Second (K-Means based)
    # =====================================================
    
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

    # =====================================================
    # Pipeline B: Route-First, Cluster-Second (Split based)
    # =====================================================
    
    # GA + Split
    "ga_split": _ga_split_strategy,
    "ga-split": _ga_split_strategy,  # Alias
    
    # PSO + Split
    "pso_split": _pso_split_strategy,
    "pso-split": _pso_split_strategy,  # Alias
    
    # GWO + Split
    "gwo_split": _gwo_split_strategy,
    "gwo-split": _gwo_split_strategy,  # Alias
    
    # HHO + Split
    "hho_split": _hho_split_strategy,
    "hho-split": _hho_split_strategy,  # Alias

    # =====================================================
    # Holistic Solvers (Native CVRP solutions)
    # =====================================================
    
    # Google OR-Tools
    "ortools_cvrp": _ortools_strategy,
    "ortools": _ortools_strategy,  # Alias
    
    # PyVRP (HGS - DIMACS 2021 Winner)
    "pyvrp": _pyvrp_strategy if _PYVRP_AVAILABLE else _ortools_strategy,
    "hgs": _pyvrp_strategy if _PYVRP_AVAILABLE else _ortools_strategy,  # Alias
    "pyvrp_alt": _pyvrp_alt_strategy if _PYVRP_AVAILABLE else _ortools_strategy,
    
    # VROOM (Ultra-fast C++)
    "vroom": _vroom_strategy if _VROOM_AVAILABLE else _ortools_strategy,
    "vroom_fallback": _vroom_fallback_strategy if _VROOM_AVAILABLE else _ortools_strategy,

    # =====================================================
    # =====================================================
    # SOTA Algorithms (FAZ 0 Infrastructure + FAZ 1+ Algorithms)
    # =====================================================

    # E²BSO — Enhanced Entropy-Balanced Swarm Optimization (FAZ 1)
    "e2bso": _e2bso_strategy,
    "entropy_bso": _e2bso_strategy,  # Alias
    "e2b": _e2bso_strategy,  # Short alias

    # R²DMA — Resonance-Supported Destroy-and-Merge (FAZ 2)
    "r2dma": _r2dma_strategy,
    "rdma": _r2dma_strategy,

    # P-AOEA — Production Adaptive Operator Evolution (FAZ 3)
    "paoea": _paoea_strategy,
    "aoea": _paoea_strategy,

    # =====================================================
    # Heuristics & Local Search
    # =====================================================
    
    # Two-Opt Local Search
    "two_opt": _two_opt_strategy,
    "2opt": _two_opt_strategy,  # Alias

    # Greedy / Nearest Neighbor
    "greedy": _greedy_strategy,
    "nearest_neighbor": _greedy_strategy,  # Alias

    # Permutation TSP (Exact for small instances)
    "permutation_tsp": _permutation_strategy,
    "permutation": _permutation_strategy,  # Alias
    "exact": _permutation_strategy,  # Alias
}


def get_strategy(name: str) -> Optional[BaseRoutingStrategy]:
    """
    Get strategy by name.
    
    Args:
        name: Strategy name or alias
        
    Returns:
        Strategy instance or None if not found
    """
    return STRATEGY_REGISTRY.get(name.lower())


def get_all_strategies() -> List[BaseRoutingStrategy]:
    """
    Get list of all unique strategy instances.
    
    Returns:
        List of unique strategy instances (excluding None)
    """
    return list(set(s for s in STRATEGY_REGISTRY.values() if s is not None))


def get_strategy_info() -> List[dict]:
    """
    Get information about all strategies.
    
    Returns:
        List of strategy info dicts with name, display_name, description
    """
    seen = set()
    info = []

    for name, strategy in STRATEGY_REGISTRY.items():
        if strategy and strategy.name not in seen:
            seen.add(strategy.name)
            info.append({
                "name": strategy.name,
                "display_name": strategy.display_name,
                "description": strategy.description
            })

    return info


def get_available_solvers() -> Dict[str, dict]:
    """
    Get availability status of all solvers.
    
    Returns:
        Dict mapping solver category to availability info
        
    Example:
        {
            "pipeline_a": {"available": True, "count": 4},
            "pipeline_b": {"available": True, "count": 4},
            "holistic": {
                "ortools": True,
                "pyvrp": False,
                "vroom": True
            }
        }
    """
    return {
        "pipeline_a": {
            "available": True,
            "count": 4,
            "algorithms": ["genetic_algorithm", "pso", "gwo", "hho"]
        },
        "pipeline_b": {
            "available": True,
            "count": 4,
            "algorithms": ["ga_split", "pso_split", "gwo_split", "hho_split"]
        },
        "holistic": {
            "ortools": True,
            "pyvrp": _PYVRP_AVAILABLE,
            "vroom": _VROOM_AVAILABLE
        },
        "heuristics": {
            "available": True,
            "algorithms": ["two_opt", "greedy", "permutation_tsp"]
        },
        "sota": {
            "available": True,
            "algorithms": ["e2bso", "r2dma", "paoea"]
        }
    }


def get_recommended_strategy(n_students: int, priority: str = "balanced") -> str:
    """
    Get recommended strategy based on problem size and priority.
    
    Literature-based recommendations:
    - N ≤ 30: Split algorithms (optimal partitioning)
    - 30 < N ≤ 100: Either pipeline works well
    - N > 100: Holistic solvers or Pipeline A with Sweep/CW
    
    Args:
        n_students: Number of students (problem size)
        priority: "speed", "quality", or "balanced"
        
    Returns:
        Recommended strategy name
    """
    if priority == "speed":
        if n_students <= 30:
            return "vroom" if _VROOM_AVAILABLE else "pso_split"
        elif n_students <= 100:
            return "pso"  # Fast convergence
        else:
            return "vroom" if _VROOM_AVAILABLE else "ortools"
    
    elif priority == "quality":
        if n_students <= 30:
            return "ga_split"  # Best quality for small instances
        elif n_students <= 100:
            return "pyvrp" if _PYVRP_AVAILABLE else "ga_split"
        else:
            return "pyvrp" if _PYVRP_AVAILABLE else "ortools"
    
    else:  # balanced
        if n_students <= 30:
            return "pso_split"  # Good balance
        elif n_students <= 100:
            return "hho_split"  # Adaptive, good balance
        else:
            return "ortools"  # Reliable for large instances


def get_strategies_by_pipeline(pipeline: str) -> List[dict]:
    """
    Get strategies filtered by pipeline type.
    
    Args:
        pipeline: "a" (Cluster-First), "b" (Route-First), 
                 "holistic", or "heuristic"
        
    Returns:
        List of strategy info dicts
    """
    pipeline_map = {
        "a": ["genetic_algorithm", "pso", "gwo", "hho"],
        "b": ["ga_split", "pso_split", "gwo_split", "hho_split"],
        "holistic": ["ortools_cvrp", "pyvrp", "pyvrp_alt", "vroom", "vroom_fallback"],
        "heuristic": ["two_opt", "greedy", "permutation_tsp"]
    }
    
    strategy_names = pipeline_map.get(pipeline.lower(), [])
    all_info = get_strategy_info()
    
    return [info for info in all_info if info["name"] in strategy_names]


# Export all
__all__ = [
    # Base classes
    'BaseRoutingStrategy',
    
    # Pipeline A strategies
    'GeneticAlgorithmStrategy',
    'PSOStrategy',
    'GreyWolfOptimizerStrategy',
    'HarrisHawksOptimizerStrategy',
    
    # Pipeline B strategies
    'GASplitStrategy',
    'PSOSplitStrategy',
    'HHOSplitStrategy',
    'GWOSplitStrategy',
    
    # Holistic solvers (optional)
    'PyVRPStrategy',
    'PyVRPAlternativeStrategy',
    'VROOMStrategy',
    'VROOMFallbackStrategy',
    
    # Heuristics
    'TwoOptStrategy',
    'GreedyHeuristicStrategy',
    'PermutationTSPStrategy',
    'E2BSoStrategy',
    'R2DMAStrategy',
    'PAOEAStrategy',
    'ORToolsCVRPStrategy',
    
    # Registry and utilities
    'STRATEGY_REGISTRY',
    'get_strategy',
    'get_all_strategies',
    'get_strategy_info',
    'get_available_solvers',
    'get_recommended_strategy',
    'get_strategies_by_pipeline',
]
