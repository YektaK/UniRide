#!/usr/bin/env python3
"""Multi-objective (Pareto) analysis of the fleet options of the week 2026-10-05 campaign.
Standard library only. Reuses SVG helpers from plan_resource_profile / plan_schedule_report.

Usage: python scripts/plan_fleet_pareto.py [results_dir]
Reads, from results_dir (default docs/paper/results/week-2026-10-05-fleet) and its extra/L4 and
extra/minivan-cap3 sub-folders: run_manifest.json, scenario_daily.csv, scenario_weekly.csv and the
*_R<R>_<scenario>.response.json route files. Writes pareto_options.csv, pareto_daily.csv, pareto_borrowed_hourly.csv,
pareto_analysis.md, figures/pareto_*.svg and a marked section in figures/index.html.
Every number is recomputed from the routes and cross-checked against the CSVs.

Method: epsilon-constraint. The owned minibus count L and the ride limit R are fixed as
constraints and the borrowed vehicles are minimised (done by the planner, per weekday). This script
only enumerates those results as options and finds the non-dominated ones. Routes are heuristic and
the minimum is proven only over the generated route menus, so the front is an approximation.
"""
import csv
import html
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "paper", "results", "week-2026-10-05-fleet")
MINIVAN_DIR = sys.argv[2] if len(sys.argv) > 2 else "minivan-cap3"  # sub-folder of extra/
sys.argv[1:] = [RES]  # the imported campaign helpers read RES from argv[1]
from plan_resource_profile import PAD, head, write  # noqa: E402
from plan_schedule_report import hm  # noqa: E402

FIG = os.path.join(RES, "figures")
RS = [50, 60, 70, 90]
WD = ["Mon", "Tue", "Wed", "Thu", "Fri"]
MORNING_END = 600  # 10:00
TOUR_LIMIT = 150
FAMS = ["minibus-only", "minibus+sedan", "minibus+minivan", "hybrid"]
FAM_COL = {"minibus-only": "#0072B2", "minibus+sedan": "#E69F00", "minibus+minivan": "#CC79A7", "hybrid": "#009E73"}
FAM_SHAPE = {"minibus-only": "circle", "minibus+sedan": "square", "minibus+minivan": "triangle", "hybrid": "diamond"}
FAM_CODE = {"minibus-only": "A", "minibus+sedan": "S", "minibus+minivan": "V", "hybrid": "H"}
R_DASH = {50: "none", 60: "7 4", 70: "2 3", 90: "9 3 2 3"}
VIRIDIS = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]


def esc(s):
    return html.escape(str(s))


def num(s):
    return int(float(s)) if s not in ("", None) else None


