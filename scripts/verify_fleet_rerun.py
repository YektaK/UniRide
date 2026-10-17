#!/usr/bin/env python3
"""Offline acceptance checks of a WP-E10 fleet re-run archive (design section 9, rules (d), (e), (g) and the composition of (a)).

Reads archives only (JSON files and `git diff`); never touches the database, the optimizer or the network.

    python scripts/verify_fleet_rerun.py --rerun-dir <new archive> --single-archive docs/paper/results/week-2026-10-05-4sw5so \
        --historical-dir docs/paper/results/week-2026-10-05-fleet [--double-run-dir <second run of one day>] [--base <git rev>]

Checks (exit code 1 when any fails):
  composition  per cell and wave, the occurrence ids and Sw/So counts of the re-run base option equal the 4sw5so archive (rule (a), again after the run)
  (d) anchor   per cell and wave, the re-run `base` routes (stop order, step minutes, anonymised occurrence ids) equal the 4sw5so `_repeat1` routes
  (d) selected per (cell, L, wave), the archived selected option is compared with the same option of the re-run; every difference gets a category:
                 identical                         same routes, same selection
                 selection_changed_h06_expected    narrow: both days optimal with equal cars and largeVehicles, every archived selected option identical
                                                   in the re-run menu, and either total lower with car-minutes higher, or both equal (index tie):
                                                   the H06 order change (total vehicle-minutes before car-minutes, 2026-10-13)
                 selection_changed_unexplained     any other changed selection                              (unexplained, fails)
                 scenario_outcome_differs          status, cars, largeVehicles, selection status or wave keys differ, or a scenario exists on one side only (fails)
                 both_not_ok_identical             both sides infeasible with the same outcome
                 option_absent_in_rerun            the option has no routes in the re-run menu            (unexplained, fails)
                 routes_differ_unexplained         the same option has other routes                         (unexplained, fails)
  (e)          with --double-run-dir: every *.menu_options.json of the second run is byte-identical to the same file of the first
  (g)          `git diff --stat` and `git status --porcelain` over the three historical directories are empty (and, with --base, `git diff --stat <base> HEAD`)
"""
import argparse
import json
import os
import subprocess
import sys

HISTORICAL_DIRS = [
    "docs/paper/results/week-2026-10-05",
    "docs/paper/results/week-2026-10-05-4sw5so",
    "docs/paper/results/week-2026-10-05-fleet",
]


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def cells_of(manifest):
    return [(run["date"], run["ride_limit"]) for run in manifest["runs"]]


def route_canon(steps, ids):
    return (tuple((s["location1"], s["location2"], s["duration"]) for s in steps), tuple(ids))


def single_waves(single_dir, date, ride):
    """wave id -> (sorted route canon list, sorted occurrence ids, Sw, So) from the 4sw5so response."""
    doc = load(os.path.join(single_dir, f"{date}_R{ride}_repeat1.response.json"))
    waves = {}
    for job in doc["jobs"]:
        routes = sorted(route_canon(r["route_details"], r["student_ids"]) for r in job["result"]["routes"])
        waves[job["id"]] = {"routes": routes, "ids": [], "sw": 0, "so": 0}
    for interval in doc["routeIntervals"]:
        wave = waves[interval["jobId"]]
        wave["ids"] += interval["occurrenceIds"]
        wave["sw"] += interval["swCount"]
        wave["so"] += interval["soCount"]
    for wave in waves.values():
        wave["ids"].sort()
    return waves


def menu_options(rerun_dir, date, ride):
    doc = load(os.path.join(rerun_dir, f"{date}_R{ride}.menu_options.json"))
    return {wave["waveId"]: {opt["optionId"]: opt for opt in wave["options"]} for wave in doc["waves"]}


def option_routes_by_interval(option):
    """Routes of a menu option as (steps, occurrence ids), the form of a selected route in a response file."""
    out = []
    for route in option["routes"]:
        ids = route["interval"]["occurrenceIds"] if route.get("interval") else []
        out.append(route_canon(route["steps"], ids))
    return sorted(out)


def check_anchor_and_composition(rerun_dir, single_dir, cells, failures, report):
    waves_checked = 0
    for date, ride in cells:
        reference = single_waves(single_dir, date, ride)
        menu = menu_options(rerun_dir, date, ride)
        if set(reference) != set(menu):
            failures.append(f"{date} R{ride}: wave ids differ between the re-run menu and the 4sw5so archive")
            continue
        for wave_id, ref in reference.items():
            base = menu[wave_id].get("base")
            if base is None or not base["routes"]:
                failures.append(f"{date} R{ride} {wave_id}: no base option routes in the re-run")
                continue
            waves_checked += 1
            ids = sorted(i for r in base["routes"] for i in (r["interval"]["occurrenceIds"] if r.get("interval") else []))
            sw = sum(r["swCount"] for r in base["routes"])
            so = sum(r["soCount"] for r in base["routes"])
            if ids != ref["ids"] or (sw, so) != (ref["sw"], ref["so"]):
                failures.append(f"{date} R{ride} {wave_id}: composition differs from the 4sw5so archive (ids or Sw/So counts)")
            rerun_routes = sorted(route_canon(r["steps"], r["studentIds"]) for r in base["routes"])
            if rerun_routes != ref["routes"]:
                failures.append(f"{date} R{ride} {wave_id}: base routes differ from the 4sw5so routes (stop order, step minutes or ids)")
    report["waves_checked_against_4sw5so"] = waves_checked


