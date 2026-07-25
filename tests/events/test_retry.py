from datetime import UTC, datetime, timedelta

import pytest

from cortex.events.retry import RetryPolicy


def test_retry_policy_uses_bounded_exponential_backoff() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_delay=timedelta(seconds=2),
        max_delay=timedelta(seconds=5),
    )
    now = datetime(2026, 7, 19, tzinfo=UTC)

    assert policy.retry_at(attempt_count=1, now=now) == now + timedelta(seconds=2)
    assert policy.retry_at(attempt_count=2, now=now) == now + timedelta(seconds=4)
    assert policy.retry_at(attempt_count=3, now=now) == now + timedelta(seconds=5)
    assert policy.exhausted(2) is False
    assert policy.exhausted(3) is True


@pytest.mark.parametrize("attempt_count", [0, -1])
def test_retry_policy_rejects_non_positive_attempt_counts(attempt_count: int) -> None:
    with pytest.raises(ValueError, match="attempt_count"):
        RetryPolicy().retry_at(attempt_count=attempt_count)
