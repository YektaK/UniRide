"""WP3 tests: ga_split_hf API contract, 422 matrix, typed certificate, P6.

Design: docs/designs/HETEROGENEOUS_FLEET_DESIGN.md sections 5, 6, 7 (P6), 9.
"""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from certifier_matrix_support import (
    echo_arc_lookup,
)
from models.schemas import (
    LocationNode,
    OptimizationRequest,
    OptimizationResponse,
    RouteStep,
    StudentNode,
    VehicleRoute,
)
from p6_scenario import DEPOT_ID, install_loader, run_default_scenario, star_arcs, students
from routers import optimization
from verification.response_certifier import certify_optimization_response

GOLDEN = Path(__file__).parent / "golden" / "p6_ga_split_optimize_response.json"
LARGE = {"type_id": "large", "sw_capacity": 4, "so_capacity": 5}
CAR = {"type_id": "car", "sw_capacity": 0, "so_capacity": 4}


def _payload(**overrides):
    base = {
        "algorithm": "ga_split_hf",
        "students": [],
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
        "vehicle_types": [dict(LARGE), dict(CAR)],
        "minimize_type": "car",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 422 validation matrix
# ---------------------------------------------------------------------------

REJECTED = [
    ("hf_without_vehicle_types", _payload(vehicle_types=None, minimize_type=None), "requires vehicle_types"),
    ("types_with_other_algorithm", _payload(algorithm="ga_split"), "only supported by algorithm ga_split_hf"),
    (
        "types_and_vehicles",
        _payload(vehicles=[{"vehicle_id": "V1"}]),
        "mutually exclusive",
    ),
    ("time_windows", _payload(use_time_windows=True), "use_time_windows"),
    ("duplicate_type_id", _payload(vehicle_types=[dict(LARGE), dict(LARGE)]), "unique"),
    ("minimize_unknown", _payload(minimize_type="van"), "must name one of"),
    ("minimize_missing_with_two_types", _payload(minimize_type=None), "minimize_type is required"),
    (
        "minimize_without_types",
        _payload(algorithm="ga_split", vehicle_types=None),
        "minimize_type requires vehicle_types",
    ),
    (
        "two_quota_types",
        _payload(vehicle_types=[dict(LARGE, max_routes=1), dict(CAR, max_routes=2)]),
        "at most one vehicle type may set max_routes",
    ),
    (
        "quota_on_minimized_type",
        _payload(vehicle_types=[dict(LARGE), dict(CAR, max_routes=2)]),
        "max_routes cannot be set on the minimized type",
    ),
    ("sw_capacity_mismatch", _payload(sw_capacity=3), "sw_capacity must equal"),
    ("so_capacity_mismatch", _payload(so_capacity=9), "so_capacity must equal"),
    ("uppercase_type_id", _payload(vehicle_types=[dict(LARGE, type_id="Large")], minimize_type="Large"), "type_id"),
    (
        "too_many_types",
        _payload(
            vehicle_types=[dict(LARGE, type_id=f"t{i}") for i in range(5)], minimize_type="t0"
        ),
        "vehicle_types",
    ),
    ("empty_types", _payload(vehicle_types=[], minimize_type=None), "vehicle_types"),
    ("zero_capacity_type", _payload(vehicle_types=[dict(LARGE, sw_capacity=0, so_capacity=0)], minimize_type="large"), "capacity"),
    ("negative_capacity", _payload(vehicle_types=[dict(LARGE, so_capacity=-1)], minimize_type="large"), "so_capacity"),
    ("type_ride_zero", _payload(vehicle_types=[dict(LARGE, max_ride_time=0), dict(CAR)]), "max_ride_time"),
    ("type_ride_over_600", _payload(vehicle_types=[dict(LARGE, max_ride_time=601), dict(CAR)]), "max_ride_time"),
    ("negative_quota", _payload(vehicle_types=[dict(LARGE, max_routes=-1), dict(CAR)]), "max_routes"),
    (
        "type_ride_above_request_limit",
        _payload(max_ride_time=40, vehicle_types=[dict(LARGE, max_ride_time=41), dict(CAR)]),
        "max_ride_time cannot exceed",
    ),
    (
        "type_travel_above_request_limit",
        _payload(max_travel_time=100, vehicle_types=[dict(LARGE, max_travel_time=101), dict(CAR)]),
        "max_travel_time cannot exceed",
    ),
    ("total_capacity_zero", _payload(vehicle_types=[dict(LARGE, total_capacity=0), dict(CAR)]), "total_capacity"),
    ("total_capacity_negative", _payload(vehicle_types=[dict(LARGE, total_capacity=-2), dict(CAR)]), "total_capacity"),
    (
        "total_capacity_above_pools",
        _payload(vehicle_types=[dict(LARGE), dict(CAR, total_capacity=5)]),
        "total_capacity must be <=",
    ),
    ("quota_over_policy_ceiling", _payload(vehicle_types=[dict(LARGE, max_routes=51), dict(CAR)]), "max_routes cannot exceed"),
]


@pytest.mark.parametrize("case_id,payload,message", REJECTED, ids=[c[0] for c in REJECTED])
def test_invalid_heterogeneous_requests_are_rejected(case_id, payload, message):
    with pytest.raises(ValidationError) as excinfo:
        OptimizationRequest(**payload)
    assert message in str(excinfo.value)


def _client(monkeypatch):
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")
    app = FastAPI()
    app.include_router(optimization.router)
    return TestClient(app)


@pytest.mark.parametrize("case_id,payload,message", REJECTED, ids=[c[0] for c in REJECTED])
def test_invalid_heterogeneous_requests_are_http_422(monkeypatch, case_id, payload, message):
    response = _client(monkeypatch).post("/api/v1/optimize", json=payload)
    assert response.status_code == 422


def _client_for_get(monkeypatch):
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")
    from routers import strategies as strategies_router

    app = FastAPI()
    app.include_router(strategies_router.router)
    return TestClient(app)


def test_ga_split_hf_is_rejected_by_compare_with_422(monkeypatch):
    body = {"students": [], "depot": {"id": "D", "lat": 0.0, "lng": 0.0}, "algorithms": ["ga_split_hf"]}
    response = _client(monkeypatch).post("/api/v1/compare", json=body)
    assert response.status_code == 422
    assert "ga_split_hf" in response.text


def test_type_limits_equal_to_request_limits_are_accepted():
    request = OptimizationRequest(**_payload(
        max_ride_time=40, max_travel_time=100,
        vehicle_types=[dict(LARGE, max_ride_time=40, max_travel_time=100), dict(CAR, max_ride_time=30)],
    ))
    assert request.vehicle_types[1].max_ride_time == 30


def test_ga_split_hf_is_hidden_from_discovery_lists(monkeypatch):
    from routers import benchmark
    from strategies import get_strategy_info, STRATEGY_FACTORIES

    assert "ga_split_hf" in STRATEGY_FACTORIES  # still executable via /optimize
    assert "ga_split_hf" not in {s["name"] for s in get_strategy_info()}
    assert "ga_split_hf" not in benchmark._strategy_param_spaces()
    reply = _client_for_get(monkeypatch).get("/api/v1/strategies")
    assert reply.status_code == 200
    assert "ga_split_hf" not in {s["name"] for s in reply.json()}


def test_ga_split_hf_strategy_without_vehicle_types_fails_closed():
    from strategies import get_strategy

    request = OptimizationRequest(
        algorithm="ga_split", students=[], depot={"id": "D", "lat": 0.0, "lng": 0.0}
    )
    with pytest.raises(ValueError, match="requires vehicle_types"):
        get_strategy("ga_split_hf").optimize(request)


def test_valid_typed_request_accepted_and_defaults():
    request = OptimizationRequest(**_payload())
    assert (request.sw_capacity, request.so_capacity) == (4, 5)  # max over the types
    assert request.minimize_type == "car"
    explicit = OptimizationRequest(**_payload(sw_capacity=4, so_capacity=5))
    assert explicit.vehicle_types[0].type_id == "large"
    single = OptimizationRequest(**_payload(vehicle_types=[dict(LARGE, max_routes=3)], minimize_type=None))
    assert single.minimize_type == "large"  # single type: unambiguous


def test_requests_without_new_fields_are_unchanged():
    request = OptimizationRequest(
        algorithm="ga_split", students=[], depot={"id": "D", "lat": 0.0, "lng": 0.0}
    )
    assert request.vehicle_types is None and request.minimize_type is None
    assert (request.sw_capacity, request.so_capacity) == (4, 5)


# ---------------------------------------------------------------------------
# Typed certificate
# ---------------------------------------------------------------------------


def _student(sid, loc, kind):
    return StudentNode(
        id=sid, location_code=loc, disability_type=kind, coordinates={"lat": 0.0, "lng": 0.0}
    )


def _route(stops, vehicle_type, sw, so, step=2.0, ids=None):
    chain = [DEPOT_ID, *stops, DEPOT_ID]
    steps = [
        RouteStep(location1=a, location2=b, duration=step) for a, b in zip(chain, chain[1:])
    ]
    return VehicleRoute(
        vehicle_id=f"{vehicle_type or 'x'}-{'-'.join(stops)}",
        route_details=steps,
        total_duration_minutes=step * len(steps),
        sw_count=sw,
        so_count=so,
        student_ids=ids or list(stops),
        vehicle_type=vehicle_type,
    )


def _typed_request(students_, types=None, **overrides):
    values = dict(
        algorithm="ga_split_hf",
        students=students_,
        depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0),
        vehicle_types=types or [dict(LARGE), dict(CAR)],
        minimize_type="car",
    )
    values.update(overrides)
    return OptimizationRequest(**values)


