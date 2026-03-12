# Expose strategies for easy importing
from strategies.base_strategy import BaseRoutingStrategy
from strategies.kmeans_tsp import KMeansTSPStrategy
from strategies.ortools_cvrp import ORToolsCVRPStrategy
from strategies.greedy_heuristic import GreedyHeuristicStrategy
from strategies.permutation_tsp import PermutationTSPStrategy

# Dictionary to map string names to actual class instances
STRATEGY_REGISTRY = {
    "kmeans_tsp": KMeansTSPStrategy(),
    "ortools_cvrp": ORToolsCVRPStrategy(),
    "greedy_heuristic": GreedyHeuristicStrategy(),
    "permutation_tsp": PermutationTSPStrategy()
}
