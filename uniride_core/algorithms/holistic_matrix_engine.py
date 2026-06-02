"""UnifiedEngine adapters for holistic routing solvers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from uniride_core.algorithms.base_engine import UnifiedEngine
from uniride_core.models import PermutationResult, RoutingProblem, RoutingResult, TSPResult


class HolisticMatrixEngine(UnifiedEngine):
    """Expose holistic CVRP solvers through the core matrix-first interface."""

    def __init__(self, name: str):
        self.name = name

    def optimize_permutation(self, distance_matrix, config=None, seed=None) -> PermutationResult:
        raise NotImplementedError("HolisticMatrixEngine uses solve_problem() dispatch directly")

    def solve_problem(
        self,
        problem: RoutingProblem,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> TSPResult | RoutingResult:
        del seed
        problem_type = problem.problem_type.lower()
        cfg = dict(config or {})
        matrix = np.asarray(problem.matrix.values, dtype=float)

        if problem_type in {"tsp", "atsp"}:
            solution = self._solve_as_single_vehicle(matrix, problem, cfg)
            route = solution_to_node_routes(solution)
            if not route:
                raise RuntimeError(f"{self.name} did not return a route")
            tour = [0, *route[0]]
            return TSPResult(
                algorithm=self.name,
                tour=tour,
                tour_length=_cycle_cost(tour, matrix),
                params=cfg,
            )

        if problem_type not in {"cvrp", "cvrptw", "uniride", "uniride_cvrp", "uniride_cvrptw"}:
            raise ValueError(f"Unsupported problem_type for {self.name}: {problem.problem_type}")

        constraints = problem.constraints
        if constraints.demands is None or constraints.capacities is None:
            raise ValueError(f"{problem.problem_type} problem requires demands and capacities")

        solution = self._solve_cvrp(matrix, problem, cfg)
        routes = solution_to_node_routes(solution)
        route_costs = [_route_cost(route, matrix, constraints.depot_index) for route in routes]
        tw_violations = _time_window_violations(routes, matrix, problem)
        return RoutingResult(
            algorithm=self.name,
            problem_type=problem.problem_type.upper(),
            objective_cost=float(sum(route_costs)),
            routes=routes,
            tour=[node for route in routes for node in route],
            num_vehicles=len(routes),
            route_costs=route_costs,
            route_loads=[_route_load(route, constraints.demands) for route in routes],
            tw_violations=tw_violations,
            params=cfg,
        )

    def _solve_as_single_vehicle(self, matrix: np.ndarray, problem: RoutingProblem, config: Dict[str, Any]):
        n = int(matrix.shape[0])
        if n <= 1:
            return _AdHocSolution(True, [_AdHocRoute([0])])
        demands = [[0, 0], *([[0, 1]] * (n - 1))]
        capacities = [n, n]
        return self._call_solver(
            matrix,
            problem,
            config,
            demands=demands,
            capacities=capacities,
            num_vehicles=1,
        )

    def _solve_cvrp(self, matrix: np.ndarray, problem: RoutingProblem, config: Dict[str, Any]):
        constraints = problem.constraints
        return self._call_solver(
            matrix,
            problem,
            config,
            demands=constraints.demands or [],
            capacities=constraints.capacities or [],
            num_vehicles=int(config.get("num_vehicles") or problem.metadata.get("vehicles") or matrix.shape[0] - 1 or 1),
        )

    def _call_solver(
        self,
        matrix: np.ndarray,
        problem: RoutingProblem,
        config: Dict[str, Any],
        *,
        demands: Sequence,
        capacities: Sequence[int],
        num_vehicles: int,
    ):
        customer_count = max(0, int(matrix.shape[0]) - 1)
        max_route_duration = float(problem.constraints.max_route_duration or config.get("max_route_duration") or 1_000_000)
        time_limit_seconds = int(config.get("time_limit_seconds", 1))

        if self.name == "OR-Tools":
            from uniride_core.algorithms.ortools_cvrp_engine import solve_ortools_cvrp

            solution = solve_ortools_cvrp(
                time_matrix=matrix.tolist(),
                demand_vectors=demands,
                capacities=capacities,
                max_route_duration=max_route_duration,
                num_vehicles=num_vehicles,
                time_limit_seconds=time_limit_seconds,
                scale=int(config.get("scale", 10)),
                time_windows=problem.constraints.time_windows,
                service_times=problem.constraints.service_times,
                first_solution_strategy=config.get("first_solution_strategy"),
                local_search_metaheuristic=config.get("local_search_metaheuristic"),
            )
        elif self.name == "PyVRP":
            from uniride_core.algorithms.pyvrp_cvrp_engine import solve_pyvrp_cvrp

            solution = solve_pyvrp_cvrp(
                duration_matrix=matrix.tolist(),
                coordinates=_coordinates(problem),
                demand_vectors=demands,
                capacities=capacities,
                num_vehicles=num_vehicles,
                time_limit_seconds=time_limit_seconds,
                scale=int(config.get("scale", 60)),
                time_windows=problem.constraints.time_windows,
                service_times=problem.constraints.service_times,
                max_route_duration=max_route_duration,
            )
        elif self.name == "VROOM":
            from uniride_core.algorithms.vroom_cvrp_engine import solve_sweep_fallback_routes, solve_vroom_cvrp

            solution = solve_vroom_cvrp(
                duration_matrix=matrix.tolist(),
                demand_vectors=demands,
                capacities=capacities,
                max_route_duration=max_route_duration,
                num_vehicles=num_vehicles,
                time_windows=problem.constraints.time_windows,
                service_times=problem.constraints.service_times,
            )
            if not solution.success and not problem.constraints.time_windows:
                fallback_routes = solve_sweep_fallback_routes(
                    customer_indices=list(range(customer_count)),
                    coordinates=_coordinates(problem),
                    depot_index=0,
                    duration_lookup=lambda origin, destination: float(matrix[origin, destination]),
                    max_route_duration=max_route_duration,
                    demand_vectors=demands,
                    capacities=capacities,
                )
                solution = _AdHocSolution(
                    bool(fallback_routes),
                    [_AdHocRoute(route.customer_indices) for route in fallback_routes],
                )
        else:
            raise ValueError(f"Unsupported holistic solver: {self.name}")

        if not solution.success:
            raise RuntimeError(solution.error_message or f"{self.name} failed")
        return solution


class _AdHocRoute:
    def __init__(self, customer_indices: Sequence[int]):
        self.customer_indices = list(customer_indices)


class _AdHocSolution:
    def __init__(self, success: bool, routes: Sequence[_AdHocRoute]):
        self.success = success
        self.routes = list(routes)
        self.error_message = None


def solution_to_node_routes(solution) -> List[List[int]]:
    routes: List[List[int]] = []
    for route in solution.routes:
        nodes = [int(idx) + 1 for idx in route.customer_indices]
        if nodes:
            routes.append(nodes)
    return routes


def _disability_types(demands: Sequence) -> List[str]:
    types: List[str] = []
    for demand in list(demands)[1:]:
        if isinstance(demand, Sequence) and not isinstance(demand, (str, bytes)):
            sw = int(demand[0]) if len(demand) > 0 else 0
            so = int(demand[1]) if len(demand) > 1 else 0
            types.append("Sw" if sw > 0 and sw >= so else "So")
        else:
            types.append("So" if int(demand) > 0 else "So")
    return types


def _sw_so_capacity(capacities: Sequence[int], *, fallback: int) -> tuple[int, int]:
    values = list(capacities)
    if not values:
        return fallback, fallback
    if len(values) == 1:
        return fallback, int(values[0])
    return int(values[0]), int(values[1])


def _coordinates(problem: RoutingProblem) -> List[dict[str, float]]:
    coords = list(problem.coordinates or [])
    if not coords:
        coords = [(float(idx), 0.0) for idx in range(problem.dimension)]
    return [{"lat": float(y), "lng": float(x)} for x, y in coords]


def _cycle_cost(tour: Sequence[int], matrix: np.ndarray) -> float:
    if not tour:
        return 0.0
    return float(sum(matrix[tour[idx], tour[(idx + 1) % len(tour)]] for idx in range(len(tour))))


def _route_cost(route: Sequence[int], matrix: np.ndarray, depot: int) -> float:
    if not route:
        return 0.0
    total = float(matrix[depot, route[0]])
    total += sum(float(matrix[route[idx], route[idx + 1]]) for idx in range(len(route) - 1))
    total += float(matrix[route[-1], depot])
    return total


def _route_load(route: Sequence[int], demands: Sequence) -> List[int]:
    load = [0, 0]
    for node in route:
        demand = demands[node]
        if isinstance(demand, Sequence) and not isinstance(demand, (str, bytes)):
            if len(demand) == 1:
                load[0] += int(demand[0])
            elif len(demand) >= 2:
                load[0] += int(demand[0])
                load[1] += int(demand[1])
        else:
            load[0] += int(demand)
    return load


def _time_window_violations(
    routes: Sequence[Sequence[int]],
    matrix: np.ndarray,
    problem: RoutingProblem,
) -> int:
    constraints = problem.constraints
    if not constraints.time_windows:
        return 0
    depot = int(constraints.depot_index)
    windows = list(constraints.time_windows)
    service_times = list(constraints.service_times or [0] * len(windows))
    violations = 0

    for route in routes:
        current = depot
        current_time = float(windows[depot][0]) if depot < len(windows) else 0.0
        for node in route:
            current_time += float(matrix[current, node])
            if node < len(windows):
                ready, due = windows[node]
                if current_time > float(due):
                    violations += 1
                if current_time < float(ready):
                    current_time = float(ready)
            if node < len(service_times):
                current_time += float(service_times[node])
            current = node

        current_time += float(matrix[current, depot])
        if depot < len(windows) and current_time > float(windows[depot][1]):
            violations += 1

    return violations


__all__ = ["HolisticMatrixEngine", "solution_to_node_routes"]