def _response(routes, fleet_mix, success=True):
    return OptimizationResponse(
        algorithm_used="ga_split_hf",
        success=success,
        routes=routes,
        total_vehicles=len(routes),
        total_duration_minutes=sum(r.total_duration_minutes for r in routes),
        fleet_mix=fleet_mix,
    )


def _certify(request, response, lookup=None):
    return certify_optimization_response(
        request, response, arc_lookup=lookup or echo_arc_lookup(request, response)
    )


def _types(certificate):
    return {v["type"] for v in certificate["violations"]}


SW1 = _student("a", "A", "Sw")
SO = [_student(f"b{i}", f"B{i}", "So") for i in range(1, 7)]


def test_typed_certificate_accepts_valid_mixed_fleet():
    request = _typed_request([SW1, SO[0], SO[1]])
    response = _response(
        [_route(["A"], "large", 1, 0), _route(["B1", "B2"], "car", 0, 2, ids=["b1", "b2"])],
        {"large": 1, "car": 1},
    )
    certificate = _certify(request, response)
    assert certificate["is_feasible"], certificate


def test_sw_passenger_on_car_route_is_rejected():
    request = _typed_request([SW1, SO[0]])
    response = _response(
        [_route(["A", "B1"], "car", 1, 1, ids=["a", "b1"])], {"car": 1}
    )
    certificate = _certify(request, response)
    assert not certificate["is_feasible"]
    assert "typed_capacity_violation" in _types(certificate)
    assert any("Sw load 1" in v["details"] for v in certificate["violations"])


