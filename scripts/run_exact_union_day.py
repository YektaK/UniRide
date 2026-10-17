#!/usr/bin/env python3
"""WP-E4b: day-level selection over the union of the GA and the per-wave exact menus (typed fleets).

Design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 1.5 ("Day level over the union menu"), section 8 (row
"Union day level") and section 9 (WP-E4, WP-E6 ``day_gaps.csv``). OFFLINE and archive-only: it reads

* the WP-E10 GA re-run archives (``week-2026-10-05-fleet-rerun-large-sedan`` and ``...-doblo-cap3``): menus,
  archived selection requests and responses;
* the WP-E4a exact options (``wp-e4a-typed-options``: ``exact_routes.json``, ``option_gaps.csv``, manifest);

and needs NO AMPL: CP-SAT (``solve_day_selection`` called directly) plus the TypeScript confirmation CLI
``scripts/verify-typed-selection.ts`` (``node --conditions=react-server --import tsx``, the command of the npm
script ``experiments:fleet``).

Per (fleet, date, R, L) two day selections at one commit and ``time_scale = 100``:

* over the GA menus alone, recomputed here: it must equal the archived WP-E10 response (``status``, ``cars``,
  ``large_peak``, ``car_minutes``, ``total_minutes``, ``selection`` with labels), else the cell is a blocking error;
* over the union menu (GA options in their WP-E10 order, then the certified exact options ``xbase, xq0..xqQ``, never
  deduped against a GA option, deduped among themselves only when their routes are identical).

Time limit: the producer's 30 s; a union run that stopped on its time limit is re-run ONCE at 60 s (the compute
policy ceiling) and the limit is recorded; still not optimal gives ``union_not_proven`` with ``timing_dependent``.
``union cars <= GA-menu cars`` is checked (blocking) only when both runs are ``optimal``. Every selection, GA and
union, goes through the TS CLI; a missing check gives ``not_independently_confirmed``, a failed one
``verification_failed``. The report never shows ``min(GA, union)``.

Wording rule: a single snapshot week; a descriptive comparison; the GA is one seed-42 native run; no superiority claim;
the claim of a ``proven_over_union_menu`` row is exactly ``uniride_core.planning.union_day_menu.CLAIM`` (not a global
day optimum, EQ3).

Exit codes: 0 ok; 1 blocking error (results are still written); 2 archive refused/rejected or unsafe --out.

Run: PYTHONPATH=<repo root> python scripts/run_exact_union_day.py [--fleets ...] [--rides ...] [--dates ...] [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO / "optimizer_api"), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from academic_benchmark.exact_reference import protocol  # noqa: E402
from uniride_core.exact import certification as cert  # noqa: E402
from uniride_core.planning import fleet_selection_request as fsr  # noqa: E402
from uniride_core.planning import union_day_menu as udm  # noqa: E402

RESULTS = REPO / "docs" / "paper" / "results"
E4A_DIR = RESULTS / "week-2026-10-05-exact" / "wp-e4a-typed-options"
DEFAULT_OUT = RESULTS / "week-2026-10-05-exact" / "wp-e4b-union-day"
MANIFEST_FILENAME = "union_day_manifest.json"
WORK_PACKAGE = "WP-E4b"
RERUN_TIME_LIMIT_S = 60.0  # lead decision 2026-10-10: the compute-policy ceiling (compute_policy.py solver_seconds)
SERVICE_DAY_END_MINUTES = 24 * 60  # dudullu-preview.ts SERVICE_DAY_END_MINUTES
CLI_RELATIVE = "scripts/verify-typed-selection.ts"
CLI_COMMAND = ("node", "--conditions=react-server", "--import", "tsx", CLI_RELATIVE)


def _load_module(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tm = _load_module("run_exact_typed_menus")  # fleet contexts, SOURCES, provenance (imports no AMPL at import time)
wg = tm.wg
replay = tm.replay

CSV_FIELDS = (
    "fleet", "date", "R", "L",
    "ga_status", "ga_time_limit_s", "ga_cars", "ga_large_peak", "ga_car_minutes", "ga_total_minutes", "ga_wall_seconds",
    "ga_equals_archived_response", "ga_archived_status",
    "union_status", "union_time_limit_s", "union_cars", "union_large_peak", "union_car_minutes", "union_total_minutes",
    "union_wall_seconds", "union_rerun", "union_first_status", "union_first_wall_seconds",
    "cars_difference_union_minus_ga",
    "label", "timing_dependent", "not_proven_reason", "claim",
    "ga_confirmation", "ga_confirmation_detail", "ga_ts_assignment_status", "ga_ts_cars",
    "union_confirmation", "union_confirmation_detail", "union_ts_assignment_status", "union_ts_cars",
    "union_exact_options_selected", "union_waves_selecting_exact",
    "ga_options", "exact_options_certified", "exact_options_deduped_among_exact", "exact_options_added", "exact_options_skipped_outside_service_day",
    "union_options",
    "ga_max_options_per_wave", "ga_max_routes_per_option", "ga_total_routes", "ga_cap_options_per_wave",
    "ga_cap_routes_per_option", "ga_cap_total_routes",
    "union_max_options_per_wave", "union_waves_over_options_cap", "union_cap_options_per_wave",
    "union_max_routes_per_option", "union_options_over_routes_cap", "union_cap_routes_per_option",
    "union_total_routes", "union_cap_total_routes",
    "base_waves_compared", "dK_day_base", "gD_day_base", "gD_excluded_waves_base", "base_options_not_compared",
    "q_options_compared", "dK_day_q", "gD_day_q", "gD_excluded_options_q", "q_options_not_compared",
    "cpsat_version", "cpsat_seed", "cpsat_workers", "ga_commit", "ga_protocol", "ga_seed", "ga_dirty_tree",
)


# ---------------------------------------------------------------- inputs
def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_e4a(e4a_dir: Path) -> dict:
    """The E4a exact options, checked against the E4a manifest (routes sha256, work package, clean tree)."""
    e4a_dir = Path(e4a_dir)
    manifest = json.loads((e4a_dir / protocol.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    routes_path = e4a_dir / tm.EXACT_ROUTES_FILENAME
    routes_sha = sha256_file(routes_path)
    declared = manifest.get("exact_routes", {}).get("sha256")
    if routes_sha != declared:
        raise loader_error(f"exact_routes.json sha256 {routes_sha} differs from the E4a manifest {declared}")
    if manifest.get("dirty_working_tree") is not False:
        raise loader_error("the E4a campaign was not run from a clean tree")
    doc = json.loads(routes_path.read_text(encoding="utf-8"))
    return {"manifest": manifest, "routes_doc": doc, "routes_sha256": routes_sha,
            "manifest_sha256": sha256_file(e4a_dir / protocol.MANIFEST_FILENAME),
            "option_gaps_sha256": sha256_file(e4a_dir / "option_gaps.csv"),
            "option_gaps_rows": list(csv.DictReader((e4a_dir / "option_gaps.csv").open(encoding="utf-8", newline=""))),
            "replay_rows": {(r["fleet"], r["date"], int(r["R"]), int(r["L"])): r for r in
                            csv.DictReader((e4a_dir / "replay.csv").open(encoding="utf-8", newline=""))}}


def loader_error(message: str) -> Exception:
    return tm.loader.InputRejected(message)


def exact_option_id(doc: dict) -> str:
    return "xbase" if doc["kind"] == "base" else f"xq{doc['quota']}"


def exact_option_sort_key(doc: dict):
    return (0, 0) if doc["kind"] == "base" else (1, int(doc["quota"]))


def is_menu_entry(doc: dict) -> bool:
    """A certified, feasible exact option with routes; infeasible or uncertified options are not menu entries."""
    return bool(doc.get("certified")) and bool(doc.get("routes")) and doc.get("status") in ("optimal", "feasible_with_gap")


def exact_menu_option(wave, doc: dict, type_ids) -> tuple:
    """``(MenuOption or None, reason)``: an exact option as a menu entry, intervals from the wave matrix and anchor.

    Same rules as the producer: a pickup route ends at the anchor and starts ``total`` minutes before, a dropoff route
    starts at the anchor; a route outside the service day is not a valid option (the producer would refuse it).
    """
    pairs = [(r["type_id"], tuple(r["occurrence_ids"])) for r in doc["routes"]]
    payload = cert.typed_response_payload(wave, pairs, type_ids=type_ids)
    facts, stops, data = [], [], []
    for route in payload["routes"]:
        durations = tuple(step["duration"] for step in route["route_details"])
        total = sum(durations)
        start = wave.anchor_minutes - total if wave.direction == "pickup" else wave.anchor_minutes
        end = wave.anchor_minutes if wave.direction == "pickup" else wave.anchor_minutes + total
        if not (start >= 0 and end <= SERVICE_DAY_END_MINUTES):
            return None, "ROUTE_OUTSIDE_SERVICE_DAY"
        facts.append(fsr.RouteFacts(start, end, durations, wave.direction, route["sw_count"], route["so_count"]))
        stops.append(tuple(route["student_ids"]))
        data.append({"route_details": route["route_details"], "student_ids": route["student_ids"], "sw_count": route["sw_count"],
                     "so_count": route["so_count"], "total_duration_minutes": route["total_duration_minutes"]})
    return udm.MenuOption(exact_option_id(doc), False, tuple(facts), "exact", tuple(stops), tuple(data)), ""


def exact_menus(ctx, ride: int, date: str, e4a: dict) -> tuple:
    """``({wave_id: [MenuOption xbase, xq0..]}, skipped)`` of one (fleet, date, R) from the E4a stored routes."""
    waves = {w.wave_id: w for w in ctx.campaign.waves_for(ride) if w.service_date == date}
    docs: dict = {}
    for doc in e4a["routes_doc"]["waves"]:
        if doc["fleet"] == ctx.name and doc["R"] == ride and doc["service_date"] == date and is_menu_entry(doc):
            docs.setdefault(doc["wave_id"], []).append(doc)
    out, skipped = {}, []
    for wave_id, items in docs.items():
        if wave_id not in waves:
            raise loader_error(f"{ctx.name} {date} R{ride}: exact options of unknown wave {wave_id}")
        options = []
        for doc in sorted(items, key=exact_option_sort_key):
            option, reason = exact_menu_option(waves[wave_id], doc, ctx.type_ids)
            if option is None:
                skipped.append({"wave_id": wave_id, "option": exact_option_id(doc), "reason": reason})
            else:
                options.append(option)
        out[wave_id] = options
    return out, skipped


def ga_wave_menus(menu_doc: dict) -> list:
    """The GA menu (included options only, archive order) with the route data the TS confirmation needs."""
    waves = []
    for wave in menu_doc["waves"]:
        options = []
        for o in wave["options"]:
            if o["status"] != "included":
                continue
            routes = tuple(replay.route_facts(r, wave["direction"]) for r in o["routes"])
            data = tuple({"route_details": [{"location1": s["location1"], "location2": s["location2"], "duration": s["duration"]}
                                            for s in r["steps"]],
                          "student_ids": list(r["studentIds"]), "sw_count": r["swCount"], "so_count": r["soCount"],
                          "total_duration_minutes": r["totalDurationMinutes"]} for r in o["routes"])
            options.append(udm.MenuOption(o["optionId"], o["kind"] == "baseline", routes, "ga",
                                          tuple(tuple(r["studentIds"]) for r in o["routes"]), data))
        waves.append(udm.WaveMenu(wave["waveId"], wave["direction"], wave["anchorMinutes"], tuple(options)))
    return waves


# ---------------------------------------------------------------- router caps and limits
def router_caps() -> dict:
    router = replay._router()
    return {"max_options_per_wave": router.MAX_OPTIONS_PER_WAVE, "max_routes_per_option": router.MAX_ROUTES_PER_OPTION,
            "max_total_routes": router.MAX_TOTAL_ROUTES}


def check_limits(producer_limit_s: float) -> None:
    """The producer's limit and the re-run limit must both be accepted by the router's compute policy."""
    router = replay._router()
    for limit in (producer_limit_s, RERUN_TIME_LIMIT_S):
        if router._policy_time_limit(limit) is None:
            raise loader_error(f"time limit {limit} s is above the compute policy")


# ---------------------------------------------------------------- the TS confirmation CLI
def type_json(spec) -> dict:
    out = {"typeId": spec.type_id, "swCapacity": spec.sw_capacity, "soCapacity": spec.so_capacity,
           "cooldownMinutes": spec.cooldown_minutes}
    for key, value in (("totalCapacity", spec.total_capacity), ("rideLimit", spec.ride_limit_minutes),
                       ("tourLimit", spec.tour_limit_minutes)):
        if value is not None:
            out[key] = value
    return out


class SelectionMismatch(Exception):
    """The selection does not match the menu it was computed on (a label count differs from the route count)."""


def cli_case(case_id: str, ctx, limits: dict, max_large: int, request: dict, waves: list, run: udm.RunRecord) -> dict:
    """The TS CLI input of one selection: the chosen option's route data per wave, labels, and the Python interval values."""
    menu = {w.wave_id: w for w in waves}
    out_waves = []
    for wave_req in request["waves"]:
        wave_id = wave_req["wave_id"]
        pick = run.selection.get(wave_id)
        if pick is None:
            raise SelectionMismatch(f"{wave_id}: no option selected")
        option = next((o for o in menu[wave_id].options if o.option_id == pick["option_id"]), None)
        req_option = next((o for o in wave_req["options"] if o["option_id"] == pick["option_id"]), None)
        if option is None or req_option is None or len(pick["labels"]) != len(option.routes):
            raise SelectionMismatch(f"{wave_id}: selection {pick.get('option_id')} does not match the menu")
        out_waves.append({
            "waveId": wave_id, "direction": menu[wave_id].direction, "anchorMinutes": menu[wave_id].anchor_minutes,
            "routes": [dict(data, label=label, python={k: body[k] for k in ("start", "end", "minutes", "large_ok", "car_ok")})
                       for data, label, body in zip(option.route_data, pick["labels"], req_option["routes"])]})
    case = {"caseId": case_id, "timeScale": request["time_scale"], "fixedType": type_json(ctx.fixed),
            "minimiseType": type_json(ctx.minimise),
            "limits": {"maxRideTimeMinutes": limits["maxRideTimeMinutes"], "maxTourMinutes": limits["maxTourMinutes"]},
            "maxLarge": max_large, "pythonCooldowns": {"large": request["cooldown_large"], "car": request["cooldown_car"]},
            "waves": out_waves}
    if request.get("max_cars") is not None:
        case["maxCars"] = request["max_cars"]
    return case


