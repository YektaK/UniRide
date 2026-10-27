"""MT1-07 (audit N1-a): a split strategy must not report success when the
decoder fell back to one route per student.

``string_split_decoder`` returns ``{"error": "No feasible splitting found",
"total_cost": inf, ...}`` with singleton routes when no feasible split exists
(for example a single trip that already exceeds ``max_travel_time``). The four
GA/PSO/GWO/HHO split strategies used to ignore that flag and answered
``success=True`` with those infeasible singleton routes. Rule R3 of the MT1
plan: the fallback is reported as ``success=False`` with reason
``no_feasible_split``.

Offline: a coordinate-based fake data loader, real engines with tiny configs.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from models.schemas import LocationNode, OptimizationRequest, StudentNode

TINY_CONFIGS = {
    "ga_split": {"population_size": 4, "max_iterations": 2, "max_no_improvement": 2},
    "pso_split": {"swarm_size": 4, "max_iterations": 2},
    "gwo_split": {"population_size": 4, "max_iterations": 2},
    "hho_split": {"population_size": 4, "max_iterations": 2},
}


class FakeDataLoader:
    """Coordinate-based submatrix: travel time == Euclidean distance."""

    def get_submatrix(self, locations, coordinates=None, geo_coords=False):
        n = len(locations)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            c1 = (coordinates or {}).get(locations[i]) or {"lat": 0.0, "lng": 0.0}
            for j in range(n):
                c2 = (coordinates or {}).get(locations[j]) or {"lat": 0.0, "lng": 0.0}
                matrix[i][j] = round(
                    ((c1["lat"] - c2["lat"]) ** 2 + (c1["lng"] - c2["lng"]) ** 2) ** 0.5, 2
                )
        return matrix


def _strategy(name):
    if name == "ga_split":
        from strategies.ga_split_strategy import GASplitStrategy as cls
    elif name == "pso_split":
        from strategies.pso_split_strategy import PSOSplitStrategy as cls
    elif name == "gwo_split":
        from strategies.gwo_split_strategy import GWOSplitStrategy as cls
    else:
        from strategies.hho_split_strategy import HHOSplitStrategy as cls
    return cls(config={**TINY_CONFIGS[name], "seed": 7})


def _request(algorithm, max_travel_time):
    students = [
        StudentNode(id="S1", name="S1", location_code="L1",
                    coordinates={"lat": 10.0, "lng": 0.0}, disability_type="So"),
        StudentNode(id="S2", name="S2", location_code="L2",
                    coordinates={"lat": 0.0, "lng": 10.0}, disability_type="So"),
    ]
    return OptimizationRequest(
        algorithm=algorithm,
        students=students,
        depot=LocationNode(id="D.Kampus", lat=0.0, lng=0.0, type="Depot"),
        max_travel_time=max_travel_time,
        sw_capacity=10,
        so_capacity=10,
    )


@pytest.fixture(autouse=True)
def _fake_loader(monkeypatch):
    from utils.data_loader import DataLoader

    fake = FakeDataLoader()
    monkeypatch.setattr(DataLoader, "get_instance", staticmethod(lambda: fake))


@pytest.mark.parametrize("name", sorted(TINY_CONFIGS))
def test_singleton_trip_over_tour_limit_is_reported_as_no_feasible_split(name):
    # Each depot -> student -> depot trip costs 20 > max_travel_time 15, so the
    # decoder can only fall back to one route per student.
    result = _strategy(name).optimize(_request(name, max_travel_time=15))

    assert result.success is False
    assert result.error_message is not None
    assert "no_feasible_split" in result.error_message
    assert result.routes == []
    assert result.total_vehicles == 0


@pytest.mark.parametrize("name", sorted(TINY_CONFIGS))
def test_feasible_split_still_succeeds(name):
    # Same instance with a limit that allows the singleton trips: no fallback.
    result = _strategy(name).optimize(_request(name, max_travel_time=100))

    assert result.success is True
    assert result.error_message is None
    assert sorted(sid for r in result.routes for sid in r.student_ids) == ["S1", "S2"]
