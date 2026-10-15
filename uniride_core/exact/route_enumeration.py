"""Exact route enumeration for one wave (design EXACT_SOLVER_AMPL_DESIGN.md section 1.1, Step A; WP-E1).

One column per (multiset S over (location, class) items, vehicle type t): the minimum-duration
order of S that satisfies ``ride <= R_t``, ``tour <= T_t`` and the capacities of t
(``Sw <= sw_t``, ``So <= so_t``, ``Sw + So <= total_t`` when set). Route semantics are F1:
``depot -> s1..sk -> depot``, no waiting; pickup ride = the tour minus its first arc,
dropoff ride = the tour minus its closing arc; tour = all arcs.

* Pickup: backward DP ``g(S, f)`` (cheapest path that starts at f, serves S and ends at the
  depot); column cost ``min_f { c(0,f) + g(S,f) : g <= R_t, c(0,f) + g <= T_t }``.
* Dropoff: forward DP ``h(S, e)`` (cheapest path depot -> .. -> e over S); tour ``h + c(e,0)``.
* Labels are extended only while some type still admits the class counts and the path cost
  (the cost is a ride in both directions and only grows because every arc is >= 0).
* Co-located students of one class are one item with a multiplicity (F2). A label may move
  to any item that still has unserved students, including an item visited earlier, so the
  nonmetric "revisit" orders the GA can produce stay representable (F8).
* A missing arc (``None`` or ``inf``) never forms a label or a column (O06); it is not an error.
* Integer arithmetic only; iteration order and tie-breaks are deterministic; the only caps that
  switch model are counts (column cap, label cap). The wall-clock safety limit aborts with
  ``timing_dependent_abort`` and never switches model.

Pure Python, no amplpy. Not imported by optimizer_api or src.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence, Tuple

COLUMN_CAP_DEFAULT = 2_000_000
# Label cap: proposed from the WP-E1 measurement over all archived waves
# (docs/paper/results/week-2026-10-05-exact/wp-e1-enumeration/); pending review before WP-E2.
LABEL_CAP_DEFAULT = 20_000_000
WALL_CLOCK_LIMIT_DEFAULT = 600.0  # seconds (10 min safety limit)
ENUMERATION_STATUSES = ("complete", "count_cap", "timing_dependent_abort")
_CLOCK_CHECK_EVERY = 4096
_CLASSES = ("Sw", "So")
_DIRECTIONS = ("pickup", "dropoff")


@dataclass(frozen=True)
class RouteType:
    """A vehicle type with its resolved limits (type value, else the wave's R and T)."""

    type_id: str
    sw_capacity: int
    so_capacity: int
    total_capacity: Optional[int]
    ride_limit: int
    tour_limit: int

    def admits(self, sw: int, so: int) -> bool:
        return sw <= self.sw_capacity and so <= self.so_capacity and (
            self.total_capacity is None or sw + so <= self.total_capacity)


@dataclass(frozen=True)
class Item:
    """Interchangeable occurrences: one (location, class) with their node indices (1..n)."""

    location_code: str
    cls: str
    multiplicity: int
    nodes: tuple


@dataclass(frozen=True)
class Column:
    type_id: str
    multiplicity: tuple  # a_{r,item} over EnumerationResult.items
    stop_order: tuple  # item indices in visiting order (an item may recur: revisit)
    cost: int  # d_r = tour (integer, matrix units)
    ride: int
    tour: int


@dataclass(frozen=True)
class EnumerationResult:
    direction: str
    status: str  # one of ENUMERATION_STATUSES
    cap_fired: Optional[str]  # None, "column_cap", "label_cap" or "wall_clock"
    model: Optional[str]  # "SP" (complete), "compact" (count cap), None (timing abort)
    items: tuple
    types: tuple
    columns: tuple  # empty unless status == "complete"
    column_count: int
    label_count: int
    labels_per_level: tuple
    column_cap: int
    label_cap: Optional[int]
    wall_clock_limit: float
    elapsed_seconds: float = field(default=0.0, compare=False)


def _arc(value, where: str):
    if value is None or (isinstance(value, float) and math.isinf(value) and value > 0):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"arc {where} must be an integer >= 0 or missing (None), got {value!r}")
    return value


