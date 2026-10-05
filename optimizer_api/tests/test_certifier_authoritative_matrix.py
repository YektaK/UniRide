"""C2 (certifier + rounding): the certificate re-costs every step on the matrix.

Owner requirement (2026-10-05): all travel times come from the Supabase
``time_matrix`` table. The route certificate must judge feasibility against that
directed matrix, never against the durations a solver reports about itself
(audit C2 mechanism points 3 and 4, Appendix H.3).
"""

import os

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

import pytest

from models.schemas import (
    LocationNode,
    OptimizationRequest,
    OptimizationResponse,
    RouteStep,
    StudentNode,
    VehicleRoute,
)
from strategies.ortools_cvrp import ORToolsCVRPStrategy
from utils.matrix_repository import IncompleteTravelMatrixError
from verification import response_certifier
from verification.response_certifier import certify_optimization_response

CODES = ["D", "L1", "L2", "L3", "L4", "L5"]
TRUE_ARC = 10.04


def _arcs(value=TRUE_ARC):
    return {a: {b: value for b in CODES if b != a} for a in CODES}


def _lookup(arcs):
    def lookup(origin, destination):
        if origin == destination:
            return 0.0
        try:
            return float(arcs[origin][destination])
        except KeyError:
            raise IncompleteTravelMatrixError(origin, destination) from None

    return lookup


def _request(count=5, **overrides):
    base = dict(
        algorithm="ortools_cvrp",
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=[
            StudentNode(
                id=f"S{i}",
                location_code=f"L{i}",
                disability_type="So",
                coordinates={"lat": 0.01 * i, "lng": 0.0},
            )
            for i in range(1, count + 1)
        ],
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=60,
    )
    base.update(overrides)
    return OptimizationRequest(**base)


def _response(chain, durations, total=None):
    steps = [
        RouteStep(location1=a, location2=b, duration=d, distance=0.0)
        for (a, b), d in zip(zip(chain, chain[1:]), durations)
    ]
    customers = [code for code in chain if code != "D"]
    route = VehicleRoute(
        vehicle_id="Araç 1 (test)",
        route_details=steps,
        total_duration_minutes=sum(durations) if total is None else total,
        total_distance_km=0.0,
        sw_count=0,
        so_count=len(customers),
        student_ids=[f"S{code[1:]}" for code in customers],
    )
    return OptimizationResponse(
        algorithm_used="test",
        success=True,
        routes=[route],
        total_vehicles=1,
        total_duration_minutes=route.total_duration_minutes,
    )


def _types(certificate):
    return {violation["type"] for violation in certificate["violations"]}


def test_matching_durations_certify():
    chain = ["D", "L1", "L2", "D"]
    response = _response(chain, [TRUE_ARC] * 3)
    certificate = certify_optimization_response(
        _request(2), response, arc_lookup=_lookup(_arcs())
    )
    assert certificate["is_feasible"], certificate["violations"]


def test_all_zero_step_durations_are_rejected():
    """C2(a): a zero-minute route claimed against a real matrix must not certify."""
    chain = ["D", "L1", "L2", "L3", "D"]
    response = _response(chain, [0.0] * 4)
    certificate = certify_optimization_response(
        _request(3), response, arc_lookup=_lookup(_arcs())
    )
    assert not certificate["is_feasible"]
    assert "arc_duration_mismatch" in _types(certificate)


def test_durations_that_differ_from_matrix_are_rejected():
    chain = ["D", "L1", "L2", "D"]
    response = _response(chain, [5.0, 5.0, 5.0])
    certificate = certify_optimization_response(
        _request(2), response, arc_lookup=_lookup(_arcs())
    )
    assert not certificate["is_feasible"]
    assert "arc_duration_mismatch" in _types(certificate)


def test_directed_matrix_is_used_not_a_symmetric_guess():
    arcs = _arcs()
    arcs["L1"]["L2"] = 25.0  # L2 -> L1 stays 10.04
    chain = ["D", "L2", "L1", "D"]
    # reported as if the arc were the cheap reverse direction
    response = _response(chain, [TRUE_ARC, TRUE_ARC, TRUE_ARC])
    ok = certify_optimization_response(
        _request(2), response, arc_lookup=_lookup(arcs)
    )
    assert ok["is_feasible"], ok["violations"]
    chain = ["D", "L1", "L2", "D"]
    wrong = _response(chain, [TRUE_ARC, TRUE_ARC, TRUE_ARC])
    bad = certify_optimization_response(
        _request(2), wrong, arc_lookup=_lookup(arcs)
    )
    assert not bad["is_feasible"]
    assert "arc_duration_mismatch" in _types(bad)


