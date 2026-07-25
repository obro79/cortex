from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable


class CacheUnavailableError(RuntimeError):
    pass


class CacheCounterError(ValueError):
    pass


class EphemeralCacheService(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None: ...

    def increment(
        self, key: str, *, amount: int = 1, ttl_seconds: int | None = None
    ) -> int: ...

    def delete(self, key: str) -> None: ...

    def acquire_lock(self, key: str, *, ttl_seconds: int) -> bool: ...

    def release_lock(self, key: str) -> None: ...


@runtime_checkable
class RedisCacheClient(Protocol):
    def get(self, name: str) -> str | bytes | None: ...

    def set(
        self,
        name: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None: ...

    def incrby(self, name: str, amount: int = 1) -> int: ...

    def expire(self, name: str, time: int) -> bool: ...

    def delete(self, name: str) -> int: ...


@dataclass(frozen=True)
class CacheEntry:
    value: str
    expires_at: datetime | None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at <= now


class InMemoryEphemeralCache:
    """Process-local cache for transient state only.

    This backend is intentionally safe to lose and must not be used as an
    authority for source data, permissions, jobs, or audit records.
    """

    def __init__(self) -> None:
        self._records: dict[str, CacheEntry] = {}
        self._locks: set[str] = set()

    def get(self, key: str) -> str | None:
        self._purge_expired(key)
        entry = self._records.get(key)
        if entry is None:
            return None
        return entry.value

    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        self._records[key] = CacheEntry(
            value=value,
            expires_at=_expires_at(ttl_seconds),
        )

    def increment(
        self, key: str, *, amount: int = 1, ttl_seconds: int | None = None
    ) -> int:
        self._purge_expired(key)
        current = self._records.get(key)
        value = _counter_value(current)
        value += amount
        expires_at = (
            current.expires_at if current is not None else _expires_at(ttl_seconds)
        )
        if current is not None and ttl_seconds is not None:
            expires_at = _expires_at(ttl_seconds)
        self._records[key] = CacheEntry(value=str(value), expires_at=expires_at)
        return value

    def delete(self, key: str) -> None:
        self._records.pop(key, None)
        self._locks.discard(key)

    def acquire_lock(self, key: str, *, ttl_seconds: int) -> bool:
        self._purge_expired(key)
        if key in self._locks:
            return False
        if key in self._records:
            return False
        self._locks.add(key)
        self.set(key, "locked", ttl_seconds=ttl_seconds)
        return True

    def release_lock(self, key: str) -> None:
        self.delete(key)

    def clear(self) -> None:
        self._records.clear()
        self._locks.clear()

    def _purge_expired(self, key: str) -> None:
        entry = self._records.get(key)
        if entry is None:
            return
        if entry.is_expired(datetime.now(UTC)):
            self._records.pop(key, None)
            self._locks.discard(key)


class RedisEphemeralCache:
    """Redis-backed cache for transient state only."""

    def __init__(self, client: RedisCacheClient) -> None:
        self._client = client

    def get(self, key: str) -> str | None:
        try:
            value = self._client.get(key)
        except Exception as exc:
            raise CacheUnavailableError("Redis cache get failed") from exc
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        try:
            if ttl_seconds is not None and ttl_seconds <= 0:
                self._client.delete(key)
                return
            self._client.set(key, value, ex=ttl_seconds)
        except Exception as exc:
            raise CacheUnavailableError("Redis cache set failed") from exc

    def increment(
        self, key: str, *, amount: int = 1, ttl_seconds: int | None = None
    ) -> int:
        try:
            value = self._client.incrby(key, amount)
            if ttl_seconds is not None and ttl_seconds <= 0:
                self._client.delete(key)
            elif ttl_seconds is not None:
                self._client.expire(key, ttl_seconds)
        except ValueError as exc:
            raise CacheCounterError("cache value is not an integer counter") from exc
        except Exception as exc:
            raise CacheUnavailableError("Redis cache increment failed") from exc
        return value

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as exc:
            raise CacheUnavailableError("Redis cache delete failed") from exc

    def acquire_lock(self, key: str, *, ttl_seconds: int) -> bool:
        try:
            acquired = self._client.set(key, "locked", ex=max(ttl_seconds, 1), nx=True)
            if acquired and ttl_seconds <= 0:
                self._client.delete(key)
        except Exception as exc:
            raise CacheUnavailableError("Redis cache lock failed") from exc
        return bool(acquired)

    def release_lock(self, key: str) -> None:
        self.delete(key)


def _expires_at(ttl_seconds: int | None) -> datetime | None:
    if ttl_seconds is None:
        return None
    if ttl_seconds <= 0:
        return datetime.now(UTC)
    return datetime.now(UTC) + timedelta(seconds=ttl_seconds)


def _counter_value(entry: CacheEntry | None) -> int:
    if entry is None:
        return 0
    try:
        return int(entry.value)
    except ValueError as exc:
        raise CacheCounterError("cache value is not an integer counter") from exc
