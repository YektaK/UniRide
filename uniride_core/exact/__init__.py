"""Exact-solver contracts (offline research tooling, design EXACT_SOLVER_AMPL_DESIGN.md).

Never imported by optimizer_api or src and never registered in the production
registry. This package must not import amplpy at import time.
"""
from .day_instance import (
    NOT_RUN_ENUMERATION_CAP,
    DayColumn,
    DayInstance,
    DayWave,
    build_day_instance,
)
from .wave_instance import (
    EXACT_STATUSES,
    ExactResult,
    VehicleTypeSpec,
    WaveInstance,
    compute_matrix_sha256,
)

__all__ = [
    "EXACT_STATUSES", "ExactResult", "VehicleTypeSpec", "WaveInstance", "compute_matrix_sha256",
    "NOT_RUN_ENUMERATION_CAP", "DayColumn", "DayInstance", "DayWave", "build_day_instance",
]
