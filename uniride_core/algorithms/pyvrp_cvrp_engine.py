"""Core PyVRP adapter for string-compatible UniRide CVRP problems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping, Sequence


@dataclass
class PyVRPRoutePlan:
    vehicle_index: int
    customer_indices: List[int] = field(default_factory=list)
    sw_count: int = 0
    so_count: int = 0


@dataclass
class PyVRPCVRPSolution:
    success: bool
    routes: List[PyVRPRoutePlan] = field(default_factory=list)
    error_message: str | None = None


def solve_pyvrp_cvrp(
    *,
    duration_matrix: Sequence[Sequence[float]],
    coordinates: Sequence[Mapping[str, float]],
    disability_types: Sequence[str],
    sw_capacity: int,
    so_capacity: int,
    num_vehicles: int | None = None,
    time_limit_seconds: int = 30,
    scale: int = 60,
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

        model = Model()
        depot_coords = coordinates[0] if coordinates else {"lat": 0, "lng": 0}
        depot = model.add_depot(
            x=int(float(depot_coords.get("lng", 0)) * 1_000_000),
            y=int(float(depot_coords.get("lat", 0)) * 1_000_000),
        )

        clients = []
        for idx, disability_type in enumerate(disability_types, start=1):
            coords = coordinates[idx] if idx < len(coordinates) else {"lat": 0, "lng": 0}
            clients.append(
                model.add_client(
                    x=int(float(coords.get("lng", 0)) * 1_000_000),
                    y=int(float(coords.get("lat", 0)) * 1_000_000),
                    delivery=[1 if disability_type == "Sw" else 0, 0 if disability_type == "Sw" else 1],
                )
            )

        vehicle_count = int(num_vehicles or min(len(disability_types), 15) or 1)
        model.add_vehicle_type(
            num_available=vehicle_count,
            capacity=[sw_capacity, so_capacity],
            start_depot=depot,
            end_depot=depot,
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
                if not 0 <= customer_idx < len(disability_types):
                    continue
                customer_indices.append(customer_idx)
                if disability_types[customer_idx] == "Sw":
                    sw_count += 1
                else:
                    so_count += 1
            if customer_indices:
                if sw_count > sw_capacity or so_count > so_capacity:
                    return PyVRPCVRPSolution(
                        success=False,
                        error_message="PyVRP returned a route that violates UniRide capacity constraints",
                    )
                visited.extend(customer_indices)
                routes.append(
                    PyVRPRoutePlan(
                        vehicle_index=vehicle_idx,
                        customer_indices=customer_indices,
                        sw_count=sw_count,
                        so_count=so_count,
                    )
                )

        if sorted(visited) != list(range(len(disability_types))):
            return PyVRPCVRPSolution(
                success=False,
                error_message="PyVRP did not return a complete feasible customer assignment",
            )

        return PyVRPCVRPSolution(success=True, routes=routes)
    except Exception as exc:
        return PyVRPCVRPSolution(success=False, error_message=f"PyVRP optimization failed: {exc}")


__all__ = ["PyVRPCVRPSolution", "PyVRPRoutePlan", "solve_pyvrp_cvrp"]
