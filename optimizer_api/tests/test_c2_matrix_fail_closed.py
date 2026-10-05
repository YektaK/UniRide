"""C2 (repository part) regression tests: the travel-time matrix fails closed.

Audit finding C2 (docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md), repros
H.2 (unbound zero matrix) and H.4 (failed first load, no recovery).

Owner requirement (2026-10-05): every operational travel time comes from the
stored Supabase ``time_matrix``. No zero, haversine or Euclidean values may
stand in for travel times unless the explicit development opt-in
``UNIRIDE_ALLOW_COORDINATE_FALLBACK`` is set.

All tests are offline: no network, no Supabase, no ``.env`` loading.
"""

import pytest
from fastapi import HTTPException

import runtime_config
from models import schemas
from routers import optimization
from strategies.ga_split_strategy import GASplitStrategy
from utils.data_loader import DataLoader
from utils.matrix_repository import (
    IncompleteTravelMatrixError,
    MatrixSnapshotError,
    MatrixUnavailableError,
    TimeMatrixRepository,
)
from utils.patterns import SingletonMeta

FLAG = "UNIRIDE_ALLOW_COORDINATE_FALLBACK"
CODES = ["D.Kampus", "L1", "L2", "L3"]
ROWS = [
    {"origin_code": a, "destination_code": b, "duration_minutes": 7 + i + 2 * j}
    for i, a in enumerate(CODES)
    for j, b in enumerate(CODES)
    if a != b
]
COORDS = {
    "D.Kampus": {"lat": 41.00, "lng": 29.17},
    "L1": {"lat": 41.01, "lng": 29.18},
    "L2": {"lat": 41.02, "lng": 29.19},
    "L3": {"lat": 41.03, "lng": 29.20},
}


