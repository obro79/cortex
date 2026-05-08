from __future__ import annotations

import pytest

from cortex.platform import CacheCounterError, InMemoryEphemeralCache


def test_cache_sets_gets_and_deletes_values() -> None:
    cache = InMemoryEphemeralCache()

    cache.set("session:1", "warm")

    assert cache.get("session:1") == "warm"

    cache.delete("session:1")

    assert cache.get("session:1") is None


def test_cache_expires_values_by_ttl() -> None:
    cache = InMemoryEphemeralCache()

    cache.set("source:status", "indexed", ttl_seconds=0)

    assert cache.get("source:status") is None


def test_increment_creates_and_updates_counter() -> None:
    cache = InMemoryEphemeralCache()

    assert cache.increment("rate:user-1", ttl_seconds=60) == 1
    assert cache.increment("rate:user-1", amount=2) == 3

    assert cache.get("rate:user-1") == "3"


def test_increment_rejects_non_counter_value() -> None:
    cache = InMemoryEphemeralCache()
    cache.set("rate:user-1", "not-a-counter")

    with pytest.raises(CacheCounterError):
        cache.increment("rate:user-1")


def test_locks_are_exclusive_until_released() -> None:
    cache = InMemoryEphemeralCache()

    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is True
    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is False

    cache.release_lock("job:nightly")

    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is True


def test_expired_locks_can_be_reacquired() -> None:
    cache = InMemoryEphemeralCache()

    assert cache.acquire_lock("job:nightly", ttl_seconds=0) is True
    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is True


def test_clear_drops_all_state() -> None:
    cache = InMemoryEphemeralCache()
    cache.set("retrieval:query", "cached")
    cache.acquire_lock("job:nightly", ttl_seconds=60)

    cache.clear()

    assert cache.get("retrieval:query") is None
    assert cache.acquire_lock("job:nightly", ttl_seconds=60) is True
