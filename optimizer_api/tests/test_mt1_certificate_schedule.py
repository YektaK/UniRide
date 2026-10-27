"""MT1-02 (audit H2, decision O09): the production certificate uses the simulator.

When a request has ``target_time`` or ``use_time_windows`` the certificate
simulates every route on the captured authoritative arcs
(``uniride_core.algorithms.route_schedule``): the return arc to school is held to
``target_time - offset_minutes`` (pickup), waits count in the tour and in the
ride, and the optional ``stop_dwell_minutes`` / ``sw_boarding_minutes`` count as
service. Requests without ``target_time`` keep the pre-MT1 certificate.
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
from uniride_core.adapters.demand_builder import student_occurrence_keys
from verification.response_certifier import certify_optimization_response


def _lookup(arcs):
    def lookup(origin, destination):
        if origin == destination:
            return 0.0
        return float(arcs[(origin, destination)])

    return lookup


def _student(code, *, sw=False, pickup=None, dropoff=None, sid=None):
    return StudentNode(
        id=sid or f"S_{code}",
        location_code=code,
        disability_type="Sw" if sw else "So",
        pickup_time=pickup,
        dropoff_time=dropoff,
        coordinates={"lat": 0.0, "lng": 0.0},
    )


def _request(students, **overrides):
    base = dict(
        algorithm="ga_split",
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=students,
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=120,
    )
    base.update(overrides)
    return OptimizationRequest(**base)


def _response(request, order, arcs):
    """One route D -> order -> D whose reported steps equal the matrix arcs.

    ``order`` lists the students' occurrence keys.
    """
    keys = student_occurrence_keys(request.students)
    by_key = dict(zip(keys, request.students))
    code = {"D": "D", **{k: s.location_code for k, s in by_key.items()}}
    chain = ["D", *order, "D"]
    steps = [
        RouteStep(
            location1=a,
            location2=b,
            duration=0.0 if code[a] == code[b] else float(arcs[(code[a], code[b])]),
            distance=0.0,
        )
        for a, b in zip(chain, chain[1:])
    ]
    total = sum(step.duration for step in steps)
    stops = [by_key[k] for k in order]
    route = VehicleRoute(
        vehicle_id="Arac 1 (test)",
        route_details=steps,
        total_duration_minutes=total,
        total_distance_km=0.0,
        sw_count=sum(1 for s in stops if s.disability_type == "Sw"),
        so_count=sum(1 for s in stops if s.disability_type != "Sw"),
        student_ids=[s.id for s in stops],
    )
    return OptimizationResponse(
        algorithm_used="test",
        success=True,
        routes=[route],
        total_vehicles=1,
        total_duration_minutes=total,
    )


def _certify(request, order, arcs):
    response = _response(request, order, arcs)
    return certify_optimization_response(request, response, arc_lookup=_lookup(arcs))


def _types(certificate):
    """Violation types, without the derived ``hard_violation`` (the stub says success)."""
    return [
        violation["type"]
        for violation in certificate["violations"]
        if violation["type"] != "hard_violation"
    ]


# ---------------------------------------------------------------------------
# 1. audit H2 scenario
# ---------------------------------------------------------------------------

H2_ARCS = {
    ("D", "LA"): 10.0,
    ("LA", "LB"): 20.0,
    ("LB", "D"): 20.0,
}


def _h2_request(**overrides):
    # Audit H2: target 08:30, offset 15, both students window 08:00-08:30
    # (pickup_time 08:30). Every departure reaches the school at 08:40 or later.
    return _request(
        [_student("LA", pickup="08:30"), _student("LB", pickup="08:30")],
        use_time_windows=True,
        target_time="08:30",
        offset_minutes=15,
        **overrides,
    )


def test_h2_scenario_misses_the_school_deadline():
    certificate = _certify(_h2_request(), ["LA", "LB"], H2_ARCS)
    assert not certificate["is_feasible"], certificate
    violation = next(
        v for v in certificate["violations"] if v["type"] == "time_window_violation"
    )
    assert violation["route_index"] == 0
    assert "deadline" in violation["details"]


def test_h2_scenario_is_feasible_when_the_offset_leaves_room():
    # School arrival is 08:40 (520); offset 0 gives deadline 08:30 -> still late.
    late = _certify(_h2_request(offset_minutes=0), ["LA", "LB"], H2_ARCS)
    assert "time_window_violation" in _types(late)
    # Windows 08:30-09:00 and target 09:30 give a deadline (570) the route meets:
    # depart 510, A 520, B 540, school 560.
    request = _request(
        [_student("LA", pickup="09:00"), _student("LB", pickup="09:00")],
        use_time_windows=True,
        target_time="09:30",
        offset_minutes=0,
    )
    ok = _certify(request, ["LA", "LB"], H2_ARCS)
    assert ok["is_feasible"], ok


# ---------------------------------------------------------------------------
# 2. demo-shaped request: unchanged certificate
# ---------------------------------------------------------------------------

DEMO_ARCS = {
    ("D", "L1"): 10.0,
    ("L1", "L2"): 7.5,
    ("L2", "D"): 12.25,
    ("D", "L2"): 9.0,
    ("L2", "L1"): 8.0,
    ("L1", "D"): 11.0,
}


def _demo_students():
    return [_student("L1"), _student("L2", sw=True)]


def test_demo_shape_certificate_is_unchanged():
    base = dict(use_time_windows=False, direction="pickup")
    plain = _request(_demo_students(), **base)
    demo = _request(_demo_students(), target_time="08:15", offset_minutes=0, **base)
    before = _certify(plain, ["L1", "L2"], DEMO_ARCS)
    after = _certify(demo, ["L1", "L2"], DEMO_ARCS)
    assert before == {"is_feasible": True, "violation_count": 0, "violations": []}
    assert after == before


def test_demo_shape_infeasible_certificate_is_byte_identical():
    base = dict(use_time_windows=False, direction="pickup", max_travel_time=25)
    plain = _request(_demo_students(), **base)
    demo = _request(_demo_students(), target_time="08:15", offset_minutes=0, **base)
    before = _certify(plain, ["L1", "L2"], DEMO_ARCS)
    after = _certify(demo, ["L1", "L2"], DEMO_ARCS)
    assert _types(before) == ["duration_violation"]
    assert after == before


# ---------------------------------------------------------------------------
# 3. offset_minutes not sent: API default 15, deadline must not depend on it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("direction", ["pickup", "dropoff"])
def test_offset_not_sent_stays_feasible_without_new_violation(direction):
    base = dict(use_time_windows=False, direction=direction, target_time="08:15")
    sent = _request(_demo_students(), offset_minutes=15, **base)
    unsent = _request(_demo_students(), **base)
    assert "offset_minutes" not in unsent.model_fields_set
    assert unsent.offset_minutes == 15
    plain = _request(
        _demo_students(), use_time_windows=False, direction=direction
    )
    expected = _certify(plain, ["L1", "L2"], DEMO_ARCS)
    assert expected["is_feasible"]
    assert _certify(unsent, ["L1", "L2"], DEMO_ARCS) == expected
    # sending the default explicitly gives the same answer
    assert _certify(sent, ["L1", "L2"], DEMO_ARCS) == expected


def test_deadline_is_the_same_whether_or_not_offset_was_sent():
    """The H2 route (school 08:40) against target 08:55: deadline 08:40 either way."""
    kwargs = dict(use_time_windows=True, target_time="08:55")
    students = lambda: [_student("LA", pickup="08:30"), _student("LB", pickup="08:30")]  # noqa: E731
    unsent = _request(students(), **kwargs)
    sent = _request(students(), offset_minutes=15, **kwargs)
    assert "offset_minutes" not in unsent.model_fields_set
    a = _certify(unsent, ["LA", "LB"], H2_ARCS)
    b = _certify(sent, ["LA", "LB"], H2_ARCS)
    assert a == b
    # deadline = 08:55 - 15 = 08:40 = 520 and the route reaches the school at 520
    assert a["is_feasible"], a


# ---------------------------------------------------------------------------
# 4. waiting aboard counts for max_ride_time and max_travel_time
# ---------------------------------------------------------------------------

WAIT_ARCS = {("D", "LA"): 5.0, ("LA", "LB"): 5.0, ("LB", "D"): 5.0}


def _wait_request(**overrides):
    # Drop-off, ready 14:00. A's window opens 14:00; B's window opens 14:30, so
    # the vehicle (aboard: B, and A until stop 1) waits 20 min at B.
    # Travel: tour 15, ride(B) 10. With the wait: tour 35, ride(B) 30.
    return _request(
        [_student("LA", dropoff="14:00"), _student("LB", dropoff="14:30")],
        use_time_windows=True,
        target_time="14:00",
        offset_minutes=0,
        direction="dropoff",
        **overrides,
    )


def test_wait_aboard_is_feasible_without_limits_being_tight():
    certificate = _certify(_wait_request(), ["LA", "LB"], WAIT_ARCS)
    assert certificate["is_feasible"], certificate


def test_wait_aboard_breaks_max_ride_time():
    certificate = _certify(_wait_request(max_ride_time=25), ["LA", "LB"], WAIT_ARCS)
    assert _types(certificate) == ["ride_time_violation"], certificate
    assert certificate["violations"][0]["route_index"] == 0


def test_ride_time_without_wait_still_passes_the_same_limit():
    request = _request(
        [_student("LA", dropoff="14:00"), _student("LB", dropoff="14:00")],
        use_time_windows=True,
        target_time="14:00",
        offset_minutes=0,
        direction="dropoff",
        max_ride_time=25,
    )
    assert _certify(request, ["LA", "LB"], WAIT_ARCS)["is_feasible"]


def test_wait_aboard_breaks_max_travel_time():
    certificate = _certify(_wait_request(max_travel_time=30), ["LA", "LB"], WAIT_ARCS)
    assert _types(certificate) == ["duration_violation"], certificate


# ---------------------------------------------------------------------------
# 5. service fields
# ---------------------------------------------------------------------------

SERVICE_ARCS = {("D", "L1"): 10.0, ("L1", "L2"): 10.0, ("L2", "D"): 10.0}


def test_stop_dwell_counts_in_the_tour():
    students = lambda: [_student("L1"), _student("L2")]  # noqa: E731
    base = dict(target_time="08:15", offset_minutes=0, max_travel_time=30)
    assert _certify(_request(students(), **base), ["L1", "L2"], SERVICE_ARCS)[
        "is_feasible"
    ]
    explicit_zero = _request(students(), stop_dwell_minutes=0, **base)
    assert _certify(explicit_zero, ["L1", "L2"], SERVICE_ARCS)["is_feasible"]
    heavy = _request(students(), stop_dwell_minutes=5, **base)
    certificate = _certify(heavy, ["L1", "L2"], SERVICE_ARCS)
    assert _types(certificate) == ["duration_violation"], certificate


def test_sw_boarding_misses_the_deadline_only_with_the_extra_time():
    # Pickup, target 09:00 offset 0 (deadline 540). A closes 08:00, B opens 08:30
    # after A, so the vehicle waits at B; the Sw boarding at B starts after that
    # wait: 510 + 30 + 5 = 545 > 540.
    def request(**extra):
        return _request(
            [
                _student("LA", pickup="08:00"),
                _student("LB", pickup="09:00", sw=True),
            ],
            use_time_windows=True,
            target_time="09:00",
            offset_minutes=0,
            **extra,
        )

    arcs = {("D", "LA"): 5.0, ("LA", "LB"): 5.0, ("LB", "D"): 5.0}
    assert _certify(request(), ["LA", "LB"], arcs)["is_feasible"]
    assert _certify(request(sw_boarding_minutes=0), ["LA", "LB"], arcs)["is_feasible"]
    late = _certify(request(sw_boarding_minutes=30), ["LA", "LB"], arcs)
    assert not late["is_feasible"]
    assert "time_window_violation" in _types(late)


def test_sw_boarding_counts_once_per_sw_student():
    arcs = {("D", "L1"): 10.0, ("L1", "D"): 10.0}
    students = lambda: [  # noqa: E731
        _student("L1", sw=True, sid="S1"),
        _student("L1", sw=True, sid="S2"),
    ]
    keys = student_occurrence_keys(students())
    assert len(keys) == 2 and keys[0] != keys[1]
    # tour = 20 + 2 * 6 = 32 > 30 although 1 * 6 would give 26.
    request = _request(
        students(), target_time="08:15", offset_minutes=0, max_travel_time=30,
        sw_boarding_minutes=6,
    )
    certificate = _certify(request, keys, arcs)
    assert _types(certificate) == ["duration_violation"], certificate
    # 2 * 4 = 8 -> 28 <= 30 passes.
    ok = _request(
        students(), target_time="08:15", offset_minutes=0, max_travel_time=30,
        sw_boarding_minutes=4,
    )
    assert _certify(ok, keys, arcs)["is_feasible"]


def test_service_fields_default_to_zero_and_reject_negative():
    request = _request([_student("L1")])
    assert request.stop_dwell_minutes == 0
    assert request.sw_boarding_minutes == 0
    with pytest.raises(ValueError):
        _request([_student("L1")], stop_dwell_minutes=-1)
    with pytest.raises(ValueError):
        _request([_student("L1")], sw_boarding_minutes=-1)


# ---------------------------------------------------------------------------
# students sharing a stop
# ---------------------------------------------------------------------------


def test_windows_of_students_sharing_a_stop_are_intersected():
    # Drop-off ready 14:00. S1 window 14:00-14:30, S2 window 14:30-15:00, both
    # at L1 (arc 10): the stop window is the single point 14:30 -> wait 20,
    # tour = 30 + 10 (return) = 40.
    arcs = {("D", "L1"): 10.0, ("L1", "D"): 10.0}
    students = lambda: [  # noqa: E731
        _student("L1", dropoff="14:00", sid="S1"),
        _student("L1", dropoff="14:30", sid="S2"),
    ]
    keys = student_occurrence_keys(students())
    common = dict(
        use_time_windows=True, target_time="14:00", offset_minutes=0,
        direction="dropoff",
    )
    ok = _certify(_request(students(), **common), keys, arcs)
    assert ok["is_feasible"], ok
    tight = _certify(_request(students(), max_travel_time=35, **common), keys, arcs)
    assert _types(tight) == ["duration_violation"], tight


def test_disjoint_windows_at_one_stop_are_a_violation():
    arcs = {("D", "L1"): 10.0, ("L1", "D"): 10.0}
    students = [
        _student("L1", dropoff="14:00", sid="S1"),
        _student("L1", dropoff="16:00", sid="S2"),
    ]
    keys = student_occurrence_keys(students)
    request = _request(
        students, use_time_windows=True, target_time="14:00", offset_minutes=0,
        direction="dropoff",
    )
    certificate = _certify(request, keys, arcs)
    assert not certificate["is_feasible"]
    assert "time_window_violation" in _types(certificate)
    assert "certify_error" not in certificate
