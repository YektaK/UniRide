"""WP-E11 J6: one failing case per rule of the independent day-plan checker (design section 5.1).

Every negative test starts from one valid hand plan, changes exactly one thing and expects the matching violation code
(and, where the rule is easy to isolate, no other code). The positive case reads the archived 4sw5so GA routes of one
day, read-only.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from academic_benchmark.validation import day_plan as dp

REPO = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = REPO / "docs" / "paper" / "results" / "week-2026-10-05-4sw5so"

DEPOT = "D"
LARGE = dp.TypeSpec("large", 4, 5, 10)
SEDAN = dp.TypeSpec("sedan", 0, 4, 10)
DOBLO = dp.TypeSpec("doblo", 1, 3, 10, total_capacity=3)
TYPES = {t.type_id: t for t in (LARGE, SEDAN, DOBLO)}


def make_arcs(codes, value=10):
    names = [DEPOT, *codes]
    return {(a, b): value for a in names for b in names if a != b}


def occ(wave, code):
    return f"{wave}:{code}~1"


def good(**over):
    """Pickup wave at 600 (two routes, large + sedan) and a dropoff wave at 900 (one large route). Valid."""
    codes = ["Sw1", "Sw2", "So1", "So2", "So3", "So4"]
    w1 = dp.Wave("w1", "pickup", 600, {occ("w1", c): c for c in ("Sw1", "So1", "So2", "So3")})
    w2 = dp.Wave("w2", "dropoff", 900, {occ("w2", c): c for c in ("So4", "Sw2")})
    routes = [
        dp.Route("w1", "large", (occ("w1", "Sw1"), occ("w1", "So1"))),
        dp.Route("w1", "sedan", (occ("w1", "So2"), occ("w1", "So3"))),
        dp.Route("w2", "large", (occ("w2", "So4"), occ("w2", "Sw2"))),
    ]
    kwargs = dict(waves=[w1, w2], routes=routes, types=TYPES, arcs=make_arcs(codes), depot=DEPOT,
                  tour_limit=150, ride_limit=60, peak_caps=None, claims=None)
    kwargs.update(over)
    return kwargs


def run(**over):
    return dp.check_day_plan(**good(**over))


def test_the_valid_hand_plan_passes_and_reports_per_type_peaks():
    report = run()
    assert report.ok, report.violations
    # w1: both routes are busy on [570, 610) (tour 30, cooldown 10); w2 is busy on [900, 940)
    assert dict(report.peaks_minutes) == {"large": 1, "sedan": 1}
    assert dict(report.peaks_centi) == dict(report.peaks_minutes)
    assert report.route_count == 3
    assert report.total_minutes == 90
    assert dict(report.minutes_by_type) == {"large": 60, "sedan": 30}


# ---------------------------------------------------------------- coverage
def test_missing_occurrence():
    routes = good()["routes"]
    routes[1] = dp.Route("w1", "sedan", (occ("w1", "So2"),))
    assert "MISSING_OCCURRENCE" in run(routes=routes).codes


def test_duplicate_occurrence():
    routes = good()["routes"]
    routes[1] = dp.Route("w1", "sedan", (occ("w1", "So2"), occ("w1", "So3"), occ("w1", "So1")))
    assert "DUPLICATE_OCCURRENCE" in run(routes=routes).codes


def test_a_route_may_not_mix_waves():
    routes = good()["routes"]
    routes[1] = dp.Route("w1", "sedan", (occ("w1", "So2"), occ("w2", "So4")))
    assert "MIXED_WAVE" in run(routes=routes).codes


def test_unknown_occurrence_and_unknown_type():
    routes = good()["routes"]
    routes[1] = dp.Route("w1", "sedan", (occ("w1", "So2"), "ghost~1"))
    assert "UNKNOWN_OCCURRENCE" in run(routes=routes).codes
    routes = good()["routes"]
    routes[1] = dp.Route("w1", "tractor", routes[1].stops)
    assert "UNKNOWN_TYPE" in run(routes=routes).codes


# ---------------------------------------------------------------- per-type capacity
def test_sw_on_a_sedan():
    routes = good()["routes"]
    routes[0] = dp.Route("w1", "sedan", routes[0].stops)  # Sw1 + So1 on a type with 0 Sw
    assert run(routes=routes).codes == ("CAPACITY_SW",)


def test_doblo_total_four():
    wave = dp.Wave("w1", "pickup", 600, {occ("w1", c): c for c in ("Sw1", "So1", "So2", "So3")})
    stops = tuple(occ("w1", c) for c in ("Sw1", "So1", "So2", "So3"))  # 1 Sw + 3 So = 4 > total 3; each class alone fits
    report = run(waves=[wave], routes=[dp.Route("w1", "doblo", stops)])
    assert report.codes == ("CAPACITY_TOTAL",)


def test_doblo_total_three_passes():
    wave = dp.Wave("w1", "pickup", 600, {occ("w1", c): c for c in ("Sw1", "So1", "So2")})
    stops = tuple(occ("w1", c) for c in ("Sw1", "So1", "So2"))
    assert run(waves=[wave], routes=[dp.Route("w1", "doblo", stops)]).ok


def test_the_class_is_taken_from_the_location_code_and_cross_checked_with_the_claim():
    routes = good()["routes"]
    routes[0] = dp.Route("w1", "large", routes[0].stops, claimed_sw=0, claimed_so=2)  # the codes say 1 Sw + 1 So
    assert "CLASS_MISMATCH" in run(routes=routes).codes


# ---------------------------------------------------------------- arcs, tour, ride
def test_missing_arc():
    arcs = good()["arcs"]
    del arcs[("Sw1", "So1")]
    assert "MISSING_ARC" in run(arcs=arcs).codes


@pytest.mark.parametrize("bad", [-1, 10.5, "10", True, None])
def test_arcs_must_be_non_negative_integers(bad):
    arcs = good()["arcs"]
    arcs[("Sw1", "So1")] = bad
    assert "BAD_ARC" in run(arcs=arcs).codes


def test_tour_151():
    arcs = good()["arcs"]
    arcs[("Sw1", "So1")] = 131  # 10 + 131 + 10 = 151
    report = run(arcs=arcs, ride_limit=150)
    assert report.codes == ("TOUR_LIMIT",)


def test_tour_150_passes():
    arcs = good()["arcs"]
    arcs[("Sw1", "So1")] = 130
    assert run(arcs=arcs, ride_limit=150).ok


def test_pickup_ride_is_the_tour_minus_the_first_arc():
    arcs = good()["arcs"]
    arcs[("Sw1", "So1")], arcs[("So1", DEPOT)] = 31, 30  # ride = 31 + 30 = 61 = R + 1; tour 71
    assert run(arcs=arcs).codes == ("RIDE_LIMIT",)
    arcs[("Sw1", "So1")] = 30  # ride exactly R
    assert run(arcs=arcs).ok


def test_dropoff_ride_is_the_tour_minus_the_closing_arc():
    arcs = good()["arcs"]
    # w2 is the dropoff wave: D -> So4 = 10, So4 -> Sw2 = 51, Sw2 -> D = 1; ride = 61, but the pickup rule would give 52
    arcs[("So4", "Sw2")], arcs[("Sw2", DEPOT)] = 51, 1
    assert run(arcs=arcs).codes == ("RIDE_LIMIT",)
    arcs[("So4", "Sw2")] = 50
    assert run(arcs=arcs).ok


def test_type_limits_override_the_defaults():
    types = dict(TYPES, large=dp.TypeSpec("large", 4, 5, 10, tour_limit=30))  # both large routes have tour 30
    assert run(types=types).ok
    types = dict(TYPES, large=dp.TypeSpec("large", 4, 5, 10, tour_limit=29))
    assert "TOUR_LIMIT" in run(types=types).codes
    types = dict(TYPES, large=dp.TypeSpec("large", 4, 5, 10, ride_limit=19))  # ride = 20 on both routes
    assert "RIDE_LIMIT" in run(types=types).codes


# ---------------------------------------------------------------- anchoring and service day
def test_a_pickup_route_starting_before_minute_zero_is_outside_the_service_day():
    waves = good()["waves"]
    waves[0] = dp.Wave("w1", "pickup", 20, waves[0].occurrences)  # start = 20 - 30 < 0
    assert "OUTSIDE_SERVICE_DAY" in run(waves=waves).codes
    waves[0] = dp.Wave("w1", "pickup", 30, waves[0].occurrences)  # start = 0 exactly is fine
    assert "OUTSIDE_SERVICE_DAY" not in run(waves=waves).codes


def test_a_dropoff_route_ending_after_minute_1440_is_outside_the_service_day():
    waves = good()["waves"]
    waves[1] = dp.Wave("w2", "dropoff", 1420, waves[1].occurrences)  # end = 1420 + 30 > 1440
    assert "OUTSIDE_SERVICE_DAY" in run(waves=waves).codes


def test_the_cooldown_may_run_past_minute_1440():
    waves = good()["waves"]
    waves[1] = dp.Wave("w2", "dropoff", 1410, waves[1].occurrences)  # end = 1440 exactly; only the cooldown leaves the day
    assert "OUTSIDE_SERVICE_DAY" not in run(waves=waves).codes


# ---------------------------------------------------------------- peaks
def test_peak_above_L():
    routes = good()["routes"]
    routes[1] = dp.Route("w1", "large", routes[1].stops)  # two large routes busy on [570, 610)
    assert dict(run(routes=routes).peaks_minutes)["large"] == 2
    report = run(routes=routes, peak_caps={"large": 1})
    assert report.codes == ("PEAK_ABOVE_CAP",)
    assert run(routes=routes, peak_caps={"large": 2}).ok


def test_the_cooldown_is_part_of_the_busy_interval_and_the_interval_is_half_open():
    routes = good()["routes"]
    routes[1] = dp.Route("w1", "large", routes[1].stops)  # w1: two large routes busy on [570, 610)
    for anchor, expected in ((609, 3), (610, 2)):  # the w2 dropoff route starts at its anchor, busy on [anchor, anchor + 40)
        waves = good()["waves"]
        waves[1] = dp.Wave("w2", "dropoff", anchor, waves[1].occurrences)
        assert dict(run(waves=waves, routes=routes).peaks_minutes)["large"] == expected, anchor


def test_claimed_S_off_by_one():
    assert run(claims=dp.DayClaims(peaks={"sedan": 1, "large": 1})).ok
    assert "CLAIMED_PEAK" in run(claims=dp.DayClaims(peaks={"sedan": 2})).codes
    assert "CLAIMED_PEAK" in run(claims=dp.DayClaims(peaks={"sedan": 0})).codes


def test_minutes_off_by_one():
    assert run(claims=dp.DayClaims(total_minutes=90, minutes_by_type={"large": 60, "sedan": 30}, route_count=3)).ok
    assert "CLAIMED_TOTAL_MINUTES" in run(claims=dp.DayClaims(total_minutes=91)).codes
    assert "CLAIMED_TOTAL_MINUTES" in run(claims=dp.DayClaims(total_minutes=89)).codes
    assert "CLAIMED_TYPE_MINUTES" in run(claims=dp.DayClaims(minutes_by_type={"sedan": 31})).codes
    assert "CLAIMED_ROUTE_COUNT" in run(claims=dp.DayClaims(route_count=4)).codes
    routes = good()["routes"]
    routes[0] = dp.Route("w1", "large", routes[0].stops, claimed_minutes=31)
    assert "CLAIMED_ROUTE_MINUTES" in run(routes=routes).codes


def test_a_centi_grid_peak_that_differs_from_the_minute_peak():
    """A zero-minute route with cooldown 0 has an empty minute interval [s, s), but the production grid gives it
    [100 s, 100 s + 1): the integer-minute peak is 0 and the time_scale = 100 peak is 1."""
    zero = dp.TypeSpec("zero", 4, 5, 0)
    wave = dp.Wave("w1", "pickup", 600, {occ("w1", "So1"): "So1"})
    arcs = {(DEPOT, "So1"): 0, ("So1", DEPOT): 0}
    report = run(waves=[wave], routes=[dp.Route("w1", "zero", (occ("w1", "So1"),))], types={"zero": zero}, arcs=arcs)
    assert dict(report.peaks_minutes) == {"zero": 0}
    assert dict(report.peaks_centi) == {"zero": 1}
    assert report.codes == ("PEAK_GRID_MISMATCH",)


def test_the_same_peak_on_both_grids_reports_no_mismatch():
    assert "PEAK_GRID_MISMATCH" not in run().codes


# ---------------------------------------------------------------- archived positive case
def _archive_day(date="2026-10-06", ride=60):
    base = ARCHIVE_DIR / f"{date}_R{ride}_repeat1"
    response = json.loads(Path(f"{base}.response.json").read_text(encoding="utf-8"))
    matrix = json.loads(Path(f"{base}.matrix.json").read_text(encoding="utf-8"))
    return response, matrix


def test_archived_4sw5so_ga_routes_of_one_day_pass_and_give_a_peak():
    response, matrix = _archive_day()
    kwargs = dp.plan_from_single_type_response(response, matrix, type_spec=dp.TypeSpec("large", 4, 5, 10), depot="D.Kampus")
    report = dp.check_day_plan(**kwargs)
    assert report.ok, report.violations
    assert report.route_count == 20 == sum(j["routeCount"] for j in response["vehicleSummary"]["routesPerJob"])
    assert report.total_minutes == 1307 == sum(r["total_duration_minutes"] for j in response["jobs"] for r in j["result"]["routes"])
    assert dict(report.peaks_minutes) == dict(report.peaks_centi) == {"large": 4}
    # the archive's own summary names the same peak of concurrent routes (a separate production computation)
    assert response["vehicleSummary"]["peakConcurrentRoutes"] == 4


def test_a_tampered_archive_arc_is_caught():
    response, matrix = _archive_day()
    for rec in matrix["arcs"]:
        if rec["origin_code"] == "D.Kampus" and rec["destination_code"] == "So15":
            rec["duration_minutes"] += 400  # the first route of the first wave now exceeds the tour limit
    kwargs = dp.plan_from_single_type_response(response, matrix, type_spec=dp.TypeSpec("large", 4, 5, 10), depot="D.Kampus")
    assert "TOUR_LIMIT" in dp.check_day_plan(**kwargs).codes
