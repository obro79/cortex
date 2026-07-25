from __future__ import annotations

import pytest

from cortex.platform import InMemoryEphemeralCache
from cortex.platform.rate_limits import (
    RateLimitPolicy,
    RateLimitService,
    RateLimitSubject,
)


def test_rate_limit_allows_until_policy_limit() -> None:
    service = RateLimitService(InMemoryEphemeralCache())
    policy = RateLimitPolicy(name="api", limit=2, window_seconds=60, namespace="http")
    subject = RateLimitSubject(
        workspace_id="workspace-1", user_id="user-1", client_id="127.0.0.1"
    )

    first = service.check(policy, subject)
    second = service.check(policy, subject)
    third = service.check(policy, subject)

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert third.allowed is False
    assert third.retry_after_seconds == 60


def test_rate_limit_subjects_are_isolated() -> None:
    service = RateLimitService(InMemoryEphemeralCache())
    policy = RateLimitPolicy(name="api", limit=1, window_seconds=60, namespace="http")

    first_subject = RateLimitSubject(
        workspace_id="workspace-1", user_id="user-1", client_id="127.0.0.1"
    )
    second_subject = RateLimitSubject(
        workspace_id="workspace-1", user_id="user-2", client_id="127.0.0.1"
    )

    assert service.check(policy, first_subject).allowed is True
    assert service.check(policy, first_subject).allowed is False
    assert service.check(policy, second_subject).allowed is True


def test_rate_limit_policy_requires_positive_values() -> None:
    with pytest.raises(ValueError):
        RateLimitPolicy(name="api", limit=0, window_seconds=60, namespace="http")

    with pytest.raises(ValueError):
        RateLimitPolicy(name="api", limit=1, window_seconds=0, namespace="http")
