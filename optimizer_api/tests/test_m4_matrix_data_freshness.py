"""M4 / MT2 staleness half, data freshness (owner decision 2026-10-15, DECISION_LOG T09).

The matrix LOAD age is ~0 s because the snapshot step refreshes first. The age that
matters is the age of the travel-time DATA: ``max(time_matrix.updated_at)`` over the
loaded rows, exposed as ``data_updated_at`` / ``data_age_seconds`` in the provenance.

Rules pinned here:
- the column is optional: a database without ``updated_at`` (migration not applied) still
  loads, with both fields null and nothing else changed;
- the C2 fail-closed gate (MatrixStaleError / MatrixSnapshotError) is untouched: an old
  DATA timestamp never blocks and a missing one never weakens the gate;
- pagination stays intact when the column is present or absent.

Offline: no network, no Supabase, no ``.env`` loading.
"""

import os

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from datetime import datetime, timezone

import pytest

from utils import matrix_repository
from utils.matrix_repository import (
    TIME_MATRIX_PAGE_SIZE,
    MatrixSnapshotError,
    SupabaseTimeMatrixProvider,
    TimeMatrixRepository,
)

LOADED_AT = 1_800_000_000.0
# 2026-03-05T10:00:00Z, i.e. a data timestamp much older than the load time above
OLD = datetime(2026, 3, 5, 10, 0, 0, tzinfo=timezone.utc)
NEW = datetime(2026, 3, 6, 11, 30, 0, tzinfo=timezone.utc)


def _row(origin, destination, minutes, updated_at=None, key=True):
    row = {"origin_code": origin, "destination_code": destination, "duration_minutes": minutes}
    if key:
        row["updated_at"] = updated_at
    return row


class _Clock:
    def __init__(self, now=LOADED_AT):
        self.now = now

    def __call__(self):
        return self.now


class _Provider:
    def __init__(self, rows):
        self.rows = rows

    def fetch_rows(self):
        return [dict(row) for row in self.rows]


def _repo(rows, clock=None, ttl=600):
    clock = clock or _Clock()
    repo = TimeMatrixRepository(provider=_Provider(rows), ttl_seconds=ttl, clock=clock)
    repo.load()
    return repo, clock


# ---------------------------------------------------------------- provenance


def test_provenance_carries_max_updated_at_and_data_age():
    rows = [
        _row("D.Kampus", "Sw1", 9, "2026-03-05T10:00:00+00:00"),
        _row("Sw1", "D.Kampus", 10, "2026-03-06T11:30:00.123456+00:00"),
        _row("Sw1", "Sw2", 4, "2026-03-05T12:00:00Z"),
    ]
    repo, clock = _repo(rows)
    clock.now = LOADED_AT + 100

    provenance = repo.matrix_provenance()

    assert datetime.fromisoformat(provenance["data_updated_at"]) == NEW.replace(microsecond=123456)
    assert provenance["data_updated_at"].endswith("+00:00")
    expected_age = LOADED_AT + 100 - NEW.replace(microsecond=123456).timestamp()
    assert provenance["data_age_seconds"] == pytest.approx(expected_age, abs=0.001)
    # the load age is unchanged and independent of the data age
    assert provenance["age_seconds"] == 100.0
    assert provenance["data_age_seconds"] > provenance["age_seconds"]


