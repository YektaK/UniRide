"""App-layer helpers shared by SOTA production strategy wrappers."""

from __future__ import annotations

from typing import Callable, Dict, List

from models.schemas import OptimizationResponse, RouteStep, VehicleRoute
from utils.data_loader import DataLoader, euclidean_distance
from uniride_core.adapters.demand_builder import student_occurrence_keys

DistanceLookup = Callable[[str, str], float]
DurationLookup = Callable[[str, str], float]


def build_sota_request_context(students, depot) -> Dict:
    """Build app-layer matrix context from an OptimizationRequest.

    Solver nodes use occurrence identities, so customers sharing a physical
    ``location_code`` remain distinct nodes. Single-customer locations keep
    their ``location_code`` as the key (backward compatible). The raw
    submatrix is fetched positionally by physical codes (duplicates allowed)
    and re-keyed to occurrence identities.
    """
    data_loader = DataLoader.get_instance()
    occurrence_keys = student_occurrence_keys(students)
    node_keys = [depot.id] + occurrence_keys
    physical_ids = [depot.id] + [student.location_code for student in students]

    physical_coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
    for student in students:
        physical_coordinates[student.location_code] = student.coordinates or {"lat": 0, "lng": 0}

    coordinates = {depot.id: {"lat": depot.lat, "lng": depot.lng}}
    for student, occurrence_key in zip(students, occurrence_keys):
        coordinates[occurrence_key] = student.coordinates or {"lat": 0, "lng": 0}

    raw_matrix = data_loader.get_submatrix(physical_ids, physical_coordinates)
    time_matrix = {
        node_keys[i]: {
            node_keys[j]: raw_matrix[i][j]
            for j in range(len(node_keys))
        }
        for i in range(len(node_keys))
    }

    def distance_lookup(origin: str, destination: str) -> float:
        origin_coords = coordinates.get(origin, {})
        destination_coords = coordinates.get(destination, {})
        return round(
            euclidean_distance(
                origin_coords.get("lat", 0),
                origin_coords.get("lng", 0),
                destination_coords.get("lat", 0),
                destination_coords.get("lng", 0),
            ),
            2,
        )

    return {
        "coordinates": coordinates,
        "time_matrix": time_matrix,
        "student_ids": occurrence_keys,
        "distance_lookup": distance_lookup,
    }


def build_single_route_response(
    *,
    algorithm_name: str,
    vehicle_label: str,
    students,
    depot_id: str,
    best_order: List[str],
    duration_lookup: DurationLookup,
    distance_lookup: DistanceLookup,
    execution_time_seconds: float,
) -> OptimizationResponse:
    """Convert a SOTA student order into the current UniRide API response."""
    route_details = []
    route_distance = 0.0

    current = depot_id
    for student_id in best_order:
        duration = duration_lookup(current, student_id)
        distance = distance_lookup(current, student_id)
        route_details.append(
            RouteStep(
                location1=current,
                location2=student_id,
                duration=round(duration, 2),
                distance=distance,
            )
        )
        route_distance += distance
        current = student_id

    return_duration = duration_lookup(current, depot_id)
    return_distance = distance_lookup(current, depot_id)
    route_details.append(
        RouteStep(
            location1=current,
            location2=depot_id,
            duration=round(return_duration, 2),
            distance=return_distance,
        )
    )
    route_distance += return_distance

    total_duration = sum(step.duration for step in route_details)
    student_by_key = {
        key: student
        for student, key in zip(students, student_occurrence_keys(students))
    }
    route = VehicleRoute(
        vehicle_id=f"Araç 1 ({vehicle_label})",
        route_details=route_details,
        total_duration_minutes=round(total_duration, 2),
        total_distance_km=round(route_distance, 2),
        sw_count=sum(
            1
            for student_id in best_order
            if student_by_key.get(student_id) is not None
            and student_by_key[student_id].disability_type == "Sw"
        ),
        so_count=sum(
            1
            for student_id in best_order
            if student_by_key.get(student_id) is not None
            and student_by_key[student_id].disability_type == "So"
        ),
        student_ids=best_order,
    )

    return OptimizationResponse(
        algorithm_used=algorithm_name,
        success=True,
        routes=[route],
        total_vehicles=1,
        total_duration_minutes=round(total_duration, 2),
        execution_time_seconds=round(execution_time_seconds, 4),
    )


__all__ = ["build_single_route_response", "build_sota_request_context"]
