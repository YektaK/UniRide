"""A17 owner decision 3 (2026-10-23): fixed-budget runs write ``max_no_improvement`` explicitly.

The Numba GWO/HHO executors fill a missing ``max_no_improvement`` from a registry default (75);
under a fixed evaluation budget that default is a hidden stopping rule that can end the run before
the budget is used. A fixed-budget run of every algorithm that has the key is therefore refused
before any evaluation when the key is missing. Native runs are unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from academic_benchmark.fair_pilot import FairPilotError, load_fair_pilot_config
from academic_benchmark.fairness import require_fixed_budget_max_no_improvement
from uniride_core.algorithms.tsp_matrix_metaheuristics import GWOOptimizer, HHOOptimizer

GWO_HHO_IDS = (
    "Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt",
)
NATIVE = {
    "base_seed": 239,
    "protocol_version": "uniride-native-tsp-v1",
    "comparison_regime": "algorithm_native_termination",
}


def _problem() -> ProblemInstance:
    matrix = [
        [0.0 if i == j else float((i + 1) * 7 + (j + 1) * 3 + abs(i - j)) for j in range(6)]
        for i in range(6)
    ]
    return ProblemInstance(
        name="fb-key-tsp-6", dimension=6, coordinates=[], problem_type="tsp",
        dist_matrix=matrix, optimal=1.0,
    )


def _params(algorithm_id: str, *, key: bool, protocol: str = "fixed") -> dict:
    params: dict = {"max_iterations": 2}
    if protocol == "fixed":
        params["fair_comparison"] = {"evaluation_budget": 5000, "base_seed": 41}
    else:
        params["native_comparison"] = dict(NATIVE)
    if key:
        params["max_no_improvement"] = 99
    if "GWO" in algorithm_id:
        params["pack_size"] = 4
    else:
        params.update(hawks=4, dive_count=0, jump_probability=0.0)
    if "Memetic" in algorithm_id:
        params.update(polish_iters=1, final_polish_iters=1)
    return params


def _run(algorithm_id: str, params: dict):
    return AlgorithmRegistry.get_executor(algorithm_id)(_problem(), params, seed=1, run_idx=0)


@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
def test_fixed_budget_run_without_the_key_is_refused_before_any_evaluation(algorithm_id, monkeypatch):
    def forbidden(self, *args, **kwargs):
        raise AssertionError("the solver must not start without an explicit max_no_improvement")

    monkeypatch.setattr(GWOOptimizer, "solve_with_matrix", forbidden)
    monkeypatch.setattr(HHOOptimizer, "solve_with_matrix", forbidden)
    with pytest.raises(ValueError) as caught:
        _run(algorithm_id, _params(algorithm_id, key=False))
    message = str(caught.value)
    assert algorithm_id in message and "max_no_improvement" in message


@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
def test_fixed_budget_run_with_the_key_runs_as_before(algorithm_id):
    result = _run(algorithm_id, _params(algorithm_id, key=True))
    assert result.termination_reason in {"evaluation_budget_exhausted", "max_iterations", "stagnation_limit"}
    assert result.evaluation_budget == 5000
    assert f"max_no_improvement=99" in result.termination_policy


@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
@pytest.mark.parametrize("bad", [0, -1, 1.5, True, "75", None])
def test_fixed_budget_key_must_be_a_positive_integer(algorithm_id, bad):
    params = _params(algorithm_id, key=False)
    params["max_no_improvement"] = bad
    with pytest.raises(ValueError, match="max_no_improvement"):
        _run(algorithm_id, params)


@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
def test_native_run_without_the_key_is_unchanged(algorithm_id):
    result = _run(algorithm_id, _params(algorithm_id, key=False, protocol="native"))
    assert result.comparison_regime == "algorithm_native_termination"


def test_helper_names_algorithm_and_key_and_ignores_algorithms_without_the_key():
    with pytest.raises(ValueError, match=r"Core-GWO-TSP-Pure.*max_no_improvement"):
        require_fixed_budget_max_no_improvement("Core-GWO-TSP-Pure", {"pack_size": 4})
    # 2-opt/3-opt/Or-opt have no such parameter, so nothing is required of them
    require_fixed_budget_max_no_improvement("Core-TwoOpt-TSP", {"max_iterations": 5})
    require_fixed_budget_max_no_improvement("Core-GWO-TSP-Pure", {"max_no_improvement": 7})


@pytest.mark.parametrize("namespace_missing", ["global"])
@pytest.mark.parametrize("algorithm_id", [
    "Core-GWO-TSP-Memetic-3opt", "Core-HHO-TSP-Memetic-ALNS",
])
def test_helper_checks_the_global_stage_of_a_composite(algorithm_id, namespace_missing):
    with pytest.raises(ValueError, match=r"max_no_improvement"):
        require_fixed_budget_max_no_improvement(algorithm_id, {"global": {"pack_size": 4}, "polish": {}})


@pytest.mark.parametrize("algorithm_id", ["Core-GWO-TSP-Memetic-ALNS", "Core-HHO-TSP-Memetic-ALNS"])
@pytest.mark.parametrize("polish", [None, {}, {"max_iterations": 5}, {"max_no_improvement": 0}, {"max_no_improvement": True}])
def test_helper_checks_the_polish_stage_of_an_alns_composite(algorithm_id, polish):
    # the global stage is complete, so only the ALNS polish block can make this refuse (A17 2026-10-23 follow-up)
    params = {"global": {"max_no_improvement": 7}}
    if polish is not None:
        params["polish"] = polish
    with pytest.raises(ValueError, match=rf"{algorithm_id} polish stage.*max_no_improvement"):
        require_fixed_budget_max_no_improvement(algorithm_id, params)
    params["polish"] = {"max_no_improvement": 3}
    require_fixed_budget_max_no_improvement(algorithm_id, params)  # both stages write the key: accepted


@pytest.mark.parametrize("algorithm_id", ["Core-GWO-TSP-Memetic-3opt", "Core-HHO-TSP-Memetic-3opt"])
def test_helper_does_not_ask_a_3opt_composite_for_a_polish_stagnation_key(algorithm_id):
    # the 3-opt polish has no max_no_improvement; only the ALNS polish is checked
    require_fixed_budget_max_no_improvement(algorithm_id, {"global": {"max_no_improvement": 7}, "polish": {}})
    require_fixed_budget_max_no_improvement(algorithm_id, {"global": {"max_no_improvement": 7}})


def _fair_config(tmp_path: Path, gwo: dict, hho: dict) -> Path:
    config = {
        "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget",
        "problems": ["tiny-tsp"],
        "algorithms": {
            "Core-GWO-TSP-Pure": gwo,
            "Core-HHO-TSP-Pure": hho,
            "Core-TwoOpt-TSP": {"max_iterations": 2, "first_improvement": False},
            "Core-ThreeOpt-TSP": {"max_iterations": 2, "first_improvement": False, "window": 4},
            "ALNS-TSP": {
                "max_iterations": 8, "max_no_improvement": 3, "remove_ratio": 0.34, "min_remove": 1,
                "segment_length": 2, "weight_update_factor": 0.2, "use_sa": True,
                "sa_start_temp": 4.0, "sa_cooling_rate": 0.9,
            },
        },
        "runs": 1, "evaluation_budget": 100, "base_seed": 1, "budget_policy": "atomic_upper_bound_v1",
        "workers": 1, "replay_replicates": [0], "allow_repository_output": False, "overwrite": False,
    }
    path = tmp_path / "fair.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_fair_pilot_config_refuses_a_gwo_hho_block_without_the_key(tmp_path):
    ok_gwo = {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 5}
    ok_hho = {"hawks": 4, "max_iterations": 2, "max_no_improvement": 5, "dive_count": 0}
    load_fair_pilot_config(_fair_config(tmp_path, ok_gwo, ok_hho))  # control: loads
    with pytest.raises(FairPilotError, match=r"Core-GWO-TSP-Pure.*max_no_improvement"):
        load_fair_pilot_config(_fair_config(tmp_path, {"pack_size": 4, "max_iterations": 2}, ok_hho))
    with pytest.raises(FairPilotError, match=r"Core-HHO-TSP-Pure.*max_no_improvement"):
        load_fair_pilot_config(_fair_config(tmp_path, ok_gwo, {"hawks": 4, "max_iterations": 2}))


# ------------------------------------------------------------------------- profiles and smoke runner
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("study", ["bildiri2026", "yaem2026"])
def test_every_study_profile_entry_writes_the_key_it_needs(study):
    payload = json.loads(
        (REPOSITORY_ROOT / "academic_benchmark" / "studies" / study / "study.json").read_text(encoding="utf-8")
    )
    for algorithm_id, block in payload["algorithm_parameters"].items():
        require_fixed_budget_max_no_improvement(algorithm_id, block)  # raises when an entry lacks it


def test_study_smoke_refuses_a_fixed_row_without_the_key_before_running():
    from types import SimpleNamespace

    from academic_benchmark.studies.smoke import StudySmokeError, _row_params
    from uniride_core.algorithms.capabilities import ExecutionProtocol

    study = SimpleNamespace(
        algorithm_parameters={"Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 3}},
        secondary_protocol=SimpleNamespace(termination={"max_iterations": 2}),
    )
    fixed = SimpleNamespace(algorithm_id="Core-GWO-TSP-Pure", protocol=ExecutionProtocol.FIXED_BUDGET)
    native = SimpleNamespace(algorithm_id="Core-GWO-TSP-Pure", protocol=ExecutionProtocol.NATIVE_TERMINATION)
    with pytest.raises(StudySmokeError, match=r"Core-GWO-TSP-Pure.*max_no_improvement"):
        _row_params(study, fixed)
    assert _row_params(study, native)["max_iterations"] == 2  # native rows are unchanged
