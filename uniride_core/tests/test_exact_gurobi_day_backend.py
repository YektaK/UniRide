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


def _homogeneous_day(results):
    w1 = make_wave("w1", "pickup", 500, [("SwA", "Sw"), ("SoB", "So")], ARCS)
    w2 = make_wave("w2", "pickup", 500, [("SoB", "So"), ("SoB", "So")], ARCS)

    def solve(model, s):
        return StageSolve(results[model.stage])

    return run_day_stages(cell([w1, w2], (LARGE,)), solve_stage=solve)


def test_one_proven_side_with_an_equal_objective_is_not_an_agreement_when_the_other_stops_on_gap_tolerance():
    # stage 3 of one solver is feasible_with_gap 12 (reason gap_tolerance, not timing-dependent, lexicographic),
    # the other proves 12 optimal: the values are equal but only one side proved it
    proven = _fake_day({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    gapped = _fake_day({1: _opt(2), 2: _opt(30), 3: _gap(12, 11, reason="gap_tolerance")})
    last = gapped.stages[2].result
    assert (last.status, last.stop_reason, last.timing_dependent, last.non_lexicographic) == (
        "feasible_with_gap", "gap_tolerance", False, False)
    for a, b in ((proven, gapped), (gapped, proven)):
        check = crosscheck_day_results(a, b)
        assert [s.verdict for s in check.stages] == ["agree", "agree", "inconclusive"]
        assert check.verdict == "inconclusive" and check.label == "crosscheck: inconclusive"


def test_a_homogeneous_stage_one_gap_tolerance_on_one_side_is_inconclusive_in_both_orders():
    proven = _homogeneous_day({1: _opt(2), 2: _opt(30)})
    gapped = _homogeneous_day({1: _gap(2, 1, reason="gap_tolerance"), 2: _opt(30)})
    assert gapped.stages[0].result.stop_reason == "gap_tolerance" and not gapped.stages[0].result.timing_dependent
    for a, b in ((proven, gapped), (gapped, proven)):
        check = crosscheck_day_results(a, b)
        assert check.stages[0].verdict == "inconclusive"
        assert check.verdict == "inconclusive"


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
    # only AMPL's own phrase counts; a solver message that merely mentions presolve is the solver's proof
    mention = classify_gurobi_outcome(200, "Gurobi 13.0.3: infeasible problem after presolve removed 4 rows", None, None)
    assert (mention.status, mention.bound_source) == ("infeasible_proven", None)
    settled = run_day_stages(_typed_cell(), large_limit=1, solve_stage=lambda m, s: StageSolve(r))
    plain = run_day_stages(_typed_cell(), large_limit=1, solve_stage=lambda m, s: StageSolve(_INFEASIBLE))
    assert crosscheck_day_results(plain, settled).verdict == "inconclusive"


@pytest.mark.parametrize("num", [220, 299, 300])
def test_infeasible_or_unbounded_is_never_a_proof_of_infeasibility(num):
    r = classify_gurobi_outcome(num, "Gurobi: infeasible or unbounded problem", None, None)
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


class _FakeAmpl:
    """Just enough of an amplpy session for one stage; records every call."""

    def __init__(self, *, solve_error=None, num=0, message="", log=None):
        self.calls, self.option = [], {}
        self.solve_error, self.num, self.message = solve_error, num, message
        self.solve_result = "failure"
        self.log, self.sink = list(log or ()), None

    def reset(self):
        self.calls.append("reset")

    def eval(self, text):
        self.calls.append("eval")

    def solve(self):
        if self.sink is not None:
            self.sink.extend(self.log)  # the output handler of the real session fills `_log` during the solve
        if self.solve_error is not None:
            raise self.solve_error

    def get_value(self, name):
        return {"solve_result_num": self.num, "solve_message": self.message}.get(name, -1e30)

    def get_objective(self, name):
        return type("O", (), {"value": staticmethod(lambda: None)})()


class _FakeSession:
    solver_version = "Gurobi 0.0.0"

    def __init__(self, ampl, log=()):
        self.ampl, self._log = ampl, list(log)

    def close(self):
        pass


def _run_with(monkeypatch, fake, log=()):
    monkeypatch.setattr(gb, "load_day_model", lambda ampl, model: None)
    session = _FakeSession(fake)
    fake.log, fake.sink = list(log), session._log
    return run_day_stages_gurobi(_typed_cell(), large_limit=1, session=session)


def test_an_ampl_session_error_during_a_stage_is_backend_unavailable_not_raised(monkeypatch):
    import amplpy  # the real error type of the session's error handler

    err = amplpy.AMPLException("file", 3, 1, "Gurobi license expired for licensee someone@example.org")
    res = _run_with(monkeypatch, _FakeAmpl(solve_error=err))
    assert res.status == "backend_unavailable" and res.solver == "gurobi" and "AMPLException" in res.note
    assert "someone@example.org" not in res.note  # licence text is scrubbed
    broken = _run_with(monkeypatch, _FakeAmpl(solve_error=BrokenPipeError("pipe")))
    assert broken.status == "backend_unavailable"


def test_the_session_error_note_records_only_the_exception_type_never_its_text(monkeypatch):
    import amplpy

    secret = "internal token ZX-SECRET-4711 path C:/somewhere/ampl"  # no word the scrubber would catch
    res = _run_with(monkeypatch, _FakeAmpl(solve_error=amplpy.AMPLException("file", 3, 1, secret)))
    assert res.status == "backend_unavailable"
    assert res.note == "AMPL session failed during a stage: AMPLException"
    assert "ZX-SECRET" not in res.note and "somewhere" not in res.note
    pipe = _run_with(monkeypatch, _FakeAmpl(solve_error=BrokenPipeError("ZX-SECRET-4711")))
    assert pipe.note == "AMPL session failed during a stage: BrokenPipeError"


def test_a_failure_whose_log_is_a_normal_gurobi_startup_log_stays_rejected(monkeypatch):
    # made-up licence id; the lines name a licence but say nothing about it being missing, expired or invalid
    log = ["Set parameter LicenseID to value 100000",
           "Academic license 100000 - for non-commercial use only - registered to Nobody",
           "Gurobi Optimizer version 13.0.3 build v13.0.3rc0 (win64 - Windows 11.0 (26100.2))",
           "Optimize a model with 12 rows, 9 columns and 30 nonzeros"]
    res = _run_with(monkeypatch, _FakeAmpl(num=500, message="Gurobi 13.0.3: out of memory"), log=log)
    assert res.status == "rejected" and res.stages[0].result.status == "rejected"
    assert res.stages[0].result.stop_reason == "solver_failure"
    assert "Nobody" not in repr(res) and "100000" not in repr(res)  # the log is never stored


def test_a_licence_lost_failure_result_is_backend_unavailable_but_other_failures_stay_rejected(monkeypatch):
    lost = _run_with(monkeypatch, _FakeAmpl(num=500, message="?"), log=["Gurobi: license expired"])
    assert lost.status == "backend_unavailable" and "license" in lost.note
    gone = _run_with(monkeypatch, _FakeAmpl(num=999, message="Cannot invoke gurobi: no such program."))
    assert gone.status == "backend_unavailable"
    defect = _run_with(monkeypatch, _FakeAmpl(num=500, message="Gurobi: out of memory"))
    assert defect.status == "rejected" and defect.stages[0].result.status == "rejected"


def test_an_error_that_is_not_a_session_error_propagates(monkeypatch):
    with pytest.raises(ValueError):
        _run_with(monkeypatch, _FakeAmpl(solve_error=ValueError("our own defect")))


def test_load_day_model_refuses_an_unknown_row_sense_and_a_duplicate_pair_before_touching_ampl():
    model = build_joint_model(_typed_cell(), stage=1, large_limit=1)
    assert model.rows[0].terms
    row = model.rows[0]
    bad_sense = dataclasses.replace(model, rows=(dataclasses.replace(row, sense="X"),) + model.rows[1:])
    dup = dataclasses.replace(model, rows=(dataclasses.replace(row, terms=row.terms + (row.terms[0],)),) + model.rows[1:])
    for broken in (bad_sense, dup):
        fake = _FakeAmpl()
        with pytest.raises(ValueError):
            gb.load_day_model(fake, broken)
        assert fake.calls == []  # nothing was sent to AMPL


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
    assert raw_highs == "kInfeasible"
    assert raw_gurobi.solve_result_num is not None and 200 <= raw_gurobi.solve_result_num < 300
    assert raw_gurobi.bound_source != "ampl_presolve", raw_gurobi.solver_message  # Gurobi itself proved it
    assert crosscheck_day_results(h, g).verdict == "agree"


# ------------------------------------------------------------------ 6. integrality is a test of the VALUES, not of the raw objective
# J11 (large+doblo_cap3 2026-10-08 R50 L2, stage 3): Gurobi returned objective 539.9999877 with every integer variable
# inside its integrality tolerance (largest deviation 1.28e-6). Several small deviations add up through the tour
# coefficients (66, 72, 81), so the RAW objective sat 1.23e-5 from 540, beyond the old 1e-5 test on the objective.
_NOISY_OBJECTIVE = 539.9999877
_NOISY_BOUND = 539.9999877417731


def _noise_model(fix_x2=True):
    """Three integer variables with the J11 tour coefficients; x0 = 4, x1 = 3, x2 = 0 gives 81*4 + 72*3 = 540.

    ``fix_x2=False`` leaves x2 free (0 to 10), so x = (4, 3, 1) is also feasible, with objective 606."""
    from uniride_core.exact.day_joint import JointModel, MipRow, MipVariable

    variables = (MipVariable("x0", 0, 10, 81, "column"), MipVariable("x1", 0, 10, 72, "column"),
                 MipVariable("x2", 0, 10, 66, "column"))
    rows = (MipRow("r0", "E", 4, ((0, 1),), "cover"), MipRow("r1", "E", 3, ((1, 1),), "cover"),
            MipRow("r2", "E", 0, ((2, 1),), "cover"))
    if not fix_x2:
        rows = rows[:2]
    return JointModel("noise", "homogeneous", 3, "Obj", variables, rows, {})


def _noisy_values():
    """Values 4, 3, 0 pulled off the integers so that the objective computed from them is 539.9999877 (each deviation below 1e-6)."""
    dev0 = -1e-7
    dev1 = (_NOISY_OBJECTIVE - 540 - 81 * dev0) / 72
    assert abs(dev1) < 1e-6
    return [4 + dev0, 3 + dev1, 0.0]


class _ValueAmpl(_FakeAmpl):
    """A fake AMPL session that returns an incumbent: objective, best bound and the values of the variable ``x``."""

    def __init__(self, objective, values, bound=_NOISY_BOUND, message="Gurobi 13.0.3: optimal solution; objective 540", num=0):
        super().__init__(num=num, message=message)
        self.objective, self.values, self.bound = objective, values, bound
        self.solve_result = "solved"
        self.var = {"x": type("V", (), {"get_values": staticmethod(
            lambda: type("D", (), {"to_dict": staticmethod(lambda: dict(enumerate(self.values)))})())})()}

    def get_value(self, name):
        if name.endswith(".bestbound"):
            return self.bound
        return super().get_value(name)

    def get_objective(self, name):
        return type("O", (), {"value": staticmethod(lambda: self.objective)})()


def _solve_noise_stage(monkeypatch, objective, values, *, fix_x2=True, **kwargs):
    monkeypatch.setattr(gb, "load_day_model", lambda ampl, model: None)
    session = _FakeSession(_ValueAmpl(objective, values, **kwargs))
    return gb.gurobi_solve_stage(session, _noise_model(fix_x2), GurobiSettings())


def test_the_j11_stage_with_a_raw_objective_539_9999877_and_near_integral_values_is_accepted_as_540(monkeypatch):
    values = _noisy_values()
    assert abs(sum(c * x for c, x in zip((81, 72, 66), values)) - _NOISY_OBJECTIVE) < 1e-9  # the numbers are the J11 ones
    solved = _solve_noise_stage(monkeypatch, _NOISY_OBJECTIVE, values)
    assert (solved.result.status, solved.result.stop_reason, solved.result.objective) == ("optimal", "optimal", 540)
    assert solved.values == {"x0": 4, "x1": 3, "x2": 0}
    # the BOUND is never reconciled to the integer 540: it is the solver's bound lowered by the HiGHS snap rule only
    # (1e-8 relative minus 1e-6), and below 540 here
    assert solved.result.bound == pytest.approx(_NOISY_BOUND - (1e-8 * _NOISY_BOUND - 1e-6), abs=1e-12)
    assert solved.result.bound != 540 and solved.result.bound_ceil == 540 and solved.result.solver_message.startswith("Gurobi")


@pytest.mark.parametrize("objective,values", [
    # a genuinely fractional value: beyond the variable tolerance, whatever the objective says
    (540.0, [4.0, 3.0 + 3e-5, 0.0]),
    # integral values (objective 540) but the solver reports 539.9: a real mismatch, not rounding noise
    (539.9, [4.0, 3.0, 0.0]),
    (540.3, [4.0, 3.0, 0.0]),
    # a near-integral objective that belongs to other integer values (these give 606, the solver says ~540)
    (_NOISY_OBJECTIVE, [4.0, 3.0, 1.0]),
    # exactly integral but different objective: the recomputed value (540) does not match the solver's 541
    (541.0, [4.0, 3.0, 0.0]),
    # a row violated by the rounded values (x0 must be 4)
    (_NOISY_OBJECTIVE, [3.0 - 1e-6, 3.0, 0.0]),
])
def test_a_fractional_value_or_an_objective_that_disagrees_after_rounding_is_still_rejected(monkeypatch, objective, values):
    solved = _solve_noise_stage(monkeypatch, objective, values)
    assert solved.result.status == "rejected" and solved.result.stop_reason == "solver_failure"
    assert solved.values is None  # a rejected stage carries no values


# ------------------------------------------------------------------ 7. Gurobi bounds are snapped like HiGHS bounds, and the clip leaves its note
from uniride_core.exact.day_labels import label_cell  # noqa: E402
from uniride_core.exact.highs_backend import BOUND_ABOVE_INCUMBENT  # noqa: E402

_LIMIT_MESSAGE = "Gurobi 13.0.3: time limit, feasible solution; objective 606"
_X_606 = [4.0, 3.0, 1.0]  # objective 81*4 + 72*3 + 66 = 606 on the model with x2 free


def test_an_upward_noise_bound_on_a_limit_stage_is_snapped_not_rounded_up_a_whole_unit(monkeypatch):
    # bound 540.000003 is 3e-6 above the integer 540, inside the snap allowance (1e-8 relative minus 1e-6, plus the 1e-6 of
    # the ceiling rule): the lower bound is 540, not 541
    solved = _solve_noise_stage(monkeypatch, 606.0, _X_606, fix_x2=False, bound=540.000003, num=402, message=_LIMIT_MESSAGE)
    r = solved.result
    assert (r.status, r.stop_reason, r.objective, r.bound_ceil) == ("feasible_with_gap", "wall_limit", 606, 540)
    assert not str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT)


def test_a_bound_genuinely_above_540_is_still_rounded_up(monkeypatch):
    solved = _solve_noise_stage(monkeypatch, 606.0, _X_606, fix_x2=False, bound=540.2, num=402, message=_LIMIT_MESSAGE)
    assert solved.result.bound_ceil == 541 and not str(solved.result.solver_message).startswith(BOUND_ABOVE_INCUMBENT)


def test_a_correct_plan_is_not_blocking_against_an_upward_noise_gurobi_bound_on_a_limit_stage(monkeypatch):
    # HiGHS has a verified plan of 540 and proves it; Gurobi stopped on its limit with 606 and bound 540.000003. Rounded up
    # to 541 that bound "proved" the HiGHS plan impossible and made the cross-check BLOCKING (wrong, fail-safe).
    solved = _solve_noise_stage(monkeypatch, 606.0, _X_606, fix_x2=False, bound=540.000003, num=402, message=_LIMIT_MESSAGE)
    tail = {2: _opt(30), 3: _opt(12)}
    check = crosscheck_day_results(_fake_day({1: _opt(540), **tail}), _fake_day({1: solved.result, **tail}))
    assert check.verdict != "blocking" and check.stages[0].verdict == "inconclusive"
    # a bound that really is above the plan still blocks
    above = _solve_noise_stage(monkeypatch, 606.0, _X_606, fix_x2=False, bound=541.0, num=402, message=_LIMIT_MESSAGE)
    assert crosscheck_day_results(_fake_day({1: _opt(540), **tail}), _fake_day({1: above.result, **tail})).verdict == "blocking"


def test_a_gurobi_bound_above_the_incumbent_beyond_the_snap_carries_the_note_and_withholds_the_claim(monkeypatch):
    # optimal stage with objective 540 and bound 540.00001: 1e-5 above, beyond the snap allowance (5.4e-6): the ceiling is 541,
    # clipped to the incumbent 540, and the clip note is written like HiGHS does (J9b flag). The values are exactly integral
    # here, so the RAW objective is exactly 540 and 540.00001 is above it by more than the reconcile allowance (about
    # 1.5e-6, no deviation to explain): it is not noise of the objective, the note stays (round 3 rule, pinned).
    solved = _solve_noise_stage(monkeypatch, 540.0, [4.0, 3.0, 0.0], bound=540.00001)
    r = solved.result
    assert r.bound_ceil == 540 and r.objective == 540
    assert str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT) and "Gurobi 13.0.3" in r.solver_message
    day = _fake_day({1: r, 2: _opt(30), 3: _opt(12)})
    label = label_cell(enumeration_complete=True, result=day, crosscheck="agree", checker_ok=True)
    assert any(f.startswith(BOUND_ABOVE_INCUMBENT) for f in label.flags)
    assert not label.proof_claim_allowed and label.proof_claim_reason == BOUND_ABOVE_INCUMBENT


