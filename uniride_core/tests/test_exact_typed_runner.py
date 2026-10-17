"""WP-E4a part 2/3 (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 1.5, 3, 4, 6, 8, 9): the typed option runner
``scripts/run_exact_typed_menus.py``.

Pure parts (option plan, xbase guard, evaluation, gaps, CSV schema, absence exit code) run without AMPL.
Tests that solve carry ``requires_ampl`` and are skipped with a reason ONLY when the backend reports
``backend_unavailable``; any other probe failure fails.
"""
from __future__ import annotations

import csv
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
LARGE_SEDAN = RESULTS / "week-2026-10-05-fleet-rerun-large-sedan"
DOBLO = RESULTS / "week-2026-10-05-fleet-rerun-doblo-cap3"
SCRIPT = REPO / "scripts" / "run_exact_typed_menus.py"
for _p in (REPO / "optimizer_api", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from uniride_core.exact import certification as cert  # noqa: E402
from uniride_core.exact import gaps  # noqa: E402

PEAK = "2026-10-05:pickup:525"


def _load_script():
    if "run_exact_typed_menus" in sys.modules:
        return sys.modules["run_exact_typed_menus"]
    spec = importlib.util.spec_from_file_location("run_exact_typed_menus", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_exact_typed_menus"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load_script()


@pytest.fixture(scope="module")
def ls_ctx(runner):
    return runner.load_fleet_context(LARGE_SEDAN)


@pytest.fixture(scope="module")
def doblo_ctx(runner):
    return runner.load_fleet_context(DOBLO)


def _archive(directory, date="2026-10-05", ride=90):
    arcs_doc = json.loads((directory / f"{date}_R{ride}.matrix.json").read_text(encoding="utf-8"))
    menu = json.loads((directory / f"{date}_R{ride}.menu_options.json").read_text(encoding="utf-8"))
    return arcs_doc, menu


def _wave(ctx, wave_id, ride=90):
    return next(w for w in ctx.campaign.waves_for(ride) if w.wave_id == wave_id)


def _option(menu, wave_id, option_id):
    wave = next(w for w in menu["waves"] if w["waveId"] == wave_id)
    return next(o for o in wave["options"] if o["optionId"] == option_id)


def _typed_routes(option):
    return [(r["vehicleType"], tuple(r["studentIds"])) for r in option["routes"]]


def _ride(wave, seq) -> int:
    """Independent ride minutes: pickup = tour minus its first arc, dropoff = tour minus its closing arc."""
    index = {occ: i + 1 for i, occ in enumerate(wave.occurrence_ids)}
    path = [0] + [index[o] for o in seq] + [0]
    arcs = [wave.matrix[x][y] for x, y in zip(path, path[1:])]
    return sum(arcs[1:]) if wave.direction == "pickup" else sum(arcs[:-1])


def _fake_sp(wave, typed_routes, minimize, *, status="optimal", k_lb=None, d_lb=None, d_lb_free=None, d=None, k=None,
             solver="gurobi", peak=False):
    """An ``SPSolveResult`` standing in for the typed solver (no AMPL)."""
    from uniride_core.exact.ampl_backend import ExpandedRoute, SPSolveResult, StageResult

    true_k, true_d, _ = cert.recompute_typed_objective(wave, typed_routes, minimize)
    k = true_k if k is None else k
    d = true_d if d is None else d
    routes = tuple(ExpandedRoute(t, i, 0, tuple(s), cert.tour_cost(wave, s), _ride(wave, s), cert.tour_cost(wave, s))
                   for i, (t, s) in enumerate(typed_routes))
    s1 = StageResult("stage1", "optimal", "optimal", objective=k, bound=float(k), bound_ceil=k, bound_source="solver",
                     wall_seconds=0.1)
    s2 = StageResult("stage2", "optimal", "optimal", objective=d, bound=float(d), bound_ceil=d_lb or d,
                     bound_source="solver", k_fix=k, wall_seconds=0.1)
    free = StageResult("free", "optimal", "optimal", objective=d, bound=float(d), bound_ceil=d_lb_free or d,
                       bound_source="solver", wall_seconds=0.1)
    return SPSolveResult(wave.wave_id, status, stage1=s1, stage2=s2, free=free, k=k, d=d,
                         k_lb=k if k_lb is None else k_lb, k_lb_source="solver_bound", d_lb=d if d_lb is None else d_lb,
                         d_lb_free=d if d_lb_free is None else d_lb_free, routes=routes, peak=peak, column_count=10,
                         solver=solver, solver_version="fake")


ENUM = {"model": "SP", "columns": 10, "labels": 20, "seconds": 0.01, "cap_fired": None}


def _eval(runner, ctx, wave, option_id, kind, quota, ga_opt, arcs_doc, sp, highs=None):
    return runner.evaluate_option(wave, kind, quota, ga_opt, arcs_doc, sp, ctx=ctx, enum_info=ENUM, highs=highs)


# ---------- option plan and the xbase guard ----------
def test_option_plan_is_base_then_quota_range_min_maxl_legs_4(runner, ls_ctx, doblo_ctx):
    big = next(w for w in ls_ctx.campaign.waves_for(90) if w.legs >= 5)
    assert [(o, k, q) for o, k, q in runner.option_plan(ls_ctx, big)] == [
        ("base", "base", None), ("q0", "q", 0), ("q1", "q", 1), ("q2", "q", 2), ("q3", "q", 3)]  # max L = 3
    assert [o for o, _, _ in runner.option_plan(doblo_ctx, big)] == ["base", "q0", "q1", "q2"]  # max L = 2
    small = next(w for w in ls_ctx.campaign.waves_for(90) if w.legs == 1)
    assert [o for o, _, _ in runner.option_plan(ls_ctx, small)] == ["base", "q0", "q1"]  # min(maxL, legs, 4)


def test_plan_matches_the_ga_menu_of_the_archive(runner, ls_ctx, doblo_ctx):
    for ctx, directory in ((ls_ctx, LARGE_SEDAN), (doblo_ctx, DOBLO)):
        menus = {}
        for wave in ctx.campaign.waves_for(90):
            menu = menus.setdefault(wave.service_date, _archive(directory, wave.service_date)[1])
            archived = [o["optionId"] for o in next(w for w in menu["waves"] if w["waveId"] == wave.wave_id)["options"]]
            assert [o for o, _, _ in runner.option_plan(ctx, wave)] == archived


def test_xbase_fails_closed_when_the_fixed_type_has_a_total_capacity(runner, ls_ctx, doblo_ctx):
    assert runner.xbase_guard(ls_ctx.fixed) is None and runner.xbase_guard(doblo_ctx.fixed) is None
    capped = dataclasses.replace(ls_ctx.fixed, total_capacity=8)
    assert runner.xbase_guard(capped) == "XBASE_FIXED_TYPE_HAS_TOTAL_CAPACITY"
    ctx = dataclasses.replace(ls_ctx, fixed=capped)
    wave = ls_ctx.campaign.waves_for(90)[0]
    arcs_doc, menu = _archive(LARGE_SEDAN)
    ev = _eval(runner, ctx, wave, "base", "base", None, _option(menu, wave.wave_id, "base"), arcs_doc,
               runner.ab.SPSolveResult(wave.wave_id, "not_run"))
    assert ev["row"]["status"] == "input_rejected" and "TOTAL_CAPACITY" in ev["row"]["note"]
    assert any("XBASE_FIXED_TYPE_HAS_TOTAL_CAPACITY" in e for e in ev["errors"])


# ---------- evaluation: a GA option as the exact solution ----------
def test_ga_quota_option_as_exact_certifies_with_zero_gap(runner, ls_ctx):
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    opt = _option(menu, PEAK, "q2")
    sp = _fake_sp(wave, _typed_routes(opt), "sedan", peak=True)
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, opt, arcs_doc, sp)
    row = ev["row"]
    assert ev["errors"] == [], ev["errors"]
    assert row["option"] == "q2" and row["quota"] == 2 and row["k_kind"] == "K_m"
    assert row["K_GA"] == row["K_star"] == sum(r["vehicleType"] == "sedan" for r in opt["routes"])
    assert row["dK"] == 0 and row["gD"] == 0 and row["comparison"] == "compared"
    assert row["exact_certified"] is True and row["ga_recertified"] is True and row["ga_cert_archived"] is True
    assert row["ga_cert_agree"] is True and row["objective_check"] == "ok" and row["exact_le_ga"] is True
    assert row["ga_protocol"] == "native" and row["ga_seed"] == 42 and row["ga_commit"] == "f29aa3d"
    assert row["ga_dirty_tree"] is False and row["fleet"] == "large+sedan"
    assert ev["exact_routes"]["option"] == "q2" and ev["exact_routes"]["certified"] is True


def test_base_option_uses_the_single_type_path(runner, ls_ctx):
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    opt = _option(menu, PEAK, "base")
    sp = _fake_sp(wave, [("large", tuple(r["studentIds"])) for r in opt["routes"]], None, peak=True, k=len(opt["routes"]))
    ev = _eval(runner, ls_ctx, wave, "base", "base", None, opt, arcs_doc, sp)
    assert ev["errors"] == [], ev["errors"]
    assert ev["row"]["k_kind"] == "K" and ev["row"]["K_GA"] == len(opt["routes"]) and ev["row"]["quota"] is None


def _all_large_ga_option(menu):
    """A feasible GA answer with K_m = 0: the all-large baseline routes presented as a quota-4 option."""
    ga = json.loads(json.dumps(_option(menu, PEAK, "base")))
    ga.update(optionId="q4", kind="quota", quota=4)
    for r in ga["routes"]:
        r["vehicleType"] = "large"
    return ga


def test_exact_worse_than_ga_is_blocking_only_when_optimal(runner, ls_ctx):
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    ga = _all_large_ga_option(menu)
    worse = _typed_routes(_option(menu, PEAK, "q3"))  # K_m >= 1 > K_m,GA = 0
    assert sum(t == "sedan" for t, _ in worse) >= 1
    ev = _eval(runner, ls_ctx, wave, "q4", "q", 4, ga, arcs_doc, _fake_sp(wave, worse, "sedan", peak=True))
    assert ev["row"]["exact_le_ga"] is False
    assert any("exceeds the GA route count" in e for e in ev["errors"]), ev["errors"]
    # the same exact result with a stage that is not proven optimal is not a blocking violation
    ev = _eval(runner, ls_ctx, wave, "q4", "q", 4, ga, arcs_doc,
               _fake_sp(wave, worse, "sedan", status="feasible_with_gap", peak=True))
    assert not any("exceeds" in e for e in ev["errors"]), ev["errors"]
    assert ev["row"]["exact_le_ga"] is None
    # equal K_m, larger D: the second key of the lexicographic order
    assert any("exceeds the GA duration" in m for m in gaps.exact_vs_ga_violations(
        exact_optimal=True, k_star=2, d_star=100, k_ga=2, d_ga=90, k_lb=1, d_lb=None))


def test_evaluation_blocks_an_exact_option_worse_than_the_ga_option(runner, ls_ctx):
    """GA option = the all-large baseline routes as a quota-4 style answer; exact = a worse feasible partition."""
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    ga = _option(menu, PEAK, "q2")
    exact_routes = _typed_routes(ga)
    # exact claims optimal with the GA's routes but a D that is one minute worse than the recomputation would be an
    # objective mismatch (rejected); instead lie about the solver objective only through k: K_m one higher
    sp = _fake_sp(wave, exact_routes, "sedan", peak=True, k=sum(t == "sedan" for t, _ in exact_routes) + 1)
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, ga, arcs_doc, sp)
    assert ev["row"]["status"] == "rejected" and ev["row"]["objective_check"] == "mismatch"
    assert any("objective cross-check" in e for e in ev["errors"])


