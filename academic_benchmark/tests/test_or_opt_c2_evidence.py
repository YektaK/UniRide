from __future__ import annotations

from dataclasses import dataclass

import pytest

from academic_benchmark.core.registry_setup import _problem_matrix
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest


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
    name="c2-or-opt-symmetric-tsp-5",
    problem_type="tsp",
    dist_matrix=[
        [0.0, 4.0, 8.0, 7.0, 3.0],
        [4.0, 0.0, 5.0, 9.0, 6.0],
        [8.0, 5.0, 0.0, 2.0, 7.0],
        [7.0, 9.0, 2.0, 0.0, 4.0],
        [3.0, 6.0, 7.0, 4.0, 0.0],
    ],
)

DIRECTED_ATSP = _Problem(
    name="c2-or-opt-directed-atsp-5",
    problem_type="atsp",
    dist_matrix=[
        [0.0, 2.0, 9.0, 7.0, 6.0],
        [8.0, 0.0, 3.0, 9.0, 2.0],
        [5.0, 6.0, 0.0, 2.0, 8.0],
        [4.0, 7.0, 6.0, 0.0, 2.0],
        [9.0, 3.0, 7.0, 8.0, 0.0],
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


def _fixed_params() -> dict[str, object]:
    return {
        "max_iterations": 3,
        "first_improvement": False,
        "window": 3,
        "fair_comparison": {
            "evaluation_budget": 1,
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        },
    }


def _native_params() -> dict[str, object]:
    return {
        "max_iterations": 3,
        "first_improvement": False,
        "window": 3,
        "native_comparison": {
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
        },
    }


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda problem: problem.name)
def test_or_opt_fixed_protocol_proves_tsp_and_atsp_contract(problem: _Problem) -> None:
    params = _fixed_params()
    manifest = FairComparisonManifest.from_value(params["fair_comparison"])
    executor = AlgorithmRegistry.get_executor("Core-OrOpt-TSP")

    first = executor(problem, params, seed=987_654, run_idx=0)
    replay = executor(problem, params, seed=123_456, run_idx=0)

    expected_seed = manifest.paired_seed(problem.name, 0)
    assert first.algorithm == first.algorithm_id == "Core-OrOpt-TSP"
    assert first.algorithm_family == "Or-opt"
    assert first.variant == "pure"
    assert first.seed == expected_seed
    assert sorted(first.tour) == list(range(1, problem.dimension + 1))
    matrix, _ = _problem_matrix(problem)
    assert first.tour_cost == pytest.approx(
        _independent_closed_cost(first.tour, matrix)
    )
    assert first.objective_cost == pytest.approx(first.tour_cost)
    assert first.objective_evaluations == first.evaluations
    assert first.evaluation_budget == 1
    assert first.objective_evaluations == 1
    assert first.budget_terminated is True
    assert first.termination_reason == "evaluation_budget_exhausted"
    assert first.execution_backend == "objective=python;polish=none"
    assert replay.tour == first.tour
    assert replay.tour_cost == pytest.approx(first.tour_cost)
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.termination_reason == first.termination_reason
    assert replay.execution_backend == first.execution_backend


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda problem: problem.name)
def test_or_opt_native_protocol_proves_tsp_and_atsp_contract(problem: _Problem) -> None:
    params = _native_params()
    manifest = NativeComparisonManifest.from_value(params["native_comparison"])
    executor = AlgorithmRegistry.get_executor("Core-OrOpt-TSP")

    first = executor(problem, params, seed=987_654, run_idx=0)
    replay = executor(problem, params, seed=123_456, run_idx=0)

    expected_seed = manifest.paired_seed(problem.name, 0)
    assert first.algorithm == first.algorithm_id == "Core-OrOpt-TSP"
    assert first.algorithm_family == "Or-opt"
    assert first.variant == "pure"
    assert first.seed == expected_seed
    assert sorted(first.tour) == list(range(1, problem.dimension + 1))
    matrix, _ = _problem_matrix(problem)
    assert first.tour_cost == pytest.approx(
        _independent_closed_cost(first.tour, matrix)
    )
    assert first.objective_cost == pytest.approx(first.tour_cost)
    assert first.objective_evaluations == first.evaluations
    assert first.evaluation_budget is None
    assert first.budget_terminated is False
    assert first.termination_reason in {"max_iterations", "no_improving_move"}
    assert first.execution_backend == "objective=python;polish=none"
    assert replay.tour == first.tour
    assert replay.tour_cost == pytest.approx(first.tour_cost)
    assert replay.objective_evaluations == first.objective_evaluations
    assert replay.termination_reason == first.termination_reason
    assert replay.execution_backend == first.execution_backend

from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    improve_or_opt_budgeted,
)

