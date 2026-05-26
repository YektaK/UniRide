"""Matrix-native benchmark runner for core RoutingProblem objects."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from uniride_core.algorithms.base_engine import UnifiedEngine
from uniride_core.models import RoutingProblem, RoutingResult, TSPResult


@dataclass
class MatrixAlgorithmConfig:
    name: str
    engine: UnifiedEngine
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatrixBenchmarkResult:
    algorithm: str
    problem: str
    run_number: int
    problem_type: str
    matrix_kind: str
    objective_cost: float
    tour_cost: Optional[float] = None
    tour: Optional[List[int]] = None
    routes: Optional[List[List[int]]] = None
    num_vehicles: Optional[int] = None
    route_loads: Optional[List[List[int]]] = None
    capacity_violations: int = 0
    tw_violations: int = 0
    gap_percent: Optional[float] = None
    elapsed_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MatrixBenchmarkRunner:
    """Run algorithms directly against core matrix-first problem objects."""

    def __init__(self, algorithms: Sequence[MatrixAlgorithmConfig] | Mapping[str, UnifiedEngine]):
        if isinstance(algorithms, Mapping):
            self.algorithms = [
                MatrixAlgorithmConfig(name=name, engine=engine)
                for name, engine in algorithms.items()
            ]
        else:
            self.algorithms = list(algorithms)

    def run(
        self,
        problems: Iterable[RoutingProblem],
        n_runs: int = 1,
        seed: int = 42,
    ) -> List[MatrixBenchmarkResult]:
        results: List[MatrixBenchmarkResult] = []
        for problem in problems:
            for algorithm in self.algorithms:
                for run_number in range(1, n_runs + 1):
                    results.append(
                        self.run_one(
                            problem,
                            algorithm,
                            run_number=run_number,
                            seed=seed + run_number - 1,
                        )
                    )
        return results

    def run_one(
        self,
        problem: RoutingProblem,
        algorithm: MatrixAlgorithmConfig,
        run_number: int = 1,
        seed: int = 42,
    ) -> MatrixBenchmarkResult:
        started = time.perf_counter()
        try:
            result = algorithm.engine.solve_problem(problem, config=algorithm.params, seed=seed)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return self._to_benchmark_result(
                problem,
                algorithm,
                result,
                run_number=run_number,
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return MatrixBenchmarkResult(
                algorithm=algorithm.name,
                problem=problem.name,
                run_number=run_number,
                problem_type=problem.problem_type,
                matrix_kind=problem.matrix.kind,
                objective_cost=float("nan"),
                elapsed_ms=elapsed_ms,
                error=str(exc),
                metadata={
                    "problem_dimension": problem.dimension,
                    "algorithm_params": algorithm.params,
                    "execution_failed": True,
                },
            )

    def _to_benchmark_result(
        self,
        problem: RoutingProblem,
        algorithm: MatrixAlgorithmConfig,
        result: TSPResult | RoutingResult,
        run_number: int,
        elapsed_ms: float,
    ) -> MatrixBenchmarkResult:
        if isinstance(result, TSPResult):
            objective = float(result.tour_length)
            gap = _gap(objective, problem.optimal)
            return MatrixBenchmarkResult(
                algorithm=algorithm.name,
                problem=problem.name,
                run_number=run_number,
                problem_type=problem.problem_type,
                matrix_kind=problem.matrix.kind,
                objective_cost=objective,
                tour_cost=objective,
                tour=result.tour,
                routes=[result.tour],
                num_vehicles=1,
                gap_percent=gap,
                elapsed_ms=elapsed_ms if elapsed_ms else result.time_ms,
                metadata={
                    "problem_dimension": problem.dimension,
                    "algorithm_params": algorithm.params,
                    "execution_failed": False,
                },
            )

        objective = float(result.objective_cost)
        gap = _gap(objective, problem.optimal)
        return MatrixBenchmarkResult(
            algorithm=algorithm.name,
            problem=problem.name,
            run_number=run_number,
            problem_type=problem.problem_type,
            matrix_kind=problem.matrix.kind,
            objective_cost=objective,
            tour_cost=objective,
            tour=result.tour,
            routes=result.routes,
            num_vehicles=result.num_vehicles,
            route_loads=result.route_loads,
            capacity_violations=result.capacity_violations,
            tw_violations=result.tw_violations,
            gap_percent=gap,
            elapsed_ms=elapsed_ms if elapsed_ms else result.time_ms,
            metadata={
                "problem_dimension": problem.dimension,
                "algorithm_params": algorithm.params,
                "execution_failed": False,
                "route_costs": result.route_costs,
            },
        )


def _gap(value: float, optimal: Optional[float]) -> Optional[float]:
    if optimal is None or optimal <= 0 or not math.isfinite(value):
        return None
    return ((value - optimal) / optimal) * 100.0


__all__ = ["MatrixAlgorithmConfig", "MatrixBenchmarkResult", "MatrixBenchmarkRunner"]
