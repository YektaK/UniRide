"""Union-menu day level (WP-E4b): menu construction, router-cap flags, the two-run proof rule and the row label.

Design: docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 1.5 ("Day level over the union menu") and section 8
(row "Union day level"). Pure functions, no I/O, no imports outside ``uniride_core``; the CP-SAT call is injected
(``solve``) so that the proof rule is testable without a solver.

Rules reproduced exactly:

* the union menu of a wave is the GA options in their WP-E10 order (the producer's within-GA dedupe is already
  applied in the archive), followed by the certified exact options in the order ``xbase, xq0..xqQ``;
* an exact option is NEVER deduped against a GA option (the producer's ``signature()`` ignores stop order and
  would drop an exact option with the same partition but shorter routes in favour of the worse GA option);
* exact options are deduped among themselves only when their routes are identical: same partition, same stop
  order and same per-route minutes (the first one in the order is kept);
* ``union cars <= GA-menu cars`` is claimed, and checked as a blocking test, ONLY when both runs are
  ``optimal``; a union run that stopped on its time limit is re-run ONCE with the longer limit; if it is still
  not optimal the row is ``union_not_proven`` with ``timing_dependent`` set and no claim is made;
* the report never shows ``min(GA, union)``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from uniride_core.planning.fleet_selection_request import RouteFacts, round6

CLAIM = ("minimum cars over the union of the GA and per-wave exact menus; never above the GA-menu result "
         "(when both runs are optimal); not a global day optimum (EQ3)")

LABEL_PROVEN = "proven_over_union_menu"
LABEL_NOT_PROVEN = "union_not_proven"
LABEL_NOT_CONFIRMED = "not_independently_confirmed"
LABEL_FAILED = "verification_failed"
LABELS = (LABEL_PROVEN, LABEL_NOT_PROVEN, LABEL_NOT_CONFIRMED, LABEL_FAILED)

STATUS_OPTIMAL = "optimal"
# A time-limited CP-SAT stop: a witness (``feasible``) or no solution (``indeterminate``). Only these depend on the clock.
TIME_LIMITED_STATUSES = ("feasible", "indeterminate")
# Statuses of a run that carries a selection to confirm.
SELECTION_STATUSES = ("optimal", "feasible")

CONFIRMED, CONFIRM_FAILED, CONFIRM_MISSING, CONFIRM_NOT_NEEDED = "confirmed", "failed", "missing", "not_needed"


@dataclass(frozen=True)
class MenuOption:
    """One menu option of a wave: its routes' request facts and the data the TS confirmation needs."""

    option_id: str
    baseline: bool
    routes: Tuple[RouteFacts, ...]
    origin: str  # "ga" or "exact"
    # per route, in the order of ``routes``: stop order (occurrence ids) for the exact identity
    stops: Tuple[Tuple[str, ...], ...] = ()
    # per route: route_details / student_ids / sw_count / so_count / total_duration_minutes (TS confirmation input)
    route_data: Tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class WaveMenu:
    wave_id: str
    direction: str
    anchor_minutes: float
    options: Tuple[MenuOption, ...]


def exact_identity(option: MenuOption) -> Tuple:
    """Route identity of an exact option: the multiset of (stop order, per-route minutes). Route order is irrelevant."""
    if len(option.stops) != len(option.routes):
        raise ValueError(f"{option.option_id}: stop orders are required to compare exact options")
    return tuple(sorted((tuple(stops), round6(facts.minutes)) for stops, facts in zip(option.stops, option.routes)))


def dedupe_exact_options(options: Sequence[MenuOption]) -> Tuple[List[MenuOption], List[Tuple[str, str]]]:
    """Drop an exact option whose routes equal those of an EARLIER exact option; ``dropped`` = ``(dropped, kept)`` ids."""
    kept: List[MenuOption] = []
    seen: Dict[Tuple, str] = {}
    dropped: List[Tuple[str, str]] = []
    for option in options:
        key = exact_identity(option)
        if key in seen:
            dropped.append((option.option_id, seen[key]))
            continue
        seen[key] = option.option_id
        kept.append(option)
    return kept, dropped


