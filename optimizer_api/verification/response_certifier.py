"""Certify a strategy response into a JSON-safe dict.

``certify_optimization_response`` (the production ``/optimize`` and
``/compare`` boundary) re-costs every reported step on the authoritative,
directed ``time_matrix`` arcs through an injected ``arc_lookup`` and judges
capacity, duration, ride-time and time-window feasibility on those matrix
durations. The durations a solver reports about itself are only compared with
the matrix (``arc_duration_mismatch``); they are never trusted.

``certify_benchmark_response`` is the academic/benchmark certificate over a
``ProblemInstance`` and keeps its own matrix contract.
"""

from __future__ import annotations

import copy
import dataclasses
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from uniride_core.adapters.demand_builder import (
    student_capacity_demand,
    student_occurrence_keys,
)
from uniride_core.algorithms.distance import tsplib_distance_by_type
from uniride_core.algorithms.route_schedule import (
    DEADLINE,
    END_AFTER_DAY,
    RouteSchedule,
    START_BEFORE_DAY,
    WINDOW,
    simulate_school_dropoff,
    simulate_school_pickup,
)
from uniride_core.algorithms.feasibility_certificate import (
    DURATION_VIOLATION,
    RIDE_TIME_VIOLATION,
    TIME_WINDOW_VIOLATION,
    Violation,
    check_capacity_vectors,
    check_depot_closure,
    check_duration,
    check_hard_violation_rejection,
    check_occurrence_coverage,
    check_ride_time,
    check_time_windows,
    check_type_quota,
    check_typed_capacity,
    certify_problem_instance,
)
from uniride_core.models import ProblemInstance, RoutingResult

try:  # the API runs with optimizer_api on sys.path; tests/tools may import the package
    from models.schemas import _parse_hhmm
except ModuleNotFoundError:  # pragma: no cover - package-style import
    from optimizer_api.models.schemas import _parse_hhmm


def _build_location_map(problem: ProblemInstance) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for i, _coord in enumerate(problem.coordinates):
        if i == problem.depot_index:
            mapping["depot"] = i
        mapping[f"loc_{i}"] = i
        mapping[f"student_{i}"] = i
    return mapping


def _build_matrix(problem: ProblemInstance) -> Any:
    matrix = problem.dist_matrix
    if matrix is not None:
        return matrix
    n = len(problem.coordinates)
    ewt = problem.edge_weight_type or "EUC_2D"
    built = []
    for i in range(n):
        row = []
        p1 = problem.coordinates[i]
        for j in range(n):
            if i == j:
                row.append(0.0)
            else:
                p2 = problem.coordinates[j]
                row.append(float(tsplib_distance_by_type(ewt, p1, p2)))
        built.append(row)
    return built


def _extract_route_keys(route: Any) -> List[str]:
    locations = getattr(route, "locations", None)
    if isinstance(locations, list) and locations:
        return [str(key) for key in locations]
    steps = list(getattr(route, "route_details", None) or [])
    if not steps:
        return []
    keys = [str(steps[0].location1)]
    keys.extend(str(step.location2) for step in steps)
    return keys


def _keys_to_nodes(
    keys: List[str],
    loc_map: Dict[str, int],
    dimension: int,
    depot: int,
    route_index: int,
    violations: List[Dict[str, Any]],
) -> List[int]:
    nodes: List[int] = []
    for key in keys:
        if isinstance(key, int) and 0 <= key < dimension:
            node = key
        else:
            node = loc_map.get(key)
        if node is None:
            violations.append({
                "type": "missing_arc",
                "severity": "error",
                "details": f"Route {route_index} location key {key!r} not in coordinate map",
                "route_index": route_index,
            })
            nodes.append(-1)
        elif node != depot:
            nodes.append(node)
    return nodes


def _violation_to_dict(violation: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "type": violation.type,
        "severity": violation.severity,
        "details": violation.details,
    }
    if violation.route_index is not None:
        out["route_index"] = violation.route_index
    if violation.node is not None:
        out["node"] = violation.node
    return out


ArcLookup = Callable[[str, str], float]
"""Directed arc lookup over *physical* location codes: ``lookup(origin, destination)``
returns the authoritative travel time in minutes, or raises when the arc is
missing or invalid. ``lookup(a, a)`` is ``0.0``."""

