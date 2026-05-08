from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from cortex.events.bus import EventBus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import IngestionResult, RawEventIngestionService


class GitHubIngestionService(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


@dataclass
class GitHubConnectorServices:
    app_configured: bool = False
    webhook_secret: str = ""
    repo_ids: set[str] = field(default_factory=set)
    raw_events: InMemoryRawEventRepository = field(
        default_factory=InMemoryRawEventRepository
    )
    payload_store: PayloadStore = field(default_factory=InMemoryPayloadStore)
    event_bus: EventBus = field(default_factory=InMemoryEventBus)
    ingestion: GitHubIngestionService | None = None

    def __post_init__(self) -> None:
        if self.ingestion is None:
            self.ingestion = RawEventIngestionService(
                repository=self.raw_events,
                payload_store=self.payload_store,
                publisher=RawEventPublisher(self.event_bus),
            )

    def install_app(
        self, *, workspace_id: str, app_id: str, private_key: str
    ) -> dict[str, object]:
        self.app_configured = bool(app_id and private_key)
        return {
            "ok": self.app_configured,
            "workspace_id": workspace_id,
            "auth_type": "github_app",
            "app_id": app_id if app_id else None,
            "private_key_ref": "github_private_key" if private_key else None,
        }

    def select_repos(
        self, *, workspace_id: str, repos: list[dict[str, Any]]
    ) -> dict[str, object]:
        selected = []
        for repo in repos:
            repo_id = str(repo.get("id", ""))
            if repo_id:
                self.repo_ids.add(repo_id)
                selected.append({"id": repo_id})
        return {"ok": True, "workspace_id": workspace_id, "selected": selected}

    async def backfill(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        events: list[dict[str, Any]],
    ) -> dict[str, object]:
        created = 0
        duplicates = 0
        ingestion = self.ingestion
        assert ingestion is not None
        for event in events:
            repo_id = _repo_id(event)
            if self.repo_ids and repo_id not in self.repo_ids:
                continue
            event_id = _event_id(event)
            result = await ingestion.ingest(
                RawEventInput(
                    workspace_id=workspace_id,
                    source_connection_id=source_connection_id,
                    provider="github",
                    external_event_id=event_id,
                    event_type=f"github.{_event_kind(event)}",
                    external_object_key=f"github:{repo_id}:{event_id}",
                    idempotency_key=f"github:{workspace_id}:{event_id}",
                    payload=event,
                )
            )
            created += int(result.created)
            duplicates += int(not result.created)
        return {"ok": True, "raw_events_created": created, "duplicates": duplicates}

    async def webhook(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        body: bytes,
        signature: str,
        event_name: str,
        delivery_id: str,
    ) -> dict[str, object]:
        if not _valid_signature(body, signature, self.webhook_secret):
            return {"ok": False, "status": "invalid_signature"}
        payload = json.loads(body)
        ingestion = self.ingestion
        assert ingestion is not None
        result = await ingestion.ingest(
            RawEventInput(
                workspace_id=workspace_id,
                source_connection_id=source_connection_id,
                provider="github",
                external_event_id=delivery_id,
                event_type=f"github.{event_name}",
                external_object_key=f"github:{delivery_id}",
                idempotency_key=f"github:{workspace_id}:delivery:{delivery_id}",
                payload=payload,
            )
        )
        return {"ok": True, "status": "persisted", "raw_event_created": result.created}

    def health(self, workspace_id: str) -> dict[str, object]:
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "provider": "github",
            "auth_status": "active" if self.app_configured else "missing_app",
            "selected_source_count": len(self.repo_ids),
        }


def _repo_id(event: dict[str, Any]) -> str:
    repo = event.get("repository")
    if isinstance(repo, dict) and repo.get("id"):
        return str(repo["id"])
    return str(event.get("repository_id", "unknown-repo"))


def _event_id(event: dict[str, Any]) -> str:
    for key in ("pull_request", "issue", "commit"):
        value = event.get(key)
        if isinstance(value, dict):
            return f"{key}:{value.get('id') or value.get('sha') or value.get('number')}"
    return str(event.get("id", "github-event"))


def _event_kind(event: dict[str, Any]) -> str:
    for key in ("pull_request", "issue", "commit"):
        if isinstance(event.get(key), dict):
            return key
    return str(event.get("object_kind", "event"))


def _valid_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
