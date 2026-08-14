"""Mutation-proof: TSP surfaces — canonical 3-opt (TSP/ATSP) and the
permutation exact path (n <= 10).

The canonical 3-opt optimizer must only accept complete permutations of
matrix indices and must report the exact closed-cycle cost of its output
(validating those two facts back is the TSP mutation proof at core level).
The exact permutation solver must certify feasible when unmutated and must
never survive an injected step/occurrence mutation.
"""

from copy import deepcopy

import numpy as np
import pytest

from strategies.permutation_tsp import PermutationTSPStrategy
from uniride_core.algorithms.three_opt import (
    closed_tour_cost,
    improve_three_opt,
)
from verification.response_certifier import certify_optimization_response

# ---------------------------------------------------------------------------
# Canonical 3-opt contracts
# ---------------------------------------------------------------------------

SYMMETRIC_6 = np.array(
    [
        [0.0, 2.0, 9.0, 10.0, 1.0, 8.0],
        [2.0, 0.0, 6.0, 4.0, 3.0, 7.0],
        [9.0, 6.0, 0.0, 5.0, 8.0, 2.0],
        [10.0, 4.0, 5.0, 0.0, 6.0, 9.0],
        [1.0, 3.0, 8.0, 6.0, 0.0, 4.0],
        [8.0, 7.0, 2.0, 9.0, 4.0, 0.0],
    ],
    dtype=float,
)

ATSP_6 = np.array(
    [
        [0.0, 2.0, 9.0, 10.0, 1.0, 8.0],
        [3.0, 0.0, 6.0, 4.0, 3.0, 7.0],
        [9.0, 6.0, 0.0, 5.0, 8.0, 2.0],
        [10.0, 4.0, 5.0, 0.0, 6.0, 9.0],
        [1.0, 3.0, 8.0, 6.0, 0.0, 4.0],
        [8.0, 7.0, 2.0, 9.0, 4.0, 0.0],
    ],
    dtype=float,
)


def test_symmetric_three_opt_output_is_valid_permutation_with_exact_cost():
    result = improve_three_opt(list(range(6)), SYMMETRIC_6.tolist())
    assert result.mode == "symmetric_tsp"
    assert set(result.route) == set(range(6))
    assert len(set(result.route)) == 6
    assert result.cost == pytest.approx(closed_tour_cost(result.route, SYMMETRIC_6.tolist()))


def test_directed_three_opt_output_is_valid_permutation_with_exact_cost():
    result = improve_three_opt(list(range(6)), ATSP_6.tolist())
    assert result.mode == "directed_atsp"
    assert set(result.route) == set(range(6))
    assert len(set(result.route)) == 6
    assert result.cost == pytest.approx(closed_tour_cost(result.route, ATSP_6.tolist()))


@pytest.mark.parametrize(
    "mutated",
    [
        [0, 1, 2, 3, 4, 4],          # duplicate city
        [0, 1, 2, 3, 4],             # missing city (wrong length)
        [0, 1, 2, 3, 4, 6],          # out-of-range city
        [0, 1, 2, 3, 5, 5],          # duplicate + missing (same length)
    ],
    ids=["duplicate", "missing", "out_of_range", "dup_and_missing"],
)
def test_three_opt_rejects_mutated_tours(mutated):
    """A valid-looking but wrong tour must never enter the optimizer."""
    with pytest.raises(ValueError):
        improve_three_opt(mutated, SYMMETRIC_6.tolist())


def test_symmetric_three_opt_rejects_asymmetric_matrix():
    with pytest.raises(ValueError):
        improve_three_opt(list(range(6)), ATSP_6.tolist(), directed=False)


# ---------------------------------------------------------------------------
# Permutation exact path (n <= 10)
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
            "L3": {"lat": 9.0, "lng": 2.0},
            "D": {"lat": 0.0, "lng": 0.0},
        }


def _patch_loader(monkeypatch):
    loader = _EuclideanLoader()
    monkeypatch.setattr("utils.data_loader.DataLoader.get_instance", lambda: loader)
    monkeypatch.setattr(
        "strategies.sota_response_builder.DataLoader.get_instance", lambda: loader
    )
    return loader


def _tsp_request():
    from models.schemas import LocationNode, OptimizationRequest, StudentNode

    students = [
        StudentNode(
            id=f"S{i}",
            location_code=code,
            coordinates=coords,
            disability_type="Sw",
        )
        for i, (code, coords) in enumerate(
            [
                ("L1", {"lat": 1.0, "lng": 1.0}),
                ("L2", {"lat": 5.0, "lng": 5.0}),
                ("L3", {"lat": 9.0, "lng": 2.0}),
                ("L1", {"lat": 1.0, "lng": 1.0}),
                ("L2", {"lat": 5.0, "lng": 5.0}),
                ("L3", {"lat": 9.0, "lng": 2.0}),
            ],
            start=1,
        )
    ]
    return OptimizationRequest(
        algorithm="permutation_tsp",
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=students,
        sw_capacity=10,
        so_capacity=10,
        max_travel_time=600,
    )


def _mutate_drop_step(response):
    route = response.routes[0]
    if len(route.route_details) < 2:
        pytest.skip("route too short for interior-step mutation")
    route.route_details.pop(1)
    return response


def _mutate_duplicate_step(response):
    route = response.routes[0]
    route.route_details.insert(1, deepcopy(route.route_details[0]))
    return response


def test_permutation_exact_solves_and_certifies(monkeypatch):
    """n = 6 exercises the exact search path (n <= 10); unmutated output
    must certify feasible."""
    _patch_loader(monkeypatch)
    request = _tsp_request()
    response = PermutationTSPStrategy().optimize(request)
    assert response.success is True
    certificate = certify_optimization_response(request, response)
    assert certificate["is_feasible"] is True, certificate


@pytest.mark.parametrize(
    "mutate", [_mutate_drop_step, _mutate_duplicate_step], ids=["drop_step", "duplicate_step"]
)
def test_permutation_exact_mutation_never_survives(monkeypatch, mutate):
    _patch_loader(monkeypatch)
    request = _tsp_request()
    response = PermutationTSPStrategy().optimize(request)
    assert certify_optimization_response(request, response)["is_feasible"] is True

    certificate = certify_optimization_response(request, mutate(deepcopy(response)))
    assert certificate["is_feasible"] is False, certificate