def test_a_solved_gurobi_stage_with_a_consistent_bound_has_no_note_and_keeps_its_claim(monkeypatch):
    for bound in (540.0, _NOISY_BOUND, 539.2):
        solved = _solve_noise_stage(monkeypatch, 540.0, [4.0, 3.0, 0.0], bound=bound)
        assert not str(solved.result.solver_message).startswith(BOUND_ABOVE_INCUMBENT), bound
    day = _fake_day({1: _solve_noise_stage(monkeypatch, 540.0, [4.0, 3.0, 0.0], bound=540.0).result, 2: _opt(30), 3: _opt(12)})
    label = label_cell(enumeration_complete=True, result=day, crosscheck="agree", checker_ok=True)
    assert label.proof_claim_allowed and not [f for f in label.flags if f.startswith(BOUND_ABOVE_INCUMBENT)]


def test_a_gurobi_bound_only_stage_is_snapped_too():
    out = classify_gurobi_outcome(450, "Gurobi 13.0.3: time limit, no solution", None, 540.000003)
    assert (out.status, out.bound_ceil, out.objective) == ("bound_only", 540, None)


# ------------------------------------------------------------------ 8. a bound that is the solver's own raw objective (gap 0) cannot contradict the incumbent
def _model_for(coefficients, targets):
    """Integer variables with the given objective coefficients and every value fixed by a cover row."""
    from uniride_core.exact.day_joint import JointModel, MipRow, MipVariable

    variables = tuple(MipVariable(f"x{i}", 0, 20, c, "column") for i, c in enumerate(coefficients))
    rows = tuple(MipRow(f"r{i}", "E", t, ((i, 1),), "cover") for i, t in enumerate(targets))
    return JointModel("mirror", "homogeneous", 3, "Obj", variables, rows, {})


