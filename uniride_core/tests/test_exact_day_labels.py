"""WP-E11 J9b: cell labels of the joint day model (design JOINT_DAY_MODEL_DESIGN.md 4.3; DECISION_LOG E13, E14).

The labels are pure functions of already computed facts (stage results, bounds, the checker verdict and the cross-check
verdict); nothing is solved here. Every label of design 4.3 has a test, and a cell is never allowed to claim a proof in a
paper table without a two-solver agreement (E14).
"""
from __future__ import annotations

import pytest

from uniride_core.exact.ampl_backend import StageResult
from uniride_core.exact.day_bounds import (
    CERT_CAPACITY_FLOOR,
    CERT_WAVE_MIN_LARGE,
    INFEASIBLE_CERTIFIED,
    PROOF_ARITHMETIC,
    PROOF_SOLVER,
    PROOF_UNVERIFIED,
    BoundResult,
    Contribution,
    DayBounds,
    InfeasibilityCertificate,
)
from uniride_core.exact.day_labels import CROSSCHECK_VERDICTS, LABELS, label_cell
from uniride_core.exact.highs_backend import BOUND_ABOVE_INCUMBENT, DayStage, DaySolveResult, _finish

COMMON = dict(solver="highs", solver_options="threads=1", time_limit=600.0)


def sr(status="optimal", obj=None, bound=None, source="solver", msg=None, reason=None, timing=False):
    return StageResult(status=status, stop_reason=reason or ("optimal" if status == "optimal" else "wall_limit"),
                       objective=obj, bound_ceil=bound, bound_source=source, solver_message=msg, timing_dependent=timing)


def day(*stage_results, mode="homogeneous"):
    stages = [DayStage(i + 1, "m", "o", "sha", r, {}) for i, r in enumerate(stage_results)]
    return _finish(mode, stages, None, dict(COMMON))


def solved(mode="homogeneous", k=5, **kw):
    n = 3 if mode == "typed" else 2
    return day(*[sr("optimal", k if i == 0 else 100, k if i == 0 else 100, **kw) for i in range(n)], mode=mode)


def bound(value, proofs, point=525):
    return BoundResult(value, point, tuple(Contribution(f"w{i}", 1, p) for i, p in enumerate(proofs)))


def cert(tier=1):
    kind = CERT_CAPACITY_FLOOR if tier == 1 else CERT_WAVE_MIN_LARGE
    return InfeasibilityCertificate(INFEASIBLE_CERTIFIED, tier, kind, 1, 2, 525, (Contribution("w0", 1, PROOF_ARITHMETIC),))


def label(result, **kw):
    kw.setdefault("enumeration_complete", True)
    kw.setdefault("crosscheck", "agree")
    kw.setdefault("checker_ok", True)
    return label_cell(result=result, **kw)


# ---------------------------------------------------------------- vocabulary (design 4.3)
def test_the_vocabulary_is_the_design_vocabulary():
    assert set(LABELS) == {"optimal", "optimal_stage1_by_bound", "feasible_with_gap", "bound_only", "infeasible_certified",
                           "infeasible_solver_proven", "not_run_enumeration_cap", "rejected", "input_rejected",
                           "backend_unavailable"}
    assert set(CROSSCHECK_VERDICTS) == {"agree", "blocking", "inconclusive", "not_run"}


# ---------------------------------------------------------------- one test per label
def test_label_optimal():
    out = label(solved())
    assert out.label == "optimal" and out.proof_claim_allowed


def test_label_optimal_for_a_typed_cell_with_three_stages():
    assert label(solved("typed", k=2)).label == "optimal"


def test_label_optimal_stage1_by_bound():
    # stage 1 stopped on the wall limit with incumbent 5, but LB0w = 5 is proven: the stage-1 value is optimal by that bound
    res = day(sr("feasible_with_gap", 5, 4, timing=True), sr("optimal", 90, 90))
    out = label(res, bounds=DayBounds(lb0=bound(4, [PROOF_SOLVER]), lb0w=bound(5, [PROOF_SOLVER, PROOF_ARITHMETIC])))
    assert out.label == "optimal_stage1_by_bound"
    assert (out.bound_used, out.bound_source, out.bound_proof) == (5, "lb0w", PROOF_SOLVER)
    assert out.stage_statuses == ("feasible_with_gap", "optimal")  # later stages carry their own status
    assert "timing_dependent" in out.flags


