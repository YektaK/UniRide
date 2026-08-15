import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request


try:
    from optimizer_api.runtime_config import internal_api_key, internal_auth_disabled, tenant_keys
except ModuleNotFoundError:  # direct-module compatibility
    from runtime_config import internal_api_key, internal_auth_disabled, tenant_keys


async def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if internal_auth_disabled():
        return
    expected = internal_api_key()
    if expected is None or x_internal_api_key is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not secrets.compare_digest(
        x_internal_api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(status_code=403, detail="Forbidden")


def _resolve_tenant(x_internal_api_key: str | None) -> str | None:
    """Return the tenant id whose key matches, else None (constant-time)."""
    if x_internal_api_key is None:
        return None
    encoded = x_internal_api_key.encode("utf-8")
    for tenant_id, key in tenant_keys().items():
        if secrets.compare_digest(encoded, key.encode("utf-8")):
            return tenant_id
    return None


async def require_tenant_authorization(
    request: Request,
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Authorize a request as a configured tenant or the shared internal ops key.

    Sets ``request.state.tenant_id`` so downstream policies (e.g. the rate
    limiter) can act on tenant identity. Falls back to the shared internal key
    (``tenant_id="internal"``) for ops/admin access; anything else is 403.
    """
    if internal_auth_disabled():
        return
    tenant_id = _resolve_tenant(x_internal_api_key)
    if tenant_id is not None:
        request.state.tenant_id = tenant_id
        return
    await require_internal_api_key(x_internal_api_key)
    request.state.tenant_id = "internal"
