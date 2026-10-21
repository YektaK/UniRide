"""WP-E11 J9b: blocking checks (design JOINT_DAY_MODEL_DESIGN.md 5.3) and reproduction categories (6.3) of the joint day
model. Pure functions on numbers and labels; nothing is solved here.

The disagreement rule of 6.3: a prototype plan that passes the independent checker and is better than a production value
labelled ``optimal`` is a blocking defect of production (a checked plan cannot beat a proven optimum); production better
than a prototype ``optimal`` is a described difference, not blocking.
"""
from __future__ import annotations

import pytest

from academic_benchmark.exact_reference import day_compare as dc
from academic_benchmark.exact_reference.day_compare import BlockingDefect, PrototypeClaim, reproduction_category


# ---------------------------------------------------------------- the disagreement rule (red tests 1 and 2)
def test_a_checked_prototype_plan_that_beats_a_production_optimal_is_a_blocking_defect():
    with pytest.raises(BlockingDefect) as err:
        reproduction_category(PrototypeClaim.value((5, 800), plan_checked=True), production_label="optimal",
                              production_objective=(6, 700))
    assert err.value.code == dc.BLOCKING_PROTOTYPE_BEATS_OPTIMUM


def test_production_better_than_a_prototype_optimal_is_production_better_and_not_blocking():
    out = reproduction_category(PrototypeClaim.value((6, 800), plan_checked=True), production_label="optimal",
                                production_objective=(5, 900))
    assert out.category == "production_better"


def test_a_checked_prototype_plan_is_blocking_only_where_production_proved_the_component():
    # production proved only stage 1 (optimal_stage1_by_bound): a better stage-2 value of the prototype is not blocking,
    # a better stage-1 value is
    claim = PrototypeClaim.value((5, 700), plan_checked=True)
    out = reproduction_category(claim, production_label="optimal_stage1_by_bound", production_objective=(5, 800))
    assert out.category == "production_worse"
    with pytest.raises(BlockingDefect):
        reproduction_category(PrototypeClaim.value((4, 900), plan_checked=True), production_label="optimal_stage1_by_bound",
                              production_objective=(5, 800))


@pytest.mark.parametrize("checked", [False, None])
def test_a_prototype_plan_that_fails_or_skipped_the_checker_is_never_blocking_but_is_marked_unverified(checked):
    out = reproduction_category(PrototypeClaim.value((5, 800), plan_checked=checked), production_label="optimal",
                                production_objective=(6, 700))
    assert out.category == "production_worse"
    assert out.prototype_claim_verified is False
    assert out.note == "prototype_plan_not_verified"


def test_a_verified_prototype_claim_is_marked_verified():
    out = reproduction_category(PrototypeClaim.value((6, 800), plan_checked=True), production_label="optimal",
                                production_objective=(5, 900))
    assert out.prototype_claim_verified is True and out.note == ""


def test_a_better_prototype_value_against_a_production_gap_is_production_worse_not_blocking():
    out = reproduction_category(PrototypeClaim.value((5, 800), plan_checked=True), production_label="feasible_with_gap",
                                production_objective=(6, 700))
    assert out.category == "production_worse"


@pytest.mark.parametrize("label", ["infeasible_certified", "infeasible_solver_proven"])
def test_a_checked_prototype_plan_contradicts_a_production_infeasibility_proof(label):
    with pytest.raises(BlockingDefect) as err:
        reproduction_category(PrototypeClaim.value((2, 100), plan_checked=True), production_label=label)
    assert err.value.code == dc.BLOCKING_PROTOTYPE_PLAN_VS_INFEASIBLE


def test_an_unchecked_prototype_plan_against_an_infeasibility_proof_is_not_blocking():
    out = reproduction_category(PrototypeClaim.value((2, 100), plan_checked=False), production_label="infeasible_certified")
    assert out.category == "production_better" and out.note == "prototype_plan_not_verified"


# ---------------------------------------------------------------- every category (red test 5)
def test_category_equal():
    out = reproduction_category(PrototypeClaim.value((5, 800)), production_label="optimal", production_objective=(5, 800))
    assert out.category == "equal"


def test_category_equal_for_two_infeasible_cells():
    assert reproduction_category(PrototypeClaim.infeasible(), production_label="infeasible_certified").category == "equal"


def test_category_co_optimal_alternative_needs_equal_objectives_and_different_routes():
    out = reproduction_category(PrototypeClaim.value((5, 800)), production_label="optimal", production_objective=(5, 800),
                                same_routes=False)
    assert out.category == "co_optimal_alternative"
    out = reproduction_category(PrototypeClaim.value((5, 800)), production_label="optimal", production_objective=(5, 801),
                                same_routes=False)
    assert out.category != "co_optimal_alternative"


def test_category_production_better():
    out = reproduction_category(PrototypeClaim.value((6, 800)), production_label="optimal", production_objective=(5, 900))
    assert out.category == "production_better"
    out = reproduction_category(PrototypeClaim.value((5, 900)), production_label="optimal", production_objective=(5, 800))
    assert out.category == "production_better"  # same K, fewer minutes


