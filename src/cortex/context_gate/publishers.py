from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import ContextGateResult
from cortex.contracts.pipeline_events import (
    PipelineCausation,
    PipelineEventEnvelope,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
    PipelineVersions,
)
from cortex.events.bus import EventBus


class ContextGatePublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_completed(
        self, result: ContextGateResult
    ) -> PipelineEventEnvelope:
        envelope = PipelineEventEnvelope(
            event_id=f"evt_gate_{uuid4().hex}",
            event_type="context_gate.completed",
            published_at=datetime.now(UTC),
            workspace_id=result.workspace_id,
            partition_key=f"{result.workspace_id}:{result.id}",
            subject=PipelineSubject(type="context_gate_result", id=result.id),
            causation=PipelineCausation(
                retrieval_request_id=result.retrieval_request_id
            ),
            versions=PipelineVersions(gate_version=result.gate_version),
            trace=PipelineTrace(trace_id=result.trace_id or f"trace_{result.id}"),
            producer=PipelineProducer(service="context-gate", instance_id="local"),
            payload={
                "status": result.status,
                "risk_category": result.risk_category,
                "operation": "completed",
            },
        )
        await self.event_bus.publish(envelope)
        return envelope