def node_executable() -> str:
    return shutil.which("node") or ""


def run_cli(cases: list, *, timeout: float = 900.0) -> tuple:
    """``(results_by_case_id or None, error)``: the TS CLI exactly as ``npm run experiments:fleet`` starts its script.

    Any failure to obtain a parseable answer (node missing, nonzero exit, invalid JSON, wrong case ids) returns
    ``(None, reason)``: the check is MISSING, not failed.
    """
    node = node_executable()
    if not node:
        return None, "node not found"
    with tempfile.TemporaryDirectory(prefix="verify-typed-") as tmp:
        source = Path(tmp) / "in.json"
        source.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        try:
            proc = subprocess.run([node, *CLI_COMMAND[1:], str(source)], cwd=REPO, capture_output=True, text=True,
                                  timeout=timeout, encoding="utf-8")
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f"{type(exc).__name__}"
    if proc.returncode != 0:
        return None, f"exit {proc.returncode}: {proc.stderr.strip()[:300]}"
    try:
        results = {r["caseId"]: r for r in json.loads(proc.stdout)["results"]}
    except (ValueError, KeyError, TypeError) as exc:
        return None, f"unparseable CLI output ({type(exc).__name__})"
    if set(results) != {c["caseId"] for c in cases}:
        return None, "CLI answered other cases than asked"
    return results, ""


