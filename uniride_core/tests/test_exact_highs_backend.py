"""WP-E11 J4: HiGHS backend and stage runner (design JOINT_DAY_MODEL_DESIGN.md 2.4, 4.1-4.3).

Tests that solve with HiGHS carry ``requires_highspy`` and are skipped WITH a reason when ``highspy`` is absent (never
silently, never for any other problem). Labelling, stage propagation, option strings and absence are tested with fake
stage solvers and need no solver; no test runs a long solve.
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import pytest

from uniride_core.exact import highs_backend
from uniride_core.exact.ampl_backend import StageResult
from uniride_core.exact.day_instance import NOT_RUN_ENUMERATION_CAP, build_day_instance
from uniride_core.exact.day_joint import PEAK, build_joint_model
from uniride_core.exact.day_oracle import brute_force_day_optimum, enumerate_stage_optimum
from uniride_core.exact.highs_backend import (
    DEFAULT_TIME_LIMIT_SECONDS,
    HighsBackendUnavailable,
    HighsSettings,
    StageSolve,
    check_integer_solution,
    classify_highs_outcome,
    highs_probe,
    highs_solve_stage,
    run_day_stages,
)
from uniride_core.tests.test_exact_day_joint_model import (
    ARCS,
    CAR,
    HAND,
    LARGE,
    RANDOM,
    _fits,
    cell,
    make_wave,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def highs():
    """Skip, with the reason, only when highspy is genuinely absent; a broken install fails."""
    available, version, reason = highs_probe()
    if not available:
        pytest.skip(f"highspy unavailable: {reason}")
    return version


def _typed_cell():
    w1 = make_wave("w1", "pickup", 500, [("SwA", "Sw"), ("SoB", "So")], ARCS)
    w2 = make_wave("w2", "pickup", 500, [("SoB", "So"), ("SoB", "So")], ARCS)
    return cell([w1, w2], (LARGE, CAR))


def _opt(value):
    return StageResult(status="optimal", stop_reason="optimal", objective=value, bound=value, bound_ceil=value)


# ------------------------------------------------------------------ 1. oracle set through HiGHS
@pytest.mark.requires_highspy
@pytest.mark.parametrize("aggregate", [False, True], ids=["plain", "aggregated"])
@pytest.mark.parametrize("name,waves,types,large_limit", HAND, ids=[c[0] for c in HAND])
def test_hand_instances_through_highs_give_the_oracle_tuple(highs, name, waves, types, large_limit, aggregate):
    oracle = brute_force_day_optimum(waves, types, large_limit=large_limit).objective
    inst = build_day_instance(waves, types)
    res = run_day_stages(inst, large_limit=large_limit, aggregate=aggregate)
    if oracle is None:
        assert res.status == "infeasible_proven" and res.objective is None, f"{name}: {res.status} {res.objective}"
        assert res.stages[0].result.stop_reason == "infeasible"
        return
    assert res.objective == oracle, f"{name}: HiGHS {res.objective} oracle {oracle}"
    assert res.status == "optimal" and not res.non_lexicographic and not res.timing_dependent
    assert len(res.stages) == (3 if len(types) == 2 else 2)
    assert all(s.result.status == "optimal" and s.result.stop_reason == "optimal" for s in res.stages)
    assert res.stages[-1].selection  # the incumbent plan is reported


@pytest.mark.requires_highspy
def test_random_instances_through_highs_give_the_oracle_tuple(highs):
    checked = 0
    for name, waves, types, large_limit in RANDOM:
        if not _fits(waves, types):
            continue
        oracle = brute_force_day_optimum(waves, types, large_limit=large_limit).objective
        for aggregate in (False, True):
            res = run_day_stages(build_day_instance(waves, types), large_limit=large_limit, aggregate=aggregate)
            assert res.objective == oracle, f"{name} aggregate={aggregate}: HiGHS {res.objective} oracle {oracle}"
            assert (res.status == "optimal") == (oracle is not None)
        checked += 1
    assert checked >= 40


@pytest.mark.requires_highspy
def test_canonical_mps_read_by_highs_gives_the_same_optimum_as_the_api_path(highs, tmp_path):
    hp = highs_backend._import_highspy()
    inst = _typed_cell()
    compared = 0
    for stage, fixed in ((1, {}), (2, {"peak": 1}), (3, {"peak": 1, "total_minutes": 15})):
        model = build_joint_model(inst, stage=stage, large_limit=1, fixed=fixed, aggregate=True)
        path = tmp_path / f"s{stage}.mps"
        path.write_bytes(model.to_mps())
        h = hp.Highs()
        h.setOptionValue("output_flag", False)
        assert h.readModel(str(path)) == hp.HighsStatus.kOk
        h.run()
        via_api = highs_solve_stage(model)
        assert via_api.result.status in ("optimal", "infeasible_proven")
        if via_api.result.status == "optimal":
            assert round(h.getInfo().objective_function_value) == via_api.result.objective
            compared += 1
    assert compared >= 1


@pytest.mark.requires_highspy
def test_a_zero_time_limit_is_a_timing_dependent_wall_limit_stop_and_later_stages_are_skipped(highs):
    res = run_day_stages(_typed_cell(), large_limit=1, settings=HighsSettings(time_limit=0.0))
    s1 = res.stages[0].result
    assert s1.stop_reason == "wall_limit" and s1.timing_dependent and s1.status in ("bound_only", "feasible_with_gap")
    assert res.timing_dependent
    if s1.status == "bound_only":
        assert [s.result.status for s in res.stages[1:]] == ["skipped_no_stage1_incumbent"] * 2
        assert res.status == "bound_only" and res.objective is None


# ------------------------------------------------------------------ 2. status labels (fake results)
def test_time_limited_result_with_incumbent_is_feasible_with_gap_and_timing_dependent():
    r = classify_highs_outcome("kTimeLimit", incumbent=7, bound=5.2)
    assert (r.status, r.stop_reason, r.timing_dependent) == ("feasible_with_gap", "wall_limit", True)
    assert (r.objective, r.bound_ceil, r.bound_source) == (7, 6, "solver")


def test_time_limited_result_without_incumbent_is_bound_only_and_timing_dependent():
    r = classify_highs_outcome("kTimeLimit", incumbent=None, bound=2.5)
    assert (r.status, r.stop_reason, r.timing_dependent, r.objective, r.bound_ceil) == ("bound_only", "wall_limit", True, None, 3)
    r = classify_highs_outcome("kTimeLimit", incumbent=None, bound=None)
    assert (r.bound_ceil, r.bound_source) == (0, "trivial_zero")


def test_a_time_limited_day_stage_marks_the_day_timing_dependent():
    timed = StageResult(status="feasible_with_gap", stop_reason="wall_limit", timing_dependent=True, objective=2, bound_ceil=1)
    res = run_day_stages(_typed_cell(), large_limit=1,
                         solve_stage=lambda m, s: StageSolve(timed if m.stage == 1 else _opt(20)))
    assert res.timing_dependent and res.status == "feasible_with_gap"


def test_optimal_requires_the_runners_own_incumbent_versus_ceil_bound_check():
    ok = classify_highs_outcome("kOptimal", incumbent=7, bound=6.0000015)  # ceil(bound - 1e-6) = 7
    assert (ok.status, ok.stop_reason, ok.timing_dependent) == ("optimal", "optimal", False)
    gap = classify_highs_outcome("kOptimal", incumbent=7, bound=6.0000005)  # ceil(bound - 1e-6) = 6, gap 1
    assert (gap.status, gap.stop_reason, gap.timing_dependent) == ("feasible_with_gap", "gap_tolerance", False)
    far = classify_highs_outcome("kOptimal", incumbent=7, bound=5.0)
    assert far.status == "feasible_with_gap" and far.stop_reason == "gap_tolerance"
    assert classify_highs_outcome("kOptimal", incumbent=7, bound=None).status == "feasible_with_gap"  # no bound, no proof
    assert classify_highs_outcome("kOptimal", incumbent=0, bound=None).status == "optimal"  # trivial bound 0 equals incumbent


def test_remaining_status_mapping():
    inf = classify_highs_outcome("kInfeasible", incumbent=None, bound=None)
    assert (inf.status, inf.stop_reason, inf.timing_dependent) == ("infeasible_proven", "infeasible", False)
    for name in ("kIterationLimit", "kSolutionLimit", "kInterrupt", "kObjectiveBound", "kMemoryLimit"):
        with_inc = classify_highs_outcome(name, incumbent=4, bound=3.0)
        assert (with_inc.status, with_inc.stop_reason, with_inc.timing_dependent) == ("feasible_with_gap", "other_limit", True), name
        without = classify_highs_outcome(name, incumbent=None, bound=3.0)
        assert (without.status, without.stop_reason, without.timing_dependent) == ("bound_only", "other_limit", True), name
    for name in ("kUnbounded", "kUnboundedOrInfeasible", "kSolveError", "kLoadError", "kUnknown", "kNotset", "kSomethingNew"):
        r = classify_highs_outcome(name, incumbent=None, bound=None)
        assert (r.status, r.stop_reason, r.timing_dependent) == ("rejected", "solver_failure", False), name
    assert classify_highs_outcome("kOptimal", incumbent=None, bound=1.0).status == "rejected"  # optimal without a solution


def test_a_reported_bound_above_the_incumbent_is_clipped_to_it():
    r = classify_highs_outcome("kOptimal", incumbent=3, bound=3.4)
    assert r.bound_ceil == 3 and r.status == "optimal"


def test_check_integer_solution_refuses_fractional_out_of_bound_and_row_violating_values():
    model = build_joint_model(_typed_cell(), stage=1, large_limit=1)
    names = [v.name for v in model.variables]
    assert check_integer_solution(model, {n: 0.0 for n in names}) is None  # cover rows are violated
    best = enumerate_stage_optimum(model)
    good = {n: float(best.values[n]) for n in names}
    assert check_integer_solution(model, good)[1] == best.objective
    noisy = {n: x + 3e-6 for n, x in good.items()}
    assert check_integer_solution(model, noisy) == (dict(best.values), best.objective)  # within tolerance
    frac = dict(good)
    frac[names[0]] += 0.3
    assert check_integer_solution(model, frac) is None
    over = dict(good)
    over[names[-1]] = float(model.variables[-1].upper + 1)
    assert check_integer_solution(model, over) is None


# ------------------------------------------------------------------ 3. non_lexicographic propagation
def _recording(results):
    calls = []

    def solve(model, settings):
        calls.append(model)
        return StageSolve(results[model.stage])

    return solve, calls


def _peak_fixed_value(model):
    (peak,) = [v for v in model.variables if v.kind == PEAK]
    return peak.lower if peak.lower == peak.upper else None


def test_unproven_stage_1_sets_non_lexicographic_on_later_stages_and_fixes_the_incumbent():
    unproven = StageResult(status="feasible_with_gap", stop_reason="wall_limit", timing_dependent=True, objective=2, bound_ceil=1)
    solve, calls = _recording({1: unproven, 2: _opt(30), 3: _opt(12)})
    res = run_day_stages(_typed_cell(), large_limit=1, solve_stage=solve)
    assert [m.stage for m in calls] == [1, 2, 3]
    assert _peak_fixed_value(calls[1]) == 2 and _peak_fixed_value(calls[2]) == 2  # stage-1 incumbent, not the bound
    assert [s.result.non_lexicographic for s in res.stages] == [False, True, True]
    assert res.non_lexicographic and res.status == "feasible_with_gap" and res.objective == (2, 30, 12)
    assert res.stages[1].result.k_fix == 2


def test_proven_stage_1_is_lexicographic():
    solve, _ = _recording({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    res = run_day_stages(_typed_cell(), large_limit=1, solve_stage=solve)
    assert [s.result.non_lexicographic for s in res.stages] == [False, False, False]
    assert not res.non_lexicographic and res.status == "optimal" and res.objective == (2, 30, 12)


def test_unproven_stage_2_makes_stage_3_non_lexicographic_and_fixes_the_total():
    unproven = StageResult(status="feasible_with_gap", stop_reason="wall_limit", timing_dependent=True, objective=31, bound_ceil=28)
    solve, calls = _recording({1: _opt(2), 2: unproven, 3: _opt(12)})
    res = run_day_stages(_typed_cell(), large_limit=1, solve_stage=solve)
    assert [s.result.non_lexicographic for s in res.stages] == [False, False, True]
    fix = [r for r in calls[2].rows if r.kind == "fix_total"]
    assert len(fix) == 1 and fix[0].rhs == 31


def test_stage_1_without_incumbent_skips_later_stages_without_calling_the_solver():
    bound_only = StageResult(status="bound_only", stop_reason="wall_limit", timing_dependent=True, bound_ceil=1)
    solve, calls = _recording({1: bound_only})
    res = run_day_stages(_typed_cell(), large_limit=1, solve_stage=solve)
    assert [m.stage for m in calls] == [1]
    assert [s.result.status for s in res.stages] == ["bound_only", "skipped_no_stage1_incumbent", "skipped_no_stage1_incumbent"]
    assert res.status == "bound_only" and res.objective is None and not res.non_lexicographic


def test_stage_1_infeasible_stops_and_infeasible_later_stage_after_incumbent_is_rejected():
    inf = StageResult(status="infeasible_proven", stop_reason="infeasible")
    solve, calls = _recording({1: inf})
    res = run_day_stages(_typed_cell(), large_limit=0, solve_stage=solve)
    assert [m.stage for m in calls] == [1] and res.status == "infeasible_proven" and res.objective is None
    solve, _ = _recording({1: _opt(2), 2: inf})
    res = run_day_stages(_typed_cell(), large_limit=1, solve_stage=solve)
    assert res.status == "rejected" and res.stages[1].result.status == "rejected"


def test_homogeneous_day_has_two_stages():
    w = make_wave("w1", "pickup", 500, [("SwA", "Sw"), ("SoB", "So")], ARCS)
    solve, calls = _recording({1: _opt(1), 2: _opt(25)})
    res = run_day_stages(cell([w], (LARGE,)), solve_stage=solve)
    assert [m.stage for m in calls] == [1, 2] and res.objective == (1, 25) and res.mode == "homogeneous"


# ------------------------------------------------------------------ typed order is explicit
def test_stage_runner_passes_fixed_and_minimised_type_explicitly(monkeypatch):
    seen = []
    real = highs_backend.build_joint_model

    def spy(instance, **kw):
        seen.append((kw.get("fixed_type"), kw.get("minimised_type")))
        return real(instance, **kw)

    monkeypatch.setattr(highs_backend, "build_joint_model", spy)
    solve, _ = _recording({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    run_day_stages(_typed_cell(), large_limit=1, solve_stage=solve)
    assert seen == [("large", "car")] * 3


def test_typed_day_with_the_small_type_first_is_refused_unless_types_are_named():
    inst = cell([make_wave("w1", "pickup", 500, [("SoB", "So")], ARCS)], (CAR, LARGE))
    solve, _ = _recording({1: _opt(1), 2: _opt(10), 3: _opt(10)})
    with pytest.raises(ValueError, match="larger"):
        run_day_stages(inst, large_limit=1, solve_stage=solve)
    res = run_day_stages(inst, large_limit=1, fixed_type="large", minimised_type="car", solve_stage=solve)
    assert res.status == "optimal"
    with pytest.raises(ValueError, match="both"):
        run_day_stages(inst, large_limit=1, fixed_type="large", solve_stage=solve)


# ------------------------------------------------------------------ options stored verbatim
def test_option_string_is_verbatim_and_has_the_design_values():
    s = HighsSettings()
    assert (s.threads, s.seed, s.mip_gap, s.mip_gap_abs, s.time_limit) == (1, 0, 0.0, 0.99, 600.0)
    assert DEFAULT_TIME_LIMIT_SECONDS == 600.0
    assert s.option_string() == "output_flag=false threads=1 random_seed=0 mip_rel_gap=0 mip_abs_gap=0.99 time_limit=600"
    assert HighsSettings(time_limit=0.5).option_string().endswith("time_limit=0.5")
    solve, _ = _recording({1: _opt(2), 2: _opt(30), 3: _opt(12)})
    res = run_day_stages(_typed_cell(), large_limit=1, settings=HighsSettings(time_limit=0.5), solve_stage=solve)
    assert res.solver_options == HighsSettings(time_limit=0.5).option_string() and res.time_limit == 0.5
    assert res.solver == "highs"


# ------------------------------------------------------------------ 4. backend absence
def test_missing_highspy_gives_backend_unavailable_without_raising(monkeypatch):
    def absent():
        raise HighsBackendUnavailable("highspy unavailable: ImportError")

    monkeypatch.setattr(highs_backend, "_import_highspy", absent)
    res = run_day_stages(_typed_cell(), large_limit=1)
    assert res.status == "backend_unavailable" and res.objective is None and res.stages == ()
    assert "highspy" in res.note and res.solver_options == HighsSettings().option_string()
    assert highs_probe()[0] is False
    with pytest.raises(HighsBackendUnavailable):
        highs_solve_stage(build_joint_model(_typed_cell(), stage=1, large_limit=1))


def test_import_error_of_highspy_is_mapped_to_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "highspy", None)  # `import highspy` now raises ImportError
    with pytest.raises(HighsBackendUnavailable):
        highs_backend._import_highspy()
    assert run_day_stages(_typed_cell(), large_limit=1).status == "backend_unavailable"


def test_a_backend_that_goes_missing_during_a_stage_is_reported_not_raised():
    def vanish(model, settings):
        raise HighsBackendUnavailable("highspy unavailable: gone")

    assert run_day_stages(_typed_cell(), large_limit=1, solve_stage=vanish).status == "backend_unavailable"


def test_input_that_is_not_ready_is_input_rejected():
    capped = dataclasses.replace(_typed_cell(), status=NOT_RUN_ENUMERATION_CAP)
    assert run_day_stages(capped, large_limit=1, solve_stage=lambda m, s: StageSolve(_opt(1))).status == "input_rejected"


def test_highspy_is_not_imported_at_module_load():
    code = ("import sys, uniride_core.exact, uniride_core.exact.highs_backend; "
            "assert 'highspy' not in sys.modules, 'highspy imported at load'; print('ok')")
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    out = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr[-500:]


@pytest.mark.requires_highspy
def test_a_solve_after_another_highs_run_with_more_threads_still_runs_single_threaded(highs):
    # HiGHS keeps one global scheduler; a stage must not be rejected because an earlier run in the process used
    # other threads (found in J4: the stage ended with model status kNotset and was labelled `rejected`)
    hp = highs_backend._import_highspy()
    model = build_joint_model(_typed_cell(), stage=1, large_limit=1)
    hp.Highs.resetGlobalScheduler(True)
    other = hp.Highs()
    other.setOptionValue("output_flag", False)
    other.setOptionValue("threads", 4)
    other.passModel(highs_backend.to_highs_lp(model, hp))
    other.run()
    out = highs_solve_stage(model)
    assert out.result.status == "optimal" and out.result.objective == enumerate_stage_optimum(model).objective
