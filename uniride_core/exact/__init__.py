"""Exact-solver contracts (offline research tooling, design EXACT_SOLVER_AMPL_DESIGN.md).

Never imported by optimizer_api or src and never registered in the production
registry. This package must not import amplpy at import time.
"""
from .day_bounds import DayBounds, InfeasibilityCertificate, compute_day_bounds
from .day_labels import CellLabel, label_cell
from .day_instance import (
    NOT_RUN_ENUMERATION_CAP,
    DayColumn,
    DayInstance,
    DayWave,
    build_day_instance,
)
from .gurobi_day_backend import (
    CrossCheck,
    GurobiSettings,
    crosscheck_day_results,
    gurobi_probe,
    run_day_stages_gurobi,
)
from .highs_backend import HighsSettings, DaySolveResult, highs_probe, run_day_stages
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
    "HighsSettings", "DaySolveResult", "highs_probe", "run_day_stages",
    "DayBounds", "InfeasibilityCertificate", "compute_day_bounds",
    "CrossCheck", "GurobiSettings", "crosscheck_day_results", "gurobi_probe", "run_day_stages_gurobi",
    "CellLabel", "label_cell",
]
