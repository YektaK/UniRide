"""WP-E0 DUZELT round 1: matrix semantics, limits, statuses and fleet cross-checks."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
SW5SO = RESULTS / "week-2026-10-05-4sw5so"
FLEET_DIR = RESULTS / "week-2026-10-05-fleet"


@pytest.fixture(scope="module")
def loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader_sem", REPO / "scripts" / "exact_archive_loader.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_sem"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def all_campaigns(loader):
    return loader.load_all_valid(RESULTS)


def _tiny(**over):
    from uniride_core.exact import WaveInstance, compute_matrix_sha256

    matrix = ((0, 5, 6), (4, 0, 3), (7, 2, 0))
    base = dict(
        wave_id="w", service_date="2026-10-05", direction="pickup", anchor_minutes=525,
        max_ride_minutes=50, max_tour_minutes=150, depot_code="D.Kampus",
        occurrence_ids=("a~1", "b~1"), location_codes=("Sw1", "So1"), classes=("Sw", "So"),
        matrix=matrix, matrix_sha256=compute_matrix_sha256(matrix),
        arc_slice_sha256="s" * 64, declared_snapshot_sha256="d" * 64,
    )
    base.update(over)
    return WaveInstance(**base)


def _arcs(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {(a["origin_code"], a["destination_code"]): a["duration_minutes"] for a in doc["arcs"]}


def _edit_json(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _copy_4sw5so(tmp_path):
    dst = tmp_path / "results" / "week-2026-10-05-4sw5so"
    dst.mkdir(parents=True)
    for suf in ("matrix", "response"):
        shutil.copy(SW5SO / f"2026-10-05_R50_repeat1.{suf}.json", dst)
    shutil.copy(SW5SO / "run_manifest.json", dst)
    return dst


def _copy_fleet(tmp_path):
    _copy_4sw5so(tmp_path)
    dst = tmp_path / "results" / "week-2026-10-05-fleet"
    dst.mkdir()
    for f in FLEET_DIR.glob("2026-10-05_R50*"):
        shutil.copy(f, dst)
    shutil.copy(FLEET_DIR / "run_manifest.json", dst)
    return dst


def test_matrix_direction_follows_archived_arcs(all_campaigns):
    arcs = _arcs(SW5SO / "2026-10-05_R50_repeat1.matrix.json")
    waves = [w for w in all_campaigns["4sw5so"].waves_for(50) if w.service_date == "2026-10-05"]
    asymmetric = 0
    for w in waves:
        for k, code in enumerate(w.location_codes, start=1):
            assert w.matrix[0][k] == arcs[(w.depot_code, code)]
            assert w.matrix[k][0] == arcs[(code, w.depot_code)]
            asymmetric += arcs[(w.depot_code, code)] != arcs[(code, w.depot_code)]
    assert asymmetric > 0  # not vacuous: some depot arcs differ by direction


def test_limits_equal_file_name_response_and_150(all_campaigns):
    for key, camp in all_campaigns.items():
        for r in camp.rides:
            for w in camp.waves_for(r):
                assert w.max_ride_minutes == r, (key, r)
                assert w.max_tour_minutes == 150, (key, r)
    resp = json.loads((SW5SO / "2026-10-05_R90_repeat1.response.json").read_text(encoding="utf-8"))
    assert resp["limits"] == {"maxRideTimeMinutes": 90, "maxTourMinutes": 150}


def test_build_colocation_zero_and_directed_arcs(loader):
    arcs = {("D.Kampus", "Sw1"): 7, ("Sw1", "D.Kampus"): 9, ("D.Kampus", "So1"): 3, ("So1", "D.Kampus"): 4,
            ("Sw1", "So1"): 5, ("So1", "Sw1"): 6}
    ref = ("w", "2026-10-05", "pickup", 525, [("o~1", "Sw1", "Sw"), ("o~2", "Sw1", "Sw"), ("p~1", "So1", "So")])
    inst = loader._build(ref, arcs, "snap", "slice", 50, 150)
    assert inst.matrix == ((0, 7, 7, 3), (9, 0, 0, 5), (9, 0, 0, 5), (4, 6, 6, 0))


def test_missing_arc_is_rejected(loader, tmp_path):
    dst = _copy_4sw5so(tmp_path)
    _edit_json(dst / "2026-10-05_R50_repeat1.matrix.json", lambda d: d.update(
        arcs=[a for a in d["arcs"] if not (a["origin_code"] == "D.Kampus" and a["destination_code"] == "Sw5")]))
    with pytest.raises(loader.InputRejected, match="missing"):
        loader.load_campaign(dst)


def test_manifest_without_tour_limit_is_rejected(loader, tmp_path):
    dst = _copy_4sw5so(tmp_path)
    _edit_json(dst / "run_manifest.json", lambda d: d["parameters"].pop("tour_limit"))
    with pytest.raises(loader.InputRejected, match="tour_limit"):
        loader.load_campaign(dst)


def test_response_limits_must_match_ride_and_tour(loader, tmp_path):
    dst = _copy_4sw5so(tmp_path)
    _edit_json(dst / "2026-10-05_R50_repeat1.response.json", lambda d: d["limits"].update(maxTourMinutes=999))
    with pytest.raises(loader.InputRejected, match="limits"):
        loader.load_campaign(dst)
    dst2 = _copy_4sw5so(tmp_path / "b")
    _edit_json(dst2 / "2026-10-05_R50_repeat1.response.json", lambda d: d["limits"].update(maxRideTimeMinutes=90))
    with pytest.raises(loader.InputRejected, match="limits"):
        loader.load_campaign(dst2)


def test_manifest_ride_limits_must_contain_file_ride(loader, tmp_path):
    dst = _copy_4sw5so(tmp_path)
    _edit_json(dst / "run_manifest.json", lambda d: d["parameters"].update(ride_limits=[60, 70, 90]))
    with pytest.raises(loader.InputRejected, match="ride_limits"):
        loader.load_campaign(dst)


def test_untouched_fleet_copy_loads(loader, tmp_path):
    assert loader.load_campaign(_copy_fleet(tmp_path)).waves_for(50)


def test_fleet_types_carry_optional_limits_and_unknown_keys_fail_closed(loader, tmp_path):
    from uniride_core.exact import VehicleTypeSpec

    assert VehicleTypeSpec("x", 1, 1, 10).ride_limit_minutes is None
    dst = _copy_fleet(tmp_path)
    _edit_json(dst / "run_manifest.json", lambda d: d["fleet_types"][1].update(rideLimit=40, tourLimit=100))
    sedan = {t.type_id: t for t in loader.load_campaign(dst).fleet_types}["sedan"]
    assert (sedan.ride_limit_minutes, sedan.tour_limit_minutes) == (40, 100)
    dst2 = _copy_fleet(tmp_path / "b")
    _edit_json(dst2 / "run_manifest.json", lambda d: d["fleet_types"][1].update(surprise=1))
    with pytest.raises(loader.InputRejected, match="fleet_types"):
        loader.load_campaign(dst2)


def test_reference_sha_must_equal_fleet_matrix_sha(loader, tmp_path):
    dst = _copy_fleet(tmp_path)
    ref = dst.parent / "week-2026-10-05-4sw5so" / "2026-10-05_R50_repeat1.response.json"
    _edit_json(ref, lambda d: d["matrix"].update(sha256="0" * 64))
    with pytest.raises(loader.InputRejected, match="sha256"):
        loader.load_campaign(dst)


def test_selected_scenario_occurrences_must_equal_reference(loader, tmp_path):
    dst = _copy_fleet(tmp_path)
    _edit_json(dst / "2026-10-05_R50_L3.response.json", lambda d: d["scenario"]["routes"][0]["occurrenceIds"].pop())
    with pytest.raises(loader.InputRejected, match="occurrence"):
        loader.load_campaign(dst)


def test_campaign_exposes_fixed_minimize_and_scenarios(all_campaigns):
    f, c, s = all_campaigns["fleet"], all_campaigns["minivan-cap3"], all_campaigns["4sw5so"]
    assert (f.fixed_type, f.minimize_type, f.scenarios, f.max_l) == ("large", "sedan", ("A", "L1", "L2", "L3"), 3)
    assert (c.fixed_type, c.minimize_type, c.scenarios, c.max_l) == ("large", "minivan", ("L0", "L1", "L2"), 2)
    assert (s.fixed_type, s.minimize_type, s.scenarios, s.max_l) == (None, None, (), None)


def test_l4_refusal_reason_names_eq2(loader):
    with pytest.raises(loader.CampaignRefused, match="EQ2.*afc7208"):
        loader.load_campaign(FLEET_DIR / "extra" / "L4")


def test_exact_status_set_is_the_design_set():
    from uniride_core.exact import EXACT_STATUSES, ExactResult

    assert EXACT_STATUSES == frozenset({
        "not_run", "optimal", "feasible_with_gap", "bound_only", "infeasible_proven", "rejected",
        "backend_unavailable", "input_rejected", "timing_dependent_abort", "skipped_no_stage1_incumbent"})
    ExactResult(wave_id="w", status="feasible_with_gap", routes=(), route_count=None, total_cost=None)
    for bad in ("feasible", "infeasible", "limit_reached"):
        with pytest.raises(ValueError):
            ExactResult(wave_id="w", status=bad, routes=(), route_count=None, total_cost=None)


def test_arc_zero_exactly_when_codes_equal():
    from uniride_core.exact import compute_matrix_sha256

    zero = ((0, 5, 6), (4, 0, 0), (7, 0, 0))  # distinct codes with a 0 arc
    with pytest.raises(ValueError):
        _tiny(matrix=zero, matrix_sha256=compute_matrix_sha256(zero))
    same = ((0, 5, 6), (4, 0, 3), (7, 2, 0))  # same code twice with non-zero arcs
    with pytest.raises(ValueError):
        _tiny(location_codes=("Sw1", "Sw1"), matrix=same, matrix_sha256=compute_matrix_sha256(same))
    ok = ((0, 5, 6), (4, 0, 0), (7, 0, 0))
    _tiny(location_codes=("Sw1", "Sw1"), matrix=ok, matrix_sha256=compute_matrix_sha256(ok))
