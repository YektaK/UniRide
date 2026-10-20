"""Day oracle and tiny exhaustive MIP solver for the joint day model (tests only; WP-E11 J3, design 5.2).

Like ``brute_force.py`` this is deliberately independent of the code under test:

* ``brute_force_day_optimum`` never uses ``route_enumeration`` or ``day_instance``. Per wave it takes every set
  partition of the passengers, every order of every block (``itertools.permutations``), every vehicle type that admits
  the block and **every** feasible tour length, not only the shortest (so the dominance argument of design 2.2 is
  checked, not assumed). A day is one such route set per wave; its busy intervals are built on the centi-minute grid
  with the production rule ``end = max(start + 1, end * 100)``, a route outside minute 0..1440 is not allowed, and the
  peak of every type is a sweep at the interval starts. Objective: homogeneous ``(K, total minutes)``; typed (types[0]
  fixed with peak <= L, types[1] minimised) ``(S, total minutes, minimised-type minutes)``; ``None`` if no day exists.
* ``enumerate_stage_optimum`` solves one ``JointModel`` stage by depth-first enumeration of its integer variables with
  row-activity pruning. It refuses a model with more than ``MAX_ENUMERATION_COLUMNS`` integer column variables.
  Aggregation variables are substituted by the columns they sum, so they do not count.
* ``enumerate_lexicographic_optimum`` runs the stages in order and returns the same tuple as the oracle.

No external solver is imported.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from .day_instance import SERVICE_DAY_END_MINUTES, TIME_SCALE, DayInstance
from .day_joint import AGGREGATE, COLUMN, LINK, JointModel, build_joint_model

MAX_ENUMERATION_COLUMNS = 12


# ------------------------------------------------------------------ brute-force day oracle
@dataclass(frozen=True)
class DayOracleResult:
    objective: Optional[tuple]
    routes: tuple  # ((wave_id, type_id, tour), ...) of the first optimal route set


def _limits(t, wave):
    ride = t.ride_limit_minutes if t.ride_limit_minutes is not None else wave.max_ride_minutes
    tour = t.tour_limit_minutes if t.tour_limit_minutes is not None else wave.max_tour_minutes
    return ride, tour


def _block_tours(wave, types) -> Dict[tuple, frozenset]:
    """{(node subset, type_id): every distinct feasible tour} over every order of the subset."""
    n = len(wave.classes)
    out: Dict[tuple, frozenset] = {}
    for size in range(1, n + 1):
        for subset in itertools.combinations(range(1, n + 1), size):
            sw = sum(1 for v in subset if wave.classes[v - 1] == "Sw")
            so = size - sw
            orders = []
            for order in itertools.permutations(subset):
                path = (0, *order, 0)
                arcs = [wave.matrix[a][b] for a, b in zip(path, path[1:])]
                tour = sum(arcs)
                ride = tour - arcs[0] if wave.direction == "pickup" else tour - arcs[-1]
                orders.append((tour, ride))
            for t in types:
                if sw > t.sw_capacity or so > t.so_capacity or (t.total_capacity is not None and size > t.total_capacity):
                    continue
                ride_lim, tour_lim = _limits(t, wave)
                tours = frozenset(tour for tour, ride in orders if tour <= tour_lim and ride <= ride_lim)
                if tours:
                    out[(subset, t.type_id)] = tours
    return out


def _partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for part in _partitions(rest):
        yield [[first]] + part
        for i in range(len(part)):
            yield part[:i] + [[first] + part[i]] + part[i + 1:]


def _wave_route_sets(wave, types) -> list:
    """Every distinct multiset of ``(type_id, tour)`` routes that covers each passenger of the wave exactly once."""
    blocks = _block_tours(wave, types)
    sets = set()
    for part in _partitions(list(range(1, len(wave.classes) + 1))):
        choices = []
        for block in part:
            key = tuple(sorted(block))
            options = [(t.type_id, tour) for t in types for tour in sorted(blocks.get((key, t.type_id), ()))]
            if not options:
                break
            choices.append(options)
        else:
            for pick in itertools.product(*choices):
                sets.add(tuple(sorted(pick)))
    return sorted(sets)


def _peak(intervals) -> int:
    return max((sum(1 for s2, b2 in intervals if s2 <= s < b2) for s, _ in intervals), default=0)


def brute_force_day_optimum(waves: Sequence, types: Sequence, *, large_limit: Optional[int] = None) -> DayOracleResult:
    """Lexicographic day optimum over every route set of every wave (tiny days only)."""
    types = tuple(types)
    if len(types) not in (1, 2):
        raise ValueError("the oracle handles one type (homogeneous) or two (typed)")
    if len(types) == 2 and large_limit is None:
        raise ValueError("a typed day needs large_limit")
    cooldown = {t.type_id: t.cooldown_minutes for t in types}
    per_wave = [_wave_route_sets(w, types) for w in waves]
    best = None
    if any(not options for options in per_wave):
        return DayOracleResult(None, ())
    for combo in itertools.product(*per_wave):
        intervals = {t.type_id: [] for t in types}
        total = minimised = 0
        valid = True
        routes = []
        for wave, route_set in zip(waves, combo):
            for type_id, tour in route_set:
                start = wave.anchor_minutes - tour if wave.direction == "pickup" else wave.anchor_minutes
                end = wave.anchor_minutes if wave.direction == "pickup" else wave.anchor_minutes + tour
                if start < 0 or end > SERVICE_DAY_END_MINUTES:
                    valid = False
                    break
                s = start * TIME_SCALE
                e = max(s + 1, end * TIME_SCALE)
                intervals[type_id].append((s, e + cooldown[type_id] * TIME_SCALE))
                total += tour
                if len(types) == 2 and type_id == types[1].type_id:
                    minimised += tour
                routes.append((wave.wave_id, type_id, tour))
            if not valid:
                break
        if not valid:
            continue
        if len(types) == 1:
            key = (_peak(intervals[types[0].type_id]), total)
        else:
            if _peak(intervals[types[0].type_id]) > large_limit:
                continue
            key = (_peak(intervals[types[1].type_id]), total, minimised)
        if best is None or key < best[0]:
            best = (key, tuple(routes))
    return DayOracleResult(None, ()) if best is None else DayOracleResult(best[0], best[1])


# ------------------------------------------------------------------ tiny exhaustive MIP solver
@dataclass(frozen=True)
class EnumerationSolution:
    objective: int
    values: Dict[str, int]  # every variable of the model, aggregates included


def enumerate_stage_optimum(model: JointModel) -> Optional[EnumerationSolution]:
    """Minimum of one stage by exhaustive search; ``None`` if the stage is infeasible."""
    variables = model.variables
    if sum(1 for v in variables if v.kind == COLUMN) > MAX_ENUMERATION_COLUMNS:
        raise ValueError(f"enumeration is limited to {MAX_ENUMERATION_COLUMNS} integer column variables")
    members = {}  # aggregate variable index -> member variable indices (z = sum of members)
    for r in model.rows:
        if r.kind == LINK:
            (zi, zc), rest = r.terms[0], r.terms[1:]
            assert variables[zi].kind == AGGREGATE and zc == 1 and all(c == -1 for _, c in rest)
            members[zi] = [vi for vi, _ in rest]
    assert all(v.objective == 0 for v in variables if v.kind == AGGREGATE)
    free = [i for i, v in enumerate(variables) if v.kind != AGGREGATE]
    position = {vi: k for k, vi in enumerate(free)}
    rows = []
    for r in model.rows:
        if r.kind == LINK:
            continue
        acc: Dict[int, int] = {}
        for vi, c in r.terms:
            for vj in members.get(vi, [vi]):
                acc[vj] = acc.get(vj, 0) + c
        rows.append((r.sense, r.rhs, sorted((position[vj], c) for vj, c in acc.items() if c)))
    lows = [variables[i].lower for i in free]
    ups = [variables[i].upper for i in free]
    objective = [variables[i].objective for i in free]
    touching = [[] for _ in free]  # per free variable: (row index, coefficient)
    lo = [0] * len(rows)
    hi = [0] * len(rows)
    for ri, (_, _, terms) in enumerate(rows):
        for k, c in terms:
            touching[k].append((ri, c))
            lo[ri] += min(c * lows[k], c * ups[k])
            hi[ri] += max(c * lows[k], c * ups[k])

    def row_ok(ri):
        sense, rhs, _ = rows[ri]
        if sense == "E":
            return lo[ri] <= rhs <= hi[ri]
        if sense == "L":
            return lo[ri] <= rhs
        return hi[ri] >= rhs

    if not all(row_ok(ri) for ri in range(len(rows))):
        return None
    best = [None, None]  # objective, assignment
    assignment = [0] * len(free)

    def dfs(k, obj):
        if k == len(free):
            if best[0] is None or obj < best[0]:
                best[0], best[1] = obj, list(assignment)
            return
        for x in range(lows[k], ups[k] + 1):
            ok = True
            for ri, c in touching[k]:
                lo[ri] += c * x - min(c * lows[k], c * ups[k])
                hi[ri] += c * x - max(c * lows[k], c * ups[k])
            ok = all(row_ok(ri) for ri, _ in touching[k])
            if ok:
                assignment[k] = x
                dfs(k + 1, obj + objective[k] * x)
            for ri, c in touching[k]:
                lo[ri] -= c * x - min(c * lows[k], c * ups[k])
                hi[ri] -= c * x - max(c * lows[k], c * ups[k])

    dfs(0, 0)
    if best[0] is None:
        return None
    values = {variables[i].name: best[1][k] for k, i in enumerate(free)}
    for zi, ms in members.items():
        values[variables[zi].name] = sum(values[variables[vj].name] for vj in ms)
    return EnumerationSolution(best[0], values)


def enumerate_lexicographic_optimum(instance: DayInstance, *, large_limit: Optional[int] = None,
                                    aggregate: bool = False) -> Optional[tuple]:
    """Stage by stage optimum of the joint model by enumeration; the same tuple as ``brute_force_day_optimum``."""
    typed = len(instance.types) == 2
    kw = dict(large_limit=large_limit, aggregate=aggregate)
    s1 = enumerate_stage_optimum(build_joint_model(instance, stage=1, **kw))
    if s1 is None:
        return None
    fixed = {"peak": s1.objective}
    s2 = enumerate_stage_optimum(build_joint_model(instance, stage=2, fixed=dict(fixed), **kw))
    if s2 is None:
        raise AssertionError("stage 2 infeasible after a feasible stage 1")
    if not typed:
        return (s1.objective, s2.objective)
    fixed["total_minutes"] = s2.objective
    s3 = enumerate_stage_optimum(build_joint_model(instance, stage=3, fixed=dict(fixed), **kw))
    if s3 is None:
        raise AssertionError("stage 3 infeasible after a feasible stage 2")
    return (s1.objective, s2.objective, s3.objective)
