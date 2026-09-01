"""
Simple in-memory fixed-window rate limiter for auth endpoints.

In-memory is safe here because this app is deliberately run single-worker
(see docker-compose.yml — market_cache/schedulers are already in-process
state that would fragment across multiple workers, so there's no existing
multi-worker deployment path to break). A multi-worker deployment would
need a shared store (e.g. Redis) instead of this module-level dict.

Keyed by client IP rather than by the submitted email/username, so an
attacker can't lock a real user out of their own account just by
repeatedly POSTing that user's email with wrong passwords.
"""

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException, Request, status

_hits: Dict[str, List[float]] = defaultdict(list)


def reset() -> None:
    """Test-only: clear all rate-limit state between test runs."""
    _hits.clear()


def rate_limiter(max_requests: int, window_seconds: int):
    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client_ip}"
        now = time.time()
        window_start = now - window_seconds

        hits = _hits[key]
        while hits and hits[0] < window_start:
            hits.pop(0)

        if len(hits) >= max_requests:
            retry_after = max(1, int(hits[0] + window_seconds - now) + 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)

    return dependency
