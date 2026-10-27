"""MT1-03 (audit H3, decision O09): the returned schedule is the certified schedule.

With a ``target_time`` the router builds ``departure_time`` / ``arrival_times``
(HH:MM, display rounding: stop times down, the pickup school arrival up) and the
exact fields ``schedule_start_minutes`` / ``schedule_end_minutes`` /
``arrival_minutes`` from the MT1-01 simulator on the captured authoritative arcs,
never from reported step durations. The certificate re-simulates every route and
reports ``schedule_mismatch`` when a returned exact time differs.

Plan: docs/superpowers/plans/2026-10-27-mt1-time-window-unification.md, item MT1-03.
"""

import os
import random

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from models.schemas import (
    CompareRequest,
    LocationNode,
    OptimizationRequest,
    OptimizationResponse,
    RouteStep,
    StudentNode,
    VehicleRoute,
)
from routers import optimization
from test_production_feasibility_boundary import _StubStrategy, _install_strategy
from uniride_core.algorithms.route_scheduling import minutes_to_time
from uniride_core.algorithms.route_schedule import (
    simulate_school_dropoff,
    simulate_school_pickup,
)
from verification.response_certifier import certify_optimization_response

OLD_ROUTE_KEYS = {
    "vehicle_id", "route_details", "total_duration_minutes", "total_distance_km",
    "sw_count", "so_count", "student_ids", "departure_time", "arrival_times",
}
NEW_ROUTE_KEYS = {"schedule_start_minutes", "schedule_end_minutes", "arrival_minutes"}


def _lookup(arcs):
    def lookup(origin, destination):
        if origin == destination:
            return 0.0
        return float(arcs[(origin, destination)])

    return lookup


def _students(spec):
    """spec: list of (code, pickup_time, dropoff_time)."""
    return [
        {
            "id": f"S_{code}", "location_code": code, "disability_type": "So",
            "pickup_time": pickup, "dropoff_time": dropoff,
        }
        for code, pickup, dropoff in spec
    ]


def _payload(students, **overrides):
    base = {
        "algorithm": "stub",
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
        "students": students,
        "sw_capacity": 4,
        "so_capacity": 5,
        "max_travel_time": 240,
        "direction": "pickup",
    }
    base.update(overrides)
    return base


def _route_for(order, arcs, vehicle_id="V1"):
    chain = ["D", *order, "D"]
    steps = [
        RouteStep(location1=a, location2=b, duration=round(float(arcs[(a, b)]), 2), distance=0.0)
        for a, b in zip(chain, chain[1:])
    ]
    return VehicleRoute(
        vehicle_id=vehicle_id,
        route_details=steps,
        total_duration_minutes=sum(step.duration for step in steps),
        so_count=len(order),
        student_ids=[f"S_{code}" for code in order],
    )


def _stub(orders, arcs, **route_overrides):
    def factory(request):
        routes = [_route_for(order, arcs, f"V{i + 1}") for i, order in enumerate(orders)]
        for route in routes:
            for name, value in route_overrides.items():
                setattr(route, name, value)
        return OptimizationResponse(
            algorithm_used="stub", success=True, routes=routes,
            total_vehicles=len(routes),
            total_duration_minutes=sum(r.total_duration_minutes for r in routes),
            execution_time_seconds=0.01, direction=request.direction.value,
        )

    return _StubStrategy(factory)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")
    from optimizer_api import rate_limit
    rate_limit._buckets.clear()
    app = FastAPI()
    app.include_router(optimization.router)
    return TestClient(app)


def _serve(monkeypatch, orders, arcs, **route_overrides):
    _install_strategy(monkeypatch, "stub", _stub(orders, arcs, **route_overrides))
    monkeypatch.setattr(
        optimization, "authoritative_arc_lookup",
        lambda *args, **kwargs: _lookup(arcs),
    )


