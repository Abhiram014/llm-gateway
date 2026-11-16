import math

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request

from app.auth import require_api_key

# Runs inside Redis as ONE atomic step: read, refill, check, take a coin, save.
TOKEN_BUCKET_LUA = """
local key         = KEYS[1]
local capacity    = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])   -- coins per second
local cost        = tonumber(ARGV[3])

local t   = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

local saved  = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(saved[1])
local ts     = tonumber(saved[2])
if tokens == nil then
    tokens = capacity
    ts = now
end

tokens = math.min(capacity, tokens + math.max(0, now - ts) * refill_rate)

local allowed = 0
local retry_after = 0
if tokens >= cost then
    tokens = tokens - cost
    allowed = 1
else
    retry_after = (cost - tokens) / refill_rate
end

redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) + 1)

return {allowed, tostring(tokens), tostring(retry_after)}
"""


class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.script = redis_client.register_script(TOKEN_BUCKET_LUA)

    async def check(self, key_id: int, rpm_limit: int) -> tuple[bool, float, float]:
        """Returns (allowed, coins_left, seconds_until_retry)."""
        allowed, remaining, retry_after = await self.script(
            keys=[f"ratelimit:{key_id}"],
            args=[rpm_limit, rpm_limit / 60, 1],
        )
        return bool(allowed), float(remaining), float(retry_after)


async def enforce_rate_limit(
    request: Request,
    api_key: dict = Depends(require_api_key),
) -> dict:
    """Runs after the key check. Rejects with 429 if this key is over its limit."""
    limiter: RateLimiter = request.app.state.rate_limiter
    try:
        allowed, _, retry_after = await limiter.check(api_key["id"], api_key["rpm_limit"])
    except redis.RedisError:
        return api_key  # fail open: if Redis is down, don't block all traffic

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(math.ceil(retry_after))},
        )
    return api_key