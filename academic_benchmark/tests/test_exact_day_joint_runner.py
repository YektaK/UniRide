"""WP-E11 J9a: ``scripts/run_exact_day_joint.py`` (runner plumbing).

The plan names ``uniride_core/tests/test_exact_day_joint_runner.py``; this test imports ``academic_benchmark`` (the J6
checker and the J7 protocol validator), and a ``uniride_core/tests`` file importing ``academic_benchmark`` breaks the core
boundary test, so it lives here.

No real solver is ever called: HiGHS, Gurobi, the AMPL wave solver and (except in the two ``needs_node`` tests) the
TypeScript CLI are replaced by the fakes below. The fake "solver" builds a valid minimum-count cover per wave by a pure
DP and states the true peaks, so the whole certification / checker / manifest path runs on the committed archives.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _p in (REPO / "optimizer_api", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from academic_benchmark.exact_reference import protocol  # noqa: E402
from uniride_core.exact import ampl_backend as ab  # noqa: E402
from uniride_core.exact import highs_backend as hb  # noqa: E402


def _load_runner():
    name = "run_exact_day_joint"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rj = _load_runner()

DATE = "2026-10-08"
COMMIT = "a" * 40
FAKE_SHA = "b" * 64


def _node_modules_root():
    for base in (REPO, *REPO.parents):
        if (base / "node_modules" / "tsx" / "package.json").is_file():
            return base
    return None


HAS_NODE = bool(shutil.which("node")) and _node_modules_root() is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node or node_modules/tsx is not installed (TS confirmation CLI)")


# ---------------------------------------------------------------- fakes
def _min_cover(day_wave, weight):
    """Pure DP: cheapest exact cover of the wave by its columns; ``weight(column)`` is a tuple (compared lexicographically)."""
    cols = list(day_wave.columns)
    memo: dict = {}

    def f(rem):
        if not any(rem):
            return ((0, 0), ())
        if rem in memo:
            return memo[rem]
        i = next(k for k, r in enumerate(rem) if r)
        best = None
        for c in cols:
            if c.multiplicity[i] and all(m <= r for m, r in zip(c.multiplicity, rem)):
                sub = f(tuple(r - m for m, r in zip(c.multiplicity, rem)))
                if sub is None:
                    continue
                w = weight(c)
                cand = ((sub[0][0] + w[0], sub[0][1] + w[1]), sub[1] + (c.column_index,))
                if best is None or cand[0] < best[0]:
                    best = cand
        memo[rem] = best
        return best

    return f(tuple(it.multiplicity for it in day_wave.items))


def _peak(intervals):
    events = sorted([(a, 1) for a, b in intervals if b > a] + [(b, -1) for a, b in intervals if b > a])
    best = cur = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best


def _fake_stage_result(objective, bound=None):
    return ab.StageResult(status="optimal", stop_reason="optimal", objective=objective, bound=objective, bound_ceil=objective,
                          bound_source="solver", wall_seconds=0.01)


def make_fake_day_solver(solver="highs", calls=None, hook=None):
    """A ``run_day_stages`` replacement; ``hook(result)`` may alter the result (to plant a defect)."""

    def run(instance, *, settings=None, aggregate=False, large_limit=None, max_cars=None, fixed_type=None, minimised_type=None):
        if calls is not None:
            calls.append({"solver": solver, "fixed_type": fixed_type, "minimised_type": minimised_type, "large_limit": large_limit,
                          "types": [t.type_id for t in instance.types], "time_limit": settings.time_limit,
                          "aggregate": aggregate, "date": instance.service_date})
        typed = len(instance.types) == 2
        selection, intervals, minutes, car_minutes = [], {}, 0, 0
        for wi, dw in enumerate(instance.waves):
            _, chosen = _min_cover(dw, (lambda c: (1, 0 if c.type_id == instance.types[0].type_id else 1)))
            by_col = {}
            for ci in chosen:
                by_col[ci] = by_col.get(ci, 0) + 1
            for ci, copies in sorted(by_col.items()):
                col = next(c for c in dw.columns if c.column_index == ci)
                selection.append((wi, ci, copies))
                key = col.type_id if typed else "all"
                intervals.setdefault(key, []).extend([(col.start, col.busy_end)] * copies)
                minutes += col.tour * copies
                if typed and col.type_id == instance.types[1].type_id:
                    car_minutes += col.tour * copies
        peak = _peak(intervals.get(instance.types[1].type_id, [])) if typed else _peak(intervals["all"])
        objective = (peak, minutes, car_minutes) if typed else (peak, minutes)
        values = [peak, minutes, car_minutes][: len(objective)]
        stages, fixed = [], {}
        for n, value in enumerate(values, start=1):
            stages.append(hb.DayStage(n, f"fake_stage{n}", "o", FAKE_SHA, _fake_stage_result(value), dict(fixed), tuple(selection)))
            fixed = dict(fixed, **({"peak": peak} if n == 1 else {"total_minutes": minutes}))
        result = hb.DaySolveResult(status="optimal", mode="typed" if typed else "homogeneous", stages=tuple(stages),
                                   objective=objective, solver=solver, solver_version="fake", solver_options=settings.option_string(),
                                   time_limit=settings.time_limit)
        return hook(result) if hook else result

    return run


def make_fake_wave_solver(calls=None):
    cache: dict = {}

    def solve(wave, enumeration, minimize_type, solver, peak):
        if calls is not None:
            calls.append((wave.wave_id, minimize_type, solver))
        key = (wave.wave_id, minimize_type)
        if key not in cache:
            day_like = type("W", (), {})()
            day_like.items = enumeration.items
            columns = []
            for ci, c in enumerate(enumeration.columns):
                columns.append(type("C", (), {"multiplicity": c.multiplicity, "type_id": c.type_id, "column_index": ci})())
            day_like.columns = columns
            cache[key] = _min_cover(day_like, (lambda c: (1 if minimize_type is None or c.type_id == minimize_type else 0, 0)))[0][0]
        return ab.SPSolveResult(wave.wave_id, "optimal", stage1=_fake_stage_result(cache[key]))

    return solve


def fake_cli(cases):
    """Answers like the TS CLI would for a correct plan: cars = peak of the car-labelled routes (from the Python intervals)."""
    results = {}
    for case in cases:
        cooldown = case["pythonCooldowns"]["car"]
        iv = [(r["python"]["start"], r["python"]["end"] + cooldown) for w in case["waves"] for r in w["routes"] if r["label"] == "car"]
        results[case["caseId"]] = {"caseId": case["caseId"], "ok": True, "assignment": {"status": "proven", "cars": _peak(iv)},
                                   "problems": [], "recheck": {"routesChecked": 0, "failures": []}, "intervalDifferences": []}
    return results, ""


def make_deps(*, highs_calls=None, gurobi_calls=None, wave_calls=None, highs_hook=None, cli=fake_cli, crosscheck=True):
    return rj.Deps(highs_run=make_fake_day_solver("highs", highs_calls, highs_hook),
                   gurobi_run=make_fake_day_solver("gurobi", gurobi_calls) if crosscheck else None,
                   wave_solver=make_fake_wave_solver(wave_calls), cli=cli)


@pytest.fixture(autouse=True)
def clean_git(monkeypatch):
    monkeypatch.setattr(rj, "git_state", lambda out: (COMMIT, False))


def run(tmp_path, *args, deps=None):
    out = tmp_path / "out"
    rc = rj.main(["--out", str(out), *args], deps=deps or make_deps())
    return rc, out


def read_csv(path):
    return list(csv.DictReader(Path(path).open(encoding="utf-8", newline="")))


SUBSET = ("--rides", "50", "--dates", DATE, "--limits", "10")


# ---------------------------------------------------------------- red tests of the brief
def test_unsafe_out_exits_2_before_any_work(tmp_path, monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError("work was started before the --out check")

    monkeypatch.setattr(rj, "load_fleet", forbidden)
    monkeypatch.setattr(rj, "git_state", forbidden)
    inside_repo = REPO / "scratch_unsafe_out_j9a"
    below_results_existing = REPO / "docs" / "paper" / "results" / "week-2026-10-05-exact" / "wp-e3-goal1-single" / "sub"
    nonempty = tmp_path / "taken"
    nonempty.mkdir()
    (nonempty / "x.txt").write_text("x", encoding="utf-8")
    for bad in (inside_repo, REPO, below_results_existing, nonempty, REPO / "docs" / "paper" / "results"):
        assert rj.main(["--out", str(bad), "--rides", "50", "--dates", DATE], deps=make_deps()) == 2, bad
    assert not inside_repo.exists() and not below_results_existing.exists()
    assert (nonempty / "x.txt").read_text(encoding="utf-8") == "x"


def test_failing_checker_makes_the_cell_rejected(tmp_path):
    # the solver claims one vehicle fewer than its own plan needs: certification passes, the independent checker must not
    def claim_one_fewer(result):
        stages = list(result.stages)
        s1 = stages[0]
        stages[0] = hb.DayStage(s1.stage, s1.model_name, s1.objective_name, s1.mps_sha256, _fake_stage_result(s1.result.objective - 1),
                                s1.fixed, s1.selection)
        import dataclasses
        return dataclasses.replace(result, stages=tuple(stages), objective=(result.objective[0] - 1, *result.objective[1:]))

    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, deps=make_deps(highs_hook=claim_one_fewer, crosscheck=False),
                  )
    assert rc == 1
    row = read_csv(out / "day_joint.csv")[0]
    assert row["day_status"] == "rejected" and row["checker_ok"] == "False"
    manifest = json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert any("CLAIMED_PEAK" in e for e in manifest["blocking_errors"])


def test_backend_unavailable_stops_the_run_and_writes_nothing(tmp_path):
    calls: list = []
    inner = make_fake_day_solver("highs", calls)

    def flaky(instance, **kw):
        if len(calls) >= 1:  # the second cell
            calls.append("unavailable")
            return hb.DaySolveResult(status="backend_unavailable", note="highspy unavailable", solver="highs")
        return inner(instance, **kw)

    deps = rj.Deps(highs_run=flaky, gurobi_run=make_fake_day_solver("gurobi"), wave_solver=make_fake_wave_solver(), cli=fake_cli)
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, "--rides", "50", "--dates", f"2026-10-06,{DATE},2026-10-07", deps=deps)
    assert rc == 3
    assert calls[-1] == "unavailable" and len(calls) == 2  # the third date was never started, no cell was skipped
    assert not out.exists()


def test_gurobi_backend_unavailable_also_stops(tmp_path):
    gur = lambda instance, **kw: hb.DaySolveResult(status="backend_unavailable", note="no licence", solver="gurobi")  # noqa: E731
    deps = rj.Deps(highs_run=make_fake_day_solver("highs"), gurobi_run=gur, wave_solver=make_fake_wave_solver(), cli=fake_cli)
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, deps=deps)
    assert rc == 3 and not out.exists()


def test_two_cell_subset_run_writes_valid_files(tmp_path):
    rc, out = run(tmp_path, "--fleets", f"{rj.HOMOGENEOUS},large+sedan", *SUBSET)
    assert rc == 0, (out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8")[-800:]
    assert sorted(p.name for p in out.iterdir()) == sorted([*rj.OUT_FILES, rj.MANIFEST_FILENAME])
    with (out / "day_joint.csv").open(encoding="utf-8", newline="") as fh:
        assert next(csv.reader(fh)) == list(rj.CSV_FIELDS)
    rows = read_csv(out / "day_joint.csv")
    assert [(r["fleet"], r["L"]) for r in rows] == [(rj.HOMOGENEOUS, ""), ("large+sedan", "10")]
    assert all(r["day_status"] == "optimal" and r["checker_ok"] == "True" and r["crosscheck_status"] == "agree" for r in rows)
    assert rows[0]["ts_confirmation"] == "not_applicable_single_type" and rows[1]["ts_confirmation"] == "confirmed"
    assert int(rows[0]["K_or_S"]) >= int(rows[0]["lb0"]) >= 1
    manifest = json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert protocol.validate_day_joint_manifest(manifest) == [] and rj.strict_manifest_problems(manifest) == []
    assert manifest["blocking_errors"] == [] and manifest["dirty_working_tree"] is False
    assert manifest["run_history"]["jobs"] == 1 and manifest["run_history"]["invocations"][0]["serial"] is True
    assert manifest["run_history"]["cells_planned"] == 2 and "python_provenance" in manifest
    for name, sha in manifest["output_sha256"].items():
        assert rj.sha256_file(out / name) == sha
    assert set(json.loads((out / "day_joint_plans.json").read_text(encoding="utf-8"))) == {
        f"{rj.HOMOGENEOUS}|{DATE}|R50|L-", f"large+sedan|{DATE}|R50|L10"}
    stages = read_csv(out / "day_joint_stages.csv")
    assert {(s["solver"], s["stage"]) for s in stages if s["fleet"] == "large+sedan"} == {(s, str(n)) for s in ("highs", "gurobi") for n in (1, 2, 3)}
    # every bound contribution shows its proof tag (J2)
    lb = read_csv(out / "lb0.csv")
    assert {r["bound"] for r in lb} >= {"lb0", "lb0w", "lb_l", "lb_s"}
    assert all(":" in c and c.split(":")[-1] in ("solver_proven", "arithmetic_floor", "unverified")
               for r in lb for c in r["contributions"].split(";") if c)


def test_dirty_tree_is_refused_or_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(rj, "git_state", lambda out: (COMMIT, True))
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET)
    assert rc == 2 and not out.exists()
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, "--allow-dirty")
    assert rc == 0
    manifest = json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["dirty_working_tree"] is True and manifest["development_run"] is True
    assert protocol.validate_day_joint_manifest(manifest) == []


@pytest.mark.parametrize("fleet,fixed,minimised", [("large+sedan", "large", "sedan"), ("large+doblo_cap3", "large", "minivan")])
def test_explicit_types_reach_the_stage_runner(tmp_path, fleet, fixed, minimised):
    highs_calls: list = []
    gurobi_calls: list = []
    rc, _ = run(tmp_path, "--fleets", fleet, *SUBSET, deps=make_deps(highs_calls=highs_calls, gurobi_calls=gurobi_calls))
    assert rc == 0
    for call in (*highs_calls, *gurobi_calls):
        assert (call["fixed_type"], call["minimised_type"], call["large_limit"]) == (fixed, minimised, 10)
        assert call["types"] == [fixed, minimised]  # the fixed type is first because the manifest says so, not because of capacity


def test_homogeneous_cell_passes_no_typed_arguments(tmp_path):
    calls: list = []
    rc, _ = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, deps=make_deps(highs_calls=calls))
    assert rc == 0 and calls[0]["fixed_type"] is None and calls[0]["minimised_type"] is None and calls[0]["large_limit"] is None


# ---------------------------------------------------------------- limits, labels, strict values
def test_time_limit_is_a_parameter_with_a_run_label(tmp_path):
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, "--time-limit", "900")
    assert rc == 2 and not out.exists()  # a non-default limit needs a label
    calls: list = []
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, "--time-limit", "900", "--run-label", "long-900",
                  deps=make_deps(highs_calls=calls))
    assert rc == 0 and calls[0]["time_limit"] == 900.0
    manifest = json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["run_label"] == "long-900" and manifest["sensitivity_run"] is True
    assert manifest["solvers"]["highs"]["time_limit_seconds"] == 900.0 and manifest["blocking_errors"] == []
    default = tmp_path / "default"
    assert rj.main(["--out", str(default), "--fleets", rj.HOMOGENEOUS, *SUBSET], deps=make_deps()) == 0
    assert json.loads((default / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))["solvers"]["highs"]["time_limit_seconds"] == 600.0


@pytest.mark.parametrize("bad", [["--jobs", "2"], ["--jobs", "True"], ["--time-limit", "0"], ["--time-limit", "nan"],
                                 ["--time-limit", "True"], ["--rides", "True"], ["--rides", "50,x"], ["--run-label", "a/b"],
                                 ["--fleets", "nope"]])
def test_bad_values_exit_2_before_any_work(tmp_path, monkeypatch, bad):
    monkeypatch.setattr(rj, "load_fleet", lambda *a, **k: (_ for _ in ()).throw(AssertionError("work started")))
    assert rj.main(["--out", str(tmp_path / "o"), *bad], deps=make_deps()) == 2


def test_bool_is_rejected_where_an_int_is_expected():
    with pytest.raises(ValueError):
        rj.strict_int(True, "x")
    assert rj.strict_int(1, "x") == 1
    manifest = {"solvers": {"highs": {"threads": True, "seed": 0, "time_limit_seconds": 600.0, "work_limit": None}},
                "enumeration": {"columns_per_day": {"a": True}}, "run_history": {"jobs": True}}
    problems = rj.strict_manifest_problems(manifest)
    assert len(problems) == 3 and any("threads" in p for p in problems)
    # the protocol validator alone lets True through for threads (== 1): the strict check is the runner's own
    ok = {"solvers": {"highs": {"threads": 1, "seed": 0, "time_limit_seconds": 600.0, "work_limit": None}}}
    assert rj.strict_manifest_problems(ok) == []


def test_the_label_hook_decides_the_status_and_receives_the_crosscheck(tmp_path, monkeypatch):
    seen: list = []

    def hook(facts):
        seen.append(facts)
        return {"day_status": "feasible_with_gap", "bound_used": 2, "bound_source": "hook_test"}

    monkeypatch.setattr(rj, "label_day_cell", hook)
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET)
    assert rc == 0 and seen[0]["crosscheck_status"] == "agree" and seen[0]["solve_status"] == "optimal"
    row = read_csv(out / "day_joint.csv")[0]
    assert (row["day_status"], row["bound_used"], row["bound_source"]) == ("feasible_with_gap", "2", "hook_test")


def test_solver_disagreement_rejects_the_cell(tmp_path):
    def other_value(instance, **kw):
        res = make_fake_day_solver("gurobi")(instance, **kw)
        import dataclasses
        stages = list(res.stages)
        s1 = stages[0]
        stages[0] = hb.DayStage(s1.stage, s1.model_name, s1.objective_name, s1.mps_sha256, _fake_stage_result(s1.result.objective + 1),
                                s1.fixed, s1.selection)
        return dataclasses.replace(res, stages=tuple(stages))

    deps = rj.Deps(highs_run=make_fake_day_solver("highs"), gurobi_run=other_value, wave_solver=make_fake_wave_solver(), cli=fake_cli)
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, deps=deps)
    row = read_csv(out / "day_joint.csv")[0]
    assert rc == 1 and row["day_status"] == "rejected" and row["crosscheck_status"] == "blocking"


def test_crosscheck_can_be_switched_off_and_is_marked(tmp_path):
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, "--no-crosscheck", deps=make_deps(crosscheck=False))
    assert rc == 0
    assert read_csv(out / "day_joint.csv")[0]["crosscheck_status"] == "not_run"
    manifest = json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["crosscheck_enabled"] is False and "gurobi" not in manifest["solvers"]


# ---------------------------------------------------------------- the real TypeScript CLI (no solver)
@needs_node
def test_real_ts_cli_confirms_a_typed_cell_and_refuses_a_single_type(tmp_path):
    rc, out = run(tmp_path, "--fleets", "large+sedan", *SUBSET, deps=make_deps(cli=rj.ud.run_cli))
    assert rc == 0, (out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8")[-600:]
    assert read_csv(out / "day_joint.csv")[0]["ts_confirmation"] == "confirmed"
    # a case with a fixed type only (no minimised type) is refused by the CLI schema: no single-type confirmation exists
    case = {"caseId": "single", "fixedType": {"typeId": "large", "swCapacity": 4, "soCapacity": 5, "cooldownMinutes": 10},
            "limits": {"maxRideTimeMinutes": 50, "maxTourMinutes": 150}, "maxLarge": 1, "waves": []}
    results, error = rj.ud.run_cli([case])
    assert results is None and "exit 2" in error


# ---------------------------------------------------------------- J9a review round 1 (DUZELT): wave-value verdicts, hook, flags
def skewed_wave_solver(mode, calls=None, only=None):
    """The fake wave solver, but Gurobi answers differently: plus1 (proven +1), bound (only a bound), bound_above (a bound above
    the HiGHS optimum) or refused (a status that gives no value)."""
    base = make_fake_wave_solver(calls)

    def solve(wave, enumeration, minimize_type, solver, peak):
        sp = base(wave, enumeration, minimize_type, solver, peak)
        if solver != "gurobi" or (only == "l" and minimize_type is None):
            return sp
        v = sp.stage1.objective
        if mode == "plus1":
            return ab.SPSolveResult(wave.wave_id, "optimal", stage1=_fake_stage_result(v + 1))
        if mode in ("bound", "bound_above"):
            lb = v if mode == "bound" else v + 1
            s1 = ab.StageResult(status="feasible_with_gap", stop_reason="wall_limit", objective=v + 5, bound_ceil=lb)
            return ab.SPSolveResult(wave.wave_id, "feasible_with_gap", stage1=s1, k_lb=lb)
        return ab.SPSolveResult(wave.wave_id, "rejected", note="planted refusal")

    return solve


def deps_with_waves(wave_solver, **kw):
    deps = make_deps(**kw)
    deps.wave_solver = wave_solver
    return deps


def test_wave_disagreement_is_blocking_unverified_and_not_a_proof_label(tmp_path, monkeypatch):
    seen: list = []
    real_hook = rj.label_day_cell
    monkeypatch.setattr(rj, "label_day_cell", lambda facts: (seen.append(facts), real_hook(facts))[1])
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, "--rides", "50", "--dates", f"{DATE},2026-10-07",
                  deps=deps_with_waves(skewed_wave_solver("plus1")))
    assert rc == 1  # blocking error, the run goes on and no cell is dropped
    rows = read_csv(out / "day_joint.csv")
    assert len(rows) == 2 and all(r["wave_values_status"] == "blocking" for r in rows)
    assert all(r["day_status"] != "optimal" for r in rows) and all("wave values contradicted" in r["note"] for r in rows)
    assert all(f["wave_values_status"] == "blocking" for f in seen)
    lb = read_csv(out / "lb0.csv")
    waves = [r for r in lb if r["bound"] == "wave_k_any"]
    assert waves and all(r["contributions"].endswith(":unverified") and "verdict=blocking" in r["wave_value_source"] for r in waves)
    assert all("gurobi=" in r["wave_value_source"] and "highs=" in r["wave_value_source"] for r in waves)  # both values kept
    assert any(":unverified" in r["contributions"] for r in lb if r["bound"] == "lb0w")
    manifest = json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert any("contradict" in e for e in manifest["blocking_errors"])


@pytest.mark.parametrize("mode,verdict,blocking_error", [("bound", "inconclusive", False), ("refused", "inconclusive", False),
                                                          ("bound_above", "blocking", True)])
def test_wave_value_from_a_bound_or_a_refusal_is_inconclusive(tmp_path, mode, verdict, blocking_error):
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, deps=deps_with_waves(skewed_wave_solver(mode)))
    row = read_csv(out / "day_joint.csv")[0]
    assert row["wave_values_status"] == verdict
    assert rc == (1 if blocking_error else 0)
    if verdict == "inconclusive":
        assert row["day_status"] == "optimal"  # a plain optimal does not depend on a wave value


def test_agreeing_wave_values_are_marked_agree(tmp_path):
    rc, out = run(tmp_path, "--fleets", f"{rj.HOMOGENEOUS},large+sedan", *SUBSET)
    assert rc == 0 and {r["wave_values_status"] for r in read_csv(out / "day_joint.csv")} == {"agree"}


def test_no_crosscheck_wave_path_is_not_run_and_a_development_run(tmp_path):
    calls: list = []
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, "--no-crosscheck",
                  deps=make_deps(crosscheck=False, wave_calls=calls))
    assert rc == 0 and {c[2] for c in calls} == {"highs"}
    row = read_csv(out / "day_joint.csv")[0]
    assert row["wave_values_status"] == "not_run" and row["day_status"] == "feasible_with_gap"  # no proof label without the check
    assert json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))["development_run"] is True


def test_trivial_wave_values_are_not_run_and_a_development_run(tmp_path):
    calls: list = []
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, "--wave-values", "trivial", deps=make_deps(wave_calls=calls))
    assert rc == 0 and calls == []
    assert read_csv(out / "day_joint.csv")[0]["wave_values_status"] == "not_run"
    assert json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))["development_run"] is True


def test_a_full_crosschecked_run_is_not_a_development_run(tmp_path):
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET)
    manifest = json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert rc == 0 and manifest["development_run"] is False
    assert manifest["solvers"]["highs"]["version"] == "fake" and manifest["solvers"]["gurobi"]["version"] == "fake"
    assert "stopped_on_backend_unavailable" not in manifest["run_history"]


def test_menu_that_differs_from_the_loader_refuses_the_cell(tmp_path, monkeypatch):
    real = rj.read_json

    def altered(path):
        doc = real(path)
        if str(path).endswith(".menu_options.json"):
            doc = json.loads(json.dumps(doc))
            doc["waves"][0]["anchorMinutes"] += 1
        return doc

    monkeypatch.setattr(rj, "read_json", altered)
    rc, out = run(tmp_path, "--fleets", "large+sedan", *SUBSET)
    row = read_csv(out / "day_joint.csv")[0]
    assert rc == 1 and row["day_status"] == "input_rejected" and "menu demand differs" in row["note"]


# the certificate cell goes through the hook (a tier-2 certificate can be withheld)
def _certificate_cell(tmp_path, monkeypatch, wave_status, tier):
    bm = rj.bounds_mod
    kind = "certificate_wave_min_large" if tier == 2 else "certificate_capacity_floor"
    cert_ = bm.InfeasibilityCertificate(bm.INFEASIBLE_CERTIFIED, tier, kind, 10, 11, 525, (bm.Contribution("w1", 11, "solver_proven"),))
    real = rj.day_bounds

    def fake_bounds(instance, fleet, limit, deps, cfg, errors, tag):
        b, records = real(instance, fleet, limit, deps, cfg, errors, tag)
        records = [rj.WaveRecord(r.kind, r.wave_id, r.used, wave_status, r.detail) for r in records]
        return bm.DayBounds(lb_l=b.lb_l, lb_s=b.lb_s, certificate=cert_), records

    seen: list = []
    real_hook = rj.label_day_cell
    monkeypatch.setattr(rj, "day_bounds", fake_bounds)
    monkeypatch.setattr(rj, "label_day_cell", lambda facts: (seen.append(facts), real_hook(facts))[1])
    calls: list = []
    rc, out = run(tmp_path, "--fleets", "large+sedan", *SUBSET, deps=make_deps(highs_calls=calls))
    return rc, read_csv(out / "day_joint.csv")[0], seen, calls


def test_tier2_certificate_is_labelled_only_when_the_wave_values_agree(tmp_path, monkeypatch):
    rc, row, seen, calls = _certificate_cell(tmp_path, monkeypatch, "agree", 2)
    assert row["day_status"] == "infeasible_certified" and row["certificate_tier"] == "2" and calls == []
    assert seen[0]["certificate"]["tier"] == 2 and seen[0]["certificate_tier"] == 2 and seen[0]["wave_values_status"] == "agree"


@pytest.mark.parametrize("wave_status", ["inconclusive", "blocking", "not_run"])
def test_tier2_certificate_is_withheld_without_two_solver_agreement(tmp_path, monkeypatch, wave_status):
    rc, row, seen, calls = _certificate_cell(tmp_path, monkeypatch, wave_status, 2)
    assert row["day_status"] != "infeasible_certified" and "withheld" in row["note"]
    assert len(calls) >= 1  # the day MIP is still solved
    assert seen[0]["certificate"]["tier"] == 2 and seen[-1]["certificate_tier"] == 2


def test_tier1_certificate_needs_no_wave_value(tmp_path, monkeypatch):
    rc, row, seen, calls = _certificate_cell(tmp_path, monkeypatch, "inconclusive", 1)
    assert row["day_status"] == "infeasible_certified" and row["certificate_tier"] == "1" and calls == []


# the placeholder hook fails closed
GOOD = {"fleet": "f", "date": "d", "ride": 50, "large_limit": None, "solve_status": "optimal", "objective": (3, 100),
        "stage_statuses": ["optimal", "optimal"], "timing_dependent": False, "non_lexicographic": False,
        "bound_above_incumbent": False, "crosscheck_status": "agree", "wave_values_status": "agree", "stage1_bound_ceil": 3,
        "bounds": {}, "certificate": None, "certificate_tier": None}


def test_placeholder_hook_returns_optimal_only_when_everything_agrees():
    assert rj.label_day_cell(GOOD)["day_status"] == "optimal"
    assert rj.label_day_cell(dict(GOOD, wave_values_status="inconclusive"))["day_status"] == "optimal"  # not needed for a plain optimal
    for change, needle in (({"crosscheck_status": "inconclusive"}, "cross-check"), ({"crosscheck_status": "not_run"}, "cross-check"),
                           ({"crosscheck_status": "blocking"}, "cross-check"), ({"wave_values_status": "blocking"}, "wave values"),
                           ({"timing_dependent": True}, "timing"), ({"non_lexicographic": True}, "non_lex"),
                           ({"bound_above_incumbent": True}, "bound_above"), ({"stage_statuses": ["optimal", "feasible_with_gap"]}, "stage")):
        got = rj.label_day_cell(dict(GOOD, **change))
        assert got["day_status"] == "feasible_with_gap" and needle in got["reason"], change
    assert rj.label_day_cell(dict(GOOD, solve_status="bound_only", objective=None))["day_status"] == "bound_only"
    assert rj.label_day_cell(dict(GOOD, solve_status="infeasible_proven", objective=None))["day_status"] == "infeasible_solver_proven"
    assert rj.label_day_cell(dict(GOOD, solve_status="surprise"))["day_status"] == "rejected"


def test_placeholder_hook_withholds_a_tier2_certificate_unless_the_wave_values_agree():
    def cert_(tier):
        return {"tier": tier, "kind": "k", "lower_bound": 4, "point": 1, "large_limit": 3, "contributions": []}

    base = dict(GOOD, solve_status="certificate", objective=None)
    assert rj.label_day_cell(dict(base, certificate=cert_(1), wave_values_status="blocking"))["day_status"] == "infeasible_certified"
    assert rj.label_day_cell(dict(base, certificate=cert_(2), wave_values_status="agree"))["day_status"] == "infeasible_certified"
    for status in ("inconclusive", "blocking", "not_run"):
        got = rj.label_day_cell(dict(base, certificate=cert_(2), wave_values_status=status))
        assert got["day_status"] == "bound_only" and "withheld" in got["reason"] and got["bound_source"].endswith("_withheld")


# ---------------------------------------------------------------- J9a review round 2 (DUZELT): proof tags, blocked l_w, verdict order
def _record_all_days(monkeypatch):
    """Collect every WaveRecord the runner builds (the runner's own records, not a re-derivation)."""
    collected: list = []
    real = rj.day_bounds

    def spy(instance, fleet, limit, deps, cfg, errors, tag):
        bounds, records = real(instance, fleet, limit, deps, cfg, errors, tag)
        collected.extend(records)
        return bounds, records

    monkeypatch.setattr(rj, "day_bounds", spy)
    return collected


def test_every_agreed_solver_value_is_tagged_solver_proven(tmp_path, monkeypatch):
    """J9b grants an arithmetic claim when every contribution is arithmetic_floor: a solver value must never carry that tag."""
    records = _record_all_days(monkeypatch)
    rc, out = run(tmp_path, "--fleets", f"{rj.HOMOGENEOUS},large+sedan", *SUBSET)
    assert rc == 0 and records
    assert {r.verdict for r in records} == {"agree"}
    assert all(r.used.proof == "solver_proven" and r.in_bounds is None for r in records)
    lb = read_csv(out / "lb0.csv")
    for r in lb:
        tags = [c.split(":")[-1] for c in r["contributions"].split(";") if c]
        if r["bound"] in ("wave_k_any", "wave_l", "lb0", "lb0w", "lb_s"):
            assert set(tags) == {"solver_proven"}, (r["bound"], tags)
        elif r["bound"] == "lb_l":  # the merged capacity floor may win a tie with the solver value
            assert set(tags) <= {"solver_proven", "arithmetic_floor"}, tags
        if r["bound"].startswith("wave_"):
            assert r["used_proof"] == "solver_proven" and r["used_value"] == r["value"]


def test_arithmetic_floor_appears_only_for_the_trivial_floors(tmp_path, monkeypatch):
    records = _record_all_days(monkeypatch)
    rc, out = run(tmp_path, "--fleets", f"{rj.HOMOGENEOUS},large+sedan", *SUBSET, "--wave-values", "trivial")
    assert rc == 0
    assert all(r.verdict == "not_run" and r.used.proof == "arithmetic_floor" and r.used.value == (0 if r.kind == "l" else 1)
               for r in records)
    assert records and all(r.kind == "k_any" for r in records)  # trivial mode asks for no l_w at all
    from types import SimpleNamespace

    cfg = rj.Config(wave_values="trivial")
    for minimize_type, value in ((None, 1), ("large", 0)):  # the floors: 1 route for k_any, 0 large routes for l
        rec = rj._wave_record(make_deps(), cfg, SimpleNamespace(wave_id="w"), None, minimize_type=minimize_type, large_id="large",
                              peak=False, errors=[], tag="t")
        assert (rec.used.value, rec.used.proof, rec.verdict) == (value, "arithmetic_floor", "not_run")


def test_blocked_k_any_values_are_unverified_and_used_as_such(tmp_path, monkeypatch):
    records = _record_all_days(monkeypatch)
    rc, out = run(tmp_path, "--fleets", rj.HOMOGENEOUS, *SUBSET, deps=deps_with_waves(skewed_wave_solver("plus1")))
    assert rc == 1 and records and {r.verdict for r in records} == {"blocking"}
    assert all(r.kind == "k_any" and r.used.proof == "unverified" and r.in_bounds is None for r in records)
    assert all(r["used_proof"] == "unverified" for r in read_csv(out / "lb0.csv") if r["bound"] == "wave_k_any")


def test_blocked_l_w_is_replaced_by_the_arithmetic_floor_zero(tmp_path, monkeypatch):
    records = _record_all_days(monkeypatch)
    rc, out = run(tmp_path, "--fleets", "large+sedan", *SUBSET, deps=deps_with_waves(skewed_wave_solver("plus1", only="l")))
    assert rc == 1  # a blocking error, no crash (tier 2 would refuse an unverified l_w)
    row = read_csv(out / "day_joint.csv")[0]
    assert row["wave_values_status"] == "blocking" and row["day_status"] != "infeasible_certified"
    l_records = [r for r in records if r.kind == "l"]
    assert l_records and all(r.verdict == "blocking" and r.used.proof == "unverified" for r in l_records)
    assert all(r.in_bounds.value == 0 and r.in_bounds.proof == "arithmetic_floor" for r in l_records)
    assert all(r.verdict == "agree" for r in records if r.kind == "k_any")
    lb = read_csv(out / "lb0.csv")
    wave_l = [r for r in lb if r["bound"] == "wave_l"]
    # polish 1: the row shows the solver value (unverified) and, separately, what the bounds received
    assert wave_l and all(r["contributions"].endswith(":unverified") and r["used_value"] == "0" and r["used_proof"] == "arithmetic_floor"
                          for r in wave_l)
    assert any(int(r["value"]) > 0 for r in wave_l)
    lb_l = [r for r in lb if r["bound"] == "lb_l"][0]
    tags = [c.split(":")[-1] for c in lb_l["contributions"].split(";") if c]
    assert tags and set(tags) == {"arithmetic_floor"}


def test_wave_values_status_takes_the_worst_verdict():
    def rec(verdict):
        return rj.WaveRecord("k_any", "w", None, verdict, "")

    status = rj.wave_values_status
    assert status([]) == "not_run"
    assert status([rec("agree")]) == "agree"
    assert status([rec("agree"), rec("not_run")]) == "not_run"  # not_run beats agree
    assert status([rec("agree"), rec("not_run"), rec("inconclusive")]) == "inconclusive"  # inconclusive beats not_run
    assert status([rec("not_run"), rec("inconclusive"), rec("agree"), rec("blocking")]) == "blocking"  # blocking beats all
    assert status([rec("inconclusive"), rec("blocking")]) == "blocking"
    assert status([rec("blocking"), rec("agree")]) == "blocking"
