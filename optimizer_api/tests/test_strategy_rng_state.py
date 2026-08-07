import random

from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.pso_strategy import PSOStrategy
from models.schemas import LocationNode, OptimizationRequest, StudentNode


def test_pso_strategy_does_not_keep_instance_rng():
    strategy = PSOStrategy({"seed": 123})

    assert not hasattr(strategy, "rng")


def test_hho_strategy_does_not_keep_instance_rng():
    strategy = HarrisHawksOptimizerStrategy({"seed": 123})

    assert not hasattr(strategy, "rng")


def test_pso_strategy_does_not_keep_instance_rng_seed_zero():
    strategy = PSOStrategy({"seed": 0})

    assert not hasattr(strategy, "rng")


def test_hho_strategy_does_not_keep_instance_rng_seed_zero():
    strategy = HarrisHawksOptimizerStrategy({"seed": 0})

    assert not hasattr(strategy, "rng")


def test_pso_strategy_does_not_keep_instance_rng_omitted_seed():
    strategy = PSOStrategy({})

    assert not hasattr(strategy, "rng")


def test_hho_strategy_does_not_keep_instance_rng_omitted_seed():
    strategy = HarrisHawksOptimizerStrategy({})

    assert not hasattr(strategy, "rng")


def _small_request(**overrides):
    data = {
        "algorithm": "pso",
        "depot": LocationNode(id="D", lat=0.0, lng=0.0),
        "students": [
            StudentNode(
                id="student-1",
                location_code="S1",
                coordinates={"lat": 1.0, "lng": 0.0},
                disability_type="Sw",
            )
        ],
        "sw_capacity": 2,
        "so_capacity": 2,
        "max_travel_time": 120,
    }
    data.update(overrides)
    return OptimizationRequest(**data)


class _FakeDataLoader:
    def get_submatrix(self, location_ids, coordinates):
        return [
            [0.0 if i == j else 5.0 for j in range(len(location_ids))]
            for i in range(len(location_ids))
        ]


class _FakeVehicleCalculator:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def calculate(self, students, route_optimizer):
        route = route_optimizer([student["location_code"] for student in students])
        return {
            "assignments": [
                {
                    "vehicle_index": 1,
                    "route": route["route_details"],
                    "total_duration": route["total_duration"],
                    "sw_count": 1,
                    "so_count": 0,
                    "students": students,
                }
            ]
        }


def test_pso_request_config_is_passed_without_mutating_strategy_defaults(monkeypatch):
    captured = {}

    def fake_solve(self, waypoints, depot, time_matrix, coordinates, config=None, rng=None):
        captured["config"] = dict(config)
        captured["rng_type"] = type(rng).__name__
        return list(waypoints), 10.0

    monkeypatch.setattr("strategies.pso_strategy.DataLoader.get_instance", lambda: _FakeDataLoader())
    monkeypatch.setattr("strategies.pso_strategy.VehicleCalculator", _FakeVehicleCalculator)
    monkeypatch.setattr(PSOStrategy, "_solve_tsp", fake_solve)

    strategy = PSOStrategy({"seed": 123, "max_iterations": 4, "swarm_size": 2})
    request = _small_request(
        algorithm="pso",
        pso_config={"seed": 999, "max_iterations": 7, "swarm_size": 3},
    )

    response = strategy.optimize(request)

    assert response.success is True
    assert captured["config"]["seed"] == 999
    assert captured["config"]["max_iterations"] == 7
    assert captured["config"]["swarm_size"] == 3
    assert captured["rng_type"] == "Random"
    assert strategy.config["seed"] == 123
    assert strategy.config["max_iterations"] == 4
    assert strategy.config["swarm_size"] == 2


