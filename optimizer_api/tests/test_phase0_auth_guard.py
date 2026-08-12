"""Phase 0 auth-guard tests (see docs/superpowers/specs/2026-08-07-p0-auth-failclosed-design.md).

Covers:
  - G1. Fail-closed: benchmark/CLI routes return 403 when INTERNAL_API_KEY is unset.
  - G2. Failed-closed still accepts a correct key.
  - G3. Startup guard: optimizer_api.main refuses to load without the key
        (raising SystemExit) unless UNIRIDE_DISABLE_AUTH=1.
  - G4. Bind guard: non-loopback host without ALLOW_PUBLIC_BIND=1 is refused.
"""

import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.auth import require_internal_api_key
from optimizer_api import runtime_config
from optimizer_api.routers import benchmark


def _make_app():
    app = FastAPI()
    app.include_router(benchmark.router)
    return app


@pytest.fixture
def authed_client():
    return TestClient(_make_app())


@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("post", "/api/v1/benchmark/run", {"json": {"run_id": "x", "algorithms": [{"id": "ga", "params": {}}], "problems": ["berlin52"], "settings": {"n_runs": 1}}}),
        ("get", "/api/v1/benchmark/cli/preview", {"params": {"filename": "missing.json"}}),
        ("get", "/api/v1/benchmark/status", {"params": {"run_id": "x"}}),
    ],
)
def test_g1_benchmark_routes_deny_when_key_unset(authed_client, monkeypatch, method, path, kwargs):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)

    response = getattr(authed_client, method)(path, **kwargs)

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_g2_correct_key_allows_benchmark_read(authed_client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "guard-test-key")

    response = authed_client.get(
        "/api/v1/benchmark/cli/preview",
        params={"filename": "missing.json"},
        headers={"X-Internal-Api-Key": "guard-test-key"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "File not found"}


def test_g3_missing_key_correctly_forbidden(authed_client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "guard-test-key")

    response = authed_client.get("/api/v1/benchmark/problems")

    assert response.status_code == 403


def _load_main_module():
    import importlib

    module = importlib.import_module("optimizer_api.main")
    return module


def test_g3_main_import_refuses_without_key(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(SystemExit) as exc:
        _load_main_module()

    assert "INTERNAL_API_KEY is not set" in str(exc.value)


def test_g3_main_import_ok_with_key(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "guard-test-key")
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    module = _load_main_module()
    assert callable(module.health_check)


def test_g3_production_rejects_explicit_disable(monkeypatch):
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(SystemExit, match="UNIRIDE_DISABLE_AUTH"):
        runtime_config.validate_runtime_configuration()


def test_g4_bind_host_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("OPTIMIZER_HOST", raising=False)

    assert runtime_config.optimizer_host() == "127.0.0.1"
    assert runtime_config.is_loopback(runtime_config.optimizer_host())


def test_g4_bind_guard_rejects_public_bind_without_opt_in(monkeypatch):
    monkeypatch.delenv("ALLOW_PUBLIC_BIND", raising=False)

    with pytest.raises(SystemExit) as exc:
        runtime_config.validate_bind_host("0.0.0.0")

    assert "ALLOW_PUBLIC_BIND=1" in str(exc.value)


def test_g4_bind_guard_accepts_loopback(monkeypatch):
    monkeypatch.delenv("ALLOW_PUBLIC_BIND", raising=False)

    runtime_config.validate_bind_host("127.0.0.1")
    runtime_config.validate_bind_host("localhost")


def test_g4_bind_guard_accepts_public_with_opt_in(monkeypatch):
    monkeypatch.setenv("ALLOW_PUBLIC_BIND", "1")

    runtime_config.validate_bind_host("0.0.0.0")