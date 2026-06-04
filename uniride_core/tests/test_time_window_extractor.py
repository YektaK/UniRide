from __future__ import annotations

from uniride_core.algorithms.time_window_extractor import (
    TimeWindow,
    TimeWindowExtractor,
    weekly_schedule_to_optimization_input,
)


def test_time_window_clamps_and_orders_bounds():
    window = TimeWindow(earliest=25 * 60, latest=-5)

    assert window.earliest == 0
    assert window.latest == 24 * 60
    assert window.to_time_strings() == ("00:00", "24:00")


def test_extractor_builds_pickup_and_dropoff_windows():
    entry = {"startTime": "09:00", "endTime": "14:10"}
    extractor = TimeWindowExtractor(window_minutes=30)

    pickup = extractor.extract(entry, "pickup")
    dropoff = extractor.extract(entry, "dropoff")

    assert pickup is not None
    assert pickup.to_dict() == {"earliest": 510, "latest": 540}
    assert dropoff is not None
    assert dropoff.to_dict() == {"earliest": 15 * 60, "latest": 15 * 60 + 30}


def test_weekly_schedule_to_optimization_input_filters_target_day():
    result = weekly_schedule_to_optimization_input(
        schedules=[
            {
                "user_id": "u1",
                "entries": [
                    {"dayOfWeek": "monday", "startTime": "09:00", "endTime": "14:00"},
                    {"dayOfWeek": "tuesday", "startTime": "10:00", "endTime": "15:00"},
                ],
            }
        ],
        users={
            "u1": {
                "name": "Student One",
                "location_code": "Sw1",
                "disability_type": "Sw",
            }
        },
        target_date="2026-06-01",
        direction="pickup",
    )

    assert result["target_day"] == "monday"
    assert result["students"] == [
        {
            "id": "u1",
            "name": "Student One",
            "location_code": "Sw1",
            "disability_type": "Sw",
            "pickup_time": "09:00",
            "dropoff_time": None,
            "direction": "pickup",
        }
    ]
    assert result["time_windows"] == {"Sw1": {"earliest": 510, "latest": 540}}
