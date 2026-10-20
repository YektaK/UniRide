"""WP-E11 J2: lower bounds LB0, LB0w, LB_L, LB_S and the infeasibility certificate (design JOINT_DAY_MODEL_DESIGN.md 3).

A bound that is not valid would turn into a false certificate, so the main check is (c): every bound is compared with
the brute-force day optimum of the J3 oracle (``day_oracle.brute_force_day_optimum``, independent arithmetic) on the
whole J3 oracle instance set, which is imported from ``test_exact_day_joint_model`` and not copied. Wave values of
those tiny days come from the pure DP ``dp_wave_values``; the wave values of archived waves come from the wave SP
(AMPL test (d), marked ``requires_ampl``, skipped with an explicit reason when the backend is absent).
"""
from __future__ import annotations

import ast
import csv
from pathlib import Path

import pytest

from test_exact_day_joint_model import ARCS, CAR, DOBLO, HAND, LARGE, RANDOM, _fits, make_wave
from uniride_core.exact import VehicleTypeSpec
from uniride_core.exact import day_bounds as db
from uniride_core.exact.day_instance import READY, build_day_instance
from uniride_core.exact.day_oracle import brute_force_day_optimum

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
GAPS_CSV = RESULTS / "week-2026-10-05-exact" / "wp-e3-goal1-single" / "wave_gaps.csv"
# a Doblo that cannot drive a tour above 25 minutes: the lone So at SoB (tour 30) needs a large vehicle
DOBLO_SHORT = VehicleTypeSpec("doblo", 1, 3, 10, total_capacity=3, tour_limit_minutes=25)


def cell(waves, types):
    inst = build_day_instance(waves, types)
    assert inst.status == READY
    return inst


def five_sw(wave_id, anchor, direction="pickup"):
    # 5 Sw at SwA: a large vehicle carries 4 Sw, a sedan none (H01) -> at least 2 large routes
    return make_wave(wave_id, direction, anchor, [("SwA", "Sw")] * 5, ARCS)


def one_so(wave_id, anchor, direction="pickup"):
    return make_wave(wave_id, direction, anchor, [("SoB", "So")], ARCS)


def one_sw(wave_id, anchor, direction="pickup"):
    return make_wave(wave_id, direction, anchor, [("SwA", "Sw")], ARCS)


def bounds_of(waves, types, large_limit=None):
    inst = cell(waves, types)
    values = db.dp_wave_values(inst)
    return inst, db.compute_day_bounds(inst, k=values.k_any if len(types) == 1 else None, l=values.l,
                               k_any=values.k_any if len(types) == 2 else None, large_limit=large_limit)


# ------------------------------------------------------------------ (a) tier-1 certificate
def test_a_two_concurrent_waves_each_needing_two_large_routes_and_L3_give_a_tier1_certificate():
    waves = [five_sw("w1", 500), five_sw("w2", 500)]
    types = (LARGE, CAR)
    inst = cell(waves, types)
    cert = db.infeasibility_certificate(inst, 3)
    assert cert is not None
    assert cert.status == db.INFEASIBLE_CERTIFIED == "infeasible_certified"
    assert cert.tier == 1 and cert.kind == db.CERT_CAPACITY_FLOOR == "certificate_capacity_floor"
    assert cert.large_limit == 3 and cert.lower_bound == 4
    assert [c.wave_id for c in cert.contributions] == ["w1", "w2"] == list(cert.waves)
    assert all(c.value == 2 and c.proof == db.PROOF_ARITHMETIC for c in cert.contributions)
    assert 500 <= cert.point < 510
    # the claim itself, on the independent oracle: no day plan with at most 3 large vehicles exists, 4 is feasible
    assert brute_force_day_optimum(waves, types, large_limit=3).objective is None
    assert brute_force_day_optimum(waves, types, large_limit=4).objective is not None


def test_a_the_bound_equal_to_L_is_not_a_certificate():
    inst = cell([five_sw("w1", 500), five_sw("w2", 500)], (LARGE, CAR))
    assert db.infeasibility_certificate(inst, 4) is None  # LB_L == L: possibly feasible
    assert db.infeasibility_certificate(inst, 5) is None


