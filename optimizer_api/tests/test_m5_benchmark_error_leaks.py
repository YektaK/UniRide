"""M5 (audit 2026-10-01): the benchmark router must not send exception text or
absolute server paths to clients; details are logged server-side."""

from __future__ import annotations

import importlib
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.routers import benchmark

SECRET = "SECRET-DSN C:\\Users\\secret\\tsplib.db /srv/private/path"
HEADERS = {"X-Internal-API-Key": "m5-key"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "m5-key")
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    app = FastAPI()
    app.include_router(benchmark.router)
    return TestClient(app, raise_server_exceptions=False)


def _install_failing_reader(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError(SECRET)

    module = types.ModuleType("academic_benchmark.results_reader")
    for name in ("get_leaderboard", "get_best_result", "get_benchmark_rows", "get_academic_problems"):
        setattr(module, name, boom)
    monkeypatch.setitem(sys.modules, "academic_benchmark.results_reader", module)


@pytest.mark.parametrize("url", [
    "/api/v1/benchmark/academic/leaderboard",
    "/api/v1/benchmark/academic/best?problem=berlin52&algorithm=ga",
    "/api/v1/benchmark/academic/benchmark-results",
    "/api/v1/benchmark/academic/problems",
])
def test_academic_reader_failures_return_fixed_detail(client, monkeypatch, url):
    _install_failing_reader(monkeypatch)
    response = client.get(url, headers=HEADERS)
    assert response.status_code == 503
    assert "SECRET" not in response.text
    assert "secret" not in response.text.lower()
    assert "RuntimeError" not in response.text


def test_download_response_does_not_expose_absolute_server_paths(client, monkeypatch, tmp_path):
    local = tmp_path / "berlin52.tsp"
    local.write_text("x", encoding="utf-8")

    monkeypatch.setattr(benchmark, "get_problem_by_name", lambda name: types.SimpleNamespace(file_path=str(local)))
    response = client.post("/api/v1/benchmark/download/berlin52", headers=HEADERS)
    assert response.status_code == 200
    assert str(tmp_path) not in response.text

    monkeypatch.setattr(benchmark, "get_problem_by_name", lambda name: None)
    monkeypatch.setattr(benchmark, "download_tsplib_problem", lambda name: str(local))
    response = client.post("/api/v1/benchmark/download/berlin52", headers=HEADERS)
    assert response.status_code == 200
    assert str(tmp_path) not in response.text


def test_cli_preview_json_error_does_not_echo_parser_text(client, monkeypatch, tmp_path):
    (tmp_path / "bad.json").write_text("{not json " + SECRET, encoding="utf-8")
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(tmp_path))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "none"))
    response = client.get("/api/v1/benchmark/cli/preview", params={"filename": "bad.json"}, headers=HEADERS)
    assert response.status_code == 400
    assert "Expecting" not in response.text
    assert "SECRET" not in response.text


def test_matrix_native_worker_failure_text_is_not_exposed_in_run_status(monkeypatch):
    """The worker's failure goes to run status (readable by the client): fixed message only."""
    tm = importlib.import_module("academic_benchmark.tsplib_manager")
    monkeypatch.setattr(tm, "load_routing_problem", lambda name: types.SimpleNamespace(name=name))
    monkeypatch.setattr(tm, "save_benchmark_run", lambda *a, **k: None)
    monkeypatch.setattr(tm, "save_benchmark_result", lambda *a, **k: None)
    ef = importlib.import_module("uniride_core.algorithms.engine_factory")
    monkeypatch.setattr(ef, "canonical_matrix_engine_name", lambda algo: "Core-X")
    monkeypatch.setattr(ef, "create_matrix_engine", lambda algo: object())
    br = importlib.import_module("uniride_core.benchmark_runner")

    class ExplodingRunner:
        def __init__(self, algorithms):
            pass

        def run_one(self, *args, **kwargs):
            raise RuntimeError(SECRET)

    monkeypatch.setattr(br, "MatrixBenchmarkRunner", ExplodingRunner)

    run_id = "m5-matrix-leak"
    benchmark._start_matrix_native_benchmark_impl(run_id, [{"id": "x"}], ["p"], {"n_runs": 1})
    state = benchmark.benchmark_state_manager.get_run(run_id)
    state.thread.join(timeout=30)
    assert state.status.value == "failed"
    assert "SECRET" not in state.message
    assert "secret" not in state.message.lower()
