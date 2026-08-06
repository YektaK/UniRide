"""Phase 3 — benchmark run ownership (P3) tests.

See docs/superpowers/specs/2026-08-06-p3-benchmark-run-owner-tokens-design.md
"""

import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.benchmark_state import (
    BenchmarkRunState,
    BenchmarkStateManager,
    hash_owner_token,
    verify_owner_token,
)
from optimizer_api.routers import benchmark

API_HEADERS = {"X-Internal-Api-Key": "phase3-test-key"}


def _state_with_hash(token_plain):
    return BenchmarkRunState(
        run_id="st",
        owner_token_hash=hash_owner_token(token_plain),
    )


def test_hash_owner_token_is_sha256_hex():
    assert hash_owner_token("tok") == hashlib.sha256(b"tok").hexdigest()


def test_verify_owner_token_correct_wrong_missing():
    st = _state_with_hash("secret")
    assert verify_owner_token(st, "secret") is True
    assert verify_owner_token(st, "wrong") is False
    assert verify_owner_token(st, None) is False


def test_verify_owner_token_missing_hash_is_false():
    st = BenchmarkRunState(run_id="x")
    assert verify_owner_token(st, "anything") is False


def test_create_run_returns_state_and_token():
    mgr = BenchmarkStateManager()
    state, token = mgr.create_run("create-tok", 5, {"alg": "ga"})
    assert state is not None
    assert state.run_id == "create-tok"
    assert isinstance(token, str) and len(token) >= 20
    assert state.owner_token_hash == hash_owner_token(token)
    assert token not in state.parameters.values()


def test_create_run_rejection_returns_none_none():
    mgr = BenchmarkStateManager()
    s1, t1 = mgr.create_run("create-dup", 2, {})
    assert s1 is not None and t1 is not None
    s2, t2 = mgr.create_run("create-dup", 2, {})
    assert s2 is None and t2 is None


def test_import_run_returns_state_and_token():
    mgr = BenchmarkStateManager()
    state, token = mgr.import_run(
        "import-tok",
        {"results": [], "total_experiments": 0, "parameters": {}},
    )
    assert state is not None
    assert isinstance(token, str) and len(token) >= 20
    assert state.owner_token_hash == hash_owner_token(token)
    assert token not in state.parameters


def test_import_run_duplicate_returns_none_none():
    mgr = BenchmarkStateManager()
    data = {"results": [], "total_experiments": 0, "parameters": {}}
    s1, _t1 = mgr.import_run("import-dup", data)
    assert s1 is not None
    s2, t2 = mgr.import_run("import-dup", data)
    assert s2 is None and t2 is None


def _valid_payload(**overrides):
    payload = {
        "run_id": "p3-router-run",
        "algorithms": [{"id": "ga", "params": {"seed": 7, "max_iterations": 20}}],
        "problems": ["berlin52"],
        "settings": {"n_runs": 1, "seed": 7},
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase3-test-key")
    app = FastAPI()
    app.include_router(benchmark.router)
    return TestClient(app)


class _NoopRunner:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, problems=None, algorithms=None, n_runs=1, seed=None, skip_cached=False):
        pass


class _FakeProblem:
    name = "berlin52"


def test_run_response_includes_owner_token(client, monkeypatch):
    monkeypatch.setattr(benchmark, "_load_benchmark_problem", lambda name: _FakeProblem())
    monkeypatch.setattr(benchmark, "BenchmarkRunner", _NoopRunner)
    resp = client.post(
        "/api/v1/benchmark/run",
        json=_valid_payload(run_id="p3-run-tok"),
        headers={"X-Internal-Api-Key": "phase3-test-key"},
    )
    assert resp.status_code == 200
    body = resp.json()
    token = body.get("owner_token")
    assert token and isinstance(token, str)
    state = benchmark.benchmark_state_manager.get_run("p3-run-tok")
    assert state.owner_token_hash == hash_owner_token(token)
    benchmark.benchmark_state_manager.complete_run("p3-run-tok", 0, "done")


