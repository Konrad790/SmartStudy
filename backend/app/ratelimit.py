"""Simple per-user sliding-window rate limiter for expensive AI endpoints.

In-memory, so limits are per process. Use a shared store (e.g. Redis) when running multiple workers.
"""

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

from app.auth import get_current_user
from app.config import settings
from app.models import User

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque[float]] = defaultdict(deque)


def _check(user_id: str, limit: int, now: float | None = None) -> float | None:
    """Record a hit. Returns seconds to wait if the limit is exceeded, otherwise None."""
    current = time.monotonic() if now is None else now
    hits = _hits[user_id]
    while hits and current - hits[0] >= _WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= limit:
        return max(0.0, _WINDOW_SECONDS - (current - hits[0]))
    hits.append(current)
    return None


def reset_rate_limits() -> None:
    _hits.clear()


async def ai_rate_limit(user: User = Depends(get_current_user)) -> User:
    limit = settings.ai_rate_limit_per_minute
    if limit <= 0:
        return user
    retry_after = _check(user.id, limit)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Too many AI requests. Try again in {int(retry_after) + 1}s.",
                "service": "rate-limit",
                "code": "RATE_LIMITED",
            },
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
    return user