def test_production_better_than_a_prototype_infeasible_claim():
    out = reproduction_category(PrototypeClaim.infeasible(), production_label="optimal", production_objective=(2, 100))
    assert out.category == "production_better"


def test_category_production_worse():
    out = reproduction_category(PrototypeClaim.value((5, 800)), production_label="feasible_with_gap", production_objective=(5, 900))
    assert out.category == "production_worse"


def test_category_production_open():
    for label in ("bound_only", "not_run_enumeration_cap", "input_rejected", "backend_unavailable"):
        assert reproduction_category(PrototypeClaim.value((5, 800)), production_label=label).category == "production_open"
    assert reproduction_category(PrototypeClaim.infeasible(), production_label="bound_only").category == "production_open"


def test_category_prototype_open():
    out = reproduction_category(PrototypeClaim.open(), production_label="optimal", production_objective=(2, 100))
    assert out.category == "prototype_open"
    assert reproduction_category(PrototypeClaim.open(), production_label="infeasible_solver_proven").category == "prototype_open"


def test_a_rejected_production_cell_is_not_a_result_to_compare():
    with pytest.raises(ValueError, match="rejected"):
        reproduction_category(PrototypeClaim.value((5, 800)), production_label="rejected")


def test_unknown_labels_and_missing_objectives_are_refused():
    with pytest.raises(ValueError, match="label"):
        reproduction_category(PrototypeClaim.value((5, 800)), production_label="mostly_optimal", production_objective=(5, 800))
    with pytest.raises(ValueError, match="objective"):
        reproduction_category(PrototypeClaim.value((5, 800)), production_label="optimal")


def test_components_restricts_the_comparison_to_the_first_values():
    # the prototype carries only (S, minutes) while production carries (S, total, car minutes); compare S only
    out = reproduction_category(PrototypeClaim.value((2, 900)), production_label="optimal", production_objective=(2, 700, 100),
                                components=1)
    assert out.category == "equal"
    with pytest.raises(ValueError, match="length"):
        reproduction_category(PrototypeClaim.value((2, 900)), production_label="optimal", production_objective=(2, 700, 100))


# ---------------------------------------------------------------- blocking checks of 5.3
def test_joint_cars_above_the_union_menu_cars_is_blocking_where_both_are_proven():  # red test 3
    with pytest.raises(BlockingDefect) as err:
        dc.check_joint_not_above_union(joint_cars=3, union_cars=2, joint_proven=True, union_proven=True)
    assert err.value.code == dc.BLOCKING_JOINT_ABOVE_UNION


@pytest.mark.parametrize("joint, union, jp, up", [(3, 2, False, True), (3, 2, True, False), (3, 2, False, False),
                                                   (2, 2, True, True), (1, 2, True, True)])
def test_joint_versus_union_is_silent_otherwise(joint, union, jp, up):
    assert dc.check_joint_not_above_union(joint_cars=joint, union_cars=union, joint_proven=jp, union_proven=up) is None


def test_joint_k_above_an_archived_peak_is_blocking_when_the_joint_value_is_proven():
    with pytest.raises(BlockingDefect) as err:
        dc.check_joint_k_not_above_peaks(6, {"ga_archive": 6, "wp_e3": 5}, joint_proven=True)
    assert err.value.code == dc.BLOCKING_JOINT_ABOVE_PEAK and "wp_e3" in str(err.value)
    assert dc.check_joint_k_not_above_peaks(5, {"ga_archive": 6, "wp_e3": 5}, joint_proven=True) is None
    assert dc.check_joint_k_not_above_peaks(6, {"ga_archive": 5}, joint_proven=False) is None


def test_a_value_below_a_valid_bound_is_blocking():  # red test 4
    with pytest.raises(BlockingDefect) as err:
        dc.check_value_not_below_bounds(4, {"lb0": 3, "lb0w": 5})
    assert err.value.code == dc.BLOCKING_VALUE_BELOW_BOUND and "lb0w" in str(err.value)
    assert dc.check_value_not_below_bounds(5, {"lb0": 3, "lb0w": 5}) is None
    assert dc.check_value_not_below_bounds(5, {}) is None


def test_a_value_below_a_proven_optimum_of_the_same_cell_is_blocking():
    with pytest.raises(BlockingDefect):
        dc.check_value_not_below_bounds(4, {"proven_optimum": 5})


@pytest.mark.parametrize("call", [
    lambda: dc.check_value_not_below_bounds(-1, {}),
    lambda: dc.check_value_not_below_bounds(1.5, {}),
    lambda: dc.check_value_not_below_bounds(True, {}),
    lambda: dc.check_value_not_below_bounds(1, {"lb": -1}),
    lambda: dc.check_joint_not_above_union(joint_cars=-1, union_cars=1, joint_proven=True, union_proven=True),
    lambda: dc.check_joint_k_not_above_peaks(1, {"p": 1.0}, joint_proven=True),
])
def test_the_blocking_checks_refuse_malformed_numbers(call):
    with pytest.raises(ValueError):
        call()


