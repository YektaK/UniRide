import math
from typing import List
from utils.clustering import Point, Cluster, calculate_centroid, validate_cluster_capacity
from utils.clustering_strategies.base import BaseClusteringStrategy

def calculate_angle(depot_lat: float, depot_lng: float, point: Point) -> float:
    # returns angle in radians from -pi to pi
    y = point.lat - depot_lat
    x = point.lng - depot_lng
    return math.atan2(y, x)

class SweepClusteringStrategy(BaseClusteringStrategy):
    """
    Sweep algorithm heuristic for clustering.
    Sorts points radially around the depot and chunks them into `num_vehicles` clusters.
    Fast and highly effective for centralized depots.
    """
    
    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        if not students or num_vehicles <= 0: return []
        if num_vehicles >= len(students):
            return [Cluster(centroid=(p.lat, p.lng), points=[p], sw_count=1 if p.disability_type == "Sw" else 0, so_count=1 if p.disability_type == "So" else 0) for p in students]

        depot = kwargs.get("depot", {"lat": 41.001, "lng": 29.177}) # fallback to Doğuş Üniversitesi, Dudullu Kampüsü
        
        # Sort students by polar angle
        sorted_students = sorted(students, key=lambda p: calculate_angle(depot["lat"], depot["lng"], p))
        
        chunk_size = math.ceil(len(sorted_students) / num_vehicles)
        clusters = []
        
        for i in range(num_vehicles):
            chunk = sorted_students[i * chunk_size : (i + 1) * chunk_size]
            if not chunk: continue
            
            sw_count = sum(1 for p in chunk if p.disability_type == "Sw")
            so_count = sum(1 for p in chunk if p.disability_type == "So")
            clusters.append(Cluster(
                centroid=calculate_centroid(chunk),
                points=chunk,
                sw_count=sw_count,
                so_count=so_count
            ))

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
        # Recursively split in half preserving the sorted order
        mid = len(cluster.points) // 2
        p1=cluster.points[:mid]
        p2=cluster.points[mid:]
        return [
            Cluster(centroid=calculate_centroid(p), points=p, sw_count=sum(1 for point in p if point.disability_type == "Sw"), so_count=sum(1 for point in p if point.disability_type == "So"))
            for p in (p1, p2) if p
        ]
