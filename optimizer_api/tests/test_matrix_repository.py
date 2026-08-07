"""Tests for the injectable matrix repository and the DataLoader delegation."""

from utils.matrix_repository import TimeMatrixRepository
from utils.data_loader import DataLoader, euclidean_distance


class _FakeProvider:
    def __init__(self, rows=None):
        self.calls = 0
        self.rows = rows or [
            {"origin_code": "A", "destination_code": "B", "duration_minutes": 5},
            {"origin_code": "B", "destination_code": "A", "duration_minutes": 6},
            {"origin_code": "C", "destination_code": "A", "duration_minutes": 8},
        ]

    def fetch_rows(self):
        self.calls += 1
        return self.rows


class _FailingProvider:
    def fetch_rows(self):
        raise RuntimeError("boom")


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


# ------------------------------------------------------------------- build/lookup


def test_provider_rows_build_submatrix():
    repo = _build_repo()
    repo.load()
    sub = repo.get_submatrix(["A", "B", "C"])
    assert sub == [
        [0.0, 5.0, 0.0],
        [6.0, 0.0, 0.0],
        [8.0, 0.0, 0.0],
    ]


def test_get_duration_and_has_location():
    repo = _build_repo()
    repo.load()
    assert repo.get_duration("A", "B") == 5.0
    assert repo.get_duration("B", "A") == 6.0
    assert repo.get_duration("A", "C") == 0.0
    assert repo.has_location("A")
    assert not repo.has_location("Z")


# ----------------------------------------------------------------------- health


def test_health_fresh_after_load():
    repo = _build_repo()
    repo.load()
    health = repo.health()
    assert health["loaded"] is True
    assert health["stale"] is False
    assert health["age_seconds"] == 0
    assert health["locations"] == 3
    assert health["edges"] == 3
    assert health["last_error"] is None
    assert health["source"] == "supabase"


def test_ttl_staleness_with_injected_clock():
    clock = _MutableClock()
    repo = _build_repo(clock=clock)
    repo.load()
    assert repo.health()["stale"] is False
    clock.advance(60)
    assert repo.health()["stale"] is False
    clock.advance(541)
    assert repo.health()["stale"] is True


def test_coordinate_fallback_health_when_no_provider():
    repo = _build_repo(provider=None)
    repo.load()
    health = repo.health()
    assert health["loaded"] is False
    assert health["source"] == "coordinates"
    assert health["locations"] == 0


# ---------------------------------------------------------------- refresh/force


def test_refresh_reloads_when_stale_or_forced():
    clock = _MutableClock()
    provider = _FakeProvider()
    repo = _build_repo(provider=provider, clock=clock)
    repo.load()
    assert provider.calls == 1
    repo.refresh()
    assert provider.calls == 1  # not stale -> no reload
    clock.advance(601)
    repo.refresh()
    assert provider.calls == 2  # stale -> reload
    repo.refresh(force=True)
    assert provider.calls == 3  # force -> reload


# ----------------------------------------------------------- fallback + lifecycle


def test_missing_provider_uses_coordinate_fallback():
    repo = _build_repo(provider=None)
    repo.load()
    assert repo._use_coordinates is True
    assert repo.time_matrix is None
    assert repo.get_submatrix(["A", "B"]) == [[0.0, 0.0], [0.0, 0.0]]


def test_failing_provider_falls_back_and_records_error():
    repo = _build_repo(provider=_FailingProvider())
    repo.load()
    assert repo._use_coordinates is True
    assert repo.time_matrix is None
    assert "boom" in (repo.health()["last_error"] or "")
    assert repo.health()["source"] == "empty"


def test_close_clears_state():
    repo = _build_repo()
    repo.load()
    assert repo.health()["loaded"] is True
    repo.close()
    assert repo.time_matrix is None
    assert repo.health()["loaded"] is False
    assert repo.get_duration("A", "B") == 0.0


# -------------------------------------------------------------------- DataLoader


def _make_delegating_loader():
    class _DL(DataLoader):
        pass

    return _DL, _build_repo()


def test_data_loader_delegates_to_repository():
    _DL, repo = _make_delegating_loader()
    repo.load()
    loader = _DL(repository=repo)
    assert loader.repository is repo
    assert loader.get_duration("A", "B") == 5.0
    assert loader.has_location("C")
    assert loader.health() == repo.health()


def test_data_loader_get_submatrix_uses_delegated_repository():
    _DL, repo = _make_delegating_loader()
    repo.load()
    loader = _DL(repository=repo)
    assert loader.get_submatrix(["A", "B", "C"]) == repo.get_submatrix(["A", "B", "C"])


def test_data_loader_static_builders_unchanged():
    coordinates = {"a": {"lat": 0.0, "lng": 0.0}, "b": {"lat": 3.0, "lng": 4.0}}
    expected = [[0.0, 5.0], [5.0, 0.0]]
    assert DataLoader.build_euclidean_matrix(["a", "b"], coordinates) == expected
    assert TimeMatrixRepository.build_euclidean_matrix(["a", "b"], coordinates) == expected


def test_euclidean_distance_backcompat():
    assert euclidean_distance(0.0, 0.0, 3.0, 4.0) == 5.0


# ------------------------------------------------------------------- seam/DDL


def test_singleton_injection_seam_preserves_global_after_resolution():
    _DL, repo = _make_delegating_loader()
    inst = _DL(repository=repo)
    assert _DL() is inst  # singleton slot filled after first construction