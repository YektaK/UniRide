"""C-08 evidence: GWO/HHO + final 3-opt hybrids (``global_then_final_3opt``).

Each ``test_core_*_memetic_3opt_*`` function below is cited by the capability claims as
executable evidence and must pass on its own. IDs stay ``Core-GWO-TSP-Memetic-3opt`` and
``Core-HHO-TSP-Memetic-3opt`` (owner decision Q5); the composition kind and the label say
that the 3-opt polish runs once, after the global stage.
"""
from __future__ import annotations

import copy
import dataclasses
import math
from dataclasses import dataclass

import pytest

from academic_benchmark.core import registry_setup
from academic_benchmark.core.algorithm_errors import ResultContractViolation
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.execution_gateway import (
    execute_preflighted,
    governed_contract_seed,
)
from academic_benchmark.core.preflight import probe_runtime_backends
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest
from academic_benchmark.protocol_registry import assert_single_pooling_group
from uniride_core.algorithms.capabilities import (
    BackendKind,
    BackendPolicy,
    CompositionKind,
    ExecutionBackendProfile,
    ExecutionProtocol,
    LifecycleStatus,
    ProblemContract,
    find_capability_claim,
    get_algorithm_capability,
)
from uniride_core.algorithms.composition import global_stage_cap

BASE_SEED = 523
GWO = "Core-GWO-TSP-Memetic-3opt"
HHO = "Core-HHO-TSP-Memetic-3opt"
EVIDENCE_FILE = "academic_benchmark/tests/test_hybrid_3opt_evidence.py::"
PROFILE = ExecutionBackendProfile(BackendKind.NUMBA_NOPYTHON, BackendKind.PYTHON)
BACKEND_LABEL = "objective=numba;polish=python"

GLOBAL_PARAMS = {
    GWO: {
        "pack_size": 5, "max_iterations": 3, "initial_a": 2.0,
        "exploration_rate": 0.4, "max_no_improvement": 99,
    },
    HHO: {
        "hawks": 5, "max_iterations": 3, "initial_energy": 1.0,
        "jump_probability": 0.0, "max_no_improvement": 99, "dive_count": 0,
        "levy_scale": 0.3,
    },
}
POLISH_PARAMS = {"max_iterations": 6, "first_improvement": False, "window": 5}
FRACTION = 0.8
BUDGET = 600

SYMMETRIC_7 = [
    [0.0, 4.0, 8.0, 7.0, 3.0, 6.0, 5.0],
    [4.0, 0.0, 5.0, 9.0, 6.0, 4.0, 7.0],
    [8.0, 5.0, 0.0, 2.0, 7.0, 3.0, 6.0],
    [7.0, 9.0, 2.0, 0.0, 4.0, 5.0, 8.0],
    [3.0, 6.0, 7.0, 4.0, 0.0, 8.0, 2.0],
    [6.0, 4.0, 3.0, 5.0, 8.0, 0.0, 9.0],
    [5.0, 7.0, 6.0, 8.0, 2.0, 9.0, 0.0],
]
# Asymmetric on purpose: the reverse of any tour costs a different amount.
ASYMMETRIC_7 = [
    [0.0, 2.0, 9.0, 7.0, 6.0, 5.0, 8.0],
    [8.0, 0.0, 3.0, 9.0, 2.0, 7.0, 4.0],
    [5.0, 6.0, 0.0, 2.0, 8.0, 4.0, 9.0],
    [4.0, 7.0, 6.0, 0.0, 2.0, 9.0, 3.0],
    [9.0, 3.0, 7.0, 8.0, 0.0, 2.0, 6.0],
    [3.0, 8.0, 5.0, 4.0, 6.0, 0.0, 7.0],
    [6.0, 5.0, 4.0, 3.0, 9.0, 8.0, 0.0],
]


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


TSP = _Problem("hybrid-evidence-tsp-7", "tsp", SYMMETRIC_7)
ATSP = _Problem("hybrid-evidence-atsp-7", "atsp", ASYMMETRIC_7)
PROBLEMS = (TSP, ATSP)


def _require_numba() -> None:
    availability = probe_runtime_backends()
    assert availability.numba_nopython, availability.detail


def _closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    route = [node - 1 for node in tour]
    return sum(
        float(matrix[node][route[(i + 1) % len(route)]]) for i, node in enumerate(route)
    )


