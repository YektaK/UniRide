"""H12 review round 1: each routing strategy must hand *its own seeded* generator to
VehicleCalculator (``resolve_rng(None)`` would silently default to Random(42))."""

import random

import pytest

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.gwo_strategy import GreyWolfOptimizerStrategy
from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.two_opt_strategy import TwoOptStrategy
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator


class _GeoDataLoader:
    def get_submatrix(self, location_ids, coordinates=None):
        coords = [coordinates[i] for i in location_ids]
        return [
            [0.0 if i == j else (abs(a["lat"] - b["lat"]) + abs(a["lng"] - b["lng"])) * 1000.0
             for j, b in enumerate(coords)]
            for i, a in enumerate(coords)
        ]


def _recording_calculator(captured):
    class Recording(VehicleCalculator):
        def __init__(self, *args, **kwargs):
            rng = kwargs.get("rng")
            captured.append((rng, rng.getstate() if rng is not None else None))
            super().__init__(*args, **kwargs)

        def calculate(self, *args, **kwargs):  # the routing solver is not under test here
            return {"assignments": []}

    return Recording


_CASES = [
    (GeneticAlgorithmStrategy, "strategies.ga_strategy", "ga_config"),
    (GreyWolfOptimizerStrategy, "strategies.gwo_strategy", "gwo_config"),
    (HarrisHawksOptimizerStrategy, "strategies.hho_strategy", "hho_config"),
    (PSOStrategy, "strategies.pso_strategy", "pso_config"),
    (TwoOptStrategy, "strategies.two_opt_strategy", "two_opt_config"),
]
_IDS = ["ga", "gwo", "hho", "pso", "two_opt"]


def _request(**overrides):
    students = [
        StudentNode(id=f"s{i}", location_code=f"L{i}",
                    coordinates={"lat": 40.9 + 0.01 * i, "lng": 29.0 + 0.005 * i}, disability_type="So")
        for i in range(1, 7)
    ]
    data = {"depot": LocationNode(id="D", lat=40.95, lng=29.05), "students": students}
    data.update(overrides)
    return OptimizationRequest(**data)


def _spy(monkeypatch, module):
    captured = []
    monkeypatch.setattr(f"{module}.DataLoader.get_instance", lambda: _GeoDataLoader())
    monkeypatch.setattr(f"{module}.VehicleCalculator", _recording_calculator(captured))
    return captured


@pytest.mark.parametrize("cls,module,config_field", _CASES, ids=_IDS)
def test_constructor_seed_reaches_vehicle_calculator(monkeypatch, cls, module, config_field):
    captured = _spy(monkeypatch, module)
    states = []
    for seed in (3, 9, 3):
        captured.clear()
        cls({"seed": seed}).optimize(_request())
        assert len(captured) == 1
        rng, state = captured[0]
        assert state == random.Random(seed).getstate()  # fresh, seeded, unconsumed
        states.append(state)
    assert states[0] == states[2] and states[0] != states[1]


@pytest.mark.parametrize("cls,module,config_field", _CASES, ids=_IDS)
def test_request_config_seed_reaches_vehicle_calculator(monkeypatch, cls, module, config_field):
    captured = _spy(monkeypatch, module)
    cls({}).optimize(_request(**{config_field: {"seed": 17}}))
    assert len(captured) == 1
    assert captured[0][1] == random.Random(17).getstate()
