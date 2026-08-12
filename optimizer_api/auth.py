import secrets
from typing import Annotated

from fastapi import Header, HTTPException


try:
    from optimizer_api.runtime_config import internal_api_key, internal_auth_disabled
except ModuleNotFoundError:  # direct-module compatibility
    from runtime_config import internal_api_key, internal_auth_disabled


async def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if internal_auth_disabled():
        return
    expected = internal_api_key()
    if expected is None or x_internal_api_key is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not secrets.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
