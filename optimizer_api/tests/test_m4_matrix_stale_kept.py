"""M4 / MT2 staleness half (owner decision 2026-10-14, DECISION_LOG T09).

The C2 gate stays: a matrix kept after a failed refresh, or older than the TTL,
is NOT served by ``matrix_snapshot`` (redacted 503; bound /optimize shares the
same repository call). The 503 detail tells a stale/kept matrix apart from a
missing one so the daily plan can name the reason. A fresh matrix is served
(200) with its provenance: ``loaded_at``, ``age_seconds``, ``refresh_failed``.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.routers import readiness
from utils import matrix_repository
from utils.matrix_repository import MatrixSnapshotError, TimeMatrixRepository

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


class _Provider:
    """First fetch works; later fetches raise while ``down`` is set."""

    def __init__(self):
        self.calls = 0
        self.down = False

    def fetch_rows(self):
        self.calls += 1
        if self.calls > 1 and self.down:
            raise RuntimeError("provider down: secret-detail")
        return ROWS


class _Loader:
    def __init__(self, repository):
        self.repository = repository

    def refresh(self, force=False):
        self.repository.refresh(force=force)


class _NoRefreshLoader(_Loader):
    """Leaves the repository as-is so the TTL gate is reached with no failed refresh."""

    def refresh(self, force=False):
        return None


class _LoaderClass:
    instance = None

    @classmethod
    def get_instance(cls):
        return cls.instance


def _repo(clock, provider=None):
    repo = TimeMatrixRepository(
        provider=provider or _Provider(), ttl_seconds=600, clock=clock
    )
    repo.load()
    return repo


def _post(monkeypatch, repo, loader_cls=_Loader):
    monkeypatch.setenv("INTERNAL_API_KEY", KEY)
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("UNIRIDE_TENANT_KEYS", raising=False)
    _LoaderClass.instance = loader_cls(repo)
    monkeypatch.setattr(readiness, "DataLoader", _LoaderClass)
    app = FastAPI()
    app.include_router(readiness.router)
    return TestClient(app).post(
        "/api/v1/internal/matrix-snapshot",
        json={"student_location_codes": ["Sw1"]},
        headers={"X-Internal-API-Key": KEY},
    )


def test_fresh_snapshot_carries_age_and_provenance():
    clock = _Clock()
    repo = _repo(clock)
    clock.advance(30)

    provenance = repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")["provenance"]

    assert provenance["age_seconds"] == pytest.approx(30.0)
    assert provenance["refresh_failed"] is False
    assert provenance["loaded_at"].endswith("+00:00")


def test_fresh_matrix_is_served_with_200_and_provenance(monkeypatch):
    response = _post(monkeypatch, _repo(_Clock()))

    assert response.status_code == 200
    provenance = response.json()["provenance"]
    assert provenance["refresh_failed"] is False
    assert provenance["age_seconds"] == 0.0


def test_failed_forced_refresh_is_503_stale_not_served(monkeypatch):
    clock = _Clock()
    provider = _Provider()
    repo = _repo(clock, provider)
    provider.down = True
    clock.advance(30)

    response = _post(monkeypatch, repo)  # the route force-refreshes; the fetch fails

    assert response.status_code == 503
    assert response.json() == {"detail": "Matrix snapshot stale"}
    assert "secret-detail" not in response.text


def test_matrix_older_than_ttl_after_failed_refresh_is_503_stale(monkeypatch):
    clock = _Clock()
    provider = _Provider()
    repo = _repo(clock, provider)
    provider.down = True
    clock.advance(601)

    response = _post(monkeypatch, repo)

    assert response.status_code == 503
    assert response.json() == {"detail": "Matrix snapshot stale"}


def test_repository_raises_the_stale_subclass_of_the_snapshot_error():
    clock = _Clock()
    provider = _Provider()
    repo = _repo(clock, provider)
    provider.down = True
    repo.refresh(force=True)  # fails; the matrix is kept

    with pytest.raises(MatrixSnapshotError) as caught:
        repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")
    assert isinstance(caught.value, matrix_repository.MatrixStaleError)


def test_recovery_clears_the_stale_state(monkeypatch):
    clock = _Clock()
    provider = _Provider()
    repo = _repo(clock, provider)
    provider.down = True
    repo.refresh(force=True)
    provider.down = False

    response = _post(monkeypatch, repo)

    assert response.status_code == 200
    assert response.json()["provenance"]["refresh_failed"] is False


def test_failed_refresh_sets_refresh_failed_in_matrix_provenance():
    clock = _Clock()
    provider = _Provider()
    repo = _repo(clock, provider)
    assert repo.matrix_provenance()["refresh_failed"] is False
    provider.down = True
    clock.advance(30)

    repo.refresh(force=True)  # fails; the last-known-good matrix is kept

    provenance = repo.matrix_provenance()
    assert provenance["refresh_failed"] is True
    assert provenance["age_seconds"] == pytest.approx(30.0)  # still the old load time


def test_matrix_older_than_ttl_without_failed_refresh_is_stale():
    clock = _Clock()
    repo = _repo(clock)  # provider healthy; _last_error stays None
    clock.advance(601)
    assert repo._last_error is None

    with pytest.raises(matrix_repository.MatrixStaleError, match="matrix is stale"):
        repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")


def test_ttl_only_stale_matrix_is_503_through_the_route(monkeypatch):
    clock = _Clock()
    repo = _repo(clock)
    clock.advance(601)

    response = _post(monkeypatch, repo, loader_cls=_NoRefreshLoader)

    assert repo._last_error is None
    assert response.status_code == 503
    assert response.json() == {"detail": "Matrix snapshot stale"}


def test_matrix_exactly_at_ttl_is_still_served():
    clock = _Clock()
    repo = _repo(clock)
    clock.advance(600)

    assert repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")["provenance"]["refresh_failed"] is False
