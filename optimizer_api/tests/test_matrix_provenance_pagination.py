"""MT2 (partial): matrix provenance in responses and paginated time_matrix fetch.

Offline: no network, no Supabase, no ``.env`` loading.
"""

import os

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from datetime import datetime

import pytest

from models import schemas
from routers import optimization
from utils.data_loader import DataLoader
from utils.matrix_repository import (
    TIME_MATRIX_PAGE_SIZE,
    SupabaseTimeMatrixProvider,
    TimeMatrixRepository,
    matrix_sha256,
)
from utils.patterns import SingletonMeta

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
LOADED_AT = 1_800_000_000.0


class _Provider:
    def fetch_rows(self):
        return [dict(row) for row in ROWS]


class _Clock:
    def __init__(self, now=LOADED_AT):
        self.now = now

    def __call__(self):
        return self.now


def _loaded_repository(clock=None):
    clock = clock or _Clock()
    repo = TimeMatrixRepository(provider=_Provider(), ttl_seconds=600, clock=clock)
    repo.load()
    clock.now = LOADED_AT + 12.5
    return repo


def _install(monkeypatch, repo):
    monkeypatch.setattr(SingletonMeta, "_instances", {})
    return DataLoader(repository=repo)


def _request(**extra):
    return schemas.OptimizationRequest(
        algorithm="ga_split",
        depot=schemas.LocationNode(id="D.Kampus", lat=41.0, lng=29.17),
        students=[
            schemas.StudentNode(
                id=f"S{i}",
                name=f"S{i}",
                location_code=code,
                disability_type="So",
                coordinates=COORDS[code],
            )
            for i, code in enumerate(("L1", "L2", "L3"), start=1)
        ],
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=60,
        ga_config={"population_size": 6, "max_iterations": 3, "seed": 1},
        **extra,
    )


# ------------------------------------------------------------- pagination


class _FakeQuery:
    def __init__(self, table_rows, calls):
        self._rows = table_rows
        self._calls = calls
        self._range = None

    def select(self, _columns):
        return self

    def order(self, _column):
        return self

    def range(self, start, end):
        self._range = (start, end)
        self._calls.append((start, end))
        return self

    def execute(self):
        start, end = self._range
        return type("Resp", (), {"data": self._rows[start : end + 1]})()


class _FakeClient:
    def __init__(self, table_rows):
        self.rows = table_rows
        self.calls = []

    def table(self, name):
        assert name == "time_matrix"
        return _FakeQuery(self.rows, self.calls)


def _provider_with(monkeypatch, n_rows):
    rows = [
        {"origin_code": f"O{i}", "destination_code": f"T{i}", "duration_minutes": 1.0 + i}
        for i in range(n_rows)
    ]
    client = _FakeClient(rows)
    provider = SupabaseTimeMatrixProvider("http://unused.invalid", "unused-key")
    monkeypatch.setattr(provider, "_build_client", lambda _create: client)
    # the lazy ``from supabase import create_client`` must be importable
    pytest.importorskip("supabase")
    return provider, client, rows


def test_fetch_rows_pages_past_the_postgrest_row_cap(monkeypatch):
    provider, client, rows = _provider_with(monkeypatch, 2500)
    fetched = provider.fetch_rows()
    assert TIME_MATRIX_PAGE_SIZE == 1000
    assert fetched == rows
    assert client.calls == [(0, 999), (1000, 1999), (2000, 2999)]


def test_fetch_rows_exact_page_multiple_ends_on_empty_page(monkeypatch):
    provider, client, rows = _provider_with(monkeypatch, 2000)
    assert provider.fetch_rows() == rows
    assert client.calls[-1] == (2000, 2999)


def test_fetch_rows_small_table_is_a_single_request(monkeypatch):
    provider, client, rows = _provider_with(monkeypatch, 812)
    assert len(provider.fetch_rows()) == 812
    assert client.calls == [(0, 999)]


def test_fetch_rows_empty_table_still_raises(monkeypatch):
    provider, _client, _rows = _provider_with(monkeypatch, 0)
    with pytest.raises(RuntimeError, match="empty"):
        provider.fetch_rows()


# ------------------------------------------------------------- provenance


def test_repository_matrix_provenance_is_redaction_safe():
    repo = _loaded_repository()
    provenance = repo.matrix_provenance()
    assert set(provenance) == {
        "source", "sha256", "location_count", "loaded_at", "age_seconds",
    }
    assert provenance["source"] == "supabase"
    assert provenance["sha256"] == matrix_sha256(repo.locations, repo.time_matrix)
    assert provenance["location_count"] == len(CODES)
    assert provenance["age_seconds"] == 12.5
    parsed = datetime.fromisoformat(provenance["loaded_at"])
    assert parsed.utcoffset().total_seconds() == 0
    assert parsed.timestamp() == LOADED_AT


def test_optimize_response_carries_matrix_provenance(monkeypatch):
    repo = _loaded_repository()
    _install(monkeypatch, repo)
    result = optimization.optimize_route(_request())
    assert result.success is True
    provenance = result.matrix_provenance
    assert provenance is not None
    assert provenance.source == "supabase"
    assert provenance.sha256 == matrix_sha256(repo.locations, repo.time_matrix)
    assert provenance.location_count == len(CODES)
    assert provenance.age_seconds == 12.5
    dumped = result.model_dump_json()
    assert "unused-key" not in dumped and "http" not in provenance.model_dump_json()


def test_snapshot_bound_response_provenance_matches_the_binding(monkeypatch):
    repo = _loaded_repository()
    _install(monkeypatch, repo)
    snapshot = repo.matrix_snapshot(["L1", "L2", "L3"], "D.Kampus")
    result = optimization.optimize_route(
        _request(expected_matrix_sha256=snapshot["sha256"])
    )
    assert result.success is True
    assert result.matrix_provenance.sha256 == snapshot["sha256"]
    assert result.matrix_provenance.location_count == len(CODES)


def test_vehicle_calculator_response_carries_provenance(monkeypatch):
    repo = _loaded_repository()
    _install(monkeypatch, repo)
    result = optimization.calculate_vehicles(_request())
    assert result.matrix_provenance is not None
    assert result.matrix_provenance.sha256 == matrix_sha256(
        repo.locations, repo.time_matrix
    )


def test_compare_response_carries_provenance(monkeypatch):
    repo = _loaded_repository()
    _install(monkeypatch, repo)
    base = _request()
    request = schemas.CompareRequest(
        students=base.students,
        depot=base.depot,
        max_travel_time=60,
        algorithms=["ga_split"],
    )
    response = optimization.compare_algorithms(request)
    expected = matrix_sha256(repo.locations, repo.time_matrix)
    assert response.matrix_provenance is not None
    assert response.matrix_provenance.sha256 == expected
    assert all(r.matrix_provenance.sha256 == expected for r in response.results)


def test_provenance_field_is_optional_for_existing_clients():
    parsed = schemas.OptimizationResponse.model_validate(
        {"algorithm_used": "x", "success": False, "routes": []}
    )
    assert parsed.matrix_provenance is None