def rd(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ datasets
class DS:
    def __init__(self, name, path, scens):
        self.name, self.path, self.scens = name, path, scens
        with open(os.path.join(path, "run_manifest.json"), encoding="utf-8") as f:
            self.man = json.load(f)
        self.types = {t["typeId"]: t for t in self.man["fleet_types"]}
        self.bor = self.man["minimize_type"]
        self.daily = rd(os.path.join(path, "scenario_daily.csv"))
        self.weekly = rd(os.path.join(path, "scenario_weekly.csv"))
        self.D = {(r["date"], int(r["ride_limit"]), r["scenario"]): r for r in self.daily}
        self.W = {(int(r["ride_limit"]), r["scenario"]): r for r in self.weekly}
        self.dates = sorted({r["date"] for r in self.daily})

    def response(self, date, R, s):
        with open(os.path.join(self.path, "%s_R%d_%s.response.json" % (date, R, s)), encoding="utf-8") as f:
            return json.load(f)


DSS = [DS("main", RES, ["A", "L1", "L2", "L3"]),
       DS("L4", os.path.join(RES, "extra", "L4"), ["L4"]),
       # Corrected minivan model (total capacity 3, DECISION_LOG H03). extra/minivan is superseded.
       DS("minivan", os.path.join(RES, "extra", MINIVAN_DIR), ["L0", "L1", "L2"])]
DATES = DSS[0].dates


# ------------------------------------------------------------------ verification (per run)
def ride_vals(sc):
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


def check_run(ds, full, row, R, s):
    """Violations recomputed from the response routes only (types and cooldowns from the manifest)."""
    sc = full["scenario"]
    v = []
    per = {}
    for r in sc["routes"]:
        per.setdefault((r["vehicleType"], r["physicalVehicleId"]), []).append(r)
    for (t, vid), rs in per.items():
        cd = ds.types[t]["cooldownMinutes"]
        rs.sort(key=lambda r: r["startMinutes"])
        for a, b in zip(rs, rs[1:]):
            if b["startMinutes"] < a["endMinutes"] + cd:
                v.append("cooldown/overlap %s/%s %s->%s" % (t, vid, a["jobId"], b["jobId"]))
    for r in sc["routes"]:
        t = ds.types[r["vehicleType"]]
        ids = r["occurrenceIds"]
        sw = sum(1 for o in ids if o.rsplit(":", 1)[1].startswith("Sw"))
        so = len(ids) - sw
        if (sw, so) != (r["swCount"], r["soCount"]):
            v.append("Sw/So recount %s" % r["jobId"])
        if sw > t["swCapacity"] or so > t["soCapacity"]:
            v.append("capacity %s %s sw/so %d/%d" % (r["vehicleType"], r["jobId"], sw, so))
        if sw + so > t.get("totalCapacity", t["swCapacity"] + t["soCapacity"]):
            v.append("total capacity %s %s sw+so %d > %d" % (r["vehicleType"], r["jobId"], sw + so, t.get("totalCapacity", t["swCapacity"] + t["soCapacity"])))
        total = sum(x["duration"] for x in r["steps"])
        if total != r["minutes"] or r["endMinutes"] - r["startMinutes"] != total or total > TOUR_LIMIT:
            v.append("tour %s %d" % (r["jobId"], total))
    rv = ride_vals(sc)
    if max(rv) > R:
        v.append("ride %d > R=%d" % (max(rv), R))
    seen = [o for r in sc["routes"] for o in r["occurrenceIds"]]
    if sorted(seen) != sorted(full["occurrenceLabels"]) or len(seen) != len(set(seen)):
        v.append("legs not served exactly once")
    if len(seen) != num(row["legs"]):
        v.append("legs != CSV")
    nb = len({k for k in per if k[0] == ds.bor})
    if nb != (num(row["cars"]) or 0):
        v.append("borrowed vehicles %d != CSV cars %s" % (nb, row["cars"]))
    bm = sum(r["minutes"] for r in sc["routes"] if r["vehicleType"] == ds.bor)
    if bm != (num(row["car_vehicle_minutes"]) or 0):
        v.append("borrowed minutes %d != CSV %s" % (bm, row["car_vehicle_minutes"]))
    if sum(1 for r in sc["routes"] if r["vehicleType"] == ds.bor) != (num(row["car_routes"]) or 0):
        v.append("borrowed routes != CSV")
    if abs(sum(rv) / len(rv) - float(row["ride_mean"])) > 1e-4 or max(rv) != num(row["ride_max"]):
        v.append("ride mean/max != CSV")
    if row["date"] != full["serviceDate"] or full["limits"]["maxRideTimeMinutes"] != R:
        v.append("response date/limit mismatch")
    return v


# ------------------------------------------------------------------ per-day metrics
def day_metrics(ds, date, R, s, viol):
    row = ds.D[(date, R, s)]
    if row["status"] != "ok":
        return {"ok": False, "row": row, "ds": ds, "s": s, "date": date, "R": R}
    full = ds.response(date, R, s)
    SHAS.add(full["matrix"]["sha256"])
    for m in check_run(ds, full, row, R, s):
        viol.append("%s %s R=%d %s: %s" % (ds.name, date, R, s, m))
    routes = full["scenario"]["routes"]
    cd = {t: ds.types[t]["cooldownMinutes"] for t in ds.types}
    own = [r for r in routes if r["vehicleType"] != ds.bor]
    bor = [r for r in routes if r["vehicleType"] == ds.bor]
    conc = [0] * 1440
    per = {}
    morning = 0
    for r in bor:
        a, b = r["startMinutes"], r["endMinutes"] + cd[ds.bor]
        for t in range(a, b):
            conc[t] += 1
        morning += max(0, min(b, MORNING_END) - a)
        per.setdefault(r["physicalVehicleId"], []).append((r["startMinutes"], r["endMinutes"]))
    wins = sorted((min(a for a, _ in v), max(b for _, b in v)) for v in per.values())
    return {
        "ok": True, "row": row, "ds": ds, "s": s, "date": date, "R": R,
        "type": ds.bor if bor else "none",
        "nb": len(per),
        "bor_routes": len(bor),
        "bor_route_min": sum(r["minutes"] for r in bor),
        "bor_busy": sum(r["endMinutes"] + cd[ds.bor] - r["startMinutes"] for r in bor),
        "bor_window": sum(b + cd[ds.bor] - a for a, b in wins),
        "bor_morning": morning,
        "conc": conc,
        "windows": wins,
        "own_busy": sum(r["endMinutes"] + cd[r["vehicleType"]] - r["startMinutes"] for r in own),
        "own_vehicles": len({r["physicalVehicleId"] for r in own}),
        "span": (min(r["startMinutes"] for r in routes), max(r["endMinutes"] for r in routes)),
        "ride_mean": float(row["ride_mean"]), "ride_n": num(row["ride_passengers"]),
    }


VIOL = []
SHAS = set()
DAYS = {}  # (dsname, R, s) -> [day metrics x5]
for ds in DSS:
    for R in RS:
        for s in ds.scens:
            DAYS[(ds.name, R, s)] = [day_metrics(ds, d, R, s, VIOL) for d in DATES]
if len(SHAS) != 1:
    VIOL.append("matrix sha256 differs between runs: %s" % sorted(SHAS))
N_CHECKED = sum(1 for v in DAYS.values() for d in v if d["ok"])
N_INFEAS = sum(1 for v in DAYS.values() for d in v if not d["ok"])

# common service span per (date, R): earliest start .. latest end over all options (same denominator everywhere)
SPAN = {}
for (nm, R, s), days in DAYS.items():
    for d in days:
        if d["ok"]:
            a, b = SPAN.get((d["date"], R), (10 ** 9, 0))
            SPAN[(d["date"], R)] = (min(a, d["span"][0]), max(b, d["span"][1]))


# ------------------------------------------------------------------ options
def build(family, L, R, days, label, sources, derived=False):
    o = {"family": family, "L": L, "R": R, "label": label, "sources": sources, "derived": derived, "days": days}
    ok = [d for d in days if d["ok"]]
    o["feasible_days"] = len(ok)
    o["feasible"] = len(ok) == len(days)
    o["id"] = "R%d_%s_L%s" % (R, family, L) if family != "minibus-only" else "R%d_minibus-only" % R
    if not o["feasible"]:
        return o
    o["proven"] = all((d["row"]["large_vehicles_proven"] == "true") if d["s"] == "A" else
                      (d["row"]["cars_status"] == "proven_over_menu" and d["row"]["assignment_status"] == "proven") for d in days)
    o["f1"] = L
    o["nb"] = [d["nb"] for d in days]
    o["f2"] = max(o["nb"])
    o["f2c"] = max(max(d["conc"]) for d in days)
    o["f3m"] = sum(d["bor_busy"] for d in days)
    o["f3"] = o["f3m"] / 60.0
    o["route_h"] = sum(d["bor_route_min"] for d in days) / 60.0
    o["window_h"] = sum(d["bor_window"] for d in days) / 60.0
    o["f4"] = sum(1 for n in o["nb"] if n > 0)
    o["vdays"] = sum(o["nb"])
    o["mean_ride"] = sum(d["ride_mean"] * d["ride_n"] for d in days) / sum(d["ride_n"] for d in days)
    o["util_own"] = (sum(d["own_busy"] for d in days) / (L * sum(SPAN[(d["date"], R)][1] - SPAN[(d["date"], R)][0] for d in days))) if L > 0 else None
    o["util_bor"] = (o["f3m"] / sum(d["bor_window"] for d in days)) if o["f3m"] else None
    o["morning"] = (sum(d["bor_morning"] for d in days) / o["f3m"]) if o["f3m"] else None
    o["morning_h"] = sum(d["bor_morning"] for d in days) / 60.0
    o["h_sedan"] = sum(d["bor_busy"] for d in days if d["type"] == "sedan") / 60.0
    o["h_minivan"] = sum(d["bor_busy"] for d in days if d["type"] == "minivan") / 60.0
    o["minivan_days"] = sum(1 for d in days if d["type"] == "minivan")
    o["sedan_days"] = sum(1 for d in days if d["type"] == "sedan")
    o["types"] = [d["type"] for d in days]
    o["days_typed"] = "/".join("%d%s" % (d["nb"], {"sedan": "s", "minivan": "v"}.get(d["type"], "")) for d in days)
    return o


OPTS = []
for R in RS:
    d = DAYS[("main", R, "A")]
    L_A = max(num(x["row"]["large_vehicles"]) for x in d)
    OPTS.append(build("minibus-only", L_A, R, d, "A", ["main:A"]))
    for s in ("L1", "L2", "L3"):
        OPTS.append(build("minibus+sedan", int(s[1:]), R, DAYS[("main", R, s)], s, ["main:" + s]))
    OPTS.append(build("minibus+sedan", 4, R, DAYS[("L4", R, "L4")], "L4", ["L4:L4"]))
    for s in ("L0", "L1", "L2"):
        OPTS.append(build("minibus+minivan", int(s[1:]), R, DAYS[("minivan", R, s)], s, ["minivan:" + s]))
    # day-level hybrid: sedan result on days where L+sedan is feasible, minivan result on the other days.
    for L in (1, 2):
        sd, mv = DAYS[("main", R, "L%d" % L)], DAYS[("minivan", R, "L%d" % L)]
        days = [a if a["ok"] else b for a, b in zip(sd, mv)]
        used_sedan = sum(1 for a in sd if a["ok"])
        if 0 < used_sedan < 5 and all(x["ok"] for x in days):
            o = build("hybrid", L, R, days, "L%d hybrid" % L, ["main:L%d" % L, "minivan:L%d" % L], derived=True)
            o["hyb_sedan_days"] = used_sedan
            OPTS.append(o)
        elif 0 < used_sedan < 5:
            o = build("hybrid", L, R, days, "L%d hybrid" % L, ["main:L%d" % L, "minivan:L%d" % L], derived=True)
            OPTS.append(o)
FEAS = [o for o in OPTS if o["feasible"]]
for o in FEAS:
    o.setdefault("hyb_sedan_days", None)
    if o["derived"]:
        continue
    # weekly CSV cross-check of the weekly objectives recomputed from the routes
    ds = o["days"][0]["ds"]
    wk = ds.W[(o["R"], o["days"][0]["s"])]
    if o["family"] == "minibus-only":
        if num(wk["weekly_large_vehicles"]) != o["f1"]:
            VIOL.append("%s: f1 %d != weekly CSV %s" % (o["id"], o["f1"], wk["weekly_large_vehicles"]))
    else:
        if num(wk["weekly_cars"]) != o["f2"] or num(wk["car_vehicle_minutes"]) != round(o["route_h"] * 60) or num(wk["cars_day_sum"]) != o["vdays"]:
            VIOL.append("%s: borrowed max/minutes/day-sum %s/%s/%s != weekly CSV %s/%s/%s" % (
                o["id"], o["f2"], round(o["route_h"] * 60), o["vdays"], wk["weekly_cars"], wk["car_vehicle_minutes"], wk["cars_day_sum"]))
    if abs(float(wk["ride_mean"]) - o["mean_ride"]) > 1e-4:
        VIOL.append("%s: mean ride %.5f != weekly CSV %s" % (o["id"], o["mean_ride"], wk["ride_mean"]))
for o in OPTS:
    if not o["derived"]:
        ds = o["days"][0]["s"], o["days"][0]["ds"]
        wk = ds[1].W[(o["R"], ds[0])]
        if (wk["complete_week"] == "true") != o["feasible"]:
            VIOL.append("%s: feasibility %s != weekly CSV complete_week %s" % (o["id"], o["feasible"], wk["complete_week"]))


def dominates(a, b):
    return all(x <= y for x, y in zip(a, b)) and a != b


def mark(items, name, key, group=lambda o: 0):
    for o in items:
        o[name] = not any(dominates(key(p), key(o)) for p in items if p is not o and group(p) == group(o))


mark(FEAS, "nd_R", lambda o: (o["f1"], o["f2"], o["f3m"]), lambda o: o["R"])
mark(FEAS, "nd_R4", lambda o: (o["f1"], o["f2"], o["f3m"], o["f4"]), lambda o: o["R"])
mark(FEAS, "nd_glob", lambda o: (o["f1"], o["f2"], o["f3m"], o["R"]))
mark(FEAS, "nd_globmean", lambda o: (o["f1"], o["f2"], o["f3m"], o["mean_ride"]))
mark(FEAS, "nd_R_route", lambda o: (o["f1"], o["f2"], round(o["route_h"] * 60)), lambda o: o["R"])
mark(FEAS, "nd_R_window", lambda o: (o["f1"], o["f2"], round(o["window_h"] * 60)), lambda o: o["R"])
mark(FEAS, "nd_R_conc", lambda o: (o["f1"], o["f2c"], o["f3m"]), lambda o: o["R"])
for o in FEAS:
    o["dom_by"] = ";".join(p["id"] for p in FEAS if p is not o and p["R"] == o["R"] and dominates((p["f1"], p["f2"], p["f3m"]), (o["f1"], o["f2"], o["f3m"])))


def pct(x):
    return "" if x is None else "%.1f" % (100 * x)


def write_csvs():
    cols = ["option_id", "family", "derived", "source_runs", "owned_L", "ride_limit", "feasible", "feasible_days", "proven_over_menu",
            "f1_owned_minibuses", "f2_peak_borrowed_vehicles_day", "f3_borrowed_vehicle_hours_week", "f4_borrowed_days_week",
            "f5_ride_limit_min", "f5_mean_ride_min", "peak_concurrent_borrowed", "borrowed_vehicle_days", "borrowed_per_day_Mon_Fri",
            "borrowed_route_hours", "borrowed_window_hours", "minibus_utilisation_pct", "borrowed_utilisation_pct",
            "borrowed_before_10_share_pct", "borrowed_before_10_hours",
            "borrowed_sedan_hours", "borrowed_minivan_hours", "days_with_minivan",
            "nondominated_per_R_f1f2f3", "nondominated_per_R_f1f2f3f4", "nondominated_global_f1f2f3R", "nondominated_global_f1f2f3meanride",
            "nondominated_per_R_route_hours", "nondominated_per_R_window_hours", "nondominated_per_R_concurrent_peak",
            "dominated_per_R", "dominated_by"]
    with open(os.path.join(RES, "pareto_options.csv"), "w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for o in OPTS:
            if not o["feasible"]:
                w.writerow([o["id"], o["family"], str(o["derived"]).lower(), "+".join(o["sources"]), o["L"], o["R"], "false", o["feasible_days"]] + [""] * (len(cols) - 8))
                continue
            b = lambda x: str(bool(x)).lower()
            w.writerow([o["id"], o["family"], b(o["derived"]), "+".join(o["sources"]), o["L"], o["R"], "true", o["feasible_days"], b(o["proven"]),
                        o["f1"], o["f2"], "%.2f" % o["f3"], o["f4"], o["R"], "%.2f" % o["mean_ride"], o["f2c"], o["vdays"],
                        "/".join(str(n) for n in o["nb"]) if o["family"] != "hybrid" else o["days_typed"],
                        "%.2f" % o["route_h"], "%.2f" % o["window_h"], pct(o["util_own"]), pct(o["util_bor"]), pct(o["morning"]), "%.2f" % o["morning_h"],
                        "%.2f" % o["h_sedan"], "%.2f" % o["h_minivan"], o["minivan_days"],
                        b(o["nd_R"]), b(o["nd_R4"]), b(o["nd_glob"]), b(o["nd_globmean"]), b(o["nd_R_route"]), b(o["nd_R_window"]), b(o["nd_R_conc"]),
                        b(not o["nd_R"]), o["dom_by"]])
    cols = ["option_id", "date", "weekday", "borrowed_type_used", "borrowed_vehicles", "borrowed_busy_minutes_incl_cooldown", "borrowed_route_minutes",
            "borrowed_window_minutes", "borrowed_before_10_minutes", "peak_concurrent_borrowed", "peak_concurrent_first_at", "borrowed_vehicle_windows", "owned_busy_minutes_incl_cooldown"]
    with open(os.path.join(RES, "pareto_daily.csv"), "w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for o in FEAS:
            for j, d in enumerate(o["days"]):
                w.writerow([o["id"], d["date"], WD[j], d["type"], d["nb"], d["bor_busy"], d["bor_route_min"], d["bor_window"], d["bor_morning"],
                            max(d["conc"]), hm(d["conc"].index(max(d["conc"]))) if max(d["conc"]) else "", ";".join("%s-%s" % (hm(a), hm(b)) for a, b in d["windows"]), d["own_busy"]])
    with open(os.path.join(RES, "pareto_borrowed_hourly.csv"), "w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["option_id", "date", "weekday", "clock_hour", "max_concurrent_borrowed_in_use"])
        for o in FEAS:
            for j, d in enumerate(o["days"]):
                for hh in range(24):
                    v = max(d["conc"][hh * 60:(hh + 1) * 60])
                    if v:
                        w.writerow([o["id"], d["date"], WD[j], "%02d:00" % hh, v])


def fam_label(o):
    return {"minibus-only": "minibus-only", "minibus+sedan": "L%d + sedan" % o["L"], "minibus+minivan": "L%d + minivan" % o["L"],
            "hybrid": "L%d + sedan/minivan (hybrid)" % o["L"]}[o["family"]]


def short(o):
    return "A" if o["family"] == "minibus-only" else "%s%d" % (FAM_CODE[o["family"]], o["L"])


# ------------------------------------------------------------------ figure helpers
def marker(shape, cx, cy, r, fill, op=1.0, stroke="#fff", sw=1.0, title=""):
    t = "<title>%s</title>" % esc(title) if title else ""
    a = 'fill="%s" fill-opacity="%g" stroke="%s" stroke-width="%g"' % (fill, op, stroke, sw)
    if shape == "circle":
        return '<circle cx="%g" cy="%g" r="%g" %s>%s</circle>' % (cx, cy, r, a, t)
    if shape == "square":
        return '<rect x="%g" y="%g" width="%g" height="%g" %s>%s</rect>' % (cx - r, cy - r, 2 * r, 2 * r, a, t)
    if shape == "triangle":
        return '<polygon points="%g,%g %g,%g %g,%g" %s>%s</polygon>' % (cx, cy - r * 1.2, cx - r * 1.1, cy + r * 0.9, cx + r * 1.1, cy + r * 0.9, a, t)
    return '<polygon points="%g,%g %g,%g %g,%g %g,%g" %s>%s</polygon>' % (cx, cy - r * 1.25, cx + r * 1.25, cy, cx, cy + r * 1.25, cx - r * 1.25, cy, a, t)


def opt_title(o):
    return "%s, R=%d: owned %d, peak borrowed %d, %.1f borrowed h/week, %d borrowed days, mean ride %.1f min" % (
        fam_label(o), o["R"], o["f1"], o["f2"], o["f3"], o["f4"], o["mean_ride"])


def fam_legend(out, x, y, hybrid=True):
    for fam in FAMS if hybrid else FAMS[:3]:
        out.append(marker(FAM_SHAPE[fam], x + 7, y + 6, 6, FAM_COL[fam], 1, "#fff"))
        txt = {"minibus-only": "A: minibuses only", "minibus+sedan": "S: minibuses + sedans (no Sw)",
               "minibus+minivan": "V: minibuses + minivans (3 seats, max 1 Sw)", "hybrid": "H: day-level hybrid"}[fam]
        out.append('<text x="%g" y="%g" font-size="12" fill="#222">%s</text>' % (x + 18, y + 10, esc(txt)))
        x += 24 + 7 * len(txt)


def viridis(t):
    t = max(0.0, min(1.0, t)) * (len(VIRIDIS) - 1)
    i = min(int(t), len(VIRIDIS) - 2)
    f = t - i
    c = [round(VIRIDIS[i][k] + (VIRIDIS[i + 1][k] - VIRIDIS[i][k]) * f) for k in range(3)]
    return "#%02x%02x%02x" % tuple(c)


def rad(o):
    return 5 + 3.4 * math.sqrt(o["f2"])


YH = max(o["f3"] for o in FEAS)
YMAXH = math.ceil(YH / 10.0) * 10
XMAXL = max(o["f1"] for o in FEAS)


def pareto_panel(out, x0, y0, w, h, items, title, combined=False):
    out.append('<text x="%g" y="%g" font-size="14" font-weight="bold" fill="#111">%s</text>' % (x0, y0 - 10, esc(title)))
    out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#fff" stroke="#888" stroke-width="0.8"/>' % (x0, y0, w, h))
    X = lambda v: x0 + 24 + (w - 48) * v / float(XMAXL)
    Y = lambda v: y0 + h - 18 - (h - 36) * v / float(YMAXH)
    for v in range(0, YMAXH + 1, 10):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#e6e6e6" stroke-width="0.7"/><text x="%g" y="%g" font-size="11" text-anchor="end" fill="#333">%d</text>' % (
            x0, Y(v), x0 + w, Y(v), x0 - 4, Y(v) + 4, v))
    for v in range(0, XMAXL + 1):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#f0f0f0" stroke-width="0.7"/><text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#333">%d</text>' % (
            X(v), y0, X(v), y0 + h, X(v), y0 + h + 14, v))
    out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#222">Owned minibuses (f1)</text>' % (x0 + w / 2, y0 + h + 29))
    out.append('<text transform="rotate(-90 %g %g)" x="%g" y="%g" font-size="11" text-anchor="middle" fill="#222">Borrowed vehicle-hours per week (f3)</text>' % (
        x0 - 32, y0 + h / 2, x0 - 32, y0 + h / 2))
    for R in sorted({o["R"] for o in items}):
        nd = sorted([o for o in items if o["nd_R"] and o["R"] == R], key=lambda o: (o["f1"], o["f3"]))
        if len(nd) > 1:
            out.append('<polyline points="%s" fill="none" stroke="#555" stroke-width="1.4" stroke-dasharray="%s"/>' % (
                " ".join("%g,%g" % (X(o["f1"]), Y(o["f3"])) for o in nd), R_DASH[R] if combined else "5 3"))
    if combined:
        for k, R in enumerate(RS):
            out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#555" stroke-width="1.4" stroke-dasharray="%s"/><text x="%g" y="%g" font-size="11" fill="#222">R=%d front</text>' % (
                x0 + w - 330 + k * 82, y0 + 16, x0 + w - 306 + k * 82, y0 + 16, R_DASH[R], x0 + w - 300 + k * 82, y0 + 20, R))
    for o in sorted(items, key=lambda o: (o["nd_R"], -rad(o))):
        on = o["nd_R"]
        glob = combined and o["nd_glob"]
        out.append(marker(FAM_SHAPE[o["family"]], X(o["f1"]), Y(o["f3"]), rad(o) * (0.8 if combined else 1), FAM_COL[o["family"]], 0.9 if on else 0.2,
                          "#000" if glob else ("#222" if on else "#aaa"), 2.4 if glob else (1.0 if on else 0.6), opt_title(o) + ("; non-dominated" if on else "; dominated")))
        if not combined or glob:
            lab =short(o) + ("@%d" % o["R"] if combined else "")
            out.append('<text x="%g" y="%g" font-size="10" fill="%s" stroke="#fff" stroke-width="2.4" paint-order="stroke">%s</text>' % (
                X(o["f1"]) + rad(o) * (0.8 if combined else 1) + 2, Y(o["f3"]) + 3, "#111" if on else "#999", esc(lab)))