def _solve_model_stage(monkeypatch, model, objective, values, bound):
    monkeypatch.setattr(gb, "load_day_model", lambda ampl, m: None)
    return gb.gurobi_solve_stage(_FakeSession(_ValueAmpl(objective, values, bound=bound)), model, GurobiSettings())


def _claim_kept(result):
    day = _fake_day({1: result, 2: _opt(30), 3: _opt(12)})
    return label_cell(enumeration_complete=True, result=day, crosscheck="agree", checker_ok=True)


@pytest.mark.parametrize("coefficients,targets,devs,objective", [
    # J11 mirror: 81*4 + 72*3 = 540, deviations add 1.23e-5 on the upward side
    ((81, 72, 66), (4, 3, 0), (1e-7, 5.8333333e-8, 0.0), 540.0000123),
    # a smaller upward excursion of the same kind
    ((81, 72, 66), (4, 3, 0), (1e-7, 0.0, 0.0), 540.0000081),
    # a larger objective: 100*10 + 50*10 = 1500, deviations add 2e-5
    ((100, 50), (10, 10), (1e-7, 2e-7), 1500.00002),
])
def test_a_bound_equal_to_the_solvers_own_noisy_raw_objective_writes_no_note_and_keeps_the_claim(
        monkeypatch, coefficients, targets, devs, objective):
    values = [t + d for t, d in zip(targets, devs)]
    assert abs(sum(c * x for c, x in zip(coefficients, values)) - objective) < 2e-9  # the solver's raw objective
    solved = _solve_model_stage(monkeypatch, _model_for(coefficients, targets), objective, values, bound=objective)
    r = solved.result
    assert r.status == "optimal" and r.objective == round(objective) and r.bound_ceil == round(objective)
    assert not str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT), r.solver_message
    label = _claim_kept(r)
    assert label.proof_claim_allowed and not [f for f in label.flags if f.startswith(BOUND_ABOVE_INCUMBENT)]


