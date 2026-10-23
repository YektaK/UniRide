"""C-04 (audit M19): memetic-2opt labels and polish flags come from executed polish."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance

MEMETIC_IDS = ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt")
STUDY_PATH = (
    Path(__file__).resolve().parents[1] / "studies" / "bildiri2026" / "study.json"
)


def _problem() -> ProblemInstance:
    matrix = [
        [0.0 if i == j else float((i + 1) * 7 + (j + 1) * 3 + abs(i - j)) for j in range(6)]
        for i in range(6)
    ]
    return ProblemInstance(
        name="m19-tsp-6", dimension=6, coordinates=[], problem_type="tsp",
        dist_matrix=matrix, optimal=1.0,
    )


def _params(algorithm_id: str, **overrides) -> dict:
    params = {
        "fair_comparison": {"evaluation_budget": 5000, "base_seed": 41},
        "max_iterations": 2,
        "max_no_improvement": 99,
    }
    if "GWO" in algorithm_id:
        params["pack_size"] = 4
    else:
        params.update(hawks=4, dive_count=0, jump_probability=0.0)
    params.update(overrides)
    return params


def _run(algorithm_id: str, **overrides):
    executor = AlgorithmRegistry.get_executor(algorithm_id)
    return executor(_problem(), _params(algorithm_id, **overrides), seed=1, run_idx=0)


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_memetic_with_zero_polish_is_rejected_before_execution(algorithm_id):
    with pytest.raises(ValueError, match="execute no polish"):
        _run(algorithm_id, polish_iters=0, final_polish_iters=0)


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_zero_polish_is_rejected_without_a_protocol_manifest_too(algorithm_id):
    params = _params(algorithm_id, polish_iters=0, final_polish_iters=0)
    params.pop("fair_comparison")
    executor = AlgorithmRegistry.get_executor(algorithm_id)
    with pytest.raises(ValueError, match="execute no polish"):
        executor(_problem(), params, seed=1, run_idx=0)


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_polish_policy_records_executed_polish_counts(algorithm_id):
    result = _run(
        algorithm_id, polish_iters=1, final_polish_iters=1, polish_interval=1
    )
    executed = result.polish_policy["executed"]
    population = 4
    assert executed["initial"] == population
    assert executed["periodic"] == 1  # iteration 1 only (it > 0 and it % 1 == 0)
    assert executed["final"] == 1
    assert result.polish_policy["enabled"] is True
    assert result.polish_policy["initial"] is True
    assert result.polish_policy["periodic"] is True
    assert result.polish_policy["final"] is True
    assert result.polish_policy["operator"] == "2-opt"


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_periodic_flag_is_false_when_no_periodic_polish_ran(algorithm_id):
    result = _run(
        algorithm_id, polish_iters=1, final_polish_iters=1, polish_interval=1000
    )
    assert result.polish_policy["executed"]["periodic"] == 0
    assert result.polish_policy["periodic"] is False
    assert result.polish_policy["initial"] is True
    assert result.polish_policy["final"] is True
    assert result.variant == "memetic_2opt"


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_phase_with_zero_iterations_is_not_reported_as_run(algorithm_id):
    result = _run(algorithm_id, polish_iters=0, final_polish_iters=2)
    assert result.polish_policy["executed"] == {"initial": 0, "periodic": 0, "final": 1}
    assert result.polish_policy["initial"] is False
    assert result.polish_policy["final"] is True
    assert "initial_2opt" not in result.initialization_policy


@pytest.mark.parametrize("algorithm_id", ("Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"))
def test_pure_variant_reports_zero_executed_polish(algorithm_id):
    result = _run(algorithm_id)
    # Pure results keep the historical five-key shape (fixed-budget golden).
    assert result.polish_policy == {
        "enabled": False, "initial": False, "periodic": False, "final": False,
        "operator": None,
    }


def test_solvers_expose_executed_polish_counts_in_extra_stats():
    from uniride_core.algorithms.tsp_matrix_metaheuristics import GWOOptimizer, HHOOptimizer

    matrix = _problem().dist_matrix
    for solver in (
        GWOOptimizer(pack_size=4, max_iterations=2, polish_interval=1,
                     polish_iters=1, final_polish_iters=1, random_seed=3),
        HHOOptimizer(hawks=4, dive_count=0, max_iterations=2, polish_interval=1,
                     polish_iters=1, final_polish_iters=1, random_seed=3),
    ):
        stats = solver.solve_with_matrix(matrix, closed_tsp=True).extra_stats
        assert stats["polish_executed"] == {"initial": 4, "periodic": 1, "final": 1}


def test_bildiri_memetic_entries_have_nonzero_polish():
    payload = json.loads(STUDY_PATH.read_text(encoding="utf-8"))
    for algorithm_id in MEMETIC_IDS:
        params = payload["algorithm_parameters"][algorithm_id]
        assert params["polish_iters"] >= 1
        assert params["final_polish_iters"] >= 1


# ---------------------------------------------------------------------------
# DUZELT round 1: a phase counts as executed only when it spent evaluations.
# ---------------------------------------------------------------------------
from copy import deepcopy

from academic_benchmark.fairness import FairComparisonManifest, FairnessValidationError

PHASES = ("initial", "periodic", "final")


def _valid_memetic(algorithm_id: str = "Core-GWO-TSP-Memetic-2opt", **overrides):
    params = _params(
        algorithm_id, polish_iters=1, final_polish_iters=1, polish_interval=1,
        **overrides,
    )
    params["fair_comparison"] = {"evaluation_budget": 5000, "base_seed": 41}
    executor = AlgorithmRegistry.get_executor(algorithm_id)
    return (
        executor(_problem(), params, seed=1, run_idx=0),
        FairComparisonManifest.from_value(params["fair_comparison"]),
    )


@pytest.mark.parametrize(
    ("algorithm_id", "budget"),
    [("Core-GWO-TSP-Memetic-2opt", 5), ("Core-HHO-TSP-Memetic-2opt", 4)],
)
def test_memetic_run_whose_polish_spent_no_evaluation_is_rejected(algorithm_id, budget):
    """B1: the final polish was called but the budget was already spent."""
    params = _params(algorithm_id, polish_iters=0, final_polish_iters=1)
    params["fair_comparison"] = {"evaluation_budget": budget, "base_seed": 41}
    executor = AlgorithmRegistry.get_executor(algorithm_id)
    with pytest.raises(ValueError, match="must execute at least one polish phase"):
        executor(_problem(), params, seed=1, run_idx=0)


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_phase_flags_equal_polish_evaluations_across_budgets(algorithm_id):
    accepted = 0
    for budget in range(4, 120, 3):
        params = _params(algorithm_id, polish_iters=0, final_polish_iters=1)
        params["fair_comparison"] = {"evaluation_budget": budget, "base_seed": 41}
        executor = AlgorithmRegistry.get_executor(algorithm_id)
        try:
            result = executor(_problem(), params, seed=1, run_idx=0)
        except ValueError as error:
            # Only the two expected rejections may be skipped; any other error
            # (for example a flag/evaluation contradiction) must fail the sweep.
            message = str(error)
            assert (
                "cannot complete atomic population initialization" in message
                or "must execute at least one polish phase" in message
            ), (budget, message)
            continue
        accepted += 1
        policy = result.polish_policy
        evaluations = policy["evaluations"]
        for phase in PHASES:
            assert policy[phase] is (evaluations[phase] > 0), (budget, phase)
        assert sum(evaluations.values()) > 0, budget
        assert sum(evaluations.values()) <= result.objective_evaluations
    assert accepted > 0


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_polish_policy_records_polish_evaluations_per_phase(algorithm_id):
    result, _ = _valid_memetic(algorithm_id)
    evaluations = result.polish_policy["evaluations"]
    assert evaluations["initial"] > 0
    assert evaluations["periodic"] > 0
    assert evaluations["final"] > 0
    assert sum(evaluations.values()) < result.objective_evaluations


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_initial_and_periodic_polish_without_final_reports_final_false(algorithm_id):
    """P2: final_polish_iters=0 must not be reported as a final polish."""
    params = _params(algorithm_id, polish_iters=1, final_polish_iters=0, polish_interval=1)
    params["fair_comparison"] = {"evaluation_budget": 5000, "base_seed": 41}
    result = AlgorithmRegistry.get_executor(algorithm_id)(
        _problem(), params, seed=1, run_idx=0
    )
    assert result.polish_policy["final"] is False
    assert result.polish_policy["evaluations"]["final"] == 0
    assert result.polish_policy["executed"]["final"] == 0
    assert result.polish_policy["initial"] is True


def test_validator_rejects_memetic_record_without_polish_evaluations():
    result, manifest = _valid_memetic()
    manifest.validate_result(result)
    for key in ("evaluations", "executed"):
        broken = deepcopy(result)
        del broken.polish_policy[key]
        with pytest.raises(FairnessValidationError, match="polish"):
            manifest.validate_result(broken)


def test_validator_rejects_phase_flag_that_contradicts_polish_evaluations():
    result, manifest = _valid_memetic()
    manifest.validate_result(result)

    flag_without_evaluations = deepcopy(result)
    flag_without_evaluations.polish_policy["evaluations"]["final"] = 0
    with pytest.raises(FairnessValidationError, match="polish"):
        manifest.validate_result(flag_without_evaluations)

    evaluations_without_flag = deepcopy(result)
    evaluations_without_flag.polish_policy["periodic"] = False
    with pytest.raises(FairnessValidationError, match="polish"):
        manifest.validate_result(evaluations_without_flag)

    all_zero = deepcopy(result)
    all_zero.polish_policy["evaluations"] = {phase: 0 for phase in PHASES}
    all_zero.polish_policy.update(initial=False, periodic=False, final=False, enabled=False)
    with pytest.raises(FairnessValidationError, match="polish"):
        manifest.validate_result(all_zero)

    too_many = deepcopy(result)
    too_many.polish_policy["evaluations"]["final"] = result.objective_evaluations + 1
    with pytest.raises(FairnessValidationError, match="polish"):
        manifest.validate_result(too_many)


def _ft53_problem() -> ProblemInstance:
    from uniride_core.algorithms.tsplib_parser import parse_atsp_text

    path = STUDY_PATH.parents[2] / "tsplib_data" / "ft53.atsp"
    matrix = parse_atsp_text(path.read_text())["explicit_matrix"]
    return ProblemInstance(
        name="ft53", dimension=len(matrix), coordinates=[], problem_type="atsp",
        dist_matrix=matrix, optimal=6905.0,
    )


def test_bildiri_profile_runs_on_ft53_at_every_budget_level_and_spends_polish():
    """Owner decision 2026-10-19: the budget levels leave room for initial polish."""
    payload = json.loads(STUDY_PATH.read_text(encoding="utf-8"))
    problem = _ft53_problem()
    # C-19 (owner 2026-10-21): ft53 levels are 50 and 250 full 2-opt scans (1378 candidates each)
    levels = payload["scaled_fixed_budget_levels"]["levels_by_dataset"]["tsplib-ft53"]
    assert levels == [50 * 1378, 250 * 1378]
    assert min(levels) >= 5516  # 4 x (1 + 53*52/2)
    swarm_ids = [a for a in payload["algorithm_ids"] if a.startswith(("Core-GWO-", "Core-HHO-"))]
    assert len(swarm_ids) == 4
    for budget in levels:
        for algorithm_id in swarm_ids:
            params = dict(payload["algorithm_parameters"][algorithm_id])
            params["fair_comparison"] = {
                "evaluation_budget": budget, "base_seed": payload["base_seed"],
            }
            result = AlgorithmRegistry.get_executor(algorithm_id)(
                problem, params, seed=1, run_idx=0
            )
            label = (algorithm_id, budget)
            # Pure and memetic variants alike must be able to use the budget.
            assert result.termination_reason == "evaluation_budget_exhausted", label
            assert 0.99 * budget <= result.objective_evaluations <= budget, label
            if "Memetic" in algorithm_id:
                evaluations = result.polish_policy["evaluations"]
                assert evaluations["initial"] > 0, label
                assert result.polish_policy["initial"] is True, label
                for phase in PHASES:
                    assert result.polish_policy[phase] is (evaluations[phase] > 0), label
            else:
                assert result.polish_policy["enabled"] is False, label
