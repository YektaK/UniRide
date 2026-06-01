"""Core VROOM adapter and fallback sweep routing helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Mapping, Sequence

from uniride_core.algorithms.routing_demand_utils import load_for_route, normalize_demand_vectors


@dataclass
class VROOMRoutePlan:
    vehicle_index: int
    customer_indices: List[int] = field(default_factory=list)
    sw_count: int = 0
    so_count: int = 0
    load: List[int] = field(default_factory=list)


@dataclass
class VROOMCVRPSolution:
    success: bool
    routes: List[VROOMRoutePlan] = field(default_factory=list)
    error_message: str | None = None


def solve_vroom_cvrp(
    *,
    duration_matrix: Sequence[Sequence[float]],
    disability_types: Sequence[str] | None = None,
    sw_capacity: int | None = None,
    so_capacity: int | None = None,
    max_route_duration: float = 1_000_000,
    num_vehicles: int | None = None,
    demand_vectors: Sequence[Sequence[int] | int] | None = None,
    capacities: Sequence[int] | None = None,
) -> VROOMCVRPSolution:
    """Try solving a depot-first CVRP with pyvroom's `vroom` module."""
    try:
        import numpy as np
        import vroom
    except ImportError:
        return VROOMCVRPSolution(success=False, error_message="VROOM not installed. Run: pip install pyvroom")

    try:
        customer_count = max(0, len(duration_matrix) - 1)
        normalized_demands, normalized_capacities = normalize_demand_vectors(
            customer_count=customer_count,
            demand_vectors=demand_vectors,
            capacities=capacities,
            disability_types=disability_types,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
        )
        problem = vroom.Input()
        vehicle_count = int(num_vehicles or min(len(normalized_demands), 15) or 1)
        for vehicle_id in range(vehicle_count):
            problem.add_vehicle(
                vroom.Vehicle(
                    id=vehicle_id,
                    start=0,
                    end=0,
                    capacity=list(normalized_capacities),
                    time_window=vroom.TimeWindow(0, int(max_route_duration * 60)),
                )
            )

        for idx, demand in enumerate(normalized_demands):
            problem.add_job(
                vroom.Job(
                    id=idx + 1,
                    location=idx + 1,
                    delivery=list(demand),
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
                if not 0 <= customer_idx < len(normalized_demands):
                    continue
                customer_indices.append(customer_idx)
            if customer_indices:
                load = load_for_route(customer_indices, normalized_demands)
                routes.append(
                    VROOMRoutePlan(
                        route_idx,
                        customer_indices,
                        load[0] if load else 0,
                        load[1] if len(load) > 1 else 0,
                        load,
                    )
                )

        if sorted(idx for route in routes for idx in route.customer_indices) != list(range(len(normalized_demands))):
            return VROOMCVRPSolution(success=False, error_message="VROOM did not return a complete feasible assignment")
        return VROOMCVRPSolution(success=True, routes=routes)
    except Exception as exc:
        return VROOMCVRPSolution(success=False, error_message=f"VROOM optimization failed: {exc}")


def solve_sweep_fallback_routes(
    *,
    customer_indices: Sequence[int],
    coordinates: Sequence[Mapping[str, float]],
    depot_index: int,
    duration_lookup: Callable[[int, int], float],
    max_route_duration: float,
    disability_types: Sequence[str] | None = None,
    sw_capacity: int | None = None,
    so_capacity: int | None = None,
    demand_vectors: Sequence[Sequence[int] | int] | None = None,
    capacities: Sequence[int] | None = None,
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
    normalized_demands, normalized_capacities = normalize_demand_vectors(
        customer_count=len(coordinates) - 1,
        demand_vectors=demand_vectors,
        capacities=capacities,
        disability_types=disability_types,
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
    )
    routes: List[VROOMRoutePlan] = []
    current: List[int] = []
    current_load = [0] * len(normalized_capacities)
    current_duration = 0.0
    previous_node = depot_index

    def flush() -> None:
        nonlocal current, current_load, current_duration, previous_node
        if not current:
            return
        load = list(current_load)
        routes.append(
            VROOMRoutePlan(
                len(routes) + 1,
                list(current),
                load[0] if load else 0,
                load[1] if len(load) > 1 else 0,
                load,
            )
        )
        current = []
        current_load = [0] * len(normalized_capacities)
        current_duration = 0.0
        previous_node = depot_index

    for customer_idx in sorted_customers:
        node_idx = customer_idx + 1
        demand = normalized_demands[customer_idx]
        travel = duration_lookup(previous_node, node_idx)
        back = duration_lookup(node_idx, depot_index)
        capacity_ok = all(
            current_load[dim] + demand[dim] <= normalized_capacities[dim]
            for dim in range(len(normalized_capacities))
        )
        time_ok = current_duration + travel + back <= max_route_duration

        if current and not (capacity_ok and time_ok):
            flush()
            travel = duration_lookup(depot_index, node_idx)

        current.append(customer_idx)
        for dim, value in enumerate(demand):
            current_load[dim] += int(value)
        current_duration += travel
        previous_node = node_idx

    flush()
    return routes


__all__ = ["VROOMCVRPSolution", "VROOMRoutePlan", "solve_sweep_fallback_routes", "solve_vroom_cvrp"]
