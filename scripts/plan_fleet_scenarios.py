#!/usr/bin/env python3
"""Figures, independent verification and weekly tables for the heterogeneous-fleet
campaign (docs/paper/results/week-2026-10-05-fleet). Standard library only.
Reuses SVG helpers from plan_resource_profile / plan_schedule_report.

Usage: python scripts/plan_fleet_scenarios.py [results_dir]
Reads scenario_daily.csv, scenario_weekly.csv, car_usage_windows.csv, run_manifest.json and
*_R<R>_<A|L1|L2|L3>.response.json. Writes figures/*.svg, figures/index.html,
fleet_verification.md and weekly_summary.md. Violations are reported, never fixed.
"""
import csv
import datetime
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "paper", "results", "week-2026-10-05-fleet")
sys.argv[1:] = [RES]  # the imported campaign helpers read RES from argv[1]
from plan_resource_profile import PAD, PXM, X0, axes, head, peak_windows, poly, step_pts, write  # noqa: E402
from plan_schedule_report import C_DROP, C_PICK, hm  # noqa: E402

FIG = os.path.join(RES, "figures")
SCENS = ["A", "L1", "L2", "L3"]
SNAME = {"A": "A: all-large minimum", "L1": "B: 1 large + sedans", "L2": "C: 2 large + sedans", "L3": "D: 3 large + sedans"}
SSHORT = {"A": "A", "L1": "B (1)", "L2": "C (2)", "L3": "D (3)"}
RS = [50, 60, 70, 90]
WD = ["Mon", "Tue", "Wed", "Thu", "Fri"]
C_LARGE, C_SEDAN, C_BAD = "#0072B2", "#E69F00", "#C00000"
DEFS = ('<defs><pattern id="hatchgrey" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="7" stroke="#999" stroke-width="2"/></pattern>'
        '<pattern id="hatchbad" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="6" height="6" fill="%s"/><line x1="0" y1="0" x2="0" y2="6" stroke="%s" stroke-width="3"/></pattern></defs>'
        % (C_SEDAN, C_BAD))


def esc(s):
    return html.escape(str(s))


