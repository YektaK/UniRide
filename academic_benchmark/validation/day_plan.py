"""Independent day-plan checker (WP-E11 J6; design ``JOINT_DAY_MODEL_DESIGN.md`` section 5.1; DECISION_LOG E13, E14, H01, H03).

This module recomputes, from the matrix arcs alone, everything a claimed day plan says about itself, and reports every
rule that does not hold. A day plan is a set of routes. Each route belongs to one wave, serves occurrences of that wave in
visiting order and has a vehicle type.

Independence: standard library only. It imports nothing from ``uniride_core`` (``exact``, ``planning``), ``optimizer_api``,
``scripts`` or the rest of ``academic_benchmark``, and it shares no function with the solver, the enumerator or the
production selection code, and a static import guard keeps it that way (``test_exact_reference_boundaries.py``). The
module defines no vehicle types of its own: the types (seat limits, total seats, cooldown, optional ride and tour limits;
for example H01: the sedan has 0 Sw seats, H03: a Doblo has at most 1 Sw and 3 seats in total) are inputs, taken by the
caller from the source manifest of the plan.

Rules checked (violation codes in brackets):

1. coverage: every occurrence of every wave appears in exactly one route of that wave [MISSING_OCCURRENCE,
   DUPLICATE_OCCURRENCE]; a route holds no occurrence of another wave [MIXED_WAVE] or of no wave [UNKNOWN_OCCURRENCE];
   routes name a known wave and a known type [UNKNOWN_WAVE, UNKNOWN_TYPE, EMPTY_ROUTE];
2. per-type capacity, with the class taken from the location code prefix ``Sw`` / ``So`` [CAPACITY_SW, CAPACITY_SO,
   CAPACITY_TOTAL, UNKNOWN_CLASS]; a per-route claim of the class counts, if given, must match [CLASS_MISMATCH];
3. every arc of the closed tour depot -> s1 -> ... -> sk -> depot exists and is a non-negative integer [MISSING_ARC,
   BAD_ARC]. Two consecutive stops with the same location code cost 0 (as the exact loader builds its wave matrix);
4. tour <= the type's limit (else the day default T) [TOUR_LIMIT], and the longest student ride <= the type's limit (else
   the default R) [RIDE_LIMIT]; the longest ride is the tour minus the first arc for a pickup wave and the tour minus the
   closing arc for a dropoff wave (production ``longest_student_ride_minutes``);
5. anchored interval: a pickup route is [anchor - tour, anchor], a dropoff route [anchor, anchor + tour]; a route that
   starts before minute 0 or ends after ``service_day_end`` (the cooldown excluded) leaves the service day
   [OUTSIDE_SERVICE_DAY];
6. per-type peak of the half-open busy intervals [start, end + cooldown): once in integer minutes and once at
   ``time_scale`` (default 100) with the production grid rule ``end = max(start + 1, end * time_scale)``. Both peaks are
   reported; they must be equal [PEAK_GRID_MISMATCH]. A difference is a disagreement between the integer-minute model and
   the production grid, not an infeasible plan; it can only occur with a 0-minute tour (an empty minute interval that the
   grid still counts as one unit) and stays blocking. Optional caps per type (the large fleet bound L) [PEAK_ABOVE_CAP];
7. claimed values: the peak of a type (compared with the time_scale peak) [CLAIMED_PEAK], the total vehicle minutes
   [CLAIMED_TOTAL_MINUTES], the minutes of a type [CLAIMED_TYPE_MINUTES], the route count [CLAIMED_ROUTE_COUNT] and the
   minutes of a single route [CLAIMED_ROUTE_MINUTES].

Not checked here: that the plan is optimal, and anything about enumeration or solver state. Wave definitions are an input;
a caller that derives them from the routes of an archived response (``plan_from_single_type_response``) cannot see an
occurrence that no route carries, so a production-side demand list is the stronger source when one exists.

Everything is pure and deterministic; nothing is read from disk or written.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

DEFAULT_TIME_SCALE = 100
SERVICE_DAY_END_MINUTES = 24 * 60
DIRECTIONS = ("pickup", "dropoff")


@dataclass(frozen=True)
class TypeSpec:
    """One vehicle type. ``ride_limit`` / ``tour_limit`` override the day defaults when set."""

    type_id: str
    sw_capacity: int
    so_capacity: int
    cooldown_minutes: int
    total_capacity: Optional[int] = None
    ride_limit: Optional[int] = None
    tour_limit: Optional[int] = None


@dataclass(frozen=True)
class Wave:
    wave_id: str
    direction: str
    anchor_minutes: int
    occurrences: Mapping[str, str]  # occurrence id -> location code


@dataclass(frozen=True)
class Route:
    wave_id: str
    type_id: str
    stops: Tuple[str, ...]  # occurrence ids in visiting order
    claimed_sw: Optional[int] = None
    claimed_so: Optional[int] = None
    claimed_minutes: Optional[int] = None


@dataclass(frozen=True)
class DayClaims:
    """Values the plan's producer states about itself; every field is optional."""

    route_count: Optional[int] = None
    total_minutes: Optional[int] = None
    minutes_by_type: Mapping[str, int] = field(default_factory=dict)
    peaks: Mapping[str, int] = field(default_factory=dict)  # type id -> claimed peak (K, S or the large peak)


