"""C-16c evidence: the four capability claims of ``Core-GA-TSP-Memetic-2opt``.

TSP/ATSP x fixed/native, through the registered executor. The accounting contract itself is
pinned in ``test_ga_memetic_accounting.py``; here the rows are checked end to end: exact
count (population, initial 2-opt candidates, generations, final 2-opt candidates), directed
costs, the executed-count polish policy and deterministic replay.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest

# Sibling test modules are not a package; load the shared fixtures by path.
_path = Path(__file__).with_name("test_ga_memetic_accounting.py")
_spec = importlib.util.spec_from_file_location("_c16c_accounting", _path)
acc = importlib.util.module_from_spec(_spec)
sys.modules["_c16c_accounting"] = acc
_spec.loader.exec_module(acc)

MEMETIC_ID = acc.MEMETIC_ID


def _require_live_numba_objective() -> None:
    from academic_benchmark.core.preflight import probe_runtime_backends

    availability = probe_runtime_backends()
    assert availability.numba_nopython, availability.detail


def _assert_row(row, problem, expected_seed, expected_flags=None) -> None:
    expected_flags = acc.EXPECTED_POLICY_FLAGS if expected_flags is None else expected_flags
    matrix = problem.dist_matrix
    assert row.algorithm == row.algorithm_id == MEMETIC_ID
    assert row.algorithm_family == "GA"
    assert row.variant == "memetic_2opt"
    assert row.seed == expected_seed
    assert row.initialization_policy == (
        "paired_seed_random_population_all_nodes_with_initial_2opt"
    )
    flags = {k: row.polish_policy[k] for k in expected_flags}
    assert flags == expected_flags
    assert row.execution_backend == "objective=numba;polish=python"
    route = [node - 1 for node in row.tour]
    assert sorted(route) == list(range(len(matrix)))
    assert row.tour_cost == pytest.approx(acc._directed_cost(route, matrix))
    assert row.objective_cost == pytest.approx(acc._directed_cost(route, matrix))
    assert row.evaluations == row.objective_evaluations


def _assert_replay(first, replay) -> None:
    for field in ("tour", "tour_cost", "objective_evaluations", "iterations",
                  "termination_reason", "polish_policy", "execution_backend", "seed"):
        assert getattr(replay, field) == getattr(first, field), field


def _fixed(problem, expected_type) -> None:
    _require_live_numba_objective()
    assert problem.problem_type == expected_type
    executor = AlgorithmRegistry.get_executor(MEMETIC_ID)
    manifest = FairComparisonManifest.from_value(
        acc._fixed_params(acc.COMPLETE)["fair_comparison"]
    )
    seed = manifest.paired_seed(problem.name, 0)
    complete = executor(problem, acc._fixed_params(acc.COMPLETE), seed=987_654, run_idx=0)
    replay = executor(problem, acc._fixed_params(acc.COMPLETE), seed=123_456, run_idx=0)
    inside_final = executor(problem, acc._fixed_params(acc.COMPLETE - 1), seed=1, run_idx=0)
    inside_initial = executor(
        problem, acc._fixed_params(acc.POP + acc.PAIRS), seed=1, run_idx=0
    )

    _assert_row(complete, problem, seed)
    assert complete.evaluations == acc.COMPLETE
    assert complete.budget_terminated is False
    assert complete.termination_reason == "max_iterations"
    assert complete.iterations == acc.GENERATIONS
    _assert_replay(complete, replay)

    _assert_row(inside_final, problem, seed)
    assert inside_final.evaluations == acc.COMPLETE - 1
    assert inside_final.budget_terminated is True
    assert inside_final.termination_reason == "evaluation_budget_exhausted"

    # budget ends inside the initial polish: the final polish never started
    _assert_row(
        inside_initial, problem, seed,
        {**acc.EXPECTED_POLICY_FLAGS, "final": False},
    )
    assert inside_initial.evaluations == acc.POP + acc.PAIRS
    assert inside_initial.iterations == 0
    assert inside_initial.polish_policy["final"] is False
    assert inside_initial.termination_reason == "evaluation_budget_exhausted"


def _native(problem, expected_type) -> None:
    _require_live_numba_objective()
    assert problem.problem_type == expected_type
    executor = AlgorithmRegistry.get_executor(MEMETIC_ID)
    params = acc._native_params()
    manifest = NativeComparisonManifest.from_value(params["native_comparison"])
    first = executor(problem, params, seed=987_654, run_idx=0)
    replay = executor(problem, params, seed=123_456, run_idx=0)
    _assert_row(first, problem, manifest.paired_seed(problem.name, 0))
    assert first.evaluation_budget is None and first.budget_terminated is False
    assert first.termination_reason in {"max_iterations", "stagnation_limit"}
    assert first.evaluations == (
        acc.POP + acc.INIT_POLISH + first.iterations * acc.OFFSPRING + acc.PAIRS
    )
    assert first.polish_policy["evaluations"] == {
        "initial": acc.INIT_POLISH, "periodic": 0, "final": acc.PAIRS,
    }
    _assert_replay(first, replay)


def test_core_ga_memetic_2opt_fixed_tsp_evidence() -> None:
    _fixed(acc.SYMMETRIC_TSP, "tsp")


def test_core_ga_memetic_2opt_fixed_atsp_evidence() -> None:
    _fixed(acc.DIRECTED_ATSP, "atsp")


def test_core_ga_memetic_2opt_native_tsp_evidence() -> None:
    _native(acc.SYMMETRIC_TSP, "tsp")


def test_core_ga_memetic_2opt_native_atsp_evidence() -> None:
    _native(acc.DIRECTED_ATSP, "atsp")


def test_ga_memetic_claims_cite_the_four_evidence_nodes_and_pure_claims_are_unchanged() -> None:
    from uniride_core.algorithms.capabilities import (
        BackendKind,
        CompositionKind,
        ExecutionProtocol,
        LifecycleStatus,
        ProblemContract,
        get_algorithm_capability,
    )

    capability = get_algorithm_capability(MEMETIC_ID)
    assert capability is not None and capability.lifecycle is LifecycleStatus.VERIFIED
    prefix = "academic_benchmark/tests/test_ga_memetic_evidence.py::"
    assert {e for claim in capability.claims for e in claim.evidence_ids} == {
        prefix + f"test_core_ga_memetic_2opt_{protocol}_{problem}_evidence"
        for protocol in ("fixed", "native") for problem in ("tsp", "atsp")
    }
    assert {(c.problem, c.protocol) for c in capability.claims} == {
        (problem, protocol)
        for problem in (ProblemContract.TSP, ProblemContract.ATSP)
        for protocol in (ExecutionProtocol.FIXED_BUDGET, ExecutionProtocol.NATIVE_TERMINATION)
    }
    root = Path(__file__).resolve().parents[2]
    for claim in capability.claims:
        assert claim.composition is CompositionKind.MEMETIC_2OPT
        assert claim.backend_profile.objective is BackendKind.NUMBA_NOPYTHON
        assert claim.backend_profile.polish is BackendKind.PYTHON
        assert claim.directed_cost_preserved is (claim.problem is ProblemContract.ATSP)
        assert claim.exact_objective_accounting and claim.fixed_seed_deterministic
        assert claim.truthful_result_reporting
        for evidence_id in claim.evidence_ids:
            path, _, function = evidence_id.partition("::")
            assert f"def {function}(" in (root / path).read_text(encoding="utf-8")

    pure = get_algorithm_capability("Core-GA-TSP")
    for claim in pure.claims:
        assert claim.composition is CompositionKind.PURE
        assert claim.backend_profile.polish is BackendKind.NONE
