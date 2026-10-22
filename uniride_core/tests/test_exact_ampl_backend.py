"""WP-E2: AMPL set-partitioning backend (design EXACT_SOLVER_AMPL_DESIGN.md sections 1.1 Step B,
1.2, 2, 4, 7, 8). Tests that need AMPL carry the ``requires_ampl`` marker. They are skipped with a
reason ONLY when the backend reports ``backend_unavailable`` (amplpy, AMPL, the solver or its license
is absent; CI has no AMPL). Any other probe failure is a backend defect and fails the tests.

SP vs oracle: the default run uses the first 120 generator instances per solver; set
``UNIRIDE_EXACT_FULL_ORACLE=1`` to run all 500 (design section 8)."""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from exact_enum_helpers import random_instance

REPO = Path(__file__).resolve().parents[2]
EXACT = REPO / "uniride_core" / "exact"
# Default run: the first ORACLE_DEFAULT generator seeds per solver; UNIRIDE_EXACT_FULL_ORACLE=1 runs all 500
# (measured 2026-10-15: all 500 take 374 s with Gurobi and 555 s with HiGHS; the first 120 about 70 s and 130 s).
ORACLE_ALL = 500
ORACLE_DEFAULT = 500 if os.environ.get("UNIRIDE_EXACT_FULL_ORACLE") == "1" else 120
SOLVERS = ("gurobi", "highs")


@pytest.fixture(autouse=True)
def _no_real_probe_pause(monkeypatch):
    """E14: a licence-type probe failure is re-run after a pause (5 s); the fake probes here never sleep for real."""
    from uniride_core.exact import ampl_backend

    monkeypatch.setattr(ampl_backend.AmplSession, "PROBE_PAUSE_SECONDS", 0.0)


def _enum(inst):
    from uniride_core.exact.route_enumeration import enumerate_routes

    return enumerate_routes(inst["direction"], inst["matrix"], inst["location_codes"], inst["classes"],
                            inst["types"], max_ride=inst["ride"], max_tour=inst["tour"])


def _oracle(inst):
    from uniride_core.exact.brute_force import brute_force_optimum

    return brute_force_optimum(inst["direction"], inst["matrix"], inst["classes"], inst["types"],
                               max_ride=inst["ride"], max_tour=inst["tour"],
                               minimize_type=inst["minimize_type"], quota=inst["quota"])


def _route_cost(direction, matrix, nodes):
    path = [0] + list(nodes) + [0]
    arcs = [matrix[a][b] for a, b in zip(path, path[1:])]
    tour = sum(arcs)
    return tour, (tour - arcs[0] if direction == "pickup" else tour - arcs[-1])


def _loc_matrix(L, loc_of):
    locs = [0] + list(loc_of)
    return tuple(tuple(L[locs[i]][locs[j]] for j in range(len(locs))) for i in range(len(locs)))


def _single(sw=4, so=5, total=None):
    from uniride_core.exact import VehicleTypeSpec

    return (VehicleTypeSpec("large", sw, so, 10, total),)


_PROBE: dict = {}


def _require(solver: str) -> None:
    """Skip only for a genuinely absent backend; fail on any other probe problem."""
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
    # the probe really ran and solved the one-student wave correctly
    assert (res.status, res.k, res.d, res.routes) == ("optimal", 1, 10, 1), f"AMPL/{solver} probe solve wrong: {res}"


@pytest.fixture(scope="module", params=SOLVERS)
def session(request):
    from uniride_core.exact import ampl_backend

    _require(request.param)
    with ampl_backend.AmplSession(ampl_backend.SolverSettings(solver=request.param)) as s:
        yield s


