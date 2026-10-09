"""CX-04: direct fairness manifests must not coerce or silently ignore input."""

import pytest

from academic_benchmark.fairness import FairComparisonManifest, fair_manifest_from_params


@pytest.mark.parametrize("budget", [3.9, 5.0, True, False, "5", 0, -3, None])
def test_bad_evaluation_budget_rejected(budget):
    with pytest.raises(ValueError, match="evaluation_budget"):
        FairComparisonManifest.from_value({"evaluation_budget": budget})
    with pytest.raises(ValueError, match="evaluation_budget"):
        fair_manifest_from_params({"fair_comparison": {"evaluation_budget": budget}})


@pytest.mark.parametrize("seed", [False, True, 1.5, "7", None])
def test_bad_base_seed_rejected(seed):
    with pytest.raises(ValueError, match="base_seed"):
        FairComparisonManifest.from_value({"evaluation_budget": 5, "base_seed": seed})


def test_direct_constructor_also_rejects_bool_and_float():
    for kwargs in ({"evaluation_budget": True}, {"evaluation_budget": 3.9}, {"evaluation_budget": 5, "base_seed": False}):
        with pytest.raises(ValueError):
            FairComparisonManifest(**kwargs)


def test_unknown_fields_rejected_with_clear_error():
    with pytest.raises(ValueError, match="typo_field"):
        FairComparisonManifest.from_value({"evaluation_budget": 5, "typo_field": 99})


def test_valid_ints_accepted_and_paired_seeds_unchanged():
    m = FairComparisonManifest.from_value({"evaluation_budget": 500, "base_seed": 77})
    assert (m.evaluation_budget, m.base_seed) == (500, 77)
    # literal measured on the pre-fix code (3e14915^), manifest budget 500 / base_seed 77
    assert m.paired_seed("berlin52", 3) == 583917059
    neg = FairComparisonManifest.from_value({"evaluation_budget": 5, "base_seed": -7})
    assert neg.base_seed == -7 and 0 <= neg.paired_seed("p", 0) < 2_147_483_647
    default = FairComparisonManifest.from_value({"evaluation_budget": 5})
    assert default.base_seed == 1000
