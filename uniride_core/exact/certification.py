"""Certification bridge for exact wave solutions (design EXACT_SOLVER_AMPL_DESIGN.md section 3; WP-E3).

Solver-agnostic and pure Python. It builds the *payloads* (plain dicts) of the operational request
and response schemas; the caller (``scripts/run_exact_wave_gaps.py``) validates them with the
``optimizer_api`` models and calls ``certify_optimization_response`` on the arcs of the archived
per-date matrix slice. Nothing here imports ``optimizer_api``, ``academic_benchmark`` or ``amplpy``.

* ``request_payload``: the operational ``/optimize`` request of ``src/services/daily-plan-run.ts``
  (``algorithm ga_split``, ``is_asymmetric``, ``use_time_windows = false``, ``max_travel_time`` T,
  ``max_ride_time`` R, template capacities, a virtual fleet of ``min(legs, 50)`` vehicles, depot
  ``D.Kampus``), rebuilt from the loaded wave and its archived parameters.
* ``response_payload``: routes (occurrence ids in visiting order) wrapped in the operational
  response schema: ``route_details`` chains over the request's node keys (a physical location code
  for a single-customer stop, ``<code>#<occurrence id>`` for a shared stop, see
  ``student_occurrence_keys``), step durations taken from the wave matrix, loads and ids.
* ``ga_response_payload``: the archived GA result of the same wave in the same schema (its own
  ``route_details`` are kept), so both sides of a gap pass through the identical certificate call.
* ``recompute_objective`` and ``objective_mismatches``: K and D recomputed in integer arithmetic
  from the matrix and compared with the solver objective (design section 3 step 5).
"""
from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Iterable, List, Optional, Sequence, Tuple

from uniride_core.adapters.demand_builder import student_occurrence_keys

DEPOT_COORDINATES = {"lat": 41.001, "lng": 29.177}  # DUDULLU_DEPOT; the certificate does not use them
OBJECTIVE_TOLERANCE = 1e-6
VEHICLE_CAP = 50  # F5: min(legs, 50) vehicles per call


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _students(wave) -> list:
    return [SimpleNamespace(id=occ, occurrence_id=occ, location_code=code, disability_type=cls)
            for occ, code, cls in zip(wave.occurrence_ids, wave.location_codes, wave.classes)]


def request_payload(wave, *, sw_capacity: int = 4, so_capacity: int = 5, cooldown_minutes: int = 10) -> dict:
    """The operational request of ``wave`` (single type), archived parameters."""
    vehicles = [{"vehicle_id": f"Vehicle{i}", "sw_capacity": sw_capacity, "so_capacity": so_capacity,
                 "cooldown_minutes": cooldown_minutes} for i in range(1, min(wave.legs, VEHICLE_CAP) + 1)]
    return {
        "algorithm": "ga_split", "mode": "sandbox", "direction": wave.direction,
        "target_time": _clock(wave.anchor_minutes), "expected_matrix_sha256": wave.declared_snapshot_sha256,
        "use_time_windows": False, "is_asymmetric": True,
        "max_travel_time": wave.max_tour_minutes, "max_ride_time": wave.max_ride_minutes,
        "sw_capacity": sw_capacity, "so_capacity": so_capacity,
        "depot": {"id": wave.depot_code, **DEPOT_COORDINATES},
        "students": [{"id": s.id, "occurrence_id": s.occurrence_id, "name": s.id, "location_code": s.location_code,
                      "disability_type": s.disability_type} for s in _students(wave)],
        "vehicles": vehicles,
    }


def node_keys(wave) -> dict:
    """{occurrence id: node key} exactly as the certifier derives them from the request students."""
    return dict(zip(wave.occurrence_ids, student_occurrence_keys(_students(wave))))


def _sequence(route) -> Tuple[str, ...]:
    return tuple(getattr(route, "occurrence_ids", route))


def tour_cost(wave, occurrence_ids: Sequence[str]) -> int:
    """Integer tour minutes ``depot -> stops -> depot`` on the wave matrix."""
    index = {occ: i + 1 for i, occ in enumerate(wave.occurrence_ids)}
    path = [0] + [index[o] for o in occurrence_ids] + [0]
    return sum(wave.matrix[a][b] for a, b in zip(path, path[1:]))