def test_the_j11_downward_case_still_writes_no_note(monkeypatch):
    # raw objective 539.9999877, bound 539.9999877417731 (below 540): never a note, as before
    r = _solve_model_stage(monkeypatch, _noise_model(), _NOISY_OBJECTIVE, _noisy_values(), _NOISY_BOUND).result
    assert not str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT) and r.objective == 540 and r.bound_ceil == 540


@pytest.mark.parametrize("bound", [541.0, 540.3, 542.5])
def test_a_bound_genuinely_above_the_raw_objective_still_writes_the_note_and_withholds_the_claim(monkeypatch, bound):
    solved = _solve_model_stage(monkeypatch, _model_for((81, 72, 66), (4, 3, 0)), 540.0, [4.0, 3.0, 0.0], bound)
    r = solved.result
    assert str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT) and r.bound_ceil == 540
    label = _claim_kept(r)
    assert not label.proof_claim_allowed and label.proof_claim_reason == BOUND_ABOVE_INCUMBENT


def test_a_bound_above_the_noisy_raw_objective_beyond_the_allowance_still_writes_the_note(monkeypatch):
    # raw objective 540.0000123, whose deviations are small (allowance only about 1.4e-5): a bound 1e-4 above the RAW objective
    # is not the solver's number for this plan. (This held only because the allowance was small; the next tests use a large one.)
    values = [4 + 1e-7, 3 + 5.8333333e-8, 0.0]
    solved = _solve_model_stage(monkeypatch, _model_for((81, 72, 66), (4, 3, 0)), 540.0000123, values, bound=540.0001123)
    assert str(solved.result.solver_message).startswith(BOUND_ABOVE_INCUMBENT)


