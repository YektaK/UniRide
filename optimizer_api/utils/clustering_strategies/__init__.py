from .base import BaseClusteringStrategy
from .kmeans import KMeansClusteringStrategy
from .fuzzy_cmeans import FuzzyCMeansClusteringStrategy
from .k_medoids import KMedoidsClusteringStrategy
from .sweep import SweepClusteringStrategy
from .clarke_wright import ClarkeWrightClusteringStrategy

def get_clustering_strategy(strategy_name: str, sw_capacity: int = 4, so_capacity: int = 5) -> BaseClusteringStrategy:
    """
    Factory method to get the appropriate clustering strategy.
    Fallback to K-Means if unknown strategy is provided.
    """
    strategies = {
        "kmeans": KMeansClusteringStrategy,
        "fuzzy_cmeans": FuzzyCMeansClusteringStrategy,
        "k_medoids": KMedoidsClusteringStrategy,
        "sweep": SweepClusteringStrategy,
        "clarke_wright": ClarkeWrightClusteringStrategy
    }
    
    strategy_class = strategies.get(strategy_name, KMeansClusteringStrategy)
    return strategy_class(sw_capacity=sw_capacity, so_capacity=so_capacity)
