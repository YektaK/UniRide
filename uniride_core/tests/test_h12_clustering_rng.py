"""H12 / QW7: clustering must use an injected ``random.Random``, never global state."""

import random
import threading

import pytest

from uniride_core.algorithms.clustering import Point
from uniride_core.algorithms.clustering_strategies import (
    SUPPORTED_CLUSTERING_ALGORITHMS,
    get_clustering_strategy,
)
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator

RANDOMIZED = ["kmeans", "k_medoids", "fuzzy_cmeans", "fuzzy_cmeans_enhanced", "hierarchical_fcm"]
N_POINTS = 40
N_VEHICLES = 8


def _points(n=N_POINTS):
    layout = random.Random(2026)
    return [
        Point(
            f"s{i}",
            40.9 + layout.random() * 0.1,
            29.0 + layout.random() * 0.1,
            "Sw" if i % 5 == 0 else "So",
            f"L{i}",
        )
        for i in range(n)
    ]


def _matrix(points):
    return {
        a.location_code: {
            b.location_code: (abs(a.lat - b.lat) + abs(a.lng - b.lng)) * 1000.0
            for b in points
        }
        for a in points
    }


def _partition(clusters):
    return frozenset(frozenset(p.id for p in c.points) for c in clusters)


def _run(name, rng, points=None, **extra):
    points = points or _points()
    strategy = get_clustering_strategy(name, 4, 5, rng=rng, **extra)
    kwargs = {"time_matrix": _matrix(points)} if name == "k_medoids" else {}
    return strategy.cluster_students(points, N_VEHICLES, **kwargs)


def test_supported_names_match_factory():
    assert set(SUPPORTED_CLUSTERING_ALGORITHMS) == {
        "kmeans", "fuzzy_cmeans", "fuzzy_cmeans_enhanced", "hierarchical_fcm",
        "k_medoids", "sweep", "clarke_wright",
    }


@pytest.mark.parametrize("name", RANDOMIZED)
def test_same_rng_seed_same_partition_regardless_of_global_state(name):
    random.seed(1)
    first = _partition(_run(name, random.Random(7)))
    random.seed(999)
    second = _partition(_run(name, random.Random(7)))
    assert first == second


@pytest.mark.parametrize("name", RANDOMIZED)
def test_global_random_state_is_not_consumed(name):
    random.seed(123)
    before = random.getstate()
    _run(name, random.Random(7))
    assert random.getstate() == before


@pytest.mark.parametrize("name", ["kmeans", "k_medoids", "fuzzy_cmeans"])
def test_different_seeds_actually_drive_the_partition(name):
    partitions = {_partition(_run(name, random.Random(seed))) for seed in range(10)}
    assert len(partitions) > 1


@pytest.mark.parametrize("name", RANDOMIZED)
def test_no_rng_supplied_is_deterministic_and_leaves_global_alone(name):
    random.seed(5)
    before = random.getstate()
    first = _partition(_run(name, None))
    random.seed(77)
    second = _partition(_run(name, None))
    assert first == second
    random.seed(5)
    assert random.getstate() == before


@pytest.mark.parametrize("name", RANDOMIZED)
def test_concurrent_identical_calls_give_one_partition(name):
    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(7)

    def worker():
        barrier.wait()
        partition = _partition(_run(name, random.Random(7)))
        with lock:
            results.append(partition)

    def noisy():
        barrier.wait()
        for i in range(200):
            random.seed(i)
            random.random()

    threads = [threading.Thread(target=worker) for _ in range(6)] + [threading.Thread(target=noisy)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 6
    assert len(set(results)) == 1


def _students(points):
    return [
        {
            "id": p.id,
            "location_code": p.location_code,
            "coordinates": {"lat": p.lat, "lng": p.lng},
            "disability_type": p.disability_type,
        }
        for p in points
    ]


@pytest.mark.parametrize("name", ["kmeans", "k_medoids", "fuzzy_cmeans"])
def test_vehicle_calculator_replays_with_same_rng_seed(name):
    points = _points()
    matrix = _matrix(points)

    def calc(seed):
        random.seed(seed + 1000)  # hostile global state
        result = VehicleCalculator(4, 5, 120, name, rng=random.Random(seed)).calculate(
            _students(points), time_matrix=matrix
        )
        return [tuple(sorted(s["id"] for s in a["students"])) for a in result["assignments"]]

    assert calc(7) == calc(7)


@pytest.mark.parametrize("name", ["kmeans", "k_medoids", "fuzzy_cmeans"])
def test_vehicle_calculator_without_rng_replays(name):
    points = _points()
    matrix = _matrix(points)

    def calc():
        result = VehicleCalculator(4, 5, 120, name).calculate(_students(points), time_matrix=matrix)
        return [tuple(sorted(s["id"] for s in a["students"])) for a in result["assignments"]]

    random.seed(1)
    first = calc()
    random.seed(2)
    assert calc() == first
