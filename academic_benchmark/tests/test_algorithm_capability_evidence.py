"""Executable evidence for granular academic TSP/ATSP capability claims."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
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
    list_algorithm_capabilities,
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
    fixed_claims = [
        claim
        for claim in capability.claims
        if claim.protocol is ExecutionProtocol.FIXED_BUDGET
    ]
    assert len(fixed_claims) == 2
    assert {claim.problem for claim in fixed_claims} == {
        ProblemContract.TSP,
        ProblemContract.ATSP,
    }
    for claim in fixed_claims:
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


def _evidence_node_parts(evidence_id: str) -> tuple[Path, str]:
    relative_path, separator, function_name = evidence_id.partition("::")
    assert separator == "::", f"evidence ID must name one pytest node: {evidence_id}"
    assert function_name.startswith("test_") and "[" not in function_name, (
        f"evidence ID must name a concrete test function: {evidence_id}"
    )
    root = Path(__file__).resolve().parents[2]
    path = root / relative_path
    assert path.is_file(), f"evidence file is missing: {relative_path}"
    return path, function_name


def test_alns_claims_cite_all_four_focused_evidence_nodes() -> None:
    capability = get_algorithm_capability("ALNS-TSP")
    assert capability is not None
    assert capability.lifecycle is LifecycleStatus.VERIFIED
    assert {
        evidence_id
        for claim in capability.claims
        for evidence_id in claim.evidence_ids
    } == {
        "academic_benchmark/tests/test_alns_c3_evidence.py::"
        "test_alns_fixed_tsp_evidence",
        "academic_benchmark/tests/test_alns_c3_evidence.py::"
        "test_alns_fixed_atsp_evidence",
        "academic_benchmark/tests/test_alns_c3_evidence.py::"
        "test_alns_native_tsp_evidence",
        "academic_benchmark/tests/test_alns_c3_evidence.py::"
        "test_alns_native_atsp_evidence",
    }


def test_published_claim_evidence_ids_are_exact_passing_pytest_nodes(tmp_path) -> None:
    """Evidence is a real, unskipped pytest function, never a helper or substring."""
    evidence_ids = {
        evidence_id
        for capability in list_algorithm_capabilities()
        if capability.lifecycle is LifecycleStatus.VERIFIED
        for claim in capability.claims
        for evidence_id in claim.evidence_ids
    }
    assert evidence_ids

    root = Path(__file__).resolve().parents[2]
    for index, evidence_id in enumerate(sorted(evidence_ids)):
        path, function_name = _evidence_node_parts(evidence_id)
        functions = {
            node.name
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert function_name in functions, (
            f"evidence ID must match a named test function exactly: {evidence_id}"
        )

        completed = subprocess.run(
            [
                sys.executable, "-m", "pytest", evidence_id, "-q",
                "-p", "no:cacheprovider", "--tb=short",
                "--basetemp", str(tmp_path / f"evidence-{index}"),
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        output = completed.stdout.lower() + completed.stderr.lower()
        assert " skipped" not in output and "skipped " not in output, output
        assert " passed" in output, output


def _require_live_numba_objective() -> None:
    from academic_benchmark.core.preflight import probe_runtime_backends

    availability = probe_runtime_backends()
    assert availability.numba_nopython, availability.detail


def _assert_metaheuristic_claims_published(
    algorithm_id: str,
    protocol: ExecutionProtocol,
    backend_profile: ExecutionBackendProfile,
    composition: CompositionKind,
    evidence_function: str,
) -> None:
    capability = get_algorithm_capability(algorithm_id)
    assert capability is not None
    assert capability.lifecycle is LifecycleStatus.VERIFIED
    claims = [claim for claim in capability.claims if claim.protocol is protocol]
    assert len(claims) == 2
    assert {claim.problem for claim in claims} == {ProblemContract.TSP, ProblemContract.ATSP}
    evidence_id = "academic_benchmark/tests/test_algorithm_capability_evidence.py::" + evidence_function
    for claim in claims:
        assert claim.backend_profile == backend_profile
        assert claim.composition is composition
        assert claim.directed_cost_preserved is (claim.problem is ProblemContract.ATSP)
        assert claim.exact_objective_accounting is True
        assert claim.fixed_seed_deterministic is True
        assert claim.truthful_result_reporting is True
        assert claim.evidence_ids == (evidence_id,)


def test_core_gwo_pure_fixed_tsp_and_atsp_numba_evidence() -> None:
    _require_live_numba_objective()
    _prove_fixed("Core-GWO-TSP-Pure", expected_backend="objective=numba;polish=none", expected_variant="pure", polish_enabled=False)
    _assert_metaheuristic_claims_published("Core-GWO-TSP-Pure", ExecutionProtocol.FIXED_BUDGET, ExecutionBackendProfile(BackendKind.NUMBA_NOPYTHON), CompositionKind.PURE, "test_core_gwo_pure_fixed_tsp_and_atsp_numba_evidence")


def test_core_hho_pure_fixed_tsp_and_atsp_numba_evidence() -> None:
    _require_live_numba_objective()
    _prove_fixed("Core-HHO-TSP-Pure", expected_backend="objective=numba;polish=none", expected_variant="pure", polish_enabled=False)
    _assert_metaheuristic_claims_published("Core-HHO-TSP-Pure", ExecutionProtocol.FIXED_BUDGET, ExecutionBackendProfile(BackendKind.NUMBA_NOPYTHON), CompositionKind.PURE, "test_core_hho_pure_fixed_tsp_and_atsp_numba_evidence")


def test_core_gwo_pure_native_tsp_and_atsp_numba_evidence() -> None:
    _require_live_numba_objective()
    _prove_native_metaheuristic("Core-GWO-TSP-Pure", expected_evaluations=5)
    _assert_metaheuristic_claims_published("Core-GWO-TSP-Pure", ExecutionProtocol.NATIVE_TERMINATION, ExecutionBackendProfile(BackendKind.NUMBA_NOPYTHON), CompositionKind.PURE, "test_core_gwo_pure_native_tsp_and_atsp_numba_evidence")


def test_core_hho_pure_native_tsp_and_atsp_numba_evidence() -> None:
    _require_live_numba_objective()
    _prove_native_metaheuristic("Core-HHO-TSP-Pure", expected_evaluations=8)
    _assert_metaheuristic_claims_published("Core-HHO-TSP-Pure", ExecutionProtocol.NATIVE_TERMINATION, ExecutionBackendProfile(BackendKind.NUMBA_NOPYTHON), CompositionKind.PURE, "test_core_hho_pure_native_tsp_and_atsp_numba_evidence")


def test_core_gwo_memetic_2opt_fixed_tsp_and_atsp_numba_evidence() -> None:
    _require_live_numba_objective()
    _prove_fixed("Core-GWO-TSP-Memetic-2opt", expected_backend="objective=numba;polish=python", expected_variant="memetic_2opt", polish_enabled=True)
    _assert_metaheuristic_claims_published("Core-GWO-TSP-Memetic-2opt", ExecutionProtocol.FIXED_BUDGET, ExecutionBackendProfile(BackendKind.NUMBA_NOPYTHON, BackendKind.PYTHON), CompositionKind.MEMETIC_2OPT, "test_core_gwo_memetic_2opt_fixed_tsp_and_atsp_numba_evidence")


def test_core_hho_memetic_2opt_fixed_tsp_and_atsp_numba_evidence() -> None:
    _require_live_numba_objective()
    _prove_fixed("Core-HHO-TSP-Memetic-2opt", expected_backend="objective=numba;polish=python", expected_variant="memetic_2opt", polish_enabled=True)
    _assert_metaheuristic_claims_published("Core-HHO-TSP-Memetic-2opt", ExecutionProtocol.FIXED_BUDGET, ExecutionBackendProfile(BackendKind.NUMBA_NOPYTHON, BackendKind.PYTHON), CompositionKind.MEMETIC_2OPT, "test_core_hho_memetic_2opt_fixed_tsp_and_atsp_numba_evidence")


def test_core_or_opt_fixed_tsp_and_atsp_evidence() -> None:
    _prove_fixed(
        "Core-OrOpt-TSP",
        expected_backend="objective=python;polish=none",
        expected_variant="pure",
        polish_enabled=False,
    )
    _assert_fixed_local_claims_published(
        "Core-OrOpt-TSP", "test_core_or_opt_fixed_tsp_and_atsp_evidence"
    )
