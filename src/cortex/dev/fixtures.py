from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from cortex.contracts.entities import (
    EmbeddingRecord,
    RawEvent,
    SourceChunk,
    SourceFile,
    SourceObject,
)
from cortex.contracts.enums import (
    EmbeddingJobStatus,
    RawEventStatus,
    SourceChunkStatus,
    SourceObjectStatus,
)

WORKSPACE_ID = "ws_dev_cor_123"
SOURCE_CONNECTION_ID = "src_dev_fixtures"
FIXTURE_TIME = datetime(2026, 5, 6, 18, 12, tzinfo=UTC)


@dataclass(frozen=True)
class FixtureDefinition:
    fixture_id: str
    provider: str
    object_type: str
    title: str
    citation_label: str
    citation_url: str
    content: str
    source_kind: str
    is_stale: bool = False
    creates_file: bool = False


FIXTURES: tuple[FixtureDefinition, ...] = (
    FixtureDefinition(
        fixture_id="slack-thread-sessions-postgres",
        provider="slack",
        object_type="slack_thread",
        title="Decision: move sessions to Postgres",
        citation_label="Slack #architecture session decision",
        citation_url="https://fixtures.local/slack/session-postgres",
        content="Architecture approved Postgres as the source of truth for sessions.",
        source_kind="slack_decision",
    ),
    FixtureDefinition(
        fixture_id="slack-file-session-flow-diagram",
        provider="slack",
        object_type="diagram_file",
        title="Session flow diagram OCR",
        citation_label="Slack diagram session-flow.png OCR",
        citation_url="https://fixtures.local/slack/session-flow-diagram",
        content=(
            "OCR: browser writes session token, middleware validates Postgres "
            "session, API loads user."
        ),
        source_kind="diagram_ocr",
        creates_file=True,
    ),
    FixtureDefinition(
        fixture_id="linear-issue-COR-123",
        provider="linear",
        object_type="linear_issue",
        title="COR-123 migrate session reads to Postgres",
        citation_label="Linear COR-123",
        citation_url="https://fixtures.local/linear/COR-123",
        content="Implement COR-123 by migrating session reads and writes to Postgres.",
        source_kind="linear_task",
    ),
    FixtureDefinition(
        fixture_id="linear-issue-COR-119",
        provider="linear",
        object_type="linear_issue",
        title="COR-119 middleware fallback blocker",
        citation_label="Linear COR-119",
        citation_url="https://fixtures.local/linear/COR-119",
        content=(
            "Blocker: middleware fallback must remain until Postgres session "
            "rollout is complete."
        ),
        source_kind="linear_blocker",
    ),
    FixtureDefinition(
        fixture_id="github-pr-184",
        provider="github",
        object_type="pull_request",
        title="PR 184 partially migrates session writes",
        citation_label="GitHub PR #184",
        citation_url="https://fixtures.local/github/pull/184",
        content=(
            "PR 184 migrates session writes to Postgres but keeps Redis read fallback."
        ),
        source_kind="github_pr",
    ),
    FixtureDefinition(
        fixture_id="repo-doc-session-storage",
        provider="repo_docs",
        object_type="doc_section",
        title="Stale session storage doc",
        citation_label="Repo docs session storage",
        citation_url="https://fixtures.local/docs/session-storage",
        content="Legacy doc says Redis is the source of truth for sessions.",
        source_kind="repo_doc",
        is_stale=True,
    ),
)


def stable_hash(value: str) -> str:
    return f"sha256:{sha256(value.encode()).hexdigest()}"


def fixture_ids() -> list[str]:
    return [fixture.fixture_id for fixture in FIXTURES]


