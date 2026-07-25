from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.db.models import SchedulerLeaseRecord

JobStatus = Literal["completed", "failed", "skipped_lease"]
JobHandler = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class SchedulerLease:
    job_name: str
    owner_id: str
    expires_at: datetime
    fencing_token: int


class SchedulerLeaseRepository(Protocol):
    async def acquire(
        self,
        *,
        job_name: str,
        owner_id: str,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> SchedulerLease | None: ...

    async def release(self, *, job_name: str, owner_id: str) -> None: ...


@dataclass(frozen=True)
class ScheduledJob:
    name: str
    lease_ttl_seconds: int
    handler: JobHandler


@dataclass(frozen=True)
class ScheduledJobResult:
    job_name: str
    owner_id: str
    status: JobStatus
    fencing_token: int | None = None
    error: str | None = None


class SingletonJobRunner:
    def __init__(self, leases: SchedulerLeaseRepository, *, owner_id: str) -> None:
        self._leases = leases
        self._owner_id = owner_id

    async def run_once(self, job: ScheduledJob) -> ScheduledJobResult:
        lease = await self._leases.acquire(
            job_name=job.name,
            owner_id=self._owner_id,
            ttl_seconds=job.lease_ttl_seconds,
        )
        if lease is None:
            return ScheduledJobResult(
                job_name=job.name, owner_id=self._owner_id, status="skipped_lease"
            )
        try:
            await job.handler()
        except Exception as exc:
            return ScheduledJobResult(
                job_name=job.name,
                owner_id=self._owner_id,
                status="failed",
                fencing_token=lease.fencing_token,
                error=type(exc).__name__,
            )
        finally:
            await self._leases.release(job_name=job.name, owner_id=self._owner_id)

        return ScheduledJobResult(
            job_name=job.name,
            owner_id=self._owner_id,
            status="completed",
            fencing_token=lease.fencing_token,
        )


class InMemorySchedulerLeaseRepository:
    def __init__(self) -> None:
        self._leases: dict[str, SchedulerLease] = {}

    async def acquire(
        self,
        *,
        job_name: str,
        owner_id: str,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> SchedulerLease | None:
        current_time = now or datetime.now(UTC)
        current = self._leases.get(job_name)
        if current is not None and current.expires_at > current_time:
            return None
        lease = SchedulerLease(
            job_name=job_name,
            owner_id=owner_id,
            expires_at=current_time + timedelta(seconds=ttl_seconds),
            fencing_token=(current.fencing_token + 1) if current else 1,
        )
        self._leases[job_name] = lease
        return lease

    async def release(self, *, job_name: str, owner_id: str) -> None:
        current = self._leases.get(job_name)
        if current is not None and current.owner_id == owner_id:
            self._leases.pop(job_name, None)


class SqlAlchemySchedulerLeaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def acquire(
        self,
        *,
        job_name: str,
        owner_id: str,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> SchedulerLease | None:
        current_time = now or datetime.now(UTC)
        expires_at = current_time + timedelta(seconds=ttl_seconds)
        result = await self.session.execute(
            select(SchedulerLeaseRecord)
            .where(SchedulerLeaseRecord.job_name == job_name)
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is not None and record.expires_at > current_time:
            return None
        if record is None:
            record = SchedulerLeaseRecord(
                job_name=job_name,
                owner_id=owner_id,
                expires_at=expires_at,
                fencing_token=1,
            )
            self.session.add(record)
        else:
            record.owner_id = owner_id
            record.expires_at = expires_at
            record.fencing_token += 1
        await self.session.flush()
        return SchedulerLease(
            job_name=record.job_name,
            owner_id=record.owner_id,
            expires_at=record.expires_at,
            fencing_token=record.fencing_token,
        )

    async def release(self, *, job_name: str, owner_id: str) -> None:
        record = await self.session.get(SchedulerLeaseRecord, job_name)
        if record is not None and record.owner_id == owner_id:
            await self.session.delete(record)
            await self.session.flush()
