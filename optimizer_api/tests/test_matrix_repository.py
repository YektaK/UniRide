"""Tests for the injectable matrix repository and the DataLoader delegation."""

import pytest

from utils.matrix_repository import (
    IncompleteTravelMatrixError,
    SupabaseTimeMatrixProvider,
    TimeMatrixRepository,
)
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


class _CompleteProvider(_FakeProvider):
    """Full directed 3x3 matrix so submatrix lookups never hit a missing arc."""

    def __init__(self):
        rows = [
            {"origin_code": a, "destination_code": b, "duration_minutes": d}
            for a, b, d in [
                ("A", "A", 0), ("A", "B", 5), ("A", "C", 3),
                ("B", "A", 6), ("B", "B", 0), ("B", "C", 7),
                ("C", "A", 8), ("C", "B", 4), ("C", "C", 0),
            ]
        ]
        super().__init__(rows=rows)


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
    repo = _build_repo(provider=_CompleteProvider())
    repo.load()
    sub = repo.get_submatrix(["A", "B", "C"])
    assert sub == [
        [0.0, 5.0, 3.0],
        [6.0, 0.0, 7.0],
        [8.0, 4.0, 0.0],
    ]


def test_get_duration_and_has_location():
    repo = _build_repo(provider=_CompleteProvider())
    repo.load()
    assert repo.get_duration("A", "B") == 5.0
    assert repo.get_duration("B", "A") == 6.0
    assert repo.get_duration("A", "C") == 3.0
    assert repo.has_location("A")
    assert not repo.has_location("Z")


def test_missing_arc_raises():
    repo = _build_repo()  # partial: C->A only among C pairs
    repo.load()
    with pytest.raises(IncompleteTravelMatrixError):
        repo.get_duration("A", "C")
    with pytest.raises(IncompleteTravelMatrixError):
        repo.get_duration("Z", "A")
    with pytest.raises(IncompleteTravelMatrixError):
        repo.get_submatrix(["A", "B", "C"])


def test_zero_or_negative_arc_raises():
    provider = _FakeProvider(rows=[
        {"origin_code": "A", "destination_code": "B", "duration_minutes": 0},
        {"origin_code": "B", "destination_code": "A", "duration_minutes": 5},
        {"origin_code": "B", "destination_code": "C", "duration_minutes": -1},
    ])
    repo = _build_repo(provider=provider)
    repo.load()
    with pytest.raises(IncompleteTravelMatrixError):
        repo.get_duration("A", "B")
    with pytest.raises(IncompleteTravelMatrixError):
        repo.get_duration("B", "C")
    assert repo.get_duration("B", "A") == 5.0


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


def _make_delegating_loader(provider=_DEFAULT):
    class _DL(DataLoader):
        pass

    return _DL, _build_repo(provider=provider)


def test_data_loader_delegates_to_repository():
    _DL, repo = _make_delegating_loader()
    repo.load()
    loader = _DL(repository=repo)
    assert loader.repository is repo
    assert loader.get_duration("A", "B") == 5.0
    assert loader.has_location("C")
    assert loader.health() == repo.health()


def test_data_loader_get_submatrix_uses_delegated_repository():
    _DL, repo = _make_delegating_loader(provider=_CompleteProvider())
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


# ------------------------------------------------- provider timeout + last-known-good


class _FailingAfterProvider(_FakeProvider):
    """Succeeds once (full matrix), then fails on every subsequent fetch."""

    def __init__(self):
        _FakeProvider.__init__(self, rows=_CompleteProvider().rows)
        self._n = 0

    def fetch_rows(self):
        self._n += 1
        if self._n > 1:
            raise RuntimeError("boom")
        return _FakeProvider.fetch_rows(self)


def test_last_known_good_matrix_survives_failed_refresh():
    clock = _MutableClock()
    repo = _build_repo(provider=_FailingAfterProvider(), clock=clock)
    repo.load()
    assert repo.health()["loaded"] is True
    submatrix = repo.get_submatrix(["A", "B", "C"])
    clock.advance(601)
    repo.refresh()  # stale -> triggers a failing fetch
    health = repo.health()
    assert health["loaded"] is True  # matrix kept, not cleared
    assert health["stale"] is True
    assert "boom" in (health["last_error"] or "")
    assert repo.get_submatrix(["A", "B", "C"]) == submatrix  # LKG unchanged


def test_first_load_failure_still_falls_back():
    repo = _build_repo(provider=_FailingProvider())
    repo.load()
    assert repo.health()["loaded"] is False
    assert repo.time_matrix is None


def test_provider_timeout_plumbed_into_sdk_client(monkeypatch):
    pytest.importorskip("supabase")
    captured = {}

    class _FakeClient:
        def __init__(self, url, key, **kwargs):
            captured["url"] = url
            captured["key"] = key
            captured["kwargs"] = kwargs

        def table(self, _name):
            return self

        def select(self, _cols):
            return self

        def execute(self):
            return type("Resp", (), {"data": [{
                "origin_code": "A", "destination_code": "B", "duration_minutes": 5}]})()

    fake_create = lambda *a, **k: _FakeClient(*a, **k)  # noqa: E731
    provider = SupabaseTimeMatrixProvider("https://x", "k", timeout_seconds=7.5)
    rows = (
        provider._build_client(fake_create)
        .table("time_matrix")
        .select("origin_code, destination_code, duration_minutes")
        .execute()
        .data
    )
    assert rows == [{
        "origin_code": "A", "destination_code": "B", "duration_minutes": 5}]
    assert captured["url"] == "https://x"
    options = captured["kwargs"].get("options")
    assert options is not None and options.postgrest_client_timeout == 7.5