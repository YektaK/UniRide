"""Solver-neutral joint day model and canonical MPS writer (WP-E11 J3, design JOINT_DAY_MODEL_DESIGN.md 2.2, 2.4).

``build_joint_model`` turns a ready ``DayInstance`` (J1) into one sparse MIP per lexicographic stage:

* ``lambda_c`` integer, ``0 <= lambda_c <= u_c`` with ``u_c = min over items i with a_ci > 0 of floor(n_wi / a_ci)``
  (DECISION_LOG E02: one column can be needed more than once, every copy has the same interval).
* cover rows: ``sum_c a_ci lambda_c = n_wi`` for every wave and item.
* concurrency rows, one per type and per interval start ``p`` (centi-minutes, taken from ``DayColumn.interval``,
  never from ``busy_end``): ``sum_{c: type t, start_c <= p < busy_end_c} lambda_c <= Cap_t`` with ``Cap = K`` for the
  homogeneous fleet, ``Cap_large = L`` (constant) and ``Cap_minimised = S`` for a typed fleet.
* optional ``S <= max_cars``.
* optional duration aggregation: ``z_{w,t,tau} = sum lambda_c`` over the columns of one (wave, type, tour); they share
  one interval, so the concurrency rows are written over ``z`` and the model is unchanged.

Stages (design 1.3, owner decision E14 Q2, H06-consistent): homogeneous 1 ``min K``, 2 ``min total minutes`` with K
fixed; typed 1 ``min S``, 2 ``min total minutes`` with S fixed, 3 ``min car minutes`` with S and total minutes fixed.
Earlier stage values are passed in ``fixed`` as ``{"peak": value, "total_minutes": value}``.

Row and column order is fixed by construction (waves, columns, types and points in ascending order), so two builds of
one cell give the same bytes. ``JointModel.to_mps`` writes canonical free-format MPS (ascii, ``\\n``, integers only);
its sha256 is ``mps_sha256``. Pure Python: no solver import, no amplpy, nothing from ``academic_benchmark``.
"""
from __future__ import annotations

import hashlib
from bisect import bisect_left
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from .day_instance import READY, TIME_SCALE, DayInstance

COLUMN, AGGREGATE, PEAK = "column", "aggregate", "peak"
COVER, LINK, CONCURRENCY, FIX_TOTAL = "cover", "link", "concurrency", "fix_total"


@dataclass(frozen=True)
class MipVariable:
    name: str
    lower: int
    upper: int
    objective: int
    kind: str  # COLUMN, AGGREGATE or PEAK (all integer)
    type_id: Optional[str] = None
    ref: Optional[tuple] = None  # COLUMN: (wave index, column_index); AGGREGATE: (wave index, tour)
    tour: Optional[int] = None


@dataclass(frozen=True)
class MipRow:
    name: str
    sense: str  # "E", "L" or "G"
    rhs: int
    terms: Tuple[Tuple[int, int], ...]  # (variable index, integer coefficient), ascending variable index
    kind: str
    type_id: Optional[str] = None


@dataclass(frozen=True)
class JointModel:
    name: str
    mode: str  # "homogeneous" or "typed"
    stage: int
    objective_name: str
    variables: Tuple[MipVariable, ...]
    rows: Tuple[MipRow, ...]
    counts: Mapping[str, int]

    def to_mps(self) -> bytes:
        return _mps_bytes(self)

    @property
    def mps_sha256(self) -> str:
        return hashlib.sha256(self.to_mps()).hexdigest()


def _column_upper_bound(day_wave, column) -> int:
    """E02: the number of copies of a column that the wave's multiplicities allow."""
    return min(day_wave.items[i].multiplicity // a for i, a in enumerate(column.multiplicity) if a > 0)


def _require(fixed: Mapping, key: str, stage: int) -> int:
    value = fixed.get(key) if fixed else None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"stage {stage} needs the integer stage value {key!r} in `fixed`")
    return value


