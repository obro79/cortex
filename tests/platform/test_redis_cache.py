from __future__ import annotations

from dataclasses import dataclass

import pytest

from cortex.config import Settings
from cortex.platform import (
    CacheCounterError,
    CacheUnavailableError,
    InMemoryEphemeralCache,
    RedisEphemeralCache,
    build_ephemeral_cache,
)


@dataclass
class FakeRedisRecord:
    value: str
    ttl_seconds: int | None


class FakeRedisClient:
    def __init__(self) -> None:
        self.records: dict[str, FakeRedisRecord] = {}
        self.fail: bool = False

    def get(self, name: str) -> str | bytes | None:
        self._maybe_fail()
        record = self.records.get(name)
        if record is None:
            return None
        return record.value

    def set(
        self,
        name: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        self._maybe_fail()
        if nx and name in self.records:
            return False
        self.records[name] = FakeRedisRecord(value=value, ttl_seconds=ex)
        return True

    def incrby(self, name: str, amount: int = 1) -> int:
        self._maybe_fail()
        record = self.records.get(name)
        current = 0 if record is None else int(record.value)
        updated = current + amount
        ttl_seconds = None if record is None else record.ttl_seconds
        self.records[name] = FakeRedisRecord(
            value=str(updated), ttl_seconds=ttl_seconds
        )
        return updated

    def expire(self, name: str, time: int) -> bool:
        self._maybe_fail()
        record = self.records.get(name)
        if record is None:
            return False
        self.records[name] = FakeRedisRecord(value=record.value, ttl_seconds=time)
        return True

    def delete(self, name: str) -> int:
        self._maybe_fail()
        return 1 if self.records.pop(name, None) is not None else 0

    def _maybe_fail(self) -> None:
        if self.fail:
            raise RuntimeError("redis unavailable")


def test_factory_defaults_to_in_memory_cache() -> None:
    cache = build_ephemeral_cache(Settings())

    assert isinstance(cache, InMemoryEphemeralCache)


def test_factory_requires_redis_url_for_redis_backend() -> None:
    settings = Settings(cortex_cache_backend="redis")

    with pytest.raises(CacheUnavailableError):
        build_ephemeral_cache(settings)


def test_factory_requires_injected_redis_client() -> None:
    settings = Settings(
        cortex_cache_backend="redis", redis_url="redis://localhost:6379"
    )

    with pytest.raises(CacheUnavailableError):
        build_ephemeral_cache(settings)


def test_factory_builds_redis_backend_when_configured() -> None:
    settings = Settings(
        cortex_cache_backend="redis", redis_url="redis://localhost:6379"
    )

    cache = build_ephemeral_cache(settings, redis_client=FakeRedisClient())

    assert isinstance(cache, RedisEphemeralCache)


def test_redis_cache_sets_counters_and_locks() -> None:
    client = FakeRedisClient()
    cache = RedisEphemeralCache(client)

    cache.set("hot:health", "ok", ttl_seconds=30)
    assert cache.get("hot:health") == "ok"
    assert client.records["hot:health"].ttl_seconds == 30

    assert cache.increment("rate:user-1", ttl_seconds=60) == 1
    assert cache.increment("rate:user-1", amount=2) == 3
    assert client.records["rate:user-1"].ttl_seconds == 60

    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is True
    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is False

    cache.release_lock("job:nightly")

    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is True


def test_redis_cache_wraps_backend_failures() -> None:
    client = FakeRedisClient()
    client.fail = True
    cache = RedisEphemeralCache(client)

    with pytest.raises(CacheUnavailableError):
        cache.get("hot:health")


def test_redis_cache_counter_errors_are_explicit() -> None:
    client = FakeRedisClient()
    client.records["rate:user-1"] = FakeRedisRecord(
        value="not-a-counter", ttl_seconds=None
    )
    cache = RedisEphemeralCache(client)

    with pytest.raises(CacheCounterError):
        cache.increment("rate:user-1")
