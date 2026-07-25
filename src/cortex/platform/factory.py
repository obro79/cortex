from __future__ import annotations

from cortex.config import Settings
from cortex.platform.cache import (
    CacheUnavailableError,
    EphemeralCacheService,
    InMemoryEphemeralCache,
    RedisCacheClient,
    RedisEphemeralCache,
)


def build_ephemeral_cache(
    settings: Settings, *, redis_client: RedisCacheClient | None = None
) -> EphemeralCacheService:
    if settings.cortex_cache_backend == "memory":
        return InMemoryEphemeralCache()
    if not settings.redis_url:
        raise CacheUnavailableError("REDIS_URL is required for Redis cache backend")
    if redis_client is None:
        raise CacheUnavailableError("Redis cache backend requires an injected client")
    return RedisEphemeralCache(redis_client)
