"""WP-E3 (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 2, 3, 4, 6, 8, 9): the GOAL 1 runner
``scripts/run_exact_wave_gaps.py`` (single type 4 Sw / 5 So).

The pure parts (wave evaluation, certification, objective cross-check, exact <= GA, CSV schema,
absence exit code) run without AMPL. Tests that solve carry ``requires_ampl`` and are skipped with a
reason ONLY when the backend reports ``backend_unavailable``; any other probe failure fails.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SW5SO = REPO / "docs" / "paper" / "results" / "week-2026-10-05-4sw5so"
SCRIPT = REPO / "scripts" / "run_exact_wave_gaps.py"
for _p in (REPO / "optimizer_api",):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

GA_LABELS = {"ga_protocol": "native", "ga_seed": 42, "ga_commit": "6be127d", "ga_dirty_tree": True}
PEAK = "2026-10-05:pickup:525"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_exact_wave_gaps", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_exact_wave_gaps"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load_script()


@pytest.fixture(scope="module")
def campaign(runner):
    return runner.loader.load_campaign(SW5SO)


def _archive(date="2026-10-05", ride=90):
    arcs_doc = json.loads((SW5SO / f"{date}_R{ride}_repeat1.matrix.json").read_text(encoding="utf-8"))
    resp = json.loads((SW5SO / f"{date}_R{ride}_repeat1.response.json").read_text(encoding="utf-8"))
    return arcs_doc, {j["id"]: j["result"] for j in resp["jobs"]}


def _wave(campaign, wave_id, ride=90):
    return next(w for w in campaign.waves_for(ride) if w.wave_id == wave_id)


def _fake_sp(wave, seqs, *, status="optimal", k_lb=None, d_lb=None, d_lb_free=None, d=None, k_star_proven=True):
    """An ``SPSolveResult`` standing in for the solver (no AMPL): routes are given by their visiting order."""
    from uniride_core.exact import certification as cert
    from uniride_core.exact.ampl_backend import ExpandedRoute, SPSolveResult, StageResult

    k, true_d = cert.recompute_objective(wave, seqs)
    d = true_d if d is None else d
    routes = tuple(ExpandedRoute("large", i, 0, tuple(s), cert.tour_cost(wave, s), 0, cert.tour_cost(wave, s))
                   for i, s in enumerate(seqs))
    s1_status = "optimal" if k_star_proven else "feasible_with_gap"
    s1 = StageResult("stage1", s1_status, s1_status if k_star_proven else "work_limit", objective=k, bound=float(k),
                     bound_ceil=k if k_star_proven else k - 1, bound_source="solver", wall_seconds=0.1)
    s2 = StageResult("stage2", "optimal", "optimal", objective=d, bound=float(d), bound_ceil=d_lb or d,
                     bound_source="solver", k_fix=k, wall_seconds=0.1)
    free = StageResult("free", "optimal", "optimal", objective=d, bound=float(d), bound_ceil=d_lb_free or d,
                       bound_source="solver", wall_seconds=0.1)
    return SPSolveResult(wave.wave_id, status, stage1=s1, stage2=s2, free=free, k=k, d=d,
                         k_lb=k if k_lb is None else k_lb, k_lb_source="solver_bound", d_lb=d if d_lb is None else d_lb,
                         d_lb_free=d if d_lb_free is None else d_lb_free, routes=routes, peak=wave.wave_id == PEAK,
                         column_count=10, solver="gurobi", solver_version="Gurobi 13.0.3")


ENUM = {"model": "SP", "columns": 10, "labels": 20, "seconds": 0.01, "cap_fired": None}


def _evaluate(runner, wave, ga_result, arcs_doc, sp, highs=None):
    return runner.evaluate_wave(wave, ga_result, arcs_doc, sp, ga_labels=GA_LABELS, enum_info=ENUM, highs=highs)


def _ga_seqs(ga_result):
    return [tuple(r["student_ids"]) for r in ga_result["routes"]]


# ---------- pure parts: evaluation of one wave ----------
def test_ga_partition_as_exact_certifies_and_has_zero_gap(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, _fake_sp(wave, _ga_seqs(jobs[PEAK])))
    row = ev["row"]
    assert ev["errors"] == []
    assert row["status"] == "optimal"
    assert row["exact_certified"] is True and row["ga_recertified"] is True and row["objective_check"] == "ok"
    assert row["K_GA"] == row["K_star"] and row["dK"] == 0 and row["gD_note"] == "comparable" and row["gD"] == 0
    assert row["ga_protocol"] == "native" and row["ga_seed"] == 42 and row["ga_commit"] == "6be127d"
    assert row["ga_dirty_tree"] is True and row["peak"] is True and row["fleet"] == "single_4sw5so"
    assert [s["stage"] for s in ev["stages"]] == ["stage1", "stage2", "free"]


def test_tampered_exact_arc_is_rejected_and_never_repaired(runner, campaign):
    """The certificate re-costs on the archived slice: one wrong minute on an exact route -> rejected."""
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    sp = _fake_sp(wave, _ga_seqs(jobs[PEAK]))
    first = wave.location_codes[wave.occurrence_ids.index(_ga_seqs(jobs[PEAK])[0][0])]
    tampered = deepcopy(arcs_doc)
    for a in tampered["arcs"]:
        if (a["origin_code"], a["destination_code"]) == (wave.depot_code, first):
            a["duration_minutes"] += 1
    # the GA side is judged on the same (tampered) slice, so only a mismatch with the matrix of the
    # wave is exercised for the exact side; the GA failure is reported separately
    ev = _evaluate(runner, wave, jobs[PEAK], tampered, sp)
    assert ev["row"]["status"] == "rejected" and ev["row"]["exact_certified"] is False
    assert ev["row"]["K_star"] is None and ev["row"]["D_star"] is None          # nothing is reported as a result
    assert any("certificate" in e for e in ev["errors"])


def test_capacity_violating_exact_routes_are_rejected(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, _fake_sp(wave, [tuple(wave.occurrence_ids)]))
    assert ev["row"]["status"] == "rejected" and ev["row"]["exact_certified"] is False
    assert ev["errors"]


def test_objective_mismatch_is_rejected(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    sp = _fake_sp(wave, _ga_seqs(jobs[PEAK]))
    import dataclasses

    bad = dataclasses.replace(sp, d=sp.d + 1)
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, bad)
    assert ev["row"]["status"] == "rejected" and ev["row"]["objective_check"] != "ok"
    assert ev["row"]["exact_certified"] is True                                  # the routes themselves are fine
    assert any("objective" in e for e in ev["errors"])


def test_exact_worse_than_ga_is_blocking_only_when_optimal(runner, campaign):
    """Splitting a GA route into singletons gives a certified but worse 'exact' partition."""
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    seqs = []
    for s in _ga_seqs(jobs[PEAK]):
        seqs.extend([(o,) for o in s] if len(s) > 1 else [s])
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, _fake_sp(wave, seqs))
    assert ev["row"]["exact_certified"] is True
    assert any("exceeds the GA" in e for e in ev["errors"]) and ev["row"]["exact_le_ga"] is False
    ev2 = _evaluate(runner, wave, jobs[PEAK], arcs_doc,
                    _fake_sp(wave, seqs, status="feasible_with_gap", k_lb=len(_ga_seqs(jobs[PEAK])) - 3,
                             k_star_proven=False))
    assert not any("exceeds the GA" in e for e in ev2["errors"]) and ev2["row"]["exact_le_ga"] is None


def test_ga_recertification_failure_is_blocking(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    ga = deepcopy(jobs[PEAK])
    ga["routes"][0]["route_details"][0]["duration"] += 1
    ev = _evaluate(runner, wave, ga, arcs_doc, _fake_sp(wave, _ga_seqs(jobs[PEAK])))
    assert ev["row"]["ga_recertified"] is False
    assert any("GA re-certificate" in e for e in ev["errors"])


def test_gd_not_comparable_when_ga_has_more_routes(runner, campaign):
    """A (certified) GA that uses one more route than the exact optimum: dK = 1, gD not comparable, gD_free shown."""
    from uniride_core.exact import certification as cert

    arcs_doc, jobs = _archive()
    wid = "2026-10-05:pickup:765"
    wave = _wave(campaign, wid)
    seqs = _ga_seqs(jobs[wid])
    split = []
    for s in seqs:
        split.extend([(o,) for o in s[:1]] + ([s[1:]] if len(s) > 1 else []))
    ga = cert_ga_result(wave, split)
    ev = _evaluate(runner, wave, ga, arcs_doc, _fake_sp(wave, seqs, d_lb=1, d_lb_free=1))
    row = ev["row"]
    assert ev["errors"] == [], ev["errors"]
    assert row["K_GA"] == row["K_star"] + 1 and row["dK"] == 1
    assert row["gD"] is None and row["gD_note"] == "not_comparable_K_GA_gt_Kstar"
    assert row["gD_free"] == pytest.approx((row["D_GA"] - 1) / 1)
    assert cert.recompute_objective(wave, seqs)[0] == row["K_star"]


def cert_ga_result(wave, seqs):
    from uniride_core.exact import certification as cert

    payload = cert.response_payload(wave, seqs, algorithm_used="ga_split")
    return {"success": True, "routes": payload["routes"], "total_duration_minutes": payload["total_duration_minutes"]}


# ---------- HiGHS verification ----------
def test_highs_difference_in_proven_optimum_is_blocking(runner, campaign):
    import dataclasses

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    sp = _fake_sp(wave, _ga_seqs(jobs[PEAK]))
    same = dataclasses.replace(sp, solver="highs")
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, sp, highs=same)
    assert ev["row"]["highs_agrees"] is True and ev["errors"] == []
    other = dataclasses.replace(same, d=same.d + 1, stage2=dataclasses.replace(same.stage2, objective=same.d + 1))
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, sp, highs=other)
    assert ev["row"]["highs_agrees"] is False and any("HiGHS" in e for e in ev["errors"])
    # a HiGHS run that is not proven optimal is no disagreement and no agreement
    unproven = dataclasses.replace(same, status="feasible_with_gap")
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, sp, highs=unproven)
    assert ev["row"]["highs_agrees"] is None and ev["errors"] == []


# ---------- CSV and manifest schema ----------
def test_csv_has_one_row_per_wave_with_status_and_labels(runner, campaign, tmp_path):
    arcs_doc, jobs = _archive()
    rows = []
    for wid in (PEAK, "2026-10-05:pickup:765", "2026-10-05:dropoff:975"):
        wave = _wave(campaign, wid)
        rows.append(_evaluate(runner, wave, jobs[wid], arcs_doc, _fake_sp(wave, _ga_seqs(jobs[wid])))["row"])
    path = tmp_path / "wave_gaps.csv"
    runner.write_wave_csv(path, rows)
    got = list(csv.DictReader(path.open(encoding="utf-8")))
    assert list(got[0].keys()) == list(runner.WAVE_CSV_FIELDS)
    assert len(got) == 3 and [r["wave_id"] for r in got] == [PEAK, "2026-10-05:pickup:765", "2026-10-05:dropoff:975"]
    for r in got:
        assert r["status"] and r["fleet"] == "single_4sw5so"
        assert (r["ga_protocol"], r["ga_seed"], r["ga_commit"], r["ga_dirty_tree"]) == ("native", "42", "6be127d", "True")
    for needed in ("date", "R", "direction", "anchor", "students", "peak", "model", "columns", "K_GA", "K_LB", "K_star",
                   "D_GA", "D_LB", "D_star", "D_LB_free", "dK", "gD", "gD_free", "stage1_stop_reason",
                   "stage2_timing_dependent", "stage2_non_lexicographic", "solver", "solve_seconds"):
        assert needed in runner.WAVE_CSV_FIELDS


def test_ga_labels_are_read_from_the_source_manifest(runner):
    labels = runner.ga_labels(json.loads((SW5SO / "run_manifest.json").read_text(encoding="utf-8")))
    assert labels == GA_LABELS


def test_count_cap_wave_is_labelled_compact_and_not_dropped(runner, campaign):
    """A wave whose enumeration hit a count cap needs the compact model (WP-E5, not built): labelled, not solved."""
    from uniride_core.exact.ampl_backend import SPSolveResult

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    sp = SPSolveResult(wave.wave_id, "not_run", note="enumeration count_cap: compact model (WP-E5) required")
    ev = runner.evaluate_wave(wave, jobs[PEAK], arcs_doc, sp, ga_labels=GA_LABELS,
                              enum_info=dict(ENUM, model="compact", cap_fired="label_cap"))
    assert ev["row"]["status"] == "not_run" and ev["row"]["model"] == "compact"
    assert "WP-E5" in ev["row"]["note"] and ev["row"]["ga_recertified"] is True and ev["errors"] == []


# ---------- absence (section 2: exit code 3) ----------
def test_runner_exits_3_without_ampl_and_writes_nothing(tmp_path):
    out = tmp_path / "out"
    env = dict(os.environ, UNIRIDE_AMPL_DIR=str(tmp_path))  # a directory without an AMPL executable
    res = subprocess.run([sys.executable, str(SCRIPT), "--rides", "90", "--limit", "1", "--out", str(out)],
                         cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
    assert res.returncode == 3, res.stderr[-500:]
    assert "backend unavailable" in res.stderr.lower()
    assert not out.exists()
    assert str(tmp_path) not in res.stderr + res.stdout


def test_runner_reads_only_the_archive_and_imports_no_network_or_db():
    import ast

    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add((node.module or "").split(".")[0])
    assert not names & {"requests", "urllib", "http", "httpx", "socket", "sqlite3", "supabase", "psycopg2"}
    text = SCRIPT.read_text(encoding="utf-8")
    assert "tsplib.db" not in text
    for banned in ("C:\\\\Users", "yektakayman", "AMPL\\\\"):
        assert banned not in text


# ---------- AMPL-backed ----------
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


@pytest.mark.requires_ampl
def test_subset_run_writes_valid_manifest_and_csv(runner, tmp_path):
    protocol = runner.protocol  # uniride_core tests must not import academic_benchmark (architecture guard)

    _require("gurobi")
    _require("highs")
    ids = [PEAK, "2026-10-05:pickup:765", "2026-10-05:dropoff:975", "2026-10-06:pickup:525"]
    out = tmp_path / "out"
    rc = runner.main(["--rides", "50", "--wave-ids", ",".join(ids), "--out", str(out)])
    assert rc == 0
    manifest = json.loads((out / "exact_manifest.json").read_text(encoding="utf-8"))
    assert protocol.validate_manifest(manifest) == []
    assert protocol.private_data_errors(manifest) == []
    assert manifest["solver"]["name"] == "gurobi" and manifest["verification_solver"]["name"] == "highs"
    assert manifest["source_campaign"]["path"] == "docs/paper/results/week-2026-10-05-4sw5so"
    camp = runner.loader.load_campaign(SW5SO)
    ids = [w.wave_id for w in camp.waves_for(50) if w.wave_id in ids]  # campaign order
    assert len(ids) == 4 and [w["wave_id"] for w in manifest["waves"]] == ids
    assert sorted(manifest["matrix_sha256"]) == ["2026-10-05_R50", "2026-10-06_R50"]
    assert manifest["peak_waves"]["2026-10-05"]["wave_ids"] == [PEAK]
    rows = list(csv.DictReader((out / "wave_gaps.csv").open(encoding="utf-8")))
    assert [r["wave_id"] for r in rows] == ids
    for r in rows:
        assert r["status"] == "optimal" and r["exact_certified"] == "True" and r["ga_recertified"] == "True"
        assert r["highs_agrees"] == "True" and r["exact_le_ga"] == "True" and r["objective_check"] == "ok"
    by_id = {r["wave_id"]: r for r in rows}
    assert by_id[PEAK]["peak"] == "True" and by_id["2026-10-05:pickup:765"]["peak"] == "False"
    assert not manifest["blocking_errors"]
    # DUZELT round 1: HiGHS free stage, HiGHS stage rows, archived exact routes
    for r in rows:
        assert r["highs_free_agrees"] == "True" and r["highs_free_status"] == "optimal"
    for w in manifest["waves"]:
        assert [s["stage"] for s in w["highs_stages"]] == ["stage1", "stage2", "free"]
        assert all(protocol.validate_stage_row(s) == [] for s in w["highs_stages"])
    routes_file = out / manifest["exact_routes"]["file"]
    import hashlib

    assert hashlib.sha256(routes_file.read_bytes()).hexdigest() == manifest["exact_routes"]["sha256"]
    stored = json.loads(routes_file.read_text(encoding="utf-8"))
    assert protocol.private_data_errors(stored) == []
    assert [w["wave_id"] for w in stored["waves"]] == ids and manifest["exact_routes"]["waves"] == 4
    arcs50 = json.loads((SW5SO / "2026-10-05_R50_repeat1.matrix.json").read_text(encoding="utf-8"))
    arcs50_06 = json.loads((SW5SO / "2026-10-06_R50_repeat1.matrix.json").read_text(encoding="utf-8"))
    waves = {w.wave_id: w for w in camp.waves_for(50)}
    for entry in stored["waves"]:
        doc = arcs50 if entry["service_date"] == "2026-10-05" else arcs50_06
        assert entry["certified"] is True
        assert runner.recertify_stored_routes(waves[entry["wave_id"]], entry, doc)["is_feasible"] is True


@pytest.mark.requires_ampl
def test_determinism_five_waves_solved_twice_with_gurobi():
    """Design section 8 row 'Determinism': identical incumbents, bounds, columns and model choice."""
    from uniride_core.exact import ampl_backend as ab
    from uniride_core.exact.route_enumeration import enumerate_wave

    _require("gurobi")
    camp = _load_script().loader.load_campaign(SW5SO)
    waves = sorted(camp.waves_for(90), key=lambda w: (-w.legs, w.wave_id))[:5]
    assert len(waves) == 5

    def snapshot(session):
        out = []
        for w in waves:
            enum = enumerate_wave(w, camp.fleet_types)
            sp = ab.solve_wave(w, enum, peak=w.legs == 20, session=session)
            stages = [(s.status, s.objective, s.bound, s.bound_ceil, s.stop_reason)
                      for s in (sp.stage1, sp.stage2, sp.free) if s is not None]
            out.append((w.wave_id, enum.model, enum.column_count, enum.label_count, sp.status, sp.k, sp.d, sp.k_lb,
                        sp.d_lb, sp.d_lb_free, sp.selection, stages))
        return out

    with ab.AmplSession(ab.SolverSettings(solver="gurobi")) as session:
        first = snapshot(session)
    with ab.AmplSession(ab.SolverSettings(solver="gurobi")) as session:
        second = snapshot(session)
    assert first == second
    assert all(row[4] == "optimal" for row in first)


# ======================= DUZELT round 1 =======================
# ---------- item 1: R / T through the unmodified request builder ----------
def _types(note):
    """Violation types of an 'exact certificate failed: a,b' note, without the derived hard_violation marker."""
    assert note.startswith("exact certificate failed: "), note
    return set(note.split(": ", 1)[1].split(",")) - {"hard_violation"}


@pytest.mark.parametrize("wid", ["2026-10-05:pickup:765", "2026-10-05:dropoff:1035"])
def test_exact_routes_violating_only_the_ride_limit_are_rejected(runner, campaign, wid):
    """R = 90 GA routes fed as the exact side of the same wave at R = 50: only the ride limit is violated."""
    date = wid[:10]
    arcs50, jobs50 = _archive(date, 50)
    arcs90, jobs90 = _archive(date, 90)
    wave50, wave90 = _wave(campaign, wid, 50), _wave(campaign, wid, 90)
    seqs = _ga_seqs(jobs90[wid])
    assert _evaluate(runner, wave90, jobs90[wid], arcs90, _fake_sp(wave90, seqs))["row"]["status"] == "optimal"
    ev = _evaluate(runner, wave50, jobs50[wid], arcs50, _fake_sp(wave50, seqs))
    assert ev["row"]["status"] == "rejected" and ev["row"]["exact_certified"] is False
    assert _types(ev["row"]["note"]) == {"ride_time_violation"}                 # nothing else is violated
    assert any("exact certificate failed" in e and "ride_time_violation" in e for e in ev["errors"])


@pytest.mark.parametrize("wid", ["2026-10-05:pickup:765", "2026-10-05:dropoff:1035"])
def test_exact_routes_violating_only_the_tour_limit_are_rejected(runner, campaign, wid):
    import dataclasses

    date = wid[:10]
    arcs90, jobs90 = _archive(date, 90)
    wave = dataclasses.replace(_wave(campaign, wid, 90), max_tour_minutes=80)   # tours are 88 / 89, rides 57 / 79
    ev = _evaluate(runner, wave, jobs90[wid], arcs90, _fake_sp(wave, _ga_seqs(jobs90[wid])))
    assert ev["row"]["status"] == "rejected"
    assert _types(ev["row"]["note"]) == {"duration_violation"}


def test_type_spec_capacities_reach_the_certificate(runner, campaign):
    from uniride_core.exact import VehicleTypeSpec

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, "2026-10-05:pickup:765")
    sp = _fake_sp(wave, _ga_seqs(jobs[wave.wave_id]))
    ok = runner.evaluate_wave(wave, jobs[wave.wave_id], arcs_doc, sp, ga_labels=GA_LABELS, enum_info=ENUM,
                              type_spec=VehicleTypeSpec("large", 4, 5, 10))
    assert ok["row"]["status"] == "optimal"
    tight = runner.evaluate_wave(wave, jobs[wave.wave_id], arcs_doc, sp, ga_labels=GA_LABELS, enum_info=ENUM,
                                 type_spec=VehicleTypeSpec("large", 1, 1, 10))
    assert tight["row"]["status"] == "rejected" and tight["row"]["exact_certified"] is False


# ---------- item 2: dirty flag and output directory ----------
def _git_in(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=repo,
                          capture_output=True, text=True, check=True).stdout


@pytest.fixture()
def tiny_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "paper" / "results" / "x" / "run").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "code.py").write_text("a = 1\n", encoding="utf-8")
    (repo / "docs" / "paper" / "results" / "x" / "run" / "out.txt").write_text("1\n", encoding="utf-8")
    _git_in(repo, "init", "-q")
    _git_in(repo, "add", "-A")
    _git_in(repo, "commit", "-q", "-m", "init")
    return repo


def test_git_state_dirty_flag_and_output_exclusion(runner, tiny_repo):
    out = tiny_repo / "docs" / "paper" / "results" / "x" / "run"
    commit, dirty = runner._git_state(out, repo=tiny_repo)
    assert len(commit) == 40 and dirty is False
    (out / "out.txt").write_text("2\n", encoding="utf-8")                       # tracked change INSIDE out: ignored
    assert runner._git_state(out, repo=tiny_repo)[1] is False
    (tiny_repo / "src" / "code.py").write_text("a = 2\n", encoding="utf-8")     # tracked change OUTSIDE out
    assert runner._git_state(out, repo=tiny_repo)[1] is True
    _git_in(tiny_repo, "checkout", "--", "src/code.py")
    (tiny_repo / "src" / "new.py").write_text("b = 1\n", encoding="utf-8")      # untracked file outside out
    assert runner._git_state(out, repo=tiny_repo)[1] is True


def test_out_directory_rule(runner, tiny_repo, tmp_path):
    results = tiny_repo / "docs" / "paper" / "results"
    src = results / "src_campaign"
    src.mkdir()
    assert runner.check_out_dir(results / "x" / "run", src, repo=tiny_repo) == ""
    assert runner.check_out_dir(tmp_path / "elsewhere", src, repo=tiny_repo) == ""      # outside the repository
    for bad in (tiny_repo, tiny_repo / "docs", results, tiny_repo / "src", tiny_repo / "docs" / "other", src,
                src / "child"):
        assert runner.check_out_dir(bad, src, repo=tiny_repo), bad
    assert runner.check_out_dir(results / "x", results / "x" / "s", repo=tiny_repo)    # contains the source


def test_runner_refuses_an_unsafe_out_directory_before_anything_else(tmp_path):
    # an AMPL directory without an executable: a runner that did not refuse would exit 3, never run a campaign
    env = dict(os.environ, UNIRIDE_AMPL_DIR=str(tmp_path))
    for bad in (str(REPO), str(REPO / "docs"), str(REPO / "docs" / "paper" / "results"), "."):
        res = subprocess.run([sys.executable, str(SCRIPT), "--out", bad], cwd=REPO, env=env, capture_output=True,
                             text=True, timeout=300)
        assert res.returncode == 2 and "refused" in res.stderr, (bad, res.stderr[-300:])


# ---------- items 3 and 5: HiGHS free stage, non-proven results, stage rows ----------
def _highs_pair(campaign):
    import dataclasses

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    sp = _fake_sp(wave, _ga_seqs(jobs[PEAK]))
    return wave, jobs, arcs_doc, sp, dataclasses.replace(sp, solver="highs")


def _ev_highs(runner, wave, jobs, arcs_doc, sp, h):
    return runner.evaluate_wave(wave, jobs[PEAK], arcs_doc, sp, ga_labels=GA_LABELS, enum_info=ENUM, highs=h)


def test_highs_free_stage_is_compared_and_a_difference_is_blocking(runner, campaign):
    import dataclasses

    wave, jobs, arcs_doc, sp, same = _highs_pair(campaign)
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, same)
    assert ev["errors"] == [] and ev["row"]["highs_free_agrees"] is True and ev["row"]["highs_free_status"] == "optimal"
    assert ev["row"]["highs_D_LB_free"] == sp.d_lb_free
    assert [s["stage"] for s in ev["highs_stages"]] == ["stage1", "stage2", "free"]
    off = dataclasses.replace(same, free=dataclasses.replace(same.free, objective=same.free.objective + 1,
                                                             bound=same.free.bound + 1, bound_ceil=same.free.bound_ceil + 1),
                              d_lb_free=same.d_lb_free + 1)
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, off)
    assert ev["row"]["highs_free_agrees"] is False and any("free-stage" in e for e in ev["errors"])
    # a free stage that HiGHS did not prove is neither agreement nor error
    unproven = dataclasses.replace(same, free=dataclasses.replace(same.free, status="feasible_with_gap",
                                                                  stop_reason="wall_limit", timing_dependent=True))
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, unproven)
    assert ev["row"]["highs_free_agrees"] is None and ev["errors"] == []


def test_highs_incumbent_better_or_bound_above_the_proven_optimum_is_blocking(runner, campaign):
    import dataclasses

    wave, jobs, arcs_doc, sp, same = _highs_pair(campaign)
    s2 = dataclasses.replace(same.stage2, status="feasible_with_gap", stop_reason="wall_limit", timing_dependent=True,
                             objective=sp.d - 1)
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, dataclasses.replace(same, status="feasible_with_gap", stage2=s2))
    assert any("incumbent" in e and "below" in e for e in ev["errors"]), ev["errors"]
    s1 = dataclasses.replace(same.stage1, status="feasible_with_gap", stop_reason="wall_limit", timing_dependent=True,
                             bound_ceil=sp.k + 1)
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, dataclasses.replace(same, status="feasible_with_gap", stage1=s1))
    assert any("bound" in e and "above" in e for e in ev["errors"]), ev["errors"]
    s2 = dataclasses.replace(same.stage2, status="bound_only", stop_reason="wall_limit", timing_dependent=True,
                             objective=None, bound_ceil=sp.d + 1)
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, dataclasses.replace(same, status="bound_only", stage2=s2))
    assert any("stage-2 bound" in e for e in ev["errors"]), ev["errors"]
    fr = dataclasses.replace(same.free, status="feasible_with_gap", stop_reason="wall_limit", timing_dependent=True,
                             objective=sp.free.objective - 1)
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, dataclasses.replace(same, free=fr))
    assert any("free-stage incumbent" in e for e in ev["errors"]), ev["errors"]


def test_highs_rejected_is_a_blocking_error(runner, campaign):
    import dataclasses

    wave, jobs, arcs_doc, sp, same = _highs_pair(campaign)
    rej = dataclasses.replace(same, status="rejected", note="stage 2 infeasible after a stage-1 incumbent")
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, rej)
    assert any("HiGHS result rejected" in e for e in ev["errors"])


def test_highs_stage_rows_follow_the_stage_row_schema(runner, campaign):
    import dataclasses

    wave, jobs, arcs_doc, sp, same = _highs_pair(campaign)
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, same)
    for row in ev["highs_stages"]:
        assert runner.protocol.validate_stage_row(row) == []
        assert {"status", "stop_reason", "timing_dependent", "wall_seconds", "bound", "objective"} <= set(row)
    bad = dataclasses.replace(same, stage1=dataclasses.replace(same.stage1, stop_reason="wall_limit", timing_dependent=False))
    ev = _ev_highs(runner, wave, jobs, arcs_doc, sp, bad)                       # a schema-invalid stage row is surfaced
    assert any("HiGHS stage row" in e for e in ev["errors"])


# ---------- item 4: archived exact routes re-certify without a solver ----------
def test_stored_exact_routes_recertify_through_the_bridge(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    ev = _evaluate(runner, wave, jobs[PEAK], arcs_doc, _fake_sp(wave, _ga_seqs(jobs[PEAK])))
    stored = json.loads(json.dumps(ev["exact_routes"]))                        # as written to exact_routes.json
    assert stored["wave_id"] == PEAK and stored["certified"] is True and stored["status"] == "optimal"
    assert {"type_id", "occurrence_ids", "cost", "ride", "tour", "column_index", "copy"} <= set(stored["routes"][0])
    assert runner.recertify_stored_routes(wave, stored, arcs_doc)["is_feasible"] is True
    assert runner.protocol.private_data_errors(stored) == []
    tampered = json.loads(json.dumps(stored))
    first, second = tampered["routes"][0]["occurrence_ids"], tampered["routes"][1]["occurrence_ids"]
    tampered["routes"][0]["occurrence_ids"] = first + second                    # two routes merged: capacity violated
    del tampered["routes"][1]
    assert runner.recertify_stored_routes(wave, tampered, arcs_doc)["is_feasible"] is False


# ---------- items 6 and 7: GA duration errors, stage 1 not proven ----------
def test_unrecomputable_ga_duration_is_a_blocking_error(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    ga = deepcopy(jobs[PEAK])
    ga["routes"][0]["student_ids"][0] = "2026-10-05:pickup:Unknown~1"
    ev = _evaluate(runner, wave, ga, arcs_doc, _fake_sp(wave, _ga_seqs(jobs[PEAK])))
    assert ev["row"]["D_GA"] is None
    assert any("GA duration could not be recomputed" in e for e in ev["errors"])


def test_archived_ga_total_differing_from_the_matrix_recomputation_is_blocking(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    ga = deepcopy(jobs[PEAK])
    ga["total_duration_minutes"] += 5
    ev = _evaluate(runner, wave, ga, arcs_doc, _fake_sp(wave, _ga_seqs(jobs[PEAK])))
    assert any("archived GA total" in e for e in ev["errors"])


def test_stage1_not_proven_gives_no_gd_and_no_d_lb(runner, campaign):
    arcs_doc, jobs = _archive()
    wave = _wave(campaign, PEAK)
    sp = _fake_sp(wave, _ga_seqs(jobs[PEAK]), status="feasible_with_gap", k_star_proven=False)
    assert sp.d_lb is not None                                                  # a bound that must not be used
    row = _evaluate(runner, wave, jobs[PEAK], arcs_doc, sp)["row"]
    assert row["gD_note"] == "unavailable_stage1_not_proven" and row["gD"] is None
    assert row["D_LB"] is None and row["exact_le_ga"] is None
