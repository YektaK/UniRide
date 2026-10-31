"""Forward CVRPTW route simulator for Solomon-style academic instances (MT1-11, audit H16).

Third profile of the route-timing family (``route_schedule.py`` holds the two school
profiles). The academic CVRPTW contract is separate from the school contracts
(AGENTS.md: CVRP/CVRPTW validation is its own contract):

* the vehicle leaves the depot at the depot's ready time;
* it waits where a customer window opens later than it arrives;
* every customer is served for its service time;
* a customer is late when service cannot start by its window close;
* the vehicle must be back at the depot by the depot due time.

It returns the same :class:`RouteSchedule` type as the school profiles. A late customer
is a ``window`` violation (one per customer), a late return is a ``deadline`` violation
(one per route). The counts therefore equal those of the holistic counter
``holistic_matrix_engine._time_window_violations``. Pure functions, exact floats, no
I/O. The module is placed next to ``route_schedule.py`` instead of inside it because
``route_schedule.py`` is owned by the MT1-01/MT1-05 line; moving the function there is a
mechanical change.

``route`` lists customers in visiting order without the depot. ``arc(i, j)`` is the
directed travel time. ``windows`` maps a node to ``(ready, due)``; a node without a
window is unconstrained. ``depot_window`` is ``(ready, due)`` of the depot, or ``None``
(depart at 0, no return limit).
"""

from __future__ import annotations

from typing import Hashable, Mapping, Sequence

from uniride_core.algorithms.route_schedule import (
    DEADLINE,
    WINDOW,
    Arc,
    RouteSchedule,
    ScheduleViolation,
    Windows,
)

FORWARD_TW = "forward_tw"
_TOLERANCE = 1e-9  # same tolerance as route_schedule.py


def is_forward_tw(direction: object) -> bool:
    """True when ``direction`` names the academic forward CVRPTW profile."""
    return str(direction or "").strip().lower() == FORWARD_TW


def service_map(
    service_times: Sequence[float] | None, nodes: Sequence[Hashable]
) -> dict[Hashable, float]:
    """Service minutes of ``nodes`` from a node-indexed list (missing entries are 0)."""
    times = list(service_times or [])
    return {
        node: float(times[node]) if isinstance(node, int) and 0 <= node < len(times) else 0.0
        for node in nodes
    }


def window_map(
    time_windows: Sequence[tuple[float, float]] | None, nodes: Sequence[Hashable]
) -> dict[Hashable, tuple[float, float]]:
    """Windows of ``nodes`` from a node-indexed list; nodes beyond the list are free."""
    table = list(time_windows or [])
    return {
        node: (float(table[node][0]), float(table[node][1]))
        for node in nodes
        if isinstance(node, int) and 0 <= node < len(table)
    }


def simulate_forward_tw(
    route: Sequence[Hashable],
    arc: Arc,
    *,
    depot_window: tuple[float, float] | None,
    windows: Windows | None = None,
    service: Mapping[Hashable, float] | None = None,
    depot: Hashable = 0,
) -> RouteSchedule:
    """Leave at the depot ready time, wait for early windows, return by the depot due time."""
    windows = windows or {}
    service = service or {}
    start = float(depot_window[0]) if depot_window is not None else 0.0

    arrivals: list[float] = []
    waits: list[float] = []
    services: list[float] = []
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
        service_minutes = float(service.get(node, 0.0))
        arrivals.append(arrival)
        waits.append(wait)
        services.append(service_minutes)
        t = arrival + wait + service_minutes
        prev = node
    end = t + arc(prev, depot) if route else t
    if route and depot_window is not None and end > float(depot_window[1]) + _TOLERANCE:
        violations.append(ScheduleViolation(DEADLINE, None, end, float(depot_window[1])))
    # Solomon has no ride-time limit; the time on board is reported for completeness.
    rides = tuple(a + w + s - start for a, w, s in zip(arrivals, waits, services))
    return RouteSchedule(
        start=start,
        arrivals=tuple(arrivals),
        waits=tuple(waits),
        end=end,
        violations=tuple(violations),
        services=tuple(services),
        ride_times=rides,
    )


__all__ = [
    "FORWARD_TW",
    "is_forward_tw",
    "service_map",
    "window_map",
    "simulate_forward_tw",
]
