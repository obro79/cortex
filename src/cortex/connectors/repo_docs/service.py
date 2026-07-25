from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from cortex.events.bus import EventBus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadStore, sha256_digest
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import IngestionResult, RawEventIngestionService


class RepoDocsIngestionService(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


@dataclass
class RepoDocsConnectorServices:
    roots: set[str] = field(default_factory=set)
    hashes: dict[str, str] = field(default_factory=dict)
    raw_events: InMemoryRawEventRepository = field(
        default_factory=InMemoryRawEventRepository
    )
    payload_store: PayloadStore = field(default_factory=InMemoryPayloadStore)
    event_bus: EventBus = field(default_factory=InMemoryEventBus)
    ingestion: RepoDocsIngestionService | None = None

    def __post_init__(self) -> None:
        if self.ingestion is None:
            self.ingestion = RawEventIngestionService(
                repository=self.raw_events,
                payload_store=self.payload_store,
                publisher=RawEventPublisher(self.event_bus),
            )

    def select_roots(
        self, *, workspace_id: str, roots: list[dict[str, Any]]
    ) -> dict[str, object]:
        selected = []
        for root in roots:
            path = str(root.get("path", "")).strip("/")
            if path:
                self.roots.add(path)
                selected.append({"path": path})
        return {"ok": True, "workspace_id": workspace_id, "selected": selected}

    async def import_docs(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        docs: list[dict[str, Any]],
    ) -> dict[str, object]:
        created = 0
        skipped = 0
        ingestion = self.ingestion
        assert ingestion is not None
        for doc in docs:
            path = str(doc.get("path", "")).strip("/")
            content = str(doc.get("content", ""))
            repo_id = str(doc.get("repo_id", "repo"))
            if not path or not self._allowed(path):
                continue
            digest = sha256_digest(content.encode())
            if self.hashes.get(path) == digest:
                skipped += 1
                continue
            self.hashes[path] = digest
            result = await ingestion.ingest(
                RawEventInput(
                    workspace_id=workspace_id,
                    source_connection_id=source_connection_id,
                    provider="repo_docs",
                    external_event_id=f"repo_docs:{repo_id}:{path}:{digest}",
                    event_type="repo_docs.imported",
                    external_object_key=f"doc:{repo_id}:{path}",
                    idempotency_key=f"repo_docs:{workspace_id}:{path}:{digest}",
                    payload=doc,
                )
            )
            created += int(result.created)
        return {"ok": True, "raw_events_created": created, "unchanged_skipped": skipped}

    def health(self, workspace_id: str) -> dict[str, object]:
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "provider": "repo_docs",
            "selected_root_count": len(self.roots),
            "imported_doc_count": len(self.hashes),
        }

    def _allowed(self, path: str) -> bool:
        return not self.roots or any(
            path == root or path.startswith(f"{root}/") for root in self.roots
        )
