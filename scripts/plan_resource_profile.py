#!/usr/bin/env python3
"""Resource-requirement step charts for the archived week-2026-10-05 campaign.
Standard library only. Reuses parsing and interval logic from plan_schedule_report.

Usage: python scripts/plan_resource_profile.py [results_dir]
Run plan_schedule_report.py first (it regenerates index.html, README.md and
schedule_verification.md, which this script then extends idempotently).

Layers: on-route = number of route intervals [start, end) covering t;
busy = same with each interval extended by the cooldown, [start, end + cooldown).
"""
import csv
import datetime
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_schedule_report as base  # noqa: E402,F401  (reads RES from argv[1])
from plan_schedule_report import COOLDOWN, FIG, RES, TOUR, analyse, hm, load_runs  # noqa: E402

C_BUSY, C_ROUTE, C_REQ = "#56B4E9", "#111111", "#D55E00"
C_R = {50: ("#D55E00", "none"), 60: ("#E69F00", "7 4"), 70: ("#009E73", "2 3"), 90: ("#0072B2", "9 3 2 3")}
MARK_START, MARK_END = "<!-- RESOURCE-PROFILE-START -->", "<!-- RESOURCE-PROFILE-END -->"
MD_HEAD, README_HEAD = "## Resource profile checks", "## Resource requirement charts"
PXM, X0, PAD = 1.6, 60, 24


def profile(a):
    """Segments [(t0, t1, on_route, busy)] from the exact route starts and ends."""
    ev = {}
    for r in a["routes"]:
        for t, k, d in ((r["start"], 0, 1), (r["end"], 0, -1), (r["start"], 1, 1), (r["end"] + COOLDOWN, 1, -1)):
            ev.setdefault(t, [0, 0])[k] += d
    segs, cur = [], [0, 0]
    ts = sorted(ev)
    for i, t in enumerate(ts):
        cur = [cur[0] + ev[t][0], cur[1] + ev[t][1]]
        if i + 1 < len(ts):
            segs.append((t, ts[i + 1], cur[0], cur[1]))
    return segs


def peak_windows(segs, idx):
    pk = max(s[idx] for s in segs)
    wins = []
    for s in segs:
        if s[idx] == pk:
            if wins and wins[-1][1] == s[0]:
                wins[-1][1] = s[1]
            else:
                wins.append([s[0], s[1]])
    return pk, wins


def wtxt(wins):
    return ", ".join("%s-%s" % (hm(a), hm(b)) for a, b in wins)


def esc(s):
    return html.escape(s)


def trange(runs):
    t0 = min(r["start"] for a in runs for r in a["routes"])
    t1 = max(r["end"] for a in runs for r in a["routes"]) + COOLDOWN
    return t0 - t0 % 60, t1 + (-t1) % 60


def axes(out, x0, y0, w, h, t0, t1, ymax):
    out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#fff" stroke="#888" stroke-width="0.8"/>' % (x0, y0, w, h))
    step = 1 if ymax <= 12 else 2
    for v in range(0, ymax + 1, step):
        y = y0 + h - h * v / ymax
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#e2e2e2" stroke-width="0.7"/>' % (x0, y, x0 + w, y))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="end" fill="#333">%d</text>' % (x0 - 5, y + 4, v))
    t = t0
    while t <= t1:
        x = x0 + (t - t0) * PXM
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#bbb" stroke-width="0.7"/>' % (x, y0, x, y0 + h))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#333">%s</text>' % (x, y0 + h + 14, hm(t)))
        t += 60
    out.append('<text transform="rotate(-90 %g %g)" x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Vehicles</text>' % (
        x0 - 32, y0 + h / 2, x0 - 32, y0 + h / 2))


def step_pts(segs, idx, X, Y):
    pts = []
    for s in segs:
        pts += [(X(s[0]), Y(s[idx])), (X(s[1]), Y(s[idx]))]
    return pts


def poly(pts):
    return " ".join("%g,%g" % p for p in pts)