def tool_versions() -> dict:
    out = {"node": None, "tsx": None}
    node = node_executable()
    if node:
        out["node"] = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip() or None
    tsx_pkg = REPO / "node_modules" / "tsx" / "package.json"
    if tsx_pkg.is_file():
        out["tsx"] = json.loads(tsx_pkg.read_text(encoding="utf-8")).get("version")
    return out


# ---------------------------------------------------------------- day sums of the E4a options
def day_option_sums(rows: list, fleet: str, date: str, ride: int) -> dict:
    """Day aggregation of the E4a option rows (design section 1.2 "Day aggregation"), per option kind.

    ``base`` = xbase against the GA ``base``; ``q`` = the typed options xq0..xqQ against the GA ``qN`` of the same
    kind. Per kind, over the options with ``comparison == compared`` (a feasible exact option and a feasible GA
    option): ``dK_day`` = sum of ``dK`` (``K`` for base, ``K_m`` for q); ``gD_day`` = (sum D_GA - sum D_LB) / sum D_LB over
    the options where ``gD`` is defined (``K_GA = K*``); the others are counted as excluded. Options that are not
    ``compared`` are counted separately. Kinds are never pooled and the quotas q0..qQ are summed without weights.
    """
    out: dict = {}
    mine = [r for r in rows if r["fleet"] == fleet and r["date"] == date and int(r["R"]) == ride]
    for kind in ("base", "q"):
        part = [r for r in mine if r["kind"] == kind]
        compared = [r for r in part if r["comparison"] == "compared"]
        defined = [r for r in compared if r["gD"] != ""]
        d_ga = sum(int(r["D_GA"]) for r in defined)
        d_lb = sum(int(r["D_LB"]) for r in defined)
        out[kind] = {
            "compared": len(compared), "dK_day": sum(int(r["dK"]) for r in compared),
            "gD_day": None if d_lb == 0 else round((d_ga - d_lb) / d_lb, 6),
            "gD_excluded": len(compared) - len(defined), "not_compared": len(part) - len(compared)}
    return out


