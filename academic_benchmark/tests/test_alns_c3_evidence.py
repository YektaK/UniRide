from __future__ import annotations

from dataclasses import dataclass

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest
from uniride_core.algorithms.objective_budget import ObjectiveEvaluationBudget
from uniride_core.algorithms.sota_tsp.alns_tsp import ALNSConfig, ALNS_TSP
from uniride_core.algorithms.sota_tsp.repair_ops import (
    GreedyInsertion,
    Regret2Insertion,
    Regret3Insertion,
)


@dataclass
class _Problem:
    name: str
    problem_type: str
    dist_matrix: list[list[float]]
    optimal: float | None = None
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)


SYMMETRIC_TSP = _Problem(
    name="c3-alns-symmetric-tsp-6",
    problem_type="tsp",
    dist_matrix=[
        [0.0, 4.0, 8.0, 7.0, 3.0, 6.0],
        [4.0, 0.0, 5.0, 9.0, 6.0, 4.0],
        [8.0, 5.0, 0.0, 2.0, 7.0, 3.0],
        [7.0, 9.0, 2.0, 0.0, 4.0, 5.0],
        [3.0, 6.0, 7.0, 4.0, 0.0, 8.0],
        [6.0, 4.0, 3.0, 5.0, 8.0, 0.0],
    ],
)

DIRECTED_ATSP = _Problem(
    name="c3-alns-directed-atsp-6",
    problem_type="atsp",
    dist_matrix=[
        [0.0, 2.0, 9.0, 7.0, 6.0, 5.0],
        [8.0, 0.0, 3.0, 9.0, 2.0, 7.0],
        [5.0, 6.0, 0.0, 2.0, 8.0, 4.0],
        [4.0, 7.0, 6.0, 0.0, 2.0, 9.0],
        [9.0, 3.0, 7.0, 8.0, 0.0, 2.0],
        [3.0, 8.0, 5.0, 4.0, 6.0, 0.0],
    ],
)

ALNS_PARAMS = {
    "max_iterations": 8,
    "max_no_improvement": 3,
    "remove_ratio": 0.34,
    "min_remove": 2,
    "segment_length": 2,
    "weight_update_factor": 0.8,
    "use_sa": True,
    "sa_start_temp": 5.0,
    "sa_cooling_rate": 0.9,
}

BASE_SEED = 239
FIXED_REASONS = {
    "evaluation_budget_exhausted",
    "max_iterations",
    "stagnation_limit",
}
NATIVE_REASONS = {"max_iterations", "stagnation_limit"}
NO_POLISH = {
    "enabled": False,
    "initial": False,
    "periodic": False,
    "final": False,
    "operator": None,
}


def _closed_cost(one_indexed_tour: list[int], matrix: list[list[float]]) -> float:
    route = [node - 1 for node in one_indexed_tour]
    return sum(matrix[node][route[(index + 1) % len(route)]] for index, node in enumerate(route))


def _assert_complete_and_exact(result, matrix: list[list[float]]) -> None:
    assert result.tour is not None
    assert sorted(result.tour) == list(range(1, len(matrix) + 1))
    assert result.tour_cost == pytest.approx(_closed_cost(result.tour, matrix))
    assert result.objective_cost == pytest.approx(_closed_cost(result.tour, matrix))
    assert result.evaluations == result.objective_evaluations


def _zero_indexed_closed_cost(route: list[int], matrix: list[list[float]]) -> float:
    return sum(matrix[node][route[(index + 1) % len(route)]] for index, node in enumerate(route))


def _accounted_config(**overrides: object) -> ALNSConfig:
    values: dict[str, object] = {
        "iterations": 8,
        "max_no_improve": 3,
        "remove_ratio": 0.34,
        "min_remove": 2,
        "segment_length": 2,
        "weight_update_factor": 0.8,
        "use_sa": True,
        "sa_start_temp": 5.0,
        "sa_cooling_rate": 0.9,
        "seed": 41,
    }
    values.update(overrides)
    return ALNSConfig(**values)


