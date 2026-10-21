"""C-08: budget boundaries and composite-row validation of the GWO/HHO + final 3-opt hybrids.

The executors run ``uniride_core.algorithms.composition.run_composition`` with the pure
global stage (``swarm_global_stage``) and the one canonical 3-opt polish stage
(``three_opt_polish_stage``) on one shared objective counter. The global cap is
``global_stage_cap(B, f)`` and nothing else; a composite row is validated against that
same function, never against its own float arithmetic.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import pytest

from academic_benchmark.core import registry_setup
from academic_benchmark.fairness import (
    FairComparisonManifest,
    FairnessValidationError,
)
from academic_benchmark.native_protocol import NativeComparisonManifest
from uniride_core.algorithms.composition import global_stage_cap

BASE_SEED = 417
KIND = "global_then_final_3opt"

GLOBAL_PARAMS = {
    "Core-GWO-TSP-Memetic-3opt": {
        "pack_size": 4, "max_iterations": 3, "initial_a": 2.0,
        "exploration_rate": 0.4, "max_no_improvement": 99,
    },
    "Core-HHO-TSP-Memetic-3opt": {
        "hawks": 4, "max_iterations": 3, "initial_energy": 1.0,
        "jump_probability": 0.0, "max_no_improvement": 99, "dive_count": 0,
        "levy_scale": 0.3,
    },
}
POLISH_PARAMS = {"max_iterations": 5, "first_improvement": False, "window": 4}
ALGORITHMS = tuple(GLOBAL_PARAMS)

SYMMETRIC_7 = [
    [0.0, 4.0, 8.0, 7.0, 3.0, 6.0, 5.0],
    [4.0, 0.0, 5.0, 9.0, 6.0, 4.0, 7.0],
    [8.0, 5.0, 0.0, 2.0, 7.0, 3.0, 6.0],
    [7.0, 9.0, 2.0, 0.0, 4.0, 5.0, 8.0],
    [3.0, 6.0, 7.0, 4.0, 0.0, 8.0, 2.0],
    [6.0, 4.0, 3.0, 5.0, 8.0, 0.0, 9.0],
    [5.0, 7.0, 6.0, 8.0, 2.0, 9.0, 0.0],
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


PROBLEM = _Problem("hybrid-boundary-sym-7", "tsp", SYMMETRIC_7)


def _require_numba() -> None:
    from academic_benchmark.core.preflight import probe_runtime_backends

    availability = probe_runtime_backends()
    assert availability.numba_nopython, availability.detail


def _fixed_params(algorithm: str, budget: int, fraction: float) -> dict:
    return {
        "global": dict(GLOBAL_PARAMS[algorithm]),
        "polish": dict(POLISH_PARAMS),
        "global_fraction": fraction,
        "fair_comparison": {
            "evaluation_budget": budget,
            "base_seed": BASE_SEED,
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


def _run_fixed(algorithm, budget, fraction, problem=PROBLEM, run_idx=0):
    return _executor(algorithm)(
        problem, _fixed_params(algorithm, budget, fraction), seed=1, run_idx=run_idx
    )


def _run_native(algorithm, problem=PROBLEM, run_idx=0):
    return _executor(algorithm)(problem, _native_params(algorithm), seed=1, run_idx=run_idx)


def _stages(result):
    global_stage, polish_stage = result.composition["stages"]
    assert (global_stage["name"], polish_stage["name"]) == ("global", "polish")
    return global_stage, polish_stage


def _fixed_manifest(budget: int) -> FairComparisonManifest:
    return FairComparisonManifest(
        evaluation_budget=budget, base_seed=BASE_SEED,
        protocol_version="uniride-fair-tsp-v2",
        comparison_regime="fixed_evaluation_budget",
    )


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_global_cap_boundary_triplet_through_the_real_executor(algorithm):
    """Cap one below / exactly at / one above the global stage's natural spend G."""
    _require_numba()
    unlimited = _run_fixed(algorithm, 100_000, 0.5)
    global_natural = _stages(unlimited)[0]["consumed_evaluations"]
    assert _stages(unlimited)[0]["termination_reason"] == "max_iterations"
    assert global_natural > 4  # more than one atomic phase, so one-below really bites

    below = _run_fixed(algorithm, 2 * global_natural - 2, 0.5)  # cap = G - 1
    at = _run_fixed(algorithm, 2 * global_natural, 0.5)  # cap = G
    above = _run_fixed(algorithm, 2 * global_natural + 2, 0.5)  # cap = G + 1

    g_below, p_below = _stages(below)
    g_at, p_at = _stages(at)
    g_above, p_above = _stages(above)

    assert g_below["allocated_evaluations"] == global_natural - 1
    assert g_at["allocated_evaluations"] == global_natural
    assert g_above["allocated_evaluations"] == global_natural + 1
    # one below: the last atomic phase is refused; the stage's own ceiling stop stays
    # in the global record
    assert g_below["consumed_evaluations"] < global_natural
    assert g_below["consumed_evaluations"] <= g_below["allocated_evaluations"]
    assert g_below["termination_reason"] == "evaluation_budget_exhausted"
    assert g_below["details"]["stage_ceiling_reached"] is True
    # exactly at / one above: the stage completes on its own
    for g in (g_at, g_above):
        assert g["consumed_evaluations"] == global_natural
        assert g["termination_reason"] == "max_iterations"
        assert g["details"]["stage_ceiling_reached"] is False
    for result, budget, g, p in (
        (below, 2 * global_natural - 2, g_below, p_below),
        (at, 2 * global_natural, g_at, p_at),
        (above, 2 * global_natural + 2, g_above, p_above),
    ):
        assert result.evaluations == result.objective_evaluations
        assert result.evaluations == g["consumed_evaluations"] + p["consumed_evaluations"]
        assert result.evaluations <= budget
        assert p["allocated_evaluations"] == budget - g["consumed_evaluations"]
        assert p["consumed_evaluations"] <= p["allocated_evaluations"]
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
    unlimited = _run_fixed(algorithm, 100_000, 0.5)
    natural = unlimited.evaluations
    seen = {}
    for budget in range(2, natural + 2):
        try:
            result = _run_fixed(algorithm, budget, 0.5)
        except ValueError:
            continue  # cap below one unit: the engine refuses to start
        seen.setdefault(result.termination_reason, result)
        assert result.evaluations <= budget
        assert result.budget_terminated is (
            result.termination_reason == "evaluation_budget_exhausted"
        )
    exhausted = seen["evaluation_budget_exhausted"]
    assert exhausted.budget_terminated is True
    assert exhausted.evaluations == exhausted.evaluation_budget
    assert {"no_improving_move", "max_iterations"} & set(seen)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_validator_uses_global_stage_cap_not_float_arithmetic(algorithm):
    """floor(30000 * 0.3333333333333333) is 9999 by the shared rule, 10000 in floats."""
    _require_numba()
    fraction = 1 / 3
    assert global_stage_cap(30_000, fraction) == 9_999
    assert int(30_000 * fraction) == 10_000  # why the validator must not do this itself
    result = _run_fixed(algorithm, 30_000, fraction)
    assert _stages(result)[0]["allocated_evaluations"] == 9_999
    _fixed_manifest(30_000).validate_result(result)  # a float-arithmetic validator fails here

    forged = copy.deepcopy(result)
    forged.composition["stages"][0]["allocated_evaluations"] = 10_000
    with pytest.raises(FairnessValidationError, match="global stage allocation"):
        _fixed_manifest(30_000).validate_result(forged)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_fixed_row_with_unsummed_stage_evaluations_is_rejected(algorithm):
    _require_numba()
    result = _run_fixed(algorithm, 400, 0.5)
    forged = copy.deepcopy(result)
    forged.composition["stages"][1]["consumed_evaluations"] += 1
    with pytest.raises(FairnessValidationError, match="sum of the stage"):
        _fixed_manifest(400).validate_result(forged)

    forged = copy.deepcopy(result)
    forged.composition["stages"][0]["consumed_evaluations"] = (
        forged.composition["stages"][0]["allocated_evaluations"] + 1
    )
    with pytest.raises(FairnessValidationError, match="exceeds its allocation|sum of the stage"):
        _fixed_manifest(400).validate_result(forged)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_fixed_row_termination_and_budget_flag_follow_the_row_reason(algorithm):
    _require_numba()
    result = _run_fixed(algorithm, 400, 0.5)
    manifest = _fixed_manifest(400)
    forged = copy.deepcopy(result)
    forged.termination_reason = "composite_complete"  # native-only reason
    with pytest.raises(FairnessValidationError):
        manifest.validate_result(forged)
    forged = copy.deepcopy(result)
    forged.budget_terminated = not result.budget_terminated
    with pytest.raises(FairnessValidationError, match="budget_terminated"):
        manifest.validate_result(forged)
    # the global stage's ceiling stop must not leak into the row reason
    forged = copy.deepcopy(result)
    forged.composition["stages"][1]["termination_reason"] = "evaluation_budget_exhausted"
    forged.termination_reason = "no_improving_move"
    with pytest.raises(FairnessValidationError, match="termination_reason"):
        manifest.validate_result(forged)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_native_row_accepts_only_composite_complete(algorithm):
    _require_numba()
    result = _run_native(algorithm)
    manifest = NativeComparisonManifest(base_seed=BASE_SEED)
    assert result.termination_reason == "composite_complete"
    assert result.evaluation_budget is None and result.budget_terminated is False
    global_stage, polish_stage = _stages(result)
    assert result.evaluations == (
        global_stage["consumed_evaluations"] + polish_stage["consumed_evaluations"]
    )
    assert global_stage["allocated_evaluations"] is None
    assert polish_stage["allocated_evaluations"] is None
    manifest.validate_result(result)

    for reason in ("max_iterations", "stagnation_limit", "no_improving_move",
                   "evaluation_budget_exhausted"):
        forged = copy.deepcopy(result)
        forged.termination_reason = reason
        with pytest.raises(FairnessValidationError, match="composite"):
            manifest.validate_result(forged)

    forged = copy.deepcopy(result)
    forged.composition["stages"][1]["consumed_evaluations"] += 1
    with pytest.raises(FairnessValidationError, match="sum of the stage"):
        manifest.validate_result(forged)

    forged = copy.deepcopy(result)
    forged.composition["stages"][0]["termination_reason"] = "evaluation_budget_exhausted"
    with pytest.raises(FairnessValidationError, match="complete"):
        manifest.validate_result(forged)


