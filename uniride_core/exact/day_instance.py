"""Day instance of the joint day model (WP-E11 J1, design JOINT_DAY_MODEL_DESIGN.md 1.2, 2.1, 2.3).

One cell = the waves of one service date for one ride limit R and a fixed vehicle-type set. For every wave the
complete ``enumerate_wave`` output gives the columns (one per feasible (location, class) multiset and type). Each
column is anchored in time like the production day selection and carries its busy interval; columns whose route
would start before minute 0 or end after minute 1440 are dropped (service-day filter).

* Anchoring (design 1.2 rule 2; ``scripts/run_exact_union_day.py`` ``exact_menu_option``): a pickup route ends at the
  wave anchor and starts ``tour`` minutes before; a dropoff route starts at the anchor and ends ``tour`` minutes later.
* Busy interval (rule 3): ``[start, end + cooldown_t)`` with the cooldown of the column's own type, half open.
* Grid (rule 5): production builds intervals in centi-minutes. All arcs are integers, so every endpoint is an integer
  minute and ``DayColumn.interval(time_scale)`` is the exact scaled view, with the production rule
  ``end = max(start + 1, end * scale)``.
* A cell is modelled only if every wave enumerated with status ``complete``; otherwise ``status`` is
  ``not_run_enumeration_cap`` (no compact fallback, DECISION_LOG E11) and no columns are returned.

Pure Python, no solver import, no amplpy. Imports nothing from ``academic_benchmark`` or ``optimizer_api``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from .route_enumeration import EnumerationResult, enumerate_wave

READY = "ready"
NOT_RUN_ENUMERATION_CAP = "not_run_enumeration_cap"
SERVICE_DAY_END_MINUTES = 24 * 60  # dudullu-preview.ts SERVICE_DAY_END_MINUTES; run_exact_union_day.py:68
TIME_SCALE = 100  # production grid (fleet_selection_request.TIME_SCALE)


@dataclass(frozen=True)
class DayColumn:
    """One column of one wave with its place on the day's time axis (integer minutes)."""

    wave_id: str
    column_index: int  # position in ``EnumerationResult.columns`` of its wave
    type_id: str
    type_index: int  # position of the type in the cell's type tuple
    multiplicity: tuple  # a_{c,item} over the wave's items
    stop_order: tuple  # item indices in visiting order
    tour: int
    ride: int
    start: int
    end: int
    cooldown: int  # cooldown of the column's type, minutes
    sw_count: int
    so_count: int

    @property
    def busy_end(self) -> int:
        """Exclusive end of the busy interval ``[start, busy_end)``, minutes."""
        return self.end + self.cooldown

    def interval(self, time_scale: int = TIME_SCALE) -> Tuple[int, int, int]:
        """``(start, end, busy_end)`` on the 1/``time_scale``-minute grid, as ``build_selection_request`` builds them."""
        start = self.start * time_scale
        end = max(start + 1, self.end * time_scale)
        return start, end, end + self.cooldown * time_scale


@dataclass(frozen=True)
class DayWave:
    wave: object  # WaveInstance
    enumeration: EnumerationResult
    columns: Tuple[DayColumn, ...]  # after the service-day filter; empty unless the cell is ready
    enumerated_columns: int  # ``EnumerationResult.column_count`` (before the filter; partial if the cap fired)
    filtered_columns: int  # dropped by the service-day filter

    @property
    def wave_id(self) -> str:
        return self.wave.wave_id

    @property
    def enumeration_status(self) -> str:
        return self.enumeration.status

    @property
    def items(self) -> tuple:
        """(location, class, multiplicity) items ``i`` with ``n_{w,i}``; ``DayColumn.multiplicity`` is over these."""
        return self.enumeration.items


@dataclass(frozen=True)
class BlockingWave:
    wave_id: str
    enumeration_status: str
    cap_fired: Optional[str]


