"""H6: the async readiness handlers must not block the event loop.

``/readiness/time-matrix`` and ``/matrix-snapshot`` refresh the matrix through
a synchronous Supabase fetch. While that fetch runs, a cheap concurrent request
(here a trivial ``/health`` route on the same app) must still be served
promptly. The fake provider sleeps synchronously, like supabase-py/httpx does.
"""

import threading
import time

import anyio
import httpx
import pytest
from fastapi import FastAPI

from optimizer_api.routers import readiness
from utils.matrix_repository import TimeMatrixRepository

FETCH_SECONDS = 1.5
MAX_HEALTH_SECONDS = 0.5
KEY = "h6-shared-key"

ROWS = [
    {"origin_code": "D.Kampus", "destination_code": "Sw1", "duration_minutes": 9},
    {"origin_code": "Sw1", "destination_code": "D.Kampus", "duration_minutes": 10},
]


class _SlowProvider:
    def __init__(self):
        self.started = threading.Event()
        self.calls = 0

    def fetch_rows(self):
        self.calls += 1
        self.started.set()
        time.sleep(FETCH_SECONDS)  # synchronous, like supabase-py
        return ROWS


class _Loader:
    def __init__(self, repository):
        self.repository = repository

    def refresh(self, force=False):
        self.repository.refresh(force=force)


class _LoaderClass:
    instance = None

    @classmethod
    def get_instance(cls):
        return cls.instance


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path", ["/api/v1/internal/readiness/time-matrix", "/api/v1/internal/matrix-snapshot"]
)
async def test_slow_matrix_fetch_does_not_block_health(monkeypatch, path):
    monkeypatch.setenv("INTERNAL_API_KEY", KEY)
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("UNIRIDE_TENANT_KEYS", raising=False)
    provider = _SlowProvider()
    _LoaderClass.instance = _Loader(TimeMatrixRepository(provider=provider, ttl_seconds=600))
    monkeypatch.setattr(readiness, "DataLoader", _LoaderClass)

    app = FastAPI()
    app.include_router(readiness.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    results = {}
    PING_AT = 0.1  # seconds after the readiness request is started
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        async def slow_call():
            results["slow"] = await client.post(
                path,
                json={"student_location_codes": ["Sw1"]},
                headers={"X-Internal-API-Key": KEY},
            )

        async def ping():
            # Scheduled for begin + PING_AT. If the loop is blocked by the
            # fetch, the ping can only run (and finish) after the block ends.
            await anyio.sleep(PING_AT)
            results["health"] = await client.get("/health")
            results["health_done"] = time.perf_counter()
            results["slow_done_at_ping"] = "slow" in results

        begin = time.perf_counter()
        async with anyio.create_task_group() as tg:
            tg.start_soon(slow_call)
            tg.start_soon(ping)

    lateness = results["health_done"] - (begin + PING_AT)
    assert provider.calls == 1
    assert results["health"].status_code == 200
    assert results["slow"].status_code == 200
    assert not results["slow_done_at_ping"], "fetch was not in flight during the ping"
    assert lateness < MAX_HEALTH_SECONDS, (
        f"/health finished {lateness:.2f}s late while the matrix fetch was in "
        "flight: the event loop is blocked"
    )
