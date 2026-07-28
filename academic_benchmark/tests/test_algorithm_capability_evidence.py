"""Executable evidence for granular academic TSP/ATSP capability claims."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest
from uniride_core.algorithms.capabilities import (
    BackendKind,
    CompositionKind,
    ExecutionBackendProfile,
    ExecutionProtocol,
    LifecycleStatus,
    ProblemContract,
    get_algorithm_capability,
)


@dataclass
class _Problem:
    name: str
    problem_type: str
    dist_matrix: list[list[float]]
    optimal: float | None = None
    coordinates: tuple[()] = ()
    edge_weight_type: str = "EXPLICIT"
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)

    def prepare_matrices(self) -> None:
        return None


SYMMETRIC_TSP = _Problem(
    name="capability-evidence-symmetric-tsp-6",
    problem_type="tsp",
    dist_matrix=[
        [0.0, 3.0, 8.0, 7.0, 6.0, 4.0],
        [3.0, 0.0, 5.0, 9.0, 3.0, 7.0],
        [8.0, 5.0, 0.0, 4.0, 8.0, 6.0],
        [7.0, 9.0, 4.0, 0.0, 2.0, 5.0],
        [6.0, 3.0, 8.0, 2.0, 0.0, 4.0],
        [4.0, 7.0, 6.0, 5.0, 4.0, 0.0],
    ],
)

DIRECTED_ATSP = _Problem(
    name="capability-evidence-directed-atsp-6",
    problem_type="atsp",
    dist_matrix=[
        [0.0, 2.0, 9.0, 7.0, 6.0, 4.0],
        [8.0, 0.0, 3.0, 9.0, 2.0, 7.0],
        [5.0, 6.0, 0.0, 2.0, 8.0, 3.0],
        [4.0, 7.0, 6.0, 0.0, 2.0, 5.0],
        [9.0, 3.0, 7.0, 8.0, 0.0, 2.0],
        [3.0, 8.0, 4.0, 6.0, 9.0, 0.0],
    ],
)

PROBLEMS = (SYMMETRIC_TSP, DIRECTED_ATSP)
BASE_SEED = 239


def _independent_closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    route = [node - 1 for node in tour]
    return sum(
        float(matrix[node][route[(index + 1) % len(route)]])
        for index, node in enumerate(route)
    )


def _assert_common_evidence(
    first: Any,
    replay: Any,
    *,
    problem: _Problem,
    algorithm_id: str,
    expected_seed: int,
    expected_evaluations: int,
    expected_backend: str,
    expected_termination: str,
) -> None:
    expected_nodes = list(range(1, problem.dimension + 1))
    assert sorted(first.tour) == expected_nodes
    assert len(first.tour) == problem.dimension
    independent_cost = _independent_closed_cost(first.tour, problem.dist_matrix)
    assert first.objective_cost == pytest.approx(independent_cost)
    assert first.tour_cost == pytest.approx(independent_cost)
    assert first.algorithm == first.algorithm_id == algorithm_id
    assert first.seed == expected_seed
    assert first.objective_evaluations == first.evaluations == expected_evaluations
    assert first.execution_backend == expected_backend
    assert first.termination_reason == expected_termination

    assert replay.tour == first.tour
    assert replay.objective_cost == first.objective_cost
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.execution_backend == first.execution_backend
    assert replay.termination_reason == first.termination_reason
    assert replay.seed == first.seed


def _fixed_params(algorithm_id: str) -> tuple[dict[str, Any], int, int]:
    if "GWO" in algorithm_id:
        budget = 5
        params: dict[str, Any] = {
            "pack_size": 4,
            "max_iterations": 2,
            "max_no_improvement": 99,
        }
        expected_evaluations = 5
    elif "HHO" in algorithm_id:
        budget = 12
        params = {
            "hawks": 4,
            "dive_count": 0,
            "jump_probability": 0.0,
            "max_iterations": 2,
            "max_no_improvement": 99,
        }
        expected_evaluations = 8
    else:
        budget = 2 if algorithm_id == "Core-ThreeOpt-TSP" else 5
        params = {
            "max_iterations": 3,
            "first_improvement": False,
        }
        if algorithm_id == "Core-ThreeOpt-TSP":
            params["window"] = 4
        expected_evaluations = budget
    params["fair_comparison"] = {
        "evaluation_budget": budget,
        "base_seed": BASE_SEED,
        "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget",
    }
    return params, budget, expected_evaluations


def _prove_fixed(
    algorithm_id: str,
    *,
    expected_backend: str,
    expected_variant: str,
    polish_enabled: bool,
) -> None:
    executor = AlgorithmRegistry.get_executor(algorithm_id)
    for problem in PROBLEMS:
        params, budget, expected_evaluations = _fixed_params(algorithm_id)
        if polish_enabled:
            params.update(polish_iters=0, final_polish_iters=0)
        manifest = FairComparisonManifest.from_value(params["fair_comparison"])
        first = executor(problem, params, seed=987_654, run_idx=0)
        replay = executor(problem, params, seed=123_456, run_idx=0)
        _assert_common_evidence(
            first,
            replay,
            problem=problem,
            algorithm_id=algorithm_id,
            expected_seed=manifest.paired_seed(problem.name, 0),
            expected_evaluations=expected_evaluations,
            expected_backend=expected_backend,
            expected_termination="evaluation_budget_exhausted",
        )
        assert first.evaluation_budget == budget
        assert 0 < first.objective_evaluations <= first.evaluation_budget
        assert first.budget_terminated is True
        assert first.variant == expected_variant
        assert first.polish_policy["enabled"] is polish_enabled
        assert first.polish_policy["operator"] == ("2-opt" if polish_enabled else None)


def _native_params(algorithm_id: str) -> dict[str, Any]:
    if "GWO" in algorithm_id:
        params: dict[str, Any] = {
            "pack_size": 4,
            "max_iterations": 1,
            "max_no_improvement": 99,
        }
    else:
        params = {
            "hawks": 4,
            "dive_count": 0,
            "jump_probability": 0.0,
            "max_iterations": 1,
            "max_no_improvement": 99,
        }
    params["native_comparison"] = {
        "base_seed": BASE_SEED,
        "protocol_version": "uniride-native-tsp-v1",
        "comparison_regime": "algorithm_native_termination",
    }
    return params


def _prove_native_metaheuristic(algorithm_id: str, expected_evaluations: int) -> None:
    executor = AlgorithmRegistry.get_executor(algorithm_id)
    for problem in PROBLEMS:
        params = _native_params(algorithm_id)
        manifest = NativeComparisonManifest.from_value(params["native_comparison"])
        first = executor(problem, params, seed=987_654, run_idx=0)
        replay = executor(problem, params, seed=123_456, run_idx=0)
        _assert_common_evidence(
            first,
            replay,
            problem=problem,
            algorithm_id=algorithm_id,
            expected_seed=manifest.paired_seed(problem.name, 0),
            expected_evaluations=expected_evaluations,
            expected_backend="objective=numba;polish=none",
            expected_termination="max_iterations",
        )
        assert first.evaluation_budget is None
        assert first.budget_terminated is False
        assert first.variant == "pure"
        assert first.polish_policy == {
            "enabled": False,
            "initial": False,
            "periodic": False,
            "final": False,
            "operator": None,
        }


def _assert_fixed_local_claims_published(
    algorithm_id: str, evidence_function: str
) -> None:
    capability = get_algorithm_capability(algorithm_id)
    assert capability is not None
    assert capability.lifecycle is LifecycleStatus.VERIFIED
    assert len(capability.claims) == 2
    assert {claim.problem for claim in capability.claims} == {
        ProblemContract.TSP,
        ProblemContract.ATSP,
    }
    for claim in capability.claims:
        assert claim.protocol is ExecutionProtocol.FIXED_BUDGET
        assert claim.backend_profile == ExecutionBackendProfile(
            objective=BackendKind.PYTHON,
            polish=BackendKind.NONE,
        )
        assert claim.composition is CompositionKind.LOCAL_SEARCH
        assert claim.directed_cost_preserved is (
            claim.problem is ProblemContract.ATSP
        )
        assert claim.exact_objective_accounting is True
        assert claim.fixed_seed_deterministic is True
        assert claim.truthful_result_reporting is True
        assert claim.evidence_ids == (
            "academic_benchmark/tests/test_algorithm_capability_evidence.py::"
            + evidence_function,
        )


def test_core_two_opt_fixed_tsp_and_atsp_evidence() -> None:
    _prove_fixed(
        "Core-TwoOpt-TSP",
        expected_backend="objective=python;polish=none",
        expected_variant="pure",
        polish_enabled=False,
    )
    _assert_fixed_local_claims_published(
        "Core-TwoOpt-TSP", "test_core_two_opt_fixed_tsp_and_atsp_evidence"
    )


def test_core_three_opt_fixed_tsp_and_atsp_evidence() -> None:
    _prove_fixed(
        "Core-ThreeOpt-TSP",
        expected_backend="objective=python;polish=none",
        expected_variant="pure",
        polish_enabled=False,
    )
    _assert_fixed_local_claims_published(
        "Core-ThreeOpt-TSP", "test_core_three_opt_fixed_tsp_and_atsp_evidence"
    )
