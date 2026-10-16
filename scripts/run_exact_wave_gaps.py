#!/usr/bin/env python3
"""GOAL 1 runner (WP-E3): exact optimum / lower bounds of every archived wave and the gap of the GA.

Design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 1.2 (bounds and gaps), 2 (location and
rules), 3 (certification), 4 (labels, manifest, determinism), 6 (HiGHS verification), 8 (checks) and 9.
Single type 4 Sw / 5 So only; typed fleets are WP-E4.

Offline: reads the archive directory (default docs/paper/results/week-2026-10-05-4sw5so) through
scripts/exact_archive_loader.py and never the DB or HTTP. Per (R, wave) it enumerates (WP-E1),
solves the set-partitioning model with Gurobi (primary; WP-E2 backend), certifies the exact routes
with ``certify_optimization_response`` on the archived per-date matrix slice, re-certifies the
archived GA routes with the very same call, cross-checks K and D in integer arithmetic, checks
exact <= GA, and re-solves every Gurobi-``optimal`` wave with HiGHS (any difference in the proven
(K*, D*) is blocking). Writes exact_manifest.json, wave_gaps.csv and summary.json.

Wording rule (design section 9): a single snapshot week; descriptive gap measurement, not a
superiority claim; the GA is one seed-42 run under the native secondary protocol.

AMPL is located only through UNIRIDE_AMPL_DIR (or the local config / amplpy default); no path and no
solver log or license text is written.

Exit codes: 0 ok; 1 blocking error (results are still written); 2 archive refused/rejected;
3 AMPL backend unavailable (nothing is written).

Run: python scripts/run_exact_wave_gaps.py [--rides 50,60,70,90] [--out DIR] [--no-highs-verify]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
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
SOURCE = RESULTS / "week-2026-10-05-4sw5so"
DEFAULT_OUT = RESULTS / "week-2026-10-05-exact" / "wp-e3-goal1-single"
FLEET = "single_4sw5so"

WAVE_CSV_FIELDS = (
    "date", "R", "fleet", "wave_id", "direction", "anchor", "students", "peak", "model", "columns", "labels",
    "K_GA", "K_LB", "K_LB_source", "K_star", "D_GA", "D_LB", "D_star", "D_LB_free", "dK", "gD", "gD_note", "gD_free",
    "status", "note",
    "stage1_status", "stage1_stop_reason", "stage1_timing_dependent",
    "stage2_status", "stage2_stop_reason", "stage2_timing_dependent", "stage2_non_lexicographic",
    "free_status", "free_stop_reason", "free_timing_dependent",
    "solver", "solver_version", "enumeration_seconds", "solve_seconds",
    "exact_certified", "ga_recertified", "objective_check", "exact_le_ga",
    "highs_status", "highs_K", "highs_D", "highs_agrees", "highs_seconds",
    "ga_protocol", "ga_seed", "ga_commit", "ga_dirty_tree",
)


def _load_loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader", REPO / "scripts" / "exact_archive_loader.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader"] = mod
    spec.loader.exec_module(mod)
    return mod


loader = _load_loader()


# ---------------------------------------------------------------- certification (section 3)
def _violation_types(certificate: dict) -> str:
    kinds = sorted({v.get("type", "?") for v in certificate.get("violations") or []})
    if certificate.get("certify_error"):
        kinds.append("certify_error")
    return ",".join(kinds[:4]) or "unknown"


def certificate(request_payload: dict, response_payload: dict, arcs_doc: dict) -> dict:
    """``certify_optimization_response`` on the arcs of the archived per-date matrix slice (never raises)."""
    from models.schemas import OptimizationRequest, OptimizationResponse
    from verification.authoritative_arcs import arc_lookup_from_snapshot
    from verification.response_certifier import certify_optimization_response

    try:
        request = OptimizationRequest.model_validate(request_payload)
        response = OptimizationResponse.model_validate(response_payload)
    except Exception as exc:  # noqa: BLE001 - a payload the schema refuses is a failed certificate
        return {"is_feasible": False, "violation_count": 1, "violations": [{"type": "schema_error"}],
                "certify_error": type(exc).__name__}
    return certify_optimization_response(request, response, arc_lookup_from_snapshot(arcs_doc))


def ga_labels(source_manifest: dict) -> dict:
    """GA labels of the source campaign, read from its manifest (never hard-coded)."""
    return {"ga_protocol": source_manifest["termination_protocol"], "ga_seed": source_manifest["effective_seed"],
            "ga_commit": str(source_manifest["git_commit"])[:7], "ga_dirty_tree": bool(source_manifest["dirty_working_tree"])}


def stage_row(st) -> dict:
    return {"stage": st.stage, "status": st.status, "stop_reason": st.stop_reason, "timing_dependent": st.timing_dependent,
            "non_lexicographic": st.non_lexicographic, "objective": st.objective, "bound": st.bound,
            "wall_seconds": st.wall_seconds, "k_fix": st.k_fix, "bound_ceil": st.bound_ceil,
            "bound_source": st.bound_source, "work_units": st.work_units, "solve_result_num": st.solve_result_num}


def _stage_cols(prefix: str, st, row: dict, *, lex: bool = False) -> None:
    row[f"{prefix}_status"] = None if st is None else st.status
    row[f"{prefix}_stop_reason"] = None if st is None else st.stop_reason
    row[f"{prefix}_timing_dependent"] = None if st is None else st.timing_dependent
    if lex:
        row[f"{prefix}_non_lexicographic"] = None if st is None else st.non_lexicographic


def _seconds(sp) -> float:
    return round(sum(s.wall_seconds or 0.0 for s in (sp.stage1, sp.stage2, sp.free) if s is not None), 4)


def evaluate_wave(wave, ga_result, arcs_doc, sp, *, ga_labels, enum_info, highs=None, type_spec=None,
                  fleet: str = FLEET, peak=None) -> dict:
    """Certify, cross-check and compare one wave. Returns ``{"row", "stages", "errors"}``.

    ``sp`` is the Gurobi ``SPSolveResult``, ``highs`` the optional HiGHS re-solve, ``ga_result`` the
    archived GA result of the wave (``success``, ``routes``, ``total_duration_minutes``) or None.
    ``errors`` are blocking: a failed GA re-certificate, a rejected exact result, an exact result that
    violates exact <= GA or the proven bounds, a HiGHS disagreement.
    """
    tag = f"{wave.service_date} R{wave.max_ride_minutes} {wave.wave_id}"
    errors: list = []
    caps = {} if type_spec is None else dict(sw_capacity=type_spec.sw_capacity, so_capacity=type_spec.so_capacity,
                                              cooldown_minutes=type_spec.cooldown_minutes)
    request = cert.request_payload(wave, **caps)

    # ---- GA side: re-certified with the same call and the same arcs
    k_ga = d_ga = None
    ga_ok = None
    if ga_result is None:
        errors.append(f"{tag}: archived GA result missing")
    else:
        ga_cert = certificate(request, cert.ga_response_payload(wave, ga_result), arcs_doc)
        ga_ok = bool(ga_cert["is_feasible"])
        if not ga_ok:
            errors.append(f"{tag}: GA re-certificate failed ({_violation_types(ga_cert)})")
        seqs = [tuple(r["student_ids"]) for r in ga_result["routes"]]
        try:
            k_ga, d_ga = cert.recompute_objective(wave, seqs)
        except KeyError:
            k_ga = len(seqs)
        archived_total = ga_result.get("total_duration_minutes")
        if d_ga is not None and archived_total is not None and abs(float(archived_total) - d_ga) > 1e-6:
            errors.append(f"{tag}: archived GA total {archived_total} differs from the matrix recomputation {d_ga}")

    # ---- exact side: certificate, then objective cross-check; failure -> rejected, never repaired
    status, note = sp.status, sp.note
    exact_ok = None
    objective_check = "not_applicable"
    if sp.status == "rejected":
        errors.append(f"{tag}: exact solve rejected ({sp.note or 'solver failure'})")
    if sp.routes and sp.status in ("optimal", "feasible_with_gap"):
        seqs = [r.occurrence_ids for r in sp.routes]
        ec = certificate(request, cert.response_payload(wave, seqs), arcs_doc)
        exact_ok = bool(ec["is_feasible"])
        if not exact_ok:
            status, note = "rejected", f"exact certificate failed: {_violation_types(ec)}"
            errors.append(f"{tag}: exact certificate failed ({_violation_types(ec)})")
        else:
            k, d = cert.recompute_objective(wave, seqs)
            s1, s2 = sp.stage1, sp.stage2
            has_s2 = s2 is not None and s2.objective is not None
            solver_k = s2.k_fix if has_s2 else (None if s1 is None else s1.objective)
            solver_d = s2.objective if has_s2 else sp.d
            problems = (cert.objective_mismatches(k, d, solver_k, solver_d)
                        + cert.objective_mismatches(k, d, sp.k, sp.d))
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
    d_lb = sp.d_lb if k_lb is not None else None

    gap = {"dK": None, "gD": None, "gD_note": "unavailable_no_GA", "gD_free": None}
    exact_le_ga = None
    if k_ga is not None and d_ga is not None:
        gap = gaps.gap_fields(k_ga=k_ga, d_ga=d_ga, k_lb=k_lb, k_star=k_proven, d_lb=d_lb,
                              d_lb_free=sp.d_lb_free if k_lb is not None else None)
        for msg in gaps.exact_vs_ga_violations(exact_optimal=exact_optimal, k_star=k_proven, d_star=d_star, k_ga=k_ga,
                                               d_ga=d_ga, k_lb=k_lb, d_lb=d_lb):
            errors.append(f"{tag}: {msg}")
        if exact_optimal:
            exact_le_ga = (k_star, d_star) <= (k_ga, d_ga)

    # ---- HiGHS verification of a Gurobi-optimal result (section 6)
    h_status = h_k = h_d = h_agrees = h_secs = None
    if highs is not None and exact_optimal:
        h_status, h_k, h_d, h_secs = highs.status, highs.k, highs.d, _seconds(highs)
        if highs.status in ("optimal", "infeasible_proven"):
            h_agrees = (highs.status == "optimal" and (highs.k, highs.d) == (sp.k, sp.d))
            if not h_agrees:
                errors.append(f"{tag}: HiGHS ({highs.status}, K={highs.k}, D={highs.d}) differs from Gurobi "
                              f"(K={sp.k}, D={sp.d})")

    row = {
        "date": wave.service_date, "R": wave.max_ride_minutes, "fleet": fleet, "wave_id": wave.wave_id,
        "direction": wave.direction, "anchor": wave.anchor_minutes, "students": wave.legs,
        "peak": bool(sp.peak if peak is None else peak), "model": enum_info.get("model"),
        "columns": enum_info.get("columns"), "labels": enum_info.get("labels"),
        "K_GA": k_ga, "K_LB": k_lb, "K_LB_source": sp.k_lb_source if k_lb is not None else None, "K_star": k_star,
        "D_GA": d_ga, "D_LB": d_lb, "D_star": d_star, "D_LB_free": sp.d_lb_free if k_lb is not None else None,
        "dK": gap["dK"], "gD": None if gap["gD"] is None else round(gap["gD"], 6), "gD_note": gap["gD_note"],
        "gD_free": None if gap["gD_free"] is None else round(gap["gD_free"], 6),
        "status": status, "note": note or (f"cap fired: {enum_info['cap_fired']}" if enum_info.get("cap_fired") else ""),
        "solver": sp.solver or "gurobi", "solver_version": sp.solver_version,
        "enumeration_seconds": round(enum_info.get("seconds", 0.0), 4), "solve_seconds": _seconds(sp),
        "exact_certified": exact_ok, "ga_recertified": ga_ok, "objective_check": objective_check,
        "exact_le_ga": exact_le_ga, "highs_status": h_status, "highs_K": h_k, "highs_D": h_d, "highs_agrees": h_agrees,
        "highs_seconds": h_secs, **ga_labels,
    }
    _stage_cols("stage1", sp.stage1, row)
    _stage_cols("stage2", sp.stage2, row, lex=True)
    _stage_cols("free", sp.free, row)
    if status == "not_run" and not row["note"]:
        row["note"] = "not solved"
    stages = [stage_row(s) for s in (sp.stage1, sp.stage2, sp.free) if s is not None]
    return {"row": row, "stages": stages, "errors": errors}


def write_wave_csv(path, rows) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(WAVE_CSV_FIELDS), lineterminator="\n", extrasaction="raise")
        wr.writeheader()
        wr.writerows(rows)


# ---------------------------------------------------------------- run helpers
def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def _git_state(out: Path) -> tuple:
    """(full commit, dirty flag). The output directory itself is ignored when it lies inside the repo."""
    spec = ["status", "--porcelain"]
    try:
        spec += ["--", ".", f":(exclude){out.resolve().relative_to(REPO).as_posix()}"]
    except ValueError:
        pass
    return _git("rev-parse", "HEAD"), bool(_git(*spec))


def _rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return Path(path).name


def _solver_block(session, settings) -> dict:
    return {"name": settings.solver, "version": session.solver_version,
            "option_string": ab.solver_option_string(settings, peak=False),
            "peak_option_string": ab.solver_option_string(settings, peak=True), "threads": settings.threads,
            "seed": settings.seed, "time_limit_seconds": settings.wall_limit,
            "peak_time_limit_seconds": settings.peak_wall_limit, "work_limit": settings.work(False),
            "peak_work_limit": settings.work(True), "mip_gap": settings.mip_gap, "mip_gap_abs": settings.mip_gap_abs}


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", default=str(SOURCE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--rides", default="", help="comma list of R values (default: all of the campaign)")
    ap.add_argument("--wave-ids", default="", help="comma list of wave ids (default: all waves)")
    ap.add_argument("--limit", type=int, default=0, help="first N waves per R (default: all)")
    ap.add_argument("--highs-verify", action=argparse.BooleanOptionalAction, default=True,
                    help="re-solve every Gurobi-optimal wave with HiGHS (default: on)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    source, out = Path(args.source), Path(args.out)

    gurobi_settings = ab.SolverSettings(solver="gurobi")
    highs_settings = ab.SolverSettings(solver="highs")
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
        return _run(args, source, out, gurobi, highs, gurobi_settings, highs_settings)
    finally:
        for s in sessions:
            s.close()


def _run(args, source, out, gurobi, highs, gurobi_settings, highs_settings) -> int:
    try:
        camp = loader.load_campaign(source)
        source_manifest_path = source / "run_manifest.json"
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        labels = ga_labels(source_manifest)
    except (loader.CampaignRefused, loader.InputRejected, KeyError, OSError, ValueError) as exc:
        print(f"input_rejected: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    commit, dirty = _git_state(out)
    peaks = loader.peak_waves({"4sw5so": camp})
    peak_ids = {i for v in peaks.values() for i in v["wave_ids"]}
    type_spec = camp.fleet_types[0]
    rides = [int(r) for r in args.rides.split(",") if r] or list(camp.rides)
    want = {w for w in args.wave_ids.split(",") if w}

    rows, wave_docs, errors = [], [], []
    matrix_sha, slice_sha = {}, {}
    caps_fired = 0
    t_start = time.perf_counter()
    for ride in rides:
        waves = [w for w in camp.waves_for(ride) if not want or w.wave_id in want]
        if args.limit:
            waves = waves[: args.limit]
        cache: dict = {}
        for wave in waves:
            key = (wave.service_date, ride)
            if key not in cache:
                stem = f"{wave.service_date}_R{ride}_repeat1"
                arcs_doc = json.loads((source / f"{stem}.matrix.json").read_text(encoding="utf-8"))
                resp = json.loads((source / f"{stem}.response.json").read_text(encoding="utf-8"))
                cache[key] = (arcs_doc, {j["id"]: j["result"] for j in resp["jobs"]})
            arcs_doc, jobs = cache[key]
            matrix_sha[f"{wave.service_date}_R{ride}"] = wave.declared_snapshot_sha256
            slice_sha[f"{wave.service_date}_R{ride}"] = wave.arc_slice_sha256
            peak = wave.wave_id in peak_ids
            ga_result = jobs.get(wave.wave_id)
            t0 = time.perf_counter()
            enum = enumerate_wave(wave, camp.fleet_types)
            enum_info = {"model": enum.model, "columns": enum.column_count, "labels": enum.label_count,
                         "seconds": time.perf_counter() - t0, "cap_fired": enum.cap_fired}
            caps_fired += enum.status == "count_cap"
            if ga_result is None:
                sp = ab.SPSolveResult(wave.wave_id, "input_rejected", note="no archived GA job for this wave", peak=peak)
            else:
                sp = ab.solve_wave(wave, enum, peak=peak, session=gurobi)
            if sp.status == "backend_unavailable":
                print(f"backend unavailable during {wave.wave_id}: {sp.note}", file=sys.stderr)
                return 3
            h_sp = None
            if highs is not None and sp.status == "optimal":
                h_sp = ab.solve_wave(wave, enum, peak=peak, session=highs, d_lb_free=False)
                if h_sp.status == "backend_unavailable":
                    print(f"backend unavailable during {wave.wave_id} (HiGHS): {h_sp.note}", file=sys.stderr)
                    return 3
            ev = evaluate_wave(wave, ga_result, arcs_doc, sp, ga_labels=labels, enum_info=enum_info, highs=h_sp,
                               type_spec=type_spec, peak=peak)
            row = ev["row"]
            rows.append(row)
            errors.extend(ev["errors"])
            wave_docs.append({"wave_id": wave.wave_id, "service_date": wave.service_date, "R": ride, "peak": peak,
                              "model": enum_info["model"], "columns": enum_info["columns"],
                              "labels": enum_info["labels"], "cap_fired": enum_info["cap_fired"],
                              "stages": ev["stages"], "result": row})
            print(f"R{ride} {wave.wave_id} legs={wave.legs} cols={enum.column_count} {row['status']} "
                  f"K_GA={row['K_GA']} K*={row['K_star']} D_GA={row['D_GA']} D*={row['D_star']} dK={row['dK']} "
                  f"t={row['solve_seconds']:.2f}s highs={row['highs_agrees']}", flush=True)

    manifest = {
        "protocol": protocol.PROTOCOL_ID, "schema_version": protocol.MANIFEST_SCHEMA_VERSION,
        "work_package": "WP-E3", "fleet": FLEET, "git_commit": commit, "dirty_working_tree": dirty,
        "source_campaign": {"path": _rel(source),
                            "manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(),
                            "git_commit": str(source_manifest["git_commit"]),
                            "dirty_working_tree": bool(source_manifest["dirty_working_tree"]),
                            "termination_protocol": labels["ga_protocol"], "effective_seed": labels["ga_seed"]},
        "ga_labels": labels,
        "matrix_sha256": matrix_sha, "matrix_slice_sha256": slice_sha,
        "peak_waves": peaks,
        "ampl": {"version": gurobi.ampl_version, "amplpy_version": gurobi.amplpy_version, "location": gurobi.location},
        "solver": _solver_block(gurobi, gurobi_settings),
        "verification_solver": None if highs is None else _solver_block(highs, highs_settings),
        "enumeration": dict(protocol.ENUMERATION_CAPS, count_caps_fired=caps_fired),
        "waves": wave_docs,
        "options": {"highs_verify": bool(highs), "rides": rides, "wave_ids": sorted(want), "limit": args.limit},
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
    write_wave_csv(out / "wave_gaps.csv", rows)
    summary = summarise(rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["per_R"], sort_keys=True))
    if errors:
        print(f"{len(errors)} blocking error(s):", file=sys.stderr)
        for e in errors[:50]:
            print(f"  {e}", file=sys.stderr)
    return 1 if errors else 0


def summarise(rows) -> dict:
    per: dict = {}
    for r in rows:
        p = per.setdefault(str(r["R"]), {"waves": 0, "statuses": {}, "stage_stop_reasons": {}, "dK_zero": 0, "dK_positive": 0,
                                         "dK_unavailable": 0, "timing_dependent_rows": 0, "highs_agrees": 0,
                                         "highs_disagrees": 0, "highs_not_proven_or_not_run": 0, "exact_le_ga_true": 0,
                                         "exact_le_ga_false": 0, "gD_comparable": 0, "gD_not_comparable": 0})
        p["waves"] += 1
        p["statuses"][r["status"]] = p["statuses"].get(r["status"], 0) + 1
        for s in ("stage1", "stage2", "free"):
            reason = r[f"{s}_stop_reason"]
            if reason is not None:
                p["stage_stop_reasons"][reason] = p["stage_stop_reasons"].get(reason, 0) + 1
        if r["dK"] is None:
            p["dK_unavailable"] += 1
        else:
            p["dK_zero" if r["dK"] == 0 else "dK_positive"] += 1
        p["timing_dependent_rows"] += any(r[f"{s}_timing_dependent"] for s in ("stage1", "stage2", "free"))
        if r["highs_agrees"] is True:
            p["highs_agrees"] += 1
        elif r["highs_agrees"] is False:
            p["highs_disagrees"] += 1
        else:
            p["highs_not_proven_or_not_run"] += 1
        if r["exact_le_ga"] is True:
            p["exact_le_ga_true"] += 1
        elif r["exact_le_ga"] is False:
            p["exact_le_ga_false"] += 1
        if r["gD_note"] == "comparable":
            p["gD_comparable"] += 1
        elif r["gD_note"] == gaps.NOT_COMPARABLE:
            p["gD_not_comparable"] += 1
    return {"purpose": "WP-E3 GOAL 1 single type: descriptive gap measurement, no superiority claim", "waves": len(rows),
            "per_R": per}


if __name__ == "__main__":
    sys.exit(main())
