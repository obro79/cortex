from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from cortex.platform.cache import EphemeralCacheService


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    limit: int
    window_seconds: int
    namespace: str

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("rate-limit policy limit must be positive")
        if self.window_seconds < 1:
            raise ValueError("rate-limit policy window_seconds must be positive")


@dataclass(frozen=True)
class RateLimitSubject:
    workspace_id: str
    user_id: str
    client_id: str

    @property
    def stable_key(self) -> str:
        raw = "|".join([self.workspace_id, self.user_id, self.client_id])
        return sha256(raw.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    count: int


class RateLimitService:
    def __init__(self, cache: EphemeralCacheService) -> None:
        self._cache = cache

    def check(
        self, policy: RateLimitPolicy, subject: RateLimitSubject
    ) -> RateLimitDecision:
        key = f"rate:{policy.namespace}:{policy.name}:{subject.stable_key}"
        count = self._cache.increment(key, ttl_seconds=policy.window_seconds)
        allowed = count <= policy.limit
        return RateLimitDecision(
            allowed=allowed,
            limit=policy.limit,
            remaining=max(policy.limit - count, 0),
            retry_after_seconds=0 if allowed else policy.window_seconds,
            count=count,
        )