def test_label_optimal_stage1_by_bound_for_a_typed_cell_uses_lb_s():
    res = day(sr("feasible_with_gap", 2, 1), sr("feasible_with_gap", 90, 80), sr("feasible_with_gap", 40, 30), mode="typed")
    out = label(res, bounds=DayBounds(lb_s=bound(2, [PROOF_SOLVER])))
    assert out.label == "optimal_stage1_by_bound" and out.bound_source == "lb_s"


def test_label_feasible_with_gap_names_the_best_bound_and_its_source():
    res = day(sr("feasible_with_gap", 6, 4, timing=True), sr("feasible_with_gap", 90, 80))
    out = label(res, bounds=DayBounds(lb0=bound(5, [PROOF_SOLVER]), lb0w=bound(5, [PROOF_SOLVER])))
    assert out.label == "feasible_with_gap"
    assert out.bound_used == 5 and out.bound_source in ("lb0", "lb0w") and out.bound_proof == PROOF_SOLVER


def test_the_solver_bound_wins_when_it_is_the_best():
    res = day(sr("feasible_with_gap", 6, 5), sr("feasible_with_gap", 90, 80))
    out = label(res, bounds=DayBounds(lb0=bound(3, [PROOF_SOLVER]), lb0w=bound(4, [PROOF_SOLVER])))
    assert (out.label, out.bound_used, out.bound_source) == ("feasible_with_gap", 5, "solver")
    assert {c.name for c in out.bounds_considered} == {"solver", "lb0", "lb0w"}


def test_label_bound_only():
    out = label(day(sr("bound_only", None, 3), sr("skipped_no_stage1_incumbent")), checker_ok=None)
    assert out.label == "bound_only" and out.bound_used == 3


def test_label_infeasible_certified_tier_1_and_2():
    for tier, name in ((1, CERT_CAPACITY_FLOOR), (2, CERT_WAVE_MIN_LARGE)):
        out = label(None, bounds=DayBounds(certificate=cert(tier)), crosscheck="not_run", checker_ok=None)
        assert out.label == "infeasible_certified" and out.certificate_tier == tier
        assert out.bound_source == "certificate" and out.reason == name


def test_a_certificate_wins_over_a_solver_that_stopped_without_a_plan():
    out = label(day(sr("bound_only", None, 0), sr("skipped_no_stage1_incumbent")), bounds=DayBounds(certificate=cert(1)),
                checker_ok=None)
    assert out.label == "infeasible_certified"


def test_label_infeasible_solver_proven():
    out = label(day(sr("infeasible_proven", reason="infeasible")), checker_ok=None)
    assert out.label == "infeasible_solver_proven" and out.proof_claim_allowed and out.certificate_tier is None


def test_label_not_run_enumeration_cap():
    out = label(None, enumeration_complete=False, checker_ok=None, crosscheck="not_run")
    assert out.label == "not_run_enumeration_cap" and not out.proof_claim_allowed


def test_not_run_enumeration_cap_wins_over_anything_else():
    out = label(solved(), enumeration_complete=False, bounds=DayBounds(certificate=cert(1)))
    assert out.label == "not_run_enumeration_cap"


def test_label_rejected_when_the_solver_result_is_rejected():
    res = day(sr("rejected", reason="solver_failure"), sr("skipped_no_stage1_incumbent"))
    assert label(res, checker_ok=None).label == "rejected"


def test_label_rejected_when_the_independent_checker_fails():
    out = label(solved(), checker_ok=False)
    assert out.label == "rejected" and out.reason == "checker_failed" and not out.proof_claim_allowed


def test_label_rejected_when_the_two_solvers_disagree():
    for res in (solved(), day(sr("infeasible_proven", reason="infeasible"))):
        out = label(res, crosscheck="blocking", checker_ok=True)
        assert out.label == "rejected" and out.reason == "crosscheck_disagreement" and not out.proof_claim_allowed


def test_label_rejected_when_a_certificate_contradicts_a_plan():
    out = label(solved(), bounds=DayBounds(certificate=cert(1)))
    assert out.label == "rejected" and out.reason == "certificate_contradicts_plan"


def test_label_rejected_when_the_value_is_below_a_proven_bound():
    out = label(solved(k=4), bounds=DayBounds(lb0=bound(5, [PROOF_SOLVER])))
    assert out.label == "rejected" and out.reason == "value_below_bound"


