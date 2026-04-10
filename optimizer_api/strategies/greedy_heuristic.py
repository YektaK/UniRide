"""
Greedy (Nearest Neighbor) Heuristic Strategy
Constructs routes by always visiting the nearest valid student
"""

import time
from typing import List, Dict

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    VehicleRoute, RouteStep
)
from strategies.base_strategy import BaseRoutingStrategy
from utils.data_loader import DataLoader, haversine_distance, estimate_travel_time
from utils.constants import DEFAULT_TRAVEL_FALLBACK_MINUTES

logger = logging.getLogger(__name__)


class GreedyHeuristicStrategy(BaseRoutingStrategy):
    """
    Greedy Nearest Neighbor Heuristic.
    Fast but may not find optimal solution.
    """

    @property
    def name(self) -> str:
        return "greedy"

    @property
    def display_name(self) -> str:
        return "Greedy (En Yakın Komşu)"

    @property
    def description(self) -> str:
        return "Hızlı sezgisel algoritma. En yakın öğrenciyi her adımda seçer."

    def _get_duration(self, from_loc: str, to_loc: str, time_matrix: Dict, coordinates: Dict) -> float:
        """Get duration between locations"""
        if from_loc in time_matrix and to_loc in time_matrix[from_loc]:
            return time_matrix[from_loc][to_loc]

        if from_loc in coordinates and to_loc in coordinates:
            c1 = coordinates[from_loc]
            c2 = coordinates[to_loc]
            dist = haversine_distance(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            return estimate_travel_time(dist)

        logger.warning(f"Distance matrix miss for {from_loc} to {to_loc}. Using default fallback: {DEFAULT_TRAVEL_FALLBACK_MINUTES} mins")
        return DEFAULT_TRAVEL_FALLBACK_MINUTES

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Execute greedy optimization"""
        start_time = time.time()

        students = request.students
        depot = request.depot

        if not students:
            return OptimizationResponse(
                algorithm_used=self.name,
                success=True,
                routes=[],
                total_vehicles=0,
                execution_time_seconds=time.time() - start_time
            )

        # Build time matrix
        data_loader = DataLoader.get_instance()
        location_ids = [depot.id] + [s.location_code for s in students]
        raw_matrix = data_loader.get_submatrix(location_ids)
        time_matrix = {
            location_ids[i]: {
                location_ids[j]: raw_matrix[i][j]
                for j in range(len(location_ids))
            }
            for i in range(len(location_ids))
        }

        coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
        for s in students:
            coords = s.coordinates or {"lat": 0, "lng": 0}
            coordinates[s.location_code] = coords

        # Greedy assignment
        unassigned = list(students)
        routes = []
        vehicle_idx = 1

        while unassigned:
            current_loc = depot.id
            current_sw = 0
            current_so = 0
            current_time = 0.0
            route_details = []
            route_students = []
            sw_count = 0
            so_count = 0

            while unassigned:
                best_student = None
                best_time = float('inf')
                best_idx = -1

                for idx, student in enumerate(unassigned):
                    # Check capacity
                    sw_needed = 1 if student.disability_type == "Sw" else 0
                    so_needed = 1 if student.disability_type == "So" else 0

                    if current_sw + sw_needed > request.sw_capacity:
                        continue
                    if current_so + so_needed > request.so_capacity:
                        continue

                    # Check time constraint
                    travel_time = self._get_duration(
                        current_loc, student.location_code, time_matrix, coordinates
                    )
                    return_time = self._get_duration(
                        student.location_code, depot.id, time_matrix, coordinates
                    )

                    if current_time + travel_time + return_time > request.max_travel_time:
                        continue

                    if travel_time < best_time:
                        best_time = travel_time
                        best_student = student
                        best_idx = idx

                if best_student is None:
                    break

                # Add to route
                route_details.append(RouteStep(
                    location1=current_loc,
                    location2=best_student.location_code,
                    duration=round(best_time, 2),
                    distance=0.0
                ))

                current_time += best_time
                current_loc = best_student.location_code

                if best_student.disability_type == "Sw":
                    current_sw += 1
                    sw_count += 1
                else:
                    current_so += 1
                    so_count += 1

                route_students.append(best_student)
                unassigned.pop(best_idx)

            # Return to depot
            return_time = self._get_duration(current_loc, depot.id, time_matrix, coordinates)
            route_details.append(RouteStep(
                location1=current_loc,
                location2=depot.id,
                duration=round(return_time, 2),
                distance=0.0
            ))
            current_time += return_time

            routes.append(VehicleRoute(
                vehicle_id=f"Araç {vehicle_idx} (Greedy)",
                route_details=route_details,
                total_duration_minutes=round(current_time, 2),
                total_distance_km=0.0,
                sw_count=sw_count,
                so_count=so_count,
                student_ids=[s.id for s in route_students]
            ))
            vehicle_idx += 1

        execution_time = time.time() - start_time

        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(r.total_duration_minutes for r in routes),
            execution_time_seconds=round(execution_time, 4)
        )