def rd(name):
    with open(os.path.join(RES, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(s):
    return int(float(s)) if s not in ("", None) else None


# ---------------------------------------------------------------- data
daily = rd("scenario_daily.csv")
weekly_csv = rd("scenario_weekly.csv")
windows = rd("car_usage_windows.csv")
with open(os.path.join(RES, "run_manifest.json"), encoding="utf-8") as f:
    MAN = json.load(f)
TYPES = {t["typeId"]: t for t in MAN["fleet_types"]}
DATES = sorted({r["date"] for r in daily})
D = {(r["date"], int(r["ride_limit"]), r["scenario"]): r for r in daily}


def resp(date, R, s):
    with open(os.path.join(RES, "%s_R%d_%s.response.json" % (date, R, s)), encoding="utf-8") as f:
        return json.load(f)["scenario"]


def day_ok(r):
    return r["status"] == "ok"


def day_unproven(r):
    if not day_ok(r):
        return False
    if r["scenario"] == "A":
        return r["large_vehicles_proven"] != "true"
    return r["cars_status"] != "proven_over_menu" or r["assignment_status"] != "proven"


def weekly(R, s):
    rows = [D[(d, R, s)] for d in DATES]
    ok = [r for r in rows if day_ok(r)]
    w = {"R": R, "s": s, "days": rows, "feasible_days": len(ok), "complete": len(ok) == len(rows),
         "unproven": any(day_unproven(r) for r in ok)}
    if s == "A":
        w["large"] = max(num(r["large_vehicles"]) for r in ok)
        w["cars"] = 0
        w["per_day"] = [num(r["large_vehicles"]) for r in rows]
    else:
        w["large"] = num(rows[0]["large_limit"])
        w["cars"] = max(num(r["cars"]) for r in ok) if w["complete"] else None
        w["per_day"] = [num(r["cars"]) if day_ok(r) else None for r in rows]
    w["total"] = w["large"] + w["cars"] if w["complete"] else None
    w["cars_sum"] = sum(w["per_day"]) if (w["complete"] and s != "A") else None
    for k in ("large_vehicle_minutes", "car_vehicle_minutes", "total_vehicle_minutes"):
        w[k] = sum(num(r[k]) for r in rows) if w["complete"] else None
    return w


W = {(R, s): weekly(R, s) for R in RS for s in SCENS}


# ---------------------------------------------------------------- verification
def check_run(sc, R):
    """Return {check: [violations]} recomputed from the response routes only."""
    v = {k: [] for k in ("overlap_cooldown", "sw_not_on_sedan", "capacity", "ride_tour", "legs_once", "fleet_consistency")}
    routes = sc["routes"]
    per = {}
    for r in routes:
        per.setdefault((r["vehicleType"], r["physicalVehicleId"]), []).append(r)
    for (t, vid), rs in per.items():
        cd = TYPES[t]["cooldownMinutes"]
        rs.sort(key=lambda r: r["startMinutes"])
        for a, b in zip(rs, rs[1:]):
            if b["startMinutes"] < a["endMinutes"] + cd:
                v["overlap_cooldown"].append("%s/%s: %s ends %s, next %s starts %s (cooldown %d)" % (
                    t, vid, a["jobId"], hm(a["endMinutes"]), b["jobId"], hm(b["startMinutes"]), cd))
    for r in routes:
        t = TYPES[r["vehicleType"]]
        ids = r["occurrenceIds"]
        sw = sum(1 for o in ids if o.rsplit(":", 1)[1].startswith("Sw"))
        so = len(ids) - sw
        if sw != r["swCount"] or so != r["soCount"]:
            v["capacity"].append("%s route %d: recount sw/so %d/%d != reported %d/%d" % (r["jobId"], r["routeIndex"], sw, so, r["swCount"], r["soCount"]))
        if r["vehicleType"] == "sedan" and sw > 0:
            v["sw_not_on_sedan"].append("%s route %d carries %d Sw" % (r["jobId"], r["routeIndex"], sw))
        if sw > t["swCapacity"] or so > t["soCapacity"]:
            v["capacity"].append("%s route %d (%s): sw/so %d/%d exceeds %d/%d" % (
                r["jobId"], r["routeIndex"], r["vehicleType"], sw, so, t["swCapacity"], t["soCapacity"]))
        steps = r["steps"]
        total = sum(s["duration"] for s in steps)
        if total != r["minutes"] or r["endMinutes"] - r["startMinutes"] != total:
            v["ride_tour"].append("%s route %d: minutes %s, steps %d, window %d" % (r["jobId"], r["routeIndex"], r["minutes"], total, r["endMinutes"] - r["startMinutes"]))
        if total > 150:
            v["ride_tour"].append("%s route %d: tour %d > 150" % (r["jobId"], r["routeIndex"], total))
        for o in ids:
            lab = o.rsplit(":", 1)[1].split("~")[0]
            if r["direction"] == "pickup":
                idx = [i for i, s in enumerate(steps) if s["location1"] == lab]
                ride = sum(s["duration"] for s in steps[idx[0]:]) if idx else None
            else:
                idx = [i for i, s in enumerate(steps) if s["location2"] == lab]
                ride = sum(s["duration"] for s in steps[:idx[0] + 1]) if idx else None
            if ride is None:
                v["ride_tour"].append("%s: %s not found in steps" % (r["jobId"], lab))
            elif ride > R:
                v["ride_tour"].append("%s route %d: %s ride %d > R=%d" % (r["jobId"], r["routeIndex"], lab, ride, R))
    return v, per


def ride_stats(sc, R):
    vals = []
    for r in sc["routes"]:
        steps = r["steps"]
        for o in r["occurrenceIds"]:
            lab = o.rsplit(":", 1)[1].split("~")[0]
            if r["direction"] == "pickup":
                i = [k for k, s in enumerate(steps) if s["location1"] == lab][0]
                vals.append(sum(s["duration"] for s in steps[i:]))
            else:
                i = [k for k, s in enumerate(steps) if s["location2"] == lab][0]
                vals.append(sum(s["duration"] for s in steps[:i + 1]))
    return vals


def verify_all():
    rows, viol = [], []
    for R in RS:
        for date in DATES:
            for s in SCENS:
                row = D[(date, R, s)]
                with open(os.path.join(RES, "%s_R%d_%s.response.json" % (date, R, s)), encoding="utf-8") as f:
                    full = json.load(f)
                sc = full["scenario"]
                if not day_ok(row):
                    rows.append((date, R, s, None))
                    continue
                v, per = check_run(sc, R)
                labels = set(full["occurrenceLabels"])
                seen = [o for r in sc["routes"] for o in r["occurrenceIds"]]
                if sorted(seen) != sorted(labels) or len(seen) != len(set(seen)):
                    miss, dup = labels - set(seen), {o for o in seen if seen.count(o) > 1}
                    v["legs_once"].append("missing %d, duplicated %d (legs expected %d, got %d)" % (len(miss), len(dup), len(labels), len(seen)))
                if len(labels) != num(row["legs"]):
                    v["legs_once"].append("legs in CSV %s != occurrence labels %d" % (row["legs"], len(labels)))
                nl = len({k for k in per if k[0] == "large"})
                nc = len({k for k in per if k[0] == "sedan"})
                exp_c = num(row["cars"]) or 0
                if nc != exp_c:
                    v["fleet_consistency"].append("distinct sedans %d != cars %d" % (nc, exp_c))
                if s != "A" and nl > num(row["large_limit"]):
                    v["fleet_consistency"].append("large vehicles used %d > L=%s" % (nl, row["large_limit"]))
                if s == "A" and nl != num(row["large_vehicles"]):
                    v["fleet_consistency"].append("distinct large %d != large_vehicles %s" % (nl, row["large_vehicles"]))
                rv = ride_stats(sc, R)
                mean = sum(rv) / len(rv)
                if abs(mean - float(row["ride_mean"])) > 1e-4 or max(rv) != num(row["ride_max"]):
                    v["fleet_consistency"].append("ride mean/max recomputed %.4f/%d != CSV %s/%s" % (mean, max(rv), row["ride_mean"], row["ride_max"]))
                mins = {t: sum(r["minutes"] for r in sc["routes"] if r["vehicleType"] == t) for t in TYPES}
                if mins["large"] != num(row["large_vehicle_minutes"]) or mins["sedan"] != num(row["car_vehicle_minutes"]):
                    v["fleet_consistency"].append("minutes by type %s != CSV %s/%s" % (mins, row["large_vehicle_minutes"], row["car_vehicle_minutes"]))
                cw = [w for w in windows if w["date"] == date and int(w["ride_limit"]) == R and w["scenario"] == s]
                srt = sorted((min(r["startMinutes"] for r in rs), max(r["endMinutes"] for r in rs)) for (t, _), rs in per.items() if t == "sedan")
                cws = sorted((hm_to_min(w["window_start"]), hm_to_min(w["window_end"])) for w in cw)
                if srt != cws:
                    v["fleet_consistency"].append("sedan windows from routes %s != car_usage_windows.csv %s" % (srt, cws))
                rows.append((date, R, s, v))
                for k, lst in v.items():
                    for m in lst:
                        viol.append("%s R=%d %s [%s] %s" % (date, R, s, k, m))
    return rows, viol


def hm_to_min(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


CHECKS = [("overlap_cooldown", "No overlap and cooldown per vehicle (per type)"),
          ("sw_not_on_sedan", "Sw never on a sedan"),
          ("capacity", "Per-route capacity by type (and Sw/So recount)"),
          ("ride_tour", "Ride time <= R, tour <= 150, step sums"),
          ("legs_once", "Every leg served exactly once"),
          ("fleet_consistency", "CSV consistency (vehicles, minutes, ride stats, sedan windows)")]


def write_verification(rows, viol):
    out = ["# Fleet verification", "",
           "Generated by `scripts/plan_fleet_scenarios.py`. Recomputed from the `*.response.json` routes only (steps, occurrence ids, vehicle ids); "
           "violations are reported, not fixed. Fleet types and cooldowns come from `run_manifest.json`: %s." % "; ".join(
               "%s %dSw/%dSo cd%d" % (t["typeId"], t["swCapacity"], t["soCapacity"], t["cooldownMinutes"]) for t in TYPES.values()), ""]
    checked = [r for r in rows if r[3] is not None]
    out.append("Runs: %d (date x R x scenario); %d checked (feasible, routes present); %d infeasible_for_L (no routes, not checked)." % (
        len(rows), len(checked), len(rows) - len(checked)))
    out.append("")
    out.append("Verdict: %s" % ("ALL CHECKS PASS" if not viol else "%d VIOLATION(S) FOUND" % len(viol)))
    out += ["", "| Check | Runs checked | Runs failing | Result |", "|---|---|---|---|"]
    for k, label in CHECKS:
        f = sum(1 for r in checked if r[3][k])
        out.append("| %s | %d | %d | %s |" % (label, len(checked), f, "FAIL" if f else "pass"))
    if viol:
        out += ["", "## Violations", ""] + ["- " + x for x in viol]
    out += ["", "## Per run", "", "| Date | R | Scenario | " + " | ".join(l.split(" (")[0] for _, l in CHECKS) + " |", "|---|---|---|" + "---|" * len(CHECKS)]
    for date, R, s, v in sorted(rows, key=lambda x: (x[1], x[0], SCENS.index(x[2]))):
        if v is None:
            out.append("| %s | %d | %s | %s |" % (date, R, s, " | ".join(["n/a (infeasible_for_L)"] * len(CHECKS))))
        else:
            out.append("| %s | %d | %s | %s |" % (date, R, s, " | ".join("FAIL" if v[k] else "pass" for k, _ in CHECKS)))
    out += ["", "## Weekly CSV cross-check", ""]
    wl = []
    for r in weekly_csv:
        R, s = int(r["ride_limit"]), r["scenario"]
        w = W[(R, s)]
        if s == "A":
            ok = num(r["weekly_large_vehicles"]) == w["large"]
        else:
            ok = (num(r["weekly_cars"]) == w["cars"]) and (r["complete_week"] == "true") == w["complete"]
        if not ok:
            wl.append("R=%d %s: scenario_weekly.csv (%s / %s / complete %s) != recomputed from scenario_daily.csv (%s / %s)" % (
                R, s, r["weekly_cars"], r["weekly_large_vehicles"], r["complete_week"], w["cars"], w["large"]))
    out.append("Weekly cars / large vehicles / completeness recomputed from scenario_daily.csv vs scenario_weekly.csv: %s" % (
        "all 16 rows agree." if not wl else "%d mismatch(es)." % len(wl)))
    out += ["- " + x for x in wl]
    p = os.path.join(RES, "fleet_verification.md")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    return len(wl)


# ---------------------------------------------------------------- tables
def cell_text(r):
    if not day_ok(r):
        return "infeasible"
    L = num(r["large_vehicles"]) if r["scenario"] == "A" else num(r["large_limit"])
    return "%d+%d%s" % (L, num(r["cars"]) or 0, " *" if day_unproven(r) else "")


def write_weekly_md():
    out = ["# Weekly summary (recomputed from scenario_daily.csv)", "",
           "Generated by `scripts/plan_fleet_scenarios.py`. Weekly vehicles = large vehicles + the largest daily sedan need (same sedans every day). "
           "`-` = scenario infeasible on at least one weekday. `*` = not proven over the menu.", "",
           "| R | Scenario | Feasible days | Large | Max sedans/day | Weekly vehicles | Sedans per day (Mon..Fri) | Sedan-day sum | Large min/wk | Sedan min/wk |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for R in RS:
        for s in SCENS:
            w = W[(R, s)]
            pd = "/".join("x" if v is None else str(v) for v in w["per_day"]) if s != "A" else "-"
            if not w["complete"]:
                out.append("| %d | %s | %d/5 | %d | - | - | %s | - | - | - |" % (R, SNAME[s], w["feasible_days"], w["large"], pd))
            else:
                out.append("| %d | %s | 5/5 | %d | %d | %d%s | %s | %s | %d | %d |" % (
                    R, SNAME[s], w["large"], w["cars"], w["total"], " *" if w["unproven"] else "", pd,
                    "-" if s == "A" else w["cars_sum"], w["large_vehicle_minutes"], w["car_vehicle_minutes"]))
    out += ["", "Scenario A: the Large column is the weekly maximum of the daily minimum (per day: %s)." % "; ".join(
        "R=%d %s" % (R, "/".join(str(v) for v in W[(R, "A")]["per_day"])) for R in RS), ""]
    out += ["## Daily demand (from the scenario A responses, R = 60)", "",
            "| Date | Day | Students | Sw students | So students | Most Sw passengers in one wave | Wave |", "|---|---|---|---|---|---|---|"]
    for j, d in enumerate(DATES):
        sc = resp(d, 60, "A")
        labs = {o.rsplit(":", 1)[1].split("~")[0] for r in sc["routes"] for o in r["occurrenceIds"]}
        nsw = sum(1 for x in labs if x.startswith("Sw"))
        per = {}
        for r in sc["routes"]:
            per[r["jobId"]] = per.get(r["jobId"], 0) + r["swCount"]
        wid = max(per, key=per.get)
        out.append("| %s | %s | %d | %d | %d | %d | %s |" % (d, WD[j], len(labs), nsw, len(labs) - nsw, per[wid], wid.split(":", 1)[1]))
    with open(os.path.join(RES, "weekly_summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


# ---------------------------------------------------------------- figures
YMAX = max(w["total"] for w in W.values() if w["total"] is not None) + 1


def panel(out, x0, y0, w, h, R, title):
    out.append('<text x="%g" y="%g" font-size="14" font-weight="bold" fill="#111">%s</text>' % (x0, y0 - 12, esc(title)))
    out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#fff" stroke="#888" stroke-width="0.8"/>' % (x0, y0, w, h))
    Y = lambda v: y0 + h - h * v / YMAX
    for v in range(0, YMAX + 1):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#e2e2e2" stroke-width="0.7"/>' % (x0, Y(v), x0 + w, Y(v)))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="end" fill="#333">%d</text>' % (x0 - 5, Y(v) + 4, v))
    slot = w / len(SCENS)
    bw = min(58, slot * 0.55)
    for i, s in enumerate(SCENS):
        wk = W[(R, s)]
        cx = x0 + slot * (i + 0.5)
        out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#111">%s</text>' % (cx, y0 + h + 15, esc(SSHORT[s])))
        pd = "/".join("x" if v is None else str(v) for v in wk["per_day"])
        out.append('<text x="%g" y="%g" font-size="10" text-anchor="middle" fill="#444">%s</text>' % (
            cx, y0 + h + 28, esc(("large " if s == "A" else "sedans ") + pd)))
        if not wk["complete"]:
            out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="url(#hatchgrey)" fill-opacity="0.45" stroke="#777" stroke-dasharray="5 3"><title>%s</title></rect>' % (
                cx - bw / 2, y0 + 4, bw, h - 4, esc("%s R=%d: infeasible on %d of 5 days with %d large vehicle(s)" % (SNAME[s], R, 5 - wk["feasible_days"], wk["large"]))))
            out.append('<text transform="rotate(-90 %g %g)" x="%g" y="%g" font-size="13" font-weight="bold" text-anchor="middle" fill="#333" stroke="#fff" stroke-width="3" paint-order="stroke">infeasible (%d of 5 days)</text>' % (
                cx, y0 + h / 2, cx + 4, y0 + h / 2, 5 - wk["feasible_days"]))
            continue
        hl = h * wk["large"] / YMAX
        hc = h * wk["cars"] / YMAX
        bad = wk["unproven"]
        out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s"><title>%s</title></rect>' % (
            cx - bw / 2, Y(0) - hl, bw, hl, C_LARGE, esc("%s R=%d: %d large" % (SNAME[s], R, wk["large"]))))
        if hc:
            out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" stroke="%s"><title>%s</title></rect>' % (
                cx - bw / 2, Y(0) - hl - hc, bw, hc, "url(#hatchbad)" if bad else C_SEDAN, C_BAD if bad else "#fff",
                esc("%s R=%d: %d sedans (max over days)%s" % (SNAME[s], R, wk["cars"], "; NOT proven over menu" if bad else ""))))
        out.append('<text x="%g" y="%g" font-size="12" font-weight="bold" text-anchor="middle" fill="#111">%d%s</text>' % (
            cx, Y(0) - hl - hc - 5, wk["total"], " (unproven)" if bad else ""))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#fff">%d</text>' % (cx, Y(0) - hl / 2 + 4, wk["large"]))
        if hc >= 14:
            out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#111">%d</text>' % (cx, Y(0) - hl - hc / 2 + 4, wk["cars"]))