def draw_run(out, a, segs, x0, y0, w, h, t0, t1, ymax):
    X = lambda t: x0 + (t - t0) * PXM
    Y = lambda v: y0 + h - h * v / ymax
    axes(out, x0, y0, w, h, t0, t1, ymax)
    pts = step_pts(segs, 3, X, Y)
    out.append('<polygon points="%g,%g %s %g,%g" fill="%s" fill-opacity="0.35" stroke="none"/>' % (pts[0][0], Y(0), poly(pts), pts[-1][0], Y(0), C_BUSY))
    out.append('<polyline points="%s" fill="none" stroke="#1f7fb8" stroke-width="1.2"/>' % poly(pts))
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.2"/>' % (poly(step_pts(segs, 2, X, Y)), C_ROUTE))
    req = a["rec"]["vehicles"]
    out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.6" stroke-dasharray="7 4"/>' % (x0, Y(req), x0 + w, Y(req), C_REQ))
    out.append('<text x="%g" y="%g" font-size="12" font-weight="bold" text-anchor="end" fill="%s">vehicles required = %d</text>' % (
        x0 + w - 4, Y(req) - 4 if req < ymax else Y(req) + 14, C_REQ, req))
    pk, wins = peak_windows(segs, 3)
    for wa, wb in wins:
        out.append('<rect x="%g" y="%g" width="%g" height="5" fill="%s"/>' % (X(wa), Y(pk) - 2.5, (wb - wa) * PXM, C_REQ))
        out.append('<text x="%g" y="%g" font-size="11" text-anchor="middle" fill="#222">peak %d</text>' % ((X(wa) + X(wb)) / 2, Y(pk) - 7, pk))
    for s in segs:
        tip = "%s-%s: %d on route, %d busy incl. %d-min cooldown" % (hm(s[0]), hm(s[1]), s[2], s[3], COOLDOWN)
        out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#000" fill-opacity="0"><title>%s</title></rect>' % (
            X(s[0]), y0, (s[1] - s[0]) * PXM, h, esc(tip)))


def head(W, H):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" width="%g" height="%g" font-family="Arial, Helvetica, sans-serif">'
            '<rect width="100%%" height="100%%" fill="#ffffff"/>' % (W, H, W, H))


def legend(out, x, y):
    out.append('<rect x="%g" y="%g" width="16" height="10" fill="%s" fill-opacity="0.35" stroke="#1f7fb8" stroke-width="1.2"/>'
               '<text x="%g" y="%g" font-size="12" fill="#222">Busy incl. %d-min cooldown</text>' % (x, y, C_BUSY, x + 22, y + 10, COOLDOWN))
    x += 200
    out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="2.2"/><text x="%g" y="%g" font-size="12" fill="#222">On route</text>' % (
        x, y + 5, x + 16, y + 5, C_ROUTE, x + 22, y + 10))
    x += 90
    out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.6" stroke-dasharray="7 4"/>'
               '<text x="%g" y="%g" font-size="12" fill="#222">Vehicles required</text>' % (x, y + 5, x + 16, y + 5, C_REQ, x + 22, y + 10))
    x += 140
    out.append('<rect x="%g" y="%g" width="16" height="5" fill="%s"/><text x="%g" y="%g" font-size="12" fill="#222">Peak window (busy)</text>' % (
        x, y + 3, C_REQ, x + 22, y + 10))


def subtitle(segs):
    pb, wb = peak_windows(segs, 3)
    pr, wr = peak_windows(segs, 2)
    return "Peak busy %d at %s; peak on route %d at %s" % (pb, wtxt(wb), pr, wtxt(wr))


def write(path, W, H, out):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(head(W, H) + "\n" + "\n".join(out) + "\n</svg>\n")


def fig_single(path, a, segs):
    t0, t1 = trange([a])
    ymax = max(a["rec"]["vehicles"], max(s[3] for s in segs)) + 1
    w, h = (t1 - t0) * PXM, 240
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Resource requirement, %s %s, R=%d min, tour limit %d min, %d vehicles required" % (a["wd"], a["date"], a["R"], TOUR, a["rec"]["vehicles"]))),
        '<text x="%d" y="42" font-size="12" fill="#444">%s</text>' % (PAD, esc(subtitle(segs)))]
    legend(out, PAD, 52)
    draw_run(out, a, segs, X0, 80, w, h, t0, t1, ymax)
    out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Time of day (HH:MM)</text>' % (X0 + w / 2, 80 + h + 34))
    write(path, X0 + w + PAD, 80 + h + 46, out)