def scenario_files(directory, date, ride):
    """scenario name (L1, L2, ...) -> response file of one cell."""
    prefix, suffix = f"{date}_R{ride}_L", ".response.json"
    return {name[len(f"{date}_R{ride}_"):-len(suffix)]: os.path.join(directory, name)
            for name in os.listdir(directory) if name.startswith(prefix) and name.endswith(suffix)}


def outcome_of(scenario):
    selection = scenario.get("selection") or {}
    return {
        # scenario.cars is the assignment's minimumCount; selection.cars is the CP-SAT stage-1 value: both are compared
        "status": scenario.get("status"), "cars": scenario.get("cars"), "largeVehicles": scenario.get("largeVehicles"),
        "selection.cars": selection.get("cars"), "selection.status": selection.get("status"), "waves": sorted((selection.get("optionByWave") or {}).keys()),
    }


def h06_improvement(old, new):
    """True only for a change that H06 explains, with both runs optimal, equal cars and every archived selected option unchanged in the re-run menu.

    DECISION_LOG H06 (2026-10-13) changed the day-selection order (typed_day_selection.py):
        before H06: (cars, car-minutes, total vehicle-minutes, option indices)
        after  H06: (cars, total vehicle-minutes, car-minutes, option indices)
    Same cars, archived selected options unchanged. The old run minimised car-minutes first, so the old selection has the least car-minutes among
    the equal-cars selections and, among those, the least total. The new run minimises total first. A genuinely different
    selection is therefore possible in exactly two ways:
      1. total vehicle-minutes strictly lower AND car-minutes strictly higher: the new order trades car-minutes for total
         (the old order would never have accepted the higher car-minutes);
      2. both values equal: only the option-index tie-break (stage 4) differs.
    The other combinations cannot come from H06 when the archived selected options are unchanged, because the OLD order would already have chosen the
    new selection: total lower with car-minutes equal or lower, or total equal with car-minutes lower (the old order prefers
    lower car-minutes first). A total that is higher can never win under the new order. All of these are unexplained.
    Limit: only the archived SELECTED options can be compared. Options that were never selected cannot be, so the new
    selection may use a new or changed option. H06 is then a necessary cause of the change, not proven to be the only one.
    Both carMinutes values and both totals are required; a missing value is unexplained.
    """
    eps = 1e-6

    def num(scenario, key):
        value = scenario.get(key)
        return value if isinstance(value, (int, float)) else None
    old_total, new_total = num(old, "totalVehicleMinutes"), num(new, "totalVehicleMinutes")
    old_car, new_car = num(old.get("selection") or {}, "carMinutes"), num(new.get("selection") or {}, "carMinutes")
    if None in (old_total, new_total, old_car, new_car):
        return False
    d_total, d_car = new_total - old_total, new_car - old_car
    if d_total < -eps and d_car > eps:
        return True
    return abs(d_total) <= eps and abs(d_car) <= eps


def check_selected_options(rerun_dir, hist_dir, cells, manifest, failures, report):
    counts = {}

    def count(category, failing=False, message=None, amount=1):
        counts[category] = counts.get(category, 0) + amount
        if failing:
            failures.append(message or category)

    for date, ride in cells:
        menu = menu_options(rerun_dir, date, ride)
        old_files, new_files = scenario_files(hist_dir, date, ride), scenario_files(rerun_dir, date, ride)
        for name in sorted(set(old_files) | set(new_files)):
            cell = f"{date} R{ride} {name}"
            if name not in new_files or name not in old_files:
                side = "only in the old archive" if name not in new_files else "only in the re-run"
                count("scenario_outcome_differs", True, f"{cell}: scenario_outcome_differs: scenario {side}")
                continue
            old, new = load(old_files[name])["scenario"], load(new_files[name])["scenario"]
            old_outcome, new_outcome = outcome_of(old), outcome_of(new)
            if old_outcome != new_outcome:
                fields = [k for k in old_outcome if old_outcome[k] != new_outcome[k]]
                count("scenario_outcome_differs", True, f"{cell}: scenario_outcome_differs: {', '.join(fields)} (old {[old_outcome[k] for k in fields]}, new {[new_outcome[k] for k in fields]})")
                continue
            if old_outcome["status"] != "ok":
                count("both_not_ok_identical")  # e.g. both infeasible_for_L with the same diagnostics status: nothing selected to compare
                continue
            old_selection = (old.get("selection") or {}).get("optionByWave") or {}
            new_selection = (new.get("selection") or {}).get("optionByWave") or {}
            options_identical, changed = True, []
            for wave_id, option_id in old_selection.items():
                old_routes = sorted(route_canon(r["steps"], r["occurrenceIds"]) for r in old["routes"] if r["jobId"] == wave_id)
                option = menu.get(wave_id, {}).get(option_id)
                if option is None or not option["routes"]:
                    options_identical = False
                    count("option_absent_in_rerun", True, f"{cell} {wave_id}: archived selected option {option_id}: option_absent_in_rerun")
                elif option_routes_by_interval(option) != old_routes:
                    options_identical = False
                    count("routes_differ_unexplained", True, f"{cell} {wave_id}: archived selected option {option_id}: routes_differ_unexplained")
                elif new_selection.get(wave_id) == option_id:
                    count("identical")
                else:
                    changed.append(wave_id)
            if not changed:
                continue
            # selection_changed_h06_expected only when the old selection is still feasible in the re-run (every archived selected
            # option is identical in the re-run menu), both days are optimal with the same cars and large vehicles (outcome equal
            # above), and the re-run is not worse under the H06 order.
            both_optimal = old_outcome["selection.status"] == "optimal" and new_outcome["selection.status"] == "optimal"
            if options_identical and both_optimal and h06_improvement(old, new):
                count("selection_changed_h06_expected", amount=len(changed))
            else:
                count("selection_changed_unexplained", True, f"{cell}: selection_changed_unexplained: {len(changed)} wave(s) selected another option", amount=len(changed))
    report["selected_option_categories"] = dict(sorted(counts.items()))


