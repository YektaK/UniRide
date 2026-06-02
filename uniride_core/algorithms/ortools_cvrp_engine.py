"""Core OR-Tools adapter for string-keyed UniRide CVRP problems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from uniride_core.algorithms.routing_demand_utils import load_for_route, normalize_demand_vectors


@dataclass
class ORToolsRouteStep:
    from_index: int
    to_index: int
    duration: float


@dataclass
class ORToolsRoutePlan:
    vehicle_index: int
    steps: List[ORToolsRouteStep] = field(default_factory=list)
    customer_indices: List[int] = field(default_factory=list)
    total_duration: float = 0.0
    sw_count: int = 0
    so_count: int = 0
    load: List[int] = field(default_factory=list)


@dataclass
class ORToolsCVRPSolution:
    success: bool
    routes: List[ORToolsRoutePlan] = field(default_factory=list)
    error_message: str | None = None


def solve_ortools_cvrp(
    *,
    time_matrix: Sequence[Sequence[float]],
    disability_types: Sequence[str] | None = None,
    sw_capacity: int | None = None,
    so_capacity: int | None = None,
    max_route_duration: float = 1_000_000,
    num_vehicles: int | None = None,
    time_limit_seconds: int = 30,
    scale: int = 10,
    demand_vectors: Sequence[Sequence[int] | int] | None = None,
    capacities: Sequence[int] | None = None,
    time_windows: Sequence[Sequence[float]] | None = None,
    service_times: Sequence[float] | None = None,
) -> ORToolsCVRPSolution:
    """Solve a depot-first string-compatible CVRP using OR-Tools."""
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return ORToolsCVRPSolution(
            success=False,
            error_message="OR-Tools not installed. Run: pip install ortools",
        )

    if not time_matrix:
        return ORToolsCVRPSolution(success=True, routes=[])

    matrix = [[int(float(value) * scale) for value in row] for row in time_matrix]
    num_locations = len(matrix)
    customer_count = max(0, num_locations - 1)
    normalized_demands, normalized_capacities = normalize_demand_vectors(
        customer_count=customer_count,
        demand_vectors=demand_vectors,
        capacities=capacities,
        disability_types=disability_types,
        sw_capacity=sw_capacity,
        so_capacity=so_capacity,
    )
    vehicle_count = int(num_vehicles or min(customer_count, 10) or 1)
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(num_locations, vehicle_count, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    scaled_service_times = [int(float(value) * scale) for value in service_times or []]
    if len(scaled_service_times) < num_locations:
        scaled_service_times.extend([0] * (num_locations - len(scaled_service_times)))

    def transit_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        return matrix[from_node][manager.IndexToNode(to_index)] + scaled_service_times[from_node]

    transit_callback_index = routing.RegisterTransitCallback(transit_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def add_capacity_dimension(name: str, demands: List[int], capacity: int) -> None:
        def demand_callback(from_index):
            return demands[manager.IndexToNode(from_index)]

        callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            callback_index,
            0,
            [int(capacity * scale)] * vehicle_count,
            False,
            name,
        )

    for dim, capacity in enumerate(normalized_capacities):
        dimension_demands = [0] + [row[dim] * scale for row in normalized_demands]
        add_capacity_dimension(f"Capacity{dim}", dimension_demands, capacity)
    slack_max = int(max_route_duration * scale) if time_windows else 0
    routing.AddDimension(
        transit_callback_index,
        slack_max,
        int(max_route_duration * scale),
        False,
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")
    if time_windows:
        scaled_windows = [
            (int(float(window[0]) * scale), int(float(window[1]) * scale))
            for window in time_windows
        ]
        if len(scaled_windows) != num_locations:
            return ORToolsCVRPSolution(
                success=False,
                error_message=(
                    "OR-Tools CVRPTW requires one time-window row per location; "
                    f"got {len(scaled_windows)} for {num_locations} locations"
                ),
            )

        for node in range(1, num_locations):
            index = manager.NodeToIndex(node)
            time_dimension.CumulVar(index).SetRange(*scaled_windows[node])

        depot_window = scaled_windows[depot_index]
        for vehicle_index in range(vehicle_count):
            time_dimension.CumulVar(routing.Start(vehicle_index)).SetRange(*depot_window)
            time_dimension.CumulVar(routing.End(vehicle_index)).SetRange(*depot_window)
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.Start(vehicle_index)))
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(vehicle_index)))

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = int(time_limit_seconds)

    solution = routing.SolveWithParameters(search_parameters)
    if not solution:
        return ORToolsCVRPSolution(success=False, error_message="OR-Tools could not find a solution")

    routes: List[ORToolsRoutePlan] = []
    for vehicle_index in range(vehicle_count):
        index = routing.Start(vehicle_index)
        route = ORToolsRoutePlan(vehicle_index=vehicle_index + 1)

        while not routing.IsEnd(index):
            from_index = index
            to_index = solution.Value(routing.NextVar(index))
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            duration = matrix[from_node][to_node] / float(scale)
            route.steps.append(ORToolsRouteStep(from_index=from_node, to_index=to_node, duration=round(duration, 2)))
            route.total_duration += duration

            if to_node > 0:
                customer_idx = to_node - 1
                route.customer_indices.append(customer_idx)

            index = to_index

        if route.customer_indices:
            route.load = load_for_route(route.customer_indices, normalized_demands)
            route.sw_count = route.load[0] if route.load else 0
            route.so_count = route.load[1] if len(route.load) > 1 else 0
            route.total_duration = round(route.total_duration, 2)
            routes.append(route)

    return ORToolsCVRPSolution(success=True, routes=routes)


__all__ = ["ORToolsCVRPSolution", "ORToolsRoutePlan", "ORToolsRouteStep", "solve_ortools_cvrp"]
