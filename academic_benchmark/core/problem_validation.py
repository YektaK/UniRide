"""Canonical TSP/ATSP problem validation for academic preflight."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from numbers import Real

from uniride_core.algorithms.capabilities import ProblemContract


@dataclass(frozen=True)
class ProblemValidationReport:
    """Immutable structural and identity evidence for one loaded problem."""

    problem_name: str
    contract: ProblemContract
    dimension: int
    matrix_kind: str
    matrix: tuple[tuple[float, ...], ...]
    matrix_sha256: str
    observed_asymmetric: bool


def _problem_name(problem: object) -> str:
    return str(getattr(problem, "name", "<unknown>"))


def _contract_for(problem: object) -> ProblemContract:
    declared = getattr(problem, "problem_type", None)
    if isinstance(declared, ProblemContract):
        return declared
    normalized = str(declared or "").lower()
    try:
        return ProblemContract(normalized)
    except ValueError as exc:
        raise ValueError(f"{_problem_name(problem)}: problem_type must be TSP or ATSP") from exc


def _matrix_source(problem: object) -> tuple[object | None, str]:
    """Select the authoritative cost matrix without materializing it twice."""
    time_declared = bool(getattr(problem, "is_time_matrix", False))
    preferred = ("time_matrix", "travel_time") if time_declared else ("dist_matrix", "distance")
    fallback = ("dist_matrix", "distance") if time_declared else ("time_matrix", "travel_time")
    for attribute, default_kind in (preferred, fallback):
        matrix = getattr(problem, attribute, None)
        if matrix is not None:
            declared_kind = str(getattr(problem, "matrix_kind", "") or "")
            if attribute == "time_matrix" and declared_kind in {"", "distance"}:
                declared_kind = default_kind
            return matrix, declared_kind or default_kind
    core_matrix = getattr(problem, "matrix", None)
    if core_matrix is not None and hasattr(core_matrix, "values"):
        return core_matrix.values, str(getattr(core_matrix, "kind", "distance") or "distance")
    return None, "distance"


def _extract_matrix_once(problem: object) -> tuple[object, str]:
    matrix, matrix_kind = _matrix_source(problem)
    if matrix is not None:
        return matrix, matrix_kind
    prepare = getattr(problem, "prepare_matrices", None)
    if callable(prepare):
        prepare()
        matrix, matrix_kind = _matrix_source(problem)
        if matrix is not None:
            return matrix, matrix_kind
    raise ValueError(f"{_problem_name(problem)}: no matrix is available")


def _normalized_matrix(problem: object, matrix: object) -> tuple[tuple[float, ...], ...]:
    try:
        rows = tuple(tuple(row) for row in matrix)  # type: ignore[union-attr]
    except TypeError as exc:
        raise ValueError(f"{_problem_name(problem)}: matrix must be square") from exc
    dimension = len(rows)
    if not dimension or any(len(row) != dimension for row in rows):
        raise ValueError(f"{_problem_name(problem)}: matrix must be square")
    declared_dimension = getattr(problem, "dimension", None)
    if (isinstance(declared_dimension, bool) or not isinstance(declared_dimension, int)
            or declared_dimension != dimension):
        raise ValueError(f"{_problem_name(problem)}: declared dimension does not match matrix")
    normalized: list[tuple[float, ...]] = []
    for row_index, row in enumerate(rows):
        normalized_row: list[float] = []
        for column_index, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f"{_problem_name(problem)}: matrix costs must be numeric")
            cost = float(value)
            if not math.isfinite(cost):
                raise ValueError(f"{_problem_name(problem)}: matrix costs must be finite")
            # Explicit TSPLIB matrices may carry a finite diagonal sentinel
            # (for example ft53's 9999999); only travel arcs are non-negative.
            if row_index != column_index and cost < 0:
                raise ValueError(f"{_problem_name(problem)}: off-diagonal costs must be non-negative")
            normalized_row.append(cost)
        normalized.append(tuple(normalized_row))
    return tuple(normalized)


def validate_problem_for_preflight(problem: object) -> ProblemValidationReport:
    """Extract, validate, and fingerprint one declared TSP/ATSP problem."""
    contract = _contract_for(problem)
    matrix_source, matrix_kind = _extract_matrix_once(problem)
    matrix = _normalized_matrix(problem, matrix_source)
    payload = json.dumps(matrix, separators=(",", ":"), allow_nan=False).encode("utf-8")
    observed_asymmetric = any(
        not math.isclose(matrix[row][column], matrix[column][row], rel_tol=0.0, abs_tol=1e-12)
        for row in range(len(matrix))
        for column in range(row + 1, len(matrix))
    )
    return ProblemValidationReport(
        problem_name=_problem_name(problem),
        contract=contract,
        dimension=len(matrix),
        matrix_kind=matrix_kind,
        matrix=matrix,
        matrix_sha256=hashlib.sha256(payload).hexdigest(),
        observed_asymmetric=observed_asymmetric,
    )