def fig_pareto_small(path):
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (PAD, esc("Pareto front per ride limit R: owned minibuses vs borrowed vehicle-hours per week")),
           '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (PAD, esc("Bubble size grows with peak borrowed vehicles on the busiest day (f2). Solid = non-dominated on (f1, f2, f3); faint = dominated. Dashed line joins the non-dominated points of that R (visual guide).")),
           '<text x="%d" y="58" font-size="12" fill="#444">%s</text>' % (PAD, esc("Labels: A = minibuses only; S/V/H + L = owned minibuses with sedans / minivans / day-level hybrid. Infeasible options are not drawn."))]
    fam_legend(out, PAD, 70)
    for i, R in enumerate(RS):
        pareto_panel(out, 70 + (i % 2) * 500, 130 + (i // 2) * 360, 430, 290, [o for o in FEAS if o["R"] == R], "R = %d min" % R)
    write(path, 1040, 130 + 2 * 360 - 10, out)


def fig_pareto_combined(path):
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (PAD, esc("Pareto options for all ride limits R (combined)")),
           '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (PAD, esc("Labels name option@R. Solid = non-dominated for its own R; black ring = non-dominated globally on (f1, f2, f3, R); faint = dominated.")),
           '<text x="%d" y="58" font-size="12" fill="#444">%s</text>' % (PAD, esc("Bubble size grows with peak borrowed vehicles (f2)."))]
    fam_legend(out, PAD, 70)
    pareto_panel(out, 70, 130, 900, 520, FEAS, "All feasible options, R = 50, 60, 70, 90", combined=True)
    write(path, 1010, 130 + 520 + 50, out)


def fig_service(path):
    ms = [o["mean_ride"] for o in FEAS]
    lo, hi = math.floor(min(ms)) - 1, math.ceil(max(ms)) + 1
    x0, y0, w, h = 80, 120, 820, 400
    X = lambda v: x0 + w * (v - lo) / float(hi - lo)
    Y = lambda v: y0 + h - 25 - (h - 50) * v / float(XMAXL)
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (PAD, esc("Service level vs owned minibuses (colour = borrowed vehicle-hours per week)")),
           '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (PAD, esc("x = realised mean ride (passenger-weighted, week). The four clusters are R = 50, 60, 70, 90; a small vertical offset separates families at the same L.")),
           '<text x="%d" y="58" font-size="12" fill="#444">%s</text>' % (PAD, esc("Shape = family; black outline = non-dominated for its R, grey outline = dominated."))]
    fam_legend(out, PAD, 70)
    out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#fff" stroke="#888" stroke-width="0.8"/>' % (x0, y0, w, h))
    for v in range(0, XMAXL + 1):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#eee"/><text x="%g" y="%g" font-size="11" text-anchor="end" fill="#333">%d</text>' % (x0, Y(v), x0 + w, Y(v), x0 - 5, Y(v) + 4, v))
    for v in range(lo, hi + 1, 2):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#f0f0f0"/><text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#333">%d</text>' % (X(v), y0, X(v), y0 + h, X(v), y0 + h + 14, v))
    out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Mean ride (min), lower = better service</text>' % (x0 + w / 2, y0 + h + 32))
    out.append('<text transform="rotate(-90 28 %g)" x="28" y="%g" font-size="12" text-anchor="middle" fill="#222">Owned minibuses (f1)</text>' % (y0 + h / 2, y0 + h / 2))
    off = {"minibus-only": 0, "minibus+sedan": -0.18, "minibus+minivan": 0.18, "hybrid": 0.0}
    for R in RS:
        rs = [o["mean_ride"] for o in FEAS if o["R"] == R]
        out.append('<text x="%g" y="%g" font-size="12" font-weight="bold" text-anchor="middle" fill="#111">R=%d</text>' % (X(sum(rs) / len(rs)), y0 + 16, R))
    for o in FEAS:
        col = viridis(o["f3"] / YMAXH)
        cx, cy = X(o["mean_ride"]), Y(o["f1"] + off[o["family"]])
        m = marker(FAM_SHAPE[o["family"]], cx, cy, 7, col, 1, "#111" if o["nd_R"] else "#777", 1.4, opt_title(o))
        out.append(m)
    bx = x0 + w + 30
    for i in range(0, 101):
        out.append('<rect x="%g" y="%g" width="16" height="4.2" fill="%s"/>' % (bx, y0 + h - 25 - i * 3.4, viridis(i / 100.0)))
    for v in range(0, YMAXH + 1, 10):
        out.append('<text x="%g" y="%g" font-size="11" fill="#333">%d h</text>' % (bx + 22, y0 + h - 25 - 3.4 * 100 * v / YMAXH + 3, v))
    out.append('<text x="%g" y="%g" font-size="11" fill="#222">borrowed h/week (f3)</text>' % (bx - 10, y0 + h - 25 - 360))
    write(path, x0 + w + 140, y0 + h + 50, out)


