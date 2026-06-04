from uniride_core.algorithms import time_window_violation_tracker as core_tracker
from utils import time_window_violation_tracker as api_tracker


def test_time_window_violation_tracker_api_shim_reexports_core_symbols():
    assert api_tracker.TimeWindowViolationTracker is core_tracker.TimeWindowViolationTracker
    assert api_tracker.ViolationType is core_tracker.ViolationType
    assert api_tracker.create_tracker_from_students is core_tracker.create_tracker_from_students
