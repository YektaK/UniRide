"""Compatibility exports for core clustering and vehicle assignment utilities."""

from uniride_core.algorithms.clustering import (  # noqa: F401
    Cluster,
    Point,
    calculate_centroid,
    initialize_centroids_kmeans_plus_plus,
    kmeans_clustering,
    split_cluster,
    validate_cluster_capacity,
)
from uniride_core.algorithms.distance import haversine_distance  # noqa: F401
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator  # noqa: F401

__all__ = [
    "Cluster",
    "Point",
    "VehicleCalculator",
    "calculate_centroid",
    "haversine_distance",
    "initialize_centroids_kmeans_plus_plus",
    "kmeans_clustering",
    "split_cluster",
    "validate_cluster_capacity",
]
