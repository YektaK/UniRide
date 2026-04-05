"""
Enhanced Fuzzy C-Means Clustering Strategy with Border Point Detection and Transfer Mechanism

This module extends the basic FCM implementation with:
1. Border Point Detection - Identifying students with high membership to multiple clusters
2. Transfer Mechanism - Moving students between clusters when constraints are violated
3. Membership Metadata - Preserving and utilizing the membership matrix U

Reference:
- Based on MATLAB FCM implementations for TSP (FCM_TEK_ASAMA_UYELIK.m, FCM_IKI_ASAMA_MERKEZ.m)
- Adapted for VRP/CVRPTW problems

Author: Super Z AI Assistant
Date: 05 Nisan 2026
"""

import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from utils.clustering import Point, Cluster, calculate_centroid, haversine_distance, validate_cluster_capacity
from utils.clustering_strategies.base import BaseClusteringStrategy


class BorderStatus(str, Enum):
    """Border point status based on membership ambiguity"""
    HIGH = "HIGH"      # Very ambiguous, strong membership to 2+ clusters
    MEDIUM = "MEDIUM"  # Moderately ambiguous
    LOW = "LOW"        # Clear membership to one cluster


@dataclass
class StudentMembership:
    """
    Membership information for a student across all clusters.
    
    Attributes:
        student_id: Unique identifier for the student
        membership_values: Dict mapping cluster_id to membership value
        primary_cluster: Cluster with highest membership
        primary_membership: Highest membership value
        secondary_cluster: Cluster with second highest membership
        secondary_membership: Second highest membership value
        ambiguity_score: |primary - secondary|, lower = more ambiguous
        border_status: HIGH/MEDIUM/LOW based on ambiguity
    """
    student_id: str
    membership_values: Dict[int, float]
    primary_cluster: int
    primary_membership: float
    secondary_cluster: int
    secondary_membership: float
    ambiguity_score: float
    border_status: BorderStatus
    
    def get_membership(self, cluster_id: int) -> float:
        """Get membership value for a specific cluster"""
        return self.membership_values.get(cluster_id, 0.0)
    
    def is_border_point(self) -> bool:
        """Check if this student is a border point (HIGH or MEDIUM status)"""
        return self.border_status in [BorderStatus.HIGH, BorderStatus.MEDIUM]


@dataclass
class TransferCandidate:
    """
    A candidate student for transfer between clusters.
    
    Attributes:
        student: The student point to transfer
        student_membership: Membership metadata for the student
        source_cluster: Index of source cluster
        target_cluster: Index of target cluster
        priority_score: Lower = higher priority for transfer
        is_feasible: Whether transfer is feasible
        feasibility_reason: Reason if not feasible
    """
    student: Point
    student_membership: StudentMembership
    source_cluster: int
    target_cluster: int
    priority_score: float
    is_feasible: bool = True
    feasibility_reason: Optional[str] = None


@dataclass
class EnhancedCluster(Cluster):
    """
    Extended Cluster with membership metadata and border point information.
    
    Inherits from Cluster and adds:
        cluster_id: Unique identifier for this cluster
        membership_data: Dict mapping student_id to StudentMembership
        border_points: List of student_ids that are border points
        capacity_sw: SW capacity limit
        capacity_so: SO capacity limit
    """
    cluster_id: int = 0
    membership_data: Dict[str, StudentMembership] = field(default_factory=dict)
    border_points: List[str] = field(default_factory=list)
    capacity_sw: int = 4
    capacity_so: int = 5
    
    def get_sorted_border_points(self) -> List[Tuple[str, float]]:
        """
        Get border points sorted by ambiguity score (ascending).
        Lower score = higher priority for transfer.
        
        Returns:
            List of (student_id, ambiguity_score) tuples
        """
        border_with_scores = []
        for student_id in self.border_points:
            if student_id in self.membership_data:
                membership = self.membership_data[student_id]
                border_with_scores.append((student_id, membership.ambiguity_score))
        
        return sorted(border_with_scores, key=lambda x: x[1])
    
    def has_capacity_violation(self) -> bool:
        """Check if cluster violates capacity constraints"""
        return self.sw_count > self.capacity_sw or self.so_count > self.capacity_so
    
    def get_capacity_violation_severity(self) -> float:
        """Calculate severity of capacity violation"""
        sw_excess = max(0, self.sw_count - self.capacity_sw)
        so_excess = max(0, self.so_count - self.capacity_so)
        return sw_excess + so_excess