# ---------------------------------------------------------------- one cell

def prepare_day(ctx, ride: int, date: str, e4a: dict) -> dict:
    """The GA menu, the exact options, the union menu and the E4a day sums of one (fleet, date, R); shared by every L."""
    menu_doc = json.loads((ctx.path / f"{date}_R{ride}.menu_options.json").read_text(encoding="utf-8"))
    ga_waves = ga_wave_menus(menu_doc)
    exact, skipped = exact_menus(ctx, ride, date, e4a)
    union_waves, dedupe = udm.build_union_menu(ga_waves, exact)
    return {"menu_doc": menu_doc, "ga_waves": ga_waves, "union_waves": union_waves,
            "exact_info": {"menus": exact, "skipped": skipped, "dedupe_log": dedupe},
            "sums": day_option_sums(e4a["option_gaps_rows"], ctx.name, date, ride)}


def load_archived_exchange(ctx, date: str, ride: int, limit: int) -> dict:
    return json.loads((ctx.path / f"{date}_R{ride}_L{limit}.selection_exchange.json").read_text(encoding="utf-8"))


def blank(value):
    return "" if value is None else value


def solve_cell_row(ctx, date: str, ride: int, limit: int, *, ga_waves: list, union_waves: list, exact_info: dict, archived: dict,
                   menu_limits: dict, caps: dict, day_sums: dict, producer_limit_s: float, solve, to_body, clock, cli, cpsat: dict,
                   e4a_replay_row=None) -> tuple:
    """One CSV row (and its blocking errors) of (fleet, date, R, L)."""
    tag = f"{ctx.name} {date} R{ride} L{limit}"
    errors: list = []
    kw = dict(fixed_type=ctx.replay_fleet.fixed, minimise_type=ctx.replay_fleet.minimise, max_large=limit,
              ride_default=menu_limits["maxRideTimeMinutes"], tour_default=menu_limits["maxTourMinutes"],
              cooldown_large_minutes=replay._cooldown(ctx.replay_fleet, ctx.replay_fleet.fixed),
              cooldown_car_minutes=replay._cooldown(ctx.replay_fleet, ctx.replay_fleet.minimise),
              max_cars=ctx.replay_fleet.max_cars, time_limit_seconds=producer_limit_s)
    ga_request = fsr.build_selection_request(udm.request_waves(ga_waves), **kw)
    union_request = fsr.build_selection_request(udm.request_waves(union_waves), **kw)
    request_diffs = replay.diff_json(archived["request"], ga_request)
    if request_diffs:
        errors.append(f"{tag}: the rebuilt GA-menu request differs from the archived request: {request_diffs[:3]}")
    cell = udm.solve_cell(ga_request, union_request, producer_limit_s=producer_limit_s, rerun_limit_s=RERUN_TIME_LIMIT_S,
                          solve=solve, to_body=to_body, clock=clock)
    ga, union = cell.ga, cell.union
    response_diffs = replay.compare_response(archived["response"], dict(ga.body)) if isinstance(archived.get("response"), dict) else ["no archived response"]
    if response_diffs:
        errors.append(f"{tag}: the recomputed GA-menu selection differs from the archived WP-E10 response: {response_diffs[:3]}")
    if e4a_replay_row is not None and (e4a_replay_row["replay_status"] != ga.status or e4a_replay_row["label"] not in replay.MATCH_LABELS):
        errors.append(f"{tag}: the recomputed GA-menu status {ga.status} differs from the WP-E4a replay "
                      f"({e4a_replay_row['replay_status']}, {e4a_replay_row['label']})")
    stats = ga.body.get("stats") or {}
    if ga.status in udm.SELECTION_STATUSES and (stats.get("random_seed"), stats.get("num_workers")) != (cpsat["seed"], cpsat["workers"]):
        errors.append(f"{tag}: CP-SAT seed/workers {stats.get('random_seed')}/{stats.get('num_workers')} differ from the archive")

    # independent confirmation: every selection, GA-menu and union, through the TS CLI
    cases, case_errors = [], {}
    for name, run, request, waves in (("ga", ga, ga_request, ga_waves), ("union", union, union_request, union_waves)):
        if run.status not in udm.SELECTION_STATUSES:
            continue
        try:
            cases.append(cli_case(f"{tag}|{name}", ctx, menu_limits, limit, request, waves, run))
        except SelectionMismatch as exc:
            case_errors[name] = str(exc)
    cli_results, cli_error = (cli(cases) if cases else ({}, ""))

    def confirm(name, run):
        if name in case_errors:  # the selection does not match its menu: a failed check, never a missing one
            return udm.Confirmation(udm.CONFIRM_FAILED, f"SELECTION_RESPONSE_MISMATCH: {case_errors[name]}")
        result = None if cli_results is None else cli_results.get(f"{tag}|{name}")
        got = udm.confirmation_from_cli(result, run)
        if got.status == udm.CONFIRM_MISSING and cli_error:
            return udm.Confirmation(udm.CONFIRM_MISSING, cli_error)
        return got

    ga_conf, union_conf = confirm("ga", ga), confirm("union", union)
    verdict = udm.classify(cell, ga_conf, union_conf)
    errors.extend(f"{tag}: {e}" for e in verdict.blocking_errors)

    exact_selected = [wid for wid, pick in union.selection.items() if str(pick.get("option_id", "")).startswith("x")]
    exact_option_total = sum(len(v) for v in exact_info["menus"].values())
    ga_flags = udm.router_cap_flags(ga_request, **caps)
    union_flags = udm.router_cap_flags(union_request, **caps)
    proven = verdict.label == udm.LABEL_PROVEN
    row = {
        "fleet": ctx.name, "date": date, "R": ride, "L": limit,
        "ga_status": ga.status, "ga_time_limit_s": ga.time_limit_s, "ga_cars": blank(ga.cars), "ga_large_peak": blank(ga.large_peak),
        "ga_car_minutes": blank(ga.car_minutes), "ga_total_minutes": blank(ga.total_minutes), "ga_wall_seconds": ga.wall_seconds,
        "ga_equals_archived_response": not response_diffs and not request_diffs,
        "ga_archived_status": blank((archived.get("response") or {}).get("status")),
        "union_status": union.status, "union_time_limit_s": union.time_limit_s, "union_cars": blank(union.cars),
        "union_large_peak": blank(union.large_peak), "union_car_minutes": blank(union.car_minutes),
        "union_total_minutes": blank(union.total_minutes), "union_wall_seconds": union.wall_seconds, "union_rerun": cell.rerun,
        "union_first_status": cell.union_first.status, "union_first_wall_seconds": cell.union_first.wall_seconds,
        # a difference of the two runs is shown only for a proven row; never a min(GA, union)
        "cars_difference_union_minus_ga": (union.cars - ga.cars) if proven else "",
        "label": verdict.label, "timing_dependent": verdict.timing_dependent, "not_proven_reason": verdict.reason if not proven else "",
        "claim": verdict.claim,
        "ga_confirmation": ga_conf.status, "ga_confirmation_detail": ga_conf.detail, "ga_ts_assignment_status": blank(ga_conf.ts_status),
        "ga_ts_cars": blank(ga_conf.ts_cars),
        "union_confirmation": union_conf.status, "union_confirmation_detail": union_conf.detail,
        "union_ts_assignment_status": blank(union_conf.ts_status), "union_ts_cars": blank(union_conf.ts_cars),
        "union_exact_options_selected": len(exact_selected), "union_waves_selecting_exact": ";".join(sorted(exact_selected)),
        "ga_options": sum(len(w.options) for w in ga_waves), "exact_options_certified": exact_option_total,
        "exact_options_deduped_among_exact": len(exact_info["dedupe_log"]),
        "exact_options_skipped_outside_service_day": len(exact_info["skipped"]),
        "exact_options_added": sum(len(w.options) for w in union_waves) - sum(len(w.options) for w in ga_waves),
        "union_options": sum(len(w.options) for w in union_waves),
        "ga_max_options_per_wave": ga_flags["max_options_per_wave"], "ga_max_routes_per_option": ga_flags["max_routes_per_option"],
        "ga_total_routes": ga_flags["total_routes"], "ga_cap_options_per_wave": ga_flags["cap_options_per_wave"],
        "ga_cap_routes_per_option": ga_flags["cap_routes_per_option"], "ga_cap_total_routes": ga_flags["cap_total_routes"],
        "union_max_options_per_wave": union_flags["max_options_per_wave"], "union_waves_over_options_cap": union_flags["waves_over_options_cap"],
        "union_cap_options_per_wave": union_flags["cap_options_per_wave"],
        "union_max_routes_per_option": union_flags["max_routes_per_option"],
        "union_options_over_routes_cap": union_flags["options_over_routes_cap"],
        "union_cap_routes_per_option": union_flags["cap_routes_per_option"], "union_total_routes": union_flags["total_routes"],
        "union_cap_total_routes": union_flags["cap_total_routes"],
        "base_waves_compared": day_sums["base"]["compared"], "dK_day_base": day_sums["base"]["dK_day"],
        "gD_day_base": blank(day_sums["base"]["gD_day"]), "gD_excluded_waves_base": day_sums["base"]["gD_excluded"],
        "base_options_not_compared": day_sums["base"]["not_compared"],
        "q_options_compared": day_sums["q"]["compared"], "dK_day_q": day_sums["q"]["dK_day"],
        "gD_day_q": blank(day_sums["q"]["gD_day"]), "gD_excluded_options_q": day_sums["q"]["gD_excluded"],
        "q_options_not_compared": day_sums["q"]["not_compared"],
        "cpsat_version": cpsat["version"], "cpsat_seed": cpsat["seed"], "cpsat_workers": cpsat["workers"],
        "ga_commit": ctx.ga_labels["ga_commit"], "ga_protocol": ctx.ga_labels["ga_protocol"], "ga_seed": ctx.ga_labels["ga_seed"],
        "ga_dirty_tree": ctx.ga_labels["ga_dirty_tree"],
    }
    return row, errors, {"rerun": cell.rerun, "cli_error": cli_error, "cli_calls": 1 if cases else 0}




