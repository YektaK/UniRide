"""Strict vs soft time-window mode regressions for the split decoders.

Task B: SplitDecoder gains ``strict_time_windows``; LinearSplitDecoder's
``PenaltyConfig.allow_time_warp`` implements the strict/soft pair.
Task C: pickup prefixes are enumerated per capacity-feasible prefix, and
duration excess is tracked separately from time-window warp.
"""

import math

import pytest

from uniride_core.algorithms.linear_split_decoder import (
    LinearSplitDecoder,
    LinearSplitResult,
    PenaltyConfig,
)
from uniride_core.algorithms.string_split_decoder import Direction, SplitDecoder, Trip

DEPOT = "DEPOT"


def _complete_pickup_matrix():
    return {
        DEPOT: {"L1": 10.0, "L2": 20.0},
        "L1": {DEPOT: 10.0, "L2": 10.0},
        "L2": {DEPOT: 10.0, "L1": 10.0},
    }


def _complete_dropoff_matrix():
    return {
        DEPOT: {"L1": 10.0, "L2": 30.0, "L3": 40.0},
        "L1": {DEPOT: 10.0, "L2": 20.0, "L3": 30.0},
        "L2": {DEPOT: 10.0, "L1": 20.0, "L3": 10.0},
        "L3": {DEPOT: 10.0, "L1": 30.0, "L2": 10.0},
    }


def _demands_sw(*locs):
    return {loc: (1, 0) for loc in locs}


# ── Task B: strict vs soft time-window modes ────────────────────────────────


def test_split_soft_keeps_violating_pickup_trip():
    decoder = SplitDecoder(
        use_time_windows=True,
        direction=Direction.PICKUP,
        time_windows={"L1": (100, 110), "L2": (100, 200)},
        max_tour_duration=1000,
        offset_minutes=0,
    )
    trips = decoder._build_trips_with_tw(
        ["L1", "L2"], DEPOT, _complete_pickup_matrix(), _demands_sw("L1", "L2")
    )

    violating = next((t for t in trips[2] if t.start_idx == 0 and t.end_idx == 1), None)
    assert violating is not None
    assert violating.time_window_violations == 2


def test_split_strict_drops_violating_pickup_trip():
    decoder = SplitDecoder(
        use_time_windows=True,
        direction=Direction.PICKUP,
        time_windows={"L1": (100, 110), "L2": (100, 200)},
        max_tour_duration=1000,
        offset_minutes=0,
        strict_time_windows=True,
    )
    trips = decoder._build_trips_with_tw(
        ["L1", "L2"], DEPOT, _complete_pickup_matrix(), _demands_sw("L1", "L2")
    )

    for k, trip_list in trips.items():
        assert all(t.time_window_violations == 0 for t in trip_list)


def test_split_soft_keeps_violating_dropoff_trip():
    decoder = SplitDecoder(
        use_time_windows=True,
        direction=Direction.DROPOFF,
        time_windows={"L1": (100, 150), "L2": (50, 80), "L3": (10, 20)},
        max_tour_duration=1000,
        target_time=50,
        offset_minutes=0,
    )
    trips = decoder._build_trips_with_tw(
        ["L1", "L2", "L3"], DEPOT, _complete_dropoff_matrix(), _demands_sw("L1", "L2", "L3")
    )

    violating = next((t for t in trips[3] if t.start_idx == 0 and t.end_idx == 2), None)
    assert violating is not None
    assert violating.time_window_violations == 2


def test_split_strict_blocks_violating_dropoff_trip():
    decoder = SplitDecoder(
        use_time_windows=True,
        direction=Direction.DROPOFF,
        time_windows={"L1": (100, 150), "L2": (50, 80), "L3": (10, 20)},
        max_tour_duration=1000,
        target_time=50,
        offset_minutes=0,
        strict_time_windows=True,
    )
    trips = decoder._build_trips_with_tw(
        ["L1", "L2", "L3"], DEPOT, _complete_dropoff_matrix(), _demands_sw("L1", "L2", "L3")
    )

    for k, trip_list in trips.items():
        assert all(t.time_window_violations == 0 for t in trip_list)


def _linear_matrix():
    return {
        DEPOT: {"A": 5.0, "B": 5.0},
        "A": {DEPOT: 5.0, "B": 7.0},
        "B": {DEPOT: 5.0, "A": 7.0},
    }


def test_linear_soft_accepts_tw_violating_route():
    decoder = LinearSplitDecoder(
        time_windows={"B": (2, 110)},
        max_tour_duration=120,
        penalty_config=PenaltyConfig(allow_time_warp=True),
    )
    res = decoder.decode(["A", "B"], DEPOT, _linear_matrix(), {"A": (1, 0), "B": (1, 0)})

    assert res.routes
    assert res.time_window_violations > 0
    assert res.final_objective < float("inf")
    assert any(s["tw_violations"] > 0 for s in res.schedules)


