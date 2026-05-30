"""Core vehicle assignment utilities for cluster-first routing."""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional

from uniride_core.algorithms.clustering import Cluster, Point
from uniride_core.algorithms.clustering_strategies import get_clustering_strategy

RouteOptimizer = Callable[[List[str]], Dict]


class VehicleCalculator:
    """Calculate vehicle requirements and cluster students into route assignments."""

    def __init__(
        self,
        sw_capacity: int = 4,
        so_capacity: int = 5,
        max_tour_time: int = 120,
        clustering_algorithm: str = "sweep",
    ):
        self.sw_capacity = sw_capacity
        self.so_capacity = so_capacity
        self.max_tour_time = max_tour_time
        self.clustering_algorithm = clustering_algorithm

    def estimate_vehicle_count(self, students: List[Point]) -> int:
        """Estimate the minimum number of vehicles required by vector capacity."""
        sw_count = sum(1 for student in students if student.disability_type == "Sw")
        so_count = sum(1 for student in students if student.disability_type == "So")

        min_by_sw = math.ceil(sw_count / self.sw_capacity) if self.sw_capacity > 0 else 0
        min_by_so = math.ceil(so_count / self.so_capacity) if self.so_capacity > 0 else 0

        return max(min_by_sw, min_by_so, 1)

    def cluster_students(self, students: List[Point], num_vehicles: int, **kwargs) -> List[Cluster]:
        """Cluster students using the selected core clustering strategy."""
        strategy = get_clustering_strategy(
            self.clustering_algorithm,
            self.sw_capacity,
            self.so_capacity,
        )
        return strategy.cluster_students(students, num_vehicles, **kwargs)

    def calculate(
        self,
        students: List[Dict],
        route_optimizer: Optional[RouteOptimizer] = None,
    ) -> Dict:
        """Create vehicle assignments and optionally optimize each cluster route."""
        if not students:
            return {
                "success": True,
                "required_vehicles": 0,
                "assignments": [],
                "total_duration": 0,
                "unassigned_students": [],
                "message": "No students to assign",
            }

        points = []
        student_map = {}
        for student in students:
            coords = student.get("coordinates") or {"lat": 0, "lng": 0}
            point = Point(
                id=student["id"],
                lat=coords.get("lat", 0),
                lng=coords.get("lng", 0),
                disability_type=student.get("disability_type", "So"),
                location_code=student.get("location_code", ""),
            )
            points.append(point)
            student_map[student["id"]] = student

        num_vehicles = self.estimate_vehicle_count(points)
        max_attempts = min(len(students) - num_vehicles + 1, 15)

        best_assignments = []
        min_violation = float("inf")
        best_vehicle_count = 0
        best_duration = 0

        for _ in range(max_attempts):
            clusters = self.cluster_students(points, num_vehicles)

            assignments = []
            total_duration = 0
            valid = True
            violation_sum = 0

            for idx, cluster in enumerate(clusters):
                cluster_students = [student_map[point.id] for point in cluster.points]
                route_duration = 0
                route_details = []

                if route_optimizer:
                    location_codes = [student["location_code"] for student in cluster_students]
                    route_result = route_optimizer(location_codes)
                    route_details = route_result.get("route_details", [])
                    route_duration = route_result.get("total_duration", 0)
                else:
                    route_duration = len(cluster_students) * 15 + 20

                if route_duration > self.max_tour_time:
                    valid = False
                    violation_sum += route_duration - self.max_tour_time

                assignments.append(
                    {
                        "vehicle_index": idx + 1,
                        "students": cluster_students,
                        "route": route_details,
                        "total_duration": route_duration,
                        "sw_count": cluster.sw_count,
                        "so_count": cluster.so_count,
                    }
                )
                total_duration += route_duration

            if valid:
                return {
                    "success": True,
                    "required_vehicles": len(clusters),
                    "assignments": assignments,
                    "total_duration": total_duration,
                    "unassigned_students": [],
                    "message": f"Optimal routes found with {len(clusters)} vehicles",
                }

            if violation_sum < min_violation:
                min_violation = violation_sum
                best_assignments = list(assignments)
                best_vehicle_count = len(clusters)
                best_duration = total_duration

            num_vehicles += 1

        if best_assignments:
            return {
                "success": True,
                "required_vehicles": best_vehicle_count,
                "assignments": best_assignments,
                "total_duration": best_duration,
                "unassigned_students": [],
                "message": (
                    "Best effort grouping used because constraints were exceeded "
                    f"(timeout: {min_violation:.1f} min)"
                ),
            }

        assignments = []
        for idx, student in enumerate(students):
            assignments.append(
                {
                    "vehicle_index": idx + 1,
                    "students": [student],
                    "route": [],
                    "total_duration": 0,
                    "sw_count": 1 if student.get("disability_type") == "Sw" else 0,
                    "so_count": 1 if student.get("disability_type") == "So" else 0,
                }
            )

        return {
            "success": True,
            "required_vehicles": len(students),
            "assignments": assignments,
            "total_duration": 0,
            "unassigned_students": [],
            "message": "Fallback: one vehicle assigned per student",
        }


__all__ = ["VehicleCalculator", "RouteOptimizer"]