def build_union_menu(ga_waves: Sequence[WaveMenu], exact: Mapping[str, Sequence[MenuOption]]) -> Tuple[List[WaveMenu], List[Dict[str, str]]]:
    """Union menu: per wave the GA options (unchanged, in order), then the exact options (deduped among themselves).

    ``exact`` maps a wave id to its exact options in the order ``xbase, xq0..xqQ`` (feasible, certified ones only).
    An exact wave id that is not in the GA menu is an error. Returns the waves and the exact-dedupe log.
    """
    known = {w.wave_id for w in ga_waves}
    unknown = sorted(set(exact) - known)
    if unknown:
        raise ValueError(f"exact options for waves that are not in the GA menu: {unknown}")
    waves: List[WaveMenu] = []
    log: List[Dict[str, str]] = []
    for wave in ga_waves:
        kept, dropped = dedupe_exact_options(exact.get(wave.wave_id, ()))
        log.extend({"wave_id": wave.wave_id, "dropped": d, "kept": k} for d, k in dropped)
        ga_ids = {o.option_id for o in wave.options}
        clash = sorted(ga_ids & {o.option_id for o in kept})
        if clash:
            raise ValueError(f"{wave.wave_id}: option ids {clash} exist in both menus")
        waves.append(WaveMenu(wave.wave_id, wave.direction, wave.anchor_minutes, tuple(wave.options) + tuple(kept)))
    return waves, log


def request_waves(waves: Sequence[WaveMenu]) -> List[Tuple[str, List[Tuple[str, bool, Sequence[RouteFacts]]]]]:
    """The ``waves`` argument of ``fleet_selection_request.build_selection_request``."""
    return [(w.wave_id, [(o.option_id, o.baseline, list(o.routes)) for o in w.options]) for w in waves]


def router_cap_flags(request: Mapping[str, Any], *, max_options_per_wave: int, max_routes_per_option: int,
                     max_total_routes: int) -> Dict[str, Any]:
    """Which router caps a request would exceed (the direct ``solve_day_selection`` call bypasses them)."""
    option_counts = [len(w["options"]) for w in request["waves"]]
    route_counts = [len(o["routes"]) for w in request["waves"] for o in w["options"]]
    total = sum(route_counts)
    max_options = max(option_counts, default=0)
    max_routes = max(route_counts, default=0)
    return {
        "max_options_per_wave": max_options, "waves_over_options_cap": sum(c > max_options_per_wave for c in option_counts),
        "cap_options_per_wave": max_options > max_options_per_wave,
        "max_routes_per_option": max_routes, "options_over_routes_cap": sum(c > max_routes_per_option for c in route_counts),
        "cap_routes_per_option": max_routes > max_routes_per_option,
        "total_routes": total, "cap_total_routes": total > max_total_routes,
    }


# ---------------------------------------------------------------- the two runs and the proof rule
@dataclass(frozen=True)
class RunRecord:
    status: str
    cars: Optional[int]
    large_peak: Optional[int]
    car_minutes: Optional[float]
    total_minutes: Optional[float]
    selection: Mapping[str, Any]
    time_limit_s: float
    wall_seconds: float
    body: Mapping[str, Any] = field(default_factory=dict)  # the router-shaped response (``result_body``)


def run_selection(request: Mapping[str, Any], time_limit_s: float, solve: Callable[..., Any], to_body: Callable[[Any], Mapping[str, Any]],
                  clock: Callable[[], float]) -> RunRecord:
    t0 = clock()
    result = solve(request, time_limit_s=time_limit_s)
    wall = clock() - t0
    body = to_body(result)
    return RunRecord(body["status"], body.get("cars"), body.get("large_peak"), body.get("car_minutes"), body.get("total_minutes"),
                     body.get("selection") or {}, time_limit_s, round(wall, 3), body)


@dataclass(frozen=True)
class CellSolve:
    ga: RunRecord
    union: RunRecord  # the run the label rests on (the re-run when there was one)
    union_first: RunRecord  # the run at the producer's limit
    rerun: bool


def solve_cell(ga_request: Mapping[str, Any], union_request: Mapping[str, Any], *, producer_limit_s: float, rerun_limit_s: float,
               solve: Callable[..., Any], to_body: Callable[[Any], Mapping[str, Any]], clock: Callable[[], float]) -> CellSolve:
    """Two direct day-selection calls at the producer's limit; the union only is re-run ONCE at ``rerun_limit_s``
    when it stopped on its time limit. A proven infeasibility is final (no clock dependence), so it is not re-run."""
    ga = run_selection(ga_request, producer_limit_s, solve, to_body, clock)
    union_first = run_selection(union_request, producer_limit_s, solve, to_body, clock)
    if union_first.status in TIME_LIMITED_STATUSES:
        return CellSolve(ga, run_selection(union_request, rerun_limit_s, solve, to_body, clock), union_first, True)
    return CellSolve(ga, union_first, union_first, False)


