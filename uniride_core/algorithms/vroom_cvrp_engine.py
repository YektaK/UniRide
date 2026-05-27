"""Core VROOM adapter and fallback sweep routing helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Mapping, Sequence


@dataclass
class VROOMRoutePlan:
    vehicle_index: int
    customer_indices: List[int] = field(default_factory=list)
    sw_count: int = 0
    so_count: int = 0


@dataclass
class VROOMCVRPSolution:
    success: bool
    routes: List[VROOMRoutePlan] = field(default_factory=list)
    error_message: str | None = None


def solve_vroom_cvrp(
    *,
    duration_matrix: Sequence[Sequence[float]],
    disability_types: Sequence[str],
    sw_capacity: int,
    so_capacity: int,
    max_route_duration: float,
    num_vehicles: int | None = None,
) -> VROOMCVRPSolution:
    """Try solving a depot-first CVRP with pyvroom's `vroom` module."""
    try:
        import numpy as np
        import vroom
    except ImportError:
        return VROOMCVRPSolution(success=False, error_message="VROOM not installed. Run: pip install pyvroom")

    try:
        problem = vroom.Input()
        vehicle_count = int(num_vehicles or min(len(disability_types), 15) or 1)
        for vehicle_id in range(vehicle_count):
            problem.add_vehicle(
                vroom.Vehicle(
                    id=vehicle_id,
                    start=0,
                    end=0,
                    capacity=[sw_capacity, so_capacity],
                    time_window=vroom.TimeWindow(0, int(max_route_duration * 60)),
                )
            )

        for idx, disability_type in enumerate(disability_types):
            problem.add_job(
                vroom.Job(
                    id=idx + 1,
                    location=idx + 1,
                    delivery=[1 if disability_type == "Sw" else 0, 0 if disability_type == "Sw" else 1],
                )
            )

        matrix = np.asarray([[int(max(0, float(value) * 60)) for value in row] for row in duration_matrix], dtype=np.uint32)
        problem.set_durations_matrix("car", matrix)
        problem.set_distances_matrix("car", matrix)
        solution = problem.solve(exploration_level=5, nb_threads=4)

        routes: List[VROOMRoutePlan] = []
        for route_idx, route in enumerate(solution.routes, start=1):
            customer_indices: List[int] = []
            sw_count = 0
            so_count = 0
            for step in route.steps:
                if getattr(step, "type", None) != "job":
                    continue
                customer_idx = int(getattr(step, "job")) - 1
                if not 0 <= customer_idx < len(disability_types):
                    continue
                customer_indices.append(customer_idx)
                if disability_types[customer_idx] == "Sw":
                    sw_count += 1
                else:
                    so_count += 1
            if customer_indices:
                routes.append(VROOMRoutePlan(route_idx, customer_indices, sw_count, so_count))

        if sorted(idx for route in routes for idx in route.customer_indices) != list(range(len(disability_types))):
            return VROOMCVRPSolution(success=False, error_message="VROOM did not return a complete feasible assignment")
        return VROOMCVRPSolution(success=True, routes=routes)
    except Exception as exc:
        return VROOMCVRPSolution(success=False, error_message=f"VROOM optimization failed: {exc}")


def solve_sweep_fallback_routes(
    *,
    customer_indices: Sequence[int],
    coordinates: Sequence[Mapping[str, float]],
    disability_types: Sequence[str],
    depot_index: int,
    duration_lookup: Callable[[int, int], float],
    sw_capacity: int,
    so_capacity: int,
    max_route_duration: float,
) -> List[VROOMRoutePlan]:
    """Build deterministic sweep fallback routes over indexed customers."""
    depot_coords = coordinates[depot_index]

    def angle(customer_idx: int) -> float:
        coords = coordinates[customer_idx + 1]
        return math.atan2(
            float(coords.get("lat", 0)) - float(depot_coords.get("lat", 0)),
            float(coords.get("lng", 0)) - float(depot_coords.get("lng", 0)),
        )

    sorted_customers = sorted(customer_indices, key=angle)
    routes: List[VROOMRoutePlan] = []
    current: List[int] = []
    current_sw = 0
    current_so = 0
    current_duration = 0.0
    previous_node = depot_index

    def flush() -> None:
        nonlocal current, current_sw, current_so, current_duration, previous_node
        if not current:
            return
        routes.append(VROOMRoutePlan(len(routes) + 1, list(current), current_sw, current_so))
        current = []
        current_sw = 0
        current_so = 0
        current_duration = 0.0
        previous_node = depot_index

    for customer_idx in sorted_customers:
        node_idx = customer_idx + 1
        sw_needed = 1 if disability_types[customer_idx] == "Sw" else 0
        so_needed = 1 if disability_types[customer_idx] == "So" else 0
        travel = duration_lookup(previous_node, node_idx)
        back = duration_lookup(node_idx, depot_index)
        capacity_ok = current_sw + sw_needed <= sw_capacity and current_so + so_needed <= so_capacity
        time_ok = current_duration + travel + back <= max_route_duration

        if current and not (capacity_ok and time_ok):
            flush()
            travel = duration_lookup(depot_index, node_idx)

        current.append(customer_idx)
        current_sw += sw_needed
        current_so += so_needed
        current_duration += travel
        previous_node = node_idx

    flush()
    return routes


__all__ = ["VROOMCVRPSolution", "VROOMRoutePlan", "solve_sweep_fallback_routes", "solve_vroom_cvrp"]