def test_exact_infeasible_with_ga_feasible_is_a_blocking_mismatch(runner, ls_ctx):
    from uniride_core.exact.ampl_backend import SPSolveResult

    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    sp = SPSolveResult(wave.wave_id, "infeasible_proven", peak=True)
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, _option(menu, PEAK, "q2"), arcs_doc, sp)
    assert ev["row"]["comparison"] == "exact_infeasible_ga_feasible"
    assert any("model or semantics mismatch" in e for e in ev["errors"])


def test_ga_infeasible_with_exact_feasible_is_labelled_not_blocking(runner, ls_ctx):
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    ga = _option(menu, PEAK, "q0")
    assert ga["status"] == "skipped_infeasible" and ga["success"] is False
    exact = _typed_routes(_option(menu, PEAK, "q2"))
    sp = _fake_sp(wave, exact, "sedan", peak=True)
    # the fake exact solution has 2 large routes; judge it against quota 2 (the plan's q) while the GA option is q0
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, ga, arcs_doc, sp)
    assert ev["row"]["comparison"] == "ga_infeasible_exact_feasible"
    assert ev["row"]["K_GA"] is None and ev["row"]["dK"] is None
    assert not any("GA re-certificate" in e for e in ev["errors"])  # an infeasible GA answer is not re-certified as a route set
    assert ev["errors"] == [], ev["errors"]