def _assert_accounted_complete_and_exact(result, matrix: list[list[float]]) -> None:
    assert sorted(result.route) == list(range(len(matrix)))
    assert result.cost == pytest.approx(_zero_indexed_closed_cost(result.route, matrix))


REPAIR_MATRIX = [
    [0.0, 5.0, 90.0, 20.0],
    [90.0, 0.0, 5.0, 20.0],
    [100.0, 90.0, 0.0, 20.0],
    [20.0, 20.0, 20.0, 0.0],
]


@pytest.mark.parametrize(
    "operator",
    [GreedyInsertion(), Regret2Insertion(), Regret3Insertion()],
    ids=["greedy", "regret2", "regret3"],
)
def test_alns_repair_boundary_insertions_use_exact_directed_cycle_delta(operator) -> None:
    partial = [0, 1, 2]
    node = 3
    deltas = [
        REPAIR_MATRIX[partial[pos - 1] if pos else partial[-1]][node]
        + REPAIR_MATRIX[node][partial[pos] if pos < len(partial) else partial[0]]
        - REPAIR_MATRIX[
            partial[pos - 1] if pos else partial[-1]
        ][partial[pos] if pos < len(partial) else partial[0]]
        for pos in range(len(partial) + 1)
    ]

    assert deltas[0] == pytest.approx(deltas[-1])
    assert {index for index, delta in enumerate(deltas) if delta == min(deltas)} == {0, 3}
    assert operator.repair(partial, [node], REPAIR_MATRIX) == [node, *partial]


def test_alns_accounted_budget_one_stops_before_candidate_evaluation() -> None:
    budget = ObjectiveEvaluationBudget(1)
    result = ALNS_TSP(_accounted_config()).solve_accounted_with_matrix(
        DIRECTED_ATSP.dist_matrix, budget
    )

    _assert_accounted_complete_and_exact(result, DIRECTED_ATSP.dist_matrix)
    assert result.evaluations == budget.used == 1
    assert result.iterations == 0
    assert result.budget_exhausted is True
    assert result.termination_reason == "evaluation_budget_exhausted"


def test_alns_accounted_larger_fixed_budget_reports_exact_consumption() -> None:
    budget = ObjectiveEvaluationBudget(4)
    result = ALNS_TSP(
        _accounted_config(max_no_improve=8)
    ).solve_accounted_with_matrix(SYMMETRIC_TSP.dist_matrix, budget)

    _assert_accounted_complete_and_exact(result, SYMMETRIC_TSP.dist_matrix)
    assert result.evaluations == budget.used == 4
    assert result.iterations == 3
    assert result.budget_exhausted is True
    assert result.termination_reason == "evaluation_budget_exhausted"


def test_alns_accounted_native_counter_is_uncapped() -> None:
    budget = ObjectiveEvaluationBudget(None)
    result = ALNS_TSP(
        _accounted_config(iterations=3, max_no_improve=8)
    ).solve_accounted_with_matrix(DIRECTED_ATSP.dist_matrix, budget)

    _assert_accounted_complete_and_exact(result, DIRECTED_ATSP.dist_matrix)
    assert result.evaluations == budget.used == 4
    assert result.iterations == 3
    assert result.budget_exhausted is False
    assert result.termination_reason == "max_iterations"


def _fixed_params(evaluation_budget: int) -> dict[str, object]:
    return {
        **ALNS_PARAMS,
        "fair_comparison": {
            "evaluation_budget": evaluation_budget,
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        },
    }


def _native_params() -> dict[str, object]:
    return {
        **ALNS_PARAMS,
        "native_comparison": {
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
        },
    }


