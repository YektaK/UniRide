"""Typed split decoder (heterogeneous fleet, WP1).

Pure module, see ``docs/designs/HETEROGENEOUS_FLEET_DESIGN.md`` section 3.1.
Splits a giant tour into routes and labels each route with a vehicle type
(per-type Sw/So capacity, ride limit, tour limit).  At most ``quota`` routes may
use the quota type (the "large" vehicle); the objective is the lexicographic
pair (routes of the minimised type, total cost).

Arc feasibility mirrors ``string_split_decoder.SplitDecoder._build_trips``
(capacity-only path): route = depot -> s1..sk -> depot, no waiting;
pickup longest ride = arcs s1->..->sk->depot, dropoff longest ride =
arcs depot->s1..sk; tour = all arcs incl. the closing one.  Departures from
``SplitDecoder``: a non-finite arc cost is always infeasible, and an
infeasible tour yields ``feasible=False`` with NO singleton fallback.

Nothing here is imported by the academic stack (parity gate P2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from uniride_core.algorithms.string_split_decoder import Direction


@dataclass(frozen=True)
class VehicleType:
    """Per-type limits.  ``None`` ride limit = unlimited."""

    id: str
    sw_capacity: int
    so_capacity: int
    max_tour_duration: float = 120.0
    max_ride_time: Optional[float] = None
    cooldown: float = 0.0  # carried as data for day-level planning; unused here


@dataclass
class TypedSplitResult:
    feasible: bool
    routes: List[List[str]]
    costs: List[float]
    type_ids: List[str]
    total_cost: float
    routes_by_type: Dict[str, int]

    @property
    def num_vehicles(self) -> int:
        return len(self.routes)


def _arc(frm: str, to: str, matrix: Dict[str, Dict[str, float]], asymmetric: bool) -> float:
    direct = matrix.get(frm, {}).get(to)
    if direct is not None:
        return direct
    if not asymmetric:
        rev = matrix.get(to, {}).get(frm)
        if rev is not None:
            return rev
    return math.inf


def decode_typed(
    giant_tour: Sequence[str],
    depot: str,
    distance_matrix: Dict[str, Dict[str, float]],
    demands: Dict[str, Tuple[int, int]],
    types: Sequence[VehicleType],
    *,
    minimize_type: Optional[str] = None,
    quota_type: Optional[str] = None,
    quota: Optional[int] = None,
    is_asymmetric: bool = False,
    direction: Direction = Direction.PICKUP,
) -> TypedSplitResult:
    """Optimal typed split of ``giant_tour`` (depot-free) for a fixed order.

    Minimises (routes of ``minimize_type``, cost) subject to at most ``quota``
    routes of ``quota_type`` (``None`` = unlimited).  Ties: strict ``<``, first
    predecessor (ascending start index, then type order) kept.
    """
    tour = list(giant_tour)
    if any(str(x) == str(depot) for x in tour):
        raise ValueError("typed split expects a depot-free giant tour")
    ids = [t.id for t in types]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate vehicle type ids")
    for name in (minimize_type, quota_type):
        if name is not None and name not in ids:
            raise ValueError(f"unknown vehicle type {name!r}")
    if quota is not None and quota < 0:
        raise ValueError("quota must be >= 0")
    for t in types:
        if t.max_ride_time is not None and not (t.max_ride_time > 0):
            raise ValueError(f"max_ride_time must be positive for {t.id!r}")
    track = quota_type is not None and quota is not None
    kmax = quota if track else 0
    qi = ids.index(quota_type) if quota_type is not None else -1
    mi = ids.index(minimize_type) if minimize_type is not None else -1
    dropoff = str(getattr(direction, "value", direction)).strip().lower() == "dropoff"

    n = len(tour)
    if n == 0:
        return TypedSplitResult(True, [], [], [], 0.0, {i: 0 for i in ids})

    # trips[j]: ascending start i -> [(type_idx, cost)] for segment tour[i:j]
    trips: Dict[int, List[Tuple[int, int, float]]] = {j: [] for j in range(1, n + 1)}
    for i in range(n):
        alive = list(range(len(types)))
        sw = so = 0
        cost = tail = 0.0
        prev = depot
        for j in range(i, n):
            loc = tour[j]
            d_sw, d_so = demands.get(loc, (0, 0))
            sw += d_sw
            so += d_so
            alive = [
                t for t in alive
                if sw <= types[t].sw_capacity and so <= types[t].so_capacity
            ]
            if not alive:
                break
            arc = _arc(prev, loc, distance_matrix, is_asymmetric)
            cost += arc
            if j > i:
                tail += arc
            prev = loc
            ret = _arc(loc, depot, distance_matrix, is_asymmetric)
            total = cost + ret
            if not math.isfinite(total):
                continue
            ride = cost if dropoff else tail + ret
            for t in alive:
                vt = types[t]
                if total > vt.max_tour_duration:
                    continue
                if vt.max_ride_time is not None and not (ride <= vt.max_ride_time):
                    continue
                trips[j + 1].append((i, t, total))

    Label = Tuple[int, float]
    V: List[List[Optional[Label]]] = [[None] * (kmax + 1) for _ in range(n + 1)]
    V[0][0] = (0, 0.0)
    pred: Dict[Tuple[int, int], Tuple[int, int, int]] = {}
    for j in range(1, n + 1):
        for i, t, c in trips[j]:
            for kp in range(kmax + 1):
                base = V[i][kp]
                if base is None:
                    continue
                k = kp + 1 if t == qi and track else kp
                if k > kmax:
                    continue
                cand = (base[0] + (1 if t == mi else 0), base[1] + c)
                cur = V[j][k]
                if cur is None or cand < cur:
                    V[j][k] = cand
                    pred[(j, k)] = (i, kp, t)

    best_k = -1
    for k in range(kmax + 1):
        lab = V[n][k]
        if lab is not None and (best_k < 0 or lab < V[n][best_k]):  # type: ignore[operator]
            best_k = k
    if best_k < 0:
        return TypedSplitResult(False, [], [], [], math.inf, {i: 0 for i in ids})

    routes: List[List[str]] = []
    costs: List[float] = []
    labels: List[str] = []
    j, k = n, best_k
    while j > 0:
        i, kp, t = pred[(j, k)]
        routes.append(tour[i:j])
        costs.append(next(c for (ii, tt, c) in trips[j] if ii == i and tt == t))
        labels.append(ids[t])
        j, k = i, kp
    routes.reverse()
    costs.reverse()
    labels.reverse()
    return TypedSplitResult(
        True, routes, costs, labels, V[n][best_k][1],  # type: ignore[index]
        {i: labels.count(i) for i in ids},
    )
