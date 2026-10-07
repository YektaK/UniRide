#!/usr/bin/env python3
"""Heterogeneous-fleet what-if for the archived week-2026-10-05 campaign.
Standard library only. Reuses parsing and the route interval definition from
plan_schedule_report (route [start, end), vehicle busy until end + COOLDOWN).

Usage: python scripts/plan_fleet_mix.py [results_dir]
Run plan_schedule_report.py and plan_resource_profile.py first; this script then
adds its own idempotent sections to figures/index.html and figures/README.md.

Routes are FIXED as produced by the archived runs (no re-optimisation).
Vehicle types: large (4 Sw / 10 So) and car (0 Sw / 4 So), same cooldown.
A route needs a large vehicle unless it is car-eligible (Sw = 0 and So <= 4).
For fixed route sets each vehicle type is an interval-scheduling problem, so a
set of routes fits on k vehicles of one type iff its peak busy count (with
cooldown) is <= k. The exact search therefore decides, for given (L, C), whether
the car-eligible routes can be split into a car set and a large set whose peaks
are <= C and <= L (DFS over routes in start order, memoised, with a node budget).
"""
import csv
import datetime
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan_schedule_report import COOLDOWN, FIG, RES, SO_CAP, SW_CAP, TOUR, analyse, hm, load_runs  # noqa: E402
from plan_resource_profile import PAD, X0, esc, head, write  # noqa: E402

CAR_SO = 4  # car: 0 Sw / 4 So
NODE_BUDGET = 2_000_000
MARK_START, MARK_END = "<!-- FLEET-MIX-START -->", "<!-- FLEET-MIX-END -->"
README_HEAD = "## Fleet-mix frontier charts"
C_DAY, C_WEEK, C_BASE = "#9ab", "#D55E00", "#111111"


def classify(r):
    if r["sw"] > 0 and r["so"] > 0:
        return "mixed"
    return "Sw-only" if r["sw"] > 0 else "So-only"


def eligible(r):
    return r["sw"] == 0 and r["so"] <= CAR_SO


def peak(routes):
    """Peak busy count (interval [start, end + COOLDOWN)) of a route list."""
    ev = []
    for r in routes:
        ev += [(r["start"], 1), (r["end"] + COOLDOWN, -1)]
    cur = best = 0
    for _, d in sorted(ev, key=lambda e: (e[0], e[1])):  # ends (-1) before starts at the same minute
        cur += d
        best = max(best, cur)
    return best


class Budget(Exception):
    pass


def feasible(routes, L, C):
    """Return (True, set of route indices on cars) / (False, None) / (None, None) if budget hit."""
    order = sorted(range(len(routes)), key=lambda i: (routes[i]["start"], routes[i]["end"]))
    nodes = [0]
    dead = set()

    def rec(k, large, car, cars):
        if k == len(order):
            return cars
        nodes[0] += 1
        if nodes[0] > NODE_BUDGET:
            raise Budget
        r = routes[order[k]]
        t = r["start"]
        large = tuple(e for e in large if e > t)
        car = tuple(e for e in car if e > t)
        key = (k, large, car)
        if key in dead:
            return None
        e = r["end"] + COOLDOWN
        if eligible(r) and len(car) < C:
            res = rec(k + 1, large, tuple(sorted(car + (e,))), cars | {order[k]})
            if res is not None:
                return res
        if len(large) < L:
            res = rec(k + 1, tuple(sorted(large + (e,))), car, cars)
            if res is not None:
                return res
        dead.add(key)
        return None

    try:
        res = rec(0, (), (), frozenset())
    except Budget:
        return None, None
    return (False, None) if res is None else (True, res)


def frontier(routes, V):
    """List of dicts (L, C, proven, cars) for L = L_min .. V, exact min cars per L."""
    forced = [r for r in routes if not eligible(r)]
    lmin = peak(forced)
    out, prev = {}, None  # prev = (C, proven) of L+1
    for L in range(V, lmin - 1, -1):
        c = prev[0] if prev and prev[1] else 0
        proven = True
        while True:
            ok, cars = feasible(routes, L, c)
            if ok:
                break
            if ok is None:
                proven = False  # budget hit: lower C values not excluded by proof
            c += 1
            if c > len(routes):
                raise RuntimeError("no feasible C")
        # a budget hit at a smaller C means c is only an upper bound
        out[L] = dict(L=L, C=c, proven=proven, cars=cars)
        prev = (c, proven)
    return lmin, [out[L] for L in sorted(out)]


