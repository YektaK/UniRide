from __future__ import annotations

from uniride_core.algorithms.gwo_split_engine import GWOSplitSolution, Wolf
from uniride_core.algorithms.hho_split_engine import HHOSplitSolution, Hawk

from optimizer_api.models import OptimizationRequest
from optimizer_api.strategies.gwo_split_strategy import GWOSplitStrategy
from optimizer_api.strategies.hho_split_strategy import HHOSplitStrategy


class _FakeDataLoader:
    def get_submatrix(self, location_ids):
        size = len(location_ids)
        return [
            [0 if i == j else abs(i - j) + 1 for j in range(size)]
            for i in range(size)
        ]


def _request(**overrides) -> OptimizationRequest:
    payload = {
        "depot": "D",
        "locations": ["A", "B"],
        "distance_matrix": {
            "D": {"D": 0, "A": 2, "B": 3},
            "A": {"D": 2, "A": 0, "B": 1},
            "B": {"D": 3, "A": 1, "B": 0},
        },
        "demands": {"A": (1, 0), "B": (0, 1)},
        "max_travel_time": 120,
        "sw_capacity": 1,
        "so_capacity": 1,
    }
    payload.update(overrides)
    return OptimizationRequest(**payload)


def test_gwo_split_strategy_delegates_to_core_solver(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "optimizer_api.strategies.gwo_split_strategy.DataLoader.get_instance",
        lambda: _FakeDataLoader(),
    )

    def fake_solve_gwo_split(**kwargs):
        calls.append(kwargs)
        wolf = Wolf(position=["A", "B"], fitness=1.0, total_cost=7.0)
        return GWOSplitSolution(
            alpha=wolf,
            beta=wolf,
            delta=wolf,
            final_result={"routes": [["A"], ["B"]], "time_window_violations": 0},
            iterations=1,
        )

    monkeypatch.setattr(
        "optimizer_api.strategies.gwo_split_strategy.solve_gwo_split",
        fake_solve_gwo_split,
    )

    response = GWOSplitStrategy(config={"seed": 123, "population_size": 2}).optimize(
        _request(gwo_config={"max_iterations": 3})
    )

    assert response.success is True
    assert response.algorithm_used == "gwo_split"
    assert response.total_vehicles == 2
    assert len(calls) == 1
    assert calls[0]["waypoints"] == ["A", "B"]
    assert calls[0]["depot"] == "D"
    assert calls[0]["config"]["seed"] == 123
    assert calls[0]["config"]["population_size"] == 2
    assert calls[0]["config"]["max_iterations"] == 3
    assert calls[0]["sw_capacity"] == 1
    assert calls[0]["so_capacity"] == 1


def test_hho_split_strategy_delegates_to_core_solver(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "optimizer_api.strategies.hho_split_strategy.DataLoader.get_instance",
        lambda: _FakeDataLoader(),
    )

    def fake_solve_hho_split(**kwargs):
        calls.append(kwargs)
        return HHOSplitSolution(
            prey=Hawk(position=["A", "B"], fitness=1.0, total_cost=7.0),
            final_result={"routes": [["A", "B"]], "time_window_violations": 0},
            iterations=1,
        )

    monkeypatch.setattr(
        "optimizer_api.strategies.hho_split_strategy.solve_hho_split",
        fake_solve_hho_split,
    )

    response = HHOSplitStrategy(config={"seed": 456, "population_size": 2}).optimize(
        _request(hho_config={"max_iterations": 4})
    )

    assert response.success is True
    assert response.algorithm_used == "hho_split"
    assert response.total_vehicles == 1
    assert len(calls) == 1
    assert calls[0]["waypoints"] == ["A", "B"]
    assert calls[0]["depot"] == "D"
    assert calls[0]["config"]["seed"] == 456
    assert calls[0]["config"]["population_size"] == 2
    assert calls[0]["config"]["max_iterations"] == 4
    assert calls[0]["sw_capacity"] == 1
    assert calls[0]["so_capacity"] == 1