@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda problem: problem.name)
@pytest.mark.parametrize("limit", [1, 7, None], ids=["atomic", "bounded", "unbounded"])
def test_or_opt_budgeted_controller_is_exact_and_deterministic(
    problem: _Problem, limit: int | None
) -> None:
    initial_route = [0, 1, 2, 3, 4]
    matrix = problem.dist_matrix

    budget = ObjectiveEvaluationBudget(limit)
    first = improve_or_opt_budgeted(
        initial_route,
        matrix,
        budget,
        max_iterations=2,
        first_improvement=False,
        max_segment_length=3,
    )
    replay_budget = ObjectiveEvaluationBudget(limit)
    replay = improve_or_opt_budgeted(
        initial_route,
        matrix,
        replay_budget,
        max_iterations=2,
        first_improvement=False,
        max_segment_length=3,
    )

    assert sorted(first.route) == list(range(problem.dimension))
    assert first.cost == pytest.approx(
        sum(
            matrix[node][first.route[(index + 1) % len(first.route)]]
            for index, node in enumerate(first.route)
        )
    )
    assert first.evaluations == budget.used
    if limit is not None:
        assert first.evaluations <= limit
    assert first.mode == (
        "symmetric_tsp" if problem is SYMMETRIC_TSP else "directed_atsp"
    )
    if limit == 1:
        assert first.budget_exhausted is True
        assert first.termination_reason == "evaluation_budget_exhausted"
    else:
        assert first.termination_reason in {
            "max_iterations",
            "no_improving_move",
            "evaluation_budget_exhausted",
        }
    assert replay == first
    assert replay_budget.used == budget.used

from academic_benchmark.fairness import FairRunResult, FairnessValidationError

def _or_opt_result(*, native: bool, family: str = "Or-opt", window: int | None = 3, reason: str | None = None) -> FairRunResult:
    if native:
        manifest = NativeComparisonManifest.from_value(
            {
                "base_seed": BASE_SEED,
                "protocol_version": "uniride-native-tsp-v1",
                "comparison_regime": "algorithm_native_termination",
            }
        )
        evaluation_budget = None
        budget_terminated = False
        termination_reason = reason or "no_improving_move"
    else:
        manifest = FairComparisonManifest.from_value(
            {
                "evaluation_budget": 1,
                "base_seed": BASE_SEED,
                "protocol_version": "uniride-fair-tsp-v2",
                "comparison_regime": "fixed_evaluation_budget",
            }
        )
        evaluation_budget = 1
        budget_terminated = True
        termination_reason = reason or "evaluation_budget_exhausted"
    problem = "c2-or-opt-validator"
    seed = manifest.paired_seed(problem, 0)
    return FairRunResult(
        problem=problem,
        algorithm="Core-OrOpt-TSP",
        algorithm_id="Core-OrOpt-TSP",
        algorithm_family=family,
        variant="pure",
        run=0,
        seed=seed,
        seed_group=manifest.seed_group(problem, 0),
        dimension=5,
        optimal=None,
        tour_cost=10.0,
        objective_cost=10.0,
        gap_pct=None,
        elapsed_sec=0.0,
        iterations=1,
        evaluations=1,
        objective_evaluations=1,
        evaluation_budget=evaluation_budget,
        budget_terminated=budget_terminated,
        tour=[1, 2, 3, 4, 5],
        problem_type="tsp",
        matrix_kind="distance",
        initialization_policy="paired_seed_random_permutation_all_nodes",
        termination_policy="test",
        execution_backend="objective=python;polish=none",
        polish_policy={
            "enabled": False,
            "initial": False,
            "periodic": False,
            "final": False,
            "operator": None,
        },
        comparison_regime=manifest.comparison_regime,
        acceptance_policy="best_improvement",
        neighborhood_window=window,
        termination_reason=termination_reason,
    )


def test_or_opt_fair_manifest_accepts_family_and_window() -> None:
    manifest = FairComparisonManifest.from_value(
        {
            "evaluation_budget": 1,
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        }
    )
    manifest.validate_result(_or_opt_result(native=False))


def test_or_opt_native_manifest_accepts_family_and_window() -> None:
    manifest = NativeComparisonManifest.from_value(
        {
            "base_seed": BASE_SEED,
            "protocol_version": "uniride-native-tsp-v1",
            "comparison_regime": "algorithm_native_termination",
        }
    )
    manifest.validate_result(_or_opt_result(native=True))


@pytest.mark.parametrize("native,family,window,reason", [
    (False, "2-opt", 3, "evaluation_budget_exhausted"),
    (False, "Or-opt", 0, "evaluation_budget_exhausted"),
    (False, "Or-opt", 3, "unsupported"),
    (True, "2-opt", 3, "no_improving_move"),
    (True, "Or-opt", 0, "no_improving_move"),
    (True, "Or-opt", 3, "unsupported"),
])
def test_or_opt_manifest_rejects_invalid_family_window_or_reason(
    native: bool, family: str, window: int, reason: str
) -> None:
    result = _or_opt_result(
        native=native, family=family, window=window, reason=reason
    )
    manifest = (
        NativeComparisonManifest.from_value(
            {
                "base_seed": BASE_SEED,
                "protocol_version": "uniride-native-tsp-v1",
                "comparison_regime": "algorithm_native_termination",
            }
        )
        if native
        else FairComparisonManifest.from_value(
            {
                "evaluation_budget": 1,
                "base_seed": BASE_SEED,
                "protocol_version": "uniride-fair-tsp-v2",
                "comparison_regime": "fixed_evaluation_budget",
            }
        )
    )
    with pytest.raises(FairnessValidationError):
        manifest.validate_result(result)