def test_both_infeasible_is_labelled_and_not_an_error(runner, ls_ctx):
    from uniride_core.exact.ampl_backend import SPSolveResult

    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    ev = _eval(runner, ls_ctx, wave, "q0", "q", 0, _option(menu, PEAK, "q0"), arcs_doc,
               SPSolveResult(wave.wave_id, "infeasible_proven", peak=True))
    assert ev["row"]["comparison"] == "both_infeasible" and ev["errors"] == []


def test_exact_certificate_failure_marks_the_option_rejected(runner, ls_ctx):
    """The exact routes of q3 judged against quota 1 break the quota: rejected, never repaired."""
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    ga = _option(menu, PEAK, "q3")
    routes = _typed_routes(ga)
    assert sum(t == "large" for t, _ in routes) >= 2
    sp = _fake_sp(wave, routes, "sedan", peak=True)
    ev = _eval(runner, ls_ctx, wave, "q1", "q", 1, ga, arcs_doc, sp)
    assert ev["row"]["status"] == "rejected" and ev["row"]["exact_certified"] is False
    assert any("quota" in e for e in ev["errors"])


def test_highs_disagreement_blocks_a_typed_option(runner, ls_ctx):
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    opt = _option(menu, PEAK, "q2")
    routes = _typed_routes(opt)
    sp = _fake_sp(wave, routes, "sedan", peak=True)
    same = dataclasses.replace(sp, solver="highs")
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, opt, arcs_doc, sp, highs=same)
    assert ev["row"]["highs_agrees"] is True and ev["errors"] == []
    other = dataclasses.replace(same, d=same.d + 1, stage2=dataclasses.replace(same.stage2, objective=same.d + 1))
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, opt, arcs_doc, sp, highs=other)
    assert ev["row"]["highs_agrees"] is False and any("HiGHS" in e for e in ev["errors"])
    other_k = dataclasses.replace(same, k=same.k + 1)
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, opt, arcs_doc, sp, highs=other_k)
    assert ev["row"]["highs_agrees"] is False and any("HiGHS" in e for e in ev["errors"])


def test_highs_finding_a_solution_where_gurobi_proved_infeasible_blocks(runner, ls_ctx):
    from uniride_core.exact.ampl_backend import SPSolveResult

    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    gurobi = SPSolveResult(wave.wave_id, "infeasible_proven", peak=True)
    feasible = _fake_sp(wave, _typed_routes(_option(menu, PEAK, "q2")), "sedan", solver="highs", peak=True)
    ev = _eval(runner, ls_ctx, wave, "q0", "q", 0, _option(menu, PEAK, "q0"), arcs_doc, gurobi, highs=feasible)
    assert any("HiGHS" in e for e in ev["errors"])
    agree = SPSolveResult(wave.wave_id, "infeasible_proven", peak=True, solver="highs")
    ev = _eval(runner, ls_ctx, wave, "q0", "q", 0, _option(menu, PEAK, "q0"), arcs_doc, gurobi, highs=agree)
    assert ev["errors"] == [] and ev["row"]["highs_agrees"] is True


# ---------- typed gap arithmetic on a hand example ----------
def test_typed_gap_arithmetic_on_a_hand_example():
    # GA: K_m = 3, D = 100.  Exact: K_m* = 2 (stage-1 bound 2), D* = 90 under K_m = 2, D_LB_free = 80.
    g = gaps.gap_fields(k_ga=3, d_ga=100, k_lb=2, k_star=2, d_lb=90, d_lb_free=80)
    assert g["dK"] == 1  # K_m,GA - K_m_LB
    assert g["gD"] is None and g["gD_note"] == gaps.NOT_COMPARABLE  # the GA already has more routes of the type
    assert g["gD_free"] == pytest.approx((100 - 80) / 80)
    # equal K_m: gD = (D_GA - D_LB) / D_LB
    g = gaps.gap_fields(k_ga=2, d_ga=99, k_lb=2, k_star=2, d_lb=90, d_lb_free=80)
    assert g["dK"] == 0 and g["gD"] == pytest.approx(9 / 90) and g["gD_note"] == "comparable"
    # stage 1 not proven: K_m_LB only from the solver bound, no gD
    g = gaps.gap_fields(k_ga=3, d_ga=100, k_lb=1, k_star=None, d_lb=None, d_lb_free=80)
    assert g["dK"] == 2 and g["gD"] is None and g["gD_note"] == "unavailable_stage1_not_proven"


# ---------- CSV schema ----------
def test_option_csv_has_one_row_per_option_with_the_required_columns(runner, ls_ctx, tmp_path):
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    opt = _option(menu, PEAK, "q2")
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, opt, arcs_doc, _fake_sp(wave, _typed_routes(opt), "sedan", peak=True))
    path = tmp_path / "option_gaps.csv"
    runner.write_option_csv(path, [ev["row"], ev["row"]])
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 2 and list(rows[0].keys()) == list(runner.OPTION_CSV_FIELDS)
    required = {"fleet", "date", "R", "wave_id", "option", "quota", "students", "peak", "model", "columns", "K_GA",
                "K_LB", "K_star", "D_GA", "D_LB", "D_star", "D_LB_free", "dK", "gD", "gD_free", "status",
                "stage1_stop_reason", "stage2_stop_reason", "free_stop_reason", "stage1_timing_dependent",
                "stage2_non_lexicographic", "solver", "solve_seconds", "ga_protocol", "ga_seed", "ga_commit",
                "ga_dirty_tree", "comparison", "k_kind", "exact_le_ga", "highs_agrees"}
    assert required <= set(runner.OPTION_CSV_FIELDS)
    assert rows[0]["fleet"] == "large+sedan" and rows[0]["option"] == "q2" and rows[0]["quota"] == "2"