def _fixed_params(algorithm: str, budget: int = BUDGET, fraction: float = FRACTION) -> dict:
    return {
        "global": dict(GLOBAL_PARAMS[algorithm]),
        "polish": dict(POLISH_PARAMS),
        "global_fraction": fraction,
        "fair_comparison": {
            "evaluation_budget": budget, "base_seed": BASE_SEED,
            "protocol_version": "uniride-fair-tsp-v2",
            "comparison_regime": "fixed_evaluation_budget",
        },
    }


def _native_params(algorithm: str) -> dict:
    return {
        "global": dict(GLOBAL_PARAMS[algorithm]),
        "polish": dict(POLISH_PARAMS),
        "native_comparison": {"base_seed": BASE_SEED},
    }


def _executor(algorithm: str):
    return registry_setup._make_hybrid_3opt_executor(algorithm)


def _assert_common(result, problem, algorithm, *, native: bool) -> None:
    assert sorted(result.tour) == list(range(1, problem.dimension + 1))
    independent = _closed_cost(result.tour, problem.dist_matrix)
    assert result.tour_cost == pytest.approx(independent)
    assert result.objective_cost == pytest.approx(independent)
    assert result.algorithm == result.algorithm_id == algorithm
    assert result.variant == "global_then_final_3opt"
    assert result.execution_backend == BACKEND_LABEL
    global_stage, polish_stage = result.composition["stages"]
    assert (global_stage["stage_id"], polish_stage["stage_id"]) == (
        algorithm.replace("Memetic-3opt", "Pure"), "Core-ThreeOpt-TSP",
    )
    assert polish_stage["seed"] is None  # deterministic 3-opt: no secondary seed
    assert global_stage["seed"] == result.seed
    assert result.evaluations == result.objective_evaluations == (
        global_stage["consumed_evaluations"] + polish_stage["consumed_evaluations"]
    )
    assert result.composition["kind"] == "global_then_final_3opt"
    assert "polish_iters" not in global_stage["parameters"]
    if native:
        assert result.comparison_regime == "algorithm_native_termination"
        assert result.termination_reason == "composite_complete"
        assert result.evaluation_budget is None and result.budget_terminated is False
        assert result.composition["global_fraction"] is None
        assert global_stage["allocated_evaluations"] is None
    else:
        assert result.comparison_regime == "fixed_evaluation_budget"
        assert result.evaluation_budget == BUDGET
        assert result.composition["global_fraction"] == FRACTION
        assert global_stage["allocated_evaluations"] == global_stage_cap(BUDGET, FRACTION)
        assert result.evaluations <= BUDGET
        assert result.budget_terminated is (
            result.termination_reason == "evaluation_budget_exhausted"
        )
    # polish never makes the tour worse; the flag says whether it changed
    assert result.tour_cost <= global_stage["details"]["cost"] + 1e-9
    assert polish_stage["details"]["polish_changed_tour"] is result.composition[
        "polish_changed_tour"
    ]


def _prove_fixed(algorithm: str) -> None:
    _require_numba()
    for problem in PROBLEMS:
        params = _fixed_params(algorithm)
        first = _executor(algorithm)(problem, params, seed=9, run_idx=0)
        replay = _executor(algorithm)(problem, params, seed=77, run_idx=0)
        manifest = FairComparisonManifest.from_value(params["fair_comparison"])
        assert first.seed == manifest.paired_seed(problem.name, 0)
        _assert_common(first, problem, algorithm, native=False)
        manifest.validate_result(first)
        assert (replay.tour, replay.tour_cost, replay.evaluations, replay.composition) == (
            first.tour, first.tour_cost, first.evaluations, first.composition,
        )


def _prove_native(algorithm: str) -> None:
    _require_numba()
    for problem in PROBLEMS:
        params = _native_params(algorithm)
        first = _executor(algorithm)(problem, params, seed=9, run_idx=0)
        replay = _executor(algorithm)(problem, params, seed=77, run_idx=0)
        manifest = NativeComparisonManifest.from_value(params["native_comparison"])
        assert first.seed == manifest.paired_seed(problem.name, 0)
        _assert_common(first, problem, algorithm, native=True)
        manifest.validate_result(first)
        assert (replay.tour, replay.tour_cost, replay.evaluations, replay.composition) == (
            first.tour, first.tour_cost, first.evaluations, first.composition,
        )


