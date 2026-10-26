"""A20 L9: the hybrid 3-opt polish window follows the one top-level 3-opt window rule.

``uniride_core.algorithms.three_opt.validate_three_opt_window`` accepts any integer (numpy integers
included) that is at least 2 and refuses floats; the hybrid polish namespace used to accept only a
plain ``int`` and so refused a numpy integer that the standalone 3-opt window accepts.
"""
from __future__ import annotations

import numpy as np
import pytest

from academic_benchmark.fairness import validate_scientific_hybrid_3opt_params
from uniride_core.algorithms.composition import SWARM_REQUIRED_PARAMS

_GLOBAL = {
    "pack_size": 4, "max_iterations": 3, "initial_a": 2.0, "exploration_rate": 0.1, "max_no_improvement": 5,
}
assert set(_GLOBAL) == set(SWARM_REQUIRED_PARAMS["GWO"])


def _params(window):
    return {"global": dict(_GLOBAL), "global_fraction": 0.8,
            "polish": {"max_iterations": 2, "first_improvement": False, "window": window}}


def _validate(window):
    return validate_scientific_hybrid_3opt_params("GWO", _params(window), fixed_budget=True)


@pytest.mark.parametrize("window", [2, 12, 100, np.int64(12), np.int32(2), np.intp(7)])
def test_the_hybrid_polish_window_accepts_plain_and_numpy_integers_from_two(window):
    assert _validate(window)["polish"]["window"] == window


@pytest.mark.parametrize("window", [1, 0, -3, np.int64(1), 12.0, 12.5, np.float64(12.0), "12", None, True, False])
def test_the_hybrid_polish_window_refuses_small_integers_floats_and_other_types(window):
    with pytest.raises(ValueError, match="invalid hybrid polish parameter: window"):
        _validate(window)