def test_linear_strict_never_emits_tw_violating_route():
    decoder = LinearSplitDecoder(
        time_windows={"B": (2, 110)},
        max_tour_duration=120,
        penalty_config=PenaltyConfig(allow_time_warp=False),
    )
    res = decoder.decode(["A", "B"], DEPOT, _linear_matrix(), {"A": (1, 0), "B": (1, 0)})

    assert math.isinf(res.final_objective)
    assert res.routes == []


# ── Task C: enumerate pickup prefixes ────────────────────────────────────────


def _cap2_tour_matrix():
    return {
        DEPOT: {"A": 10.0, "B": 30.0, "C": 50.0},
        "A": {DEPOT: 20.0, "B": 10.0, "C": 40.0},
        "B": {DEPOT: 10.0, "A": 40.0, "C": 10.0},
        "C": {DEPOT: 10.0, "A": 40.0, "B": 10.0},
    }


def test_pickup_enumerates_every_capacity_feasible_prefix():
    decoder = SplitDecoder(
        sw_capacity=2,
        so_capacity=5,
        use_time_windows=True,
        direction=Direction.PICKUP,
        max_tour_duration=1000,
        offset_minutes=0,
    )
    trips = decoder._build_trips_with_tw(
        ["A", "B", "C"], DEPOT, _cap2_tour_matrix(), _demands_sw("A", "B", "C")
    )

    assert any(t.start_idx == 0 and t.end_idx == 0 for t in trips[1])
    assert any(t.start_idx == 0 and t.end_idx == 1 for t in trips[2])
    assert not any(t.start_idx == 0 and t.end_idx == 2 for t in trips[3])


def test_pickup_prefix_enumeration_unblocks_dp():
    decoder = SplitDecoder(
        sw_capacity=2,
        so_capacity=5,
        use_time_windows=True,
        direction=Direction.PICKUP,
        max_tour_duration=1000,
        offset_minutes=0,
    )
    result = decoder.decode(["A", "B", "C"], DEPOT, _cap2_tour_matrix(), _demands_sw("A", "B", "C"))

    assert "error" not in result
    assert result["total_cost"] == pytest.approx(80.0)
    assert result["routes"] == [["A"], ["B", "C"]]


def test_dropoff_still_emits_every_prefix():
    decoder = SplitDecoder(
        sw_capacity=2,
        so_capacity=5,
        use_time_windows=True,
        direction=Direction.DROPOFF,
        max_tour_duration=1000,
        offset_minutes=0,
    )
    trips = decoder._build_trips_with_tw(
        ["A", "B", "C"], DEPOT, _cap2_tour_matrix(), _demands_sw("A", "B", "C")
    )

    assert any(t.start_idx == 0 and t.end_idx == 1 for t in trips[2])


# ── Task C: duration excess separated from time-warp violation ───────────────


def _duration_matrix():
    return {
        DEPOT: {"A": 50.0},
        "A": {DEPOT: 50.0},
    }


def test_penalty_config_exposes_duration_penalty_rate():
    assert PenaltyConfig().duration_penalty_rate == 10.0


def test_duration_excess_tracked_without_tw_violation():
    decoder = LinearSplitDecoder(
        max_tour_duration=80,
        penalty_config=PenaltyConfig(allow_time_warp=True),
    )
    res = decoder.decode(["A"], DEPOT, _duration_matrix(), {"A": (1, 0)})

    assert res.time_window_violations == 0
    assert res.duration_excess_minutes == pytest.approx(20.0)
    assert res.final_objective == pytest.approx(300.0)
    assert res.schedules[0]["duration_excess"] == pytest.approx(20.0)
    assert res.schedules[0]["tw_violations"] == 0


def test_tw_violation_reports_without_duration_excess():
    decoder = LinearSplitDecoder(
        max_tour_duration=200,
        time_windows={"A": (0, 100)},
        penalty_config=PenaltyConfig(allow_time_warp=True),
    )
    res = decoder.decode(["A"], DEPOT, _duration_matrix(), {"A": (1, 0)})

    assert res.duration_excess_minutes == 0
    assert res.time_window_violations > 0
    assert res.time_window_violations != res.duration_excess_minutes


def test_linear_result_defaults_duration_excess_zero():
    res = LinearSplitResult([], 0.0, 0.0, 0.0, 0, 0, 0, [])
    assert res.duration_excess_minutes == 0.0