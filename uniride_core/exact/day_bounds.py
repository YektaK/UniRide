"""Lower bounds and infeasibility certificates of the joint day model (WP-E11 J2, design JOINT_DAY_MODEL_DESIGN.md 3).

Every bound below is a lower bound on a quantity of the day problem of design 1.2 (a day plan uses only the
service-day-filtered columns of ``DayInstance``). A bound that is not valid would become a false certificate, so each
function carries a one-line reason why it is valid. All of them rest on three facts:

* (F-window) every route of wave ``w`` is busy at least on the window ``J_w = [a_w, a_w + cd)``: a pickup route is busy
  on ``[a_w - tour, a_w + cd)`` and a dropoff route on ``[a_w, a_w + tour + cd)`` (design 2.3), and both contain ``J_w``.
  ``cd`` is the cooldown; when routes of several types are counted, the smallest cooldown among them is used.
* (F-sum) vehicles busy at one minute ``p`` are distinct vehicles, so the peak of a type is at least the number of its
  routes whose busy interval contains ``p``; the lower bound for a wave's route count may be summed over the waves whose
  window contains ``p``.
* (F-wave) a wave value computed on a superset of the day's columns (e.g. the unfiltered enumeration of the wave SP, the
  WP-E3 ``K*``) is still a lower bound for the filtered day, because the filter only removes columns.

Wave values (``WaveValue``) come from outside: the wave SP (``ampl_backend.solve_wave``, see ``wave_value_from_sp``) or
the pure DP ``dp_wave_values`` for tiny waves (tests). Values taken from a solver must have passed the two-solver
cross-check of the run (DECISION_LOG E14); this module cannot check that.

Pure Python. No solver import at module level (``wave_value_from_sp`` only reads fields of a result object).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple, Union

from .day_instance import DayInstance, DayWave

PROOF_ARITHMETIC = "arithmetic_floor"  # needs no solver; checkable by hand from Sw counts and anchors
PROOF_SOLVER = "solver_proven"  # solver-proven wave value or proven wave lower bound

INFEASIBLE_CERTIFIED = "infeasible_certified"
CERT_CAPACITY_FLOOR = "certificate_capacity_floor"  # tier 1
CERT_WAVE_MIN_LARGE = "certificate_wave_min_large"  # tier 2

_NOT_SERVED = ("backend_unavailable", "not_run", "timing_dependent_abort", "infeasible_proven", "rejected")


class WaveInfeasible(ValueError):
    """A wave has no feasible route set at all, so the whole day has no plan."""


@dataclass(frozen=True)
class WaveValue:
    value: int
    proof: str = PROOF_SOLVER


@dataclass(frozen=True)
class Contribution:
    wave_id: str
    value: int
    proof: str


@dataclass(frozen=True)
class BoundResult:
    """``value`` at minute ``point``; ``contributions`` are the waves (value > 0) whose window contains the point."""

    value: int
    point: Optional[int]
    contributions: Tuple[Contribution, ...]

    @property
    def waves(self) -> Tuple[str, ...]:
        return tuple(c.wave_id for c in self.contributions)


@dataclass(frozen=True)
class InfeasibilityCertificate:
    """Proof that no day plan with at most ``large_limit`` large vehicles exists (LB_L > L, design 3.2)."""

    status: str
    tier: int  # 1 = capacity floor only, 2 = uses solver-proven wave minima
    kind: str
    large_limit: int
    lower_bound: int  # LB_L, > large_limit
    point: int  # minute at which the concurrent large routes are counted
    contributions: Tuple[Contribution, ...]  # the contributing waves with their value and proof

    @property
    def waves(self) -> Tuple[str, ...]:
        return tuple(c.wave_id for c in self.contributions)


@dataclass(frozen=True)
class WaveValues:
    k_any: Dict[str, WaveValue]  # minimum number of routes of the wave over all types
    l: Dict[str, WaveValue]  # minimum number of large routes of the wave (typed only; else empty)


@dataclass(frozen=True)
class DayBounds:
    lb0: Optional[BoundResult] = None  # homogeneous, prototype definition
    lb0w: Optional[BoundResult] = None  # homogeneous, widened
    lb_l: Optional[BoundResult] = None  # typed: concurrent large routes
    lb_s: Optional[BoundResult] = None  # typed: minimised-type vehicles (needs k_any)
    certificate: Optional[InfeasibilityCertificate] = None


# ------------------------------------------------------------------ inputs
def _as_value(wave_id: str, v: Union[int, WaveValue]) -> WaveValue:
    wv = v if isinstance(v, WaveValue) else WaveValue(v)
    if isinstance(wv.value, bool) or not isinstance(wv.value, int) or wv.value < 0:
        raise ValueError(f"wave value of {wave_id} must be a non-negative integer, got {wv.value!r}")
    return wv


def _values(instance: DayInstance, values: Mapping[str, Union[int, WaveValue]], what: str) -> Dict[str, WaveValue]:
    out = {}
    for w in instance.waves:
        if w.wave_id not in values:
            raise ValueError(f"missing {what} for wave {w.wave_id}")
        out[w.wave_id] = _as_value(w.wave_id, values[w.wave_id])
    return out


def _require_types(instance: DayInstance, n: int, what: str) -> None:
    if len(instance.types) != n:
        raise ValueError(f"{what} needs {n} vehicle type(s), the instance has {len(instance.types)}")


# ------------------------------------------------------------------ windows and the sweep
def _anchor_window(w: DayWave, cooldown: int) -> Tuple[int, int]:
    a = w.wave.anchor_minutes
    return a, a + cooldown  # J_w (F-window)


def _widened_window(w: DayWave, cooldown: int) -> Tuple[int, int]:
    a = w.wave.anchor_minutes
    if not w.columns:  # no feasible route at all: fall back to J_w
        return a, a + cooldown
    tau_min = min(c.tour for c in w.columns)  # every route of the wave has tour >= tau_min
    if w.wave.direction == "pickup":
        return a - tau_min, a + cooldown  # pickup busy interval [a - tour, a + cd) contains it
    return a, a + tau_min + cooldown  # dropoff busy interval [a, a + tour + cd) contains it


def _sweep(entries: List[tuple]) -> BoundResult:
    """Max over window starts of the sum of the values of the windows containing the point (F-sum).

    The sum over a point set is attained at some window start, so the maximum over starts is the maximum over all
    minutes; each evaluated point gives a valid bound on its own.
    """
    entries = [e for e in entries if e[3] > 0]
    best_total, best_point = 0, None
    for p in sorted({e[1] for e in entries}):
        total = sum(e[3] for e in entries if e[1] <= p < e[2])
        if total > best_total:
            best_total, best_point = total, p
    if best_point is None:
        return BoundResult(0, None, ())
    contributions = tuple(Contribution(e[0], e[3], e[4]) for e in entries if e[1] <= best_point < e[2])
    return BoundResult(best_total, best_point, contributions)


def _entries(instance: DayInstance, values: Dict[str, WaveValue], cooldown: int, window) -> List[tuple]:
    out = []
    for w in instance.waves:
        s, e = window(w, cooldown)
        v = values[w.wave_id]
        out.append((w.wave_id, s, e, v.value, v.proof))
    return out


# ------------------------------------------------------------------ homogeneous bounds
def lb0(instance: DayInstance, k: Mapping[str, Union[int, WaveValue]]) -> BoundResult:
    """LB0 <= K*_day: ``k_w`` routes of wave w are all busy on J_w, and busy routes at one minute need distinct vehicles."""
    _require_types(instance, 1, "LB0")
    vals = _values(instance, k, "k_w")
    return _sweep(_entries(instance, vals, instance.types[0].cooldown_minutes, _anchor_window))


def lb0w(instance: DayInstance, k: Mapping[str, Union[int, WaveValue]]) -> BoundResult:
    """LB0w <= K*_day and LB0w >= LB0: the same sum over windows widened by the smallest tour of the wave, which every
    route of the wave contains in its busy interval (and which contain J_w)."""
    _require_types(instance, 1, "LB0w")
    vals = _values(instance, k, "k_w")
    return _sweep(_entries(instance, vals, instance.types[0].cooldown_minutes, _widened_window))


# ------------------------------------------------------------------ typed bounds
def capacity_floor_large(instance: DayInstance, large_type_index: int = 0) -> Dict[str, WaveValue]:
    """Tier-1 wave floors: the number of large routes of a wave is >= ceil(Sw / large Sw capacity) when the other type
    carries no Sw (sedan, H01); 0 otherwise (Doblo carries one Sw, H03; a bound of 0 is always valid)."""
    _require_types(instance, 2, "the large-route floor")
    large = instance.types[large_type_index]
    other = instance.types[1 - large_type_index]
    per_route = large.sw_capacity if large.total_capacity is None else min(large.sw_capacity, large.total_capacity)
    out = {}
    for w in instance.waves:
        sw = sum(it.multiplicity for it in w.items if it.cls == "Sw")
        # every Sw rides a large route (other type has no Sw seat) and a large route seats at most ``per_route`` Sw
        floor = math.ceil(sw / per_route) if other.sw_capacity == 0 and per_route > 0 and sw > 0 else 0
        out[w.wave_id] = WaveValue(floor, PROOF_ARITHMETIC)
    return out


def _merged_large_values(instance: DayInstance, l: Optional[Mapping], large_type_index: int) -> Dict[str, WaveValue]:
    floors = capacity_floor_large(instance, large_type_index)
    if not l:
        return floors
    solver = _values(instance, l, "l_w")
    # both are lower bounds of the same quantity, so their maximum is one too
    return {wid: (solver[wid] if solver[wid].value > floors[wid].value else floors[wid]) for wid in floors}


def lb_large(instance: DayInstance, l: Optional[Mapping[str, Union[int, WaveValue]]] = None,
             large_type_index: int = 0) -> BoundResult:
    """LB_L: at minute p the waves whose J_w contains p need ``sum l_w`` large vehicles at once (F-window, F-sum, and
    ``l_w`` is the fewest large routes of wave w); the capacity floor is used where it is larger than ``l_w`` or ``l`` is absent."""
    values = _merged_large_values(instance, l, large_type_index)
    return _sweep(_entries(instance, values, instance.types[large_type_index].cooldown_minutes, _anchor_window))


def lb_cars(instance: DayInstance, k_any: Mapping[str, Union[int, WaveValue]], large_limit: int,
            large_type_index: int = 0) -> BoundResult:
    """LB_S = max(0, max_p sum k_any_w - L): at p at least ``sum k_any_w`` vehicles are busy (all types, F-window with the
    smaller cooldown, F-sum) and at most L of them are large, so the rest are of the other type. ``contributions``
    list the k_any_w summed at the best point; ``value`` is that sum minus L."""
    _require_types(instance, 2, "LB_S")
    _check_limit(large_limit)
    vals = _values(instance, k_any, "k_any_w")
    cooldown = min(t.cooldown_minutes for t in instance.types)
    swept = _sweep(_entries(instance, vals, cooldown, _anchor_window))
    return BoundResult(max(0, swept.value - large_limit), swept.point, swept.contributions)


def _check_limit(large_limit) -> None:
    if isinstance(large_limit, bool) or not isinstance(large_limit, int) or large_limit < 0:
        raise ValueError("large_limit must be a non-negative integer")


def infeasibility_certificate(instance: DayInstance, large_limit: int,
                              l: Optional[Mapping[str, Union[int, WaveValue]]] = None,
                              large_type_index: int = 0) -> Optional[InfeasibilityCertificate]:
    """A certificate that no day plan with at most ``large_limit`` large vehicles exists, or ``None``.

    Valid because LB_L (see ``lb_large``) is a lower bound of the large peak of every day plan, so LB_L > L leaves no plan
    (design 3.2). Tier 1 uses only the arithmetic capacity floor; tier 2 also uses the solver-proven ``l_w`` passed in
    ``l``. ``None`` means "no certificate", never "feasible".
    """
    _require_types(instance, 2, "the certificate")
    _check_limit(large_limit)
    floors = capacity_floor_large(instance, large_type_index)
    cooldown = instance.types[large_type_index].cooldown_minutes
    tier1 = _sweep(_entries(instance, floors, cooldown, _anchor_window))
    if tier1.value > large_limit:
        return InfeasibilityCertificate(INFEASIBLE_CERTIFIED, 1, CERT_CAPACITY_FLOOR, large_limit, tier1.value,
                                        tier1.point, tier1.contributions)
    if l:
        merged = _merged_large_values(instance, l, large_type_index)
        tier2 = _sweep(_entries(instance, merged, cooldown, _anchor_window))
        if tier2.value > large_limit:
            return InfeasibilityCertificate(INFEASIBLE_CERTIFIED, 2, CERT_WAVE_MIN_LARGE, large_limit, tier2.value,
                                            tier2.point, tier2.contributions)
    return None


def compute_day_bounds(instance: DayInstance, *, k: Optional[Mapping] = None, l: Optional[Mapping] = None,
                       k_any: Optional[Mapping] = None, large_limit: Optional[int] = None,
                       large_type_index: int = 0) -> DayBounds:
    """All bounds that apply: homogeneous (one type) LB0/LB0w from ``k``; typed (two types) LB_L, LB_S (needs ``k_any``)
    and the certificate for ``large_limit`` (required)."""
    if len(instance.types) == 1:
        if k is None:
            raise ValueError("a homogeneous day needs the wave values k")
        return DayBounds(lb0=lb0(instance, k), lb0w=lb0w(instance, k))
    if large_limit is None:
        raise ValueError("a typed day needs large_limit")
    return DayBounds(lb_l=lb_large(instance, l, large_type_index),
                     lb_s=None if k_any is None else lb_cars(instance, k_any, large_limit, large_type_index),
                     certificate=infeasibility_certificate(instance, large_limit, l, large_type_index))


# ------------------------------------------------------------------ wave values
def wave_value_from_sp(result) -> WaveValue:
    """Proven lower bound of the stage-1 count of an ``SPSolveResult`` (``k_w``, ``l_w`` or ``k_any_w`` by how the wave
    SP was called): the stage-1 optimum when proven, else the proven bound ``k_lb``. A bound is a valid lower bound but
    is not the wave optimum. Refuses results without a proof (unavailable, not run, infeasible, rejected)."""
    if result.status in _NOT_SERVED:
        raise ValueError(f"wave {result.wave_id}: status {result.status} gives no wave value")
    s1 = result.stage1
    if s1 is not None and s1.status == "optimal" and s1.objective is not None:
        return WaveValue(int(s1.objective), PROOF_SOLVER)
    if result.k_lb is None:
        raise ValueError(f"wave {result.wave_id}: no proven bound")
    return WaveValue(int(result.k_lb), PROOF_SOLVER)


def _wave_minimum(day_wave: DayWave, counted: Optional[frozenset], state_cap: int) -> int:
    """Fewest counted columns (columns of other types count 0) that cover the wave exactly, by memoised DP."""
    demand = tuple(it.multiplicity for it in day_wave.items)
    weights: Dict[tuple, int] = {}
    for c in day_wave.columns:
        if any(c.multiplicity):
            w = 1 if counted is None or c.type_id in counted else 0
            weights[c.multiplicity] = min(w, weights.get(c.multiplicity, 1))
    cols = sorted(weights.items())
    memo: Dict[tuple, Optional[int]] = {}

    def f(rem: tuple) -> Optional[int]:
        if not any(rem):
            return 0
        if rem in memo:
            return memo[rem]
        if len(memo) > state_cap:
            raise ValueError("wave DP exceeds its state cap; use the wave SP")
        best = None
        for mult, w in cols:
            if all(m <= r for m, r in zip(mult, rem)):
                sub = f(tuple(r - m for m, r in zip(mult, rem)))
                if sub is not None and (best is None or sub + w < best):
                    best = sub + w
        memo[rem] = best
        return best

    value = f(demand)
    if value is None:
        raise WaveInfeasible(f"wave {day_wave.wave_id} has no feasible route set")
    return value


def dp_wave_values(instance: DayInstance, *, large_type_index: int = 0, state_cap: int = 200_000) -> WaveValues:
    """Exact ``k_any_w`` (and ``l_w`` for a typed day) of every wave by a pure DP over the day columns (tiny waves only;
    the run uses the wave SP). The values are exact on the day's filtered columns, hence valid lower bounds (F-wave)."""
    k_any = {w.wave_id: WaveValue(_wave_minimum(w, None, state_cap), PROOF_SOLVER) for w in instance.waves}
    l: Dict[str, WaveValue] = {}
    if len(instance.types) == 2:
        large_id = frozenset([instance.types[large_type_index].type_id])
        l = {w.wave_id: WaveValue(_wave_minimum(w, large_id, state_cap), PROOF_SOLVER) for w in instance.waves}
    return WaveValues(k_any, l)