def legend(out, x, y, two_rows=False):
    x0 = x
    out.append('<rect x="%g" y="%g" width="14" height="10" fill="%s"/><text x="%g" y="%g" font-size="12" fill="#222">Large minibuses (fixed fleet)</text>' % (x, y, C_LARGE, x + 20, y + 10))
    x += 210
    out.append('<rect x="%g" y="%g" width="14" height="10" fill="%s"/><text x="%g" y="%g" font-size="12" fill="#222">Sedans (largest daily need)</text>' % (x, y, C_SEDAN, x + 20, y + 10))
    x += 200
    if two_rows:
        x, y = x0, y + 18
    out.append('<rect x="%g" y="%g" width="14" height="10" fill="url(#hatchgrey)" stroke="#777"/><text x="%g" y="%g" font-size="12" fill="#222">Infeasible on at least one weekday</text>' % (x, y, x + 20, y + 10))
    x += 250
    out.append('<rect x="%g" y="%g" width="14" height="10" fill="url(#hatchbad)" stroke="%s"/><text x="%g" y="%g" font-size="12" fill="#222">Sedan count not proven over menu</text>' % (x, y, C_BAD, x + 20, y + 10))


def fig_scen(path, R):
    out = [DEFS, '<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Weekly vehicles by scenario, R=%d min" % R)),
        '<text x="%d" y="42" font-size="12" fill="#444">Large + sedans; per-day need under each bar (x = infeasible day).</text>' % PAD]
    legend(out, PAD, 54, True)
    panel(out, 60, 120, 560, 280, R, "R = %d min, week of %s" % (R, DATES[0]))
    write(path, 660, 450, out)


