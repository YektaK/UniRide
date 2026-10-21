"""WP-E11 J11: comparison and reproduction files of the joint day campaign (scripts/report_exact_day_joint.py).

Design JOINT_DAY_MODEL_DESIGN.md sections 5.3 (blocking checks), 6.1 (comparison.csv, reproduction_check.csv) and 6.3
(categories); DECISION_LOG E14 notes of 2026-10-21 (``proof_claim_allowed`` gates every proof; ``both_open``).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("report_exact_day_joint", REPO / "scripts" / "report_exact_day_joint.py")
rep = importlib.util.module_from_spec(_SPEC)
sys.modules["report_exact_day_joint"] = rep
_SPEC.loader.exec_module(rep)

J11 = REPO / "docs" / "paper" / "results" / "week-2026-10-05-exact" / "wp-e11-joint-day"


def joint(**kw):
    row = dict(fleet="large+sedan", date="2026-10-06", R="70", L="2", day_status="optimal", K_or_S="2", large_peak="2",
               total_minutes="1500", car_minutes="300", lb0="", lb0w="", lb_L="", lb_S="", bound_used="2",
               bound_source="solver", unverified_bounds="", proof_claim_allowed="True", checker_ok="True")
    row.update(kw)
    return row


def codes(defects):
    return sorted(code for code, _ in defects)


# ------------------------------------------------------------------ proof gate
def test_unclaimed_optimal_is_not_proven():
    assert rep.is_claimed(joint()) is True
    assert rep.is_claimed(joint(proof_claim_allowed="False")) is False
    assert rep.is_claimed(joint(day_status="feasible_with_gap")) is False  # not a proof label


def test_unclaimed_cell_never_blocks_against_union_or_peaks():
    union = dict(union_status="optimal", union_cars="1", label="proven_over_union_menu")
    row = joint(K_or_S="2", proof_claim_allowed="False")
    assert rep.blocking_defects(row, union_row=union) == []
    assert rep.blocking_defects(joint(fleet="single_4sw5so", L="", K_or_S="6", proof_claim_allowed="False"),
                                peaks={"ga_archive": 5}) == []


def test_unclaimed_infeasible_is_production_open():
    proto = rep.prototype_claim_typed(dict(cs_durum="infeasible", cs_sedan="", cs_dakika=""))
    claimed = rep.reproduction_row(joint(day_status="infeasible_solver_proven", K_or_S="", total_minutes="",
                                         car_minutes=""), proto)
    unclaimed = rep.reproduction_row(joint(day_status="infeasible_solver_proven", K_or_S="", total_minutes="",
                                           car_minutes="", proof_claim_allowed="False"), proto)
    assert claimed["category"] == "equal"
    assert unclaimed["category"] == "production_open"


def test_unclaimed_optimal_does_not_raise_against_a_better_checked_prototype():
    # a checked prototype plan below an unclaimed production value is a described difference, never a proof defect
    proto = rep.PrototypeInput(rep.dc.PrototypeClaim.value((1, 1400), plan_checked=True), 2, "")
    row = rep.reproduction_row(joint(proof_claim_allowed="False"), proto)
    assert row["category"] == "production_worse"
    with pytest.raises(rep.dc.BlockingDefect):
        rep.reproduction_row(joint(), proto)


# ------------------------------------------------------------------ blocking checks (design 5.3)
def test_joint_above_proven_union_blocks():
    union = dict(union_status="optimal", union_cars="1", label="proven_over_union_menu")
    assert codes(rep.blocking_defects(joint(K_or_S="2"), union_row=union)) == [rep.dc.BLOCKING_JOINT_ABOVE_UNION]
    assert rep.blocking_defects(joint(K_or_S="1"), union_row=union) == []


def test_union_menu_infeasible_does_not_block():
    union = dict(union_status="infeasible_for_L", union_cars="", label="both_infeasible_for_L")
    assert rep.blocking_defects(joint(K_or_S="3"), union_row=union) == []


def test_joint_infeasible_against_a_proven_union_plan_blocks():
    union = dict(union_status="optimal", union_cars="2", label="proven_over_union_menu")
    row = joint(day_status="infeasible_certified", K_or_S="", total_minutes="", car_minutes="", large_peak="")
    assert codes(rep.blocking_defects(row, union_row=union)) == [rep.dc.BLOCKING_JOINT_ABOVE_UNION]


def test_joint_k_above_archived_peak_blocks():
    row = joint(fleet="single_4sw5so", L="", K_or_S="6")
    assert codes(rep.blocking_defects(row, peaks={"ga_archive": 5, "wp_e3_routes": 6})) == [rep.dc.BLOCKING_JOINT_ABOVE_PEAK]
    assert rep.blocking_defects(row, peaks={"ga_archive": 6, "wp_e3_routes": 7}) == []


def test_value_below_a_valid_bound_blocks_and_unverified_bounds_are_skipped():
    assert codes(rep.blocking_defects(joint(K_or_S="2", lb_S="3"))) == [rep.dc.BLOCKING_VALUE_BELOW_BOUND]
    assert rep.blocking_defects(joint(K_or_S="2", lb_S="3", unverified_bounds="lb_S")) == []
    assert codes(rep.blocking_defects(joint(fleet="single_4sw5so", L="", K_or_S="4", lb0="5"))) == \
        [rep.dc.BLOCKING_VALUE_BELOW_BOUND]


def test_large_peak_below_lb_l_blocks():
    assert codes(rep.blocking_defects(joint(large_peak="1", lb_L="2"))) == [rep.dc.BLOCKING_VALUE_BELOW_BOUND]


def test_value_below_a_solver_stage1_bound_blocks():
    stages = [dict(solver="gurobi", stage="1", status="optimal", bound_ceil="3")]
    assert codes(rep.blocking_defects(joint(K_or_S="2"), stage_rows=stages)) == [rep.dc.BLOCKING_VALUE_BELOW_BOUND]
    rejected = [dict(solver="gurobi", stage="1", status="rejected", bound_ceil="3")]
    assert rep.blocking_defects(joint(K_or_S="2"), stage_rows=rejected) == []


def test_failed_checker_blocks():
    assert codes(rep.blocking_defects(joint(checker_ok="False"))) == [rep.BLOCKING_CHECKER_FAILED]


# ------------------------------------------------------------------ prototype parsing and categories (design 6.3)
def test_prototype_homogeneous_rows():
    p = rep.prototype_claim_homogeneous(dict(cs_kanit="joint MIP optimal", cs_ortak_K="5", cs_ortak_dakika="984.0"))
    assert p.claim.kind == "value" and p.claim.objective == (5, 984) and p.components == 2
    p = rep.prototype_claim_homogeneous(dict(cs_kanit="seq plan = LB0 (MIP status -9)", cs_ortak_K="4", cs_ortak_dakika=""))
    assert p.claim.objective == (4,) and p.components == 1 and p.note
    with pytest.raises(ValueError):
        rep.prototype_claim_homogeneous(dict(cs_kanit="something else", cs_ortak_K="4", cs_ortak_dakika=""))
    with pytest.raises(ValueError):
        rep.prototype_claim_homogeneous(dict(cs_kanit="joint MIP optimal", cs_ortak_K="5", cs_ortak_dakika="984.5"))


def test_prototype_typed_rows():
    assert rep.prototype_claim_typed(dict(cs_durum="infeasible", cs_sedan="", cs_dakika="")).claim.kind == "infeasible"
    p = rep.prototype_claim_typed(dict(cs_durum="ok", cs_sedan="2", cs_dakika="1510"))
    assert p.claim.objective == (2, 1510) and p.components == 2
    p = rep.prototype_claim_typed(dict(cs_durum="ok (homojen K=3=LB0 planı)", cs_sedan="1", cs_dakika=""))
    assert p.claim.objective == (1,) and p.components == 1
    assert rep.prototype_claim_typed(dict(cs_durum="açık: S in {1, 2}", cs_sedan="", cs_dakika="")).claim.kind == "open"
    with pytest.raises(ValueError):
        rep.prototype_claim_typed(dict(cs_durum="weird", cs_sedan="", cs_dakika=""))


def test_reproduction_categories_on_values():
    proto = rep.prototype_claim_typed(dict(cs_durum="ok", cs_sedan="2", cs_dakika="1510"))
    assert rep.reproduction_row(joint(K_or_S="2", total_minutes="1510"), proto)["category"] == "equal"
    assert rep.reproduction_row(joint(K_or_S="2", total_minutes="1500"), proto)["category"] == "production_better"
    r = rep.reproduction_row(joint(K_or_S="1", total_minutes="1600"), proto)
    assert r["category"] == "production_better" and r["fleet_category"] == "production_better"
    r = rep.reproduction_row(joint(K_or_S="2", total_minutes="1520"), proto)  # unchecked prototype plan: no defect
    assert r["category"] == "production_worse" and r["fleet_category"] == "equal"
    assert r["note"] == rep.dc.NOTE_PROTOTYPE_NOT_VERIFIED


def test_reproduction_open_cases():
    open_proto = rep.prototype_claim_typed(dict(cs_durum="açık: S in {1, 2}", cs_sedan="", cs_dakika=""))
    assert rep.reproduction_row(joint(), open_proto)["category"] == "prototype_open"
    assert rep.reproduction_row(joint(day_status="bound_only", K_or_S="", proof_claim_allowed="False"),
                                open_proto)["category"] == "both_open"


def test_production_infeasible_against_an_unchecked_prototype_value_is_reported_not_guessed():
    proto = rep.prototype_claim_typed(dict(cs_durum="ok", cs_sedan="2", cs_dakika="1510"))
    row = rep.reproduction_row(joint(day_status="infeasible_certified", K_or_S="", total_minutes=""), proto)
    assert row["category"] == "" and row["note"] == rep.NOTE_NEEDS_PROTOTYPE_PLAN_CHECK


# ------------------------------------------------------------------ the committed J11 campaign (results branch)
@pytest.mark.skipif(not (J11 / "day_joint.csv").exists(), reason="J11 results not in this checkout")
def test_committed_campaign_has_no_blocking_defect():
    built = rep.build(J11, REPO / "docs" / "paper" / "results", rep.DEFAULT_PROTOTYPE_DIR)
    assert len(built.comparison) == 140
    assert len(built.reproduction) == 80  # single type + large+sedan; Doblo has no external target (E14 Q1)
    assert built.defects == []
    for row in built.comparison:
        if row["fleet"] == rep.HOMOGENEOUS:
            assert row["ga_archive_checker_violations"] == 0 and row["wp_e3_checker_violations"] == 0
