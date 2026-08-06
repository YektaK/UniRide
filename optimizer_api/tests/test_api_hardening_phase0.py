"""Phase 0 API hardening RED tests (see docs/superpowers/specs/2026-08-05-phase0-api-hardening-audit.md).

Covers the six required behaviors:
  B1. Unauthenticated callers cannot start benchmark jobs or read arbitrary files.
  B2. Caller-controlled file paths are rejected (path traversal).
  B3. Bounds on problems, algorithms, workers, repetitions, iterations.
  B4. Explicit external-provider timeouts.
  B5. No shared-mutable strategy config under concurrency.
  B6. Preserve existing 401/403 semantics.

Tests are behavioral; router-level tests exercise the real FastAPI dependency wiring.
"""

import socket
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from optimizer_api.models.schemas import BenchmarkRunRequest
from optimizer_api.routers import benchmark, strategies as strategies_router

from uniride_core.algorithms import tsplib_parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_payload(**overrides):
    payload = {
        "run_id": "phase0-hardening-test",
        "algorithms": [{"id": "ga", "params": {"seed": 7, "max_iterations": 20}}],
        "problems": ["berlin52"],
        "settings": {"n_runs": 1, "seed": 7},
    }
    payload.update(overrides)
    return payload


def _make_app():
    app = FastAPI()
    app.include_router(benchmark.router)
    app.include_router(strategies_router.router)
    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


