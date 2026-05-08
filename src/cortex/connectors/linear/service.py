from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from cortex.events.bus import EventBus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import IngestionResult, RawEventIngestionService


class LinearIngestionService(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


@dataclass
class LinearConnectorServices:
    api_token_configured: bool = False
    source_ids: set[str] = field(default_factory=set)
    raw_events: InMemoryRawEventRepository = field(
        default_factory=InMemoryRawEventRepository
    )
    payload_store: PayloadStore = field(default_factory=InMemoryPayloadStore)
    event_bus: EventBus = field(default_factory=InMemoryEventBus)
    ingestion: LinearIngestionService | None = None

    def __post_init__(self) -> None:
        if self.ingestion is None:
            self.ingestion = RawEventIngestionService(
                repository=self.raw_events,
                payload_store=self.payload_store,
                publisher=RawEventPublisher(self.event_bus),
            )

    def install_api_token(self, *, workspace_id: str, token: str) -> dict[str, object]:
        self.api_token_configured = bool(token)
        return {
            "ok": self.api_token_configured,
            "workspace_id": workspace_id,
            "auth_type": "api_token",
            "secret_ref": "linear_api_token" if token else None,
        }

    def select_sources(
        self, *, workspace_id: str, sources: list[dict[str, Any]]
    ) -> dict[str, object]:
        selected = []
        for source in sources:
            source_id = str(source.get("id", ""))
            source_type = str(source.get("type", "project"))
            if not source_id or source_type not in {"team", "project"}:
                continue
            self.source_ids.add(source_id)
            selected.append({"id": source_id, "type": source_type})
        return {"ok": True, "workspace_id": workspace_id, "selected": selected}

    async def backfill(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        issues: list[dict[str, Any]],
    ) -> dict[str, object]:
        created = 0
        duplicates = 0
        ingestion = self.ingestion
        assert ingestion is not None
        for issue in issues:
            scope_id = _scope_id(issue)
            if self.source_ids and scope_id not in self.source_ids:
                continue
            issue_id = str(issue.get("id", issue.get("identifier", "")))
            if not issue_id:
                continue
            result = await ingestion.ingest(
                RawEventInput(
                    workspace_id=workspace_id,
                    source_connection_id=source_connection_id,
                    provider="linear",
                    external_event_id=f"linear.issue:{issue_id}",
                    event_type="linear.issue",
                    external_object_key=f"linear:{issue.get('identifier', issue_id)}",
                    idempotency_key=f"linear:{workspace_id}:issue:{issue_id}",
                    payload={"issue": issue},
                )
            )
            created += int(result.created)
            duplicates += int(not result.created)
        return {"ok": True, "raw_events_created": created, "duplicates": duplicates}

    def health(self, workspace_id: str) -> dict[str, object]:
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "provider": "linear",
            "auth_status": "active" if self.api_token_configured else "missing_token",
            "selected_source_count": len(self.source_ids),
        }


def _scope_id(issue: dict[str, Any]) -> str | None:
    for key in ("project", "team"):
        value = issue.get(key)
        if isinstance(value, dict) and value.get("id"):
            return str(value["id"])
    return None
