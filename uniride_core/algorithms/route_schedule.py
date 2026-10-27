"""Pure route-timing simulator for the school profiles (MT1-01).

One definition of "when is each stop reached" for a fixed stop order. The module
is deliberately small: pure functions, exact floats (no ``int()`` truncation), no
I/O, no dependency beyond the standard library.

Two profiles share one output type:

* :func:`simulate_school_pickup` -- the vehicle must reach the school (depot) by a
  hard ``deadline``. It departs as late as possible (latest feasible departure) and
  waits only where a window opens later than the vehicle arrives.
* :func:`simulate_school_dropoff` -- the vehicle leaves the school at ``ready`` and
  waits where a window opens later than it arrives.

All times are minutes from midnight. ``arc(i, j)`` is the authoritative directed
travel time between two nodes; the depot (school) node id is ``depot`` (default 0).
``route`` lists the stops in visiting order and does not contain the depot.

Counted quantities (owner decisions, plan section 3.1):

* the return arc is part of the route;
* waiting and service count in the tour (``end - start``);
* a pickup student boards when service at the stop starts (arrival plus wait); the
  ride runs from there to school arrival, so waiting and service after boarding,
  including the service at the student's own stop, count. A drop-off student rides
  from school departure to arrival at the stop, so waits at earlier stops count;
* service time of a stop is ``service[stop]`` plus ``sw_boarding`` per Sw student
  at the stop (``sw_counts[stop]``); both inputs are optional and default to 0.

Feasibility tolerance: comparisons allow ``1e-9`` minutes so that float round-off in
a sum of decimal arcs is not reported as a violation.

The module is imported by no other module in MT1-01.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Hashable, Mapping, Sequence

DEADLINE = "deadline"
WINDOW = "window"
START_BEFORE_DAY = "start_before_day"
END_AFTER_DAY = "end_after_day"

_TOLERANCE = 1e-9

Arc = Callable[[Hashable, Hashable], float]
Windows = Mapping[Hashable, tuple[float, float]]


@dataclass(frozen=True)
class ScheduleViolation:
    """One broken rule.

    ``position`` is the index in the route for a ``window`` violation and ``None``
    for route-level kinds. ``actual`` and ``limit`` are minutes from midnight.
    """

    kind: str
    position: int | None
    actual: float
    limit: float

    @property
    def amount(self) -> float:
        """Minutes by which the rule is broken (always positive for a violation)."""
        if self.kind == START_BEFORE_DAY:
            return self.limit - self.actual
        return self.actual - self.limit


@dataclass(frozen=True)
class RouteSchedule:
    start: float  # departure from the depot
    arrivals: tuple[float, ...]  # arrival at each stop, before any wait
    waits: tuple[float, ...]  # waiting at each stop before service starts
    end: float  # arrival back at the depot (school)
    violations: tuple[ScheduleViolation, ...]  # empty = feasible
    services: tuple[float, ...]  # service minutes used at each stop
    ride_times: tuple[float, ...]  # per stop; definition in the module docstring

    @property
    def feasible(self) -> bool:
        return not self.violations

    @property
    def tour(self) -> float:
        """Whole route duration, waits and service included."""
        return self.end - self.start

    @property
    def service_starts(self) -> tuple[float, ...]:
        return tuple(a + w for a, w in zip(self.arrivals, self.waits))


def _services(
    route: Sequence[Hashable],
    service: Mapping[Hashable, float] | None,
    sw_boarding: float,
    sw_counts: Mapping[Hashable, int] | None,
) -> tuple[float, ...]:
    service = service or {}
    sw_counts = sw_counts or {}
    return tuple(
        float(service.get(node, 0.0)) + float(sw_boarding) * sw_counts.get(node, 0)
        for node in route
    )


def _forward(
    route: Sequence[Hashable],
    arc: Arc,
    start: float,
    windows: Windows,
    services: tuple[float, ...],
    depot: Hashable,
) -> tuple[list[float], list[float], list[ScheduleViolation], float]:
    """Leave the depot at ``start``; wait for windows; return to the depot."""
    arrivals: list[float] = []
    waits: list[float] = []
    violations: list[ScheduleViolation] = []
    t = start
    prev = depot
    for position, node in enumerate(route):
        arrival = t + arc(prev, node)
        wait = 0.0
        if node in windows:
            earliest, latest = windows[node]
            if arrival < earliest:
                wait = earliest - arrival
            if arrival + wait > latest + _TOLERANCE:
                violations.append(
                    ScheduleViolation(WINDOW, position, arrival + wait, float(latest))
                )
        arrivals.append(arrival)
        waits.append(wait)
        t = arrival + wait + services[position]
        prev = node
    end = t + arc(prev, depot) if route else t
    return arrivals, waits, violations, end


def simulate_school_pickup(
    route: Sequence[Hashable],
    arc: Arc,
    *,
    deadline: float,
    windows: Windows | None = None,
    service: Mapping[Hashable, float] | None = None,
    sw_boarding: float = 0.0,
    sw_counts: Mapping[Hashable, int] | None = None,
    day_start: float = 0.0,
    depot: Hashable = 0,
) -> RouteSchedule:
    """Pickup: reach the school by ``deadline``, departing as late as possible.

    One backward pass gives the latest service start at every stop
    (``min(window close, next latest - service - arc)``); the departure is the first
    latest start minus the first arc. A forward pass from there waits only where a
    window opens later. For a fixed order this is exact: a feasible departure exists
    iff the forward pass from this one reports no violation, and no later departure
    is feasible. ``deadline`` is the hard limit (``target_time - offset_minutes``).
    """
    windows = windows or {}
    services = _services(route, service, sw_boarding, sw_counts)

    if route:
        latest_start = float(deadline)
        next_node = depot
        # latest service start at each stop, built from the last stop backwards
        latest: list[float] = [0.0] * len(route)
        for position in range(len(route) - 1, -1, -1):
            node = route[position]
            bound = latest_start - arc(node, next_node) - services[position]
            if node in windows:
                bound = min(bound, float(windows[node][1]))
            latest[position] = bound
            latest_start = bound
            next_node = node
        start = latest[0] - arc(depot, route[0])
    else:
        start = float(deadline)

    arrivals, waits, violations, end = _forward(
        route, arc, start, windows, services, depot
    )
    if end > deadline + _TOLERANCE:
        violations.append(ScheduleViolation(DEADLINE, None, end, float(deadline)))
    if start < day_start - _TOLERANCE:
        violations.append(
            ScheduleViolation(START_BEFORE_DAY, None, start, float(day_start))
        )
    rides = tuple(end - (a + w) for a, w in zip(arrivals, waits))
    return RouteSchedule(
        start=start,
        arrivals=tuple(arrivals),
        waits=tuple(waits),
        end=end,
        violations=tuple(violations),
        services=services,
        ride_times=rides,
    )


def simulate_school_dropoff(
    route: Sequence[Hashable],
    arc: Arc,
    *,
    ready: float,
    windows: Windows | None = None,
    service: Mapping[Hashable, float] | None = None,
    sw_boarding: float = 0.0,
    sw_counts: Mapping[Hashable, int] | None = None,
    day_end: float = 1440.0,
    depot: Hashable = 0,
) -> RouteSchedule:
    """Drop-off: leave the school at ``ready``; wait where a window opens later.

    Feasible iff every stop is reached by its window close and the vehicle is back
    by ``day_end``. There is no per-student "home by" constraint.
    """
    windows = windows or {}
    services = _services(route, service, sw_boarding, sw_counts)
    start = float(ready)

    arrivals, waits, violations, end = _forward(
        route, arc, start, windows, services, depot
    )
    if end > day_end + _TOLERANCE:
        violations.append(ScheduleViolation(END_AFTER_DAY, None, end, float(day_end)))
    rides = tuple(a - start for a in arrivals)
    return RouteSchedule(
        start=start,
        arrivals=tuple(arrivals),
        waits=tuple(waits),
        end=end,
        violations=tuple(violations),
        services=services,
        ride_times=rides,
    )
