"""One canonical reading of a problem type for the analysis layer (A20 L10).

Run rows store the lowercase problem type (``studies/run.py``), exact-reference records and dataset manifests carry the uppercase
contract (``TSP``, ``ATSP``). Wherever the analysis layer compares a problem type with a contract, reference or family value, both
sides go through ``canonical_problem_contract`` and the comparison is between ``ProblemContract`` members. A value that is not a
TSP/ATSP contract (for example ``cvrp`` or ``uniride_wave``) is refused with ``ProblemContractError``, never compared as a string.
"""
from __future__ import annotations

from typing import Any

from uniride_core.algorithms.capabilities import ProblemContract


class ProblemContractError(ValueError):
    """The value is not a known TSP/ATSP problem contract."""


_BY_NAME = {member.value: member for member in ProblemContract}


def canonical_problem_contract(value: Any) -> ProblemContract:
    """``ProblemContract`` of a problem type spelled in any case (``tsp``, ``TSP``, ``Tsp``); unknown values, including a value with
    surrounding whitespace (``" tsp "``), are refused."""
    if isinstance(value, ProblemContract):
        return value
    if isinstance(value, str):
        member = _BY_NAME.get(value.lower())  # case mapping only: surrounding whitespace is not trimmed (A20 L10)
        if member is not None:
            return member
    raise ProblemContractError(f"{value!r} is not a known problem contract (expected one of {sorted(_BY_NAME)}, any case)")


def same_problem_contract(left: Any, right: Any) -> bool:
    """True when both values name the same contract; either value being unknown raises ``ProblemContractError``."""
    return canonical_problem_contract(left) is canonical_problem_contract(right)


__all__ = ["ProblemContractError", "canonical_problem_contract", "same_problem_contract"]
