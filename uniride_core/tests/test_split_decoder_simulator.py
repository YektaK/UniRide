"""MT1-05: the split decoder's time-window branch uses the route simulator.

Audit findings closed on the decoder side: H2-d (fixed start, truncated arcs, no
return check after waits), H4-b (09:00 / 14:00 anchors, drop-off first-stop start),
N1-b (drop-off phantom wait).  Scenarios come from the audit and from the MT1 plan
(``docs/superpowers/plans/2026-10-27-mt1-time-window-unification.md``, item MT1-05).

Every expected schedule number is computed by ``route_schedule`` (MT1-01) or
written down from the audit; nothing here is read back from the decoder.
"""

from __future__ import annotations

import random

import pytest

from uniride_core.algorithms.ga_split_engine import solve_ga_split
from uniride_core.algorithms.route_schedule import (
    simulate_school_dropoff,
    simulate_school_pickup,
)
from uniride_core.algorithms.string_split_decoder import (
    Direction,
    SplitDecoder,
    decode_with_time_windows,
)

DEPOT = "D"
BIG = 100.0


def matrix_from(arcs, nodes):
    """Directed matrix; arcs not listed cost BIG (never a useful shortcut)."""
    m = {a: {b: (0.0 if a == b else BIG) for b in nodes} for a in nodes}
    for (a, b), v in arcs.items():
        m[a][b] = float(v)
    return m


def arc_fn(m):
    return lambda a, b: m[a][b]


def trip_of(trips, start, end):
    return next((t for t in trips[end + 1] if t.start_idx == start and t.end_idx == end), None)


# ── H4: latest feasible departure, no truncation (pickup) ───────────────────


def test_h4_pickup_trip_is_feasible_with_latest_departure():
    nodes = [DEPOT, "A", "B"]
    m = matrix_from({(DEPOT, "A"): 10.9, ("A", "B"): 10.9, ("B", DEPOT): 10.2}, nodes)
    windows = {"A": (0, 473)}
    # target 08:15, offset 0 -> deadline 495
    expected = simulate_school_pickup(
        ["A", "B"], arc_fn(m), deadline=495, windows=windows, depot=DEPOT
    )
    assert expected.violations == ()
    assert expected.start == pytest.approx(462.1, abs=1e-9)

    result = decode_with_time_windows(
        giant_tour=["A", "B"], depot=DEPOT, distance_matrix=m,
        demands={"A": (0, 1), "B": (0, 1)}, time_windows=windows,
        direction=Direction.PICKUP, target_time=495, offset_minutes=0,
        is_asymmetric=True,
    )
    assert result["routes"] == [["A", "B"]]
    assert result["time_window_violations"] == 0
    schedule = result["schedules"][0]
    assert schedule["departure_time"] == pytest.approx(expected.start, abs=1e-9)
    assert schedule["departure_time"] == pytest.approx(462.1, abs=1e-9)


# ── H2: waiting makes the school arrival miss the deadline ──────────────────


def _h2_trips(strict):
    nodes = [DEPOT, "A", "B"]
    m = matrix_from({(DEPOT, "A"): 10, ("A", "B"): 20, ("B", DEPOT): 20}, nodes)
    decoder = SplitDecoder(
        use_time_windows=True, direction=Direction.PICKUP,
        time_windows={"A": (480, 510), "B": (480, 510)},
        target_time=510, offset_minutes=15,  # deadline 495
        max_tour_duration=1000, is_asymmetric=True, strict_time_windows=strict,
    )
    return decoder._build_trips_with_tw(["A", "B"], DEPOT, m, {"A": (0, 1), "B": (0, 1)})


def test_h2_strict_does_not_admit_trip_that_misses_the_deadline():
    assert trip_of(_h2_trips(strict=True), 0, 1) is None


def test_h2_soft_keeps_the_trip_with_one_violation():
    trip = trip_of(_h2_trips(strict=False), 0, 1)
    assert trip is not None
    assert trip.time_window_violations == 1  # the audit: school reached 08:40 > 08:15


