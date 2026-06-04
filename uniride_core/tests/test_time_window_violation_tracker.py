from __future__ import annotations

from uniride_core.algorithms.time_window_violation_tracker import (
    TimeWindowViolationTracker,
    ViolationType,
    create_tracker_from_students,
)


def test_violation_tracker_reports_late_arrival():
    tracker = TimeWindowViolationTracker({"A": (0, 10), "B": (10, 20)})
    matrix = {
        "D": {"A": 5, "B": 100},
        "A": {"B": 30, "D": 5},
        "B": {"D": 5},
    }

    report = tracker.analyze_route(["A", "B"], matrix, "D", vehicle_id="V1")

    assert report.total_violations == 1
    assert report.late_arrivals == 1
    assert report.violations[1].violation_type == ViolationType.LATE_ARRIVAL
    assert report.vehicle_id == "V1"


def test_create_tracker_from_students_builds_pickup_windows():
    tracker = create_tracker_from_students(
        [{"location_code": "A", "pickup_time": "09:00"}],
        window_size=30,
        direction="pickup",
    )

    assert tracker.time_windows == {"A": (8 * 60 + 30, 9 * 60)}