# ---------------------------------------------------------------- run
def write_csv(path: Path, rows: list) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(CSV_FIELDS), lineterminator="\n", extrasaction="raise")
        wr.writeheader()
        wr.writerows(rows)


def summarise(rows: list) -> dict:
    per: dict = {}
    for r in rows:
        p = per.setdefault(f"{r['fleet']}|L{r['L']}", {
            "cells": 0, "labels": {}, "union_cars_below_ga": 0, "union_cars_equal_ga": 0, "union_cars_above_ga": 0,
            "not_proven": 0, "timing_dependent": 0, "ga_statuses": {}, "union_statuses": {}, "union_reruns": 0,
            "union_selects_exact_in_cells": 0, "router_caps_exceeded_by_union": {"options_per_wave": 0, "routes_per_option": 0, "total_routes": 0}})
        p["cells"] += 1
        p["labels"][r["label"]] = p["labels"].get(r["label"], 0) + 1
        p["ga_statuses"][r["ga_status"]] = p["ga_statuses"].get(r["ga_status"], 0) + 1
        p["union_statuses"][r["union_status"]] = p["union_statuses"].get(r["union_status"], 0) + 1
        if r["label"] == udm.LABEL_PROVEN:
            diff = int(r["cars_difference_union_minus_ga"])
            p["union_cars_below_ga" if diff < 0 else "union_cars_equal_ga" if diff == 0 else "union_cars_above_ga"] += 1
        else:
            p["not_proven"] += 1
        p["timing_dependent"] += bool(r["timing_dependent"])
        p["union_reruns"] += bool(r["union_rerun"])
        p["union_selects_exact_in_cells"] += int(r["union_exact_options_selected"]) > 0
        caps = p["router_caps_exceeded_by_union"]
        caps["options_per_wave"] += bool(r["union_cap_options_per_wave"])
        caps["routes_per_option"] += bool(r["union_cap_routes_per_option"])
        caps["total_routes"] += bool(r["union_cap_total_routes"])
    return {"purpose": "WP-E4b union-menu day selection: descriptive comparison of one seed-42 native GA run's menus with the "
                       "union of the GA and per-wave exact menus; no superiority claim, never min(GA, union)",
            "claim": udm.CLAIM, "cells": len(rows), "per_fleet_L": per,
            "labels": {k: sum(1 for r in rows if r["label"] == k) for k in udm.LABELS}}


