"""Protected redacted Dudullu matrix-readiness contract.

Tests the repository-level ``readiness_summary`` measurement and the
internal-key-protected HTTP boundary
(``GET /api/v1/internal/readiness``, ``POST /api/v1/internal/readiness/time-matrix``).
"""

import importlib
import json
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from utils.matrix_repository import TimeMatrixRepository
from optimizer_api.routers import readiness

# --------------------------------------------------------------------------- fakes


class _FakeProvider:
    def __init__(self, rows=None):
        self.calls = 0
        self.rows = rows if rows is not None else []

    def fetch_rows(self):
        self.calls += 1
        return self.rows


class _FailingProvider:
    def fetch_rows(self):
        raise RuntimeError("dedicated secret boom")


class _FailingAfterProvider(_FakeProvider):
    def fetch_rows(self):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("provider down")
        return self.rows


class _MutableClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


_DEFAULT = object()


def _build_repo(provider=_DEFAULT, clock=None, ttl_seconds=600):
    if provider is _DEFAULT:
        provider = _FakeProvider()
    if clock is None:
        clock = _MutableClock()
    return TimeMatrixRepository(provider=provider, ttl_seconds=ttl_seconds, clock=clock)


COMPLETE_ROWS = [
    {"origin_code": "D.Kampus", "destination_code": "Sw1", "duration_minutes": 9},
    {"origin_code": "D.Kampus", "destination_code": "So1", "duration_minutes": 11},
    {"origin_code": "Sw1", "destination_code": "D.Kampus", "duration_minutes": 10},
    {"origin_code": "Sw1", "destination_code": "So1", "duration_minutes": 12},
    {"origin_code": "So1", "destination_code": "D.Kampus", "duration_minutes": 13},
    {"origin_code": "So1", "destination_code": "Sw1", "duration_minutes": 15},
]

EXPECTED_READY_SUMMARY = {
    "source": "supabase",
    "loaded": True,
    "stale": False,
    "hasError": False,
    "matrixLocationCount": 3,
    "requiredLocationCount": 3,
    "missingRequiredLocationCount": 0,
    "expectedRequiredDirectedArcCount": 6,
    "validRequiredDirectedArcCount": 6,
    "invalidOrMissingRequiredDirectedArcCount": 0,
    "depotPresent": True,
    "complete": True,
    "ready": True,
}

# -------------------------------------------------------------------- repository


def test_complete_asymmetric_required_set_is_ready():
    repo = _build_repo(provider=_FakeProvider(rows=[dict(r) for r in COMPLETE_ROWS]))
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["Sw1", "So1"], depot_code="D.Kampus"
    )

    assert summary == EXPECTED_READY_SUMMARY


def test_required_codes_are_stripped_deduped_and_depot_deduped():
    repo = _build_repo(provider=_FakeProvider(rows=[dict(r) for r in COMPLETE_ROWS]))
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["Sw1", "Sw1", "  So1 ", "D.Kampus"],
        depot_code="D.Kampus",
    )

    assert summary["requiredLocationCount"] == 3
    assert summary["expectedRequiredDirectedArcCount"] == 6
    assert summary["validRequiredDirectedArcCount"] == 6
    assert summary["ready"] is True


def test_required_code_absent_from_loaded_matrix_counts_missing():
    repo = _build_repo(provider=_FakeProvider(rows=[dict(r) for r in COMPLETE_ROWS]))
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["MissingHome"], depot_code="D.Kampus"
    )

    assert summary["depotPresent"] is True
    assert summary["requiredLocationCount"] == 2
    assert summary["missingRequiredLocationCount"] == 1
    assert summary["expectedRequiredDirectedArcCount"] == 2
    assert summary["validRequiredDirectedArcCount"] == 0
    assert summary["complete"] is False
    assert summary["ready"] is False


def test_missing_depot_blocks_readiness():
    rows = [
        {"origin_code": "A", "destination_code": "B", "duration_minutes": 5},
        {"origin_code": "B", "destination_code": "A", "duration_minutes": 6},
    ]
    repo = _build_repo(provider=_FakeProvider(rows=rows))
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["A", "B"], depot_code="D.Kampus"
    )

    assert summary["depotPresent"] is False
    assert summary["requiredLocationCount"] == 3
    assert summary["missingRequiredLocationCount"] == 1
    assert summary["ready"] is False