# Responses publish step durations as ``round(x, 2)``. Rounding to two decimals
# moves a value by at most half a unit of the second decimal, i.e. 0.005 min, so
# this is the largest deviation from the matrix arc that is pure float
# formatting. Matrix values themselves may be integers or arbitrary decimals;
# the tolerance must NOT be widened to hide solver rounding (the pre-fix
# OR-Tools scaling error of up to 0.05 min per arc is deliberately larger).
ARC_DURATION_TOLERANCE = 0.005
_ROUNDING_TOLERANCE_STEP = ARC_DURATION_TOLERANCE

# Guard against binary float noise only (e.g. 60.00000000000001 > 60 after
# summing arcs in a different order). Far below any meaningful duration.
_FLOAT_EPSILON = 1e-9

_MATRIX_UNAVAILABLE_ERROR = (
    "certification aborted: authoritative travel-time matrix unavailable"
)


def _sanitize_certify_error(exc: Exception) -> str:
    """Sanitize a certification failure into a bounded, single-line summary.

    The returned string is independent of the raw exception message: it never
    embeds exception text, markers, or newlines, so internal details cannot
    leak across the production boundary.
    """
    return (
        "certification aborted: internal certificate construction failure "
        f"({type(exc).__name__})"
    )


def _route_duration_tolerance(num_steps: int) -> float:
    return _ROUNDING_TOLERANCE_STEP * (num_steps + 1)


def _parse_anchor_minutes(target_time: Any) -> Optional[int]:
    """``HH:MM`` (00:00-23:59, the API's own range check) -> minutes from midnight;
    ``None`` when absent or malformed."""
    if not target_time:
        return None
    try:
        return _parse_hhmm(str(target_time))
    except ValueError:
        return None


def _group_stops(route: List[int], node_codes: List[str]) -> List[List[int]]:
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


# Simulator violation kinds a typed (vehicle_types) request is held to.
_TYPED_SCHEDULE_KINDS = frozenset({DEADLINE, START_BEFORE_DAY, END_AFTER_DAY})


def _fmt(minutes: float) -> str:
    return f"{minutes:.2f}"


