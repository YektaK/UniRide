"""Compatibility exports for time-window extraction helpers."""

from uniride_core.algorithms.time_window_extractor import (  # noqa: F401
    TimeWindow,
    TimeWindowExtractor,
    weekly_schedule_to_optimization_input,
)

__all__ = ["TimeWindow", "TimeWindowExtractor", "weekly_schedule_to_optimization_input"]