# Border status thresholds
BORDER_THRESHOLD_HIGH = 0.15   # ambiguity < 0.15 → HIGH
BORDER_THRESHOLD_MEDIUM = 0.30  # 0.15 ≤ ambiguity < 0.30 → MEDIUM
# ambiguity ≥ 0.30 → LOW


def _initialize_membership_matrix(n: int, k: int) -> List[List[float]]:
    """Initialize membership matrix with random values normalized per row."""
    U = []
    for _ in range(n):
        row = [random.random() for _ in range(k)]
        s = sum(row)
        U.append([x / s for x in row])
    return U


def fuzzy_c_means_with_membership(
    points: List[Point],
    k: int,
    filter_limit: int = 100,
    m: float = 2.0
) -> Tuple[List[Tuple[float, float]], List[List[float]], List[int]]:
    """
    Run FCM and return centroids, membership matrix, and assignments.
    
    This is the core FCM algorithm that preserves the membership matrix.
    
    Args:
        points: List of Point objects to cluster
        k: Number of clusters
        filter_limit: Maximum iterations
        m: Fuzziness parameter (typically 2.0)
    
    Returns:
        Tuple of (centroids, membership_matrix, assignments)
    """
    if not points or k <= 0:
        return [], [], []
    
    if k >= len(points):
        # Each point is its own cluster; cap the effective cluster count
        # to the number of available points so returned shapes stay consistent.
        effective_k = len(points)
        centroids = [(p.lat, p.lng) for p in points]
        U = [[1.0 if i == j else 0.0 for j in range(effective_k)] for i in range(len(points))]
        assignments = list(range(effective_k))
        return centroids, U, assignments
    
    n = len(points)
    U = _initialize_membership_matrix(n, k)
    centroids = [(0.0, 0.0)] * k
    
    for iteration in range(filter_limit):
        # Update centroids
        U_m = [[u ** m for u in row] for row in U]
        for j in range(k):
            sum_u_lat = sum(U_m[i][j] * points[i].lat for i in range(n))
            sum_u_lng = sum(U_m[i][j] * points[i].lng for i in range(n))
            sum_u = sum(U_m[i][j] for i in range(n))
            if sum_u == 0:
                sum_u = 1e-10
            centroids[j] = (sum_u_lat / sum_u, sum_u_lng / sum_u)
        
        # Update membership matrix
        new_U = [[0.0] * k for _ in range(n)]
        U_changed = False
        
        for i in range(n):
            distances = [
                max(haversine_distance(points[i].lat, points[i].lng, c[0], c[1]), 1e-10)
                for c in centroids
            ]
            for j in range(k):
                d_ij = distances[j]
                sum_ratio = sum((d_ij / d_ik) ** (2 / (m - 1)) for d_ik in distances)
                val = 1.0 / sum_ratio
                if abs(U[i][j] - val) > 1e-4:
                    U_changed = True
                new_U[i][j] = val
        
        U = new_U
        if not U_changed:
            break
    
    # Hard assignment (max membership)
    assignments = []
    for i in range(n):
        max_val = -1
        max_idx = 0
        for j in range(k):
            if U[i][j] > max_val:
                max_val = U[i][j]
                max_idx = j
        assignments.append(max_idx)
    
    return centroids, U, assignments


