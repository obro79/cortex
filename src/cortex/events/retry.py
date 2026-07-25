"""Small, deterministic retry primitives shared by durable event delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential backoff for at-least-once delivery."""

    max_attempts: int = 5
    initial_delay: timedelta = timedelta(seconds=5)
    max_delay: timedelta = timedelta(minutes=15)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.initial_delay <= timedelta(0) or self.max_delay <= timedelta(0):
            raise ValueError("retry delays must be positive")

    def retry_at(self, *, attempt_count: int, now: datetime | None = None) -> datetime:
        """Return the first eligible retry time for a failed attempt."""
        if attempt_count < 1:
            raise ValueError("attempt_count must be positive")
        current = now or datetime.now(UTC)
        calculated_delay = self.initial_delay * (2 ** (attempt_count - 1))
        delay = (
            self.max_delay if calculated_delay > self.max_delay else calculated_delay
        )
        return current + delay

    def exhausted(self, attempt_count: int) -> bool:
        return attempt_count >= self.max_attempts
