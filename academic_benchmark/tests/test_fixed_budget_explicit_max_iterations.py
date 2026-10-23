"""A17 owner decision (2026-10-23): fixed-budget runs write ``max_iterations`` explicitly.

Two registry defaults can end a fixed-budget run before the evaluation budget is used: the
GWO/HHO executors fill a missing ``max_iterations`` with 250 and the local searches (2-opt,
3-opt, Or-opt) with 1000. A fixed-budget run of these algorithms is refused before any
evaluation when the key is missing (same layers as ``max_no_improvement``). GA, PSO, ALNS and
the composite stages already require it. Native runs are unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from academic_benchmark.core import registry_setup
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from academic_benchmark.fair_pilot import FairPilotError, load_fair_pilot_config
from uniride_core.algorithms.tsp_matrix_metaheuristics import GWOOptimizer, HHOOptimizer

GWO_HHO_IDS = (
    "Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt",
)
LOCAL_SEARCH_IDS = ("Core-TwoOpt-TSP", "Core-ThreeOpt-TSP", "Core-OrOpt-TSP")
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
        name="fb-iter-tsp-6", dimension=6, coordinates=[], problem_type="tsp",
        dist_matrix=matrix, optimal=1.0,
    )


def _swarm_params(algorithm_id: str, *, key: bool, protocol: str = "fixed") -> dict:
    params: dict = {"max_no_improvement": 99}
    if key:
        params["max_iterations"] = 2
    if protocol == "fixed":
        params["fair_comparison"] = {"evaluation_budget": 5000, "base_seed": 41}
    else:
        params["native_comparison"] = dict(NATIVE)
    if "GWO" in algorithm_id:
        params["pack_size"] = 4
    else:
        params.update(hawks=4, dive_count=0, jump_probability=0.0)
    if "Memetic" in algorithm_id:
        params.update(polish_iters=1, final_polish_iters=1)
    return params


def _local_params(*, key: bool, protocol: str = "fixed") -> dict:
    params: dict = {"first_improvement": False}
    if key:
        params["max_iterations"] = 3
    if protocol == "fixed":
        params["fair_comparison"] = {"evaluation_budget": 5000, "base_seed": 41}
    else:
        params["native_comparison"] = dict(NATIVE)
    return params


def _run(algorithm_id: str, params: dict):
    return AlgorithmRegistry.get_executor(algorithm_id)(_problem(), params, seed=1, run_idx=0)


# ------------------------------------------------------------------------------ GWO / HHO
@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
def test_fixed_budget_swarm_run_without_max_iterations_is_refused_before_any_evaluation(
    algorithm_id, monkeypatch
):
    def forbidden(self, *args, **kwargs):
        raise AssertionError("the solver must not start without an explicit max_iterations")

    monkeypatch.setattr(GWOOptimizer, "solve_with_matrix", forbidden)
    monkeypatch.setattr(HHOOptimizer, "solve_with_matrix", forbidden)
    with pytest.raises(ValueError) as caught:
        _run(algorithm_id, _swarm_params(algorithm_id, key=False))
    message = str(caught.value)
    assert algorithm_id in message and "max_iterations" in message


@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
def test_fixed_budget_swarm_run_with_the_key_runs_as_before(algorithm_id):
    result = _run(algorithm_id, _swarm_params(algorithm_id, key=True))
    assert result.evaluation_budget == 5000
    assert "max_iterations=2" in result.termination_policy


@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
@pytest.mark.parametrize("bad", [0, -1, 1.5, True, "250", None])
def test_fixed_budget_swarm_key_must_be_a_positive_integer(algorithm_id, bad):
    params = _swarm_params(algorithm_id, key=False)
    params["max_iterations"] = bad
    with pytest.raises(ValueError, match="max_iterations"):
        _run(algorithm_id, params)


@pytest.mark.parametrize("algorithm_id", GWO_HHO_IDS)
def test_native_swarm_run_without_the_key_is_unchanged(algorithm_id):
    result = _run(algorithm_id, _swarm_params(algorithm_id, key=False, protocol="native"))
    assert result.comparison_regime == "algorithm_native_termination"


# --------------------------------------------------------------------------- local searches
@pytest.mark.parametrize("algorithm_id", LOCAL_SEARCH_IDS)
def test_fixed_budget_local_search_without_max_iterations_is_refused_before_any_evaluation(
    algorithm_id, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("no search work may start without an explicit max_iterations")

    monkeypatch.setattr(registry_setup, "_problem_matrix", forbidden)
    with pytest.raises(ValueError) as caught:
        _run(algorithm_id, _local_params(key=False))
    message = str(caught.value)
    assert algorithm_id in message and "max_iterations" in message


@pytest.mark.parametrize("algorithm_id", LOCAL_SEARCH_IDS)
def test_fixed_budget_local_search_with_the_key_runs_as_before(algorithm_id):
    result = _run(algorithm_id, _local_params(key=True))
    assert result.evaluation_budget == 5000
    assert "max_iterations=3" in result.termination_policy


@pytest.mark.parametrize("algorithm_id", LOCAL_SEARCH_IDS)
@pytest.mark.parametrize("bad", [0, -2, 2.5, True, "1000", None])
def test_fixed_budget_local_search_key_must_be_a_positive_integer(algorithm_id, bad):
    params = _local_params(key=False)
    params["max_iterations"] = bad
    with pytest.raises(ValueError, match="max_iterations"):
        _run(algorithm_id, params)


@pytest.mark.parametrize("algorithm_id", ["Core-TwoOpt-TSP", "Core-ThreeOpt-TSP"])
def test_native_two_and_three_opt_already_require_the_key(algorithm_id):
    with pytest.raises(ValueError, match="max_iterations"):
        _run(algorithm_id, _local_params(key=False, protocol="native"))


def test_native_or_opt_without_the_key_is_unchanged():
    """Native runs are out of scope: Or-opt keeps its default of 1000 in native mode."""
    result = _run("Core-OrOpt-TSP", _local_params(key=False, protocol="native"))
    assert result.comparison_regime == "algorithm_native_termination"


# ----------------------------------------------------------------------------------- helpers
def test_helper_names_algorithm_and_key_and_ignores_algorithms_that_already_require_it():
    from academic_benchmark.fairness import require_fixed_budget_max_iterations

    for algorithm_id in (*GWO_HHO_IDS, *LOCAL_SEARCH_IDS):
        with pytest.raises(ValueError, match=rf"{algorithm_id}.*max_iterations"):
            require_fixed_budget_max_iterations(algorithm_id, {"first_improvement": False})
        require_fixed_budget_max_iterations(algorithm_id, {"max_iterations": 7})
    # GA / PSO / ALNS validate the key in their own strict schemas; the helper leaves them alone.
    for algorithm_id in ("Core-GA-TSP", "Core-PSO-TSP", "ALNS-TSP"):
        require_fixed_budget_max_iterations(algorithm_id, {})


@pytest.mark.parametrize("algorithm_id", ["Core-GWO-TSP-Memetic-3opt", "Core-HHO-TSP-Memetic-ALNS"])
def test_helper_checks_the_global_stage_of_a_composite(algorithm_id):
    from academic_benchmark.fairness import require_fixed_budget_max_iterations

    with pytest.raises(ValueError, match=rf"{algorithm_id} global stage.*max_iterations"):
        require_fixed_budget_max_iterations(algorithm_id, {"global": {"pack_size": 4}, "polish": {}})
    require_fixed_budget_max_iterations(
        algorithm_id, {"global": {"max_iterations": 5}, "polish": {}}
    )


def test_combined_helper_checks_both_keys():
    from academic_benchmark.fairness import require_fixed_budget_stopping_keys

    with pytest.raises(ValueError, match=r"Core-GWO-TSP-Pure.*max_no_improvement"):
        require_fixed_budget_stopping_keys("Core-GWO-TSP-Pure", {"max_iterations": 5})
    with pytest.raises(ValueError, match=r"Core-GWO-TSP-Pure.*max_iterations"):
        require_fixed_budget_stopping_keys("Core-GWO-TSP-Pure", {"max_no_improvement": 5})
    require_fixed_budget_stopping_keys(
        "Core-GWO-TSP-Pure", {"max_iterations": 5, "max_no_improvement": 5}
    )
    with pytest.raises(ValueError, match=r"Core-TwoOpt-TSP.*max_iterations"):
        require_fixed_budget_stopping_keys("Core-TwoOpt-TSP", {})


# ------------------------------------------------------------------------- fair-pilot loader
def _fair_config(tmp_path: Path, *, gwo: dict, two_opt: dict, three_opt: dict) -> Path:
    config = {
        "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget",
        "problems": ["tiny-tsp"],
        "algorithms": {
            "Core-GWO-TSP-Pure": gwo,
            "Core-HHO-TSP-Pure": {
                "hawks": 4, "max_iterations": 2, "max_no_improvement": 5, "dive_count": 0,
            },
            "Core-TwoOpt-TSP": two_opt,
            "Core-ThreeOpt-TSP": three_opt,
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


def test_fair_pilot_config_refuses_blocks_without_max_iterations(tmp_path):
    ok_gwo = {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 5}
    ok_two = {"max_iterations": 2, "first_improvement": False}
    ok_three = {"max_iterations": 2, "first_improvement": False, "window": 4}
    load_fair_pilot_config(_fair_config(tmp_path, gwo=ok_gwo, two_opt=ok_two, three_opt=ok_three))
    with pytest.raises(FairPilotError, match=r"Core-GWO-TSP-Pure.*max_iterations"):
        load_fair_pilot_config(_fair_config(
            tmp_path, gwo={"pack_size": 4, "max_no_improvement": 5}, two_opt=ok_two, three_opt=ok_three
        ))
    with pytest.raises(FairPilotError, match=r"Core-TwoOpt-TSP.*max_iterations"):
        load_fair_pilot_config(_fair_config(
            tmp_path, gwo=ok_gwo, two_opt={"first_improvement": False}, three_opt=ok_three
        ))
    with pytest.raises(FairPilotError, match=r"Core-ThreeOpt-TSP.*max_iterations"):
        load_fair_pilot_config(_fair_config(
            tmp_path, gwo=ok_gwo, two_opt=ok_two, three_opt={"first_improvement": False, "window": 4}
        ))


# ------------------------------------------------------------------- profiles and smoke runner
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("study", ["bildiri2026", "yaem2026"])
def test_every_study_profile_entry_writes_the_stopping_keys_it_needs(study):
    from academic_benchmark.fairness import require_fixed_budget_stopping_keys

    payload = json.loads(
        (REPOSITORY_ROOT / "academic_benchmark" / "studies" / study / "study.json").read_text(encoding="utf-8")
    )
    for algorithm_id, block in payload["algorithm_parameters"].items():
        require_fixed_budget_stopping_keys(algorithm_id, block)  # raises when an entry lacks a key


@pytest.mark.parametrize("algorithm_id,block", [
    ("Core-GWO-TSP-Pure", {"pack_size": 4, "max_no_improvement": 3}),
    ("Core-TwoOpt-TSP", {"first_improvement": False}),
    ("Core-OrOpt-TSP", {"first_improvement": False, "window": 3}),
])
def test_study_smoke_refuses_a_fixed_row_without_max_iterations_before_running(algorithm_id, block):
    from types import SimpleNamespace

    from academic_benchmark.studies.smoke import StudySmokeError, _row_params
    from uniride_core.algorithms.capabilities import ExecutionProtocol

    study = SimpleNamespace(
        algorithm_parameters={algorithm_id: block},
        secondary_protocol=SimpleNamespace(termination={"max_iterations": 2}),
    )
    fixed = SimpleNamespace(algorithm_id=algorithm_id, protocol=ExecutionProtocol.FIXED_BUDGET)
    native = SimpleNamespace(algorithm_id=algorithm_id, protocol=ExecutionProtocol.NATIVE_TERMINATION)
    with pytest.raises(StudySmokeError, match=rf"{algorithm_id}.*max_iterations"):
        _row_params(study, fixed)
    assert _row_params(study, native)["max_iterations"] == 2  # native rows are unchanged
