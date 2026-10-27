from uniride_core.algorithms.route_scheduling import minutes_to_time

# MT1-03 (audit H3): the calculate_scheduled_times tests that lived here pinned the
# defect (a backward walk from the last window close, no return arc, no waits).
# The schedule now comes from the route simulator on the authoritative arcs and is
# tested in test_mt1_03_returned_schedule.py; only the display helper stays here.


def test_minutes_to_time_clamps_to_valid_day_range():
    assert minutes_to_time(-10) == "00:00"
    assert minutes_to_time(9 * 60 + 5) == "09:05"
    assert minutes_to_time(24 * 60 + 30) == "23:59"