# ── N1-b: drop-off start is the ready time, not the first stop's earliest ───


def test_n1_dropoff_three_students_one_vehicle():
    # Reconstructed scenario (the audit gives only the outcome: 3 vehicles although a
    # single vehicle's longest ride is 42): target 16:00 = 960, ride limit 45. The
    # first stop's window opens at 15:40, before the target; the old decoder started
    # there and "waited" 18 minutes at S2 that the real bus (ready at 16:00) never waits.
    nodes = [DEPOT, "S1", "S2", "S3"]
    m = matrix_from(
        {(DEPOT, "S1"): 5, ("S1", "S2"): 12, ("S2", "S3"): 25, ("S3", DEPOT): 10}, nodes
    )
    windows = {"S1": (940, 1000), "S2": (975, 1005), "S3": (985, 1010)}
    expected = simulate_school_dropoff(
        ["S1", "S2", "S3"], arc_fn(m), ready=960, windows=windows, depot=DEPOT
    )
    assert expected.violations == ()
    assert max(expected.ride_times) == pytest.approx(42)

    result = decode_with_time_windows(
        giant_tour=["S1", "S2", "S3"], depot=DEPOT, distance_matrix=m,
        demands={k: (0, 1) for k in ("S1", "S2", "S3")}, time_windows=windows,
        direction=Direction.DROPOFF, target_time=960, offset_minutes=0,
        max_ride_time=45, is_asymmetric=True,
    )
    assert result["num_vehicles"] == 1
    assert result["routes"] == [["S1", "S2", "S3"]]
    assert result["time_window_violations"] == 0
    assert result["schedules"][0]["departure_time"] == pytest.approx(960)


def test_dropoff_ready_time_is_target_plus_offset_and_departure_is_recorded_exactly():
    nodes = [DEPOT, "S1"]
    m = matrix_from({(DEPOT, "S1"): 7.5, ("S1", DEPOT): 7.5}, nodes)
    # window opens later than the arrival: the bus waits, the recorded departure from
    # the school stays at the ready time (old code recorded current_time - int(cost)).
    result = decode_with_time_windows(
        giant_tour=["S1"], depot=DEPOT, distance_matrix=m, demands={"S1": (0, 1)},
        time_windows={"S1": (980, 1000)}, direction=Direction.DROPOFF,
        target_time=960, offset_minutes=5, is_asymmetric=True,
    )
    expected = simulate_school_dropoff(
        ["S1"], arc_fn(m), ready=965, windows={"S1": (980, 1000)}, depot=DEPOT
    )
    schedule = result["schedules"][0]
    assert schedule["departure_time"] == pytest.approx(965)
    assert schedule["arrivals"]["S1"] == pytest.approx(expected.arrivals[0])
    assert schedule["waits"]["S1"] == pytest.approx(expected.waits[0])
    assert schedule["end"] == pytest.approx(expected.end)


# ── tour limit and ride limit count waits ────────────────────────────────────


def test_tour_limit_counts_waiting_not_only_travel():
    nodes = [DEPOT, "A"]
    m = matrix_from({(DEPOT, "A"): 10, ("A", DEPOT): 10}, nodes)
    # drop-off ready 420; A opens at 460: travel 20 + wait 30 = tour 50
    kwargs = dict(
        use_time_windows=True, direction=Direction.DROPOFF,
        time_windows={"A": (460, 500)}, target_time=420, offset_minutes=0,
        is_asymmetric=True,
    )
    tight = SplitDecoder(max_tour_duration=40, **kwargs)
    assert trip_of(tight._build_trips_with_tw(["A"], DEPOT, m, {"A": (0, 1)}), 0, 0) is None
    loose = SplitDecoder(max_tour_duration=50, **kwargs)
    assert trip_of(loose._build_trips_with_tw(["A"], DEPOT, m, {"A": (0, 1)}), 0, 0) is not None