def _assert_fixed_evidence(problem: _Problem) -> None:
    executor = AlgorithmRegistry.get_executor("ALNS-TSP")
    first_params = _fixed_params(1)
    larger_params = _fixed_params(4)
    manifest = FairComparisonManifest.from_value(first_params["fair_comparison"])

    first = executor(problem, first_params, seed=987_654, run_idx=0)
    replay = executor(problem, first_params, seed=123_456, run_idx=0)
    larger = executor(problem, larger_params, seed=456_789, run_idx=0)

    assert first.algorithm == first.algorithm_id == "ALNS-TSP"
    assert first.algorithm_family == "ALNS"
    assert first.variant == "pure"
    assert first.seed == manifest.paired_seed(problem.name, 0)
    assert first.initialization_policy == "nearest_neighbor_from_node_zero_all_nodes"
    assert first.acceptance_policy == "simulated_annealing"
    assert first.neighborhood_window is None
    assert first.polish_policy == NO_POLISH
    assert first.execution_backend == "objective=python;polish=none"
    _assert_complete_and_exact(first, problem.dist_matrix)
    assert first.evaluation_budget == 1
    assert first.evaluations == 1
    assert first.iterations == 0
    assert first.budget_terminated is True
    assert first.termination_reason == "evaluation_budget_exhausted"
    assert larger.evaluation_budget == 4
    assert 1 <= larger.evaluations <= 4
    assert larger.budget_terminated is (
        larger.termination_reason == "evaluation_budget_exhausted"
    )
    assert larger.termination_reason in FIXED_REASONS
    _assert_complete_and_exact(larger, problem.dist_matrix)
    assert replay.tour == first.tour
    assert replay.tour_cost == pytest.approx(first.tour_cost)
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.iterations == first.iterations
    assert replay.termination_reason == first.termination_reason
    assert replay.execution_backend == first.execution_backend


def _assert_native_evidence(problem: _Problem) -> None:
    executor = AlgorithmRegistry.get_executor("ALNS-TSP")
    params = _native_params()
    manifest = NativeComparisonManifest.from_value(params["native_comparison"])

    first = executor(problem, params, seed=987_654, run_idx=0)
    replay = executor(problem, params, seed=123_456, run_idx=0)

    assert first.algorithm == first.algorithm_id == "ALNS-TSP"
    assert first.algorithm_family == "ALNS"
    assert first.variant == "pure"
    assert first.seed == manifest.paired_seed(problem.name, 0)
    assert first.initialization_policy == "nearest_neighbor_from_node_zero_all_nodes"
    assert first.acceptance_policy == "simulated_annealing"
    assert first.neighborhood_window is None
    assert first.polish_policy == NO_POLISH
    assert first.execution_backend == "objective=python;polish=none"
    _assert_complete_and_exact(first, problem.dist_matrix)
    assert first.evaluation_budget is None
    assert first.budget_terminated is False
    assert first.evaluations >= 1
    assert first.termination_reason in NATIVE_REASONS
    assert replay.tour == first.tour
    assert replay.tour_cost == pytest.approx(first.tour_cost)
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.iterations == first.iterations
    assert replay.termination_reason == first.termination_reason
    assert replay.execution_backend == first.execution_backend


def test_alns_fixed_tsp_evidence() -> None:
    _assert_fixed_evidence(SYMMETRIC_TSP)


def test_alns_fixed_atsp_evidence() -> None:
    _assert_fixed_evidence(DIRECTED_ATSP)


def test_alns_native_tsp_evidence() -> None:
    _assert_native_evidence(SYMMETRIC_TSP)


def test_alns_native_atsp_evidence() -> None:
    _assert_native_evidence(DIRECTED_ATSP)


@pytest.mark.parametrize(
    "invalid",
    [
        {"seed": 42},
        {"iterations": 8},
        {"max_no_improve": 3},
        {"noise_scale": 0.05},
        {"unexpected": "value"},
        {"remove_ratio": 0},
        {"weight_update_factor": 1.1},
        {"use_sa": True, "sa_start_temp": 0},
    ],
    ids=[
        "caller-seed",
        "legacy-iterations",
        "legacy-max-no-improve",
        "legacy-noise-scale",
        "unknown-key",
        "zero-remove-ratio",
        "oversized-weight-update",
        "zero-sa-temperature",
    ],
)
def test_alns_scientific_protocol_rejects_invalid_parameters(invalid: dict[str, object]) -> None:
    params = _fixed_params(1)
    params.update(invalid)

    with pytest.raises(ValueError):
        AlgorithmRegistry.get_executor("ALNS-TSP")(DIRECTED_ATSP, params, seed=41, run_idx=0)
