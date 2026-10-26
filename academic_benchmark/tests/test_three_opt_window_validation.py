"""A20 L9 follow-up: the 3-opt ``window`` is validated up front on every registry path.

The core rule (``uniride_core.algorithms.three_opt.validate_three_opt_window``): an integer
(``operator.index``) that is at least 2. The fixed-budget path used to hand the raw value to the
search (the error then came from deep inside it, after the matrix was built) and the native path
truncated it with ``int(...)`` (``12.5`` silently became ``12``). Both now refuse a bad value
before the matrix is built and before any objective evaluation is counted. ``None`` is refused as
well. On a V1 fixed-budget manifest (the default protocol) ``window=None`` used to run an
unrestricted 3-opt and could pass validation (``fairness.py`` ``validate_result``: the check that the
window is an integer >= 2 is inside the V2 block only); it is now refused up front. Both study
profiles are V2 with integer windows, where the result validator rejected ``None`` only after the
whole run.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from academic_benchmark import fairness
from academic_benchmark.core import registry_setup
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance

ALGORITHM_ID = "Core-ThreeOpt-TSP"
NATIVE = {
    "base_seed": 239,
    "protocol_version": "uniride-native-tsp-v1",
    "comparison_regime": "algorithm_native_termination",
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BAD_WINDOWS = [12.0, 12.5, 1, 0, -3, True, "12", None]


def _problem() -> ProblemInstance:
    matrix = [
        [0.0 if i == j else float((i + 1) * 7 + (j + 1) * 3 + abs(i - j)) for j in range(8)]
        for i in range(8)
    ]
    return ProblemInstance(
        name="window-tsp-8", dimension=8, coordinates=[], problem_type="tsp",
        dist_matrix=matrix, optimal=1.0,
    )


def _params(protocol: str, **extra) -> dict:
    params: dict = {"first_improvement": False, "max_iterations": 3}
    if protocol == "fixed":
        params["fair_comparison"] = {"evaluation_budget": 5000, "base_seed": 41}
    else:
        params["native_comparison"] = dict(NATIVE)
    params.update(extra)
    return params


def _run(params: dict):
    return AlgorithmRegistry.get_executor(ALGORITHM_ID)(_problem(), params, seed=1, run_idx=0)


def _forbid_all_search_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no matrix may be built and no evaluation counted for a bad window")

    monkeypatch.setattr(registry_setup, "_problem_matrix", forbidden)
    monkeypatch.setattr(fairness, "improve_three_opt_budgeted", forbidden)


@pytest.mark.parametrize("protocol", ["fixed", "native"])
@pytest.mark.parametrize("bad", BAD_WINDOWS, ids=repr)
def test_bad_window_is_refused_before_any_evaluation(protocol, bad, monkeypatch):
    _forbid_all_search_work(monkeypatch)
    with pytest.raises(ValueError, match="window"):
        _run(_params(protocol, window=bad))


@pytest.mark.parametrize("bad", [12.0, 12.5, 1, None], ids=repr)
def test_fixed_budget_alias_key_is_validated_and_named(bad, monkeypatch):
    _forbid_all_search_work(monkeypatch)
    with pytest.raises(ValueError, match="max_segment_length"):
        _run(_params("fixed", max_segment_length=bad))


@pytest.mark.parametrize("protocol", ["fixed", "native"])
@pytest.mark.parametrize("good", [12, np.int64(12), np.int32(5), 2], ids=repr)
def test_integer_windows_are_accepted_and_recorded_as_plain_int(protocol, good):
    result = _run(_params(protocol, window=good))
    assert result.neighborhood_window == int(good)
    assert type(result.neighborhood_window) is int


def test_fixed_budget_alias_key_still_works():
    result = _run(_params("fixed", max_segment_length=np.int64(7)))
    assert result.neighborhood_window == 7


def test_fixed_budget_default_window_is_unchanged():
    assert _run(_params("fixed")).neighborhood_window == 12


@pytest.mark.parametrize("study", ["bildiri2026", "yaem2026"])
def test_study_profile_windows_pass_the_core_rule(study):
    from uniride_core.algorithms.three_opt import validate_three_opt_window

    payload = json.loads(
        (REPOSITORY_ROOT / "academic_benchmark" / "studies" / study / "study.json").read_text(encoding="utf-8")
    )
    block = payload["algorithm_parameters"]["Core-ThreeOpt-TSP"]
    assert validate_three_opt_window(block["window"], allow_none=False) == block["window"]
    for composite in ("Core-GWO-TSP-Memetic-3opt", "Core-HHO-TSP-Memetic-3opt"):
        polish = payload["algorithm_parameters"].get(composite, {}).get("polish")
        if polish is not None:
            assert validate_three_opt_window(polish["window"], allow_none=False) == polish["window"]


def test_helper_rules():
    from uniride_core.algorithms.three_opt import validate_three_opt_window

    assert validate_three_opt_window(None) is None
    with pytest.raises(ValueError, match="window"):
        validate_three_opt_window(None, allow_none=False)
    with pytest.raises(ValueError, match="my_key"):
        validate_three_opt_window(12.0, name="my_key")
    with pytest.raises(ValueError, match="at least 2"):
        validate_three_opt_window(1)
    assert validate_three_opt_window(np.int64(9)) == 9
