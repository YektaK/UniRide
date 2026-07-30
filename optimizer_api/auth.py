import os
import logging
from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

INTERNAL_API_KEY: str | None = os.getenv("INTERNAL_API_KEY")

async def require_internal_api_key(x_internal_api_key: str | None = Header(None)):
    if INTERNAL_API_KEY is None:
        return
    if x_internal_api_key != INTERNAL_API_KEY:
        logger.warning("Rejected request with invalid internal API key")
        raise HTTPException(status_code=403, detail="Forbidden")
