from typing import List, Tuple, Any
from uniride_core.algorithms.local_search_numba import LocalSearchType

LOCAL_SEARCH_STRATEGIES: List[Tuple[str, Any, dict]] = [
    ("2-opt", LocalSearchType.TWO_OPT, {"max_iterations": 3000, "algorithm_type": "local_search"}),
    ("3-opt-bounded", LocalSearchType.THREE_OPT, {"max_iterations": 400, "algorithm_type": "local_search"}),
    ("Or-opt", LocalSearchType.OR_OPT, {"max_iterations": 1500, "algorithm_type": "local_search"}),
    ("Swap", LocalSearchType.SWAP, {"max_iterations": 8000, "algorithm_type": "local_search"}),
    ("Hybrid", LocalSearchType.HYBRID, {"max_iterations": 10, "algorithm_type": "local_search"}),
]

META_HEURISTIC_STRATEGIES: List[Tuple[str, str, dict]] = [
    ("GA", "GA", {"pop_size": 120, "generations": 300, "mutation_rate": 0.12, "elite_size": 6, "algorithm_type": "meta_heuristic"}),
    ("PSO", "PSO", {"swarm_size": 80, "iterations": 250, "w": 0.72, "c1": 1.6, "c2": 1.6, "algorithm_type": "meta_heuristic"}),
    ("GWO", "GWO", {"pack_size": 80, "iterations": 250, "algorithm_type": "meta_heuristic"}),
    ("HHO", "HHO", {"hawks": 80, "iterations": 250, "algorithm_type": "meta_heuristic"}),
]

STRATEGIES = LOCAL_SEARCH_STRATEGIES + META_HEURISTIC_STRATEGIES
