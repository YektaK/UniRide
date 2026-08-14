"""Requested-algorithm policy: non-default explicitly-requested algorithms
must receive the identical mandatory feasibility certificate contract as the
six canonical defaults, on every production surface.

This is a confirmation suite, not a TDD RED suite: the certification gate is
already unconditional in the code (see REQUESTED_ALGORITHM_POLICY_VERIFICATION).
The load-bearing claim is expressed by the "infeasible success is demoted"
tests — if the certification line in the endpoint were removed (or stubbed
always-feasible), those tests would fail. This is distinct from the roadmap
"Mutation proof" item (closed at d3b19de), which proves solver success cannot
survive an injected hard violation; here we prove non-default *requested*
algorithm keys are admitted and pass through the same gate.
"""

from copy import deepcopy

import pytest

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
from strategies.canonical import resolve_strategy

# Non-default requested keys that are always available (not optional solvers).
REQUESTED_KEYS = [
    "hho_split",
    "gwo_split",
    "pso_split",
    "e2bso",
    "rdma",
    "paoea",
    "permutation_tsp",
]


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

    def get_location_coordinates(self, *args, **kwargs):
        return {
            "L1": {"lat": 1.0, "lng": 1.0},
            "L2": {"lat": 5.0, "lng": 5.0},
            "D": {"lat": 0.0, "lng": 0.0},
        }


def _patch_live_loader(monkeypatch):
    loader = _EuclideanLoader()
    monkeypatch.setattr("utils.data_loader.DataLoader.get_instance", lambda: loader)
    monkeypatch.setattr(
        "strategies.sota_response_builder.DataLoader.get_instance", lambda: loader
    )
    return loader


def _live_request(algorithm):
    return OptimizationRequest(
        algorithm=algorithm,
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=[
            StudentNode(
                id="S1",
                location_code="L1",
                coordinates={"lat": 1.0, "lng": 1.0},
                disability_type="Sw",
            ),
            StudentNode(
                id="S2",
                location_code="L1",
                coordinates={"lat": 1.0, "lng": 1.0},
                disability_type="So",
            ),
            StudentNode(
                id="S3",
                location_code="L2",
                coordinates={"lat": 5.0, "lng": 5.0},
                disability_type="Sw",
            ),
        ],
        sw_capacity=10,
        so_capacity=10,
        max_travel_time=600,
    )


def _chain_steps(*nodes):
    """Depot-closed step chain: DEPOT -> each node -> DEPOT."""
    chain = ["D"] + list(nodes)
    steps = [
        RouteStep(
            location1=chain[i],
            location2=chain[i + 1],
            duration=10.0,
            distance=0.0,
        )
        for i in range(len(chain) - 1)
    ]
    steps.append(RouteStep(location1=chain[-1], location2="D", duration=5.0, distance=0.0))
    return steps


def _route(*nodes, student_ids=None):
    return VehicleRoute(
        vehicle_id="V1",
        route_details=_chain_steps(*nodes),
        total_duration_minutes=float(sum(s.duration for s in _chain_steps(*nodes))),
        sw_count=1,
        so_count=0,
        student_ids=list(student_ids or [f"S{i}" for i in range(1, len(nodes) + 1)]),
    )


class _LyingStrategy:
    """Solver that claims success but returns an occurrence-incomplete route."""

    name = "stub"
    display_name = "Stub"
    description = "test stub"

    def optimize(self, request):
        # Covers only S1: S2 and S3 are missing -> hard coverage violation.
        return OptimizationResponse(
            algorithm_used=self.name,
            success=True,
            routes=[_route("S1", student_ids=["S1"])],
            total_vehicles=1,
            total_duration_minutes=15.0,
            execution_time_seconds=0.01,
            direction="pickup",
        )


def _install_strategy(monkeypatch, key, strategy):
    installed = getattr(optimization, "_test_strategies", None)
    if installed is None:
        installed = {}
        monkeypatch.setattr(optimization, "_test_strategies", installed, raising=False)
    installed[key] = strategy

    def resolve(requested):
        requested = requested.strip().lower()
        if requested not in installed:
            raise optimization.UnknownStrategyError(f"Unknown algorithm '{requested}'")
        template = installed[requested]

        def factory():
            instance = deepcopy(template)
            instance.name = requested
            return instance

        return optimization.ResolvedStrategy(requested, requested, factory, (requested,))

    def resolve_unique(keys):
        unique = {}
        for requested in keys:
            item = resolve(requested)
            previous = unique.get(item.canonical)
            if previous is None:
                unique[item.canonical] = item
        return list(unique.values())

    monkeypatch.setattr(optimization, "resolve_strategy", resolve)
    monkeypatch.setattr(optimization, "resolve_unique_strategies", resolve_unique)


# ---------------------------------------------------------------------------
# Baseline: a real non-default requested algorithm is admitted and certified.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", REQUESTED_KEYS)
def test_real_non_default_requested_algorithm_certifies(monkeypatch, key):
    """A real solve for a non-default requested key must be certified feasible
    at the endpoint. Proves the key is admitted and passes the same gate."""
    _patch_live_loader(monkeypatch)
    response = optimization.optimize_route(_live_request(key))
    assert response.success is True, (key, response.error_message)
    assert response.algorithm_requested == key, (key, response.algorithm_requested)
    assert response.algorithm_used == resolve_strategy(key).canonical, key
    assert response.feasibility_certificate.is_feasible is True, key


# ---------------------------------------------------------------------------
# Load-bearing: an infeasible success claim from a non-default requested
# algorithm is demoted. If the certification line were removed, success would
# remain True and these tests fail.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", REQUESTED_KEYS)
def test_non_default_requested_algorithm_infeasible_success_is_demoted(monkeypatch, key):
    _install_strategy(monkeypatch, key, _LyingStrategy())
    response = optimization.optimize_route(_live_request(key))
    assert response.success is False, key
    assert response.feasibility_certificate.is_feasible is False, key


@pytest.mark.parametrize("key", REQUESTED_KEYS)
def test_non_default_requested_algorithm_demoted_in_compare(monkeypatch, key):
    _install_strategy(monkeypatch, key, _LyingStrategy())
    request = CompareRequest(
        students=_live_request(key).students,
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        sw_capacity=10,
        so_capacity=10,
        max_travel_time=600,
        algorithms=[key],
    )
    response = optimization.compare_algorithms(request)
    result = next(r for r in response.results if r.algorithm == key)
    assert result.success is False, key
    assert result.feasibility_certificate.is_feasible is False, key


def test_certification_line_is_load_bearing(monkeypatch):
    """Stubbing the certificate always-feasible lets a lying non-default
    algorithm pass — proving the endpoint certification is the enforcement
    point (the 'remove the line' property of this confirmation suite)."""
    _install_strategy(monkeypatch, "rdma", _LyingStrategy())

    def always_feasible(request, response):
        return {
            "is_feasible": True,
            "violation_count": 0,
            "violations": [],
        }

    monkeypatch.setattr(optimization, "certify_optimization_response", always_feasible)
    response = optimization.optimize_route(_live_request("rdma"))
    assert response.success is True, "certification line is not the demotion gate"