def analyze_border_points(
    membership_matrix: List[List[float]],
    points: List[Point],
    threshold_high: float = BORDER_THRESHOLD_HIGH,
    threshold_medium: float = BORDER_THRESHOLD_MEDIUM
) -> Dict[str, StudentMembership]:
    """
    Analyze membership matrix to identify border points.
    
    Border points are students with high membership to multiple clusters.
    They are good candidates for transfer when constraints are violated.
    
    Args:
        membership_matrix: U[n×k] membership values
        points: List of Point objects
        threshold_high: Ambiguity threshold for HIGH border status
        threshold_medium: Ambiguity threshold for MEDIUM border status
    
    Returns:
        Dict mapping student_id to StudentMembership
    """
    result = {}
    
    for i, point in enumerate(points):
        memberships = membership_matrix[i]
        
        # Sort by membership value (descending)
        sorted_indices = sorted(range(len(memberships)), key=lambda x: memberships[x], reverse=True)
        
        primary_cluster = sorted_indices[0]
        primary_membership = memberships[primary_cluster]
        
        secondary_cluster = sorted_indices[1] if len(sorted_indices) > 1 else -1
        secondary_membership = memberships[secondary_cluster] if secondary_cluster >= 0 else 0.0
        
        # Calculate ambiguity score
        ambiguity = abs(primary_membership - secondary_membership)
        
        # Determine border status
        if ambiguity < threshold_high:
            border_status = BorderStatus.HIGH
        elif ambiguity < threshold_medium:
            border_status = BorderStatus.MEDIUM
        else:
            border_status = BorderStatus.LOW
        
        result[point.id] = StudentMembership(
            student_id=point.id,
            membership_values={j: memberships[j] for j in range(len(memberships))},
            primary_cluster=primary_cluster,
            primary_membership=primary_membership,
            secondary_cluster=secondary_cluster,
            secondary_membership=secondary_membership,
            ambiguity_score=ambiguity,
            border_status=border_status
        )
    
    return result


def create_enhanced_clusters(
    points: List[Point],
    centroids: List[Tuple[float, float]],
    assignments: List[int],
    membership_data: Dict[str, StudentMembership],
    k: int,
    sw_capacity: int,
    so_capacity: int
) -> List[EnhancedCluster]:
    """
    Create EnhancedCluster objects with membership metadata.
    
    Maintains stable k-length structure (including empty clusters) to preserve
    cluster indices for membership references. Empty clusters are still included
    but marked with empty points.
    
    Args:
        points: List of Point objects
        centroids: Cluster centroids
        assignments: Assignment of each point to a cluster
        membership_data: Dict of student membership info
        k: Number of clusters
        sw_capacity: SW capacity limit
        so_capacity: SO capacity limit
    
    Returns:
        List of EnhancedCluster objects (length k, including empty ones)
    """
    clusters = []
    
    for j in range(k):
        cluster_points = [points[i] for i in range(len(points)) if assignments[i] == j]
        
        # Create cluster even if empty (stable structure for index consistency)
        if cluster_points:
            sw_count = sum(1 for p in cluster_points if p.disability_type == "Sw")
            so_count = sum(1 for p in cluster_points if p.disability_type == "So")
            
            # Get membership data for points in this cluster
            cluster_membership = {
                p.id: membership_data[p.id]
                for p in cluster_points
                if p.id in membership_data
            }
            
            # Identify border points
            border_points = [
                p.id for p in cluster_points
                if p.id in membership_data and membership_data[p.id].is_border_point()
            ]
            
            cluster = EnhancedCluster(
                centroid=centroids[j],
                points=cluster_points,
                sw_count=sw_count,
                so_count=so_count,
                cluster_id=j,
                membership_data=cluster_membership,
                border_points=border_points,
                capacity_sw=sw_capacity,
                capacity_so=so_capacity
            )
        else:
            # Empty cluster with valid centroid and cluster_id
            cluster = EnhancedCluster(
                centroid=centroids[j] if j < len(centroids) else (0.0, 0.0),
                points=[],
                sw_count=0,
                so_count=0,
                cluster_id=j,
                membership_data={},
                border_points=[],
                capacity_sw=sw_capacity,
                capacity_so=so_capacity
            )
        
        clusters.append(cluster)
    
    return clusters


