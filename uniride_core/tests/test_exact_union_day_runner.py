"""WP-E4b runner: union menu from the archives, GA-menu recomputation, TS confirmation, labels, manifest and CSV schema.

CP-SAT and the TypeScript CLI only (no AMPL, no DB, no HTTP). The tests that call the CLI are skipped, with a reason,
when node or tsx is not installed.
"""
from __future__ import annotations

import copy
import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
for _p in (REPO / "optimizer_api", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from uniride_core.planning import fleet_selection_request as fsr  # noqa: E402
from uniride_core.planning import union_day_menu as udm  # noqa: E402


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ud = _load("run_exact_union_day")
tm = ud.tm

HAS_NODE = bool(shutil.which("node")) and (REPO / "node_modules" / "tsx" / "package.json").is_file()
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node or node_modules/tsx is not installed (TS confirmation CLI)")

DATE = "2026-10-05"
RIDE = 50


@pytest.fixture(scope="module")
def e4a():
    return ud.load_e4a(ud.E4A_DIR)


@pytest.fixture(scope="module")
def ctxs():
    return {n: tm.load_fleet_context(tm.SOURCES[n]) for n in tm.SOURCES}


@pytest.fixture(scope="module")
def day_large_sedan(ctxs, e4a):
    return ud.prepare_day(ctxs["large+sedan"], RIDE, DATE, e4a)


# ---------------------------------------------------------------- menu from the archives
def test_infeasible_or_uncertified_exact_options_are_not_menu_entries():
    good = {"certified": True, "routes": [{"x": 1}], "status": "optimal"}
    assert ud.is_menu_entry(good)
    assert not ud.is_menu_entry(dict(good, status="infeasible_proven", routes=[]))
    assert not ud.is_menu_entry(dict(good, routes=[]))
    assert not ud.is_menu_entry(dict(good, certified=False))
    assert not ud.is_menu_entry(dict(good, status="rejected"))


def test_exact_option_ids_and_order_follow_xbase_then_xq(day_large_sedan):
    order = {"xbase": -1, **{f"xq{q}": q for q in range(0, 5)}}
    for wave_id, options in day_large_sedan["exact_info"]["menus"].items():
        ids = [o.option_id for o in options]
        assert ids == sorted(ids, key=order.__getitem__), wave_id
        assert all(o.origin == "exact" and o.baseline is False for o in options)


def test_the_union_menu_is_the_ga_menu_then_the_deduped_exact_options_and_every_ga_option_is_kept(day_large_sedan):
    ga, union = day_large_sedan["ga_waves"], day_large_sedan["union_waves"]
    for g, u in zip(ga, union):
        assert g.wave_id == u.wave_id
        assert u.options[: len(g.options)] == g.options  # GA options unchanged and first
        added = u.options[len(g.options):]
        assert all(o.option_id.startswith("x") for o in added)
        assert len({udm.exact_identity(o) for o in added}) == len(added)  # no identical exact routes left
    dropped = day_large_sedan["exact_info"]["dedupe_log"]
    assert dropped, "the example day has exact options that repeat an earlier exact option"
    assert sum(len(u.options) - len(g.options) for g, u in zip(ga, union)) == sum(
        len(v) for v in day_large_sedan["exact_info"]["menus"].values()) - len(dropped)


def test_an_exact_option_with_the_same_partition_as_a_ga_option_is_kept(day_large_sedan):
    """xbase of a wave usually has the GA ``base`` partition; it must still be in the union menu."""
    kept_same_partition = 0
    for g, u in zip(day_large_sedan["ga_waves"], day_large_sedan["union_waves"]):
        ga_sets = {frozenset(frozenset(s) for s in o.stops) for o in g.options}
        for o in u.options[len(g.options):]:
            if frozenset(frozenset(s) for s in o.stops) in ga_sets:
                kept_same_partition += 1
    assert kept_same_partition > 0


def test_the_menu_does_not_depend_on_L_and_the_ga_part_equals_every_archived_request(ctxs, day_large_sedan):
    """L semantics: one GA menu and one exact menu per (date, R), shared by all L; only ``max_large`` differs."""
    ctx = ctxs["large+sedan"]
    seen = []
    for limit in ctx.replay_fleet.l_values:
        archived = ud.load_archived_exchange(ctx, DATE, RIDE, limit)["request"]
        ids = [[o["option_id"] for o in w["options"]] for w in archived["waves"]]
        seen.append(ids)
        assert archived["max_large"] == limit
    assert all(s == seen[0] for s in seen)  # the archived requests offer every included GA option at every L
    assert [[o.option_id for o in w.options] for w in day_large_sedan["ga_waves"]] == seen[0]


def test_exact_waves_unknown_to_the_campaign_are_rejected(ctxs, e4a):
    bad = copy.deepcopy(e4a)
    doc = next(d for d in bad["routes_doc"]["waves"] if d["fleet"] == "large+sedan" and d["R"] == RIDE and d["service_date"] == DATE)
    doc["wave_id"] = "2026-10-05:pickup:999"
    with pytest.raises(Exception, match="unknown wave"):
        ud.exact_menus(ctxs["large+sedan"], RIDE, DATE, bad)


def test_day_option_sums_define_dK_day_gD_day_and_the_excluded_options():
    def r(kind, comparison, dk, gd, d_ga, d_lb):
        return {"fleet": "f", "date": "d", "R": "50", "kind": kind, "comparison": comparison, "dK": dk, "gD": gd, "D_GA": d_ga, "D_LB": d_lb}

    rows = [r("base", "compared", "0", "0.1", "110", "100"), r("base", "compared", "1", "", "50", "40"),
            r("base", "compared", "0", "0.0", "200", "200"), r("base", "both_infeasible", "", "", "", ""),
            r("q", "compared", "1", "", "10", "9"), r("q", "ga_infeasible_exact_feasible", "", "", "", "")]
    sums = ud.day_option_sums(rows, "f", "d", 50)
    assert sums["base"] == {"compared": 3, "dK_day": 1, "gD_day": round((310 - 300) / 300, 6), "gD_excluded": 1, "not_compared": 1}
    assert sums["q"] == {"compared": 1, "dK_day": 1, "gD_day": None, "gD_excluded": 1, "not_compared": 1}


def test_day_sums_of_the_real_e4a_rows_match_option_counts(e4a):
    total = sum(1 for r in e4a["option_gaps_rows"] if r["fleet"] == "large+sedan" and r["date"] == DATE and int(r["R"]) == RIDE)
    sums = ud.day_option_sums(e4a["option_gaps_rows"], "large+sedan", DATE, RIDE)
    assert sum(s["compared"] + s["not_compared"] for s in sums.values()) == total


# ---------------------------------------------------------------- TS CLI interval parity for exact options
@needs_node
@pytest.mark.parametrize("fleet,date,ride", [(f, d, r) for f in sorted(tm.SOURCES) for d, r in (("2026-10-05", 50), ("2026-10-07", 90))])
def test_exact_option_intervals_equal_the_typescript_intervals(fleet, date, ride, ctxs, e4a):
    """Every exact option of one day (pickup and dropoff waves): the TS CLI rebuilds the same intervals and flags."""
    ctx = ctxs[fleet]
    day = ud.prepare_day(ctx, ride, date, e4a)
    request = fsr.build_selection_request(
        udm.request_waves(day["union_waves"]), fixed_type=ctx.replay_fleet.fixed, minimise_type=ctx.replay_fleet.minimise, max_large=50,
        ride_default=day["menu_doc"]["limits"]["maxRideTimeMinutes"], tour_default=day["menu_doc"]["limits"]["maxTourMinutes"],
        cooldown_large_minutes=replay_cooldown(ctx, ctx.replay_fleet.fixed), cooldown_car_minutes=replay_cooldown(ctx, ctx.replay_fleet.minimise),
        max_cars=ctx.replay_fleet.max_cars)
    cases = []
    for wave_req, wave in zip(request["waves"], day["union_waves"]):
        for option in wave.options:
            if option.origin != "exact":
                continue
            body = next(o for o in wave_req["options"] if o["option_id"] == option.option_id)
            routes = [dict(data, label="large" if r["large_ok"] else "car", python={k: r[k] for k in ("start", "end", "minutes", "large_ok", "car_ok")})
                      for data, r in zip(option.route_data, body["routes"])]
            cases.append({"caseId": f"{wave.wave_id}|{option.option_id}", "timeScale": 100, "fixedType": ud.type_json(ctx.fixed),
                          "minimiseType": ud.type_json(ctx.minimise),
                          "limits": {"maxRideTimeMinutes": day["menu_doc"]["limits"]["maxRideTimeMinutes"],
                                     "maxTourMinutes": day["menu_doc"]["limits"]["maxTourMinutes"]},
                          "maxLarge": 50, "pythonCooldowns": {"large": request["cooldown_large"], "car": request["cooldown_car"]},
                          "waves": [{"waveId": wave.wave_id, "direction": wave.direction, "anchorMinutes": wave.anchor_minutes, "routes": routes}]})
    assert len(cases) > 10 and {w.direction for w in day["union_waves"]} == {"pickup", "dropoff"}
    results, error = ud.run_cli(cases)
    assert results is not None, error
    bad = {k: v["intervalDifferences"][:2] for k, v in results.items() if v["intervalDifferences"]}
    assert bad == {}
    assert [k for k, v in results.items() if v["problems"] or v["recheck"]["failures"]] == []


def replay_cooldown(ctx, type_):
    return tm.replay._cooldown(ctx.replay_fleet, type_)


# ---------------------------------------------------------------- one cell: recomputation, labels, caps
def run_cell(ctx, day, e4a, limit, *, cli, solve=fsr.solve_request, to_body=fsr.result_body, ride=RIDE):
    fleet = ctx.replay_fleet
    return ud.solve_cell_row(
        ctx, DATE, ride, limit, ga_waves=day["ga_waves"], union_waves=day["union_waves"], exact_info=day["exact_info"],
        archived=ud.load_archived_exchange(ctx, DATE, ride, limit), menu_limits=day["menu_doc"]["limits"], caps=ud.router_caps(),
        producer_limit_s=fleet.selection_time_limit, solve=solve, to_body=to_body, clock=__import__("time").perf_counter,
        cli=cli, cpsat={"version": fleet.solver["version"], "seed": fleet.solver["random_seed"], "workers": fleet.solver["num_workers"]},
        e4a_replay_row=e4a["replay_rows"].get((ctx.replay_fleet.name, DATE, ride, limit)))


def test_the_ga_menu_recomputation_equals_the_archived_response_in_every_cell_of_the_day(ctxs, e4a):
    for name, ctx in ctxs.items():
        day = ud.prepare_day(ctx, RIDE, DATE, e4a)
        for limit in ctx.replay_fleet.l_values:
            row, errors, _ = run_cell(ctx, day, e4a, limit, cli=lambda cases: (None, "no cli"))
            assert errors == [], (name, limit, errors)
            assert row["ga_equals_archived_response"] is True and row["ga_status"] == row["ga_archived_status"]


def test_the_recomputation_is_also_checked_against_the_e4a_replay_rows(ctxs, e4a, day_large_sedan):
    ctx = ctxs["large+sedan"]
    assert e4a["replay_rows"][(ctx.replay_fleet.name, DATE, RIDE, 3)]["replay_status"] == "optimal"
    forged = dict(e4a["replay_rows"][(ctx.replay_fleet.name, DATE, RIDE, 3)], replay_status="feasible")
    fleet = ctx.replay_fleet
    _, errors, _ = ud.solve_cell_row(
        ctx, DATE, RIDE, 3, ga_waves=day_large_sedan["ga_waves"], union_waves=day_large_sedan["union_waves"], exact_info=day_large_sedan["exact_info"],
        archived=ud.load_archived_exchange(ctx, DATE, RIDE, 3), menu_limits=day_large_sedan["menu_doc"]["limits"], caps=ud.router_caps(),
        producer_limit_s=fleet.selection_time_limit, solve=fsr.solve_request, to_body=fsr.result_body,
        clock=__import__("time").perf_counter, cli=lambda cases: (None, "no cli"),
        cpsat={"version": fleet.solver["version"], "seed": fleet.solver["random_seed"], "workers": fleet.solver["num_workers"]}, e4a_replay_row=forged)
    assert any("differs from the WP-E4a replay" in e for e in errors)


def test_a_changed_ga_selection_is_a_blocking_recompute_mismatch(ctxs, e4a, day_large_sedan):
    ctx = ctxs["large+sedan"]
    real = {}

    def tampered(request, *, time_limit_s):
        res = fsr.solve_request(request, time_limit_s=time_limit_s)
        real.setdefault("n", 0)
        real["n"] += 1
        if real["n"] == 1:  # the GA-menu call
            res = type(res)(**{**res.__dict__, "cars": (res.cars or 0) + 1})
        return res

    _, errors, _ = run_cell(ctx, day_large_sedan, e4a, 3, cli=lambda cases: (None, "no cli"), solve=tampered)
    assert any("differs from the archived WP-E10 response" in e for e in errors)


def test_a_missing_cli_check_gives_not_independently_confirmed(ctxs, e4a, day_large_sedan):
    row, errors, info = run_cell(ctxs["large+sedan"], day_large_sedan, e4a, 3, cli=lambda cases: (None, "node not found"))
    assert row["label"] == udm.LABEL_NOT_CONFIRMED and row["claim"] == ""
    assert row["ga_confirmation"] == udm.CONFIRM_MISSING and row["union_confirmation"] == udm.CONFIRM_MISSING
    assert "node not found" in row["union_confirmation_detail"] and errors == []


def _cli_answering(ok, ts_cars=None):
    def cli(cases):
        out = {}
        for c in cases:
            out[c["caseId"]] = {"caseId": c["caseId"], "ok": ok, "assignment": {"status": "proven" if ok else "infeasible_for_L", "cars": ts_cars,
                                "countsByType": {}, "reasonCodes": [], "nodes": 0},
                                "problems": [] if ok else ["x"], "recheck": {"routesChecked": 0, "failures": []},
                                "intervalDifferences": [] if ok else [{"field": "start"}]}
        return out, ""

    return cli


def test_a_failed_cli_check_gives_verification_failed(ctxs, e4a, day_large_sedan):
    row, _, _ = run_cell(ctxs["large+sedan"], day_large_sedan, e4a, 3, cli=_cli_answering(False))
    assert row["label"] == udm.LABEL_FAILED and row["claim"] == ""
    assert row["ga_confirmation"] == udm.CONFIRM_FAILED and row["union_confirmation"] == udm.CONFIRM_FAILED


@needs_node
def test_with_the_real_cli_the_ga_and_union_selections_are_confirmed_and_the_row_is_proven(ctxs, e4a, day_large_sedan):
    row, errors, info = run_cell(ctxs["large+sedan"], day_large_sedan, e4a, 3, cli=ud.run_cli)
    assert errors == [] and info["cli_calls"] == 1
    assert (row["ga_confirmation"], row["union_confirmation"]) == (udm.CONFIRMED, udm.CONFIRMED)
    assert row["ga_ts_cars"] == row["ga_cars"] and row["union_ts_cars"] == row["union_cars"]
    assert row["label"] == udm.LABEL_PROVEN and row["claim"] == udm.CLAIM
    assert int(row["union_cars"]) <= int(row["ga_cars"]) and row["cars_difference_union_minus_ga"] == int(row["union_cars"]) - int(row["ga_cars"])


def test_a_union_run_on_its_time_limit_is_rerun_once_at_60_s_and_labelled_union_not_proven(ctxs, e4a, day_large_sedan):
    calls = []

    def limited(request, *, time_limit_s):
        calls.append(time_limit_s)
        res = fsr.solve_request(request, time_limit_s=time_limit_s)
        if len(calls) >= 2:  # both union calls stop on their time limit
            res = type(res)(**{**res.__dict__, "status": "feasible"})
        return res

    row, errors, info = run_cell(ctxs["large+sedan"], day_large_sedan, e4a, 3, cli=_cli_answering(True), solve=limited)
    assert calls == [30, 30, 60]
    assert row["union_rerun"] is True and row["union_time_limit_s"] == 60 and row["union_first_status"] == "feasible"
    assert row["label"] == udm.LABEL_NOT_PROVEN and row["timing_dependent"] is True and row["claim"] == "" and row["cars_difference_union_minus_ga"] == ""
    assert "60" in row["not_proven_reason"]


def test_router_caps_exceeded_by_the_union_request_are_flagged_per_cap(ctxs, e4a):
    caps = ud.router_caps()
    assert caps == {"max_options_per_wave": 6, "max_routes_per_option": 40, "max_total_routes": 1000}
    for name, ctx in ctxs.items():
        day = ud.prepare_day(ctx, RIDE, DATE, e4a)
        for limit in ctx.replay_fleet.l_values[:1]:
            row, _, _ = run_cell(ctx, day, e4a, limit, cli=lambda cases: (None, "no cli"))
            flags = udm.router_cap_flags(fsr.build_selection_request(
                udm.request_waves(day["union_waves"]), fixed_type=ctx.replay_fleet.fixed, minimise_type=ctx.replay_fleet.minimise, max_large=limit,
                ride_default=90, tour_default=120), **caps)
            assert row["union_cap_options_per_wave"] == flags["cap_options_per_wave"]
            assert row["union_max_options_per_wave"] == max(len(w.options) for w in day["union_waves"])
            assert row["ga_cap_options_per_wave"] is False  # the GA menus passed the router in WP-E10
            assert row["union_cap_options_per_wave"] == (row["union_max_options_per_wave"] > caps["max_options_per_wave"])


def test_the_output_directory_rule(tmp_path):
    srcs = [tm.SOURCES["large+sedan"]]
    assert ud.check_out(ud.DEFAULT_OUT, ud.E4A_DIR, srcs) == ""
    assert "strictly below" in ud.check_out(REPO, ud.E4A_DIR, srcs)
    assert "strictly below" in ud.check_out(RESULTS, ud.E4A_DIR, srcs)
    assert "strictly below" in ud.check_out(REPO / "scripts", ud.E4A_DIR, srcs)
    assert ud.check_out(ud.E4A_DIR, ud.E4A_DIR, srcs) != ""
    assert ud.check_out(ud.E4A_DIR / "sub", ud.E4A_DIR, srcs) != ""
    assert ud.check_out(tm.SOURCES["large+sedan"], ud.E4A_DIR, srcs) != ""
    assert ud.check_out(tmp_path / "out", ud.E4A_DIR, srcs) == ""


# ---------------------------------------------------------------- campaign slice: manifest and CSV schema
@pytest.fixture(scope="module")
def slice_out(tmp_path_factory):
    out = tmp_path_factory.mktemp("union_day")
    code = ud.main(["--rides", str(RIDE), "--dates", DATE, "--out", str(out)])
    return out, code


@needs_node
def test_slice_run_writes_manifest_csv_and_summary_without_blocking_errors(slice_out):
    out, code = slice_out
    manifest = json.loads((out / ud.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert code == 0 and manifest["blocking_errors"] == []
    assert ud.validate_manifest(manifest) == []
    assert (out / "day_gaps.csv").is_file() and (out / "summary.json").is_file()
    for name in (ud.MANIFEST_FILENAME, "day_gaps.csv", "summary.json"):
        assert b"\r" not in (out / name).read_bytes(), name  # LF writes


@needs_node
def test_slice_manifest_records_commit_provenance_versions_run_history_and_limits(slice_out):
    out, _ = slice_out
    m = json.loads((out / ud.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert len(m["git_commit"]) == 40 and isinstance(m["dirty_working_tree"], bool)
    assert m["python_provenance"] == {"uniride_core": "uniride_core/__init__.py", "optimizer_api": "optimizer_api/__init__.py",
                                      "academic_benchmark": "academic_benchmark/__init__.py"}
    assert m["cpsat"]["version"] == "9.15.6755" and m["cpsat"]["random_seed"] == 20261008 and m["cpsat"]["num_workers"] == 1
    assert m["cpsat"]["producer_time_limit_seconds"] == {"large+sedan": 30, "large+doblo_cap3": 30} and m["cpsat"]["rerun_time_limit_seconds"] == 60
    assert m["tools"]["node"].startswith("v") and m["tools"]["tsx"] and "--conditions=react-server --import tsx" in m["tools"]["cli_command"]
    assert m["time_scale"] == 100 and m["router_caps"] == {"max_options_per_wave": 6, "max_routes_per_option": 40, "max_total_routes": 1000}
    rh = m["run_history"]
    assert rh["invocations"][0]["serial"] is True and rh["cells_planned"] == rh["cells_solved"] == len(rh["cells"]) == 6
    assert rh["cli_errors"] == 0 and rh["union_reruns"] == 0
    assert m["ga_recompute"] == {"cells": 6, "equal_to_archived_response": 6}
    assert m["claim"] == udm.CLAIM
    assert m["source_campaigns"]["large+sedan"]["manifest_sha256"] and m["exact_options_source"]["exact_routes_sha256"]


@needs_node
def test_slice_csv_schema_has_no_min_of_ga_and_union_and_claims_only_proven_rows(slice_out):
    out, _ = slice_out
    with (out / "day_gaps.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header, rows = list(reader.fieldnames), list(reader)
    assert tuple(header) == ud.CSV_FIELDS and len(rows) == 6
    forbidden = [h for h in header if "min(" in h.lower() or h.lower() in ("min_cars", "best_cars", "cars_min", "cars_best", "min_ga_union")]
    assert forbidden == []
    for key in ("ga_status", "union_status", "ga_time_limit_s", "union_time_limit_s", "label", "ga_large_peak",
                "ga_car_minutes", "ga_total_minutes", "union_large_peak", "union_car_minutes", "union_total_minutes", "union_cap_options_per_wave", "union_cap_routes_per_option", "union_cap_total_routes"):
        assert key in header
    for r in rows:
        assert r["label"] in udm.LABELS
        assert r["claim"] == {udm.LABEL_PROVEN: udm.CLAIM, udm.LABEL_GA_INFEASIBLE: udm.CLAIM_UNION_ONLY}.get(r["label"], "")
        assert r["ga_equals_archived_response"] == "True" and r["ga_ts_cars"] in ("", r["ga_cars"])
        if r["label"] == udm.LABEL_PROVEN:
            assert int(r["union_cars"]) <= int(r["ga_cars"])
        else:
            assert r["cars_difference_union_minus_ga"] == ""


# ---------------------------------------------------------------- an endpoint off the centi-minute grid refuses the cell
def _off_grid(day):
    """The union menu with one exact route whose start is 0.005 minutes off the 1/100-minute grid."""
    union = []
    for w in day["union_waves"]:
        options = []
        for o in w.options:
            if o.option_id == "xbase" and not union:
                bad = fsr.RouteFacts(o.routes[0].start_minutes + 0.005, o.routes[0].end_minutes, o.routes[0].step_durations,
                                     o.routes[0].direction, o.routes[0].sw_count, o.routes[0].so_count)
                o = udm.MenuOption(o.option_id, o.baseline, (bad,) + o.routes[1:], o.origin, o.stops, o.route_data)
            options.append(o)
        union.append(udm.WaveMenu(w.wave_id, w.direction, w.anchor_minutes, tuple(options)))
    return dict(day, union_waves=union)


def test_an_exact_endpoint_off_the_centi_minute_grid_is_refused_never_rounded(ctxs, e4a, day_large_sedan):
    with pytest.raises(fsr.SelectionIntervalPrecision):
        run_cell(ctxs["large+sedan"], _off_grid(day_large_sedan), e4a, 3, cli=lambda cases: (None, "no cli"))


def test_the_runner_reports_a_refused_cell_as_a_blocking_error(monkeypatch, tmp_path, ctxs, e4a):
    original = ud.prepare_day
    monkeypatch.setattr(ud, "prepare_day", lambda *a, **k: _off_grid(original(*a, **k)))
    code = ud.main(["--fleets", "large+sedan", "--rides", str(RIDE), "--dates", DATE, "--limits", "3", "--out", str(tmp_path / "o")])
    manifest = json.loads((tmp_path / "o" / ud.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert code == 1 and any("SELECTION_INTERVAL_PRECISION" in e for e in manifest["blocking_errors"])


# ---------------------------------------------------------------- the committed campaign
def test_committed_campaign_results_are_consistent():
    out = ud.DEFAULT_OUT
    manifest = json.loads((out / ud.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    with (out / "day_gaps.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 120 and tuple(rows[0].keys()) == ud.CSV_FIELDS
    assert manifest["dirty_working_tree"] is False and len(manifest["git_commit"]) == 40 and manifest["blocking_errors"] == []
    assert ud.validate_manifest(manifest) == []
    counts = {k: sum(r["label"] == k for r in rows) for k in udm.LABELS}
    assert counts == manifest["labels"] == summary["labels"] and sum(counts.values()) == 120
    assert manifest["ga_recompute"] == {"cells": 120, "equal_to_archived_response": 120}
    assert all(r["ga_equals_archived_response"] == "True" for r in rows)
    for r in rows:
        proven = r["label"] == udm.LABEL_PROVEN
        assert r["claim"] == {udm.LABEL_PROVEN: udm.CLAIM, udm.LABEL_GA_INFEASIBLE: udm.CLAIM_UNION_ONLY}.get(r["label"], "")
        if proven:
            assert r["ga_status"] == r["union_status"] == "optimal" and int(r["union_cars"]) <= int(r["ga_cars"])
            assert (r["ga_confirmation"], r["union_confirmation"]) == (udm.CONFIRMED, udm.CONFIRMED)
        else:
            assert r["cars_difference_union_minus_ga"] == "" and r["not_proven_reason"]
        if r["union_rerun"] == "True":
            assert r["union_time_limit_s"] == "60.0" and r["union_first_status"] in udm.TIME_LIMITED_STATUSES
    assert counts[udm.LABEL_BOTH_INFEASIBLE] == 28 and counts[udm.LABEL_GA_INFEASIBLE] == 1 and counts[udm.LABEL_NOT_PROVEN] == 0
    ga_inf = next(r for r in rows if r["label"] == udm.LABEL_GA_INFEASIBLE)
    assert (ga_inf["fleet"], ga_inf["date"], ga_inf["R"], ga_inf["L"], ga_inf["union_cars"], ga_inf["cars_difference_union_minus_ga"]) == (
        "large+sedan", "2026-10-05", "60", "2", "3", "")
    with (out / "day_sums.csv").open(encoding="utf-8", newline="") as fh:
        assert len(list(csv.DictReader(fh))) == 40
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert udm.CLAIM in readme and "min(GA, union)" in readme
    assert f"`{manifest['git_commit'][:12]}`" in readme
    assert not [h for h in rows[0] if "min(" in h.lower() or h.lower() in ("min_cars", "best_cars")]


# ---------------------------------------------------------------- owner decision 2026-10-18: labels on real cells
def test_a_cell_where_both_runs_are_proven_infeasible_is_both_infeasible_for_L_and_calls_no_cli(ctxs, e4a, day_large_sedan):
    calls = []
    row, errors, info = run_cell(ctxs["large+sedan"], day_large_sedan, e4a, 1, cli=lambda cases: calls.append(cases) or ({}, ""))
    assert (row["ga_status"], row["union_status"]) == ("infeasible_for_L", "infeasible_for_L")
    assert row["label"] == udm.LABEL_BOTH_INFEASIBLE and row["claim"] == "" and row["cars_difference_union_minus_ga"] == ""
    assert row["timing_dependent"] is False and errors == [] and info["cli_calls"] == 0 and calls == []
    assert "infeasible_for_L" in row["not_proven_reason"]


@needs_node
def test_sedan_2026_10_05_R60_L2_is_ga_menu_infeasible_for_L_with_the_union_cars_and_no_difference(ctxs, e4a):
    ctx = ctxs["large+sedan"]
    day = ud.prepare_day(ctx, 60, DATE, e4a)
    row, errors, _ = run_cell(ctx, day, e4a, 2, cli=ud.run_cli, ride=60)
    assert errors == []
    assert (row["ga_status"], row["union_status"], row["union_cars"]) == ("infeasible_for_L", "optimal", 3)
    assert row["label"] == udm.LABEL_GA_INFEASIBLE and row["union_confirmation"] == udm.CONFIRMED and row["ga_confirmation"] == udm.CONFIRM_NOT_NEEDED
    assert row["claim"] == udm.CLAIM_UNION_ONLY and "never above" not in row["claim"]
    assert row["cars_difference_union_minus_ga"] == "" and row["ga_cars"] == ""
    assert row["timing_dependent"] is False


# ---------------------------------------------------------------- P3: the union REQUEST carries every exact option at every L
def test_the_union_request_at_every_L_carries_every_exact_option_including_xq_above_L(ctxs, e4a):
    seen_above_l = 0
    for name, ctx in ctxs.items():
        day = ud.prepare_day(ctx, RIDE, DATE, e4a)
        expected = [[o.option_id for o in w.options] for w in day["union_waves"]]
        exact_ids = {o.option_id for w in day["union_waves"] for o in w.options if o.origin == "exact"}
        for limit in ctx.replay_fleet.l_values:
            requests = []

            def recording(request, *, time_limit_s, _r=requests):
                _r.append(request)
                return fsr.solve_request(request, time_limit_s=time_limit_s)

            run_cell(ctx, day, e4a, limit, cli=lambda cases: (None, "no cli"), solve=recording)
            union_request = requests[1]  # call 0 = GA menus, call 1 = union (first run)
            assert union_request["max_large"] == limit
            assert [[o["option_id"] for o in w["options"]] for w in union_request["waves"]] == expected, (name, limit)
            carried = {o["option_id"] for w in union_request["waves"] for o in w["options"]}
            assert exact_ids <= carried
            seen_above_l += sum(1 for oid in exact_ids if oid.startswith("xq") and int(oid[2:]) > limit)
    assert seen_above_l > 0, "the example day must contain an exact xq option with q above L, or the test proves nothing"


# ---------------------------------------------------------------- P4: day sums in their own file
def test_day_sums_csv_has_one_row_per_fleet_date_R_with_renamed_q_aggregates(slice_out):
    out, _ = slice_out
    with (out / "day_sums.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header, rows = list(reader.fieldnames), list(reader)
    assert tuple(header) == ud.DAY_SUMS_FIELDS
    assert len(rows) == 2 and {(r["fleet"], r["date"], r["R"]) for r in rows} == {(f, DATE, str(RIDE)) for f in ("large+sedan", "large+doblo_cap3")}
    for name in ("dK_day_base", "gD_day_base", "dK_sum_over_q_options", "gD_over_q_options"):
        assert name in header
    assert not {"dK_day_q", "gD_day_q"} & set(header)
    with (out / "day_gaps.csv").open(encoding="utf-8", newline="") as fh:
        gap_header = csv.DictReader(fh).fieldnames
    assert not set(ud.DAY_SUMS_FIELDS[3:]) & set(gap_header)