def fig_scen_all(path):
    out = [DEFS, '<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Weekly vehicles by scenario and ride limit R (shared y-scale), week of %s" % DATES[0]))]
    legend(out, PAD, 38)
    for i, R in enumerate(RS):
        panel(out, 56 + (i % 2) * 520, 92 + (i // 2) * 360, 450, 260, R, "R = %d min" % R)
    write(path, 1040, 760, out)


def fig_heat(path):
    cw, ch, x0 = 120, 26, 150
    out = [DEFS, '<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Daily fleet per scenario: large + sedans (L+C) or infeasible, week of %s" % DATES[0])),
        '<text x="%d" y="42" font-size="12" fill="#444">Cell = large vehicles + sedans needed that day. Grey hatch = infeasible_for_L.</text>' % PAD,
        '<text x="%d" y="58" font-size="12" fill="#444">Red outline and * = not proven over the menu.</text>' % PAD]
    y = 82
    for R in RS:
        out.append('<text x="%d" y="%g" font-size="13" font-weight="bold" fill="#111">R = %d min</text>' % (PAD, y + 14, R))
        for j, d in enumerate(DATES):
            out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#333">%s %s</text>' % (x0 + cw * (j + 0.5), y + 14, WD[j], d[5:]))
        y += 22
        for s in SCENS:
            out.append('<text x="%d" y="%g" font-size="12" fill="#222">%s</text>' % (PAD + 6, y + ch / 2 + 4, esc(SNAME[s])))
            for j, d in enumerate(DATES):
                r = D[(d, R, s)]
                cx = x0 + cw * j
                if not day_ok(r):
                    fill = "url(#hatchgrey)"
                else:
                    c = num(r["cars"]) or 0
                    g = 235 - min(c, 5) * 28
                    fill = "rgb(%d,%d,255)" % (g, g + 10) if s == "A" else "rgb(255,%d,%d)" % (min(g + 20, 255), max(g - 60, 60))
                stroke = C_BAD if day_unproven(r) else "#fff"
                out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" stroke="%s" stroke-width="%g"><title>%s</title></rect>' % (
                    cx, y, cw, ch, fill, stroke, 2.5 if stroke == C_BAD else 1.5,
                    esc("%s %s R=%d: %s %s" % (WD[j], d, R, SNAME[s], r["reason_codes"] if not day_ok(r) else "L+C = " + cell_text(r)))))
                out.append('<text x="%g" y="%g" font-size="13" text-anchor="middle" fill="%s">%s</text>' % (
                    cx + cw / 2, y + ch / 2 + 5, "#333" if not day_ok(r) else "#111", cell_text(r)))
            y += ch
        y += 22
    write(path, x0 + cw * 5 + PAD, y, out)


def busy_segs(routes, cd):
    ev = {}
    for r in routes:
        for t, d in ((r["startMinutes"], 1), (r["endMinutes"] + cd, -1)):
            ev[t] = ev.get(t, 0) + d
    segs, cur, ts = [], 0, sorted(ev)
    for i, t in enumerate(ts):
        cur += ev[t]
        if i + 1 < len(ts):
            segs.append((t, ts[i + 1], cur, cur))
    return segs


def fig_resource(path, R):
    days = []
    for d in DATES:
        r = D[(d, R, "L3")]
        sc = resp(d, R, "L3")
        days.append((d, r, sc))
    t0 = min(x["startMinutes"] for _, _, sc in days for x in sc["routes"])
    t1 = max(x["endMinutes"] for _, _, sc in days for x in sc["routes"]) + 10
    t0, t1 = t0 - t0 % 60, t1 + (-t1) % 60
    w, h, gap = (t1 - t0) * PXM, 120, 46
    ymax = 1
    prof = {}
    for d, r, sc in days:
        for t in TYPES:
            prof[(d, t)] = busy_segs([x for x in sc["routes"] if x["vehicleType"] == t], TYPES[t]["cooldownMinutes"])
            ymax = max(ymax, max([s[3] for s in prof[(d, t)]] + [0]))
    ymax = max(ymax, max(num(r["large_limit"]) for _, r, _ in days)) + 1
    out = [DEFS, '<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Busy vehicles by type incl. %d-min cooldown, scenario D (3 large + sedans), R=%d min, tour limit 150" % (TYPES["large"]["cooldownMinutes"], R))),
        '<rect x="%d" y="38" width="16" height="10" fill="%s" fill-opacity="0.3" stroke="%s" stroke-width="2"/><text x="%d" y="47" font-size="12" fill="#222">Large busy (step line)</text>' % (PAD, C_LARGE, C_LARGE, PAD + 22),
        '<rect x="%d" y="38" width="16" height="10" fill="%s" fill-opacity="0.3" stroke="%s" stroke-width="2"/><text x="%d" y="47" font-size="12" fill="#222">Sedan busy (step line)</text>' % (PAD + 190, C_SEDAN, C_SEDAN, PAD + 212),
        '<text x="%d" y="47" font-size="12" fill="#222">Dashed: vehicles provided (large) / sedans needed that day. Red heading = sedan count not proven over the menu.</text>' % (PAD + 400)]
    y = 64
    for d, r, sc in days:
        X = lambda t, y0=y: X0 + (t - t0) * PXM
        y0 = y + 20
        Y = lambda v, y0=y0: y0 + h - h * v / ymax
        bad = day_unproven(r)
        out.append('<text x="%d" y="%g" font-size="13" font-weight="bold" fill="%s">%s %s: %d large, %d sedans%s</text>' % (
            X0, y + 12, C_BAD if bad else "#111", WD[DATES.index(d)], d, num(r["large_limit"]), num(r["cars"]), " (NOT proven over menu)" if bad else ""))
        axes(out, X0, y0, w, h, t0, t1, ymax)
        for t, col in (("large", C_LARGE), ("sedan", C_SEDAN)):
            segs = prof[(d, t)]
            if not segs:
                continue
            pts = step_pts(segs, 3, X, Y)
            out.append('<polygon points="%g,%g %s %g,%g" fill="%s" fill-opacity="0.25" stroke="none"/>' % (pts[0][0], Y(0), poly(pts), pts[-1][0], Y(0), col))
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4"/>' % (poly(pts), col))
            pk, _ = peak_windows(segs, 3)
            out.append('<text x="%g" y="%g" font-size="11" fill="#222">%s peak %d</text>' % (X0 + w + 6, Y(pk) + 4 + (8 if t == "sedan" and prof[(d, "large")] and pk == peak_windows(prof[(d, "large")], 3)[0] else 0), t, pk))
        for val, col in ((num(r["large_limit"]), C_LARGE), (num(r["cars"]), C_SEDAN)):
            out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.4" stroke-dasharray="7 4"/>' % (X0, Y(val), X0 + w, Y(val), col))
        y += 20 + h + gap
    out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Time of day (HH:MM)</text>' % (X0 + w / 2, y - 14))
    write(path, X0 + w + 110, y, out)


def fig_gantt(path, R, s="L3"):
    rowh, gap = 18, 34
    t0, t1 = 24 * 60, 0
    days = []
    for d in DATES:
        sc = resp(d, R, s)
        by = {}
        for x in sc["routes"]:
            if x["vehicleType"] == "sedan":
                by.setdefault(x["physicalVehicleId"], []).append(x)
        for rs in by.values():
            t0 = min(t0, min(x["startMinutes"] for x in rs))
            t1 = max(t1, max(x["endMinutes"] for x in rs) + 10)
        days.append((d, D[(d, R, s)], by))
    t0, t1 = t0 - t0 % 60, t1 + (-t1) % 60
    w = (t1 - t0) * PXM
    X = lambda t: X0 + 40 + (t - t0) * PXM
    X0g = X0 + 40
    height = 70 + sum(30 + max(1, len(by)) * rowh + gap for _, _, by in days)
    out = [DEFS, '<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Sedan usage, scenario D (3 large + sedans), R=%d min, week of %s" % (R, DATES[0]))),
        '<rect x="%d" y="38" width="16" height="10" fill="%s"/><text x="%d" y="47" font-size="12" fill="#222">Pickup route</text>' % (PAD, C_PICK, PAD + 22),
        '<rect x="%d" y="38" width="16" height="10" fill="%s"/><text x="%d" y="47" font-size="12" fill="#222">Dropoff route</text>' % (PAD + 110, C_DROP, PAD + 132),
        '<rect x="%d" y="38" width="16" height="10" fill="#bbb"/><text x="%d" y="47" font-size="12" fill="#222">Cooldown (%d min)</text>' % (PAD + 230, PAD + 252, TYPES["sedan"]["cooldownMinutes"]),
        '<line x1="%d" y1="43" x2="%d" y2="43" stroke="#555" stroke-width="2"/><text x="%d" y="47" font-size="12" fill="#222">First start to last end of the sedan</text>' % (PAD + 380, PAD + 400, PAD + 406)]
    y = 64
    for d, r, by in days:
        bad = day_unproven(r)
        out.append('<text x="%d" y="%g" font-size="13" font-weight="bold" fill="%s">%s %s: %d sedan(s)%s</text>' % (
            PAD, y + 12, C_BAD if bad else "#111", WD[DATES.index(d)], d, num(r["cars"]), " (NOT proven over menu)" if bad else ""))
        y0 = y + 20
        n = max(1, len(by))
        out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#fff" stroke="%s" stroke-width="%g"/>' % (X0g, y0, w, n * rowh, C_BAD if bad else "#888", 2 if bad else 0.8))
        t = t0
        while t <= t1:
            out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#ddd" stroke-width="0.7"/><text x="%g" y="%g" font-size="10" text-anchor="middle" fill="#333">%s</text>' % (
                X(t), y0, X(t), y0 + n * rowh, X(t), y0 + n * rowh + 12, hm(t)))
            t += 60
        if not by:
            out.append('<text x="%g" y="%g" font-size="12" fill="#555">no sedan needed</text>' % (X0g + 8, y0 + 13))
        for k, (vid, rs) in enumerate(sorted(by.items(), key=lambda kv: min(x["startMinutes"] for x in kv[1]))):
            ry = y0 + k * rowh
            out.append('<text x="%g" y="%g" font-size="11" text-anchor="end" fill="#222">C%d</text>' % (X0g - 6, ry + 13, k + 1))
            a, b = min(x["startMinutes"] for x in rs), max(x["endMinutes"] for x in rs)
            out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#555" stroke-width="2"/>' % (X(a), ry + rowh / 2, X(b), ry + rowh / 2))
            for x in rs:
                col = C_PICK if x["direction"] == "pickup" else C_DROP
                out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#bbb"/>' % (X(x["endMinutes"]), ry + 3, TYPES["sedan"]["cooldownMinutes"] * PXM, rowh - 6))
                out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" stroke="#fff" stroke-width="0.6"><title>%s</title></rect>' % (
                    X(x["startMinutes"]), ry + 2, (x["endMinutes"] - x["startMinutes"]) * PXM, rowh - 4, col,
                    esc("%s %s-%s (%d min, %d So)" % (x["direction"], hm(x["startMinutes"]), hm(x["endMinutes"]), x["minutes"], x["soCount"]))))
        y += 30 + n * rowh + gap - 10
    write(path, X0g + w + PAD, y, out)


