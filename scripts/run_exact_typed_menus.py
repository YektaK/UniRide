#!/usr/bin/env python3
"""GOAL 1 typed runner (WP-E4a): exact per-wave typed menus against the WP-E10 GA options, option by option.

Design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 1.2 (bounds and gaps), 1.5 (per-wave exact menu and
per-option comparison), 3 (certification, typed path), 4 (labels, manifest, determinism), 6 (HiGHS), 8, 9 (WP-E4).
Mirrors ``scripts/run_exact_wave_gaps.py`` (WP-E3). Part 1 (replay of the WP-E10 day selections with the Python
interval port) runs first and is a gate: if any (date, R, L) cell fails, only ``replay.csv`` is written and nothing
else is solved (exit 4).

Offline: reads the WP-E10 re-run archives (``week-2026-10-05-fleet-rerun-large-sedan`` and ``...-doblo-cap3``)
through ``scripts/exact_archive_loader.py`` and never the DB or HTTP. The old archives are historical and refused.
Per (fleet, date, R, wave) the exact menu is:

* ``xbase``: the single-type set-partitioning problem on the fixed (large) type only; fails closed when that type
  has a ``total_capacity``;
* ``xq`` for ``q = 0..min(max L of the campaign, legs, 4)``: the typed problem with at most ``q`` routes of the
  fixed type, lexicographically minimising the routes of the minimised type (``K_m``), then the tour minutes ``D``.

Each exact option is certified through ``certify_optimization_response`` (typed path: ``vehicle_types``, quota,
``total_capacity``) on the archived matrix slice; the GA option of the same kind (``base`` vs ``xbase``, ``qN`` vs
``xqN``) is re-certified by the same call; K_m and D are recomputed in integers; exact <= GA is checked; every
Gurobi-optimal (or infeasible-proven) option is re-solved with HiGHS (a proven difference blocks).

Wording rule (design section 9): a single snapshot week; a descriptive gap, not a superiority claim; the GA is one
seed-42 run under the native secondary protocol. No exact row is pooled with a heuristic row.

AMPL is located only through UNIRIDE_AMPL_DIR (or the local config / amplpy default); no path and no solver log or
license text is written.

Exit codes: 0 ok; 1 blocking error (results are still written); 2 archive refused/rejected or unsafe --out;
3 AMPL backend unavailable (nothing is written); 4 replay acceptance failed (only replay.csv is written).

Run: python scripts/run_exact_typed_menus.py [--fleets large+sedan,large+doblo_cap3] [--rides 50,60,70,90]
         [--out DIR] [--no-highs-verify]
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import importlib.util
import json
import os
import platform
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
from uniride_core.exact import ampl_backend as ab  # noqa: E402
from uniride_core.exact import certification as cert  # noqa: E402
from uniride_core.exact import gaps  # noqa: E402
from uniride_core.exact.route_enumeration import enumerate_wave  # noqa: E402

RESULTS = REPO / "docs" / "paper" / "results"
DEFAULT_OUT = RESULTS / "week-2026-10-05-exact" / "wp-e4a-typed-options"
SOURCES = {
    "large+sedan": RESULTS / "week-2026-10-05-fleet-rerun-large-sedan",
    "large+doblo_cap3": RESULTS / "week-2026-10-05-fleet-rerun-doblo-cap3",
}
EXACT_ROUTES_FILENAME = "exact_routes.json"
MENU_MAX_QUOTA = 4  # fleet-scenario-run.ts MENU_MAX_QUOTA
XBASE_TOTAL_CAPACITY_LABEL = "XBASE_FIXED_TYPE_HAS_TOTAL_CAPACITY"


def _load_module(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


wg = _load_module("run_exact_wave_gaps")
replay = _load_module("exact_typed_replay")
loader = replay.loader

OPTION_CSV_FIELDS = (
    "fleet", "date", "R", "wave_id", "direction", "anchor", "option", "kind", "quota", "k_kind", "students", "peak",
    "model", "columns", "labels",
    "ga_option_status", "K_GA", "D_GA", "K_LB", "K_LB_source", "K_star", "D_LB", "D_star", "D_LB_free", "dK", "gD",
    "gD_note", "gD_free", "status", "note", "comparison",
    "stage1_status", "stage1_stop_reason", "stage1_timing_dependent",
    "stage2_status", "stage2_stop_reason", "stage2_timing_dependent", "stage2_non_lexicographic",
    "free_status", "free_stop_reason", "free_timing_dependent",
    "solver", "solver_version", "enumeration_seconds", "solve_seconds",
    "exact_certified", "ga_recertified", "ga_cert_archived", "ga_cert_agree", "objective_check", "exact_le_ga",
    "highs_status", "highs_K", "highs_D", "highs_agrees", "highs_free_status", "highs_D_LB_free", "highs_free_agrees",
    "highs_seconds",
    "ga_protocol", "ga_seed", "ga_commit", "ga_dirty_tree",
)
REPLAY_CSV_FIELDS = (
    "fleet", "date", "R", "L", "label", "archived_status", "replay_status", "request_diff_count", "response_diff_count",
    "first_difference", "diagnostics_equal", "seed_workers_equal", "solver_version", "replay_seconds", "router_checks",
    "archived_http_status",
)


# ---------------------------------------------------------------- fleet context and plan
@dataclasses.dataclass(frozen=True)
class FleetContext:
    name: str
    path: Path
    campaign: object
    manifest: dict
    fixed: object  # VehicleTypeSpec of the fixed (large) type
    minimise: object  # VehicleTypeSpec of the minimised type
    ga_labels: dict
    replay_fleet: object

    @property
    def type_ids(self) -> tuple:
        return (self.fixed.type_id, self.minimise.type_id)


def fleet_name(path: Path) -> str:
    for name, src in SOURCES.items():
        if Path(path).resolve() == src.resolve():
            return name
    return Path(path).name


def load_fleet_context(path) -> FleetContext:
    """Context of a WP-E10 re-run archive; the historical fleet archives are refused (never pooled, decision D-A)."""
    path = Path(path)
    if loader.classify(path) not in loader.RERUN.values():
        raise loader.CampaignRefused(f"{path.name}: only the WP-E10 re-run archives are a GA source of the typed study")
    camp = loader.load_campaign(path)
    manifest = json.loads((path / "run_manifest.json").read_text(encoding="utf-8"))
    by_id = {t.type_id: t for t in camp.fleet_types}
    return FleetContext(fleet_name(path), path, camp, manifest, by_id[manifest["fixed_type"]],
                        by_id[manifest["minimize_type"]], wg.ga_labels(manifest), replay.load_fleet(path))


def option_plan(ctx: FleetContext, wave) -> list:
    """``[(option_id, kind, quota)]``: ``base``, then ``q0..min(max L of the campaign, legs, 4)`` (F6, section 1.5)."""
    top = min(ctx.campaign.max_l, wave.legs, MENU_MAX_QUOTA)
    return [("base", "base", None)] + [(f"q{q}", "q", q) for q in range(0, top + 1)]


def xbase_guard(fixed) -> object:
    """None when the single-type baseline is allowed; a label when the fixed type has a ``total_capacity``.

    The GA baseline (``ga_split``) only knows the Sw/So pools; the exact baseline therefore fails closed
    when the fixed type carries a shared seat limit (fleet-scenario-run.ts:470-475).
    """
    return XBASE_TOTAL_CAPACITY_LABEL if fixed.total_capacity is not None else None


def ga_option(menu_doc: dict, wave_id: str, option_id: str):
    for wave in menu_doc["waves"]:
        if wave["waveId"] == wave_id:
            return next((o for o in wave["options"] if o["optionId"] == option_id), None)
    return None


# ---------------------------------------------------------------- certification of one option
def option_request(ctx: FleetContext, wave, kind: str, quota) -> dict:
    if kind == "base":
        f = ctx.fixed
        return cert.request_payload(wave, sw_capacity=f.sw_capacity, so_capacity=f.so_capacity,
                                    cooldown_minutes=f.cooldown_minutes)
    return cert.typed_request_payload(wave, [ctx.fixed, ctx.minimise], minimize_type=ctx.minimise.type_id,
                                      quota=(ctx.fixed.type_id, quota))


def _typed_routes(ctx: FleetContext, kind: str, routes) -> list:
    return [(t if kind == "q" else ctx.fixed.type_id, tuple(seq)) for t, seq in routes]


def _objective(ctx: FleetContext, wave, kind: str, typed_routes) -> tuple:
    """``(K or K_m, D)`` in integers: all routes for ``base``, routes of the minimised type for ``q``."""
    if kind == "base":
        return cert.recompute_objective(wave, [seq for _, seq in typed_routes])
    k_m, d, _ = cert.recompute_typed_objective(wave, typed_routes, ctx.minimise.type_id)
    return k_m, d


def _ga_side(ctx, wave, kind, quota, ga_opt, arcs_doc, tag, errors) -> dict:
    out = {"status": None, "feasible": False, "k": None, "d": None, "recert": None, "archived_cert": None, "agree": None}
    if ga_opt is None:
        errors.append(f"{tag}: archived GA option missing")
        return out
    out["status"] = ga_opt["status"]
    if not (ga_opt.get("success") and ga_opt.get("routes")):
        return out
    out["feasible"] = True
    archived = ga_opt.get("certificate") or {}
    out["archived_cert"] = None if "is_feasible" not in archived else bool(archived["is_feasible"])
    response = cert.ga_option_response_payload(wave, ga_opt, typed=kind == "q", type_ids=ctx.type_ids)
    c = wg.certificate(option_request(ctx, wave, kind, quota), response, arcs_doc)
    out["recert"] = bool(c["is_feasible"])
    out["agree"] = out["recert"] == out["archived_cert"]
    if not out["recert"]:
        errors.append(f"{tag}: GA re-certificate failed ({wg._violation_types(c)})")
    if out["archived_cert"] is not None and not out["agree"]:
        errors.append(f"{tag}: archived GA certificate ({out['archived_cert']}) and re-certificate ({out['recert']}) disagree")
    routes = _typed_routes(ctx, kind, [(r.get("vehicleType"), r["studentIds"]) for r in ga_opt["routes"]])
    try:
        out["k"], out["d"] = _objective(ctx, wave, kind, routes)
    except KeyError:
        errors.append(f"{tag}: GA duration could not be recomputed (a studentIds entry is not an occurrence of the wave)")
        out["feasible"] = False
        return out
    archived_total = ga_opt.get("totalDurationMinutes")
    if archived_total is not None and abs(float(archived_total) - out["d"]) > 1e-6:
        errors.append(f"{tag}: archived GA total {archived_total} differs from the matrix recomputation {out['d']}")
    return out


def _exact_routes_payload(ctx, wave, kind, sp) -> dict:
    if kind == "base":
        return cert.response_payload(wave, [r.occurrence_ids for r in sp.routes])
    return cert.typed_response_payload(wave, [(r.type_id, r.occurrence_ids) for r in sp.routes], type_ids=ctx.type_ids)


def evaluate_option(wave, kind: str, quota, ga_opt, arcs_doc, sp, *, ctx: FleetContext, enum_info: dict, highs=None,
                    peak=None) -> dict:
    """Certify, cross-check and compare one option. Returns ``{"row", "stages", "errors", ...}``.

    ``sp`` is the Gurobi ``SPSolveResult``, ``highs`` the optional HiGHS re-solve, ``ga_opt`` the archived GA
    option of the same kind (a ``menu_options.json`` option) or None. ``errors`` are blocking.
    """
    option_id = "base" if kind == "base" else f"q{quota}"
    tag = f"{ctx.name} {wave.service_date} R{wave.max_ride_minutes} {wave.wave_id} {option_id}"
    errors: list = []
    ga = _ga_side(ctx, wave, kind, quota, ga_opt, arcs_doc, tag, errors)
    k_kind = "K" if kind == "base" else "K_m"

    status, note = sp.status, sp.note
    exact_ok = None
    objective_check = "not_applicable"
    guard = xbase_guard(ctx.fixed) if kind == "base" else None
    if guard:
        status, note = "input_rejected", f"{guard}: the exact baseline fails closed (single-type SP has no shared seat limit)"
        errors.append(f"{tag}: {guard}")
    elif sp.status == "rejected":
        errors.append(f"{tag}: exact solve rejected ({sp.note or 'solver failure'})")
    if not guard and sp.routes and sp.status in ("optimal", "feasible_with_gap"):
        typed = _typed_routes(ctx, kind, [(r.type_id, r.occurrence_ids) for r in sp.routes])
        ec = wg.certificate(option_request(ctx, wave, kind, quota), _exact_routes_payload(ctx, wave, kind, sp), arcs_doc)
        exact_ok = bool(ec["is_feasible"])
        if not exact_ok:
            status, note = "rejected", f"exact certificate failed: {wg._violation_types(ec)}"
            errors.append(f"{tag}: exact certificate failed ({wg._violation_types(ec)})")
        else:
            k, d = _objective(ctx, wave, kind, typed)
            s1, s2 = sp.stage1, sp.stage2
            has_s2 = s2 is not None and s2.objective is not None
            solver_k = s2.k_fix if has_s2 else (None if s1 is None else s1.objective)
            solver_d = s2.objective if has_s2 else sp.d
            problems = cert.objective_mismatches(k, d, solver_k, solver_d) + cert.objective_mismatches(k, d, sp.k, sp.d)
            if problems:
                objective_check = "mismatch"
                status, note = "rejected", "objective cross-check failed: " + "; ".join(problems[:2])
                errors.append(f"{tag}: objective cross-check failed ({'; '.join(problems[:2])})")
            else:
                objective_check = "ok"
    usable = status in ("optimal", "feasible_with_gap")
    exact_optimal = status == "optimal"
    k_star = sp.k if usable else None
    d_star = sp.d if usable else None
    k_proven = sp.k if (usable and sp.stage1 is not None and sp.stage1.status == "optimal") else None
    k_lb = sp.k_lb if status not in ("rejected", "not_run", "input_rejected", "timing_dependent_abort") else None
    d_lb = sp.d_lb if (k_lb is not None and k_proven is not None) else None

    gap = {"dK": None, "gD": None, "gD_note": "unavailable_no_GA", "gD_free": None}
    exact_le_ga = None
    if ga["k"] is not None and ga["d"] is not None:
        gap = gaps.gap_fields(k_ga=ga["k"], d_ga=ga["d"], k_lb=k_lb, k_star=k_proven, d_lb=d_lb,
                              d_lb_free=sp.d_lb_free if k_lb is not None else None)
        for msg in gaps.exact_vs_ga_violations(exact_optimal=exact_optimal, k_star=k_proven, d_star=d_star, k_ga=ga["k"],
                                               d_ga=ga["d"], k_lb=k_lb, d_lb=d_lb):
            errors.append(f"{tag}: {msg}")
        if exact_optimal:
            exact_le_ga = (k_star, d_star) <= (ga["k"], ga["d"])

    # ---- feasibility comparison (section 1.5): labelled; exact infeasible with a feasible GA blocks
    if guard:
        comparison = "exact_not_run"
    elif ga["feasible"] and usable:
        comparison = "compared"
    elif status == "infeasible_proven":
        if ga["feasible"]:
            comparison = "exact_infeasible_ga_feasible"
            errors.append(f"{tag}: exact proves infeasible but the GA option is feasible: model or semantics mismatch")
        else:
            comparison = "both_infeasible" if ga["status"] == "skipped_infeasible" else "exact_infeasible_ga_unavailable"
    elif usable:
        comparison = "ga_infeasible_exact_feasible" if ga["status"] == "skipped_infeasible" else "ga_option_unavailable"
    else:
        comparison = "exact_unsolved"

    # ---- HiGHS verification (section 6) of every Gurobi-optimal or infeasible-proven option
    h_status = h_k = h_d = h_agrees = h_secs = h_free_status = h_free_lb = h_free_agrees = None
    highs_stages: list = []
    if highs is not None and (exact_optimal or status == "infeasible_proven"):
        h_status, h_k, h_d, h_secs = highs.status, highs.k, highs.d, wg._seconds(highs)
        h_free_status = None if highs.free is None else highs.free.status
        h_free_lb = highs.d_lb_free
        if exact_optimal:
            h_agrees, h_free_agrees, h_errors = wg.highs_check(sp, highs)
            errors.extend(f"{tag}: {m}" for m in h_errors)
        else:
            if highs.status == "rejected":
                errors.append(f"{tag}: HiGHS result rejected ({highs.note or 'solver failure'})")
            elif highs.status in ("optimal", "feasible_with_gap"):
                h_agrees = False
                errors.append(f"{tag}: HiGHS found a solution where Gurobi proved the option infeasible")
            elif highs.status == "infeasible_proven":
                h_agrees = True
        highs_stages = [wg.stage_row(s) for s in (highs.stage1, highs.stage2, highs.free) if s is not None]
        for hs in highs_stages:
            errors.extend(f"{tag}: HiGHS stage row: {m}" for m in protocol.validate_stage_row(hs))

    row = {
        "fleet": ctx.name, "date": wave.service_date, "R": wave.max_ride_minutes, "wave_id": wave.wave_id,
        "direction": wave.direction, "anchor": wave.anchor_minutes, "option": option_id, "kind": kind, "quota": quota,
        "k_kind": k_kind, "students": wave.legs, "peak": bool(sp.peak if peak is None else peak),
        "model": enum_info.get("model"), "columns": enum_info.get("columns"), "labels": enum_info.get("labels"),
        "ga_option_status": ga["status"], "K_GA": ga["k"], "D_GA": ga["d"], "K_LB": k_lb,
        "K_LB_source": sp.k_lb_source if k_lb is not None else None, "K_star": k_star, "D_LB": d_lb, "D_star": d_star,
        "D_LB_free": sp.d_lb_free if k_lb is not None else None, "dK": gap["dK"],
        "gD": None if gap["gD"] is None else round(gap["gD"], 6), "gD_note": gap["gD_note"],
        "gD_free": None if gap["gD_free"] is None else round(gap["gD_free"], 6),
        "status": status, "note": note or (f"cap fired: {enum_info['cap_fired']}" if enum_info.get("cap_fired") else ""),
        "comparison": comparison, "solver": sp.solver or "gurobi", "solver_version": sp.solver_version,
        "enumeration_seconds": round(enum_info.get("seconds", 0.0), 4), "solve_seconds": wg._seconds(sp),
        "exact_certified": exact_ok, "ga_recertified": ga["recert"], "ga_cert_archived": ga["archived_cert"],
        "ga_cert_agree": ga["agree"], "objective_check": objective_check, "exact_le_ga": exact_le_ga,
        "highs_status": h_status, "highs_K": h_k, "highs_D": h_d, "highs_agrees": h_agrees,
        "highs_free_status": h_free_status, "highs_D_LB_free": h_free_lb, "highs_free_agrees": h_free_agrees,
        "highs_seconds": h_secs, **ctx.ga_labels,
    }
    wg._stage_cols("stage1", sp.stage1, row)
    wg._stage_cols("stage2", sp.stage2, row, lex=True)
    wg._stage_cols("free", sp.free, row)
    if status == "not_run" and not row["note"]:
        row["note"] = "not solved"
    stages = [wg.stage_row(s) for s in (sp.stage1, sp.stage2, sp.free) if s is not None]
    exact_routes = None
    if sp.routes and not guard:
        exact_routes = {"fleet": ctx.name, "wave_id": wave.wave_id, "service_date": wave.service_date,
                        "R": wave.max_ride_minutes, "option": option_id, "kind": kind, "quota": quota, "status": status,
                        "certified": exact_ok,
                        "routes": [{"type_id": r.type_id, "column_index": r.column_index, "copy": r.copy,
                                    "occurrence_ids": list(r.occurrence_ids), "cost": r.cost, "ride": r.ride,
                                    "tour": r.tour} for r in sp.routes]}
    return {"row": row, "stages": stages, "errors": errors, "highs_stages": highs_stages, "exact_routes": exact_routes}


def recertify_stored_option(wave, stored: dict, arcs_doc: dict, ctx: FleetContext) -> dict:
    """Certificate of the archived exact routes of an option (``exact_routes.json`` entry), no solver needed."""
    kind, quota = stored["kind"], stored["quota"]
    routes = [(r["type_id"], tuple(r["occurrence_ids"])) for r in stored["routes"]]
    if kind == "base":
        payload = cert.response_payload(wave, [seq for _, seq in routes])
    else:
        payload = cert.typed_response_payload(wave, routes, type_ids=ctx.type_ids)
    result = dict(wg.certificate(option_request(ctx, wave, kind, quota), payload, arcs_doc))
    extra = []
    for n, (seq, r) in enumerate(zip([s for _, s in routes], stored["routes"])):
        recomputed = {"cost": cert.tour_cost(wave, seq), "ride": wg._ride_minutes(wave, seq), "tour": cert.tour_cost(wave, seq)}
        for field, value in recomputed.items():
            if r.get(field) != value:
                extra.append({"type": f"stored_{field}_mismatch", "route_index": n, "stored": r.get(field), "recomputed": value})
    if extra:
        result["violations"] = list(result.get("violations") or []) + extra
        result["violation_count"] = int(result.get("violation_count") or 0) + len(extra)
        result["is_feasible"] = False
    return result


# ---------------------------------------------------------------- replay (part 1) and CSV
def replay_rows(ctx: FleetContext) -> list:
    return replay.replay_fleet(ctx.replay_fleet)


def _replay_csv_row(r: dict) -> dict:
    diffs = (r["request_diffs"] or []) + (r["response_diffs"] or [])
    return {"fleet": r["fleet"], "date": r["date"], "R": r["R"], "L": r["L"], "label": r["label"],
            "archived_status": r["archived_status"], "replay_status": r["replay_status"],
            "request_diff_count": len(r["request_diffs"]), "response_diff_count": len(r["response_diffs"]),
            "first_difference": diffs[0] if diffs else "", "diagnostics_equal": r["diagnostics_equal"],
            "seed_workers_equal": r["seed_workers_equal"], "solver_version": r["solver_version"],
            "replay_seconds": r["replay_seconds"], "router_checks": r["router_checks"],
            "archived_http_status": r["http_status"]}


def write_replay_csv(path, rows) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(REPLAY_CSV_FIELDS), lineterminator="\n", extrasaction="raise")
        wr.writeheader()
        wr.writerows(_replay_csv_row(r) for r in rows)


def write_option_csv(path, rows) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(OPTION_CSV_FIELDS), lineterminator="\n", extrasaction="raise")
        wr.writeheader()
        wr.writerows(rows)


# ---------------------------------------------------------------- run
def _provenance() -> dict:
    """Repo-relative files of the packages that were imported (they must come from this checkout)."""
    import academic_benchmark
    import optimizer_api
    import uniride_core

    out = {}
    for name, mod in (("uniride_core", uniride_core), ("optimizer_api", optimizer_api), ("academic_benchmark", academic_benchmark)):
        try:
            out[name] = Path(mod.__file__).resolve().relative_to(REPO).as_posix()
        except ValueError as exc:
            raise RuntimeError(f"{name} is imported from outside this checkout ({exc}); set PYTHONPATH to the repo root") from exc
    return out


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--fleets", default=",".join(SOURCES), help="comma list (default: both typed fleets)")
    ap.add_argument("--rides", default="", help="comma list of R values (default: all of the campaign)")
    ap.add_argument("--wave-ids", default="", help="comma list of wave ids (default: all waves)")
    ap.add_argument("--limit", type=int, default=0, help="first N waves per R (default: all)")
    ap.add_argument("--jobs", type=int, default=1,
                    help="worker processes, one unit of work = (fleet, R, date); results are merged in a fixed order")
    ap.add_argument("--cache-dir", default="",
                    help="per-unit result cache (default: a folder in the system temp dir named after the commit); a "
                         "finished unit is never solved again, so an interrupted run resumes")
    ap.add_argument("--unit-timeout", type=float, default=7200.0,
                    help="wall seconds after which a stuck unit worker is killed and retried once (jobs > 1)")
    ap.add_argument("--worker-unit", default="", help=argparse.SUPPRESS)
    ap.add_argument("--worker-peaks", default="", help=argparse.SUPPRESS)
    ap.add_argument("--worker-out", default="", help=argparse.SUPPRESS)
    ap.add_argument("--highs-verify", action=argparse.BooleanOptionalAction, default=True,
                    help="re-solve every Gurobi-optimal option with HiGHS (default: on)")
    return ap.parse_args(argv)


def _worker_main(args) -> int:
    """One (fleet, R, date) unit in its own process; the result goes to a JSON file (atomic rename)."""
    unit = tuple(json.loads(args.worker_unit))
    unit = (unit[0], unit[1], unit[2], tuple(unit[3]))
    res = _solve_unit(unit, bool(args.highs_verify), set(json.loads(args.worker_peaks)))
    if res.get("unavailable"):
        print(f"backend unavailable: {res['unavailable']}", file=sys.stderr)
        return 3
    tmp = Path(args.worker_out + ".tmp")
    tmp.write_text(json.dumps(res, sort_keys=True), encoding="utf-8")
    tmp.replace(args.worker_out)
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.worker_unit:
        return _worker_main(args)
    out = Path(args.out)
    names = [n for n in args.fleets.split(",") if n]
    unknown = [n for n in names if n not in SOURCES]
    if unknown:
        print(f"refused: unknown fleet(s) {unknown}; valid: {sorted(SOURCES)}", file=sys.stderr)
        return 2
    for n in names:
        refusal = wg.check_out_dir(out, SOURCES[n])
        if refusal:
            print(f"refused: {refusal}", file=sys.stderr)
            return 2
    gurobi_settings, highs_settings = ab.SolverSettings(solver="gurobi"), ab.SolverSettings(solver="highs")
    gurobi = ab.AmplSession(gurobi_settings)
    highs = ab.AmplSession(highs_settings) if args.highs_verify else None
    sessions = [s for s in (gurobi, highs) if s is not None]
    try:
        for s in sessions:
            try:
                s.open()
            except ab.ExactBackendUnavailable as exc:
                print(f"backend unavailable ({s.settings.solver}): {exc}; GOAL 1 needs AMPL with a Gurobi licence"
                      + (" and HiGHS" if args.highs_verify else ""), file=sys.stderr)
                return 3
        return _run(args, names, out, gurobi, highs, gurobi_settings, highs_settings)
    finally:
        for s in sessions:
            s.close()


def _run(args, names, out, gurobi, highs, gurobi_settings, highs_settings) -> int:
    try:
        provenance = _provenance()
        ctxs = [load_fleet_context(SOURCES[n]) for n in names]
        peaks = loader.peak_waves({c.name: c.campaign for c in ctxs})
    except (loader.CampaignRefused, loader.InputRejected, KeyError, OSError, ValueError, RuntimeError) as exc:
        print(f"input_rejected: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    peak_ids = {i for v in peaks.values() for i in v["wave_ids"]}
    commit, dirty = wg._git_state(out)
    want = {w for w in args.wave_ids.split(",") if w}
    rides_filter = [int(r) for r in args.rides.split(",") if r]
    t_start = time.perf_counter()

    # ---- part 1: replay acceptance (a gate)
    replay_all: list = []
    for ctx in ctxs:
        replay_all.extend(replay_rows(ctx))
    failed = [r for r in replay_all if r["label"] not in replay.MATCH_LABELS]
    print(f"replay: {len(replay_all) - len(failed)}/{len(replay_all)} cells reproduced", flush=True)
    if failed:
        out.mkdir(parents=True, exist_ok=True)
        write_replay_csv(out / "replay.csv", replay_all)
        print(f"replay acceptance FAILED in {len(failed)} cell(s); nothing else is solved:", file=sys.stderr)
        for r in failed[:50]:
            print(f"  {r['fleet']} {r['date']} R{r['R']} L{r['L']} {r['label']}: "
                  f"{(r['request_diffs'] + r['response_diffs'])[:3]}", file=sys.stderr)
        return 4

    rows, option_docs, errors, route_docs = [], [], [], []
    matrix_sha, slice_sha = {}, {}
    caps_fired = 0
    source_docs: dict = {}
    units: list = []
    for ctx in ctxs:
        mpath = ctx.path / "run_manifest.json"
        source_docs[ctx.name] = {
            "path": wg._rel(ctx.path), "manifest_sha256": hashlib.sha256(mpath.read_bytes()).hexdigest(),
            "git_commit": str(ctx.manifest["git_commit"]), "dirty_working_tree": bool(ctx.manifest["dirty_working_tree"]),
            "termination_protocol": ctx.ga_labels["ga_protocol"], "effective_seed": ctx.ga_labels["ga_seed"],
            "fixed_type": ctx.fixed.type_id, "minimize_type": ctx.minimise.type_id,
            "selection_solver": ctx.manifest["selection_solver"]}
        for ride in rides_filter or list(ctx.campaign.rides):
            waves = [w for w in ctx.campaign.waves_for(ride) if not want or w.wave_id in want]
            if args.limit:
                waves = waves[: args.limit]
            for date in sorted({w.service_date for w in waves}):
                units.append((ctx.name, ride, date, tuple(w.wave_id for w in waves if w.service_date == date)))
    results = _solve_units(units, args, peak_ids, gurobi, highs, commit)
    for res in results:
        if res.get("unavailable"):
            print(f"backend unavailable: {res['unavailable']}", file=sys.stderr)
            return 3
        rows.extend(res["rows"])
        option_docs.extend(res["option_docs"])
        errors.extend(res["errors"])
        route_docs.extend(res["route_docs"])
        matrix_sha.update(res["matrix_sha"])
        slice_sha.update(res["slice_sha"])
        caps_fired += res["caps_fired"]

    routes_doc = {"protocol": protocol.PROTOCOL_ID, "schema_version": 1, "work_package": "WP-E4a", "git_commit": commit,
                  "note": "exact option routes per (fleet, wave, option) with the vehicle type of every route (occurrence ids "
                          "in stop order, integer minutes); re-certifiable without a solver through "
                          "scripts/run_exact_typed_menus.py recertify_stored_option",
                  "waves": route_docs}
    routes_text = json.dumps(routes_doc, indent=1, sort_keys=True) + "\n"
    errors.extend(f"exact_routes: {e}" for e in protocol.private_data_errors(routes_doc))

    manifest = {
        "protocol": protocol.PROTOCOL_ID, "schema_version": protocol.MANIFEST_SCHEMA_VERSION,
        "work_package": "WP-E4a", "fleets": names, "git_commit": commit, "dirty_working_tree": dirty,
        "source_campaigns": source_docs, "ga_labels": {c.name: c.ga_labels for c in ctxs},
        "matrix_sha256": matrix_sha, "matrix_slice_sha256": slice_sha, "peak_waves": peaks,
        "ampl": {"version": gurobi.ampl_version, "amplpy_version": gurobi.amplpy_version, "location": gurobi.location},
        "solver": wg._solver_block(gurobi, gurobi_settings),
        "verification_solver": None if highs is None else wg._solver_block(highs, highs_settings),
        "enumeration": dict(protocol.ENUMERATION_CAPS, count_caps_fired=caps_fired),
        "waves": option_docs,
        "replay": {"cells": len(replay_all), "reproduced": len(replay_all) - len(failed), "labels": _count(replay_all, "label"),
                   "cpsat_version": replay_all[0]["solver_version"] if replay_all else None, "file": "replay.csv"},
        "python_provenance": provenance,
        "exact_routes": {"file": EXACT_ROUTES_FILENAME, "sha256": hashlib.sha256(routes_text.encode("utf-8")).hexdigest(),
                         "options": len(route_docs)},
        "options": {"highs_verify": bool(highs), "rides": rides_filter, "wave_ids": sorted(want), "limit": args.limit,
                    "fleets": names, "jobs": args.jobs},
        "total_wall_seconds": round(time.perf_counter() - t_start, 1),
        "blocking_errors": errors,
        "python_version": platform.python_version(), "host_os": ab.host_description(),
    }
    problems = protocol.validate_manifest(manifest)
    if problems:
        errors.extend(f"manifest: {p}" for p in problems)
        manifest["blocking_errors"] = errors
    out.mkdir(parents=True, exist_ok=True)
    (out / protocol.MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / EXACT_ROUTES_FILENAME).write_bytes(routes_text.encode("utf-8"))
    write_option_csv(out / "option_gaps.csv", rows)
    write_replay_csv(out / "replay.csv", replay_all)
    summary = summarise(rows, replay_all)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["replay"], sort_keys=True))
    if errors:
        print(f"{len(errors)} blocking error(s):", file=sys.stderr)
        for e in errors[:50]:
            print(f"  {e}", file=sys.stderr)
    return 1 if errors else 0


_WORKER: dict = {}


def _ctx_cached(name: str) -> FleetContext:
    key = ("ctx", name)
    if key not in _WORKER:
        _WORKER[key] = load_fleet_context(SOURCES[name])
    return _WORKER[key]


def _worker_sessions(highs_verify: bool):
    """Per-process AMPL sessions (opened once, closed at exit); raises ExactBackendUnavailable."""
    import atexit

    if "sessions" not in _WORKER:
        sessions = [ab.AmplSession(ab.SolverSettings(solver="gurobi"))]
        if highs_verify:
            sessions.append(ab.AmplSession(ab.SolverSettings(solver="highs")))
        for sess in sessions:
            sess.open()
            atexit.register(sess.close)
        _WORKER["sessions"] = (sessions[0], sessions[1] if highs_verify else None)
    return _WORKER["sessions"]


def _solve_unit(unit, highs_verify: bool, peak_ids, sessions=None) -> dict:
    """All options of the waves of one (fleet, R, date); self-contained so it can run in a worker process."""
    fleet, ride, date, wave_ids = unit
    out = {"rows": [], "option_docs": [], "errors": [], "route_docs": [], "matrix_sha": {}, "slice_sha": {}, "caps_fired": 0}
    try:
        gurobi, highs = sessions if sessions is not None else _worker_sessions(highs_verify)
    except ab.ExactBackendUnavailable as exc:
        return {**out, "unavailable": str(exc)}
    ctx = _ctx_cached(fleet)
    arcs_doc = json.loads((ctx.path / f"{date}_R{ride}.matrix.json").read_text(encoding="utf-8"))
    menu_doc = json.loads((ctx.path / f"{date}_R{ride}.menu_options.json").read_text(encoding="utf-8"))
    by_id = {w.wave_id: w for w in ctx.campaign.waves_for(ride)}
    for wave_id in wave_ids:
        wave = by_id[wave_id]
        out["matrix_sha"][f"{date}_R{ride}"] = wave.declared_snapshot_sha256
        out["slice_sha"][f"{date}_R{ride}"] = wave.arc_slice_sha256
        peak = wave.wave_id in peak_ids
        enums: dict = {}

        def enum_for(kind):
            if kind not in enums:
                t0 = time.perf_counter()
                enum = enumerate_wave(wave, [ctx.fixed] if kind == "base" else [ctx.fixed, ctx.minimise])
                out["caps_fired"] += enum.status == "count_cap"
                enums[kind] = (enum, {"model": enum.model, "columns": enum.column_count, "labels": enum.label_count,
                                      "seconds": time.perf_counter() - t0, "cap_fired": enum.cap_fired})
            return enums[kind]

        for option_id, kind, quota in option_plan(ctx, wave):
            ga_opt = ga_option(menu_doc, wave.wave_id, option_id)
            kw = {} if kind == "base" else dict(minimize_type=ctx.minimise.type_id, quota=(ctx.fixed.type_id, quota))
            enum, info = enum_for(kind)
            if kind == "base" and xbase_guard(ctx.fixed):
                sp = ab.SPSolveResult(wave.wave_id, "not_run", peak=peak)
            else:
                sp = ab.solve_wave(wave, enum, peak=peak, session=gurobi, **kw)
            if sp.status == "backend_unavailable":
                return {**out, "unavailable": f"{wave.wave_id} {option_id}: {sp.note}"}
            h_sp = None
            if highs is not None and sp.status in ("optimal", "infeasible_proven"):
                h_sp = ab.solve_wave(wave, enum, peak=peak, session=highs, d_lb_free=True, **kw)
                if h_sp.status == "backend_unavailable":
                    return {**out, "unavailable": f"{wave.wave_id} {option_id} (HiGHS): {h_sp.note}"}
            ev = evaluate_option(wave, kind, quota, ga_opt, arcs_doc, sp, ctx=ctx, enum_info=info, highs=h_sp, peak=peak)
            row = ev["row"]
            out["rows"].append(row)
            out["errors"].extend(ev["errors"])
            out["option_docs"].append({"fleet": ctx.name, "option": option_id, "kind": kind, "quota": quota,
                                       "wave_id": wave.wave_id, "service_date": wave.service_date, "R": ride, "peak": peak,
                                       "model": info["model"], "columns": info["columns"], "labels": info["labels"],
                                       "cap_fired": info["cap_fired"], "stages": ev["stages"],
                                       "highs_stages": ev["highs_stages"], "result": row})
            if ev["exact_routes"] is not None:
                out["route_docs"].append(ev["exact_routes"])
            print(f"{ctx.name} R{ride} {wave.wave_id} {option_id} legs={wave.legs} cols={info['columns']} {row['status']} "
                  f"{row['k_kind']}_GA={row['K_GA']} {row['k_kind']}*={row['K_star']} D_GA={row['D_GA']} "
                  f"D*={row['D_star']} dK={row['dK']} {row['comparison']} t={row['solve_seconds']:.2f}s "
                  f"highs={row['highs_agrees']}/{row['highs_free_agrees']}", flush=True)
    return out


def _cache_path(args, commit: str, unit) -> Path:
    base = Path(args.cache_dir) if args.cache_dir else Path(tempfile.gettempdir()) / f"uniride_wp_e4a_cache_{commit[:12]}"
    base.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps([list(unit[:3]), list(unit[3]), bool(args.highs_verify)]).encode("utf-8")).hexdigest()[:10]
    return base / f"{unit[0].replace('+', '_')}_R{unit[1]}_{unit[2]}_{key}.json"


def _run_worker(unit, args, peak_ids, path: Path) -> dict:
    """Solve one unit in a subprocess with a wall limit; a stuck worker is killed (with its AMPL children) and retried once."""
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker-unit", json.dumps([unit[0], unit[1], unit[2], list(unit[3])]),
           "--worker-peaks", json.dumps(sorted(peak_ids)), "--worker-out", str(path),
           "--highs-verify" if args.highs_verify else "--no-highs-verify"]
    last = "unit worker failed"
    for attempt in (1, 2):
        proc = subprocess.Popen(cmd)
        try:
            code = proc.wait(timeout=args.unit_timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True) if os.name == "nt" else proc.kill()
            proc.wait()
            last = f"unit worker exceeded {args.unit_timeout:.0f} s (attempt {attempt})"
            print(f"{last}: {unit[:3]}", file=sys.stderr, flush=True)
            continue
        if code == 3:
            return {"unavailable": f"unit {unit[:3]}: AMPL backend unavailable"}
        if code == 0 and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        last = f"unit worker exited with code {code} (attempt {attempt})"
    return {"unavailable": None, "failed": f"unit {unit[:3]}: {last}", "rows": [], "option_docs": [], "errors": [f"unit {unit[:3]}: {last}"],
            "route_docs": [], "matrix_sha": {}, "slice_sha": {}, "caps_fired": 0}


def _solve_units(units, args, peak_ids, gurobi, highs, commit: str = "nocommit") -> list:
    """Results of every unit in the order of ``units`` (independent of the number of worker processes).

    Every finished unit is cached on disk (``--cache-dir``); a cached unit is read, never solved again.
    """
    paths = [_cache_path(args, commit, u) for u in units]
    results: list = [json.loads(p.read_text(encoding="utf-8")) if p.exists() else None for p in paths]
    todo = [i for i, r in enumerate(results) if r is None]
    if not todo:
        return results
    if args.jobs <= 1 or len(todo) <= 1:
        for i in todo:
            results[i] = _solve_unit(units[i], bool(highs), peak_ids, sessions=(gurobi, highs))
            if not results[i].get("unavailable"):
                paths[i].write_text(json.dumps(results[i], sort_keys=True), encoding="utf-8")
        return results
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(args.jobs, len(todo))) as pool:
        futures = {i: pool.submit(_run_worker, units[i], args, peak_ids, paths[i]) for i in todo}
        for i, f in futures.items():
            results[i] = f.result()
    return results


def _count(items, key) -> dict:
    out: dict = {}
    for it in items:
        out[str(it[key])] = out.get(str(it[key]), 0) + 1
    return out


def summarise(rows, replay_rows_=()) -> dict:
    per: dict = {}
    for r in rows:
        p = per.setdefault(f"{r['fleet']}|R{r['R']}|{r['kind']}", {
            "options": 0, "statuses": {}, "comparison": {}, "stage_stop_reasons": {}, "dK_zero": 0, "dK_positive": 0,
            "dK_unavailable": 0, "timing_dependent_rows": 0, "non_lexicographic_rows": 0, "highs_agrees": 0,
            "highs_disagrees": 0, "highs_not_proven_or_not_run": 0, "exact_le_ga_true": 0, "exact_le_ga_false": 0,
            "gD_comparable": 0, "gD_not_comparable": 0, "gD_positive": 0, "gD_max": None, "ga_certificates_agree": 0,
            "ga_certificates_disagree": 0, "solve_seconds": 0.0, "highs_seconds": 0.0})
        p["options"] += 1
        p["statuses"][r["status"]] = p["statuses"].get(r["status"], 0) + 1
        p["comparison"][r["comparison"]] = p["comparison"].get(r["comparison"], 0) + 1
        for s in ("stage1", "stage2", "free"):
            reason = r[f"{s}_stop_reason"]
            if reason is not None:
                p["stage_stop_reasons"][reason] = p["stage_stop_reasons"].get(reason, 0) + 1
        if r["dK"] is None:
            p["dK_unavailable"] += 1
        else:
            p["dK_zero" if r["dK"] == 0 else "dK_positive"] += 1
        p["timing_dependent_rows"] += any(r[f"{s}_timing_dependent"] for s in ("stage1", "stage2", "free"))
        p["non_lexicographic_rows"] += bool(r["stage2_non_lexicographic"])
        key = {True: "highs_agrees", False: "highs_disagrees"}.get(r["highs_agrees"], "highs_not_proven_or_not_run")
        p[key] += 1
        if r["exact_le_ga"] is True:
            p["exact_le_ga_true"] += 1
        elif r["exact_le_ga"] is False:
            p["exact_le_ga_false"] += 1
        if r["gD_note"] == "comparable":
            p["gD_comparable"] += 1
            if r["gD"]:
                p["gD_positive"] += 1
                p["gD_max"] = max(p["gD_max"] or 0, r["gD"])
        elif r["gD_note"] == gaps.NOT_COMPARABLE:
            p["gD_not_comparable"] += 1
        if r["ga_cert_agree"] is True:
            p["ga_certificates_agree"] += 1
        elif r["ga_cert_agree"] is False:
            p["ga_certificates_disagree"] += 1
        p["solve_seconds"] = round(p["solve_seconds"] + (r["solve_seconds"] or 0.0), 2)
        p["highs_seconds"] = round(p["highs_seconds"] + (r["highs_seconds"] or 0.0), 2)
    rep: dict = {}
    for r in replay_rows_:
        p = rep.setdefault(r["fleet"], {"cells": 0, "labels": {}, "statuses": {}})
        p["cells"] += 1
        p["labels"][r["label"]] = p["labels"].get(r["label"], 0) + 1
        p["statuses"][str(r["replay_status"])] = p["statuses"].get(str(r["replay_status"]), 0) + 1
    return {"purpose": "WP-E4a typed option gaps: descriptive gap measurement of one seed-42 native GA run, no superiority claim",
            "options": len(rows), "per_fleet_R_kind": per, "replay": rep}


if __name__ == "__main__":
    sys.exit(main())