# ------------------------------------------------------------------ 9. the exemption is float noise around the solver's own number, not the reconcile allowance
# The allowance says how far the RAW objective may sit from the rounded one; it says nothing about how far a bound may sit above
# the raw objective (at gap 0 the bound IS the raw objective). Adding it would count it twice (reviewer's hole.py).
from uniride_core.exact.ampl_backend import reconcile_objective_with_allowance  # noqa: E402

_BIG_DEVS = (1e-6, -9.5417e-7, 0.0)  # signed sum 1.23e-5, but |c|*|dev| adds up to about 1.5e-4 (J11-sized allowance)


def _big_allowance_values():
    values = [4 + _BIG_DEVS[0], 3 + _BIG_DEVS[1], 0.0]
    raw = sum(c * x for c, x in zip((81, 72, 66), values))
    return values, raw


def test_the_big_allowance_setup_is_what_the_reviewer_measured():
    values, raw = _big_allowance_values()
    assert raw == pytest.approx(540.0000123, abs=2e-9)
    obj, allowance = reconcile_objective_with_allowance(raw, (81, 72, 66), values)
    assert obj == 540.0 and 1.4e-4 < allowance < 1.7e-4


@pytest.mark.parametrize("excess", [1e-5, 1e-4, 1.4e-4])
def test_a_bound_above_the_raw_objective_by_more_than_float_noise_writes_the_note_even_with_a_large_allowance(monkeypatch, excess):
    values, raw = _big_allowance_values()
    solved = _solve_model_stage(monkeypatch, _model_for((81, 72, 66), (4, 3, 0)), raw, values, bound=raw + excess)
    r = solved.result
    assert r.objective == 540 and r.bound_ceil == 540
    assert str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT), (excess, r.solver_message)
    label = _claim_kept(r)
    assert not label.proof_claim_allowed and label.proof_claim_reason == BOUND_ABOVE_INCUMBENT