@pytest.mark.parametrize("mutation", ["missing", "zero", "negative", "nan", "infinite"])
def test_invalid_required_off_diagonal_arcs_are_counted(mutation):
    rows = [
        {"origin_code": "D0", "destination_code": "A", "duration_minutes": 5},
        {"origin_code": "A", "destination_code": "D0", "duration_minutes": 6},
        {"origin_code": "D0", "destination_code": "B", "duration_minutes": 7},
        {"origin_code": "B", "destination_code": "D0", "duration_minutes": 8},
        {"origin_code": "A", "destination_code": "B", "duration_minutes": 9},
        {"origin_code": "B", "destination_code": "A", "duration_minutes": 10},
    ]
    bad_values = {"missing": None, "zero": 0, "negative": -7, "nan": float("nan"), "infinite": float("inf")}
    target = bad_values[mutation]
    if target is None:
        rows = [
            r
            for r in rows
            if not (r["origin_code"] == "A" and r["destination_code"] == "B")
        ]
    else:
        for r in rows:
            if r["origin_code"] == "A" and r["destination_code"] == "B":
                r["duration_minutes"] = target
    repo = _build_repo(provider=_FakeProvider(rows=rows))
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["A", "B"], depot_code="D0"
    )

    assert summary["expectedRequiredDirectedArcCount"] == 6
    assert summary["validRequiredDirectedArcCount"] == 5
    assert summary["invalidOrMissingRequiredDirectedArcCount"] == 1
    assert summary["missingRequiredLocationCount"] == 0
    assert summary["depotPresent"] is True
    assert summary["complete"] is False
    assert summary["ready"] is False


def test_diagonal_arcs_are_excluded_from_counts():
    rows = [dict(r) for r in COMPLETE_ROWS]
    rows.append({"origin_code": "D.Kampus", "destination_code": "D.Kampus", "duration_minutes": 99})
    repo = _build_repo(provider=_FakeProvider(rows=rows))
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["Sw1", "So1"], depot_code="D.Kampus"
    )

    assert summary["expectedRequiredDirectedArcCount"] == 6
    assert summary["validRequiredDirectedArcCount"] == 6
    assert summary["ready"] is True


def test_coordinate_fallback_never_ready():
    repo = _build_repo(provider=None)
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["A"], depot_code="D.Kampus"
    )

    assert summary["source"] == "coordinates"
    assert summary["loaded"] is False
    assert summary["complete"] is False
    assert summary["ready"] is False


def test_stale_last_known_good_data_blocks_readiness():
    clock = _MutableClock()
    repo = _build_repo(
        provider=_FailingAfterProvider(rows=[dict(r) for r in COMPLETE_ROWS]),
        clock=clock,
        ttl_seconds=600,
    )
    repo.load()
    assert repo.readiness_summary(student_locations=["Sw1"], depot_code="D.Kampus")["ready"] is True

    clock.advance(601)
    repo.refresh()

    summary = repo.readiness_summary(
        student_locations=["Sw1"], depot_code="D.Kampus"
    )
    assert summary["source"] == "supabase"
    assert summary["loaded"] is True
    assert summary["stale"] is True
    assert summary["hasError"] is True
    assert summary["ready"] is False


def test_provider_error_is_redacted_and_never_returns_last_error():
    repo = _build_repo(provider=_FailingProvider())
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["A"], depot_code="D.Kampus"
    )

    assert summary["source"] == "empty"
    assert summary["hasError"] is True
    assert summary["ready"] is False
    assert "last_error" not in summary
    assert "boom" not in json.dumps(summary)


def test_empty_and_depot_only_input_never_ready():
    repo = _build_repo(provider=_FakeProvider(rows=[dict(r) for r in COMPLETE_ROWS]))
    repo.load()

    for codes in ([], ["D.Kampus"]):
        summary = repo.readiness_summary(student_locations=codes, depot_code="D.Kampus")
        assert summary["complete"] is False
        assert summary["ready"] is False
        assert summary["validRequiredDirectedArcCount"] == 0