def fig_heat(path, keys, R=60):
    sel = []
    for fam, L in keys:
        for o in FEAS:
            if o["R"] == R and o["family"] == fam and o["L"] == L:
                sel.append(o)
    if not sel:
        return []
    hrs = [t // 60 for o in sel for d in o["days"] for t in range(1440) if d["conc"][t]]
    h0, h1 = min(hrs), max(hrs)
    vmax = max(max(d["conc"]) for o in sel for d in o["days"])
    cw, ch, gx = 54, 24, 70
    pw = cw * 5 + 40
    cols = 2 if len(sel) > 2 else len(sel)
    rows = (len(sel) + cols - 1) // cols
    ph = (h1 - h0 + 1) * ch + 70
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (PAD, esc("Borrowed-vehicle demand by hour and weekday, R = %d min" % R)),
           '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (PAD, esc("Cell = most borrowed vehicles in use at once within the clock hour (route + 10-min cooldown); blank = none.")),
           '<text x="%d" y="58" font-size="12" fill="#444">%s</text>' % (PAD, esc("Monday to Friday of 2026-10-05..09; same colour scale in all panels; dashed line = 10:00."))]
    for i, o in enumerate(sel):
        px, py = PAD + (i % cols) * (gx + pw), 90 + (i // cols) * ph
        out.append('<text x="%g" y="%g" font-size="13" font-weight="bold" fill="%s">%s</text>' % (px, py + 4, "#111", esc("%s: %d borrowed h/week, peak %d" % (fam_label(o), round(o["f3"] * 10) / 10.0, o["f2"]))))
        for j in range(5):
            out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#333">%s</text>' % (px + gx + cw * (j + 0.5), py + 24, WD[j]))
        for k, hh in enumerate(range(h0, h1 + 1)):
            y = py + 32 + k * ch
            out.append('<text x="%g" y="%g" font-size="11" text-anchor="end" fill="#333">%02d:00</text>' % (px + gx - 6, y + ch / 2 + 4, hh))
            for j, d in enumerate(o["days"]):
                v = max(d["conc"][hh * 60:(hh + 1) * 60])
                if v:
                    t = 0.15 + 0.85 * v / float(vmax)
                    fill = "rgb(%d,%d,%d)" % (round(255 - 235 * t), round(255 - 140 * t), round(255 - 30 * t))
                else:
                    fill = "#f4f4f4"
                out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" stroke="#fff"><title>%s</title></rect>' % (
                    px + gx + cw * j, y, cw, ch, fill, esc("%s %02d:00-%02d:59: up to %d borrowed in use" % (WD[j], hh, hh, v))))
                if v:
                    out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="%s">%d</text>' % (px + gx + cw * (j + 0.5), y + ch / 2 + 4, "#fff" if t > 0.55 else "#111", v))
        if h0 <= 10 <= h1:
            yy = py + 32 + (10 - h0) * ch
            out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#111" stroke-dasharray="4 3" stroke-width="1.4"/>' % (px + gx, yy, px + gx + cw * 5, yy))
    write(path, max(PAD + cols * (gx + pw), 700), 90 + rows * ph, out)
    return sel


