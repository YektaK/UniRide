"""WP-E11 J5: Gurobi cross-check adapter for the joint day model (design JOINT_DAY_MODEL_DESIGN.md 4.1-4.3; owner decision
E14: Gurobi is reached through AMPL, not gurobipy).

Tests that solve carry ``requires_gurobi`` and are skipped WITH a reason when amplpy, AMPL, Gurobi or its licence is
absent (never silently, never for any other problem: a backend defect fails). Labelling, the cross-check, the integer
re-check, option strings and absence are tested with fake results and need no solver. No test runs a long solve and no
solver log is printed or stored.
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import pytest

from uniride_core.exact import gurobi_day_backend as gb
from uniride_core.exact.ampl_backend import ExactBackendUnavailable, SolverSettings, StageResult, solver_option_string
from uniride_core.exact.day_instance import NOT_RUN_ENUMERATION_CAP, build_day_instance
from uniride_core.exact.day_joint import build_joint_model
from uniride_core.exact.day_oracle import brute_force_day_optimum
from uniride_core.exact.gurobi_day_backend import (
    GurobiBackendUnavailable,
    GurobiSettings,
    classify_gurobi_outcome,
    crosscheck_day_results,
    gurobi_probe,
    run_day_stages_gurobi,
    stage_solve_from_values,
)
from uniride_core.exact.highs_backend import (
    DaySolveResult,
    HighsSettings,
    StageSolve,
    check_integer_solution,
    highs_probe,
    run_day_stages,
)
from uniride_core.tests.test_exact_day_joint_model import ARCS, CAR, HAND, LARGE, cell, make_wave

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def gurobi():
    """Skip, with the reason, only when the backend is genuinely absent; a broken install fails."""
    available, version, reason = gurobi_probe()
    if not available:
        pytest.skip(f"Gurobi through AMPL unavailable: {reason}")
    return version


@pytest.fixture(scope="module")
def session(gurobi):
    s = gb.open_session()
    yield s
    s.close()


def _typed_cell():
    w1 = make_wave("w1", "pickup", 500, [("SwA", "Sw"), ("SoB", "So")], ARCS)
    w2 = make_wave("w2", "pickup", 500, [("SoB", "So"), ("SoB", "So")], ARCS)
    return cell([w1, w2], (LARGE, CAR))


def _opt(value):
    return StageResult(status="optimal", stop_reason="optimal", objective=value, bound=value, bound_ceil=value)


def _gap(value, bound_ceil, *, reason="wall_limit"):
    return StageResult(status="feasible_with_gap", stop_reason=reason, objective=value, bound=float(bound_ceil),
                       bound_ceil=bound_ceil, timing_dependent=reason in ("wall_limit", "other_limit"))


def _bound_only(bound_ceil):
    return StageResult(status="bound_only", stop_reason="wall_limit", timing_dependent=True, bound=float(bound_ceil),
                       bound_ceil=bound_ceil)


_INFEASIBLE = StageResult(status="infeasible_proven", stop_reason="infeasible")


def _fake_day(results, *, settings=None):
    """A DaySolveResult for the typed cell from fake stage results {stage: StageResult}."""
    def solve(model, s):
        return StageSolve(results[model.stage])

    return run_day_stages(_typed_cell(), large_limit=1, settings=settings or HighsSettings(), solve_stage=solve)


# ------------------------------------------------------------------ 1. cross-check (fake results)
def test_a_planted_wrong_proven_value_is_a_blocking_disagreement_with_both_values():
    highs = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    wrong = _fake_day({1: _opt(2), 2: _opt(31), 3: _opt(12)})
    check = crosscheck_day_results(highs, wrong)
    assert check.verdict == "blocking" and check.label == "crosscheck: BLOCKING"
    blocking = [s for s in check.stages if s.verdict == "blocking"]
    assert [s.stage for s in blocking] == [2]
    assert "30" in blocking[0].detail and "31" in blocking[0].detail
    assert check.stages[0].verdict == "agree"
    assert check.stages[2].verdict == "inconclusive"  # stage 3 was fixed with 30 on one side and 31 on the other


def test_stage_one_disagreement_makes_later_stages_inconclusive_not_agreeing():
    a = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    b = _fake_day({1: _opt(3), 2: _opt(30), 3: _opt(12)})
    check = crosscheck_day_results(a, b)
    assert check.verdict == "blocking"
    assert [s.verdict for s in check.stages] == ["blocking", "inconclusive", "inconclusive"]


def test_proven_infeasible_against_a_feasible_stage_is_blocking_in_both_directions():
    feasible = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    infeasible = run_day_stages(_typed_cell(), large_limit=1, solve_stage=lambda m, s: StageSolve(_INFEASIBLE))
    assert crosscheck_day_results(feasible, infeasible).verdict == "blocking"
    assert crosscheck_day_results(infeasible, feasible).verdict == "blocking"
    assert crosscheck_day_results(infeasible, infeasible).verdict == "agree"


def test_an_incumbent_below_the_other_solvers_proven_bound_is_blocking_even_when_unproven():
    proven = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    better = _fake_day({1: _gap(1, 0), 2: _opt(30), 3: _opt(12)})  # claims S = 1 while the other proved S = 2 optimal
    check = crosscheck_day_results(proven, better)
    assert check.verdict == "blocking" and check.stages[0].verdict == "blocking"
    assert check.stages[0].detail.count("1") >= 1 and "2" in check.stages[0].detail


def test_identical_proven_results_agree():
    a = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    b = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    check = crosscheck_day_results(a, b)
    assert check.verdict == "agree" and check.label == "crosscheck: agree"
    assert [s.verdict for s in check.stages] == ["agree"] * 3


@pytest.mark.parametrize("other", [
    {1: _gap(2, 1), 2: _opt(30), 3: _opt(12)},          # timing-dependent unproven stage 1
    {1: _bound_only(1)},                                 # bound only, nothing to compare
])
def test_unproven_or_timing_dependent_stages_are_inconclusive_never_agreement(other):
    proven = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    limited = _fake_day(other)
    check = crosscheck_day_results(proven, limited)
    assert check.verdict == "inconclusive" and check.label == "crosscheck: inconclusive"
    assert check.stages[0].verdict == "inconclusive"
    assert crosscheck_day_results(limited, proven).verdict == "inconclusive"


def test_two_unproven_results_that_do_not_contradict_are_inconclusive():
    a = _fake_day({1: _gap(3, 2), 2: _gap(40, 30), 3: _gap(15, 10)})
    b = _fake_day({1: _gap(2, 2, reason="gap_tolerance"), 2: _gap(35, 30), 3: _gap(14, 10)})
    assert crosscheck_day_results(a, b).verdict == "inconclusive"


def test_an_unavailable_or_rejected_side_is_inconclusive():
    ok = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    unavailable = DaySolveResult(status="backend_unavailable", note="x", solver="gurobi")
    assert crosscheck_day_results(ok, unavailable).verdict == "inconclusive"
    rejected = _fake_day({1: StageResult(status="rejected", stop_reason="solver_failure")})
    assert crosscheck_day_results(ok, rejected).verdict == "inconclusive"


# ------------------------------------------------------------------ 2. status mapping and integer re-check
@pytest.mark.parametrize("num,message,obj,bound,status,reason,timing", [
    (0, "Gurobi 13.0.3: optimal solution; objective 3", 3.0, 3.0, "optimal", "optimal", False),
    (0, "Gurobi: optimal solution", 3.0, 1.2, "feasible_with_gap", "gap_tolerance", False),  # the runner's own check wins
    (200, "Gurobi: infeasible problem", None, None, "infeasible_proven", "infeasible", False),
    (299, "Gurobi: infeasible problem", None, None, "infeasible_proven", "infeasible", False),
    (300, "Gurobi: unbounded problem", None, None, "rejected", "solver_failure", False),
    (500, "Gurobi: failure", None, None, "rejected", "solver_failure", False),
    (999, "?", None, None, "rejected", "solver_failure", False),
    (400, "Gurobi: time limit; objective 7", 7.0, 5.0, "feasible_with_gap", "wall_limit", True),
    (401, "Gurobi: work limit; objective 7", 7.0, 5.0, "feasible_with_gap", "work_limit", False),
    (450, "Gurobi: time limit", None, 2.5, "bound_only", "wall_limit", True),
    (450, "Gurobi: interrupted", None, 2.5, "bound_only", "other_limit", True),
])
def test_solve_result_mapping(num, message, obj, bound, status, reason, timing):
    r = classify_gurobi_outcome(num, message, obj, bound)
    assert (r.status, r.stop_reason, r.timing_dependent) == (status, reason, timing)
    if status == "optimal":
        assert (r.objective, r.bound_ceil) == (3, 3)


def test_an_infeasibility_settled_by_ampl_presolve_is_labelled_and_never_counts_as_a_solver_agreement():
    r = classify_gurobi_outcome(299, "presolve finds no feasible solution possible", None, None)
    assert (r.status, r.bound_source) == ("infeasible_proven", "ampl_presolve")
    assert classify_gurobi_outcome(200, "Gurobi 13.0.3: infeasible problem", None, None).bound_source is None
    settled = run_day_stages(_typed_cell(), large_limit=1, solve_stage=lambda m, s: StageSolve(r))
    plain = run_day_stages(_typed_cell(), large_limit=1, solve_stage=lambda m, s: StageSolve(_INFEASIBLE))
    assert crosscheck_day_results(plain, settled).verdict == "inconclusive"


def test_infeasible_or_unbounded_is_never_a_proof_of_infeasibility():
    r = classify_gurobi_outcome(300, "Gurobi: infeasible or unbounded problem", None, None)
    assert r.status == "rejected"


def test_a_fractional_incumbent_objective_is_rejected():
    assert classify_gurobi_outcome(0, "optimal solution", 3.4, 3.4).status == "rejected"


def _feasible_point(model):
    """A feasible integer point of the stage-1 model found by exhaustive search over the (small) column variables."""
    import itertools

    cols = [i for i, v in enumerate(model.variables) if v.kind == "column"]
    peak = [i for i, v in enumerate(model.variables) if v.kind == "peak"][0]
    ranges = [range(model.variables[i].lower, model.variables[i].upper + 1) for i in cols]
    for combo in itertools.product(*ranges):
        raw = {v.name: float(v.lower) for v in model.variables}
        for i, c in zip(cols, combo):
            raw[model.variables[i].name] = float(c)
        for k in range(model.variables[peak].lower, model.variables[peak].upper + 1):
            raw[model.variables[peak].name] = float(k)
            checked = check_integer_solution(model, raw)
            if checked is not None:
                return raw, checked[1]
    raise AssertionError("no feasible point")


def test_stage_solve_from_values_accepts_a_feasible_point_and_recomputes_the_objective():
    model = build_joint_model(_typed_cell(), stage=1, large_limit=1)
    raw, objective = _feasible_point(model)
    ok = stage_solve_from_values(model, _opt(objective), raw)
    assert ok.result.status == "optimal" and ok.result.objective == objective and ok.values is not None


def test_stage_solve_from_values_rejects_fractional_row_violating_and_mismatching_values():
    model = build_joint_model(_typed_cell(), stage=1, large_limit=1)
    raw, objective = _feasible_point(model)
    first_column = next(v.name for v in model.variables if v.kind == "column" and v.upper > 0)
    fractional = dict(raw, **{first_column: raw[first_column] + 0.3})
    assert stage_solve_from_values(model, _opt(objective), fractional).result.status == "rejected"
    over = dict(raw, **{first_column: float(model.variables[[v.name for v in model.variables].index(first_column)].upper + 1)})
    assert stage_solve_from_values(model, _opt(objective), over).result.status == "rejected"
    assert stage_solve_from_values(model, _opt(objective + 1), raw).result.status == "rejected"  # solver objective != recomputed
    assert stage_solve_from_values(model, StageResult(status="infeasible_proven"), {}).values is None


# ------------------------------------------------------------------ 3. settings and option string
def test_option_string_is_verbatim_and_has_the_design_values():
    s = GurobiSettings()
    assert (s.threads, s.seed, s.mip_gap, s.mip_gap_abs, s.time_limit, s.work_limit) == (1, 0, 0.0, 0.99, 600.0, None)
    gurobi_part = "mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 lim:time=600 outlev=1"
    assert s.option_string() == "ampl:presolve=0 " + gurobi_part
    assert s.solver_options_string() == gurobi_part == solver_option_string(
        SolverSettings(solver="gurobi", wall_limit=600, work_limit=None), peak=False)
    assert s.ampl_options() == (("presolve", 0),)
    w = GurobiSettings(time_limit=0.5, work_limit=7.5, ampl_presolve=None)
    assert w.option_string() == ("mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 lim:time=0.5 "
                                 "lim:work=7.5 outlev=1")
    assert w.ampl_options() == () and w.solver_options_string() == w.option_string()
    assert w.option_string() == " ".join(f"{k}={format(v, 'g') if isinstance(v, float) else v}" for k, v in w.options())


# ------------------------------------------------------------------ 4. absence and import hygiene
def test_missing_ampl_directory_gives_backend_unavailable_without_raising(monkeypatch, tmp_path):
    monkeypatch.setenv("UNIRIDE_AMPL_DIR", str(tmp_path))  # a directory without an AMPL executable
    res = run_day_stages_gurobi(_typed_cell(), large_limit=1)
    assert res.status == "backend_unavailable" and res.solver == "gurobi" and res.stages == ()
    assert res.solver_options == GurobiSettings().option_string() and res.time_limit == 600.0
    assert gurobi_probe()[0] is False


def test_missing_amplpy_gives_backend_unavailable_without_raising(monkeypatch):
    monkeypatch.setitem(sys.modules, "amplpy", None)  # makes `import amplpy` raise ImportError
    res = run_day_stages_gurobi(_typed_cell(), large_limit=1)
    assert res.status == "backend_unavailable" and "amplpy" in res.note
    available, version, reason = gurobi_probe()
    assert (available, version) == (False, None) and "amplpy" in reason


def test_a_solver_or_licence_that_goes_missing_is_reported_not_raised(monkeypatch):
    def refuse(*a, **k):
        raise ExactBackendUnavailable("gurobi: solver or license missing")

    monkeypatch.setattr(gb.AmplSession, "open", refuse)
    res = run_day_stages_gurobi(_typed_cell(), large_limit=1)
    assert res.status == "backend_unavailable" and "gurobi" in res.note


def test_a_session_failing_midway_is_reported_not_raised():
    class Session:
        solver_version = "Gurobi 0.0.0"

        def close(self):
            pass

    def vanish(*a, **k):
        raise GurobiBackendUnavailable("gone")

    res = run_day_stages_gurobi(_typed_cell(), large_limit=1, session=Session(), stage_solver=vanish)
    assert res.status == "backend_unavailable" and res.note == "gone"


def test_input_that_is_not_ready_is_input_rejected_without_opening_a_session(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("a session was opened")

    monkeypatch.setattr(gb, "open_session", boom)
    capped = dataclasses.replace(_typed_cell(), status=NOT_RUN_ENUMERATION_CAP)
    res = run_day_stages_gurobi(capped, large_limit=1)
    assert res.status == "input_rejected" and res.solver == "gurobi"


def test_importing_the_backend_loads_neither_amplpy_nor_highspy():
    code = ("import sys, uniride_core.exact, uniride_core.exact.gurobi_day_backend; "
            "assert 'amplpy' not in sys.modules, 'amplpy imported at load'; "
            "assert 'highspy' not in sys.modules, 'highspy imported at load'; print('ok')")
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    out = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr[-500:]


def test_the_module_imports_nothing_from_academic_benchmark_or_optimizer_api():
    import ast

    tree = ast.parse((REPO_ROOT / "uniride_core" / "exact" / "gurobi_day_backend.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imported.add((node.module or "").split(".")[0])
    assert not imported & {"academic_benchmark", "optimizer_api", "src", "amplpy", "highspy", "gurobipy"}, imported


# ------------------------------------------------------------------ 5. real Gurobi through AMPL (unit-test sized)
# every oracle cell plain, every third cell also aggregated (each AMPL solve costs about a second)
GUROBI_CASES = [(c, False) for c in HAND] + [(c, True) for c in HAND[::3]]


@pytest.mark.requires_gurobi
@pytest.mark.parametrize("case,aggregate", GUROBI_CASES,
                         ids=[f"{c[0]}-{'aggregated' if a else 'plain'}" for c, a in GUROBI_CASES])
def test_hand_instances_through_gurobi_give_the_oracle_tuple(session, case, aggregate):
    name, waves, types, large_limit = case
    oracle = brute_force_day_optimum(waves, types, large_limit=large_limit).objective
    res = run_day_stages_gurobi(build_day_instance(waves, types), large_limit=large_limit, aggregate=aggregate, session=session)
    if oracle is None:
        assert res.status == "infeasible_proven" and res.objective is None, f"{name}: {res.status} {res.objective}"
        assert res.stages[0].result.stop_reason == "infeasible"
        return
    assert res.objective == oracle, f"{name}: Gurobi {res.objective} oracle {oracle}"
    assert res.status == "optimal" and not res.non_lexicographic and not res.timing_dependent
    assert len(res.stages) == (3 if len(types) == 2 else 2)
    assert all(s.result.status == "optimal" and s.result.stop_reason == "optimal" for s in res.stages)
    assert res.stages[-1].selection
    assert res.solver == "gurobi" and res.solver_version and res.solver_version.startswith("Gurobi")
    assert res.solver_options == GurobiSettings().option_string() and res.time_limit == 600.0


@pytest.mark.requires_gurobi
def test_stage_rows_carry_wall_seconds_time_limit_and_work_limit(session):
    res = run_day_stages_gurobi(_typed_cell(), large_limit=1, session=session,
                                settings=GurobiSettings(time_limit=30.0, work_limit=500.0))
    assert res.status == "optimal"
    for s in res.stages:
        assert s.result.wall_seconds is not None and s.result.wall_seconds >= 0
        assert s.result.time_limit == 30.0 and s.result.work_limit == 500.0
        assert s.result.solve_result_num is not None and s.result.solve_result
    assert res.solver_options == ("ampl:presolve=0 mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 "
                                  "lim:time=30 lim:work=500 outlev=1")


@pytest.mark.requires_gurobi
@pytest.mark.parametrize("aggregate", [False, True], ids=["plain", "aggregated"])
@pytest.mark.parametrize("name,waves,types,large_limit", HAND[::7], ids=[c[0] for c in HAND[::7]])
def test_the_ampl_side_model_is_the_j3_model(session, name, waves, types, large_limit, aggregate):
    """Variable and row counts, bounds, costs, rows, right-hand sides and every coefficient read back from AMPL."""
    inst = build_day_instance(waves, types)
    fixed_by_stage = {1: {}, 2: {"peak": 1}, 3: {"peak": 1, "total_minutes": 15}}
    for stage in range(1, (3 if len(types) == 2 else 2) + 1):
        model = build_joint_model(inst, stage=stage, large_limit=large_limit, fixed=fixed_by_stage[stage], aggregate=aggregate)
        gb.load_day_model(session.ampl, model)
        back = gb.readback_model(session.ampl)
        assert back["n_variables"] == len(model.variables) and back["n_rows"] == len(model.rows)
        assert back["n_nonzeros"] == model.counts["nonzeros"]
        assert back["variables"] == [(v.lower, v.upper, v.objective) for v in model.variables]
        assert back["rows"] == [(r.sense, r.rhs) for r in model.rows]
        assert back["coefficients"] == {(ri, vi): c for ri, r in enumerate(model.rows) for vi, c in r.terms}


@pytest.mark.requires_gurobi
@pytest.mark.requires_highspy
def test_gurobi_and_highs_give_equal_tuples_and_the_cross_check_agrees_on_the_oracle_set(session):
    if not highs_probe()[0]:
        pytest.skip(f"highspy unavailable: {highs_probe()[2]}")
    compared = 0
    for name, waves, types, large_limit in HAND[::3]:
        oracle = brute_force_day_optimum(waves, types, large_limit=large_limit).objective
        inst = build_day_instance(waves, types)
        h = run_day_stages(inst, large_limit=large_limit)
        g = run_day_stages_gurobi(inst, large_limit=large_limit, session=session)
        assert h.objective == g.objective == oracle, f"{name}: HiGHS {h.objective} Gurobi {g.objective} oracle {oracle}"
        assert h.status == g.status
        check = crosscheck_day_results(h, g)
        assert check.verdict == "agree", f"{name}: {check.label} {[s.detail for s in check.stages]}"
        compared += 1
    assert compared >= 15


@pytest.mark.requires_gurobi
@pytest.mark.requires_highspy
def test_an_infeasible_typed_cell_is_infeasible_proven_from_both_and_the_raw_statuses_are_recorded(session):
    if not highs_probe()[0]:
        pytest.skip(f"highspy unavailable: {highs_probe()[2]}")
    name, waves, types, large_limit = next(c for c in HAND if len(c[2]) == 2 and
                                           brute_force_day_optimum(c[1], c[2], large_limit=c[3]).objective is None)
    inst = build_day_instance(waves, types)
    h = run_day_stages(inst, large_limit=large_limit)
    g = run_day_stages_gurobi(inst, large_limit=large_limit, session=session)
    assert h.status == "infeasible_proven", f"{name}: HiGHS {h.status} raw {h.stages[0].result.solve_result}"
    assert g.status == "infeasible_proven", f"{name}: Gurobi {g.status} raw {g.stages[0].result.solve_result}"
    raw_highs, raw_gurobi = h.stages[0].result.solve_result, g.stages[0].result
    assert raw_highs in ("kInfeasible", "kUnboundedOrInfeasible")
    assert raw_gurobi.solve_result_num is not None and 200 <= raw_gurobi.solve_result_num < 300
    assert raw_gurobi.bound_source != "ampl_presolve", raw_gurobi.solver_message  # Gurobi itself proved it
    assert crosscheck_day_results(h, g).verdict == "agree"