def vm(routes, cars):
    car = sum(routes[i]["total"] for i in cars)
    return sum(r["total"] for r in routes) - car, car


def pct(a, b):
    return "%.0f%%" % (100.0 * a / b) if b else "-"


def fig_frontier(path, R, week, days):
    vmax = max(p["L"] for p in week) + 1
    cmax = max([p["C"] for p in week] + [q["C"] for d in days for q in d["pts"]]) + 1
    W, H, x0, y0, w, h = 560, 400, X0 + 10, 84, 400, 260
    X = lambda v: x0 + w * v / vmax
    Y = lambda v: y0 + h - h * v / cmax
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Fleet-mix what-if, R=%d min: large vehicles vs cars needed (weekly)" % R)),
        '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (
        PAD, esc("Routes fixed as produced for the large vehicle; upper bound, not a mixed-fleet optimum.")),
        '<line x1="%d" y1="57" x2="%d" y2="57" stroke="%s" stroke-width="1.2"/><text x="%d" y="61" font-size="12" fill="#222">Single weekday</text>' % (
        PAD, PAD + 26, C_DAY, PAD + 32),
        '<line x1="%d" y1="57" x2="%d" y2="57" stroke="%s" stroke-width="2.6"/><text x="%d" y="61" font-size="12" fill="#222">Whole week (max over days)</text>' % (
        PAD + 140, PAD + 166, C_WEEK, PAD + 172),
        '<rect x="%d" y="52" width="10" height="10" fill="%s"/><text x="%d" y="61" font-size="12" fill="#222">All-large baseline</text>' % (
        PAD + 350, C_BASE, PAD + 366)]
    out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#fff" stroke="#888" stroke-width="0.8"/>' % (x0, y0, w, h))
    for v in range(0, vmax + 1):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#e2e2e2" stroke-width="0.7"/>' % (X(v), y0, X(v), y0 + h))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#333">%d</text>' % (X(v), y0 + h + 14, v))
    for v in range(0, cmax + 1):
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#e2e2e2" stroke-width="0.7"/>' % (x0, Y(v), x0 + w, Y(v)))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="end" fill="#333">%d</text>' % (x0 - 5, Y(v) + 4, v))
    out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Large vehicles (4 Sw / 10 So)</text>' % (x0 + w / 2, y0 + h + 34))
    out.append('<text transform="rotate(-90 %g %g)" x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Cars (0 Sw / 4 So)</text>' % (
        x0 - 32, y0 + h / 2, x0 - 32, y0 + h / 2))
    for d in days:
        pts = d["pts"]
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.2"><title>%s</title></polyline>' % (
            " ".join("%g,%g" % (X(p["L"]), Y(p["C"])) for p in pts), C_DAY, esc(d["date"])))
        out.append('<text x="%g" y="%g" font-size="9" fill="#678">%s</text>' % (X(pts[0]["L"]) + 3, Y(pts[0]["C"]) - 3, d["date"][5:]))
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.6"/>' % (
        " ".join("%g,%g" % (X(p["L"]), Y(p["C"])) for p in week), C_WEEK))
    for p in week:
        tip = "L=%d large, C=%d cars%s" % (p["L"], p["C"], "" if p["proven"] else " (not proven)")
        out.append('<circle cx="%g" cy="%g" r="4.5" fill="%s" fill-opacity="%s" stroke="%s"><title>%s</title></circle>' % (
            X(p["L"]), Y(p["C"]), C_WEEK, "1" if p["proven"] else "0.3", C_WEEK, esc(tip)))
        out.append('<text x="%g" y="%g" font-size="11" font-weight="bold" fill="%s">%d+%d</text>' % (X(p["L"]) + 6, Y(p["C"]) - 7, C_WEEK, p["L"], p["C"]))
    b = week[-1]
    out.append('<rect x="%g" y="%g" width="12" height="12" fill="%s"/>' % (X(b["L"]) - 6, Y(0) - 6, C_BASE))
    out.append('<text x="%g" y="%g" font-size="12" font-weight="bold" text-anchor="end" fill="%s">all-large %d</text>' % (X(b["L"]) - 10, Y(0) - 10, C_BASE, b["L"]))
    write(path, W, H, out)


