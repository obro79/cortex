from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.events.bus import EventBus
from cortex.ingestion.payloads import PayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import (
    RawEventIdempotencyConflict,
    RawEventInput,
    SqlAlchemyRawEventRepository,
)
from cortex.ingestion.service import IngestionResult


class SessionRawEventIngestionService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        payload_store: PayloadStore,
        event_bus: EventBus,
    ) -> None:
        self.session_factory = session_factory
        self.payload_store = payload_store
        self.event_bus = event_bus

    async def ingest(self, item: RawEventInput) -> IngestionResult:
        described = self.payload_store.describe_json(item.payload)
        async with self.session_factory() as session:
            repository = SqlAlchemyRawEventRepository(session)
            existing = await repository.get_by_idempotency_key(
                item.workspace_id, item.idempotency_key
            )
            if existing is not None:
                if existing.payload_hash != described.payload_hash:
                    raise RawEventIdempotencyConflict(
                        "idempotency key already exists with different payload hash"
                    )
                return IngestionResult(
                    raw_event_id=existing.id,
                    created=False,
                    published=False,
                )

            stored = self.payload_store.put_json(item.payload)
            raw_event, created = await repository.create_or_get_by_idempotency_key(
                item=item,
                payload_ref=stored.payload_ref,
                payload_hash=stored.payload_hash,
                payload_size_bytes=stored.payload_size_bytes,
            )
            if not created:
                await session.commit()
                return IngestionResult(
                    raw_event_id=raw_event.id, created=False, published=False
                )
            await session.commit()

        publisher = RawEventPublisher(self.event_bus)
        try:
            await publisher.publish_persisted(raw_event)
        except Exception as error:
            async with self.session_factory() as session:
                repository = SqlAlchemyRawEventRepository(session)
                await repository.mark_failed_retryable(
                    raw_event.id,
                    "publish_failed",
                    type(error).__name__,
                )
                await session.commit()
            return IngestionResult(
                raw_event_id=raw_event.id,
                created=True,
                published=False,
            )

        async with self.session_factory() as session:
            repository = SqlAlchemyRawEventRepository(session)
            await repository.mark_published(raw_event.id)
            await session.commit()
        return IngestionResult(raw_event_id=raw_event.id, created=True, published=True)
