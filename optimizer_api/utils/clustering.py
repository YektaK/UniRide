"""
Clustering Module
K-Means clustering and vehicle assignment utilities
"""

import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from utils.data_loader import haversine_distance


@dataclass
class Point:
    """Geographic point with student info"""
    id: str
    lat: float
    lng: float
    disability_type: str  # 'Sw' or 'So'
    location_code: str = ""


@dataclass
class Cluster:
    """Cluster of points"""
    centroid: Tuple[float, float]
    points: List[Point]
    sw_count: int
    so_count: int





def calculate_centroid(points: List[Point]) -> Tuple[float, float]:
    """Calculate the geographic centroid of points"""
    if not points:
        return (0.0, 0.0)

    sum_lat = sum(p.lat for p in points)
    sum_lng = sum(p.lng for p in points)

    return (sum_lat / len(points), sum_lng / len(points))


def initialize_centroids_kmeans_plus_plus(points: List[Point], k: int) -> List[Tuple[float, float]]:
    """
    Initialize centroids using K-means++ algorithm.
    Provides better initial placement than random selection.
    """
    if k <= 0 or not points:
        return []

    centroids = []

    # Pick first centroid randomly
    first_idx = random.randint(0, len(points) - 1)
    centroids.append((points[first_idx].lat, points[first_idx].lng))

    # Pick remaining centroids
    while len(centroids) < k:
        # Calculate squared distances to nearest centroid
        distances = []
        for point in points:
            min_dist = min(
                haversine_distance(point.lat, point.lng, c[0], c[1]) ** 2
                for c in centroids
            )
            distances.append(min_dist)

        # Select with probability proportional to distance squared
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


def kmeans_clustering(
    points: List[Point],
    k: int,
    max_iterations: int = 100
) -> List[Cluster]:
    """
    K-Means clustering algorithm for geographic points.

    Args:
        points: List of Point objects
        k: Number of clusters
        max_iterations: Maximum iterations

    Returns:
        List of Cluster objects
    """
    if not points:
        return []

    if k <= 0:
        return []

    if k >= len(points):
        # Each point is its own cluster
        return [
            Cluster(
                centroid=(p.lat, p.lng),
                points=[p],
                sw_count=1 if p.disability_type == "Sw" else 0,
                so_count=1 if p.disability_type == "So" else 0
            )
            for p in points
        ]

    # Initialize centroids using K-means++
    centroids = initialize_centroids_kmeans_plus_plus(points, k)

    prev_assignments = [-1] * len(points)

    for iteration in range(max_iterations):
        # Assign each point to nearest centroid
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

        # Check for convergence
        if assignments == prev_assignments:
            break
        prev_assignments = assignments

        # Update centroids
        for i in range(k):
            cluster_points = [points[j] for j in range(len(points)) if assignments[j] == i]
            if cluster_points:
                centroids[i] = calculate_centroid(cluster_points)

    # Build final clusters
    clusters = []
    for i in range(k):
        cluster_points = [points[j] for j in range(len(points)) if prev_assignments[j] == i]
        if cluster_points:
            sw_count = sum(1 for p in cluster_points if p.disability_type == "Sw")
            so_count = sum(1 for p in cluster_points if p.disability_type == "So")
            clusters.append(Cluster(
                centroid=centroids[i],
                points=cluster_points,
                sw_count=sw_count,
                so_count=so_count
            ))

    return clusters


def validate_cluster_capacity(
    cluster: Cluster,
    sw_capacity: int,
    so_capacity: int
) -> bool:
    """Check if cluster respects capacity constraints"""
    return cluster.sw_count <= sw_capacity and cluster.so_count <= so_capacity


def split_cluster(cluster: Cluster) -> List[Cluster]:
    """Split an over-capacity cluster into two"""
    if len(cluster.points) <= 1:
        return [cluster]

    return kmeans_clustering(cluster.points, 2)


