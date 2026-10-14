"""M4 / MT2 staleness half (owner decision 2026-10-13, DECISION_LOG T09).

A failed forced refresh keeps the last-known-good matrix. The matrix snapshot
must still be served (HTTP 200, same matrix), but it must say that it is a
stale-kept matrix: ``provenance.refresh_failed`` is true and ``loaded_at`` /
``age_seconds`` show how old it is. Warn and show the age; never fail closed.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.routers import readiness
from utils.matrix_repository import TimeMatrixRepository

KEY = "m4-shared-key"
ROWS = [
    {"origin_code": "D.Kampus", "destination_code": "Sw1", "duration_minutes": 9},
    {"origin_code": "Sw1", "destination_code": "D.Kampus", "duration_minutes": 10},
]


class _Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class _LoadsOnceThenFails:
    """Fake provider: the first fetch works, every later fetch raises."""

    def __init__(self):
        self.calls = 0

    def fetch_rows(self):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("provider down: secret-detail")
        return ROWS


class _Loader:
    def __init__(self, repository):
        self.repository = repository

    def refresh(self, force=False):
        self.repository.refresh(force=force)


class _LoaderClass:
    instance = None

    @classmethod
    def get_instance(cls):
        return cls.instance


def _repo(clock):
    repo = TimeMatrixRepository(
        provider=_LoadsOnceThenFails(), ttl_seconds=600, clock=clock
    )
    repo.load()
    return repo


def _post(monkeypatch, repo):
    monkeypatch.setenv("INTERNAL_API_KEY", KEY)
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("UNIRIDE_TENANT_KEYS", raising=False)
    _LoaderClass.instance = _Loader(repo)
    monkeypatch.setattr(readiness, "DataLoader", _LoaderClass)
    app = FastAPI()
    app.include_router(readiness.router)
    return TestClient(app).post(
        "/api/v1/internal/matrix-snapshot",
        json={"student_location_codes": ["Sw1"]},
        headers={"X-Internal-API-Key": KEY},
    )


def test_healthy_snapshot_reports_refresh_not_failed():
    snapshot = _repo(_Clock()).matrix_snapshot(["Sw1"], depot_code="D.Kampus")

    assert snapshot["provenance"]["refresh_failed"] is False
    assert snapshot["provenance"]["age_seconds"] == 0.0


def test_failed_forced_refresh_keeps_serving_and_flags_the_snapshot(monkeypatch):
    clock = _Clock()
    repo = _repo(clock)
    healthy = repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")
    clock.advance(30)

    response = _post(monkeypatch, repo)  # forced refresh fails inside the route

    assert response.status_code == 200
    body = response.json()
    assert body["sha256"] == healthy["sha256"]  # same matrix is served
    assert body["arcs"] == healthy["arcs"]
    provenance = body["provenance"]
    assert provenance["refresh_failed"] is True
    assert provenance["age_seconds"] == pytest.approx(30.0)
    assert provenance["loaded_at"] == healthy["provenance"]["loaded_at"]
    assert "secret-detail" not in response.text


def test_matrix_older_than_ttl_after_failed_refresh_is_served_with_its_age(monkeypatch):
    clock = _Clock()
    repo = _repo(clock)
    clock.advance(601)  # past the 600 s TTL

    response = _post(monkeypatch, repo)

    assert response.status_code == 200
    assert response.json()["provenance"]["refresh_failed"] is True
    assert response.json()["provenance"]["age_seconds"] == pytest.approx(601.0)


def test_successful_refresh_clears_the_flag():
    clock = _Clock()
    provider = _LoadsOnceThenFails()
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=clock)
    repo.load()
    clock.advance(30)
    repo.refresh(force=True)  # fails
    assert repo.matrix_snapshot(["Sw1"], "D.Kampus")["provenance"]["refresh_failed"] is True

    provider.calls = 0  # the provider recovers
    repo.refresh(force=True)

    fresh = repo.matrix_snapshot(["Sw1"], "D.Kampus")["provenance"]
    assert fresh["refresh_failed"] is False
    assert fresh["age_seconds"] == 0.0