def test_car_route_over_so_capacity_is_rejected():
    five = SO[:5]
    request = _typed_request(five)
    response = _response(
        [_route([s.location_code for s in five], "car", 0, 5, ids=[s.id for s in five])],
        {"car": 1},
    )
    certificate = _certify(request, response)
    assert "typed_capacity_violation" in _types(certificate)
    # the same load fits a large minibus (5 So)
    ok = _response(
        [_route([s.location_code for s in five], "large", 0, 5, ids=[s.id for s in five])],
        {"large": 1},
    )
    assert _certify(request, ok)["is_feasible"]


def test_total_capacity_violation_is_a_typed_capacity_violation():
    students_ = [SW1, SO[0], SO[1]]
    response = _response(
        [_route(["A", "B1", "B2"], "large", 1, 2, ids=["a", "b1", "b2"])], {"large": 1}
    )
    capped = _typed_request(students_, [dict(LARGE, total_capacity=2), dict(CAR)])
    certificate = _certify(capped, response)
    assert "typed_capacity_violation" in _types(certificate)
    assert any("total load 3" in v["details"] for v in certificate["violations"])
    # no cap: pools only, same response certifies as before
    assert _certify(_typed_request(students_), response)["is_feasible"]


def test_missing_or_unknown_vehicle_type_is_rejected_never_defaulted():
    request = _typed_request([SO[0]])
    for label in (None, "van"):
        response = _response([_route(["B1"], label, 0, 1, ids=["b1"])], {"large": 1})
        certificate = _certify(request, response)
        assert "vehicle_type_unknown" in _types(certificate), label
        assert not certificate["is_feasible"]