def test_composite_complete_is_refused_for_non_composite_native_rows():
    _require_numba()
    from academic_benchmark.engine_core import AlgorithmRegistry

    pure = AlgorithmRegistry.get_executor("Core-GWO-TSP-Pure")(
        PROBLEM,
        {
            "pack_size": 4, "max_iterations": 2, "max_no_improvement": 99,
            "native_comparison": {"base_seed": BASE_SEED},
        },
        seed=1, run_idx=0,
    )
    manifest = NativeComparisonManifest(base_seed=BASE_SEED)
    manifest.validate_result(pure)
    pure.termination_reason = "composite_complete"
    with pytest.raises(FairnessValidationError, match="composite_complete"):
        manifest.validate_result(pure)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_executor_requires_explicit_stage_namespaces_and_rejects_hidden_polish(algorithm):
    _require_numba()
    executor = _executor(algorithm)
    base = _fixed_params(algorithm, 400, 0.5)

    missing_fraction = {k: v for k, v in base.items() if k != "global_fraction"}
    with pytest.raises(ValueError, match="global_fraction"):
        executor(PROBLEM, missing_fraction, seed=1, run_idx=0)

    hidden = copy.deepcopy(base)
    hidden["global"]["polish_iters"] = 3
    with pytest.raises(ValueError, match="polish_iters"):
        executor(PROBLEM, hidden, seed=1, run_idx=0)

    absent = copy.deepcopy(base)
    del absent["global"][next(iter(GLOBAL_PARAMS[algorithm]))]
    with pytest.raises(ValueError, match="missing"):
        executor(PROBLEM, absent, seed=1, run_idx=0)

    flat = {k: v for k, v in base.items() if k not in ("global", "polish")}
    flat.update(GLOBAL_PARAMS[algorithm])
    with pytest.raises(ValueError, match="global"):
        executor(PROBLEM, flat, seed=1, run_idx=0)

    native_with_fraction = _native_params(algorithm)
    native_with_fraction["global_fraction"] = 0.5
    with pytest.raises(ValueError, match="global_fraction"):
        executor(PROBLEM, native_with_fraction, seed=1, run_idx=0)

    outside_protocol = {k: v for k, v in base.items() if k != "fair_comparison"}
    with pytest.raises(ValueError, match="comparison"):
        executor(PROBLEM, outside_protocol, seed=1, run_idx=0)
