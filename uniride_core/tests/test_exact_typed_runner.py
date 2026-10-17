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
def test_parallel_workers_give_the_same_results_as_a_serial_run(runner, tmp_path):
    _require("gurobi")
    ids = _subset_ids(runner)
    common = ["--fleets", "large+doblo_cap3", "--rides", "90", "--wave-ids", ",".join(ids), "--no-highs-verify"]
    assert runner.main(common + ["--jobs", "1", "--out", str(tmp_path / "a")]) == 0
    assert runner.main(common + ["--jobs", "2", "--out", str(tmp_path / "b")]) == 0
    timing = {"enumeration_seconds", "solve_seconds", "highs_seconds"}

    def stable(path):
        return [{k: v for k, v in r.items() if k not in timing} for r in csv.DictReader(path.open(encoding="utf-8"))]

    assert stable(tmp_path / "a" / "option_gaps.csv") == stable(tmp_path / "b" / "option_gaps.csv")
    assert (tmp_path / "a" / "exact_routes.json").read_bytes() == (tmp_path / "b" / "exact_routes.json").read_bytes()


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
