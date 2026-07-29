from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable

import pytest

from academic_benchmark.core.algorithm_errors import (
    CandidateAlgorithmError,
    ResultContractViolation,
    UnknownAlgorithmError,
    UnsupportedProblemContractError,
)
from academic_benchmark.core.algorithm_resolution import IdentifierSource, resolve_algorithm_id
from academic_benchmark.core.execution_gateway import (
    execute_preflighted,
    serialize_preflight_decision,
    validate_preflighted_result,
)
from academic_benchmark.core.preflight import PreflightRequest, RuntimeBackendAvailability, preflight_run
from academic_benchmark.fairness import FairRunResult
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol


@dataclass
class _Problem:
    name: str = "gateway-directed-atsp"
    problem_type: str = "atsp"
    dimension: int = 3
    dist_matrix: list[list[float]] | None = None

    def __post_init__(self) -> None:
        if self.dist_matrix is None:
            self.dist_matrix = [[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]]


PROBLEM = _Problem()
CANONICAL_ID = "Core-TwoOpt-TSP"
RUNTIME = RuntimeBackendAvailability(True, False, "deterministic Python-only unit test")


def _valid_result(**changes: Any) -> FairRunResult:
    values: dict[str, Any] = {
        "problem": PROBLEM.name,
        "algorithm": CANONICAL_ID,
        "algorithm_id": CANONICAL_ID,
        "algorithm_family": "2-opt",
        "variant": "local_search",
        "run": 2,
        "seed": 41,
        "dimension": 3,
        "optimal": None,
        "tour_cost": 9.0,
        "objective_cost": 9.0,
        "gap_pct": None,
        "elapsed_sec": 0.01,
        "iterations": 1,
        "evaluations": 7,
        "objective_evaluations": 7,
        "tour": [1, 2, 3],
        "evaluation_budget": 10,
        "budget_terminated": False,
        "termination_reason": "no_improving_move",
        "execution_backend": "objective=python;polish=none",
    }
    values.update(changes)
    return FairRunResult(**values)


def _execute(
    *,
    requested_algorithm_id: str = CANONICAL_ID,
    source: IdentifierSource = IdentifierSource.INTERNAL,
    problem: object = PROBLEM,
    protocol: ExecutionProtocol = ExecutionProtocol.FIXED_BUDGET,
    budget: int | None = 10,
    registry_getter: Callable[[str], Callable[..., FairRunResult]] | None = None,
):
    getter = registry_getter or (lambda _: lambda *args, **kwargs: _valid_result())
    return execute_preflighted(
        requested_algorithm_id=requested_algorithm_id,
        identifier_source=source,
        problem=problem,
        params={},
        seed=41,
        run_idx=2,
        protocol=protocol,
        backend_policy=BackendPolicy.PYTHON_ONLY,
        evaluation_budget=budget,
        registered_algorithm_ids=frozenset({CANONICAL_ID}),
        runtime_backends=RUNTIME,
        registry_getter=getter,
    )


class _ExplodingGetter:
    def __call__(self, algorithm_id: str):
        raise AssertionError(f"registry lookup occurred for {algorithm_id}")