def union_not_above_ga_error(ga: RunRecord, union: RunRecord) -> Optional[str]:
    """Blocking check, applied only when BOTH runs are ``optimal``: union cars must not exceed the GA-menu cars."""
    if ga.status == STATUS_OPTIMAL and union.status == STATUS_OPTIMAL:
        if ga.cars is None or union.cars is None:
            return "both runs optimal but a cars value is missing"
        if union.cars > ga.cars:
            return f"union cars {union.cars} exceed the GA-menu cars {ga.cars} although both runs are optimal"
    return None


# ---------------------------------------------------------------- confirmation and label
@dataclass(frozen=True)
class Confirmation:
    status: str  # confirmed | failed | missing | not_needed
    detail: str = ""
    ts_cars: Optional[int] = None
    ts_status: Optional[str] = None


def confirmation_from_cli(result: Optional[Mapping[str, Any]], run: RunRecord) -> Confirmation:
    """The confirmation of one run from its TS CLI result (None = no result: the check is missing).

    ``failed`` when the CLI reports problems, recheck failures, interval differences, a non-proven/witness
    assignment status, or (assignment proven) a car count that differs from the CP-SAT one.
    """
    if run.status not in SELECTION_STATUSES:
        return Confirmation(CONFIRM_NOT_NEEDED)
    if result is None:
        return Confirmation(CONFIRM_MISSING, "no CLI result")
    assignment = result.get("assignment") or {}
    ts_cars, ts_status = assignment.get("cars"), assignment.get("status")
    reasons: List[str] = []
    if not result.get("ok"):
        if result.get("intervalDifferences"):
            reasons.append(f"{len(result['intervalDifferences'])} interval difference(s)")
        if result.get("problems"):
            reasons.append(f"problems: {list(result['problems'])[:3]}")
        if (result.get("recheck") or {}).get("failures"):
            reasons.append(f"recheck: {list(result['recheck']['failures'])[:3]}")
        if ts_status not in ("proven", "witness"):
            reasons.append(f"assignment {ts_status}")
        if not reasons:
            reasons.append("CLI reported ok=false")
    if ts_status == "proven" and ts_cars is not None and run.cars is not None and ts_cars != run.cars:
        reasons.append(f"TS proven minimum {ts_cars} cars differs from the CP-SAT cars {run.cars}")
    if reasons:
        return Confirmation(CONFIRM_FAILED, "; ".join(reasons), ts_cars, ts_status)
    return Confirmation(CONFIRMED, "", ts_cars, ts_status)


@dataclass(frozen=True)
class Verdict:
    label: str
    timing_dependent: bool
    reason: str
    blocking_errors: Tuple[str, ...]
    claim: str


def classify(cell: CellSolve, ga_confirmation: Confirmation, union_confirmation: Confirmation) -> Verdict:
    """The row label. Precedence: a failed check, a missing check, then the proof state of the two runs."""
    ga, union = cell.ga, cell.union
    errors: List[str] = []
    bound_error = union_not_above_ga_error(ga, union)
    if bound_error:
        errors.append(bound_error)
    timing = any(r.status in TIME_LIMITED_STATUSES for r in (ga, union))
    confirmations = (ga_confirmation, union_confirmation)
    if any(c.status == CONFIRM_FAILED for c in confirmations):
        reason = "; ".join(f"{n}: {c.detail}" for n, c in (("ga", ga_confirmation), ("union", union_confirmation))
                           if c.status == CONFIRM_FAILED)
        return Verdict(LABEL_FAILED, timing, reason, tuple(errors), "")
    if any(c.status == CONFIRM_MISSING for c in confirmations):
        reason = "; ".join(f"{n}: {c.detail}" for n, c in (("ga", ga_confirmation), ("union", union_confirmation))
                           if c.status == CONFIRM_MISSING)
        return Verdict(LABEL_NOT_CONFIRMED, timing, reason, tuple(errors), "")
    if ga.status == STATUS_OPTIMAL and union.status == STATUS_OPTIMAL:
        return Verdict(LABEL_PROVEN, False, "", tuple(errors), CLAIM)
    if union.status in TIME_LIMITED_STATUSES:
        reason = f"union run {union.status} at {union.time_limit_s:g} s" + (" (re-run)" if cell.rerun else "")
    else:  # a proven status of at least one run that is not optimal (e.g. infeasible_for_L): final, not clock dependent
        reason = f"GA-menu run {ga.status}; union run {union.status}"
    return Verdict(LABEL_NOT_PROVEN, timing, reason, tuple(errors), "")
