"""H12 / QW7: ``clustering_algorithm`` is an allowlist, unknown names are rejected (422)."""

import pytest
from pydantic import ValidationError

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from uniride_core.algorithms.clustering_strategies import SUPPORTED_CLUSTERING_ALGORITHMS


def _request(**overrides):
    data = {
        "depot": LocationNode(id="D", lat=0.0, lng=0.0),
        "students": [
            StudentNode(id="s1", location_code="S1", coordinates={"lat": 1.0, "lng": 0.0}, disability_type="So")
        ],
    }
    data.update(overrides)
    return OptimizationRequest(**data)


def test_default_is_sweep():
    assert _request().clustering_algorithm == "sweep"


@pytest.mark.parametrize("name", sorted(SUPPORTED_CLUSTERING_ALGORITHMS))
def test_every_supported_name_is_accepted(name):
    assert _request(clustering_algorithm=name).clustering_algorithm == name


@pytest.mark.parametrize("bad", ["", "Sweep", "kmeans ", "random", "../x", "dbscan"])
def test_unknown_names_are_rejected(bad):
    with pytest.raises(ValidationError):
        _request(clustering_algorithm=bad)


def test_unknown_name_is_422_over_http():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.post("/probe")
    def probe(body: OptimizationRequest):
        return {"clustering_algorithm": body.clustering_algorithm}

    payload = {
        "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
        "students": [
            {"id": "s1", "location_code": "S1", "coordinates": {"lat": 1.0, "lng": 0.0}, "disability_type": "So"}
        ],
    }
    client = TestClient(app)
    assert client.post("/probe", json={**payload, "clustering_algorithm": "kmeans"}).status_code == 200
    assert client.post("/probe", json={**payload, "clustering_algorithm": "not_a_strategy"}).status_code == 422
