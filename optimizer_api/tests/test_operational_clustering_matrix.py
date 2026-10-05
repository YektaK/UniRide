"""Operational clustering (k_medoids, clarke_wright) runs on the stored matrix.

The cluster-first strategies (ga, pso, gwo, hho, two_opt, permutation_tsp) hand
the authoritative directed matrix, keyed by physical location code and
including the depot, to ``VehicleCalculator.calculate``; k_medoids and
clarke_wright then read only matrix values (no haversine stand-in).
"""

import os

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

import pytest

from routers import optimization
from test_certifier_arc_sources import _RepositoryLoader, _decimal_repository
from test_certifier_authoritative_matrix import _request
from uniride_core.algorithms.clustering_strategies import clarke_wright, k_medoids


@pytest.mark.parametrize("clustering", ["k_medoids", "clarke_wright"])
@pytest.mark.parametrize(
    "key", ["ga", "pso", "gwo", "hho", "two_opt", "permutation_tsp"]
)
def test_cluster_first_strategies_cluster_on_directed_matrix_values(
    monkeypatch, key, clustering
):
    repository = _decimal_repository()
    loader = _RepositoryLoader(repository)
    monkeypatch.setattr(
        "utils.data_loader.DataLoader.get_instance", staticmethod(lambda: loader)
    )

    calls = []
    module = {"k_medoids": k_medoids, "clarke_wright": clarke_wright}[clustering]
    original = module.get_duration

    def spy(p1, p2, time_matrix):
        value = original(p1, p2, time_matrix)
        calls.append((p1.location_code, p2.location_code, value))
        return value

    monkeypatch.setattr(module, "get_duration", spy)

    request = _request(5, algorithm=key, max_travel_time=120, so_capacity=2)
    request.clustering_algorithm = clustering

    result = optimization.optimize_route(request)

    assert result.success is True, (key, clustering, result.error_message)
    assert calls, "the clustering never read the matrix"
    for origin, destination, value in calls:
        assert value == pytest.approx(repository.arc(origin, destination)), (
            origin,
            destination,
        )
    # the matrix is directed: at least one queried pair differs from its reverse
    assert any(
        repository.arc(a, b) != repository.arc(b, a) for a, b, _ in calls if a != b
    )
