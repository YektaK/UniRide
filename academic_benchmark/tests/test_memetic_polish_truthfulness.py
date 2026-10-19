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


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS + ("Core-GWO-TSP", "Core-HHO-TSP"))
def test_memetic_with_zero_polish_is_rejected_before_execution(algorithm_id):
    with pytest.raises(ValueError, match="polish"):
        _run(algorithm_id, polish_iters=0, final_polish_iters=0)


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_zero_polish_is_rejected_without_a_protocol_manifest_too(algorithm_id):
    params = _params(algorithm_id, polish_iters=0, final_polish_iters=0)
    params.pop("fair_comparison")
    executor = AlgorithmRegistry.get_executor(algorithm_id)
    with pytest.raises(ValueError, match="polish"):
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
        # ft53 (n=53) needs 4 * (1 + 1378) = 5516 evaluations for one initial 2-opt
        # pass per individual, so initial polish cannot fit the profile's 100/500
        # budget levels; the polish lives in the final phase, which the fixed-budget
        # accounting truncates cleanly.
        assert params["final_polish_iters"] >= 1
        assert params.get("polish_iters", 0) + params["final_polish_iters"] >= 1