def find_transfer_candidates(
    clusters: List[EnhancedCluster],
    sw_capacity: int,
    so_capacity: int
) -> List[TransferCandidate]:
    """
    Find transfer candidates from clusters with capacity violations.
    
    Candidates are sorted by priority (lowest ambiguity score = highest priority).
    Uses cluster.cluster_id for membership index lookup (not list position).
    
    Args:
        clusters: List of EnhancedCluster objects
        sw_capacity: SW capacity limit
        so_capacity: SO capacity limit
    
    Returns:
        List of TransferCandidate objects sorted by priority
    """
    candidates = []
    
    for cluster_id, cluster in enumerate(clusters):
        # Skip empty clusters
        if not cluster.points:
            continue
        
        # Check for capacity violation
        if not cluster.has_capacity_violation():
            continue
        
        # Get border points sorted by ambiguity (ascending)
        sorted_border = cluster.get_sorted_border_points()
        
        for student_id, ambiguity_score in sorted_border:
            if student_id not in cluster.membership_data:
                continue
            
            membership = cluster.membership_data[student_id]
            
            # Find student point
            student = next((p for p in cluster.points if p.id == student_id), None)
            if not student:
                continue
            
            # Get target cluster using membership's secondary_cluster index
            target_cluster_id = membership.secondary_cluster
            
            # Validate target cluster exists and is not empty
            if target_cluster_id < 0 or target_cluster_id >= len(clusters):
                continue
            
            target_cluster = clusters[target_cluster_id]
            
            # Skip empty target clusters
            if not target_cluster.points:
                continue
            
            # Check feasibility
            is_feasible = True
            reason = None
            
            # Check if target has capacity
            new_sw = target_cluster.sw_count + (1 if student.disability_type == "Sw" else 0)
            new_so = target_cluster.so_count + (1 if student.disability_type == "So" else 0)
            
            if new_sw > sw_capacity or new_so > so_capacity:
                is_feasible = False
                reason = f"Target cluster {target_cluster_id} would exceed capacity"
            
            candidate = TransferCandidate(
                student=student,
                student_membership=membership,
                source_cluster=cluster_id,
                target_cluster=target_cluster_id,
                priority_score=ambiguity_score,
                is_feasible=is_feasible,
                feasibility_reason=reason
            )
            candidates.append(candidate)
            
            # Only take one candidate per violating cluster
            break
    
    # Sort by priority (lower = higher priority)
    candidates.sort(key=lambda x: x.priority_score)
    
    return candidates


def execute_transfer(
    clusters: List[EnhancedCluster],
    candidate: TransferCandidate
) -> List[EnhancedCluster]:
    """
    Execute a transfer of a student between clusters.
    
    Args:
        clusters: List of EnhancedCluster objects
        candidate: TransferCandidate to execute
    
    Returns:
        Updated list of EnhancedCluster objects
    """
    source = clusters[candidate.source_cluster]
    target = clusters[candidate.target_cluster]
    
    student = candidate.student
    
    # Remove from source
    source.points.remove(student)
    if student.id in source.membership_data:
        del source.membership_data[student.id]
    if student.id in source.border_points:
        source.border_points.remove(student.id)
    
    # Update source counts
    if student.disability_type == "Sw":
        source.sw_count -= 1
    else:
        source.so_count -= 1
    
    # Add to target
    target.points.append(student)
    # Always add membership data (unconditionally)
    target.membership_data[student.id] = candidate.student_membership
    # Add to border_points with duplicate check
    if (
        candidate.student_membership.is_border_point()
        and student.id not in target.border_points
    ):
        target.border_points.append(student.id)
    
    # Update target counts
    if student.disability_type == "Sw":
        target.sw_count += 1
    else:
        target.so_count += 1
    
    # Update centroids
    if source.points:
        source.centroid = calculate_centroid(source.points)
    if target.points:
        target.centroid = calculate_centroid(target.points)
    
    return clusters


def run_transfer_optimization(
    clusters: List[EnhancedCluster],
    sw_capacity: int,
    so_capacity: int,
    max_iterations: int = 50
) -> List[EnhancedCluster]:
    """
    Run transfer optimization to resolve capacity violations.
    
    Iteratively transfers border points from violating clusters
    to their secondary clusters when feasible.
    
    Args:
        clusters: List of EnhancedCluster objects
        sw_capacity: SW capacity limit
        so_capacity: SO capacity limit
        max_iterations: Maximum number of transfer iterations
    
    Returns:
        Optimized list of EnhancedCluster objects
    """
    for iteration in range(max_iterations):
        # Check if all clusters are valid
        violations = sum(1 for c in clusters if c.has_capacity_violation())
        
        if violations == 0:
            break
        
        # Find transfer candidates
        candidates = find_transfer_candidates(clusters, sw_capacity, so_capacity)
        
        if not candidates:
            break
        
        # Get the highest priority feasible candidate
        feasible = [c for c in candidates if c.is_feasible]
        
        if not feasible:
            break
        
        # Execute the highest priority transfer
        clusters = execute_transfer(clusters, feasible[0])
    
    return clusters


