"""WP-E3 (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md sections 1.2, 3, 8): the certification bridge,
the objective cross-check and the exact-vs-GA gap arithmetic. Everything here runs without AMPL.

The bridge wraps routes in the operational response schema and rebuilds the operational request, then
``certify_optimization_response`` (called here, never from ``uniride_core``) judges them on the arcs of
the archived per-date matrix slice.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
SW5SO = RESULTS / "week-2026-10-05-4sw5so"
EXACT = REPO / "uniride_core" / "exact"
for _p in (REPO / "optimizer_api",):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _load_loader():
    spec = importlib.util.spec_from_file_location("exact_archive_loader", REPO / "scripts" / "exact_archive_loader.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def loader():
    return _load_loader()


@pytest.fixture(scope="module")
def campaign(loader):
    return loader.load_campaign(SW5SO)


def _certify(wave, payload_response, arcs_doc, *, request_payload=None, lookup=...):
    from models.schemas import OptimizationRequest, OptimizationResponse
    from uniride_core.exact import certification as cert
    from verification.authoritative_arcs import arc_lookup_from_snapshot
    from verification.response_certifier import certify_optimization_response

    req = OptimizationRequest.model_validate(request_payload or cert.request_payload(wave))
    resp = OptimizationResponse.model_validate(payload_response)
    if lookup is ...:
        lookup = arc_lookup_from_snapshot(arcs_doc)
    return certify_optimization_response(req, resp, lookup)


def _archive(date="2026-10-05", ride=90):
    arcs_doc = json.loads((SW5SO / f"{date}_R{ride}_repeat1.matrix.json").read_text(encoding="utf-8"))
    resp = json.loads((SW5SO / f"{date}_R{ride}_repeat1.response.json").read_text(encoding="utf-8"))
    return arcs_doc, {j["id"]: j for j in resp["jobs"]}


def _wave(campaign, wave_id, ride=90):
    return next(w for w in campaign.waves_for(ride) if w.wave_id == wave_id)


# ---------- GA re-certification and exact certification on archived waves ----------
@pytest.mark.parametrize("date,ride,wave_id", [
    ("2026-10-05", 90, "2026-10-05:pickup:525"),   # the 20-leg peak wave
    ("2026-10-05", 90, "2026-10-05:pickup:765"),
    ("2026-10-06", 50, "2026-10-06:pickup:525"),
])
def test_archived_ga_routes_recertify_feasible(campaign, date, ride, wave_id):
    from uniride_core.exact import certification as cert

    arcs_doc, jobs = _archive(date, ride)
    wave = _wave(campaign, wave_id, ride)
    ga = cert.ga_response_payload(wave, jobs[wave_id]["result"])
    out = _certify(wave, ga, arcs_doc)
    assert out["is_feasible"] is True, out["violations"]
    assert out.get("certify_error") is None


def test_exact_wrapped_routes_certify_and_recompute_objective(campaign):
    """The GA partition wrapped as 'exact' routes (visiting order only) certifies; K and D recompute in integers."""
    from uniride_core.exact import certification as cert

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, "2026-10-05:pickup:525")
    routes = [tuple(r["student_ids"]) for r in jobs[wave.wave_id]["result"]["routes"]]
    out = _certify(wave, cert.response_payload(wave, routes), arcs_doc)
    assert out["is_feasible"] is True, out["violations"]
    k, d = cert.recompute_objective(wave, routes)
    assert k == len(routes)
    assert d == sum(r["total_duration_minutes"] for r in jobs[wave.wave_id]["result"]["routes"])


def test_tampered_arc_minute_is_rejected(campaign):
    from uniride_core.exact import certification as cert

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, "2026-10-05:pickup:525")
    routes = [tuple(r["student_ids"]) for r in jobs[wave.wave_id]["result"]["routes"]]
    resp = cert.response_payload(wave, routes)
    resp["routes"][0]["route_details"][0]["duration"] += 1
    out = _certify(wave, resp, arcs_doc)
    assert out["is_feasible"] is False
    assert "arc_duration_mismatch" in {v["type"] for v in out["violations"]}


def test_capacity_exceeded_is_rejected(campaign):
    from uniride_core.exact import certification as cert

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, "2026-10-05:pickup:525")
    ids = list(wave.occurrence_ids)
    # every student on one route: more than 4 Sw / 5 So seats
    out = _certify(wave, cert.response_payload(wave, [tuple(ids)]), arcs_doc)
    assert out["is_feasible"] is False
    types = {v["type"] for v in out["violations"]}
    assert types & {"capacity_violation", "fleet_capacity_violation"}, types


def test_ride_time_over_r_is_rejected(campaign):
    """The same visiting order is feasible at R = 90 and infeasible when the request carries R = 5."""
    from uniride_core.exact import certification as cert

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, "2026-10-05:pickup:765")
    routes = [tuple(r["student_ids"]) for r in jobs[wave.wave_id]["result"]["routes"]]
    resp = cert.response_payload(wave, routes)
    assert _certify(wave, resp, arcs_doc)["is_feasible"] is True
    tight = cert.request_payload(wave)
    tight["max_ride_time"] = 5
    out = _certify(wave, resp, arcs_doc, request_payload=tight)
    assert out["is_feasible"] is False
    assert "ride_time_violation" in {v["type"] for v in out["violations"]}


def test_missing_arc_fails_closed(campaign):
    from uniride_core.exact import certification as cert

    arcs_doc, jobs = _archive()
    wave = _wave(campaign, "2026-10-05:pickup:765")
    routes = [tuple(r["student_ids"]) for r in jobs[wave.wave_id]["result"]["routes"]]
    resp = cert.response_payload(wave, routes)
    # (a) no lookup at all
    assert _certify(wave, resp, arcs_doc, lookup=None)["is_feasible"] is False
    # (b) a slice with one arc of the route removed
    first = resp["routes"][0]["route_details"][1]
    holed = deepcopy(arcs_doc)
    holed["arcs"] = [a for a in holed["arcs"]
                     if (a["origin_code"], a["destination_code"]) != (first["location1"], first["location2"])]
    out = _certify(wave, resp, holed)
    assert out["is_feasible"] is False
    assert "missing_arc" in {v["type"] for v in out["violations"]}


# ---------- occurrence expansion: a column selected twice ----------
def _two_colocated_wave():
    from uniride_core.exact import WaveInstance, compute_matrix_sha256

    # two Sw students at the same stop: matrix [depot, s1, s2]; zero arc between them
    matrix = ((0, 10, 10), (12, 0, 0), (12, 0, 0))
    return WaveInstance(
        wave_id="2026-10-05:pickup:525", service_date="2026-10-05", direction="pickup", anchor_minutes=525,
        max_ride_minutes=60, max_tour_minutes=150, depot_code="D.Kampus",
        occurrence_ids=("2026-10-05:pickup:SwA~1", "2026-10-05:pickup:SwA~2"),
        location_codes=("SwA", "SwA"), classes=("Sw", "Sw"), matrix=matrix,
        matrix_sha256=compute_matrix_sha256(matrix), arc_slice_sha256="s" * 64, declared_snapshot_sha256="d" * 64)


_ARCS = {"arcs": [{"origin_code": "D.Kampus", "destination_code": "SwA", "duration_minutes": 10},
                  {"origin_code": "SwA", "destination_code": "D.Kampus", "duration_minutes": 12}]}


def test_column_selected_twice_expands_to_distinct_occurrences_and_certifies():
    from uniride_core.exact import VehicleTypeSpec, certification as cert
    from uniride_core.exact.ampl_backend import expand_selection
    from uniride_core.exact.route_enumeration import enumerate_wave

    wave = _two_colocated_wave()
    # one Sw seat per vehicle: the only feasible partition uses the one-student column twice
    enum = enumerate_wave(wave, (VehicleTypeSpec("large", 1, 0, 10),))
    single = [i for i, c in enumerate(enum.columns) if sum(c.multiplicity) == 1]
    assert len(single) == 1
    routes = expand_selection(enum, [(single[0], 2)], wave.occurrence_ids)
    seqs = [r.occurrence_ids for r in routes]
    assert sorted(i for s in seqs for i in s) == sorted(wave.occurrence_ids)  # each occurrence exactly once
    request = cert.request_payload(wave, sw_capacity=1, so_capacity=0)
    ok = _certify(wave, cert.response_payload(wave, seqs), _ARCS, request_payload=request)
    assert ok["is_feasible"] is True, ok["violations"]
    # the naive expansion (the same occurrence on both copies) is rejected: coverage, not a quiet pass
    dup = _certify(wave, cert.response_payload(wave, [seqs[0], seqs[0]]), _ARCS, request_payload=request)
    assert dup["is_feasible"] is False
    assert cert.recompute_objective(wave, seqs) == (2, 44)


# ---------- objective cross-check ----------
def test_objective_cross_check_accepts_equal_and_rejects_mismatch():
    from uniride_core.exact import certification as cert

    assert cert.objective_mismatches(4, 300, 4, 300) == []
    assert cert.objective_mismatches(4, 300, 4, 300.0000004) == []        # within 1e-6
    assert cert.objective_mismatches(4, 300, 4, 301)                      # duration differs
    assert cert.objective_mismatches(4, 300, 5, 300)                      # route count differs
    assert cert.objective_mismatches(4, 300, None, 300)                   # missing solver value never passes


# ---------- exact <= GA and gap arithmetic ----------
def test_exact_not_above_ga_violations():
    from uniride_core.exact import gaps

    ok = dict(exact_optimal=True, k_star=4, d_star=300, k_ga=5, d_ga=250, k_lb=4, d_lb=300)
    assert gaps.exact_vs_ga_violations(**ok) == []                         # fewer routes wins over duration
    assert gaps.exact_vs_ga_violations(**dict(ok, k_ga=4, d_ga=300)) == []  # equal is allowed
    assert gaps.exact_vs_ga_violations(**dict(ok, k_ga=3, d_ga=900, k_lb=None))  # exact needs more routes than the GA
    assert gaps.exact_vs_ga_violations(**dict(ok, k_ga=4, d_ga=299, d_lb=None))  # equal K, GA shorter (no D_LB masking)
    # the exact claim is blocking only when the exact stage is optimal
    assert gaps.exact_vs_ga_violations(**dict(ok, exact_optimal=False, k_ga=3, d_ga=900, k_lb=2, d_lb=None)) == []


def test_bound_violations_are_errors_even_without_proof():
    from uniride_core.exact import gaps

    assert gaps.exact_vs_ga_violations(exact_optimal=False, k_star=None, d_star=None, k_ga=3, d_ga=900,
                                       k_lb=4, d_lb=None)                  # K_GA < K_LB
    assert gaps.exact_vs_ga_violations(exact_optimal=False, k_star=5, d_star=None, k_ga=5, d_ga=299,
                                       k_lb=4, d_lb=300)                   # equal K*, D_GA < D_LB


def test_gap_arithmetic_hand_example():
    from uniride_core.exact import gaps

    g = gaps.gap_fields(k_ga=5, d_ga=330, k_lb=4, k_star=4, d_lb=300, d_lb_free=290)
    assert g["dK"] == 1
    assert g["gD_note"] == "not_comparable_K_GA_gt_Kstar" and g["gD"] is None
    assert g["gD_free"] == pytest.approx((330 - 290) / 290)
    g = gaps.gap_fields(k_ga=4, d_ga=330, k_lb=4, k_star=4, d_lb=300, d_lb_free=290)
    assert g["dK"] == 0 and g["gD_note"] == "comparable"
    assert g["gD"] == pytest.approx(0.1) and g["gD_free"] == pytest.approx(40 / 290)


def test_gap_fields_when_stage1_is_not_proven_or_bound_missing():
    from uniride_core.exact import gaps

    g = gaps.gap_fields(k_ga=5, d_ga=330, k_lb=4, k_star=None, d_lb=None, d_lb_free=None)
    assert g["dK"] == 1 and g["gD"] is None and g["gD_free"] is None
    assert g["gD_note"] == "unavailable_stage1_not_proven"
    g = gaps.gap_fields(k_ga=4, d_ga=330, k_lb=4, k_star=4, d_lb=None, d_lb_free=250)
    assert g["gD_note"] == "unavailable_no_D_LB" and g["gD_free"] == pytest.approx(80 / 250)


# ---------- boundary ----------
def test_bridge_modules_import_no_optimizer_api_or_academic_benchmark_or_amplpy():
    for name in ("certification.py", "gaps.py"):
        tree = ast.parse((EXACT / name).read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                roots.add((node.module or "").split(".")[0])
        assert not roots & {"optimizer_api", "academic_benchmark", "amplpy", "models", "verification"}, (name, roots)
    code = "import sys, uniride_core.exact.certification, uniride_core.exact.gaps; sys.exit(1 if 'amplpy' in sys.modules else 0)"
    assert subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO).returncode == 0