def _schedule_violations(
    request: Any,
    routes: List[List[int]],
    matrix: Any,
    depot: int,
    node_codes: List[str],
    demands: List[List[int]],
    occurrence_keys: List[str],
    anchor: int,
    *,
    typed: bool,
    use_windows: bool,
    core_duration_routes: set,
    core_ride_routes: set,
) -> List[Violation]:
    """MT1-02 (audit H2): judge every route on a simulated schedule.

    The route is simulated on the captured authoritative arcs with
    ``simulate_school_pickup`` (deadline = ``target_time - offset_minutes``) or
    ``simulate_school_dropoff`` (ready = ``target_time + offset_minutes``). The
    return arc to school, waiting and service count. Reported as
    ``time_window_violation`` (deadline, window, day bounds), ``duration_violation``
    (tour including waits and service against ``max_travel_time``) and
    ``ride_time_violation`` (per stop, waits and service aboard included, against
    ``max_ride_time``). A route the core travel-only checks already flagged is not
    reported a second time.

    Typed requests keep the deadline, start-before-day and end-after-day checks
    (service time counts toward them) and drop window, tour and ride: the typed
    tour and ride limits stay travel-only (plan MT1-02). No window is applied to a
    typed request, so in practice only the day-bound checks can fire for it.

    Intra-stop arcs are never read: consecutive students at one location code
    form one stop (zero-length arcs by construction; every authoritative lookup
    answers ``lookup(a, a) == 0.0``), and the simulator only uses the arc from
    the last node of a stop to the first node of the next one, which are
    different codes.

    A direction other than ``pickup``/``dropoff`` is a violation, never a drop-off.
    """
    direction = str(getattr(request.direction, "value", request.direction)).strip().lower()
    if direction not in ("pickup", "dropoff"):
        return [Violation(
            type=TIME_WINDOW_VIOLATION,
            severity="error",
            details=f"Request direction {direction!r} is not pickup or dropoff",
        )]
    pickup = direction == "pickup"
    offset = getattr(request, "offset_minutes", 15)
    offset = 15 if offset is None else offset
    dwell = float(getattr(request, "stop_dwell_minutes", 0) or 0)
    sw_boarding = float(getattr(request, "sw_boarding_minutes", 0) or 0)
    tw_by_key = request.get_time_windows() if (use_windows and not typed) else {}
    max_travel = getattr(request, "max_travel_time", None)
    max_ride = getattr(request, "max_ride_time", None)

    out: List[Violation] = []
    for idx, route in enumerate(routes):
        if not route:
            continue
        stops = _group_stops(route, node_codes)
        ins = [depot] + [stop[0] for stop in stops]
        outs = [depot] + [stop[-1] for stop in stops]

        def arc(i: int, j: int, _ins=ins, _outs=outs) -> float:
            return float(matrix[_outs[i]][_ins[j]])

        windows: Dict[int, Tuple[float, float]] = {}
        for position, stop in enumerate(stops, start=1):
            found = [
                tw_by_key[occurrence_keys[node - 1]]
                for node in stop
                if occurrence_keys[node - 1] in tw_by_key
            ]
            if not found:
                continue
            earliest = max(float(w.earliest) for w in found)
            latest = min(float(w.latest) for w in found)
            if earliest > latest:
                out.append(Violation(
                    type=TIME_WINDOW_VIOLATION,
                    severity="error",
                    details=(
                        f"Route {idx} node {stop[0]} students sharing the stop have "
                        f"disjoint time windows (opens {_fmt(earliest)}, closes {_fmt(latest)})"
                    ),
                    route_index=idx,
                    node=stop[0],
                ))
                continue
            windows[position] = (earliest, latest)
        service = {position: dwell for position in range(1, len(stops) + 1)}
        sw_counts = {
            position: sum(1 for node in stop if demands[node][0] > 0)
            for position, stop in enumerate(stops, start=1)
        }

        if pickup:
            limit = float(anchor) - float(offset)
            schedule: RouteSchedule = simulate_school_pickup(
                list(range(1, len(stops) + 1)), arc, deadline=limit, windows=windows,
                service=service, sw_boarding=sw_boarding, sw_counts=sw_counts,
            )
        else:
            limit = float(anchor) + float(offset)
            schedule = simulate_school_dropoff(
                list(range(1, len(stops) + 1)), arc, ready=limit, windows=windows,
                service=service, sw_boarding=sw_boarding, sw_counts=sw_counts,
            )

        for item in schedule.violations:
            if typed and item.kind not in _TYPED_SCHEDULE_KINDS:
                continue
            # simulator positions are 0-based indices into the route we passed
            node = stops[item.position][0] if item.position is not None else None
            if item.kind == DEADLINE:
                details = (
                    f"Route {idx} reaches the school at {_fmt(item.actual)}, after the "
                    f"deadline {_fmt(item.limit)} (target_time minus offset_minutes)"
                )
            elif item.kind == WINDOW:
                details = (
                    f"Route {idx} node {node} service starts at {_fmt(item.actual)}, "
                    f"after the window closes at {_fmt(item.limit)}"
                )
            elif item.kind == START_BEFORE_DAY:
                details = (
                    f"Route {idx} cannot start early enough: departure "
                    f"{_fmt(item.actual)} is before the start of the day"
                )
            elif item.kind == END_AFTER_DAY:
                details = (
                    f"Route {idx} returns to the school at {_fmt(item.actual)}, after "
                    f"the end of the day"
                )
            else:  # pragma: no cover - a new simulator kind must be mapped here
                details = f"Route {idx} schedule violation {item.kind}"
            out.append(Violation(
                type=TIME_WINDOW_VIOLATION,
                severity="error",
                details=details,
                route_index=idx,
                node=node,
            ))

        if typed:
            continue
        if (
            max_travel is not None
            and idx not in core_duration_routes
            and schedule.tour > float(max_travel) + _FLOAT_EPSILON
        ):
            out.append(Violation(
                type=DURATION_VIOLATION,
                severity="error",
                details=(
                    f"Route {idx} duration {schedule.tour:.1f} (waiting and service "
                    f"included) exceeds max {max_travel}"
                ),
                route_index=idx,
            ))
        if max_ride is not None and idx not in core_ride_routes and schedule.ride_times:
            worst = max(range(len(stops)), key=lambda p: schedule.ride_times[p])
            ride = schedule.ride_times[worst]
            if ride > float(max_ride) + _FLOAT_EPSILON:
                out.append(Violation(
                    type=RIDE_TIME_VIOLATION,
                    severity="error",
                    details=(
                        f"Route {idx} {'pickup' if pickup else 'dropoff'} ride time "
                        f"{ride:.1f} (waiting and service aboard included) exceeds max "
                        f"{max_ride} (node {stops[worst][0]})"
                    ),
                    route_index=idx,
                    node=stops[worst][0],
                ))
    return out


