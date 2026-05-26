"""
Clustering Module
K-Means clustering and vehicle assignment utilities
"""

import math
from typing import Dict, List

from uniride_core.algorithms.clustering import (
    Cluster,
    Point,
    calculate_centroid,
    initialize_centroids_kmeans_plus_plus,
    kmeans_clustering,
    split_cluster,
    validate_cluster_capacity,
)
from uniride_core.algorithms.distance import haversine_distance


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
