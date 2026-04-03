"""Redis-based sliding window rate limiting for auth endpoints."""

import time
import logging

import redis.asyncio as aioredis
from fastapi import Request, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(
    request: Request,
    action: str,
    max_attempts: int,
    window_seconds: int,
) -> None:
    """
    Sliding window rate limiter using Redis sorted sets.
    Raises 429 if the client IP exceeds max_attempts within window_seconds.
    Fails open (allows request) if Redis is unavailable.
    """
    try:
        r = await _get_redis()
        ip = _client_ip(request)
        key = f"ratelimit:{action}:{ip}"
        now = time.time()

        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        count = results[2]
        if count > max_attempts:
            earliest = await r.zrange(key, 0, 0)
            if earliest:
                remaining_secs = int(window_seconds - (now - float(earliest[0])))
            else:
                remaining_secs = window_seconds
            logger.warning("Rate limit hit: %s %s (%d/%d)", action, ip, count, max_attempts)
            raise HTTPException(
                status_code=429,
                detail=f"Too many attempts. Try again in {max(1, remaining_secs)} seconds.",
                headers={"Retry-After": str(max(1, remaining_secs))},
            )
    except HTTPException:
        raise
    except Exception:
        logger.warning("Rate limiter unavailable, failing open", exc_info=True)


async def rate_limit_login(request: Request) -> None:
    await check_rate_limit(request, "login", max_attempts=5, window_seconds=60)


async def rate_limit_register(request: Request) -> None:
    await check_rate_limit(request, "register", max_attempts=3, window_seconds=3600)
