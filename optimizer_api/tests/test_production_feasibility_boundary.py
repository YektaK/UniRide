"""Package A RED tests: universal final feasibility certificate at production boundaries.

Every hard-constraint violation must demote ``success`` to False at
``/optimize`` (``optimize_route``) and ``/compare`` (``_run_single_algorithm``).
The response shape of the certificate mirrors ``certify_benchmark_response``:

    {"is_feasible": bool, "violation_count": int, "violations": [...]}

These tests are written against the missing boundary (RED): they fail while
``success`` is passed through uncertified and pass once the certificate is
mandatory.
"""

import json

from types import SimpleNamespace

import pytest

from models.schemas import (
    AlgorithmResult,
    CompareRequest,
    LocationNode,
    OptimizationRequest,
    OptimizationResponse,
    RouteStep,
    StudentNode,
    VehicleConfig,
    VehicleRoute,
)
from routers import optimization
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.gwo_strategy import GreyWolfOptimizerStrategy
from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.permutation_tsp import PermutationTSPStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.two_opt_strategy import TwoOptStrategy
from strategies.holistic_response_builder import (
    build_indexed_step_routes_response,
    build_sequence_routes_response,
)
from strategies.sota_response_builder import build_single_route_response
from uniride_core.adapters.demand_builder import student_occurrence_keys
from uniride_core.algorithms.string_greedy_routing import solve_string_greedy_routes
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator
from verification import response_certifier
from verification.response_certifier import certify_optimization_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _student(student_id, loc, disability, pickup="08:30", dropoff="17:00"):
    return StudentNode(
        id=student_id,
        location_code=loc,
        disability_type=disability,
        coordinates={"lat": 0.0, "lng": 0.0},
        pickup_time=pickup,
        dropoff_time=dropoff,
    )


BASIC_STUDENTS = [
    _student("s1", "LocA", "So"),
    _student("s2", "LocB", "Sw"),
    _student("s3", "LocC", "So"),
]

DEPOT = LocationNode(id="DEPOT", lat=0.0, lng=0.0)


def _request(students=None, **overrides):
    base = dict(
        algorithm="stub",
        students=students if students is not None else BASIC_STUDENTS,
        depot=DEPOT,
        sw_capacity=1,
        so_capacity=5,
        max_travel_time=120,
        direction="pickup",
    )
    base.update(overrides)
    return OptimizationRequest(**base)


def _steps(*nodes, durations=None):
    """Build depot-closed step chains: DEPOT -> each node -> DEPOT."""
    durations = durations or [10.0] * len(nodes)
    chain = ["DEPOT"] + list(nodes)
    steps = []
    for i in range(len(chain) - 1):
        steps.append(RouteStep(
            location1=chain[i],
            location2=chain[i + 1],
            duration=float(durations[i]),
            distance=0.0,
        ))
    steps.append(RouteStep(
        location1=chain[-1],
        location2="DEPOT",
        duration=float(durations[-1]) if len(durations) > len(nodes) else 5.0,
        distance=0.0,
    ))
    return steps


def _response(routes, success=True, **overrides):
    base = dict(
        algorithm_used="stub",
        success=success,
        routes=routes,
        total_vehicles=len(routes),
        total_duration_minutes=sum(r.total_duration_minutes for r in routes),
        execution_time_seconds=0.01,
        direction="pickup",
    )
    base.update(overrides)
    return OptimizationResponse(**base)


def _valid_route(students=None, durations=None):
    students = students if students is not None else BASIC_STUDENTS
    locations = [s.location_code for s in students]
    steps = _steps(*locations, durations=durations)
    return VehicleRoute(
        vehicle_id="V1",
        route_details=steps,
        total_duration_minutes=sum(step.duration for step in steps),
        sw_count=sum(1 for s in students if s.disability_type == "Sw"),
        so_count=sum(1 for s in students if s.disability_type == "So"),
        student_ids=[s.id for s in students],
    )


class _StubStrategy:
    """Registry stub producing a fixed response; returned fresh per call."""

    name = "stub"
    display_name = "Stub"
    description = "test stub"

    def __init__(self, response_factory):
        self._factory = response_factory

    def optimize(self, request):
        return self._factory(request)


def _install_strategy(monkeypatch, key, strategy):
    monkeypatch.setitem(optimization.STRATEGY_REGISTRY, key, strategy)


# ---------------------------------------------------------------------------
# Unit-level certificate tests (RED: symbol does not exist yet)
# ---------------------------------------------------------------------------

def test_certificate_accepts_valid_route():
    request = _request()
    response = _response(routes=[_valid_route()])

    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is True
    assert certificate["violation_count"] == 0


@pytest.mark.parametrize(
    "label,mutate",
    [
        ("capacity overflow", lambda r: _request(sw_capacity=0)),
        ("duration overflow", lambda r: _request(max_travel_time=10)),
        ("route not depot-closed", lambda r: r),
        ("open start", lambda r: r),
        ("unknown node", lambda r: r),
        ("duplicate visit", lambda r: r),
        ("missing occurrence", lambda r: r),
        ("negative arc", lambda r: r),
        ("non-finite arc", lambda r: r),
        ("broken chain", lambda r: r),
    ],
)
def test_certificate_rejects_hard_violations(label, mutate):
    request = mutate(_request())

    violations = {
        "capacity overflow": lambda req: _response(routes=[_route_with_capacity_overflow(req)]),
        "duration overflow": lambda req: _response(routes=[_route_with_duration_overflow(req)]),
        "route not depot-closed": lambda req: _response(routes=[_route_open_end(req)]),
        "open start": lambda req: _response(routes=[_route_open_start(req)]),
        "unknown node": lambda req: _response(routes=[_route_unknown_node(req)]),
        "duplicate visit": lambda req: _response(routes=[_route_duplicate_visit(req)]),
        "missing occurrence": lambda req: _response(routes=[_route_missing_occurrence(req)]),
        "negative arc": lambda req: _response(routes=[_route_negative_arc(req)]),
        "non-finite arc": lambda req: _response(routes=[_route_nonfinite_arc(req)]),
        "broken chain": lambda req: _response(routes=[_route_broken_chain(req)]),
    }
    response = violations[label](request)

    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is False, label
    assert certificate["violation_count"] >= 1, label


# --- mutation route builders (all must fail certification) ---

def _route_with_capacity_overflow(request):
    steps = _steps("LocA", "LocB")
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=1, student_ids=["s1", "s2"],
    )


def _route_with_duration_overflow(request):
    steps = _steps("LocA", "LocB", "LocC", durations=[60.0, 60.0, 60.0])
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=2, student_ids=["s1", "s2", "s3"],
    )


def _route_open_end(request):
    steps = [
        RouteStep(location1="DEPOT", location2="LocA", duration=10.0),
        RouteStep(location1="LocA", location2="LocB", duration=10.0),
        RouteStep(location1="LocB", location2="LocC", duration=10.0),
    ]
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=30.0, sw_count=1, so_count=2,
        student_ids=["s1", "s2", "s3"],
    )


def _route_open_start(request):
    steps = [
        RouteStep(location1="LocA", location2="LocB", duration=10.0),
        RouteStep(location1="LocB", location2="LocC", duration=10.0),
        RouteStep(location1="LocC", location2="DEPOT", duration=5.0),
    ]
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=25.0, sw_count=1, so_count=2,
        student_ids=["s1", "s2", "s3"],
    )


def _route_unknown_node(request):
    steps = _steps("LocA", "LocB", "ZZZ")
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=2, student_ids=["s1", "s2", "s3"],
    )


def _route_duplicate_visit(request):
    steps = _steps("LocA", "LocA", "LocB", "LocC")
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=2, student_ids=["s1", "s1", "s2", "s3"],
    )


def _route_missing_occurrence(request):
    steps = _steps("LocA", "LocB")
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=1, student_ids=["s1", "s2"],
    )


def _route_negative_arc(request):
    steps = _steps("LocA", "LocB", durations=[10.0, -5.0])
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=20.0, sw_count=1, so_count=1,
        student_ids=["s1", "s2"],
    )


def _route_nonfinite_arc(request):
    steps = _steps("LocA", "LocB", durations=[10.0, float("inf")])
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=20.0, sw_count=1, so_count=1,
        student_ids=["s1", "s2"],
    )


def _route_broken_chain(request):
    steps = [
        RouteStep(location1="DEPOT", location2="LocA", duration=10.0),
        RouteStep(location1="LocB", location2="LocC", duration=10.0),
        RouteStep(location1="LocC", location2="DEPOT", duration=5.0),
    ]
    return VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=25.0, sw_count=1, so_count=2,
        student_ids=["s1", "s2", "s3"],
    )


# ---------------------------------------------------------------------------
# /optimize boundary (RED: currently passes success through uncertified)
# ---------------------------------------------------------------------------

def test_optimize_demotes_capacity_violation(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_route_with_capacity_overflow(req)])
    ))

    result = optimization.optimize_route(_request(sw_capacity=0))

    assert result.success is False
    assert result.error_message is not None
    assert "capacity_violation" in result.error_message


def test_optimize_demotes_duration_violation(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_route_with_duration_overflow(req)])
    ))

    result = optimization.optimize_route(_request(max_travel_time=100))

    assert result.success is False
    assert result.error_message is not None
    assert "duration_violation" in result.error_message


def test_optimize_demotes_missing_occurrence(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_route_missing_occurrence(req)])
    ))

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert result.error_message is not None
    assert "occurrence_coverage" in result.error_message


def test_optimize_demotes_duplicate_visit(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_route_duplicate_visit(req)])
    ))

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert "occurrence_coverage" in result.error_message


def test_optimize_demotes_unknown_node(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_route_unknown_node(req)])
    ))

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert result.error_message is not None


def test_optimize_demotes_open_and_broken_routes(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_route_open_end(req)])
    ))

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert result.error_message is not None


def test_optimize_demotes_negative_and_nonfinite_arcs(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_route_nonfinite_arc(req)])
    ))

    result = optimization.optimize_route(_request())

    assert result.success is False
    assert result.error_message is not None


def test_optimize_keeps_valid_response_success(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[_valid_route(req.students)])
    ))

    result = optimization.optimize_route(_request())

    assert result.success is True
    assert result.error_message is None


def test_optimize_demotes_time_window_violation(monkeypatch):
    def late_response(req):
        route = _valid_route(req.students, durations=[200.0, 200.0, 200.0])
        return _response(
            routes=[route],
            time_windows_used=True,
            total_time_window_violations=1,
        )

    _install_strategy(monkeypatch, "stub", _StubStrategy(late_response))
    request = _request(use_time_windows=True, target_time="08:30", max_travel_time=700)

    result = optimization.optimize_route(request)

    assert result.success is False
    assert result.error_message is not None
    assert "time_window_violation" in result.error_message


# ---------------------------------------------------------------------------
# /compare boundary (RED: currently wraps success without certification)
# ---------------------------------------------------------------------------

def test_compare_demotes_infeasible_strategy_keeps_feasible(monkeypatch):
    _install_strategy(monkeypatch, "good", _StubStrategy(
        lambda req: _response(routes=[_valid_route(req.students)])
    ))
    _install_strategy(monkeypatch, "bad", _StubStrategy(
        lambda req: _response(routes=[_route_missing_occurrence(req)])
    ))
    _install_strategy(monkeypatch, "evil", _StubStrategy(
        lambda req: _response(routes=[_route_nonfinite_arc(req)])
    ))

    response = optimization.compare_algorithms(
        CompareRequest(
            students=BASIC_STUDENTS,
            depot=DEPOT,
            sw_capacity=1,
            so_capacity=5,
            max_travel_time=120,
            algorithms=["good", "bad", "evil"],
        )
    )

    by_algorithm = {r.algorithm: r for r in response.results}
    assert by_algorithm["good"].success is True
    assert by_algorithm["bad"].success is False
    assert by_algorithm["evil"].success is False
    assert by_algorithm["bad"].error_message is not None
    assert "occurrence_coverage" in by_algorithm["bad"].error_message
    assert response.success is True
    assert response.best_algorithm == "good"


def test_compare_with_no_certified_success_has_no_ranked_algorithm(monkeypatch):
    _install_strategy(monkeypatch, "failed-one", _StubStrategy(
        lambda req: _response(routes=[_valid_route(req.students)], success=False)
    ))
    _install_strategy(monkeypatch, "failed-two", _StubStrategy(
        lambda req: _response(routes=[_valid_route(req.students)], success=False)
    ))

    response = optimization.compare_algorithms(
        CompareRequest(
            students=BASIC_STUDENTS,
            depot=DEPOT,
            sw_capacity=1,
            so_capacity=5,
            max_travel_time=120,
            algorithms=["failed-one", "failed-two"],
        )
    )

    assert response.success is False
    assert all(result.success is False for result in response.results)
    assert response.best_algorithm == ""
    assert response.fastest_algorithm == ""


def test_compare_all_infeasible_reports_failure(monkeypatch):
    _install_strategy(monkeypatch, "bad1", _StubStrategy(
        lambda req: _response(routes=[_route_missing_occurrence(req)])
    ))
    _install_strategy(monkeypatch, "bad2", _StubStrategy(
        lambda req: _response(routes=[_route_with_duration_overflow(req)])
    ))

    response = optimization.compare_algorithms(
        CompareRequest(
            students=BASIC_STUDENTS,
            depot=DEPOT,
            sw_capacity=1,
            so_capacity=5,
            max_travel_time=100,
            algorithms=["bad1", "bad2"],
        )
    )

    assert all(r.success is False for r in response.results)
    assert response.success is False


def test_compare_empty_students_still_succeeds(monkeypatch):
    _install_strategy(monkeypatch, "empty", _StubStrategy(
        lambda req: _response(routes=[], total_vehicles=0, total_duration_minutes=0.0)
    ))

    response = optimization.compare_algorithms(
        CompareRequest(students=[], depot=DEPOT, algorithms=["empty"])
    )

    assert response.results[0].success is True


# ---------------------------------------------------------------------------
# Follow-up RED section: heterogeneous fleet feasibility, response
# consistency, occurrence/output identity, fail-closed construction.
# ---------------------------------------------------------------------------

FLEET_STUDENTS = [
    _student("s1", "LocA", "So"),
    _student("s2", "LocB", "Sw"),
    _student("s3", "LocC", "Sw"),
    _student("s4", "LocD", "Sw"),
]

SAME_LOCATION_STUDENTS = [
    _student("s1", "LocA", "So"),
    _student("s2", "LocA", "Sw"),
]


def _cert_types(certificate):
    return {v["type"] for v in certificate["violations"]}


def _fleet_request(students, vehicles, **overrides):
    base = dict(students=students, so_capacity=5, max_travel_time=120)
    base.update(overrides)
    return _request(
        vehicles=[VehicleConfig(vehicle_id=v, sw_capacity=sw, so_capacity=so)
                  for v, sw, so in vehicles],
        **base
    )


# --- heterogeneous fleet feasibility (Scope 2) -------------------------------

def test_fleet_feasible_heterogeneous_matching_supersedes_global_caps():
    request = _fleet_request(
        FLEET_STUDENTS, [("V1", 1, 5), ("V2", 4, 5)], sw_capacity=2
    )
    routes = [
        _valid_route(students=[FLEET_STUDENTS[0]]),
        _valid_route(students=FLEET_STUDENTS[1:]),
    ]
    routes[0].vehicle_id = "Autobüs-X"
    routes[1].vehicle_id = "Araç-Y"

    certificate = certify_optimization_response(
        request, _response(routes=routes)
    )

    assert certificate["is_feasible"] is True
    assert certificate["violation_count"] == 0


def test_fleet_rejects_insufficient_vehicle_count():
    request = _fleet_request(FLEET_STUDENTS, [("V1", 4, 5)], sw_capacity=4)
    routes = [
        _valid_route(students=[FLEET_STUDENTS[0]]),
        _valid_route(students=FLEET_STUDENTS[1:]),
    ]

    certificate = certify_optimization_response(
        request, _response(routes=routes)
    )

    assert certificate["is_feasible"] is False
    assert "fleet_size_violation" in _cert_types(certificate)


def test_fleet_rejects_impossible_zero_sw_capacity_matching():
    sw_students = FLEET_STUDENTS[1:3]
    request = _fleet_request(
        sw_students, [("V1", 0, 5), ("V2", 0, 5)], sw_capacity=4
    )
    routes = [
        _valid_route(students=[sw_students[0]]),
        _valid_route(students=[sw_students[1]]),
    ]

    certificate = certify_optimization_response(
        request, _response(routes=routes)
    )

    assert certificate["is_feasible"] is False
    assert "fleet_capacity_violation" in _cert_types(certificate)


def test_optimize_demotes_insufficient_fleet(monkeypatch):
    _install_strategy(monkeypatch, "stub", _StubStrategy(
        lambda req: _response(routes=[
            _valid_route(students=[FLEET_STUDENTS[0]]),
            _valid_route(students=FLEET_STUDENTS[1:]),
        ])
    ))

    result = optimization.optimize_route(_fleet_request(
        FLEET_STUDENTS, [("V1", 4, 5)], sw_capacity=4
    ))

    assert result.success is False
    assert result.error_message is not None
    assert "fleet_size_violation" in result.error_message


# --- occurrence/output identity (Scope 4) ------------------------------------

def test_identity_accepts_same_location_distinct_students_ordered():
    request = _request(students=SAME_LOCATION_STUDENTS)
    keys = student_occurrence_keys(SAME_LOCATION_STUDENTS)
    steps = _steps(*keys)
    route = VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=1, student_ids=["s1", "s2"],
    )

    certificate = certify_optimization_response(
        request, _response(routes=[route])
    )

    assert certificate["is_feasible"] is True
    assert certificate["violation_count"] == 0


def test_identity_accepts_occurrence_keys_sota_style():
    request = _request(students=SAME_LOCATION_STUDENTS)
    keys = student_occurrence_keys(SAME_LOCATION_STUDENTS)
    steps = _steps(*keys)
    route = VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=1, student_ids=list(keys),
    )

    certificate = certify_optimization_response(
        request, _response(routes=[route])
    )

    assert certificate["is_feasible"] is True


@pytest.mark.parametrize(
    "bad_ids",
    [
        ["s2", "s1"],
        ["ghost", "s2"],
        ["s1"],
        ["s1", "s1"],
        ["s1", "unknown"],
    ],
)
def test_identity_rejects_swapped_unknown_missing_duplicated_ids(bad_ids):
    request = _request(students=SAME_LOCATION_STUDENTS)
    keys = student_occurrence_keys(SAME_LOCATION_STUDENTS)
    steps = _steps(*keys)
    route = VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=1, student_ids=bad_ids,
    )

    certificate = certify_optimization_response(
        request, _response(routes=[route])
    )

    assert certificate["is_feasible"] is False, bad_ids
    assert "student_id_mismatch" in _cert_types(certificate), bad_ids


# --- response consistency (Scope 3) ------------------------------------------

def test_route_total_mismatch_rejected():
    request = _request()
    route = _valid_route()
    route.total_duration_minutes = 999.0

    certificate = certify_optimization_response(
        request, _response(routes=[route])
    )

    assert certificate["is_feasible"] is False
    assert "route_duration_mismatch" in _cert_types(certificate)


def test_response_total_mismatch_rejected():
    request = _request()
    response = _response(routes=[_valid_route()])
    response.total_duration_minutes = 999.0

    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is False
    assert "response_duration_mismatch" in _cert_types(certificate)


def test_total_vehicles_mismatch_rejected():
    request = _request()
    response = _response(routes=[_valid_route()])
    response.total_vehicles = 2

    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is False
    assert "vehicle_count_mismatch" in _cert_types(certificate)


def test_certificate_rejects_interior_depot_without_fabricating_a_zero_arc():
    request = _request(students=BASIC_STUDENTS[:2], max_travel_time=40)
    steps = [
        RouteStep(location1="DEPOT", location2="LocA", duration=10.0),
        RouteStep(location1="LocA", location2="DEPOT", duration=10.0),
        RouteStep(location1="DEPOT", location2="LocB", duration=10.0),
        RouteStep(location1="LocB", location2="DEPOT", duration=10.0),
    ]
    route = VehicleRoute(
        vehicle_id="V1", route_details=steps, total_duration_minutes=40.0,
        sw_count=1, so_count=1, student_ids=["s1", "s2"],
    )

    certificate = certify_optimization_response(
        request, _response(routes=[route])
    )

    assert certificate["is_feasible"] is False
    assert certificate["violation_count"] == 1
    assert certificate["violations"] == [{
        "type": "route_continuity",
        "severity": "error",
        "details": "Route 0 contains an interior depot visit",
        "route_index": 0,
    }]


@pytest.mark.parametrize("reported", [3, "not-a-number", float("nan"), float("inf"), -1])
def test_certificate_rejects_reported_or_invalid_time_window_violations(reported):
    response = _response(routes=[_valid_route()])
    response.total_time_window_violations = reported

    certificate = certify_optimization_response(_request(), response)

    assert certificate["is_feasible"] is False
    violations = [
        violation for violation in certificate["violations"]
        if violation["type"] == "reported_time_window_violation"
    ]
    assert len(violations) == 1


@pytest.mark.parametrize("field,value", [("sw_count", 9), ("so_count", 9)])
def test_load_count_mismatch_rejected(field, value):
    request = _request()
    route = _valid_route()
    setattr(route, field, value)

    certificate = certify_optimization_response(
        request, _response(routes=[route])
    )

    assert certificate["is_feasible"] is False
    assert "load_count_mismatch" in _cert_types(certificate)


def test_compare_demotes_uncertified_aggregate_total(monkeypatch):
    def bogus_total(req):
        route = _valid_route(req.students)
        route.total_duration_minutes = 5.0
        response = _response(routes=[route])
        response.total_duration_minutes = 5.0
        return response

    _install_strategy(monkeypatch, "good", _StubStrategy(
        lambda req: _response(routes=[_valid_route(req.students)])
    ))
    _install_strategy(monkeypatch, "bogus", _StubStrategy(bogus_total))

    response = optimization.compare_algorithms(
        CompareRequest(
            students=BASIC_STUDENTS,
            depot=DEPOT,
            sw_capacity=1,
            so_capacity=5,
            max_travel_time=120,
            algorithms=["good", "bogus"],
        )
    )

    by_algorithm = {r.algorithm: r for r in response.results}
    assert by_algorithm["bogus"].success is False
    assert by_algorithm["good"].success is True
    assert response.best_algorithm == "good"


# --- fail-closed construction boundary (Scope 5) ------------------------------

def test_certify_fail_closed_on_construction_error(monkeypatch):
    def boom(students):
        raise RuntimeError("internal matrix construction failure")

    monkeypatch.setattr(response_certifier, "student_occurrence_keys", boom)

    certificate = certify_optimization_response(_request(), _response(routes=[_valid_route()]))

    assert isinstance(certificate, dict)
    assert certificate["is_feasible"] is False
    assert certificate["violation_count"] == 0
    assert "RuntimeError" in certificate["certify_error"]


# --- representative response-builder compatibility (Scope 7) ------------------

def test_builder_compat_holistic_sequence_routes():
    request = _request()
    plans = [
        SimpleNamespace(customer_indices=[0, 1], sw_count=1, so_count=1),
        SimpleNamespace(customer_indices=[2], sw_count=0, so_count=1),
    ]
    response = build_sequence_routes_response(
        request=request,
        route_plans=plans,
        duration_lookup=lambda origin, destination: 10.0,
        distance_lookup=lambda origin, destination: 0.0,
        algorithm_name="holistic-seq",
        vehicle_label="HOL",
        execution_time_seconds=0.1,
    )

    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is True, certificate
    assert certificate["violation_count"] == 0


def test_builder_compat_holistic_indexed_steps():
    request = _request()
    location_ids = [request.depot.id] + ["LocA", "LocB", "LocC"]
    plan = SimpleNamespace(
        steps=[
            SimpleNamespace(from_index=0, to_index=1, duration=10.0),
            SimpleNamespace(from_index=1, to_index=2, duration=10.0),
            SimpleNamespace(from_index=2, to_index=3, duration=10.0),
            SimpleNamespace(from_index=3, to_index=0, duration=10.0),
        ],
        vehicle_index=1,
        customer_indices=[0, 1, 2],
        sw_count=1,
        so_count=2,
        total_duration=40.0,
    )
    response = build_indexed_step_routes_response(
        request=request,
        route_plans=[plan],
        location_ids=location_ids,
        distance_lookup=lambda origin, destination: 0.0,
        algorithm_name="holistic-idx",
        vehicle_label="HOL",
        execution_time_seconds=0.1,
    )

    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is True, certificate
    assert certificate["violation_count"] == 0


def test_builder_compat_sota_single_route_with_key_ids():
    request = _request()
    response = build_single_route_response(
        algorithm_name="sota",
        vehicle_label="SOT",
        students=request.students,
        depot_id=request.depot.id,
        best_order=["LocA", "LocB", "LocC"],
        duration_lookup=lambda origin, destination: 10.0,
        distance_lookup=lambda origin, destination: 0.0,
        execution_time_seconds=0.1,
    )

    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is True, certificate
    assert certificate["violation_count"] == 0


def test_builder_compat_greedy_routes():
    request = _request()
    plans = solve_string_greedy_routes(
        customer_locations=["LocA", "LocB", "LocC"],
        disability_types={"LocA": "So", "LocB": "Sw", "LocC": "So"},
        depot_id=request.depot.id,
        duration_lookup=lambda origin, destination: 10.0,
        sw_capacity=4,
        so_capacity=5,
        max_route_duration=120,
    )
    student_by_key = {
        key: student
        for student, key in zip(request.students, student_occurrence_keys(request.students))
    }
    routes = [
        VehicleRoute(
            vehicle_id=f"Araç {idx} (Greedy)",
            route_details=[
                RouteStep(location1=step.location1, location2=step.location2,
                          duration=step.duration)
                for step in plan.steps
            ],
            total_duration_minutes=plan.total_duration,
            sw_count=plan.sw_count,
            so_count=plan.so_count,
            student_ids=[student_by_key[location].id for location in plan.student_locations],
        )
        for idx, plan in enumerate(plans, start=1)
    ]

    certificate = certify_optimization_response(
        request, _response(routes=routes)
    )

    assert certificate["is_feasible"] is True, certificate
    assert certificate["violation_count"] == 0


