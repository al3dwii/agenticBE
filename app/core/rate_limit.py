import time
from fastapi import HTTPException
from app.memory.redis import get_redis
from app.core.config import settings

def _key(prefix: str, ident: str) -> str:
    return f"rl:{prefix}:{ident}"

async def _allow(prefix: str, ident: str, limit: int) -> bool:
    r = get_redis()
    key = _key(prefix, ident)
    # Fixed window (per 60s) for simplicity
    current = await r.incr(key)
    if current == 1:
        await r.expire(key, 60)
    return current <= limit

async def check_rate_limit(tenant_id: str, user_id: str | None = None):
    user_limit = int(getattr(settings, "RATE_LIMIT_USER_PER_MIN", 60))
    tenant_limit = int(getattr(settings, "RATE_LIMIT_TENANT_PER_MIN", 600))
    ok_tenant = await _allow("tenant", tenant_id, tenant_limit)
    if not ok_tenant:
        raise HTTPException(429, "Tenant rate limit exceeded")
    if user_id:
        ok_user = await _allow("user", user_id, user_limit)
        if not ok_user:
            raise HTTPException(429, "User rate limit exceeded")
    return True
