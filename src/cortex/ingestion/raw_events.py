from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus
from cortex.db.models import RawEventRecord

ALLOWED_PROVIDERS = {"slack", "linear", "github", "repo_docs", "fixture"}

VALID_TRANSITIONS: dict[RawEventStatus, set[RawEventStatus]] = {
    RawEventStatus.RECEIVED: {RawEventStatus.PERSISTED},
    RawEventStatus.PERSISTED: {
        RawEventStatus.PUBLISHED,
        RawEventStatus.FAILED_RETRYABLE,
    },
    RawEventStatus.PUBLISHED: {
        RawEventStatus.PROCESSING,
        RawEventStatus.FAILED_RETRYABLE,
        RawEventStatus.DEADLETTERED,
    },
    RawEventStatus.PROCESSING: {
        RawEventStatus.PROCESSED,
        RawEventStatus.FAILED_RETRYABLE,
        RawEventStatus.DEADLETTERED,
    },
    RawEventStatus.PROCESSED: {RawEventStatus.DELETED},
    RawEventStatus.FAILED_RETRYABLE: {
        RawEventStatus.PUBLISHED,
        RawEventStatus.PROCESSING,
        RawEventStatus.DEADLETTERED,
    },
    RawEventStatus.DEADLETTERED: set(),
    RawEventStatus.DELETED: set(),
}


class RawEventError(Exception):
    pass


class RawEventValidationError(RawEventError):
    pass


class RawEventIdempotencyConflict(RawEventError):
    pass


class RawEventTransitionError(RawEventError):
    pass


class RawEventNotFoundError(RawEventError):
    pass


@dataclass(frozen=True)
class RawEventInput:
    workspace_id: str
    source_connection_id: str
    provider: str
    external_event_id: str
    event_type: str
    external_object_key: str
    idempotency_key: str
    payload: Any
    occurred_at: datetime | None = None
    trace_id: str | None = None
    raw_event_id: str | None = None


class InMemoryRawEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, RawEvent] = {}
        self._by_idempotency: dict[tuple[str, str], str] = {}
        self._by_provider_event: dict[tuple[str, str, str], str] = {}

    def create_or_get_by_idempotency_key(
        self,
        *,
        item: RawEventInput,
        payload_ref: str,
        payload_hash: str,
        payload_size_bytes: int,
        received_at: datetime | None = None,
    ) -> tuple[RawEvent, bool]:
        self._validate_input(item)
        existing = self.get_by_idempotency_key(item.workspace_id, item.idempotency_key)
        if existing is not None:
            if existing.payload_hash != payload_hash:
                raise RawEventIdempotencyConflict(
                    "idempotency key already exists with different payload hash"
                )
            return existing, False

        provider_key = (item.workspace_id, item.provider, item.external_event_id)
        if provider_key in self._by_provider_event:
            existing = self._events[self._by_provider_event[provider_key]]
            if existing.payload_hash != payload_hash:
                raise RawEventIdempotencyConflict(
                    "provider event already exists with different payload hash"
                )
            return existing, False

        now = received_at or datetime.now(UTC)
        raw_event = RawEvent(
            id=item.raw_event_id or f"raw_{uuid4().hex}",
            workspace_id=item.workspace_id,
            source_connection_id=item.source_connection_id,
            provider=item.provider,
            external_event_id=item.external_event_id,
            event_type=item.event_type,
            external_object_key=item.external_object_key,
            idempotency_key=item.idempotency_key,
            payload_ref=payload_ref,
            payload_hash=payload_hash,
            payload_size_bytes=payload_size_bytes,
            occurred_at=item.occurred_at,
            received_at=now,
            published_at=None,
            processed_at=None,
            status=RawEventStatus.PERSISTED,
            trace_id=item.trace_id,
            created_at=now,
            updated_at=now,
        )
        self._events[raw_event.id] = raw_event
        self._by_idempotency[(raw_event.workspace_id, raw_event.idempotency_key)] = (
            raw_event.id
        )
        self._by_provider_event[provider_key] = raw_event.id
        return raw_event, True

    def get_by_id(self, raw_event_id: str) -> RawEvent:
        try:
            return self._events[raw_event_id]
        except KeyError as error:
            raise RawEventNotFoundError(raw_event_id) from error

    def get_by_idempotency_key(
        self, workspace_id: str, idempotency_key: str
    ) -> RawEvent | None:
        raw_event_id = self._by_idempotency.get((workspace_id, idempotency_key))
        return self._events[raw_event_id] if raw_event_id else None

    def mark_published(
        self, raw_event_id: str, published_at: datetime | None = None
    ) -> RawEvent:
        event = self.get_by_id(raw_event_id)
        return self._transition(
            event,
            RawEventStatus.PUBLISHED,
            published_at=published_at or datetime.now(UTC),
            last_error_code=None,
            last_error_message=None,
        )

    def mark_processing(self, raw_event_id: str) -> RawEvent:
        return self._transition(self.get_by_id(raw_event_id), RawEventStatus.PROCESSING)

    def mark_processed(self, raw_event_id: str) -> RawEvent:
        return self._transition(
            self.get_by_id(raw_event_id),
            RawEventStatus.PROCESSED,
            processed_at=datetime.now(UTC),
        )

    def mark_failed_retryable(
        self, raw_event_id: str, error_code: str, error_message: str
    ) -> RawEvent:
        event = self.get_by_id(raw_event_id)
        return self._transition(
            event,
            RawEventStatus.FAILED_RETRYABLE,
            attempt_count=event.attempt_count + 1,
            last_attempt_at=datetime.now(UTC),
            last_error_code=error_code,
            last_error_message=error_message,
        )

    def mark_deadlettered(
        self, raw_event_id: str, error_code: str, error_message: str
    ) -> RawEvent:
        event = self.get_by_id(raw_event_id)
        return self._transition(
            event,
            RawEventStatus.DEADLETTERED,
            last_attempt_at=datetime.now(UTC),
            last_error_code=error_code,
            last_error_message=error_message,
        )

    def mark_deleted(self, raw_event_id: str) -> RawEvent:
        return self._transition(self.get_by_id(raw_event_id), RawEventStatus.DELETED)

    def list_replay_candidates(
        self,
        *,
        workspace_id: str,
        source_connection_id: str | None = None,
        statuses: set[RawEventStatus] | None = None,
        batch_size: int = 100,
    ) -> list[RawEvent]:
        allowed = statuses or {
            RawEventStatus.PUBLISHED,
            RawEventStatus.FAILED_RETRYABLE,
            RawEventStatus.PROCESSED,
        }
        candidates = [
            event
            for event in self._events.values()
            if event.workspace_id == workspace_id
            and event.status in allowed
            and event.status != RawEventStatus.DELETED
            and event.status != RawEventStatus.PROCESSING
            and (
                source_connection_id is None
                or event.source_connection_id == source_connection_id
            )
        ]
        return sorted(candidates, key=lambda event: (event.received_at, event.id))[
            :batch_size
        ]

    def _transition(
        self,
        event: RawEvent,
        next_status: RawEventStatus,
        **updates: Any,
    ) -> RawEvent:
        current = RawEventStatus(event.status)
        if next_status not in VALID_TRANSITIONS[current]:
            raise RawEventTransitionError(
                f"invalid raw event transition: {current.value} -> {next_status.value}"
            )
        updated = event.model_copy(
            update={
                "status": next_status,
                "updated_at": datetime.now(UTC),
                **updates,
            }
        )
        self._events[event.id] = updated
        return updated

    def _validate_input(self, item: RawEventInput) -> None:
        required = {
            "workspace_id": item.workspace_id,
            "source_connection_id": item.source_connection_id,
            "provider": item.provider,
            "external_event_id": item.external_event_id,
            "event_type": item.event_type,
            "external_object_key": item.external_object_key,
            "idempotency_key": item.idempotency_key,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RawEventValidationError(
                f"missing required fields: {', '.join(missing)}"
            )
        if item.provider not in ALLOWED_PROVIDERS:
            raise RawEventValidationError(f"unsupported provider: {item.provider}")


def raw_event_from_record(record: RawEventRecord) -> RawEvent:
    return RawEvent(
        id=record.id,
        workspace_id=record.workspace_id,
        source_connection_id=record.source_connection_id,
        provider=record.provider,
        external_event_id=record.external_event_id,
        event_type=record.event_type,
        external_object_key=record.external_object_key,
        idempotency_key=record.idempotency_key,
        payload_ref=record.payload_ref,
        payload_hash=record.payload_hash,
        payload_size_bytes=record.payload_size_bytes,
        occurred_at=record.occurred_at,
        received_at=record.received_at,
        published_at=record.published_at,
        processed_at=record.processed_at,
        status=RawEventStatus(record.status),
        attempt_count=record.attempt_count,
        last_error_code=record.last_error_code,
        last_error_message=record.last_error_message,
        next_retry_at=record.next_retry_at,
        last_attempt_at=record.last_attempt_at,
        trace_id=record.trace_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def apply_raw_event_to_record(event: RawEvent, record: RawEventRecord) -> None:
    record.published_at = event.published_at
    record.processed_at = event.processed_at
    record.status = RawEventStatus(event.status).value
    record.attempt_count = event.attempt_count
    record.last_error_code = event.last_error_code
    record.last_error_message = event.last_error_message
    record.next_retry_at = event.next_retry_at
    record.last_attempt_at = event.last_attempt_at
    record.updated_at = event.updated_at


class SqlAlchemyRawEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._memory = InMemoryRawEventRepository()

    async def create_or_get_by_idempotency_key(
        self,
        *,
        item: RawEventInput,
        payload_ref: str,
        payload_hash: str,
        payload_size_bytes: int,
        received_at: datetime | None = None,
    ) -> tuple[RawEvent, bool]:
        self._memory._validate_input(item)
        existing = await self.get_by_idempotency_key(
            item.workspace_id, item.idempotency_key
        )
        if existing is not None:
            if existing.payload_hash != payload_hash:
                raise RawEventIdempotencyConflict(
                    "idempotency key already exists with different payload hash"
                )
            return existing, False

        provider_existing = await self.get_by_provider_event(
            item.workspace_id, item.provider, item.external_event_id
        )
        if provider_existing is not None:
            if provider_existing.payload_hash != payload_hash:
                raise RawEventIdempotencyConflict(
                    "provider event already exists with different payload hash"
                )
            return provider_existing, False

        now = received_at or datetime.now(UTC)
        raw_event = RawEvent(
            id=item.raw_event_id or f"raw_{uuid4().hex}",
            workspace_id=item.workspace_id,
            source_connection_id=item.source_connection_id,
            provider=item.provider,
            external_event_id=item.external_event_id,
            event_type=item.event_type,
            external_object_key=item.external_object_key,
            idempotency_key=item.idempotency_key,
            payload_ref=payload_ref,
            payload_hash=payload_hash,
            payload_size_bytes=payload_size_bytes,
            occurred_at=item.occurred_at,
            received_at=now,
            status=RawEventStatus.PERSISTED,
            trace_id=item.trace_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(self._record_from_raw_event(raw_event))
        await self.session.flush()
        return raw_event, True

    async def get_by_id(self, raw_event_id: str) -> RawEvent:
        record = await self.session.get(RawEventRecord, raw_event_id)
        if record is None:
            raise RawEventNotFoundError(raw_event_id)
        return raw_event_from_record(record)

    async def get_by_idempotency_key(
        self, workspace_id: str, idempotency_key: str
    ) -> RawEvent | None:
        result = await self.session.execute(
            select(RawEventRecord).where(
                RawEventRecord.workspace_id == workspace_id,
                RawEventRecord.idempotency_key == idempotency_key,
            )
        )
        record = result.scalar_one_or_none()
        return raw_event_from_record(record) if record else None

    async def get_by_provider_event(
        self, workspace_id: str, provider: str, external_event_id: str
    ) -> RawEvent | None:
        result = await self.session.execute(
            select(RawEventRecord).where(
                RawEventRecord.workspace_id == workspace_id,
                RawEventRecord.provider == provider,
                RawEventRecord.external_event_id == external_event_id,
            )
        )
        record = result.scalar_one_or_none()
        return raw_event_from_record(record) if record else None

    async def mark_published(
        self, raw_event_id: str, published_at: datetime | None = None
    ) -> RawEvent:
        event = await self.get_by_id(raw_event_id)
        updated = self._memory._transition(
            event,
            RawEventStatus.PUBLISHED,
            published_at=published_at or datetime.now(UTC),
            last_error_code=None,
            last_error_message=None,
        )
        await self._persist_status_update(updated)
        return updated

    async def mark_processing(self, raw_event_id: str) -> RawEvent:
        return await self._transition(raw_event_id, RawEventStatus.PROCESSING)

    async def mark_processed(self, raw_event_id: str) -> RawEvent:
        return await self._transition(
            raw_event_id,
            RawEventStatus.PROCESSED,
            processed_at=datetime.now(UTC),
        )

    async def mark_failed_retryable(
        self, raw_event_id: str, error_code: str, error_message: str
    ) -> RawEvent:
        event = await self.get_by_id(raw_event_id)
        updated = self._memory._transition(
            event,
            RawEventStatus.FAILED_RETRYABLE,
            attempt_count=event.attempt_count + 1,
            last_attempt_at=datetime.now(UTC),
            last_error_code=error_code,
            last_error_message=error_message,
        )
        await self._persist_status_update(updated)
        return updated

    async def mark_deadlettered(
        self, raw_event_id: str, error_code: str, error_message: str
    ) -> RawEvent:
        event = await self.get_by_id(raw_event_id)
        updated = self._memory._transition(
            event,
            RawEventStatus.DEADLETTERED,
            last_attempt_at=datetime.now(UTC),
            last_error_code=error_code,
            last_error_message=error_message,
        )
        await self._persist_status_update(updated)
        return updated

    async def mark_deleted(self, raw_event_id: str) -> RawEvent:
        return await self._transition(raw_event_id, RawEventStatus.DELETED)

    async def list_replay_candidates(
        self,
        *,
        workspace_id: str,
        source_connection_id: str | None = None,
        statuses: set[RawEventStatus] | None = None,
        batch_size: int = 100,
    ) -> list[RawEvent]:
        allowed = statuses or {
            RawEventStatus.PUBLISHED,
            RawEventStatus.FAILED_RETRYABLE,
            RawEventStatus.PROCESSED,
        }
        statement = (
            select(RawEventRecord)
            .where(
                RawEventRecord.workspace_id == workspace_id,
                RawEventRecord.status.in_([status.value for status in allowed]),
                RawEventRecord.status != RawEventStatus.DELETED.value,
                RawEventRecord.status != RawEventStatus.PROCESSING.value,
            )
            .order_by(RawEventRecord.received_at, RawEventRecord.id)
            .limit(batch_size)
        )
        if source_connection_id is not None:
            statement = statement.where(
                RawEventRecord.source_connection_id == source_connection_id
            )
        result = await self.session.execute(statement)
        return [raw_event_from_record(record) for record in result.scalars()]

    async def _transition(
        self,
        raw_event_id: str,
        next_status: RawEventStatus,
        **updates: Any,
    ) -> RawEvent:
        event = await self.get_by_id(raw_event_id)
        updated = self._memory._transition(event, next_status, **updates)
        await self._persist_status_update(updated)
        return updated

    async def _persist_status_update(self, event: RawEvent) -> None:
        record = await self.session.get(RawEventRecord, event.id)
        if record is None:
            raise RawEventNotFoundError(event.id)
        apply_raw_event_to_record(event, record)
        await self.session.flush()

    def _record_from_raw_event(self, event: RawEvent) -> RawEventRecord:
        return RawEventRecord(
            id=event.id,
            workspace_id=event.workspace_id,
            source_connection_id=event.source_connection_id,
            provider=event.provider,
            external_event_id=event.external_event_id,
            event_type=event.event_type,
            external_object_key=event.external_object_key,
            idempotency_key=event.idempotency_key,
            payload_ref=event.payload_ref,
            payload_hash=event.payload_hash,
            payload_size_bytes=event.payload_size_bytes,
            occurred_at=event.occurred_at,
            received_at=event.received_at,
            published_at=event.published_at,
            processed_at=event.processed_at,
            status=RawEventStatus(event.status).value,
            attempt_count=event.attempt_count,
            last_error_code=event.last_error_code,
            last_error_message=event.last_error_message,
            next_retry_at=event.next_retry_at,
            last_attempt_at=event.last_attempt_at,
            trace_id=event.trace_id,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
