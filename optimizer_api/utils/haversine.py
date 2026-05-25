"""
Haversine distance and travel time estimation utilities.

DEPRECATED: Import from uniride_core.algorithms.distance instead.
This module is kept for backward compatibility.
"""

from uniride_core.algorithms.distance import (
    haversine_distance,
    estimate_travel_time,
)

__all__ = ["haversine_distance", "estimate_travel_time"]