def fig_parallel(path):
    axes = [("f1 owned minibuses", lambda o: o["f1"], "%d"), ("f2 peak borrowed", lambda o: o["f2"], "%d"),
            ("f3 borrowed h/week", lambda o: o["f3"], "%.0f"), ("f4 borrowed days", lambda o: o["f4"], "%d"),
            ("R (ride limit)", lambda o: o["R"], "%d"), ("mean ride (min)", lambda o: o["mean_ride"], "%.1f")]
    x0, y0, w, h = 90, 150, 900, 380
    xs = [x0 + w * i / float(len(axes) - 1) for i in range(len(axes))]
    rng = [(min(f(o) for o in FEAS), max(f(o) for o in FEAS)) for _, f, _ in axes]
    Y = lambda i, v: y0 + h - h * (v - rng[i][0]) / float(rng[i][1] - rng[i][0] or 1)
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (PAD, esc("Parallel coordinates of the objectives f1..f5, all feasible options")),
           '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (PAD, esc("Every axis is minimised: bottom = better. One line per option (hover for details). Solid = non-dominated on (f1, f2, f3) for its R; dashed = dominated. Colour and marker = family.")),
           '<text x="%d" y="58" font-size="12" fill="#444">%s</text>' % (PAD, esc("f5 = service level, shown as the ride limit R and the realised weekly mean ride."))]
    fam_legend(out, PAD, 70)
    for i, (nm, f, fmt) in enumerate(axes):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#333" stroke-width="1.4"/>' % (xs[i], y0, xs[i], y0 + h))
        out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" font-weight="bold" fill="#111">%s</text>' % (xs[i], y0 - 14, esc(nm)))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#333">%s</text>' % (xs[i], y0 + h + 16, fmt % rng[i][0]))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#333">%s</text>' % (xs[i], y0 - 1, fmt % rng[i][1]))
    for o in sorted(FEAS, key=lambda o: o["nd_R"]):
        pts = " ".join("%g,%g" % (xs[i], Y(i, f(o))) for i, (_, f, _) in enumerate(axes))
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g" stroke-opacity="%g" stroke-dasharray="%s"><title>%s</title></polyline>' % (
            pts, FAM_COL[o["family"]], 2.2 if o["nd_R"] else 1.4, 0.8 if o["nd_R"] else 0.6, "none" if o["nd_R"] else "4 3", esc(opt_title(o) + ("; non-dominated" if o["nd_R"] else "; dominated"))))
        out.append(marker(FAM_SHAPE[o["family"]], xs[0], Y(0, o["f1"]), 4, FAM_COL[o["family"]], 0.9, "#fff", 0.6))
    write(path, x0 + w + 80, y0 + h + 40, out)