# ---------------------------------------------------------------- review round 1
def test_c4_a_prototype_plan_without_a_checker_verdict_against_a_production_infeasibility_proof_is_refused():
    for label in ("infeasible_certified", "infeasible_solver_proven"):
        with pytest.raises(ValueError, match="checker"):
            reproduction_category(PrototypeClaim.value((2, 100), plan_checked=None), production_label=label)


def test_c4_a_failed_checker_verdict_is_a_verdict():
    out = reproduction_category(PrototypeClaim.value((2, 100), plan_checked=False), production_label="infeasible_certified")
    assert out.category == "production_better" and out.note == "prototype_plan_not_verified"


def test_c5_the_docstring_tells_the_runner_to_check_values_against_bounds():
    doc = dc.reproduction_category.__doc__
    assert "check_value_not_below_bounds" in doc and "feasible_with_gap" in doc and "bound_only" in doc


def test_c6_leading_optimal_stages_are_proven_even_when_a_later_stage_hit_a_limit():
    statuses = ("optimal", "feasible_with_gap", "feasible_with_gap")
    kw = dict(production_label="feasible_with_gap", production_objective=(5, 800, 50), production_stage_statuses=statuses)
    with pytest.raises(BlockingDefect) as err:  # smaller S, stage 1 proven
        reproduction_category(PrototypeClaim.value((4, 900, 60), plan_checked=True), **kw)
    assert err.value.code == dc.BLOCKING_PROTOTYPE_BEATS_OPTIMUM
    # a smaller stage-2 value at equal S is not proven: not blocking
    out = reproduction_category(PrototypeClaim.value((5, 700, 60), plan_checked=True), **kw)
    assert out.category == "production_worse"
    # without statuses the old behaviour stays (nothing proven for feasible_with_gap)
    out = reproduction_category(PrototypeClaim.value((4, 900, 60), plan_checked=True), production_label="feasible_with_gap",
                                production_objective=(5, 800, 50))
    assert out.category == "production_worse"


def test_c6_two_leading_optimal_stages_prove_two_components():
    statuses = ("optimal", "optimal", "feasible_with_gap")
    with pytest.raises(BlockingDefect):
        reproduction_category(PrototypeClaim.value((5, 700, 60), plan_checked=True), production_label="feasible_with_gap",
                              production_objective=(5, 800, 50), production_stage_statuses=statuses)


def test_c6_a_later_optimal_stage_after_a_gap_stage_is_not_counted():
    statuses = ("feasible_with_gap", "optimal", "optimal")
    out = reproduction_category(PrototypeClaim.value((4, 900, 60), plan_checked=True), production_label="feasible_with_gap",
                                production_objective=(5, 800, 50), production_stage_statuses=statuses)
    assert out.category == "production_worse"


def test_a_blocking_defect_is_an_exception_with_a_code_and_a_message():
    err = BlockingDefect(dc.BLOCKING_VALUE_BELOW_BOUND, "x")
    assert err.code == dc.BLOCKING_VALUE_BELOW_BOUND and "x" in str(err)


# ---------------------------------------------------------------- C3 (owner, E14 note 2026-10-21): both_open
@pytest.mark.parametrize("label", ["bound_only", "not_run_enumeration_cap", "input_rejected", "backend_unavailable"])
def test_c3_both_open_when_neither_side_has_a_value_or_a_proof(label):
    out = reproduction_category(PrototypeClaim.open(), production_label=label)
    assert out.category == "both_open"


def test_c3_the_design_6_3_example_2026_10_05_r90_l2_open_on_both_sides():
    # prototype: S in {1, 2} (open); production: a bound and no plan
    out = reproduction_category(PrototypeClaim.open(), production_label="bound_only")
    assert out.category == "both_open" and out.prototype_claim_verified is None and out.note == ""


def test_c3_both_open_is_neither_agreement_nor_disagreement():
    both = reproduction_category(PrototypeClaim.open(), production_label="bound_only")
    assert both.agreement is None
    assert reproduction_category(PrototypeClaim.value((5, 800)), production_label="optimal", production_objective=(5, 800)).agreement is True
    assert reproduction_category(PrototypeClaim.value((6, 800)), production_label="optimal", production_objective=(5, 800)).agreement is False


def test_c3_a_production_value_against_an_open_prototype_stays_prototype_open():
    assert reproduction_category(PrototypeClaim.open(), production_label="feasible_with_gap",
                                 production_objective=(2, 100)).category == "prototype_open"


def test_c3_not_comparable_is_gone_and_the_vocabulary_has_seven_categories():
    assert not hasattr(dc, "NotComparable")
    assert set(dc.REPRODUCTION_CATEGORIES) == {"equal", "production_better", "production_worse", "production_open",
                                               "prototype_open", "co_optimal_alternative", "both_open"}
