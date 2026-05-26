"""Unified matrix-first engine interface for core algorithms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Sequence

import numpy as np

from uniride_core.algorithms.split_decoder import (
    optimal_split_result,
    split_with_time_windows_result,
)
from uniride_core.models import PermutationResult, RoutingProblem, RoutingResult, TSPResult


class UnifiedEngine(ABC):
    """Base class for algorithms that optimize node permutations.

    Engines implement `optimize_permutation` once. Problem-specific methods
    decode that permutation for TSP, ATSP, CVRP, and CVRPTW.
    """

    name: str = "UnifiedEngine"

    @abstractmethod
    def optimize_permutation(
        self,
        distance_matrix,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> PermutationResult:
        """Return the best customer permutation for an explicit matrix."""

    def solve_tsp(
        self,
        dm,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> TSPResult:
        result = self.optimize_permutation(dm, config=config, seed=seed)
        return TSPResult(
            algorithm=result.algorithm,
            tour=result.permutation,
            tour_length=float(result.cost),
            time_ms=result.time_ms,
            convergence_curve=result.convergence_curve,
            iterations=result.iterations,
            seed=result.seed,
            params=result.params,
        )

    def solve_atsp(
        self,
        dm,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> TSPResult:
        return self.solve_tsp(dm, config=config, seed=seed)

    def solve_problem(
        self,
        problem: RoutingProblem,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> TSPResult | RoutingResult:
        """Solve a unified core problem using the correct matrix-first path."""
        problem_type = problem.problem_type.lower()
        dm = problem.matrix.values
        constraints = problem.constraints
        run_config = {
            **dict(config or {}),
            "problem_type": problem_type,
            "depot_index": constraints.depot_index,
        }

        if problem_type == "tsp":
            return self.solve_tsp(dm, config=run_config, seed=seed)
        if problem_type == "atsp":
            return self.solve_atsp(dm, config=run_config, seed=seed)

        if problem_type in {"cvrp", "uniride_cvrp", "uniride"}:
            if constraints.demands is None:
                raise ValueError(f"{problem.problem_type} problem requires demands")
            if constraints.capacities is None:
                raise ValueError(f"{problem.problem_type} problem requires capacities")
            return self.solve_cvrp(
                dm,
                demands=constraints.demands,
                capacities=constraints.capacities,
                config=run_config,
                seed=seed,
                depot=constraints.depot_index,
                max_route_duration=constraints.max_route_duration,
            )

        if problem_type in {"cvrptw", "uniride_cvrptw"}:
            if constraints.demands is None:
                raise ValueError(f"{problem.problem_type} problem requires demands")
            if constraints.capacities is None:
                raise ValueError(f"{problem.problem_type} problem requires capacities")
            if constraints.time_windows is None:
                raise ValueError(f"{problem.problem_type} problem requires time windows")
            return self.solve_cvrptw(
                dm,
                demands=constraints.demands,
                capacities=constraints.capacities,
                time_windows=constraints.time_windows,
                service_times=constraints.service_times,
                config=run_config,
                seed=seed,
                depot=constraints.depot_index,
                max_route_duration=constraints.max_route_duration,
                direction=constraints.direction,
                target_time=constraints.target_time,
                offset_minutes=constraints.offset_minutes,
            )

        raise ValueError(f"Unsupported problem_type: {problem.problem_type}")

    def solve_cvrp(
        self,
        dm,
        demands: Sequence,
        capacities: int | Sequence[int],
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        depot: int = 0,
        max_route_duration: Optional[float] = None,
    ) -> RoutingResult:
        permutation_result = self.optimize_permutation(dm, config=config, seed=seed)
        split = optimal_split_result(
            permutation_result.permutation,
            dm,
            demands,
            capacities,
            depot=depot,
            max_route_duration=max_route_duration,
        )
        return RoutingResult(
            algorithm=permutation_result.algorithm,
            problem_type="CVRP",
            objective_cost=float(split.total_cost),
            routes=split.routes,
            tour=permutation_result.permutation,
            num_vehicles=len(split.routes),
            time_ms=permutation_result.time_ms,
            capacity_violations=split.capacity_violations,
            route_costs=split.route_costs,
            route_loads=split.route_loads,
            convergence_curve=permutation_result.convergence_curve,
            iterations=permutation_result.iterations,
            seed=permutation_result.seed,
            params=permutation_result.params,
        )

    def solve_cvrptw(
        self,
        dm,
        demands: Sequence,
        capacities: int | Sequence[int],
        time_windows: Sequence,
        service_times: Optional[Sequence[int]] = None,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        depot: int = 0,
        max_route_duration: Optional[float] = None,
        direction: str = "pickup",
        target_time: Optional[int] = None,
        offset_minutes: int = 10,
    ) -> RoutingResult:
        permutation_result = self.optimize_permutation(dm, config=config, seed=seed)
        split = split_with_time_windows_result(
            permutation_result.permutation,
            dm,
            demands,
            capacities,
            time_windows,
            service_times,
            depot=depot,
            max_route_duration=max_route_duration,
            direction=direction,
            target_time=target_time,
            offset_minutes=offset_minutes,
        )
        return RoutingResult(
            algorithm=permutation_result.algorithm,
            problem_type="CVRPTW",
            objective_cost=float(split.total_cost),
            routes=split.routes,
            tour=permutation_result.permutation,
            num_vehicles=len(split.routes),
            time_ms=permutation_result.time_ms,
            capacity_violations=split.capacity_violations,
            tw_violations=split.tw_violations,
            route_costs=split.route_costs,
            route_loads=split.route_loads,
            convergence_curve=permutation_result.convergence_curve,
            iterations=permutation_result.iterations,
            seed=permutation_result.seed,
            params=permutation_result.params,
        )


class StaticPermutationEngine(UnifiedEngine):
    """Small test/adapter engine that evaluates a provided permutation."""

    def __init__(self, permutation: Sequence[int], name: str = "StaticPermutation"):
        self._permutation = list(permutation)
        self.name = name

    def optimize_permutation(self, distance_matrix, config=None, seed=None) -> PermutationResult:
        dm = np.asarray(distance_matrix, dtype=np.float64)
        cost = 0.0
        if self._permutation:
            for i, node in enumerate(self._permutation):
                nxt = self._permutation[(i + 1) % len(self._permutation)]
                cost += float(dm[node, nxt])
        return PermutationResult(
            algorithm=self.name,
            permutation=list(self._permutation),
            cost=cost,
            seed=seed,
            params=dict(config or {}),
        )


__all__ = ["UnifiedEngine", "StaticPermutationEngine"]