def test_type_quota_violation():
    request = _typed_request(
        [SO[0], SO[1]],
        types=[dict(LARGE, max_routes=1), dict(CAR)],
    )
    response = _response(
        [_route(["B1"], "large", 0, 1, ids=["b1"]), _route(["B2"], "large", 0, 1, ids=["b2"])],
        {"large": 2},
    )
    certificate = _certify(request, response)
    assert "type_quota_violation" in _types(certificate)


def test_per_type_ride_and_tour_limits_use_the_type_not_the_request():
    # 3 stops, 4 arcs of 5 min: pickup ride = 15, tour = 20.
    stops = ["B1", "B2", "B3"]
    ids = ["b1", "b2", "b3"]
    request = _typed_request(
        SO[:3],
        types=[dict(LARGE), dict(CAR, max_ride_time=10, max_travel_time=18)],
        max_ride_time=60,
        max_travel_time=120,
    )
    on_car = _response([_route(stops, "car", 0, 3, step=5.0, ids=ids)], {"car": 1})
    certificate = _certify(request, on_car)
    assert {"ride_time_violation", "duration_violation"} <= _types(certificate)
    on_large = _response([_route(stops, "large", 0, 3, step=5.0, ids=ids)], {"large": 1})
    assert _certify(request, on_large)["is_feasible"]


def test_typed_recost_stays_on_the_authoritative_matrix():
    request = _typed_request([SO[0]])
    response = _response([_route(["B1"], "car", 0, 1, step=1.0, ids=["b1"])], {"car": 1})

    def lookup(origin, destination):
        return 0.0 if origin == destination else 30.0  # matrix says 30, response says 1

    certificate = _certify(request, response, lookup)
    assert "arc_duration_mismatch" in _types(certificate)
    assert not certificate["is_feasible"]


def test_typed_matrix_durations_not_reported_ones_drive_limits():
    # response claims 1 min arcs, matrix has 30: tour 60 > car limit 40
    request = _typed_request(
        [SO[0]], types=[dict(LARGE), dict(CAR, max_travel_time=40)]
    )
    response = _response([_route(["B1"], "car", 0, 1, step=1.0, ids=["b1"])], {"car": 1})
    certificate = _certify(request, response, lambda o, d: 0.0 if o == d else 30.0)
    assert "duration_violation" in _types(certificate)


def test_fleet_mix_must_match_route_labels():
    request = _typed_request([SO[0]])
    for mix in (None, {"large": 1}, {"car": 2}):
        response = _response([_route(["B1"], "car", 0, 1, ids=["b1"])], mix)
        assert "fleet_mix_mismatch" in _types(_certify(request, response)), mix
    good = _response([_route(["B1"], "car", 0, 1, ids=["b1"])], {"car": 1, "large": 0})
    assert _certify(request, good)["is_feasible"]


def test_single_type_certification_ignores_vehicle_type_labels():
    """No vehicle_types in the request: global caps rule, labels are inert."""
    request = OptimizationRequest(
        algorithm="ga_split",
        students=[SW1, SO[0]],
        depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0),
        sw_capacity=4,
        so_capacity=5,
    )
    response = OptimizationResponse(
        algorithm_used="ga_split",
        success=True,
        routes=[_route(["A", "B1"], "car", 1, 1, ids=["a", "b1"])],
        total_vehicles=1,
        total_duration_minutes=6.0,
    )
    assert _certify(request, response)["is_feasible"]
    over = OptimizationRequest(
        algorithm="ga_split",
        students=[SW1, SO[0]],
        depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0),
        sw_capacity=0,
        so_capacity=5,
    )
    assert "capacity_violation" in _types(_certify(over, response))


# ---------------------------------------------------------------------------
# End to end through /optimize with a fake matrix
# ---------------------------------------------------------------------------