def test_replay_csv_has_one_row_per_cell(runner, tmp_path):
    ctx = runner.load_fleet_context(DOBLO)
    rows = runner.replay_rows(ctx)
    assert len(rows) == 60 and all(r["label"] in runner.replay.MATCH_LABELS for r in rows)
    runner.write_replay_csv(tmp_path / "replay.csv", rows)
    back = list(csv.DictReader((tmp_path / "replay.csv").open(encoding="utf-8")))
    assert len(back) == 60 and list(back[0].keys()) == list(runner.REPLAY_CSV_FIELDS)


# ---------- stored routes ----------
def test_stored_exact_option_routes_recertify_through_the_typed_bridge(runner, ls_ctx):
    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    opt = _option(menu, PEAK, "q2")
    ev = _eval(runner, ls_ctx, wave, "q2", "q", 2, opt, arcs_doc, _fake_sp(wave, _typed_routes(opt), "sedan", peak=True))
    stored = json.loads(json.dumps(ev["exact_routes"]))
    assert runner.recertify_stored_option(wave, stored, arcs_doc, ls_ctx)["is_feasible"] is True
    stored["routes"][0]["type_id"] = "sedan" if stored["routes"][0]["type_id"] == "large" else "large"
    assert runner.recertify_stored_option(wave, stored, arcs_doc, ls_ctx)["is_feasible"] is False


