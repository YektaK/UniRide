"""WP-E4a part 1 GATE: the Python recomputation of the WP-E10 day selections.

For every (date, R, L) of both typed fleets: rebuild the ``/internal/fleet-selection`` request from the
archived option routes, require it equal to the archived request, call ``solve_day_selection`` with the
router's effective parameters and compare the result with the archived response (design sections 1.5, 8, 9).
CP-SAT only; no AMPL needed.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
LARGE_SEDAN = RESULTS / "week-2026-10-05-fleet-rerun-large-sedan"
DOBLO = RESULTS / "week-2026-10-05-fleet-rerun-doblo-cap3"
for _p in (REPO / "optimizer_api", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def replay():
    return _load("exact_typed_replay")


@pytest.fixture(scope="module")
def large_sedan(replay):
    return replay.load_fleet(LARGE_SEDAN)


def test_diff_json_reports_every_difference_with_its_path(replay):
    a = {"x": 1, "y": [1, {"z": 2}], "only_a": 1}
    b = {"x": 1, "y": [1, {"z": 3}], "only_b": 1}
    diffs = replay.diff_json(a, b)
    assert any("y[1].z" in d for d in diffs) and any("only_a" in d for d in diffs) and any("only_b" in d for d in diffs)
    assert replay.diff_json(a, copy.deepcopy(a)) == []
    assert replay.diff_json({"v": 76}, {"v": 76.0}) == []  # JSON numbers: 76 and 76.0 are the same number


def test_response_comparison_covers_the_six_fields_and_the_labels(replay):
    base = {"status": "optimal", "cars": 2, "large_peak": 2, "car_minutes": 336, "total_minutes": 1319,
            "selection": {"w": {"option_id": "q3", "option_index": 2, "labels": ["large", "car"]}}}
    assert replay.compare_response(base, copy.deepcopy(base)) == []
    for field, value in (("status", "feasible"), ("cars", 3), ("large_peak", 1), ("car_minutes", 337),
                         ("total_minutes", 1320)):
        changed = copy.deepcopy(base)
        changed[field] = value
        assert replay.compare_response(base, changed), field
    relabelled = copy.deepcopy(base)
    relabelled["selection"]["w"]["labels"] = ["car", "large"]
    assert replay.compare_response(base, relabelled)
    other_option = copy.deepcopy(base)
    other_option["selection"]["w"]["option_id"] = "base"
    assert replay.compare_response(base, other_option)


def test_replay_cell_rebuilds_the_archived_request_exactly(replay, large_sedan):
    row = replay.replay_cell(large_sedan, "2026-10-05", 90, 2)
    assert row["request_diffs"] == []
    assert row["label"] == "match"
    assert row["archived_status"] == row["replay_status"] == "optimal"


def test_replay_detects_a_tampered_archived_response(replay, large_sedan, tmp_path):
    """The comparison must not be skippable: a changed archived car count is reported as a mismatch."""
    cell = replay.load_cell(large_sedan, "2026-10-05", 90, 2)
    tampered = copy.deepcopy(cell)
    tampered["exchange"]["response"]["cars"] = tampered["exchange"]["response"]["cars"] + 1
    row = replay.replay_loaded_cell(large_sedan, tampered)
    assert row["label"] == "response_mismatch"
    assert any(d.startswith("cars") for d in row["response_diffs"])


def test_replay_detects_a_tampered_archived_request(replay, large_sedan):
    cell = replay.load_cell(large_sedan, "2026-10-05", 90, 2)
    tampered = copy.deepcopy(cell)
    tampered["exchange"]["request"]["waves"][0]["options"][0]["routes"][0]["start"] += 1
    row = replay.replay_loaded_cell(large_sedan, tampered)
    assert row["label"] == "request_mismatch" and row["request_diffs"]


def test_interval_start_plus_one_rule_is_exercised_by_a_route_without_length(replay):
    from uniride_core.planning import fleet_selection_request as fsr

    facts = fsr.RouteFacts(start_minutes=100, end_minutes=100, step_durations=(0, 0), direction="pickup", sw_count=0,
                           so_count=1)
    req = fsr.build_selection_request([("w", [("base", True, [facts])])], fixed_type=fsr.TypeLimits("large", 4, 5, None, None, None),
                                      minimise_type=fsr.TypeLimits("sedan", 0, 4, None, None, None), max_large=1,
                                      ride_default=90, tour_default=150)
    assert req["waves"][0]["options"][0]["routes"][0]["end"] == 10001


@pytest.mark.parametrize("directory,expected_cells", [(LARGE_SEDAN, 60), (DOBLO, 60)])
def test_full_replay_on_the_real_wp_e10_archive(replay, directory, expected_cells):
    """ACCEPTANCE GATE: every (date, R, L) cell reproduces the archived request and selection response."""
    fleet = replay.load_fleet(directory)
    rows = replay.replay_fleet(fleet)
    assert len(rows) == expected_cells
    failures = [r for r in rows if r["label"] not in replay.MATCH_LABELS]
    assert failures == [], [(r["date"], r["R"], r["L"], r["label"], r["request_diffs"][:2], r["response_diffs"][:2]) for r in failures]
    assert all(r["solver_version"] == "9.15.6755" for r in rows)


def test_diff_json_is_type_strict_for_booleans_and_none(replay):
    assert replay.diff_json({"v": True}, {"v": 1}) and replay.diff_json({"v": 1}, {"v": True})
    assert replay.diff_json({"v": False}, {"v": 0}) and replay.diff_json({"v": 0}, {"v": False})
    assert replay.diff_json({"v": None}, {"v": 0}) and replay.diff_json({"v": 0}, {"v": None})
    assert replay.diff_json({"v": True}, {"v": True}) == [] and replay.diff_json({"v": None}, {"v": None}) == []
    assert replay.diff_json({"v": 1}, {"v": 1.0}) == []  # numbers still compare by value
