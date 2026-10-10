"""Frozen data contracts for one exact-solver wave (design section 1.1, WP-E0)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Sequence

EXACT_STATUSES = frozenset(
    {"not_run", "optimal", "feasible", "infeasible", "rejected", "input_rejected", "backend_unavailable", "limit_reached"}
)
_CLASSES = ("Sw", "So")
_DIRECTIONS = ("pickup", "dropoff")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_matrix(matrix: Sequence[Sequence[int]]) -> None:
    n = len(matrix)
    for i, row in enumerate(matrix):
        if len(row) != n:
            raise ValueError(f"matrix is not square (row {i} has {len(row)} entries, expected {n})")
        for j, value in enumerate(row):
            if not _is_int(value) or value < 0:
                raise ValueError(f"arc [{i}][{j}] must be an integer >= 0, got {value!r}")
    for i in range(n):
        if matrix[i][i] != 0:
            raise ValueError(f"diagonal arc [{i}][{i}] must be 0")


def compute_matrix_sha256(matrix: Sequence[Sequence[int]]) -> str:
    """sha256 of the canonical JSON of an integer matrix (the wave's own slice, not the snapshot)."""
    _check_matrix(matrix)
    payload = json.dumps([list(row) for row in matrix], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class VehicleTypeSpec:
    type_id: str
    sw_capacity: int
    so_capacity: int
    cooldown_minutes: int
    total_capacity: Optional[int] = None


@dataclass(frozen=True)
class WaveInstance:
    """One wave: node 0 is the depot, nodes 1..n the occurrences (one node per occurrence)."""

    wave_id: str
    service_date: str
    direction: str
    anchor_minutes: int
    max_ride_minutes: int
    max_tour_minutes: int
    depot_code: str
    occurrence_ids: tuple
    location_codes: tuple
    classes: tuple
    matrix: tuple
    matrix_sha256: str
    arc_slice_sha256: str  # runner's own sha of the archived per-date arc slice
    declared_snapshot_sha256: str  # sha declared by the archive (describes the full snapshot, not the slice)

    @property
    def legs(self) -> int:
        return len(self.occurrence_ids)

    def __post_init__(self) -> None:
        if self.direction not in _DIRECTIONS:
            raise ValueError(f"direction must be one of {_DIRECTIONS}")
        n = len(self.occurrence_ids)
        if len(self.location_codes) != n or len(self.classes) != n:
            raise ValueError("occurrence_ids, location_codes and classes must have equal length")
        if any(c not in _CLASSES for c in self.classes):
            raise ValueError(f"class must be one of {_CLASSES}")
        if len(self.matrix) != n + 1:
            raise ValueError(f"matrix must be {n + 1}x{n + 1} (depot + {n} legs)")
        _check_matrix(self.matrix)
        if compute_matrix_sha256(self.matrix) != self.matrix_sha256:
            raise ValueError("matrix_sha256 does not match the matrix")


@dataclass(frozen=True)
class ExactResult:
    wave_id: str
    status: str
    routes: tuple  # tuple of tuples of occurrence ids
    route_count: Optional[int]
    total_cost: Optional[int]

    def __post_init__(self) -> None:
        if self.status not in EXACT_STATUSES:
            raise ValueError(f"unknown status {self.status!r}")
