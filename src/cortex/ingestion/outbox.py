"""Transactional-outbox storage and reconciliation for raw-event notifications.

The SQL repository deliberately does not commit: callers enqueue a raw event and
its outbox record through the same ``AsyncSession`` transaction.  Wiring that
transaction into durable ingestion is intentionally left to the composition root.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.events.bus import EventBus
from cortex.events.retry import RetryPolicy
from cortex.ingestion.raw_events import RawEventNotFoundError
from cortex.utils.asyncio import maybe_await

OUTBOX_PENDING = "pending"
OUTBOX_PUBLISHED = "published"
OUTBOX_DEADLETTERED = "deadlettered"

_metadata = MetaData()
ingestion_outbox = Table(
    "ingestion_outbox",
    _metadata,
    Column("id", String(128), primary_key=True),
    Column("workspace_id", String(128), nullable=False),
    Column("raw_event_id", String(128), nullable=False, unique=True),
    Column("event_type", String(128), nullable=False),
    Column("event_json", JSON, nullable=False),
    Column("status", String(32), nullable=False),
    Column("attempt_count", Integer, nullable=False, default=0),
    Column("next_attempt_at", DateTime(timezone=True)),
    Column("last_error", String(1024)),
    Column("published_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


@dataclass(frozen=True)
class OutboxMessage:
    id: str
    workspace_id: str
    raw_event_id: str
    event: PipelineEventEnvelope
    status: str = OUTBOX_PENDING
    attempt_count: int = 0
    next_attempt_at: datetime | None = None
    last_error: str | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OutboxRepository(Protocol):
    async def enqueue(
        self, *, raw_event_id: str, event: PipelineEventEnvelope
    ) -> OutboxMessage: ...

    async def due(
        self, *, limit: int, now: datetime | None = None
    ) -> list[OutboxMessage]: ...

    async def mark_published(self, message_id: str) -> OutboxMessage: ...

    async def record_failure(
        self, message_id: str, error: Exception
    ) -> OutboxMessage: ...


class RawEventReconciler(Protocol):
    def mark_published(self, raw_event_id: str) -> Any: ...

    def mark_failed_retryable(
        self, raw_event_id: str, error_code: str, error_message: str
    ) -> Any: ...

    def mark_deadlettered(
        self, raw_event_id: str, error_code: str, error_message: str
    ) -> Any: ...


class InMemoryOutboxRepository:
    """Deterministic outbox implementation for local processing and tests."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self.retry_policy = retry_policy or RetryPolicy()
        self._messages: dict[str, OutboxMessage] = {}
        self._by_raw_event: dict[str, str] = {}

    async def enqueue(
        self, *, raw_event_id: str, event: PipelineEventEnvelope
    ) -> OutboxMessage:
        existing_id = self._by_raw_event.get(raw_event_id)
        if existing_id is not None:
            return self._messages[existing_id]
        now = datetime.now(UTC)
        message = OutboxMessage(
            id=f"outbox_{uuid4().hex}",
            workspace_id=event.workspace_id,
            raw_event_id=raw_event_id,
            event=event,
            created_at=now,
            updated_at=now,
        )
        self._messages[message.id] = message
        self._by_raw_event[raw_event_id] = message.id
        return message

    async def due(
        self, *, limit: int, now: datetime | None = None
    ) -> list[OutboxMessage]:
        _validate_limit(limit)
        current = now or datetime.now(UTC)
        messages = (
            message
            for message in self._messages.values()
            if message.status == OUTBOX_PENDING
            and (message.next_attempt_at is None or message.next_attempt_at <= current)
        )
        return sorted(
            messages, key=lambda message: (message.created_at or current, message.id)
        )[:limit]

    async def mark_published(self, message_id: str) -> OutboxMessage:
        return self._replace(
            message_id,
            status=OUTBOX_PUBLISHED,
            published_at=datetime.now(UTC),
            next_attempt_at=None,
            last_error=None,
        )

    async def record_failure(self, message_id: str, error: Exception) -> OutboxMessage:
        message = self._require(message_id)
        attempts = message.attempt_count + 1
        status = (
            OUTBOX_DEADLETTERED
            if self.retry_policy.exhausted(attempts)
            else OUTBOX_PENDING
        )
        retry_at = (
            None
            if status == OUTBOX_DEADLETTERED
            else self.retry_policy.retry_at(attempt_count=attempts)
        )
        return self._replace(
            message_id,
            status=status,
            attempt_count=attempts,
            next_attempt_at=retry_at,
            last_error=str(error)[:1024],
        )

    def get_by_raw_event_id(self, raw_event_id: str) -> OutboxMessage | None:
        message_id = self._by_raw_event.get(raw_event_id)
        return self._messages[message_id] if message_id is not None else None

    def _require(self, message_id: str) -> OutboxMessage:
        try:
            return self._messages[message_id]
        except KeyError as error:
            raise RawEventNotFoundError(message_id) from error

    def _replace(self, message_id: str, **values: Any) -> OutboxMessage:
        message = replace(
            self._require(message_id), updated_at=datetime.now(UTC), **values
        )
        self._messages[message_id] = message
        return message