def fig_week(path, R, days, profs):
    t0, t1 = trange(days)
    ymax = max(max(s[3] for s in profs[a["date"]]) for a in days)
    ymax = max(ymax, max(a["rec"]["vehicles"] for a in days)) + 1
    w, h, gap = (t1 - t0) * PXM, 150, 50
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Resource requirement, week of %s, R=%d min, tour limit %d min (shared time axis and y-scale)" % (days[0]["date"], R, TOUR)))]
    legend(out, PAD, 36)
    y = 62
    for a in days:
        segs = profs[a["date"]]
        out.append('<text x="%d" y="%g" font-size="13" font-weight="bold" fill="#111">%s %s (%d vehicles required)</text>' % (
            X0, y + 12, a["wd"], a["date"], a["rec"]["vehicles"]))
        out.append('<text x="%g" y="%g" font-size="11" fill="#444">%s</text>' % (X0 + 330, y + 12, esc(subtitle(segs))))
        draw_run(out, a, segs, X0, y + 20, w, h, t0, t1, ymax)
        y += 20 + h + gap
    out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Time of day (HH:MM)</text>' % (X0 + w / 2, y - 14))
    write(path, X0 + w + PAD, y, out)


def fig_compare(path, date, runs, profs):
    t0, t1 = trange(runs)
    ymax = max(max(s[3] for s in profs[(date, a["R"])]) for a in runs) + 1
    w, h, y0 = (t1 - t0) * PXM, 260, 84
    X = lambda t: X0 + (t - t0) * PXM
    Y = lambda v: y0 + h - h * v / ymax
    out = ['<text x="%d" y="24" font-size="16" font-weight="bold" fill="#111">%s</text>' % (
        PAD, esc("Busy vehicles incl. %d-min cooldown by ride limit R, %s %s" % (COOLDOWN, runs[0]["wd"], date))),
        '<text x="%d" y="42" font-size="12" fill="#444">Event-based step functions; hover a segment for the counts of all four R values.</text>' % PAD]
    lx = PAD
    for a in runs:
        R = a["R"]
        col, dash = C_R[R]
        pk, _ = peak_windows(profs[(date, R)], 3)
        txt = "R=%d: peak %d (required %d)" % (R, pk, a["rec"]["vehicles"])
        out.append('<line x1="%g" y1="57" x2="%g" y2="57" stroke="%s" stroke-width="2.4" stroke-dasharray="%s"/>'
                   '<text x="%g" y="61" font-size="12" fill="#222">%s</text>' % (lx, lx + 30, col, dash, lx + 36, esc(txt)))
        lx += 36 + 7 * len(txt) + 20
    axes(out, X0, y0, w, h, t0, t1, ymax)
    for a in runs:
        col, dash = C_R[a["R"]]
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4" stroke-dasharray="%s"/>' % (
            poly(step_pts(profs[(date, a["R"])], 3, X, Y)), col, dash))
    cuts = sorted({t for a in runs for s in profs[(date, a["R"])] for t in (s[0], s[1])})
    for p, q in zip(cuts, cuts[1:]):
        vals = []
        for a in runs:
            v = [s for s in profs[(date, a["R"])] if s[0] <= p < s[1]]
            vals.append("R=%d: %d" % (a["R"], v[0][3] if v else 0))
        out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#000" fill-opacity="0"><title>%s</title></rect>' % (
            X(p), y0, (q - p) * PXM, h, esc("%s-%s busy incl. cooldown: %s" % (hm(p), hm(q), ", ".join(vals)))))
    out.append('<text x="%g" y="%g" font-size="12" text-anchor="middle" fill="#222">Time of day (HH:MM)</text>' % (X0 + w / 2, y0 + h + 34))
    write(path, X0 + w + PAD, y0 + h + 46, out)


def cut(text, marker):
    i = text.find(marker)
    return text if i < 0 else text[:i].rstrip("\n") + "\n"


