"""H12 / QW7 acceptance: identical request + seed -> identical partition and routes,
also when several /compare-style calls run concurrently and global ``random`` is hostile."""

import random
import threading

import pytest

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from strategies.two_opt_strategy import TwoOptStrategy


class _GeoDataLoader:
    """Deterministic matrix from coordinates, so the test needs no database."""

    def get_submatrix(self, location_ids, coordinates=None):
        coords = [coordinates[i] for i in location_ids]
        return [
            [
                0.0 if i == j else (abs(a["lat"] - b["lat"]) + abs(a["lng"] - b["lng"])) * 1000.0
                for j, b in enumerate(coords)
            ]
            for i, a in enumerate(coords)
        ]


def _request(algorithm):
    layout = random.Random(11)
    students = [
        StudentNode(
            id=f"s{i}",
            location_code=f"L{i}",
            coordinates={"lat": 40.9 + layout.random() * 0.1, "lng": 29.0 + layout.random() * 0.1},
            disability_type="Sw" if i % 5 == 0 else "So",
        )
        for i in range(1, 41)
    ]
    return OptimizationRequest(
        algorithm="two_opt",
        depot=LocationNode(id="D", lat=40.95, lng=29.05),
        students=students,
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=600,
        clustering_algorithm=algorithm,
    )


def _signature(response):
    return (
        frozenset(frozenset(r.student_ids) for r in response.routes),
        tuple(tuple(step.location2 for step in r.route_details) for r in response.routes),
    )


@pytest.mark.parametrize("clustering", ["kmeans", "k_medoids", "fuzzy_cmeans"])
def test_concurrent_identical_requests_replay_partition_and_routes(monkeypatch, clustering):
    monkeypatch.setattr("strategies.two_opt_strategy.DataLoader.get_instance", lambda: _GeoDataLoader())
    request = _request(clustering)
    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(7)

    def worker():
        barrier.wait()
        response = TwoOptStrategy({"seed": 5, "max_iterations": 30}).optimize(request)
        with lock:
            results.append(_signature(response))

    def noisy():
        barrier.wait()
        for i in range(300):
            random.seed(i)
            random.random()

    threads = [threading.Thread(target=worker) for _ in range(6)] + [threading.Thread(target=noisy)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 6
    assert len({partition for partition, _ in results}) == 1
    assert len(set(results)) == 1
