#!/usr/bin/env python3
"""Independent verification and SVG Gantt charts for the archived
week-2026-10-05 daily-plan campaign. Standard library only.

Usage: python scripts/plan_schedule_report.py [results_dir]
Reads only *.response.json, summary.csv and weekly.csv from results_dir.
Writes schedule_verification.md, figures/*.svg, figures/index.html,
figures/README.md.
"""
import csv
import datetime
import glob
import html
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "paper", "results", "week-2026-10-05")
FIG = os.path.join(RES, "figures")
COOLDOWN, SW_CAP, SO_CAP, TOUR = 10, 4, 10, 150
BUFFER = 15  # documented arrival/departure buffer (class time is not in the JSON)
C_PICK, C_DROP = "#0072B2", "#E69F00"  # Okabe-Ito blue / orange


def hm(m):
    m = int(round(m))
    return "%02d:%02d" % (m // 60, m % 60)


def vnum(s):
    return int(re.sub(r"\D", "", s) or 0)


def load_runs():
    runs = []
    for p in sorted(glob.glob(os.path.join(RES, "*_R*_repeat1.response.json"))):
        m = re.match(r"(\d{4}-\d\d-\d\d)_R(\d+)_repeat1", os.path.basename(p))
        with open(p, encoding="utf-8") as f:
            runs.append((m.group(1), int(m.group(2)), json.load(f)))
    runs.sort(key=lambda r: (r[1], r[0]))
    return runs


def analyse(date, R, d):
    v = []  # (check, detail)
    labels = d["occurrenceLabels"]
    limits = d["limits"]
    tour = limits["maxTourMinutes"]
    if limits["maxRideTimeMinutes"] != R:
        v.append(("e", "limits.maxRideTimeMinutes=%s != filename R=%s" % (limits["maxRideTimeMinutes"], R)))
    if tour != TOUR:
        v.append(("e", "limits.maxTourMinutes=%s != %s" % (tour, TOUR)))
    cd = d["fleet"]["template"]["cooldownMinutes"]
    if cd != COOLDOWN:
        v.append(("b", "fleet cooldown=%s != %s" % (cd, COOLDOWN)))
    caps = d["fleet"]["template"]
    if (caps["swCapacity"], caps["soCapacity"]) != (SW_CAP, SO_CAP):
        v.append(("d", "fleet capacity %s/%s != %d/%d" % (caps["swCapacity"], caps["soCapacity"], SW_CAP, SO_CAP)))

    routes = []
    rides = {}
    served = defaultdict(list)
    for job in d["jobs"]:
        direction = job["direction"]
        anchor = job["anchorMinutes"]
        for ri, r in enumerate(job["result"]["routes"]):
            steps = r["route_details"]
            durs = [s["duration"] for s in steps]
            total = sum(durs)
            if total != r["total_duration_minutes"]:
                v.append(("g", "%s r%d: sum(step)=%d != total_duration_minutes=%d" % (job["id"], ri, total, r["total_duration_minutes"])))
            ids = r["student_ids"]
            stop_of = [s["location2"] for s in steps[:-1]]
            if steps and (steps[0]["location1"] != "D.Kampus" or steps[-1]["location2"] != "D.Kampus"):
                v.append(("g", "%s r%d: route does not start and end at campus" % (job["id"], ri)))
            for i, oid in enumerate(ids):
                # pickup: campus -> stop1 .. stopN -> campus; ride = legs after the stop
                # drop-off: campus -> stop1 .. stopN -> campus; ride = legs up to the stop
                rides[oid] = sum(durs[i + 1:]) if direction == "pickup" else sum(durs[:i + 1])
            if len(stop_of) != len(ids):
                v.append(("c", "%s r%d: %d stops vs %d student ids" % (job["id"], ri, len(stop_of), len(ids))))
            for i, oid in enumerate(ids):
                if i < len(stop_of) and labels.get(oid) != stop_of[i]:
                    v.append(("c", "%s r%d: student %s label %s != stop %s" % (job["id"], ri, oid, labels.get(oid), stop_of[i])))
                if ":" + direction + ":" not in oid:
                    v.append(("c", "%s: id %s has wrong direction" % (job["id"], oid)))
                served[oid].append((job["id"], ri))
            sw = sum(1 for o in ids if labels.get(o, "").startswith("Sw"))
            so = sum(1 for o in ids if labels.get(o, "").startswith("So"))
            if (sw, so) != (r["sw_count"], r["so_count"]):
                v.append(("g", "%s r%d: recomputed load %dSw/%dSo != reported %d/%d" % (job["id"], ri, sw, so, r["sw_count"], r["so_count"])))
            start, end = (anchor - total, anchor) if direction == "pickup" else (anchor, anchor + total)
            if sw > SW_CAP or so > SO_CAP:
                v.append(("d", "%s r%d: load %dSw/%dSo exceeds %d/%d" % (job["id"], ri, sw, so, SW_CAP, SO_CAP)))
            if total > tour:
                v.append(("e", "%s r%d: duration %d > tour limit %d" % (job["id"], ri, total, tour)))
            for oid in ids:
                if rides[oid] > R:
                    v.append(("e", "%s r%d: ride %s = %d > R=%d" % (job["id"], ri, oid, rides[oid], R)))
            routes.append(dict(job=job["id"], ri=ri, dir=direction, anchor=anchor, start=start, end=end,
                               total=total, sw=sw, so=so, ids=ids, n=len(ids),
                               ride_max=max((rides[o] for o in ids), default=0)))

    amap = defaultdict(list)
    for a in d["assignments"]:
        amap[(a["jobId"], a["routeIndex"])].append(a)
    for rt in routes:
        al = amap.get((rt["job"], rt["ri"]), [])
        if len(al) != 1:
            v.append(("c", "route %s r%d assigned %d times" % (rt["job"], rt["ri"], len(al))))
            rt["pv"] = None
            continue
        a = al[0]
        rt["pv"] = a["physicalVehicleId"]
        if (a["startMinutes"], a["endMinutes"]) != (rt["start"], rt["end"]):
            v.append(("g", "%s r%d: assignment interval %d-%d != recomputed %d-%d" % (rt["job"], rt["ri"], a["startMinutes"], a["endMinutes"], rt["start"], rt["end"])))
        if (a["swCount"], a["soCount"]) != (rt["sw"], rt["so"]):
            v.append(("g", "%s r%d: assignment load differs" % (rt["job"], rt["ri"])))
        if sorted(a["occurrenceIds"]) != sorted(rt["ids"]):
            v.append(("c", "%s r%d: assignment occurrenceIds differ from route student_ids" % (rt["job"], rt["ri"])))
    keys = {(r["job"], r["ri"]) for r in routes}
    for k in amap:
        if k not in keys:
            v.append(("c", "assignment for unknown route %s" % (k,)))
    if len(d["assignments"]) != len(routes):
        v.append(("c", "assignments=%d routes=%d" % (len(d["assignments"]), len(routes))))
    if len(d["routeIntervals"]) != len(routes):
        v.append(("g", "routeIntervals=%d routes=%d" % (len(d["routeIntervals"]), len(routes))))
    if d["unassignedOccurrenceIds"]:
        v.append(("c", "unassignedOccurrenceIds=%s" % d["unassignedOccurrenceIds"]))
    for oid, lst in served.items():
        if len(lst) != 1:
            v.append(("c", "leg %s served %d times" % (oid, len(lst))))
    missing = set(labels) - set(served)
    if missing:
        v.append(("c", "legs never served: %s" % sorted(missing)))
    extra = set(served) - set(labels)
    if extra:
        v.append(("c", "served legs without label: %s" % sorted(extra)))

    byv = defaultdict(list)
    for rt in routes:
        if rt["pv"]:
            byv[rt["pv"]].append(rt)
    vstats = {}
    mingap = None
    for pv, lst in byv.items():
        lst.sort(key=lambda x: (x["start"], x["end"]))
        gaps = []
        for p, q in zip(lst, lst[1:]):
            gap = q["start"] - p["end"]
            gaps.append(gap)
            if gap < 0:
                v.append(("a", "%s overlap: %s r%d [%s-%s] and %s r%d [%s-%s]" % (pv, p["job"], p["ri"], hm(p["start"]), hm(p["end"]), q["job"], q["ri"], hm(q["start"]), hm(q["end"]))))
            elif gap < COOLDOWN:
                v.append(("b", "%s gap %d min < %d between %s and %s" % (pv, gap, COOLDOWN, hm(p["end"]), hm(q["start"]))))
            mingap = gap if mingap is None else min(mingap, gap)
        vstats[pv] = dict(n=len(lst), first=lst[0]["start"], last=max(x["end"] for x in lst),
                          busy=sum(x["end"] - x["start"] for x in lst), gaps=gaps,
                          idle=sum(g for g in gaps if g > 0))
    rl = list(rides.values())
    rec = dict(vehicles=len(byv), routes=len(routes), legs=len(rl), max_ride=max(rl), mean_ride=sum(rl) / len(rl),
               total_vm=sum(r["total"] for r in routes), waves=len(d["jobs"]),
               students=d["candidateSummary"]["dudulluStudents"],
               reported_min_vehicles=d["vehicleSummary"]["minimumVehicles"],
               first_start=min(r["start"] for r in routes), last_end=max(r["end"] for r in routes), min_gap=mingap)
    if rec["vehicles"] != rec["reported_min_vehicles"]:
        v.append(("f", "distinct vehicles %d != vehicleSummary.minimumVehicles %d" % (rec["vehicles"], rec["reported_min_vehicles"])))
    return dict(date=date, R=R, routes=routes, byv=byv, vstats=vstats, rec=rec, viol=v)


CHECKS = [("a", "no overlap on a vehicle"), ("b", "cooldown >= 10 min"), ("c", "each route and leg served exactly once"),
          ("d", "load within 4 Sw / 10 So"), ("e", "tour <= 150 and ride <= R"),
          ("f", "vehicles and summary.csv match"), ("g", "internal consistency of fields")]


def main():
    runs = load_runs()
    assert len(runs) == 20, len(runs)
    with open(os.path.join(RES, "summary.csv"), encoding="utf-8") as f:
        summ = {(r["date"], int(r["ride_limit"])): r for r in csv.DictReader(f)}
    res = []
    for date, R, d in runs:
        a = analyse(date, R, d)
        a["wd"] = datetime.date.fromisoformat(date).strftime("%A")
        s = summ.get((date, R))
        if not s:
            a["viol"].append(("f", "no summary.csv row"))
        else:
            rc = a["rec"]
            comp = [("students", rc["students"], int(s["students"])), ("legs", rc["legs"], int(s["legs"])),
                    ("waves", rc["waves"], int(s["waves"])), ("routes", rc["routes"], int(s["routes"])),
                    ("vehicles_required", rc["vehicles"], int(s["vehicles_required"])),
                    ("max_ride_min", rc["max_ride"], float(s["max_ride_min"])),
                    ("mean_ride_min", rc["mean_ride"], float(s["mean_ride_min"])),
                    ("total_vehicle_minutes", rc["total_vm"], float(s["total_vehicle_minutes"])),
                    ("tour_limit", TOUR, int(s["tour_limit"])), ("ride_limit", R, int(s["ride_limit"]))]
            for k, mine, theirs in comp:
                if abs(mine - theirs) > 1e-4:
                    a["viol"].append(("f", "summary.csv %s=%s but recomputed %s" % (k, theirs, mine)))
            if s["weekday"].lower() != a["wd"].lower():
                a["viol"].append(("f", "summary weekday %s != calendar %s" % (s["weekday"], a["wd"])))
        res.append(a)

    weekly_notes = []
    with open(os.path.join(RES, "weekly.csv"), encoding="utf-8") as f:
        wrows = list(csv.DictReader(f))
    weekly_notes.append("columns: " + ", ".join(wrows[0].keys()))
    for w in wrows:
        Rw = int(w["ride_limit"])
        mine = [x for x in res if x["R"] == Rw]
        wv = max(x["rec"]["vehicles"] for x in mine)
        wm = sum(x["rec"]["total_vm"] for x in mine)
        for k, val in w.items():
            if "total_vehicle_minutes" in k and abs(float(val) - wm) > 1e-6:
                weekly_notes.append("MISMATCH R=%d %s=%s recomputed %s" % (Rw, k, val, wm))
            if k in ("weekly_fleet_need", "weekly_vehicles", "fleet_need", "weekly_vehicles_required") and int(float(val)) != wv:
                weekly_notes.append("MISMATCH R=%d %s=%s recomputed %s" % (Rw, k, val, wv))
    if len(weekly_notes) == 1:
        weekly_notes.append("weekly vehicle and vehicle-minute columns match the recomputed per-day values (max vehicles over days, sum of route minutes).")

    write_md(res, weekly_notes)
    os.makedirs(FIG, exist_ok=True)
    for a in res:
        write_svg(os.path.join(FIG, "gantt_%s_R%d.svg" % (a["date"], a["R"])), [a], True)
    for R in sorted({a["R"] for a in res}):
        write_svg(os.path.join(FIG, "gantt_week_R%d.svg" % R), sorted([a for a in res if a["R"] == R], key=lambda x: x["date"]), False)
    write_index(res)
    tot = defaultdict(int)
    for a in res:
        for c, _ in a["viol"]:
            tot[c] += 1
    print("violations by check:", dict(tot) or "none")


def write_md(res, weekly_notes):
    L = ["# Schedule verification, week of 2026-10-05", "",
         "Generated by `scripts/plan_schedule_report.py` from the archived `*.response.json` files only. "
         "Every check is recomputed from raw route steps (`jobs[].result.routes[].route_details`) and the "
         "physical-vehicle assignments; summary fields are used only for the comparison in check f.", "",
         "Conventions: pickup interval = [anchor - total, anchor], drop-off interval = [anchor, anchor + total] "
         "(total = sum of step durations). Pickup ride = steps after the student's stop up to campus; "
         "drop-off ride = steps from campus up to the student's stop. "
         "Gap = next start - previous end on the same physical vehicle. Cooldown 10 min, capacity 4 Sw / 10 So, tour limit 150.", ""]
    tot = defaultdict(int)
    for a in res:
        for c, _ in a["viol"]:
            tot[c] += 1
    L += ["## Verdict", "",
          "Runs verified: %d. Runs with at least one violation: %d. Total violations: %d." % (
              len(res), sum(1 for a in res if a["viol"]), sum(tot.values())), "",
          "| Check | Description | Runs passed (of 20) | Violations |", "|---|---|---|---|"]
    for c, desc in CHECKS:
        L.append("| %s | %s | %d | %d |" % (c, desc, sum(1 for a in res if not any(x == c for x, _ in a["viol"])), tot[c]))
    L += ["", "## Per-run results", "",
          "| Date | Day | R | a | b | c | d | e | f | g | Min gap (min) | Vehicles | First start | Last end | Routes | Max ride | Mean idle per vehicle (min) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in sorted(res, key=lambda x: (x["R"], x["date"])):
        pf = ["FAIL" if any(x == c for x, _ in a["viol"]) else "pass" for c, _ in CHECKS]
        rc = a["rec"]
        idle = sum(s["idle"] for s in a["vstats"].values()) / max(1, len(a["vstats"]))
        L.append("| %s | %s | %d | %s | %s | %d | %s | %s | %d | %d | %.1f |" % (
            a["date"], a["wd"][:3], a["R"], " | ".join(pf),
            rc["min_gap"] if rc["min_gap"] is not None else "n/a", rc["vehicles"],
            hm(rc["first_start"]), hm(rc["last_end"]), rc["routes"], rc["max_ride"], idle))
    L += ["", "Idle = sum of gaps between consecutive routes of a vehicle (the 10-min cooldown is included), excluding time before the first and after the last route.", "",
          "## Campus waiting", "",
          "The response JSON holds anchors but not class times, so waiting is checked only against the documented definition. "
          "A pickup anchor is the first class start minus %d min, so students wait exactly %d min at campus (the route ends at the anchor). "
          "A drop-off route leaves campus at the anchor, which is the last class end plus %d min, so students wait %d min after class. "
          "Check g confirms every interval is [anchor - total, anchor] (pickup) or [anchor, anchor + total] (drop-off), so no pickup ends after and no drop-off starts before its anchor. "
          "This follows from construction and is not an independent measurement." % (BUFFER, BUFFER, BUFFER, BUFFER), "",
          "## weekly.csv", ""] + ["- " + n for n in weekly_notes] + ["", "## Violations", ""]
    if not sum(tot.values()):
        L.append("None. All checks passed in all 20 runs.")
    else:
        for a in sorted(res, key=lambda x: (x["R"], x["date"])):
            for c, det in a["viol"]:
                L.append("- %s R%d check %s: %s" % (a["date"], a["R"], c, det))
    L += ["", "## Per-vehicle detail", ""]
    for a in sorted(res, key=lambda x: (x["R"], x["date"])):
        L += ["### %s (%s) R=%d" % (a["date"], a["wd"], a["R"]), "",
              "| Vehicle | Routes | First start | Last end | Busy (min) | Idle gaps (min) | Min gap |", "|---|---|---|---|---|---|---|"]
        for k, pv in enumerate(sorted(a["vstats"], key=vnum)):
            s = a["vstats"][pv]
            L.append("| %s (Vehicle %d) | %d | %s | %s | %d | %d | %s |" % (pv, k + 1, s["n"], hm(s["first"]), hm(s["last"]), s["busy"], s["idle"], min(s["gaps"]) if s["gaps"] else "-"))
        L.append("")
    with open(os.path.join(RES, "schedule_verification.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L).rstrip() + "\n")


def panel(a, x0, y0, pxm, t0, t1, out, ids):
    veh = sorted(a["byv"], key=vnum)
    rowh, bar, top = 30, 22, 24
    h = top + rowh * len(veh) + 6
    W = (t1 - t0) * pxm
    for k, pv in enumerate(veh):
        y = y0 + top + k * rowh
        out.append('<rect x="%g" y="%g" width="%g" height="%d" fill="%s"/>' % (x0, y, W, rowh, "#f4f4f4" if k % 2 == 0 else "#ffffff"))
        out.append('<text x="%g" y="%g" font-size="12" text-anchor="end" fill="#222">Vehicle %d</text>' % (x0 - 6, y + 19, k + 1))
    t = t0 - t0 % 60 + (60 if t0 % 60 else 0)
    while t <= t1:
        x = x0 + (t - t0) * pxm
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#bbb" stroke-width="0.7"/>' % (x, y0 + top, x, y0 + h - 6))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#333">%s</text>' % (x, y0 + top - 6, hm(t)))
        t += 60
    for k, pv in enumerate(veh):
        y = y0 + top + k * rowh + (rowh - bar) / 2
        for r in sorted(a["byv"][pv], key=lambda r: r["start"]):
            x = x0 + (r["start"] - t0) * pxm
            w = (r["end"] - r["start"]) * pxm
            pick = r["dir"] == "pickup"
            ids[0] += 1
            cid = "c%d" % ids[0]
            out.append('<rect x="%g" y="%g" width="%g" height="%d" fill="url(#cool)" stroke="#888" stroke-width="0.6"/>' % (x + w, y, COOLDOWN * pxm, bar))
            tip = "%s %s, anchor %s, %d students, route %d min, max ride %d min, %d Sw / %d So, %s-%s" % (
                "Pickup" if pick else "Drop-off", pv, hm(r["anchor"]), r["n"], r["total"], r["ride_max"], r["sw"], r["so"], hm(r["start"]), hm(r["end"]))
            out.append('<g><title>%s</title><clipPath id="%s"><rect x="%g" y="%g" width="%g" height="%d"/></clipPath>' % (html.escape(tip), cid, x, y, w, bar))
            out.append('<rect x="%g" y="%g" width="%g" height="%d" fill="%s" stroke="#222" stroke-width="0.7"/>' % (x, y, w, bar, C_PICK if pick else C_DROP))
            out.append('<text clip-path="url(#%s)" x="%g" y="%g" font-size="9.5" fill="%s">%s %s %dSw/%dSo</text></g>' % (
                cid, x + 3, y + 15, "#fff" if pick else "#000", hm(r["anchor"]), "P" if pick else "D", r["sw"], r["so"]))
    return h


def write_svg(path, runs, single):
    pxm = 3.0 if single else 2.2
    t0 = min(min(r["start"] for r in a["routes"]) for a in runs)
    t1 = max(max(r["end"] for r in a["routes"]) + COOLDOWN for a in runs)
    t0 -= t0 % 60
    t1 += (-t1) % 60
    x0, pad = 80, 20
    W = x0 + (t1 - t0) * pxm + pad
    out = []
    ids = [0]
    if single:
        a = runs[0]
        title = "%s %s, ride limit R=%d min, tour limit %d min, %d vehicles" % (a["wd"], a["date"], a["R"], TOUR, a["rec"]["vehicles"])
    else:
        title = "Week of %s, ride limit R=%d min, tour limit %d min (vehicles per day: %s)" % (
            runs[0]["date"], runs[0]["R"], TOUR, ", ".join(str(a["rec"]["vehicles"]) for a in runs))
    out.append('<text x="%g" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (pad, html.escape(title)))
    y = 40
    lx = pad
    for col, name in ((C_PICK, "Pickup (P): ends at campus at anchor"), (C_DROP, "Drop-off (D): leaves campus at anchor")):
        out.append('<rect x="%g" y="%g" width="14" height="12" fill="%s" stroke="#222" stroke-width="0.7"/><text x="%g" y="%g" font-size="12" fill="#222">%s</text>' % (lx, y, col, lx + 20, y + 11, name))
        lx += 20 + 6.5 * len(name) + 20
    out.append('<rect x="%g" y="%g" width="14" height="12" fill="url(#cool)" stroke="#888" stroke-width="0.6"/><text x="%g" y="%g" font-size="12" fill="#222">10-min cooldown</text>' % (lx, y, lx + 20, y + 11))
    out.append('<text x="%g" y="%g" font-size="11" fill="#555">Bar label: anchor time, direction, Sw/So load</text>' % (lx + 130, y + 11))
    y += 22
    for a in runs:
        if not single:
            out.append('<text x="%g" y="%g" font-size="13" font-weight="bold" fill="#111">%s %s (%d vehicles)</text>' % (pad, y + 14, a["wd"], a["date"], a["rec"]["vehicles"]))
            y += 18
        y += panel(a, x0, y, pxm, t0, t1, out, ids) + 6
    H = y + 6
    head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" width="%g" height="%g" font-family="Arial, Helvetica, sans-serif">'
            '<defs><pattern id="cool" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">'
            '<rect width="5" height="5" fill="#f3f3f3"/><line x1="0" y1="0" x2="0" y2="5" stroke="#999" stroke-width="1.5"/></pattern></defs>'
            '<rect width="100%%" height="100%%" fill="#ffffff"/>' % (W, H, W, H))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + "\n" + "\n".join(out) + "\n</svg>\n")


def write_index(res):
    Rs = sorted({a["R"] for a in res})
    H = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Schedule Gantt charts, week of 2026-10-05</title>'
         '<style>body{font-family:Arial,sans-serif;margin:20px}img{max-width:100%;border:1px solid #ccc;margin-bottom:24px}</style></head><body>',
         "<h1>Schedule Gantt charts, week of 2026-10-05</h1>",
         "<p>Generated by scripts/plan_schedule_report.py. Hover a bar for details.</p><ul>"]
    for R in Rs:
        H.append('<li><a href="#week%d">Weekly overview R=%d</a></li>' % (R, R))
    H.append("</ul>")
    for R in Rs:
        H.append('<h2 id="week%d">Weekly overview, R=%d</h2><img src="gantt_week_R%d.svg" alt="Weekly overview R=%d">' % (R, R, R, R))
        for a in sorted([x for x in res if x["R"] == R], key=lambda x: x["date"]):
            H.append('<h3>%s %s, R=%d (%d vehicles)</h3><img src="gantt_%s_R%d.svg" alt="Gantt %s R=%d">' % (
                a["wd"], a["date"], R, a["rec"]["vehicles"], a["date"], R, a["date"], R))
    H.append("</body></html>")
    with open(os.path.join(FIG, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(H) + "\n")
    L = ["# Figures", "",
         "Hand-written SVG Gantt charts (standard library only). Open `index.html` in a browser to browse all 24; hover a bar for student count, route minutes and max ride.",
         "Colours (Okabe-Ito, colourblind safe): blue = pickup, orange = drop-off, hatched = 10-min cooldown after each route.", "",
         "- `gantt_week_R<R>.svg` (4 files): Monday to Friday stacked on a shared time axis, one per ride limit R in 50, 60, 70, 90.",
         "- `gantt_<date>_R<R>.svg` (20 files): one weekday and ride limit; rows are physical vehicles.", "", "Daily charts:", ""]
    for a in sorted(res, key=lambda x: (x["R"], x["date"])):
        L.append("- `gantt_%s_R%d.svg`: %s, R=%d, %d vehicles" % (a["date"], a["R"], a["wd"], a["R"], a["rec"]["vehicles"]))
    L += ["", "Weekly charts:", ""] + ["- `gantt_week_R%d.svg`: R=%d" % (R, R) for R in Rs]
    L += ["", "Verification: see `../schedule_verification.md`.", ""]
    with open(os.path.join(FIG, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
