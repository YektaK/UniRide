"""Fixed-window in-memory rate limiter for the compute surface.

Keyed by client IP. Applies to the optimization router (the UniRide routing
compute surface) alongside the internal API key auth. Exceeding the window's
request budget returns HTTP 429 with ``Retry-After``.
"""

import threading
import time
from typing import Dict, List

from fastapi import HTTPException, Request

try:
    from optimizer_api.compute_policy import load_compute_policy
except ModuleNotFoundError:  # direct-module compatibility
    from compute_policy import load_compute_policy

_lock = threading.Lock()
# client key -> [window_start_monotonic, request_count_in_window]
_buckets: Dict[str, List[float]] = {}


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def require_rate_limit(request: Request) -> None:
    """Allow the request or raise 429 once the per-IP window budget is spent.

    ponytail: in-memory fixed-window limiter is per-process; scale out requires
    a shared store (e.g. Redis) when more than one API instance runs.
    """
    policy = load_compute_policy()
    limit = policy.rate_limit_requests
    window = policy.rate_limit_window_seconds
    key = _client_key(request)
    now = time.monotonic()

    with _lock:
        state = _buckets.get(key)
        if state is None or now - state[0] >= window:
            _buckets[key] = [now, 1.0]
            return
        state[1] += 1.0
        if state[1] > limit:
            retry_after = max(1, int(window - (now - state[0])) + 1)
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )