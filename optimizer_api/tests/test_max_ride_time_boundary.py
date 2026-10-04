"""Production boundary tests for the per-student ``max_ride_time`` constraint.

Owner decision 2026-10-04.  Route = DEPOT -> s1 .. sk -> DEPOT.

* pickup  : a student's ride = travel from that student's stop to the campus
            (closing arc included); the longest is the first student's.
* dropoff : a student's ride = travel from the campus to that student's stop;
            the longest is the last student's.

The certifier is the safety net for every strategy: a strategy that ignores
the field must be rejected (``success=False``) when it violates it.
"""

import sys

import pytest

from models.schemas import (
    CompareRequest,
    LocationNode,
    OptimizationRequest,
    StudentNode,
    VehicleRoute,
)
from routers import optimization
from verification.response_certifier import certify_optimization_response

from test_production_feasibility_boundary import (
    _StubStrategy,
    _install_strategy,
    _response,
    _steps,
)

DEPOT_ID = "DEPOT"


def _student(sid, loc, disability="So"):
    return StudentNode(
        id=sid,
        location_code=loc,
        disability_type=disability,
        coordinates={"lat": 0.0, "lng": 0.0},
        pickup_time="08:30",
        dropoff_time="17:00",
    )


def _students(count):
    return [_student(f"s{i}", f"L{i}") for i in range(1, count + 1)]


def _request(count=3, **overrides):
    base = dict(
        algorithm="ga_split",
        students=_students(count),
        depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0),
        sw_capacity=4,
        so_capacity=10,
        max_travel_time=120,
        direction="pickup",
        is_asymmetric=True,
        ga_config={"population_size": 20, "max_iterations": 15, "seed": 7},
    )
    base.update(overrides)
    if base["algorithm"] != "ga_split":
        base["ga_config"] = None  # tunables only apply to their own strategy
    return OptimizationRequest(**base)


class _ArcLoader:
    """DataLoader stand-in serving an explicit directed arc table."""

    def __init__(self, arcs):
        self._arcs = arcs

    def get_submatrix(self, locations, **_kwargs):
        return [
            [0.0 if a == b else float(self._arcs[(a, b)]) for b in locations]
            for a in locations
        ]


def _install_loader(monkeypatch, arcs):
    strategy = optimization.resolve_strategy("ga_split").create()
    module = sys.modules[type(strategy).__module__]
    monkeypatch.setattr(
        module.DataLoader, "get_instance", staticmethod(lambda: _ArcLoader(arcs))
    )


def _star_arcs(count, out_arc=12.0, in_arc=10.0, between=15.0):
    """DEPOT->x = out_arc, x->DEPOT = in_arc, x->y = between (all directed)."""
    nodes = [f"L{i}" for i in range(1, count + 1)]
    arcs = {}
    for x in nodes:
        arcs[(DEPOT_ID, x)] = out_arc
        arcs[(x, DEPOT_ID)] = in_arc
        for y in nodes:
            if x != y:
                arcs[(x, y)] = between
    return arcs


def _route_rides(route, direction):
    """Per-route longest ride from the response's own step durations."""
    durations = [step.duration for step in route.route_details]
    if direction == "pickup":
        return sum(durations[1:])
    return sum(durations[:-1])


def _longest_ride(response, direction):
    return max(_route_rides(route, direction) for route in response.routes)


def _violation_types(response):
    return {v.type for v in response.feasibility_certificate.violations}


# -- ga_split honours the limit end to end -------------------------------------


@pytest.mark.parametrize(
    "direction,limit,expected_routes",
    [
        # pickup: ride = 10 + 15*(k-1)   dropoff: ride = 12 + 15*(k-1), 5 stops
        ("pickup", None, 1),
        ("pickup", 100, 1),
        ("pickup", 40, 2),
        ("pickup", 25, 3),
        ("pickup", 10, 5),
        ("dropoff", None, 1),
        ("dropoff", 100, 1),
        ("dropoff", 40, 3),
        ("dropoff", 25, 5),
    ],
)
def test_ga_split_route_count_grows_as_limit_tightens(
    monkeypatch, direction, limit, expected_routes
):
    _install_loader(monkeypatch, _star_arcs(5))

    result = optimization.optimize_route(
        _request(5, direction=direction, max_ride_time=limit)
    )

    assert result.success is True, result.error_message
    assert result.feasibility_certificate.is_feasible is True
    assert len(result.routes) == expected_routes
    if limit is not None:
        assert _longest_ride(result, direction) <= limit


def test_ga_split_dropoff_infeasible_single_student_limit(monkeypatch):
    # limit 10 < direct DEPOT->stop arc (12): no split can satisfy it
    _install_loader(monkeypatch, _star_arcs(3))

    result = optimization.optimize_route(
        _request(3, direction="dropoff", max_ride_time=10)
    )

    assert result.success is False
    assert "ride_time_violation" in _violation_types(result)
    assert "ride_time_violation" in result.error_message


def test_ga_split_pickup_single_student_direct_ride_over_limit(monkeypatch):
    arcs = _star_arcs(1, out_arc=5.0, in_arc=50.0)

    _install_loader(monkeypatch, arcs)
    result = optimization.optimize_route(
        _request(1, direction="pickup", max_ride_time=30)
    )

    assert result.success is False  # unsuccessful, not a crash
    assert "ride_time_violation" in _violation_types(result)
    assert "ride_time_violation" in result.error_message
    assert "Optimization endpoint failed" not in (result.error_message or "")


def test_ga_split_single_student_exactly_at_limit_is_feasible(monkeypatch):
    _install_loader(monkeypatch, _star_arcs(1, out_arc=5.0, in_arc=30.0))

    result = optimization.optimize_route(
        _request(1, direction="pickup", max_ride_time=30)
    )

    assert result.success is True, result.error_message
    assert len(result.routes) == 1


def test_default_none_is_unchanged_by_the_field(monkeypatch):
    _install_loader(monkeypatch, _star_arcs(5))

    without = optimization.optimize_route(_request(5))
    explicit = optimization.optimize_route(_request(5, max_ride_time=None))

    assert without.success and explicit.success
    assert [r.student_ids for r in without.routes] == [r.student_ids for r in explicit.routes]
    assert without.total_duration_minutes == explicit.total_duration_minutes


# -- fail closed: strategies that ignore the field are rejected ------------------


def _single_route(durations, students):
    steps = _steps(*[s.location_code for s in students], durations=durations)
    return VehicleRoute(
        vehicle_id="V1",
        route_details=steps,
        total_duration_minutes=sum(step.duration for step in steps),
        sw_count=0,
        so_count=len(students),
        student_ids=[s.id for s in students],
    )


# DEPOT->L1 5, L1->L2 10, L2->L3 10, L3->DEPOT 20:
#   pickup rides  L1=40 L2=30 L3=20 (longest 40) / dropoff L1=5 L2=15 L3=25
DURATIONS = [5.0, 10.0, 10.0, 20.0]


@pytest.mark.parametrize(
    "direction,limit,feasible",
    [
        ("pickup", 40, True),
        ("pickup", 39, False),
        ("dropoff", 25, True),
        ("dropoff", 24, False),
    ],
)
def test_ignoring_strategy_is_rejected_when_it_violates(
    monkeypatch, direction, limit, feasible
):
    students = _students(3)
    _install_strategy(
        monkeypatch,
        "stub",
        _StubStrategy(
            lambda req: _response(
                routes=[_single_route(DURATIONS, students)], direction=direction
            )
        ),
    )

    result = optimization.optimize_route(
        _request(3, algorithm="stub", direction=direction, max_ride_time=limit)
    )

    assert result.success is feasible, result.error_message
    if not feasible:
        assert "ride_time_violation" in _violation_types(result)
        assert "ride_time_violation" in result.error_message


def test_ignoring_strategy_without_limit_is_unaffected(monkeypatch):
    students = _students(3)
    _install_strategy(
        monkeypatch,
        "stub",
        _StubStrategy(lambda req: _response(routes=[_single_route(DURATIONS, students)])),
    )

    result = optimization.optimize_route(_request(3, algorithm="stub"))

    assert result.success is True


def test_certifier_checks_ride_time_per_direction():
    students = _students(3)
    response = _response(routes=[_single_route(DURATIONS, students)])

    pickup = certify_optimization_response(
        _request(3, algorithm="stub", direction="pickup", max_ride_time=39), response
    )
    dropoff = certify_optimization_response(
        _request(3, algorithm="stub", direction="dropoff", max_ride_time=39), response
    )

    assert pickup["is_feasible"] is False
    # a success=True response with violations also gets the generic hard_violation
    assert {v["type"] for v in pickup["violations"]} == {
        "ride_time_violation",
        "hard_violation",
    }
    assert dropoff["is_feasible"] is True


# -- schema ------------------------------------------------------------------


def test_max_ride_time_defaults_to_none_and_validates_range():
    assert _request(1).max_ride_time is None
    assert _request(1, max_ride_time=1).max_ride_time == 1
    assert _request(1, max_ride_time=600).max_ride_time == 600
    for bad in (0, -5, 601):
        with pytest.raises(ValueError):
            _request(1, max_ride_time=bad)


def test_compare_request_carries_max_ride_time_to_each_algorithm():
    compare = CompareRequest(
        students=_students(2),
        depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0),
        max_ride_time=45,
    )
    assert compare.max_ride_time == 45
    forwarded = optimization._compare_optimization_request(compare, "ga_split")
    assert forwarded.max_ride_time == 45
    assert CompareRequest(
        students=_students(2), depot=LocationNode(id=DEPOT_ID, lat=0.0, lng=0.0)
    ).max_ride_time is None