class FixtureRepository:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.raw_events: dict[str, RawEvent] = {}
        self.source_objects: dict[str, SourceObject] = {}
        self.source_files: dict[str, SourceFile] = {}
        self.source_chunks: dict[str, SourceChunk] = {}
        self.embeddings: dict[str, EmbeddingRecord] = {}
        self.relationships: list[dict[str, Any]] = []

    def seed(self) -> dict[str, Any]:
        for fixture in FIXTURES:
            self._upsert_fixture(fixture)
        self.relationships = [
            {
                "id": "rel-cor-123-slack-decision",
                "from_id": "so-linear-issue-COR-123",
                "to_id": "so-slack-thread-sessions-postgres",
                "type": "constrained_by_decision",
                "confidence": 1.0,
            },
            {
                "id": "rel-cor-123-stale-doc-conflict",
                "from_id": "so-linear-issue-COR-123",
                "to_id": "so-repo-doc-session-storage",
                "type": "conflicts_with_stale_doc",
                "confidence": 1.0,
            },
            {
                "id": "rel-cor-123-pr-184",
                "from_id": "so-linear-issue-COR-123",
                "to_id": "so-github-pr-184",
                "type": "implemented_by",
                "confidence": 0.9,
            },
        ]
        return self.summary()

    def summary(self) -> dict[str, Any]:
        return {
            "workspace_id": WORKSPACE_ID,
            "fixture_ids": fixture_ids(),
            "raw_event_ids": sorted(self.raw_events),
            "source_object_ids": sorted(self.source_objects),
            "source_file_ids": sorted(self.source_files),
            "source_chunk_ids": sorted(self.source_chunks),
            "embedding_ids": sorted(self.embeddings),
            "relationship_ids": [
                relationship["id"] for relationship in self.relationships
            ],
            "counts": {
                "raw_events": len(self.raw_events),
                "source_objects": len(self.source_objects),
                "source_files": len(self.source_files),
                "source_chunks": len(self.source_chunks),
                "embeddings": len(self.embeddings),
                "relationships": len(self.relationships),
            },
        }

    def seeded(self) -> bool:
        return len(self.source_objects) == len(FIXTURES)

    def source_ids(self) -> set[str]:
        return {*self.source_objects, *self.source_files}

    def _upsert_fixture(self, fixture: FixtureDefinition) -> None:
        raw_id = f"raw-{fixture.fixture_id}"
        source_object_id = f"so-{fixture.fixture_id}"
        chunk_id = f"chunk-{fixture.fixture_id}"
        embedding_id = f"emb-{fixture.fixture_id}"
        payload_hash = stable_hash(f"payload:{fixture.fixture_id}")
        content_hash = stable_hash(fixture.content)

        self.raw_events[raw_id] = RawEvent(
            id=raw_id,
            workspace_id=WORKSPACE_ID,
            source_connection_id=SOURCE_CONNECTION_ID,
            provider=fixture.provider,
            external_event_id=f"evt-{fixture.fixture_id}",
            event_type=f"{fixture.provider}.{fixture.object_type}.fixture",
            external_object_key=f"{fixture.provider}:{fixture.fixture_id}",
            idempotency_key=f"fixture:{fixture.fixture_id}",
            payload_ref=f"fixture://{fixture.fixture_id}",
            payload_hash=payload_hash,
            payload_size_bytes=len(fixture.content),
            occurred_at=FIXTURE_TIME,
            received_at=FIXTURE_TIME,
            published_at=FIXTURE_TIME,
            processed_at=FIXTURE_TIME,
            status=RawEventStatus.PROCESSED,
            trace_id="trace-dev-cor-123",
            created_at=FIXTURE_TIME,
            updated_at=FIXTURE_TIME,
        )
        self.source_objects[source_object_id] = SourceObject(
            id=source_object_id,
            workspace_id=WORKSPACE_ID,
            source_connection_id=SOURCE_CONNECTION_ID,
            provider=fixture.provider,
            object_type=fixture.object_type,
            external_object_id=fixture.fixture_id,
            external_object_key=f"{fixture.provider}:{fixture.fixture_id}",
            title=fixture.title,
            canonical_url=fixture.citation_url,
            occurred_at=FIXTURE_TIME,
            source_updated_at=FIXTURE_TIME,
            normalized_version="fixture-normalizer-v1",
            content_hash=content_hash,
            metadata_json={
                "fixture_id": fixture.fixture_id,
                "source_kind": fixture.source_kind,
                "is_stale": fixture.is_stale,
            },
            status=SourceObjectStatus.STALE
            if fixture.is_stale
            else SourceObjectStatus.ACTIVE,
            trace_id="trace-dev-cor-123",
            created_at=FIXTURE_TIME,
            updated_at=FIXTURE_TIME,
        )
        source_file_id = None
        if fixture.creates_file:
            source_file_id = f"file-{fixture.fixture_id}"
            self.source_files[source_file_id] = SourceFile(
                id=source_file_id,
                workspace_id=WORKSPACE_ID,
                source_object_id=source_object_id,
                source_connection_id=SOURCE_CONNECTION_ID,
                provider=fixture.provider,
                external_file_id=fixture.fixture_id,
                external_object_key=f"{fixture.provider}:{fixture.fixture_id}",
                file_name_hash=stable_hash("session-flow.png"),
                content_type="image/png",
                storage_ref=f"fixture://files/{fixture.fixture_id}",
                content_hash=content_hash,
                metadata_json={
                    "ocr_fixture": True,
                    "citation_label": fixture.citation_label,
                },
                trace_id="trace-dev-cor-123",
                created_at=FIXTURE_TIME,
                updated_at=FIXTURE_TIME,
            )
        self.source_chunks[chunk_id] = SourceChunk(
            id=chunk_id,
            workspace_id=WORKSPACE_ID,
            source_object_id=source_object_id,
            source_file_id=source_file_id,
            chunk_type="ocr_text" if fixture.creates_file else fixture.object_type,
            chunk_index=0,
            text=fixture.content,
            text_hash=stable_hash(fixture.content),
            token_count=len(fixture.content.split()),
            chunking_version="fixture-chunker-v1",
            citation_label=fixture.citation_label,
            citation_url=fixture.citation_url,
            metadata_json={
                "fixture_id": fixture.fixture_id,
                "source_kind": fixture.source_kind,
                "is_stale": fixture.is_stale,
            },
            status=SourceChunkStatus.STALE
            if fixture.is_stale
            else SourceChunkStatus.ACTIVE,
            created_from_hash=content_hash,
            created_at=FIXTURE_TIME,
            updated_at=FIXTURE_TIME,
        )
        self.embeddings[embedding_id] = EmbeddingRecord(
            id=embedding_id,
            workspace_id=WORKSPACE_ID,
            source_chunk_id=chunk_id,
            provider="deterministic",
            model="fixture-vector-v1",
            dimensions=8,
            task_type="retrieval_document",
            embedding_version="fixture-embedding-v1",
            chunking_version="fixture-chunker-v1",
            input_text_hash=stable_hash(fixture.content),
            vector_hash=stable_hash(f"vector:{fixture.fixture_id}"),
            qdrant_collection="fixture-cortex-dev",
            qdrant_point_id=f"point-{fixture.fixture_id}",
            status=EmbeddingJobStatus.COMPLETED,
            created_at=FIXTURE_TIME,
            updated_at=FIXTURE_TIME,
        )
