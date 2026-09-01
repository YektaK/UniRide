"""Protected internal matrix-readiness endpoints (redacted, read-only)."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

try:
    from optimizer_api.auth import require_internal_api_key
    from optimizer_api.utils.data_loader import DataLoader
except ModuleNotFoundError:  # direct-module compatibility
    from auth import require_internal_api_key
    from utils.data_loader import DataLoader

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["Internal Readiness"],
    dependencies=[Depends(require_internal_api_key)],
)

DEPOT_CODE = "D.Kampus"
MAX_STUDENT_LOCATION_CODES = 250
_FIXED_422 = {"detail": "Invalid readiness request"}


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

    if not isinstance(body, dict):
        return JSONResponse(status_code=422, content=_FIXED_422)

    codes = body.get("student_location_codes")
    if set(body) != {"student_location_codes"}:
        return JSONResponse(status_code=422, content=_FIXED_422)
    if (
        not isinstance(codes, list)
        or not codes
        or len(codes) > MAX_STUDENT_LOCATION_CODES
        or any(not isinstance(code, str) or not code.strip() for code in codes)
    ):
        return JSONResponse(status_code=422, content=_FIXED_422)

    loader = DataLoader.get_instance()
    loader.refresh()
    summary = loader.repository.readiness_summary(
        student_locations=codes,
        depot_code=DEPOT_CODE,
    )
    return JSONResponse(status_code=200, content=summary)