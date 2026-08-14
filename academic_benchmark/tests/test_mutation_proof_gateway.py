"""Mutation-proof: the academic execution-gateway RunResult contract.

A real canonical 3-opt solve produces a RunResult through the preflight
gateway (control). Every injected mutation — algorithm identity, tour
permutation, reported cost, evaluation counts, budget, termination, backend —
must raise ``ResultContractViolation``. A mutated result surviving the gateway
would let a solver claim a cost/tour/budget it did not actually produce.
"""

import numpy as np
import pytest

from academic_benchmark.core.algorithm_errors import ResultContractViolation
from academic_benchmark.core.algorithm_resolution import IdentifierSource, resolve_algorithm_id
from academic_benchmark.core.execution_gateway import (
    execute_preflighted,
    validate_preflighted_result,
)
from academic_benchmark.core.preflight import RuntimeBackendAvailability, preflight_run, PreflightRequest
from academic_benchmark.fairness import FairRunResult
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol
from uniride_core.algorithms.three_opt import improve_three_opt

CANONICAL_ID = "Core-TwoOpt-TSP"
BACKEND_PROFILE = "objective=python;polish=none"
BUDGET = 50

MATRIX_6 = np.array(
    [
        [0.0, 2.0, 9.0, 10.0, 1.0, 8.0],
        [3.0, 0.0, 6.0, 4.0, 3.0, 7.0],
        [9.0, 6.0, 0.0, 5.0, 8.0, 2.0],
        [10.0, 4.0, 5.0, 0.0, 6.0, 9.0],
        [1.0, 3.0, 8.0, 6.0, 0.0, 4.0],
        [8.0, 7.0, 2.0, 9.0, 4.0, 0.0],
    ],
    dtype=float,
).tolist()


class _Problem:
    name = "mutation-proof-directed-atsp"
    problem_type = "atsp"
    dimension = 6
    dist_matrix = MATRIX_6


def _real_solve_run_result() -> FairRunResult:
    """Run the real canonical 3-opt engine and wrap its output as RunResult."""
    result = improve_three_opt(list(range(6)), MATRIX_6)
    tour = [node + 1 for node in result.route]
    return FairRunResult(
        problem=_Problem.name,
        algorithm=CANONICAL_ID,
        algorithm_id=CANONICAL_ID,
        algorithm_family="2-opt",
        variant="local_search",
        run=2,
        seed=41,
        dimension=6,
        optimal=None,
        tour_cost=result.cost,
        objective_cost=result.cost,
        gap_pct=None,
        elapsed_sec=0.01,
        iterations=result.iterations,
        evaluations=result.evaluations,
        objective_evaluations=result.evaluations,
        tour=tour,
        evaluation_budget=BUDGET,
        budget_terminated=False,
        termination_reason="no_improving_move",
        execution_backend=BACKEND_PROFILE,
    )


def _decision():
    resolution = resolve_algorithm_id(CANONICAL_ID, IdentifierSource.INTERNAL)
    return preflight_run(
        PreflightRequest(
            resolution=resolution,
            problem=_Problem(),
            protocol=ExecutionProtocol.FIXED_BUDGET,
            backend_policy=BackendPolicy.PYTHON_ONLY,
            evaluation_budget=BUDGET,
            registered_algorithm_ids=frozenset({CANONICAL_ID}),
            runtime_backends=RuntimeBackendAvailability(
                True, False, "deterministic Python-only unit test"
            ),
        )
    )


DECISION = _decision()


def _valid_result() -> FairRunResult:
    return _real_solve_run_result()


def _assert_rejected(**changes):
    result = _real_solve_run_result()
    for key, value in changes.items():
        setattr(result, key, value)
    with pytest.raises(ResultContractViolation):
        validate_preflighted_result(result, DECISION)


def test_gateway_accepts_real_solver_output():
    validate_preflighted_result(_valid_result(), DECISION)


def test_gateway_rejects_wrong_algorithm_identity():
    _assert_rejected(algorithm="Other-TSP", algorithm_id="Other-TSP")


def test_gateway_rejects_tour_with_missing_node():
    _assert_rejected(tour=[1, 2, 3, 4, 5])


def test_gateway_rejects_tour_with_duplicate_node():
    _assert_rejected(tour=[1, 2, 3, 4, 5, 5])


def test_gateway_rejects_tour_with_non_1_indexed_node():
    _assert_rejected(tour=[0, 1, 2, 3, 4, 5])


def test_gateway_rejects_tour_with_bool_node():
    _assert_rejected(tour=[1, 2, 3, 4, 5, True])


def test_gateway_rejects_inflated_tour_cost():
    _assert_rejected(tour_cost=_real_solve_run_result().tour_cost + 1.0)


def test_gateway_rejects_mismatched_objective_cost():
    _assert_rejected(objective_cost=_real_solve_run_result().objective_cost + 1.0)


def test_gateway_rejects_zero_evaluations():
    _assert_rejected(evaluations=0, objective_evaluations=0)


def test_gateway_rejects_evaluation_count_mismatch():
    _assert_rejected(evaluations=3, objective_evaluations=4)


def test_gateway_rejects_budget_mismatch():
    _assert_rejected(evaluation_budget=BUDGET - 1)


def test_gateway_rejects_inconsistent_budget_termination():
    _assert_rejected(budget_terminated=True)


def test_gateway_rejects_wrong_backend_profile():
    _assert_rejected(execution_backend="objective=rust;polish=none")


def test_gateway_rejects_blank_termination_reason():
    _assert_rejected(termination_reason="")