def _optimize(client, payload):
    response = client.post("/api/v1/optimize", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# The audit H3 scenario: target 08:30, A has pickup 08:00 (window 07:30-08:00), B has
# no time of its own (MT1-08: no implicit window). Arcs D->A 10, A->B 5, B->D 10.
H3_ARCS = {("D", "A"): 10, ("A", "B"): 5, ("B", "D"): 10}


def test_h3_returned_schedule_is_the_certified_schedule(client, monkeypatch):
    _serve(monkeypatch, [["A", "B"]], H3_ARCS)
    body = _optimize(client, _payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    ))

    assert body["success"] is True, body.get("error_message")
    route = body["routes"][0]
    # before the fix: the last stop was pinned to its own window close and the walk went
    # backwards with no return arc (A picked up 25 minutes late, school at 08:40)
    assert route["departure_time"] == "07:50"
    assert route["arrival_times"] == {"A": "08:00", "B": "08:05", "D": "08:15"}
    assert route["schedule_start_minutes"] == pytest.approx(470.0)
    assert route["schedule_end_minutes"] == pytest.approx(495.0)
    assert route["arrival_minutes"] == pytest.approx({"A": 480.0, "B": 485.0})


def test_schedule_is_built_from_arcs_not_from_reported_durations(client, monkeypatch):
    # the stub reports 1-minute steps; the authoritative arcs are the H3 arcs
    _serve(monkeypatch, [["A", "B"]], H3_ARCS)
    original = _stub([["A", "B"]], H3_ARCS)._factory

    def lying(request):
        response = original(request)
        for step in response.routes[0].route_details:
            step.duration = 1.0
        response.routes[0].total_duration_minutes = 3.0
        response.total_duration_minutes = 3.0
        return response

    _install_strategy(monkeypatch, "stub", _StubStrategy(lying))
    body = _optimize(client, _payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    ))

    # the certificate rejects the lying durations, but the schedule it computed is the
    # arc-based one, not 1-minute steps
    assert body["success"] is False
    route = body["routes"][0]
    assert route["schedule_start_minutes"] == pytest.approx(470.0)
    assert route["schedule_end_minutes"] == pytest.approx(495.0)


def test_display_rounding_stops_down_school_arrival_up(client, monkeypatch):
    # B at 479.6 (07:59 shown), school arrival 494.1 (08:15 shown, rounded up)
    arcs = {("D", "B"): 10, ("B", "A"): 0.4, ("A", "D"): 14.1}
    _serve(monkeypatch, [["B", "A"]], arcs)
    body = _optimize(client, _payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:15", offset_minutes=0,
    ))

    assert body["success"] is True, body.get("error_message")
    route = body["routes"][0]
    assert route["arrival_minutes"] == pytest.approx({"B": 479.6, "A": 480.0})
    assert route["schedule_end_minutes"] == pytest.approx(494.1)
    assert route["arrival_times"]["B"] == "07:59"
    assert route["arrival_times"]["A"] == "08:00"
    assert route["arrival_times"]["D"] == "08:15"
    assert route["departure_time"] == "07:49"  # 469.6 shown down


def test_minutes_to_time_rounding_modes():
    assert minutes_to_time(479.6) == "07:59"
    assert minutes_to_time(494.1, rounding="ceil") == "08:15"
    assert minutes_to_time(494.0, rounding="ceil") == "08:14"
    # float noise around a whole minute does not move the displayed minute
    assert minutes_to_time(494.0 + 1e-12, rounding="ceil") == "08:14"
    assert minutes_to_time(494.0 - 1e-12) == "08:14"
    assert minutes_to_time(480.0 - 1e-12) == "08:00"
    assert minutes_to_time(-5, rounding="ceil") == "00:00"
    assert minutes_to_time(24 * 60 + 30, rounding="ceil") == "23:59"


def test_edited_arrival_minutes_is_a_schedule_mismatch():
    arcs = H3_ARCS
    request = OptimizationRequest.model_validate(_payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    ))

    def response(arrival_a):
        route = _route_for(["A", "B"], arcs)
        route.schedule_start_minutes = 470.0
        route.schedule_end_minutes = 495.0
        route.arrival_minutes = {"A": arrival_a, "B": 485.0}
        return OptimizationResponse(
            algorithm_used="stub", success=True, routes=[route], total_vehicles=1,
            total_duration_minutes=route.total_duration_minutes,
            execution_time_seconds=0.01, direction="pickup",
        )

    honest = certify_optimization_response(request, response(480.0), arc_lookup=_lookup(arcs))
    assert honest["is_feasible"] is True, honest["violations"]

    edited = certify_optimization_response(request, response(483.0), arc_lookup=_lookup(arcs))
    assert edited["is_feasible"] is False
    types = [v["type"] for v in edited["violations"]]
    assert types == ["schedule_mismatch"]