def test_a_the_certificate_names_only_the_contributing_waves():
    inst = cell([five_sw("w1", 500), five_sw("w2", 500), one_so("far", 900)], (LARGE, CAR))
    cert = db.infeasibility_certificate(inst, 3)
    assert cert is not None and cert.waves == ("w1", "w2")


def test_a_waves_that_are_not_concurrent_give_no_certificate():
    # busy windows [a, a + cooldown) = [500, 510) and [560, 570) never overlap, so the large vehicle can be reused
    waves = [five_sw("w1", 500), five_sw("w2", 560)]
    inst = cell(waves, (LARGE, CAR))
    assert db.infeasibility_certificate(inst, 2) is None
    assert brute_force_day_optimum(waves, (LARGE, CAR), large_limit=2).objective is not None


@pytest.mark.parametrize("second_anchor,overlap", [(509, True), (510, False)])
def test_cooldown_window_is_half_open(second_anchor, overlap):
    inst = cell([five_sw("w1", 500), five_sw("w2", second_anchor)], (LARGE, CAR))
    assert (db.infeasibility_certificate(inst, 3) is not None) is overlap


def test_tier2_uses_solver_proven_wave_minima_when_the_capacity_floor_is_not_enough():
    waves = [one_so("w1", 500), one_so("w2", 500)]
    types = (LARGE, DOBLO_SHORT)
    inst = cell(waves, types)
    assert db.infeasibility_certificate(inst, 1) is None  # floor is 0 for a type that may carry Sw
    values = db.dp_wave_values(inst)
    assert {w: v.value for w, v in values.l.items()} == {"w1": 1, "w2": 1}
    cert = db.infeasibility_certificate(inst, 1, l=values.l)
    assert cert is not None and cert.tier == 2 and cert.kind == db.CERT_WAVE_MIN_LARGE == "certificate_wave_min_large"
    assert cert.waves == ("w1", "w2") and cert.lower_bound == 2
    assert all(c.proof == db.PROOF_SOLVER for c in cert.contributions)
    assert brute_force_day_optimum(waves, types, large_limit=1).objective is None
    assert brute_force_day_optimum(waves, types, large_limit=2).objective is not None


def test_tier1_is_preferred_when_both_tiers_prove_infeasibility():
    inst = cell([five_sw("w1", 500), five_sw("w2", 500)], (LARGE, CAR))
    cert = db.infeasibility_certificate(inst, 3, l=db.dp_wave_values(inst).l)
    assert cert.tier == 1


# ------------------------------------------------------------------ (b) LB0w > LB0
def test_b_widened_bound_is_larger_than_lb0_and_still_valid():
    # w1 busy [480, 510), w2 busy [470, 500): they overlap, but neither anchor lies in the other's [a, a + cd)
    waves = [one_sw("w1", 500), one_sw("w2", 490)]
    inst, b = bounds_of(waves, (LARGE,))
    assert b.lb0.value == 1 and b.lb0w.value == 2
    assert b.lb0w.value > b.lb0.value
    assert brute_force_day_optimum(waves, (LARGE,)).objective[0] == 2
    assert [c.wave_id for c in b.lb0w.contributions] == ["w1", "w2"]


def test_lb0_counts_every_wave_whose_window_contains_the_anchor():
    waves = [one_sw("w1", 500), one_sw("w2", 505), one_sw("w3", 509), one_sw("w4", 510)]
    _, b = bounds_of(waves, (LARGE,))
    assert b.lb0.value == 3  # w4's window [510, 520) starts when [500, 510) has closed
    assert b.lb0.point == 509 and b.lb0.contributions[0].wave_id == "w1"


# ------------------------------------------------------------------ LB_S
def test_lb_s_is_the_concurrent_route_floor_minus_L():
    waves = [one_so("w1", 500), one_so("w2", 500)]
    types = (LARGE, CAR)
    for L, want in ((0, 2), (1, 1), (2, 0), (5, 0)):
        _, b = bounds_of(waves, types, large_limit=L)
        assert b.lb_s.value == want, (L, b.lb_s)
        oracle = brute_force_day_optimum(waves, types, large_limit=L).objective
        assert oracle is not None and b.lb_s.value <= oracle[0]