def test_builder_compat_split_family_mirror():
    request = _request()
    keys = student_occurrence_keys(request.students)
    steps = _steps(*keys)
    routes = [VehicleRoute(
        vehicle_id="Araç 1 (GA-Split)",
        route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=sum(1 for s in request.students if s.disability_type == "Sw"),
        so_count=sum(1 for s in request.students if s.disability_type == "So"),
        student_ids=[s.id for s in request.students],
    )]

    certificate = certify_optimization_response(
        request, _response(routes=routes)
    )

    assert certificate["is_feasible"] is True, certificate
    assert certificate["violation_count"] == 0


def test_builder_compat_cluster_first_single_student_clusters():
    request = _request(students=[FLEET_STUDENTS[0], FLEET_STUDENTS[1]])
    routes = [
        _valid_route(students=[FLEET_STUDENTS[0]]),
        _valid_route(students=[FLEET_STUDENTS[1]]),
    ]

    certificate = certify_optimization_response(
        request, _response(routes=routes)
    )

    assert certificate["is_feasible"] is True, certificate


def test_vehicle_calculator_normalizes_students_to_visit_order():
    """Shared root contract: VehicleCalculator must return cluster students in
    the optimized visit order so production builders emit positional ids."""
    students = [
        {"id": "S1", "location_code": "L1", "occurrence_key": "L1#S1",
         "coordinates": {"lat": 1.0, "lng": 1.0}, "disability_type": "Sw"},
        {"id": "S2", "location_code": "L1", "occurrence_key": "L1#S2",
         "coordinates": {"lat": 1.0, "lng": 1.0}, "disability_type": "So"},
        {"id": "S3", "location_code": "L2", "occurrence_key": "L2",
         "coordinates": {"lat": 5.0, "lng": 5.0}, "disability_type": "Sw"},
    ]

    def route_optimizer(location_codes):
        chain = ["L2", "L1#S2", "L1#S1"]
        steps = []
        current = "D"
        for loc in chain:
            steps.append({"location1": current, "location2": loc, "duration": 10.0})
            current = loc
        steps.append({"location1": current, "location2": "D", "duration": 10.0})
        return {"route_details": steps, "total_duration": 50.0}

    calc = VehicleCalculator(sw_capacity=10, so_capacity=10, max_tour_time=600)
    result = calc.calculate(students, route_optimizer)

    assignment = result["assignments"][0]
    assert [s["id"] for s in assignment["students"]] == ["S3", "S2", "S1"]


# --- follow-up blockers: co-located zero arcs, non-finite totals, sanitized errors

def test_zero_duration_arc_between_colocated_occurrences_is_valid():
    """A zero-duration arc between two distinct co-located occurrence nodes is
    legitimate travel (L1#s1 -> L1#s2); negative and non-finite arcs remain
    rejected."""
    request = _request(students=SAME_LOCATION_STUDENTS)
    keys = student_occurrence_keys(SAME_LOCATION_STUDENTS)
    steps = _steps(*keys, durations=[10.0, 0.0])

    route = VehicleRoute(
        vehicle_id="V1", route_details=steps,
        total_duration_minutes=sum(s.duration for s in steps),
        sw_count=1, so_count=1, student_ids=["s1", "s2"],
    )

    certificate = certify_optimization_response(
        request, _response(routes=[route])
    )

    assert certificate["is_feasible"] is True, certificate
    assert "missing_arc" not in _cert_types(certificate)


@pytest.mark.parametrize(
    "bad", [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "pos_inf", "neg_inf"],
)
def test_route_nonfinite_total_rejected(bad):
    route = _valid_route()
    route.total_duration_minutes = bad

    certificate = certify_optimization_response(
        _request(), _response(routes=[route])
    )

    assert certificate["is_feasible"] is False
    assert "non_finite_duration" in _cert_types(certificate)


@pytest.mark.parametrize(
    "bad", [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "pos_inf", "neg_inf"],
)
def test_response_nonfinite_total_rejected(bad):
    response = _response(routes=[_valid_route()])
    response.total_duration_minutes = bad

    certificate = certify_optimization_response(_request(), response)

    assert certificate["is_feasible"] is False
    assert "non_finite_duration" in _cert_types(certificate)


