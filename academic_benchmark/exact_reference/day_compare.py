"""Objective comparison, blocking checks and reproduction categories of the joint day model (WP-E11 J8 and J9b; design
``JOINT_DAY_MODEL_DESIGN.md`` sections 1.3, 5.3, 5.4 and 6.3).

Two plans of the same instance are compared on their objective tuple, never on route identity: a wave is ``(K, D)`` (routes,
total vehicle minutes), a typed day ``(S, total minutes, car minutes)``, a homogeneous day ``(K, total minutes)``. Equal
tuples with different routes are co-optimal alternatives (the optimum is not unique); any other difference is a mismatch
(``compare_objectives``, J8).

J9b adds, on top of it and still as pure functions of numbers and labels:

* the blocking checks of design 5.3 (``check_joint_not_above_union``, ``check_joint_k_not_above_peaks``,
  ``check_value_not_below_bounds``), each raising ``BlockingDefect`` with a stable ``code``;
* the reproduction categories of design 6.3 (``reproduction_category``) with the disagreement rule: a prototype plan that
  passes the independent checker and is better than a production value that production proved (label ``optimal``, or the
  stage-1 value of ``optimal_stage1_by_bound``) is a blocking defect of production; production better than a prototype
  ``optimal`` is a described difference (``production_better``), not blocking. Nothing here changes a limit, an option or
  the model to approach a prototype number.

Production labels are the ``day_status`` labels of design 4.3 (strings; this module imports nothing from ``uniride_core``).
Standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

CO_OPTIMAL_ALTERNATIVE = "co_optimal_alternative"
MISMATCH = "mismatch"


def _check(objective: Sequence[int], name: str) -> tuple:
    values = tuple(objective)
    if not values:
        raise ValueError(f"{name}: an objective tuple needs at least one value")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name}: objective values must be integers, got {value!r}")
        if value < 0:
            raise ValueError(f"{name}: objective values must be non-negative, got {value!r}")
    return values


def compare_objectives(a: Sequence[int], b: Sequence[int]) -> str:
    """``co_optimal_alternative`` when the objective tuples are equal, else ``mismatch``. Routes are never looked at."""
    left, right = _check(a, "first objective"), _check(b, "second objective")
    if len(left) != len(right):
        raise ValueError(f"objective tuples differ in length: {len(left)} and {len(right)}")
    return CO_OPTIMAL_ALTERNATIVE if left == right else MISMATCH


# ------------------------------------------------------------------ blocking checks (design 5.3)
BLOCKING_PROTOTYPE_BEATS_OPTIMUM = "prototype_plan_beats_proven_optimum"
BLOCKING_PROTOTYPE_PLAN_VS_INFEASIBLE = "prototype_plan_contradicts_infeasibility_proof"
BLOCKING_JOINT_ABOVE_UNION = "joint_above_union_menu"
BLOCKING_JOINT_ABOVE_PEAK = "joint_above_archived_peak"
BLOCKING_VALUE_BELOW_BOUND = "value_below_valid_bound"


class BlockingDefect(Exception):
    """A result that cannot be true (design 5.3, 6.3): an error of the run, never a result. ``code`` is stable."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class NotComparable(ValueError):
    """Neither side has a value or a proof: the design names no reproduction category for it."""


def _int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name}: must be an integer, got {value!r}")
    if value < 0:
        raise ValueError(f"{name}: must be non-negative, got {value!r}")
    return value


def check_value_not_below_bounds(value: int, bounds: Mapping[str, int]) -> None:
    """A K or S below any valid bound (LB0, LB0w, LB_S, the solver bound, a proven optimum of the same cell) is an error."""
    _int(value, "value")
    for name in sorted(bounds):
        if value < _int(bounds[name], f"bound {name}"):
            raise BlockingDefect(BLOCKING_VALUE_BELOW_BOUND, f"value {value} is below the valid bound {name} = {bounds[name]}")


def check_joint_not_above_union(*, joint_cars: int, union_cars: int, joint_proven: bool, union_proven: bool) -> None:
    """Where both are proven, joint cars <= WP-E4b union-menu cars (design 2.2: every menu route is dominated by a column)."""
    _int(joint_cars, "joint_cars")
    _int(union_cars, "union_cars")
    if joint_proven and union_proven and joint_cars > union_cars:
        raise BlockingDefect(BLOCKING_JOINT_ABOVE_UNION,
                             f"joint cars {joint_cars} > union-menu cars {union_cars} while both are proven")


def check_joint_k_not_above_peaks(joint_k: int, peaks: Mapping[str, int], *, joint_proven: bool) -> None:
    """A proven joint K is at most the peak of every archived route set of the same day (GA routes, WP-E3 routes)."""
    _int(joint_k, "joint_k")
    for name in sorted(peaks):
        peak = _int(peaks[name], f"peak {name}")
        if joint_proven and joint_k > peak:
            raise BlockingDefect(BLOCKING_JOINT_ABOVE_PEAK, f"proven joint K {joint_k} > the peak {peak} of {name}")


# ------------------------------------------------------------------ reproduction categories (design 6.3)
CATEGORY_EQUAL = "equal"
CATEGORY_PRODUCTION_BETTER = "production_better"
CATEGORY_PRODUCTION_WORSE = "production_worse"
CATEGORY_PRODUCTION_OPEN = "production_open"
CATEGORY_PROTOTYPE_OPEN = "prototype_open"
CATEGORY_CO_OPTIMAL = CO_OPTIMAL_ALTERNATIVE
REPRODUCTION_CATEGORIES = (CATEGORY_EQUAL, CATEGORY_PRODUCTION_BETTER, CATEGORY_PRODUCTION_WORSE, CATEGORY_PRODUCTION_OPEN,
                           CATEGORY_PROTOTYPE_OPEN, CATEGORY_CO_OPTIMAL)