def test_import_response_includes_owner_token(client):
    resp = client.post(
        "/api/v1/benchmark/import",
        json={"run_id": "p3-import-token", "results": [], "total_experiments": 0, "parameters": {}},
        headers={"X-Internal-Api-Key": "phase3-test-key"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json().get("owner_token"), str)


def test_cli_import_response_includes_owner_token(client, monkeypatch):
    monkeypatch.setattr(benchmark, "_resolve_cli_filename", lambda f: "dummy.json")
    monkeypatch.setattr(benchmark, "_load_and_validate_cli_json", lambda f: [{"problem": "P1", "strategy": "A", "n_runs": 1}])
    monkeypatch.setattr(benchmark, "_convert_cli_record_to_web", lambda rec, run_number: {"algorithm": "ga", "problem": "P1", "run_number": run_number})
    resp = client.post(
        "/api/v1/benchmark/cli/import?filename=dummy.json&run_id=p3-cli-token",
        headers={"X-Internal-Api-Key": "phase3-test-key"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json().get("owner_token"), str)


def test_cli_import_returns_429_when_concurrent_limit_hit(client, monkeypatch):
    monkeypatch.setattr(benchmark, "_resolve_cli_filename", lambda f: "dummy.json")
    monkeypatch.setattr(benchmark, "_load_and_validate_cli_json", lambda f: [{"problem": "P1", "strategy": "A", "n_runs": 1}])
    monkeypatch.setattr(benchmark, "_convert_cli_record_to_web", lambda rec, run_number: {"algorithm": "ga", "problem": "P1", "run_number": run_number})
    mgr = benchmark.benchmark_state_manager
    seeded = []
    try:
        for i in range(benchmark.MAX_CONCURRENT_BENCHMARKS):
            s, _tok = mgr.create_run(f"p3-cli-seed-{i}", 1, {})
            assert s is not None
            seeded.append(f"p3-cli-seed-{i}")
        resp = client.post(
            "/api/v1/benchmark/cli/import?filename=dummy.json&run_id=p3-cli-reject",
            headers={"X-Internal-Api-Key": "phase3-test-key"},
        )
        assert resp.status_code == 429
        assert resp.json()["detail"]["error"] == "Maximum concurrent benchmarks reached"
        assert mgr.get_run("p3-cli-reject") is None
    finally:
        for rid in seeded:
            mgr.complete_run(rid, 0, "done")


@pytest.mark.parametrize("method,path_fn,case_id", [
    ("get", lambda rid: ("/api/v1/benchmark/status", {"params": {"run_id": rid}}), "status"),
    ("post", lambda rid: ("/api/v1/benchmark/stop", {"params": {"run_id": rid}}), "stop"),
    ("get", lambda rid: (f"/api/v1/benchmark/results/{rid}", {}), "results"),
])
def test_owner_gated_endpoints(method, path_fn, case_id, client, monkeypatch):
    run_id = f"p3-gate-{case_id}"
    state, token = benchmark.benchmark_state_manager.create_run(run_id, 2, {})
    assert state is not None
    try:
        path, kwargs = path_fn(run_id)
        base = {"X-Internal-Api-Key": "phase3-test-key"}

        no_tok = getattr(client, method)(path, headers=base, **kwargs)
        assert no_tok.status_code == 403

        wrong = getattr(client, method)(path, headers={**base, "X-Benchmark-Owner-Token": "wrong"}, **kwargs)
        assert wrong.status_code == 403

        ok = getattr(client, method)(path, headers={**base, "X-Benchmark-Owner-Token": token}, **kwargs)
        assert ok.status_code == 200
        assert "owner_token" not in ok.json()
    finally:
        benchmark.benchmark_state_manager.complete_run(run_id, 2, "done")


def test_results_returns_data_for_completed_run(client):
    state, token = benchmark.benchmark_state_manager.create_run("p3-completed-results", 2, {"p": 1})
    assert state is not None
    benchmark.benchmark_state_manager.add_result(
        "p3-completed-results", {"algorithm": "ga", "tour_length": 1.0}
    )
    benchmark.benchmark_state_manager.complete_run("p3-completed-results", 1, "done")
    try:
        resp = client.get(
            "/api/v1/benchmark/results/p3-completed-results",
            headers={"X-Internal-Api-Key": "phase3-test-key", "X-Benchmark-Owner-Token": token},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["results"] == [{"algorithm": "ga", "tour_length": 1.0}]
        assert "owner_token" not in body
    finally:
        benchmark.benchmark_state_manager.complete_run("p3-completed-results", 1, "done")


def test_owner_404_when_run_missing(client):
    cases = [
        ("get", "/api/v1/benchmark/status?run_id=nope", {}),
        ("post", "/api/v1/benchmark/stop?run_id=nope", {}),
        ("get", "/api/v1/benchmark/results/nope", {}),
    ]
    for method, path, kwargs in cases:
        resp = getattr(client, method)(
            path,
            headers={"X-Internal-Api-Key": "phase3-test-key", "X-Benchmark-Owner-Token": "whatever"},
            **kwargs,
        )
        assert resp.status_code == 404


def test_owner_403_when_run_has_no_hash(client, monkeypatch):
    state, _tok = benchmark.benchmark_state_manager.create_run("p3-nohash", 1, {})
    state.owner_token_hash = None
    resp = client.get(
        "/api/v1/benchmark/status?run_id=p3-nohash",
        headers={"X-Internal-Api-Key": "phase3-test-key", "X-Benchmark-Owner-Token": "x"},
    )
    assert resp.status_code == 403
    benchmark.benchmark_state_manager.complete_run("p3-nohash", 1, "done")


def test_malformed_end_time_does_not_poison_manager():
    """A malformed end_time from /import must not 500 every get/list call."""
    mgr = BenchmarkStateManager()
    state, token = mgr.import_run(
        "p3-bad-end-time",
        {"results": [], "total_experiments": 0, "end_time": "not-a-date"},
    )
    assert state is not None
    assert token is not None
    run = mgr.get_run("p3-bad-end-time")
    assert run is not None
    assert run.run_id == "p3-bad-end-time"

