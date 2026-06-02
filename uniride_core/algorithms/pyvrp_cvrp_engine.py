"""Core PyVRP adapter for string-compatible UniRide CVRP problems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping, Sequence

from uniride_core.algorithms.routing_demand_utils import load_for_route, normalize_demand_vectors


@dataclass
class PyVRPRoutePlan:
    vehicle_index: int
    customer_indices: List[int] = field(default_factory=list)
    sw_count: int = 0
    so_count: int = 0
    load: List[int] = field(default_factory=list)


@dataclass
class PyVRPCVRPSolution:
    success: bool
    routes: List[PyVRPRoutePlan] = field(default_factory=list)
    error_message: str | None = None


def solve_pyvrp_cvrp(
    *,
    duration_matrix: Sequence[Sequence[float]],
    coordinates: Sequence[Mapping[str, float]],
    disability_types: Sequence[str] | None = None,
    sw_capacity: int | None = None,
    so_capacity: int | None = None,
    num_vehicles: int | None = None,
    time_limit_seconds: int = 30,
    scale: int = 60,
    demand_vectors: Sequence[Sequence[int] | int] | None = None,
    capacities: Sequence[int] | None = None,
    time_windows: Sequence[Sequence[float]] | None = None,
    service_times: Sequence[float] | None = None,
    max_route_duration: float | None = None,
) -> PyVRPCVRPSolution:
    """Solve a depot-first CVRP with PyVRP's Model API."""
    try:
        from pyvrp import Model
        from pyvrp.stop import MaxRuntime
    except ImportError:
        return PyVRPCVRPSolution(success=False, error_message="PyVRP not installed. Run: pip install pyvrp")

    try:
        if not duration_matrix:
            return PyVRPCVRPSolution(success=True, routes=[])
        customer_count = max(0, len(duration_matrix) - 1)
        normalized_demands, normalized_capacities = normalize_demand_vectors(
            customer_count=customer_count,
            demand_vectors=demand_vectors,
            capacities=capacities,
            disability_types=disability_types,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
        )
        scaled_windows = None
        if time_windows is not None:
            scaled_windows = [
                (int(float(window[0]) * scale), int(float(window[1]) * scale))
                for window in time_windows
            ]
            if len(scaled_windows) != len(duration_matrix):
                return PyVRPCVRPSolution(
                    success=False,
                    error_message=(
                        "PyVRP CVRPTW requires one time-window row per location; "
                        f"got {len(scaled_windows)} for {len(duration_matrix)} locations"
                    ),
                )
        scaled_service_times = [int(float(value) * scale) for value in service_times or []]
        if len(scaled_service_times) < len(duration_matrix):
            scaled_service_times.extend([0] * (len(duration_matrix) - len(scaled_service_times)))

        model = Model()
        depot_coords = coordinates[0] if coordinates else {"lat": 0, "lng": 0}
        depot = model.add_depot(
            x=int(float(depot_coords.get("lng", 0)) * 1_000_000),
            y=int(float(depot_coords.get("lat", 0)) * 1_000_000),
        )

        clients = []
        for idx, demand in enumerate(normalized_demands, start=1):
            coords = coordinates[idx] if idx < len(coordinates) else {"lat": 0, "lng": 0}
            tw_early, tw_late = scaled_windows[idx] if scaled_windows is not None else (0, 9223372036854775807)
            clients.append(
                model.add_client(
                    x=int(float(coords.get("lng", 0)) * 1_000_000),
                    y=int(float(coords.get("lat", 0)) * 1_000_000),
                    delivery=list(demand),
                    service_duration=scaled_service_times[idx],
                    tw_early=tw_early,
                    tw_late=tw_late,
                )
            )

        vehicle_count = int(num_vehicles or min(len(normalized_demands), 15) or 1)
        depot_tw_early, depot_tw_late = scaled_windows[0] if scaled_windows is not None else (0, 9223372036854775807)
        shift_duration = (
            int(float(max_route_duration) * scale)
            if max_route_duration is not None
            else 9223372036854775807
        )
        model.add_vehicle_type(
            num_available=vehicle_count,
            capacity=list(normalized_capacities),
            start_depot=depot,
            end_depot=depot,
            tw_early=depot_tw_early,
            tw_late=depot_tw_late,
            shift_duration=shift_duration,
        )

        locations = [depot, *clients]
        for i, origin in enumerate(locations):
            for j, destination in enumerate(locations):
                if i == j:
                    continue
                value = int(max(1, float(duration_matrix[i][j]) * scale))
                model.add_edge(origin, destination, distance=value, duration=value)

        result = model.solve(stop=MaxRuntime(time_limit_seconds), display=False)
        if result.best is None:
            return PyVRPCVRPSolution(success=False, error_message="PyVRP could not find a feasible solution")

        routes: List[PyVRPRoutePlan] = []
        visited: List[int] = []
        for vehicle_idx, route in enumerate(result.best.routes(), start=1):
            customer_indices: List[int] = []
            sw_count = 0
            so_count = 0
            for client_node in route:
                customer_idx = int(client_node) - 1
                if not 0 <= customer_idx < len(normalized_demands):
                    continue
                customer_indices.append(customer_idx)
            if customer_indices:
                load = load_for_route(customer_indices, normalized_demands)
                if any(load[dim] > normalized_capacities[dim] for dim in range(len(load))):
                    return PyVRPCVRPSolution(
                        success=False,
                        error_message="PyVRP returned a route that violates capacity constraints",
                    )
                visited.extend(customer_indices)
                if time_windows is not None and _time_window_violations(
                    customer_indices,
                    duration_matrix,
                    time_windows,
                    service_times or [],
                ):
                    return PyVRPCVRPSolution(
                        success=False,
                        error_message="PyVRP returned a route that violates time-window constraints",
                    )
                routes.append(
                    PyVRPRoutePlan(
                        vehicle_index=vehicle_idx,
                        customer_indices=customer_indices,
                        sw_count=load[0] if load else 0,
                        so_count=load[1] if len(load) > 1 else 0,
                        load=load,
                    )
                )

        if sorted(visited) != list(range(len(normalized_demands))):
            return PyVRPCVRPSolution(
                success=False,
                error_message="PyVRP did not return a complete feasible customer assignment",
            )

        return PyVRPCVRPSolution(success=True, routes=routes)
    except Exception as exc:
        return PyVRPCVRPSolution(success=False, error_message=f"PyVRP optimization failed: {exc}")


def _time_window_violations(
    customer_indices: Sequence[int],
    duration_matrix: Sequence[Sequence[float]],
    time_windows: Sequence[Sequence[float]],
    service_times: Sequence[float],
) -> int:
    if not customer_indices:
        return 0
    services = list(service_times)
    if len(services) < len(time_windows):
        services.extend([0] * (len(time_windows) - len(services)))

    current_node = 0
    current_time = float(time_windows[0][0])
    violations = 0
    for customer_idx in customer_indices:
        node = customer_idx + 1
        current_time += float(duration_matrix[current_node][node])
        ready, due = time_windows[node]
        if current_time > float(due):
            violations += 1
        if current_time < float(ready):
            current_time = float(ready)
        current_time += float(services[node])
        current_node = node
    current_time += float(duration_matrix[current_node][0])
    if current_time > float(time_windows[0][1]):
        violations += 1
    return violations


__all__ = ["PyVRPCVRPSolution", "PyVRPRoutePlan", "solve_pyvrp_cvrp"]
