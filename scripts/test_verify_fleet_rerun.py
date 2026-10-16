"""Tests of scripts/verify_fleet_rerun.py on small fixture archives (no real campaign data).

Run: python -m pytest scripts/test_verify_fleet_rerun.py   (project venv)
"""
import copy
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


def response(selected_option, routes):
    return {"scenario": {"scenario": 1, "routes": routes, "selection": {"optionByWave": {WAVE: selected_option}}}}


def selected_routes(steps, ids):
    return [{"jobId": WAVE, "routeIndex": 0, "steps": steps, "occurrenceIds": ids}]


@pytest.fixture
def archive(tmp_path):
    root = tmp_path
    rerun, single, hist = root / "rerun", root / "single", root / "hist"
    write(str(rerun / "run_manifest.json"), {
        "state": "completed", "parameters": {"scenarios": ["A", "L1"]}, "runs": [{"date": DATE, "ride_limit": RIDE}],
    })
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
    argv = ["--rerun-dir", str(root / "rerun"), "--single-archive", str(root / "single"), "--historical-dir", str(root / "hist"),
            "--repo", str(root), "--expected-cells", str(cells), *extra]
    args = V.argparse.Namespace(rerun_dir=argv[1], single_archive=argv[3], historical_dir=argv[5], repo=argv[7], expected_cells=cells,
                                double_run_dir=None, base=None)
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


def test_a_consistent_rerun_passes_with_every_selected_option_identical(archive):
    failures, report = run(archive)
    assert failures == []
    assert report["selected_option_categories"] == {"identical": 1}
    assert report["waves_checked_against_4sw5so"] == 1 and report["history_untouched"] is True


def test_cli_exit_code_is_zero_on_success_and_one_on_failure(archive, capsys):
    argv = ["--rerun-dir", str(archive / "rerun"), "--single-archive", str(archive / "single"), "--historical-dir", str(archive / "hist"),
            "--repo", str(archive), "--expected-cells", "1"]
    assert V.main(argv) == 0
    edit(str(archive / "rerun" / f"{DATE}_R{RIDE}.menu_options.json"), lambda v: v["waves"][0]["options"][0]["routes"][0]["steps"].reverse())
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
    edit(str(archive / "rerun" / f"{DATE}_R{RIDE}.menu_options.json"), change)
    failures, _ = run(archive)
    assert failures, name


def test_selected_option_with_other_routes_is_unexplained_and_fails(archive):
    edit(str(archive / "rerun" / f"{DATE}_R{RIDE}.menu_options.json"),
         lambda v: v["waves"][0]["options"][1].update({"routes": [route(STEPS_OTHER, IDS)]}))
    failures, report = run(archive)
    assert report["selected_option_categories"] == {"routes_differ_unexplained": 1}
    assert any("routes_differ_unexplained" in f for f in failures)


def test_selected_option_absent_in_the_rerun_fails(archive):
    edit(str(archive / "rerun" / f"{DATE}_R{RIDE}.menu_options.json"), lambda v: v["waves"][0]["options"].pop(1))
    failures, report = run(archive)
    assert report["selected_option_categories"] == {"option_absent_in_rerun": 1}
    assert failures


def test_same_routes_but_another_selected_option_is_the_expected_h06_category_and_passes(archive):
    edit(str(archive / "rerun" / f"{DATE}_R{RIDE}_L1.response.json"), lambda v: v["scenario"]["selection"]["optionByWave"].update({WAVE: "base"}))
    failures, report = run(archive)
    assert failures == []
    assert report["selected_option_categories"] == {"selection_changed_h06_expected": 1}


def test_manifest_must_be_completed_with_the_expected_cells(archive):
    edit(str(archive / "rerun" / "run_manifest.json"), lambda v: v.update({"state": "failed"}))
    assert any("not completed" in f for f in run(archive)[0])
    edit(str(archive / "rerun" / "run_manifest.json"), lambda v: v.update({"state": "completed"}))
    assert any("expected 20" in f for f in run(archive, cells=20)[0])


def test_double_run_must_be_byte_identical(archive, tmp_path):
    second = tmp_path / "second"
    os.makedirs(second)
    name = f"{DATE}_R{RIDE}.menu_options.json"
    with open(archive / "rerun" / name, "rb") as handle:
        data = handle.read()
    (second / name).write_bytes(data)
    assert run(archive, "--double-run-dir", str(second))[0] == []
    (second / name).write_bytes(data.replace(b"21", b"22", 1))
    failures, _ = run(archive, "--double-run-dir", str(second))
    assert any("differs between the two runs" in f for f in failures)
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
