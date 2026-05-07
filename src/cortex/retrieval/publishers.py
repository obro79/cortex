from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import EvidencePack
from cortex.contracts.pipeline_events import (
    PipelineCausation,
    PipelineEventEnvelope,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
)
from cortex.events.bus import EventBus


class EvidencePackPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_created(
        self, evidence_pack: EvidencePack
    ) -> PipelineEventEnvelope:
        envelope = PipelineEventEnvelope(
            event_id=f"evt_ep_{uuid4().hex}",
            event_type="evidence_pack.created",
            published_at=datetime.now(UTC),
            workspace_id=evidence_pack.workspace_id,
            partition_key=f"{evidence_pack.workspace_id}:{evidence_pack.id}",
            subject=PipelineSubject(type="evidence_pack", id=evidence_pack.id),
            causation=PipelineCausation(
                retrieval_request_id=evidence_pack.retrieval_request_id
            ),
            trace=PipelineTrace(trace_id=f"trace_{evidence_pack.id}"),
            producer=PipelineProducer(service="retrieval", instance_id="local"),
            payload={
                "status": evidence_pack.status,
                "candidate_count": evidence_pack.candidate_summary_json.get(
                    "candidate_count", 0
                ),
                "token_budget": evidence_pack.token_budget,
                "operation": "created",
            },
        )
        await self.event_bus.publish(envelope)
        return envelope
