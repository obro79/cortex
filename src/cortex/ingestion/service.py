from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cortex.utils.asyncio import maybe_await

from .payloads import PayloadStore
from .publisher import RawEventPublisher
from .raw_events import RawEventInput


@dataclass(frozen=True)
class IngestionResult:
    raw_event_id: str
    created: bool
    published: bool


class RawEventIngestionService:
    def __init__(
        self,
        repository: Any,
        payload_store: PayloadStore,
        publisher: RawEventPublisher,
    ) -> None:
        self.repository = repository
        self.payload_store = payload_store
        self.publisher = publisher

    async def ingest(self, item: RawEventInput) -> IngestionResult:
        described = self.payload_store.describe_json(item.payload)
        existing = await maybe_await(
            self.repository.get_by_idempotency_key(
                item.workspace_id, item.idempotency_key
            )
        )
        if existing is not None:
            if existing.payload_hash != described.payload_hash:
                from .raw_events import RawEventIdempotencyConflict

                raise RawEventIdempotencyConflict(
                    "idempotency key already exists with different payload hash"
                )
            return IngestionResult(
                raw_event_id=existing.id,
                created=False,
                published=False,
            )

        stored = self.payload_store.put_json(item.payload)
        raw_event, created = await maybe_await(
            self.repository.create_or_get_by_idempotency_key(
                item=item,
                payload_ref=stored.payload_ref,
                payload_hash=stored.payload_hash,
                payload_size_bytes=stored.payload_size_bytes,
            )
        )
        if not created:
            return IngestionResult(
                raw_event_id=raw_event.id, created=False, published=False
            )
        try:
            await self.publisher.publish_persisted(raw_event)
        except Exception as error:
            await maybe_await(
                self.repository.mark_failed_retryable(
                    raw_event.id,
                    "publish_failed",
                    str(error),
                )
            )
            return IngestionResult(
                raw_event_id=raw_event.id,
                created=True,
                published=False,
            )
        await maybe_await(self.repository.mark_published(raw_event.id))
        return IngestionResult(raw_event_id=raw_event.id, created=True, published=True)
