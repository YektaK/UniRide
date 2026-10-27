from __future__ import annotations

from uniride_core.algorithms.route_scheduling import minutes_to_time

# MT1-03 (audit H3): the calculate_scheduled_times tests that lived here pinned the
# defect (a backward walk from the last window close, no return arc, no waits); that
# function is removed. The schedule is built by the simulator (test_route_schedule.py)
# and returned by the router (optimizer_api/tests/test_mt1_03_returned_schedule.py).


def test_minutes_to_time_clamps_to_valid_day_range():
    assert minutes_to_time(-10) == "00:00"
    assert minutes_to_time(9 * 60 + 5) == "09:05"
    assert minutes_to_time(24 * 60 + 30) == "23:59"


def test_minutes_to_time_rounds_down_by_default_and_up_on_request():
    assert minutes_to_time(479.6) == "07:59"
    assert minutes_to_time(494.1, rounding="ceil") == "08:15"
