import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException


async def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = os.getenv("INTERNAL_API_KEY")
    if expected is None:
        return
    if x_internal_api_key is None or not secrets.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
