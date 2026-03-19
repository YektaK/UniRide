import math
import random
from typing import List, Tuple
from utils.clustering import Point, Cluster, calculate_centroid, haversine_distance, validate_cluster_capacity
from utils.clustering_strategies.base import BaseClusteringStrategy

def _initialize_membership_matrix(n: int, k: int) -> List[List[float]]:
    U = []
    for _ in range(n):
        row = [random.random() for _ in range(k)]
        s = sum(row)
        U.append([x / s for x in row])
    return U

def fuzzy_c_means_core(points: List[Point], k: int, filter_limit: int = 100, m: float = 2.0) -> List[Cluster]:
    if not points or k <= 0: return []
    if k >= len(points):
        return [Cluster(centroid=(p.lat, p.lng), points=[p], sw_count=1 if p.disability_type == "Sw" else 0, so_count=1 if p.disability_type == "So" else 0) for p in points]

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
            if sum_u == 0: sum_u = 1e-10
            centroids[j] = (sum_u_lat / sum_u, sum_u_lng / sum_u)
            
        # Update membership matrix U
        new_U = [[0.0] * k for _ in range(n)]
        U_changed = False
        
        for i in range(n):
            distances = [max(haversine_distance(points[i].lat, points[i].lng, c[0], c[1]), 1e-10) for c in centroids]
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

    # Hard assignment step (max membership)
    assignments = []
    for i in range(n):
        max_val = -1
        max_idx = 0
        for j in range(k):
            if U[i][j] > max_val:
                max_val = U[i][j]
                max_idx = j
        assignments.append(max_idx)

    clusters = []
    for j in range(k):
        cluster_points = [points[i] for i in range(n) if assignments[i] == j]
        if cluster_points:
            sw_count = sum(1 for p in cluster_points if p.disability_type == "Sw")
            so_count = sum(1 for p in cluster_points if p.disability_type == "So")
            clusters.append(Cluster(centroid=centroids[j], points=cluster_points, sw_count=sw_count, so_count=so_count))
            
    return clusters

class FuzzyCMeansClusteringStrategy(BaseClusteringStrategy):
    """
    Fuzzy C-Means clustering strategy.
    Assigns points softly to all clusters before resolving into discrete sets, ensuring less rigid geographic boundaries.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        clusters = fuzzy_c_means_core(students, num_vehicles)
        
        # Fallback to recursively split over-capacity clusters just in case
        validated_clusters = []
        for cluster in clusters:
            if validate_cluster_capacity(cluster, self.sw_capacity, self.so_capacity):
                validated_clusters.append(cluster)
            else:
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
        if len(cluster.points) <= 1:
            return [cluster]
        return fuzzy_c_means_core(cluster.points, 2)
