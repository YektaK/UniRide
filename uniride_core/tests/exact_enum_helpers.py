"""Test-only helpers for WP-E1 (design EXACT_SOLVER_AMPL_DESIGN.md section 8).

Contains the random instance generator and a tiny exact set-partition search over
enumerated columns (pure Python). Not a test module (no ``test_`` prefix).
"""
from __future__ import annotations

import random
from functools import lru_cache
from typing import Optional


def random_instance(seed: int) -> dict:
    """One random instance with n <= 7 nodes (depot = node 0).

    Mixes: both directions, single and typed fleets (with total_capacity and quota,
    per-type ride/tour limits), nonmetric directed matrices, co-located students
    (same and different class) and occasional missing arcs (None).
    """
    from uniride_core.exact import VehicleTypeSpec

    rng = random.Random(seed)
    n = rng.randint(1, 7)
    nloc = rng.randint(max(1, n - 3), n)
    loc_of = [rng.randrange(nloc) for _ in range(n)]
    classes = tuple(rng.choice(("Sw", "So", "So")) for _ in range(n))
    # location-level directed matrix, index 0 = depot; distinct locations get 1..30
    L = [[0] * (nloc + 1) for _ in range(nloc + 1)]
    for a in range(nloc + 1):
        for b in range(nloc + 1):
            if a != b:
                L[a][b] = None if rng.random() < 0.03 else rng.randint(1, 30)
    locs = [0] + [x + 1 for x in loc_of]
    matrix = tuple(tuple(L[locs[i]][locs[j]] for j in range(n + 1)) for i in range(n + 1))
    location_codes = tuple(f"L{x}" for x in loc_of)
    direction = rng.choice(("pickup", "dropoff"))
    ride = rng.randint(15, 60)
    tour = rng.randint(20, 110)
    typed = seed % 2 == 1
    if not typed:
        sw = rng.randint(0, 3)
        so = rng.randint(1, 4)
        total = rng.choice((None, None, rng.randint(1, sw + so)))
        types = (VehicleTypeSpec("large", sw, so, 10, total),)
        return dict(seed=seed, direction=direction, matrix=matrix, location_codes=location_codes,
                    classes=classes, types=types, ride=ride, tour=tour, minimize_type=None, quota=None)
    big = VehicleTypeSpec("large", rng.randint(1, 4), rng.randint(1, 5), 10,
                          rng.choice((None, None, rng.randint(2, 6))),
                          rng.choice((None, rng.randint(15, 70))), rng.choice((None, rng.randint(20, 120))))
    if big.total_capacity is not None and big.total_capacity > big.sw_capacity + big.so_capacity:
        big = VehicleTypeSpec(big.type_id, big.sw_capacity, big.so_capacity, 10, None,
                              big.ride_limit_minutes, big.tour_limit_minutes)
    small_sw = rng.randint(0, 1)
    small = VehicleTypeSpec("car", small_sw, rng.randint(1, 4), 10,
                            rng.choice((None, rng.randint(1, small_sw + 3))),
                            rng.choice((None, rng.randint(15, 70))), None)
    if small.total_capacity is not None and small.total_capacity > small.sw_capacity + small.so_capacity:
        small = VehicleTypeSpec("car", small.sw_capacity, small.so_capacity, 10, None, small.ride_limit_minutes, None)
    quota = rng.choice((None, ("large", rng.randint(0, 3))))
    types = (big, small) if rng.random() < 0.5 else (small, big)
    return dict(seed=seed, direction=direction, matrix=matrix, location_codes=location_codes,
                classes=classes, types=types, ride=ride, tour=tour, minimize_type="car", quota=quota)


def column_search(result, minimize_type: Optional[str] = None, quota=None):
    """Exact lexicographic optimum over enumerated columns (tests only).

    Each column may be selected an integer number of times (co-located students of one
    (location, class) may need the same multiset route twice). Objective: single type
    (K, D); typed (K_m, D), with at most ``q`` routes of the quota type.
    Returns ((K or K_m, D), [(column, times)]) or None when no cover exists.
    """
    items = result.items
    demand = tuple(it.multiplicity for it in items)
    cols = list(result.columns)
    qtype, q = quota if quota is not None else (None, None)

    @lru_cache(maxsize=None)
    def best(rem: tuple, qleft):
        first = next((i for i, v in enumerate(rem) if v > 0), None)
        if first is None:
            return (0, 0, ())
        out = None
        for ci, c in enumerate(cols):
            a = c.multiplicity
            if a[first] == 0 or any(a[i] > rem[i] for i in range(len(rem))):
                continue
            nq = qleft
            if qtype is not None and c.type_id == qtype:
                if qleft == 0:
                    continue
                nq = qleft - 1
            sub = best(tuple(rem[i] - a[i] for i in range(len(rem))), nq)
            if sub is None:
                continue
            k = (1 if (minimize_type is None or c.type_id == minimize_type) else 0) + sub[0]
            cand = (k, c.cost + sub[1], (ci,) + sub[2])
            if out is None or cand[:2] < out[:2]:
                out = cand
        return out

    res = best(demand, q if qtype is not None else None)
    best.cache_clear()
    if res is None:
        return None
    counts: dict = {}
    for ci in res[2]:
        counts[ci] = counts.get(ci, 0) + 1
    return (res[0], res[1]), [(cols[ci], t) for ci, t in sorted(counts.items())]
