"""Objective comparison of two route sets (WP-E11 J8; design ``JOINT_DAY_MODEL_DESIGN.md`` sections 1.3, 5.4 and 6.3).

Two plans of the same instance are compared on their objective tuple, never on route identity: a wave is ``(K, D)`` (routes,
total vehicle minutes), a typed day ``(S, total minutes, car minutes)``, a homogeneous day ``(K, total minutes)``. Equal
tuples with different routes are co-optimal alternatives (the optimum is not unique); any other difference is a mismatch.
This module only names the equal-objective case; ordering a mismatch as better or worse, and the remaining reproduction
categories (``equal``, ``production_better``, ``production_open`` ...), belong to the reproduction step.

Pure and deterministic; standard library only.
"""
from __future__ import annotations

from typing import Sequence

CO_OPTIMAL_ALTERNATIVE = "co_optimal_alternative"
MISMATCH = "mismatch"


def _check(objective: Sequence[int], name: str) -> tuple:
    values = tuple(objective)
    if not values:
        raise ValueError(f"{name}: an objective tuple needs at least one value")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name}: objective values must be integers, got {value!r}")
    return values


def compare_objectives(a: Sequence[int], b: Sequence[int]) -> str:
    """``co_optimal_alternative`` when the objective tuples are equal, else ``mismatch``. Routes are never looked at."""
    left, right = _check(a, "first objective"), _check(b, "second objective")
    if len(left) != len(right):
        raise ValueError(f"objective tuples differ in length: {len(left)} and {len(right)}")
    return CO_OPTIMAL_ALTERNATIVE if left == right else MISMATCH
