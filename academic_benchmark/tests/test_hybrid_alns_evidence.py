"""C-09 evidence: GWO/HHO + final ALNS hybrids (``global_then_final_alns``).

Each ``test_core_*_memetic_alns_*`` function below is cited by the capability claims as
executable evidence and must pass on its own. IDs stay ``Core-GWO-TSP-Memetic-ALNS`` and
``Core-HHO-TSP-Memetic-ALNS`` (owner decision Q5); the composition kind and the label say
that the ALNS polish runs once, after the global stage. The tests also hold the boundary
triplet of the global cap, the derived polish seed, the single pooling group check and the
per-stage runtimes (design native rule 4) for both composite kinds.
"""
from __future__ import annotations

import copy
import dataclasses
import math
from dataclasses import dataclass

import pytest

from academic_benchmark import fairness as fairness_module
from academic_benchmark.core import registry_setup
from academic_benchmark.core.algorithm_errors import ResultContractViolation
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.execution_gateway import (
    execute_preflighted,
    governed_contract_seed,
)
from academic_benchmark.core.preflight import probe_runtime_backends
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fairness import (
    FairComparisonManifest,
    FairnessValidationError,
    validate_scientific_alns_params,
    validate_scientific_hybrid_alns_params,
)
from academic_benchmark.native_protocol import NativeComparisonManifest
from academic_benchmark.protocol_registry import assert_single_pooling_group
from uniride_core.algorithms import composition as composition_module
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
from uniride_core.algorithms.composition import (
    CompositionError,
    derive_polish_seed,
    global_stage_cap,
)

BASE_SEED = 611
FAIR_VERSION = "uniride-fair-tsp-v2"
NATIVE_VERSION = "uniride-native-tsp-v1"
GWO = "Core-GWO-TSP-Memetic-ALNS"
HHO = "Core-HHO-TSP-Memetic-ALNS"
ALGORITHMS = (GWO, HHO)
KIND = "global_then_final_alns"
EVIDENCE_FILE = "academic_benchmark/tests/test_hybrid_alns_evidence.py::"
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
POLISH_PARAMS = {
    "max_iterations": 12, "max_no_improvement": 99, "remove_ratio": 0.3, "min_remove": 2,
    "segment_length": 5, "weight_update_factor": 0.8, "use_sa": True,
    "sa_start_temp": 10.0, "sa_cooling_rate": 0.99,
}
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


TSP = _Problem("hybrid-alns-evidence-tsp-7", "tsp", SYMMETRIC_7)
ATSP = _Problem("hybrid-alns-evidence-atsp-7", "atsp", ASYMMETRIC_7)
PROBLEMS = (TSP, ATSP)


def _require_numba() -> None:
    availability = probe_runtime_backends()
    assert availability.numba_nopython, availability.detail


def _closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    route = [node - 1 for node in tour]
    return sum(
        float(matrix[node][route[(i + 1) % len(route)]]) for i, node in enumerate(route)
    )


