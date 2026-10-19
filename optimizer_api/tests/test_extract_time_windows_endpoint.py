"""M23 (bug part): POST /api/v1/extract-time-windows must work for valid input.

The endpoint used to pass a Pydantic ``WeeklyScheduleEntry`` to
``TimeWindowExtractor.extract``, which calls ``entry.get`` (dict contract), so
every request ended in ``AttributeError``.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.routers import utils as utils_router

URL = "/api/v1/extract-time-windows"


def _client():
    app = FastAPI()
    app.include_router(utils_router.router)
    return TestClient(app, raise_server_exceptions=True)


def _entries():
    return [
        {"id": "S1", "dayOfWeek": "Monday", "startTime": "08:00", "endTime": "10:20"},
        {"id": "S2", "dayOfWeek": "Tuesday", "startTime": "09:00", "endTime": "11:00"},
    ]


def test_pickup_returns_windows_ending_at_class_start():
    response = _client().post(
        URL, params={"direction": "pickup", "target_day": "monday", "window_minutes": 30}, json=_entries()
    )
    assert response.status_code == 200
    assert response.json() == {"S1": {"earliest": 450, "latest": 480}}


def test_dropoff_returns_windows_after_class_end_rounded_up_to_hour():
    response = _client().post(
        URL, params={"direction": "dropoff", "target_day": "Monday", "window_minutes": 30}, json=_entries()
    )
    assert response.status_code == 200
    assert response.json() == {"S1": {"earliest": 660, "latest": 690}}


def test_no_entry_on_target_day_returns_empty_object():
    response = _client().post(URL, params={"direction": "pickup", "target_day": "friday"}, json=_entries())
    assert response.status_code == 200
    assert response.json() == {}