# ---------- boundary (section 8 row "Boundary", section 2) ----------
def test_importing_ampl_backend_does_not_import_amplpy():
    code = ("import sys, uniride_core.exact, uniride_core.exact.ampl_backend; "
            "sys.exit(1 if 'amplpy' in sys.modules else 0)")
    res = subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_amplpy_is_imported_only_inside_functions():
    tree = ast.parse((EXACT / "ampl_backend.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert not any(a.name.split(".")[0] == "amplpy" for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "amplpy"
    inner = [n for n in ast.walk(tree) if isinstance(n, ast.Import) and any(a.name == "amplpy" for a in n.names)]
    assert inner, "the backend must import amplpy lazily"


def test_no_hard_coded_ampl_path_or_identity_in_new_files():
    files = [EXACT / "ampl_backend.py", EXACT / "models" / "wave_sp.mod",
             REPO / "requirements-exact.txt", REPO / "academic_benchmark" / "exact_reference" / "protocol.py"]
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\\\?Users|/Users/|/home/|yektakayman|\bAMPL\\\\", text), f.name


def test_wave_sp_model_is_shipped_as_package_data():
    from uniride_core.exact import ampl_backend

    path = ampl_backend.model_path()
    assert path.name == "wave_sp.mod" and path.is_file()
    assert '"uniride_core.exact" = ["models/*.mod"]' in (REPO / "pyproject.toml").read_text(encoding="utf-8")


def test_requirements_exact_is_optional_and_operational_requirements_untouched():
    text = (REPO / "requirements-exact.txt").read_text(encoding="utf-8")
    assert re.search(r"^amplpy==\d+\.\d+\.\d+$", text, re.M)
    for req in (REPO / "optimizer_api").glob("requirements*.txt"):
        assert "amplpy" not in req.read_text(encoding="utf-8")


# ---------- environment lookup and absence (section 7) ----------
def test_locate_ampl_prefers_env_then_local_config_then_default(tmp_path):
    from uniride_core.exact import ampl_backend

    cfg = tmp_path / "ampl_local.json"
    cfg.write_text('{"ampl_dir": "from-config"}', encoding="utf-8")
    assert ampl_backend.locate_ampl({"UNIRIDE_AMPL_DIR": "from-env"}, cfg) == ("from-env", "env")
    assert ampl_backend.locate_ampl({}, cfg) == ("from-config", "local_config")
    assert ampl_backend.locate_ampl({}, tmp_path / "missing.json") == (None, "amplpy_default")


def test_local_config_file_is_git_ignored():
    from uniride_core.exact import ampl_backend

    rel = ampl_backend.LOCAL_CONFIG_PATH.relative_to(REPO).as_posix()
    res = subprocess.run(["git", "check-ignore", "-q", rel], cwd=REPO)
    assert res.returncode == 0, rel


def test_empty_ampl_dir_gives_backend_unavailable_without_raising(tmp_path, monkeypatch):
    from uniride_core.exact import ampl_backend

    monkeypatch.setenv("UNIRIDE_AMPL_DIR", str(tmp_path))
    inst = random_instance(0)
    res = ampl_backend.solve_columns(_enum(inst))
    assert res.status == "backend_unavailable"
    assert res.stage1 is None and res.routes == ()
    assert "UNIRIDE_AMPL_DIR" in res.note and str(tmp_path) not in res.note
    probe = ampl_backend.probe_backend("gurobi")
    assert probe.available is False and probe.reason and probe.status is None


def _fake_result(status, **kw):
    from uniride_core.exact.ampl_backend import SPSolveResult

    return SPSolveResult("probe", status, **kw)


def test_probe_reports_unavailable_only_for_backend_unavailable(monkeypatch):
    from uniride_core.exact import ampl_backend as ab

    monkeypatch.setattr(ab, "solve_columns", lambda *a, **k: _fake_result("backend_unavailable", note="no AMPL"))
    assert ab.probe_backend("gurobi") == ab.ProbeResult(False, reason="no AMPL")
    monkeypatch.setattr(ab, "solve_columns", lambda *a, **k: _fake_result("rejected", note="cross-check"))
    probe = ab.probe_backend("gurobi")
    assert probe.available is True and probe.status == "rejected"  # _require then fails the tests


class _FakeAmpl:
    """Mocked AMPL for the open/probe path: no real solver and no license file is touched."""

    def __init__(self, num=0, message="Gurobi 13.0.3: optimal solution; objective 1", output="", raises=None):
        self.option = {}
        self._num, self._msg, self._out, self._raises = num, message, output, raises

    def reset(self):
        pass

    def eval(self, text):
        pass

    def solve(self, return_output=False):
        if self._raises is not None:
            raise self._raises
        return self._out if return_output else None

    def get_value(self, name):
        return {"solve_message": self._msg, "solve_result_num": self._num}[name]


@pytest.mark.parametrize("fake,absent", [
    (dict(num=999, message="?", output="Cannot invoke gurobi: no such program."), True),
    (dict(num=500, message="Gurobi 13.0.3: license not found"), True),
    (dict(num=500, message="Gurobi 13.0.3: No Gurobi license found"), True),
    (dict(raises=RuntimeError("can't find file gurobi")), True),
    # defects that merely mention "can't find" or "licen": must FAIL, never skip
    (dict(num=500, message="Gurobi 13.0.3: can't find file 'routes.tab'"), False),
    (dict(num=500, message='Gurobi 13.0.3: Unknown option or invalid key "mip:licensefoo"'), False),
    (dict(num=999, message="?", output="Cannot invoke highs: no such program."), False),  # another solver
    (dict(raises=RuntimeError("can't find set COLS in the licensed model")), False),
])
def test_absence_is_only_a_missing_named_solver_or_license(fake, absent):
    from uniride_core.exact import ampl_backend as ab

    s = ab.AmplSession(ab.SolverSettings(solver="gurobi"))
    s._ampl = _FakeAmpl(**fake)
    expected = ab.ExactBackendUnavailable if absent else RuntimeError
    with pytest.raises(expected) as info:
        s._solver_version()
    if not absent:
        assert not isinstance(info.value, ab.ExactBackendUnavailable)


def test_probe_skips_for_missing_solver_and_fails_for_a_defect_message(monkeypatch):
    from uniride_core.exact import ampl_backend as ab

    monkeypatch.setattr(sys.modules[__name__], "_PROBE", {})
    outcomes = []
    for fake, want in ((dict(num=999, message="?", output="Cannot invoke gurobi: no such program."), "skip"),
                       (dict(num=500, message="Gurobi 13.0.3: can't find file 'x.tab'"), "fail"),
                       (dict(num=500, message="Gurobi 13.0.3: licensing banner parse error at key 3"), "fail")):
        def fake_open(self, fake=fake):
            self._ampl = _FakeAmpl(**fake)
            self.solver_version = self._solver_version()

        monkeypatch.setattr(ab.AmplSession, "open", fake_open)
        monkeypatch.setattr(ab.AmplSession, "close", lambda self: None)
        _PROBE.pop("gurobi", None)
        try:  # a skip must not escape: the test itself would then be reported as skipped
            _require("gurobi")
            got = "ran"
        except pytest.skip.Exception:
            got = "skip"
        except pytest.fail.Exception:
            got = "fail"
        outcomes.append((got, want))
    assert [g for g, _ in outcomes] == [w for _, w in outcomes]


def test_probe_exception_propagates_and_is_never_a_skip(monkeypatch):
    from uniride_core.exact import ampl_backend as ab

    def boom(*a, **k):
        raise ValueError("selection does not cover every occurrence exactly once")

    monkeypatch.setattr(ab, "solve_columns", boom)
    with pytest.raises(ValueError):
        ab.probe_backend("gurobi")
    _PROBE.pop("fake-solver", None)
    monkeypatch.setattr(ab, "probe_backend", lambda solver: boom())
    with pytest.raises(pytest.fail.Exception):
        _require("fake-solver")
    _PROBE.pop("fake-solver", None)
    monkeypatch.setattr(ab, "probe_backend", lambda solver: ab.ProbeResult(True, status="feasible_with_gap", k=1, d=12))
    with pytest.raises(AssertionError):
        _require("fake-solver")
    _PROBE.pop("fake-solver", None)


def test_missing_amplpy_gives_backend_unavailable(monkeypatch):
    from uniride_core.exact import ampl_backend

    monkeypatch.setitem(sys.modules, "amplpy", None)
    res = ampl_backend.solve_columns(_enum(random_instance(2)))
    assert res.status == "backend_unavailable" and "amplpy" in res.note


# ---------- option strings (F17) and limits (section 1.2, 4) ----------
def test_option_strings_use_qualified_names_only():
    from uniride_core.exact import ampl_backend as ab

    g = ab.solver_option_string(ab.SolverSettings(solver="gurobi"), peak=False)
    h = ab.solver_option_string(ab.SolverSettings(solver="highs"), peak=True)
    for s in (g, h):
        for opt in ("mip:bestbound=1", "tech:threads=1", "tech:seed=0", "mip:gap=0", "mip:gapabs=0.99"):
            assert opt in s.split()
        assert not re.search(r"(^|\s)bestbound=", s)
    assert (ab.DEFAULT_WORK_LIMIT, ab.PEAK_WORK_LIMIT) == (20, 200)  # owner decision 2026-10-16 (E03)
    assert "lim:time=60" in g.split() and "lim:work=20" in g.split()
    assert "lim:time=600" in h.split() and not any(o.startswith("lim:work") for o in h.split())
    assert ab.wall_limit_seconds(False) == 60 and ab.wall_limit_seconds(True) == 600
    gp = ab.solver_option_string(ab.SolverSettings(solver="gurobi"), peak=True)
    assert "lim:work=200" in gp.split()


@pytest.mark.parametrize("num,msg,obj,bound,want", [
    (0, "Gurobi 13.0.3: optimal solution; objective 28", 28.0, 28.0, ("optimal", "optimal", False, 28, 28)),
    (0, "HiGHS 1.15.1: optimal solution; objective 28", 28.0, 27.2, ("optimal", "optimal", False, 28, 28)),
    (99, "Solution determined by presolve;", 10.0, None, ("optimal", "optimal", False, 10, 10)),
    (99, "Solution determined by presolve;", 6.0, 0.0, ("optimal", "optimal", False, 6, 6)),
    (0, "x: optimal solution; objective 28", 28.0, 26.5, ("feasible_with_gap", "gap_tolerance", False, 28, 27)),
    (402, "Gurobi 13.0.3: time limit, feasible solution; objective 1270", 1270.0, 762.0,
     ("feasible_with_gap", "wall_limit", True, 1270, 762)),
    (409, "Gurobi 13.0.3: work limit, feasible solution; objective 19", 19.0, 11.2,
     ("feasible_with_gap", "work_limit", False, 19, 12)),
    (472, "HiGHS 1.15.1: time limit, no solution", 0.0, float("-inf"), ("bound_only", "wall_limit", True, None, 0)),
    (479, "Gurobi 13.0.3: work limit, no solution", 0.0, 4.5, ("bound_only", "work_limit", False, None, 5)),
    (400, "x: limit, feasible solution; objective 5", 5.0, 3.0, ("feasible_with_gap", "other_limit", True, 5, 3)),
    (470, "x: limit, no solution", 0.0, 2.0, ("bound_only", "other_limit", True, None, 2)),
    (0, "x: optimal solution; objective 28", 28.0, 28.3, ("optimal", "optimal", False, 28, 28)),
    (0, "x: optimal solution; objective 28", 28.000005, 28.0, ("optimal", "optimal", False, 28, 28)),
    (299, "Infeasible constraints determined by presolve.", 0.0, None, ("infeasible_proven", "infeasible", False, None, None)),
    (200, "Gurobi 13.0.3: infeasible problem", 0.0, None, ("infeasible_proven", "infeasible", False, None, None)),
    (500, "Gurobi 13.0.3: Unknown option", 0.0, None, ("rejected", "solver_failure", False, None, None)),
])
def test_classify_outcome(num, msg, obj, bound, want):
    from uniride_core.exact.ampl_backend import classify_outcome

    out = classify_outcome(num, msg, obj, bound)
    assert (out.status, out.stop_reason, out.timing_dependent, out.objective, out.bound_ceil) == want


def test_classify_outcome_rejects_fractional_incumbent():
    from uniride_core.exact.ampl_backend import classify_outcome

    assert classify_outcome(0, "optimal solution", 28.4, 28.0).status == "rejected"


# ---------- stage orchestration (section 1.1 "Stage 2 when stage 1 is not proven") ----------
def _fake(outcomes):
    from uniride_core.exact.ampl_backend import classify_outcome

    calls = []

    def call(stage, k_fix):
        calls.append((stage, k_fix))
        return classify_outcome(*outcomes[stage])

    return call, calls


def test_stage2_runs_with_incumbent_and_is_non_lexicographic_when_stage1_unproven():
    from uniride_core.exact.ampl_backend import run_stages

    call, calls = _fake({"stage1": (409, "work limit, feasible solution", 5.0, 3.4),
                         "stage2": (0, "optimal solution", 300.0, 300.0),
                         "free": (0, "optimal solution", 250.0, 250.0)})
    out = run_stages(call)
    assert calls == [("stage1", None), ("stage2", 5), ("free", None)]
    assert out["stage2"].non_lexicographic is True and out["d_lb"] is None and out["d_lb_free"] == 250
    assert out["k_lb_solver"] == 4


def test_stage2_skipped_without_stage1_incumbent():
    from uniride_core.exact.ampl_backend import run_stages

    call, calls = _fake({"stage1": (472, "time limit, no solution", 0.0, 2.0),
                         "free": (0, "optimal solution", 250.0, 250.0)})
    out = run_stages(call)
    assert out["stage2"].status == "skipped_no_stage1_incumbent"
    assert [c[0] for c in calls] == ["stage1", "free"]


def test_proven_stage1_gives_lexicographic_stage2_and_d_lb():
    from uniride_core.exact.ampl_backend import run_stages

    call, calls = _fake({"stage1": (0, "optimal solution", 3.0, 3.0),
                         "stage2": (402, "time limit, feasible solution", 310.0, 290.5),
                         "free": (0, "optimal solution", 250.0, 250.0)})
    out = run_stages(call, d_lb_free=True)
    assert calls[1] == ("stage2", 3)
    assert out["stage2"].non_lexicographic is False and out["d_lb"] == 291 and out["k_lb_solver"] == 3


def test_k_lb_source_names_a_trivial_zero_bound():
    from uniride_core.exact.ampl_backend import _k_lower_bound, run_stages

    call, _ = _fake({"stage1": (472, "time limit, no solution", 0.0, float("-inf")),
                     "free": (0, "optimal solution", 10.0, 10.0)})
    out = run_stages(call)
    assert (out["k_lb_solver"], out["k_lb_solver_source"]) == (0, "trivial_zero")
    res = _enum(random_instance(1))  # typed instance: no capacity or clique floor
    assert _k_lower_bound(res, 0, False, "trivial_zero") == (0, "trivial_zero")
    assert _k_lower_bound(res, 2, False, "solver") == (2, "solver_bound")
    assert _k_lower_bound(res, 2, False, "ampl_presolve") == (2, "ampl_presolve")


def test_stage2_infeasible_after_a_stage1_incumbent_is_rejected(monkeypatch):
    """K is fixed to an existing incumbent's value, so a proven-infeasible stage 2 is a contradiction."""
    import dataclasses

    from uniride_core.exact import ampl_backend as ab

    inst = dict(direction="pickup", matrix=_loc_matrix([[0, 7], [7, 0]], (1, 1)), location_codes=("A", "A"),
                classes=("Sw", "Sw"), types=_single(sw=1, so=0), ride=50, tour=150)
    res = _enum(inst)
    outcomes = {"stage1": dataclasses.replace(ab.classify_outcome(0, "optimal solution", 2.0, 2.0), selection=((0, 2),)),
                "stage2": ab.classify_outcome(200, "infeasible problem", 0.0, None),
                "free": ab.classify_outcome(0, "optimal solution", 28.0, 28.0)}
    s = ab.AmplSession(ab.SolverSettings())
    monkeypatch.setattr(s, "_load", lambda *a, **k: None)
    monkeypatch.setattr(s, "_call", lambda stage, k_fix, peak, ncols: outcomes[stage])
    sp = s.solve_columns(res, occurrence_ids=("a~1", "a~2"))
    assert sp.status == "rejected" and sp.routes == () and sp.k is None
    assert "stage 2 infeasible_proven" in sp.note


def test_stage1_infeasible_skips_everything_else():
    from uniride_core.exact.ampl_backend import run_stages

    call, calls = _fake({"stage1": (299, "Infeasible constraints determined by presolve.", 0.0, None)})
    out = run_stages(call)
    assert out["stage1"].status == "infeasible_proven" and out["stage2"] is None and out["free"] is None
    assert calls == [("stage1", None)]


# ---------- column expansion (E02: a column selected k >= 2 times) ----------
def test_expansion_gives_each_copy_its_own_occurrences_in_sorted_id_order():
    from uniride_core.exact.ampl_backend import expand_selection

    L = [[0, 7, 9], [7, 0, 4], [9, 4, 0]]
    # node order deliberately not id order: A has occurrences b~2, a~1, c~3
    inst = dict(direction="pickup", matrix=_loc_matrix(L, (1, 1, 1, 2)), location_codes=("A", "A", "A", "B"),
                classes=("Sw", "Sw", "Sw", "So"), types=_single(sw=1, so=1), ride=50, tour=150,
                minimize_type=None, quota=None)
    res = _enum(inst)
    ids = ("b~2", "a~1", "c~3", "z~1")
    with_b = next(i for i, c in enumerate(res.columns) if c.multiplicity == (1, 1))
    only_a = next(i for i, c in enumerate(res.columns) if c.multiplicity == (1, 0))
    routes = expand_selection(res, [(only_a, 2), (with_b, 1)], ids)
    assert [r.column_index for r in routes] == sorted([only_a, only_a, with_b])
    got = sorted(o for r in routes for o in r.occurrence_ids)
    assert got == sorted(ids)
    assert only_a < with_b
    assert [o for r in routes for o in r.occurrence_ids if o != "z~1"] == ["a~1", "b~2", "c~3"]
    a_routes = [r for r in routes if r.column_index == only_a]
    assert [r.copy for r in a_routes] == [0, 1]
    assert len({r.occurrence_ids for r in a_routes}) == 2


def test_expansion_refuses_over_or_under_cover():
    from uniride_core.exact.ampl_backend import expand_selection

    inst = dict(direction="pickup", matrix=_loc_matrix([[0, 7], [7, 0]], (1, 1)), location_codes=("A", "A"),
                classes=("Sw", "Sw"), types=_single(sw=1, so=0), ride=50, tour=150)
    res = _enum(inst)
    with pytest.raises(ValueError):
        expand_selection(res, [(0, 3)], ("a~1", "a~2"))
    with pytest.raises(ValueError):
        expand_selection(res, [(0, 1)], ("a~1", "a~2"))


# ---------- requires AMPL: SP vs oracle (section 8 row "SP vs oracle") ----------
def _check_routes(inst, res, sp):
    node_of = {i + 1: i + 1 for i in range(len(inst["classes"]))}
    covered = sorted(o for r in sp.routes for o in r.occurrence_ids)
    assert covered == sorted(node_of), "every occurrence exactly once"
    for r in sp.routes:
        tour, ride = _route_cost(inst["direction"], inst["matrix"], r.occurrence_ids)
        col = res.columns[r.column_index]
        assert (tour, ride) == (col.tour, col.ride) and r.type_id == col.type_id
    counted = [r for r in sp.routes if inst["minimize_type"] is None or r.type_id == inst["minimize_type"]]
    assert (len(counted), sum(r.cost for r in sp.routes)) == (sp.k, sp.d)
    if inst["quota"] is not None:
        assert sum(1 for r in sp.routes if r.type_id == inst["quota"][0]) <= inst["quota"][1]


@pytest.mark.requires_ampl
def test_sp_matches_brute_force_oracle(session):
    from uniride_core.exact import ampl_backend

    t0 = time.perf_counter()
    mismatches, counts = [], {"optimal": 0, "infeasible_proven": 0, "lambda_ge_2": 0}
    for seed in range(ORACLE_DEFAULT):
        inst = random_instance(seed)
        res = _enum(inst)
        want = _oracle(inst).objective
        sp = ampl_backend.solve_columns(res, occurrence_ids=tuple(range(1, len(inst["classes"]) + 1)),
                                        minimize_type=inst["minimize_type"], quota=inst["quota"],
                                        session=session, d_lb_free=False)
        if want is None:
            if sp.status != "infeasible_proven":
                mismatches.append((seed, sp.status, None))
            counts["infeasible_proven"] += sp.status == "infeasible_proven"
            continue
        got = (sp.k, sp.d)
        if sp.status != "optimal" or got != want or sp.stage1.status != "optimal" or sp.stage2.status != "optimal":
            mismatches.append((seed, sp.status, got, want))
            continue
        _check_routes(inst, res, sp)
        counts["optimal"] += 1
        counts["lambda_ge_2"] += any(t >= 2 for _, t in sp.selection)
    elapsed = time.perf_counter() - t0
    print(f"SP vs oracle [{session.settings.solver}] {ORACLE_DEFAULT} instances in {elapsed:.1f} s: {counts}")
    assert mismatches == []
    assert counts["optimal"] + counts["infeasible_proven"] == ORACLE_DEFAULT


@pytest.mark.requires_ampl
def test_same_multiset_column_twice_is_feasible_and_expanded(session):
    from uniride_core.exact import ampl_backend

    inst = dict(direction="pickup", matrix=_loc_matrix([[0, 7], [7, 0]], (1, 1)), location_codes=("A", "A"),
                classes=("Sw", "Sw"), types=_single(sw=1, so=0), ride=50, tour=150, minimize_type=None, quota=None)
    res = _enum(inst)
    sp = ampl_backend.solve_columns(res, occurrence_ids=("a~2", "a~1"), session=session)
    assert sp.status == "optimal" and (sp.k, sp.d) == (2, 28) == _oracle(inst).objective
    assert sp.selection == ((0, 2),)
    assert [(r.copy, r.occurrence_ids) for r in sp.routes] == [(0, ("a~1",)), (1, ("a~2",))]


@pytest.mark.requires_ampl
def test_lambda_upper_bound_is_the_cover_floor(session):
    inst = dict(direction="pickup", matrix=_loc_matrix([[0, 7, 9], [7, 0, 4], [9, 4, 0]], (1, 1, 1, 2, 2)),
                location_codes=("A", "A", "A", "B", "B"), classes=("Sw", "Sw", "Sw", "So", "So"),
                types=_single(sw=2, so=2), ride=50, tour=150)
    res = _enum(inst)
    bounds = session.declared_lambda_bounds(res)
    demand = [it.multiplicity for it in res.items]
    want = [min(demand[i] // a for i, a in enumerate(c.multiplicity) if a > 0) for c in res.columns]
    assert bounds == want and max(want) >= 2


@pytest.mark.requires_ampl
def test_stage2_keeps_the_stage1_route_count(session):
    """min D alone would use two direct routes (D = 30); lexicographic (K, D) is (1, 30)."""
    from uniride_core.exact import ampl_backend

    L = [[0, 10, 10], [5, 0, 25], [5, 25, 0]]
    inst = dict(direction="pickup", matrix=_loc_matrix(L, (1, 2)), location_codes=("A", "B"), classes=("So", "So"),
                types=_single(sw=0, so=2), ride=60, tour=150, minimize_type=None, quota=None)
    res = _enum(inst)
    sp = ampl_backend.solve_columns(res, occurrence_ids=(1, 2), session=session, d_lb_free=True)
    assert _oracle(inst).objective == (1, 40)
    assert (sp.k, sp.d, sp.d_lb) == (1, 40, 40) and sp.status == "optimal"
    assert sp.d_lb_free == 30 and sp.free.objective == 30


@pytest.mark.requires_ampl
def test_fleet_limit_v_max_below_legs_is_enforced(session):
    """Typed: two large (1 So) routes give K_m = 0; with V_max = 1 only one car route (2 So) fits."""
    from uniride_core.exact import VehicleTypeSpec, ampl_backend

    L = [[0, 5, 5], [5, 0, 3], [5, 3, 0]]
    inst = dict(direction="pickup", matrix=_loc_matrix(L, (1, 2)), location_codes=("A", "B"), classes=("So", "So"),
                types=(VehicleTypeSpec("large", 0, 1, 10), VehicleTypeSpec("car", 0, 2, 10)), ride=60, tour=150)
    res = _enum(inst)
    free = ampl_backend.solve_columns(res, occurrence_ids=(1, 2), minimize_type="car", session=session)
    one = ampl_backend.solve_columns(res, occurrence_ids=(1, 2), minimize_type="car", v_max=1, session=session)
    none = ampl_backend.solve_columns(res, occurrence_ids=(1, 2), minimize_type="car", v_max=0, session=session)
    assert (free.status, free.k, free.d, len(free.routes)) == ("optimal", 0, 20, 2)
    assert (one.status, one.k, one.d, len(one.routes)) == ("optimal", 1, 13, 1)
    assert none.status == "infeasible_proven"


@pytest.mark.requires_ampl
def test_bestbound_is_reset_before_every_solve(session):
    """A solve that returns no bound (AMPL presolve settles the model) must not expose an older bound."""
    inst = dict(direction="pickup", matrix=_loc_matrix([[0, 7], [7, 0]], (1, 1)), location_codes=("A", "A"),
                classes=("Sw", "Sw"), types=_single(sw=1, so=0), ride=50, tour=150)
    res = _enum(inst)
    session._load(res, None, None, 2)
    session._ampl.eval("let RouteCount.bestbound := 5;")  # a stale value from an imagined earlier solve
    st = session._call("stage1", None, False, len(res.columns))
    assert st.solver_message.startswith("Solution determined by presolve")
    assert session._read_bound("RouteCount") is None  # the sentinel written before the solve survived
    assert (st.status, st.objective, st.bound_ceil, st.bound_source) == ("optimal", 2, 2, "ampl_presolve")


@pytest.mark.requires_ampl
def test_infeasible_wave_is_proven_infeasible(session):
    from uniride_core.exact import ampl_backend

    inst = dict(direction="pickup", matrix=_loc_matrix([[0, 99], [99, 0]], (1,)), location_codes=("A",),
                classes=("So",), types=_single(sw=0, so=1), ride=50, tour=150)
    res = _enum(inst)
    assert res.columns == ()
    sp = ampl_backend.solve_columns(res, occurrence_ids=(1,), session=session)
    assert sp.status == "infeasible_proven" and sp.stage2 is None and sp.routes == ()


@pytest.mark.requires_ampl
def test_result_records_versions_and_options_without_paths(session):
    from uniride_core.exact import ampl_backend

    sp = ampl_backend.solve_columns(_enum(random_instance(4)), session=session)
    assert sp.ampl_version.startswith("AMPL Version ") and "\n" not in sp.ampl_version
    assert re.match(r"^(Gurobi|HiGHS) \d+\.\d+\.\d+$", sp.solver_version)
    assert sp.amplpy_version and sp.threads == 1 and sp.seed == 0
    assert sp.option_string == ampl_backend.solver_option_string(session.settings, peak=False)
    assert sp.ampl_location == "local AMPL installation used" or sp.ampl_location == "amplpy default lookup"
    blob = repr(sp)
    assert not re.search(r"@|licen|[A-Za-z]:\\|/Users/", blob, re.I)


# ---------- requires AMPL: determinism on archived waves (section 8 row "Determinism") ----------
@pytest.mark.requires_ampl
def test_same_archived_waves_twice_give_identical_results():
    import importlib.util

    from uniride_core.exact import ampl_backend
    from uniride_core.exact.route_enumeration import enumerate_wave

    _require("gurobi")
    spec = importlib.util.spec_from_file_location("exact_archive_loader_e2", REPO / "scripts" / "exact_archive_loader.py")
    loader = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_e2"] = loader
    spec.loader.exec_module(loader)
    camp = loader.load_campaign(REPO / "docs" / "paper" / "results" / "week-2026-10-05-4sw5so")
    waves = sorted(camp.waves_for(90), key=lambda w: (-w.legs, w.wave_id))[:5]
    peaks = {i for v in loader.peak_waves({"4sw5so": camp}).values() for i in v["wave_ids"]}

    def fingerprint(sp):
        stages = tuple((s.status, s.objective, s.bound, s.stop_reason) for s in (sp.stage1, sp.stage2, sp.free))
        return (sp.status, sp.k, sp.d, sp.k_lb, sp.d_lb, sp.d_lb_free, sp.selection, sp.routes, stages)

    runs = []
    for _ in range(2):
        with ampl_backend.AmplSession(ampl_backend.SolverSettings(solver="gurobi")) as s:
            runs.append([fingerprint(ampl_backend.solve_wave(w, enumerate_wave(w, camp.fleet_types),
                                                             peak=w.wave_id in peaks, session=s)) for w in waves])
    assert runs[0] == runs[1]
    assert all(fp[0] == "optimal" for fp in runs[0])


# ---------- integrality is a test of the VALUES, not of the raw objective (J11 finding) ----------
def _wave_stage_call(stage, objective, lam_of, *, bound=None):
    """Run the real ``AmplSession._call`` of ``stage`` on a mocked AMPL session that returns ``objective`` and ``lam_of(r)``."""
    from unittest import mock

    from uniride_core.exact import ampl_backend as ab

    inst = dict(direction="pickup", matrix=_loc_matrix([[0, 7, 7], [7, 0, 7], [7, 7, 0]], (1, 2)), location_codes=("A", "B"),
                classes=("Sw", "Sw"), types=_single(sw=2, so=0), ride=50, tour=150)
    res = _enum(inst)
    ncols = len(res.columns)
    ampl = mock.MagicMock()
    ampl.solve_result = "solved"
    ampl.get_value.side_effect = lambda name: {"solve_result_num": 0, "solve_message": "Gurobi: optimal solution"}.get(
        name, ab._BOUND_SENTINEL if bound is None else bound)
    ampl.get_objective.return_value.value.return_value = objective
    ampl.var.__getitem__.return_value.get_values.return_value.to_dict.return_value = {r: lam_of(r) for r in range(ncols)}
    s = ab.AmplSession(ab.SolverSettings())
    s._ampl = ampl
    s._load(res, None, None, 2)
    return res, s._call(stage, None, False, ncols)


def test_a_wave_duration_with_near_integral_lam_and_a_raw_objective_beyond_the_old_tolerance_is_accepted():
    # one selected column of cost c is taken as 1 - 1.2e-5 / c: each value is inside the 1e-5 tolerance, the raw
    # objective is 1.2e-5 below the integer c (more than the old 1e-5 test on the objective allowed)
    inst_cols = _wave_stage_call("stage2", 0.0, lambda r: 0.0)[0].columns
    r_best = max(range(len(inst_cols)), key=lambda r: inst_cols[r].cost)
    cost = inst_cols[r_best].cost
    assert cost >= 4
    lam = lambda r: 1 - 1.2e-5 / cost if r == r_best else 0.0  # noqa: E731
    _, out = _wave_stage_call("stage2", cost - 1.2e-5, lam, bound=cost - 1.2e-5)
    assert out.status == "optimal" and out.objective == cost and out.selection == ((r_best, 1),)
    assert out.bound == cost - 1.2e-5 and out.bound_ceil == cost  # the wave path keeps the raw bound (no snap, no reconcile)


def test_the_wave_path_does_not_snap_bounds_only_the_gurobi_day_path_does():
    """Design rule of the wave path (EXACT_SOLVER_AMPL_DESIGN 1.2): ceil(bound - 1e-6); the snap is the day path's and TSP's (E10)."""
    from uniride_core.exact.ampl_backend import classify_outcome

    out = classify_outcome(402, "Gurobi 13.0.3: time limit, feasible solution; objective 606", 606.0, 540.000003)
    assert out.bound_ceil == 541 and out.bound == 540.000003


def test_a_wave_stage_with_a_real_objective_mismatch_or_a_fractional_lam_is_still_rejected():
    cols = _wave_stage_call("stage2", 0.0, lambda r: 0.0)[0].columns
    r_best = max(range(len(cols)), key=lambda r: cols[r].cost)
    cost = cols[r_best].cost
    one = lambda r: 1.0 if r == r_best else 0.0  # noqa: E731
    half = lambda r: 1.0 + 3e-5 if r == r_best else 0.0  # noqa: E731
    assert _wave_stage_call("stage2", cost - 0.3, one)[1].status == "rejected"  # solver objective is not the values' objective
    assert _wave_stage_call("stage2", cost + 1.0, one)[1].objective == cost + 1  # existing behaviour: no recheck of equal integers
    assert _wave_stage_call("stage2", cost - 1.2e-5, half)[1].status == "rejected"  # lam outside the variable tolerance


@pytest.mark.parametrize("objective,coefficients,values,want", [
    # J11: 81*4 + 72*3 with deviations adding up to 1.23e-5 below 540 -> the integer objective of the rounded values
    (539.9999877, (81, 72, 66), (4 - 1e-7, 3 - 5.8333333e-8, 0.0), 540.0),
    (540.0000123, (81, 72), (4 + 1e-7, 3 + 5.8333333e-8), 540.0),
    # already integral: unchanged value
    (540.0, (81, 72), (4.0, 3.0), 540.0),
    # a value beyond the variable tolerance: the objective is returned unchanged (the caller rejects it)
    (540.0, (81, 72), (4.0, 3.0 + 3e-5), 540.0),
    (539.9999877, (81, 72), (4.0, 3.0 + 3e-5), 539.9999877),
    # the values do not produce the objective: unchanged
    (539.9999877, (81, 72, 66), (4.0, 3.0, 1.0), 539.9999877),
    (539.6, (81, 72), (4.0, 3.0), 539.6),
    (540.3, (81, 72), (4.0, 3.0), 540.3),
    # non-finite or missing objective: unchanged
    (None, (1,), (1.0,), None),
    (float("inf"), (1,), (1.0,), float("inf")),
])
def test_reconcile_objective(objective, coefficients, values, want):
    from uniride_core.exact.ampl_backend import reconcile_objective

    got = reconcile_objective(objective, coefficients, values)
    assert got == want if want is None or want == float("inf") else got == pytest.approx(want, abs=1e-12)


def test_reconcile_objective_cap_stops_a_large_coefficient_from_moving_the_objective_to_another_integer():
    """The per-value check passes (deviation 8e-6 is inside _INT_TOL), so the 0.25 cap is what decides.

    Coefficient 1e5 and deviation 8e-6 explain 0.8 of objective, more than the gap to the next integer, so without the
    cap an objective 0.55 away from the integer 100000 would be "explained" and silently accepted as 100000. With the cap
    (0.25) it is returned unchanged (the caller rejects it); a gap of 0.2 is still accepted and equals round(raw).
    """
    from uniride_core.exact.ampl_backend import _INT_TOL, reconcile_objective

    values = (1 + 8e-6,)
    assert abs(values[0] - 1) < _INT_TOL  # inside the variable tolerance: the cap, not the per-value check, is tested
    assert reconcile_objective(100_000.55, (100_000,), values) == 100_000.55
    assert reconcile_objective(100_000.45, (100_000,), values) == 100_000.45
    assert reconcile_objective(100_000.2, (100_000,), values) == 100_000.0 == round(100_000.2)
    assert reconcile_objective(99_999.8, (100_000,), values) == 100_000.0 == round(99_999.8)


def test_reconcile_objective_needs_integer_coefficients():
    """Coefficient 81.4 would round to 81 and then 'explain' the objective; any non-integral coefficient returns it unchanged."""
    from uniride_core.exact.ampl_backend import reconcile_objective

    values = (4 - 1e-7, 3 - 5.8333333e-8)
    assert reconcile_objective(539.9999877, (81, 72), values) == 540.0  # integral coefficients: reconciled
    assert reconcile_objective(539.9999877, (81.4, 72), values) == 539.9999877
    assert reconcile_objective(539.9999877, (81.0, 72.0), values) == 540.0  # integral floats are fine


def test_reconcile_objective_with_allowance_returns_what_the_deviations_explain():
    from uniride_core.exact.ampl_backend import reconcile_objective_with_allowance

    obj, allowance = reconcile_objective_with_allowance(540.0000123, (81, 72), (4 + 1e-7, 3 + 5.8333333e-8))
    assert obj == 540.0 and 1.23e-5 < allowance < 1.5e-5  # the explained 1.23e-5 plus the float margin
    obj, allowance = reconcile_objective_with_allowance(540.0, (81, 72), (4.0, 3.0))
    assert obj == 540.0 and 0 < allowance < 2e-6  # nothing to explain: only the float margin
    # not reconciled: the objective comes back unchanged with allowance 0
    assert reconcile_objective_with_allowance(540.3, (81, 72), (4.0, 3.0)) == (540.3, 0.0)
    assert reconcile_objective_with_allowance(540.0, (81, 72), (4.0, 3.0 + 3e-5)) == (540.0, 0.0)
    assert reconcile_objective_with_allowance(None, (1,), (1.0,)) == (None, 0.0)
