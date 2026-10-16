#!/usr/bin/env python3
"""WP-E2 work-limit calibration: stage 1, stage 2 and D_LB_free SP solves on archived waves.

Design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 9 (WP-E2 acceptance "wall limit not
binding on the calibration set"), section 4 (determinism), section 6 (Gurobi primary, HiGHS
reproducibility). Offline: reads the single-type 4sw5so archive through
scripts/exact_archive_loader.py (never the DB or HTTP), enumerates every wave (WP-E1) and solves
the SP with each solver under the production limits (60 s per call, 600 s per call on a peak
wave, Gurobi work limit, threads 1, seed 0).

These are calibration numbers only: no certification (WP-E3), no GA gap, no superiority claim.
The AMPL location comes from UNIRIDE_AMPL_DIR (or the local config / amplpy default) and is
never written; the solver log is never written.

Run: python scripts/calibrate_exact_sp.py [--solvers gurobi,highs] [--rides 50,60,70,90] [--out DIR]
Writes DIR/calibration_calls.csv, DIR/calibration_waves.csv and DIR/summary.json (DIR defaults to
docs/paper/results/week-2026-10-05-exact/wp-e2-calibration). Exit code 3 if the backend is unavailable.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from uniride_core.exact import ampl_backend as ab  # noqa: E402
from uniride_core.exact.route_enumeration import enumerate_wave  # noqa: E402

RESULTS = REPO / "docs" / "paper" / "results"
SOURCE = RESULTS / "week-2026-10-05-4sw5so"
DEFAULT_OUT = RESULTS / "week-2026-10-05-exact" / "wp-e2-calibration"
CALL_FIELDS = ["solver", "R", "wave_id", "service_date", "direction", "anchor", "legs", "peak", "columns", "stage",
               "k_fix", "status", "stop_reason", "timing_dependent", "non_lexicographic", "objective", "bound",
               "bound_ceil", "bound_source", "solve_result_num", "wall_seconds", "work_units", "time_limit",
               "work_limit", "limit_hit"]
WAVE_FIELDS = ["solver", "R", "wave_id", "service_date", "direction", "anchor", "legs", "peak", "columns", "labels",
               "status", "K", "D", "K_LB", "K_LB_source", "D_LB", "D_LB_free", "non_lexicographic", "routes",
               "lambda_max", "enumeration_seconds", "solve_seconds_total"]


def _loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader_cal", REPO / "scripts" / "exact_archive_loader.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_cal"] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solvers", default="gurobi,highs")
    ap.add_argument("--rides", default="")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    solvers = [s for s in args.solvers.split(",") if s]
    out = Path(args.out)
    loader = _loader()
    camp = loader.load_campaign(SOURCE)
    rides = [int(r) for r in args.rides.split(",") if r] or list(camp.rides)
    peaks = loader.peak_waves({"4sw5so": camp})
    peak_ids = {i for v in peaks.values() for i in v["wave_ids"]}
    enums = {}
    for ride in rides:
        for w in camp.waves_for(ride):
            t0 = time.perf_counter()
            res = enumerate_wave(w, camp.fleet_types)
            enums[(ride, w.wave_id)] = (w, res, time.perf_counter() - t0)
    calls, waves, identity = [], [], {}
    for solver in solvers:
        settings = ab.SolverSettings(solver=solver)
        try:
            session = ab.AmplSession(settings)
            session.open()
        except ab.ExactBackendUnavailable as exc:
            print(f"backend unavailable for {solver}: {exc}", file=sys.stderr)
            return 3
        identity[solver] = {"solver_version": session.solver_version, "ampl_version": session.ampl_version,
                            "amplpy_version": session.amplpy_version, "ampl_location": session.location,
                            "option_string": ab.solver_option_string(settings, peak=False),
                            "option_string_peak": ab.solver_option_string(settings, peak=True)}
        try:
            for (ride, wid), (w, res, enum_s) in enums.items():
                peak = wid in peak_ids
                sp = ab.solve_wave(w, res, peak=peak, session=session, d_lb_free=True)
                if sp.status == "backend_unavailable":
                    print(f"backend unavailable during {wid}: {sp.note}", file=sys.stderr)
                    return 3
                base = dict(solver=solver, R=ride, wave_id=wid, service_date=w.service_date, direction=w.direction,
                            anchor=w.anchor_minutes, legs=w.legs, peak=peak, columns=res.column_count)
                total = 0.0
                for st in (sp.stage1, sp.stage2, sp.free):
                    if st is None:
                        continue
                    total += st.wall_seconds or 0.0
                    calls.append(dict(base, stage=st.stage, k_fix=st.k_fix, status=st.status, stop_reason=st.stop_reason,
                                      timing_dependent=st.timing_dependent, non_lexicographic=st.non_lexicographic,
                                      objective=st.objective, bound=st.bound, bound_ceil=st.bound_ceil,
                                      bound_source=st.bound_source, solve_result_num=st.solve_result_num,
                                      wall_seconds=st.wall_seconds, work_units=st.work_units, time_limit=st.time_limit,
                                      work_limit=st.work_limit,
                                      limit_hit=st.stop_reason in ("wall_limit", "work_limit", "other_limit")))
                waves.append(dict(base, labels=res.label_count, status=sp.status, K=sp.k, D=sp.d, K_LB=sp.k_lb,
                                  K_LB_source=sp.k_lb_source, D_LB=sp.d_lb, D_LB_free=sp.d_lb_free,
                                  non_lexicographic=sp.non_lexicographic, routes=len(sp.routes),
                                  lambda_max=max((t for _, t in sp.selection), default=0),
                                  enumeration_seconds=round(enum_s, 3), solve_seconds_total=round(total, 3)))
                print(f"{solver} R{ride} {wid} legs={w.legs} cols={res.column_count} {sp.status} K={sp.k} D={sp.d} "
                      f"t={total:.2f}s", flush=True)
        finally:
            session.close()
    out.mkdir(parents=True, exist_ok=True)
    for name, fields, rows in (("calibration_calls.csv", CALL_FIELDS, calls), ("calibration_waves.csv", WAVE_FIELDS, waves)):
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            wr.writeheader()
            wr.writerows(rows)
    per = {}
    for c in calls:
        key = f"{c['solver']}_R{c['R']}"
        p = per.setdefault(key, {"calls": 0, "max_call_seconds": 0.0, "max_call_seconds_peak": 0.0,
                                 "max_work_units": None, "statuses": {}, "stop_reasons": {}, "limit_hit": 0})
        p["calls"] += 1
        p["max_call_seconds"] = max(p["max_call_seconds"], c["wall_seconds"] or 0.0)
        if c["peak"]:
            p["max_call_seconds_peak"] = max(p["max_call_seconds_peak"], c["wall_seconds"] or 0.0)
        if c["work_units"] is not None:
            p["max_work_units"] = max(p["max_work_units"] or 0.0, c["work_units"])
        p["statuses"][c["status"]] = p["statuses"].get(c["status"], 0) + 1
        p["stop_reasons"][str(c["stop_reason"])] = p["stop_reasons"].get(str(c["stop_reason"]), 0) + 1
        p["limit_hit"] += bool(c["limit_hit"])
    agree = disagree = 0
    if len(solvers) >= 2:
        by = {}
        for wv in waves:
            if wv["status"] == "optimal":
                by.setdefault((wv["R"], wv["wave_id"]), {})[wv["solver"]] = (wv["K"], wv["D"])
        for v in by.values():
            if len(v) == len(solvers):
                if len(set(v.values())) == 1:
                    agree += 1
                else:
                    disagree += 1
    summary = {
        "purpose": "WP-E2 work-limit calibration (engineering measurement; no certification, no gap, no claim)",
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "dirty_working_tree": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "source_campaign": "docs/paper/results/week-2026-10-05-4sw5so",
        "fleet": "single_4sw5so",
        "rides": rides, "waves_per_ride": len(camp.waves_for(rides[0])),
        "peak_waves": peaks,
        "solvers": identity,
        "limits": {"wall_seconds": ab.DEFAULT_WALL_LIMIT_SECONDS, "peak_wall_seconds": ab.PEAK_WALL_LIMIT_SECONDS,
                   "gurobi_work_limit": ab.DEFAULT_WORK_LIMIT, "gurobi_peak_work_limit": ab.PEAK_WORK_LIMIT,
                   "threads": 1, "seed": 0, "mip_gap": ab.MIP_GAP, "mip_gap_abs": ab.MIP_GAP_ABS},
        "per_solver_and_R": per,
        "wave_status_counts": {s: {st: sum(1 for w in waves if w["solver"] == s and w["status"] == st)
                                   for st in sorted({w["status"] for w in waves})} for s in solvers},
        "proven_optimum_agreement": {"agree": agree, "disagree": disagree},
        "any_limit_hit": any(c["limit_hit"] for c in calls),
        "python_version": platform.python_version(),
        "host_os": ab.host_description(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("per_solver_and_R", "proven_optimum_agreement", "any_limit_hit")}, indent=1))
    return 1 if disagree else 0


if __name__ == "__main__":
    sys.exit(main())
