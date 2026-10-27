"""MT1-03: one route-timing helper for the returned schedule and the certificate.

``simulate_route`` is the single place that turns a stop order into a simulated
schedule on the MT1-01 simulator: stops sharing a location code form one physical
stop (one dwell, one wait, one ride time), windows of students at one stop are
intersected, service time is the request's dwell plus the Sw boarding extra. The
certificate (``response_certifier._schedule_violations``) and the router
(``attach_route_schedules``) both call it, so "returned times equal certified
times" holds by construction and is still re-checked by the certificate
(``schedule_mismatch``).

``attach_route_schedules`` writes ``departure_time``, ``arrival_times`` (HH:MM
compatibility fields) and the exact fields ``schedule_start_minutes``,
``schedule_end_minutes``, ``arrival_minutes`` on every route of a response. Times
come only from the authoritative arcs, never from the durations a strategy reports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from uniride_core.adapters.demand_builder import (
    student_capacity_demand,
    student_occurrence_keys,
)
from uniride_core.algorithms.route_schedule import (
    RouteSchedule,
    simulate_school_dropoff,
    simulate_school_pickup,
)
from uniride_core.algorithms.route_scheduling import minutes_to_time

try:  # the API runs with optimizer_api on sys.path; tests/tools may import the package
    from models.schemas import _parse_hhmm
except ModuleNotFoundError:  # pragma: no cover - package-style import
    from optimizer_api.models.schemas import _parse_hhmm

ArcLookup = Callable[[str, str], float]
NodeArc = Callable[[int, int], float]


def parse_anchor_minutes(target_time: Any) -> Optional[int]:
    """``HH:MM`` (00:00-23:59, the API's own range check) -> minutes from midnight;
    ``None`` when absent or malformed."""
    if not target_time:
        return None
    try:
        return _parse_hhmm(str(target_time))
    except ValueError:
        return None


def group_stops(route: List[int], node_codes: List[str]) -> List[List[int]]:
    """Split a route into physical stops.

    Students sharing a location are separate occurrence nodes joined by
    zero-length arcs; a maximal run of consecutive nodes with the same location
    code is one stop (one dwell, one wait, one ride time).
    """
    stops: List[List[int]] = []
    for node in route:
        if stops and node_codes[stops[-1][-1]] == node_codes[node]:
            stops[-1].append(node)
        else:
            stops.append([node])
    return stops


@dataclass(frozen=True)
class RequestNodes:
    """Node numbering of a request: node 0 is the depot, node ``i`` the i-th student."""

    occurrence_keys: List[str]
    node_keys: List[str]
    loc_to_node: Dict[str, int]
    node_codes: List[str]
    demands: List[List[int]]

    @property
    def dimension(self) -> int:
        return len(self.node_keys)


def request_nodes(request: Any) -> RequestNodes:
    occurrence_keys = student_occurrence_keys(request.students)
    node_keys = [request.depot.id] + occurrence_keys
    return RequestNodes(
        occurrence_keys=occurrence_keys,
        node_keys=node_keys,
        loc_to_node={key: idx for idx, key in enumerate(node_keys)},
        node_codes=[str(request.depot.id)]
        + [str(student.location_code) for student in request.students],
        demands=[[0, 0]] + [
            list(student_capacity_demand(student)) for student in request.students
        ],
    )


@dataclass(frozen=True)
class TimingSpec:
    """How a request's routes are timed: direction, the hard limit, service."""

    pickup: bool
    limit: float  # pickup: deadline = target - offset; dropoff: ready = target + offset
    dwell: float
    sw_boarding: float


def timing_direction(request: Any) -> Optional[bool]:
    """``True`` pickup, ``False`` dropoff, ``None`` for any other direction."""
    direction = str(getattr(request.direction, "value", request.direction)).strip().lower()
    if direction == "pickup":
        return True
    if direction == "dropoff":
        return False
    return None


def timing_spec(request: Any, anchor: int) -> Optional[TimingSpec]:
    pickup = timing_direction(request)
    if pickup is None:
        return None
    offset = getattr(request, "offset_minutes", 15)
    offset = 15 if offset is None else offset
    limit = float(anchor) - float(offset) if pickup else float(anchor) + float(offset)
    return TimingSpec(
        pickup=pickup,
        limit=limit,
        dwell=float(getattr(request, "stop_dwell_minutes", 0) or 0),
        sw_boarding=float(getattr(request, "sw_boarding_minutes", 0) or 0),
    )


@dataclass(frozen=True)
class RouteTiming:
    stops: List[List[int]]
    schedule: RouteSchedule
    # stops whose students' windows do not intersect: (node, earliest, latest)
    disjoint_windows: List[Tuple[int, float, float]]


def simulate_route(
    spec: TimingSpec,
    route: List[int],
    arc_nodes: NodeArc,
    nodes: RequestNodes,
    tw_by_key: Dict[str, Any],
    depot: int = 0,
) -> RouteTiming:
    """Simulate one route (non-depot node numbers, in visiting order).

    ``arc_nodes(src, dst)`` is the authoritative directed arc between two node
    numbers. Intra-stop arcs are never read: only the arc from the last node of a
    stop to the first node of the next one is, and those have different location
    codes.
    """
    stops = group_stops(route, nodes.node_codes)
    ins = [depot] + [stop[0] for stop in stops]
    outs = [depot] + [stop[-1] for stop in stops]

    def arc(i: int, j: int) -> float:
        return float(arc_nodes(outs[i], ins[j]))

    windows: Dict[int, Tuple[float, float]] = {}
    disjoint: List[Tuple[int, float, float]] = []
    for position, stop in enumerate(stops, start=1):
        found = [
            tw_by_key[nodes.occurrence_keys[node - 1]]
            for node in stop
            if nodes.occurrence_keys[node - 1] in tw_by_key
        ]
        if not found:
            continue
        earliest = max(float(w.earliest) for w in found)
        latest = min(float(w.latest) for w in found)
        if earliest > latest:
            disjoint.append((stop[0], earliest, latest))
            continue
        windows[position] = (earliest, latest)
    service = {position: spec.dwell for position in range(1, len(stops) + 1)}
    sw_counts = {
        position: sum(1 for node in stop if nodes.demands[node][0] > 0)
        for position, stop in enumerate(stops, start=1)
    }
    positions = list(range(1, len(stops) + 1))
    if spec.pickup:
        schedule = simulate_school_pickup(
            positions, arc, deadline=spec.limit, windows=windows,
            service=service, sw_boarding=spec.sw_boarding, sw_counts=sw_counts,
        )
    else:
        schedule = simulate_school_dropoff(
            positions, arc, ready=spec.limit, windows=windows,
            service=service, sw_boarding=spec.sw_boarding, sw_counts=sw_counts,
        )
    return RouteTiming(stops=stops, schedule=schedule, disjoint_windows=disjoint)


def stop_arrivals_by_key(timing: RouteTiming, nodes: RequestNodes) -> Dict[str, float]:
    """Arrival at each stop (before any wait) for every occurrence key at the stop."""
    out: Dict[str, float] = {}
    for stop, arrival in zip(timing.stops, timing.schedule.arrivals):
        for node in stop:
            out[nodes.occurrence_keys[node - 1]] = arrival
    return out


def _route_nodes(route: Any, nodes: RequestNodes) -> Optional[List[int]]:
    """Non-depot node numbers of a response route, or ``None`` when its chain cannot
    be resolved (the certificate reports that; no schedule is invented for it)."""
    steps = list(getattr(route, "route_details", None) or [])
    if not steps:
        return None
    keys = [steps[0].location1] + [step.location2 for step in steps]
    chain: List[int] = []
    for key in keys:
        node = nodes.loc_to_node.get(str(key))
        if node is None:
            return None
        chain.append(node)
    return [node for node in chain if node != 0]


def _clear_schedule(route: Any) -> None:
    route.departure_time = None
    route.arrival_times = None
    route.schedule_start_minutes = None
    route.schedule_end_minutes = None
    route.arrival_minutes = None


def attach_route_schedules(
    request: Any, routes: Sequence[Any], arc_lookup: Optional[ArcLookup]
) -> None:
    """Set the returned schedule of every route from the simulator.

    Does nothing when the request has no usable ``target_time`` (the response then
    keeps its pre-MT1 shape). A route whose chain cannot be resolved or whose arcs
    the authoritative matrix cannot answer gets no schedule at all (strategy-supplied
    times are cleared, never trusted); the certificate rejects such a route.

    HH:MM display (decision OQ-MT1-10 b): stop times and the departure are rounded
    down; the pickup school arrival is rounded up. Drop-off: the school entry is the
    departure (ready time). The exact minutes are not rounded.
    """
    anchor = parse_anchor_minutes(getattr(request, "target_time", None))
    if anchor is None:
        return
    spec = timing_spec(request, anchor)
    if spec is None:
        return
    nodes = request_nodes(request)
    use_windows = bool(getattr(request, "use_time_windows", False))
    typed = bool(getattr(request, "vehicle_types", None))
    tw_by_key = request.get_time_windows() if (use_windows and not typed) else {}
    depot_key = str(request.depot.id)

    arc_cache: Dict[Tuple[int, int], float] = {}

    def arc_nodes(src: int, dst: int) -> float:
        key = (src, dst)
        if key not in arc_cache:
            value = float(arc_lookup(nodes.node_codes[src], nodes.node_codes[dst]))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError("invalid arc")
            arc_cache[key] = value
        return arc_cache[key]

    for route in routes:
        route_nodes = _route_nodes(route, nodes)
        if arc_lookup is None or not route_nodes:
            _clear_schedule(route)
            continue
        try:
            timing = simulate_route(spec, route_nodes, arc_nodes, nodes, tw_by_key)
        except Exception:  # noqa: BLE001 - an unanswered arc: no schedule for this route
            _clear_schedule(route)
            continue
        schedule = timing.schedule
        arrivals = stop_arrivals_by_key(timing, nodes)
        display: Dict[str, str] = {
            key: minutes_to_time(value, "floor") for key, value in arrivals.items()
        }
        if spec.pickup:
            display[depot_key] = minutes_to_time(schedule.end, "ceil")
        else:
            display[depot_key] = minutes_to_time(schedule.start, "floor")
        route.departure_time = minutes_to_time(schedule.start, "floor")
        route.arrival_times = display
        route.schedule_start_minutes = schedule.start
        route.schedule_end_minutes = schedule.end
        route.arrival_minutes = arrivals


__all__ = [
    "RequestNodes",
    "RouteTiming",
    "TimingSpec",
    "attach_route_schedules",
    "group_stops",
    "parse_anchor_minutes",
    "request_nodes",
    "simulate_route",
    "stop_arrivals_by_key",
    "timing_direction",
    "timing_spec",
]
