from typing import Protocol

from cortex.contracts.pipeline_events import PipelineEventEnvelope


class EventBus(Protocol):
    async def publish(self, event: PipelineEventEnvelope) -> None: ...


class KafkaEventBus:
    async def publish(self, event: PipelineEventEnvelope) -> None:
        raise NotImplementedError("KafkaEventBus is implemented in Phase 2")