def test_ortools_rounding_repro_h3_is_rejected():
    """C2(b), Appendix H.3: reported 60.0, true 60.24, max 60 must not certify."""
    chain = ["D", "L5", "L4", "L3", "L2", "L1", "D"]
    response = _response(chain, [10.0] * 6)
    certificate = certify_optimization_response(
        _request(5), response, arc_lookup=_lookup(_arcs())
    )
    assert not certificate["is_feasible"]
    assert "arc_duration_mismatch" in _types(certificate)
    assert "duration_violation" in _types(certificate)


def test_true_duration_over_max_is_rejected_even_when_claim_matches_matrix():
    chain = ["D", "L5", "L4", "L3", "L2", "L1", "D"]
    response = _response(chain, [TRUE_ARC] * 6)  # 60.24 > 60, honestly reported
    certificate = certify_optimization_response(
        _request(5), response, arc_lookup=_lookup(_arcs())
    )
    assert not certificate["is_feasible"]
    assert "duration_violation" in _types(certificate)
    assert "arc_duration_mismatch" not in _types(certificate)


def test_ride_time_is_judged_on_matrix_durations():
    chain = ["D", "L1", "L2", "L3", "D"]
    response = _response(chain, [1.0, 1.0, 1.0, 1.0])  # claims a 3 min ride
    certificate = certify_optimization_response(
        _request(3, max_ride_time=25), response, arc_lookup=_lookup(_arcs())
    )
    assert not certificate["is_feasible"]
    assert "arc_duration_mismatch" in _types(certificate)
    assert "ride_time_violation" in _types(certificate)


def test_unresolvable_step_endpoint_is_an_error_not_a_skip():
    chain = ["D", "L1", "GHOST", "D"]
    response = _response(chain, [TRUE_ARC] * 3)
    certificate = certify_optimization_response(
        _request(2), response, arc_lookup=_lookup(_arcs())
    )
    assert not certificate["is_feasible"]
    assert "missing_arc" in _types(certificate)


def test_arc_missing_from_matrix_is_an_error():
    arcs = _arcs()
    del arcs["L1"]["L2"]
    chain = ["D", "L1", "L2", "D"]
    response = _response(chain, [TRUE_ARC] * 3)
    certificate = certify_optimization_response(
        _request(2), response, arc_lookup=_lookup(arcs)
    )
    assert not certificate["is_feasible"]
    assert "missing_arc" in _types(certificate)


def test_missing_arc_lookup_fails_closed():
    chain = ["D", "L1", "L2", "D"]
    response = _response(chain, [TRUE_ARC] * 3)
    certificate = certify_optimization_response(_request(2), response, arc_lookup=None)
    assert certificate["is_feasible"] is False
    assert "travel-time matrix" in certificate.get("certify_error", "")


def test_tolerance_only_absorbs_two_decimal_formatting():
    arcs = _arcs(10.0449)  # a decimal matrix value; response reports round(x, 2)
    chain = ["D", "L1", "L2", "D"]
    response = _response(chain, [10.04] * 3)
    certificate = certify_optimization_response(
        _request(2), response, arc_lookup=_lookup(arcs)
    )
    assert certificate["is_feasible"], certificate["violations"]
    assert response_certifier.ARC_DURATION_TOLERANCE == pytest.approx(0.005)
    off = _response(chain, [10.06] * 3)
    assert not certify_optimization_response(
        _request(2), off, arc_lookup=_lookup(arcs)
    )["is_feasible"]


def test_ortools_reports_true_unscaled_durations_and_respects_max(monkeypatch):
    """C2(b) at the source: true arcs reported, rounding can never exceed the max."""

    class _Loader:
        def get_submatrix(self, request_locations, coordinates=None, **_kwargs):
            lookup = _lookup(_arcs())
            return [[lookup(a, b) for b in request_locations] for a in request_locations]

    import utils.data_loader as data_loader

    monkeypatch.setattr(
        data_loader.DataLoader, "get_instance", staticmethod(lambda: _Loader())
    )
    request = _request(5)
    response = ORToolsCVRPStrategy(time_limit_seconds=1).optimize(request)
    assert response.success
    lookup = _lookup(_arcs())
    for route in response.routes:
        true_total = 0.0
        for step in route.route_details:
            expected = lookup(step.location1, step.location2)
            assert step.duration == pytest.approx(expected, abs=0.005)
            true_total += expected
        assert true_total <= request.max_travel_time + 1e-9
    certificate = certify_optimization_response(request, response, arc_lookup=lookup)
    assert certificate["is_feasible"], certificate["violations"]
