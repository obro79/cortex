"""Bounded, credential-free GitHub snapshot import plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cortex.ingestion.raw_events import RawEventInput

from .snapshot import (
    GitHubSnapshotEvent,
    GitHubSnapshotPage,
    GitHubSnapshotPageInput,
)


class SharedIngestionSeam(Protocol):
    async def ingest(self, item: RawEventInput) -> object: ...


@dataclass(frozen=True)
class GitHubImportExecution:
    submitted: int
    results: tuple[object, ...]
    next_page_input: GitHubSnapshotPageInput | None


@dataclass(frozen=True)
class GitHubImportPlan:
    """Execute exactly one supplied snapshot page through an injected seam."""

    workspace_id: str
    source_connection_id: str
    snapshot: GitHubSnapshotPage

    def __post_init__(self) -> None:
        if not self.workspace_id.strip() or not self.source_connection_id.strip():
            raise ValueError("workspace_id and source_connection_id are required")

    async def execute(self, ingestion: SharedIngestionSeam) -> GitHubImportExecution:
        results: list[object] = []
        for event in self.snapshot.events:
            results.append(await ingestion.ingest(self._raw_event(event)))
        return GitHubImportExecution(
            submitted=len(results),
            results=tuple(results),
            next_page_input=self.snapshot.next_page_input,
        )

    def _raw_event(self, event: GitHubSnapshotEvent) -> RawEventInput:
        version = event.updated_at or "snapshot"
        event_identity = (
            f"github.{event.object_kind}:{event.repository_id}:"
            f"{event.object_id}:{version}"
        )
        return RawEventInput(
            workspace_id=self.workspace_id,
            source_connection_id=self.source_connection_id,
            provider="github",
            external_event_id=event_identity,
            event_type=f"github.{event.object_kind}.snapshot",
            external_object_key=(
                f"github:{event.repository_id}:{event.object_kind}:{event.object_id}"
            ),
            idempotency_key=f"github:{self.workspace_id}:{event_identity}",
            payload={"connector_mode": "planned_snapshot", "event": event.to_payload()},
        )
