from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import CanonicalDecision
from cortex.contracts.pipeline_events import (
    PipelineCausation,
    PipelineEventEnvelope,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
)
from cortex.events.bus import EventBus


class CanonicalDecisionPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_approved(
        self, decision: CanonicalDecision, *, action: str
    ) -> PipelineEventEnvelope:
        envelope = PipelineEventEnvelope(
            event_id=f"evt_cd_{uuid4().hex}",
            event_type="canonical_decision.approved",
            published_at=datetime.now(UTC),
            workspace_id=decision.workspace_id,
            partition_key=f"{decision.workspace_id}:{decision.id}",
            subject=PipelineSubject(type="canonical_decision", id=decision.id),
            causation=PipelineCausation(),
            trace=PipelineTrace(trace_id=f"trace_{decision.id}"),
            producer=PipelineProducer(service="canonical-memory", instance_id="local"),
            payload={
                "action": action,
                "status": decision.status,
                "scope_type": decision.scope_type,
                "operation": "approved",
            },
        )
        await self.event_bus.publish(envelope)
        return envelope