def response_payload(wave, routes: Iterable, *, algorithm_used: str = "exact_sp", success: bool = True) -> dict:
    """Wrap routes (occurrence ids in visiting order) in the operational response schema."""
    keys = node_keys(wave)
    cls_of = dict(zip(wave.occurrence_ids, wave.classes))
    index = {occ: i + 1 for i, occ in enumerate(wave.occurrence_ids)}
    out = []
    for n, route in enumerate(routes, start=1):
        seq = _sequence(route)
        chain = [wave.depot_code] + [keys[o] for o in seq] + [wave.depot_code]
        nodes = [0] + [index[o] for o in seq] + [0]
        steps = [{"location1": a, "location2": b, "duration": wave.matrix[i][j], "distance": 0}
                 for a, b, i, j in zip(chain, chain[1:], nodes, nodes[1:])]
        out.append({
            "vehicle_id": f"Vehicle{n}", "route_details": steps,
            "total_duration_minutes": sum(s["duration"] for s in steps), "total_distance_km": 0,
            "sw_count": sum(cls_of[o] == "Sw" for o in seq), "so_count": sum(cls_of[o] == "So" for o in seq),
            "student_ids": list(seq),
        })
    return {"algorithm_used": algorithm_used, "success": success, "routes": out, "total_vehicles": len(out),
            "total_duration_minutes": sum(r["total_duration_minutes"] for r in out)}


def ga_response_payload(wave, archived_result: dict) -> dict:
    """The archived GA result of ``wave`` as an operational response (its own steps are kept)."""
    routes = []
    for r in archived_result["routes"]:
        routes.append({k: copy.deepcopy(r[k]) for k in
                       ("vehicle_id", "route_details", "total_duration_minutes", "total_distance_km", "sw_count",
                        "so_count", "student_ids") if k in r})
    return {"algorithm_used": "ga_split", "success": bool(archived_result.get("success")), "routes": routes,
            "total_vehicles": len(routes),
            "total_duration_minutes": archived_result.get("total_duration_minutes",
                                                          sum(r["total_duration_minutes"] for r in routes))}


def recompute_objective(wave, routes: Iterable) -> Tuple[int, int]:
    """(K, D) in integers: number of non-empty routes and the sum of tour minutes on the wave matrix."""
    seqs = [s for s in (_sequence(r) for r in routes) if s]
    return len(seqs), sum(tour_cost(wave, s) for s in seqs)


def objective_mismatches(k: int, d: int, solver_k: Optional[float], solver_d: Optional[float],
                         tol: float = OBJECTIVE_TOLERANCE) -> List[str]:
    """Differences between the recomputed (K, D) and the solver objective (empty when equal within ``tol``)."""
    problems = []
    for name, mine, theirs in (("K", k, solver_k), ("D", d, solver_d)):
        if theirs is None:
            problems.append(f"{name}: solver value missing")
        elif abs(float(mine) - float(theirs)) > tol:
            problems.append(f"{name}: recomputed {mine} differs from solver {theirs}")
    return problems


