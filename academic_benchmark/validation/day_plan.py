"""Independent day-plan checker (WP-E11 J6): RED-PHASE STUB. Every check is missing, so a plan is always accepted."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class TypeSpec:
    type_id: str
    sw_capacity: int
    so_capacity: int
    cooldown_minutes: int
    total_capacity: Optional[int] = None
    ride_limit: Optional[int] = None
    tour_limit: Optional[int] = None


@dataclass(frozen=True)
class Wave:
    wave_id: str
    direction: str
    anchor_minutes: int
    occurrences: Mapping[str, str]  # occurrence id -> location code


@dataclass(frozen=True)
class Route:
    wave_id: str
    type_id: str
    stops: Tuple[str, ...]  # occurrence ids in visiting order
    claimed_sw: Optional[int] = None
    claimed_so: Optional[int] = None
    claimed_minutes: Optional[int] = None


@dataclass(frozen=True)
class DayClaims:
    route_count: Optional[int] = None
    total_minutes: Optional[int] = None
    minutes_by_type: Mapping[str, int] = field(default_factory=dict)
    peaks: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Violation:
    code: str
    where: str
    message: str


@dataclass(frozen=True)
class DayPlanReport:
    violations: Tuple[Violation, ...] = ()
    peaks_minutes: Mapping[str, int] = field(default_factory=dict)
    peaks_centi: Mapping[str, int] = field(default_factory=dict)
    total_minutes: int = 0
    minutes_by_type: Mapping[str, int] = field(default_factory=dict)
    route_count: int = 0
    route_metrics: Tuple[Mapping[str, Any], ...] = ()

    @property
    def ok(self) -> bool:
        return not self.violations

    @property
    def codes(self) -> Tuple[str, ...]:
        return tuple(v.code for v in self.violations)


def plan_from_single_type_response(response, matrix_doc, *, type_spec, depot):
    raise NotImplementedError


def check_day_plan(*, waves: Sequence[Wave], routes: Sequence[Route], types: Mapping[str, TypeSpec],
                   arcs: Mapping[Tuple[str, str], Any], depot: str, tour_limit: int, ride_limit: int,
                   peak_caps: Optional[Mapping[str, int]] = None, claims: Optional[DayClaims] = None,
                   time_scale: int = 100, service_day_end: int = 1440) -> DayPlanReport:
    return DayPlanReport()
