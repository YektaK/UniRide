#!/usr/bin/env python3
"""WP-E11 J11: comparison and reproduction files of the joint day campaign (design docs/designs/JOINT_DAY_MODEL_DESIGN.md
sections 5.3, 6.1 and 6.3; DECISION_LOG E13/E14 and the J9b/J9c notes of 2026-10-21).

OFFLINE, read only. Inputs (all committed):

* the J11 runner output (``day_joint.csv``, ``day_joint_stages.csv``, ``day_joint_week.csv``), never edited;
* WP-E4b union-day results ``wp-e4b-union-day/day_gaps.csv`` (GA-menu and union-menu cars of the typed cells);
* the archived GA routes of the single-type week (``week-2026-10-05-4sw5so/<date>_R<R>_repeat1.response.json`` with
  its matrix slice) and the WP-E3 exact routes (``wp-e3-goal1-single/exact_routes.json``): their day peaks are
  recomputed by the independent checker ``academic_benchmark/validation/day_plan.py`` (design 5.1);
* the prototype values of the Claude Science comparison (design 6.3): ``docs/science_review/2026-10-19_cs_cc_karsilastirma/``
  ``cs_cc_gun_homojen_4sw5so_20.csv`` and ``cs_cc_gun_tipli_large_sedan_60.csv``. The prototype plans are not in the
  repository, so the checker is never run on them (``prototype_plan_checked = not_run``): an unchecked prototype plan
  can never raise the disagreement defect of design 6.3 and is reported with ``prototype_plan_not_verified``.

Outputs, next to the J11 files: ``comparison.csv`` (descriptive, one row per cell, never ``min(...)``) and
``reproduction_check.csv`` (one row per cell, 140: the 20 single-type and 60 large+sedan cells carry a prototype target;
the 60 large+Doblo cap3 cells have no external reproduction target, E14 Q1, and get the category ``no_external_target``).

Proof gate (J9c note): a cell counts as proven only with a proof label AND ``proof_claim_allowed == True``. An unclaimed
value is compared with no proven prefix (it can never raise a defect); an unclaimed infeasibility is open.

Blocking checks of design 5.3 (each failure is reported and makes the exit code 1; nothing is tuned away):
``value_below_valid_bound`` (K or S below LB0, LB0w, LB_S, the bound used or a solver's stage-1 bound; the large peak
below LB_L), ``joint_above_union_menu`` (a proven joint value above, or a proven joint infeasibility against, a proven
WP-E4b union-menu result), ``joint_above_archived_peak`` (a proven joint K above the peak of the GA or WP-E3 routes),
``plan_checker_failed`` (a plan the runner's checker did not pass), and the disagreement rule of design 6.3.

Run: PYTHONPATH=<repo root> python scripts/report_exact_day_joint.py [--tables]
Exit codes: 0 ok; 1 a blocking defect (files are still written); 2 refused arguments.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import importlib.util
import json
import sys
from pathlib import Path
from typing import Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from academic_benchmark.exact_reference import day_compare as dc  # noqa: E402
from academic_benchmark.validation import day_plan as checker  # noqa: E402

RESULTS = REPO / "docs" / "paper" / "results"
DEFAULT_J11 = RESULTS / "week-2026-10-05-exact" / "wp-e11-joint-day"
DEFAULT_PROTOTYPE_DIR = REPO / "docs" / "science_review" / "2026-10-19_cs_cc_karsilastirma"
PROTOTYPE_HOMOGENEOUS = "cs_cc_gun_homojen_4sw5so_20.csv"
PROTOTYPE_TYPED = "cs_cc_gun_tipli_large_sedan_60.csv"
E4B_DAY_GAPS = Path("week-2026-10-05-exact") / "wp-e4b-union-day" / "day_gaps.csv"
E3_ROUTES = Path("week-2026-10-05-exact") / "wp-e3-goal1-single" / "exact_routes.json"
GA_SINGLE = Path("week-2026-10-05-4sw5so")
HOMOGENEOUS = "single_4sw5so"
PROTOTYPE_FLEETS = (HOMOGENEOUS, "large+sedan")  # E14 Q1: Doblo cap3 has no external reproduction target
RAW_FILES = ("day_joint_manifest.json", "day_joint.csv", "day_joint_stages.csv", "day_joint_plans.json", "day_joint_week.csv",
             "lb0.csv")
OUT_FILES = ("comparison.csv", "reproduction_check.csv")

PROOF_LABELS = ("optimal", "optimal_stage1_by_bound", "infeasible_certified", "infeasible_solver_proven")
VALUE_LABELS = ("optimal", "optimal_stage1_by_bound", "feasible_with_gap")
INFEASIBLE_LABELS = ("infeasible_certified", "infeasible_solver_proven")
UNION_PROVEN_LABELS = ("proven_over_union_menu", "ga_menu_infeasible_for_L")
BLOCKING_CHECKER_FAILED = "plan_checker_failed"
NOTE_NEEDS_PROTOTYPE_PLAN_CHECK = "prototype_value_vs_production_infeasible_needs_checker_on_prototype_plan"

COMPARISON_FIELDS = (
    "fleet", "date", "R", "L", "day_status", "proof_claim_allowed", "joint_K_or_S", "joint_large_peak", "joint_total_minutes",
    "joint_car_minutes", "lb0", "lb0w", "lb_L", "lb_S", "e4b_ga_status", "e4b_ga_cars", "e4b_union_status", "e4b_union_cars",
    "e4b_label", "joint_minus_union_cars", "ga_archive_peak", "ga_archive_minutes", "ga_archive_checker_violations",
    "wp_e3_peak", "wp_e3_minutes", "wp_e3_checker_violations", "check_bounds", "check_checker", "check_union",
    "check_peaks", "blocking_defects",
)
REPRODUCTION_FIELDS = (
    "fleet", "date", "R", "L", "prototype_status", "prototype_value", "prototype_minutes", "prototype_plan_checked",
    "production_status", "proof_claim_allowed", "production_value", "production_minutes", "components_compared",
    "category", "fleet_category", "note",
)
_CHECK_CODES = {"check_bounds": dc.BLOCKING_VALUE_BELOW_BOUND, "check_checker": BLOCKING_CHECKER_FAILED,
                "check_union": dc.BLOCKING_JOINT_ABOVE_UNION, "check_peaks": dc.BLOCKING_JOINT_ABOVE_PEAK}


# ---------------------------------------------------------------- small helpers
def to_int(text) -> Optional[int]:
    """An integer cell value, ``None`` for an empty cell; a non-integral number is refused."""
    if text is None or str(text).strip() == "":
        return None
    value = float(text)
    if value != int(value):
        raise ValueError(f"not an integer value: {text!r}")
    return int(value)


def key(row: Mapping) -> tuple:
    return (row["fleet"], row["date"], str(row["R"]), str(row.get("L") or ""))


def is_claimed(row: Mapping) -> bool:
    """Proven only with a proof label and ``proof_claim_allowed`` True (J9c note: ``optimal`` alone is not a proof)."""
    return str(row.get("proof_claim_allowed")) == "True" and row.get("day_status") in PROOF_LABELS


def _unverified(row: Mapping) -> set:
    text = str(row.get("unverified_bounds") or "")
    return {p.strip().lower() for p in text.replace(",", ";").split(";") if p.strip()}


# ---------------------------------------------------------------- blocking checks (design 5.3)
def blocking_defects(row: Mapping, *, union_row: Optional[Mapping] = None, peaks: Optional[Mapping[str, int]] = None,
                     stage_rows: Sequence[Mapping] = ()) -> list:
    """``[(code, message)]`` of every blocking check of design 5.3 that fails for one J11 cell (empty = all hold)."""
    defects: list = []

    def run(fn, *args, **kw):
        try:
            fn(*args, **kw)
        except dc.BlockingDefect as exc:
            defects.append((exc.code, exc.message))

    claimed = is_claimed(row)
    value = to_int(row.get("K_or_S"))
    unverified = _unverified(row)
    if value is not None:
        bounds = {}
        for name in ("lb0", "lb0w", "lb_S"):
            b = to_int(row.get(name))
            if b is not None and name.lower() not in unverified:
                bounds[name] = b
        used = to_int(row.get("bound_used"))
        if used is not None and str(row.get("bound_source") or "").lower() not in unverified:
            bounds["bound_used"] = used
        for s in stage_rows:
            ceil = to_int(s.get("bound_ceil"))
            if str(s.get("stage")) == "1" and ceil is not None and s.get("status") not in ("rejected", "skipped", ""):
                bounds[f"{s['solver']}_stage1_bound"] = ceil
        run(dc.check_value_not_below_bounds, value, bounds)
        large_peak, lb_l = to_int(row.get("large_peak")), to_int(row.get("lb_L"))
        if large_peak is not None and lb_l is not None and "lb_l" not in unverified:
            run(dc.check_value_not_below_bounds, large_peak, {"lb_L": lb_l})
        if str(row.get("checker_ok")) != "True":
            defects.append((BLOCKING_CHECKER_FAILED, f"plan with value {value} did not pass the checker "
                                                     f"(checker_ok={row.get('checker_ok')!r})"))
    if union_row is not None:
        union_cars = to_int(union_row.get("union_cars"))
        union_proven = union_row.get("union_status") == "optimal" and union_cars is not None and \
            union_row.get("label") in UNION_PROVEN_LABELS
        if value is not None and union_proven:
            run(dc.check_joint_not_above_union, joint_cars=value, union_cars=union_cars, joint_proven=claimed,
                union_proven=True)
        elif value is None and union_proven and claimed and row.get("day_status") in INFEASIBLE_LABELS:
            defects.append((dc.BLOCKING_JOINT_ABOVE_UNION, f"joint {row['day_status']} while the union menu has a proven "
                                                            f"plan with {union_cars} cars"))
    if peaks and value is not None:
        run(dc.check_joint_k_not_above_peaks, value, peaks, joint_proven=claimed)
    return defects


# ---------------------------------------------------------------- prototype rows (design 6.3)
@dataclasses.dataclass(frozen=True)
class PrototypeInput:
    claim: dc.PrototypeClaim
    components: int  # leading objective values the prototype reports (1: fleet only, 2: fleet and total minutes)
    note: str = ""
    status: str = ""


def _minutes(text) -> Optional[int]:
    if text is None or str(text).strip() == "":
        return None
    return to_int(text)


def prototype_claim_homogeneous(row: Mapping) -> PrototypeInput:
    """``cs_kanit`` "joint MIP optimal": value (K, minutes); "seq plan = LB0 ...": K only (equal to LB0, no joint plan)."""
    proof = str(row.get("cs_kanit") or "")
    k = to_int(row.get("cs_ortak_K"))
    if proof == "joint MIP optimal":
        return PrototypeInput(dc.PrototypeClaim.value((k, _minutes(row.get("cs_ortak_dakika")))), 2, "", proof)
    if proof.startswith("seq plan = LB0"):
        return PrototypeInput(dc.PrototypeClaim.value((k,)), 1, "prototype K = LB0 by its sequential plan; no joint "
                              "MIP plan, minutes not compared", proof)
    raise ValueError(f"unknown prototype proof text {proof!r}")


def prototype_claim_typed(row: Mapping) -> PrototypeInput:
    """``cs_durum`` "infeasible", "ok..." (value S and, when present, total minutes) or "açık..." (open)."""
    status = str(row.get("cs_durum") or "").strip()
    if status == "infeasible":
        return PrototypeInput(dc.PrototypeClaim.infeasible(), 0, "", status)
    if status.startswith("ok"):
        s, minutes = to_int(row.get("cs_sedan")), _minutes(row.get("cs_dakika"))
        if minutes is None:
            return PrototypeInput(dc.PrototypeClaim.value((s,)), 1, "prototype reports no minutes", status)
        return PrototypeInput(dc.PrototypeClaim.value((s, minutes)), 2, "", status)
    if status.lower().startswith(("açık", "acik")):
        return PrototypeInput(dc.PrototypeClaim.open(), 0, "", status)
    raise ValueError(f"unknown prototype status {status!r}")


NO_TARGET_STATUS = dc.CATEGORY_NO_EXTERNAL_TARGET
NO_TARGET_INPUT = PrototypeInput(dc.PrototypeClaim.no_target(), 0, "", NO_TARGET_STATUS)  # fleets outside PROTOTYPE_FLEETS


def _production(row: Mapping):
    """(effective label, objective, proven prefix override). Unclaimed: a value with no proven prefix, else open."""
    status = row.get("day_status")
    value, minutes = to_int(row.get("K_or_S")), to_int(row.get("total_minutes"))
    objective = None if value is None else ((value,) if minutes is None else (value, minutes))
    if is_claimed(row):
        return status, objective, None
    if status in VALUE_LABELS and objective is not None:
        return status, objective, 0
    return "bound_only", None, None


def reproduction_row(row: Mapping, proto: PrototypeInput, stage_statuses: Optional[Sequence[str]] = None) -> dict:
    """One row of ``reproduction_check.csv``. Raises ``dc.BlockingDefect`` for the disagreement rule of design 6.3."""
    label, objective, prefix = _production(row)
    claim = proto.claim
    out = {"fleet": row["fleet"], "date": row["date"], "R": row["R"], "L": row.get("L") or "",
           "prototype_status": proto.status, "prototype_value": "", "prototype_minutes": "",
           "prototype_plan_checked": "not_run", "production_status": row.get("day_status"),
           "proof_claim_allowed": row.get("proof_claim_allowed"), "production_value": row.get("K_or_S", ""),
           "production_minutes": row.get("total_minutes", ""), "components_compared": "", "category": "",
           "fleet_category": "", "note": proto.note}
    if claim.kind == "value":
        out["prototype_value"] = claim.objective[0]
        out["prototype_minutes"] = claim.objective[1] if len(claim.objective) > 1 else ""
    if claim.kind == "no_target":
        out["category"] = out["fleet_category"] = dc.CATEGORY_NO_EXTERNAL_TARGET
    if row.get("day_status") == "rejected":
        out["note"] = "production_rejected"
        return out
    if claim.kind == "no_target":
        return out
    if claim.kind == "value" and label in INFEASIBLE_LABELS and claim.plan_checked is None:
        out["note"] = NOTE_NEEDS_PROTOTYPE_PLAN_CHECK  # design 6.3: the checker must run on that prototype plan
        return out
    kw = dict(production_label=label, production_objective=objective, production_proven_prefix=prefix,
              production_stage_statuses=stage_statuses if prefix is None else None)
    components = None
    if claim.kind == "value" and objective is not None:
        components = min(proto.components, len(objective))
        out["components_compared"] = components
    result = dc.reproduction_category(claim, components=components, **kw)
    out["category"] = result.category
    out["fleet_category"] = result.category
    if components and components > 1:
        out["fleet_category"] = dc.reproduction_category(claim, components=1, **kw).category
    notes = [n for n in (proto.note, result.note) if n]
    out["note"] = "; ".join(notes)
    return out


# ---------------------------------------------------------------- archived single-type route sets (design 5.3)
def _load_loader():
    name = "exact_archive_loader"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def archived_peaks(results_root: Path, e3_doc: Mapping, type_spec: checker.TypeSpec, depot: str, date: str, ride: int) -> dict:
    """Checker results of the archived GA routes and the WP-E3 routes of one single-type day (same waves and arcs)."""
    stem = results_root / GA_SINGLE / f"{date}_R{ride}_repeat1"
    kwargs = checker.plan_from_single_type_response(_read_json(Path(f"{stem}.response.json")),
                                                   _read_json(Path(f"{stem}.matrix.json")), type_spec=type_spec, depot=depot)
    out = {}
    ga = checker.check_day_plan(**kwargs)
    e3_routes = [checker.Route(w["wave_id"], type_spec.type_id, tuple(r["occurrence_ids"]), claimed_minutes=r["tour"])
                 for w in e3_doc["waves"] if w["service_date"] == date and int(w["R"]) == ride for r in w["routes"]]
    e3 = checker.check_day_plan(**dict(kwargs, routes=e3_routes))
    for name, rep in (("ga_archive", ga), ("wp_e3", e3)):
        peak_m, peak_c = rep.peaks_minutes.get(type_spec.type_id, 0), rep.peaks_centi.get(type_spec.type_id, 0)
        violations = len(rep.violations) + (0 if peak_m == peak_c else 1)
        out[name] = {"peak": peak_c, "minutes": rep.total_minutes, "violations": violations}
    return out


# ---------------------------------------------------------------- build
def read_csv(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@dataclasses.dataclass
class Built:
    comparison: list
    reproduction: list
    defects: list  # (fleet, date, R, L, code, message)
    joint: list
    stages: list
    week: list
    prototype_rows: dict


def build(j11_dir: Path, results_root: Path, prototype_dir: Path) -> Built:
    joint_rows = read_csv(j11_dir / "day_joint.csv")
    stage_rows = read_csv(j11_dir / "day_joint_stages.csv")
    week = read_csv(j11_dir / "day_joint_week.csv")
    stages_by = {}
    for s in stage_rows:
        stages_by.setdefault(key(s), []).append(s)
    union_by = {key(r): r for r in read_csv(results_root / E4B_DAY_GAPS)}
    proto_h = {(r["date"], r["R"]): r for r in read_csv(prototype_dir / PROTOTYPE_HOMOGENEOUS)}
    proto_t = {(r["date"], r["R"], r["L"]): r for r in read_csv(prototype_dir / PROTOTYPE_TYPED)}
    loader = _load_loader()
    campaign = loader.load_campaign(results_root / GA_SINGLE)
    (t,) = campaign.fleet_types
    type_spec = checker.TypeSpec(t.type_id, t.sw_capacity, t.so_capacity, t.cooldown_minutes, t.total_capacity,
                                 t.ride_limit_minutes, t.tour_limit_minutes)
    e3_doc = _read_json(results_root / E3_ROUTES)

    comparison, reproduction, defects = [], [], []
    for row in joint_rows:
        k = key(row)
        homogeneous = row["fleet"] == HOMOGENEOUS
        union_row = None if homogeneous else union_by.get(k)
        if not homogeneous and union_row is None:
            raise ValueError(f"no WP-E4b row for {k}")
        arch = archived_peaks(results_root, e3_doc, type_spec, loader.DEPOT, row["date"], int(row["R"])) if homogeneous else None
        peaks = {name: v["peak"] for name, v in arch.items()} if arch else None
        cell = blocking_defects(row, union_row=union_row, peaks=peaks, stage_rows=stages_by.get(k, ()))
        if arch:
            for name, v in arch.items():
                if v["violations"]:
                    cell.append((BLOCKING_CHECKER_FAILED, f"archived {name} routes fail the checker ({v['violations']})"))
        primary = [s["status"] for s in sorted(stages_by.get(k, ()), key=lambda s: int(s["stage"])) if s["solver"] == "highs"]
        if row["fleet"] in PROTOTYPE_FLEETS:
            proto = prototype_claim_homogeneous(proto_h[(row["date"], row["R"])]) if homogeneous else \
                prototype_claim_typed(proto_t[(row["date"], row["R"], row["L"])])
            try:
                reproduction.append(reproduction_row(row, proto, primary))
            except dc.BlockingDefect as exc:
                cell.append((exc.code, exc.message))
                reproduction.append(dict(reproduction_row(dict(row, proof_claim_allowed="False"), proto),
                                         category="", note=f"BLOCKING {exc.code}"))
        else:  # owner rule: every cell gets a reproduction row
            reproduction.append(reproduction_row(row, NO_TARGET_INPUT))
        value = to_int(row["K_or_S"])
        cmp_row = {"fleet": row["fleet"], "date": row["date"], "R": row["R"], "L": row["L"], "day_status": row["day_status"],
                   "proof_claim_allowed": row["proof_claim_allowed"], "joint_K_or_S": row["K_or_S"],
                   "joint_large_peak": row["large_peak"], "joint_total_minutes": row["total_minutes"],
                   "joint_car_minutes": row["car_minutes"], "lb0": row["lb0"], "lb0w": row["lb0w"], "lb_L": row["lb_L"],
                   "lb_S": row["lb_S"], "blocking_defects": ";".join(sorted({c for c, _ in cell}))}
        for f in COMPARISON_FIELDS:
            cmp_row.setdefault(f, "")
        if union_row is not None:
            uc = to_int(union_row["union_cars"])
            cmp_row.update(e4b_ga_status=union_row["ga_status"], e4b_ga_cars=union_row["ga_cars"],
                           e4b_union_status=union_row["union_status"], e4b_union_cars=union_row["union_cars"],
                           e4b_label=union_row["label"],
                           joint_minus_union_cars="" if value is None or uc is None else value - uc)
        if arch:
            cmp_row.update(ga_archive_peak=arch["ga_archive"]["peak"], ga_archive_minutes=arch["ga_archive"]["minutes"],
                           ga_archive_checker_violations=arch["ga_archive"]["violations"], wp_e3_peak=arch["wp_e3"]["peak"],
                           wp_e3_minutes=arch["wp_e3"]["minutes"], wp_e3_checker_violations=arch["wp_e3"]["violations"])
        union_ok = union_row is not None and union_row["union_status"] == "optimal" and union_row["label"] in UNION_PROVEN_LABELS
        applicable = {"check_bounds": value is not None, "check_checker": value is not None,
                      "check_union": union_ok and is_claimed(row), "check_peaks": bool(arch) and value is not None and is_claimed(row)}
        failed = {c for c, _ in cell}
        for col, code in _CHECK_CODES.items():
            cmp_row[col] = "fail" if code in failed else ("pass" if applicable[col] else "not_applicable")
        comparison.append(cmp_row)
        defects.extend((*k, c, m) for c, m in cell)
    return Built(comparison, reproduction, defects, joint_rows, stage_rows, week, {"homogeneous": proto_h, "typed": proto_t})


def write_csv(path: Path, fields, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- README tables
def _table(header, rows) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def _count(rows, fields) -> list:
    counts: dict = {}
    for r in rows:
        k = tuple(r[f] for f in fields)
        counts[k] = counts.get(k, 0) + 1
    return [(*k, n) for k, n in sorted(counts.items())]


def markdown_tables(b: Built) -> str:
    parts = []
    parts.append("### Cells and labels\n\n" + _table(("fleet", "day_status", "proof_claim_allowed", "cells"),
                                                       _count(b.joint, ("fleet", "day_status", "proof_claim_allowed"))))
    parts.append("### Proof claim reasons\n\n" + _table(("fleet", "proof_claim_reason", "cells"),
                                                         _count(b.joint, ("fleet", "proof_claim_reason"))))
    unclaimed = [r for r in b.joint if r["proof_claim_allowed"] != "True"]
    st_rows = [(s["solver"], s["stage"], s["status"], s["stop_reason"], s["objective"], s["bound"], s["solve_result"])
               for r in unclaimed for s in b.stages if key(s) == key(r)]
    parts.append("### Unclaimed cells\n\n" + _table(
        ("fleet", "date", "R", "L", "day_status", "K_or_S", "total_minutes", "car_minutes", "proof_claim_reason", "crosscheck_status"),
        [(r["fleet"], r["date"], r["R"], r["L"], r["day_status"], r["K_or_S"], r["total_minutes"], r["car_minutes"],
          r["proof_claim_reason"], r["crosscheck_status"]) for r in unclaimed]) + "\n\nStage rows of these cells:\n\n" +
        _table(("solver", "stage", "status", "stop_reason", "objective", "bound", "solve_result"), st_rows))
    check_rows = []
    for col in _CHECK_CODES:
        vals = [r[col] for r in b.comparison]
        check_rows.append((col, vals.count("pass"), vals.count("fail"), vals.count("not_applicable")))
    parts.append("### Blocking checks (design 5.3)\n\n" + _table(("check", "pass", "fail", "not_applicable"), check_rows) +
                 f"\n\nBlocking defects: {len(b.defects)}" +
                 "".join(f"\n- {d[0]} {d[1]} R{d[2]} L{d[3]}: {d[4]}: {d[5]}" for d in b.defects))
    parts.append("### Reproduction by category (objective tuple)\n\n" +
                 _table(("fleet", "category", "cells"), _count(b.reproduction, ("fleet", "category"))))
    parts.append("### Reproduction by category (fleet value only)\n\n" +
                 _table(("fleet", "fleet_category", "cells"), _count(b.reproduction, ("fleet", "fleet_category"))))
    hom = [r for r in b.comparison if r["fleet"] == HOMOGENEOUS]
    rep_by = {key(r): r for r in b.reproduction}
    parts.append("### Single type: joint K against archived route sets and the prototype\n\n" + _table(
        ("date", "R", "joint K", "LB0", "LB0w", "GA routes peak", "WP-E3 routes peak", "joint minutes", "GA minutes",
         "WP-E3 minutes", "prototype K", "prototype minutes", "category"),
        [(r["date"], r["R"], r["joint_K_or_S"], r["lb0"], r["lb0w"], r["ga_archive_peak"], r["wp_e3_peak"],
          r["joint_total_minutes"], r["ga_archive_minutes"], r["wp_e3_minutes"], rep_by[key(r)]["prototype_value"],
          rep_by[key(r)]["prototype_minutes"], rep_by[key(r)]["category"]) for r in sorted(hom, key=lambda r: (int(r["R"]), r["date"]))]))
    typed_rows = []
    for fleet in sorted({r["fleet"] for r in b.comparison if r["fleet"] != HOMOGENEOUS}):
        for limit in sorted({r["L"] for r in b.comparison if r["fleet"] == fleet}):
            cells = [r for r in b.comparison if r["fleet"] == fleet and r["L"] == limit]
            diff = [to_int(r["joint_minus_union_cars"]) for r in cells if r["joint_minus_union_cars"] != ""]
            typed_rows.append((fleet, limit, len(cells), sum(1 for d in diff if d < 0), sum(1 for d in diff if d == 0),
                               sum(1 for d in diff if d > 0),
                               sum(1 for r in cells if r["joint_K_or_S"] != "" and r["joint_minus_union_cars"] == ""),
                               sum(1 for r in cells if r["joint_K_or_S"] == "" and r["e4b_union_cars"] == ""),
                               sum(1 for r in cells if r["joint_K_or_S"] == "" and r["e4b_union_cars"] != "")))
    parts.append("### Typed fleets: joint cars against WP-E4b union-menu cars\n\n" + _table(
        ("fleet", "L", "cells", "joint < union", "joint = union", "joint > union", "joint value, union menu infeasible",
         "both infeasible", "joint infeasible, union value"), typed_rows))
    parts.append("### Weekly values (day_joint_week.csv)\n\n" + _table(
        ("fleet", "R", "L", "dates", "weekly_fleet_max", "vehicle_days_sum", "cells_not_proven", "cells_without_value"),
        [(w["fleet"], w["R"], w["L"], w["dates"], w["weekly_fleet_max"], w["vehicle_days_sum"], w["cells_not_proven"],
          w["cells_without_value"]) for w in b.week]))
    parts.append("### Design 6.3 targets, recomputed from both sides' files\n\n" + _table(
        ("target", "prototype", "production"), targets(b)))
    return "\n\n".join(parts) + "\n"


def targets(b: Built) -> list:
    """The design 6.3 targets, each side recomputed from its own file (prototype CSV, J11 day_joint.csv)."""
    ph = list(b.prototype_rows["homogeneous"].values())
    pt = list(b.prototype_rows["typed"].values())
    jh = [r for r in b.joint if r["fleet"] == HOMOGENEOUS]
    js = [r for r in b.joint if r["fleet"] == "large+sedan"]
    rides = sorted({int(r["R"]) for r in jh})
    weekly_p = "/".join(str(max(to_int(r["cs_ortak_K"]) for r in ph if int(r["R"]) == R)) for R in rides)
    weekly_q = "/".join(str(max(to_int(r["K_or_S"]) for r in jh if int(r["R"]) == R)) for R in rides)
    out = [("single type weekly fleet, R = " + "/".join(map(str, rides)), weekly_p, weekly_q),
           ("single type vehicle-days over 20 cells", sum(to_int(r["cs_ortak_K"]) for r in ph),
            sum(to_int(r["K_or_S"]) for r in jh))]
    fewer_p = sum(1 for r in pt if r["kategori"] == "CS daha az sedan")
    union_by = {(r["date"], r["R"], r["L"]): r for r in b.comparison if r["fleet"] == "large+sedan"}
    fewer_q = sum(1 for r in union_by.values() if r["joint_minus_union_cars"] != "" and to_int(r["joint_minus_union_cars"]) < 0)
    out.append(("large+sedan cells with fewer sedans than the union menu (of 60)", fewer_p, fewer_q))
    for date, ride in (("2026-10-06", "70"), ("2026-10-06", "90"), ("2026-10-05", "90")):
        p = b.prototype_rows["typed"][(date, ride, "2")]
        q = next(r for r in js if r["date"] == date and r["R"] == ride and r["L"] == "2")
        out.append((f"large+sedan {date} R = {ride}, L = 2", f"{p['cs_durum']} S={p['cs_sedan'] or '-'}",
                    f"{q['day_status']} S={q['K_or_S'] or '-'} (claim {q['proof_claim_allowed']})"))
    sed_p = "/".join(str(max((to_int(r["cs_sedan"]) for r in pt if int(r["R"]) == R and r["L"] == "3" and r["cs_sedan"]),
                             default="-")) for R in rides)
    sed_q = "/".join(str(max((to_int(r["K_or_S"]) for r in js if int(r["R"]) == R and r["L"] == "3" and r["K_or_S"]),
                             default="-")) for R in rides)
    out.append(("large+sedan weekly sedans at L = 3, R = " + "/".join(map(str, rides)), sed_p, sed_q))
    return out


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--j11-dir", default=str(DEFAULT_J11))
    ap.add_argument("--results-root", default=str(RESULTS))
    ap.add_argument("--prototype-dir", default=str(DEFAULT_PROTOTYPE_DIR))
    ap.add_argument("--out-dir", default="", help="where comparison.csv and reproduction_check.csv go (default: --j11-dir)")
    ap.add_argument("--tables", action="store_true", help="print the README tables (Markdown) to stdout")
    args = ap.parse_args(argv)
    j11 = Path(args.j11_dir)
    out = Path(args.out_dir) if args.out_dir else j11
    if not (j11 / "day_joint.csv").is_file():
        print(f"refused: no day_joint.csv in {j11}", file=sys.stderr)
        return 2
    built = build(j11, Path(args.results_root), Path(args.prototype_dir))
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "comparison.csv", COMPARISON_FIELDS, built.comparison)
    write_csv(out / "reproduction_check.csv", REPRODUCTION_FIELDS, built.reproduction)
    if args.tables:
        sys.stdout.write(markdown_tables(built))
    for d in built.defects:
        print("BLOCKING " + " ".join(str(x) for x in d), file=sys.stderr)
    return 1 if built.defects else 0


if __name__ == "__main__":
    raise SystemExit(main())
