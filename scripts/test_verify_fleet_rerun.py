"""Tests of scripts/verify_fleet_rerun.py on small fixture archives (no real campaign data).

Run: python -m pytest scripts/test_verify_fleet_rerun.py   (project venv)
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_fleet_rerun as V  # noqa: E402

DATE, RIDE, WAVE = "2026-10-05", 60, "2026-10-05:pickup:525"


def step(a, b, d):
    return {"location1": a, "location2": b, "duration": d}


STEPS = [step("D", "Sw1", 5), step("Sw1", "So1", 7), step("So1", "D", 9)]
STEPS_OTHER = [step("D", "So1", 6), step("So1", "Sw1", 7), step("Sw1", "D", 9)]
IDS = ["2026-10-05:pickup:Sw1~1", "2026-10-05:pickup:So1~1"]


def route(steps, ids, sw=1, so=1, with_interval=True):
    return {
        "routeIndex": 0, "vehicleId": "Vehicle1", "vehicleType": None, "steps": steps, "studentIds": ids, "swCount": sw, "soCount": so,
        "totalDurationMinutes": 21, "minutes": 21, "profileError": None, "rideMinutes": [21, 14],
        "interval": {"startMinutes": 500, "endMinutes": 521, "occurrenceIds": ids} if with_interval else None,
    }


def option(option_id, routes, status="included"):
    return {"optionId": option_id, "kind": "baseline" if option_id == "base" else "quota", "quota": None, "status": status, "reason": None,
            "routeCount": len(routes), "success": True, "certificate": {"is_feasible": True}, "error": None, "totalDurationMinutes": 21, "routes": routes}


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def response(selected_option, routes, status="ok", cars=1, large=1, total=100.0, car_minutes=10.0, sel_status="optimal", waves=None):
    waves = [WAVE] if waves is None else waves
    selection = {"status": sel_status, "cars": cars, "carMinutes": car_minutes, "optionByWave": {w: selected_option for w in waves}}
    return {"scenario": {"scenario": 1, "status": status, "cars": cars, "largeVehicles": large, "totalVehicleMinutes": total,
                         "routes": routes, "selection": selection}}


def infeasible():
    return {"scenario": {"scenario": 1, "status": "infeasible_for_L", "cars": None, "largeVehicles": None, "totalVehicleMinutes": None,
                         "routes": [], "selection": {"status": "infeasible_for_L", "cars": None, "carMinutes": None, "optionByWave": {}}}}


def selected_routes(steps, ids):
    return [{"jobId": WAVE, "routeIndex": 0, "steps": steps, "occurrenceIds": ids}]


def manifest(**over):
    value = {"state": "completed", "parameters": {"scenarios": ["A", "L1"]}, "run_kind": "campaign", "runs": [{"date": DATE, "ride_limit": RIDE}]}
    value.update(over)
    return value


@pytest.fixture
def archive(tmp_path):
    root = tmp_path
    rerun, single, hist = root / "rerun", root / "single", root / "hist"
    write(str(rerun / "run_manifest.json"), manifest())
    write(str(rerun / f"{DATE}_R{RIDE}.menu_options.json"), {"waves": [{"waveId": WAVE, "options": [
        option("base", [route(STEPS, IDS)]), option("q1", [route(STEPS, IDS)], "skipped_duplicate")]}]})
    write(str(rerun / f"{DATE}_R{RIDE}_L1.response.json"), response("q1", selected_routes(STEPS, IDS)))
    write(str(single / f"{DATE}_R{RIDE}_repeat1.response.json"), {
        "jobs": [{"id": WAVE, "result": {"routes": [{"route_details": STEPS, "student_ids": IDS}]}}],
        "routeIntervals": [{"jobId": WAVE, "occurrenceIds": IDS, "swCount": 1, "soCount": 1}],
    })
    write(str(hist / f"{DATE}_R{RIDE}_L1.response.json"), response("q1", selected_routes(STEPS, IDS)))
    for d in V.HISTORICAL_DIRS:  # a throw-away git repository holding the three historical directories
        write(str(root / d / "run_manifest.json"), {"x": 1})
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "history")
    return root


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def run(root, *extra, cells=1):
    args = V.argparse.Namespace(rerun_dir=str(root / "rerun"), single_archive=str(root / "single"), historical_dir=str(root / "hist"),
                                repo=str(root), expected_cells=cells, double_run_dir=None, base=None)
    for i, item in enumerate(extra):
        if item == "--double-run-dir":
            args.double_run_dir = extra[i + 1]
        if item == "--base":
            args.base = extra[i + 1]
    return V.verify(args)


def edit(path, change):
    with open(path, "r", encoding="utf-8") as handle:
        value = json.load(handle)
    change(value)
    write(path, value)


def rerun_l1(root):
    return str(root / "rerun" / f"{DATE}_R{RIDE}_L1.response.json")


def menu(root):
    return str(root / "rerun" / f"{DATE}_R{RIDE}.menu_options.json")


def test_a_consistent_rerun_passes_with_every_selected_option_identical(archive):
    failures, report = run(archive)
    assert failures == []
    assert report["selected_option_categories"] == {"identical": 1}
    assert report["waves_checked_against_4sw5so"] == 1 and report["history_untouched"] is True


def test_cli_exit_code_is_zero_on_success_and_one_on_failure(archive):
    argv = ["--rerun-dir", str(archive / "rerun"), "--single-archive", str(archive / "single"), "--historical-dir", str(archive / "hist"),
            "--repo", str(archive), "--expected-cells", "1"]
    assert V.main(argv) == 0
    edit(menu(archive), lambda v: v["waves"][0]["options"][0]["routes"][0]["steps"].reverse())
    assert V.main(argv) == 1


@pytest.mark.parametrize("name, change", [
    ("a step minute of the base route", lambda v: v["waves"][0]["options"][0]["routes"][0]["steps"][0].__setitem__("duration", 6)),
    ("the stop order of the base route", lambda v: v["waves"][0]["options"][0]["routes"][0].__setitem__("steps", STEPS_OTHER)),
    ("an occurrence id of the base route", lambda v: v["waves"][0]["options"][0]["routes"][0]["studentIds"].__setitem__(0, "2026-10-05:pickup:Sw1~2")),
    ("the interval occurrence ids (composition)", lambda v: v["waves"][0]["options"][0]["routes"][0]["interval"]["occurrenceIds"].__setitem__(0, "2026-10-05:pickup:Sw1~2")),
    ("the Sw/So counts (composition)", lambda v: v["waves"][0]["options"][0]["routes"][0].update({"swCount": 2, "soCount": 0})),
    ("a missing base option", lambda v: v["waves"][0]["options"].pop(0)),
])
def test_anchor_and_composition_failures_are_reported(archive, name, change):
    edit(menu(archive), change)
    failures, _ = run(archive)
    assert failures, name


def test_selected_option_with_other_routes_is_unexplained_and_fails(archive):
    edit(menu(archive), lambda v: v["waves"][0]["options"][1].update({"routes": [route(STEPS_OTHER, IDS)]}))
    failures, report = run(archive)
    assert report["selected_option_categories"] == {"routes_differ_unexplained": 1}
    assert any("routes_differ_unexplained" in f for f in failures)


def test_selected_option_absent_in_the_rerun_fails(archive):
    edit(menu(archive), lambda v: v["waves"][0]["options"].pop(1))
    failures, report = run(archive)
    assert report["selected_option_categories"] == {"option_absent_in_rerun": 1}
    assert failures


# ---- V-1: the scenario outcome is compared first; the H06 category is narrow ------------------------------------------------------
def rewrite(root, new_response):
    write(rerun_l1(root), new_response)


@pytest.mark.parametrize("name, new_response", [
    ("new scenario infeasible", infeasible()),
    ("cars differ", response("q1", selected_routes(STEPS, IDS), cars=2)),
    ("largeVehicles differ", response("q1", selected_routes(STEPS, IDS), large=2)),
    ("selection status differs (feasible, not optimal)", response("q1", selected_routes(STEPS, IDS), sel_status="feasible")),
    ("scenario status differs", response("q1", selected_routes(STEPS, IDS), status="verification_failed")),
    ("wave-key sets differ", response("q1", selected_routes(STEPS, IDS), waves=[WAVE, "2026-10-05:pickup:999"])),
])
def test_a_different_scenario_outcome_fails_whatever_the_options_say(archive, name, new_response):
    rewrite(archive, new_response)
    failures, report = run(archive)
    assert report["selected_option_categories"].get("scenario_outcome_differs") == 1, name
    assert any("scenario_outcome_differs" in f for f in failures)


def test_old_infeasible_new_ok_is_a_failing_outcome_difference(archive):
    write(str(archive / "hist" / f"{DATE}_R{RIDE}_L1.response.json"), infeasible())
    failures, report = run(archive)
    assert report["selected_option_categories"] == {"scenario_outcome_differs": 1}
    assert failures


def test_both_infeasible_and_identical_passes(archive):
    write(str(archive / "hist" / f"{DATE}_R{RIDE}_L1.response.json"), infeasible())
    rewrite(archive, infeasible())
    failures, report = run(archive)
    assert failures == [] and report["selected_option_categories"] == {"both_not_ok_identical": 1}


def test_a_scenario_only_in_the_rerun_or_only_in_the_old_archive_fails(archive):
    write(str(archive / "rerun" / f"{DATE}_R{RIDE}_L2.response.json"), response("q1", selected_routes(STEPS, IDS)))
    failures, report = run(archive)
    assert report["selected_option_categories"] == {"identical": 1, "scenario_outcome_differs": 1}
    assert any("L2" in f and "only in the re-run" in f for f in failures)
    os.remove(archive / "rerun" / f"{DATE}_R{RIDE}_L2.response.json")
    write(str(archive / "hist" / f"{DATE}_R{RIDE}_L3.response.json"), response("q1", selected_routes(STEPS, IDS)))
    failures, _ = run(archive)
    assert any("L3" in f and "only in the old archive" in f for f in failures)


def test_a_genuine_h06_case_passes(archive):
    # same cars and large vehicles, the old option is still in the menu with identical routes, total vehicle-minutes now lower
    rewrite(archive, response("base", selected_routes(STEPS, IDS), total=90.0))
    failures, report = run(archive)
    assert failures == [] and report["selected_option_categories"] == {"selection_changed_h06_expected": 1}


def test_equal_total_minutes_with_lower_or_equal_car_minutes_passes(archive):
    rewrite(archive, response("base", selected_routes(STEPS, IDS), total=100.0, car_minutes=9.0))
    assert run(archive)[0] == []
    rewrite(archive, response("base", selected_routes(STEPS, IDS), total=100.0, car_minutes=10.0))
    assert run(archive)[0] == []


@pytest.mark.parametrize("name, new_response", [
    ("total vehicle-minutes worse", response("base", selected_routes(STEPS, IDS), total=110.0)),
    ("equal total minutes but worse car-minutes", response("base", selected_routes(STEPS, IDS), total=100.0, car_minutes=11.0)),
    ("new total minutes missing", response("base", selected_routes(STEPS, IDS), total=None)),
])
def test_a_changed_selection_that_is_not_an_h06_improvement_fails(archive, name, new_response):
    rewrite(archive, new_response)
    failures, report = run(archive)
    assert report["selected_option_categories"] == {"selection_changed_unexplained": 1}, name
    assert any("selection_changed_unexplained" in f for f in failures)


def test_h06_needs_the_archived_option_to_be_identical_in_the_rerun_menu(archive):
    edit(menu(archive), lambda v: v["waves"][0]["options"][1].update({"routes": [route(STEPS_OTHER, IDS)]}))
    rewrite(archive, response("base", selected_routes(STEPS, IDS), total=90.0))
    failures, report = run(archive)
    assert "selection_changed_h06_expected" not in report["selected_option_categories"]
    assert failures


def test_the_new_selection_is_really_read(archive):
    """Guards the verifier reading the re-run selection: a changed selection must never be filed as identical."""
    rewrite(archive, response("base", selected_routes(STEPS, IDS), total=90.0))
    _, report = run(archive)
    assert report["selected_option_categories"].get("identical", 0) == 0
    assert report["selected_option_categories"] == {"selection_changed_h06_expected": 1}


def test_manifest_must_be_completed_with_the_expected_cells(archive):
    edit(str(archive / "rerun" / "run_manifest.json"), lambda v: v.update({"state": "failed"}))
    assert any("not completed" in f for f in run(archive)[0])
    edit(str(archive / "rerun" / "run_manifest.json"), lambda v: v.update({"state": "completed"}))
    assert any("expected 20" in f for f in run(archive, cells=20)[0])


# ---- V-2: a rule (e) second run is labelled and cannot be the campaign archive -----------------------------------------------------
def subset_manifest():
    value = manifest(run_kind="rule_e_second_run")
    value["parameters"]["allow_subset_dates"] = True
    return value


def test_a_subset_run_is_refused_as_the_campaign_archive_whatever_the_cell_count(archive):
    edit(str(archive / "rerun" / "run_manifest.json"), lambda v: v.update(subset_manifest()))
    failures, _ = run(archive, cells=1)
    assert any("rule (e) second run" in f for f in failures)
    edit(str(archive / "rerun" / "run_manifest.json"), lambda v: (v.pop("run_kind"), v["parameters"].update({"allow_subset_dates": True})))
    assert any("rule (e) second run" in f for f in run(archive, cells=1)[0])  # the parameter alone is enough
    edit(str(archive / "rerun" / "run_manifest.json"), lambda v: (v["parameters"].pop("allow_subset_dates"), v.pop("run_kind", None)))
    assert any("run_kind" in f for f in run(archive, cells=1)[0])  # an unlabelled manifest is refused too


def test_double_run_must_be_a_labelled_subset_run_and_byte_identical(archive, tmp_path):
    second = tmp_path / "second"
    os.makedirs(second)
    name = f"{DATE}_R{RIDE}.menu_options.json"
    with open(archive / "rerun" / name, "rb") as handle:
        data = handle.read()
    (second / name).write_bytes(data)
    write(str(second / "run_manifest.json"), subset_manifest())
    assert run(archive, "--double-run-dir", str(second))[0] == []
    (second / name).write_bytes(data.replace(b"21", b"22", 1))
    assert any("differs between the two runs" in f for f in run(archive, "--double-run-dir", str(second))[0])
    (second / name).write_bytes(data)
    write(str(second / "run_manifest.json"), manifest())  # a campaign is not a second run
    assert any("not labelled as a rule (e) second run" in f for f in run(archive, "--double-run-dir", str(second))[0])
    write(str(second / "run_manifest.json"), subset_manifest())
    (second / name).unlink()
    assert any("holds no" in f for f in run(archive, "--double-run-dir", str(second))[0])


def test_history_must_be_untouched(archive):
    target = archive / V.HISTORICAL_DIRS[2] / "run_manifest.json"
    base = subprocess.run(["git", "-C", str(archive), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert run(archive, "--base", base)[0] == []
    target.write_text('{"x": 2}')  # modified, uncommitted
    assert any("(g)" in f for f in run(archive)[0])
    target.write_text('{"x": 1}')
    (archive / V.HISTORICAL_DIRS[1] / "new.json").write_text("{}")  # untracked file inside a historical directory
    assert any("(g)" in f for f in run(archive)[0])
    os.remove(archive / V.HISTORICAL_DIRS[1] / "new.json")
    target.write_text('{"x": 3}')
    git(archive, "add", "-A")
    git(archive, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "edit history")
    assert any("since" in f for f in run(archive, "--base", base)[0])  # committed change is caught through --base
