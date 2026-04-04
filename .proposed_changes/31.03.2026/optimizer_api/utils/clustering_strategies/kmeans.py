import random
from typing import List, Tuple
from utils.clustering import Point, Cluster, calculate_centroid, haversine_distance, validate_cluster_capacity
from utils.clustering_strategies.base import BaseClusteringStrategy

def initialize_centroids_kmeans_plus_plus(points: List[Point], k: int) -> List[Tuple[float, float]]:
    if k <= 0 or not points:
        return []
    centroids = []
    first_idx = random.randint(0, len(points) - 1)
    centroids.append((points[first_idx].lat, points[first_idx].lng))

    while len(centroids) < k:
        distances = []
        for point in points:
            min_dist = min(haversine_distance(point.lat, point.lng, c[0], c[1]) ** 2 for c in centroids)
            distances.append(min_dist)

        total_dist = sum(distances)
        if total_dist == 0:
            break
        r = random.random() * total_dist
        cumulative = 0
        for i, d in enumerate(distances):
            cumulative += d
            if cumulative >= r:
                centroids.append((points[i].lat, points[i].lng))
                break
    return centroids

def kmeans_clustering_core(points: List[Point], k: int, max_iterations: int = 100) -> List[Cluster]:
    if not points or k <= 0: return []
    if k >= len(points):
        return [Cluster(centroid=(p.lat, p.lng), points=[p], sw_count=1 if p.disability_type == "Sw" else 0, so_count=1 if p.disability_type == "So" else 0) for p in points]

    centroids = initialize_centroids_kmeans_plus_plus(points, k)
    prev_assignments = [-1] * len(points)

    for iteration in range(max_iterations):
        assignments = []
        for point in points:
            min_dist = float('inf')
            min_idx = 0
            for i, centroid in enumerate(centroids):
                dist = haversine_distance(point.lat, point.lng, centroid[0], centroid[1])
                if dist < min_dist:
                    min_dist = dist
                    min_idx = i
            assignments.append(min_idx)

        if assignments == prev_assignments:
            break
        prev_assignments = assignments

        for i in range(k):
            cluster_points = [points[j] for j in range(len(points)) if assignments[j] == i]
            if cluster_points:
                centroids[i] = calculate_centroid(cluster_points)

    clusters = []
    for i in range(k):
        cluster_points = [points[j] for j in range(len(points)) if prev_assignments[j] == i]
        if cluster_points:
            sw_count = sum(1 for p in cluster_points if p.disability_type == "Sw")
            so_count = sum(1 for p in cluster_points if p.disability_type == "So")
            clusters.append(Cluster(centroid=centroids[i], points=cluster_points, sw_count=sw_count, so_count=so_count))
    return clusters

class KMeansClusteringStrategy(BaseClusteringStrategy):
    """
    Standard K-Means clustering algorithm using geographic (lat/lng) distances.
    Splits over-capacity clusters recursively.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        clusters = kmeans_clustering_core(students, num_vehicles)
        
        # Validate and split over-capacity clusters
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
        return kmeans_clustering_core(cluster.points, 2)