def _fleet_assignment_violations(
    routes: List[List[int]], demands: List[List[int]], vehicles: List[Any]
) -> List[Dict[str, Any]]:
    """Certify the returned routes fit the configured vehicle fleet one-to-one.

    Deterministic Kuhn (augmenting-path) bipartite matching: vehicles are
    considered in ascending (sw_capacity, so_capacity, vehicle_id) order and
    every returned route must be assignable to a distinct vehicle whose SW/SO
    capacities cover the route's total load. When no vehicles are configured
    the global capacity vectors rule (handled by the caller).
    """
    if not vehicles:
        return []
    loads: List[List[int]] = [
        [
            sum(demands[node][0] for node in route),
            sum(demands[node][1] for node in route),
        ]
        for route in routes
    ]
    vehicles_sorted = sorted(
        vehicles, key=lambda v: (v.sw_capacity, v.so_capacity, v.vehicle_id)
    )
    if len(routes) > len(vehicles_sorted):
        return [Violation(
            type="fleet_size_violation",
            severity="error",
            details=(
                f"{len(routes)} returned route(s) but only {len(vehicles_sorted)} "
                f"configured vehicle(s)"
            ),
        )]

    match: List[int] = [-1] * len(vehicles_sorted)

    def _try_assign(route_idx: int, seen: set) -> bool:
        sw_load, so_load = loads[route_idx]
        for vehicle_idx, vehicle in enumerate(vehicles_sorted):
            if vehicle_idx in seen:
                continue
            if sw_load <= vehicle.sw_capacity and so_load <= vehicle.so_capacity:
                seen.add(vehicle_idx)
                if match[vehicle_idx] == -1 or _try_assign(match[vehicle_idx], seen):
                    match[vehicle_idx] = route_idx
                    return True
        return False

    for route_idx in range(len(routes)):
        if not _try_assign(route_idx, set()):
            return [Violation(
                type="fleet_capacity_violation",
                severity="error",
                details=(
                    "No feasible one-to-one SW/SO capacity assignment of the "
                    "returned routes to the configured vehicles"
                ),
            )]
    return []


def _typed_fleet_violations(
    request: Any,
    response: Any,
    routes: List[List[int]],
    demands: List[List[int]],
    matrix: Any,
    depot: int,
    vehicle_types: List[Any],
) -> List[Any]:
    """Per-route checks of a typed (``ga_split_hf``) response.

    Capacity (Sw and So pools), the per-type tour limit and the per-type ride
    limit are judged against the type each route declares, on the captured
    authoritative matrix. A route without a declared type is a violation and is
    never defaulted; it is still held to the request-level limits.
    """
    route_types = [
        getattr(route, "vehicle_type", None)
        for route in (getattr(response, "routes", None) or [])
    ]
    route_types += [None] * (len(routes) - len(route_types))
    type_caps = {t.type_id: (t.sw_capacity, t.so_capacity) for t in vehicle_types}
    type_totals = {
        t.type_id: getattr(t, "total_capacity", None)
        for t in vehicle_types
        if getattr(t, "total_capacity", None) is not None
    }
    out: List[Any] = list(
        check_typed_capacity(routes, demands, route_types, type_caps, type_totals)
    )
    quotas = {t.type_id: t.max_routes for t in vehicle_types if t.max_routes is not None}
    out.extend(check_type_quota(route_types, quotas, routes))

    limits = {
        t.type_id: (
            t.max_travel_time if t.max_travel_time is not None else request.max_travel_time,
            t.max_ride_time if t.max_ride_time is not None else getattr(request, "max_ride_time", None),
        )
        for t in vehicle_types
    }
    default_limits = (request.max_travel_time, getattr(request, "max_ride_time", None))
    direction = getattr(request.direction, "value", request.direction)
    for idx, route in enumerate(routes):
        if not route:
            continue
        tour_limit, ride_limit = limits.get(route_types[idx], default_limits)
        found = list(check_duration(
            [route], matrix, depot, float(tour_limit) + _FLOAT_EPSILON, None
        ))
        if ride_limit is not None:
            found.extend(check_ride_time(
                [route], matrix, depot, float(ride_limit), direction,
                tolerance=_FLOAT_EPSILON,
            ))
        out.extend(dataclasses.replace(v, route_index=idx) for v in found)

    counts: Dict[str, int] = {}
    for idx, label in enumerate(route_types):
        if idx < len(routes) and routes[idx] and isinstance(label, str):
            counts[label] = counts.get(label, 0) + 1
    reported = getattr(response, "fleet_mix", None)
    if reported is None or {k: v for k, v in reported.items() if v} != counts:
        out.append(Violation(
            type="fleet_mix_mismatch",
            severity="error",
            details=(
                f"Response fleet_mix {reported!r} differs from the routes' "
                f"declared types {counts!r}"
            ),
        ))
    return out


