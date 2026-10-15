#!/usr/bin/env python3
"""WP-E1 measurement: route enumeration column and label counts on every archived wave.

Offline (reads only the archive through scripts/exact_archive_loader.py). Enumerates every
wave of the three valid campaigns for every R: the 4sw5so archive with its single type, and
the two typed fleets (large+sedan, large+Doblo cap3) with both manifest types together.
Runs WITHOUT a label cap (the measurement fixes the cap) and with the default column cap
and wall-clock safety limit.

Run: python scripts/measure_exact_enumeration.py [--out DIR] [--only-wave WAVE_ID] [--rides 50,60]
Writes DIR/enumeration_counts.csv and DIR/summary.json (DIR defaults to
docs/paper/results/week-2026-10-05-exact/wp-e1-enumeration).
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

from uniride_core.exact.route_enumeration import (  # noqa: E402
    COLUMN_CAP_DEFAULT,
    LABEL_CAP_DEFAULT,
    WALL_CLOCK_LIMIT_DEFAULT,
    enumerate_wave,
)

RESULTS = REPO / "docs" / "paper" / "results"
DEFAULT_OUT = RESULTS / "week-2026-10-05-exact" / "wp-e1-enumeration"
FLEET_LABEL = {"4sw5so": "single_4sw5so", "fleet": "large+sedan", "minivan-cap3": "large+doblo_cap3"}
FIELDS = ["fleet", "types", "service_date", "R", "wave_id", "direction", "anchor_minutes", "legs", "items",
          "peak", "status", "cap_fired", "model", "columns", "labels", "max_labels_per_level", "levels",
          "seconds"]


def _loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader_m", REPO / "scripts" / "exact_archive_loader.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_m"] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--only-wave", default=None)
    ap.add_argument("--rides", default=None)
    args = ap.parse_args(argv[1:])
    loader = _loader()
    campaigns = loader.load_all_valid(RESULTS)
    peaks = {w for v in loader.peak_waves(campaigns).values() for w in v["wave_ids"]}
    rides_filter = {int(x) for x in args.rides.split(",")} if args.rides else None
    rows = []
    for key, camp in campaigns.items():
        types = camp.fleet_types
        tdesc = "+".join(f"{t.type_id}:{t.sw_capacity}sw{t.so_capacity}so"
                         + (f":cap{t.total_capacity}" if t.total_capacity is not None else "") for t in types)
        for ride in camp.rides:
            if rides_filter and ride not in rides_filter:
                continue
            for w in camp.waves_for(ride):
                if args.only_wave and w.wave_id != args.only_wave:
                    continue
                t0 = time.perf_counter()
                res = enumerate_wave(w, types, label_cap=None)
                secs = time.perf_counter() - t0
                row = dict(fleet=FLEET_LABEL[key], types=tdesc, service_date=w.service_date, R=ride,
                           wave_id=w.wave_id, direction=w.direction, anchor_minutes=w.anchor_minutes, legs=w.legs,
                           items=len(res.items), peak=w.wave_id in peaks, status=res.status,
                           cap_fired=res.cap_fired or "", model=res.model or "", columns=res.column_count,
                           labels=res.label_count, max_labels_per_level=max(res.labels_per_level, default=0),
                           levels=len(res.labels_per_level), seconds=round(secs, 3))
                rows.append(row)
                print(f"{row['fleet']:17s} R{ride} {w.wave_id:40s} legs={w.legs:2d} items={row['items']:2d} "
                      f"{res.status:8s} cols={res.column_count:9d} labels={res.label_count:10d} {secs:8.2f}s",
                      flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "enumeration_counts.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
    summary = {
        "work_package": "WP-E1",
        "design": "docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 1.1 Step A",
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "dirty_working_tree": bool(_git("status", "--porcelain", "--", "uniride_core", "scripts")),
        "python": platform.python_version(),
        "host_os": platform.system(),
        "caps_used": {"column_cap": COLUMN_CAP_DEFAULT, "label_cap": None,
                      "wall_clock_limit_seconds": WALL_CLOCK_LIMIT_DEFAULT},
        "label_cap_default_in_code": LABEL_CAP_DEFAULT,
        "rows": len(rows),
        "caps_fired": sorted({r["cap_fired"] for r in rows if r["cap_fired"]}),
        "per_fleet_R": {},
    }
    for r in rows:
        k = f"{r['fleet']} R{r['R']}"
        s = summary["per_fleet_R"].setdefault(k, {"waves": 0, "max_columns": 0, "max_labels": 0, "max_seconds": 0.0,
                                                  "sum_seconds": 0.0, "argmax_labels": ""})
        s["waves"] += 1
        s["max_columns"] = max(s["max_columns"], r["columns"])
        if r["labels"] > s["max_labels"]:
            s["max_labels"], s["argmax_labels"] = r["labels"], r["wave_id"]
        s["max_seconds"] = max(s["max_seconds"], r["seconds"])
        s["sum_seconds"] = round(s["sum_seconds"] + r["seconds"], 3)
    if not args.only_wave and not rides_filter:
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["per_fleet_R"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
