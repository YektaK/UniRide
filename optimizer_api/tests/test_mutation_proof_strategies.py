"""Mutation-proof: real solver output at every canonical strategy surface.

For each canonical strategy, a REAL ``optimize()`` run must first certify
feasible (control), and every injected mutation of that successful output
must demote the final feasibility certificate to False. A mutation that
survives certification would mean a hard violation can ride a ``success``
claim to the caller.
"""

from copy import deepcopy

import pytest

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from strategies.canonical import resolve_strategy
from verification.response_certifier import certify_optimization_response

try:
    import ortools  # noqa: F401
except ImportError:  # pragma: no cover - CI without OR-Tools
    ortools = None

# ---------------------------------------------------------------------------
# Fixtures (mirror test_production_feasibility_boundary's live strategy tests)
# ---------------------------------------------------------------------------


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


def _live_request():
    return OptimizationRequest(
        algorithm="x",
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


def _cert_types(certificate):
    return {v.get("type") for v in certificate["violations"]}


# ---------------------------------------------------------------------------
# Mutations: each takes a certified-feasible response and breaks one fact.
# ---------------------------------------------------------------------------


def _drop_interior_step(response):
    route = response.routes[0]
    if len(route.route_details) < 2:
        pytest.skip("route too short for interior-step mutation")
    route.route_details.pop(1)
    return response


def _duplicate_step(response):
    route = response.routes[0]
    route.route_details.insert(1, deepcopy(route.route_details[0]))
    return response


def _bump_load(response):
    response.routes[0].sw_count += 10
    return response


def _dup_student(response):
    route = response.routes[0]
    route.student_ids.append(route.student_ids[-1])
    return response


MUTATIONS = {
    "drop_interior_step": _drop_interior_step,
    "duplicate_step": _duplicate_step,
    "bump_load": _bump_load,
    "dup_student": _dup_student,
}

# Every canonical strategy surface exposed through resolve_strategy.
# ortools_cvrp is gated on OR-Tools being importable (skip, not fail).
STRATEGY_KEYS = [
    "ga",
    "pso",
    "gwo",
    "hho",
    "ga_split",
    "pso_split",
    "gwo_split",
    "hho_split",
    "two_opt",
    "greedy",
    "permutation_tsp",
    "ortools_cvrp",
]


def _skip_if_unavailable(key):
    if key == "ortools_cvrp" and ortools is None:
        pytest.skip("OR-Tools is not installed")


@pytest.mark.parametrize("key", STRATEGY_KEYS)
def test_live_strategy_output_certifies(monkeypatch, key):
    """Control: unmutated real solver output must certify feasible."""
    _skip_if_unavailable(key)
    _patch_live_loader(monkeypatch)
    request = _live_request()
    response = resolve_strategy(key).create().optimize(request)

    assert response.success is True, (key, response)
    certificate = certify_optimization_response(request, response)
    assert certificate["is_feasible"] is True, (key, certificate)
    assert "student_id_mismatch" not in _cert_types(certificate)
    assert "missing_arc" not in _cert_types(certificate)


@pytest.mark.parametrize("key", STRATEGY_KEYS)
@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_strategy_mutation_never_survives(monkeypatch, key, mutation):
    """Every injected mutation of a successful real solve must be rejected."""
    _skip_if_unavailable(key)
    _patch_live_loader(monkeypatch)
    request = _live_request()
    response = resolve_strategy(key).create().optimize(request)

    assert certify_optimization_response(request, response)["is_feasible"] is True

    mutated = MUTATIONS[mutation](deepcopy(response))
    certificate = certify_optimization_response(request, mutated)
    assert certificate["is_feasible"] is False, (key, mutation, certificate)