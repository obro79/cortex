from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from cortex.platform import (
    InMemorySchedulerLeaseRepository,
    ScheduledJob,
    SingletonJobRunner,
)


async def test_lease_allows_only_one_owner_until_release() -> None:
    leases = InMemorySchedulerLeaseRepository()

    first = await leases.acquire(
        job_name="connector-backfill", owner_id="worker-1", ttl_seconds=60
    )
    second = await leases.acquire(
        job_name="connector-backfill", owner_id="worker-2", ttl_seconds=60
    )

    assert first is not None
    assert first.owner_id == "worker-1"
    assert second is None

    await leases.release(job_name="connector-backfill", owner_id="worker-1")

    third = await leases.acquire(
        job_name="connector-backfill", owner_id="worker-2", ttl_seconds=60
    )
    assert third is not None
    assert third.owner_id == "worker-2"


async def test_expired_lease_can_be_stolen_with_new_fencing_token() -> None:
    leases = InMemorySchedulerLeaseRepository()
    now = datetime(2026, 5, 8, tzinfo=UTC)

    first = await leases.acquire(
        job_name="retention-sweep", owner_id="worker-1", ttl_seconds=60, now=now
    )
    stolen = await leases.acquire(
        job_name="retention-sweep",
        owner_id="worker-2",
        ttl_seconds=60,
        now=now + timedelta(seconds=61),
    )

    assert first is not None
    assert stolen is not None
    assert stolen.owner_id == "worker-2"
    assert stolen.fencing_token == first.fencing_token + 1


async def test_singleton_runner_skips_when_lease_is_held() -> None:
    leases = InMemorySchedulerLeaseRepository()
    await leases.acquire(job_name="source-health", owner_id="worker-1", ttl_seconds=60)
    runner = SingletonJobRunner(leases, owner_id="worker-2")
    calls = 0

    async def handler() -> None:
        nonlocal calls
        calls += 1

    result = await runner.run_once(
        ScheduledJob(name="source-health", lease_ttl_seconds=60, handler=handler)
    )

    assert result.status == "skipped_lease"
    assert calls == 0


async def test_singleton_runner_executes_and_releases_lease() -> None:
    leases = InMemorySchedulerLeaseRepository()
    runner = SingletonJobRunner(leases, owner_id="worker-1")
    calls = 0

    async def handler() -> None:
        nonlocal calls
        calls += 1

    result = await runner.run_once(
        ScheduledJob(name="source-health", lease_ttl_seconds=60, handler=handler)
    )
    reacquired = await leases.acquire(
        job_name="source-health", owner_id="worker-2", ttl_seconds=60
    )

    assert result.status == "completed"
    assert result.fencing_token == 1
    assert calls == 1
    assert reacquired is not None


def test_scheduler_lease_migration_exists() -> None:
    migration = Path("alembic/versions/0010_scheduler_leases.py")
    contents = migration.read_text()

    assert "scheduler_leases" in contents
    assert "fencing_token" in contents
    assert "expires_at" in contents