@dataclass(frozen=True)
class Violation:
    code: str
    where: str
    message: str


@dataclass(frozen=True)
class DayPlanReport:
    violations: Tuple[Violation, ...] = ()
    peaks_minutes: Mapping[str, int] = field(default_factory=dict)
    peaks_centi: Mapping[str, int] = field(default_factory=dict)
    total_minutes: int = 0
    minutes_by_type: Mapping[str, int] = field(default_factory=dict)
    route_count: int = 0
    route_metrics: Tuple[Mapping[str, Any], ...] = ()

    @property
    def ok(self) -> bool:
        return not self.violations

    @property
    def codes(self) -> Tuple[str, ...]:
        return tuple(v.code for v in self.violations)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _class_of(code: str) -> Optional[str]:
    if code.startswith("Sw"):
        return "Sw"
    if code.startswith("So"):
        return "So"
    return None


def _peak(intervals: Sequence[Tuple[int, int]]) -> int:
    """Maximum number of half-open intervals [a, b) that cover one point; an empty interval covers nothing."""
    events: List[Tuple[int, int]] = []
    for a, b in intervals:
        if b > a:
            events.append((a, 1))
            events.append((b, -1))
    best = current = 0
    for _, delta in sorted(events):  # at one time the -1 events come first: the interval is open at its end
        current += delta
        best = max(best, current)
    return best


