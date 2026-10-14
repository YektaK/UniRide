"""Protected internal matrix-readiness endpoints (redacted, read-only)."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

# H5: one import root. The optimizer router and every strategy import
# ``utils.data_loader``; importing the same module through the
# ``optimizer_api.`` package path would create a second DataLoader class and a
# second singleton (and a second matrix cache with its own TTL).
from auth import require_internal_api_key
from utils.data_loader import DataLoader
from utils.matrix_repository import MatrixSnapshotError, MatrixStaleError

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["Internal Readiness"],
    dependencies=[Depends(require_internal_api_key)],
)

DEPOT_CODE = "D.Kampus"
MAX_STUDENT_LOCATION_CODES = 250
_FIXED_422 = {"detail": "Invalid readiness request"}
_SNAPSHOT_422 = {"detail": "Invalid matrix snapshot request"}
_SNAPSHOT_503 = {"detail": "Matrix snapshot unavailable"}
_SNAPSHOT_503_STALE = {"detail": "Matrix snapshot stale"}


def _parse_student_location_codes(body):
    if not isinstance(body, dict) or set(body) != {"student_location_codes"}:
        return None
    codes = body.get("student_location_codes")
    if (
        not isinstance(codes, list)
        or not codes
        or len(codes) > MAX_STUDENT_LOCATION_CODES
        or any(not isinstance(code, str) or not code.strip() for code in codes)
    ):
        return None
    return codes


# H6: the refresh is a blocking Supabase fetch and the repository lock may be
# held by another thread during a network refresh. Both helpers run in the
# threadpool so the event loop keeps serving other requests (e.g. /health).
# The handlers stay ``async def`` because they ``await request.json()``.
def _readiness_summary_sync(codes):
    loader = DataLoader.get_instance()
    loader.refresh()
    return loader.repository.readiness_summary(
        student_locations=codes,
        depot_code=DEPOT_CODE,
    )


def _matrix_snapshot_sync(codes):
    loader = DataLoader.get_instance()
    loader.refresh(force=True)
    return loader.repository.matrix_snapshot(
        student_locations=codes,
        depot_code=DEPOT_CODE,
    )


@router.get("/readiness")
async def readiness_handshake() -> dict:
    """Protected internal-key handshake for the local launcher.

    Status-only; it is not matrix or live-data evidence. The route never logs
    the request body or any submitted location codes.
    """
    return {"service": "optimizer", "internal": "ok"}


@router.post("/readiness/time-matrix")
async def time_matrix_readiness(request: Request) -> JSONResponse:
    """Redacted aggregate matrix-readiness summary for the requested locations.

    Accepts ``{"student_location_codes": [...]}`` with 1-250 nonblank entries.
    The depot is added to the required location set internally. Returns only
    counts and booleans; never submitted codes, missing arc pairs, keys, URLs,
    or provider errors.
    """
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - redacted boundary, never echo input
        return JSONResponse(status_code=422, content=_FIXED_422)

    codes = _parse_student_location_codes(body)
    if codes is None:
        return JSONResponse(status_code=422, content=_FIXED_422)

    summary = await run_in_threadpool(_readiness_summary_sync, codes)
    return JSONResponse(status_code=200, content=summary)


@router.post("/matrix-snapshot")
async def matrix_snapshot(request: Request) -> JSONResponse:
    """Return a protected, content-addressed snapshot of requested matrix arcs."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - fixed redacted boundary
        return JSONResponse(status_code=422, content=_SNAPSHOT_422)

    codes = _parse_student_location_codes(body)
    if codes is None:
        return JSONResponse(status_code=422, content=_SNAPSHOT_422)

    try:
        snapshot = await run_in_threadpool(_matrix_snapshot_sync, codes)
    except MatrixStaleError:
        return JSONResponse(status_code=503, content=_SNAPSHOT_503_STALE)
    except MatrixSnapshotError:
        return JSONResponse(status_code=503, content=_SNAPSHOT_503)
    except Exception:  # noqa: BLE001 - fixed redacted boundary
        return JSONResponse(status_code=503, content=_SNAPSHOT_503)
    return JSONResponse(status_code=200, content=snapshot)