def required_manifest_keys() -> tuple:
    return ("protocol", "work_package", "git_commit", "dirty_working_tree", "source_campaigns", "exact_options_source", "cpsat",
            "time_scale", "router_caps", "tools", "python_provenance", "python_version", "host_os", "run_history", "claim",
            "ga_recompute", "labels", "blocking_errors", "total_wall_seconds")


def validate_manifest(manifest: dict) -> list:
    problems = [f"missing {k}" for k in required_manifest_keys() if k not in manifest]
    if manifest.get("time_scale") != 100:
        problems.append("time_scale must be 100")
    if manifest.get("claim") != udm.CLAIM:
        problems.append("claim text differs from the design wording")
    problems.extend(protocol.private_data_errors(manifest))
    return problems


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--fleets", default=",".join(tm.SOURCES), help="comma list (default: both typed fleets)")
    ap.add_argument("--rides", default="", help="comma list of R values (default: all of the campaign)")
    ap.add_argument("--dates", default="", help="comma list of service dates (default: all)")
    ap.add_argument("--limits", default="", help="comma list of L values (default: all of the campaign)")
    ap.add_argument("--e4a-dir", default=str(E4A_DIR), help="the WP-E4a results directory (exact options)")
    return ap.parse_args(argv)


def check_out(out: Path, e4a_dir: Path, sources: list) -> str:
    for source in sources:
        refusal = wg.check_out_dir(out, source)
        if refusal:
            return refusal
    out_r, e4a_r = Path(out).resolve(), Path(e4a_dir).resolve()
    if out_r == e4a_r or out_r in e4a_r.parents or e4a_r in out_r.parents:
        return "--out must not contain or lie inside the WP-E4a results directory (the exact options input)"
    return ""