# ── no target: no default anchor ─────────────────────────────────────────────


def test_windows_without_target_time_raise_value_error():
    nodes = [DEPOT, "A"]
    m = matrix_from({(DEPOT, "A"): 10, ("A", DEPOT): 10}, nodes)
    for direction in (Direction.PICKUP, Direction.DROPOFF):
        with pytest.raises(ValueError, match="target_time"):
            decode_with_time_windows(
                giant_tour=["A"], depot=DEPOT, distance_matrix=m,
                demands={"A": (0, 1)}, time_windows={"A": (480, 540)},
                direction=direction, target_time=None,
            )


def test_target_time_zero_is_a_target_not_a_missing_one():
    nodes = [DEPOT, "A"]
    m = matrix_from({(DEPOT, "A"): 10, ("A", DEPOT): 10}, nodes)
    result = decode_with_time_windows(
        giant_tour=["A"], depot=DEPOT, distance_matrix=m, demands={"A": (0, 1)},
        time_windows={"A": (0, 60)}, direction=Direction.DROPOFF, target_time=0,
        offset_minutes=0, is_asymmetric=True,
    )
    assert result["schedules"][0]["departure_time"] == 0


# ── service times (OQ-MT1-5 b) ───────────────────────────────────────────────


def _service_decoder(**service):
    return SplitDecoder(
        use_time_windows=True, direction=Direction.PICKUP, target_time=500,
        offset_minutes=0, time_windows={"A": (0, 480), "B": (0, 495)},
        max_tour_duration=1000, is_asymmetric=True, **service,
    )


def test_service_time_shifts_the_schedule_and_can_break_a_trip():
    nodes = [DEPOT, "A", "B"]
    m = matrix_from({(DEPOT, "A"): 10, ("A", "B"): 5, ("B", DEPOT): 10}, nodes)
    demands = {"A": (1, 0), "B": (0, 1)}

    base = _service_decoder()._build_trips_with_tw(["A", "B"], DEPOT, m, demands)
    t0 = trip_of(base, 0, 1)
    assert t0.time_window_violations == 0 and t0.departure_time == pytest.approx(470)

    # dwell 2 per stop, 3 extra for the Sw student at A -> service A 5, B 2
    shifted = _service_decoder(stop_dwell_minutes=2, sw_boarding_minutes=3)
    trips = shifted._build_trips_with_tw(["A", "B"], DEPOT, m, demands)
    t1 = trip_of(trips, 0, 1)
    expected = simulate_school_pickup(
        ["A", "B"], arc_fn(m), deadline=500, windows={"A": (0, 480), "B": (0, 495)},
        service={"A": 2, "B": 2}, sw_boarding=3, sw_counts={"A": 1, "B": 0}, depot=DEPOT,
    )
    assert t1.departure_time == pytest.approx(expected.start)
    assert t1.departure_time < t0.departure_time  # service pulls the start earlier
    assert t1.time_window_violations == len(expected.violations)


def test_zero_service_equals_default():
    nodes = [DEPOT, "A", "B"]
    m = matrix_from({(DEPOT, "A"): 10, ("A", "B"): 5, ("B", DEPOT): 10}, nodes)
    demands = {"A": (1, 0), "B": (0, 1)}
    a = _service_decoder()._build_trips_with_tw(["A", "B"], DEPOT, m, demands)
    b = _service_decoder(stop_dwell_minutes=0, sw_boarding_minutes=0)._build_trips_with_tw(
        ["A", "B"], DEPOT, m, demands
    )
    assert a == b


# ── H3 left open on 2026-10-28: windowed ga_split at offset 0 ────────────────


