"""Rate limiter behavior: under-limit passes, over-limit returns 429 with
Retry-After, and the window resets after it elapses."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from optimizer_api.compute_policy import ComputePolicy
from optimizer_api import rate_limit


@pytest.fixture(autouse=True)
def _clean_buckets():
    rate_limit._buckets.clear()
    yield
    rate_limit._buckets.clear()


def _client() -> TestClient:
    app = FastAPI()

    @app.get("/probe")
    def probe(_: None = Depends(rate_limit.require_rate_limit)):
        return {"ok": True}

    return TestClient(app)


def test_under_limit_passes(monkeypatch):
    monkeypatch.setattr(
        rate_limit,
        "load_compute_policy",
        lambda: ComputePolicy(rate_limit_requests=2, rate_limit_window_seconds=60),
    )
    client = _client()
    for _ in range(2):
        assert client.get("/probe").status_code == 200


def test_over_limit_returns_429_with_retry_after(monkeypatch):
    monkeypatch.setattr(
        rate_limit,
        "load_compute_policy",
        lambda: ComputePolicy(rate_limit_requests=2, rate_limit_window_seconds=60),
    )
    client = _client()
    for _ in range(2):
        assert client.get("/probe").status_code == 200
    denied = client.get("/probe")
    assert denied.status_code == 429
    assert denied.json() == {"detail": "rate limit exceeded"}
    assert denied.headers.get("Retry-After")


def test_window_reset_allows_requests_again(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        rate_limit,
        "load_compute_policy",
        lambda: ComputePolicy(rate_limit_requests=2, rate_limit_window_seconds=60),
    )
    client = _client()
    for _ in range(2):
        assert client.get("/probe").status_code == 200
    assert client.get("/probe").status_code == 429

    clock[0] = 61.0
    assert client.get("/probe").status_code == 200