def _hf_request(n_sw, n_so, quota, **overrides):
    types = [dict(LARGE, max_routes=quota), dict(CAR)]
    values = dict(
        algorithm="ga_split_hf",
        students=students(n_sw, n_so),
        depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0),
        vehicle_types=types,
        minimize_type="car",
        max_travel_time=120,
        max_ride_time=60,
        direction="pickup",
        is_asymmetric=True,
        ga_config={"population_size": 20, "max_iterations": 15, "seed": 7},
    )
    values.update(overrides)
    return OptimizationRequest(**values)


def test_ga_split_hf_end_to_end_quota_one_needs_one_car(monkeypatch):
    install_loader(monkeypatch, "ga_split_hf", star_arcs(10))
    response = optimization.optimize_route(_hf_request(3, 7, quota=1))
    assert response.success, response.error_message
    assert response.algorithm_used == "ga_split_hf"
    assert response.feasibility_certificate.is_feasible
    assert response.fleet_mix == {"large": 1, "car": 1}
    by_type = {r.vehicle_type: r for r in response.routes}
    assert by_type["large"].sw_count == 3 and by_type["large"].so_count == 5
    assert by_type["car"].sw_count == 0 and by_type["car"].so_count == 2
    dumped = json.loads(response.model_dump_json())
    assert all(r["vehicle_type"] in {"large", "car"} for r in dumped["routes"])


def test_ga_split_hf_quota_two_needs_no_cars_and_is_deterministic(monkeypatch):
    install_loader(monkeypatch, "ga_split_hf", star_arcs(10))
    first = optimization.optimize_route(_hf_request(3, 7, quota=2))
    second = optimization.optimize_route(_hf_request(3, 7, quota=2))
    assert first.success and first.fleet_mix == {"large": 2, "car": 0}
    a, b = (json.loads(r.model_dump_json()) for r in (first, second))
    a["execution_time_seconds"] = b["execution_time_seconds"] = 0.0
    assert a == b


def test_ga_split_hf_quota_zero_with_sw_is_reported_infeasible(monkeypatch):
    install_loader(monkeypatch, "ga_split_hf", star_arcs(10))
    response = optimization.optimize_route(_hf_request(3, 7, quota=0))
    assert not response.success
    assert response.routes == []
    assert not response.feasibility_certificate.is_feasible


# ---------------------------------------------------------------------------
# P6: default responses are byte-identical to the base commit
# ---------------------------------------------------------------------------


def test_p6_default_ga_split_response_is_identical_to_base_golden(monkeypatch):
    produced = run_default_scenario(monkeypatch)
    assert "vehicle_type" not in produced and "fleet_mix" not in produced
    assert produced + "\n" == GOLDEN.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_new_fields_are_absent_from_http_json_when_unset(monkeypatch):
    """Through FastAPI's own serialisation: no null vehicle_type / fleet_mix keys."""
    from certifier_matrix_support import _skip_arc_capture

    _skip_arc_capture(monkeypatch)

    class _Stub:
        name = "genetic_algorithm"

        def optimize(self, request):
            return OptimizationResponse(
                algorithm_used="genetic_algorithm",
                success=True,
                routes=[_route(["B1"], None, 0, 1, ids=["b1"])],
                total_vehicles=1,
                total_duration_minutes=4.0,
            )

    class _Resolution:
        requested = "ga"
        canonical = "genetic_algorithm"

        def create(self):
            return _Stub()

    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: _Resolution())
    monkeypatch.setattr(
        optimization,
        "certify_optimization_response",
        lambda request, response, arc_lookup=None: {
            "is_feasible": True, "violation_count": 0, "violations": [],
        },
    )
    body = {
        "algorithm": "ga",
        "students": [
            {"id": "b1", "location_code": "B1", "disability_type": "So",
             "coordinates": {"lat": 0.0, "lng": 0.0}}
        ],
        "depot": {"id": DEPOT_ID, "lat": 0.0, "lng": 0.0},
    }
    reply = _client(monkeypatch).post("/api/v1/optimize", json=body)
    assert reply.status_code == 200, reply.text
    document = reply.json()
    assert "fleet_mix" not in document
    assert all("vehicle_type" not in route for route in document["routes"])