def write_index(figs):
    H = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Heterogeneous fleet scenarios, week of %s</title>' % DATES[0],
         "<style>body{font-family:Arial,Helvetica,sans-serif;max-width:1180px;margin:20px auto;padding:0 12px}img{max-width:100%;border:1px solid #ddd}"
         "table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:3px 8px;font-size:13px;text-align:center}.inf{background:#e4e4e4;color:#555}"
         ".bad{outline:2px solid #C00000}</style></head><body>",
         "<h1>Heterogeneous fleet scenarios, week of %s</h1>" % DATES[0],
         "<p>Generated by scripts/plan_fleet_scenarios.py from the campaign CSVs and response JSONs. Large 4 Sw + 5 So, sedan 0 Sw + 4 So, cooldown 10, "
         "tour limit 150. Descriptive only. Sedan counts are minima over the generated route menus; a red mark means the count is not proven over the menu. "
         "Verification: <a href='../fleet_verification.md'>fleet_verification.md</a>.</p>",
         "<h2>(a) Scenario comparison</h2>", '<img src="fleet_scenarios_all.svg" alt="All R">']
    H += ['<h3>R = %d</h3><img src="fleet_scenarios_R%d.svg" alt="R=%d">' % (R, R, R) for R in RS]
    H += ["<h2>(b) Daily feasibility and fleet (L+C)</h2>", '<img src="fleet_daily_heatmap.svg" alt="heatmap">', "<table><tr><th>R</th><th>Scenario</th>"
          + "".join("<th>%s %s</th>" % (WD[j], d[5:]) for j, d in enumerate(DATES)) + "</tr>"]
    for R in RS:
        for s in SCENS:
            H.append("<tr><td>%d</td><td style='text-align:left'>%s</td>" % (R, esc(SNAME[s])) + "".join(
                "<td class='%s'>%s</td>" % ("" if day_ok(D[(d, R, s)]) else "inf" + (" bad" if day_unproven(D[(d, R, s)]) else ""), cell_text(D[(d, R, s)])) for d in DATES) + "</tr>")
    H.append("</table>")
    H.append("<h2>(c) Resource profile by type, scenario D</h2>")
    H += ['<h3>R = %d</h3><img src="fleet_resource_L3_R%d.svg" alt="resource R=%d">' % (R, R, R) for R in RS]
    H += ["<h2>(d) Sedan usage timeline, scenario D, R = 60</h2>", '<img src="fleet_sedan_gantt_L3_R60.svg" alt="Gantt">', "</body></html>"]
    with open(os.path.join(FIG, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(H) + "\n")


def main():
    os.makedirs(FIG, exist_ok=True)
    rows, viol = verify_all()
    nw = write_verification(rows, viol)
    write_weekly_md()
    figs = []
    for R in RS:
        fig_scen(os.path.join(FIG, "fleet_scenarios_R%d.svg" % R), R)
        fig_resource(os.path.join(FIG, "fleet_resource_L3_R%d.svg" % R), R)
    fig_scen_all(os.path.join(FIG, "fleet_scenarios_all.svg"))
    fig_heat(os.path.join(FIG, "fleet_daily_heatmap.svg"))
    fig_gantt(os.path.join(FIG, "fleet_sedan_gantt_L3_R60.svg"), 60)
    write_index(figs)
    print("violations:", len(viol), "weekly csv mismatches:", nw)
    for x in viol[:40]:
        print(" ", x)
    for R in RS:
        for s in SCENS:
            w = W[(R, s)]
            print(R, s, w["feasible_days"], w["large"], w["cars"], w["total"], w["per_day"])


if __name__ == "__main__":
    main()