def enhanced_fuzzy_c_means_core(
    points: List[Point],
    k: int,
    sw_capacity: int = 4,
    so_capacity: int = 5,
    filter_limit: int = 100,
    m: float = 2.0,
    enable_transfer: bool = True
) -> List[EnhancedCluster]:
    """
    Enhanced FCM with border point detection and transfer mechanism.
    
    This is the main entry point for the enhanced FCM algorithm.
    
    Args:
        points: List of Point objects to cluster
        k: Number of clusters
        sw_capacity: SW capacity limit per cluster
        so_capacity: SO capacity limit per cluster
        filter_limit: Maximum FCM iterations
        m: Fuzziness parameter
        enable_transfer: Whether to enable transfer optimization
    
    Returns:
        List of EnhancedCluster objects with membership metadata
    """
    if not points or k <= 0:
        return []
    
    if k >= len(points):
        # Each point is its own cluster
        return [
            EnhancedCluster(
                centroid=(p.lat, p.lng),
                points=[p],
                sw_count=1 if p.disability_type == "Sw" else 0,
                so_count=1 if p.disability_type == "So" else 0,
                cluster_id=i,
                capacity_sw=sw_capacity,
                capacity_so=so_capacity
            )
            for i, p in enumerate(points)
        ]
    
    # Step 1: Run FCM and get membership matrix
    centroids, U, assignments = fuzzy_c_means_with_membership(points, k, filter_limit, m)
    
    # Step 2: Analyze border points
    membership_data = analyze_border_points(U, points)
    
    # Step 3: Create enhanced clusters
    clusters = create_enhanced_clusters(
        points, centroids, assignments, membership_data, k, sw_capacity, so_capacity
    )
    
    # Step 4: Run transfer optimization if enabled
    if enable_transfer:
        clusters = run_transfer_optimization(clusters, sw_capacity, so_capacity)
    
    return clusters


class EnhancedFuzzyCMeansStrategy(BaseClusteringStrategy):
    """
    Enhanced Fuzzy C-Means clustering strategy with border point detection.
    
    This strategy extends the basic FCM with:
    - Membership metadata preservation
    - Border point identification
    - Transfer mechanism for capacity violations
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        """
        Cluster students using enhanced FCM with transfer optimization.
        
        Args:
            students: List of Point objects representing students
            num_vehicles: Number of vehicles (clusters)
            **kwargs: Additional parameters:
                - enable_transfer: bool (default True)
                - max_iterations: int (default 100)
        
        Returns:
            List of Cluster objects (converted from EnhancedCluster)
        """
        enable_transfer = kwargs.get("enable_transfer", True)
        max_iterations = kwargs.get("max_iterations", 100)
        
        enhanced_clusters = enhanced_fuzzy_c_means_core(
            students,
            num_vehicles,
            self.sw_capacity,
            self.so_capacity,
            filter_limit=max_iterations,
            enable_transfer=enable_transfer
        )
        
        # Convert to base Cluster for compatibility
        # But first, validate and split over-capacity clusters if any remain
        validated_clusters = []
        for cluster in enhanced_clusters:
            if validate_cluster_capacity(cluster, self.sw_capacity, self.so_capacity):
                # Convert to base Cluster for compatibility
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
                        # Ultimate fallback: one student per cluster
                        for point in sc.points:
                            validated_clusters.append(Cluster(
                                centroid=(point.lat, point.lng),
                                points=[point],
                                sw_count=1 if point.disability_type == "Sw" else 0,
                                so_count=1 if point.disability_type == "So" else 0
                            ))
        
        return validated_clusters
    
    def _split_cluster(self, cluster: Cluster) -> List[Cluster]:
        """Split an over-capacity cluster into two using FCM."""
        if len(cluster.points) <= 1:
            return [cluster]
        
        # Use enhanced FCM for splitting
        enhanced = enhanced_fuzzy_c_means_core(
            cluster.points,
            2,
            self.sw_capacity,
            self.so_capacity,
            enable_transfer=False
        )
        
        # Convert to base Cluster
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
    'BorderStatus',
    'StudentMembership',
    'TransferCandidate',
    'EnhancedCluster',
    'fuzzy_c_means_with_membership',
    'analyze_border_points',
    'create_enhanced_clusters',
    'find_transfer_candidates',
    'execute_transfer',
    'run_transfer_optimization',
    'enhanced_fuzzy_c_means_core',
    'EnhancedFuzzyCMeansStrategy',
    'BORDER_THRESHOLD_HIGH',
    'BORDER_THRESHOLD_MEDIUM',
]