def test_both_nonfinite_route_and_response_totals_rejected():
    route = _valid_route()
    route.total_duration_minutes = float("nan")
    response = _response(routes=[route])
    response.total_duration_minutes = float("nan")

    certificate = certify_optimization_response(_request(), response)

    assert certificate["is_feasible"] is False
    assert "non_finite_duration" in _cert_types(certificate)


def test_certify_error_is_bounded_and_independent_of_exception_message(monkeypatch):
    def boom(students):
        raise RuntimeError("SECRET_MARKER_42\nsecond line\nthird line")

    monkeypatch.setattr(response_certifier, "student_occurrence_keys", boom)

    certificate = certify_optimization_response(
        _request(), _response(routes=[_valid_route()])
    )

    assert certificate["is_feasible"] is False
    certify_error = certificate["certify_error"]
    assert "SECRET_MARKER_42" not in certify_error
    assert "\n" not in certify_error
    assert len(certify_error) < 200


# --- live cluster-first strategy acceptance (blocker 1 + 2 + 6) ---------------

class _EuclideanLoader:
    """Coordinate-fallback submatrix mirroring the real DataLoader."""

    def get_submatrix(self, request_locations, coordinates=None, geo_coords=False, asymmetric_haversine=False):
        n = len(request_locations)
        coords = coordinates or {}
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            c1 = coords.get(request_locations[i], {})
            x1, y1 = c1.get("lat", 0.0), c1.get("lng", 0.0)
            for j in range(i + 1, n):
                c2 = coords.get(request_locations[j], {})
                x2, y2 = c2.get("lat", 0.0), c2.get("lng", 0.0)
                d = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                matrix[i][j] = d
                matrix[j][i] = d
        return matrix


def _live_request():
    return OptimizationRequest(
        algorithm="x",
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=[
            StudentNode(id="S1", location_code="L1",
                        coordinates={"lat": 1.0, "lng": 1.0}, disability_type="Sw"),
            StudentNode(id="S2", location_code="L1",
                        coordinates={"lat": 1.0, "lng": 1.0}, disability_type="So"),
            StudentNode(id="S3", location_code="L2",
                        coordinates={"lat": 5.0, "lng": 5.0}, disability_type="Sw"),
        ],
        sw_capacity=10,
        so_capacity=10,
        max_travel_time=600,
    )


def _patch_live_loader(monkeypatch):
    loader = _EuclideanLoader()
    monkeypatch.setattr("utils.data_loader.DataLoader.get_instance", lambda: loader)
    monkeypatch.setattr(
        "strategies.sota_response_builder.DataLoader.get_instance", lambda: loader
    )
    return loader


@pytest.mark.parametrize(
    "strategy",
    [
        GeneticAlgorithmStrategy({"seed": 7, "population_size": 4, "max_iterations": 3,
                                  "elite_count": 1, "max_no_improvement": 2, "tournament_size": 2}),
        PSOStrategy({"seed": 7, "swarm_size": 4, "max_iterations": 3, "max_velocity_size": 2}),
        GreyWolfOptimizerStrategy({"seed": 7, "population_size": 4, "max_iterations": 3,
                                   "max_no_improvement": 2}),
        HarrisHawksOptimizerStrategy({"seed": 7, "population_size": 4, "max_iterations": 3,
                                      "max_no_improvement": 2}),
        TwoOptStrategy({"seed": 7, "max_iterations": 200, "multi_start": False}),
        PermutationTSPStrategy(),
    ],
    ids=["ga", "pso", "gwo", "hho", "two_opt", "permutation"],
)
def test_live_cluster_first_strategy_output_certifies(monkeypatch, strategy):
    _patch_live_loader(monkeypatch)
    request = _live_request()
    response = strategy.optimize(request)

    assert response.success is True
    certificate = certify_optimization_response(request, response)

    assert certificate["is_feasible"] is True, (strategy.name, certificate)
    assert "student_id_mismatch" not in _cert_types(certificate)
    assert "missing_arc" not in _cert_types(certificate)

    by_key = {
        key: s.id for s, key in zip(request.students, student_occurrence_keys(request.students))
    }
    for route in response.routes:
        stops = [route.route_details[0].location1] + [step.location2 for step in route.route_details]
        expected = [by_key[k] for k in stops if k != request.depot.id]
        assert list(route.student_ids) == expected, (strategy.name, route.student_ids, expected)