"""MT1-08 (audit M2, DECISION_LOG O09 OQ-MT1-14): time windows are built for the
request direction only; a windowed request needs target_time; no implicit window.

Plan: docs/superpowers/plans/2026-10-27-mt1-time-window-unification.md, item MT1-08.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from models.schemas import CompareRequest, OptimizationRequest, TimeWindow
from routers import optimization

REFUSAL = "use_time_windows requires target_time"
DEPOT = {"id": "D", "lat": 0.0, "lng": 0.0}


def _student(sid, loc, **times):
    return {"id": sid, "location_code": loc, "disability_type": "So", **times}


def _request(students, **overrides):
    payload = {"algorithm": "ga_split", "students": students, "depot": DEPOT}
    payload.update(overrides)
    return OptimizationRequest.model_validate(payload)


def _client(monkeypatch):
    monkeypatch.setenv("UNIRIDE_DISABLE_AUTH", "1")
    # the per-IP limiter is process-wide; earlier tests in a full run can exhaust it (429)
    from optimizer_api import rate_limit
    rate_limit._buckets.clear()
    app = FastAPI()
    app.include_router(optimization.router)
    return TestClient(app)


# --- M2: no cross-direction fallback -----------------------------------------

def test_pickup_ignores_dropoff_time():
    request = _request(
        [_student("s1", "L1", dropoff_time="17:00")],
        direction="pickup", use_time_windows=True, target_time="08:30",
    )
    # before MT1-08 this was (990, 1020): a morning pickup window built from dropoff_time
    assert request.get_time_windows() == {}


def test_dropoff_ignores_pickup_time():
    request = _request(
        [_student("s1", "L1", pickup_time="07:30")],
        direction="dropoff", use_time_windows=True, target_time="17:00",
    )
    assert request.get_time_windows() == {}


def test_pickup_uses_pickup_time_and_dropoff_uses_dropoff_time_when_both_set():
    students = [_student("s1", "L1", pickup_time="07:30", dropoff_time="17:00")]
    pickup = _request(students, direction="pickup", use_time_windows=True, target_time="08:30")
    dropoff = _request(students, direction="dropoff", use_time_windows=True, target_time="17:00")
    assert pickup.get_time_windows() == {"L1": TimeWindow(earliest=450 - 30, latest=450)}
    assert dropoff.get_time_windows() == {"L1": TimeWindow(earliest=1020, latest=1050)}


# --- OQ-MT1-14: no implicit window for a student without a time ---------------

def test_student_without_time_gets_no_window_even_with_target_time():
    request = _request(
        [_student("s1", "L1", pickup_time="07:30"), _student("s2", "L2")],
        direction="pickup", use_time_windows=True, target_time="08:30",
    )
    windows = request.get_time_windows()
    # before MT1-08 L2 got (target - 30, target) = (480, 510)
    assert set(windows) == {"L1"}


# --- OQ-MT1-14: windowed request without target_time is refused ----------------

def test_windowed_request_without_target_time_is_rejected_by_model():
    with pytest.raises(ValidationError, match=REFUSAL):
        _request([_student("s1", "L1", pickup_time="07:30")], use_time_windows=True)


def test_optimize_h4_scenario_2_is_http_422_with_fixed_message(monkeypatch):
    # audit H4 scenario 2: one student with pickup 07:30, no target_time
    payload = {
        "algorithm": "ga_split",
        "students": [_student("s1", "L1", pickup_time="07:30")],
        "depot": DEPOT,
        "use_time_windows": True,
    }
    response = _client(monkeypatch).post("/api/v1/optimize", json=payload)
    assert response.status_code == 422
    assert REFUSAL in response.text


def test_compare_windowed_without_target_time_is_http_422(monkeypatch):
    payload = {
        "students": [_student("s1", "L1", pickup_time="07:30")],
        "depot": DEPOT,
        "use_time_windows": True,
        "algorithms": ["ga_split"],
    }
    response = _client(monkeypatch).post("/api/v1/compare", json=payload)
    assert response.status_code == 422
    assert REFUSAL in response.text


def test_compare_request_carries_target_time_into_the_optimization_request():
    compare = CompareRequest.model_validate({
        "students": [_student("s1", "L1", pickup_time="07:30")],
        "depot": DEPOT,
        "use_time_windows": True,
        "target_time": "08:30",
    })
    opt = optimization._compare_optimization_request(compare, "ga_split")
    assert opt.use_time_windows is True
    assert opt.target_time == "08:30"


# --- use_time_windows=false behaves as before -----------------------------------

def test_requests_without_time_windows_are_unchanged():
    students = [_student("s1", "L1", pickup_time="07:30"), _student("s2", "L2")]
    # accepted with and without target_time; the flag is off so no refusal
    plain = _request(students, direction="pickup", use_time_windows=False)
    with_target = _request(students, direction="pickup", use_time_windows=False, target_time="08:30")
    assert plain.use_time_windows is False and plain.target_time is None
    assert with_target.target_time == "08:30"
    # a student's own pickup_time still yields its window; the target never made one
    assert plain.get_time_windows() == {"L1": TimeWindow(earliest=420, latest=450)}
    assert with_target.get_time_windows() == plain.get_time_windows()


# --- DUZELT r1: drop-off direction, bad target_time, validator order -----------

def test_dropoff_windowed_request_without_target_time_is_rejected_by_model():
    with pytest.raises(ValidationError, match=REFUSAL):
        _request([_student("s1", "L1", dropoff_time="17:00")], direction="dropoff", use_time_windows=True)


def test_optimize_dropoff_windowed_without_target_time_is_http_422(monkeypatch):
    payload = {
        "algorithm": "ga_split",
        "students": [_student("s1", "L1", dropoff_time="17:00")],
        "depot": DEPOT,
        "direction": "dropoff",
        "use_time_windows": True,
    }
    response = _client(monkeypatch).post("/api/v1/optimize", json=payload)
    assert response.status_code == 422
    assert REFUSAL in response.text


def test_compare_dropoff_windowed_without_target_time_is_http_422(monkeypatch):
    payload = {
        "students": [_student("s1", "L1", dropoff_time="17:00")],
        "depot": DEPOT,
        "direction": "dropoff",
        "use_time_windows": True,
        "algorithms": ["ga_split"],
    }
    response = _client(monkeypatch).post("/api/v1/compare", json=payload)
    assert response.status_code == 422
    assert REFUSAL in response.text


def test_compare_invalid_target_time_is_http_422(monkeypatch):
    payload = {
        "students": [_student("s1", "L1", pickup_time="07:30")],
        "depot": DEPOT,
        "target_time": "25:99",
        "algorithms": ["ga_split"],
    }
    response = _client(monkeypatch).post("/api/v1/compare", json=payload)
    assert response.status_code == 422
    assert "Invalid time" in response.text


def test_heterogeneous_fleet_message_wins_over_target_time_refusal():
    payload = {
        "algorithm": "ga_split_hf",
        "students": [],
        "depot": DEPOT,
        "vehicle_types": [{"type_id": "large", "sw_capacity": 4, "so_capacity": 5}],
        "minimize_type": "large",
        "use_time_windows": True,
    }
    with pytest.raises(ValidationError) as excinfo:
        OptimizationRequest.model_validate(payload)
    text = str(excinfo.value)
    assert "vehicle_types does not support use_time_windows" in text
    assert REFUSAL not in text
