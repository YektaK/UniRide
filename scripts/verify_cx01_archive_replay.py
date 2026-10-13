#!/usr/bin/env python3
"""CX-01 archive replay (offline): does the exact centi-minute interval contract change any archived result?

Reads only the committed archives under docs/paper/results/week-2026-10-05-fleet (never the DB or HTTP).
For every labelled (date, R, scenario) response file the archived chosen routes are rebuilt as a one-option
menu per wave with the label fixed by the archived ``selectionLabel`` and passed to
``uniride_core.planning.typed_day_selection.solve_day_selection`` two ways:

  OLD  whole-minute floor(start)/ceil(end) at scale 1, cooldown in raw minutes
       (8ab88ca:src/services/fleet-scenario-run.ts:530-548).
  NEW  exact centi-minute endpoints at time_scale 100, cooldown x100
       (src/services/fleet-scenario-run.ts, CX-01); an off-grid value is refused, never rounded.

Status, cars and large_peak are compared, cars is also compared with the archived ``scenario.cars``, and per
campaign the arcs and route endpoints are counted, with how many are non-integer.

Run (from the repository root):
  PYTHON_DOTENV_DISABLED=1 PYTHONPATH=optimizer_api .venv-jit/Scripts/python.exe -B scripts/verify_cx01_archive_replay.py
Exit code 1 when any OLD/NEW difference, archived-cars mismatch or non-integer value is found.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from uniride_core.planning.typed_day_selection import (  # noqa: E402
    SOLVER_SEED, Option, Route, Wave, solve_day_selection,
)

TIME_SCALE = 100
CENTI_TOLERANCE = 1e-6
FLEET = Path("docs/paper/results/week-2026-10-05-fleet")
# explicit allow-list: campaign key -> (directory relative to FLEET, recurse?)
ALLOWED = {
    "fleet (A, L1-L3)": (Path("."), False),
    "extra/minivan-cap3": (Path("extra/minivan-cap3"), True),
    "extra/L4": (Path("extra/L4"), True),
}
# superseded directories: never read
REFUSED = {
    "week-2026-10-05": "INVALID: wrong capacity 4 Sw / 10 So, superseded (X01)",
    "extra/minivan": "superseded: capacity 1 Sw + 3 So (DECISION_LOG H03)",
}
COMMAND = ("PYTHON_DOTENV_DISABLED=1 PYTHONPATH=optimizer_api .venv-jit/Scripts/python.exe -B "
           "scripts/verify_cx01_archive_replay.py")


def to_units(value: float, mode: str, how: str = "start") -> int:
    """One endpoint in solver units. old: floor (start) / ceil (end) minutes; new: exact centi-minutes."""
    if mode == "old":
        return max(0, math.floor(value) if how == "start" else math.ceil(value))
    scaled = value * TIME_SCALE
    rounded = round(scaled)
    if not math.isfinite(scaled) or abs(scaled - rounded) > CENTI_TOLERANCE:
        raise ValueError(f"endpoint {value!r} is off the 0.01-minute grid")
    return max(0, rounded)


def cooldown_units(minutes: float, mode: str) -> int:
    return int(minutes) if mode == "old" else to_units(minutes, "new")


def build_input(routes, mode: str, cooldown_minutes: float = 10):
    """(waves, cooldown_units, time_scale): one single-option wave per jobId, labels fixed by selectionLabel."""
    if mode not in ("old", "new"):
        raise ValueError(mode)
    by_wave: dict = {}
    for r in routes:
        by_wave.setdefault(r["jobId"], []).append(r)
    waves = []
    for wave_id in sorted(by_wave):
        built = []
        for r in by_wave[wave_id]:
            start = to_units(r["startMinutes"], mode, "start")
            end = max(start + 1, to_units(r["endMinutes"], mode, "end"))
            built.append(Route(start, end, float(r["minutes"]),
                               r["selectionLabel"] == "large", r["selectionLabel"] == "car"))
        waves.append(Wave(wave_id, (Option("archived", tuple(built), True),)))
    return tuple(waves), cooldown_units(cooldown_minutes, mode), (1 if mode == "old" else TIME_SCALE)


def _is_int(v) -> bool:
    return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer())


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _solve(routes, mode, limit, cd_large, cd_car, max_cars, time_limit):
    waves, _, _ = build_input(routes, mode)
    res = solve_day_selection(
        waves, limit, cooldown_large=cooldown_units(cd_large, mode), cooldown_car=cooldown_units(cd_car, mode),
        max_cars=max_cars, time_limit_s=time_limit)
    return res.status, res.cars, res.large_peak


def check_campaign(results: Path, key: str, sub: Path, recurse: bool):
    root = results / sub
    manifest = _load(root / "run_manifest.json")
    params = manifest["parameters"]
    solver = manifest["selection_solver"]
    cd = {t["typeId"]: t["cooldownMinutes"] for t in manifest["fleet_types"]}
    fixed = manifest.get("fixed_type") or "large"
    other = [t for t in cd if t != fixed][0]
    time_limit = float(params["selection_time_limit_seconds"])
    max_cars = params.get("max_cars")
    files = sorted((root.rglob if recurse else root.glob)("*.response.json"))
    stat = {"campaign": key, "commit": manifest["git_commit"][:7], "response_files": len(files),
            "labelled_files": 0, "unlabelled_or_empty_files": 0, "arcs": 0, "arcs_non_integer": 0,
            "route_endpoints": 0, "endpoints_non_integer": 0, "diffs": 0, "cars_mismatch": 0,
            "solver_params_match": solver["num_workers"] == 1 and solver["random_seed"] == SOLVER_SEED,
            "time_limit_s": time_limit, "max_cars": max_cars, "cooldown": f"{fixed}={cd[fixed]}, {other}={cd[other]}"}
    rows = []
    for m in sorted((root.rglob if recurse else root.glob)("*.matrix.json")):
        for arc in _load(m)["arcs"]:
            stat["arcs"] += 1
            stat["arcs_non_integer"] += not _is_int(arc["duration_minutes"])
    for f in files:
        sc = _load(f).get("scenario") or {}
        routes = sc.get("routes") or []
        frac = 0
        for r in routes:
            for k in ("startMinutes", "endMinutes"):
                stat["route_endpoints"] += 1
                if not _is_int(r[k]):
                    stat["endpoints_non_integer"] += 1
                    frac += 1
        if not routes or any(r.get("selectionLabel") not in ("large", "car") for r in routes):
            stat["unlabelled_or_empty_files"] += 1
            continue
        stat["labelled_files"] += 1
        stem = f.name.replace(".response.json", "")
        date, rest = stem.split("_", 1)
        ride, scen = rest.split("_", 1)
        limit = int(sc["largeLimit"])
        old = _solve(routes, "old", limit, cd[fixed], cd[other], max_cars, time_limit)
        new = _solve(routes, "new", limit, cd[fixed], cd[other], max_cars, time_limit)
        same = old == new
        cars_ok = new[1] == sc.get("cars") and old[1] == sc.get("cars")
        stat["diffs"] += not same
        stat["cars_mismatch"] += not cars_ok
        rows.append({"campaign": key, "date": date, "R": ride, "scenario": scen, "file": f.name, "routes": len(routes),
                     "waves": len({r["jobId"] for r in routes}), "large_limit": limit, "archived_cars": sc.get("cars"),
                     "old_status": old[0], "old_cars": old[1], "old_large_peak": old[2],
                     "new_status": new[0], "new_cars": new[1], "new_large_peak": new[2],
                     "old_equals_new": same, "cars_equals_archived": cars_ok, "non_integer_endpoints": frac})
    return stat, rows


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=str(REPO / FLEET))
    ap.add_argument("--out-dir", default=str(REPO / FLEET))
    args = ap.parse_args()
    results, out = Path(args.results_dir), Path(args.out_dir)
    stats, rows = [], []
    for key, (sub, recurse) in ALLOWED.items():
        s, r = check_campaign(results, key, sub, recurse)
        stats.append(s)
        rows += r
    import ortools
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "cx01_replay_check.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    keys = ("response_files", "labelled_files", "unlabelled_or_empty_files", "arcs", "arcs_non_integer",
            "route_endpoints", "endpoints_non_integer", "diffs", "cars_mismatch")
    tot = {k: sum(s[k] for s in stats) for k in keys}
    dirty = "dirty" if _git("status", "--porcelain", "--untracked-files=no") else "clean"
    lines = [
        "# CX-01 archive replay check", "",
        "Offline replay of `uniride_core.planning.typed_day_selection.solve_day_selection` on the archived chosen routes of "
        "every labelled fleet day (one single-option menu per wave, label fixed by the archived `selectionLabel`), two ways:", "",
        "- OLD: whole-minute floor(start)/ceil(end), scale 1, raw-minute cooldown (pre-fix producer, "
        "`8ab88ca:src/services/fleet-scenario-run.ts:530-548`).",
        f"- NEW: exact centi-minute endpoints, `time_scale` {TIME_SCALE}, cooldown x{TIME_SCALE} (DECISION_LOG H05).", "",
        f"- Script: `scripts/verify_cx01_archive_replay.py`; command: `{COMMAND}`",
        f"- Repository commit at run time: `{_git('rev-parse', 'HEAD')}` (tracked files {dirty})",
        f"- ortools {ortools.__version__}; solver seed {SOLVER_SEED}, 1 worker (as recorded in each manifest `selection_solver`); "
        "time limit and max_cars from each manifest",
        "- Allow-list: " + ", ".join(f"`{k}`" for k in ALLOWED) + "; refused, never read: "
        + ", ".join(f"`{k}` ({v})" for k, v in REFUSED.items()), "",
        "| Campaign | Commit | Response files | Labelled days replayed | Unlabelled / no routes | Arcs | Non-integer arcs "
        "| Route endpoints | Non-integer endpoints | OLD vs NEW differences | Cars != archived | Time limit (s) | Cooldown (min) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in stats:
        lines.append(
            f"| {s['campaign']} | {s['commit']} | {s['response_files']} | {s['labelled_files']} | {s['unlabelled_or_empty_files']} "
            f"| {s['arcs']} | {s['arcs_non_integer']} | {s['route_endpoints']} | {s['endpoints_non_integer']} | {s['diffs']} "
            f"| {s['cars_mismatch']} | {s['time_limit_s']:g} | {s['cooldown']} |")
    lines.append(
        f"| **Total** | | {tot['response_files']} | {tot['labelled_files']} | {tot['unlabelled_or_empty_files']} | {tot['arcs']} "
        f"| {tot['arcs_non_integer']} | {tot['route_endpoints']} | {tot['endpoints_non_integer']} | {tot['diffs']} "
        f"| {tot['cars_mismatch']} | | |")
    ok = (tot["diffs"] == 0 and tot["cars_mismatch"] == 0 and tot["arcs_non_integer"] == 0
          and tot["endpoints_non_integer"] == 0 and all(s["solver_params_match"] for s in stats))
    lines += [
        "", f"Result: {'no difference' if ok else 'DIFFERENCE FOUND'}. Status, cars and large_peak are compared per file; "
        "`cars` is also compared with the archived `scenario.cars`. Unlabelled files are scenario A (no typed selection) "
        "and infeasible scenarios without routes. One row per replayed file is in `cx01_replay_check.csv`.",
        "The archive holds only the chosen routes, not the full per-wave menus, so this replays the selection stage on the "
        "chosen routes; it does not re-run the GA menus."]
    (out / "cx01_replay_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