def build_joint_model(instance: DayInstance, *, stage: int = 1, large_limit: Optional[int] = None,
                      fixed: Optional[Mapping] = None, aggregate: bool = False, max_cars: Optional[int] = None,
                      fixed_type: Optional[str] = None, minimised_type: Optional[str] = None,
                      time_scale: int = TIME_SCALE) -> JointModel:
    """One stage of the joint day MIP for a ready cell (see the module docstring)."""
    if instance.status != READY:
        raise ValueError(f"only a ready day instance is modelled (status {instance.status!r})")
    types = instance.types
    if len(types) == 1:
        mode = "homogeneous"
        if stage not in (1, 2):
            raise ValueError("a homogeneous day has stages 1 and 2")
        if large_limit is not None or max_cars is not None:
            raise ValueError("large_limit and max_cars belong to a typed fleet")
    elif len(types) == 2:
        mode = "typed"
        if stage not in (1, 2, 3):
            raise ValueError("a typed day has stages 1, 2 and 3")
        if isinstance(large_limit, bool) or not isinstance(large_limit, int) or large_limit < 0:
            raise ValueError("a typed day needs the integer large_limit L >= 0")
    else:
        raise ValueError("a day instance has one type (homogeneous) or two (typed)")
    ids = [t.type_id for t in types]
    fixed_id = fixed_type or ids[0]
    minimised_id = minimised_type or ids[-1]
    if mode == "typed" and (fixed_id == minimised_id or {fixed_id, minimised_id} != set(ids)):
        raise ValueError(f"fixed type {fixed_id!r} and minimised type {minimised_id!r} must be the two types {ids}")
    peak_id = ids[0] if mode == "homogeneous" else minimised_id
    legs = sum(it.multiplicity for w in instance.waves for it in w.items)
    peak_upper = legs if max_cars is None else min(legs, max_cars)
    fixed = dict(fixed or {})
    peak_value = _require(fixed, "peak", stage) if stage >= 2 else None
    total_value = _require(fixed, "total_minutes", stage) if stage == 3 else None

    variables: list = []
    column_var = {}  # (wave index, column_index) -> variable index
    for wi, dw in enumerate(instance.waves):
        for col in dw.columns:
            if stage == 1:
                obj = 0
            elif stage == 2 or (stage == 3 and col.type_id == minimised_id):
                obj = col.tour
            else:
                obj = 0
            column_var[(wi, col.column_index)] = len(variables)
            variables.append(MipVariable(f"x{wi}_{col.column_index}", 0, _column_upper_bound(dw, col), obj, COLUMN,
                                         col.type_id, (wi, col.column_index), col.tour))
    n_columns = len(variables)

    rows: list = []
    # cover rows
    for wi, dw in enumerate(instance.waves):
        terms_by_item = [[] for _ in dw.items]
        for col in dw.columns:
            vi = column_var[(wi, col.column_index)]
            for ii, a in enumerate(col.multiplicity):
                if a:
                    terms_by_item[ii].append((vi, a))
        for ii, it in enumerate(dw.items):
            rows.append(MipRow(f"cv{wi}_{ii}", "E", it.multiplicity, tuple(terms_by_item[ii]), COVER))

    # duration aggregation: one z per (wave, type, tour) group with more than one column
    group_var = {}  # (wave index, type index, tour) -> variable index of z, or of the single column
    if aggregate:
        groups: dict = {}
        for wi, dw in enumerate(instance.waves):
            for col in dw.columns:
                groups.setdefault((wi, col.type_index, col.tour), []).append(col)
        for key in sorted(groups):
            wi, ti, tour = key
            members = groups[key]
            if len(members) == 1:
                group_var[key] = column_var[(wi, members[0].column_index)]
                continue
            zi = len(variables)
            upper = sum(variables[column_var[(wi, c.column_index)]].upper for c in members)
            variables.append(MipVariable(f"z{wi}_{ti}_{tour}", 0, upper, 0, AGGREGATE, types[ti].type_id, (wi, tour), tour))
            group_var[key] = zi
            terms = [(zi, 1)] + [(column_var[(wi, c.column_index)], -1) for c in members]
            rows.append(MipRow(f"ag{wi}_{ti}_{tour}", "E", 0, tuple(terms), LINK))

    # peak variable (K or S)
    peak_index = len(variables)
    if stage == 1:
        variables.append(MipVariable("peak", 0, peak_upper, 1, PEAK, peak_id))
    else:  # fixed by the earlier stage
        variables.append(MipVariable("peak", peak_value, peak_value, 0, PEAK, peak_id))

    # concurrency rows at the interval starts of each type (centi grid, DayColumn.interval)
    for ti, t in enumerate(types):
        entries = []  # (start, busy_end, variable index), in construction order
        seen = set()
        for wi, dw in enumerate(instance.waves):
            for col in dw.columns:
                if col.type_index != ti:
                    continue
                s, _, be = col.interval(time_scale)
                if aggregate:
                    key = (wi, ti, col.tour)
                    vi = group_var[key]
                    if vi in seen:
                        continue
                    seen.add(vi)
                else:
                    vi = column_var[(wi, col.column_index)]
                entries.append((s, be, vi))
        points = sorted({s for s, _, _ in entries})
        row_terms = [[] for _ in points]
        for s, be, vi in entries:
            for pi in range(bisect_left(points, s), bisect_left(points, be)):
                row_terms[pi].append((vi, 1))
        for pi in range(len(points)):
            terms = sorted(row_terms[pi])
            if mode == "typed" and t.type_id == fixed_id:
                rows.append(MipRow(f"cc{ti}_{pi}", "L", large_limit, tuple(terms), CONCURRENCY, t.type_id))
            else:
                rows.append(MipRow(f"cc{ti}_{pi}", "L", 0, tuple(terms) + ((peak_index, -1),), CONCURRENCY, t.type_id))

    if stage == 3:
        terms = tuple((vi, v.tour) for vi, v in enumerate(variables[:n_columns]) if v.tour)
        rows.append(MipRow("fixtot", "E", total_value, terms, FIX_TOTAL))

    objective_name = {1: "min_peak", 2: "min_total_minutes", 3: "min_car_minutes"}[stage]
    counts = {
        "column_variables": n_columns,
        "aggregate_variables": sum(1 for v in variables if v.kind == AGGREGATE),
        "peak_variables": 1,
        "cover_rows": sum(1 for r in rows if r.kind == COVER),
        "link_rows": sum(1 for r in rows if r.kind == LINK),
        "concurrency_rows": sum(1 for r in rows if r.kind == CONCURRENCY),
        "fix_total_rows": sum(1 for r in rows if r.kind == FIX_TOTAL),
        "concurrency_nonzeros": sum(len(r.terms) for r in rows if r.kind == CONCURRENCY),
        "nonzeros": sum(len(r.terms) for r in rows),
    }
    name = f"day_{instance.service_date}_R{instance.ride}_{mode}_stage{stage}"
    if mode == "typed":
        name += f"_L{large_limit}"
    return JointModel(name, mode, stage, objective_name, tuple(variables), tuple(rows), counts)


