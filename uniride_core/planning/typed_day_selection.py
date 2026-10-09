"""Day-level exact selection of wave options under a large-vehicle limit (WP4).

Pure module, in integer time units (the endpoint may scale them, see time_scale), see ``docs/designs/HETEROGENEOUS_FLEET_DESIGN.md`` section 3.3.
Not imported by the academic stack (parity gate P2).

Model.  Every wave offers a menu of options (large-route quota q = 0..3 plus
the all-large baseline).  An option is a list of routes with a fixed interval
``[start, end)`` in minutes, a duration in vehicle-minutes and per-type label
feasibility.  CP-SAT picks exactly one option per wave and labels each route of
the picked options ``large`` or ``car``.  A vehicle of type ``t`` that serves a
route is busy on ``[start, end + cooldown_t)``.  Routes of one type form an
interval graph, so the vehicles needed equal the peak number of simultaneously
busy extended intervals, and it is enough to bound the load at every route
start time.  Constraints: large peak <= ``max_large`` (L), car peak <= C
(optionally C <= ``max_cars``).

Objective, lexicographic (owner decisions Q5/Q7/Q8):
  1. minimise cars C (peak of concurrently busy cars, cooldown included);
  2. minimise car-minutes;
  3. minimise total vehicle-minutes of the selected options;
  4. minimise the sum of selected option indices (deterministic tie-break).

Optimality claim.  ``status == "optimal"`` proves that C is the minimum
**over the given menus only**; it is not a global minimum number of cars, the
menus come from a heuristic (GA) and contain at most one route set per quota.

Determinism.  ``num_workers = 1`` and a fixed ``random_seed``; for a given
input and a time limit that is not hit, the output is identical across runs.
When the time limit is hit the result is ``feasible`` (a witness) and may
depend on machine speed.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

SOLVER_SEED = 20261008
DEFAULT_TIME_LIMIT_S = 30.0
_MINUTE_SCALE = 1000  # minutes are scaled to integers for CP-SAT

STATUS_OPTIMAL = "optimal"
STATUS_FEASIBLE = "feasible"
STATUS_INFEASIBLE_FOR_L = "infeasible_for_L"
STATUS_INFEASIBLE_DATA = "infeasible_data"
STATUS_INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class Route:
    start: int
    end: int
    minutes: float
    large_ok: bool = True
    car_ok: bool = True


@dataclass(frozen=True)
class Option:
    option_id: str
    routes: Tuple[Route, ...]
    baseline: bool = False


@dataclass(frozen=True)
class Wave:
    wave_id: str
    options: Tuple[Option, ...]


@dataclass
class DaySelectionResult:
    status: str
    cars: Optional[int] = None
    large_peak: Optional[int] = None
    car_minutes: Optional[float] = None
    total_minutes: Optional[float] = None
    # wave_id -> {"option_id", "option_index", "labels": ["large"|"car", ...]}
    selection: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)


def peak_concurrency(intervals: Sequence[Tuple[float, float]]) -> int:
    """Max number of half-open intervals ``[a, b)`` covering one point."""
    best = 0
    for a, _ in intervals:
        best = max(best, sum(1 for s, e in intervals if s <= a < e))
    return best


def _forced_large_peak(option: Option, cooldown_large: int) -> int:
    ivs = [(r.start, r.end + cooldown_large) for r in option.routes if not r.car_ok]
    return peak_concurrency(ivs)


def validate_data(waves: Sequence[Wave]) -> List[Dict[str, Any]]:
    """Return data problems (empty list = well-formed)."""
    problems: List[Dict[str, Any]] = []
    seen = set()
    for w in waves:
        if w.wave_id in seen:
            problems.append({"wave": w.wave_id, "reason": "DUPLICATE_WAVE_ID"})
        seen.add(w.wave_id)
        if not w.options:
            problems.append({"wave": w.wave_id, "reason": "WAVE_HAS_NO_OPTIONS"})
        for o in w.options:
            for i, r in enumerate(o.routes):
                if not (r.large_ok or r.car_ok):
                    problems.append({"wave": w.wave_id, "option": o.option_id,
                                     "route": i, "reason": "ROUTE_HAS_NO_FEASIBLE_TYPE"})
                if not (r.end > r.start) or not math.isfinite(r.minutes) or r.minutes < 0:
                    problems.append({"wave": w.wave_id, "option": o.option_id,
                                     "route": i, "reason": "BAD_ROUTE_INTERVAL"})
    return problems


def solve_day_selection(
    waves: Sequence[Wave],
    max_large: int,
    *,
    cooldown_large: int = 10,
    cooldown_car: int = 10,
    max_cars: Optional[int] = None,
    time_limit_s: float = DEFAULT_TIME_LIMIT_S,
) -> DaySelectionResult:
    """Select one option per wave; see the module docstring for the model."""
    if max_large < 0 or cooldown_large < 0 or cooldown_car < 0:
        raise ValueError("max_large and cooldowns must be >= 0")
    if max_cars is not None and max_cars < 0:
        raise ValueError("max_cars must be >= 0")
    if not (time_limit_s > 0):
        raise ValueError("time_limit_s must be > 0")

    problems = validate_data(waves)
    if problems:
        return DaySelectionResult(
            STATUS_INFEASIBLE_DATA,
            diagnostics={"reason": "MALFORMED_MENU", "problems": problems},
        )
    if not waves:
        return DaySelectionResult(
            STATUS_OPTIMAL, cars=0, large_peak=0, car_minutes=0.0, total_minutes=0.0,
            diagnostics={"note": "no waves"},
        )

    # Per-wave structural lower bound on L (routes that no car can serve).
    wave_min_forced: Dict[str, int] = {
        w.wave_id: min(_forced_large_peak(o, cooldown_large) for o in w.options)
        for w in waves
    }
    exceeding = sorted(wid for wid, v in wave_min_forced.items() if v > max_large)
    lower_bound_l = max(wave_min_forced.values())
    if exceeding:
        return DaySelectionResult(
            STATUS_INFEASIBLE_FOR_L,
            diagnostics={
                "reason": "SW_DEMAND_EXCEEDS_LARGE_CAPACITY",
                "waves_exceeding_L": exceeding,
                "lower_bound_L": lower_bound_l,
                "min_forced_large_per_wave": wave_min_forced,
            },
        )

    from ortools.sat.python import cp_model  # lazy: optional dependency

    t0 = time.monotonic()
    model = cp_model.CpModel()
    y: Dict[Tuple[int, int], Any] = {}
    # (wave idx, option idx, route idx, route, x_large, c_car)
    recs: List[Tuple[int, int, int, Route, Any, Any]] = []
    for wi, w in enumerate(waves):
        for oi in range(len(w.options)):
            y[wi, oi] = model.NewBoolVar(f"y_{wi}_{oi}")
        model.AddExactlyOne([y[wi, oi] for oi in range(len(w.options))])
        for oi, o in enumerate(w.options):
            for ri, r in enumerate(o.routes):
                x = model.NewBoolVar(f"x_{wi}_{oi}_{ri}") if r.large_ok else 0
                c = model.NewBoolVar(f"c_{wi}_{oi}_{ri}") if r.car_ok else 0
                model.Add(x + c == y[wi, oi])
                recs.append((wi, oi, ri, r, x, c))

    cap_c = len(recs) if max_cars is None else min(len(recs), max_cars)
    big_c = model.NewIntVar(0, cap_c, "C")
    for t in sorted({rec[3].start for rec in recs}):
        act_l = [rec[4] for rec in recs
                 if rec[3].large_ok and rec[3].start <= t < rec[3].end + cooldown_large]
        act_c = [rec[5] for rec in recs
                 if rec[3].car_ok and rec[3].start <= t < rec[3].end + cooldown_car]
        if act_l:
            model.Add(sum(act_l) <= max_large)
        if act_c:
            model.Add(sum(act_c) <= big_c)

    def scaled(r: Route) -> int:
        return int(round(r.minutes * _MINUTE_SCALE))

    car_min = sum(scaled(rec[3]) * rec[5] for rec in recs if rec[3].car_ok)
    tot_min = sum(scaled(rec[3]) * y[rec[0], rec[1]] for rec in recs)
    idx_sum = sum(oi * var for (_, oi), var in y.items())
    stages = (("cars", big_c), ("car_minutes", car_min),
              ("total_minutes", tot_min), ("option_index", idx_sum))

    all_optimal = True
    best_values: Dict[str, int] = {}
    snapshot: Dict[Tuple[int, int], int] = {}
    rec_vals: List[Tuple[int, int]] = []
    have_solution = False
    for name, expr in stages:
        remaining = time_limit_s - (time.monotonic() - t0)
        if have_solution and remaining <= 0:
            all_optimal = False
            break
        model.Minimize(expr)
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        solver.parameters.random_seed = SOLVER_SEED
        solver.parameters.max_time_in_seconds = max(remaining, 0.001)
        st = solver.Solve(model)
        if st == cp_model.INFEASIBLE and not have_solution:
            return DaySelectionResult(
                STATUS_INFEASIBLE_FOR_L,
                diagnostics={
                    "reason": ("CROSS_WAVE_CONFLICT_OR_CAR_CAP" if max_cars is not None
                               else "CROSS_WAVE_CONFLICT"),
                    "waves_exceeding_L": [],
                    "lower_bound_L": lower_bound_l,
                    "min_forced_large_per_wave": wave_min_forced,
                },
                stats={"wall_time_s": time.monotonic() - t0},
            )
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if have_solution:
                all_optimal = False
                break
            return DaySelectionResult(
                STATUS_INDETERMINATE,
                diagnostics={"reason": "TIME_LIMIT_NO_SOLUTION"},
                stats={"wall_time_s": time.monotonic() - t0},
            )
        have_solution = True
        snapshot = {k: solver.Value(v) for k, v in y.items()}
        rec_vals = [(solver.Value(rec[4]) if rec[3].large_ok else 0,
                     solver.Value(rec[5]) if rec[3].car_ok else 0) for rec in recs]
        value = int(round(solver.ObjectiveValue()))
        best_values[name] = value
        if st != cp_model.OPTIMAL:
            all_optimal = False
            break
        model.Add(expr == value)

    selection: Dict[str, Dict[str, Any]] = {}
    labels_by_key: Dict[Tuple[int, int], List[Tuple[int, str]]] = {}
    car_ivs: List[Tuple[float, float]] = []
    large_ivs: List[Tuple[float, float]] = []
    car_minutes = 0.0
    total_minutes = 0.0
    for rec, (xv, cv) in zip(recs, rec_vals):
        wi, oi, ri, r, _, _ = rec
        if not snapshot[wi, oi]:
            continue
        labels_by_key.setdefault((wi, oi), []).append((ri, "large" if xv else "car"))
        total_minutes += r.minutes
        if cv:
            car_minutes += r.minutes
            car_ivs.append((r.start, r.end + cooldown_car))
        else:
            large_ivs.append((r.start, r.end + cooldown_large))
    for (wi, oi), v in snapshot.items():
        if v:
            w = waves[wi]
            selection[w.wave_id] = {
                "option_id": w.options[oi].option_id,
                "option_index": oi,
                "labels": [lab for _, lab in sorted(labels_by_key.get((wi, oi), []))],
            }
    return DaySelectionResult(
        STATUS_OPTIMAL if all_optimal else STATUS_FEASIBLE,
        cars=peak_concurrency(car_ivs),
        large_peak=peak_concurrency(large_ivs),
        car_minutes=car_minutes,
        total_minutes=total_minutes,
        selection=selection,
        diagnostics={
            "lower_bound_L": lower_bound_l,
            "claim": ("minimum cars over the given menus only" if all_optimal
                      else "witness: time limit reached, not proven"),
        },
        stats={"wall_time_s": time.monotonic() - t0, "num_workers": 1,
               "random_seed": SOLVER_SEED, "stage_values": best_values,
               "routes": len(recs)},
    )
