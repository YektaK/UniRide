"""QW4 / audit C4 backend half: benchmark stop is real, slots are bounded,
oversize parameters are rejected and the router is rate limited.

Appendix H.5 turned into a test with fake, finite, slow workers (no solver)."""

import sys
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api import rate_limit
from optimizer_api.benchmark_state import (
    BenchmarkStateManager,
    BenchmarkStatus,
    MAX_CONCURRENT_BENCHMARKS,
)
from optimizer_api.compute_policy import ComputePolicy
from optimizer_api.routers import benchmark

EXPERIMENT_SECONDS = 0.15


def _wait(predicate, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _slow_worker(manager, run_id):
    """Fake worker: many slow 'experiments', checks the stop flag between them."""
    def work():
        for _ in range(1000):
            if manager.stop_requested(run_id):
                break
            time.sleep(EXPERIMENT_SECONDS)
        manager.complete_run(run_id, 0, "fake done")
    return threading.Thread(target=work, daemon=True)


def test_stop_keeps_slot_until_thread_exits_then_frees_it():
    manager = BenchmarkStateManager()
    threads = []
    for i in range(MAX_CONCURRENT_BENCHMARKS):
        state, _ = manager.create_run(f"r{i}", 1000, {})
        assert state is not None
        t = _slow_worker(manager, f"r{i}")
        t.start()
        manager.register_thread(f"r{i}", t)
        threads.append(t)

    assert manager.create_run("r-extra", 1, {})[0] is None

    for i in range(MAX_CONCURRENT_BENCHMARKS):
        manager.stop_run(f"r{i}", "stop")

    # Stopped but still alive: the slot must stay occupied.
    assert any(t.is_alive() for t in threads)
    assert manager.can_start_run() is False
    assert manager.create_run("r-extra", 1, {})[0] is None

    for t in threads:
        t.join(timeout=3 * EXPERIMENT_SECONDS + 1)
    assert not any(t.is_alive() for t in threads)
    assert _wait(manager.can_start_run)
    assert all(manager.get_run(f"r{i}").status == BenchmarkStatus.STOPPED
               for i in range(MAX_CONCURRENT_BENCHMARKS))
    assert manager.create_run("r-extra", 1, {})[0] is not None


def test_stop_without_live_worker_stops_immediately():
    manager = BenchmarkStateManager()
    manager.create_run("solo", 1, {})
    manager.stop_run("solo", "stop")
    assert manager.get_run("solo").status == BenchmarkStatus.STOPPED
    assert manager.can_start_run() is True


def test_real_runner_exits_within_one_experiment_after_stop(monkeypatch):
    """Appendix H.5: start 3, stop, no thread survives beyond one experiment,
    a 4th start is refused while stopped-but-alive runs exist."""
    # The router imports the runner as a top-level module; patch that exact class.
    BenchmarkRunner = benchmark.BenchmarkRunner
    ExperimentResult = sys.modules[BenchmarkRunner.__module__].ExperimentResult

    manager = BenchmarkStateManager()
    monkeypatch.setattr(benchmark, "benchmark_state_manager", manager)
    monkeypatch.setattr(benchmark, "_load_benchmark_problem",
                        lambda name: SimpleNamespace(name=name))
    executed = []

    def slow_experiment(self, problem, algorithm, run_number, run_seed=None):
        executed.append(self.run_id)
        time.sleep(EXPERIMENT_SECONDS)
        return ExperimentResult(algorithm=algorithm.algorithm_id,
                                problem=problem.name, run_number=run_number,
                                tour_length=1.0, elapsed_ms=1.0)

    monkeypatch.setattr(BenchmarkRunner, "_run_single_experiment", slow_experiment)

    algos = [{"id": "genetic_algorithm", "params": {}}]
    for i in range(MAX_CONCURRENT_BENCHMARKS):
        out = benchmark._start_benchmark_impl(f"h5-{i}", algos, ["p"], {"n_runs": 100})
        assert out["status"] == "running"
    with pytest.raises(benchmark.HTTPException) as exc:
        benchmark._start_benchmark_impl("h5-4th", algos, ["p"], {"n_runs": 100})
    assert exc.value.status_code == 429

    time.sleep(EXPERIMENT_SECONDS * 1.5)
    for i in range(MAX_CONCURRENT_BENCHMARKS):
        manager.stop_run(f"h5-{i}", "stop")

    def alive():
        return [t for t in threading.enumerate()
                if t.name.startswith("benchmark-executor-h5-")]

    # Workers are still inside their current experiment: 4th start is refused.
    assert alive()
    with pytest.raises(benchmark.HTTPException) as exc:
        benchmark._start_benchmark_impl("h5-4th", algos, ["p"], {"n_runs": 100})
    assert exc.value.status_code == 429

    assert _wait(lambda: not alive(), timeout=3 * EXPERIMENT_SECONDS + 1)
    per_run = {rid: executed.count(rid) for rid in set(executed)}
    assert all(count <= 4 for count in per_run.values()), per_run
    assert all(manager.get_run(f"h5-{i}").status == BenchmarkStatus.STOPPED
               for i in range(MAX_CONCURRENT_BENCHMARKS))
    out = benchmark._start_benchmark_impl("h5-after", algos, ["p"], {"n_runs": 1})
    assert out["status"] == "running"
    assert _wait(lambda: manager.get_run("h5-after").status != BenchmarkStatus.RUNNING)


# --- parameter bounds -------------------------------------------------------

@pytest.fixture
def client():
    rate_limit._buckets.clear()
    app = FastAPI()
    app.include_router(benchmark.router)
    app.dependency_overrides[benchmark.require_tenant_authorization] = lambda: None
    yield TestClient(app)
    rate_limit._buckets.clear()


def _body(params, algo="genetic_algorithm"):
    return {"run_id": "bounds-1", "algorithms": [{"id": algo, "params": params}],
            "problems": ["p"], "settings": {"n_runs": 1}}


@pytest.mark.parametrize("algo,params", [
    ("genetic_algorithm", {"population_size": 5000}),
    ("genetic_algorithm", {"max_iterations": 100_000}),
    ("genetic_algorithm", {"max_no_improvement": 10**9}),
    ("e2bso", {"time_limit": 10**6}),
    ("pso", {"swarm_size": 5000}),
])
def test_oversize_parameters_rejected_with_422(client, algo, params):
    resp = client.post("/api/v1/benchmark/run", json=_body(params, algo))
    assert resp.status_code == 422, resp.text
    assert benchmark.benchmark_state_manager.get_run("bounds-1") is None


def test_runner_rejects_oversize_params_before_assignment():
    from optimizer_api.benchmark_runner import BenchmarkRunner

    request = SimpleNamespace()
    with pytest.raises(ValueError):
        BenchmarkRunner()._apply_algorithm_params(
            request, "genetic_algorithm", {"population_size": 5000})
    assert not hasattr(request, "ga_config")


def test_in_policy_parameters_still_assigned():
    from optimizer_api.benchmark_runner import BenchmarkRunner

    request = SimpleNamespace()
    BenchmarkRunner()._apply_algorithm_params(
        request, "genetic_algorithm",
        {"population_size": 50, "max_iterations": 100, "max_no_improvement": 20})
    assert request.ga_config["population_size"] == 50


def test_benchmark_router_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(
        rate_limit, "load_compute_policy",
        lambda: ComputePolicy(rate_limit_requests=1, rate_limit_window_seconds=60))
    bad = _body({"population_size": 5000})
    assert client.post("/api/v1/benchmark/run", json=bad).status_code == 422
    assert client.post("/api/v1/benchmark/run", json=bad).status_code == 429