def _fixed_params(algorithm: str, budget: int = BUDGET, fraction: float = FRACTION,
                  polish: dict | None = None) -> dict:
    return {
        "global": dict(GLOBAL_PARAMS[algorithm]),
        "polish": dict(polish or POLISH_PARAMS),
        "global_fraction": fraction,
        "fair_comparison": {
            "evaluation_budget": budget, "base_seed": BASE_SEED,
            "protocol_version": FAIR_VERSION,
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
    return registry_setup._make_hybrid_executor(algorithm)


def _run_fixed(algorithm, budget, fraction, problem=TSP, run_idx=0, polish=None):
    return _executor(algorithm)(
        problem, _fixed_params(algorithm, budget, fraction, polish), seed=1, run_idx=run_idx
    )


def _run_native(algorithm, problem=TSP, run_idx=0):
    return _executor(algorithm)(problem, _native_params(algorithm), seed=1, run_idx=run_idx)


def _stages(result):
    global_stage, polish_stage = result.composition["stages"]
    assert (global_stage["name"], polish_stage["name"]) == ("global", "polish")
    return global_stage, polish_stage


def _fixed_manifest(budget: int) -> FairComparisonManifest:
    return FairComparisonManifest(
        evaluation_budget=budget, base_seed=BASE_SEED, protocol_version=FAIR_VERSION,
        comparison_regime="fixed_evaluation_budget",
    )


def _without_timing(composition: dict) -> dict:
    """Stage records minus the wall times, which differ between two identical runs."""
    record = copy.deepcopy(composition)
    for stage in record["stages"]:
        stage.pop("elapsed_sec")
    return record


def _assert_common(result, problem, algorithm, *, native: bool) -> None:
    assert sorted(result.tour) == list(range(1, problem.dimension + 1))
    independent = _closed_cost(result.tour, problem.dist_matrix)
    assert result.tour_cost == pytest.approx(independent)
    assert result.objective_cost == pytest.approx(independent)
    assert result.algorithm == result.algorithm_id == algorithm
    assert result.variant == KIND
    assert result.execution_backend == BACKEND_LABEL
    global_stage, polish_stage = _stages(result)
    assert (global_stage["stage_id"], polish_stage["stage_id"]) == (
        algorithm.replace("Memetic-ALNS", "Pure"), "ALNS-TSP",
    )
    assert global_stage["seed"] == result.seed
    version = NATIVE_VERSION if native else FAIR_VERSION
    assert polish_stage["seed"] == derive_polish_seed(version, result.seed)
    assert polish_stage["seed"] not in (result.seed, BASE_SEED)
    assert polish_stage["parameters"] == POLISH_PARAMS
    assert result.evaluations == result.objective_evaluations == (
        global_stage["consumed_evaluations"] + polish_stage["consumed_evaluations"]
    )
    assert result.composition["kind"] == KIND
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
    # the polish never makes the tour worse; the flag says whether it changed
    assert result.tour_cost <= global_stage["details"]["cost"] + 1e-9
    assert polish_stage["details"]["polish_changed_tour"] is result.composition[
        "polish_changed_tour"
    ]


def _prove(algorithm: str, *, native: bool) -> None:
    _require_numba()
    for problem in PROBLEMS:
        params = _native_params(algorithm) if native else _fixed_params(algorithm)
        first = _executor(algorithm)(problem, params, seed=9, run_idx=0)
        replay = _executor(algorithm)(problem, params, seed=77, run_idx=0)
        manifest = (
            NativeComparisonManifest.from_value(params["native_comparison"]) if native
            else FairComparisonManifest.from_value(params["fair_comparison"])
        )
        assert first.seed == manifest.paired_seed(problem.name, 0)
        _assert_common(first, problem, algorithm, native=native)
        manifest.validate_result(first)
        # deterministic replay: tour, cost, counts and every stage record but the wall times
        assert (replay.tour, replay.tour_cost, replay.evaluations) == (
            first.tour, first.tour_cost, first.evaluations,
        )
        assert _without_timing(replay.composition) == _without_timing(first.composition)


def _assert_claims_published(algorithm: str, protocol: ExecutionProtocol, function: str) -> None:
    capability = get_algorithm_capability(algorithm)
    assert capability is not None
    assert capability.lifecycle is LifecycleStatus.VERIFIED
    assert "final polish once" in capability.label
    for problem in (ProblemContract.TSP, ProblemContract.ATSP):
        claim = find_capability_claim(
            algorithm, problem=problem, protocol=protocol, backend_profile=PROFILE,
            composition=CompositionKind.GLOBAL_THEN_FINAL_ALNS,
        )
        assert claim is not None, (algorithm, problem, protocol)
        assert claim.directed_cost_preserved is (problem is ProblemContract.ATSP)
        assert claim.exact_objective_accounting is True
        assert claim.fixed_seed_deterministic is True
        assert claim.truthful_result_reporting is True
        assert claim.evidence_ids == (EVIDENCE_FILE + function,)


# ---- the four evidence nodes cited by the claims ---------------------------

def test_core_gwo_memetic_alns_fixed_tsp_and_atsp_evidence() -> None:
    _prove(GWO, native=False)
    _assert_claims_published(GWO, ExecutionProtocol.FIXED_BUDGET,
                             "test_core_gwo_memetic_alns_fixed_tsp_and_atsp_evidence")


def test_core_hho_memetic_alns_fixed_tsp_and_atsp_evidence() -> None:
    _prove(HHO, native=False)
    _assert_claims_published(HHO, ExecutionProtocol.FIXED_BUDGET,
                             "test_core_hho_memetic_alns_fixed_tsp_and_atsp_evidence")


def test_core_gwo_memetic_alns_native_tsp_and_atsp_evidence() -> None:
    _prove(GWO, native=True)
    _assert_claims_published(GWO, ExecutionProtocol.NATIVE_TERMINATION,
                             "test_core_gwo_memetic_alns_native_tsp_and_atsp_evidence")


def test_core_hho_memetic_alns_native_tsp_and_atsp_evidence() -> None:
    _prove(HHO, native=True)
    _assert_claims_published(HHO, ExecutionProtocol.NATIVE_TERMINATION,
                             "test_core_hho_memetic_alns_native_tsp_and_atsp_evidence")


# ---- derived polish seed ---------------------------------------------------

@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_polish_seed_is_derived_from_the_manifest_version_and_the_per_run_seed(algorithm):
    _require_numba()
    for run_idx in (0, 1, 2):
        row = _run_fixed(algorithm, BUDGET, FRACTION, run_idx=run_idx)
        _g, polish = _stages(row)
        manifest = _fixed_manifest(BUDGET)
        assert row.seed == manifest.paired_seed(TSP.name, run_idx)
        assert polish["seed"] == derive_polish_seed(manifest.protocol_version, row.seed)
        details = polish["details"]
        assert details["derived_seed"] == polish["seed"]
        assert details["run_seed"] == row.seed != BASE_SEED
        assert details["protocol_version"] == FAIR_VERSION
        assert polish["seed"] != derive_polish_seed(manifest.protocol_version, BASE_SEED)
    native = _run_native(algorithm)
    assert _stages(native)[1]["seed"] == derive_polish_seed(NATIVE_VERSION, native.seed)
    assert _stages(native)[1]["details"]["protocol_version"] == NATIVE_VERSION
    # a different run replicate gets a different polish seed (the stage is stochastic)
    assert (
        _stages(_run_fixed(algorithm, BUDGET, FRACTION, run_idx=0))[1]["seed"]
        != _stages(_run_fixed(algorithm, BUDGET, FRACTION, run_idx=1))[1]["seed"]
    )


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_a_polish_seed_derived_from_the_base_seed_or_the_wrong_version_is_rejected(algorithm):
    _require_numba()
    row = _run_fixed(algorithm, BUDGET, FRACTION)
    manifest = _fixed_manifest(BUDGET)
    manifest.validate_result(row)
    for wrong in (
        derive_polish_seed(FAIR_VERSION, BASE_SEED),     # base seed instead of the run seed
        derive_polish_seed(NATIVE_VERSION, row.seed),    # another protocol version
        None,                                            # an ALNS polish always has a seed
    ):
        forged = copy.deepcopy(row)
        forged.composition["stages"][1]["seed"] = wrong
        with pytest.raises(FairnessValidationError, match="polish seed"):
            manifest.validate_result(forged)


# ---- boundaries of the global cap and the polish budget --------------------

def _completes_naturally(algorithm: str, cap: int, natural: int) -> bool:
    """Run with B = 2 * cap, f = 0.5 (so the global cap is exactly ``cap``)."""
    try:
        result = _run_fixed(algorithm, 2 * cap, 0.5)
    except CompositionError:
        return False  # the cap does not even fit the atomic initialization
    return _stages(result)[0]["consumed_evaluations"] == natural


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_global_cap_boundary_triplet_through_the_real_executor(algorithm):
    """Cap one below / exactly at / one above the smallest cap the global stage completes in."""
    _require_numba()
    unlimited = _run_fixed(algorithm, 100_000, 0.5)
    natural = _stages(unlimited)[0]["consumed_evaluations"]
    assert _stages(unlimited)[0]["termination_reason"] == "max_iterations"
    assert natural > 4  # more than one atomic phase, so one-below really bites
    boundary = next(
        cap for cap in range(natural, 4 * natural) if _completes_naturally(algorithm, cap, natural)
    )
    assert not _completes_naturally(algorithm, boundary - 1, natural)

    below_budget, below = 2 * (boundary - 1), None
    try:
        below = _run_fixed(algorithm, below_budget, 0.5)
    except CompositionError:
        pass  # below the atomic initialization upper bound: the run is refused outright
    at_budget, at = 2 * boundary, _run_fixed(algorithm, 2 * boundary, 0.5)
    above_budget, above = 2 * (boundary + 1), _run_fixed(algorithm, 2 * (boundary + 1), 0.5)

    for result, cap in ((at, boundary), (above, boundary + 1)):
        g, _p = _stages(result)
        assert g["allocated_evaluations"] == cap
        assert g["consumed_evaluations"] == natural
        assert g["termination_reason"] == "max_iterations"
        assert g["details"]["stage_ceiling_reached"] is False
    if below is not None:
        g, _p = _stages(below)
        assert g["allocated_evaluations"] == boundary - 1
        assert g["consumed_evaluations"] < natural  # the last atomic phase is refused
        assert g["termination_reason"] == "evaluation_budget_exhausted"
        assert g["details"]["stage_ceiling_reached"] is True
    for result, budget in ((below, below_budget), (at, at_budget), (above, above_budget)):
        if result is None:
            continue
        g, p = _stages(result)
        assert result.evaluations == result.objective_evaluations
        assert result.evaluations == g["consumed_evaluations"] + p["consumed_evaluations"]
        assert result.evaluations <= budget
        # polish gets B - used_global; ALNS spends one evaluation per iteration and the
        # incoming tour is not re-counted
        assert p["allocated_evaluations"] == budget - g["consumed_evaluations"]
        assert p["consumed_evaluations"] == p["iterations"] <= p["allocated_evaluations"]
        assert result.evaluation_budget == budget
        # the row reason is the polish stage's, never the global ceiling's
        assert result.termination_reason == p["termination_reason"]
        assert result.budget_terminated is (
            result.termination_reason == "evaluation_budget_exhausted"
        )
        _fixed_manifest(budget).validate_result(result)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_polish_cut_by_the_total_budget_reports_exhaustion_and_fills_the_budget(algorithm):
    _require_numba()
    natural = _run_fixed(algorithm, 100_000, 0.5).evaluations
    seen = {}
    for budget in range(2, natural + 2):
        try:
            result = _run_fixed(algorithm, budget, 0.5)
        except CompositionError:
            continue  # cap below the atomic initialization: the run is refused
        seen.setdefault(result.termination_reason, result)
        assert result.evaluations <= budget
        assert result.budget_terminated is (
            result.termination_reason == "evaluation_budget_exhausted"
        )
        _fixed_manifest(budget).validate_result(result)
    exhausted = seen["evaluation_budget_exhausted"]
    assert exhausted.budget_terminated is True
    assert exhausted.evaluations == exhausted.evaluation_budget
    assert "max_iterations" in seen


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_polish_stagnation_is_a_valid_fixed_and_native_polish_reason(algorithm):
    _require_numba()
    polish = dict(POLISH_PARAMS, max_no_improvement=1, max_iterations=500)
    row = _run_fixed(algorithm, 5_000, 0.5, polish=polish)
    assert _stages(row)[1]["termination_reason"] == "stagnation_limit"
    assert row.termination_reason == "stagnation_limit"
    _fixed_manifest(5_000).validate_result(row)
    native_params = _native_params(algorithm)
    native_params["polish"] = dict(polish)
    native = _executor(algorithm)(TSP, native_params, seed=1, run_idx=0)
    assert _stages(native)[1]["termination_reason"] == "stagnation_limit"
    assert native.termination_reason == "composite_complete"
    NativeComparisonManifest(base_seed=BASE_SEED).validate_result(native)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_validator_uses_global_stage_cap_not_float_arithmetic(algorithm):
    _require_numba()
    fraction = 1 / 3
    assert global_stage_cap(30_000, fraction) == 9_999
    result = _run_fixed(algorithm, 30_000, fraction)
    assert _stages(result)[0]["allocated_evaluations"] == 9_999
    _fixed_manifest(30_000).validate_result(result)
    forged = copy.deepcopy(result)
    forged.composition["stages"][0]["allocated_evaluations"] = 10_000
    with pytest.raises(FairnessValidationError, match="global stage allocation"):
        _fixed_manifest(30_000).validate_result(forged)


# ---- directed costs, pooling, forged rows ----------------------------------

@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_atsp_directed_cost_is_preserved_with_an_independent_closed_cycle_cost(algorithm):
    _require_numba()
    reverse = _Problem("reverse", "atsp", [list(col) for col in zip(*ASYMMETRIC_7)])
    result = _run_fixed(algorithm, BUDGET, FRACTION, problem=ATSP)
    independent = _closed_cost(result.tour, ASYMMETRIC_7)
    assert independent != pytest.approx(_closed_cost(result.tour, reverse.dist_matrix))
    assert math.isclose(result.tour_cost, independent, rel_tol=1e-9)
    polish = _stages(result)[1]
    assert polish["details"]["cost"] == pytest.approx(independent)
    assert result.matrix_kind == "distance"
    # the polish ran on the directed matrix: replaying it on the transposed matrix is another run
    transposed = _run_fixed(algorithm, BUDGET, FRACTION, problem=reverse)
    assert _closed_cost(transposed.tour, reverse.dist_matrix) == pytest.approx(
        transposed.tour_cost
    )


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_fixed_and_native_composite_rows_fail_the_single_pooling_group_check(algorithm):
    _require_numba()
    fixed = _run_fixed(algorithm, BUDGET, FRACTION)
    native = _run_native(algorithm)
    fixed_row, native_row = dataclasses.asdict(fixed), dataclasses.asdict(native)
    assert assert_single_pooling_group([fixed_row, copy.deepcopy(fixed_row)]) == "fixed_budget"
    assert assert_single_pooling_group([native_row]) == "native"
    with pytest.raises(ValueError, match="pooled"):
        assert_single_pooling_group([fixed_row, native_row])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_forged_composite_rows_are_rejected_by_the_manifest_validators(algorithm):
    _require_numba()
    fixed, native = _run_fixed(algorithm, BUDGET, FRACTION), _run_native(algorithm)
    fixed_manifest, native_manifest = _fixed_manifest(BUDGET), NativeComparisonManifest(
        base_seed=BASE_SEED
    )

    def stage_id(row):
        row.composition["stages"][1]["stage_id"] = "Core-ThreeOpt-TSP"

    def hidden_key(row):
        del row.composition["stages"][1]["parameters"]["use_sa"]

    def extra_key(row):
        row.composition["stages"][1]["parameters"]["polish_iters"] = 3

    def no_move_reason(row):  # ALNS never stops for lack of an improving move
        row.composition["stages"][1]["termination_reason"] = "no_improving_move"

    def operator(row):
        row.polish_policy["operator"] = "3-opt"

    for tamper in (stage_id, hidden_key, extra_key, no_move_reason, operator):
        for manifest, row in ((fixed_manifest, fixed), (native_manifest, native)):
            forged = copy.deepcopy(row)
            tamper(forged)
            with pytest.raises(FairnessValidationError):
                manifest.validate_result(forged)


def test_capability_labels_and_claims_name_the_final_polish_once_composition():
    for algorithm, family in ((GWO, "Grey Wolf Optimizer"), (HHO, "Harris Hawks Optimizer")):
        capability = get_algorithm_capability(algorithm)
        assert capability.label == f"{family} + ALNS (final polish once)"
        assert {claim.composition for claim in capability.claims} == {
            CompositionKind.GLOBAL_THEN_FINAL_ALNS
        }
        assert {claim.protocol for claim in capability.claims} == {
            ExecutionProtocol.FIXED_BUDGET, ExecutionProtocol.NATIVE_TERMINATION,
        }
    assert CompositionKind.GLOBAL_THEN_FINAL_ALNS.value == KIND


# ---- per-stage runtime (design native rule 4), both composite kinds ----------

@pytest.mark.parametrize("algorithm", (
    GWO, HHO, "Core-GWO-TSP-Memetic-3opt", "Core-HHO-TSP-Memetic-3opt",
))
def test_every_composite_row_carries_a_non_negative_wall_time_per_stage(algorithm):
    _require_numba()
    alns = algorithm.endswith("ALNS")
    for native in (False, True):
        params = _native_params(algorithm) if native else _fixed_params(algorithm)
        if not alns:
            params["polish"] = {"max_iterations": 6, "first_improvement": False, "window": 5}
        row = _executor(algorithm)(TSP, params, seed=1, run_idx=0)
        stages = row.composition["stages"]
        times = [stage["elapsed_sec"] for stage in stages]
        assert all(isinstance(t, float) and math.isfinite(t) and t >= 0 for t in times)
        assert sum(times) <= row.elapsed_sec + 1e-3  # the row total stays as it was
        manifest = (
            NativeComparisonManifest(base_seed=BASE_SEED) if native else _fixed_manifest(BUDGET)
        )
        manifest.validate_result(row)
        for bad in (None, -0.5, True, float("nan"), "0.1"):
            forged = copy.deepcopy(row)
            forged.composition["stages"][0]["elapsed_sec"] = bad
            with pytest.raises(FairnessValidationError, match="elapsed_sec"):
                manifest.validate_result(forged)
        forged = copy.deepcopy(row)
        del forged.composition["stages"][1]["elapsed_sec"]
        with pytest.raises(FairnessValidationError, match="elapsed_sec"):
            manifest.validate_result(forged)


# ---- one rule set for the ALNS parameters (fairness imports the core's) -----

def test_fairness_uses_the_core_alns_constants_and_delegates_value_checks(monkeypatch):
    assert fairness_module.ALNS_REQUIRED_PARAMS is composition_module.ALNS_REQUIRED_PARAMS
    assert fairness_module.ALNS_OPTIONAL_PARAMS is composition_module.ALNS_OPTIONAL_PARAMS
    assert fairness_module.SWARM_REQUIRED_PARAMS is composition_module.SWARM_REQUIRED_PARAMS
    # the old private name keeps working as an alias
    assert composition_module._SWARM_REQUIRED is composition_module.SWARM_REQUIRED_PARAMS

    def refuse(params, *, strict=True):
        raise CompositionError("invalid ALNS polish parameter: delegated")

    monkeypatch.setattr(fairness_module, "validate_alns_polish_params", refuse)
    with pytest.raises(ValueError, match="delegated"):
        validate_scientific_alns_params(dict(POLISH_PARAMS))
    with pytest.raises(ValueError, match="delegated"):
        validate_scientific_hybrid_alns_params(
            "GWO",
            {"global": GLOBAL_PARAMS[GWO], "polish": POLISH_PARAMS, "global_fraction": 0.5},
            fixed_budget=True,
        )


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_hybrid_alns_parameter_schema_is_strict(algorithm):
    family = "GWO" if algorithm == GWO else "HHO"
    good = {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS, "global_fraction": 0.5}
    assert validate_scientific_hybrid_alns_params(family, good, fixed_budget=True) == good
    native = {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS}
    assert validate_scientific_hybrid_alns_params(family, native, fixed_budget=False) == native

    def broken(**changes):
        params = copy.deepcopy(good)
        for key, value in changes.items():
            if value is None:
                del params[key]
            else:
                params[key] = value
        return params

    cases = (
        (broken(global_fraction=None), True, "global_fraction"),
        (broken(global_fraction=1.0), True, "global_fraction"),
        (good, False, "global_fraction"),  # native runs take no fraction
        (broken(polish={**POLISH_PARAMS, "surprise": 1}), True, "polish"),
        (broken(polish={k: v for k, v in POLISH_PARAMS.items() if k != "remove_ratio"}), True, "polish"),
        (broken(polish={**POLISH_PARAMS, "remove_ratio": 0.0}), True, "remove_ratio"),
        (broken(polish={**POLISH_PARAMS, "use_sa": 1}), True, "use_sa"),
        (broken(polish={"max_iterations": 6, "first_improvement": False, "window": 5}), True, "polish"),
        (broken(**{"global": {**GLOBAL_PARAMS[algorithm], "polish_iters": 2}}), True, "global"),
    )
    for params, fixed, text in cases:
        with pytest.raises(ValueError, match=text):
            validate_scientific_hybrid_alns_params(family, params, fixed_budget=fixed)


# ---- governed gateway -------------------------------------------------------

@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_registered_executor_is_selectable_through_the_governed_gateway(algorithm):
    _require_numba()
    assert AlgorithmRegistry.get_executor(algorithm) is not None
    runtime = probe_runtime_backends()
    for problem in PROBLEMS:
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
            assert decision.selected_claim.composition is CompositionKind.GLOBAL_THEN_FINAL_ALNS
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


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_gateway_postflight_rejects_forged_composite_rows(algorithm):
    _require_numba()
    fixed = {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS,
             "global_fraction": FRACTION}
    native = {"global": GLOBAL_PARAMS[algorithm], "polish": POLISH_PARAMS}

    def unsum(result):
        result.composition["stages"][1]["consumed_evaluations"] += 1

    def base_seed_polish(result):
        result.composition["stages"][1]["seed"] = derive_polish_seed(FAIR_VERSION, BASE_SEED)

    def native_reason(result):
        result.termination_reason = "max_iterations"

    def fixed_composite_complete(result):
        result.termination_reason = "composite_complete"
        result.budget_terminated = False

    def no_runtime(result):
        del result.composition["stages"][0]["elapsed_sec"]

    for tamper, protocol, budget, params in (
        (unsum, ExecutionProtocol.FIXED_BUDGET, BUDGET, fixed),
        (unsum, ExecutionProtocol.NATIVE_TERMINATION, None, native),
        (base_seed_polish, ExecutionProtocol.FIXED_BUDGET, BUDGET, fixed),
        (native_reason, ExecutionProtocol.NATIVE_TERMINATION, None, native),
        (fixed_composite_complete, ExecutionProtocol.FIXED_BUDGET, BUDGET, fixed),
        (no_runtime, ExecutionProtocol.FIXED_BUDGET, BUDGET, fixed),
    ):
        with pytest.raises(ResultContractViolation):
            _gateway_run(algorithm, tamper, protocol, budget, params)