def test_label_input_rejected_and_backend_unavailable():
    rejected = DaySolveResult(status="input_rejected", note="x", **COMMON)
    unavailable = DaySolveResult(status="backend_unavailable", note="highspy unavailable", **COMMON)
    assert label(rejected, checker_ok=None, crosscheck="not_run").label == "input_rejected"
    assert label(unavailable, checker_ok=None, crosscheck="not_run").label == "backend_unavailable"


# ---------------------------------------------------------------- E14: the cross-check gate (red test 6)
@pytest.mark.parametrize("verdict", ["not_run", "inconclusive"])
def test_optimal_without_a_cross_check_agreement_is_not_paper_eligible(verdict):
    out = label(solved(), crosscheck=verdict)
    assert out.label == "optimal"  # the design label is kept; the proof claim is withheld, with the reason
    assert not out.proof_claim_allowed and out.proof_claim_reason == f"crosscheck_{verdict}"
    assert out.crosscheck_status == verdict


def test_optimal_with_a_cross_check_agreement_is_paper_eligible():
    out = label(solved(), crosscheck="agree")
    assert out.proof_claim_allowed and out.proof_claim_reason == "crosscheck_agree"


@pytest.mark.parametrize("verdict", ["not_run", "inconclusive"])
def test_infeasible_solver_proven_and_by_bound_and_tier_2_need_the_agreement_too(verdict):
    res = day(sr("infeasible_proven", reason="infeasible"))
    assert not label(res, crosscheck=verdict, checker_ok=None).proof_claim_allowed
    by_bound = day(sr("feasible_with_gap", 5, 4), sr("optimal", 90, 90))
    assert not label(by_bound, crosscheck=verdict, bounds=DayBounds(lb0w=bound(5, [PROOF_SOLVER]))).proof_claim_allowed
    assert not label(None, crosscheck=verdict, bounds=DayBounds(certificate=cert(2)), checker_ok=None).proof_claim_allowed


def test_a_tier_1_certificate_is_checkable_by_hand_and_needs_no_cross_check():
    assert label(None, crosscheck="not_run", bounds=DayBounds(certificate=cert(1)), checker_ok=None).proof_claim_allowed


@pytest.mark.parametrize("res, checker_ok", [
    (day(sr("feasible_with_gap", 6, 4), sr("feasible_with_gap", 90, 80)), True),
    (day(sr("bound_only", None, 3), sr("skipped_no_stage1_incumbent")), None),
])
def test_open_cells_make_no_proof_claim_even_with_an_agreement(res, checker_ok):
    out = label(res, checker_ok=checker_ok)
    assert not out.proof_claim_allowed and out.proof_claim_reason == "not_a_proof_label"


def test_a_cross_check_verdict_outside_the_vocabulary_is_refused():
    with pytest.raises(ValueError, match="cross-check"):
        label(solved(), crosscheck="yes")


def test_a_cell_with_a_plan_needs_the_checker_verdict():
    with pytest.raises(ValueError, match="checker"):
        label(solved(), checker_ok=None)


# ---------------------------------------------------------------- bounds: source, proof tag, unverified visibility
def test_unverified_bound_contributions_are_visible_and_never_used():
    res = day(sr("feasible_with_gap", 5, 3), sr("feasible_with_gap", 90, 80))
    out = label(res, bounds=DayBounds(lb0=bound(4, [PROOF_SOLVER]), lb0w=bound(5, [PROOF_SOLVER, PROOF_UNVERIFIED])))
    assert out.unverified_bounds == (("lb0w", "w1"),)
    unverified = [c for c in out.bounds_considered if c.name == "lb0w"][0]
    assert unverified.proof == PROOF_UNVERIFIED and unverified.value == 5
    assert out.bound_used == 4 and out.bound_source == "lb0"  # the verified bound, not the unverified 5
    assert out.label == "feasible_with_gap"  # an unverified 5 cannot make the incumbent 5 optimal


def test_an_incumbent_below_an_unverified_bound_is_a_flag_not_a_rejection():
    out = label(day(sr("feasible_with_gap", 4, 3), sr("feasible_with_gap", 90, 80)),
                bounds=DayBounds(lb0w=bound(5, [PROOF_UNVERIFIED])))
    assert out.label == "feasible_with_gap" and "value_below_unverified_bound" in out.flags


def test_arithmetic_only_bounds_carry_the_arithmetic_tag():
    res = day(sr("feasible_with_gap", 3, 1), sr("feasible_with_gap", 90, 80))
    out = label(res, bounds=DayBounds(lb0=bound(2, [PROOF_ARITHMETIC])))
    assert (out.bound_used, out.bound_source, out.bound_proof) == (2, "lb0", PROOF_ARITHMETIC)


