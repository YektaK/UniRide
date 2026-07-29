"""Pilot-level proof that governed TSP/ATSP runs cannot bypass preflight."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from academic_benchmark.core.algorithm_errors import (
    BackendUnavailableError,
    CandidateAlgorithmError,
    ExecutorUnavailableError,
    PlannedAlgorithmError,
    UnsupportedProblemContractError,
    UnsupportedProtocolError,
)
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.preflight import RuntimeBackendAvailability
from academic_benchmark.fair_pilot import _execute_preflighted_run
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol


@dataclass
class _Problem:
    name: str = "pilot-boundary-atsp"
    problem_type: str = "atsp"
    dimension: int = 3
    dist_matrix: list[list[float]] | None = None

    def __post_init__(self) -> None:
        if self.dist_matrix is None:
            self.dist_matrix = [
                [0.0, 2.0, 7.0],
                [5.0, 0.0, 3.0],
                [4.0, 9.0, 0.0],
            ]


class _ExplodingGetter:
    def __call__(self, algorithm_id: str) -> Any:
        raise AssertionError(f"registry getter bypassed preflight for {algorithm_id}")


_PYTHON = RuntimeBackendAvailability(
    python=True,
    numba_nopython=False,
    detail="deterministic Python-only pilot boundary",
)


@pytest.mark.parametrize(
    ("algorithm_id", "problem", "protocol", "budget", "registered", "runtime", "error"),
    [
        (
            "Core-OrOpt-TSP",
            _Problem(),
            ExecutionProtocol.FIXED_BUDGET,
             10,
            frozenset({"Core-OrOpt-TSP"}),
            _PYTHON,
            CandidateAlgorithmError,
        ),
        (
            "Core-GWO-TSP-Memetic-3opt",
            _Problem(),
            ExecutionProtocol.FIXED_BUDGET,
            10,
            frozenset({"Core-GWO-TSP-Memetic-3opt"}),
            _PYTHON,
            PlannedAlgorithmError,
        ),
        (
            "Core-TwoOpt-TSP",
            _Problem(problem_type="cvrp"),
            ExecutionProtocol.FIXED_BUDGET,
            10,
            frozenset({"Core-TwoOpt-TSP"}),
            _PYTHON,
            UnsupportedProblemContractError,
        ),
        (
            "Core-TwoOpt-TSP",
            _Problem(),
            ExecutionProtocol.FIXED_BUDGET,
            None,
            frozenset({"Core-TwoOpt-TSP"}),
            _PYTHON,
            UnsupportedProtocolError,
        ),
        (
            "Core-TwoOpt-TSP",
            _Problem(),
            ExecutionProtocol.NATIVE_TERMINATION,
            10,
            frozenset({"Core-TwoOpt-TSP"}),
            _PYTHON,
            UnsupportedProtocolError,
        ),
        (
            "Core-TwoOpt-TSP",
            _Problem(),
            ExecutionProtocol.FIXED_BUDGET,
            10,
            frozenset({"Core-TwoOpt-TSP"}),
            RuntimeBackendAvailability(
                python=False,
                numba_nopython=False,
                detail="no runtime backend is available",
            ),
            BackendUnavailableError,
        ),
        (
            "Core-TwoOpt-TSP",
            _Problem(),
            ExecutionProtocol.FIXED_BUDGET,
            10,
            frozenset(),
            _PYTHON,
            ExecutorUnavailableError,
        ),
    ],
    ids=(
        "candidate",
        "planned",
        "wrong-problem",
        "fixed-budget-missing",
        "native-budget-present",
        "unavailable-backend",
        "missing-executor",
    ),
)
def test_pilot_preflight_failures_happen_before_registry_getter(
    algorithm_id: str,
    problem: object,
    protocol: ExecutionProtocol,
    budget: int | None,
    registered: frozenset[str],
    runtime: RuntimeBackendAvailability,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        _execute_preflighted_run(
            requested_algorithm_id=algorithm_id,
            identifier_source=IdentifierSource.MANIFEST,
            problem=problem,
            params={},
            seed=17,
            run_idx=0,
            protocol=protocol,
            backend_policy=(
                BackendPolicy.REQUIRE_NUMBA_OBJECTIVE
                if algorithm_id in {"Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"}
                else BackendPolicy.PYTHON_ONLY
            ),
            evaluation_budget=budget,
            registered_algorithm_ids=registered,
            runtime_backends=runtime,
            registry_getter=_ExplodingGetter(),
        )