def fig_util(path):
    rowh = 17
    rows = {R: sorted([o for o in FEAS if o["R"] == R], key=lambda o: (o["f1"], FAMS.index(o["family"]))) for R in RS}
    x0 = 190
    cwid = [150, 150, 110]
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (PAD, esc("Utilisation per option: minibuses, borrowed hours and borrowed days")),
           '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (PAD, esc("Minibus utilisation = owned busy minutes (route + cooldown) / (owned minibuses x common daily service span). Borrowed hours = f3. Borrowed days = f4.")),
           '<text x="%d" y="58" font-size="12" fill="#444">%s</text>' % (PAD, esc("Right-hand numbers: borrowed utilisation (busy / time on loan, first start to last end) and share of borrowed time before 10:00."))]
    fam_legend(out, PAD, 70)
    y = 110
    for R in RS:
        out.append('<text x="%d" y="%g" font-size="13" font-weight="bold" fill="#111">R = %d min</text>' % (PAD, y, R))
        xs = [x0, x0 + cwid[0] + 30, x0 + cwid[0] + cwid[1] + 60]
        for k, t in enumerate(["minibus utilisation %", "borrowed vehicle-hours/week", "borrowed days/week"]):
            out.append('<text x="%g" y="%g" font-size="11" fill="#333">%s</text>' % (xs[k], y, esc(t)))
        out.append('<text x="%g" y="%g" font-size="11" fill="#333">borrowed util. %% / before 10:00 %%</text>' % (xs[2] + cwid[2] + 20, y))
        y += 8
        for o in rows[R]:
            out.append('<text x="%g" y="%g" font-size="12" text-anchor="end" fill="#111">%s</text>' % (x0 - 8, y + 12, esc(fam_label(o))))
            if o["util_own"] is None:
                out.append('<text x="%g" y="%g" font-size="11" fill="#777">n/a (no minibus)</text>' % (xs[0], y + 12))
            else:
                out.append('<rect x="%g" y="%g" width="%g" height="12" fill="#f0f0f0"/><rect x="%g" y="%g" width="%g" height="12" fill="#0072B2"><title>%s</title></rect>' % (
                    xs[0], y + 2, cwid[0], xs[0], y + 2, cwid[0] * o["util_own"], esc(opt_title(o))))
                out.append('<text x="%g" y="%g" font-size="11" fill="#111">%.0f%%</text>' % (xs[0] + cwid[0] * o["util_own"] + 4, y + 12, 100 * o["util_own"]))
            out.append('<rect x="%g" y="%g" width="%g" height="12" fill="#f0f0f0"/><rect x="%g" y="%g" width="%g" height="12" fill="%s"/>' % (
                xs[1], y + 2, cwid[1], xs[1], y + 2, cwid[1] * o["f3"] / YMAXH, FAM_COL[o["family"]]))
            out.append('<text x="%g" y="%g" font-size="11" fill="#111">%.1f</text>' % (xs[1] + cwid[1] * o["f3"] / YMAXH + 4, y + 12, o["f3"]))
            out.append('<rect x="%g" y="%g" width="%g" height="12" fill="#f0f0f0"/><rect x="%g" y="%g" width="%g" height="12" fill="%s"/>' % (
                xs[2], y + 2, cwid[2], xs[2], y + 2, cwid[2] * o["f4"] / 5.0, FAM_COL[o["family"]]))
            out.append('<text x="%g" y="%g" font-size="11" fill="#111">%d</text>' % (xs[2] + cwid[2] * o["f4"] / 5.0 + 4, y + 12, o["f4"]))
            if o["util_bor"] is not None:
                out.append('<text x="%g" y="%g" font-size="11" fill="#111">%.0f%% / %.0f%%</text>' % (xs[2] + cwid[2] + 20, y + 12, 100 * o["util_bor"], 100 * o["morning"]))
            y += rowh
        y += 34
    write(path, x0 + sum(cwid) + 330, y, out)


def update_index(figs):
    p = os.path.join(FIG, "index.html")
    with open(p, encoding="utf-8") as f:
        txt = f.read()
    a, b = "<!-- PARETO-START -->", "<!-- PARETO-END -->"
    if a in txt:
        txt = txt[:txt.index(a)] + txt[txt.index(b) + len(b):].lstrip("\n")
    sec = [a, "<h2>(e) Multi-objective (Pareto) analysis of fleet options</h2>",
           "<p>Generated by scripts/plan_fleet_pareto.py. Epsilon-constraint method (L and R fixed, borrowed vehicles minimised per weekday); heuristic routes, so the front is an approximation. "
           "Tables: <a href='../pareto_analysis.md'>pareto_analysis.md</a>, <a href='../pareto_options.csv'>pareto_options.csv</a>. Descriptive only; no cost claim. "
           "Re-run this script after plan_fleet_scenarios.py, which rewrites this page.</p>"]
    for fn, cap in figs:
        sec.append("<h3>%s</h3><img src=\"%s\" alt=\"%s\">" % (esc(cap), fn, esc(cap)))
    sec.append(b)
    i = txt.rindex("</body>")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt[:i] + "\n".join(sec) + "\n" + txt[i:])


KEY_HEAT = [("minibus+minivan", 2), ("minibus+sedan", 3), ("minibus+sedan", 4), ("hybrid", 2)]


def figures():
    os.makedirs(FIG, exist_ok=True)
    fig_pareto_small(os.path.join(FIG, "pareto_front_by_R.svg"))
    fig_pareto_combined(os.path.join(FIG, "pareto_front_combined.svg"))
    fig_service(os.path.join(FIG, "pareto_service_vs_minibuses.svg"))
    sel = fig_heat(os.path.join(FIG, "pareto_borrowed_heatmap_R60.svg"), KEY_HEAT, 60)
    fig_parallel(os.path.join(FIG, "pareto_parallel_coordinates.svg"))
    fig_util(os.path.join(FIG, "pareto_utilisation.svg"))
    figs = [("pareto_front_by_R.svg", "Fig. 1a: Pareto front per R (small multiples)"),
            ("pareto_front_combined.svg", "Fig. 1b: Pareto options, all R combined"),
            ("pareto_service_vs_minibuses.svg", "Fig. 2: Service level (mean ride) vs owned minibuses"),
            ("pareto_borrowed_heatmap_R60.svg", "Fig. 3: Borrowed-vehicle demand by hour and weekday, R = 60"),
            ("pareto_parallel_coordinates.svg", "Fig. 4: Parallel coordinates f1..f5"),
            ("pareto_utilisation.svg", "Fig. 5: Utilisation per option")]
    update_index(figs)
    return sel


