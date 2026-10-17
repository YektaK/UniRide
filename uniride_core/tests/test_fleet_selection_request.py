"""WP-E4a part 1: the Python port of the producer's selection-request construction
(``src/services/fleet-scenario-run.ts`` ``scenarioL``, ``typeAccepts``; design section 1.5 "Same inputs as the
producer and the router")."""
from __future__ import annotations

import pytest

from uniride_core.planning import fleet_selection_request as fsr

LARGE = fsr.TypeLimits("large", 4, 5, None, None, None)
SEDAN = fsr.TypeLimits("sedan", 0, 4, None, None, None)
MINIVAN = fsr.TypeLimits("minivan", 1, 3, 3, None, None)


def _facts(start, end, durations=(10, 20, 15), direction="pickup", sw=0, so=2):
    return fsr.RouteFacts(start_minutes=start, end_minutes=end, step_durations=tuple(durations), direction=direction,
                          sw_count=sw, so_count=so)


def test_centi_converts_minutes_to_centi_minutes_and_refuses_off_grid_values():
    assert fsr.centi(449) == 44900
    assert fsr.centi(10) == 1000
    assert fsr.centi(12.34) == 1234
    with pytest.raises(fsr.SelectionIntervalPrecision):
        fsr.centi(12.345)  # never rounded (SELECTION_INTERVAL_PRECISION)


def test_round6_uses_javascript_half_up_rounding():
    assert fsr.round6(76) == 76
    assert fsr.round6(0.0000005) == 0.000001  # JS Math.round rounds .5 up, Python round() would give 0.0
    assert fsr.round6(2.5e-7) == 0.0


def test_interval_end_is_at_least_start_plus_one_centi_minute():
    """The ``start + 1`` rule: an empty or reversed interval still has length 1 (router needs end > start)."""
    req = fsr.build_selection_request(
        [("w1", [("base", True, [_facts(525, 525)])])], fixed_type=LARGE, minimise_type=SEDAN, max_large=1,
        ride_default=90, tour_default=150)
    route = req["waves"][0]["options"][0]["routes"][0]
    assert (route["start"], route["end"]) == (52500, 52501)


def test_request_shape_and_defaults_match_the_producer():
    req = fsr.build_selection_request(
        [("w1", [("base", True, [_facts(449, 525)]), ("q1", False, [_facts(430, 525, sw=1, so=0)])])],
        fixed_type=LARGE, minimise_type=SEDAN, max_large=2, ride_default=90, tour_default=150)
    assert set(req) == {"time_scale", "waves", "max_large", "cooldown_large", "cooldown_car", "time_limit_seconds"}
    assert req["time_scale"] == 100 and req["max_large"] == 2 and req["time_limit_seconds"] == 30
    assert req["cooldown_large"] == 1000 and req["cooldown_car"] == 1000  # 10 minutes in centi-minutes
    opt = req["waves"][0]["options"]
    assert [(o["option_id"], o["baseline"]) for o in opt] == [("base", True), ("q1", False)]
    assert opt[0]["routes"][0] == {"start": 44900, "end": 52500, "minutes": 76, "large_ok": True, "car_ok": True}


def test_max_cars_is_sent_only_when_set():
    base = dict(fixed_type=LARGE, minimise_type=SEDAN, max_large=1, ride_default=90, tour_default=150)
    waves = [("w1", [("base", True, [_facts(449, 525)])])]
    assert "max_cars" not in fsr.build_selection_request(waves, **base)
    assert fsr.build_selection_request(waves, max_cars=3, **base)["max_cars"] == 3


def test_type_accepts_uses_capacity_pools_total_capacity_and_limits():
    ok = _facts(449, 525, durations=(30, 8, 38), sw=0, so=2)
    assert fsr.type_accepts(LARGE, ok, ride_default=90, tour_default=150)
    assert fsr.type_accepts(SEDAN, ok, ride_default=90, tour_default=150)
    assert not fsr.type_accepts(SEDAN, _facts(449, 525, sw=1, so=1), ride_default=90, tour_default=150)  # Sw pool 0
    assert not fsr.type_accepts(MINIVAN, _facts(449, 525, sw=1, so=3), ride_default=90, tour_default=150)  # total 3
    assert fsr.type_accepts(MINIVAN, _facts(449, 525, sw=1, so=2), ride_default=90, tour_default=150)
    # tour limit: facts.minutes = end - start = 151 > 150
    assert not fsr.type_accepts(LARGE, _facts(400, 551), ride_default=90, tour_default=150)
    # ride limit: pickup ride = total minus the first arc = 20 + 15 = 35 > 30
    assert not fsr.type_accepts(LARGE, _facts(449, 525, durations=(10, 20, 15)), ride_default=30, tour_default=150)
    # a type's own limits override the defaults
    own = fsr.TypeLimits("large", 4, 5, None, 40, 80)
    assert fsr.type_accepts(own, _facts(449, 525, durations=(10, 20, 15)), ride_default=30, tour_default=150)  # 35 <= 40, 76 <= 80
    assert fsr.longest_student_ride_minutes((10, 20, 15), "pickup") == 35
    assert fsr.longest_student_ride_minutes((10, 20, 15), "dropoff") == 30
    assert fsr.longest_student_ride_minutes((), "pickup") == 0
