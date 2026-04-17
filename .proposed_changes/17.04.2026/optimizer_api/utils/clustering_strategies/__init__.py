"""
Clustering Strategies Module

This module provides various clustering strategies for CVRP/CVRPTW problems.
Available strategies:
- kmeans: K-Means clustering (fast, geometric)
- fuzzy_cmeans: Fuzzy C-Means (soft assignment)
- fuzzy_cmeans_enhanced: Enhanced FCM with border detection and transfer
- hierarchical_fcm: Two-stage FCM for large problems
- k_medoids: K-Medoids (uses actual distances)
- sweep: Sweep algorithm (depot-centric)
- clarke_wright: Clarke-Wright savings algorithm

Author: UniRide Team
Date: 05 Nisan 2026
"""

from .base import BaseClusteringStrategy
from .kmeans import KMeansClusteringStrategy
from .fuzzy_cmeans import FuzzyCMeansClusteringStrategy
from .fuzzy_cmeans_enhanced import EnhancedFuzzyCMeansStrategy, EnhancedCluster, StudentMembership
from .hierarchical_fcm import HierarchicalFCMStrategy, HierarchicalConfig
from .k_medoids import KMedoidsClusteringStrategy
from .sweep import SweepClusteringStrategy
from .clarke_wright import ClarkeWrightClusteringStrategy


def get_clustering_strategy(
    strategy_name: str, 
    sw_capacity: int = 4, 
    so_capacity: int = 5,
    **kwargs
) -> BaseClusteringStrategy:
    """
    Factory method to get the appropriate clustering strategy.
    
    Args:
        strategy_name: Name of the clustering strategy
        sw_capacity: SW (tekerlekli sandalye) capacity per vehicle
        so_capacity: SO (tekerlekli sandalye olmayan) capacity per vehicle
        **kwargs: Additional parameters for specific strategies
            - hierarchical_threshold: For hierarchical_fcm, default 50
            - students_per_region: For hierarchical_fcm, default 30
    
    Returns:
        Instance of the requested clustering strategy
    
    Fallback:
        Defaults to Sweep if unknown strategy is provided (better for CVRP than K-Means)
    """
    strategies = {
        "kmeans": KMeansClusteringStrategy,
        "fuzzy_cmeans": FuzzyCMeansClusteringStrategy,
        "fuzzy_cmeans_enhanced": EnhancedFuzzyCMeansStrategy,
        "hierarchical_fcm": HierarchicalFCMStrategy,
        "k_medoids": KMedoidsClusteringStrategy,
        "sweep": SweepClusteringStrategy,
        "clarke_wright": ClarkeWrightClusteringStrategy,
    }
    
    strategy_class = strategies.get(strategy_name, SweepClusteringStrategy)
    
    # Handle special initialization parameters
    if strategy_name == "hierarchical_fcm":
        return strategy_class(
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
            hierarchical_threshold=kwargs.get('hierarchical_threshold', 50),
            students_per_region=kwargs.get('students_per_region', 30)
        )
    
    return strategy_class(sw_capacity=sw_capacity, so_capacity=so_capacity)


# Export all strategies
__all__ = [
    'BaseClusteringStrategy',
    'KMeansClusteringStrategy',
    'FuzzyCMeansClusteringStrategy',
    'EnhancedFuzzyCMeansStrategy',
    'EnhancedCluster',
    'StudentMembership',
    'HierarchicalFCMStrategy',
    'HierarchicalConfig',
    'KMedoidsClusteringStrategy',
    'SweepClusteringStrategy',
    'ClarkeWrightClusteringStrategy',
    'get_clustering_strategy',
]