def test_summary_contains_only_redacted_aggregate_fields():
    repo = _build_repo(provider=_FakeProvider(rows=[dict(r) for r in COMPLETE_ROWS]))
    repo.load()

    summary = repo.readiness_summary(
        student_locations=["Sw1", "So1"], depot_code="D.Kampus"
    )

    assert set(summary) == set(EXPECTED_READY_SUMMARY)
    serialized = json.dumps(summary)
    for forbidden in ("D.Kampus", "Sw1", "So1", "last_error"):
        assert forbidden not in serialized


# --------------------------------------------------------- HTTP boundary helpers


class _StubMatrixRepository:
    def __init__(self, summary=None):
        self.summary = summary or dict(EXPECTED_READY_SUMMARY, ready=True)
        self.last_locations = None
        self.last_depot = None

    def readiness_summary(self, student_locations, depot_code):
        self.last_locations = [str(code) for code in student_locations]
        self.last_depot = depot_code
        return dict(self.summary)


class _StubDataLoader:
    def __init__(self, repository):
        self.repository = repository
        self.refresh_calls = []

    def refresh(self, force=False):
        self.refresh_calls.append(force)


class _StubDataLoaderClass:
    instance = None

    @classmethod
    def get_instance(cls):
        return cls.instance


def _client():
    app = FastAPI()
    app.include_router(readiness.router)
    return TestClient(app)


def _install_stub_loader(monkeypatch, loader):
    _StubDataLoaderClass.instance = loader
    monkeypatch.setattr(readiness, "DataLoader", _StubDataLoaderClass)


def _enable_internal_key(monkeypatch, key="shared-key"):
    monkeypatch.setenv("INTERNAL_API_KEY", key)
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("UNIRIDE_TENANT_KEYS", raising=False)


def _post_codes(monkeypatch, loader, codes, headers=None):
    _install_stub_loader(monkeypatch, loader)
    return _client().post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": codes},
        headers=headers,
    )


# ------------------------------------------------------------------ HTTP boundary


def test_missing_shared_correct_and_tenant_keys(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    _install_stub_loader(monkeypatch, _StubDataLoader(_StubMatrixRepository()))
    client = _client()

    missing = client.post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": ["Sw1"]},
    )
    wrong = client.post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": ["Sw1"]},
        headers={"X-Internal-API-Key": "wrong-key"},
    )
    shared = client.post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": ["Sw1"]},
        headers={"X-Internal-API-Key": "shared-key"},
    )

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert missing.json() == wrong.json() == {"detail": "Forbidden"}
    assert shared.status_code == 200
    assert "shared-key" not in shared.text

    monkeypatch.setenv(
        "UNIRIDE_TENANT_KEYS", json.dumps({"tenantA": "tenant-only-key"})
    )
    tenant = client.post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": ["Sw1"]},
        headers={"X-Internal-API-Key": "tenant-only-key"},
    )
    assert tenant.status_code == 403
    assert tenant.json() == {"detail": "Forbidden"}


def test_auth_disabled_keeps_development_opt_out(monkeypatch):
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")
    _install_stub_loader(monkeypatch, _StubDataLoader(_StubMatrixRepository()))

    response = _client().post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": ["Sw1"]},
    )

    assert response.status_code == 200


