"""Python port of the producer's day-selection request construction (WP-E4a part 1).

Mirrors ``src/services/fleet-scenario-run.ts`` (``scenarioL`` ~545-578, ``typeAccepts``, ``fits``, ``round6``)
and ``src/services/dudullu-preview.ts`` (``longestStudentRideMinutes``), so that a request can be rebuilt
from archived option routes and a day selection recomputed without the TypeScript producer
(docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 1.5, "Same inputs as the producer and the router").

Pure functions, no I/O, no imports outside ``uniride_core``. The router checks (option and route caps,
policy time limit) are NOT here: they belong to ``optimizer_api`` and are applied by the caller.

Rules reproduced exactly:

* interval endpoints and both cooldowns are integer centi-minutes (``centi``); a value off the
  centi-minute grid is refused (``SelectionIntervalPrecision``), never rounded;
* ``end = max(start + 1, centi(end))`` (a route is never empty or reversed);
* ``minutes = round6(end_minutes - start_minutes)`` in real minutes, NOT scaled; JavaScript ``Math.round``
  (half up) is used, not the banker's rounding of Python's ``round``;
* ``large_ok`` / ``car_ok`` come from ``type_accepts`` of the fixed and the minimised type;
* ``max_cars`` is sent only when set; ``time_limit_seconds`` defaults to 30.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

from uniride_core.planning.typed_day_selection import DaySelectionResult, Option, Route, Wave, solve_day_selection

TIME_SCALE = 100
CENTI_TOLERANCE = 1e-6
DEFAULT_SELECTION_TIME_LIMIT_S = 30
DEFAULT_COOLDOWN_MINUTES = 10  # router: cooldown null means 10 * time_scale


class SelectionIntervalPrecision(ValueError):
    """An interval endpoint or cooldown is off the centi-minute grid (producer: SELECTION_INTERVAL_PRECISION)."""


@dataclass(frozen=True)
class TypeLimits:
    """The fields of a fleet type that ``typeAccepts`` reads."""

    type_id: str
    sw_capacity: int
    so_capacity: int
    total_capacity: Optional[int] = None
    ride_limit: Optional[int] = None
    tour_limit: Optional[int] = None


@dataclass(frozen=True)
class RouteFacts:
    """One verified route: its interval in real minutes, its optimizer steps and its class counts."""

    start_minutes: float
    end_minutes: float
    step_durations: Tuple[float, ...]
    direction: str
    sw_count: int
    so_count: int

    @property
    def minutes(self) -> float:
        return self.end_minutes - self.start_minutes


def js_round(value: float) -> int:
    """JavaScript ``Math.round``: halves round toward +infinity."""
    return math.floor(value + 0.5)


def round6(value: float) -> float:
    return js_round(value * 1_000_000) / 1_000_000


def centi(value: float, time_scale: int = TIME_SCALE) -> int:
    scaled = value * time_scale
    rounded = js_round(scaled) if math.isfinite(scaled) else None
    if rounded is None or abs(scaled - rounded) > CENTI_TOLERANCE:
        raise SelectionIntervalPrecision(f"{value!r} is not on the 1/{time_scale}-minute grid")
    return max(0, rounded)


def fits(type_: TypeLimits, sw: int, so: int) -> bool:
    return sw <= type_.sw_capacity and so <= type_.so_capacity and (
        type_.total_capacity is None or sw + so <= type_.total_capacity)


def longest_student_ride_minutes(durations: Sequence[float], direction: str) -> float:
    """Pickup: total minus the first arc; dropoff: total minus the closing arc (pure travel time)."""
    if len(durations) == 0:
        return 0
    total = sum(durations)
    excluded = durations[0] if direction == "pickup" else durations[-1]
    return max(0, total - excluded)


def type_accepts(type_: TypeLimits, facts: RouteFacts, *, ride_default: float, tour_default: float) -> bool:
    if not fits(type_, facts.sw_count, facts.so_count):
        return False
    ride = type_.ride_limit if type_.ride_limit is not None else ride_default
    tour = type_.tour_limit if type_.tour_limit is not None else tour_default
    return (facts.minutes <= tour + 1e-9
            and longest_student_ride_minutes(facts.step_durations, facts.direction) <= ride + 1e-9)


def build_selection_request(
    waves: Sequence[Tuple[str, Sequence[Tuple[str, bool, Sequence[RouteFacts]]]]],
    *,
    fixed_type: TypeLimits,
    minimise_type: TypeLimits,
    max_large: int,
    ride_default: float,
    tour_default: float,
    cooldown_large_minutes: float = DEFAULT_COOLDOWN_MINUTES,
    cooldown_car_minutes: float = DEFAULT_COOLDOWN_MINUTES,
    max_cars: Optional[int] = None,
    time_limit_seconds: float = DEFAULT_SELECTION_TIME_LIMIT_S,
    time_scale: int = TIME_SCALE,
) -> Dict[str, Any]:
    """The ``/internal/fleet-selection`` request body of one (date, R, L).

    ``waves`` is ``[(wave_id, [(option_id, baseline, [RouteFacts, ...]), ...]), ...]`` in the producer's
    order (wave order; ``base`` first, then the included quota options).
    """

    def route_body(facts: RouteFacts) -> Dict[str, Any]:
        start = centi(facts.start_minutes, time_scale)
        return {
            "start": start, "end": max(start + 1, centi(facts.end_minutes, time_scale)),
            "minutes": round6(facts.minutes),
            "large_ok": type_accepts(fixed_type, facts, ride_default=ride_default, tour_default=tour_default),
            "car_ok": type_accepts(minimise_type, facts, ride_default=ride_default, tour_default=tour_default),
        }

    request: Dict[str, Any] = {
        "time_scale": time_scale,
        "waves": [{"wave_id": wave_id,
                   "options": [{"option_id": option_id, "baseline": baseline,
                                "routes": [route_body(f) for f in routes]}
                               for option_id, baseline, routes in options]}
                  for wave_id, options in waves],
        "max_large": max_large,
    }
    if max_cars is not None:
        request["max_cars"] = max_cars
    request["cooldown_large"] = centi(cooldown_large_minutes, time_scale)
    request["cooldown_car"] = centi(cooldown_car_minutes, time_scale)
    request["time_limit_seconds"] = time_limit_seconds
    return request


def effective_cooldown(value: Optional[int], time_scale: int) -> int:
    """Router rule: a missing cooldown is 10 real minutes in scaled units."""
    return DEFAULT_COOLDOWN_MINUTES * time_scale if value is None else value


def solve_request(request: Dict[str, Any], *, time_limit_s: float) -> DaySelectionResult:
    """``solve_day_selection`` on a request body, with the router's effective parameters."""
    scale = request.get("time_scale", 1)
    waves = tuple(
        Wave(w["wave_id"], tuple(
            Option(o["option_id"], tuple(Route(r["start"], r["end"], r["minutes"], r.get("large_ok", True),
                                               r.get("car_ok", True)) for r in o["routes"]), o.get("baseline", False))
            for o in w["options"]))
        for w in request["waves"])
    return solve_day_selection(
        waves, request["max_large"],
        cooldown_large=effective_cooldown(request.get("cooldown_large"), scale),
        cooldown_car=effective_cooldown(request.get("cooldown_car"), scale),
        max_cars=request.get("max_cars"), time_limit_s=time_limit_s)


def result_body(res: DaySelectionResult) -> Dict[str, Any]:
    """The router's response body for a result."""
    return {"status": res.status, "cars": res.cars, "large_peak": res.large_peak, "car_minutes": res.car_minutes,
            "total_minutes": res.total_minutes, "selection": res.selection, "diagnostics": res.diagnostics,
            "stats": res.stats}
