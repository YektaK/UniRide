"""Optional wall-clock safety deadline for the SOTA TSP solvers (audit H11, MT6-03).

SOTA solvers stop on iteration and stagnation limits only, so a result is a
function of its seed and configuration. The one allowed use of the wall clock is
this opt-in deadline (``deadline_seconds``; ``None`` means no deadline and no
clock call at all). When the deadline is reached the solver stops early and the
result says so: ``termination_reason == "wall_clock_deadline"`` and
``reproducible is False`` (both in ``TSPResult.extra_stats``).

The deadline is soft. It is checked once per iteration (the iterative solvers skip the
check after the last iteration, which is the iteration limit anyway) and never inside
the local search, so a run can overrun it by one full iteration plus the whole final
polish, which always runs with its iteration limit. It is a safety net against runaway runs, not a precise time budget.

This module is the only place in ``sota_tsp`` where the clock is compared with a
limit (``test_mt6_sota_deterministic_stop.py`` enforces that).
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional

TERMINATION_ITERATION_LIMIT = "iteration_limit"
TERMINATION_WALL_CLOCK_DEADLINE = "wall_clock_deadline"


class WallClockDeadline:
    """Started on construction; ``expired()`` is cheap and never true when unset."""

    def __init__(self, seconds: Optional[float]):
        if seconds is not None:
            seconds = float(seconds)
            if not math.isfinite(seconds) or seconds <= 0.0:
                raise ValueError("deadline_seconds must be a positive finite number or None")
        self._seconds = seconds
        self._start = time.monotonic() if seconds is not None else 0.0
        self.hit = False

    @property
    def seconds(self) -> Optional[float]:
        return self._seconds

    def expired(self) -> bool:
        if self._seconds is None:
            return False
        if not self.hit and time.monotonic() - self._start > self._seconds:
            self.hit = True
        return self.hit

    def stats(self) -> Dict[str, Any]:
        """Result metadata: why the solver stopped and whether the result is a pure function of seed + config."""
        return {
            "termination_reason": (
                TERMINATION_WALL_CLOCK_DEADLINE if self.hit else TERMINATION_ITERATION_LIMIT
            ),
            "reproducible": not self.hit,
            "deadline_seconds": self._seconds,
        }