@pytest.fixture(autouse=True)
def _no_opt_in(monkeypatch):
    """Every test starts from the production default: fallback not allowed."""
    monkeypatch.delenv(FLAG, raising=False)


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class _FlakyProvider:
    """Fails the first ``failures`` fetches, then serves the full matrix."""

    def __init__(self, failures=1):
        self.failures = failures
        self.calls = 0

    def fetch_rows(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("transient outage")
        return [dict(row) for row in ROWS]


def _install_loader(monkeypatch, repository):
    monkeypatch.setattr(SingletonMeta, "_instances", {})
    return DataLoader(repository=repository)


def _request(codes=("L1", "L2", "L3"), algorithm="ga_split"):
    return schemas.OptimizationRequest(
        algorithm=algorithm,
        depot=schemas.LocationNode(id="D.Kampus", lat=41.0, lng=29.17),
        students=[
            schemas.StudentNode(
                id=f"S{i}",
                name=f"S{i}",
                location_code=code,
                disability_type="So",
                coordinates=COORDS.get(code, {"lat": 41.0 + 0.2 * i, "lng": 29.17}),
            )
            for i, code in enumerate(codes, start=1)
        ],
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=60,
        ga_config={"population_size": 6, "max_iterations": 3, "seed": 1},
    )


# ------------------------------------------------- H.2: unbound zero matrix


def test_h2_no_provider_get_submatrix_raises_instead_of_zero_matrix():
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    with pytest.raises(MatrixSnapshotError):
        repo.get_submatrix(["A", "B"])
    with pytest.raises(MatrixSnapshotError):
        repo.get_submatrix(["A", "B"], coordinates={"A": {"lat": 0, "lng": 0}, "B": {"lat": 1, "lng": 1}})
    with pytest.raises(MatrixSnapshotError):
        repo.get_submatrix(["A", "B"], coordinates={"A": {"lat": 0, "lng": 0}, "B": {"lat": 1, "lng": 1}}, geo_coords=True)


def test_h2_matrix_unavailable_error_is_a_matrix_snapshot_error():
    assert issubclass(MatrixUnavailableError, MatrixSnapshotError)


def test_h2_get_duration_never_returns_zero_for_unknown_pairs():
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    with pytest.raises(MatrixSnapshotError):
        repo.get_duration("A", "B")

    loaded = TimeMatrixRepository(provider=_FlakyProvider(failures=0))
    loaded.load()
    with pytest.raises(IncompleteTravelMatrixError):
        loaded.get_duration("L1", "NOT-IN-MATRIX")
    assert loaded.get_duration("L1", "L1") == 0.0  # same node is the only zero


def test_h2_split_strategy_without_matrix_raises_not_zero_routes(monkeypatch):
    _install_loader(monkeypatch, TimeMatrixRepository(provider=None))
    strategy = GASplitStrategy({"seed": 1, "population_size": 6, "max_iterations": 3})
    with pytest.raises(MatrixSnapshotError):
        strategy.optimize(_request())


def test_h2_unbound_optimize_without_matrix_is_redacted_503(monkeypatch):
    _install_loader(monkeypatch, TimeMatrixRepository(provider=None))
    with pytest.raises(HTTPException) as caught:
        optimization.optimize_route(_request())
    assert caught.value.status_code == 503
    assert caught.value.detail == "travel-time matrix unavailable"


def test_h2_unbound_optimize_unknown_location_is_redacted_422(monkeypatch):
    repo = TimeMatrixRepository(provider=_FlakyProvider(failures=0))
    repo.load()
    _install_loader(monkeypatch, repo)
    with pytest.raises(HTTPException) as caught:
        optimization.optimize_route(_request(codes=("L1", "L2", "SECRET-CODE-42")))
    assert caught.value.status_code == 422
    assert "SECRET-CODE-42" not in str(caught.value.detail)
    assert caught.value.detail == "requested locations are missing from the travel-time matrix"


def test_h2_503_never_echoes_provider_error(monkeypatch):
    class _Leaky:
        def fetch_rows(self):
            raise RuntimeError("https://secret.supabase.co service-role-key-123")

    repo = TimeMatrixRepository(provider=_Leaky())
    repo.load()
    _install_loader(monkeypatch, repo)
    with pytest.raises(HTTPException) as caught:
        optimization.optimize_route(_request())
    assert caught.value.status_code == 503
    assert "secret" not in str(caught.value.detail).lower()
    assert "key" not in str(caught.value.detail).lower()


def test_h2_compare_without_matrix_is_redacted_503(monkeypatch):
    _install_loader(monkeypatch, TimeMatrixRepository(provider=None))
    request = schemas.CompareRequest(
        depot=schemas.LocationNode(id="D.Kampus", lat=41.0, lng=29.17),
        students=_request().students,
        algorithms=["ga_split"],
    )
    with pytest.raises(HTTPException) as caught:
        optimization.compare_algorithms(request)
    assert caught.value.status_code == 503
    assert caught.value.detail == "travel-time matrix unavailable"


# ------------------------------------- H.4: failed first load, no recovery


def test_h4_never_loaded_with_provider_is_stale():
    repo = TimeMatrixRepository(provider=_FlakyProvider(failures=1))
    repo.load()  # first load fails
    assert repo._loaded_at is None
    assert repo._is_cache_stale() is True


def test_h4_no_provider_is_not_stale():
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    assert repo._is_cache_stale() is False


def test_h4_failed_first_load_recovers_after_backoff_without_restart():
    clock = _Clock()
    provider = _FlakyProvider(failures=1)
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=clock)
    repo.load()
    assert provider.calls == 1

    # Inside the backoff window: fail closed, and no fetch storm.
    for _ in range(5):
        with pytest.raises(MatrixUnavailableError):
            repo.get_submatrix(["D.Kampus", "L1"])
    assert provider.calls == 1

    # Backoff expired and provider recovered: the next call heals the cache.
    clock.now = 601.0
    sub = repo.get_submatrix(["D.Kampus", "L1", "L2"])
    assert provider.calls == 2
    assert repo.health()["loaded"] is True
    assert sub[0][1] == 7 + 0 + 2 * 1
    assert all(sub[i][j] > 0 for i in range(3) for j in range(3) if i != j)


def test_h4_failed_first_load_keeps_failing_closed_while_provider_is_down():
    clock = _Clock()
    provider = _FlakyProvider(failures=99)
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=clock)
    repo.load()
    clock.now = 601.0
    with pytest.raises(MatrixUnavailableError):
        repo.get_submatrix(["D.Kampus", "L1"])
    assert provider.calls == 2  # retried once after the backoff, still down


def test_h4_unbound_optimize_recovers_after_provider_recovers(monkeypatch):
    clock = _Clock()
    provider = _FlakyProvider(failures=1)
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=clock)
    repo.load()
    _install_loader(monkeypatch, repo)

    with pytest.raises(HTTPException) as caught:
        optimization.optimize_route(_request())
    assert caught.value.status_code == 503

    clock.now = 601.0
    result = optimization.optimize_route(_request())
    assert result.success is True
    durations = [s.duration for r in result.routes for s in r.route_details]
    assert durations and all(d > 0 for d in durations)