# ------------------------------------------------------------------ (e) Doblo floor 0
def test_e_doblo_floor_is_zero_and_sedan_floor_is_the_sw_ceiling():
    waves = [five_sw("w1", 500), one_sw("w2", 500)]
    sedan = db.capacity_floor_large(cell(waves, (LARGE, CAR)))
    doblo = db.capacity_floor_large(cell(waves, (LARGE, DOBLO)))
    assert {w: v.value for w, v in sedan.items()} == {"w1": 2, "w2": 1}
    assert {w: v.value for w, v in doblo.items()} == {"w1": 0, "w2": 0}
    assert all(v.proof == db.PROOF_ARITHMETIC for v in sedan.values())
    assert doblo["w1"].value == 0 and DOBLO.type_id == "doblo"
    assert db.infeasibility_certificate(cell([five_sw("w1", 500), five_sw("w2", 500)], (LARGE, DOBLO)), 0) is None


def test_doblo_minivan_id_has_floor_zero():
    minivan = VehicleTypeSpec("minivan", 1, 3, 10, total_capacity=3)  # production type id of the Doblo (loader)
    floors = db.capacity_floor_large(cell([five_sw("w1", 500)], (LARGE, minivan)))
    assert floors["w1"].value == 0


def test_floor_needs_a_type_pair():
    with pytest.raises(ValueError):
        db.capacity_floor_large(cell([one_sw("w1", 500)], (LARGE,)))
    with pytest.raises(ValueError):
        db.infeasibility_certificate(cell([one_sw("w1", 500)], (LARGE,)), 1)


# ------------------------------------------------------------------ pure DP wave values against the oracle
def test_dp_wave_values_equal_the_single_wave_oracle():
    checked = 0
    for name, waves, types, _ in HAND:
        if len(types) != 1 or not _fits(waves, types):
            continue
        inst = cell(waves, types)
        values = db.dp_wave_values(inst)
        for w in waves:
            oracle = brute_force_day_optimum([w], types).objective
            assert values.k_any[w.wave_id].value == oracle[0], (name, w.wave_id)
            checked += 1
    assert checked >= 20


# ------------------------------------------------------------------ (c) every bound <= brute-force day optimum
def test_c_every_bound_is_at_most_the_day_optimum_on_the_j3_oracle_set():
    feasible = infeasible = certificates = unservable = 0
    for name, waves, types, L in HAND + RANDOM:
        if not _fits(waves, types):
            continue
        oracle = brute_force_day_optimum(waves, types, large_limit=L).objective
        try:
            inst, b = bounds_of(waves, types, L)
        except db.WaveInfeasible:  # a wave without any route set: the oracle must agree that no day exists
            assert oracle is None, name
            unservable += 1
            continue
        assert b.lb0w is None or b.lb0w.value >= b.lb0.value, name
        if len(types) == 1:
            assert oracle is not None, name
            assert b.lb0.value <= b.lb0w.value <= oracle[0], f"{name}: {b.lb0} {b.lb0w} oracle {oracle}"
            feasible += 1
            continue
        cert = b.certificate
        if oracle is None:
            infeasible += 1
            certificates += cert is not None
            continue
        feasible += 1
        assert cert is None, f"{name}: false certificate {cert}"
        assert b.lb_l.value <= L, f"{name}: LB_L {b.lb_l} > L {L} on a feasible cell"
        assert b.lb_s.value <= oracle[0], f"{name}: LB_S {b.lb_s} > optimum {oracle}"
        # the certificate under solver-proven wave minima must not fire either
        assert db.infeasibility_certificate(inst, L, l=db.dp_wave_values(inst).l) is None, name
    assert feasible >= 60 and infeasible >= 5
    assert certificates >= 1  # at least one oracle-infeasible cell is explained by a certificate


# ------------------------------------------------------------------ plumbing
def test_wave_value_from_sp_result_uses_only_proven_values():
    from uniride_core.exact.ampl_backend import SPSolveResult, StageResult

    s1 = StageResult(status="optimal", objective=2, bound=2)
    assert db.wave_value_from_sp(SPSolveResult("w", "feasible_with_gap", stage1=s1, k=3, k_lb=2)).value == 2
    v = db.wave_value_from_sp(SPSolveResult("w", "bound_only", stage1=StageResult(status="feasible_with_gap", objective=4, bound=3), k_lb=3))
    assert v.value == 3 and v.proof == db.PROOF_SOLVER
    with pytest.raises(ValueError):
        db.wave_value_from_sp(SPSolveResult("w", "backend_unavailable"))
    with pytest.raises(ValueError):
        db.wave_value_from_sp(SPSolveResult("w", "infeasible_proven"))


