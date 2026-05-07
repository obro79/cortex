from __future__ import annotations

from cortex.contracts.enums import RawEventStatus
from cortex.contracts.pipeline_events import PipelineEventEnvelope

from .publisher import RawEventPublisher
from .raw_events import InMemoryRawEventRepository


class RawEventReplayService:
    def __init__(
        self,
        repository: InMemoryRawEventRepository,
        publisher: RawEventPublisher,
    ) -> None:
        self.repository = repository
        self.publisher = publisher

    async def replay_by_id(
        self,
        raw_event_id: str,
        *,
        replay_run_id: str,
        replay_reason: str,
        requested_by: str,
    ) -> PipelineEventEnvelope:
        raw_event = self.repository.get_by_id(raw_event_id)
        if raw_event.status == RawEventStatus.DELETED:
            raise ValueError("deleted raw events cannot be replayed")
        return await self.publisher.publish_persisted(
            raw_event,
            replay_metadata={
                "replay_run_id": replay_run_id,
                "replay_reason": replay_reason,
                "requested_by": requested_by,
            },
        )

    async def replay_candidates(
        self,
        *,
        workspace_id: str,
        replay_run_id: str,
        replay_reason: str,
        requested_by: str,
        batch_size: int = 100,
    ) -> list[PipelineEventEnvelope]:
        events = []
        for raw_event in self.repository.list_replay_candidates(
            workspace_id=workspace_id,
            batch_size=batch_size,
        ):
            events.append(
                await self.replay_by_id(
                    raw_event.id,
                    replay_run_id=replay_run_id,
                    replay_reason=replay_reason,
                    requested_by=requested_by,
                )
            )
        return events