def test_h4_force_refresh_bypasses_backoff_for_recovery():
    provider = _FlakyProvider(failures=1)
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=_Clock())
    repo.load()
    repo.refresh(force=True)
    assert repo.get_submatrix(["D.Kampus", "L1"])[0][1] > 0


# ------------------------------------------------ explicit opt-in fallback


@pytest.mark.parametrize("value", ["1", "true", "TRUE", " yes ", "Yes"])
def test_flag_truthy_values(monkeypatch, value):
    monkeypatch.setenv(FLAG, value)
    assert runtime_config.allow_coordinate_fallback() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "2", "maybe"])
def test_flag_falsy_and_unrecognised_values(monkeypatch, value):
    monkeypatch.setenv(FLAG, value)
    assert runtime_config.allow_coordinate_fallback() is False


def test_flag_default_is_false():
    assert runtime_config.allow_coordinate_fallback() is False


def test_opt_in_enables_euclidean_fallback_with_coordinates(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    matrix = repo.get_submatrix(["D.Kampus", "L1"], COORDS)
    assert matrix[0][1] > 0 and matrix[0][1] == matrix[1][0]


def test_opt_in_enables_haversine_fallback_with_geo_coords(monkeypatch):
    monkeypatch.setenv(FLAG, "yes")
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    matrix = repo.get_submatrix(["D.Kampus", "L1"], COORDS, geo_coords=True)
    assert matrix[0][1] > 0


def test_opt_in_without_coordinates_still_never_returns_zeros(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    with pytest.raises(MatrixSnapshotError):
        repo.get_submatrix(["A", "B"])


def test_opt_in_does_not_hide_unknown_codes_when_a_real_matrix_is_loaded(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    repo = TimeMatrixRepository(provider=_FlakyProvider(failures=0))
    repo.load()
    with pytest.raises(IncompleteTravelMatrixError):
        repo.get_submatrix(["D.Kampus", "NOT-IN-MATRIX"], COORDS)


def test_explicit_constructor_flag_overrides_env(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    repo = TimeMatrixRepository(provider=None, allow_coordinate_fallback=False)
    repo.load()
    with pytest.raises(MatrixSnapshotError):
        repo.get_submatrix(["D.Kampus", "L1"], COORDS)


def test_opt_in_split_strategy_runs_on_coordinates(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    _install_loader(monkeypatch, TimeMatrixRepository(provider=None))
    strategy = GASplitStrategy({"seed": 1, "population_size": 6, "max_iterations": 3})
    result = strategy.optimize(_request())
    durations = [s.duration for r in result.routes for s in r.route_details]
    assert result.success is True
    assert durations and all(d > 0 for d in durations)


# ------------------------------------------------------- startup validation


def _clean_startup_env(monkeypatch, app_env):
    monkeypatch.setenv("INTERNAL_API_KEY", "k")
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("UNIRIDE_TENANT_KEYS", raising=False)
    monkeypatch.setenv("APP_ENV", app_env)


def test_production_without_supabase_credentials_is_a_startup_error(monkeypatch):
    _clean_startup_env(monkeypatch, "production")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    with pytest.raises(SystemExit) as caught:
        runtime_config.validate_runtime_configuration()
    message = str(caught.value)
    assert "SUPABASE" in message


@pytest.mark.parametrize(
    "url,key", [("https://x.invalid", ""), ("", "service-key")]
)
def test_production_with_partial_credentials_is_a_startup_error(monkeypatch, url, key):
    _clean_startup_env(monkeypatch, "production")
    monkeypatch.setenv("SUPABASE_URL", url)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", key)
    with pytest.raises(SystemExit):
        runtime_config.validate_runtime_configuration()


def test_production_startup_error_never_prints_credential_values(monkeypatch):
    _clean_startup_env(monkeypatch, "production")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret-value")
    with pytest.raises(SystemExit) as caught:
        runtime_config.validate_runtime_configuration()
    assert "super-secret-value" not in str(caught.value)


def test_production_with_credentials_starts(monkeypatch):
    _clean_startup_env(monkeypatch, "production")
    monkeypatch.setenv("SUPABASE_URL", "https://x.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    runtime_config.validate_runtime_configuration()


def test_production_forbids_the_coordinate_fallback_opt_in(monkeypatch):
    _clean_startup_env(monkeypatch, "production")
    monkeypatch.setenv("SUPABASE_URL", "https://x.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv(FLAG, "1")
    with pytest.raises(SystemExit) as caught:
        runtime_config.validate_runtime_configuration()
    assert FLAG in str(caught.value)


def test_development_without_credentials_starts_and_fails_closed(monkeypatch):
    _clean_startup_env(monkeypatch, "development")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    runtime_config.validate_runtime_configuration()  # must not raise
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    with pytest.raises(MatrixUnavailableError):
        repo.get_submatrix(["D.Kampus", "L1"], COORDS)


# ------------------------------------------------ router status mapping


def test_invalid_stored_arc_is_a_503_not_a_422(monkeypatch):
    # Codes exist but a stored arc is zero: stored-data problem, not caller input.
    rows = [dict(row) for row in ROWS]
    rows[0]["duration_minutes"] = 0
    repo = TimeMatrixRepository(provider=type("P", (), {"fetch_rows": lambda self: rows})())
    repo.load()
    _install_loader(monkeypatch, repo)
    with pytest.raises(HTTPException) as caught:
        optimization.optimize_route(_request())
    assert caught.value.status_code == 503
    assert caught.value.detail == "travel-time matrix unavailable"


def test_compare_unknown_location_is_redacted_422(monkeypatch):
    repo = TimeMatrixRepository(provider=_FlakyProvider(failures=0))
    repo.load()
    _install_loader(monkeypatch, repo)
    request = schemas.CompareRequest(
        depot=schemas.LocationNode(id="D.Kampus", lat=41.0, lng=29.17),
        students=_request(codes=("L1", "SECRET-CODE-42")).students,
        algorithms=["ga_split"],
    )
    with pytest.raises(HTTPException) as caught:
        optimization.compare_algorithms(request)
    assert caught.value.status_code == 422
    assert "SECRET-CODE-42" not in str(caught.value.detail)


def test_bound_request_keeps_its_existing_fail_closed_response(monkeypatch):
    """A snapshot-bound request still gets the 200 binding failure, not a 503."""
    repo = TimeMatrixRepository(provider=_FlakyProvider(failures=0))
    repo.load()
    _install_loader(monkeypatch, repo)
    digest = repo.matrix_snapshot(["L1", "L2", "L3"], "D.Kampus")["sha256"]

    def _boom(self, request):
        raise MatrixUnavailableError()

    monkeypatch.setattr(GASplitStrategy, "optimize", _boom)
    request = _request()
    request.expected_matrix_sha256 = digest
    result = optimization.optimize_route(request)
    assert result.success is False
    assert result.feasibility_certificate.certify_error == "matrix snapshot unavailable or changed"


# ------------------------------------------- academic benchmark isolation


def test_academic_scope_uses_problem_coordinates_without_any_matrix():
    from utils.matrix_repository import academic_coordinate_scope

    coords = {"A": {"lat": 0.0, "lng": 0.0}, "B": {"lat": 3.0, "lng": 4.0}}
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    with academic_coordinate_scope():
        assert repo.get_submatrix(["A", "B"], coords) == [[0.0, 5.0], [5.0, 0.0]]
    # The scope ends with the block: operational lookups fail closed again.
    with pytest.raises(MatrixUnavailableError):
        repo.get_submatrix(["A", "B"], coords)


def test_academic_scope_does_not_need_the_stored_matrix_even_when_loaded():
    from utils.matrix_repository import academic_coordinate_scope

    repo = TimeMatrixRepository(provider=_FlakyProvider(failures=0))
    repo.load()
    coords = {"loc_1": {"lat": 0.0, "lng": 0.0}, "loc_2": {"lat": 3.0, "lng": 4.0}}
    with academic_coordinate_scope():
        assert repo.get_submatrix(["loc_1", "loc_2"], coords) == [[0.0, 5.0], [5.0, 0.0]]
    with pytest.raises(IncompleteTravelMatrixError):
        repo.get_submatrix(["loc_1", "loc_2"], coords)


def test_benchmark_runner_runs_production_strategies_on_problem_coordinates(monkeypatch):
    """The legacy /benchmark runner (TSPLIB coordinates) keeps working with no matrix."""
    from benchmark_runner import AlgorithmConfig, BenchmarkRunner
    from uniride_core.models import ProblemInstance

    _install_loader(monkeypatch, TimeMatrixRepository(provider=None))
    problem = ProblemInstance(
        name="tiny4",
        dimension=4,
        problem_type="tsp",
        edge_weight_type="EUC_2D",
        category="small",
        coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        depot_index=0,
    )
    runner = BenchmarkRunner()
    result = runner._run_single_experiment(
        problem, AlgorithmConfig(name="greedy", algorithm_id="greedy"), 1
    )
    assert result.tour_length == pytest.approx(40.0)


# ---------------------------------------- exponential failed-load backoff


def _down_repo(ttl=600, base=None, failures=99):
    clock = _Clock()
    provider = _FlakyProvider(failures=failures)
    kwargs = {} if base is None else {"retry_base_seconds": base}
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=ttl, clock=clock, **kwargs)
    repo.load()  # failure 1 at t=0
    return repo, provider, clock


def _attempt(repo):
    try:
        repo.get_submatrix(["D.Kampus", "L1"])
    except MatrixUnavailableError:
        pass


def test_backoff_first_retry_after_30_seconds_by_default():
    repo, provider, clock = _down_repo()
    clock.now = 29.9
    _attempt(repo)
    assert provider.calls == 1  # still inside the 30 s window
    clock.now = 30.0
    _attempt(repo)
    assert provider.calls == 2


def test_backoff_doubles_after_each_consecutive_failure():
    repo, provider, clock = _down_repo()
    clock.now = 30.0
    _attempt(repo)  # failure 2 -> next window 60 s
    assert provider.calls == 2
    clock.now = 89.9
    _attempt(repo)
    assert provider.calls == 2
    clock.now = 90.0
    _attempt(repo)  # failure 3 -> next window 120 s
    assert provider.calls == 3
    clock.now = 209.9
    _attempt(repo)
    assert provider.calls == 3
    clock.now = 210.0
    _attempt(repo)
    assert provider.calls == 4


def test_backoff_is_capped_at_the_ttl():
    repo, provider, clock = _down_repo(ttl=100)
    waits = []
    for _ in range(6):
        waits.append(repo._next_retry_at - clock.now)
        clock.now = repo._next_retry_at
        _attempt(repo)
    assert waits == [30, 60, 100, 100, 100, 100]


def test_backoff_resets_after_a_successful_load():
    repo, provider, clock = _down_repo(failures=3)  # fails at t=0, then twice more
    clock.now = 30.0
    _attempt(repo)  # failure 2
    clock.now = 90.0
    _attempt(repo)  # failure 3
    assert repo._consecutive_failures == 3
    clock.now = 210.0
    repo.get_submatrix(["D.Kampus", "L1"])  # success
    assert repo.health()["loaded"] is True
    assert repo._consecutive_failures == 0
    assert repo._next_retry_at is None
    # A later refresh failure starts again at the base (30 s), not at 240 s.
    provider.failures = 99
    clock.now = 210.0 + 601.0  # TTL expired
    repo.refresh()
    assert repo._next_retry_at - clock.now == 30.0


def test_backoff_base_is_configurable():
    repo, provider, clock = _down_repo(base=5)
    assert repo._next_retry_at == 5
    clock.now = 5.0
    _attempt(repo)
    assert repo._next_retry_at - clock.now == 10


def test_backoff_base_env_is_parsed_like_the_ttl_env(monkeypatch):
    class _DL(DataLoader):
        pass

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("TIME_MATRIX_RETRY_BASE_SECONDS", "7")
    assert _DL().repository._retry_base_seconds == 7

    class _DL2(DataLoader):
        pass

    monkeypatch.setenv("TIME_MATRIX_RETRY_BASE_SECONDS", "garbage")
    assert _DL2().repository._retry_base_seconds == 30
    class _DL3(DataLoader):
        pass

    monkeypatch.delenv("TIME_MATRIX_RETRY_BASE_SECONDS")
    assert _DL3().repository._retry_base_seconds == 30


def test_backoff_allows_one_fetch_per_window_under_concurrency():
    import threading

    repo, provider, clock = _down_repo()
    clock.now = 30.0
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        _attempt(repo)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert provider.calls == 2  # initial load + exactly one retry
