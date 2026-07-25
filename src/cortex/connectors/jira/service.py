"""Planned Jira snapshot import plan; live auth and API calls are absent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cortex.ingestion.raw_events import RawEventInput

from .models import JiraIssueSnapshot, JiraSnapshotPage


class SharedIngestionSeam(Protocol):
    async def ingest(self, item: RawEventInput) -> object: ...


@dataclass(frozen=True)
class JiraImportExecution:
    submitted: int
    results: tuple[object, ...]


@dataclass(frozen=True)
class JiraImportPlan:
    """An executable plan for importing a supplied Jira snapshot page."""

    workspace_id: str
    source_connection_id: str
    snapshot: JiraSnapshotPage

    def __post_init__(self) -> None:
        if not self.workspace_id.strip() or not self.source_connection_id.strip():
            raise ValueError("workspace_id and source_connection_id are required")

    async def execute(self, ingestion: SharedIngestionSeam) -> JiraImportExecution:
        results: list[object] = []
        for issue in self.snapshot.issues:
            results.append(await ingestion.ingest(self._raw_event(issue)))
        return JiraImportExecution(submitted=len(results), results=tuple(results))

    def _raw_event(self, issue: JiraIssueSnapshot) -> RawEventInput:
        version = issue.updated_at or "snapshot"
        return RawEventInput(
            workspace_id=self.workspace_id,
            source_connection_id=self.source_connection_id,
            provider="jira",
            external_event_id=f"jira.issue:{issue.issue_id}:{version}",
            event_type="jira.issue.snapshot",
            external_object_key=f"jira:issue:{issue.issue_key}",
            idempotency_key=(
                f"jira:{self.workspace_id}:issue:{issue.issue_id}:{version}"
            ),
            payload={"connector_mode": "planned_snapshot", "issue": issue.to_payload()},
        )