def _assert_claims_published(algorithm: str, protocol: ExecutionProtocol, function: str) -> None:
    capability = get_algorithm_capability(algorithm)
    assert capability is not None
    assert capability.lifecycle is LifecycleStatus.VERIFIED
    assert "final polish once" in capability.label
    for problem in (ProblemContract.TSP, ProblemContract.ATSP):
        claim = find_capability_claim(
            algorithm, problem=problem, protocol=protocol, backend_profile=PROFILE,
            composition=CompositionKind.GLOBAL_THEN_FINAL_3OPT,
        )
        assert claim is not None, (algorithm, problem, protocol)
        assert claim.directed_cost_preserved is (problem is ProblemContract.ATSP)
        assert claim.exact_objective_accounting is True
        assert claim.fixed_seed_deterministic is True
        assert claim.truthful_result_reporting is True
        assert claim.evidence_ids == (EVIDENCE_FILE + function,)


# ---- the four evidence nodes cited by the claims ---------------------------

def test_core_gwo_memetic_3opt_fixed_tsp_and_atsp_evidence() -> None:
    _prove_fixed(GWO)
    _assert_claims_published(GWO, ExecutionProtocol.FIXED_BUDGET,
                             "test_core_gwo_memetic_3opt_fixed_tsp_and_atsp_evidence")


def test_core_hho_memetic_3opt_fixed_tsp_and_atsp_evidence() -> None:
    _prove_fixed(HHO)
    _assert_claims_published(HHO, ExecutionProtocol.FIXED_BUDGET,
                             "test_core_hho_memetic_3opt_fixed_tsp_and_atsp_evidence")


def test_core_gwo_memetic_3opt_native_tsp_and_atsp_evidence() -> None:
    _prove_native(GWO)
    _assert_claims_published(GWO, ExecutionProtocol.NATIVE_TERMINATION,
                             "test_core_gwo_memetic_3opt_native_tsp_and_atsp_evidence")


def test_core_hho_memetic_3opt_native_tsp_and_atsp_evidence() -> None:
    _prove_native(HHO)
    _assert_claims_published(HHO, ExecutionProtocol.NATIVE_TERMINATION,
                             "test_core_hho_memetic_3opt_native_tsp_and_atsp_evidence")


# ---- further C-08 evidence -------------------------------------------------

@pytest.mark.parametrize("algorithm", (GWO, HHO))
def test_atsp_directed_cost_is_preserved_with_an_independent_closed_cycle_cost(algorithm):
    _require_numba()
    reverse = _Problem("reverse", "atsp", [list(col) for col in zip(*ASYMMETRIC_7)])
    result = _executor(algorithm)(ATSP, _fixed_params(algorithm), seed=1, run_idx=0)
    independent = _closed_cost(result.tour, ASYMMETRIC_7)
    reversed_cost = _closed_cost(result.tour, reverse.dist_matrix)
    assert independent != pytest.approx(reversed_cost)  # fixture really is directed
    assert math.isclose(result.tour_cost, independent, rel_tol=1e-9)
    assert result.composition["stages"][1]["details"]["mode"] == "directed_atsp"
    assert result.matrix_kind == "distance"


@pytest.mark.parametrize("algorithm", (GWO, HHO))
def test_fixed_and_native_composite_rows_fail_the_single_pooling_group_check(algorithm):
    _require_numba()
    fixed = _executor(algorithm)(TSP, _fixed_params(algorithm), seed=1, run_idx=0)
    native = _executor(algorithm)(TSP, _native_params(algorithm), seed=1, run_idx=0)
    fixed_row, native_row = dataclasses.asdict(fixed), dataclasses.asdict(native)
    assert assert_single_pooling_group([fixed_row, copy.deepcopy(fixed_row)]) == "fixed_budget"
    assert assert_single_pooling_group([native_row]) == "native"
    with pytest.raises(ValueError, match="pooled"):
        assert_single_pooling_group([fixed_row, native_row])


def test_capability_labels_and_claims_name_the_final_polish_once_composition():
    for algorithm, family in ((GWO, "Grey Wolf Optimizer"), (HHO, "Harris Hawks Optimizer")):
        capability = get_algorithm_capability(algorithm)
        assert capability.label == f"{family} + 3-opt (final polish once)"
        assert {claim.composition for claim in capability.claims} == {
            CompositionKind.GLOBAL_THEN_FINAL_3OPT
        }
        assert {claim.protocol for claim in capability.claims} == {
            ExecutionProtocol.FIXED_BUDGET, ExecutionProtocol.NATIVE_TERMINATION,
        }
    assert CompositionKind.GLOBAL_THEN_FINAL_3OPT.value == "global_then_final_3opt"


