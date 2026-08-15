import json
import os


def optimizer_host() -> str:
    return os.getenv("OPTIMIZER_HOST", "127.0.0.1")


def allow_public_bind() -> bool:
    """Whether a non-loopback bind address is explicitly permitted."""
    return os.getenv("ALLOW_PUBLIC_BIND") == "1"


def is_loopback(host: str) -> bool:
    """True for loopback addresses that are safe to bind by default."""
    lowered = host.strip().lower()
    if lowered in {"localhost", "127.0.0.1", "::1"}:
        return True
    if lowered.startswith("127."):
        return True
    return False


def internal_auth_disabled() -> bool:
    """Explicit dev/test opt-out for the internal API key gate."""
    return os.getenv("UNIRIDE_DISABLE_AUTH") == "1"

def app_env() -> str:

    return os.getenv("APP_ENV", "development").strip().lower()


def internal_api_key() -> str | None:
    value = os.getenv("INTERNAL_API_KEY")
    return value if value else None


def tenant_keys() -> dict[str, str]:
    """Tenant id -> key mapping from UNIRIDE_TENANT_KEYS (JSON object).

    Empty when unset; every configured tenant key stays static for the
    process lifetime.
    """
    raw = os.getenv("UNIRIDE_TENANT_KEYS")
    if raw is None:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("UNIRIDE_TENANT_KEYS must be a JSON object mapping tenant id to key")
    invalid = {
        str(tenant_id)
        for tenant_id, key in parsed.items()
        if not isinstance(key, str) or not key
    }
    if invalid:
        raise ValueError(f"UNIRIDE_TENANT_KEYS has empty/non-string keys for tenants: {sorted(invalid)}")
    return {str(tenant_id): str(key) for tenant_id, key in parsed.items()}


def validate_runtime_configuration() -> None:
    disabled = internal_auth_disabled()
    if disabled and app_env() == "production":
        raise SystemExit("UNIRIDE_DISABLE_AUTH=1 is forbidden when APP_ENV=production")
    if not disabled and internal_api_key() is None:
        raise SystemExit(
            "INTERNAL_API_KEY is not set; configure it or use "
            "UNIRIDE_DISABLE_AUTH=1 outside production"
        )
    try:
        if os.getenv("UNIRIDE_TENANT_KEYS") is not None:
            tenant_keys()
    except ValueError as exc:
        raise SystemExit(str(exc))
    try:
        from optimizer_api.compute_policy import load_compute_policy
    except ModuleNotFoundError:  # direct `python optimizer_api/main.py` compatibility
        from compute_policy import load_compute_policy
    load_compute_policy()


def validate_bind_host(host: str) -> None:
    """Raise when binding outside loopback without an explicit opt-in.

    Enforces the Phase 0 trusted-network-boundary contract at startup:
    public binds require ``ALLOW_PUBLIC_BIND=1``.
    """
    if is_loopback(host):
        return
    if allow_public_bind():
        return
    raise SystemExit(
        f"Refusing to bind API to non-loopback host {host!r} without "
        "ALLOW_PUBLIC_BIND=1. The optimizer API must stay on a trusted "
        "network boundary."
    )