def check_double_run(first_dir, second_dir, failures, report):
    second_manifest_path = os.path.join(second_dir, "run_manifest.json")
    second = load(second_manifest_path) if os.path.exists(second_manifest_path) else {}
    if second.get("run_kind") != "rule_e_second_run" or not (second.get("parameters") or {}).get("allow_subset_dates"):
        failures.append("(e) the second run is not labelled as a rule (e) second run (run_kind, parameters.allow_subset_dates)")
    if second.get("state") != "completed":
        failures.append("(e) the second run is not completed")
    names = sorted(n for n in os.listdir(second_dir) if n.endswith(".menu_options.json"))
    if not names:
        failures.append("(e) the second run holds no *.menu_options.json")
    same = 0
    for name in names:
        other = os.path.join(first_dir, name)
        if not os.path.exists(other):
            failures.append(f"(e) {name} is missing in the first run")
            continue
        with open(other, "rb") as a, open(os.path.join(second_dir, name), "rb") as b:
            if a.read() == b.read():
                same += 1
            else:
                failures.append(f"(e) {name} differs between the two runs")
    report["double_run_files_identical"] = f"{same}/{len(names)}"


def check_history_untouched(repo, base, failures, report):
    def git(*args):
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=120, check=True).stdout.strip()
    stat = git("diff", "--stat", "HEAD", "--", *HISTORICAL_DIRS)
    status = git("status", "--porcelain", "--untracked-files=all", "--", *HISTORICAL_DIRS)
    if stat or status:
        failures.append("(g) the historical archive directories are not untouched")
    if base:
        since = git("diff", "--stat", base, "HEAD", "--", *HISTORICAL_DIRS)
        if since:
            failures.append(f"(g) the historical archive directories changed since {base}")
    report["history_untouched"] = not (stat or status)


def verify(args):
    failures, report = [], {}
    manifest = load(os.path.join(args.rerun_dir, "run_manifest.json"))
    cells = cells_of(manifest)
    if manifest.get("run_kind") == "rule_e_second_run" or (manifest.get("parameters") or {}).get("allow_subset_dates"):
        failures.append("the --rerun-dir is a rule (e) second run (subset of the dates), not a campaign archive")
    elif manifest.get("run_kind") != "campaign":
        failures.append("run_manifest.json has no run_kind 'campaign': the archive is not labelled as a campaign")
    if manifest.get("state") != "completed":
        failures.append("the re-run manifest is not completed")
    if len(cells) != args.expected_cells or len(set(cells)) != len(cells):
        failures.append(f"expected {args.expected_cells} distinct (date, R) cells, found {len(set(cells))}")
    report["cells"] = len(cells)
    check_anchor_and_composition(args.rerun_dir, args.single_archive, cells, failures, report)
    check_selected_options(args.rerun_dir, args.historical_dir, cells, manifest, failures, report)
    if args.double_run_dir:
        check_double_run(args.rerun_dir, args.double_run_dir, failures, report)
    check_history_untouched(args.repo, args.base, failures, report)
    return failures, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rerun-dir", required=True)
    parser.add_argument("--single-archive", required=True, help="4sw5so archive with *_repeat1.response.json")
    parser.add_argument("--historical-dir", required=True, help="old fleet archive of the same campaign")
    parser.add_argument("--double-run-dir", help="second full run of one day (rule (e))")
    parser.add_argument("--repo", default=".", help="repository root for the git checks")
    parser.add_argument("--base", help="git revision the history must be unchanged since")
    parser.add_argument("--expected-cells", type=int, default=20)
    args = parser.parse_args(argv)
    failures, report = verify(args)
    print(json.dumps({"report": report, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