def check_day_plan(*, waves: Sequence[Wave], routes: Sequence[Route], types: Mapping[str, TypeSpec],
                   arcs: Mapping[Tuple[str, str], Any], depot: str, tour_limit: int, ride_limit: int,
                   peak_caps: Optional[Mapping[str, int]] = None, claims: Optional[DayClaims] = None,
                   time_scale: int = DEFAULT_TIME_SCALE, service_day_end: int = SERVICE_DAY_END_MINUTES) -> DayPlanReport:
    """Check one day plan and return every violation found together with the recomputed values."""
    if not _is_int(time_scale) or time_scale <= 0:
        raise ValueError(f"time_scale must be a positive integer, got {time_scale!r}")
    violations: List[Violation] = []

    def fail(code: str, where: str, message: str) -> None:
        violations.append(Violation(code, where, message))

    wave_by_id: Dict[str, Wave] = {}
    code_of: Dict[str, str] = {}
    wave_of: Dict[str, str] = {}
    for wave in waves:
        wave_by_id[wave.wave_id] = wave
        for occ_id, code in wave.occurrences.items():
            code_of[occ_id] = code
            wave_of[occ_id] = wave.wave_id
        if wave.direction not in DIRECTIONS:
            fail("BAD_DIRECTION", wave.wave_id, f"direction {wave.direction!r} is neither pickup nor dropoff")
        if not _is_int(wave.anchor_minutes):
            fail("BAD_ANCHOR", wave.wave_id, f"anchor {wave.anchor_minutes!r} is not an integer minute")

    served: Dict[str, int] = {occ_id: 0 for occ_id in code_of}
    intervals_min: Dict[str, List[Tuple[int, int]]] = {}
    intervals_centi: Dict[str, List[Tuple[int, int]]] = {}
    minutes_by_type: Dict[str, int] = {}
    total_minutes = 0
    metrics: List[Dict[str, Any]] = []

    for index, route in enumerate(routes):
        where = f"route {index} ({route.wave_id}/{route.type_id})"
        wave = wave_by_id.get(route.wave_id)
        spec = types.get(route.type_id)
        if wave is None:
            fail("UNKNOWN_WAVE", where, f"wave {route.wave_id!r} is not defined")
        if spec is None:
            fail("UNKNOWN_TYPE", where, f"vehicle type {route.type_id!r} is not defined")
        if not route.stops:
            fail("EMPTY_ROUTE", where, "the route serves no occurrence")
        codes: List[str] = []
        stops_known = True
        for stop in route.stops:
            if wave is not None and stop in wave.occurrences:
                served[stop] += 1
            elif stop in code_of:
                fail("MIXED_WAVE", where, f"occurrence {stop!r} belongs to wave {wave_of[stop]!r}, not {route.wave_id!r}")
            else:
                fail("UNKNOWN_OCCURRENCE", where, f"occurrence {stop!r} is in no wave")
            if stop in code_of:
                codes.append(code_of[stop])
            else:
                stops_known = False
        if wave is None or spec is None or not route.stops or not stops_known:
            continue

        # class counts and capacity
        sw = so = 0
        classes_ok = True
        for code in codes:
            klass = _class_of(code)
            if klass is None:
                fail("UNKNOWN_CLASS", where, f"cannot classify location code {code!r}")
                classes_ok = False
            else:
                sw += klass == "Sw"
                so += klass == "So"
        if classes_ok:
            if route.claimed_sw is not None and route.claimed_so is not None and (route.claimed_sw, route.claimed_so) != (sw, so):
                fail("CLASS_MISMATCH", where, f"location codes give {sw} Sw / {so} So, the plan claims "
                                              f"{route.claimed_sw} / {route.claimed_so}")
            if sw > spec.sw_capacity:
                fail("CAPACITY_SW", where, f"{sw} Sw exceed the {spec.sw_capacity} Sw seats of {spec.type_id}")
            if so > spec.so_capacity:
                fail("CAPACITY_SO", where, f"{so} So exceed the {spec.so_capacity} So seats of {spec.type_id}")
            if spec.total_capacity is not None and sw + so > spec.total_capacity:
                fail("CAPACITY_TOTAL", where, f"{sw + so} students exceed the total of {spec.total_capacity} of {spec.type_id}")

        # arcs and tour
        sequence = [depot, *codes, depot]
        durations: List[int] = []
        arcs_ok = True
        for a, b in zip(sequence, sequence[1:]):
            if a == b:
                durations.append(0)
                continue
            if (a, b) not in arcs:
                fail("MISSING_ARC", where, f"arc {a} -> {b} is not in the matrix")
                arcs_ok = False
                continue
            value = arcs[(a, b)]
            if not _is_int(value) or value < 0:
                fail("BAD_ARC", where, f"arc {a} -> {b} is {value!r}, not a non-negative integer")
                arcs_ok = False
                continue
            durations.append(value)
        if not arcs_ok or wave.direction not in DIRECTIONS or not _is_int(wave.anchor_minutes):
            continue
        tour = sum(durations)
        ride = max(0, tour - (durations[0] if wave.direction == "pickup" else durations[-1]))
        tour_cap = spec.tour_limit if spec.tour_limit is not None else tour_limit
        ride_cap = spec.ride_limit if spec.ride_limit is not None else ride_limit
        if tour > tour_cap:
            fail("TOUR_LIMIT", where, f"tour {tour} exceeds {tour_cap}")
        if ride > ride_cap:
            fail("RIDE_LIMIT", where, f"longest ride {ride} exceeds {ride_cap}")
        if route.claimed_minutes is not None and route.claimed_minutes != tour:
            fail("CLAIMED_ROUTE_MINUTES", where, f"recomputed tour {tour}, the plan claims {route.claimed_minutes}")

        # anchored interval, service day, busy intervals
        if wave.direction == "pickup":
            start, end = wave.anchor_minutes - tour, wave.anchor_minutes
        else:
            start, end = wave.anchor_minutes, wave.anchor_minutes + tour
        if start < 0 or end > service_day_end:
            fail("OUTSIDE_SERVICE_DAY", where, f"route [{start}, {end}] leaves the service day [0, {service_day_end}]")
        intervals_min.setdefault(spec.type_id, []).append((start, end + spec.cooldown_minutes))
        start_c = start * time_scale
        end_c = max(start_c + 1, end * time_scale)
        intervals_centi.setdefault(spec.type_id, []).append((start_c, end_c + spec.cooldown_minutes * time_scale))
        minutes_by_type[spec.type_id] = minutes_by_type.get(spec.type_id, 0) + tour
        total_minutes += tour
        metrics.append({"route": index, "wave_id": route.wave_id, "type_id": spec.type_id, "sw": sw, "so": so,
                        "tour": tour, "ride": ride, "start": start, "end": end})

    for occ_id in sorted(served):
        if served[occ_id] == 0:
            fail("MISSING_OCCURRENCE", wave_of[occ_id], f"occurrence {occ_id!r} is served by no route")
        elif served[occ_id] > 1:
            fail("DUPLICATE_OCCURRENCE", wave_of[occ_id], f"occurrence {occ_id!r} is served by {served[occ_id]} routes")

    peaks_minutes = {t: _peak(iv) for t, iv in sorted(intervals_min.items())}
    peaks_centi = {t: _peak(iv) for t, iv in sorted(intervals_centi.items())}
    for type_id in peaks_minutes:
        if peaks_minutes[type_id] != peaks_centi[type_id]:
            fail("PEAK_GRID_MISMATCH", type_id, f"peak is {peaks_minutes[type_id]} in integer minutes but "
                                                f"{peaks_centi[type_id]} at time_scale {time_scale}")
    for type_id, cap in (peak_caps or {}).items():
        if peaks_centi.get(type_id, 0) > cap:
            fail("PEAK_ABOVE_CAP", type_id, f"peak {peaks_centi[type_id]} exceeds the cap {cap}")

    if claims is not None:
        if claims.route_count is not None and claims.route_count != len(routes):
            fail("CLAIMED_ROUTE_COUNT", "plan", f"the plan has {len(routes)} routes, it claims {claims.route_count}")
        if claims.total_minutes is not None and claims.total_minutes != total_minutes:
            fail("CLAIMED_TOTAL_MINUTES", "plan", f"recomputed {total_minutes} vehicle minutes, it claims {claims.total_minutes}")
        for type_id, claimed in claims.minutes_by_type.items():
            if claimed != minutes_by_type.get(type_id, 0):
                fail("CLAIMED_TYPE_MINUTES", type_id, f"recomputed {minutes_by_type.get(type_id, 0)} minutes, it claims {claimed}")
        for type_id, claimed in claims.peaks.items():
            if claimed != peaks_centi.get(type_id, 0):
                fail("CLAIMED_PEAK", type_id, f"recomputed peak {peaks_centi.get(type_id, 0)}, it claims {claimed}")

    return DayPlanReport(tuple(violations), peaks_minutes, peaks_centi, total_minutes, dict(sorted(minutes_by_type.items())),
                         len(routes), tuple(metrics))