class SqlAlchemyOutboxRepository:
    """Outbox repository bound to a caller-owned SQLAlchemy transaction.

    Every method issues statements through the supplied session but deliberately
    never commits or rolls back it.  This lets durable ingestion atomically
    persist a raw event and its notification in one transaction; callers also
    decide the transaction boundary for dispatcher state updates.
    """

    def __init__(
        self, session: AsyncSession, retry_policy: RetryPolicy | None = None
    ) -> None:
        self.session = session
        self.retry_policy = retry_policy or RetryPolicy()

    async def enqueue(
        self, *, raw_event_id: str, event: PipelineEventEnvelope
    ) -> OutboxMessage:
        existing = await self._by_raw_event_id(raw_event_id)
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        message = OutboxMessage(
            id=f"outbox_{uuid4().hex}",
            workspace_id=event.workspace_id,
            raw_event_id=raw_event_id,
            event=event,
            created_at=now,
            updated_at=now,
        )
        await self.session.execute(
            insert(ingestion_outbox).values(**_message_values(message))
        )
        return message

    async def due(
        self, *, limit: int, now: datetime | None = None
    ) -> list[OutboxMessage]:
        _validate_limit(limit)
        current = now or datetime.now(UTC)
        result = await self.session.execute(
            select(ingestion_outbox)
            .where(
                ingestion_outbox.c.status == OUTBOX_PENDING,
                ingestion_outbox.c.next_attempt_at.is_(None)
                | (ingestion_outbox.c.next_attempt_at <= current),
            )
            .order_by(ingestion_outbox.c.created_at, ingestion_outbox.c.id)
            .limit(limit)
        )
        return [_message_from_row(row) for row in result.mappings()]

    async def mark_published(self, message_id: str) -> OutboxMessage:
        now = datetime.now(UTC)
        await self.session.execute(
            update(ingestion_outbox)
            .where(ingestion_outbox.c.id == message_id)
            .values(
                status=OUTBOX_PUBLISHED,
                published_at=now,
                next_attempt_at=None,
                last_error=None,
                updated_at=now,
            )
        )
        return await self._require(message_id)

    async def record_failure(self, message_id: str, error: Exception) -> OutboxMessage:
        message = await self._require(message_id)
        attempts = message.attempt_count + 1
        status = (
            OUTBOX_DEADLETTERED
            if self.retry_policy.exhausted(attempts)
            else OUTBOX_PENDING
        )
        retry_at = (
            None
            if status == OUTBOX_DEADLETTERED
            else self.retry_policy.retry_at(attempt_count=attempts)
        )
        await self.session.execute(
            update(ingestion_outbox)
            .where(ingestion_outbox.c.id == message_id)
            .values(
                status=status,
                attempt_count=attempts,
                next_attempt_at=retry_at,
                last_error=str(error)[:1024],
                updated_at=datetime.now(UTC),
            )
        )
        return await self._require(message_id)

    async def _by_raw_event_id(self, raw_event_id: str) -> OutboxMessage | None:
        result = await self.session.execute(
            select(ingestion_outbox).where(
                ingestion_outbox.c.raw_event_id == raw_event_id
            )
        )
        row = result.mappings().one_or_none()
        return _message_from_row(row) if row is not None else None

    async def _require(self, message_id: str) -> OutboxMessage:
        result = await self.session.execute(
            select(ingestion_outbox).where(ingestion_outbox.c.id == message_id)
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise RawEventNotFoundError(message_id)
        return _message_from_row(row)


class RawEventOutboxDispatcher:
    """Delivers committed outbox messages; delivery is at-least-once by design."""

    def __init__(
        self,
        repository: OutboxRepository,
        event_bus: EventBus,
        raw_events: RawEventReconciler | None = None,
    ) -> None:
        self.repository = repository
        self.event_bus = event_bus
        self.raw_events = raw_events

    async def dispatch_due(self, *, limit: int = 100) -> list[OutboxMessage]:
        delivered: list[OutboxMessage] = []
        for message in await self.repository.due(limit=limit):
            try:
                await self.event_bus.publish(message.event)
            except Exception as error:
                failed = await self.repository.record_failure(message.id, error)
                await self._reconcile_failure(failed, error)
                continue
            published = await self.repository.mark_published(message.id)
            await self._reconcile_published(published)
            delivered.append(published)
        return delivered

    async def _reconcile_published(self, message: OutboxMessage) -> None:
        if self.raw_events is not None:
            await maybe_await(self.raw_events.mark_published(message.raw_event_id))

    async def _reconcile_failure(
        self, message: OutboxMessage, error: Exception
    ) -> None:
        if self.raw_events is None:
            return
        error_code = type(error).__name__
        if message.status == OUTBOX_DEADLETTERED:
            await maybe_await(
                self.raw_events.mark_deadlettered(
                    message.raw_event_id, error_code, str(error)
                )
            )
        elif message.attempt_count == 1:
            # Raw-event lifecycle has a single retryable state; its detailed retry
            # schedule remains authoritative in the outbox record.
            await maybe_await(
                self.raw_events.mark_failed_retryable(
                    message.raw_event_id, error_code, str(error)
                )
            )


def _validate_limit(limit: int) -> None:
    if limit < 1:
        raise ValueError("limit must be at least one")


def _message_values(message: OutboxMessage) -> dict[str, object]:
    return {
        "id": message.id,
        "workspace_id": message.workspace_id,
        "raw_event_id": message.raw_event_id,
        "event_type": message.event.event_type,
        "event_json": message.event.model_dump(mode="json"),
        "status": message.status,
        "attempt_count": message.attempt_count,
        "next_attempt_at": message.next_attempt_at,
        "last_error": message.last_error,
        "published_at": message.published_at,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }


def _message_from_row(row: Any) -> OutboxMessage:
    return OutboxMessage(
        id=row["id"],
        workspace_id=row["workspace_id"],
        raw_event_id=row["raw_event_id"],
        event=PipelineEventEnvelope.model_validate(row["event_json"]),
        status=row["status"],
        attempt_count=row["attempt_count"],
        next_attempt_at=row["next_attempt_at"],
        last_error=row["last_error"],
        published_at=row["published_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
