"""Brute-force oracle for tiny waves (tests only; design EXACT_SOLVER_AMPL_DESIGN.md sections 2 and 8).

Deliberately independent of ``route_enumeration``: it works on single occurrence nodes
(no (location, class) aggregation), tries every order of every subset with
``itertools.permutations`` and every set partition, and evaluates routes with its own
F1 arithmetic. Lexicographic objective: single type (K, D); typed (K_m, D) with at most
``q`` routes of the quota type (F4).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

MAX_ORACLE_NODES = 7


@dataclass(frozen=True)
class BruteForceResult:
    objective: Optional[Tuple[int, int]]  # (K or K_m, D); None when no feasible partition exists
    routes: tuple  # ((type_id, node order), ...)


def _limits(t, max_ride: int, max_tour: int):
    ride = t.ride_limit_minutes if t.ride_limit_minutes is not None else max_ride
    tour = t.tour_limit_minutes if t.tour_limit_minutes is not None else max_tour
    return ride, tour


def _route(direction: str, matrix, order) -> Optional[Tuple[int, int]]:
    path = [0, *order, 0]
    arcs = []
    for a, b in zip(path, path[1:]):
        v = matrix[a][b]
        if v is None:
            return None
        arcs.append(v)
    tour = sum(arcs)
    ride = tour - arcs[0] if direction == "pickup" else tour - arcs[-1]
    return tour, ride


def best_orders_by_subset(direction: str, matrix, classes: Sequence[str], types, *, max_ride: int,
                          max_tour: int, max_n: int = 8) -> Dict[tuple, tuple]:
    """{(frozenset(nodes), type_id): (tour, ride, order)} for every subset with a feasible order."""
    n = len(classes)
    if n > max_n:
        raise ValueError(f"brute force is limited to n <= {max_n} (got {n})")
    out: Dict[tuple, tuple] = {}
    nodes = range(1, n + 1)
    for size in range(1, n + 1):
        for subset in itertools.combinations(nodes, size):
            sw = sum(1 for v in subset if classes[v - 1] == "Sw")
            so = size - sw
            evaluated = [(order, _route(direction, matrix, order)) for order in itertools.permutations(subset)]
            for t in types:
                if sw > t.sw_capacity or so > t.so_capacity:
                    continue
                if t.total_capacity is not None and size > t.total_capacity:
                    continue
                ride_lim, tour_lim = _limits(t, max_ride, max_tour)
                best = None
                for order, rc in evaluated:
                    if rc is None or rc[0] > tour_lim or rc[1] > ride_lim:
                        continue
                    if best is None or rc[0] < best[0]:
                        best = (rc[0], rc[1], order)
                if best is not None:
                    out[(frozenset(subset), t.type_id)] = best
    return out


def _set_partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for part in _set_partitions(rest):
        yield [[first]] + part
        for i in range(len(part)):
            yield part[:i] + [[first] + part[i]] + part[i + 1:]


def brute_force_optimum(direction: str, matrix, classes: Sequence[str], types, *, max_ride: int, max_tour: int,
                        minimize_type: Optional[str] = None, quota=None) -> BruteForceResult:
    """Lexicographic optimum over all set partitions x all orders x all type labels (n <= 7)."""
    n = len(classes)
    if n > MAX_ORACLE_NODES:
        raise ValueError(f"the oracle is limited to n <= {MAX_ORACLE_NODES} (got {n})")
    if n == 0:
        return BruteForceResult((0, 0), ())
    best_sub = best_orders_by_subset(direction, matrix, classes, types, max_ride=max_ride, max_tour=max_tour,
                                     max_n=MAX_ORACLE_NODES)
    qtype, q = quota if quota is not None else (None, None)
    best = None
    for part in _set_partitions(list(range(1, n + 1))):
        options = []
        for block in part:
            key = frozenset(block)
            opts = [(t.type_id, best_sub[(key, t.type_id)]) for t in types if (key, t.type_id) in best_sub]
            if not opts:
                break
            options.append(opts)
        else:
            for choice in itertools.product(*options):
                if qtype is not None and sum(1 for tid, _ in choice if tid == qtype) > q:
                    continue
                k = sum(1 for tid, _ in choice if minimize_type is None or tid == minimize_type)
                d = sum(rec[0] for _, rec in choice)
                if best is None or (k, d) < best[0]:
                    best = ((k, d), tuple((tid, rec[2]) for tid, rec in choice))
    if best is None:
        return BruteForceResult(None, ())
    return BruteForceResult(best[0], best[1])