def main():
    runs = load_runs()
    assert len(runs) == 20, len(runs)
    res = []
    for date, R, d in runs:
        a = analyse(date, R, d)
        a["wd"] = datetime.date.fromisoformat(date).strftime("%A")
        rts = a["routes"]
        V = a["rec"]["vehicles"]
        assert peak(rts) == V, (date, R, peak(rts), V)  # archived assignment: L=V, C=0 exactly tight
        lmin, pts = frontier(rts, V)
        assert pts[-1]["L"] == V and pts[-1]["C"] == 0, (date, R)
        for p in pts:
            p["lvm"], p["cvm"] = vm(rts, p["cars"]) if p["cars"] is not None else (None, None)
        a.update(V=V, lmin=lmin, pts=pts)
        res.append(a)
    Rs = sorted({a["R"] for a in res})
    dates = sorted({a["date"] for a in res})

    # CSV
    cp = os.path.join(RES, "fleet_mix.csv")
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["scope", "date", "ride_limit", "large_L", "cars_C", "proven", "large_vehicle_minutes", "car_vehicle_minutes", "all_large_vehicles"])
        for R in Rs:
            for a in sorted([x for x in res if x["R"] == R], key=lambda x: x["date"]):
                for p in a["pts"]:
                    w.writerow(["day", a["date"], R, p["L"], p["C"], "yes" if p["proven"] else "no", p["lvm"], p["cvm"], a["V"]])
        week = {}
        for R in Rs:
            week[R] = weekly(res, R)
            for p in week[R]:
                w.writerow(["week", "", R, p["L"], p["C"], "yes" if p["proven"] else "no", "", "", week[R][-1]["L"]])
    cl = os.path.join(RES, "fleet_mix_classification.csv")
    with open(cl, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "ride_limit", "routes", "sw_only", "so_only", "mixed", "car_eligible", "car_eligible_share", "so_load_distribution_on_so_only_routes"])
        for a in sorted(res, key=lambda x: (x["R"], x["date"])):
            c = Counter(classify(r) for r in a["routes"])
            ce = sum(1 for r in a["routes"] if eligible(r))
            dist = Counter(r["so"] for r in a["routes"] if classify(r) == "So-only")
            w.writerow([a["date"], a["R"], len(a["routes"]), c["Sw-only"], c["So-only"], c["mixed"], ce,
                        "%.3f" % (ce / len(a["routes"])), ";".join("%d:%d" % (k, dist[k]) for k in sorted(dist))])

    # figures
    for R in Rs:
        days = [dict(date=a["date"], pts=a["pts"]) for a in sorted([x for x in res if x["R"] == R], key=lambda x: x["date"])]
        # extend each daily line to the weekly baseline so lines share the x-range
        fig_frontier(os.path.join(FIG, "fleet_mix_frontier_R%d.svg" % R), R, week[R], days)

    # markdown
    L = ["# Heterogeneous fleet what-if, week of 2026-10-05", "",
         "Generated by `scripts/plan_fleet_mix.py` from the 20 archived `*.response.json` files. Descriptive only.", "",
         "## Method note", "",
         "- Routes are fixed exactly as produced for the large vehicle (4 Sw / 10 So); nothing is re-optimised. The result is therefore an upper bound on what a mixed fleet would need, not a mixed-fleet optimum.",
         "- Route classes by load: Sw-only (Sw > 0, So = 0), So-only (Sw = 0), mixed (Sw > 0 and So > 0). A route is car-eligible when Sw = 0 and So <= %d, i.e. it fits a %d-seat passenger car with no wheelchair place." % (CAR_SO, CAR_SO),
         "- Vehicle types: large (%d Sw / %d So) and car (0 Sw / %d So). Both use the same %d-min cooldown. Route interval = [start, end) as in the archived assignment; a vehicle is busy until end + %d min. A route needs a large vehicle unless it is car-eligible; a car-eligible route may use either type." % (SW_CAP, SO_CAP, CAR_SO, COOLDOWN, COOLDOWN),
         "- For a fixed route set one vehicle type is an interval-scheduling problem: k vehicles suffice iff the peak busy count is <= k. For each number of large vehicles L, from L_min (peak of the routes that must use a large vehicle, i.e. every car-eligible route goes to a car) up to the archived vehicles_required V, the script finds the minimum number of cars C(L) by exact memoised depth-first search over the car-eligible routes in start order (node budget %d per feasibility test). A value is marked not proven if the budget was hit before a smaller C was excluded; none is reported as proven otherwise." % NODE_BUDGET,
         "- Check: for every run the peak busy count of all routes equals V, so L = V with C = 0 is feasible and the frontier ends there (asserted in the script).",
         "- Vehicle-minutes are route travel minutes (cooldown excluded). The split between large and car minutes comes from one witness assignment (the search tries cars first); other optimal splits with the same C may exist. The total per day is fixed.",
         "- Weekly view: a fleet of L large vehicles and C cars covers day d iff L >= L_min(d) and C >= C_d(L) (C_d(L) = 0 for L >= V_d). Because the daily frontier is monotone in L, the exact weekly pair for each L is C_week(L) = max over days of C_d(L), for L from max_d L_min(d) up to max_d V_d. Choosing a different L per day and taking per-type maxima can only give dominated pairs, so this fixed-L rule is used. The last point is the all-large baseline (L = weekly fleet need, C = 0).",
         "- Limits: no cost data (no cost conclusion); car driver and accessibility policies are not modelled; ride-time and tour limits are those of the large-vehicle routes; one snapshot, one run per cell.", ""]
    nproof = sum(1 for a in res for p in a["pts"] if not p["proven"])
    L += ["Not proven points: %s." % ("none, every daily frontier value was proven exactly" if not nproof else "%d daily frontier point(s), marked below" % nproof), ""]

    L += ["## Route classes", "",
          "| R | Date | Day | Routes | Sw-only | So-only | Mixed | Car-eligible | Share |", "|---:|---|---|---:|---:|---:|---:|---:|---:|"]
    for R in Rs:
        for a in sorted([x for x in res if x["R"] == R], key=lambda x: x["date"]):
            c = Counter(classify(r) for r in a["routes"])
            ce = sum(1 for r in a["routes"] if eligible(r))
            L.append("| %d | %s | %s | %d | %d | %d | %d | %d | %s |" % (R, a["date"], a["wd"][:3], len(a["routes"]), c["Sw-only"], c["So-only"], c["mixed"], ce, pct(ce, len(a["routes"]))))
    L += ["", "Aggregate over the five weekdays:", "",
          "| R | Routes | Sw-only | So-only | Mixed | Car-eligible | Share |", "|---:|---:|---:|---:|---:|---:|---:|"]
    agg = {}
    for R in Rs:
        rr = [r for a in res if a["R"] == R for r in a["routes"]]
        c = Counter(classify(r) for r in rr)
        ce = sum(1 for r in rr if eligible(r))
        agg[R] = (len(rr), c, ce)
        L.append("| %d | %d | %d | %d | %d | %d | %s |" % (R, len(rr), c["Sw-only"], c["So-only"], c["mixed"], ce, pct(ce, len(rr))))
    L += ["", "Distribution of the So load on So-only routes (route counts, all five days):", "",
          "| R | " + " | ".join("So=%d" % k for k in range(1, SO_CAP + 1)) + " |", "|---:|" + "---:|" * SO_CAP]
    for R in Rs:
        dist = Counter(r["so"] for a in res if a["R"] == R for r in a["routes"] if classify(r) == "So-only")
        L.append("| %d | " % R + " | ".join(str(dist[k]) for k in range(1, SO_CAP + 1)) + " |")

    L += ["", "## Daily frontier", "",
          "Each row: the minimum cars C for L large vehicles (vehicle-minutes of the witness assignment). L_min = large vehicles needed when every car-eligible route goes to a car; V = archived all-large requirement.", "",
          "| R | Date | Day | L_min | V | L | Cars C | Large min | Car min | Proven |", "|---:|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for R in Rs:
        for a in sorted([x for x in res if x["R"] == R], key=lambda x: x["date"]):
            for p in a["pts"]:
                L.append("| %d | %s | %s | %d | %d | %d | %d | %s | %s | %s |" % (
                    R, a["date"], a["wd"][:3], a["lmin"], a["V"], p["L"], p["C"], p["lvm"], p["cvm"], "yes" if p["proven"] else "NOT PROVEN"))
    L += ["", "## Weekly frontier", "",
          "| R | Large L | Cars C | Total vehicles | Note |", "|---:|---:|---:|---:|---|"]
    for R in Rs:
        wk = week[R]
        for p in wk:
            note = "all-large baseline" if p is wk[-1] else ("" if p["proven"] else "NOT PROVEN")
            L.append("| %d | %d | %d | %d | %s |" % (R, p["L"], p["C"], p["L"] + p["C"], note))
    L.append("")
    with open(os.path.join(RES, "fleet_mix_analysis.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))

    # index.html and README (own markers, idempotent)
    H = [MARK_START, "<h1>Fleet-mix what-if</h1>",
         "<p>Large vehicles vs cars needed per ride limit R (scripts/plan_fleet_mix.py). Routes fixed as produced; upper bound, not a mixed-fleet optimum.</p>"]
    for R in Rs:
        H.append('<h2 id="fleetmix%d">Fleet mix, R=%d</h2><img src="fleet_mix_frontier_R%d.svg" alt="Fleet-mix frontier R=%d">' % (R, R, R, R))
    H.append(MARK_END)
    ip = os.path.join(FIG, "index.html")
    with open(ip, encoding="utf-8") as f:
        t = f.read()
    i, j = t.find(MARK_START), t.find(MARK_END)
    if i >= 0 and j >= 0:
        t = t[:i] + t[j + len(MARK_END):].lstrip("\n")
    t = t.replace("</body>", "\n".join(H) + "\n</body>")
    with open(ip, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    rp = os.path.join(FIG, "README.md")
    with open(rp, encoding="utf-8") as f:
        t = f.read()
    k = t.find("\n" + README_HEAD)
    if k >= 0:
        t = t[:k].rstrip("\n") + "\n"
    Lr = ["", README_HEAD, "",
          "From `scripts/plan_fleet_mix.py` (run after `plan_resource_profile.py`). Weekly frontier of large vehicles (x) versus cars (y) that cover all five weekdays, thin lines = single weekdays, black square = all-large baseline. Routes are fixed as produced for the large vehicle, so this is an upper bound, not a mixed-fleet optimum. Details: `../fleet_mix_analysis.md`.", ""]
    Lr += ["- `fleet_mix_frontier_R%d.svg`: R = %d min" % (R, R) for R in Rs] + [""]
    with open(rp, "w", encoding="utf-8", newline="\n") as f:
        f.write(t + "\n".join(Lr))

    print("not proven points:", nproof)
    for R in Rs:
        n, c, ce = agg[R]
        print("R=%d routes=%d car-eligible=%d (%s) week=%s" % (R, n, ce, pct(ce, n), " ".join("%d+%d%s" % (p["L"], p["C"], "" if p["proven"] else "?") for p in week[R])))


def weekly(res, R):
    days = [a for a in res if a["R"] == R]
    lo = max(a["lmin"] for a in days)
    hi = max(a["V"] for a in days)
    out = []
    for L in range(lo, hi + 1):
        c, proven = 0, True
        for a in days:
            if L >= a["V"]:
                continue
            p = next(q for q in a["pts"] if q["L"] == L)
            c = max(c, p["C"])
            proven = proven and p["proven"]
        out.append(dict(L=L, C=c, proven=proven))
    return out


if __name__ == "__main__":
    main()