def main(argv=None) -> int:
    args = parse_args(argv)
    out, e4a_dir = Path(args.out), Path(args.e4a_dir)
    names = [n for n in args.fleets.split(",") if n]
    unknown = [n for n in names if n not in tm.SOURCES]
    if unknown:
        print(f"refused: unknown fleet(s) {unknown}; valid: {sorted(tm.SOURCES)}", file=sys.stderr)
        return 2
    refusal = check_out(out, e4a_dir, [tm.SOURCES[n] for n in names])
    if refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    t_start = time.perf_counter()
    try:
        provenance = tm._provenance()
        ctxs = [tm.load_fleet_context(tm.SOURCES[n]) for n in names]
        e4a = load_e4a(e4a_dir)
        caps = router_caps()
    except (tm.loader.CampaignRefused, tm.loader.InputRejected, KeyError, OSError, ValueError, RuntimeError) as exc:
        print(f"input_rejected: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    commit, dirty = wg._git_state(out)
    import ortools

    cpsat = {"version": ortools.__version__, "seed": None, "workers": None}
    errors: list = []
    rows: list = []
    cell_log: list = []
    sources: dict = {}
    dedupe_log: list = []
    skipped_log: list = []
    rides_filter = [int(r) for r in args.rides.split(",") if r]
    dates_filter = [d for d in args.dates.split(",") if d]
    limits_filter = [int(x) for x in args.limits.split(",") if x]
    cli_calls = 0
    for ctx in ctxs:
        fleet = ctx.replay_fleet
        if ortools.__version__ != fleet.solver["version"]:
            print(f"input_rejected: CP-SAT {ortools.__version__} differs from the archived {fleet.solver['version']}", file=sys.stderr)
            return 2
        cpsat.update(seed=fleet.solver["random_seed"], workers=fleet.solver["num_workers"])
        try:
            check_limits(fleet.selection_time_limit)
        except tm.loader.InputRejected as exc:
            print(f"input_rejected: {exc}", file=sys.stderr)
            return 2
        sources[ctx.name] = {
            "path": wg._rel(ctx.path), "manifest_sha256": sha256_file(ctx.path / "run_manifest.json"),
            "git_commit": str(ctx.manifest["git_commit"]), "dirty_working_tree": bool(ctx.manifest["dirty_working_tree"]),
            "termination_protocol": ctx.ga_labels["ga_protocol"], "effective_seed": ctx.ga_labels["ga_seed"],
            "fixed_type": ctx.fixed.type_id, "minimize_type": ctx.minimise.type_id, "selection_solver": ctx.manifest["selection_solver"],
            "selection_time_limit_seconds": fleet.selection_time_limit}
        dates = sorted({w.service_date for w in ctx.campaign.waves_for(ctx.campaign.rides[0])})
        for ride in rides_filter or list(ctx.campaign.rides):
            for date in dates_filter or dates:
                day = prepare_day(ctx, ride, date, e4a)
                menu_doc, ga_waves, union_waves, exact_info, sums = (
                    day["menu_doc"], day["ga_waves"], day["union_waves"], day["exact_info"], day["sums"])
                dedupe_log.extend({"fleet": ctx.name, "date": date, "R": ride, **d} for d in exact_info["dedupe_log"])
                skipped_log.extend({"fleet": ctx.name, "date": date, "R": ride, **s} for s in exact_info["skipped"])
                for limit in limits_filter or list(fleet.l_values):
                    archived = load_archived_exchange(ctx, date, ride, limit)
                    t_cell = time.perf_counter()
                    replay_row = e4a["replay_rows"].get((fleet.name, date, ride, limit))
                    if replay_row is None:
                        errors.append(f"{ctx.name} {date} R{ride} L{limit}: no WP-E4a replay row for the cell")
                    row, cell_errors, info = solve_cell_row(
                        ctx, date, ride, limit, ga_waves=ga_waves, union_waves=union_waves, exact_info=exact_info, archived=archived,
                        menu_limits=menu_doc["limits"], caps=caps, day_sums=sums, producer_limit_s=fleet.selection_time_limit,
                        solve=fsr.solve_request, to_body=fsr.result_body, clock=time.perf_counter, cli=run_cli, cpsat=cpsat,
                        e4a_replay_row=replay_row)
                    rows.append(row)
                    errors.extend(cell_errors)
                    cli_calls += info["cli_calls"]
                    cell_log.append({"cell": f"{ctx.name}|R{ride}|{date}|L{limit}", "wall_seconds": round(time.perf_counter() - t_cell, 2),
                                     "union_rerun": info["rerun"], "cli_error": info["cli_error"] or None, "label": row["label"]})
                    print(f"{ctx.name} {date} R{ride} L{limit}: GA {row['ga_status']}/{row['ga_cars']} union {row['union_status']}/"
                          f"{row['union_cars']} -> {row['label']} ({cell_log[-1]['wall_seconds']} s)", flush=True)

    wall = round(time.perf_counter() - t_start, 1)
    summary = summarise(rows)
    manifest = {
        "protocol": "union_day_v1", "work_package": WORK_PACKAGE, "git_commit": commit, "dirty_working_tree": dirty,
        "fleets": names, "source_campaigns": sources,
        "exact_options_source": {"path": wg._rel(e4a_dir), "exact_routes_sha256": e4a["routes_sha256"],
                                 "option_gaps_sha256": e4a["option_gaps_sha256"], "manifest_sha256": e4a["manifest_sha256"],
                                 "git_commit": e4a["manifest"]["git_commit"], "work_package": e4a["manifest"].get("work_package")},
        "cpsat": {"version": cpsat["version"], "random_seed": cpsat["seed"], "num_workers": cpsat["workers"],
                  "producer_time_limit_seconds": {n: sources[n]["selection_time_limit_seconds"] for n in names},
                  "rerun_time_limit_seconds": RERUN_TIME_LIMIT_S,
                  "rerun_rule": "a union run that stopped on its time limit (feasible or indeterminate) is re-run once at the "
                                "re-run limit; a proven infeasibility is final"},
        "time_scale": fsr.TIME_SCALE, "router_caps": caps, "tools": dict(tool_versions(), cli_command=" ".join(CLI_COMMAND)),
        "python_provenance": provenance, "python_version": platform.python_version(), "host_os": platform.system() + "-" + platform.release(),
        "options": {"rides": rides_filter, "dates": dates_filter, "limits": limits_filter, "fleets": names},
        "menu_rules": {"dedupe": "exact options are never deduped against GA options; deduped among themselves only when partition, "
                                 "stop order and per-route minutes are identical (first kept)",
                       "exact_option_order": "xbase, xq0..xqQ", "exact_baseline_flag": False,
                       "exact_dedupe_log": dedupe_log, "exact_skipped": skipped_log},
        "ga_recompute": {"cells": len(rows), "equal_to_archived_response": sum(bool(r["ga_equals_archived_response"]) for r in rows)},
        "claim": udm.CLAIM, "labels": summary["labels"],
        "run_history": {"invocations": [{"serial": True, "wall_seconds": wall}], "cells_planned": len(rows), "cells_solved": len(rows),
                        "union_reruns": sum(c["union_rerun"] for c in cell_log), "cli_calls": cli_calls,
                        "cli_errors": sum(bool(c["cli_error"]) for c in cell_log), "cells": cell_log},
        "total_wall_seconds": wall, "blocking_errors": errors,
    }
    problems = validate_manifest(manifest)
    if problems:
        errors.extend(f"manifest: {p}" for p in problems)
        manifest["blocking_errors"] = errors
    out.mkdir(parents=True, exist_ok=True)
    (out / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    write_csv(out / "day_gaps.csv", rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary["labels"], sort_keys=True))
    if errors:
        print(f"{len(errors)} blocking error(s):", file=sys.stderr)
        for e in errors[:50]:
            print(f"  {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
