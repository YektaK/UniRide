"""Core OR-Tools adapter for string-keyed UniRide CVRP problems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence


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


@dataclass
class ORToolsCVRPSolution:
    success: bool
    routes: List[ORToolsRoutePlan] = field(default_factory=list)
    error_message: str | None = None


def solve_ortools_cvrp(
    *,
    time_matrix: Sequence[Sequence[float]],
    disability_types: Sequence[str],
    sw_capacity: int,
    so_capacity: int,
    max_route_duration: float,
    num_vehicles: int | None = None,
    time_limit_seconds: int = 30,
    scale: int = 10,
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
    vehicle_count = int(num_vehicles or min(customer_count, 10) or 1)
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(num_locations, vehicle_count, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def transit_callback(from_index, to_index):
        return matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(transit_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    sw_demands = [0] + [scale if disability_type == "Sw" else 0 for disability_type in disability_types]
    so_demands = [0] + [scale if disability_type == "So" else 0 for disability_type in disability_types]

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

    add_capacity_dimension("SwCapacity", sw_demands, sw_capacity)
    add_capacity_dimension("SoCapacity", so_demands, so_capacity)
    routing.AddDimension(
        transit_callback_index,
        0,
        int(max_route_duration * scale),
        False,
        "Time",
    )

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
                if disability_types[customer_idx] == "Sw":
                    route.sw_count += 1
                else:
                    route.so_count += 1

            index = to_index

        if route.customer_indices:
            route.total_duration = round(route.total_duration, 2)
            routes.append(route)

    return ORToolsCVRPSolution(success=True, routes=routes)


__all__ = ["ORToolsCVRPSolution", "ORToolsRoutePlan", "ORToolsRouteStep", "solve_ortools_cvrp"]