@pytest.fixture
def authed(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase0-test-key")
    return client


API_HEADERS = {"X-Internal-Api-Key": "phase0-test-key"}


class _NoCall:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return None


# ---------------------------------------------------------------------------
# B1 + B6 — auth on benchmark endpoints; public surface stays open
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("post", "/api/v1/benchmark/run", {"json": {"run_id": "x", "algorithms": [{"id": "ga", "params": {}}], "problems": ["berlin52"], "settings": {"n_runs": 1}}}),
        ("post", "/api/v1/benchmark/import", {"json": {"run_id": "x", "results": []}}),
        ("post", "/api/v1/benchmark/stop", {"params": {"run_id": "x"}}),
        ("post", "/api/v1/benchmark/download/berlin52", {}),
        ("get", "/api/v1/benchmark/status", {"params": {"run_id": "x"}}),
        ("get", "/api/v1/benchmark/param-spaces", {}),
        ("get", "/api/v1/benchmark/problems", {}),
        ("get", "/api/v1/benchmark/problems/berlin52", {}),
        ("get", "/api/v1/benchmark/results/x", {}),
        ("get", "/api/v1/benchmark/academic/leaderboard", {}),
        ("get", "/api/v1/benchmark/cli/files", {}),
        ("get", "/api/v1/benchmark/cli/preview", {"params": {"filename": "missing.json"}}),
    ],
)
def test_b1_benchmark_endpoints_reject_missing_key(client, monkeypatch, method, path, kwargs):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase0-test-key")
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_b1_missing_key_does_not_start_benchmark_run(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase0-test-key")
    before = {s.run_id for s in benchmark.benchmark_state_manager.list_runs()}

    response = client.post("/api/v1/benchmark/run", json=_valid_payload())

    assert response.status_code == 403
    after = {s.run_id for s in benchmark.benchmark_state_manager.list_runs()}
    assert after == before


def test_b1_missing_key_does_not_trigger_download(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase0-test-key")
    no_call = _NoCall()
    monkeypatch.setattr(benchmark, "download_tsplib_problem", no_call)

    response = client.post("/api/v1/benchmark/download/berlin52")

    assert response.status_code == 403
    assert no_call.calls == []


def test_b1_authenticated_run_still_works(client, authed, monkeypatch):
    monkeypatch.setattr(
        benchmark,
        "_start_benchmark_impl",
        lambda run_id, algorithms, problems, settings: {
            "run_id": run_id, "status": "running",
        },
    )

    response = client.post(
        "/api/v1/benchmark/run",
        json=_valid_payload(),
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_b1_authenticated_download_still_returns_failed_shape(client, authed, monkeypatch):
    monkeypatch.setattr(benchmark, "download_tsplib_problem", lambda name: None)

    response = client.post(
        "/api/v1/benchmark/download/berlin52",
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_b1_public_strategies_endpoint_remains_open(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase0-test-key")

    response = client.get("/api/v1/strategies")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# B2 — path traversal rejection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    ["..", "...evil", "evil.txt", "path%2F..%2Fevil"],
)
def test_b2_download_router_rejects_invalid_problem_names(client, authed, monkeypatch, name):
    no_call = _NoCall()
    monkeypatch.setattr(benchmark, "download_tsplib_problem", no_call)

    response = client.post(
        f"/api/v1/benchmark/download/{name}",
        headers=API_HEADERS,
    )

    # ".." / "%2F" payloads are normalized away by routing (404) before the
    # handler runs; literal invalid names hit the router validation (400).
    # The security invariant is that no download is ever triggered.
    assert response.status_code in (400, 404)
    assert no_call.calls == []


def test_b2_download_function_rejects_traversal_name(monkeypatch, tmp_path):
    fetched = []
    monkeypatch.setattr(
        tsplib_parser,
        "_fetch_url",
        lambda url, timeout=None: fetched.append(url) or b"not a gzip, but generic tsp data",
    )
    dest = tmp_path / "tsplib"

    result = tsplib_parser.download_tsplib_problem("../escape", dest_dir=str(dest))

    assert result is None
    assert not (tmp_path / "escape.tsp").exists()
    assert not (dest / "escape.tsp").exists()
    assert fetched == []


# ---------------------------------------------------------------------------
# B3 — bounds
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "settings",
    [{"n_runs": 10**9}, {"n_runs": 101}, {"workers": 10_000}, {"workers": 65}],
)
def test_b3_benchmark_request_rejects_unbounded_settings(settings):
    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(_valid_payload(settings=settings))


def test_b3_benchmark_request_rejects_oversized_algorithm_list():
    algorithms = [{"id": "ga", "params": {}}] * 500

    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(_valid_payload(algorithms=algorithms))


def test_b3_benchmark_request_rejects_oversized_problem_list():
    problems = ["p"] * 1000

    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(_valid_payload(problems=problems))


@pytest.mark.parametrize(
    "params",
    [
        {"max_iterations": 10**9},
        {"max_generations": 10**9},
        {"population_size": 10**9},
        {"num_particles": 10**9},
        {"num_wolves": 10**9},
        {"num_hawks": 10**9},
    ],
)
def test_b3_benchmark_request_rejects_unbounded_algorithm_params(params):
    with pytest.raises(ValidationError):
        BenchmarkRunRequest.model_validate(
            _valid_payload(algorithms=[{"id": "ga", "params": params}])
        )


def test_b3_benchmark_request_accepts_reasonable_algorithm_params():
    request = BenchmarkRunRequest.model_validate(
        _valid_payload(algorithms=[{"id": "ga", "params": {"max_iterations": 1000, "population_size": 100}}])
    )

    assert request.algorithms[0]["params"]["max_iterations"] == 1000


def test_b3_router_returns_422_for_unbounded_n_runs(client, authed):
    response = client.post(
        "/api/v1/benchmark/run",
        json=_valid_payload(settings={"n_runs": 10**9}),
        headers=API_HEADERS,
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# B4 — explicit external-provider timeouts
# ---------------------------------------------------------------------------

def test_b4_fetch_url_honors_timeout():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def _slow_peer():
        conn, _ = server.accept()
        time.sleep(5)
        conn.close()

    peer = threading.Thread(target=_slow_peer, daemon=True)
    peer.start()

    start = time.monotonic()
    result = tsplib_parser._fetch_url(f"http://127.0.0.1:{port}/slow", timeout=0.5)
    elapsed = time.monotonic() - start

    server.close()
    peer.join(timeout=6)

    assert result is None
    assert elapsed < 4.0


def test_b4_download_endpoint_does_not_fetch_without_credentials(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase0-test-key")
    no_call = _NoCall()
    monkeypatch.setattr(benchmark, "download_tsplib_problem", no_call)

    response = client.post("/api/v1/benchmark/download/berlin52")

    assert response.status_code == 403
    assert no_call.calls == []


# ---------------------------------------------------------------------------
# P1 — import_run missing (500 → 200)
# ---------------------------------------------------------------------------

def test_p1_import_run_unit():
    from optimizer_api.benchmark_state import BenchmarkStateManager

    mgr = BenchmarkStateManager()
    state = mgr.import_run("unit-import-1", {
        "results": [
            {
                "algorithm": "two_opt",
                "problem": "berlin52",
                "run_number": 1,
                "tour_length": 7550.0,
                "elapsed_ms": 40.0,
                "timestamp": "2026-01-01T00:00:00",
                "metadata": {},
            },
        ],
        "parameters": {"source": "api-test"},
        "total_experiments": 1,
        "start_time": "2026-01-01T00:00:00",
        "end_time": "2026-01-01T00:01:00",
    })

    assert state.run_id == "unit-import-1"
    assert state.status.value == "completed"
    assert state.results_count == 1
    assert state.results == [{"algorithm": "two_opt", "problem": "berlin52", "run_number": 1, "tour_length": 7550.0, "elapsed_ms": 40.0, "timestamp": "2026-01-01T00:00:00", "metadata": {}}]
    assert state.parameters == {"source": "api-test"}


def test_p1_import_endpoint_works_with_auth(client, authed):
    payload = {
        "run_id": "import-hardened-1",
        "results": [
            {
                "algorithm": "ga",
                "problem": "berlin52",
                "run_number": 1,
                "tour_length": 7600.0,
                "elapsed_ms": 123.0,
                "timestamp": "2026-01-01T00:00:00",
                "metadata": {},
            },
        ],
        "parameters": {"source": "api-hardening"},
        "total_experiments": 1,
    }

    response = client.post(
        "/api/v1/benchmark/import",
        json=payload,
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "import-hardened-1"
    assert body["status"] == "completed"
    assert body["results_imported"] == 1


# ---------------------------------------------------------------------------
# P2 — atomic create_run rejects past concurrent limit
# ---------------------------------------------------------------------------

def test_p2_create_run_returns_none_when_limit_hit_then_accepts_after_complete(
    monkeypatch,
):
    from optimizer_api.benchmark_state import (
        BenchmarkStateManager,
    )

    monkeypatch.setattr("optimizer_api.benchmark_state.MAX_CONCURRENT_BENCHMARKS", 1)

    mgr = BenchmarkStateManager()

    s1 = mgr.create_run("p2-run-1", 5, {})
    assert s1 is not None

    s2 = mgr.create_run("p2-run-2", 5, {})
    assert s2 is None

    mgr.complete_run("p2-run-1", 5, "done")
    s3 = mgr.create_run("p2-run-3", 5, {})
    assert s3 is not None


# ---------------------------------------------------------------------------
# D3 — duplicate run_id guard (no silent overwrite)
# ---------------------------------------------------------------------------

def test_d3_create_run_rejects_duplicate_run_id():
    from optimizer_api.benchmark_state import BenchmarkStateManager

    mgr = BenchmarkStateManager()
    s1 = mgr.create_run("dup-create-1", 5, {"alg": "ga"})
    assert s1 is not None

    s2 = mgr.create_run("dup-create-1", 5, {"alg": "pso"})
    assert s2 is None
    assert mgr.get_run("dup-create-1") is s1


def test_d3_import_run_rejects_duplicate_run_id():
    from optimizer_api.benchmark_state import BenchmarkStateManager

    mgr = BenchmarkStateManager()
    data = {"results": [], "total_experiments": 0, "parameters": {}}

    s1 = mgr.import_run("dup-import-1", data)
    assert s1 is not None

    s2 = mgr.import_run("dup-import-1", data)
    assert s2 is None
    assert mgr.get_run("dup-import-1") is s1


def test_d3_create_then_import_same_run_id_rejected():
    from optimizer_api.benchmark_state import BenchmarkStateManager

    mgr = BenchmarkStateManager()
    s1 = mgr.create_run("mixed-dupe-1", 3, {})
    assert s1 is not None

    s2 = mgr.import_run("mixed-dupe-1", {"results": [], "total_experiments": 0, "parameters": {}})
    assert s2 is None


def test_d3_run_endpoint_duplicate_run_id_409(client, authed):
    mgr = benchmark.benchmark_state_manager
    mgr.create_run("dup-endpoint-1", 1, {})
    mgr.complete_run("dup-endpoint-1", 1, "done")

    response = client.post(
        "/api/v1/benchmark/run",
        json=_valid_payload(run_id="dup-endpoint-1"),
        headers=API_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "Benchmark run already exists"


def test_d3_import_endpoint_duplicate_run_id_409(client, authed):
    payload = {
        "run_id": "dup-import-endpoint-1",
        "results": [
            {
                "algorithm": "ga",
                "problem": "berlin52",
                "run_number": 1,
                "tour_length": 7600.0,
                "elapsed_ms": 123.0,
                "timestamp": "2026-01-01T00:00:00",
                "metadata": {},
            },
        ],
        "parameters": {"source": "api-hardening"},
        "total_experiments": 1,
    }

    first = client.post("/api/v1/benchmark/import", json=payload, headers=API_HEADERS)
    assert first.status_code == 200

    second = client.post("/api/v1/benchmark/import", json=payload, headers=API_HEADERS)
    assert second.status_code == 409
    assert second.json()["detail"]["error"] == "Benchmark run already exists"


# ---------------------------------------------------------------------------
# B5 — no shared-mutable strategy config under concurrency
# ---------------------------------------------------------------------------

def _smoke_request():
    from optimizer_api.models.schemas import (
        LocationNode, OptimizationRequest, StudentNode, VehicleConfig,
    )

    return OptimizationRequest(
        students=[
            StudentNode(id="s1", location_code="LocB", disability_type="So", pickup_time="08:00"),
            StudentNode(id="s2", location_code="LocC", disability_type="Sw", pickup_time="08:15"),
            StudentNode(id="s3", location_code="LocD", disability_type="So", pickup_time="08:30"),
        ],
        depot=LocationNode(id="DEPOT", lat=40.0, lng=29.0),
        vehicles=[VehicleConfig(vehicle_id="V1")],
        direction="pickup",
    )


@pytest.mark.parametrize("registry_key", ["ga", "pso"])
def test_b5_config_not_mutated_after_request(registry_key):
    from optimizer_api.strategies import STRATEGY_REGISTRY

    strategy = STRATEGY_REGISTRY[registry_key]
    config_before = dict(strategy.config)

    request = _smoke_request()
    request.ga_config = {"max_iterations": 2, "population_size": 4, "seed": 1}

    result = strategy.optimize(request)

    assert result.success is True
    assert strategy.config == config_before


def test_b5_concurrent_requests_do_not_corrupt_shared_config():
    from optimizer_api.strategies import STRATEGY_REGISTRY

    strategy = STRATEGY_REGISTRY["ga"]
    config_before = dict(strategy.config)

    outcomes = [None] * 4

    def _run(index, seed):
        request = _smoke_request()
        request.ga_config = {"max_iterations": 2, "population_size": 4, "seed": seed}
        try:
            outcomes[index] = ("ok", strategy.optimize(request).success)
        except Exception as exc:  # pragma: no cover - failure path must surface
            outcomes[index] = ("error", str(exc))

    threads = [threading.Thread(target=_run, args=(i, 100 + i)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert all(status == "ok" and success is True for status, success in outcomes)
    assert strategy.config == config_before