@pytest.mark.parametrize(
    "requested_id,problem,error",
    [
        ("unknown", PROBLEM, UnknownAlgorithmError),
        ("Core-OrOpt-TSP", PROBLEM, CandidateAlgorithmError),
        (CANONICAL_ID, _Problem(problem_type="cvrp"), UnsupportedProblemContractError),
    ],
)
def test_resolution_and_preflight_failures_happen_before_registry_lookup(
    requested_id: str, problem: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        _execute(
            requested_algorithm_id=requested_id,
            problem=problem,
            registry_getter=_ExplodingGetter(),
        )


def test_gateway_uses_exact_lookup_then_execute_order_after_preflight() -> None:
    events: list[str] = []

    def getter(algorithm_id: str):
        events.append(f"lookup:{algorithm_id}")

        def executor(problem: object, params: object, seed: int, run_idx: int):
            events.append(f"execute:{seed}:{run_idx}")
            return _valid_result()

        return executor

    result, decision = _execute(registry_getter=getter)
    assert events == [f"lookup:{CANONICAL_ID}", "execute:41:2"]
    assert result.tour_cost == 9.0
    assert decision.executor_registry_id == CANONICAL_ID


def test_preflight_decision_serializer_preserves_complete_provenance() -> None:
    _, decision = _execute()

    assert serialize_preflight_decision(decision) == {
        "requested_algorithm_id": CANONICAL_ID,
        "canonical_algorithm_id": CANONICAL_ID,
        "backend_policy": "python_only",
        "backend_profile": {"objective": "python", "polish": "none"},
        "backend_fallback_used": False,
        "backend_fallback_reason": None,
        "executor_registry_id": CANONICAL_ID,
        "capability_evidence_ids": [
            "academic_benchmark/tests/test_algorithm_capability_evidence.py::"
            "test_core_two_opt_fixed_tsp_and_atsp_evidence"
        ],
    }

@pytest.mark.parametrize(
    "changes,match",
    [
        ({"tour": [1, 2]}, "complete"),
        ({"tour": [1, 1, 3]}, "duplicate"),
        ({"tour_cost": 16.0, "objective_cost": 16.0}, "directed closed-cycle cost"),
        ({"objective_cost": 16.0}, "objective_cost"),
        ({"objective_evaluations": 6}, "evaluation counts"),
        ({"evaluations": 11, "objective_evaluations": 11}, "budget"),
        ({"termination_reason": ""}, "termination_reason"),
        ({"algorithm": "Numba-2-opt"}, "canonical algorithm"),
        ({"algorithm_id": "Numba-2-opt"}, "canonical algorithm_id"),
    ],
)
def test_gateway_rejects_invalid_postflight_results(changes: dict[str, Any], match: str) -> None:
    with pytest.raises(ResultContractViolation, match=match):
        _execute(registry_getter=lambda _: lambda *args, **kwargs: _valid_result(**changes))


@pytest.mark.parametrize(
    "backend",
    [
        "unknown",
        "objective=unknown;polish=none",
        "objective=unused;polish=none",
        "objective=mixed;polish=none",
        "objective=numba+python;polish=none",
        "objective=python;polish=unused",
    ],
)
def test_gateway_rejects_unknown_unused_or_mixed_backend_labels(backend: str) -> None:
    with pytest.raises(ResultContractViolation, match="execution_backend"):
        _execute(
            registry_getter=lambda _: lambda *args, **kwargs: _valid_result(
                execution_backend=backend
            )
        )


def test_gateway_rejects_backend_profile_that_differs_from_decision() -> None:
    with pytest.raises(ResultContractViolation, match="selected backend profile"):
        _execute(
            registry_getter=lambda _: lambda *args, **kwargs: _valid_result(
                execution_backend="objective=numba;polish=none"
            )
        )


def test_native_postflight_requires_truthful_accounting_and_termination() -> None:
    fixed_decision = preflight_run(
        PreflightRequest(
            resolution=resolve_algorithm_id(CANONICAL_ID, IdentifierSource.INTERNAL),
            problem=PROBLEM,
            protocol=ExecutionProtocol.FIXED_BUDGET,
            backend_policy=BackendPolicy.PYTHON_ONLY,
            evaluation_budget=10,
            registered_algorithm_ids=frozenset({CANONICAL_ID}),
            runtime_backends=RUNTIME,
        )
    )
    native_decision = replace(fixed_decision, protocol=ExecutionProtocol.NATIVE_TERMINATION)
    with pytest.raises(ResultContractViolation, match="native termination"):
        validate_preflighted_result(
            _valid_result(evaluation_budget=None, termination_reason="evaluation_budget_exhausted"),
            native_decision,
        )
    with pytest.raises(ResultContractViolation, match="evaluation_budget must be null"):
        validate_preflighted_result(_valid_result(), native_decision)


def test_gateway_attaches_requested_alias_only_when_alias_was_used() -> None:
    canonical, _ = _execute(
        registry_getter=lambda _: lambda *args, **kwargs: _valid_result(
            requested_algorithm_id="stale-alias"
        )
    )
    with pytest.warns(DeprecationWarning, match="Numba-2-opt"):
        alias, _ = _execute(
            requested_algorithm_id="Numba-2-opt",
            source=IdentifierSource.CLI,
        )
    assert canonical.requested_algorithm_id is None
    assert alias.algorithm == alias.algorithm_id == CANONICAL_ID
    assert alias.requested_algorithm_id == "Numba-2-opt"