def test_missing_or_negative_wave_values_are_refused():
    inst = cell([one_sw("w1", 500), one_sw("w2", 500)], (LARGE,))
    with pytest.raises(ValueError):
        db.lb0(inst, {"w1": 1})
    with pytest.raises(ValueError):
        db.lb0(inst, {"w1": 1, "w2": -1})


def test_module_imports_no_solver_and_nothing_from_academic_or_api():
    src = (REPO / "uniride_core" / "exact" / "day_bounds.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
            [node.module or ""] if isinstance(node, ast.ImportFrom) else []
        for n in names:
            assert not n.startswith(("amplpy", "highspy", "gurobipy", "academic_benchmark", "optimizer_api")), n
    # ampl_backend may only appear inside a function body (lazy), never at module level
    for node in ast.parse(src).body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert "ampl_backend" not in ast.dump(node)


def test_exports():
    import uniride_core.exact as exact

    for name in ("DayBounds", "InfeasibilityCertificate", "compute_day_bounds"):
        assert name in exact.__all__ and hasattr(exact, name)


# ------------------------------------------------------------------ (d) k_w equals WP-E3 K* (needs AMPL)
def _load_loader():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("exact_archive_loader_j2", REPO / "scripts" / "exact_archive_loader.py")
    loader = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_j2"] = loader
    spec.loader.exec_module(loader)
    return loader


@pytest.mark.requires_ampl
def test_d_k_w_equals_wp_e3_kstar_on_three_archived_waves():
    from test_exact_ampl_backend import _require

    _require("gurobi")  # skips with the reason when AMPL, the solver or its licence is absent; fails on a defect
    from uniride_core.exact import ampl_backend

    with GAPS_CSV.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["fleet"] == "single_4sw5so" and r["R"] == "50"
                and r["status"] == "optimal" and 2 <= int(r["columns"]) <= 400 and int(r["K_star"]) >= 2]
    assert len(rows) >= 3
    camp = _load_loader().load_campaign(RESULTS / "week-2026-10-05-4sw5so")
    by_id = {w.wave_id: w for w in camp.waves_for(50)}
    settings = ampl_backend.SolverSettings(solver="gurobi")
    for row in rows[:3]:
        wave = by_id[row["wave_id"]]
        inst = build_day_instance([wave], camp.fleet_types, service_date=wave.service_date)
        res = ampl_backend.solve_wave(wave, inst.waves[0].enumeration, settings=settings)
        value = db.wave_value_from_sp(res)
        assert value.value == int(row["K_star"]), (row["wave_id"], value, row["K_star"])
        assert value.proof == db.PROOF_SOLVER


# ------------------------------------------------------------------ the widened window must use the SMALLEST tour
def test_widened_window_uses_the_smallest_tour_not_the_longest():
    # wave columns have tours 10 ({P}), 38 ({P,Q} in one route) and 60 ({Q} alone); the best plan serves w1 with the
    # single 38-minute route, so a second wave that ends before it starts can reuse the vehicle: day optimum 1
    d = "D.Kampus"
    arcs = {(d, "P"): 5, ("P", d): 5, (d, "Q"): 30, ("Q", d): 30, ("P", "Q"): 3, ("Q", "P"): 3}
    w1 = make_wave("w1", "pickup", 500, [("P", "Sw"), ("Q", "So")], arcs, ride=60, tour=90)
    w2 = make_wave("w2", "pickup", 452, [("P", "Sw")], arcs, ride=60, tour=90)  # busy [442, 462)
    inst, b = bounds_of([w1, w2], (LARGE,))
    assert sorted({c.tour for c in inst.waves[0].columns}) == [10, 38, 60]
    assert brute_force_day_optimum([w1, w2], (LARGE,)).objective[0] == 1
    assert b.lb0w.value == 1  # a window widened by the longest tour (60) would claim 2 and be invalid
