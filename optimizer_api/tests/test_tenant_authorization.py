"""Per-tenant authorization: tenant keys resolve to a tenant identity, the
shared internal key remains an ops override, invalid keys are 403, and the
rate limiter isolates budgets per tenant."""

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from optimizer_api import rate_limit, runtime_config
from optimizer_api.auth import require_tenant_authorization
from optimizer_api.compute_policy import ComputePolicy

TENANTS = {"alpha": "key-alpha", "beta": "key-beta"}


@pytest.fixture(autouse=True)
def _clean_buckets():
    rate_limit._buckets.clear()
    yield
    rate_limit._buckets.clear()


def _client() -> TestClient:
    app = FastAPI()

    @app.get(
        "/whoami",
        dependencies=[Depends(require_tenant_authorization)],
    )
    def whoami(request: Request):
        return {"tenant_id": getattr(request.state, "tenant_id", None)}

    return TestClient(app)


def test_tenant_key_authorizes_and_sets_tenant_id(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", '{"alpha": "key-alpha", "beta": "key-beta"}')
    monkeypatch.setenv("INTERNAL_API_KEY", "ops-key")

    client = _client()
    alpha = client.get("/whoami", headers={"X-Internal-API-Key": "key-alpha"})
    assert alpha.status_code == 200
    assert alpha.json() == {"tenant_id": "alpha"}

    beta = client.get("/whoami", headers={"X-Internal-API-Key": "key-beta"})
    assert beta.json() == {"tenant_id": "beta"}


def test_shared_internal_key_authorizes_as_internal(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", '{"alpha": "key-alpha"}')
    monkeypatch.setenv("INTERNAL_API_KEY", "ops-key")

    client = _client()
    response = client.get("/whoami", headers={"X-Internal-API-Key": "ops-key"})
    assert response.status_code == 200
    assert response.json() == {"tenant_id": "internal"}


def test_wrong_or_missing_key_is_forbidden(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", '{"alpha": "key-alpha"}')
    monkeypatch.setenv("INTERNAL_API_KEY", "ops-key")

    client = _client()
    assert client.get("/whoami").status_code == 403
    denied = client.get("/whoami", headers={"X-Internal-API-Key": "nope"})
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Forbidden"}


def test_auth_disabled_skips_the_gate(monkeypatch):
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", '{"alpha": "key-alpha"}')
    monkeypatch.setenv("INTERNAL_API_KEY", "ops-key")
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")

    client = _client()
    response = client.get("/whoami")
    assert response.status_code == 200


def _rate_limited_client() -> TestClient:
    app = FastAPI()

    @app.get(
        "/probe",
        dependencies=[
            Depends(require_tenant_authorization),
            Depends(rate_limit.require_rate_limit),
        ],
    )
    def probe():
        return {"ok": True}

    return TestClient(app)


def test_rate_limit_is_isolated_per_tenant(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", '{"alpha": "key-alpha", "beta": "key-beta"}')
    monkeypatch.setenv("INTERNAL_API_KEY", "ops-key")
    monkeypatch.setattr(
        rate_limit,
        "load_compute_policy",
        lambda: ComputePolicy(rate_limit_requests=2, rate_limit_window_seconds=60),
    )

    client = _rate_limited_client()
    for _ in range(2):
        assert client.get("/probe", headers={"X-Internal-API-Key": "key-alpha"}).status_code == 200
    assert client.get("/probe", headers={"X-Internal-API-Key": "key-alpha"}).status_code == 429

    for _ in range(2):
        assert client.get("/probe", headers={"X-Internal-API-Key": "key-beta"}).status_code == 200
    for _ in range(2):
        assert client.get("/probe", headers={"X-Internal-API-Key": "ops-key"}).status_code == 200


def test_tenant_keys_bad_json_raises_value_error(monkeypatch):
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", "not-json")
    with pytest.raises(ValueError):
        runtime_config.tenant_keys()


def test_tenant_keys_empty_values_rejected(monkeypatch):
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", '{"alpha": ""}')
    with pytest.raises(ValueError, match="alpha"):
        runtime_config.tenant_keys()


def test_startup_validation_rejects_bad_tenant_keys(monkeypatch):
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", "not-json")
    monkeypatch.setenv("INTERNAL_API_KEY", "ops-key")
    with pytest.raises(SystemExit):
        runtime_config.validate_runtime_configuration()