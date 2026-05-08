from __future__ import annotations

from datetime import UTC, datetime

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.context_gate.publishers import ContextGatePublisher
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.context_gate.service import ContextGateService
from cortex.contracts.entities import SourceObject
from cortex.contracts.enums import ContextGateStatus, SourceObjectStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.ingestion.payloads import sha256_digest
from cortex.normalization.repositories import InMemoryRelationshipSeedRepository
from cortex.relationships.service import DeterministicRelationshipBuilder
from cortex.retrieval.publishers import EvidencePackPublisher
from cortex.retrieval.repositories import (
    InMemoryEvidencePackRepository,
    InMemoryRetrievalRequestRepository,
)
from cortex.retrieval.service import RetrievalService


async def test_cor_123_query_expands_to_slack_github_and_docs_and_blocks() -> None:
    query = "I'm implementing Linear issue COR-123. What docs and PRs constrain this?"
    objects = [
        source_object(
            "linear",
            "linear_issue",
            "so_linear",
            (
                "COR-123: Move sessions to Postgres\n"
                "See #12 and docs/architecture/session.md."
            ),
            {"source_kind": "linear_issue", "identifier": "COR-123"},
        ),
        source_object(
            "github",
            "github_pull_request",
            "so_pr",
            "PR #12 implements COR-123 and changed src/cortex/session.py.",
            {
                "source_kind": "github_pull_request",
                "number": 12,
                "changed_file_paths": ["src/cortex/session.py"],
            },
        ),
        source_object(
            "repo_docs",
            "repo_doc",
            "so_doc",
            "Redis is the session source of truth.",
            {
                "source_kind": "repo_doc",
                "path": "docs/architecture/session.md",
                "is_stale": True,
            },
        ),
        source_object(
            "slack",
            "slack_thread",
            "so_slack",
            "Slack decision: COR-123 should use Postgres, not Redis.",
            {"source_kind": "slack_message"},
        ),
    ]
    config = load_retrieval_config()
    chunks = InMemorySourceChunkRepository()
    chunker = SourceAwareChunker(config.chunking)
    for item in objects:
        chunks.upsert_many(chunker.chunks_for_source_object(item))
    relationships = InMemoryRelationshipSeedRepository()
    built = DeterministicRelationshipBuilder().build(
        workspace_id="ws_1",
        source_objects=objects,
        raw_event_id="raw_phase9",
    )
    relationships.upsert_many(built.seeds)
    bus = InMemoryEventBus()
    retrieval = RetrievalService(
        config=config,
        source_chunks=chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(bus),
        relationship_seeds=relationships,
    )

    response = await retrieval.retrieve_context(
        workspace_id="ws_1",
        query=query,
    )
    gate = ContextGateService(
        retrieval_service=retrieval,
        repository=InMemoryContextGateResultRepository(),
        publisher=ContextGatePublisher(bus),
    )
    gate_response = await gate.check_context_gate(
        workspace_id="ws_1",
        query=query,
    )

    providers = response.evidence_pack["source_coverage_json"]["providers"]
    assert providers == ["github", "linear", "repo_docs", "slack"]
    assert "Linear issue" in response.text
    assert "GitHub pull request" in response.text
    assert "Repo doc" in response.text
    assert "Slack thread" in response.text
    assert response.evidence_pack["conflict_summary_json"]["conflict_count"] == 1
    assert gate_response.status == ContextGateStatus.BLOCK


async def test_relationship_expansion_preserves_source_allowlist() -> None:
    objects = [
        source_object(
            "linear",
            "linear_issue",
            "so_linear",
            "COR-123: Move sessions to Postgres\nSee #12.",
            {"source_kind": "linear_issue", "identifier": "COR-123"},
        ),
        source_object(
            "github",
            "github_pull_request",
            "so_pr",
            "PR #12 implements COR-123.",
            {"source_kind": "github_pull_request", "number": 12},
        ),
    ]
    config = load_retrieval_config()
    chunks = InMemorySourceChunkRepository()
    chunker = SourceAwareChunker(config.chunking)
    for item in objects:
        chunks.upsert_many(chunker.chunks_for_source_object(item))
    relationships = InMemoryRelationshipSeedRepository()
    relationships.upsert_many(
        DeterministicRelationshipBuilder()
        .build(
            workspace_id="ws_1",
            source_objects=objects,
            raw_event_id="raw_phase9",
        )
        .seeds
    )
    retrieval = RetrievalService(
        config=config,
        source_chunks=chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(InMemoryEventBus()),
        relationship_seeds=relationships,
    )

    response = await retrieval.retrieve_context(
        workspace_id="ws_1",
        query="COR-123 #12",
        source_allowlist=["so_linear"],
    )

    citations = response.evidence_pack["citations_json"]["items"]
    assert [citation["source_object_id"] for citation in citations] == ["so_linear"]
    assert response.evidence_pack["permission_exclusions_json"]["excluded_count"] > 0


def source_object(
    provider: str,
    object_type: str,
    object_id: str,
    content: str,
    metadata: dict[str, object],
) -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id=object_id,
        workspace_id="ws_1",
        source_connection_id=f"src_{provider}",
        provider=provider,
        object_type=object_type,
        external_object_id=object_id,
        external_object_key=f"{provider}:{object_id}",
        title=object_id,
        content_text=content,
        content_hash=sha256_digest(content.encode()),
        metadata_json=metadata,
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