def main():
    runs = load_runs()
    assert len(runs) == 20, len(runs)
    with open(os.path.join(RES, "summary.csv"), encoding="utf-8") as f:
        summ = {(r["date"], int(r["ride_limit"])): int(r["vehicles_required"]) for r in csv.DictReader(f)}
    res, profs = [], {}
    for date, R, d in runs:
        a = analyse(date, R, d)
        a["wd"] = datetime.date.fromisoformat(date).strftime("%A")
        res.append(a)
        profs[(date, R)] = profile(a)
    os.makedirs(FIG, exist_ok=True)
    rows, bad = [], []
    for a in sorted(res, key=lambda x: (x["R"], x["date"])):
        segs = profs[(a["date"], a["R"])]
        req = a["rec"]["vehicles"]
        pr, wr = peak_windows(segs, 2)
        pb, wb = peak_windows(segs, 3)
        probs = []
        if pb != req:
            probs.append("peak busy %d != vehicles_required %d" % (pb, req))
        if pr > req:
            probs.append("peak on-route %d > vehicles_required %d" % (pr, req))
        if summ.get((a["date"], a["R"])) != req:
            probs.append("summary.csv vehicles_required %s != %d" % (summ.get((a["date"], a["R"])), req))
        if probs:
            bad.append("%s R=%d: %s" % (a["date"], a["R"], "; ".join(probs)))
        rows.append("| %s | %s | %d | %d | %d | %d | %s | %s | %s |" % (
            a["date"], a["wd"][:3], a["R"], pr, pb, req, wtxt(wr), wtxt(wb), "FAIL" if probs else "pass"))
        fig_single(os.path.join(FIG, "resource_%s_R%d.svg" % (a["date"], a["R"])), a, segs)
    Rs = sorted({a["R"] for a in res})
    for R in Rs:
        days = sorted([a for a in res if a["R"] == R], key=lambda x: x["date"])
        fig_week(os.path.join(FIG, "resource_week_R%d.svg" % R), R, days, {a["date"]: profs[(a["date"], R)] for a in days})
    dates = sorted({a["date"] for a in res})
    for date in dates:
        rs = sorted([a for a in res if a["date"] == date], key=lambda x: x["R"])
        fig_compare(os.path.join(FIG, "resource_compare_%s.svg" % date), date, rs, profs)

    md = os.path.join(RES, "schedule_verification.md")
    with open(md, encoding="utf-8") as f:
        txt = cut(f.read(), "\n" + MD_HEAD)
    sec = ["", MD_HEAD, "",
           "Generated by `scripts/plan_resource_profile.py`. Event-based step functions from the exact route starts and ends: "
           "on-route counts intervals [start, end); busy counts [start, end + %d min cooldown). Checks: peak busy must equal "
           "vehicles_required (assignment lower bound), peak on-route must be <= vehicles_required, vehicles_required must match "
           "summary.csv." % COOLDOWN, "",
           "Result: %s" % ("all 20 runs pass." if not bad else "%d mismatch(es), listed below." % len(bad)), ""]
    sec += ["- MISMATCH " + b for b in bad] + ([""] if bad else [])
    sec += ["| Date | Day | R | Peak on route | Peak busy | vehicles_required | Peak on-route window(s) | Peak busy window(s) | Result |",
            "|---|---|---|---|---|---|---|---|---|"] + rows
    with open(md, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt + "\n".join(sec) + "\n")

    H = [MARK_START, "<h1>Resource requirement</h1>",
         "<p>Event-based step charts (scripts/plan_resource_profile.py). Dark line: vehicles on a route; light fill: busy incl. cooldown; "
         "dashed: vehicles required. Hover a segment for counts.</p><ul>"]
    for R in Rs:
        H.append('<li><a href="#resweek%d">Week R=%d</a></li>' % (R, R))
    for d in dates:
        H.append('<li><a href="#rescmp%s">Compare R values, %s</a></li>' % (d, d))
    H.append("</ul>")
    for d in dates:
        H.append('<h2 id="rescmp%s">Compare R values, %s</h2><img src="resource_compare_%s.svg" alt="Busy vehicles by R, %s">' % (d, d, d, d))
    for R in Rs:
        H.append('<h2 id="resweek%d">Week, R=%d</h2><img src="resource_week_R%d.svg" alt="Resource week R=%d">' % (R, R, R, R))
        for a in sorted([x for x in res if x["R"] == R], key=lambda x: x["date"]):
            H.append('<h3>%s %s, R=%d (%d vehicles)</h3><img src="resource_%s_R%d.svg" alt="Resource %s R=%d">' % (
                a["wd"], a["date"], R, a["rec"]["vehicles"], a["date"], R, a["date"], R))
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
        t = cut(f.read(), "\n" + README_HEAD)
    L = ["", README_HEAD, "",
         "Event-based step charts from `scripts/plan_resource_profile.py` (run after `plan_schedule_report.py`). Dark line = vehicles on a route; "
         "light fill = busy including the 10-min cooldown; dashed line = vehicles required; red bar = peak window. "
         "Hover a segment for its time window and counts.", "",
         "- `resource_<date>_R<R>.svg` (20 files): one run each.",
         "- `resource_week_R<R>.svg` (4 files): Monday to Friday stacked, shared time axis and y-scale.",
         "- `resource_compare_<date>.svg` (5 files): busy-including-cooldown lines for R = 50, 60, 70, 90 (colour plus dash pattern).", "",
         "Checks (peak busy = vehicles required, peak on route <= vehicles required): `../schedule_verification.md`, section 'Resource profile checks'.", ""]
    with open(rp, "w", encoding="utf-8", newline="\n") as f:
        f.write(t + "\n".join(L))
    print("mismatches:", bad or "none")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