def test_h3_scenario_at_offset_zero_is_one_feasible_route():
    # The O09 close-evidence scenario: target 08:30, A pickup 08:00 (window 07:30-08:00),
    # B no window, D-A 10, A-B 5, B-D 10, every other arc 100.
    nodes = [DEPOT, "A", "B"]
    m = matrix_from({(DEPOT, "A"): 10, ("A", "B"): 5, ("B", DEPOT): 10}, nodes)
    solution = solve_ga_split(
        ["A", "B"], DEPOT, m, {"A": (0, 1), "B": (0, 1)}, 4, 5, 120.0,
        {"population_size": 4, "max_iterations": 3, "max_no_improvement": 3},
        random.Random(42),
        use_time_windows=True, time_windows={"A": (450, 480)}, direction="pickup",
        target_time=510, offset_minutes=0, is_asymmetric=True,
    )
    result = solution.final_result
    assert result["routes"] == [["A", "B"]]
    assert result["time_window_violations"] == 0
    assert "error" not in result
    schedule = result["schedules"][0]
    assert schedule["departure_time"] == pytest.approx(470)  # 07:50, as in MT1-01 test 3


# ── demo shape: windows off, target_time set, offset_minutes not sent ────────
# Pinned on the unmodified decoder (WIP 4ddd2d36) and required to stay equal.

_XY = {"D": (0, 0), "L1": (4, 1), "L2": (7, 5), "L3": (2, 9), "L4": (11, 3),
       "L5": (9, 12), "L6": (14, 8)}
_DEMO_MATRIX = {
    a: {
        b: (0 if a == b else round(
            ((_XY[a][0] - _XY[b][0]) ** 2 + (_XY[a][1] - _XY[b][1]) ** 2) ** 0.5 * 1.3
            + (0.37 if a < b else 0.0), 2))
        for b in _XY
    }
    for a in _XY
}
_DEMO_DEMANDS = {"L1": (1, 0), "L2": (0, 1), "L3": (1, 0), "L4": (0, 1), "L5": (1, 0), "L6": (0, 1)}
_NAMES = ["L1", "L2", "L3", "L4", "L5", "L6"]


def _demo_decode(direction):
    decoder = SplitDecoder(
        sw_capacity=2, so_capacity=2, max_tour_duration=60, target_time=495,
        use_time_windows=False, direction=direction, is_asymmetric=True, max_ride_time=40,
    )
    return decoder.decode(_NAMES, DEPOT, _DEMO_MATRIX, _DEMO_DEMANDS)


def test_demo_shape_decoder_pickup_is_pinned():
    r = _demo_decode(Direction.PICKUP)
    assert r["routes"] == [["L1"], ["L2", "L3", "L4"], ["L5", "L6"]]
    assert r["costs"] == pytest.approx([11.09, 49.49, 49.52])
    assert r["total_cost"] == pytest.approx(110.1)
    assert r["time_window_violations"] == 0
    assert "schedules" not in r


def test_demo_shape_decoder_dropoff_is_pinned():
    r = _demo_decode(Direction.DROPOFF)
    assert r["routes"] == [["L1", "L2", "L3"], ["L4", "L5", "L6"]]
    assert r["costs"] == pytest.approx([33.28, 57.2])
    assert r["total_cost"] == pytest.approx(90.48)
    assert r["time_window_violations"] == 0
    assert "schedules" not in r


def test_demo_shape_ga_split_is_pinned():
    solution = solve_ga_split(
        _NAMES, DEPOT, _DEMO_MATRIX, _DEMO_DEMANDS, 2, 2, 60,
        {"population_size": 8, "max_iterations": 5, "max_no_improvement": 4},
        random.Random(42),
        use_time_windows=False, time_windows=None, direction="pickup",
        target_time=495, is_asymmetric=True, max_ride_time=40,
    )
    r = solution.final_result
    assert r["routes"] == [["L1", "L2"], ["L4", "L6", "L5", "L3"]]
    assert r["costs"] == pytest.approx([23.78, 53.35])
    assert r["total_cost"] == pytest.approx(77.13)
    assert r["time_window_violations"] == 0
