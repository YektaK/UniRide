"""Reported tour-cost typing shared by the legacy academic executors (M18).

TSPLIB distances are integers, so legacy executors historically reported the
cycle cost as an ``int``. That is exact only when every matrix entry is
integer-valued; on a fractional matrix ``int()`` silently truncates the cost
(for example 40 for a true 40.28692). ``report_cycle_cost`` keeps the ``int``
for integer-valued matrices and returns the unrounded float otherwise.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def matrix_is_integer_valued(matrix: Any) -> bool:
    values = np.asarray(matrix, dtype=np.float64)
    return bool(np.all(np.isfinite(values) & (values == np.floor(values))))


def report_cycle_cost(total: Any, matrix: Any) -> Any:
    """Return ``int(total)`` for an integer-valued matrix, else the float total."""
    if matrix_is_integer_valued(matrix):
        return int(total)
    return float(total)
