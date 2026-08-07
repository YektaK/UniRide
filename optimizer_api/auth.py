import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException


async def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Fail-closed internal API key gate for benchmark/CLI routes.

    A missing ``INTERNAL_API_KEY`` environment variable is always a deny:
    production deployments must configure the key or the app refuses to
    serve these routes.
    """
    expected = os.getenv("INTERNAL_API_KEY")
    if expected is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if x_internal_api_key is None or not secrets.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