def test_data_age_is_not_blocked_by_an_old_data_timestamp():
    """Months-old data is shown, never turned into a stale error (T09)."""
    rows = [_row("D.Kampus", "Sw1", 9, "2026-03-05T10:00:00+00:00"),
            _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00+00:00")]
    repo, _clock = _repo(rows)

    snapshot = repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")

    assert snapshot["provenance"]["data_age_seconds"] > 86400 * 30
    assert snapshot["provenance"]["refresh_failed"] is False


def test_column_missing_gives_null_fields_and_unchanged_provenance_otherwise():
    rows = [_row("D.Kampus", "Sw1", 9, key=False), _row("Sw1", "D.Kampus", 10, key=False)]
    repo, clock = _repo(rows)
    clock.now = LOADED_AT + 12.5

    provenance = repo.matrix_provenance()

    assert provenance["data_updated_at"] is None
    assert provenance["data_age_seconds"] is None
    assert provenance["age_seconds"] == 12.5
    assert provenance["refresh_failed"] is False
    assert repo.get_duration("D.Kampus", "Sw1") == 9.0


@pytest.mark.parametrize("value", [None, "", "not-a-date", 12345])
def test_unusable_timestamps_give_null_fields(value):
    rows = [_row("D.Kampus", "Sw1", 9, value), _row("Sw1", "D.Kampus", 10, value)]
    repo, _clock = _repo(rows)

    provenance = repo.matrix_provenance()

    assert provenance["data_updated_at"] is None
    assert provenance["data_age_seconds"] is None


def test_unusable_rows_are_ignored_and_the_usable_maximum_is_kept():
    rows = [_row("D.Kampus", "Sw1", 9, None), _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00+00:00"),
            _row("Sw1", "Sw2", 4, "garbage")]
    repo, _clock = _repo(rows)

    assert datetime.fromisoformat(repo.matrix_provenance()["data_updated_at"]) == OLD


def test_naive_timestamp_is_read_as_utc():
    rows = [_row("D.Kampus", "Sw1", 9, "2026-03-05T10:00:00"), _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00")]
    repo, _clock = _repo(rows)

    assert datetime.fromisoformat(repo.matrix_provenance()["data_updated_at"]) == OLD


def test_data_timestamp_follows_the_reloaded_rows():
    """A refresh that finds newer rows moves the timestamp; a clear resets it."""
    rows = [_row("D.Kampus", "Sw1", 9, "2026-03-05T10:00:00+00:00"),
            _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00+00:00")]
    provider = _Provider(rows)
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=_Clock())
    repo.load()
    provider.rows = [_row("D.Kampus", "Sw1", 9, "2026-03-06T11:30:00+00:00"),
                     _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00+00:00")]
    repo.refresh(force=True)
    assert datetime.fromisoformat(repo.matrix_provenance()["data_updated_at"]) == NEW

    repo.close()
    repo.load()
    assert datetime.fromisoformat(repo.matrix_provenance()["data_updated_at"]) == NEW


# ---------------------------------------------------------------- C2 gate


def test_gate_is_unchanged_with_and_without_the_column():
    for with_column in (True, False):
        rows = [_row("D.Kampus", "Sw1", 9, "2026-03-05T10:00:00+00:00", key=with_column),
                _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00+00:00", key=with_column)]
        repo, clock = _repo(rows)
        clock.now = LOADED_AT + 601  # past the TTL, no refresh in this call

        with pytest.raises(matrix_repository.MatrixStaleError, match="matrix is stale"):
            repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")


def test_kept_matrix_after_failed_refresh_is_still_refused():
    rows = [_row("D.Kampus", "Sw1", 9, "2026-03-05T10:00:00+00:00"),
            _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00+00:00")]

    class _Flaky:
        calls = 0

        def fetch_rows(self):
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("down")
            return [dict(row) for row in rows]

    repo = TimeMatrixRepository(provider=_Flaky(), ttl_seconds=600, clock=_Clock())
    repo.load()
    repo.refresh(force=True)  # fails; the last-known-good matrix is kept

    with pytest.raises(MatrixSnapshotError) as caught:
        repo.matrix_snapshot(["Sw1"], depot_code="D.Kampus")
    assert isinstance(caught.value, matrix_repository.MatrixStaleError)
    assert repo.matrix_provenance()["refresh_failed"] is True
    assert repo.matrix_provenance()["data_updated_at"] is not None


def test_snapshot_digest_ignores_the_data_timestamp():
    """The content address covers the arcs only; a touched timestamp must not change it."""
    first, _ = _repo([_row("D.Kampus", "Sw1", 9, "2026-03-05T10:00:00+00:00"),
                      _row("Sw1", "D.Kampus", 10, "2026-03-05T10:00:00+00:00")])
    second, _ = _repo([_row("D.Kampus", "Sw1", 9, "2026-03-06T10:00:00+00:00"),
                       _row("Sw1", "D.Kampus", 10, "2026-03-06T10:00:00+00:00")])

    assert first.matrix_snapshot(["Sw1"], "D.Kampus")["sha256"] == second.matrix_snapshot(["Sw1"], "D.Kampus")["sha256"]


# ---------------------------------------------------------------- provider


class _FakeQuery:
    def __init__(self, client):
        self._client = client
        self._columns = None
        self._range = None

    def select(self, columns):
        self._columns = columns
        return self

    def order(self, _column):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        self._client.selects.append(self._columns)
        self._client.calls.append(self._range)
        if "updated_at" in self._columns and self._client.error is not None:
            raise self._client.error
        start, end = self._range
        data = self._client.rows[start : end + 1]
        if "updated_at" not in self._columns:
            data = [{k: v for k, v in row.items() if k != "updated_at"} for row in data]
        return type("Resp", (), {"data": data})()


class _FakeClient:
    def __init__(self, rows, error=None):
        self.rows = rows
        self.error = error
        self.selects = []
        self.calls = []

    def table(self, name):
        assert name == "time_matrix"
        return _FakeQuery(self)


def _provider(monkeypatch, n_rows, error=None):
    pytest.importorskip("supabase")
    rows = [
        {"origin_code": f"O{i}", "destination_code": f"T{i}", "duration_minutes": 1.0 + i,
         "updated_at": "2026-03-05T10:00:00+00:00"}
        for i in range(n_rows)
    ]
    client = _FakeClient(rows, error)
    provider = SupabaseTimeMatrixProvider("http://unused.invalid", "unused-key")
    monkeypatch.setattr(provider, "_build_client", lambda _create: client)
    return provider, client, rows


def _undefined_column_error():
    from postgrest.exceptions import APIError

    return APIError({"message": "column time_matrix.updated_at does not exist",
                     "code": "42703", "hint": None, "details": None})


def test_provider_selects_updated_at_and_keeps_pagination(monkeypatch):
    provider, client, rows = _provider(monkeypatch, 2500)

    fetched = provider.fetch_rows()

    assert fetched == rows
    assert TIME_MATRIX_PAGE_SIZE == 1000
    assert client.calls == [(0, 999), (1000, 1999), (2000, 2999)]
    assert all("updated_at" in columns for columns in client.selects)


def test_provider_falls_back_when_the_column_does_not_exist(monkeypatch):
    provider, client, rows = _provider(monkeypatch, 2500, error=_undefined_column_error())

    fetched = provider.fetch_rows()

    assert len(fetched) == 2500
    assert all("updated_at" not in row for row in fetched)
    # the old select is used for every page after the fallback, paging unchanged
    assert [c for c in client.selects if "updated_at" not in c] == [client.selects[-1]] * 3
    assert client.calls[-3:] == [(0, 999), (1000, 1999), (2000, 2999)]


def test_provider_fallback_loads_a_working_matrix_with_null_data_age(monkeypatch):
    provider, _client, _rows = _provider(monkeypatch, 6, error=_undefined_column_error())
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=_Clock())

    repo.load()

    assert repo.health()["loaded"] is True
    assert repo.matrix_provenance()["data_updated_at"] is None
    assert repo.matrix_provenance()["data_age_seconds"] is None


def test_provider_does_not_swallow_other_errors(monkeypatch):
    """Only an undefined-column error falls back; any other failure still propagates."""
    from postgrest.exceptions import APIError

    other = APIError({"message": "permission denied for table time_matrix", "code": "42501",
                      "hint": None, "details": None})
    provider, _client, _rows = _provider(monkeypatch, 5, error=other)

    with pytest.raises(APIError):
        provider.fetch_rows()


def test_undefined_column_error_for_another_column_is_not_a_missing_updated_at(monkeypatch):
    """42703 alone is not enough: only an error that names ``updated_at`` triggers the fallback.

    A different undefined column (e.g. a renamed ``duration_minutes``) is a real schema
    problem; it must propagate and the load must fail closed, not be papered over by
    silently retrying without ``updated_at``.
    """
    from postgrest.exceptions import APIError

    other_column = APIError({"message": "column time_matrix.duration_minutes does not exist",
                             "code": "42703", "hint": None, "details": None})
    provider, client, _rows = _provider(monkeypatch, 5, error=other_column)
    with pytest.raises(APIError, match="duration_minutes"):
        provider.fetch_rows()
    assert len(client.selects) == 1  # no retry with the base columns

    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=_Clock())
    repo.load()
    assert repo.health()["loaded"] is False
    with pytest.raises(matrix_repository.MatrixUnavailableError):
        repo.matrix_provenance()


def test_failed_first_load_with_other_error_still_fails_closed(monkeypatch):
    from postgrest.exceptions import APIError

    other = APIError({"message": "boom", "code": "XX000", "hint": None, "details": None})
    provider, _client, _rows = _provider(monkeypatch, 5, error=other)
    repo = TimeMatrixRepository(provider=provider, ttl_seconds=600, clock=_Clock())

    repo.load()

    assert repo.health()["loaded"] is False
    with pytest.raises(matrix_repository.MatrixUnavailableError):
        repo.matrix_provenance()


def test_empty_table_still_raises_with_the_column(monkeypatch):
    provider, _client, _rows = _provider(monkeypatch, 0)
    with pytest.raises(RuntimeError, match="empty"):
        provider.fetch_rows()


def test_response_schema_accepts_the_new_fields_and_stays_optional():
    from models import schemas

    old = schemas.MatrixProvenanceInfo.model_validate(
        {"source": "supabase", "sha256": "a" * 64, "location_count": 2})
    assert old.data_updated_at is None and old.data_age_seconds is None
    new = schemas.MatrixProvenanceInfo.model_validate(
        {"source": "supabase", "sha256": "a" * 64, "location_count": 2,
         "data_updated_at": "2026-03-05T10:00:00+00:00", "data_age_seconds": 123.5})
    assert new.data_updated_at == "2026-03-05T10:00:00+00:00"
    assert new.data_age_seconds == 123.5