def test_trivial_zero_solver_bound_is_arithmetic():
    out = label(day(sr("bound_only", None, 0, source="trivial_zero"), sr("skipped_no_stage1_incumbent")), checker_ok=None)
    assert (out.bound_used, out.bound_source, out.bound_proof) == (0, "trivial_zero", PROOF_ARITHMETIC)


# ---------------------------------------------------------------- flags
def test_a_bound_above_incumbent_message_surfaces_as_a_flag():
    msg = f"{BOUND_ABOVE_INCUMBENT}: ceil(bound - 1e-6)=6 > incumbent=5; bound clipped to the incumbent"
    out = label(day(sr("optimal", 5, 5, msg=msg), sr("optimal", 90, 90)))
    assert out.label == "optimal" and "bound_above_incumbent:stage1" in out.flags


def test_no_flag_without_the_message():
    assert not [f for f in label(solved()).flags if f.startswith("bound_above_incumbent")]


def test_non_lexicographic_and_timing_dependent_are_reported():
    first = sr("feasible_with_gap", 6, 4, timing=True)
    second = StageResult(status="optimal", objective=90, bound_ceil=90, bound_source="solver", non_lexicographic=True,
                         stop_reason="optimal")
    out = label(day(first, second))
    assert "non_lexicographic" in out.flags and "timing_dependent" in out.flags


# ---------------------------------------------------------------- review round 1, E1: by-bound needs a verified section 3 bound
CLIP_MSG = f"{BOUND_ABOVE_INCUMBENT}: ceil(bound - 1e-6)=6 > incumbent=5; bound clipped to the incumbent"


def test_p1_a_clipped_solver_bound_never_makes_a_stage_1_value_optimal_by_bound():
    # highs_backend clips a contradicting bound to the incumbent and leaves the clip note: bound 5 == incumbent 5 is no proof
    res = day(sr("feasible_with_gap", 5, 5, msg=CLIP_MSG), sr("feasible_with_gap", 90, 80))
    out = label(res)
    assert out.label == "feasible_with_gap" and out.label != "optimal_stage1_by_bound"
    assert not out.proof_claim_allowed
    clipped = [c for c in out.bounds_considered if c.name == "solver"][0]
    assert clipped.proof == PROOF_UNVERIFIED  # visible, never used
    assert out.bound_source != "solver"


def test_p2_an_unclipped_solver_bound_equal_to_the_incumbent_is_not_a_section_3_bound():
    res = day(sr("feasible_with_gap", 5, 5), sr("feasible_with_gap", 90, 80))
    for bounds in (None, DayBounds(lb0=bound(3, [PROOF_SOLVER]), lb0w=bound(4, [PROOF_SOLVER]))):
        out = label(res, bounds=bounds)
        assert out.label == "feasible_with_gap" and not out.proof_claim_allowed


def test_p2_the_typed_case_needs_lb_s_not_the_solver_bound():
    res = day(sr("feasible_with_gap", 2, 2), sr("feasible_with_gap", 90, 80), sr("feasible_with_gap", 40, 30), mode="typed")
    assert label(res).label == "feasible_with_gap"
    assert label(res, bounds=DayBounds(lb_s=bound(1, [PROOF_SOLVER]))).label == "feasible_with_gap"


def test_p3_a_section_3_bound_that_ties_the_solver_bound_is_reported_as_the_source():
    by_bound = label(day(sr("feasible_with_gap", 5, 5), sr("optimal", 90, 90)), bounds=DayBounds(lb0w=bound(5, [PROOF_SOLVER])))
    assert by_bound.label == "optimal_stage1_by_bound" and by_bound.bound_source == "lb0w"
    gap = label(day(sr("feasible_with_gap", 6, 5), sr("feasible_with_gap", 90, 80)), bounds=DayBounds(lb0w=bound(5, [PROOF_SOLVER])))
    assert gap.label == "feasible_with_gap" and (gap.bound_used, gap.bound_source) == (5, "lb0w")


# ---------------------------------------------------------------- E2: a contradicting solver bound withholds the proof claim
def test_e2_a_bound_above_incumbent_flag_on_any_stage_withholds_the_proof_claim():
    for first, second in ((sr("optimal", 5, 5, msg=CLIP_MSG), sr("optimal", 90, 90)),
                          (sr("optimal", 5, 5), sr("optimal", 90, 90, msg=CLIP_MSG))):
        out = label(day(first, second), crosscheck="agree")
        assert out.label == "optimal" and any(f.startswith("bound_above_incumbent") for f in out.flags)
        assert not out.proof_claim_allowed and out.proof_claim_reason == "bound_above_incumbent"


