"""C-07: the core ALNS polish schema must accept and refuse what the C3 schema does.

``uniride_core`` cannot import ``academic_benchmark``, so
``composition.validate_alns_polish_params`` restates the rules of
``fairness.validate_scientific_alns_params``. This test keeps the two in step
until C-09 makes one import the other.
"""

from __future__ import annotations

import pytest

from academic_benchmark.fairness import (
    ALNS_OPTIONAL_PARAMS as FAIRNESS_OPTIONAL,
    ALNS_REQUIRED_PARAMS as FAIRNESS_REQUIRED,
    validate_scientific_alns_params,
)
from uniride_core.algorithms.composition import (
    ALNS_OPTIONAL_PARAMS,
    ALNS_REQUIRED_PARAMS,
    CompositionError,
    validate_alns_polish_params,
)

BASE = {
    "max_iterations": 60, "max_no_improvement": 100, "remove_ratio": 0.25,
    "min_remove": 2, "segment_length": 10, "weight_update_factor": 0.8,
    "use_sa": True, "sa_start_temp": 100.0, "sa_cooling_rate": 0.995,
}

BAD_VALUES = {
    "max_iterations": [0, -1, True, 1.5, "5"],
    "max_no_improvement": [0, True, 2.0],
    "min_remove": [0, False],
    "segment_length": [0, None],
    "remove_ratio": [0, 0.0, 1.5, float("nan"), float("inf"), True],
    "weight_update_factor": [-0.01, 1.01, float("nan"), True],
    "use_sa": [0, 1, "yes", None],
    "sa_start_temp": [-1.0, 0.0, float("nan"), True],
    "sa_cooling_rate": [0.0, 1.01, -0.5, float("nan"), True],
}


def _accepts(validator, params, error) -> bool:
    try:
        validator(params)
    except error:
        return False
    return True


def test_parameter_name_sets_are_identical():
    assert ALNS_REQUIRED_PARAMS == FAIRNESS_REQUIRED
    assert ALNS_OPTIONAL_PARAMS == FAIRNESS_OPTIONAL


def test_exact_schema_accepted_by_both():
    assert validate_alns_polish_params(BASE) == validate_scientific_alns_params(BASE)


def _cases():
    for name, values in BAD_VALUES.items():
        for value in values:
            yield dict(BASE, **{name: value})
    yield dict(BASE, use_sa=False, sa_start_temp=0.0)  # allowed when SA is off
    yield dict(BASE, sa_start_temp=0.0)  # refused when SA is on
    yield dict(BASE, surprise=1)
    for name in BASE:
        yield {k: v for k, v in BASE.items() if k != name}


@pytest.mark.parametrize("params", list(_cases()))
def test_core_and_fairness_schemas_agree(params):
    core = _accepts(validate_alns_polish_params, params, CompositionError)
    fairness = _accepts(validate_scientific_alns_params, params, ValueError)
    assert core == fairness, params