def plan_from_single_type_response(response: Mapping[str, Any], matrix_doc: Mapping[str, Any], *, type_spec: TypeSpec,
                                   depot: str) -> Dict[str, Any]:
    """Keyword arguments of ``check_day_plan`` for one archived single-type response and its matrix slice.

    Wave definitions come from the routes of the response (its jobs); the arcs come from the matrix document unchanged,
    so a bad value is reported by the checker, not hidden here. The route's own class counts and minutes become claims.
    """
    labels = response["occurrenceLabels"]
    waves: List[Wave] = []
    routes: List[Route] = []
    for job in response["jobs"]:
        job_routes = job["result"].get("routes", [])
        waves.append(Wave(job["id"], job["direction"], job["anchorMinutes"],
                          {oid: labels[oid] for route in job_routes for oid in route["student_ids"]}))
        routes.extend(Route(job["id"], type_spec.type_id, tuple(route["student_ids"]), route["sw_count"], route["so_count"],
                            route["total_duration_minutes"]) for route in job_routes)
    arcs = {(rec["origin_code"], rec["destination_code"]): rec["duration_minutes"] for rec in matrix_doc["arcs"]}
    limits = response["limits"]
    return {"waves": waves, "routes": routes, "types": {type_spec.type_id: type_spec}, "arcs": arcs, "depot": depot,
            "tour_limit": limits["maxTourMinutes"], "ride_limit": limits["maxRideTimeMinutes"]}
