from typing import List, Dict, Optional
import random
from utils.clustering import Point, Cluster, calculate_centroid, validate_cluster_capacity
from utils.clustering_strategies.base import BaseClusteringStrategy
from utils.data_loader import estimate_travel_time, haversine_distance

def get_duration(p1: Point, p2: Point, time_matrix: Dict) -> float:
    """Returns actual time or falls back to haversine estimate."""
    if p1.location_code in time_matrix and p2.location_code in time_matrix[p1.location_code]:
        return time_matrix[p1.location_code][p2.location_code]
    dist = haversine_distance(p1.lat, p1.lng, p2.lat, p2.lng)
    return estimate_travel_time(dist)

def initialize_medoids(points: List[Point], k: int) -> List[Point]:
    if k <= 0 or not points: return []
    return random.sample(points, min(k, len(points)))

def k_medoids_clustering_core(points: List[Point], k: int, time_matrix: Dict, max_iterations: int = 50) -> List[Cluster]:
    if not points or k <= 0: return []
    if k >= len(points):
        return [Cluster(centroid=(p.lat, p.lng), points=[p], sw_count=1 if p.disability_type == "Sw" else 0, so_count=1 if p.disability_type == "So" else 0) for p in points]

    medoids = initialize_medoids(points, k)
    prev_assignments = [-1] * len(points)
    
    for iteration in range(max_iterations):
        assignments = []
        for point in points:
            min_dist = float('inf')
            min_idx = 0
            for i, medoid in enumerate(medoids):
                dist = get_duration(medoid, point, time_matrix)
                if dist < min_dist:
                    min_dist = dist
                    min_idx = i
            assignments.append(min_idx)
            
        if assignments == prev_assignments:
            break
        prev_assignments = assignments
        
        # Update medoids (swap step): find point in cluster that minimizes total distance to other points in cluster
        for i in range(k):
            cluster_points = [points[j] for j in range(len(points)) if assignments[j] == i]
            if not cluster_points: continue
            
            best_medoid = medoids[i]
            min_total_cost = float('inf')
            
            for potential_medoid in cluster_points:
                cost = sum(get_duration(potential_medoid, p, time_matrix) for p in cluster_points)
                if cost < min_total_cost:
                    min_total_cost = cost
                    best_medoid = potential_medoid
            medoids[i] = best_medoid

    clusters = []
    for i in range(k):
        cluster_points = [points[j] for j in range(len(points)) if prev_assignments[j] == i]
        if cluster_points:
            sw_count = sum(1 for p in cluster_points if p.disability_type == "Sw")
            so_count = sum(1 for p in cluster_points if p.disability_type == "So")
            clusters.append(Cluster(centroid=(medoids[i].lat, medoids[i].lng), points=cluster_points, sw_count=sw_count, so_count=so_count))
    return clusters

class KMedoidsClusteringStrategy(BaseClusteringStrategy):
    """
    Time-Matrix based K-Medoids algorithm (PAM).
    Clusters using actual driving time instead of Haversine distance.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        time_matrix = kwargs.get("time_matrix", {})
        clusters = k_medoids_clustering_core(students, num_vehicles, time_matrix)
        
        # Validate and split over-capacity clusters
        validated_clusters = []
        for cluster in clusters:
            if validate_cluster_capacity(cluster, self.sw_capacity, self.so_capacity):
                validated_clusters.append(cluster)
            else:
                split_clusters = self._split_cluster(cluster, time_matrix)
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

    def _split_cluster(self, cluster: Cluster, time_matrix: Dict) -> List[Cluster]:
        if len(cluster.points) <= 1:
            return [cluster]
        return k_medoids_clustering_core(cluster.points, 2, time_matrix)