@pytest.mark.parametrize(
    "field,value",
    [("schedule_start_minutes", 465.0), ("schedule_end_minutes", 500.0)],
)
def test_edited_start_or_end_is_a_schedule_mismatch(field, value):
    request = OptimizationRequest.model_validate(_payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    ))
    route = _route_for(["A", "B"], H3_ARCS)
    route.schedule_start_minutes = 470.0
    route.schedule_end_minutes = 495.0
    route.arrival_minutes = {"A": 480.0, "B": 485.0}
    setattr(route, field, value)
    response = OptimizationResponse(
        algorithm_used="stub", success=True, routes=[route], total_vehicles=1,
        total_duration_minutes=route.total_duration_minutes,
        execution_time_seconds=0.01, direction="pickup",
    )

    certificate = certify_optimization_response(request, response, arc_lookup=_lookup(H3_ARCS))

    assert [v["type"] for v in certificate["violations"]] == ["schedule_mismatch"]


def test_missing_or_extra_arrival_key_is_a_schedule_mismatch():
    request = OptimizationRequest.model_validate(_payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    ))
    for arrivals in ({"A": 480.0}, {"A": 480.0, "B": 485.0, "X": 1.0}):
        route = _route_for(["A", "B"], H3_ARCS)
        route.schedule_start_minutes = 470.0
        route.schedule_end_minutes = 495.0
        route.arrival_minutes = arrivals
        response = OptimizationResponse(
            algorithm_used="stub", success=True, routes=[route], total_vehicles=1,
            total_duration_minutes=route.total_duration_minutes,
            execution_time_seconds=0.01, direction="pickup",
        )
        certificate = certify_optimization_response(
            request, response, arc_lookup=_lookup(H3_ARCS)
        )
        assert [v["type"] for v in certificate["violations"]] == ["schedule_mismatch"]


def test_exact_fields_without_a_target_time_are_a_schedule_mismatch():
    request = OptimizationRequest.model_validate(_payload(_students([("A", None, None)])))
    arcs = {("D", "A"): 5, ("A", "D"): 5}
    route = _route_for(["A"], arcs)
    route.schedule_start_minutes = 470.0
    response = OptimizationResponse(
        algorithm_used="stub", success=True, routes=[route], total_vehicles=1,
        total_duration_minutes=route.total_duration_minutes,
        execution_time_seconds=0.01, direction="pickup",
    )

    certificate = certify_optimization_response(request, response, arc_lookup=_lookup(arcs))

    assert [v["type"] for v in certificate["violations"]] == ["schedule_mismatch"]


# -- equality over every route of a seeded multi-route response ---------------

def _random_instance(seed, direction):
    rng = random.Random(seed)
    codes = [f"L{i}" for i in range(1, 7)]
    arcs = {}
    nodes = ["D", *codes]
    for a in nodes:
        for b in nodes:
            if a != b:
                arcs[(a, b)] = round(rng.uniform(2.0, 9.0), 3)
    anchor = "08:30" if direction == "pickup" else "17:00"
    spec = []
    for index, code in enumerate(codes):
        if index % 2 == 0:
            spec.append((code, "08:30" if direction == "pickup" else None,
                         "17:00" if direction == "dropoff" else None))
        else:
            spec.append((code, None, None))
    orders = [codes[0:2], codes[2:4], codes[4:6]]
    rng.shuffle(orders)
    return arcs, spec, orders, anchor


@pytest.mark.parametrize("direction", ["pickup", "dropoff"])
@pytest.mark.parametrize("seed", [1, 2, 3, 11])
def test_returned_times_equal_independent_resimulation_on_every_route(
    client, monkeypatch, direction, seed
):
    arcs, spec, orders, anchor = _random_instance(seed, direction)
    _serve(monkeypatch, orders, arcs)
    body = _optimize(client, _payload(
        _students(spec), direction=direction, use_time_windows=True,
        target_time=anchor, offset_minutes=5, so_capacity=3,
    ))

    assert body["success"] is True, body.get("error_message")
    assert len(body["routes"]) == 3
    anchor_minutes = int(anchor[:2]) * 60 + int(anchor[3:])
    windows = {
        code: ((anchor_minutes - 30, anchor_minutes) if direction == "pickup"
               else (anchor_minutes, anchor_minutes + 30))
        for code, pickup, dropoff in spec if pickup or dropoff
    }
    for route, order in zip(body["routes"], orders):
        stops = list(range(1, len(order) + 1))

        def arc(i, j, order=order):
            names = ["D", *order]
            return 0.0 if names[i] == names[j] else arcs[(names[i], names[j])]

        local_windows = {
            i + 1: windows[code] for i, code in enumerate(order) if code in windows
        }
        if direction == "pickup":
            expected = simulate_school_pickup(
                stops, arc, deadline=anchor_minutes - 5, windows=local_windows
            )
        else:
            expected = simulate_school_dropoff(
                stops, arc, ready=anchor_minutes + 5, windows=local_windows
            )
        assert expected.feasible
        assert route["schedule_start_minutes"] == pytest.approx(expected.start, abs=1e-9)
        assert route["schedule_end_minutes"] == pytest.approx(expected.end, abs=1e-9)
        for code, arrival in zip(order, expected.arrivals):
            assert route["arrival_minutes"][code] == pytest.approx(arrival, abs=1e-9)
        assert set(route["arrival_minutes"]) == set(order)


