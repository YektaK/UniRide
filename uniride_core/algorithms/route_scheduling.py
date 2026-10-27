"""Display helpers for route times shared by core and API response adapters.

MT1-03 (audit H3, decision O09): the schedule itself is built by the route
simulator (``uniride_core.algorithms.route_schedule``) on the authoritative arcs.
The former ``calculate_scheduled_times`` walked backwards from a window close with
no return arc and no waits (a third, uncertified schedule model); it is gone. This
module only formats exact minutes for the HH:MM compatibility fields.
"""

from __future__ import annotations

import math

# Absorbs binary float noise only (a sum of decimal arcs landing a hair off a whole
# minute); far below any meaningful duration, so 479.6 still shows 07:59.
_DISPLAY_EPSILON = 1e-6

_LAST_MINUTE = 23 * 60 + 59


def minutes_to_time(minutes: float, rounding: str = "floor") -> str:
    """Convert minutes from midnight to a clamped HH:MM string.

    ``rounding="floor"`` (default) shows a stop time rounded down; ``"ceil"``
    rounds up and is used for the pickup school arrival (owner decision
    OQ-MT1-10 b). The exact value is kept in the response's minute fields.
    """
    if rounding == "floor":
        whole = math.floor(minutes + _DISPLAY_EPSILON)
    elif rounding == "ceil":
        whole = math.ceil(minutes - _DISPLAY_EPSILON)
    else:
        raise ValueError(f"unknown rounding {rounding!r}; use 'floor' or 'ceil'")
    total = max(0, min(int(whole), _LAST_MINUTE))
    hours = total // 60
    mins = total % 60
    return f"{hours:02d}:{mins:02d}"


__all__ = ["minutes_to_time"]
