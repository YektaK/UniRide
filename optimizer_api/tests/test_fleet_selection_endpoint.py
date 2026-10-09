"""WP4: protected internal fleet-selection endpoint (auth, 422 matrix, redaction)."""

import copy
import json

import pytest

pytest.importorskip("ortools")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.routers import fleet_selection

URL = "/api/v1/internal/fleet-selection"
KEY = {"X-Internal-API-Key": "shared-key"}
SENTINEL = "SENTINEL-ECHO-9137"


def _client():
    app = FastAPI()
    app.include_router(fleet_selection.router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _auth(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "shared-key")
    monkeypatch.delenv("UNIRIDE_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("UNIRIDE_TENANT_KEYS", raising=False)


def _body():
    r = lambda s, e, car=True: {"start": s, "end": e, "minutes": float(e - s), "car_ok": car}  # noqa: E731
    return {
        "waves": [
            {"wave_id": "w1", "options": [
                {"option_id": "base", "baseline": True, "routes": [r(0, 30, False), r(5, 35)]},
                {"option_id": "q1", "routes": [r(0, 30, False), r(5, 35)]},
            ]},
            {"wave_id": "w2", "options": [{"option_id": "q0", "routes": [r(40, 70)]}]},
        ],
        "max_large": 1,
    }


def test_403_without_or_with_wrong_key_and_tenant_key(monkeypatch):
    c = _client()
    assert c.post(URL, json=_body()).status_code == 403
    assert c.post(URL, json=_body(), headers={"X-Internal-API-Key": "nope"}).status_code == 403
    monkeypatch.setenv("UNIRIDE_TENANT_KEYS", json.dumps({"t": "tenant-key"}))
    assert c.post(URL, json=_body(), headers={"X-Internal-API-Key": "tenant-key"}).status_code == 403


def test_success_contract():
    res = _client().post(URL, json=_body(), headers=KEY)
    assert res.status_code == 200
    out = res.json()
    assert out["status"] == "optimal"
    assert set(out) == {"status", "cars", "large_peak", "car_minutes", "total_minutes",
                        "selection", "diagnostics", "stats"}
    assert out["cars"] == 1 and out["large_peak"] == 1
    assert set(out["selection"]) == {"w1", "w2"}
    assert out["selection"]["w1"]["labels"] == ["large", "car"]


def test_infeasible_for_L_is_200_with_diagnostics():
    body = _body()
    body["max_large"] = 0
    out = _client().post(URL, json=body, headers=KEY).json()
    assert out["status"] == "infeasible_for_L"
    assert out["diagnostics"]["waves_exceeding_L"] == ["w1"]


def test_infeasible_data_is_200():
    body = _body()
    body["waves"][0]["options"][0]["routes"][0].update(car_ok=False, large_ok=False)
    out = _client().post(URL, json=body, headers=KEY).json()
    assert out["status"] == "infeasible_data"


def _mut(fn):
    b = copy.deepcopy(_body())
    fn(b)
    return b


BAD = {
    "unknown_top_field": lambda b: b.update(extra=1),
    "unknown_route_field": lambda b: b["waves"][0]["options"][0]["routes"][0].update(x=1),
    "no_waves": lambda b: b.update(waves=[]),
    "too_many_waves": lambda b: b.update(waves=[
        {"wave_id": f"w{i}", "options": [{"option_id": "a", "routes": []}]} for i in range(31)]),
    "too_many_options": lambda b: b["waves"][0].update(options=[
        {"option_id": f"o{i}", "routes": []} for i in range(7)]),
    "no_options": lambda b: b["waves"][0].update(options=[]),
    "too_many_routes_in_option": lambda b: b["waves"][0]["options"][0].update(routes=[
        {"start": 0, "end": 5, "minutes": 5.0}] * 41),
    "too_many_total_routes": lambda b: b.update(waves=[
        {"wave_id": f"w{i}", "options": [
            {"option_id": f"o{j}", "routes": [{"start": 0, "end": 5, "minutes": 5.0}] * 40}
            for j in range(6)]} for i in range(5)]),
    "dup_wave": lambda b: b["waves"][1].update(wave_id="w1"),
    "dup_option": lambda b: b["waves"][0]["options"][1].update(option_id="base"),
    "bad_id_chars": lambda b: b["waves"][0].update(wave_id="w 1;drop"),
    "end_not_after_start": lambda b: b["waves"][1]["options"][0]["routes"][0].update(end=40),
    "negative_start": lambda b: b["waves"][1]["options"][0]["routes"][0].update(start=-1),
    "start_too_large": lambda b: b["waves"][1]["options"][0]["routes"][0].update(end=3000),
    "string_start": lambda b: b["waves"][1]["options"][0]["routes"][0].update(start="40"),
    "float_start": lambda b: b["waves"][1]["options"][0]["routes"][0].update(start=40.5),
    "nan_minutes": lambda b: b["waves"][1]["options"][0]["routes"][0].update(minutes="NaN"),
    "negative_minutes": lambda b: b["waves"][1]["options"][0]["routes"][0].update(minutes=-1.0),
    "bool_as_int_L": lambda b: b.update(max_large=True),
    "negative_L": lambda b: b.update(max_large=-1),
    "L_over_ceiling": lambda b: b.update(max_large=51),
    "missing_L": lambda b: b.pop("max_large"),
    "negative_cap": lambda b: b.update(max_cars=-1),
    "cap_over_ceiling": lambda b: b.update(max_cars=51),
    "cooldown_negative": lambda b: b.update(cooldown_car=-1),
    "cooldown_over": lambda b: b.update(cooldown_large=241),
    "time_limit_zero": lambda b: b.update(time_limit_seconds=0),
    "time_limit_over_policy": lambda b: b.update(time_limit_seconds=61),
    "time_limit_string": lambda b: b.update(time_limit_seconds="5"),
    "large_ok_string": lambda b: b["waves"][0]["options"][0]["routes"][0].update(large_ok="yes"),
}


@pytest.mark.parametrize("name", sorted(BAD))
def test_422_matrix_fixed_body(name):
    body = _mut(BAD[name])
    res = _client().post(URL, json=body, headers=KEY)
    assert res.status_code == 422, name
    assert res.json() == {"detail": "Invalid fleet selection request"}


@pytest.mark.parametrize("raw", [b"", b"not json", b"[]", b"null", b'"x"', b"{"])
def test_422_malformed_bodies(raw):
    res = _client().post(URL, content=raw, headers={**KEY, "content-type": "application/json"})
    assert res.status_code == 422
    assert res.json() == {"detail": "Invalid fleet selection request"}


def test_422_does_not_echo_input():
    body = _body()
    body["waves"][0]["wave_id"] = SENTINEL + " bad id"
    res = _client().post(URL, json=body, headers=KEY)
    assert res.status_code == 422 and SENTINEL not in res.text


def test_solver_failure_is_redacted_503(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(fleet_selection, "solve_day_selection", boom)
    res = _client().post(URL, json=_body(), headers=KEY)
    assert res.status_code == 503 and SENTINEL not in res.text
    assert res.json() == {"detail": "Fleet selection unavailable"}


def test_policy_ceiling_follows_env(monkeypatch):
    monkeypatch.setenv("UNIRIDE_COMPUTE_SOLVER_SECONDS", "10")
    body = _body()
    body["time_limit_seconds"] = 11
    assert _client().post(URL, json=body, headers=KEY).status_code == 422
    body["time_limit_seconds"] = 10
    assert _client().post(URL, json=body, headers=KEY).status_code == 200
    assert fleet_selection._policy_time_limit(None) == 10


def test_main_includes_router_source_check():
    # main must not be imported here: test_phase0_auth_guard relies on a fresh import.
    from pathlib import Path

    src = (Path(fleet_selection.__file__).parents[1] / "main.py").read_text(encoding="utf-8")
    assert "app.include_router(fleet_selection.router)" in src


def _scaled_body(scale, start2=61120, cooldown=1000):
    r = lambda s, e: {"start": s, "end": e, "minutes": 1.0, "car_ok": False}  # noqa: E731
    return {
        "waves": [
            {"wave_id": "w1", "options": [{"option_id": "base", "baseline": True, "routes": [r(60000, 60110)]}]},
            {"wave_id": "w2", "options": [{"option_id": "base", "baseline": True, "routes": [r(start2, 62000)]}]},
        ],
        "max_large": 1, "cooldown_large": cooldown, "cooldown_car": cooldown, "time_scale": scale,
    }


def test_time_scale_100_fractional_gap_is_feasible():
    res = _client().post(URL, json=_scaled_body(100), headers=KEY)
    assert res.status_code == 200
    assert res.json()["status"] == "optimal"
    assert res.json()["large_peak"] == 1


def test_time_scale_default_1_keeps_legacy_integer_minutes():
    body = _scaled_body(1)
    del body["time_scale"]
    # legacy units: 60000 minutes is out of range
    assert _client().post(URL, json=body, headers=KEY).status_code == 422
    assert _client().post(URL, json=_body(), headers=KEY).status_code == 200


def test_time_scale_scales_bounds():
    c = _client()
    ok = _scaled_body(100)
    ok["waves"][1]["options"][0]["routes"][0]["end"] = 2880 * 100
    assert c.post(URL, json=ok, headers=KEY).status_code == 200
    over = _scaled_body(100)
    over["waves"][1]["options"][0]["routes"][0]["end"] = 2880 * 100 + 1
    assert c.post(URL, json=over, headers=KEY).status_code == 422
    assert c.post(URL, json=_scaled_body(100, cooldown=240 * 100 + 1), headers=KEY).status_code == 422
    assert c.post(URL, json=_scaled_body(100, cooldown=240 * 100), headers=KEY).status_code == 200


@pytest.mark.parametrize("bad", [0, -1, 101, 1.5, "100", True, None])
def test_time_scale_rejects_invalid_values(bad):
    body = _scaled_body(100)
    body["time_scale"] = bad
    assert _client().post(URL, json=body, headers=KEY).status_code == 422


def _default_cooldown_body(start2, **extra):
    r = lambda s, e: {"start": s, "end": e, "minutes": 1.0, "car_ok": False}  # noqa: E731
    body = {
        "waves": [
            {"wave_id": "w1", "options": [{"option_id": "base", "baseline": True, "routes": [r(60000, 60110)]}]},
            {"wave_id": "w2", "options": [{"option_id": "base", "baseline": True, "routes": [r(start2, 62000)]}]},
        ],
        "max_large": 1, "time_scale": 100,
    }
    body.update(extra)
    return body


@pytest.mark.parametrize("extra", [{}, {"cooldown_large": None, "cooldown_car": None}])
def test_omitted_or_null_cooldown_means_ten_real_minutes_at_scale(extra):
    c = _client()
    # gap 9.9 minutes < 10: one vehicle cannot serve both
    tight = c.post(URL, json=_default_cooldown_body(61100, **extra), headers=KEY)
    assert tight.status_code == 200 and tight.json()["status"] == "infeasible_for_L"
    # gap 10.1 minutes >= 10: feasible
    ok = c.post(URL, json=_default_cooldown_body(61120, **extra), headers=KEY)
    assert ok.status_code == 200
    assert ok.json()["status"] == "optimal" and ok.json()["large_peak"] == 1
