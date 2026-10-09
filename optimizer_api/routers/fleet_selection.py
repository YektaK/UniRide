"""Protected internal day-level fleet selection (heterogeneous fleet WP4).

``POST /api/v1/internal/fleet-selection``: pure computation over the request
body (no DB, no matrix).  Same internal-key protection as the other
``/api/v1/internal/*`` routes.  Errors are redacted: fixed bodies, nothing of
the submitted data is echoed.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError, model_validator

from auth import require_internal_api_key
from compute_policy import load_compute_policy
from uniride_core.planning.typed_day_selection import (
    DEFAULT_TIME_LIMIT_S,
    Option,
    Route,
    Wave,
    solve_day_selection,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["Internal Fleet Selection"],
    dependencies=[Depends(require_internal_api_key)],
)

_FIXED_422 = {"detail": "Invalid fleet selection request"}
_FIXED_503 = {"detail": "Fleet selection unavailable"}

# Request-shape ceilings (design: ~12 waves x 5 options x <= 6 routes).
MAX_WAVES = 30
MAX_OPTIONS_PER_WAVE = 6
MAX_ROUTES_PER_OPTION = 40
MAX_TOTAL_ROUTES = 1000
MAX_MINUTE_OF_DAY = 2880
MAX_COOLDOWN_MINUTES = 240
# Time scale (CX-01): interval endpoints and cooldowns are integers in units of
# 1/time_scale minute (1 = whole minutes, legacy default; 100 = centi-minutes,
# the precision of the matrix durations and step times).  ``minutes`` stays a
# real number of vehicle-minutes and is NOT scaled.  The core solver is
# integer-based and only ever sees the already-scaled integers.
MAX_TIME_SCALE = 100
_ID = r"^[A-Za-z0-9_.:-]{1,64}$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RouteIn(_Strict):
    start: StrictInt = Field(ge=0, le=MAX_MINUTE_OF_DAY * MAX_TIME_SCALE)
    end: StrictInt = Field(ge=1, le=MAX_MINUTE_OF_DAY * MAX_TIME_SCALE)
    minutes: float = Field(ge=0, le=MAX_MINUTE_OF_DAY, allow_inf_nan=False)
    large_ok: StrictBool = True
    car_ok: StrictBool = True

    @model_validator(mode="after")
    def _interval(self) -> "RouteIn":
        if self.end <= self.start:
            raise ValueError("end must exceed start")
        return self


class OptionIn(_Strict):
    option_id: str = Field(pattern=_ID)
    baseline: StrictBool = False
    routes: List[RouteIn] = Field(max_length=MAX_ROUTES_PER_OPTION)


class WaveIn(_Strict):
    wave_id: str = Field(pattern=_ID)
    options: List[OptionIn] = Field(min_length=1, max_length=MAX_OPTIONS_PER_WAVE)


class FleetSelectionRequest(_Strict):
    waves: List[WaveIn] = Field(min_length=1, max_length=MAX_WAVES)
    max_large: StrictInt = Field(ge=0, le=50)
    max_cars: Optional[StrictInt] = Field(default=None, ge=0, le=50)
    cooldown_large: Optional[StrictInt] = Field(default=None, ge=0, le=MAX_COOLDOWN_MINUTES * MAX_TIME_SCALE)
    cooldown_car: Optional[StrictInt] = Field(default=None, ge=0, le=MAX_COOLDOWN_MINUTES * MAX_TIME_SCALE)
    time_scale: StrictInt = Field(default=1, ge=1, le=MAX_TIME_SCALE)
    time_limit_seconds: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def _bounds(self) -> "FleetSelectionRequest":
        total = sum(len(o.routes) for w in self.waves for o in w.options)
        if total > MAX_TOTAL_ROUTES:
            raise ValueError("too many routes")
        if len({w.wave_id for w in self.waves}) != len(self.waves):
            raise ValueError("duplicate wave_id")
        for w in self.waves:
            if len({o.option_id for o in w.options}) != len(w.options):
                raise ValueError("duplicate option_id")
        # Bounds are real-minute limits expressed in the request's time scale.
        max_t = MAX_MINUTE_OF_DAY * self.time_scale
        max_cd = MAX_COOLDOWN_MINUTES * self.time_scale
        for w in self.waves:
            for o in w.options:
                for r in o.routes:
                    if r.start > max_t or r.end > max_t:
                        raise ValueError("interval outside the service-day bound")
        for cd in (self.cooldown_large, self.cooldown_car):
            if cd is not None and cd > max_cd:
                raise ValueError("cooldown above bound")
        return self

    def effective_cooldown(self, value: Optional[int]) -> int:
        """Cooldown in scaled units; the default is 10 real minutes."""
        return 10 * self.time_scale if value is None else value


def _policy_time_limit(requested: Optional[float]) -> Optional[float]:
    """Effective limit, or None when the request exceeds the compute policy."""
    ceiling = float(load_compute_policy().solver_seconds)
    if requested is None:
        return min(DEFAULT_TIME_LIMIT_S, ceiling)
    return requested if requested <= ceiling else None


def _compute(req: FleetSelectionRequest, limit: float) -> dict:
    waves = tuple(
        Wave(
            w.wave_id,
            tuple(
                Option(
                    o.option_id,
                    tuple(Route(r.start, r.end, r.minutes, r.large_ok, r.car_ok) for r in o.routes),
                    o.baseline,
                )
                for o in w.options
            ),
        )
        for w in req.waves
    )
    res = solve_day_selection(
        waves,
        req.max_large,
        cooldown_large=req.effective_cooldown(req.cooldown_large),
        cooldown_car=req.effective_cooldown(req.cooldown_car),
        max_cars=req.max_cars,
        time_limit_s=limit,
    )
    return {
        "status": res.status,
        "cars": res.cars,
        "large_peak": res.large_peak,
        "car_minutes": res.car_minutes,
        "total_minutes": res.total_minutes,
        "selection": res.selection,
        "diagnostics": res.diagnostics,
        "stats": res.stats,
    }


async def _read_body(request: Request):
    try:
        return await request.json()
    except Exception:  # noqa: BLE001 - redacted boundary
        return None


# Raw-body handler: every malformed body yields the fixed 422 (FastAPI's
# default 422 would echo the offending input).
@router.post("/fleet-selection")
async def fleet_selection_route(request: Request) -> JSONResponse:
    """Choose one option per wave minimising cars (see typed_day_selection)."""
    raw = await _read_body(request)
    try:
        req = FleetSelectionRequest.model_validate(raw)
    except (ValidationError, ValueError):
        return JSONResponse(status_code=422, content=_FIXED_422)
    limit = _policy_time_limit(req.time_limit_seconds)
    if limit is None:
        return JSONResponse(status_code=422, content=_FIXED_422)
    try:
        payload = await run_in_threadpool(_compute, req, limit)
    except Exception:  # noqa: BLE001 - fixed redacted boundary
        logger.error("fleet selection failed")
        return JSONResponse(status_code=503, content=_FIXED_503)
    return JSONResponse(status_code=200, content=payload)
