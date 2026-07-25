"""Planned Google Drive snapshot import plan; OAuth and API calls are absent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cortex.ingestion.raw_events import RawEventInput

from .models import GoogleDriveFileSnapshot, GoogleDriveSnapshotPage


class SharedIngestionSeam(Protocol):
    async def ingest(self, item: RawEventInput) -> object: ...


@dataclass(frozen=True)
class GoogleDriveImportExecution:
    submitted: int
    results: tuple[object, ...]


@dataclass(frozen=True)
class GoogleDriveImportPlan:
    """An executable plan for importing a supplied Google Drive snapshot page."""

    workspace_id: str
    source_connection_id: str
    snapshot: GoogleDriveSnapshotPage

    def __post_init__(self) -> None:
        if not self.workspace_id.strip() or not self.source_connection_id.strip():
            raise ValueError("workspace_id and source_connection_id are required")

    async def execute(
        self, ingestion: SharedIngestionSeam
    ) -> GoogleDriveImportExecution:
        results: list[object] = []
        for file in self.snapshot.files:
            results.append(await ingestion.ingest(self._raw_event(file)))
        return GoogleDriveImportExecution(
            submitted=len(results), results=tuple(results)
        )

    def _raw_event(self, file: GoogleDriveFileSnapshot) -> RawEventInput:
        version = file.modified_at or "snapshot"
        return RawEventInput(
            workspace_id=self.workspace_id,
            source_connection_id=self.source_connection_id,
            provider="google_drive",
            external_event_id=f"google_drive.file:{file.file_id}:{version}",
            event_type="google_drive.file.snapshot",
            external_object_key=f"google_drive:file:{file.file_id}",
            idempotency_key=(
                f"google_drive:{self.workspace_id}:file:{file.file_id}:{version}"
            ),
            payload={"connector_mode": "planned_snapshot", "file": file.to_payload()},
        )
