from __future__ import annotations

from cortex.contracts.enums import RawEventStatus
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadNotFoundError
from cortex.ingestion.raw_events import (
    InMemoryRawEventRepository,
    RawEventNotFoundError,
)
from cortex.normalization.service import SourceNormalizationService


class NormalizationWorkerSkeleton:
    def __init__(
        self,
        repository: InMemoryRawEventRepository,
        payload_store: InMemoryPayloadStore,
        max_attempts: int = 3,
        normalization_service: SourceNormalizationService | None = None,
    ) -> None:
        self.repository = repository
        self.payload_store = payload_store
        self.max_attempts = max_attempts
        self.normalization_service = normalization_service

    async def handle_raw_event_persisted(
        self, envelope: PipelineEventEnvelope
    ) -> dict[str, str]:
        if self.normalization_service is not None:
            result = await self.normalization_service.handle_raw_event_persisted(
                envelope
            )
            response = {
                "status": result.status,
            }
            if result.raw_event_id is not None:
                response["raw_event_id"] = result.raw_event_id
            if result.reason is not None:
                response["reason"] = result.reason
            return response
        if envelope.event_type != "raw_event.persisted":
            return {"status": "ignored", "reason": "unsupported_event_type"}
        if envelope.subject.type != "raw_event":
            return {"status": "ignored", "reason": "unsupported_subject"}

        try:
            raw_event = self.repository.get_by_id(envelope.subject.id)
        except RawEventNotFoundError:
            return {"status": "retryable", "reason": "raw_event_not_found"}

        try:
            self.repository.mark_processing(raw_event.id)
            if raw_event.payload_ref is None:
                raise PayloadNotFoundError("<missing>")
            self.payload_store.get(raw_event.payload_ref)
            self.repository.mark_processed(raw_event.id)
            return {"status": "processed", "raw_event_id": raw_event.id}
        except PayloadNotFoundError as error:
            current = self.repository.get_by_id(raw_event.id)
            if current.attempt_count + 1 >= self.max_attempts:
                self.repository.mark_deadlettered(
                    raw_event.id,
                    "payload_not_found",
                    str(error),
                )
                return {"status": "deadlettered", "raw_event_id": raw_event.id}
            self.repository.mark_failed_retryable(
                raw_event.id,
                "payload_not_found",
                str(error),
            )
            return {"status": "retryable", "raw_event_id": raw_event.id}


def is_terminal_raw_event_status(status: RawEventStatus) -> bool:
    return status in {RawEventStatus.PROCESSED, RawEventStatus.DEADLETTERED}
