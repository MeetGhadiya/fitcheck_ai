"""
FitCheck AI — Rate Limiter
Redis-backed server-side rate limiting (cannot be bypassed by users)
"""

import redis.asyncio as aioredis
from fastapi import HTTPException, Request
from datetime import datetime
from app.core.config import settings
from app.models.user import UserPlan
import logging

logger = logging.getLogger("fitcheck.ratelimit")

# ── Redis client ──────────────────────────────────────
_redis: aioredis.Redis = None
_redis_error = False  # Track if Redis is unavailable

async def get_redis() -> aioredis.Redis:
    global _redis, _redis_error
    
    # If we already know Redis is unavailable, return None
    if _redis_error:
        return None
    
    if _redis is None:
        try:
            _redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            await _redis.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}) — rate limiting disabled")
            _redis_error = True
            return None
    
    return _redis


# ── Try-on rate limiter ───────────────────────────────
async def check_tryon_limit(user_id: str, plan: UserPlan, request: Request):
    """
    Enforces daily try-on limits per plan.
    - Free:     3  per day
    - Pro:      999 per day (effectively unlimited)
    - Business: unlimited (API key quota handled separately)
    Keyed by user_id + UTC date → resets at midnight UTC.
    """
    if plan in (UserPlan.PRO, UserPlan.BUSINESS):
        return  # no limit

    redis = await get_redis()
    if redis is None:
        logger.info(f"Redis unavailable — skipping rate limit check for user {user_id}")
        return  # Allow request if Redis is down
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"tryon_limit:{user_id}:{today}"

    count = await redis.get(key)
    count = int(count) if count else 0

    limit = settings.FREE_DAILY_TRYON_LIMIT

    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": f"Free plan allows {limit} try-ons per day. Upgrade for unlimited access.",
                "limit": limit,
                "used": count,
                "resets_at": f"{today}T24:00:00Z",
            },
        )


async def increment_tryon_count(user_id: str):
    redis = await get_redis()
    if redis is None:
        return  # Skip if Redis unavailable
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"tryon_limit:{user_id}:{today}"
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expireat(key, _midnight_timestamp())
    await pipe.execute()


def _midnight_timestamp() -> int:
    from datetime import timezone
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return int(midnight.timestamp())


async def get_tryon_usage(user_id: str) -> dict:
    redis = await get_redis()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"tryon_limit:{user_id}:{today}"
    
    if redis is None:
        # Return default if Redis unavailable
        return {
            "used": 0,
            "limit": settings.FREE_DAILY_TRYON_LIMIT,
            "date": today,
            "redis_unavailable": True,
        }
    
    count = await redis.get(key)
    return {
        "used": int(count) if count else 0,
        "limit": settings.FREE_DAILY_TRYON_LIMIT,
        "date": today,
    }


# ── API rate limiter (B2B) ────────────────────────────
async def check_api_rate_limit(api_key: str):
    """60 requests/minute per API key."""
    redis = await get_redis()
    if redis is None:
        return  # Skip rate limiting if Redis unavailable
    
    now = datetime.utcnow()
    window = now.strftime("%Y-%m-%dT%H:%M")
    key = f"api_rate:{api_key}:{window}"

    count = await redis.incr(key)
    await redis.expire(key, 90)  # expire after 90s

    if count > 60:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": "API rate limit: 60 requests/minute",
                "retry_after": 60,
            },
        )


# ── Guest IP limiter ──────────────────────────────────
async def check_guest_ip_limit(request: Request):
    """3 try-ons per day per IP for unauthenticated users."""
    redis = await get_redis()
    if redis is None:
        return  # Skip rate limiting if Redis unavailable
    
    ip = request.client.host
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"guest_limit:{ip}:{today}"

    count = await redis.get(key)
    count = int(count) if count else 0

    if count >= settings.FREE_DAILY_TRYON_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "guest_limit_reached",
                "message": "Create a free account to continue.",
                "limit": settings.FREE_DAILY_TRYON_LIMIT,
            },
        )

    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expireat(key, _midnight_timestamp())
    await pipe.execute()
