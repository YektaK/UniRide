"""Phase 2: occurrence identity for cluster-first (Pipeline A) strategies.

Two students sharing a physical ``location_code`` must remain distinct
solver nodes. The non-split TSP strategies (ga/pso/gwo/hho/two_opt) derive
their route waypoints from ``VehicleCalculator.calculate``, which currently
passes physical location codes; duplicates then collapse or crash the GA
crossover. With occurrence identity, the route optimizer receives unique
occurrence keys (``L1#S1``, ``L1#S2``) while the raw submatrix is still
fetched positionally by physical codes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.gwo_strategy import GreyWolfOptimizerStrategy
from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.two_opt_strategy import TwoOptStrategy
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator

DEPOT = LocationNode(id="D", lat=0.0, lng=0.0)


def make_request():
    """Two students at L1 + one at L2 (L2 stays a single-customer location)."""
    students = [
        StudentNode(id="S1", location_code="L1", coordinates={"lat": 1.0, "lng": 1.0}, disability_type="Sw"),
        StudentNode(id="S2", location_code="L1", coordinates={"lat": 1.0, "lng": 1.0}, disability_type="So"),
        StudentNode(id="S3", location_code="L2", coordinates={"lat": 5.0, "lng": 5.0}, disability_type="Sw"),
    ]
    return OptimizationRequest(
        algorithm="x",
        depot=DEPOT,
        students=students,
        sw_capacity=10,
        so_capacity=10,
        max_travel_time=600,
    )


def make_unique_request():
    """One student per location: keys must stay identical to location codes."""
    students = [
        StudentNode(id="S1", location_code="L1", coordinates={"lat": 1.0, "lng": 1.0}, disability_type="Sw"),
        StudentNode(id="S2", location_code="L2", coordinates={"lat": 5.0, "lng": 5.0}, disability_type="So"),
    ]
    return OptimizationRequest(
        algorithm="x",
        depot=DEPOT,
        students=students,
        sw_capacity=10,
        so_capacity=10,
        max_travel_time=600,
    )


class _EuclideanDataLoader:
    """Mirrors the coordinate-fallback submatrix used by the real DataLoader."""

    def __init__(self):
        self.recorded = []

    def get_submatrix(self, request_locations, coordinates=None, geo_coords=False, asymmetric_haversine=False):
        self.recorded.append(list(request_locations))
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


def _route_stop_keys(response):
    stops = []
    for route in response.routes:
        for step in route.route_details:
            stops.append(step.location1)
        if route.route_details:
            stops.append(route.route_details[-1].location2)
    return stops


def _patch_loader(monkeypatch, strategy_module, loader):
    monkeypatch.setattr(f"strategies.{strategy_module}.DataLoader.get_instance", lambda: loader)


# ---------------------------------------------------------------------------
# RED: GA crashes on duplicate locations; the rest emit bare duplicate stops.
# ---------------------------------------------------------------------------


def test_ga_strategy_preserves_same_location_occurrences(monkeypatch):
    loader = _EuclideanDataLoader()
    _patch_loader(monkeypatch, "ga_strategy", loader)

    strategy = GeneticAlgorithmStrategy(
        {"seed": 7, "population_size": 4, "max_iterations": 4, "elite_count": 1,
         "max_no_improvement": 2, "tournament_size": 2}
    )
    response = strategy.optimize(make_request())

    assert response.success is True
    stops = _route_stop_keys(response)
    assert "L1#S1" in stops
    assert "L1#S2" in stops
    assert "L2" in stops
    assert "L1" not in stops
    student_ids = {sid for r in response.routes for sid in r.student_ids}
    assert student_ids == {"S1", "S2", "S3"}
    assert sum(r.sw_count for r in response.routes) == 2
    assert sum(r.so_count for r in response.routes) == 1
    # The submatrix must still be fetched positionally with physical codes.
    assert ["D", "L1", "L1", "L2"] in loader.recorded


def test_pso_strategy_preserves_same_location_occurrences(monkeypatch):
    loader = _EuclideanDataLoader()
    _patch_loader(monkeypatch, "pso_strategy", loader)

    strategy = PSOStrategy({"seed": 7, "swarm_size": 4, "max_iterations": 3, "max_velocity_size": 2})
    response = strategy.optimize(make_request())

    assert response.success is True
    stops = _route_stop_keys(response)
    assert "L1#S1" in stops and "L1#S2" in stops and "L2" in stops
    assert "L1" not in stops
    student_ids = {sid for r in response.routes for sid in r.student_ids}
    assert student_ids == {"S1", "S2", "S3"}
    assert sum(r.sw_count for r in response.routes) == 2
    assert sum(r.so_count for r in response.routes) == 1
    assert ["D", "L1", "L1", "L2"] in loader.recorded


def test_gwo_strategy_preserves_same_location_occurrences(monkeypatch):
    loader = _EuclideanDataLoader()
    _patch_loader(monkeypatch, "gwo_strategy", loader)

    strategy = GreyWolfOptimizerStrategy({"seed": 7, "population_size": 4, "max_iterations": 3, "max_no_improvement": 2})
    response = strategy.optimize(make_request())

    assert response.success is True
    stops = _route_stop_keys(response)
    assert "L1#S1" in stops and "L1#S2" in stops and "L2" in stops
    assert "L1" not in stops
    student_ids = {sid for r in response.routes for sid in r.student_ids}
    assert student_ids == {"S1", "S2", "S3"}
    assert sum(r.sw_count for r in response.routes) == 2
    assert sum(r.so_count for r in response.routes) == 1
    assert ["D", "L1", "L1", "L2"] in loader.recorded


def test_hho_strategy_preserves_same_location_occurrences(monkeypatch):
    loader = _EuclideanDataLoader()
    _patch_loader(monkeypatch, "hho_strategy", loader)

    strategy = HarrisHawksOptimizerStrategy({"seed": 7, "population_size": 4, "max_iterations": 3, "max_no_improvement": 2})
    response = strategy.optimize(make_request())

    assert response.success is True
    stops = _route_stop_keys(response)
    assert "L1#S1" in stops and "L1#S2" in stops and "L2" in stops
    assert "L1" not in stops
    student_ids = {sid for r in response.routes for sid in r.student_ids}
    assert student_ids == {"S1", "S2", "S3"}
    assert sum(r.sw_count for r in response.routes) == 2
    assert sum(r.so_count for r in response.routes) == 1
    assert ["D", "L1", "L1", "L2"] in loader.recorded


def test_two_opt_strategy_preserves_same_location_occurrences(monkeypatch):
    loader = _EuclideanDataLoader()
    _patch_loader(monkeypatch, "two_opt_strategy", loader)

    strategy = TwoOptStrategy({"seed": 7, "max_iterations": 200, "multi_start": False})
    response = strategy.optimize(make_request())

    assert response.success is True
    stops = _route_stop_keys(response)
    assert "L1#S1" in stops and "L1#S2" in stops and "L2" in stops
    assert "L1" not in stops
    student_ids = {sid for r in response.routes for sid in r.student_ids}
    assert student_ids == {"S1", "S2", "S3"}
    assert sum(r.sw_count for r in response.routes) == 2
    assert sum(r.so_count for r in response.routes) == 1
    assert ["D", "L1", "L1", "L2"] in loader.recorded


# ---------------------------------------------------------------------------
# VehicleCalculator route-optimizer contract.
# ---------------------------------------------------------------------------


def test_vehicle_calculator_passes_occurrence_keys_when_present():
    captured = []

    def route_optimizer(location_codes):
        captured.append(list(location_codes))
        return {"route_details": [], "total_duration": 0}

    students = [
        {"id": "S1", "location_code": "L1", "occurrence_key": "L1#S1",
         "coordinates": {"lat": 1.0, "lng": 1.0}, "disability_type": "Sw"},
        {"id": "S2", "location_code": "L1", "occurrence_key": "L1#S2",
         "coordinates": {"lat": 1.0, "lng": 1.0}, "disability_type": "So"},
        {"id": "S3", "location_code": "L2", "occurrence_key": "L2",
         "coordinates": {"lat": 5.0, "lng": 5.0}, "disability_type": "Sw"},
    ]
    calc = VehicleCalculator(sw_capacity=10, so_capacity=10, max_tour_time=600)
    calc.calculate(students, route_optimizer)

    assert captured, "route_optimizer was never invoked"
    assert sorted(captured[0]) == ["L1#S1", "L1#S2", "L2"]


def test_vehicle_calculator_falls_back_to_location_code_without_occurrence_key():
    captured = []

    def route_optimizer(location_codes):
        captured.append(list(location_codes))
        return {"route_details": [], "total_duration": 0}

    students = [
        {"id": "S1", "location_code": "L1", "coordinates": {"lat": 1.0, "lng": 1.0}, "disability_type": "Sw"},
        {"id": "S2", "location_code": "L2", "coordinates": {"lat": 5.0, "lng": 5.0}, "disability_type": "So"},
    ]
    calc = VehicleCalculator(sw_capacity=10, so_capacity=10, max_tour_time=600)
    calc.calculate(students, route_optimizer)

    assert captured, "route_optimizer was never invoked"
    assert sorted(captured[0]) == ["L1", "L2"]


# ---------------------------------------------------------------------------
# GREEN guard: unique locations keep identical keys/output (backward compat).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module,factory",
    [
        ("ga_strategy", lambda: GeneticAlgorithmStrategy({"seed": 7, "population_size": 4, "max_iterations": 3, "max_no_improvement": 2})),
        ("pso_strategy", lambda: PSOStrategy({"seed": 7, "swarm_size": 4, "max_iterations": 3})),
        ("gwo_strategy", lambda: GreyWolfOptimizerStrategy({"seed": 7, "population_size": 4, "max_iterations": 3})),
        ("hho_strategy", lambda: HarrisHawksOptimizerStrategy({"seed": 7, "population_size": 4, "max_iterations": 3})),
        ("two_opt_strategy", lambda: TwoOptStrategy({"seed": 7, "max_iterations": 200, "multi_start": False})),
    ],
    ids=["ga", "pso", "gwo", "hho", "two_opt"],
)
def test_unique_locations_keep_location_code_keys(monkeypatch, module, factory):
    _patch_loader(monkeypatch, module, _EuclideanDataLoader())
    strategy = factory()
    response = strategy.optimize(make_unique_request())

    assert response.success is True
    stops = _route_stop_keys(response)
    assert all("#" not in stop for stop in stops)
    student_ids = {sid for r in response.routes for sid in r.student_ids}
    assert student_ids == {"S1", "S2"}