@pytest.mark.parametrize("algorithm", (GWO, HHO))
def test_registered_executor_is_selectable_through_the_governed_gateway(algorithm):
    _require_numba()
    assert AlgorithmRegistry.get_executor(algorithm) is not None
    runtime = probe_runtime_backends()
    problem = ATSP
    for protocol, budget, params in (
        (ExecutionProtocol.FIXED_BUDGET, BUDGET,
         {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS,
          "global_fraction": FRACTION}),
        (ExecutionProtocol.NATIVE_TERMINATION, None,
         {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS}),
    ):
        result, decision = execute_preflighted(
            requested_algorithm_id=algorithm,
            identifier_source=IdentifierSource.MANIFEST,
            problem=problem, params=params,
            seed=governed_contract_seed(protocol, budget, BASE_SEED, problem.name, 0),
            run_idx=0, protocol=protocol,
            backend_policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE,
            evaluation_budget=budget,
            registered_algorithm_ids=frozenset(AlgorithmRegistry.list_algorithms()),
            runtime_backends=runtime,
            registry_getter=AlgorithmRegistry.get_executor,
            comparison_base_seed=BASE_SEED,
        )
        assert decision.selected_claim.composition is CompositionKind.GLOBAL_THEN_FINAL_3OPT
        assert decision.selected_backend == PROFILE
        if protocol is ExecutionProtocol.NATIVE_TERMINATION:
            assert result.termination_reason == "composite_complete"


def _gateway_run(algorithm, tamper, protocol, budget, params):
    runtime = probe_runtime_backends()
    inner = AlgorithmRegistry.get_executor(algorithm)

    def getter(_registry_id):
        def run(problem, run_params, seed, run_idx):
            result = inner(problem, run_params, seed, run_idx)
            tamper(result)
            return result
        return run

    return execute_preflighted(
        requested_algorithm_id=algorithm,
        identifier_source=IdentifierSource.MANIFEST,
        problem=TSP, params=params,
        seed=governed_contract_seed(protocol, budget, BASE_SEED, TSP.name, 0),
        run_idx=0, protocol=protocol,
        backend_policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE,
        evaluation_budget=budget,
        registered_algorithm_ids=frozenset(AlgorithmRegistry.list_algorithms()),
        runtime_backends=runtime, registry_getter=getter,
        comparison_base_seed=BASE_SEED,
    )


@pytest.mark.parametrize("algorithm", (GWO, HHO))
def test_gateway_postflight_rejects_forged_composite_rows(algorithm):
    _require_numba()
    fixed = {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS,
             "global_fraction": FRACTION}
    native = {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS}

    def unsum(result):
        result.composition["stages"][1]["consumed_evaluations"] += 1

    def native_reason(result):
        result.termination_reason = "max_iterations"

    def fixed_composite_complete(result):
        result.termination_reason = "composite_complete"
        result.budget_terminated = False

    for tamper, protocol, budget, params in (
        (unsum, ExecutionProtocol.FIXED_BUDGET, BUDGET, fixed),
        (unsum, ExecutionProtocol.NATIVE_TERMINATION, None, native),
        (native_reason, ExecutionProtocol.NATIVE_TERMINATION, None, native),
        (fixed_composite_complete, ExecutionProtocol.FIXED_BUDGET, BUDGET, fixed),
    ):
        with pytest.raises(ResultContractViolation):
            _gateway_run(algorithm, tamper, protocol, budget, params)


def test_pure_native_row_cannot_borrow_composite_complete_at_the_gateway():
    _require_numba()
    params = {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 99}

    def borrow(result):
        result.termination_reason = "composite_complete"

    runtime = probe_runtime_backends()
    inner = AlgorithmRegistry.get_executor("Core-GWO-TSP-Pure")

    def getter(_registry_id):
        def run(problem, run_params, seed, run_idx):
            result = inner(problem, run_params, seed, run_idx)
            borrow(result)
            return result
        return run

    with pytest.raises(ResultContractViolation, match="composite"):
        execute_preflighted(
            requested_algorithm_id="Core-GWO-TSP-Pure",
            identifier_source=IdentifierSource.MANIFEST,
            problem=TSP, params=params,
            seed=governed_contract_seed(
                ExecutionProtocol.NATIVE_TERMINATION, None, BASE_SEED, TSP.name, 0),
            run_idx=0, protocol=ExecutionProtocol.NATIVE_TERMINATION,
            backend_policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE,
            evaluation_budget=None,
            registered_algorithm_ids=frozenset(AlgorithmRegistry.list_algorithms()),
            runtime_backends=runtime, registry_getter=getter,
            comparison_base_seed=BASE_SEED,
        )