# -- no target_time: the response keeps today's shape -------------------------

def test_request_without_target_time_keeps_todays_response(client, monkeypatch):
    arcs = {("D", "A"): 5, ("A", "D"): 5}
    _serve(monkeypatch, [["A"]], arcs)
    body = _optimize(client, _payload(_students([("A", None, None)])))

    assert body["success"] is True, body.get("error_message")
    route = body["routes"][0]
    assert set(route) == OLD_ROUTE_KEYS
    assert route["departure_time"] is None and route["arrival_times"] is None


def test_unscheduled_route_dump_is_byte_identical_to_the_old_shape():
    route = _route_for(["A"], {("D", "A"): 5, ("A", "D"): 5})
    assert set(route.model_dump()) == OLD_ROUTE_KEYS
    assert NEW_ROUTE_KEYS.isdisjoint(route.model_dump_json())


def test_target_time_without_windows_also_gets_the_schedule(client, monkeypatch):
    # demo shape: one anchor, no windows -> start = anchor - total travel, end = anchor
    arcs = {("D", "A"): 5, ("A", "D"): 7}
    _serve(monkeypatch, [["A"]], arcs)
    body = _optimize(client, _payload(
        _students([("A", None, None)]), use_time_windows=False,
        target_time="08:30", offset_minutes=0,
    ))

    route = body["routes"][0]
    assert route["schedule_start_minutes"] == pytest.approx(498.0)
    assert route["schedule_end_minutes"] == pytest.approx(510.0)
    assert route["departure_time"] == "08:18"
    assert route["arrival_times"] == {"A": "08:23", "D": "08:30"}


def test_a_strategy_supplied_schedule_is_replaced(client, monkeypatch):
    _serve(
        monkeypatch, [["A", "B"]], H3_ARCS,
        departure_time="01:00", arrival_times={"A": "01:05", "B": "01:10", "D": "01:20"},
    )
    body = _optimize(client, _payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    ))

    assert body["routes"][0]["departure_time"] == "07:50"


def test_unanswered_arc_leaves_the_route_unscheduled_and_rejected(client, monkeypatch):
    arcs = dict(H3_ARCS)
    _install_strategy(monkeypatch, "stub", _stub([["A", "B"]], arcs))

    def lookup(origin, destination):
        if (origin, destination) == ("A", "B"):
            raise KeyError("no arc")
        return 0.0 if origin == destination else float(arcs[(origin, destination)])

    monkeypatch.setattr(
        optimization, "authoritative_arc_lookup", lambda *a, **k: lookup
    )
    body = _optimize(client, _payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    ))

    assert body["success"] is False
    route = body["routes"][0]
    assert route["departure_time"] is None and route["arrival_times"] is None
    assert NEW_ROUTE_KEYS.isdisjoint(route)


def test_compare_routes_carry_the_same_schedule(monkeypatch):
    _serve(monkeypatch, [["A", "B"]], H3_ARCS)
    base = OptimizationRequest.model_validate(_payload(
        _students([("A", "08:00", None), ("B", None, None)]),
        use_time_windows=True, target_time="08:30", offset_minutes=0,
    )).model_dump()
    compare = CompareRequest.model_validate(
        {k: v for k, v in base.items() if k in CompareRequest.model_fields}
        | {"algorithms": ["stub"]}
    )

    result = optimization.compare_algorithms(compare).results[0]

    assert result.success is True, result.error_message
    route = result.routes[0]
    assert route.departure_time == "07:50"
    assert route.arrival_times == {"A": "08:00", "B": "08:05", "D": "08:15"}
    assert route.schedule_end_minutes == pytest.approx(495.0)