def test_hho_request_config_is_passed_without_mutating_strategy_defaults(monkeypatch):
    captured = {}

    def fake_solve(self, waypoints, depot, time_matrix, coordinates, rng, config=None):
        captured["config"] = dict(config)
        captured["rng_type"] = type(rng).__name__
        return list(waypoints), 10.0

    monkeypatch.setattr("strategies.hho_strategy.DataLoader.get_instance", lambda: _FakeDataLoader())
    monkeypatch.setattr("strategies.hho_strategy.VehicleCalculator", _FakeVehicleCalculator)
    monkeypatch.setattr(HarrisHawksOptimizerStrategy, "_solve_tsp", fake_solve)

    strategy = HarrisHawksOptimizerStrategy({"seed": 123, "max_iterations": 4, "population_size": 2})
    request = _small_request(
        algorithm="hho",
        hho_config={"seed": 999, "max_iterations": 7, "population_size": 3},
    )

    response = strategy.optimize(request)

    assert response.success is True
    assert captured["config"]["seed"] == 999
    assert captured["config"]["max_iterations"] == 7
    assert captured["config"]["population_size"] == 3
    assert captured["rng_type"] == "Random"
    assert strategy.config["seed"] == 123
    assert strategy.config["max_iterations"] == 4
    assert strategy.config["population_size"] == 2


def _rng_shuffle_solve(self, waypoints, depot, time_matrix, coordinates, first=None, second=None):
    rng = first if isinstance(first, random.Random) else second
    route = list(waypoints)
    rng.shuffle(route)
    return route, 10.0


def _multi_student_request(**overrides):
    students = [
        StudentNode(
            id=f"student-{i}",
            location_code=f"S{i}",
            coordinates={"lat": float(i), "lng": 0.0},
            disability_type="Sw" if i % 2 == 0 else "So",
        )
        for i in range(1, 5)
    ]
    data = {
        "algorithm": "pso",
        "depot": LocationNode(id="D", lat=0.0, lng=0.0),
        "students": students,
        "sw_capacity": 2,
        "so_capacity": 2,
        "max_travel_time": 120,
    }
    data.update(overrides)
    return OptimizationRequest(**data)


def _route_sequence(response):
    return [step.location2 for step in response.routes[0].route_details][:-1]


def test_pso_seed_zero_replays(monkeypatch):
    monkeypatch.setattr("strategies.pso_strategy.DataLoader.get_instance", lambda: _FakeDataLoader())
    monkeypatch.setattr("strategies.pso_strategy.VehicleCalculator", _FakeVehicleCalculator)
    monkeypatch.setattr(PSOStrategy, "_solve_tsp", _rng_shuffle_solve)

    strategy = PSOStrategy({"seed": 0})
    request = _multi_student_request(algorithm="pso")

    assert strategy.seed == 0
    assert _route_sequence(strategy.optimize(request)) == _route_sequence(strategy.optimize(request))


def test_hho_seed_zero_replays(monkeypatch):
    monkeypatch.setattr("strategies.hho_strategy.DataLoader.get_instance", lambda: _FakeDataLoader())
    monkeypatch.setattr("strategies.hho_strategy.VehicleCalculator", _FakeVehicleCalculator)
    monkeypatch.setattr(HarrisHawksOptimizerStrategy, "_solve_tsp", _rng_shuffle_solve)

    strategy = HarrisHawksOptimizerStrategy({"seed": 0})
    request = _multi_student_request(algorithm="hho")

    assert strategy.seed == 0
    assert _route_sequence(strategy.optimize(request)) == _route_sequence(strategy.optimize(request))


def test_pso_omitted_seed_replays(monkeypatch):
    monkeypatch.setattr("strategies.pso_strategy.DataLoader.get_instance", lambda: _FakeDataLoader())
    monkeypatch.setattr("strategies.pso_strategy.VehicleCalculator", _FakeVehicleCalculator)
    monkeypatch.setattr(PSOStrategy, "_solve_tsp", _rng_shuffle_solve)

    strategy = PSOStrategy({})
    request = _multi_student_request(algorithm="pso")

    assert strategy.seed == 42
    assert _route_sequence(strategy.optimize(request)) == _route_sequence(strategy.optimize(request))


def test_hho_omitted_seed_replays(monkeypatch):
    monkeypatch.setattr("strategies.hho_strategy.DataLoader.get_instance", lambda: _FakeDataLoader())
    monkeypatch.setattr("strategies.hho_strategy.VehicleCalculator", _FakeVehicleCalculator)
    monkeypatch.setattr(HarrisHawksOptimizerStrategy, "_solve_tsp", _rng_shuffle_solve)

    strategy = HarrisHawksOptimizerStrategy({})
    request = _multi_student_request(algorithm="hho")

    assert strategy.seed == 42
    assert _route_sequence(strategy.optimize(request)) == _route_sequence(strategy.optimize(request))
