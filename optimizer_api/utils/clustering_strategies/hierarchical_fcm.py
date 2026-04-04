"""
Hierarchical Fuzzy C-Means Clustering for Large-Scale VRP Problems

This module implements a two-stage FCM clustering approach for large problems:
1. Stage 1 (Coarse): Partition students into geographic regions
2. Stage 2 (Fine): Within each region, create vehicle-specific clusters
3. Stage 3: Border point transfer optimization across regions

The hierarchical approach provides:
- Better scalability for large N (N > threshold)
- Improved solution quality through localized optimization
- Parallel processing potential

Reference:
- Based on MATLAB FCM_IKI_ASAMA_MERKEZ.m approach
- Adapted for CVRP/CVRPTW problems

Author: Super Z AI Assistant
Date: 05 Nisan 2026
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from utils.clustering import Point, Cluster, calculate_centroid, validate_cluster_capacity
from utils.clustering_strategies.base import BaseClusteringStrategy
from utils.clustering_strategies.fuzzy_cmeans_enhanced import (
    enhanced_fuzzy_c_means_core,
    EnhancedCluster,
    BorderStatus,
    analyze_border_points,
    run_transfer_optimization,
    fuzzy_c_means_with_membership,
    create_enhanced_clusters,
    BORDER_THRESHOLD_HIGH,
    BORDER_THRESHOLD_MEDIUM
)


@dataclass
class HierarchicalConfig:
    """Configuration for hierarchical FCM clustering."""
    
    # Threshold for switching to hierarchical mode
    # N > threshold → hierarchical, N ≤ threshold → standard
    hierarchical_threshold: int = 50
    
    # Target number of students per region (Stage 1)
    students_per_region: int = 30
    
    # Minimum number of regions
    min_regions: int = 2
    
    # Enable cross-region transfer optimization
    enable_cross_region_transfer: bool = True
    
    # Maximum transfer iterations
    max_transfer_iterations: int = 50
    
    # FCM parameters
    fcm_max_iterations: int = 100
    fcm_fuzziness: float = 2.0


def calculate_region_allocation(
    n_students: int,
    n_vehicles: int,
    config: HierarchicalConfig
) -> Tuple[int, int]:
    """
    Calculate number of regions and vehicles per region.
    
    Args:
        n_students: Total number of students
        n_vehicles: Total number of vehicles
        config: Hierarchical configuration
    
    Returns:
        Tuple of (num_regions, avg_vehicles_per_region)
    """
    # Calculate number of regions based on students per region
    num_regions = max(
        config.min_regions,
        math.ceil(n_students / config.students_per_region)
    )
    
    # Don't create more regions than vehicles
    num_regions = min(num_regions, n_vehicles)
    
    # Average vehicles per region
    avg_vehicles = max(1, n_vehicles // num_regions)
    
    return num_regions, avg_vehicles


def stage1_regional_clustering(
    points: List[Point],
    num_regions: int,
    config: HierarchicalConfig
) -> List[EnhancedCluster]:
    """
    Stage 1: Partition students into geographic regions.
    
    Uses standard FCM to create coarse-grained regions.
    
    Args:
        points: All student points
        num_regions: Number of regions to create
        config: Hierarchical configuration
    
    Returns:
        List of region clusters (coarse)
    """
    return enhanced_fuzzy_c_means_core(
        points,
        num_regions,
        sw_capacity=float('inf'),  # No capacity limit at region level
        so_capacity=float('inf'),
        filter_limit=config.fcm_max_iterations,
        m=config.fcm_fuzziness,
        enable_transfer=False  # No transfer at region level
    )


def stage2_vehicle_clustering(
    region: EnhancedCluster,
    num_vehicles: int,
    sw_capacity: int,
    so_capacity: int,
    config: HierarchicalConfig
) -> List[EnhancedCluster]:
    """
    Stage 2: Within a region, create vehicle-specific clusters.
    
    Args:
        region: Region cluster from Stage 1
        num_vehicles: Number of vehicles for this region
        sw_capacity: SW capacity limit
        so_capacity: SO capacity limit
        config: Hierarchical configuration
    
    Returns:
        List of vehicle clusters within the region
    """
    if not region.points:
        return []
    
    # Don't create more clusters than points
    actual_vehicles = min(num_vehicles, len(region.points))
    
    if actual_vehicles <= 0:
        return []
    
    if actual_vehicles == 1:
        # Single vehicle for this region
        return [EnhancedCluster(
            centroid=region.centroid,
            points=region.points,
            sw_count=region.sw_count,
            so_count=region.so_count,
            cluster_id=0,
            capacity_sw=sw_capacity,
            capacity_so=so_capacity
        )]
    
    return enhanced_fuzzy_c_means_core(
        region.points,
        actual_vehicles,
        sw_capacity,
        so_capacity,
        filter_limit=config.fcm_max_iterations,
        m=config.fcm_fuzziness,
        enable_transfer=True
    )


def distribute_vehicles_to_regions(
    regions: List[EnhancedCluster],
    n_vehicles: int,
    sw_capacity: int,
    so_capacity: int
) -> List[int]:
    """
    Distribute vehicles among regions based on student count.
    
    Uses proportional allocation with minimum 1 vehicle per region.
    
    Args:
        regions: List of region clusters
        n_vehicles: Total number of vehicles
        sw_capacity: SW capacity (for weighted allocation)
        so_capacity: SO capacity
    
    Returns:
        List of vehicle counts per region
    """
    n_regions = len(regions)
    
    if n_regions == 0:
        return []
    
    if n_regions == 1:
        return [n_vehicles]
    
    # Calculate total students and weight per region
    total_students = sum(len(r.points) for r in regions)
    
    if total_students == 0:
        return [1] * n_regions
    
    # Proportional allocation
    allocations = []
    remaining_vehicles = n_vehicles
    
    for i, region in enumerate(regions):
        if i == n_regions - 1:
            # Last region gets remaining vehicles
            allocations.append(remaining_vehicles)
        else:
            # Proportional to student count
            proportion = len(region.points) / total_students
            vehicles = max(1, round(n_vehicles * proportion))
            allocations.append(vehicles)
            remaining_vehicles -= vehicles
    
    return allocations


def stage3_cross_region_transfer(
    all_clusters: List[EnhancedCluster],
    membership_matrix: List[List[float]],
    points: List[Point],
    sw_capacity: int,
    so_capacity: int,
    config: HierarchicalConfig
) -> List[EnhancedCluster]:
    """
    Stage 3: Cross-region border point transfer optimization.
    
    Identifies students near region boundaries and transfers them
    to resolve capacity violations.
    
    Args:
        all_clusters: All vehicle clusters from all regions
        membership_matrix: Original membership matrix (all points × all clusters)
        points: All student points
        sw_capacity: SW capacity limit
        so_capacity: SO capacity limit
        config: Hierarchical configuration
    
    Returns:
        Optimized list of clusters
    """
    if not config.enable_cross_region_transfer:
        return all_clusters
    
    # Rebuild membership data for all clusters
    global_membership = analyze_border_points(membership_matrix, points)
    
    # Update cluster membership data
    for cluster in all_clusters:
        for point in cluster.points:
            if point.id in global_membership:
                cluster.membership_data[point.id] = global_membership[point.id]
                if global_membership[point.id].is_border_point():
                    if point.id not in cluster.border_points:
                        cluster.border_points.append(point.id)
    
    # Run transfer optimization
    return run_transfer_optimization(
        all_clusters,
        sw_capacity,
        so_capacity,
        config.max_transfer_iterations
    )


def hierarchical_fcm_clustering(
    points: List[Point],
    num_vehicles: int,
    sw_capacity: int = 4,
    so_capacity: int = 5,
    config: Optional[HierarchicalConfig] = None
) -> List[EnhancedCluster]:
    """
    Main entry point for hierarchical FCM clustering.
    
    Automatically chooses between standard and hierarchical mode
    based on problem size.
    
    Args:
        points: List of student points
        num_vehicles: Number of vehicles
        sw_capacity: SW capacity limit
        so_capacity: SO capacity limit
        config: Optional configuration (uses defaults if None)
    
    Returns:
        List of EnhancedCluster objects
    """
    if config is None:
        config = HierarchicalConfig()
    
    n = len(points)
    
    # Check if hierarchical mode is needed
    if n <= config.hierarchical_threshold:
        # Standard single-stage FCM
        return enhanced_fuzzy_c_means_core(
            points,
            num_vehicles,
            sw_capacity,
            so_capacity,
            filter_limit=config.fcm_max_iterations,
            m=config.fcm_fuzziness,
            enable_transfer=True
        )
    
    # HIERARCHICAL MODE
    # ==================
    
    # Stage 1: Regional clustering
    num_regions, _ = calculate_region_allocation(n, num_vehicles, config)
    
    # Ensure we don't have more regions than vehicles
    if num_regions > num_vehicles:
        num_regions = num_vehicles
    
    regions = stage1_regional_clustering(points, num_regions, config)
    
    # Stage 2: Vehicle clustering within each region
    vehicle_allocations = distribute_vehicles_to_regions(
        regions, num_vehicles, sw_capacity, so_capacity
    )
    
    all_clusters = []
    cluster_id_counter = 0
    
    for region, n_vehicles in zip(regions, vehicle_allocations):
        region_clusters = stage2_vehicle_clustering(
            region, n_vehicles, sw_capacity, so_capacity, config
        )
        
        # Assign global cluster IDs
        for cluster in region_clusters:
            cluster.cluster_id = cluster_id_counter
            cluster_id_counter += 1
        
        all_clusters.extend(region_clusters)
    
    # Stage 3: Cross-region transfer (simplified - uses local membership)
    # Note: Full cross-region transfer would require recomputing membership
    # across all clusters, which is expensive. Instead, we run local transfer.
    for _ in range(config.max_transfer_iterations):
        violations = sum(1 for c in all_clusters if c.has_capacity_violation())
        if violations == 0:
            break
        
        all_clusters = run_transfer_optimization(
            all_clusters,
            sw_capacity,
            so_capacity,
            max_iterations=1
        )
    
    return all_clusters


class HierarchicalFCMStrategy(BaseClusteringStrategy):
    """
    Hierarchical FCM clustering strategy for large-scale problems.
    
    Uses two-stage clustering when problem size exceeds threshold,
    otherwise falls back to standard enhanced FCM.
    """
    
    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        hierarchical_threshold: int = 50,
        students_per_region: int = 30
    ):
        """
        Initialize hierarchical FCM strategy.
        
        Args:
            sw_capacity: SW capacity per vehicle
            so_capacity: SO capacity per vehicle
            hierarchical_threshold: Switch to hierarchical mode if N > threshold
            students_per_region: Target students per region in Stage 1
        """
        super().__init__(sw_capacity, so_capacity)
        self.config = HierarchicalConfig(
            hierarchical_threshold=hierarchical_threshold,
            students_per_region=students_per_region
        )
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        """
        Cluster students using hierarchical FCM.
        
        Args:
            students: List of student points
            num_vehicles: Number of vehicles
            **kwargs: Additional parameters (override config)
        
        Returns:
            List of Cluster objects
        """
        # Allow config override via kwargs
        config = HierarchicalConfig(
            hierarchical_threshold=kwargs.get('hierarchical_threshold', self.config.hierarchical_threshold),
            students_per_region=kwargs.get('students_per_region', self.config.students_per_region),
            enable_cross_region_transfer=kwargs.get('enable_cross_region_transfer', True)
        )
        
        enhanced_clusters = hierarchical_fcm_clustering(
            students,
            num_vehicles,
            self.sw_capacity,
            self.so_capacity,
            config
        )
        
        # Validate and handle remaining violations
        validated_clusters = []
        for cluster in enhanced_clusters:
            if validate_cluster_capacity(cluster, self.sw_capacity, self.so_capacity):
                validated_clusters.append(Cluster(
                    centroid=cluster.centroid,
                    points=cluster.points,
                    sw_count=cluster.sw_count,
                    so_count=cluster.so_count
                ))
            else:
                # Split over-capacity cluster
                split_clusters = self._split_cluster(cluster)
                for sc in split_clusters:
                    if validate_cluster_capacity(sc, self.sw_capacity, self.so_capacity):
                        validated_clusters.append(sc)
                    else:
                        for point in sc.points:
                            validated_clusters.append(Cluster(
                                centroid=(point.lat, point.lng),
                                points=[point],
                                sw_count=1 if point.disability_type == "Sw" else 0,
                                so_count=1 if point.disability_type == "So" else 0
                            ))
        
        return validated_clusters
    
    def _split_cluster(self, cluster: Cluster) -> List[Cluster]:
        """Split an over-capacity cluster using enhanced FCM."""
        if len(cluster.points) <= 1:
            return [cluster]
        
        enhanced = enhanced_fuzzy_c_means_core(
            cluster.points,
            2,
            self.sw_capacity,
            self.so_capacity,
            enable_transfer=False
        )
        
        return [
            Cluster(
                centroid=c.centroid,
                points=c.points,
                sw_count=c.sw_count,
                so_count=c.so_count
            )
            for c in enhanced
        ]


# Export classes and functions
__all__ = [
    'HierarchicalConfig',
    'calculate_region_allocation',
    'stage1_regional_clustering',
    'stage2_vehicle_clustering',
    'distribute_vehicles_to_regions',
    'stage3_cross_region_transfer',
    'hierarchical_fcm_clustering',
    'HierarchicalFCMStrategy',
]