def test_a_capped_allowance_does_not_hide_a_bound_above_the_raw_objective(monkeypatch):
    # reviewer's capped case: 100000 * 2.4e-6 = 0.24 of deviation, raw objective 540.24 accepted as 540
    model = _model_for((100_000, 1), (0, 540))
    values = [2.4e-6, 540.0]
    raw = 100_000 * values[0] + values[1]
    assert raw == pytest.approx(540.24, abs=1e-9)
    assert reconcile_objective_with_allowance(raw, (100_000, 1), values)[0] == 540.0
    for bound in (540.3, 540.45, 540.49):  # ceiling 541 contradicts the plan of 540; all were silently clipped before
        r = _solve_model_stage(monkeypatch, model, raw, values, bound=bound).result
        assert r.objective == 540 and r.bound_ceil == 540
        assert str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT), bound
    # the bound that IS the solver's raw objective is its own number for the plan: no note (the rule as written)
    own = _solve_model_stage(monkeypatch, model, raw, values, bound=raw).result
    assert not str(own.solver_message).startswith(BOUND_ABOVE_INCUMBENT)


def test_a_bound_between_the_rounded_objective_and_the_raw_objective_is_the_solvers_own_noise(monkeypatch):
    # catches a rule that compares the bound with the rounded objective R plus the margin instead of the RAW objective:
    # raw 540.0000123, bound 540.00001 lies above R + margin (540.0000015) and below raw
    values = [4 + 1e-7, 3 + 5.8333333e-8, 0.0]
    solved = _solve_model_stage(monkeypatch, _model_for((81, 72, 66), (4, 3, 0)), 540.0000123, values, bound=540.00001)
    assert not str(solved.result.solver_message).startswith(BOUND_ABOVE_INCUMBENT)
    assert _claim_kept(solved.result).proof_claim_allowed


def test_the_comparison_uses_the_solvers_bound_not_the_snapped_one(monkeypatch):
    # catches a rule that compares the SNAPPED bound. Raw objective 540.00001 (deviations 1e-5 upward), solver bound
    # 540.000015: above raw + margin (540.0000115), so it is a contradiction. The snap lowers it by 4.4e-6 to 540.0000106,
    # which would sit below raw + margin, and the note would be lost; the ceiling of the snapped bound is still 541.
    values = [4 + 1e-7, 3 + (1e-5 - 8.1e-6) / 72, 0.0]
    raw = 81 * 1e-7 + 72 * (1e-5 - 8.1e-6) / 72 + 540.0
    assert raw == pytest.approx(540.00001, abs=1e-9)
    solved = _solve_model_stage(monkeypatch, _model_for((81, 72, 66), (4, 3, 0)), 540.00001, values, bound=540.000015)
    r = solved.result
    assert r.objective == 540 and r.bound_ceil == 540
    assert str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT)


@pytest.mark.parametrize("excess,note", [
    (5e-7, False),    # DECISION_LOG 2026-10-22 open polish: bound = raw + 5e-7 is inside the float margin
    (1.5e-6, False),  # just below the margin _BOUND_TOL + 1e-9 * |raw| = 1e-6 + 5.4e-7 = 1.54e-6
    (1.6e-6, True),   # just above the margin: no longer the solver's own number
])
def test_the_float_margin_of_the_solvers_own_number_has_its_boundary_at_bound_tol_plus_relative_noise(monkeypatch, excess, note):
    values = [4 + 1e-7, 3 + 5.8333333e-8, 0.0]
    raw = 540.0000123
    solved = _solve_model_stage(monkeypatch, _model_for((81, 72, 66), (4, 3, 0)), raw, values, bound=raw + excess)
    r = solved.result
    assert r.objective == 540 and r.bound_ceil == 540
    assert str(r.solver_message).startswith(BOUND_ABOVE_INCUMBENT) is note, (excess, r.solver_message)
    assert _claim_kept(r).proof_claim_allowed is (not note)