def selection_from_values(model: JointModel, values: Mapping[str, int]) -> Tuple[Tuple[int, int, int], ...]:
    """``(wave index, column_index, copies)`` for every column variable with a positive value, in model order."""
    return tuple((v.ref[0], v.ref[1], values[v.name]) for v in model.variables
                 if v.kind == COLUMN and values[v.name] > 0)


def _mps_bytes(model: JointModel) -> bytes:
    """Canonical free-format MPS: ascii, ``\\n``, integer column section, explicit bounds on every variable."""
    entries = [[] for _ in model.variables]  # per variable: (row name, coefficient), in row order
    for r in model.rows:
        for vi, coef in r.terms:
            entries[vi].append((r.name, coef))
    lines = [f"NAME {model.name}", "ROWS", " N obj"]
    lines += [f" {r.sense} {r.name}" for r in model.rows]
    lines.append("COLUMNS")
    lines.append("    MARKER 'MARKER' 'INTORG'")
    for v, ent in zip(model.variables, entries):
        items = ([("obj", v.objective)] if v.objective else []) + ent
        if not items:
            items = [("obj", 0)]
        for name, coef in items:
            lines.append(f"    {v.name} {name} {coef}")
    lines.append("    MARKER 'MARKER' 'INTEND'")
    lines.append("RHS")
    lines += [f"    RHS {r.name} {r.rhs}" for r in model.rows if r.rhs]
    lines.append("BOUNDS")
    for v in model.variables:
        if v.lower == v.upper:
            lines.append(f" FX BND {v.name} {v.lower}")
        else:
            if v.lower:
                lines.append(f" LO BND {v.name} {v.lower}")
            lines.append(f" UP BND {v.name} {v.upper}")
    lines.append("ENDATA")
    return ("\n".join(lines) + "\n").encode("ascii")