def _pos_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be an integer >= 0, got {value!r}")
    return value


def resolve_types(types: Sequence, max_ride: int, max_tour: int) -> tuple:
    """VehicleTypeSpec-like objects -> RouteType (ride/tour: type value, else the wave's R/T)."""
    out = []
    seen = set()
    for t in types:
        if t.type_id in seen:
            raise ValueError(f"duplicate type id {t.type_id!r}")
        seen.add(t.type_id)
        ride = t.ride_limit_minutes if t.ride_limit_minutes is not None else max_ride
        tour = t.tour_limit_minutes if t.tour_limit_minutes is not None else max_tour
        total = t.total_capacity
        out.append(RouteType(t.type_id, _pos_int(t.sw_capacity, "sw_capacity"), _pos_int(t.so_capacity, "so_capacity"),
                             None if total is None else _pos_int(total, "total_capacity"),
                             _pos_int(ride, "ride limit"), _pos_int(tour, "tour limit")))
    if not out:
        raise ValueError("at least one vehicle type is required")
    return tuple(out)


def _items(matrix, location_codes, classes):
    n = len(classes)
    if len(location_codes) != n:
        raise ValueError("location_codes and classes must have equal length")
    if len(matrix) != n + 1 or any(len(row) != n + 1 for row in matrix):
        raise ValueError(f"matrix must be {n + 1}x{n + 1} (depot + {n} occurrences)")
    if any(c not in _CLASSES for c in classes):
        raise ValueError(f"class must be one of {_CLASSES}")
    arcs = [[None if i == j else _arc(matrix[i][j], f"[{i}][{j}]") for j in range(n + 1)] for i in range(n + 1)]
    for i in range(n + 1):
        arcs[i][i] = 0
    for u in range(1, n + 1):
        for v in range(1, n + 1):
            if u != v and location_codes[u - 1] == location_codes[v - 1] and arcs[u][v] != 0:
                raise ValueError(f"co-located occurrences {u}, {v} must be joined by zero arcs (F2)")
    groups: dict = {}
    for node in range(1, n + 1):
        groups.setdefault((location_codes[node - 1], classes[node - 1]), []).append(node)
    items = tuple(Item(loc, cls, len(nodes), tuple(nodes)) for (loc, cls), nodes in sorted(groups.items()))
    for it in items:
        rep = it.nodes[0]
        for node in it.nodes[1:]:
            for x in range(n + 1):
                if x in (rep, node):
                    continue
                if arcs[node][x] != arcs[rep][x] or arcs[x][node] != arcs[x][rep]:
                    raise ValueError(f"occurrences {rep} and {node} of item {it.location_code}/{it.cls} "
                                     "are not interchangeable (different arcs)")
    return items, arcs


