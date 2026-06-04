from uniride_core.algorithms import (
    resource_profiler as core_resource_profiler,
    route_scheduling as core_route_scheduling,
    time_window_extractor as core_time_window_extractor,
)
from utils import resource_profiler as api_resource_profiler
from utils import scheduling as api_scheduling
from utils import time_window_extractor as api_time_window_extractor


def test_scheduling_utility_shim_reexports_core_helpers():
    assert api_scheduling.calculate_scheduled_times is core_route_scheduling.calculate_scheduled_times
    assert api_scheduling.minutes_to_time is core_route_scheduling.minutes_to_time


def test_time_window_extractor_utility_shim_reexports_core_helpers():
    assert api_time_window_extractor.TimeWindow is core_time_window_extractor.TimeWindow
    assert api_time_window_extractor.TimeWindowExtractor is core_time_window_extractor.TimeWindowExtractor
    assert (
        api_time_window_extractor.weekly_schedule_to_optimization_input
        is core_time_window_extractor.weekly_schedule_to_optimization_input
    )


def test_resource_profiler_utility_shim_reexports_core_helpers():
    assert api_resource_profiler.ResourceProfiler is core_resource_profiler.ResourceProfiler
    assert api_resource_profiler.ResourceBlock is core_resource_profiler.ResourceBlock
    assert api_resource_profiler.HourlyDemand is core_resource_profiler.HourlyDemand
    assert api_resource_profiler.Bottleneck is core_resource_profiler.Bottleneck
    assert api_resource_profiler.TimeShiftSuggestion is core_resource_profiler.TimeShiftSuggestion
    assert api_resource_profiler.minutes_to_time_str is core_resource_profiler.minutes_to_time_str
    assert api_resource_profiler.time_str_to_minutes is core_resource_profiler.time_str_to_minutes