def test_e2_the_infeasible_and_certificate_labels_also_lose_the_claim_when_a_stage_is_flagged():
    out = label(day(sr("infeasible_proven", reason="infeasible", msg=CLIP_MSG)), checker_ok=None)
    assert out.label == "infeasible_solver_proven" and not out.proof_claim_allowed
    assert out.proof_claim_reason == "bound_above_incumbent"


# ---------------------------------------------------------------- C1: the certificate is checked, not trusted
def _cert(tier, proofs, kind=None, limit=1, lower=2):
    kind = kind or (CERT_CAPACITY_FLOOR if tier == 1 else CERT_WAVE_MIN_LARGE)
    return InfeasibilityCertificate(INFEASIBLE_CERTIFIED, tier, kind, limit, lower, 525,
                                    tuple(Contribution(f"w{i}", 1, p) for i, p in enumerate(proofs)))


def _cert_label(c):
    return label(None, bounds=DayBounds(certificate=c), checker_ok=None)


def test_p4_a_tier_2_certificate_with_an_unverified_contribution_is_rejected():
    out = _cert_label(_cert(2, [PROOF_SOLVER, PROOF_UNVERIFIED]))
    assert out.label == "rejected" and out.reason == "certificate_invalid" and not out.proof_claim_allowed


def test_p5_a_tier_1_certificate_with_a_solver_contribution_is_rejected():
    out = _cert_label(_cert(1, [PROOF_ARITHMETIC, PROOF_SOLVER]))
    assert out.label == "rejected" and out.reason == "certificate_invalid" and not out.proof_claim_allowed


@pytest.mark.parametrize("bad", [_cert(1, [PROOF_UNVERIFIED]), _cert(3, [PROOF_ARITHMETIC]),
                                 _cert(1, [PROOF_ARITHMETIC], kind=CERT_WAVE_MIN_LARGE),
                                 _cert(2, [PROOF_SOLVER], kind=CERT_CAPACITY_FLOOR),
                                 _cert(1, [PROOF_ARITHMETIC], limit=2, lower=2)])
def test_inconsistent_certificates_are_rejected(bad):
    assert _cert_label(bad).label == "rejected"


@pytest.mark.parametrize("good", [_cert(1, [PROOF_ARITHMETIC, PROOF_ARITHMETIC]), _cert(2, [PROOF_SOLVER, PROOF_ARITHMETIC])])
def test_consistent_certificates_are_accepted(good):
    assert _cert_label(good).label == "infeasible_certified"


# ---------------------------------------------------------------- C2 (owner, E14 note 2026-10-21): wave values are cross-checked too
BY_BOUND = day(sr("feasible_with_gap", 5, 4), sr("optimal", 90, 90))
BY_BOUND_BOUNDS = DayBounds(lb0w=bound(5, [PROOF_SOLVER]))


def test_the_wave_values_verdict_vocabulary_is_the_crosscheck_vocabulary():
    with pytest.raises(ValueError, match="wave-values"):
        label(solved(), wave_values_crosscheck="yes")


@pytest.mark.parametrize("day_verdict", ["inconclusive", "not_run", "agree"])
def test_c2_by_bound_rests_on_the_checked_plan_and_the_wave_values_not_on_a_day_agreement(day_verdict):
    # J5 gives day 'agree' only when every stage is proven on both solvers; stage 1 of a by-bound cell never is, so a
    # realistic day verdict is 'inconclusive'. The claim must not depend on it.
    ok = label(BY_BOUND, bounds=BY_BOUND_BOUNDS, crosscheck=day_verdict, wave_values_crosscheck="agree")
    assert ok.label == "optimal_stage1_by_bound" and ok.proof_claim_allowed
    assert ok.proof_claim_reason == "checked_plan_and_wave_values_agree" and ok.wave_values_crosscheck_status == "agree"


@pytest.mark.parametrize("day_verdict", ["inconclusive", "not_run", "agree"])
@pytest.mark.parametrize("wave", ["not_run", "inconclusive"])
def test_c2_by_bound_without_a_wave_values_agreement_makes_no_claim(day_verdict, wave):
    out = label(BY_BOUND, bounds=BY_BOUND_BOUNDS, crosscheck=day_verdict, wave_values_crosscheck=wave)
    assert out.label == "optimal_stage1_by_bound" and not out.proof_claim_allowed
    assert out.proof_claim_reason == f"wave_values_crosscheck_{wave}"


