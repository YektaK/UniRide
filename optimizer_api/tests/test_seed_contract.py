import itertools
import random
import threading

import numpy as np
import pytest

from models.schemas import (
    LocationNode,
    OptimizationRequest,
    OptimizationResponse,
    RouteStep,
    StudentNode,
    VehicleRoute,
)
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.ga_split_strategy import GASplitStrategy
from strategies.gwo_strategy import GreyWolfOptimizerStrategy
from strategies.gwo_split_strategy import GWOSplitStrategy
from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.hho_split_strategy import HHOSplitStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.pso_split_strategy import PSOSplitStrategy
from strategies.two_opt_strategy import TwoOptStrategy
from strategies.seed_utils import DEFAULT_SEED, make_rng, resolve_seed

from optimizer_api.benchmark_runner import AlgorithmConfig, BenchmarkRunner
from uniride_core.algorithms.clustering import Point
from uniride_core.models import ProblemInstance


def test_resolve_seed_preserves_zero():
    assert resolve_seed({"seed": 0}) == 0


def test_resolve_seed_defaults_when_absent_or_none():
    assert resolve_seed({}) == DEFAULT_SEED
    assert resolve_seed({"seed": None}) == DEFAULT_SEED
    assert DEFAULT_SEED == 42


def test_resolve_seed_passes_through_int_and_coerces():
    assert resolve_seed({"seed": 7}) == 7
    assert resolve_seed({"seed": "7"}) == 7


def test_make_rng_returns_random_instance_seeded_by_config():
    rng = make_rng({"seed": 0})
    assert isinstance(rng, random.Random)
    assert rng.randint(0, 10**6) == random.Random(0).randint(0, 10**6)


def test_make_rng_default_seed_is_deterministic():
    assert make_rng({}).randint(0, 10**6) == make_rng({}).randint(0, 10**6)


# ---------------------------------------------------------------------------
# Strategy-level seed contract: all 9 strategies
# ---------------------------------------------------------------------------

