"""Legacy /benchmark runner (academic_coordinate_scope) parity after C2.

Inside ``academic_coordinate_scope`` the production strategies run on the
problem's own coordinates:

* ``ortools_cvrp`` keeps the historical ``"nearest"`` OR-Tools rounding;
* the split strategies (ga/pso/gwo/hho_split) use the coordinate metric.
  This is an intended correction: on WIP they optimized on an all-zero matrix
  (the C2 defect itself). Measured on tiny12 EUC, seed 42: ga_split 556 -> 264,
  pso_split 468 -> 264.
"""

import os

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

import pytest

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from strategies.ga_split_strategy import GASplitStrategy
from strategies.gwo_split_strategy import GWOSplitStrategy
from strategies.hho_split_strategy import HHOSplitStrategy
from strategies.ortools_cvrp import ORToolsCVRPStrategy
from strategies.pso_split_strategy import PSOSplitStrategy
from utils.matrix_repository import (
    TimeMatrixRepository,
    academic_coordinate_scope,
    in_academic_coordinate_scope,
)

COORDS = {
    "D": (0.0, 0.0),
    "L1": (3.0, 4.0),
    "L2": (6.0, 8.0),
    "L3": (0.0, 10.0),
    "L4": (9.0, 12.0),
}


def _request(**overrides):
    base = dict(
        algorithm="x",
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=[
            StudentNode(
                id=f"S{code}",
                location_code=code,
                disability_type="So",
                coordinates={"lat": lat, "lng": lng},
            )
            for code, (lat, lng) in COORDS.items()
            if code != "D"
        ],
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=600,
    )
    base.update(overrides)
    return OptimizationRequest(**base)


class _CoordinateLoader:
    """DataLoader stand-in over a repository with no stored matrix."""

    def __init__(self):
        self.repository = TimeMatrixRepository(provider=None)
        self.repository.load()

    def get_instance(self):
        return self

    def get_submatrix(self, request_locations, coordinates=None, **kwargs):
        return self.repository.get_submatrix(request_locations, coordinates, **kwargs)


@pytest.fixture
def coordinate_loader(monkeypatch):
    loader = _CoordinateLoader()
    monkeypatch.setattr(
        "utils.data_loader.DataLoader.get_instance", staticmethod(lambda: loader)
    )
    return loader


def test_scope_flag_is_public_and_scoped():
    assert in_academic_coordinate_scope() is False
    with academic_coordinate_scope():
        assert in_academic_coordinate_scope() is True
    assert in_academic_coordinate_scope() is False


def test_ortools_strategy_uses_nearest_rounding_only_inside_the_academic_scope(
    monkeypatch,
):
    from uniride_core.algorithms.ortools_cvrp_engine import ORToolsCVRPSolution

    class _FlatLoader:
        def get_submatrix(self, request_locations, coordinates=None, **_kwargs):
            n = len(request_locations)
            return [[0.0 if i == j else 5.0 for j in range(n)] for i in range(n)]

    monkeypatch.setattr(
        "utils.data_loader.DataLoader.get_instance",
        staticmethod(lambda: _FlatLoader()),
    )

    seen = []

    def fake_solve(**kwargs):
        seen.append(kwargs["arc_rounding"])
        return ORToolsCVRPSolution(success=False, error_message="stop")

    monkeypatch.setattr("strategies.ortools_cvrp.solve_ortools_cvrp", fake_solve)
    strategy = ORToolsCVRPStrategy(time_limit_seconds=1)

    with academic_coordinate_scope():
        strategy.optimize(_request())
    strategy.optimize(_request())  # operational: outside the scope

    assert seen == ["nearest", "conservative"]


@pytest.mark.parametrize(
    "strategy",
    [
        GASplitStrategy({"seed": 42, "population_size": 6, "max_iterations": 3}),
        PSOSplitStrategy({"seed": 42, "swarm_size": 6, "max_iterations": 3}),
        GWOSplitStrategy({"seed": 42, "population_size": 6, "max_iterations": 3}),
        HHOSplitStrategy({"seed": 42, "population_size": 6, "max_iterations": 3}),
    ],
    ids=["ga_split", "pso_split", "gwo_split", "hho_split"],
)
def test_split_strategies_inside_the_scope_use_the_coordinate_metric_not_zeros(
    coordinate_loader, strategy
):
    request = _request()
    with academic_coordinate_scope():
        result = strategy.optimize(request)

    assert result.success is True, result.error_message
    steps = [step for route in result.routes for step in route.route_details]
    assert steps
    for step in steps:
        a, b = COORDS[step.location1], COORDS[step.location2]
        euclid = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        assert step.duration == pytest.approx(euclid, abs=0.01), step
    assert result.total_duration_minutes > 0