# ---------------------------------------------------------------- typed path (WP-E4a, design section 3)
def typed_request_payload(wave, types: Sequence, *, minimize_type: str, quota: Optional[Tuple[str, int]] = None) -> dict:
    """The operational ``ga_split_hf`` request of ``wave``: ``vehicle_types`` (pools, ``total_capacity``, own
    limits, ``max_routes`` on the quota type) and ``minimize_type``, as ``fleet-scenario-run.ts`` builds it.

    ``types`` are ``VehicleTypeSpec``-like objects; ``quota`` is ``(type_id, q)`` or None. No ``vehicles``
    list (mutually exclusive with ``vehicle_types``).
    """
    specs = []
    for t in types:
        spec = {"type_id": t.type_id, "sw_capacity": t.sw_capacity, "so_capacity": t.so_capacity}
        if t.total_capacity is not None:
            spec["total_capacity"] = t.total_capacity
        if t.ride_limit_minutes is not None:
            spec["max_ride_time"] = t.ride_limit_minutes
        if t.tour_limit_minutes is not None:
            spec["max_travel_time"] = t.tour_limit_minutes
        if quota is not None and t.type_id == quota[0]:
            spec["max_routes"] = quota[1]
        specs.append(spec)
    return {
        "algorithm": "ga_split_hf", "mode": "sandbox", "direction": wave.direction,
        "target_time": _clock(wave.anchor_minutes), "expected_matrix_sha256": wave.declared_snapshot_sha256,
        "use_time_windows": False, "is_asymmetric": True,
        "max_travel_time": wave.max_tour_minutes, "max_ride_time": wave.max_ride_minutes,
        "depot": {"id": wave.depot_code, **DEPOT_COORDINATES},
        "students": [{"id": s.id, "occurrence_id": s.occurrence_id, "name": s.id, "location_code": s.location_code,
                      "disability_type": s.disability_type} for s in _students(wave)],
        "vehicle_types": specs, "minimize_type": minimize_type,
    }


def typed_response_payload(wave, routes: Iterable, *, algorithm_used: str = "exact_sp", success: bool = True,
                           type_ids: Optional[Sequence[str]] = None) -> dict:
    """Wrap ``(type_id, occurrence_ids)`` routes in the operational response with ``vehicle_type`` and ``fleet_mix``."""
    routes = [(t, tuple(seq)) for t, seq in routes]
    out = response_payload(wave, [seq for _, seq in routes], algorithm_used=algorithm_used, success=success)
    for route, (type_id, _) in zip(out["routes"], routes):
        route["vehicle_type"] = type_id
    ids = list(type_ids) if type_ids is not None else sorted({t for t, _ in routes})
    mix = {t: 0 for t in ids}
    for type_id, _ in routes:
        mix[type_id] = mix.get(type_id, 0) + 1
    out["fleet_mix"] = mix
    return out


def ga_option_response_payload(wave, option: dict, *, typed: bool, algorithm_used: Optional[str] = None,
                               type_ids: Optional[Sequence[str]] = None) -> dict:
    """An archived WP-E10 menu option (``<date>_R<R>.menu_options.json``) as an operational response.

    The optimizer's own steps are kept. ``typed`` adds each route's ``vehicleType`` and the ``fleet_mix``.
    """
    routes = []
    for r in option["routes"]:
        body = {"vehicle_id": r["vehicleId"],
                "route_details": [{"location1": s["location1"], "location2": s["location2"],
                                   "duration": s["duration"], "distance": 0} for s in r["steps"]],
                "total_duration_minutes": r["totalDurationMinutes"], "total_distance_km": 0,
                "sw_count": r["swCount"], "so_count": r["soCount"], "student_ids": list(r["studentIds"])}
        if typed:
            body["vehicle_type"] = r["vehicleType"]
        routes.append(body)
    out = {"algorithm_used": algorithm_used or ("ga_split_hf" if typed else "ga_split"),
           "success": bool(option.get("success")), "routes": routes, "total_vehicles": len(routes),
           "total_duration_minutes": option.get("totalDurationMinutes") or sum(r["total_duration_minutes"] for r in routes)}
    if typed:
        ids = list(type_ids) if type_ids is not None else sorted({r["vehicle_type"] for r in routes})
        mix = {t: 0 for t in ids}
        for r in routes:
            mix[r["vehicle_type"]] = mix.get(r["vehicle_type"], 0) + 1
        out["fleet_mix"] = mix
    return out


def recompute_typed_objective(wave, routes: Iterable, minimize_type: str) -> Tuple[int, int, int]:
    """``(K_m, D, route count)`` in integers: routes of the minimised type, summed tour minutes, all routes."""
    kept = [(t, tuple(seq)) for t, seq in routes if tuple(seq)]
    return (sum(1 for t, _ in kept if t == minimize_type), sum(tour_cost(wave, seq) for _, seq in kept), len(kept))