def _multi_student_request(**overrides):
    students = [
        StudentNode(
            id=f"student-{i}",
            location_code=f"S{i}",
            coordinates={"lat": float(i), "lng": 0.0},
            disability_type="Sw" if i % 2 == 0 else "So",
        )
        for i in range(1, 6)
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


class _FakeDataLoader:
    def get_submatrix(self, location_ids, coordinates=None):
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


def _rng_shuffle_solve(self, waypoints, depot, time_matrix, coordinates, first=None, second=None):
    rng = first if isinstance(first, random.Random) else second
    route = list(waypoints)
    rng.shuffle(route)
    return route, 10.0


class _FakeSplitSolution:
    def __init__(self, routes):
        self.best_tour = routes[0] if routes else None
        self.final_result = {"routes": routes, "time_window_violations": 0}


def _split_solver(waypoints, **kwargs):
    route = list(waypoints)
    kwargs["rng"].shuffle(route)
    return _FakeSplitSolution([route])


def _patch_strategy(monkeypatch, module, strategy_cls, engine):
    tick = itertools.count(1)
    monkeypatch.setattr(f"{module}.time.time", lambda: next(tick))
    monkeypatch.setattr(f"{module}.DataLoader.get_instance", lambda: _FakeDataLoader())
    if engine is None:
        monkeypatch.setattr(f"{module}.VehicleCalculator", _FakeVehicleCalculator)
        monkeypatch.setattr(strategy_cls, "_solve_tsp", _rng_shuffle_solve)
    else:
        monkeypatch.setattr(f"{module}.{engine}", _split_solver)


def _route_sequence(response):
    return [
        [step.location2 for step in route.route_details][:-1]
        for route in response.routes
    ]


_SEED_CASES = [
    (GeneticAlgorithmStrategy, "strategies.ga_strategy", "genetic_algorithm", None),
    (GASplitStrategy, "strategies.ga_split_strategy", "ga_split", "solve_ga_split"),
    (GreyWolfOptimizerStrategy, "strategies.gwo_strategy", "gwo", None),
    (GWOSplitStrategy, "strategies.gwo_split_strategy", "gwo_split", "solve_gwo_split"),
    (HarrisHawksOptimizerStrategy, "strategies.hho_strategy", "hho", None),
    (HHOSplitStrategy, "strategies.hho_split_strategy", "hho_split", "solve_hho_split"),
    (PSOStrategy, "strategies.pso_strategy", "pso", None),
    (PSOSplitStrategy, "strategies.pso_split_strategy", "pso_split", "solve_pso_split"),
    (TwoOptStrategy, "strategies.two_opt_strategy", "two_opt", None),
]


@pytest.mark.parametrize("cls,module,algo,engine", _SEED_CASES, ids=[case[2] for case in _SEED_CASES])
def test_strategy_seed_zero_replays(monkeypatch, cls, module, algo, engine):
    _patch_strategy(monkeypatch, module, cls, engine)
    request = _multi_student_request(algorithm=algo)

    first = _route_sequence(cls({"seed": 0}).optimize(request))
    strategy_b = cls({"seed": 0})
    second = _route_sequence(strategy_b.optimize(request))

    assert strategy_b.seed == 0
    assert first == second


@pytest.mark.parametrize("cls,module,algo,engine", _SEED_CASES, ids=[case[2] for case in _SEED_CASES])
def test_strategy_seed_zero_differs_from_seed_one(monkeypatch, cls, module, algo, engine):
    _patch_strategy(monkeypatch, module, cls, engine)
    request = _multi_student_request(algorithm=algo)

    sequence_zero = _route_sequence(cls({"seed": 0}).optimize(request))
    sequence_one = _route_sequence(cls({"seed": 1}).optimize(request))

    assert sequence_zero != sequence_one


@pytest.mark.parametrize("cls,module,algo,engine", _SEED_CASES, ids=[case[2] for case in _SEED_CASES])
def test_strategy_omitted_seed_replays(monkeypatch, cls, module, algo, engine):
    _patch_strategy(monkeypatch, module, cls, engine)
    request = _multi_student_request(algorithm=algo)

    first = _route_sequence(cls({}).optimize(request))
    strategy_b = cls({})
    second = _route_sequence(strategy_b.optimize(request))

    assert strategy_b.seed == DEFAULT_SEED
    assert first == second


def test_pso_rng_for_config_honors_seed_zero():
    strategy = PSOStrategy({"seed": 7})
    rng = strategy._rng_for_config({"seed": 0})
    assert rng.randint(0, 10**6) == random.Random(0).randint(0, 10**6)


def test_pso_rng_for_config_falls_back_to_strategy_seed():
    strategy = PSOStrategy({"seed": 7})
    assert strategy._rng_for_config(None).randint(0, 10**6) == random.Random(7).randint(0, 10**6)
    assert strategy._rng_for_config({}).randint(0, 10**6) == random.Random(7).randint(0, 10**6)
    assert strategy._rng_for_config({"seed": None}).randint(0, 10**6) == random.Random(7).randint(0, 10**6)


def test_pso_request_seed_zero_override_without_mutating_strategy_defaults(monkeypatch):
    captured = {}

    def fake_solve(self, waypoints, depot, time_matrix, coordinates, config=None, rng=None):
        captured["config_seed"] = config.get("seed")
        return list(waypoints), 10.0

    monkeypatch.setattr("strategies.pso_strategy.DataLoader.get_instance", lambda: _FakeDataLoader())
    monkeypatch.setattr("strategies.pso_strategy.VehicleCalculator", _FakeVehicleCalculator)
    monkeypatch.setattr(PSOStrategy, "_solve_tsp", fake_solve)

    strategy = PSOStrategy({"seed": 123})
    request = _multi_student_request(algorithm="pso", pso_config={"seed": 0})

    response = strategy.optimize(request)

    assert response.success is True
    assert captured["config_seed"] == 0
    assert strategy.seed == 123
    assert strategy.config["seed"] == 123


# ---------------------------------------------------------------------------
# Benchmark runner: seed threading, replay, no process-global reseeding
# ---------------------------------------------------------------------------

class _SeedThreadingStub:
    def __init__(self):
        self.seen_seeds = []

    def optimize(self, request):
        seed = (request.ga_config or {}).get("seed")
        self.seen_seeds.append(seed)
        keys = [f"loc_{i + 1}" for i in range(3)]
        rotation = (seed or 0) % 3
        keys = keys[rotation:] + keys[:rotation]
        steps = [RouteStep(location1="depot", location2=keys[0], duration=1.0, distance=1.0)]
        for i in range(len(keys) - 1):
            steps.append(RouteStep(location1=keys[i], location2=keys[i + 1], duration=1.0, distance=1.0))
        steps.append(RouteStep(location1=keys[-1], location2="depot", duration=1.0, distance=1.0))
        routes = [VehicleRoute(vehicle_id="V1", route_details=steps, total_duration_minutes=len(steps) * 1.0)]
        return OptimizationResponse(
            algorithm_used="stub",
            success=True,
            routes=routes,
            total_vehicles=1,
            total_duration_minutes=len(steps) * 1.0,
        )


def _tiny_problem():
    return ProblemInstance(
        name="tiny4",
        dimension=4,
        problem_type="tsp",
        edge_weight_type="EUC_2D",
        category="small",
        coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        depot_index=0,
        optimal=40.0,
    )


def _run_runner(stub, seed=42, n_runs=1):
    runner = BenchmarkRunner(strategies_registry={"ga_split": stub})
    results, metadata = runner.run(
        problems=[_tiny_problem()],
        algorithms=[AlgorithmConfig(name="stub", algorithm_id="ga_split", params={})],
        n_runs=n_runs,
        seed=seed,
    )
    return results, metadata


def test_runner_same_seed_replays_tour_lengths():
    results1, metadata1 = _run_runner(_SeedThreadingStub(), seed=42)
    results2, metadata2 = _run_runner(_SeedThreadingStub(), seed=42)

    assert [result.tour_length for result in results1] == [result.tour_length for result in results2]
    assert metadata1["seed"] == 42
    assert metadata2["seed"] == 42


def test_runner_seed_zero_replays_tour_lengths():
    stub1 = _SeedThreadingStub()
    stub2 = _SeedThreadingStub()
    results1, _ = _run_runner(stub1, seed=0)
    results2, _ = _run_runner(stub2, seed=0)

    assert [result.tour_length for result in results1] == [result.tour_length for result in results2]
    assert stub1.seen_seeds == [0]
    assert stub2.seen_seeds == [0]


def test_runner_threads_deterministic_per_experiment_seed():
    stub = _SeedThreadingStub()
    results, _ = _run_runner(stub, seed=42)
    assert stub.seen_seeds == [42]
    assert len(results) == 1
    assert results[0].tour_length > 0


def test_runner_does_not_reseed_process_global_rng():
    random_state = random.getstate()
    np_state = _np_state_snapshot()

    _run_runner(_SeedThreadingStub(), seed=42)

    assert random.getstate() == random_state
    assert _np_state_snapshot() == np_state


def _np_state_snapshot():
    state = np.random.get_state()
    return (state[0], tuple(state[1].tolist()), state[2], state[3], state[4])


# ---------------------------------------------------------------------------
# Concurrency isolation
# ---------------------------------------------------------------------------

def test_concurrent_strategies_with_different_seeds_match_sequential_output(monkeypatch):
    _patch_strategy(monkeypatch, "strategies.pso_strategy", PSOStrategy, None)
    _patch_strategy(monkeypatch, "strategies.ga_strategy", GeneticAlgorithmStrategy, None)

    pso = PSOStrategy({"seed": 1})
    ga = GeneticAlgorithmStrategy({"seed": 2})
    pso_request = _multi_student_request(algorithm="pso")
    ga_request = _multi_student_request(algorithm="genetic_algorithm")

    pso_sequential = [_route_sequence(pso.optimize(pso_request)) for _ in range(6)]
    ga_sequential = [_route_sequence(ga.optimize(ga_request)) for _ in range(6)]

    threaded = {"pso": [], "ga": []}
    start = threading.Event()
    barrier = threading.Barrier(3)

    def pso_worker():
        barrier.wait()
        start.wait()
        for _ in range(6):
            threaded["pso"].append(_route_sequence(pso.optimize(pso_request)))

    def ga_worker():
        barrier.wait()
        start.wait()
        for _ in range(6):
            threaded["ga"].append(_route_sequence(ga.optimize(ga_request)))

    thread1 = threading.Thread(target=pso_worker)
    thread2 = threading.Thread(target=ga_worker)
    thread1.start()
    thread2.start()
    barrier.wait()
    start.set()
    thread1.join()
    thread2.join()

    assert threaded["pso"] == pso_sequential
    assert threaded["ga"] == ga_sequential


# ---------------------------------------------------------------------------
# FCM and numba determinism; no global side effects
# ---------------------------------------------------------------------------

def _points(n=10):
    return [
        Point(
            id=f"p{i}",
            lat=float(i % 5),
            lng=float(i // 5),
            disability_type="Sw" if i % 2 == 0 else "So",
            location_code=f"p{i}",
        )
        for i in range(n)
    ]


def test_fcm_same_seed_identical_assignments_without_global_side_effects():
    from uniride_core.algorithms.clustering_strategies.fuzzy_cmeans_enhanced import (
        fuzzy_c_means_with_membership,
    )

    random_state = random.getstate()
    np_state = _np_state_snapshot()

    _, _, assignments_a = fuzzy_c_means_with_membership(_points(), k=3, rng=random.Random(42))
    _, _, assignments_b = fuzzy_c_means_with_membership(_points(), k=3, rng=random.Random(42))

    assert assignments_a == assignments_b
    assert random.getstate() == random_state
    assert _np_state_snapshot() == np_state


def test_fcm_split_engine_cluster_indices_deterministic_for_seed():
    from uniride_core.algorithms.fcm_split_engine import _cluster_node_indices

    indices = list(range(8))
    coordinates = [(float(i), float(i % 3)) for i in range(8)]

    random_state = random.getstate()

    clusters_a = _cluster_node_indices(indices, coordinates, k=3, cfg={}, seed=12345)
    clusters_b = _cluster_node_indices(indices, coordinates, k=3, cfg={}, seed=12345)

    assert clusters_a == clusters_b
    assert random.getstate() == random_state


def test_numba_run_single_test_deterministic_without_global_reseed():
    from uniride_core.algorithms.local_search_numba import LocalSearchType
    from uniride_core.algorithms.numba_metaheuristics import run_single_test

    class Problem:
        name = "tiny"
        dimension = 6
        coordinates = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5), (2.0, 0.0)]
        optimal = None

    random_state = random.getstate()

    first = run_single_test(Problem(), LocalSearchType.TWO_OPT, seed=777, params={"max_iterations": 8})
    second = run_single_test(Problem(), LocalSearchType.TWO_OPT, seed=777, params={"max_iterations": 8})

    assert first["tour"] == second["tour"]
    assert first["tour_length"] == second["tour_length"]
    assert random.getstate() == random_state