def mdt(head_, rows):
    return ["| " + " | ".join(head_) + " |", "|" + "---|" * len(head_)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def ids(items):
    return ", ".join(sorted((short(o) + "@" + str(o["R"])) for o in items))


def write_md():
    by = lambda R: sorted([o for o in OPTS if o["R"] == R], key=lambda o: (o["f1"] if o["feasible"] else 99, FAMS.index(o["family"]), o["L"]))
    f = lambda o: o["feasible"]
    o_ = {(o["family"], o["L"], o["R"]): o for o in OPTS}
    pg = lambda x: "-" if x is None else "%.0f%%" % (100 * x)
    out = ["# Pareto analysis of fleet options, week of %s" % DATES[0], "",
           "Generated by `scripts/plan_fleet_pareto.py` from the archived campaign files; every number below is recomputed from the route files and cross-checked against the CSVs "
           "(`pareto_options.csv`: one row per option; `pareto_daily.csv`: one row per option and weekday). Descriptive only: no cost, superiority or causality claim.", "",
           "## 1. Method", "",
           "**Epsilon-constraint method.** An option is a pair (owned minibus count L, ride limit R) plus a family. L and R are fixed as constraints; for every weekday "
           "the planner then minimises the number of borrowed vehicles (sedans or minivans) over the generated route menus and assigns the chosen routes to physical vehicles exactly. "
           "A week is feasible only if all five weekdays are feasible. The objectives below are then read off the routes; the options are compared by Pareto dominance "
           "(option a dominates b if a is no worse on every objective and strictly better on at least one; equal vectors do not dominate each other). All objectives are minimised.", "",
           "Limits of the front: (i) the routes come from a heuristic (GA), and the borrowed-vehicle minimum is proven only over the generated menus, so the front is an approximation, not the true Pareto set of the problem; "
           "(ii) the planner minimises the borrowed vehicle **count** per day; f3 and f4 are consequences of that choice and are not themselves minimised, so a different tie-break among count-minimal plans could change f3; "
           "(iii) L takes only the values that were run (A, L1..L4 with sedans, L0..L2 with minivans); (iv) one week, one matrix, one seed.", "",
           "## 2. Objectives and definitions", ""]
    out += mdt(["Symbol", "Definition"], [
        ["f1", "owned minibuses (L; for option A the largest daily minimum, as in the campaign)"],
        ["f2", "peak borrowed vehicles on the busiest weekday (distinct borrowed vehicles used that day, maximum over Mon..Fri)"],
        ["f3", "**borrowed vehicle-hours per week** = sum over borrowed routes of (route minutes + 10-min cooldown after the route), over all five days, divided by 60. This is the same busy definition (route + cooldown) as the resource-profile figures. Route minutes only (`borrowed_route_hours`) and the time on loan from first start to last end plus cooldown (`borrowed_window_hours`) are also reported; section 6 shows that the non-dominated sets do not depend on this choice"],
        ["f4", "borrowed vehicle-days per week = number of weekdays on which at least one borrowed vehicle is needed (0..5); the sum of vehicles over days is `borrowed_vehicle_days`"],
        ["f5", "service level = ride limit R (minutes, lower is stricter) and the realised passenger-weighted mean ride of the week (`f5_mean_ride_min`)"],
        ["minibus utilisation", "owned busy minutes (route + cooldown) / (f1 x service span summed over the five days); the span of a day is the earliest route start to the latest route end over all options at that (day, R), so all options share one denominator; not defined for L = 0"],
        ["borrowed utilisation", "borrowed busy minutes (route + cooldown) / time on loan (per borrowed vehicle and day: first start to last end plus cooldown). 100% means the vehicle drives (or cools down) the whole time it is borrowed; it says nothing about how long it is borrowed"],
        ["before-10:00 share", "share of the borrowed busy minutes that fall before 10:00"]])
    out += ["", "Families: **minibus-only** (A) = all-large minimum; **minibus+sedan** = L large minibuses (4 Sw + 5 So) plus sedans (0 Sw + 4 So), sedans cannot carry wheelchair (Sw) students; "
            "**minibus+minivan** = L large minibuses plus wheelchair-accessible minivans `minivan:1sw3so:cap3:cd10` (Doblo model: **3 passengers in total, of whom at most 1 is a wheelchair user**; the wheelchair is stowed in the luggage space and the student sits in a seat), which can. The minivan capacity is an **assumption and a parameter** "
            "(a smaller model such as `minivan:1sw2so` was not run). The earlier archived `extra/minivan` campaign allowed 4 people and is superseded (DECISION_LOG H03). **hybrid** = day-level combination derived exactly from existing runs (section 5).", "",
            "## 3. Data and checks", ""]
    out += mdt(["Source", "Scenarios", "Git commit (manifest)", "Fleet types", "Files"],
               [[("`%s`" % os.path.relpath(d.path, RES).replace("\\", "/")) if d.name != "main" else "`.` (archive)", ", ".join(d.scens), d.man["git_commit"][:7],
                 ", ".join("%s %dSw/%dSo%s" % (t["typeId"], t["swCapacity"], t["soCapacity"], (", total %d" % t["totalCapacity"]) if "totalCapacity" in t else "") for t in d.man["fleet_types"]), "%d daily rows" % len(d.daily)] for d in DSS])
    out += ["", "All runs: week %s..%s, R in {50, 60, 70, 90}, tour limit 150, cooldown 10, `assume_confirmed`, same matrix (sha256 `%s...%s`, read from every response file: %d distinct value(s)). "
            "The runs come from different working-tree states (manifests `dirty_working_tree: true`); the first campaign was run at an earlier commit than L4 and minivan." % (
                DATES[0], DATES[-1], sorted(SHAS)[0][:8], sorted(SHAS)[0][-8:], len(SHAS)), "",
            "Independent checks (recomputed from the routes): %d feasible-day runs checked for cooldown/overlap per vehicle, capacity by type, tour <= 150, ride <= R, every leg served once, "
            "and consistency with the CSVs; %d infeasible-day runs have no routes. Weekly CSV cross-check of f1, f2, borrowed minutes, vehicle-day sum and mean ride for the %d non-derived options. "
            "**Violations: %d.**" % (N_CHECKED, N_INFEAS, len([o for o in OPTS if not o["derived"]]), len(VIOL)), ""]
    out += ["## 4. All options", "", "Feasible = all five weekdays feasible. Per-day column is Mon/Tue/Wed/Thu/Fri borrowed vehicles (hybrid: s = sedan day, v = minivan day). "
            "ND = non-dominated on (f1, f2, f3) among the options of the same R; G = also globally non-dominated on (f1, f2, f3, R).", ""]
    for R in RS:
        out += ["### R = %d min" % R, ""]
        rows = []
        for o in by(R):
            if not f(o):
                rows.append([fam_label(o), "infeasible (feasible on %d of 5 days)" % o["feasible_days"]] + ["-"] * 9)
                continue
            rows.append([fam_label(o), o["f1"], o["f2"], "%.1f" % o["f3"], o["f4"], "%.1f" % o["mean_ride"],
                         o["days_typed"] if o["family"] == "hybrid" else "/".join(map(str, o["nb"])), pg(o["util_own"]), pg(o["util_bor"]), pg(o["morning"]),
                         ("ND" if o["nd_R"] else "dominated") + (" G" if o["nd_glob"] else "")])
        out += mdt(["Option", "f1", "f2", "f3 h/wk", "f4 days", "Mean ride", "Per day", "Minibus util.", "Borrowed util.", "Before 10:00", "Status"], rows) + [""]
    out += ["## 5. Non-dominated sets", ""]
    rows = []
    for R in RS:
        for o in sorted([o for o in FEAS if o["R"] == R and o["nd_R"]], key=lambda o: (o["f1"], o["f3"])):
            rows.append([R, fam_label(o), o["f1"], o["f2"], "%.1f" % o["f3"], o["f4"], "yes" if o["nd_glob"] else "no"])
    out += mdt(["R", "Non-dominated option", "f1", "f2", "f3 h/wk", "f4", "Also global"], rows) + [""]
    dom = [o for o in FEAS if not o["nd_R"]]
    out += ["Dominated within their R (%d): %s." % (len(dom), "; ".join("%s@%d (by %s)" % (fam_label(o), o["R"], o["dom_by"].replace("R%d_" % o["R"], "")) for o in dom) or "none"), "",
            "Globally non-dominated on (f1, f2, f3, R) (%d): %s. Every per-R non-dominated option of R = 50 is also global (no option has a smaller R); an option at a larger R is global only if "
            "no stricter-or-equal option is at least as good on f1, f2 and f3. R is treated as a minimised objective (a smaller ride limit is a stricter service level)." % (
                len([o for o in FEAS if o["nd_glob"]]), ids([o for o in FEAS if o["nd_glob"]])), "",
            "Ties: option A has the same objectives (f1, f2, f3) at R = 50, 60 and 70 (6, 0, 0), so A at R = 60 and 70 is dominated globally by A at R = 50 although it is non-dominated for its own R. "
            "At R = 90, option A and L4 + sedan have identical objectives (4, 0, 0): L4 needs no sedan on any weekday at R = 90, so it coincides with A (both are listed; equal vectors do not dominate each other).", ""]
    hy = [o for o in FEAS if o["family"] == "hybrid"]
    out += ["### Hybrid (day-level, derived)", "",
            "Derived exactly, not re-solved: for L = 2 and each R, the L2 + sedan result is used on the weekdays where it is feasible, and the L2 + minivan result on the others "
            "(each weekday is an independent optimisation given L and R, so this combination is exact at day level). For L = 1 the sedan variant is infeasible on all five days, so the hybrid equals L1 + minivan; "
            "for L >= 3 sedans are feasible every day and no minivan is run, so no hybrid arises. A wave-level hybrid (minivans only in the waves where L alone fails) needs a three-type solve and is **future work**; no numbers are given for it.", ""]
    rows = []
    for h in hy:
        mv = o_[("minibus+minivan", h["L"], h["R"])]
        rows.append([h["R"], h["days_typed"], h["f2"], "%.1f" % h["f3"], "%.1f" % h["h_minivan"], h["minivan_days"], "%.1f" % mv["f3"], mv["f2"], mv["minivan_days"], "dominated" if not h["nd_R"] else "ND"])
    out += mdt(["R", "Hybrid per day", "f2", "f3 h/wk", "of which minivan h", "Days with a minivan", "Pure minivan L2 f3", "Pure f2", "Pure minivan days", "Status on (f1,f2,f3)"], rows) + [""]
    same = sum(1 for h in hy if h["f2"] == o_[("minibus+minivan", h["L"], h["R"])]["f2"])
    higher = sum(1 for h in hy if h["f3"] > o_[("minibus+minivan", h["L"], h["R"])]["f3"])
    out += ["The hybrid has the same f2 as the pure L2 + minivan option in %d of %d cases and a higher f3 in %d of %d (the planner minimises the vehicle count per day, not the hours, so replacing a minivan day by a sedan day does not by itself lower f3). "
            "Its only gain is that sedans replace minivans on %s weekdays (at R = %s respectively), i.e. fewer days on which a minivan has to be rented (column `days_with_minivan`). "
            "That quantity is not one of f1..f5, so on (f1, f2, f3) the hybrid is dominated; it is reported because it matters if a minivan is harder to obtain than a sedan, which the data do not show." % (
                same, len(hy), higher, len(hy), ", ".join(str(h["sedan_days"]) for h in hy), ", ".join(str(h["R"]) for h in hy)), ""]
    out += ["## 6. Sensitivity of the non-dominated sets", ""]
    base = {o["id"] for o in FEAS if o["nd_R"]}
    rows = []
    for key, desc in (("nd_R4", "adding f4 to the objectives"), ("nd_R_route", "f3 = route hours (no cooldown)"), ("nd_R_window", "f3 = time on loan (first start to last end + cooldown)"),
                      ("nd_R_conc", "f2 = peak concurrent borrowed vehicles instead of distinct vehicles per day")):
        s = {o["id"] for o in FEAS if o[key]}
        rows.append([desc, "same set" if s == base else "added: %s; removed: %s" % (", ".join(sorted(s - base)) or "none", ", ".join(sorted(base - s)) or "none")])
    gm = {o["id"] for o in FEAS if o["nd_globmean"]}
    gg = {o["id"] for o in FEAS if o["nd_glob"]}
    rows.append(["global set with realised mean ride instead of R as f5", "same set" if gm == gg else "added: %s; removed: %s" % (", ".join(sorted(gm - gg)) or "none", ", ".join(sorted(gg - gm)) or "none")])
    out += mdt(["Variant", "Per-R non-dominated set compared with the base set"], rows) + [""]
    fl = [o for o in FEAS if o["util_bor"] is not None]
    ou = [o for o in FEAS if o["util_own"] is not None]
    k60 = [o_[("minibus+minivan", 2, 60)], o_[("minibus+sedan", 3, 60)], o_[("minibus+sedan", 4, 60)]]
    out += ["## 7. Utilisation and timing of borrowed vehicles", "",
            "- Minibus utilisation (owned busy / owned capacity over the common span) ranges from %s to %s over the feasible options with L >= 1; option A has %s to %s." % (
                pg(min(o["util_own"] for o in ou)), pg(max(o["util_own"] for o in ou)), pg(min(o["util_own"] for o in FEAS if o["family"] == "minibus-only")), pg(max(o["util_own"] for o in FEAS if o["family"] == "minibus-only"))),
            "- Share of borrowed busy time before 10:00 ranges from %s to %s over the options that borrow; the rest of the borrowed time is at or after 10:00." % (
                pg(min(o["morning"] for o in fl)), pg(max(o["morning"] for o in fl))),
            "- Borrowed-vehicle utilisation (busy / on loan) ranges from %s to %s; 100%% means the vehicle is busy for the whole time it is borrowed (one route, or routes separated only by the cooldown)." % (
                pg(min(o["util_bor"] for o in fl)), pg(max(o["util_bor"] for o in fl))),
            "- Key options at R = 60 (Fig. 3): " + "; ".join("%s: %d owned, up to %d borrowed on the busiest day, %.1f borrowed h/week on %d day(s) (per day %s), %s before 10:00" % (
                fam_label(o), o["f1"], o["f2"], o["f3"], o["f4"], "/".join(map(str, o["nb"])), pg(o["morning"])) for o in k60) + ".", ""]
    out += ["## 8. Reading the front (descriptive)", ""]
    for R in RS:
        ch = sorted([o for o in FEAS if o["R"] == R and o["nd_R"]], key=lambda o: o["f1"])
        out.append("- R = %d: " % R + "; ".join("%d owned -> %s (peak %d, %.1f h/week, %d days)" % (o["f1"], fam_label(o).split(" + ")[-1] if o["family"] != "minibus-only" else "no borrowing", o["f2"], o["f3"], o["f4"]) for o in ch) + ".")
    out += ["",
            "- Within a family, each extra owned minibus lowers the borrowed hours and the peak (see the chains above). The sedan options (L >= 3) need fewer borrowed hours than every minivan option "
            "(L0..L2) at every R, but they also own more minibuses; the families are not directly comparable on f1.",
            "- Sedans are possible only when enough minibuses cover the Sw demand (L >= 3 here, L2 + sedan fails on 2 to 3 weekdays at every R, L1 + sedan on all five); minivans are possible at any L (L0 is feasible), "
            "at the price of more borrowed vehicles and hours. This is the structural difference between the families, not a ranking.",
            "- Whether borrowed time of the size shown is acceptable depends on the lenders' availability, which is not in the data.", "",
            "## 9. Figures", ""]
    out += ["- `figures/pareto_front_by_R.svg` (Fig. 1a) and `figures/pareto_front_combined.svg` (Fig. 1b): owned minibuses vs borrowed vehicle-hours per week; bubble size = peak borrowed vehicles; shape and colour = family; dashed line joins the non-dominated points (a visual guide, not a 2-D front: the points are non-dominated on three objectives).",
            "- `figures/pareto_service_vs_minibuses.svg` (Fig. 2): mean ride vs owned minibuses, colour = borrowed hours.",
            "- `figures/pareto_borrowed_heatmap_R60.svg` (Fig. 3): hour of day x weekday, most borrowed vehicles in use at the same time, for L2 + minivan, L3 + sedan, L4 + sedan and the L2 hybrid at R = 60.",
            "- `figures/pareto_parallel_coordinates.svg` (Fig. 4): f1..f5 for all feasible options.",
            "- `figures/pareto_utilisation.svg` (Fig. 5): minibus utilisation, borrowed hours and borrowed days per option.",
            "- All are listed in `figures/index.html` (section e). `plan_fleet_scenarios.py` rewrites that page; run `plan_fleet_pareto.py` afterwards.", "",
            "## 10. Limits", "",
            "- One week, one timetable snapshot, `assume_confirmed` (every student with a class is assumed to ride); fixed travel-time matrix, no traffic, boarding times or driver assignment.",
            "- Heuristic routes and a minimum proven only over the generated menus; the front is an approximation (section 1).",
            "- The minivan capacity (3 passengers in total, at most 1 Sw) and the sedan capacity (0 Sw + 4 So) are assumptions; the sedan having no wheelchair place is an open owner question.",
            "- A borrowed vehicle is assumed available for the whole of its first-start to last-end window on each day it is used (f3 counts only its busy time); borrowing for single routes would need the lenders' schedules.",
            "- No cost data: this document gives no cost ranking.", "",
            "## 11. Reproduce", "",
            "`python scripts/plan_fleet_pareto.py` (standard library only) reads this folder and `extra/L4`, `extra/minivan-cap3` (second argument overrides the sub-folder), and rewrites `pareto_options.csv`, `pareto_daily.csv`, this file and the `figures/pareto_*.svg`."]
    with open(os.path.join(RES, "pareto_analysis.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


def main():
    write_csvs()
    sel = figures()
    write_md()
    print("runs checked: %d feasible-day runs, %d infeasible-day runs, violations: %d" % (N_CHECKED, N_INFEAS, len(VIOL)))
    for x in VIOL[:40]:
        print(" ", x)
    print("options: %d, feasible: %d" % (len(OPTS), len(FEAS)))
    for R in RS:
        for o in FEAS:
            if o["R"] == R and o["nd_R"]:
                print("ND", R, fam_label(o), o["f1"], o["f2"], round(o["f3"], 2), o["f4"], "glob" if o["nd_glob"] else "")


if __name__ == "__main__":
    main()
