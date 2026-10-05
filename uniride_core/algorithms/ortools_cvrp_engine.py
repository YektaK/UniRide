"""Core OR-Tools adapter for string-keyed UniRide CVRP problems."""

from __future__ import annotations

import math
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
    first_solution_strategy: str | int | None = None,
    local_search_metaheuristic: str | int | None = None,
    arc_rounding: str = "nearest",
) -> ORToolsCVRPSolution:
    """Solve a depot-first string-compatible CVRP using OR-Tools.

    ``arc_rounding`` selects how minutes become OR-Tools integers:

    * ``"nearest"`` (default): the historical behaviour, unchanged, so academic
      callers keep identical scaled values and reported durations (the reported
      step duration is the scaled value divided by ``scale``).
    * ``"conservative"``: arcs and service times are rounded up, the route
      limit is rounded down, and the true unscaled arc durations are reported,
      so rounding can never let a route exceed ``max_route_duration`` in true
      minutes. The operational ``/optimize`` and ``/compare`` path uses this.
    """
    if arc_rounding not in _ARC_ROUNDING_MODES:
        return ORToolsCVRPSolution(
            success=False,
            error_message=f"Unsupported OR-Tools arc_rounding: {arc_rounding!r}",
        )
    conservative = arc_rounding == "conservative"
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return ORToolsCVRPSolution(
            success=False,
            error_message="OR-Tools not installed. Run: pip install ortools",
        )

    if not time_matrix:
        return ORToolsCVRPSolution(success=True, routes=[])

    # OR-Tools needs integer costs. Conservative mode rounds arcs (and service
    # times) UP so the scaled route duration is never below the true one: with
    # the route limit rounded DOWN below, a route that satisfies the scaled limit
    # satisfies ``max_route_duration`` in true minutes. Nearest-integer rounding
    # could under-report a route by up to 0.5/scale per arc and hide a violation.
    def to_units(value: float) -> int:
        if conservative:
            return _scale_up(value, scale)
        return int(round(float(value) * scale))

    matrix = [[to_units(value) for value in row] for row in time_matrix]
    num_locations = len(matrix)
    customer_count = max(0, num_locations - 1)
    try:
        normalized_demands, normalized_capacities = normalize_demand_vectors(
            customer_count=customer_count,
            demand_vectors=demand_vectors,
            capacities=capacities,
            disability_types=disability_types,
            sw_capacity=sw_capacity,
            so_capacity=so_capacity,
        )
    except ValueError as exc:
        return ORToolsCVRPSolution(success=False, error_message=str(exc))
    vehicle_count = int(num_vehicles or min(customer_count, 10) or 1)
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(num_locations, vehicle_count, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    scaled_service_times = [to_units(value) for value in service_times or []]
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
    scaled_max_duration = (
        _scale_down(max_route_duration, scale)
        if conservative
        else int(max_route_duration * scale)
    )
    slack_max = scaled_max_duration if time_windows else 0
    routing.AddDimension(
        transit_callback_index,
        slack_max,
        scaled_max_duration,
        False,
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")
    if time_windows:
        scaled_windows = [
            (int(round(float(window[0]) * scale)), int(round(float(window[1]) * scale)))
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
    try:
        search_parameters.first_solution_strategy = _routing_enum_value(
            routing_enums_pb2.FirstSolutionStrategy,
            first_solution_strategy,
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            "first_solution_strategy",
        )
        search_parameters.local_search_metaheuristic = _routing_enum_value(
            routing_enums_pb2.LocalSearchMetaheuristic,
            local_search_metaheuristic,
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            "local_search_metaheuristic",
        )
    except ValueError as exc:
        return ORToolsCVRPSolution(success=False, error_message=str(exc))
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
            if conservative:
                # Report the true, unscaled arc: the caller's matrix is
                # authoritative; the scaled cost is only the solver's currency.
                duration = float(time_matrix[from_node][to_node])
            else:
                # Historical reporting, kept so academic outputs are unchanged.
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


_ARC_ROUNDING_MODES = ("nearest", "conservative")

# Absorbs binary float noise only (0.7 * 10 == 7.000000000000001 must stay 7).
_SCALE_EPSILON = 1e-9


def _scale_up(value: float, scale: int) -> int:
    """Scale minutes to solver units, rounding up (never under-estimates)."""
    return max(0, math.ceil(float(value) * scale - _SCALE_EPSILON))


def _scale_down(value: float, scale: int) -> int:
    """Scale a limit in minutes to solver units, rounding down (never over-allows)."""
    return int(math.floor(float(value) * scale + _SCALE_EPSILON))


def _routing_enum_value(enum_type, value: str | int | None, default: int, label: str) -> int:
    if value is None:
        return int(default)
    if isinstance(value, int):
        return value
    normalized = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    resolved = getattr(enum_type, normalized, None)
    if resolved is None:
        raise ValueError(f"Unsupported OR-Tools {label}: {value}")
    return int(resolved)


__all__ = ["ORToolsCVRPSolution", "ORToolsRoutePlan", "ORToolsRouteStep", "solve_ortools_cvrp"]