def test_c2_by_bound_with_an_arithmetic_only_bound_needs_no_wave_verdict():
    arithmetic = DayBounds(lb0w=bound(5, [PROOF_ARITHMETIC, PROOF_ARITHMETIC]))
    out = label(BY_BOUND, bounds=arithmetic, crosscheck="inconclusive", wave_values_crosscheck="not_run")
    assert out.label == "optimal_stage1_by_bound" and out.bound_proof == PROOF_ARITHMETIC
    assert out.proof_claim_allowed and out.proof_claim_reason == "arithmetic_bound"


def test_c2_by_bound_with_a_day_disagreement_is_rejected_and_a_failed_checker_too():
    assert label(BY_BOUND, bounds=BY_BOUND_BOUNDS, crosscheck="blocking", wave_values_crosscheck="agree").label == "rejected"
    out = label(BY_BOUND, bounds=BY_BOUND_BOUNDS, crosscheck="inconclusive", wave_values_crosscheck="agree", checker_ok=False)
    assert out.label == "rejected" and not out.proof_claim_allowed


def test_c2_by_bound_with_a_bound_above_incumbent_flag_makes_no_claim():
    msg = f"{BOUND_ABOVE_INCUMBENT}: ceil(bound - 1e-6)=6 > incumbent=5; bound clipped to the incumbent"
    res = day(sr("feasible_with_gap", 5, 4), sr("optimal", 90, 90, msg=msg))
    out = label(res, bounds=BY_BOUND_BOUNDS, crosscheck="inconclusive", wave_values_crosscheck="agree")
    assert out.label == "optimal_stage1_by_bound" and not out.proof_claim_allowed
    assert out.proof_claim_reason == "bound_above_incumbent"


def test_c2_a_tier_2_certificate_needs_the_wave_values_agreement_and_no_day_crosscheck():
    c = DayBounds(certificate=cert(2))
    out = label(None, bounds=c, crosscheck="not_run", wave_values_crosscheck="agree", checker_ok=None)
    assert out.label == "infeasible_certified" and out.proof_claim_allowed
    assert out.proof_claim_reason == "wave_values_crosscheck_agree"  # no day MIP was proven: the day verdict is not asked
    for wave in ("not_run", "inconclusive"):
        out = label(None, bounds=c, crosscheck="agree", wave_values_crosscheck=wave, checker_ok=None)
        assert not out.proof_claim_allowed and out.proof_claim_reason == f"wave_values_crosscheck_{wave}"


def test_c2_a_tier_1_certificate_needs_neither_gate():
    out = label(None, bounds=DayBounds(certificate=cert(1)), crosscheck="not_run", wave_values_crosscheck="not_run", checker_ok=None)
    assert out.proof_claim_allowed and out.proof_claim_reason == "arithmetic_certificate"


def test_c2_optimal_and_solver_proven_infeasible_are_gated_by_the_day_verdict_only():
    assert label(solved(), crosscheck="agree", wave_values_crosscheck="not_run").proof_claim_allowed
    res = day(sr("infeasible_proven", reason="infeasible"))
    assert label(res, crosscheck="agree", wave_values_crosscheck="not_run", checker_ok=None).proof_claim_allowed
    assert not label(solved(), crosscheck="not_run", wave_values_crosscheck="agree").proof_claim_allowed


@pytest.mark.parametrize("res, bounds, ok", [(solved(), None, True), (BY_BOUND, BY_BOUND_BOUNDS, True),
                                              (day(sr("infeasible_proven", reason="infeasible")), None, None),
                                              (None, DayBounds(certificate=cert(2)), None)])
def test_c2_a_blocking_wave_values_verdict_rejects_the_cell(res, bounds, ok):
    out = label(res, bounds=bounds, crosscheck="agree", wave_values_crosscheck="blocking", checker_ok=ok)
    assert out.label == "rejected" and out.reason == "wave_values_crosscheck_disagreement" and not out.proof_claim_allowed


def test_c2_open_labels_still_make_no_claim_with_both_verdicts_agreeing():
    res = day(sr("feasible_with_gap", 6, 4), sr("feasible_with_gap", 90, 80))
    out = label(res, crosscheck="agree", wave_values_crosscheck="agree")
    assert not out.proof_claim_allowed and out.proof_claim_reason == "not_a_proof_label"
