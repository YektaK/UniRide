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
