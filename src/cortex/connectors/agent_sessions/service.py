"""Shared-ingestion adapter for explicit structured checkpoint exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cortex.contracts.agent_sessions import AgentCheckpointExport
from cortex.ingestion.payloads import sha256_digest
from cortex.ingestion.raw_events import RawEventInput


class SharedIngestionSeam(Protocol):
    async def ingest(self, item: RawEventInput) -> object: ...


@dataclass(frozen=True)
class AgentCheckpointImportExecution:
    result: object


@dataclass(frozen=True)
class AgentCheckpointImportPlan:
    """Submit one caller-exported checkpoint without contacting an agent provider."""

    workspace_id: str
    source_connection_id: str
    checkpoint: AgentCheckpointExport

    def __post_init__(self) -> None:
        if not self.workspace_id.strip() or not self.source_connection_id.strip():
            raise ValueError("workspace_id and source_connection_id are required")

    async def execute(
        self, ingestion: SharedIngestionSeam
    ) -> AgentCheckpointImportExecution:
        return AgentCheckpointImportExecution(
            result=await ingestion.ingest(self.raw_event())
        )

    def raw_event(self) -> RawEventInput:
        checkpoint = self.checkpoint
        event_identity = sha256_digest(
            f"{checkpoint.checkpoint_id}:{checkpoint.content_hash}".encode()
        ).removeprefix("sha256:")
        return RawEventInput(
            workspace_id=self.workspace_id,
            source_connection_id=self.source_connection_id,
            provider="agent_session",
            external_event_id=f"agent_checkpoint:{event_identity}",
            event_type="agent_session.checkpoint.exported",
            external_object_key=f"agent_session:checkpoint:{checkpoint.checkpoint_id}",
            idempotency_key=(
                f"agent_session:{self.workspace_id}:{checkpoint.checkpoint_id}:"
                f"{checkpoint.content_hash}"
            ),
            payload=checkpoint.to_payload(),
        )