NOTE_PROTOTYPE_NOT_VERIFIED = "prototype_plan_not_verified"

_VALUE_LABELS = ("optimal", "optimal_stage1_by_bound", "feasible_with_gap")
_INFEASIBLE_LABELS = ("infeasible_certified", "infeasible_solver_proven")
_OPEN_LABELS = ("bound_only", "not_run_enumeration_cap", "input_rejected", "backend_unavailable")


@dataclass(frozen=True)
class PrototypeClaim:
    """What the prototype says about a cell: a ``value`` (objective tuple, optionally with the verdict of the independent
    checker on its plan: ``True`` passes, ``False`` fails, ``None`` not run), ``infeasible`` or ``open`` (no result)."""

    kind: str
    objective: Optional[tuple] = None
    plan_checked: Optional[bool] = None

    @classmethod
    def value(cls, objective: Sequence[int], plan_checked: Optional[bool] = None) -> "PrototypeClaim":
        return cls("value", _check(objective, "prototype objective"), plan_checked)

    @classmethod
    def infeasible(cls) -> "PrototypeClaim":
        return cls("infeasible")

    @classmethod
    def open(cls) -> "PrototypeClaim":
        return cls("open")


@dataclass(frozen=True)
class ReproductionResult:
    category: str
    prototype_claim_verified: Optional[bool] = None  # only for a prototype value: did its plan pass the checker
    note: str = ""


def _proven_prefix(label: str, length: int, override: Optional[int]) -> int:
    if override is not None:
        return min(_int(override, "production_proven_prefix"), length)
    if label == "optimal":
        return length
    if label == "optimal_stage1_by_bound":
        return min(1, length)
    return 0


def reproduction_category(prototype: PrototypeClaim, *, production_label: str,
                          production_objective: Optional[Sequence[int]] = None, same_routes: Optional[bool] = None,
                          components: Optional[int] = None,
                          production_proven_prefix: Optional[int] = None) -> ReproductionResult:
    """The category of design 6.3 for one cell.

    ``production_objective`` is required for the labels that carry a value (``optimal``, ``optimal_stage1_by_bound``,
    ``feasible_with_gap``). ``components`` compares only the first values of both tuples (a prototype that reports no car
    minutes). ``same_routes=False`` turns an equal objective into ``co_optimal_alternative`` (route identity is otherwise
    never looked at). ``production_proven_prefix`` overrides how many leading objective values production proved (default:
    all for ``optimal``, the first for ``optimal_stage1_by_bound``, none otherwise).

    Raises ``BlockingDefect`` for the disagreement rule, ``NotComparable`` when both sides are open, ``ValueError`` for a
    ``rejected`` production cell (it is a defect, not a result) or an unknown label.
    """
    if production_label == "rejected":
        raise ValueError("a rejected production cell is not a result to compare")
    if production_label not in _VALUE_LABELS + _INFEASIBLE_LABELS + _OPEN_LABELS:
        raise ValueError(f"unknown production label {production_label!r}")
    is_value = prototype.kind == "value"
    verified = (prototype.plan_checked is True) if is_value else None
    note = NOTE_PROTOTYPE_NOT_VERIFIED if is_value and not verified else ""

    if production_label in _OPEN_LABELS:
        if prototype.kind == "open":
            raise NotComparable(f"both sides are open (production {production_label})")
        return ReproductionResult(CATEGORY_PRODUCTION_OPEN, verified, note)

    if production_label in _INFEASIBLE_LABELS:
        if prototype.kind == "open":
            return ReproductionResult(CATEGORY_PROTOTYPE_OPEN)
        if prototype.kind == "infeasible":
            return ReproductionResult(CATEGORY_EQUAL)
        if verified:
            raise BlockingDefect(BLOCKING_PROTOTYPE_PLAN_VS_INFEASIBLE,
                                 f"a prototype plan {prototype.objective} passes the checker but production proved "
                                 f"{production_label}")
        return ReproductionResult(CATEGORY_PRODUCTION_BETTER, verified, note)

    # production has a value
    if production_objective is None:
        raise ValueError(f"production label {production_label} needs a production objective")
    q = _check(production_objective, "production objective")
    if prototype.kind == "open":
        return ReproductionResult(CATEGORY_PROTOTYPE_OPEN)
    if prototype.kind == "infeasible":
        return ReproductionResult(CATEGORY_PRODUCTION_BETTER)
    p = prototype.objective
    if components is not None:
        n = _int(components, "components")
        if n < 1 or len(p) < n or len(q) < n:
            raise ValueError("components exceeds an objective tuple length")
        p, q = p[:n], q[:n]
    elif len(p) != len(q):
        raise ValueError(f"objective tuples differ in length: {len(p)} and {len(q)}")
    m = _proven_prefix(production_label, len(q), production_proven_prefix)
    if verified and m and p[:m] < q[:m]:
        raise BlockingDefect(BLOCKING_PROTOTYPE_BEATS_OPTIMUM,
                             f"a prototype plan {p} passes the checker and beats the proven production value {q} "
                             f"({production_label})")
    if p == q:
        return ReproductionResult(CATEGORY_CO_OPTIMAL if same_routes is False else CATEGORY_EQUAL, verified, note)
    return ReproductionResult(CATEGORY_PRODUCTION_BETTER if q < p else CATEGORY_PRODUCTION_WORSE, verified, note)
