from cortex.contracts.pipeline_events import PipelineEventEnvelope


class InMemoryEventBus:
    def __init__(self) -> None:
        self.events: list[PipelineEventEnvelope] = []

    async def publish(self, event: PipelineEventEnvelope) -> None:
        self.events.append(event)

    def list_events(self) -> list[PipelineEventEnvelope]:
        return list(self.events)
