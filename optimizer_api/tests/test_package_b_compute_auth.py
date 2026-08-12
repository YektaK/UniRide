from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from optimizer_api.routers import optimization, strategies, utils


OPTIMIZE = {
    "algorithm": "does-not-exist",
    "students": [],
    "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
}
COMPARE = {
    "algorithms": ["does-not-exist"],
    "students": [],
    "depot": {"id": "D", "lat": 0.0, "lng": 0.0},
}


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(optimization.router)
    app.include_router(strategies.router)
    app.include_router(utils.router)
    return TestClient(app)


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/optimize", OPTIMIZE),
        ("/api/v1/compare", COMPARE),
        ("/api/v1/vehicle-calculator", OPTIMIZE),
    ],
)
def test_heavy_routes_require_internal_key(monkeypatch, path, payload):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("INTERNAL_API_KEY", "expected")

    missing = _client().post(path, json=payload)
    wrong = _client().post(path, json=payload, headers={"X-Internal-API-Key": "wrong"})
    allowed = _client().post(path, json=payload, headers={"X-Internal-API-Key": "expected"})

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert missing.json() == wrong.json() == {"detail": "Forbidden"}
    assert allowed.status_code == 400
    assert "expected" not in allowed.text


def test_heavy_route_rejects_non_ascii_wrong_key(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("INTERNAL_API_KEY", "expected")

    submitted_key = "wrongé"
    response = _client().post(
        "/api/v1/optimize",
        json=OPTIMIZE,
        headers={"X-Internal-API-Key": submitted_key.encode("utf-8")},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}
    assert "expected" not in response.text
    assert submitted_key not in response.text
def test_lightweight_routes_remain_public(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("INTERNAL_API_KEY", "expected")
    client = _client()

    assert client.get("/api/v1/strategies").status_code == 200
    response = client.post(
        "/api/v1/extract-time-windows",
        params={"direction": "pickup", "target_day": "monday"},
        json=[],
    )
    assert response.status_code == 200