# ---------------------------------------------------------------- E14 (2026-10-22): licence-type failures are retried
@pytest.fixture(autouse=True)
def _no_real_pause(monkeypatch):
    """The retry pause is a module constant (5 s); the tests never sleep for real (raising=False: red-phase safe)."""
    monkeypatch.setattr(gb, "LICENCE_RETRY_PAUSE_SECONDS", 0.0, raising=False)


_LICENCE_FAIL = (500, "?", ["Gurobi: license expired"])
_SECRET = "ZX-SECRET-4711 someone@example.org"


class _FlakyAmpl(_ValueAmpl):
    """Scripted solves: each ``script`` entry ``(num, message, log_lines)`` is one failing solve; later solves succeed.

    Every solve snapshots what the stage code handed to AMPL (model object, option values, eval texts), so a test can
    compare the first attempt with each retry.
    """

    def __init__(self, script):
        super().__init__(_NOISY_OBJECTIVE, _noisy_values())
        self.script, self.loaded, self.evals, self.attempts = list(script), [], [], []
        self.session_log = None

    def eval(self, text):
        super().eval(text)
        self.evals.append(text)

    def solve(self):
        self.attempts.append({"model": self.loaded[-1], "options": dict(self.option), "evals": list(self.evals)})
        self.evals.clear()
        if self.script:
            self.num, self.message, log = self.script.pop(0)
            self.session_log.extend(log)
        else:
            self.num, self.message = 0, "Gurobi 13.0.3: optimal solution; objective 540"


def _flaky_stage(monkeypatch, script, *, model=None, settings=None, **kwargs):
    ampl = _FlakyAmpl(script)
    monkeypatch.setattr(gb, "load_day_model", lambda a, m: a.loaded.append(m))
    session = _FakeSession(ampl)
    ampl.session_log = session._log
    model = model or _noise_model()
    try:
        return gb.gurobi_solve_stage(session, model, settings or GurobiSettings(), **kwargs), ampl, model
    except GurobiBackendUnavailable as exc:
        return exc, ampl, model


def _normal(result):
    return dataclasses.replace(result, wall_seconds=None, solve_retries=0)


def test_the_retry_pause_default_is_a_few_seconds():
    assert 5.0 <= gb.LICENCE_RETRY_PAUSE_SECONDS <= 10.0 or gb.LICENCE_RETRY_PAUSE_SECONDS == 0.0  # 0.0: the fixture above
    assert gb.LICENCE_RETRIES == 2


def test_a_licence_failure_then_success_gives_the_normal_result_with_one_retry(monkeypatch):
    clean, _, _ = _flaky_stage(monkeypatch, [])
    retried, ampl, _ = _flaky_stage(monkeypatch, [_LICENCE_FAIL])
    assert retried.result.solve_retries == 1 and clean.result.solve_retries == 0
    assert _normal(retried.result) == _normal(clean.result) and retried.values == clean.values
    assert (retried.result.status, retried.result.objective) == ("optimal", 540)
    assert len(ampl.attempts) == 2


def test_two_licence_failures_then_success_give_two_retries_and_pause_each_time(monkeypatch):
    pauses: list = []
    solved, ampl, _ = _flaky_stage(monkeypatch, [_LICENCE_FAIL, (500, "?", ["Gurobi: license not found"])],
                                   retry_pause=7.5, sleep=pauses.append)
    assert solved.result.solve_retries == 2 and solved.result.objective == 540 and len(ampl.attempts) == 3
    assert pauses == [7.5, 7.5]


def test_three_licence_failures_raise_with_scrubbed_facts_only(monkeypatch):
    fail = (500, f"Gurobi 13.0.3: license expired {_SECRET}", [f"license error {_SECRET}"])
    exc, ampl, _ = _flaky_stage(monkeypatch, [fail, fail, fail])
    assert isinstance(exc, GurobiBackendUnavailable) and len(ampl.attempts) == 3
    text = str(exc)
    assert "500" in text and "licence" in text and "2" in text
    assert "ZX-SECRET" not in text and "example.org" not in text and "expired" not in text and "error" not in text


def test_a_missing_program_is_raised_at_once_without_retry_or_pause(monkeypatch):
    # lead decision 2026-10-22: only the licence kind is retried; a missing program is permanent
    gone = (999, "Cannot invoke gurobi: no such program.", [])
    pauses: list = []
    exc, ampl, _ = _flaky_stage(monkeypatch, [gone, gone, gone], sleep=pauses.append)
    assert isinstance(exc, GurobiBackendUnavailable) and len(ampl.attempts) == 1 and pauses == []
    assert "999" in str(exc) and "binary" in str(exc) and "0 licence retries" in str(exc)


def test_a_missing_program_after_a_licence_failure_stops_at_once_and_counts_the_retry(monkeypatch):
    gone = (999, "Cannot invoke gurobi: no such program.", [])
    exc, ampl, _ = _flaky_stage(monkeypatch, [_LICENCE_FAIL, gone, gone])
    assert isinstance(exc, GurobiBackendUnavailable) and len(ampl.attempts) == 2
    assert "binary" in str(exc) and "1 licence retries" in str(exc)