class VehicleCalculator:
    """
    Main class for calculating vehicle requirements and student assignments.
    Implements CVRP (Capacitated Vehicle Routing Problem) solving.
    """

    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_time: int = 120,
        clustering_algorithm: str = "sweep"
    ):
        self.sw_capacity = sw_capacity
        self.so_capacity = so_capacity
        self.max_tour_time = max_tour_time
        self.clustering_algorithm = clustering_algorithm

    def estimate_vehicle_count(self, students: List[Point]) -> int:
        """Estimate minimum number of vehicles needed"""
        sw_count = sum(1 for s in students if s.disability_type == "Sw")
        so_count = sum(1 for s in students if s.disability_type == "So")

        min_by_sw = math.ceil(sw_count / self.sw_capacity) if self.sw_capacity > 0 else 0
        min_by_so = math.ceil(so_count / self.so_capacity) if self.so_capacity > 0 else 0

        return max(min_by_sw, min_by_so, 1)

    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        """
        Cluster students into groups for vehicle assignment.
        Handles capacity constraints by delegating to the selected clustering strategy.
        """
        from utils.clustering_strategies import get_clustering_strategy
        from utils.data_loader import DataLoader
        
        # Build local time matrix dict for strategies that need true road distances (like K-Medoids or CW)
        # Assuming depot is D.Kampus unless specified otherwise in kwargs
        depot_id = kwargs.get("depot", {"id": "D.Kampus"})["id"]
        location_ids = [depot_id] + list(set(s.location_code for s in kwargs.get("raw_students", [])))
        
        # We need raw_students passed down to get location codes easily, or we can use Point ids
        # point id is student id, not location_code!
        # wait, Point model does NOT have location_code. So we can't get time matrix easily without the dicts.
        # But we can pass time_matrix from calculate()
        
        strategy = get_clustering_strategy(self.clustering_algorithm, self.sw_capacity, self.so_capacity)
        return strategy.cluster_students(students, num_vehicles, **kwargs)

    def calculate(
        self,
        students: List[Dict],
        route_optimizer=None
    ) -> Dict:
        """
        Main calculation method.

        Args:
            students: List of student dicts with id, location_code, coordinates, disability_type
            route_optimizer: Optional function to optimize route (takes location codes, returns route)

        Returns:
            Dict with assignments, total_duration, etc.
        """
        if not students:
            return {
                "success": True,
                "required_vehicles": 0,
                "assignments": [],
                "total_duration": 0,
                "unassigned_students": [],
                "message": "No students to assign"
            }

        # Convert to Point objects
        points = []
        student_map = {}
        for s in students:
            coords = s.get("coordinates") or {"lat": 0, "lng": 0}
            point = Point(
                id=s["id"],
                lat=coords.get("lat", 0),
                lng=coords.get("lng", 0),
                disability_type=s.get("disability_type", "So"),
                location_code=s.get("location_code", "")
            )
            points.append(point)
            student_map[s["id"]] = s

        # Estimate and iteratively find correct vehicle count
        num_vehicles = self.estimate_vehicle_count(points)
        max_attempts = min(len(students) - num_vehicles + 1, 15)  # Cap attempts to avoid long loops

        best_assignments = []
        min_violation = float('inf')
        best_vehicle_count = 0
        best_duration = 0

        for attempt in range(max_attempts):
            clusters = self.cluster_students(points, num_vehicles)

            # Build assignments
            assignments = []
            total_duration = 0
            valid = True
            violation_sum = 0

            for i, cluster in enumerate(clusters):
                cluster_students = [student_map[p.id] for p in cluster.points]

                # Get route (using optimizer if provided)
                route_duration = 0
                route_details = []

                if route_optimizer:
                    location_codes = [s["location_code"] for s in cluster_students]
                    route_result = route_optimizer(location_codes)
                    route_details = route_result.get("route_details", [])
                    route_duration = route_result.get("total_duration", 0)
                else:
                    # Simple estimate: 15 min per student + 20 min base
                    route_duration = len(cluster_students) * 15 + 20

                # Check tour time constraint
                if route_duration > self.max_tour_time:
                    valid = False
                    violation_sum += (route_duration - self.max_tour_time)

                assignments.append({
                    "vehicle_index": i + 1,
                    "students": cluster_students,
                    "route": route_details,
                    "total_duration": route_duration,
                    "sw_count": cluster.sw_count,
                    "so_count": cluster.so_count
                })
                total_duration += route_duration

            if valid:
                return {
                    "success": True,
                    "required_vehicles": len(clusters),
                    "assignments": assignments,
                    "total_duration": total_duration,
                    "unassigned_students": [],
                    "message": f"Optimal routes found with {len(clusters)} vehicles"
                }
                
            # Track best effort if strictly valid solution not found
            if violation_sum < min_violation:
                min_violation = violation_sum
                best_assignments = list(assignments)
                best_vehicle_count = len(clusters)
                best_duration = total_duration

            # Try with more vehicles
            num_vehicles += 1

        # Fallback: Instead of 1 student per vehicle, return the best effort clustering we found
        if best_assignments:
            return {
                "success": True,
                "required_vehicles": best_vehicle_count,
                "assignments": best_assignments,
                "total_duration": best_duration,
                "unassigned_students": [],
                "message": f"Kısıtlamalar aşıldığı için en iyi tahmini gruplama kullanıldı (Zaman aşımı: {min_violation:.1f} dk)"
            }

        # Ultimate Fallback: one student per vehicle (should rarely hit this now)
        assignments = []
        for i, student in enumerate(students):
            assignments.append({
                "vehicle_index": i + 1,
                "students": [student],
                "route": [],
                "total_duration": 0,
                "sw_count": 1 if student.get("disability_type") == "Sw" else 0,
                "so_count": 1 if student.get("disability_type") == "So" else 0
            })

        return {
            "success": True,
            "required_vehicles": len(students),
            "assignments": assignments,
            "total_duration": 0,
            "unassigned_students": [],
            "message": f"Fallback: Her öğrenci için ayrı araç atandı"
        }