def certify_optimization_response(
    request: Any,
    response: Any,
    arc_lookup: Optional[ArcLookup] = None,
) -> dict:
    """Public fail-closed boundary for ``/optimize`` and ``/compare`` responses.

    Final certificate that judges the response against the authoritative
    directed travel-time matrix reachable through ``arc_lookup`` (the same
    snapshot the solve was bound to when the request is snapshot-bound). Never
    raises: any internal failure, and a missing ``arc_lookup``, yields an
    ``is_feasible=False`` certificate carrying only a sanitized
    ``certify_error`` summary. See ``_certify_optimization_response`` for the
    checks performed.
    """
    if arc_lookup is None:
        return {
            "is_feasible": False,
            "violation_count": 0,
            "violations": [],
            "certify_error": _MATRIX_UNAVAILABLE_ERROR,
        }
    try:
        return _certify_optimization_response(request, response, arc_lookup)
    except Exception as exc:  # noqa: BLE001 - fail-closed certification
        return {
            "is_feasible": False,
            "violation_count": 0,
            "violations": [],
            "certify_error": _sanitize_certify_error(exc),
        }


def _certify_optimization_response(
    request: Any, response: Any, arc_lookup: ArcLookup
) -> dict:
    """Certify a production ``OptimizationResponse`` against its request.

    Rebuilds the integer-node route representation from the response's own
    ``route_details`` chains (validating chain continuity, depot closure, and
    per-step arc validity), then runs the shared core feasibility checks under
    the request's hard constraints, in addition to response/request
    consistency checks: route ``total_duration_minutes`` against the reported
    step durations and the response total against the route totals (2-decimal
    rounding tolerance), ``sw_count``/``so_count`` against the occurrence
    loads of the visited nodes, ``student_ids`` against the ordered
    occurrence nodes (positional match against each node's student id or
    occurrence key), ``total_vehicles`` against the non-empty route count, and
    the heterogeneous fleet when ``request.vehicles`` is set (deterministic
    one-to-one SW/SO capacity assignment, superseding global caps).

    Matrix provenance (C2): every step is re-costed on the directed arc
    returned by ``arc_lookup`` for the physical codes of its endpoints (depot
    id and each student's ``location_code``). A step whose reported duration
    deviates from that arc by more than ``ARC_DURATION_TOLERANCE`` is an
    ``arc_duration_mismatch`` error; a step whose endpoints cannot be resolved,
    or whose arc the matrix cannot answer, is a ``missing_arc`` error. The
    duration, ride-time and time-window checks then run on the matrix
    durations, never on the reported ones. The lookup is only as authoritative
    as the matrix behind it: callers pass the request's bound snapshot, or the
    DataLoader repository. This bound certifies constraint satisfaction, not
    optimality.
    """
    occurrence_keys = student_occurrence_keys(request.students)
    node_keys = [request.depot.id] + occurrence_keys
    loc_to_node = {key: idx for idx, key in enumerate(node_keys)}
    dimension = len(node_keys)
    depot = 0

    node_codes = [str(request.depot.id)] + [
        str(student.location_code) for student in request.students
    ]
    demands = [[0, 0]] + [
        list(student_capacity_demand(student)) for student in request.students
    ]
    student_by_key = {
        key: student for student, key in zip(request.students, occurrence_keys)
    }
    fleet = list(getattr(request, "vehicles", None) or [])
    vehicle_types = list(getattr(request, "vehicle_types", None) or [])
    typed = bool(vehicle_types)
    # Typed (ga_split_hf) requests judge capacity per route against the route's
    # declared type; the global caps and the one-to-one ``vehicles`` matching
    # only apply when no types are declared (single-type behaviour unchanged).
    capacities = None if (fleet or typed) else [request.sw_capacity, request.so_capacity]

    routes: List[List[int]] = []
    pre_violations: List[Dict[str, Any]] = []

    for route_index, route in enumerate(getattr(response, "routes", None) or []):
        steps = list(getattr(route, "route_details", None) or [])
        if not steps:
            pre_violations.append({
                "type": "depot_closure", "severity": "error",
                "details": f"Route {route_index} has no route details",
                "route_index": route_index,
            })
            routes.append([])
            continue

        for step, next_step in zip(steps, steps[1:]):
            if step.location2 != next_step.location1:
                pre_violations.append({
                    "type": "route_continuity", "severity": "error",
                    "details": f"Route {route_index} broken chain: {step.location2!r} != {next_step.location1!r}",
                    "route_index": route_index,
                })

        if steps[0].location1 != request.depot.id:
            pre_violations.append({
                "type": "depot_closure", "severity": "error",
                "details": f"Route {route_index} does not start at depot {request.depot.id!r}",
                "route_index": route_index,
            })

        if steps[-1].location2 != request.depot.id:
            pre_violations.append({
                "type": "depot_closure", "severity": "error",
                "details": f"Route {route_index} does not end at depot {request.depot.id!r}",
                "route_index": route_index,
            })

        keys = [steps[0].location1] + [step.location2 for step in steps]
        nodes: List[int] = []
        node_chain: List[int] = []
        for key in keys:
            node = loc_to_node.get(str(key)) if not isinstance(key, int) else (key if 0 <= key < dimension else None)
            if node is None:
                pre_violations.append({
                    "type": "missing_arc", "severity": "error",
                    "details": f"Route {route_index} location key {key!r} not in request",
                    "route_index": route_index,
                })
                continue
            node_chain.append(node)
            if node != depot:
                nodes.append(node)
        if any(node == depot for node in node_chain[1:-1]):
            pre_violations.append({
                "type": "route_continuity", "severity": "error",
                "details": f"Route {route_index} contains an interior depot visit",
                "route_index": route_index,
            })
        routes.append(nodes)

        reported_total = float(getattr(route, "total_duration_minutes", 0.0) or 0.0)
        steps_sum = sum(float(step.duration) for step in steps)
        if not math.isfinite(reported_total) or not math.isfinite(steps_sum):
            pre_violations.append({
                "type": "non_finite_duration", "severity": "error",
                "details": (
                    f"Route {route_index} has a non-finite duration total: "
                    f"reported {reported_total}, step sum {steps_sum}"
                ),
                "route_index": route_index,
            })
        elif abs(reported_total - steps_sum) > _route_duration_tolerance(len(steps)):
            pre_violations.append({
                "type": "route_duration_mismatch", "severity": "error",
                "details": (
                    f"Route {route_index} total_duration_minutes {reported_total} "
                    f"differs from step durations sum {steps_sum}"
                ),
                "route_index": route_index,
            })

        sw_load = sum(demands[node][0] for node in nodes)
        so_load = sum(demands[node][1] for node in nodes)
        reported_sw = int(getattr(route, "sw_count", 0) or 0)
        reported_so = int(getattr(route, "so_count", 0) or 0)
        if reported_sw != sw_load or reported_so != so_load:
            pre_violations.append({
                "type": "load_count_mismatch", "severity": "error",
                "details": (
                    f"Route {route_index} sw_count/so_count {reported_sw}/{reported_so} "
                    f"differs from occurrence loads {sw_load}/{so_load}"
                ),
                "route_index": route_index,
            })

        expected_tokens: List[Any] = []
        for node in nodes:
            key = occurrence_keys[node - 1]
            student = student_by_key[key]
            expected_tokens.append((student.id, key))
        reported_ids = list(getattr(route, "student_ids", None) or [])
        if len(reported_ids) != len(nodes):
            pre_violations.append({
                "type": "student_id_mismatch", "severity": "error",
                "details": (
                    f"Route {route_index} student_ids has {len(reported_ids)} entries "
                    f"but the route visits {len(nodes)} student(s)"
                ),
                "route_index": route_index,
            })
        else:
            for position, (reported, (student_id, key)) in enumerate(zip(reported_ids, expected_tokens)):
                if reported != student_id and reported != key:
                    pre_violations.append({
                        "type": "student_id_mismatch", "severity": "error",
                        "details": (
                            f"Route {route_index} student_ids[{position}] {reported!r} "
                            f"does not match visited node {student_id!r} (key {key!r})"
                        ),
                        "route_index": route_index,
                    })

    matrix = [[0.0] * dimension for _ in range(dimension)]
    arc_cache: Dict[Tuple[int, int], Optional[float]] = {}

    def _matrix_arc(src: int, dst: int) -> Optional[float]:
        """Authoritative arc for node indices; ``None`` when it cannot be answered."""
        key = (src, dst)
        if key not in arc_cache:
            try:
                value: Optional[float] = float(arc_lookup(node_codes[src], node_codes[dst]))
            except Exception:  # noqa: BLE001 - any lookup failure is fail-closed
                value = None
            if value is not None and (not math.isfinite(value) or value < 0.0):
                value = None
            arc_cache[key] = value
        return arc_cache[key]

    reported_unanswered: set = set()

    def _unanswered(route_index: int, src: int, dst: int) -> None:
        if (route_index, src, dst) in reported_unanswered:
            return
        reported_unanswered.add((route_index, src, dst))
        pre_violations.append({
            "type": "missing_arc", "severity": "error",
            "details": (
                f"Route {route_index} arc {node_keys[src]!r}->{node_keys[dst]!r} "
                "has no valid arc in the authoritative travel-time matrix"
            ),
            "route_index": route_index,
        })

    for route_index, route in enumerate(getattr(response, "routes", None) or []):
        for step in getattr(route, "route_details", None) or []:
            src = loc_to_node.get(str(step.location1))
            dst = loc_to_node.get(str(step.location2))
            if src is None or dst is None:
                pre_violations.append({
                    "type": "missing_arc", "severity": "error",
                    "details": (
                        f"Route {route_index} step {step.location1!r}->{step.location2!r} "
                        "has an endpoint that cannot be resolved to a travel-time matrix code"
                    ),
                    "route_index": route_index,
                })
                continue
            duration = float(step.duration)
            if not (math.isfinite(duration) and duration >= 0.0):
                pre_violations.append({
                    "type": "missing_arc", "severity": "error",
                    "details": f"Route {route_index} arc {step.location1!r}->{step.location2!r} has invalid duration {step.duration!r}",
                    "route_index": route_index,
                })
                continue
            expected = _matrix_arc(src, dst)
            if expected is None:
                _unanswered(route_index, src, dst)
                continue
            if abs(duration - expected) > ARC_DURATION_TOLERANCE + _FLOAT_EPSILON:
                pre_violations.append({
                    "type": "arc_duration_mismatch", "severity": "error",
                    "details": (
                        f"Route {route_index} step {step.location1!r}->{step.location2!r} "
                        f"reports {duration} min but the matrix arc is {expected} min"
                    ),
                    "route_index": route_index,
                })
            matrix[src][dst] = expected

    # The feasibility checks walk the node chain depot -> nodes -> depot; make
    # sure every arc of that chain is the matrix arc and not a default of 0.
    for route_index, route_nodes in enumerate(routes):
        if not route_nodes:
            continue
        chain = [depot, *route_nodes, depot]
        for src, dst in zip(chain, chain[1:]):
            expected = _matrix_arc(src, dst)
            if expected is None:
                _unanswered(route_index, src, dst)
            else:
                matrix[src][dst] = expected

    routed_totals = [
        float(getattr(route, "total_duration_minutes", 0.0) or 0.0)
        for route in (getattr(response, "routes", None) or [])
    ]
    reported_total = float(getattr(response, "total_duration_minutes", 0.0) or 0.0)
    routed_sum = sum(routed_totals)
    if not math.isfinite(reported_total) or not math.isfinite(routed_sum):
        pre_violations.append({
            "type": "non_finite_duration", "severity": "error",
            "details": (
                f"Response has a non-finite duration total: reported "
                f"{reported_total}, route totals sum {routed_sum}"
            ),
        })
    elif abs(reported_total - routed_sum) > _ROUNDING_TOLERANCE_STEP * (len(routed_totals) + 1):
        pre_violations.append({
            "type": "response_duration_mismatch", "severity": "error",
            "details": (
                f"Response total_duration_minutes {reported_total} differs from "
                f"route totals sum {routed_sum}"
            ),
        })

    reported_time_window_violations = getattr(
        response, "total_time_window_violations", None
    )
    if reported_time_window_violations is not None:
        try:
            reported_tw_value = float(reported_time_window_violations)
        except (TypeError, ValueError):
            reported_tw_value = float("nan")
        if (
            isinstance(reported_time_window_violations, bool)
            or not math.isfinite(reported_tw_value)
            or reported_tw_value < 0
            or not reported_tw_value.is_integer()
        ):
            pre_violations.append({
                "type": "reported_time_window_violation",
                "severity": "error",
                "details": "Response has invalid total_time_window_violations",
            })
        elif reported_tw_value > 0:
            pre_violations.append({
                "type": "reported_time_window_violation",
                "severity": "error",
                "details": "Response reports time-window violations",
            })

    nonempty_routes = [r for r in routes if r]
    reported_total_vehicles = int(getattr(response, "total_vehicles", 0) or 0)
    if reported_total_vehicles != len(nonempty_routes):
        pre_violations.append({
            "type": "vehicle_count_mismatch", "severity": "error",
            "details": (
                f"Response total_vehicles {reported_total_vehicles} differs from "
                f"{len(nonempty_routes)} non-empty route(s)"
            ),
        })

    # MT1-02: with a target_time the routes are simulated (deadline, windows,
    # waits and service count). Only a windowed request that carries no usable
    # target_time (the API refuses it with 422, MT1-08) still takes the legacy
    # core check, so a duck-typed request is never judged more leniently.
    use_windows = bool(getattr(request, "use_time_windows", False))
    raw_target = getattr(request, "target_time", None)
    anchor = _parse_anchor_minutes(raw_target)
    if raw_target and anchor is None:
        pre_violations.append({
            "type": TIME_WINDOW_VIOLATION, "severity": "error",
            "details": f"Request target_time {raw_target!r} is not a valid HH:MM time",
        })
    time_windows = None
    if use_windows and not raw_target:
        tw_by_key = request.get_time_windows()
        time_windows = [(0, 1440)]
        for key in occurrence_keys:
            window = tw_by_key.get(key)
            time_windows.append((window.earliest, window.latest) if window else (0, 1440))

    violations = []
    violations.extend(check_depot_closure(routes, depot, dimension))
    violations.extend(check_occurrence_coverage(routes, dimension, depot, ["depot"] + occurrence_keys))
    violations.extend(_fleet_assignment_violations(routes, demands, fleet))
    if capacities is not None:
        violations.extend(check_capacity_vectors(routes, demands, capacities))
    if typed:
        violations.extend(_typed_fleet_violations(
            request, response, routes, demands, matrix, depot, vehicle_types
        ))
    else:
        violations.extend(check_duration(
            routes, matrix, depot, float(request.max_travel_time) + _FLOAT_EPSILON, None
        ))
    max_ride_time = getattr(request, "max_ride_time", None)
    if max_ride_time is not None and not typed:
        # Fail-closed safety net for every strategy: a result that violates
        # the per-student ride limit is rejected whether or not the strategy
        # knows about the field. The matrix holds the true arcs, so only float
        # noise is tolerated (reported-arc rounding is handled per arc above).
        violations.extend(check_ride_time(
            routes, matrix, depot, float(max_ride_time),
            getattr(request.direction, "value", request.direction),
            tolerance=_FLOAT_EPSILON,
        ))
    if anchor is not None:
        violations.extend(_schedule_violations(
            request, routes, matrix, depot, node_codes, demands, occurrence_keys,
            anchor,
            typed=typed,
            use_windows=use_windows,
            core_duration_routes={
                v.route_index for v in violations if v.type == DURATION_VIOLATION
            },
            core_ride_routes={
                v.route_index for v in violations if v.type == RIDE_TIME_VIOLATION
            },
        ))
    elif time_windows is not None:
        violations.extend(check_time_windows(
            routes, matrix, depot, time_windows, None,
            getattr(request.direction, "value", request.direction),
            None, getattr(request, "offset_minutes", 15),
        ))
    violations.extend(check_hard_violation_rejection(
        getattr(response, "success", None), violations
    ))

    all_violations = pre_violations + [_violation_to_dict(v) for v in violations]
    return {
        "is_feasible": not all_violations,
        "violation_count": len(all_violations),
        "violations": all_violations,
    }