@dataclass(frozen=True)
class DayInstance:
    status: str  # READY or NOT_RUN_ENUMERATION_CAP
    service_date: str
    ride: int  # R of every wave
    tour: int  # T of every wave
    types: tuple  # VehicleTypeSpec, in the order of ``DayColumn.type_index``
    waves: Tuple[DayWave, ...]  # in the order given
    blocking: Tuple[BlockingWave, ...]  # waves that did not enumerate completely

    @property
    def enumerated_columns(self) -> int:
        return sum(w.enumerated_columns for w in self.waves)

    @property
    def columns_total(self) -> int:
        return sum(len(w.columns) for w in self.waves)

    @property
    def filtered_total(self) -> int:
        return sum(w.filtered_columns for w in self.waves)


def _validated(waves: Sequence, types: Sequence, service_date: Optional[str]) -> tuple:
    waves = tuple(waves)
    types = tuple(types)
    if not waves:
        raise ValueError("a day instance needs at least one wave")
    if not types:
        raise ValueError("a day instance needs at least one vehicle type")
    dates = {w.service_date for w in waves}
    if len(dates) != 1 or (service_date is not None and dates != {service_date}):
        raise ValueError(f"waves must all have one service date{'' if service_date is None else f' {service_date}'}, got {sorted(dates)}")
    rides = {w.max_ride_minutes for w in waves}
    tours = {w.max_tour_minutes for w in waves}
    if len(rides) != 1 or len(tours) != 1:
        raise ValueError(f"waves must share one ride limit and one tour limit, got ride {sorted(rides)}, tour {sorted(tours)}")
    ids = [w.wave_id for w in waves]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate wave id in {ids}")
    return waves, types, dates.pop(), rides.pop(), tours.pop()


def _day_columns(wave, enumeration: EnumerationResult, types: tuple, filter_service_day: bool) -> tuple:
    index = {t.type_id: i for i, t in enumerate(types)}
    is_sw = [1 if it.cls == "Sw" else 0 for it in enumeration.items]
    pickup = wave.direction == "pickup"
    kept, filtered = [], 0
    for ci, col in enumerate(enumeration.columns):
        start = wave.anchor_minutes - col.tour if pickup else wave.anchor_minutes
        end = wave.anchor_minutes if pickup else wave.anchor_minutes + col.tour
        if filter_service_day and not (start >= 0 and end <= SERVICE_DAY_END_MINUTES):
            filtered += 1
            continue
        sw = sum(m for m, s in zip(col.multiplicity, is_sw) if s)
        ti = index[col.type_id]
        kept.append(DayColumn(wave.wave_id, ci, col.type_id, ti, col.multiplicity, col.stop_order, col.tour, col.ride,
                              start, end, types[ti].cooldown_minutes, sw, sum(col.multiplicity) - sw))
    return tuple(kept), filtered


def build_day_instance(waves: Sequence, types: Sequence, *, service_date: Optional[str] = None,
                       filter_service_day: bool = True, **enumeration_kwargs) -> DayInstance:
    """The cell of ``waves`` (``WaveInstance``s of one date, one R) for ``types`` (``VehicleTypeSpec``s).

    ``enumeration_kwargs`` go to ``enumerate_wave`` (``column_cap``, ``label_cap``, ``wall_clock_limit``, ``clock``).
    If any wave does not enumerate completely the instance has status ``not_run_enumeration_cap``, lists the
    offending waves in ``blocking`` and carries no columns. ``filter_service_day=False`` keeps columns outside
    minute 0..1440 (measurement only; ``DayColumn.interval`` is then not the production interval for them, the
    production builder clamps a negative start to 0).
    """
    waves, types, date, ride, tour = _validated(waves, types, service_date)
    enumerations = [enumerate_wave(w, types, **enumeration_kwargs) for w in waves]
    blocking = tuple(BlockingWave(w.wave_id, e.status, e.cap_fired)
                     for w, e in zip(waves, enumerations) if e.status != "complete")
    day_waves = []
    for w, e in zip(waves, enumerations):
        if blocking:
            cols, filtered = (), 0
        else:
            cols, filtered = _day_columns(w, e, types, filter_service_day)
        day_waves.append(DayWave(w, e, cols, e.column_count, filtered))
    return DayInstance(NOT_RUN_ENUMERATION_CAP if blocking else READY, date, ride, tour, types, tuple(day_waves),
                       blocking)
