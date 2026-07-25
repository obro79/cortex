from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cortex.contracts.pipeline_events import (
    PipelineEventEnvelope,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
)
from cortex.events.in_memory import InMemoryEventBus

from .evidence import EVIDENCE_PACK_ID, build_evidence_pack
from .fixtures import WORKSPACE_ID, FixtureRepository

STAGES = (
    "seed",
    "ingest",
    "kafka_event",
    "normalize",
    "chunk_ocr",
    "embed",
    "index",
    "link",
    "retrieve",
    "gate",
)


class FixturePipelineRunner:
    def __init__(
        self, repository: FixtureRepository, event_bus: InMemoryEventBus
    ) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def run(self, run_number: int) -> dict[str, Any]:
        if not self.repository.seeded():
            self.repository.seed()
        run_id = f"run-cor-123-{run_number:03d}"
        trace_id = f"trace-{run_id}"
        stage_records = []
        for stage in STAGES:
            event = self._event_for_stage(stage, run_id, trace_id)
            await self.event_bus.publish(event)
            stage_records.append(self._stage_record(stage, run_id, trace_id, event))
        evidence_pack = build_evidence_pack(self.repository)
        return {
            "run_id": run_id,
            "status": "completed",
            "trace_id": trace_id,
            "stages": stage_records,
            "event_ids": [stage["event_id"] for stage in stage_records],
            "artifact_ids": {
                "raw_events": sorted(self.repository.raw_events),
                "source_objects": sorted(self.repository.source_objects),
                "source_files": sorted(self.repository.source_files),
                "source_chunks": sorted(self.repository.source_chunks),
                "embeddings": sorted(self.repository.embeddings),
                "relationships": [
                    relationship["id"] for relationship in self.repository.relationships
                ],
                "evidence_pack": EVIDENCE_PACK_ID,
                "gate_result": evidence_pack["gate_result"]["id"],
            },
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }

    def _event_for_stage(
        self, stage: str, run_id: str, trace_id: str
    ) -> PipelineEventEnvelope:
        return PipelineEventEnvelope(
            event_id=f"evt-{run_id}-{stage}",
            event_type=f"dev_fixture.{stage}",
            occurred_at=datetime.now(UTC),
            published_at=datetime.now(UTC),
            workspace_id=WORKSPACE_ID,
            partition_key=f"{WORKSPACE_ID}:cor-123:{stage}",
            subject=PipelineSubject(type="dev_pipeline_stage", id=f"{run_id}:{stage}"),
            trace=PipelineTrace(trace_id=trace_id, pipeline_run_id=run_id),
            producer=PipelineProducer(service="dev-workbench", instance_id="local"),
            payload={
                "stage": stage,
                "fixture_count": len(self.repository.source_objects),
            },
        )

    def _stage_record(
        self, stage: str, run_id: str, trace_id: str, event: PipelineEventEnvelope
    ) -> dict[str, Any]:
        return {
            "stage": stage,
            "status": "completed",
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "input_ids": self._stage_inputs(stage),
            "output_ids": self._stage_outputs(stage),
            "event_id": event.event_id,
            "trace_id": trace_id,
            "idempotency_key": f"{run_id}:{stage}",
            "summary": f"{stage} completed for deterministic COR-123 fixtures",
            "error": None,
        }

    def _stage_inputs(self, stage: str) -> list[str]:
        if stage == "seed":
            return []
        if stage in {"ingest", "kafka_event"}:
            return sorted(self.repository.raw_events)
        if stage == "normalize":
            return sorted(self.repository.raw_events)
        if stage in {"chunk_ocr", "embed", "index", "link", "retrieve", "gate"}:
            return sorted(self.repository.source_objects)
        return []

    def _stage_outputs(self, stage: str) -> list[str]:
        if stage in {"seed", "ingest", "kafka_event"}:
            return sorted(self.repository.raw_events)
        if stage == "normalize":
            return sorted(self.repository.source_objects)
        if stage == "chunk_ocr":
            return sorted(self.repository.source_chunks)
        if stage == "embed":
            return sorted(self.repository.embeddings)
        if stage == "index":
            return [
                f"idx-{chunk_id}" for chunk_id in sorted(self.repository.source_chunks)
            ]
        if stage == "link":
            return [
                relationship["id"] for relationship in self.repository.relationships
            ]
        if stage == "retrieve":
            return [EVIDENCE_PACK_ID]
        if stage == "gate":
            return ["gate-cor-123"]
        return []