def certify_benchmark_response(problem: ProblemInstance, response: Any) -> dict:
    loc_map = _build_location_map(problem)
    dimension = problem.dimension
    depot = problem.depot_index
    pre_violations: List[Dict[str, Any]] = []
    int_routes: List[List[int]] = []

    for route in getattr(response, "routes", None) or []:
        route_index = len(int_routes)
        keys = _extract_route_keys(route)
        int_routes.append(_keys_to_nodes(keys, loc_map, dimension, depot, route_index, pre_violations))

    problem_copy = copy.copy(problem)
    problem_copy.dist_matrix = _build_matrix(problem)

    result = RoutingResult(
        algorithm=getattr(response, "algorithm_used", "unknown"),
        problem_type=problem.problem_type,
        objective_cost=getattr(response, "total_duration_minutes", 0.0) or 0.0,
        routes=int_routes,
        capacity_violations=int(getattr(response, "capacity_violations", 0) or 0),
        tw_violations=int(getattr(response, "total_time_window_violations", 0) or 0),
    )

    try:
        certificate = certify_problem_instance(
            result, problem_copy, success=getattr(response, "success", None)
        )
    except Exception as exc:
        return {
            "is_feasible": False,
            "violation_count": 0,
            "violations": [],
            "certify_error": str(exc),
        }

    violations = pre_violations + [_violation_to_dict(v) for v in certificate.violations]
    return {
        "is_feasible": certificate.is_feasible and not pre_violations,
        "violation_count": len(violations),
        "violations": violations,
    }


__all__ = ["certify_optimization_response", "certify_benchmark_response"]