def enumerate_routes(direction: str, matrix, location_codes: Sequence[str], classes: Sequence[str], types: Sequence,
                     *, max_ride: int, max_tour: int, column_cap: int = COLUMN_CAP_DEFAULT,
                     label_cap: Optional[int] = LABEL_CAP_DEFAULT,
                     wall_clock_limit: float = WALL_CLOCK_LIMIT_DEFAULT,
                     clock: Callable[[], float] = time.monotonic) -> EnumerationResult:
    """Enumerate one column per feasible (multiset, type); see the module docstring.

    ``matrix`` is node-level: index 0 is the depot, 1..n the occurrences in the order of
    ``location_codes``/``classes``. Entries are integers >= 0, or ``None``/``inf`` for a
    missing arc. ``types`` are ``VehicleTypeSpec``-like objects.
    """
    start = clock()
    if direction not in _DIRECTIONS:
        raise ValueError(f"direction must be one of {_DIRECTIONS}")
    rtypes = resolve_types(types, _pos_int(max_ride, "max_ride"), _pos_int(max_tour, "max_tour"))
    items, arcs = _items(matrix, location_codes, classes)
    pickup = direction == "pickup"
    m = len(items)
    reps = [it.nodes[0] for it in items]
    mult = [it.multiplicity for it in items]
    is_sw = [1 if it.cls == "Sw" else 0 for it in items]
    weight = []
    acc = 1
    for k in mult:
        weight.append(acc)
        acc *= k + 1
    from0 = [arcs[0][r] for r in reps]
    to0 = [arcs[r][0] for r in reps]
    # step[a][f]: cost of adding item a to a label whose open end is f
    # (pickup: prepend a before the first stop f; dropoff: append a after the last stop f)
    step = [[(0 if a == f else (arcs[reps[a]][reps[f]] if pickup else arcs[reps[f]][reps[a]]))
             for f in range(m)] for a in range(m)]
    total_sw = sum(k for k, s in zip(mult, is_sw) if s)
    total_so = sum(mult) - total_sw
    # lim[sw][so]: largest path cost a label may have and still be completed on some type
    lim = [[-1] * (total_so + 1) for _ in range(total_sw + 1)]
    types_for = [[() for _ in range(total_so + 1)] for _ in range(total_sw + 1)]
    for sw in range(total_sw + 1):
        for so in range(total_so + 1):
            ok = tuple(ti for ti, t in enumerate(rtypes) if t.admits(sw, so))
            types_for[sw][so] = ok
            if ok:
                lim[sw][so] = max(min(rtypes[ti].ride_limit, rtypes[ti].tour_limit) for ti in ok)
    P = m + 1
    NONE = m  # parent marker of a one-stop label
    ntypes = len(rtypes)

    def result(status, cap, columns, column_count, label_count, per_level):
        model = {"complete": "SP", "count_cap": "compact"}.get(status)
        return EnumerationResult(direction, status, cap, model, items, rtypes, tuple(columns), column_count,
                                 label_count, tuple(per_level), column_cap, label_cap, float(wall_clock_limit),
                                 elapsed_seconds=clock() - start)

    def late() -> bool:
        return clock() - start > wall_clock_limit

    levels = [None]  # levels[k]: {S * m + end: cost * P + parent} for |S| = k
    infos = [None]  # infos[k]: {S: (sw, so)}
    columns = []
    label_count = column_count = 0
    per_level: list = []
    # level 1
    cur: dict = {}
    info: dict = {}
    for a in range(m):
        base = to0[a] if pickup else from0[a]
        sw, so = is_sw[a], 1 - is_sw[a]
        if base is None or base > lim[sw][so]:
            continue
        cur[weight[a] * m + a] = base * P + NONE
        info[weight[a]] = (sw, so)
        label_count += 1
        if label_cap is not None and label_count > label_cap:
            return result("count_cap", "label_cap", (), column_count, label_count, per_level + [len(cur)])
    k = 1
    while cur:
        if late():
            return result("timing_dependent_abort", "wall_clock", (), column_count, label_count, per_level + [len(cur)])
        per_level.append(len(cur))
        levels.append(cur)
        infos.append(info)
        # ---- columns of level k: best (tour, ride, end) per (S, t) ----
        best: dict = {}
        for key, val in cur.items():
            S, f = divmod(key, m)
            g = val // P
            close = from0[f] if pickup else to0[f]
            if close is None:
                continue
            tour = g + close
            sw, so = info[S]
            for ti in types_for[sw][so]:
                t = rtypes[ti]
                if g > t.ride_limit or tour > t.tour_limit:
                    continue
                bk = S * ntypes + ti
                cand = (tour, g, f)
                old = best.get(bk)
                if old is None or cand < old:
                    best[bk] = cand
        for bk in sorted(best):
            S, ti = divmod(bk, ntypes)
            tour, ride, f = best[bk]
            column_count += 1
            if column_count > column_cap:
                return result("count_cap", "column_cap", (), column_count, label_count, per_level)
            if column_count % _CLOCK_CHECK_EVERY == 0 and late():
                return result("timing_dependent_abort", "wall_clock", (), column_count, label_count, per_level)
            seq = [f]
            s_code, lev, end = S, k, f
            parent = levels[lev][s_code * m + end] % P
            while parent != NONE:
                s_code -= weight[end]
                lev -= 1
                end = parent
                seq.append(end)
                parent = levels[lev][s_code * m + end] % P
            if not pickup:
                seq.reverse()
            columns.append(Column(rtypes[ti].type_id, tuple((S // weight[i]) % (mult[i] + 1) for i in range(m)),
                                  tuple(seq), tour, ride, tour))
        # ---- extend to level k + 1 ----
        nxt: dict = {}
        ninfo: dict = {}
        for key, val in cur.items():
            S, f = divmod(key, m)
            g = val // P
            sw, so = info[S]
            for a in range(m):
                # an item may be (re)visited while it still has unserved students (F8 revisit)
                if (S // weight[a]) % (mult[a] + 1) >= mult[a]:
                    continue
                arc = step[a][f]
                if arc is None:
                    continue
                ng = g + arc
                nsw, nso = sw + is_sw[a], so + 1 - is_sw[a]
                if ng > lim[nsw][nso]:
                    continue
                nS = S + weight[a]
                nkey = nS * m + a
                nval = ng * P + f
                old = nxt.get(nkey)
                if old is None:
                    nxt[nkey] = nval
                    ninfo[nS] = (nsw, nso)
                    label_count += 1
                    if label_cap is not None and label_count > label_cap:
                        return result("count_cap", "label_cap", (), column_count, label_count, per_level + [len(nxt)])
                    if label_count % _CLOCK_CHECK_EVERY == 0 and late():
                        return result("timing_dependent_abort", "wall_clock", (), column_count, label_count,
                                      per_level + [len(nxt)])
                elif nval < old:
                    nxt[nkey] = nval
        cur, info = nxt, ninfo
        k += 1
    return result("complete", None, columns, column_count, label_count, per_level)


def enumerate_wave(wave, types: Sequence, **kwargs) -> EnumerationResult:
    """``enumerate_routes`` for a ``WaveInstance`` (its R and T are the type defaults)."""
    return enumerate_routes(wave.direction, wave.matrix, wave.location_codes, wave.classes, types,
                            max_ride=wave.max_ride_minutes, max_tour=wave.max_tour_minutes, **kwargs)


def incompatible_student_pairs(result: EnumerationResult) -> frozenset:
    """Node pairs (u < v) that no enumerated column of any type contains together (design 1.2).

    Only defined on a complete enumeration. Never inferred from two-student columns alone:
    a longer route can make a pair jointly feasible on a nonmetric matrix.
    """
    if result.status != "complete":
        raise ValueError("the clique floor needs a complete enumeration (omitted for the compact model)")
    together = set()
    supports = {c.multiplicity for c in result.columns}
    for mvec in supports:
        present = [i for i, a in enumerate(mvec) if a > 0]
        for x, i in enumerate(present):
            if mvec[i] >= 2:
                together.add((i, i))
            for j in present[x + 1:]:
                together.add((i, j))
    node_item = {}
    for idx, it in enumerate(result.items):
        for nd in it.nodes:
            node_item[nd] = idx
    nodes = sorted(node_item)
    out = set()
    for x, u in enumerate(nodes):
        for v in nodes[x + 1:]:
            a, b = sorted((node_item[u], node_item[v]))
            if (a, b) not in together:
                out.add((u, v))
    return frozenset(out)


def clique_floor(result: EnumerationResult) -> Tuple[int, tuple]:
    """Largest set of pairwise incompatible students: (size, sorted node tuple). Bounds the
    total route count (= K in the single-type case only, design 1.2)."""
    pairs = incompatible_student_pairs(result)
    nodes = sorted(nd for it in result.items for nd in it.nodes)
    if not nodes:
        return 0, ()
    pos = {nd: i for i, nd in enumerate(nodes)}
    adj = [0] * len(nodes)
    for u, v in pairs:
        adj[pos[u]] |= 1 << pos[v]
        adj[pos[v]] |= 1 << pos[u]
    best = [0, 0]  # size, mask

    def expand(mask: int, size: int, cand: int) -> None:
        if size > best[0]:
            best[0], best[1] = size, mask
        while cand:
            if size + bin(cand).count("1") <= best[0]:
                return
            low = cand & -cand
            i = low.bit_length() - 1
            cand &= ~low
            expand(mask | low, size + 1, cand & adj[i])

    expand(0, 0, (1 << len(nodes)) - 1)
    return best[0], tuple(nodes[i] for i in range(len(nodes)) if best[1] >> i & 1)
