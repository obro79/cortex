from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol


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
