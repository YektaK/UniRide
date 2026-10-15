"""M18 / ACAD-05: GWO/HHO must report the unrounded objective cost.

The execution gateway independently recomputes the directed closed-cycle cost
and accepts only |reported - recomputed| <= 1e-9 (relative and absolute).
Rounding the reported cost to 2 decimals made every fractional ATSP/travel
time matrix fail with "reported tour_cost does not equal the independently
recomputed directed closed-cycle cost".
"""
from __future__ import annotations

import math

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401 - registration
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.core.preflight import RuntimeBackendAvailability, probe_runtime_backends
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol
from uniride_core.models import ProblemInstance

# Fair-approved GWO/HHO identities (truthful names: 2-opt polish or pure).
# GWO-3opt / HHO-3opt are not implemented yet (catalog status PLANNED).
GATEWAY_ALGORITHMS = ("Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure")
EXECUTOR_ALGORITHMS = GATEWAY_ALGORITHMS + (
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Memetic-2opt",
)


def _fractional_atsp(n: int = 8) -> ProblemInstance:
    # Costs with 3+ decimals; asymmetric; sums are not representable at 2 dp.
    matrix = [
        [
            0.0 if i == j else ((i + 1) * 1.1237 + (j + 1) * 0.3141 + (i * j % 5) * 0.00713)
            for j in range(n)
        ]
        for i in range(n)
    ]
    return ProblemInstance(
        name="m18-fractional-atsp-8",
        dimension=n,
        coordinates=[],
        optimal=1.0,
        problem_type="atsp",
        dist_matrix=matrix,
    )


def _cycle_cost(tour: list[int], matrix: list[list[float]]) -> float:
    route = [node - 1 for node in tour]
    return sum(matrix[route[i]][route[(i + 1) % len(route)]] for i in range(len(route)))


def _params() -> dict:
    return {
        "fair_comparison": {"evaluation_budget": 5000, "base_seed": 77},
        "max_iterations": 3,
        "pack_size": 6,
        "hawks": 6,
    }


@pytest.mark.parametrize("algorithm", GATEWAY_ALGORITHMS)
def test_gateway_accepts_gwo_hho_on_fractional_directed_matrix(algorithm: str) -> None:
    problem = _fractional_atsp()
    runtime = probe_runtime_backends()
    policy = (
        BackendPolicy.REQUIRE_NUMBA_OBJECTIVE
        if runtime.numba_nopython
        else BackendPolicy.PYTHON_ONLY
    )
    result, _decision = execute_preflighted(
        requested_algorithm_id=algorithm,
        identifier_source=IdentifierSource.MANIFEST,
        problem=problem,
        params=_params(),
        seed=1,
        run_idx=0,
        protocol=ExecutionProtocol.FIXED_BUDGET,
        backend_policy=policy,
        evaluation_budget=5000,
        registered_algorithm_ids=frozenset(AlgorithmRegistry.list_algorithms()),
        runtime_backends=runtime,
        registry_getter=AlgorithmRegistry.get_executor,
    )
    independent = _cycle_cost(result.tour, problem.dist_matrix)
    assert math.isclose(result.tour_cost, independent, rel_tol=1e-9, abs_tol=1e-9)


@pytest.mark.parametrize("algorithm", EXECUTOR_ALGORITHMS)
def test_executor_reports_unrounded_cycle_cost(algorithm: str) -> None:
    problem = _fractional_atsp()
    result = AlgorithmRegistry.get_executor(algorithm)(
        problem, _params(), seed=1, run_idx=0
    )
    independent = _cycle_cost(result.tour, problem.dist_matrix)
    assert abs(result.tour_cost - independent) <= 1e-9
    assert abs(result.objective_cost - independent) <= 1e-9
    # Guard against the fixture degenerating into a 2-decimal-exact matrix.
    assert abs(independent - round(independent, 2)) > 1e-6