def test_get_readiness_is_protected_handshake(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    _install_stub_loader(monkeypatch, _StubDataLoader(_StubMatrixRepository()))
    client = _client()

    assert client.get("/api/v1/internal/readiness").status_code == 403
    ok = client.get(
        "/api/v1/internal/readiness", headers={"X-Internal-API-Key": "shared-key"}
    )
    assert ok.status_code == 200
    assert ok.json() == {"service": "optimizer", "internal": "ok"}


def test_route_calls_non_forced_refresh_before_measuring(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    loader = _StubDataLoader(_StubMatrixRepository())

    response = _post_codes(
        monkeypatch, loader, ["Sw1"], headers={"X-Internal-API-Key": "shared-key"}
    )

    assert response.status_code == 200
    assert loader.refresh_calls == [False]
    assert loader.repository.last_locations == ["Sw1"]
    assert loader.repository.last_depot == "D.Kampus"


def test_request_accepts_250_codes_but_rejects_251(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    loader = _StubDataLoader(_StubMatrixRepository())

    ok = _post_codes(
        monkeypatch,
        loader,
        ["Sw1"] * 250,
        headers={"X-Internal-API-Key": "shared-key"},
    )
    over = _post_codes(
        monkeypatch,
        loader,
        ["Sw1"] * 251,
        headers={"X-Internal-API-Key": "shared-key"},
    )

    assert ok.status_code == 200
    assert over.status_code == 422
    assert over.json() == {"detail": "Invalid readiness request"}


def test_request_rejects_empty_and_blank_and_malformed_bodies(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    _install_stub_loader(monkeypatch, _StubDataLoader(_StubMatrixRepository()))
    client = _client()
    headers = {"X-Internal-API-Key": "shared-key"}

    for payload in (
        {"student_location_codes": []},
        {"student_location_codes": ["  "]},
        {"student_location_codes": ["Sw1", ""]},
        {"student_location_codes": "not-a-list"},
        {},
        [1, 2, 3],
    ):
        response = client.post(
            "/api/v1/internal/readiness/time-matrix", json=payload, headers=headers
        )
        assert response.status_code == 422
        assert response.json() == {"detail": "Invalid readiness request"}

    broken = client.post(
        "/api/v1/internal/readiness/time-matrix",
        content=b"{not json",
        headers={"X-Internal-API-Key": "shared-key", "Content-Type": "application/json"},
    )
    assert broken.status_code == 422
    assert broken.json() == {"detail": "Invalid readiness request"}


def test_unknown_top_level_fields_are_rejected_with_fixed_422(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    loader = _StubDataLoader(_StubMatrixRepository())
    _install_stub_loader(monkeypatch, loader)
    client = _client()
    headers = {"X-Internal-API-Key": "shared-key"}

    for payload in (
        {"student_location_codes": ["Sw1"], "extra": "x"},
        {"student_location_codes": ["Sw1"], "limit": 5},
        {"student_location_codes": ["Sw1"], "source": "malicious"},
        {"codes": ["Sw1"]},
        {"student_location_codes": ["Sw1"], "student_location_codes_extra": ["So1"]},
    ):
        response = client.post(
            "/api/v1/internal/readiness/time-matrix", json=payload, headers=headers
        )
        assert response.status_code == 422
        assert response.json() == {"detail": "Invalid readiness request"}
        assert "Sw1" not in response.text

    assert loader.refresh_calls == []


def test_invalid_422_and_success_neither_echo_sentinel_or_error(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    _install_stub_loader(monkeypatch, _StubDataLoader(_StubMatrixRepository()))
    client = _client()
    headers = {"X-Internal-API-Key": "shared-key"}
    sentinel = "SENTINEL-9f2a"

    bad = client.post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": [sentinel, ""]},
        headers=headers,
    )
    assert bad.status_code == 422
    assert sentinel not in bad.text

    ok = client.post(
        "/api/v1/internal/readiness/time-matrix",
        json={"student_location_codes": [sentinel]},
        headers=headers,
    )
    assert ok.status_code == 200
    assert sentinel not in ok.text
    assert "D.Kampus" not in ok.text


def test_readiness_failure_returns_200_with_ready_false(monkeypatch):
    _enable_internal_key(monkeypatch, "shared-key")
    failing_repo = _build_repo(provider=_FailingProvider())
    failing_repo.load()
    loader = _StubDataLoader(failing_repo)

    response = _post_codes(
        monkeypatch, loader, ["A"], headers={"X-Internal-API-Key": "shared-key"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["hasError"] is True
    assert "boom" not in response.text


# ----------------------------------------------------------------------- /health


def test_public_health_remains_unauthorized_and_unchanged(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "shared-key")
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("UNIRIDE_TENANT_KEYS", raising=False)
    sys.modules.pop("optimizer_api.main", None)
    sys.modules.pop("main", None)

    module = importlib.import_module("optimizer_api.main")
    client = TestClient(module.app)

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "3.1.0"
    assert {"message", "features", "algorithms"} <= set(body)

    denied = client.get("/api/v1/internal/readiness")
    assert denied.status_code == 403

    # Restore import state so cross-file startup-guard tests see a fresh main.
    sys.modules.pop("optimizer_api.main", None)
    sys.modules.pop("main", None)