# ---------- absence ----------
def test_runner_exits_3_without_ampl_and_writes_nothing(tmp_path):
    out = tmp_path / "out"
    env = dict(os.environ, UNIRIDE_AMPL_DIR=str(tmp_path))
    res = subprocess.run([sys.executable, str(SCRIPT), "--fleets", "large+doblo_cap3", "--rides", "90", "--limit", "1",
                          "--out", str(out)], cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
    assert res.returncode == 3, res.stderr[-500:]
    assert "backend unavailable" in res.stderr.lower()
    assert not out.exists()
    assert str(tmp_path) not in res.stderr + res.stdout


def test_runner_refuses_an_out_directory_outside_docs_paper_results(tmp_path):
    res = subprocess.run([sys.executable, str(SCRIPT), "--out", str(REPO / "scripts" / "x")], cwd=REPO,
                         capture_output=True, text=True, timeout=300)
    assert res.returncode == 2 and "docs/paper/results" in res.stderr


# ---------- AMPL ----------
_PROBE: dict = {}


def _require(solver: str) -> None:
    from uniride_core.exact import ampl_backend

    if solver not in _PROBE:
        try:
            _PROBE[solver] = ampl_backend.probe_backend(solver)
        except Exception as exc:  # noqa: BLE001 - a backend defect must fail, never skip
            _PROBE[solver] = exc
    res = _PROBE[solver]
    if isinstance(res, Exception):
        pytest.fail(f"AMPL/{solver} probe raised (backend defect, not absence): {type(res).__name__}: {res}")
    if not res.available:
        pytest.skip(f"AMPL/{solver} unavailable: {res.reason}")
    assert (res.status, res.k, res.d, res.routes) == ("optimal", 1, 10, 1), f"AMPL/{solver} probe solve wrong: {res}"


def _small_waves(ctx, ride, limit=6, count=6):
    waves = [w for w in ctx.campaign.waves_for(ride) if 3 <= w.legs <= limit]
    return sorted(waves, key=lambda w: (-w.legs, w.wave_id))[:count]


@pytest.mark.requires_ampl
@pytest.mark.parametrize("which", ["ls", "doblo"])
def test_typed_exact_options_equal_the_brute_force_oracle_on_archived_waves(runner, which, ls_ctx, doblo_ctx):
    """Quota respected and (K_m*, D*) equal to the independent brute-force optimum for every q."""
    from uniride_core.exact import ampl_backend as ab
    from uniride_core.exact.brute_force import brute_force_optimum
    from uniride_core.exact.route_enumeration import enumerate_wave

    _require("gurobi")
    ctx = ls_ctx if which == "ls" else doblo_ctx
    types = [ctx.fixed, ctx.minimise]
    checked = 0
    with ab.AmplSession(ab.SolverSettings(solver="gurobi")) as session:
        for wave in _small_waves(ctx, 90):
            enum = enumerate_wave(wave, types)
            for opt_id, kind, q in runner.option_plan(ctx, wave):
                if kind != "q":
                    continue
                sp = ab.solve_wave(wave, enum, minimize_type=ctx.minimise.type_id, quota=(ctx.fixed.type_id, q),
                                   session=session)
                oracle = brute_force_optimum(wave.direction, wave.matrix, wave.classes, types, max_ride=wave.max_ride_minutes,
                                             max_tour=wave.max_tour_minutes, minimize_type=ctx.minimise.type_id,
                                             quota=(ctx.fixed.type_id, q))
                if oracle.objective is None:
                    assert sp.status == "infeasible_proven", (wave.wave_id, q, sp.status)
                    continue
                assert sp.status == "optimal", (wave.wave_id, q, sp.status)
                assert (sp.k, sp.d) == oracle.objective, (wave.wave_id, q)
                assert sum(r.type_id == ctx.fixed.type_id for r in sp.routes) <= q, (wave.wave_id, q)
                checked += 1
    assert checked >= 6


def _subset_ids(runner):
    """Small waves of two dates (never the 20-leg peak wave: HiGHS needs minutes there)."""
    ctx = runner.load_fleet_context(DOBLO)
    waves = [w for w in ctx.campaign.waves_for(90) if 2 <= w.legs <= 5]
    first = [w.wave_id for w in waves if w.service_date == "2026-10-05"][:2]
    second = [w.wave_id for w in waves if w.service_date == "2026-10-06"][:1]
    assert len(first) == 2 and len(second) == 1
    return first + second


@pytest.mark.requires_ampl
def test_typed_option_run_writes_valid_manifest_csv_and_stored_routes(runner, tmp_path):
    protocol = runner.protocol
    _require("gurobi")
    _require("highs")
    ids = _subset_ids(runner)
    out = tmp_path / "out"
    rc = runner.main(["--fleets", "large+doblo_cap3", "--rides", "90", "--wave-ids", ",".join(ids), "--out", str(out)])
    assert rc == 0
    manifest = json.loads((out / "exact_manifest.json").read_text(encoding="utf-8"))
    assert protocol.validate_manifest(manifest) == []
    assert manifest["work_package"] == "WP-E4a" and not manifest["blocking_errors"]
    assert manifest["source_campaigns"]["large+doblo_cap3"]["path"] == "docs/paper/results/week-2026-10-05-fleet-rerun-doblo-cap3"
    assert manifest["solver"]["name"] == "gurobi" and manifest["verification_solver"]["name"] == "highs"
    assert manifest["python_provenance"]["uniride_core"] == "uniride_core/__init__.py"
    assert manifest["options"]["jobs"] == 1
    history = manifest["run_history"]  # B2: one invocation, serial, every unit solved, no retry, no failed stage row
    assert len(history["invocations"]) == 1 and history["invocations"][0]["jobs"] == 1
    assert history["invocations"][0]["cache_used"] is False
    assert history["units_planned"] == history["units_solved"] == len(history["units"]) == 2  # two dates
    assert history["units_from_cache"] == 0 and history["retries"] == 0 and history["timeout_kills"] == 0
    assert history["stopped_early"] is False and all(u["failed_stage_rows"] == [] for u in history["units"])
    assert all(u["source"] == "solved" and u["attempts"] == 1 for u in history["units"])
    assert "this invocation only" in manifest["total_wall_seconds_scope"]
    rows = list(csv.DictReader((out / "option_gaps.csv").open(encoding="utf-8")))
    ctx = runner.load_fleet_context(DOBLO)
    planned = sum(len(runner.option_plan(ctx, w)) for w in ctx.campaign.waves_for(90) if w.wave_id in ids)
    assert len(rows) == planned and {r["option"] for r in rows} >= {"base", "q0", "q1"}
    for r in rows:
        assert r["status"] in ("optimal", "infeasible_proven") and r["highs_agrees"] in ("True", "")
        assert r["ga_protocol"] == "native" and r["ga_seed"] == "42" and r["ga_commit"] == "f29aa3d"
        if r["status"] == "optimal":
            assert r["exact_certified"] == "True" and r["objective_check"] == "ok" and r["exact_le_ga"] == "True"
            assert r["ga_cert_agree"] == "True"
    replay = list(csv.DictReader((out / "replay.csv").open(encoding="utf-8")))
    assert len(replay) == 60  # the replay gate always covers the whole fleet: 5 dates x 4 R x L0, L1, L2
    stored = json.loads((out / manifest["exact_routes"]["file"]).read_text(encoding="utf-8"))
    arcs = {d: json.loads((DOBLO / f"{d}_R90.matrix.json").read_text(encoding="utf-8"))
            for d in {e["service_date"] for e in stored["waves"]}}
    waves = {w.wave_id: w for w in ctx.campaign.waves_for(90)}
    assert stored["waves"]
    for entry in stored["waves"]:
        assert runner.recertify_stored_option(waves[entry["wave_id"]], entry, arcs[entry["service_date"]], ctx)["is_feasible"]


@pytest.mark.requires_ampl
def test_parallel_workers_give_the_same_results_as_a_serial_run(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner.wg, "_git_state", lambda out, repo=None: ("a" * 40, False))  # the cache needs a clean tree
    _require("gurobi")
    ids = _subset_ids(runner)
    common = ["--fleets", "large+doblo_cap3", "--rides", "90", "--wave-ids", ",".join(ids), "--no-highs-verify"]
    cache_a, cache_b = tmp_path / "cache_a", tmp_path / "cache_b"
    assert runner.main(common + ["--jobs", "1", "--cache-dir", str(cache_a), "--out", str(tmp_path / "a")]) == 0
    assert runner.main(common + ["--jobs", "2", "--cache-dir", str(cache_b), "--out", str(tmp_path / "b")]) == 0
    assert len(list(cache_a.glob("*.json"))) == len(list(cache_b.glob("*.json"))) == 2  # two (fleet, R, date) units
    timing = {"enumeration_seconds", "solve_seconds", "highs_seconds"}

    def stable(path):
        return [{k: v for k, v in r.items() if k not in timing} for r in csv.DictReader(path.open(encoding="utf-8"))]

    assert stable(tmp_path / "a" / "option_gaps.csv") == stable(tmp_path / "b" / "option_gaps.csv")
    assert (tmp_path / "a" / "exact_routes.json").read_bytes() == (tmp_path / "b" / "exact_routes.json").read_bytes()
    # resume: a finished unit comes from the cache and is never solved again
    def boom(*args, **kwargs):
        raise AssertionError("a cached unit was solved again")

    runner_solve = runner._solve_unit
    runner._solve_unit, runner._run_worker = boom, boom
    try:
        assert runner.main(common + ["--jobs", "2", "--cache-dir", str(cache_b), "--out", str(tmp_path / "c")]) == 0
    finally:
        runner._solve_unit = runner_solve
    assert stable(tmp_path / "c" / "option_gaps.csv") == stable(tmp_path / "b" / "option_gaps.csv")


@pytest.mark.requires_ampl
def test_determinism_five_typed_waves_solved_twice_with_gurobi(runner, ls_ctx):
    from uniride_core.exact import ampl_backend as ab
    from uniride_core.exact.route_enumeration import enumerate_wave

    _require("gurobi")
    waves = sorted(ls_ctx.campaign.waves_for(90), key=lambda w: (-w.legs, w.wave_id))[:5]
    types = [ls_ctx.fixed, ls_ctx.minimise]

    def snapshot(session):
        out = []
        for w in waves:
            enum = enumerate_wave(w, types)
            for q in (0, 1, 2):
                sp = ab.solve_wave(w, enum, minimize_type="sedan", quota=("large", q), peak=w.legs == 20, session=session)
                stages = [(s.status, s.objective, s.bound, s.bound_ceil, s.stop_reason)
                          for s in (sp.stage1, sp.stage2, sp.free) if s is not None]
                out.append((w.wave_id, q, enum.model, enum.column_count, enum.label_count, sp.status, sp.k, sp.d, sp.k_lb,
                            sp.d_lb, sp.d_lb_free, sp.selection, stages))
        return out

    with ab.AmplSession(ab.SolverSettings(solver="gurobi")) as session:
        first = snapshot(session)
    with ab.AmplSession(ab.SolverSettings(solver="gurobi")) as session:
        second = snapshot(session)
    assert first == second
    assert any(row[5] == "optimal" for row in first)


def test_historical_fleet_archives_are_refused_as_a_ga_source(runner):
    for tail in (("week-2026-10-05-fleet",), ("week-2026-10-05-fleet", "extra", "minivan-cap3")):
        with pytest.raises(runner.loader.CampaignRefused):
            runner.load_fleet_context(RESULTS.joinpath(*tail))


RESULTS_DIR = RESULTS / "week-2026-10-05-exact" / "wp-e4a-typed-options"


@pytest.mark.skipif(not (RESULTS_DIR / "exact_manifest.json").exists(), reason="campaign results not committed yet")
def test_committed_campaign_results_are_consistent_and_recertify_without_a_solver(runner):
    """The committed WP-E4a results: valid manifest, no blocking error, every stored exact option re-certifies."""
    import hashlib

    manifest = json.loads((RESULTS_DIR / "exact_manifest.json").read_text(encoding="utf-8"))
    assert runner.protocol.validate_manifest(manifest) == [] and manifest["blocking_errors"] == []
    assert manifest["dirty_working_tree"] is False and manifest["work_package"] == "WP-E4a"
    routes_file = RESULTS_DIR / manifest["exact_routes"]["file"]
    assert hashlib.sha256(routes_file.read_bytes()).hexdigest() == manifest["exact_routes"]["sha256"]
    stored = json.loads(routes_file.read_text(encoding="utf-8"))
    rows = list(csv.DictReader((RESULTS_DIR / "option_gaps.csv").open(encoding="utf-8")))
    assert len(rows) == len(manifest["waves"]) == 1872
    assert len({(r["fleet"], r["date"], r["R"], r["wave_id"], r["option"]) for r in rows}) == len(rows)
    assert {r["ga_protocol"] for r in rows} == {"native"} and {r["ga_seed"] for r in rows} == {"42"}
    assert all(r["exact_le_ga"] == "True" for r in rows if r["status"] == "optimal" and r["comparison"] == "compared")
    assert not any(r["comparison"] == "exact_infeasible_ga_feasible" for r in rows)
    replay_rows = list(csv.DictReader((RESULTS_DIR / "replay.csv").open(encoding="utf-8")))
    assert len(replay_rows) == 120 and all(r["label"] in runner.replay.MATCH_LABELS for r in replay_rows)
    ctxs = {name: runner.load_fleet_context(path) for name, path in runner.SOURCES.items()}
    waves = {name: {(w.service_date, ride, w.wave_id): w for ride in c.campaign.rides for w in c.campaign.waves_for(ride)}
             for name, c in ctxs.items()}
    arcs: dict = {}
    assert manifest["exact_routes"]["options"] == len(stored["waves"]) and stored["waves"]
    for entry in stored["waves"]:
        name = entry["fleet"]
        key = (name, entry["service_date"], entry["R"])
        if key not in arcs:
            arcs[key] = json.loads((runner.SOURCES[name] / f"{entry['service_date']}_R{entry['R']}.matrix.json")
                                   .read_text(encoding="utf-8"))
        wave = waves[name][(entry["service_date"], entry["R"], entry["wave_id"])]
        result = runner.recertify_stored_option(wave, entry, arcs[key], ctxs[name])
        assert result["is_feasible"] is True, (name, entry["wave_id"], entry["option"], result["violations"][:2])


# ======================= DUZELT round 1 =======================
# ---------- B1: the cache is off by default and keyed on everything a result depends on ----------
BASE_KEY = dict(commit="a" * 40, dirty=False,
                solver={"name": "gurobi", "version": "Gurobi 13.0.3", "option_string": "mip:bestbound=1 lim:time=60 lim:work=20"},
                verification={"name": "highs", "version": "HiGHS 1.15.1", "option_string": "mip:bestbound=1 lim:time=60"},
                ampl_version="AMPL 20260809", source_sha={"large+sedan": "1" * 64, "large+doblo_cap3": "2" * 64},
                highs_verify=True)
UNIT = ("large+doblo_cap3", 90, "2026-10-05", ("w1", "w2"))


def test_cache_is_off_unless_a_directory_is_given(runner):
    assert runner.parse_args([]).cache_dir == ""
    assert runner.parse_args([]).stop_on_error is True


@pytest.mark.parametrize("name,change", [
    ("commit", dict(commit="b" * 40)),
    ("dirty", dict(dirty=True)),
    ("solver option string", dict(solver={**BASE_KEY["solver"], "option_string": "mip:bestbound=1 lim:time=90 lim:work=20"})),
    ("solver version", dict(solver={**BASE_KEY["solver"], "version": "Gurobi 13.0.4"})),
    ("verification option string", dict(verification={**BASE_KEY["verification"], "option_string": "mip:bestbound=1 lim:time=90"})),
    ("verification version", dict(verification={**BASE_KEY["verification"], "version": "HiGHS 1.16"})),
    ("ampl version", dict(ampl_version="AMPL 20270101")),
    ("source manifest sha", dict(source_sha={**BASE_KEY["source_sha"], "large+sedan": "3" * 64})),
    ("highs flag", dict(highs_verify=False)),
])
def test_cache_key_changes_with_every_ingredient(runner, name, change):
    base = runner.cache_key(UNIT, **BASE_KEY)
    assert runner.cache_key(UNIT, **BASE_KEY) == base  # deterministic
    assert runner.cache_key(UNIT, **{**BASE_KEY, **change}) != base, name


def test_cache_key_changes_with_unit_and_wave_ids(runner):
    base = runner.cache_key(UNIT, **BASE_KEY)
    assert runner.cache_key(("large+sedan",) + UNIT[1:], **BASE_KEY) != base
    assert runner.cache_key(UNIT[:3] + (("w1",),), **BASE_KEY) != base
    assert runner.cache_key(UNIT[:1] + (70,) + UNIT[2:], **BASE_KEY) != base


def _cache_ctx(tmp_path, **override):
    return {"dir": str(tmp_path / "cache"), **{k: v for k, v in BASE_KEY.items() if k != "highs_verify"}, **override}


def _fake_unit_result(tag="solved"):
    return {"rows": [{"tag": tag}], "option_docs": [], "errors": [], "route_docs": [], "matrix_sha": {}, "slice_sha": {},
            "caps_fired": 0, "failed_stage_rows": []}


def test_cache_file_is_used_only_under_its_own_key(runner, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "_solve_unit", lambda unit, hv, peaks, sessions=None: calls.append(unit) or _fake_unit_result(len(calls) and f"call{len(calls)}"))
    args = runner.parse_args(["--cache-dir", str(tmp_path / "cache")])
    ctx = _cache_ctx(tmp_path)
    first = runner._solve_units([UNIT], args, set(), None, None, ctx)
    assert len(calls) == 1 and first[0]["unit_run"]["source"] == "solved"
    again = runner._solve_units([UNIT], args, set(), None, None, ctx)
    assert len(calls) == 1 and again[0]["unit_run"]["source"] == "cache" and again[0]["rows"] == first[0]["rows"]
    # another commit or other options: a different key, the cached file is not used
    runner._solve_units([UNIT], args, set(), None, None, _cache_ctx(tmp_path, commit="b" * 40))
    assert len(calls) == 2
    runner._solve_units([UNIT], args, set(), None, None,
                        _cache_ctx(tmp_path, solver={**BASE_KEY["solver"], "option_string": "lim:time=90 mip:bestbound=1"}))
    assert len(calls) == 3


def test_stale_cache_file_under_the_expected_name_but_another_stored_key_is_ignored(runner, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "_solve_unit", lambda unit, hv, peaks, sessions=None: calls.append(unit) or _fake_unit_result())
    args = runner.parse_args([])
    ctx = _cache_ctx(tmp_path)
    key = runner._cache_key_for(ctx, UNIT, True)
    path = runner._cache_file(ctx, UNIT, key)
    path.write_text(json.dumps({"cache_key": "0" * 64, "result": _fake_unit_result("STALE")}), encoding="utf-8")
    res = runner._solve_units([UNIT], args, set(), None, None, ctx) if False else runner._solve_units(
        [UNIT], runner.parse_args(["--highs-verify"]), set(), None, object(), ctx)
    assert len(calls) == 1 and res[0]["rows"] == [{"tag": "solved"}]
    assert runner._cache_read(path, key)["rows"] == [{"tag": "solved"}]  # overwritten under the right key
    assert runner._cache_read(path, "f" * 64) is None


def test_no_cache_context_never_reads_or_writes_a_file(runner, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "_solve_unit", lambda unit, hv, peaks, sessions=None: calls.append(unit) or _fake_unit_result())
    monkeypatch.chdir(tmp_path)
    runner._solve_units([UNIT], runner.parse_args([]), set(), None, None, None)
    runner._solve_units([UNIT], runner.parse_args([]), set(), None, None, None)
    assert len(calls) == 2 and list(tmp_path.iterdir()) == []


@pytest.mark.requires_ampl
def test_cache_refused_on_a_dirty_tree(runner, tmp_path, monkeypatch):
    _require("gurobi")
    _require("highs")
    monkeypatch.setattr(runner.wg, "_git_state", lambda out, repo=None: ("a" * 40, True))
    rc = runner.main(["--fleets", "large+doblo_cap3", "--rides", "90", "--wave-ids", _subset_ids(runner)[0],
                      "--cache-dir", str(tmp_path / "cache"), "--out", str(tmp_path / "out")])
    assert rc == 2 and not (tmp_path / "out").exists()


# ---------- stop on error (serial) ----------
def test_serial_run_stops_after_the_first_unit_with_a_blocking_error(runner, monkeypatch):
    units = [("large+doblo_cap3", 90, d, ("w",)) for d in ("2026-10-05", "2026-10-06", "2026-10-07")]
    calls = []

    def fake(unit, hv, peaks, sessions=None):
        calls.append(unit[2])
        res = _fake_unit_result()
        if unit[2] == "2026-10-06":
            res["errors"] = ["boom"]
        return res

    monkeypatch.setattr(runner, "_solve_unit", fake)
    out = runner._solve_units(units, runner.parse_args([]), set(), None, None, None)
    assert calls == ["2026-10-05", "2026-10-06"] and len(out) == 2
    calls.clear()
    out = runner._solve_units(units, runner.parse_args(["--no-stop-on-error"]), set(), None, None, None)
    assert len(calls) == 3 and len(out) == 3


# ---------- P2: worker timeout / kill / single retry (fake worker) ----------
class _FakeProc:
    plan: list = []
    launched: list = []

    def __init__(self, cmd):
        self.cmd = cmd
        self.pid = 4200 + len(_FakeProc.launched)
        _FakeProc.launched.append(self)
        self.behaviour = _FakeProc.plan.pop(0)

    def wait(self, timeout=None):
        if self.behaviour == "timeout" and timeout is not None:
            self.behaviour = "killed"
            raise subprocess.TimeoutExpired(self.cmd, timeout)
        if self.behaviour == "killed":
            return -9
        if self.behaviour == "ok":
            out = Path(self.cmd[self.cmd.index("--worker-out") + 1])
            out.write_text(json.dumps(_fake_unit_result("worker")), encoding="utf-8")
            return 0
        return self.behaviour  # an integer exit code


@pytest.fixture()
def fake_worker(runner, monkeypatch):
    _FakeProc.plan, _FakeProc.launched = [], []
    killed = []
    monkeypatch.setattr(runner.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(runner, "_kill_tree", lambda proc: killed.append(proc.pid))
    return killed


def test_hung_worker_is_killed_and_relaunched_once_with_identical_settings(runner, fake_worker, tmp_path):
    _FakeProc.plan = ["timeout", "ok"]
    args = runner.parse_args(["--unit-timeout", "5"])
    res = runner._run_worker(UNIT, args, {"p"}, tmp_path / "u.json")
    assert res["rows"] == [{"tag": "worker"}]
    assert res["unit_run"] == {"attempts": 2, "timeout_kills": 1, "exit_codes": ["timeout", 0]}
    assert fake_worker == [_FakeProc.launched[0].pid]  # only the process this runner started, by its own PID
    assert _FakeProc.launched[0].cmd == _FakeProc.launched[1].cmd  # identical settings


def test_worker_that_hangs_twice_fails_the_unit_with_no_third_launch(runner, fake_worker, tmp_path):
    _FakeProc.plan = ["timeout", "timeout", "ok"]
    res = runner._run_worker(UNIT, runner.parse_args(["--unit-timeout", "5"]), set(), tmp_path / "u.json")
    assert res["failed"] and "exceeded" in res["failed"] and res["errors"] and res["rows"] == []
    assert res["unit_run"]["attempts"] == 2 and res["unit_run"]["timeout_kills"] == 2 and len(_FakeProc.launched) == 2
    assert len(fake_worker) == 2


def test_worker_crash_is_retried_once_and_backend_unavailable_is_not(runner, fake_worker, tmp_path):
    _FakeProc.plan = [1, "ok"]
    res = runner._run_worker(UNIT, runner.parse_args([]), set(), tmp_path / "u.json")
    assert res["unit_run"] == {"attempts": 2, "timeout_kills": 0, "exit_codes": [1, 0]}
    _FakeProc.plan, _FakeProc.launched = [3, "ok"], []
    res = runner._run_worker(UNIT, runner.parse_args([]), set(), tmp_path / "u2.json")
    assert res["unavailable"] and len(_FakeProc.launched) == 1


# ---------- B2: run_history ----------
def test_run_history_records_source_attempts_kills_and_failed_stage_rows_verbatim(runner):
    args = runner.parse_args(["--jobs", "3", "--unit-timeout", "100"])
    units = [("large+sedan", 50, "2026-10-05", ("a", "b")), ("large+sedan", 50, "2026-10-06", ("c",)),
             ("large+doblo_cap3", 70, "2026-10-05", ("d",))]
    failed = {"fleet": "large+sedan", "wave_id": "c", "option": "q1", "solver": "highs", "stage": "stage1",
              "status": "rejected", "stop_reason": "solver_failure", "solve_result_num": 999}
    results = [{"unit_run": {"source": "solved", "attempts": 1, "timeout_kills": 0, "exit_codes": [0], "wall_seconds": 5.0}},
               {"unit_run": {"source": "solved", "attempts": 2, "timeout_kills": 1, "exit_codes": ["timeout", 0], "wall_seconds": 9.0},
                "failed_stage_rows": [failed]},
               {"unit_run": {"source": "cache", "attempts": 1, "timeout_kills": 0}}]
    h = runner.build_run_history(args, results, units, wall_seconds=20.0, unit_seconds=18.0, cache_used=True)
    assert h["invocations"] == [{"jobs": 3, "unit_timeout_seconds": 100.0, "cache_used": True, "stop_on_error": True,
                                 "wall_seconds": 20.0, "unit_phase_wall_seconds": 18.0}]
    assert (h["units_planned"], h["units_solved"], h["units_from_cache"], h["retries"], h["timeout_kills"]) == (3, 2, 1, 1, 1)
    assert h["stopped_early"] is False and h["units"][1]["failed_stage_rows"] == [failed]
    assert h["units"][0]["unit"] == "large+sedan|R50|2026-10-05" and h["units"][2]["source"] == "cache"
    assert runner.build_run_history(args, results[:2], units, wall_seconds=1, unit_seconds=1, cache_used=False)["stopped_early"] is True


def _only_rejected_highs(runner, monkeypatch):
    from uniride_core.exact.ampl_backend import SPSolveResult, StageResult

    gurobi, highs = object(), object()

    def fake_solve(wave, enum, **kw):
        if kw["session"] is gurobi:
            return SPSolveResult(wave.wave_id, "infeasible_proven", peak=False, solver="gurobi",
                                 stage1=StageResult("stage1", "infeasible_proven", "infeasible"))
        return SPSolveResult(wave.wave_id, "rejected", note="solver failure", peak=False, solver="highs",
                             stage1=StageResult("stage1", "rejected", "solver_failure", solve_result_num=999))

    monkeypatch.setattr(runner.ab, "solve_wave", fake_solve)
    return gurobi, highs


def test_highs_rejected_on_a_gurobi_infeasible_option_blocks_and_the_failed_row_is_kept(runner, monkeypatch):
    sessions = _only_rejected_highs(runner, monkeypatch)
    unit = ("large+doblo_cap3", 90, "2026-10-05", (_subset_ids(runner)[0],))
    res = runner._solve_unit(unit, True, set(), sessions=sessions)
    assert any("HiGHS result rejected" in e for e in res["errors"])
    kept = [r for r in res["failed_stage_rows"] if r["solver"] == "highs"]
    assert kept and kept[0]["status"] == "rejected" and kept[0]["stop_reason"] == "solver_failure"
    assert kept[0]["solve_result_num"] == 999 and kept[0]["wave_id"] == unit[3][0]


def test_evaluation_blocks_a_rejected_highs_result_on_an_infeasible_proven_option(runner, ls_ctx):
    from uniride_core.exact.ampl_backend import SPSolveResult

    arcs_doc, menu = _archive(LARGE_SEDAN)
    wave = _wave(ls_ctx, PEAK)
    gurobi = SPSolveResult(wave.wave_id, "infeasible_proven", peak=True)
    rejected = SPSolveResult(wave.wave_id, "rejected", note="solver failure", peak=True, solver="highs")
    ev = _eval(runner, ls_ctx, wave, "q0", "q", 0, _option(menu, PEAK, "q0"), arcs_doc, gurobi, highs=rejected)
    assert any("HiGHS result rejected" in e for e in ev["errors"])


# ---------- B3: line endings ----------
@pytest.mark.parametrize("name", ["wp-e3-goal1-single", "wp-e4a-typed-options"])
def test_exact_results_are_byte_exact_in_git(name):
    """``-text``: no line-ending conversion, so a fresh checkout keeps the sha256 held in the manifest."""
    res = subprocess.run(["git", "check-attr", "text", f"docs/paper/results/week-2026-10-05-exact/{name}/exact_routes.json"],
                         cwd=REPO, capture_output=True, text=True)
    assert res.stdout.strip().endswith("text: unset"), res.stdout + res.stderr