def test_a_non_licence_failure_is_not_retried_and_stays_rejected(monkeypatch):
    pauses: list = []
    solved, ampl, _ = _flaky_stage(monkeypatch, [(500, "Gurobi: out of memory", ["Optimize a model"])], sleep=pauses.append)
    assert len(ampl.attempts) == 1 and pauses == []
    assert solved.result.status == "rejected" and solved.result.stop_reason == "solver_failure" and solved.result.solve_retries == 0


def test_a_failure_below_500_with_licence_words_is_not_retried(monkeypatch):
    solved, ampl, _ = _flaky_stage(monkeypatch, [(150, "license expired soon", [])])
    assert len(ampl.attempts) == 1 and solved.result.solve_retries == 0


def test_a_retry_hands_ampl_exactly_the_same_model_options_and_setup(monkeypatch):
    settings = GurobiSettings(time_limit=12.0, work_limit=34.0, seed=7, threads=1)
    _, ampl, model = _flaky_stage(monkeypatch, [_LICENCE_FAIL, _LICENCE_FAIL], settings=settings)
    assert len(ampl.attempts) == 3 and len(ampl.loaded) == 3
    assert all(m is model for m in ampl.loaded)
    first = ampl.attempts[0]
    assert "tech:seed=7" in first["options"]["gurobi_options"] and "lim:work=34" in first["options"]["gurobi_options"]
    assert first["options"]["solver"] == "gurobi" and first["evals"]  # the bestbound sentinel was written
    for later in ampl.attempts[1:]:
        assert later == first


_PROBE_LICENCE = (500, "?", "Gurobi: license expired")  # (solve_result_num, solve_message, the solve command's own output)
_PROBE_BINARY = (999, "?", "Cannot invoke gurobi: no such program.")
_PROBE_OK = (0, "Gurobi 13.0.3: optimal solution", "")


def _probe_session(monkeypatch, script):
    """An ``AmplSession`` whose probe solves are scripted ``(num, message, output)`` triples (the last one repeats);
    the REAL ``backend_absent_kind`` classifies them. Returns ``(session, solves, pauses)``."""
    from uniride_core.exact import ampl_backend as ab

    solves, pauses = [], []

    class Probe:
        option: dict = {}

        def reset(self):
            pass

        def eval(self, text):
            pass

        def solve(self, return_output=False):
            solves.append(1)
            return script[min(len(solves), len(script)) - 1][2]

        def get_value(self, name):
            num, message, _ = script[min(len(solves), len(script)) - 1]
            return {"solve_result_num": num, "solve_message": message}[name]

    session = ab.AmplSession.__new__(ab.AmplSession)
    session.settings = SolverSettings()
    session._ampl = Probe()
    monkeypatch.setattr(ab.time, "sleep", pauses.append)
    return session, solves, pauses


def test_a_probe_licence_failure_is_retried_and_the_retries_are_kept_on_the_session(monkeypatch):
    session, solves, pauses = _probe_session(monkeypatch, [_PROBE_LICENCE, _PROBE_LICENCE, _PROBE_OK])
    assert session._solver_version() == "Gurobi 13.0.3" and len(solves) == 3
    assert session.probe_retries == 2 and pauses == [session.PROBE_PAUSE_SECONDS] * 2
    clean, _, _ = _probe_session(monkeypatch, [_PROBE_OK])
    assert clean._solver_version() == "Gurobi 13.0.3" and clean.probe_retries == 0


def test_three_probe_licence_failures_raise_after_two_retries(monkeypatch):
    session, solves, _ = _probe_session(monkeypatch, [_PROBE_LICENCE])
    with pytest.raises(ExactBackendUnavailable, match="2 probe retries"):
        session._solver_version()
    assert len(solves) == 3


def test_a_probe_with_a_missing_program_is_raised_at_once_without_retry_or_pause(monkeypatch):
    session, solves, pauses = _probe_session(monkeypatch, [_PROBE_BINARY])
    with pytest.raises(ExactBackendUnavailable):
        session._solver_version()
    assert len(solves) == 1 and pauses == []


def test_a_probe_failure_without_absence_evidence_is_a_defect_and_is_not_retried(monkeypatch):
    session, solves, pauses = _probe_session(monkeypatch, [(500, "Gurobi: out of memory", "")])
    with pytest.raises(RuntimeError):
        session._solver_version()
    assert len(solves) == 1 and pauses == []


def test_a_stage_result_with_retries_passes_the_repr_privacy_guard():
    # test_exact_ampl_backend.py::test_result_records_versions_and_options_without_paths rejects "licen" anywhere in a repr;
    # a field named licence_retries made it fail with a real solver (found by the unfiltered run), so the field is solve_retries
    assert "licen" not in repr(StageResult(solve_retries=2)).lower()
