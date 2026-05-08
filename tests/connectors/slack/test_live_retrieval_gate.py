from __future__ import annotations

import json

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.publishers import SourceChunkPublisher
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.service import ChunkingService
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.context_gate.publishers import ContextGatePublisher
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.context_gate.service import ContextGateService
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.embeddings.publishers import EmbeddingPublisher
from cortex.embeddings.repositories import InMemoryEmbeddingRecordRepository
from cortex.embeddings.service import EmbeddingService
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.normalization.publishers import SourceFilePublisher, SourceObjectPublisher
from cortex.normalization.repositories import (
    InMemoryRelationshipSeedRepository,
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
)
from cortex.normalization.service import SourceNormalizationService
from cortex.retrieval.publishers import EvidencePackPublisher
from cortex.retrieval.repositories import (
    InMemoryEvidencePackRepository,
    InMemoryRetrievalRequestRepository,
)
from cortex.retrieval.service import RetrievalService
from cortex.workers.embeddings import EmbeddingWorkerSkeleton

from .helpers import installed_selected_services, signed_headers

MESSAGE_TEXT = "Project comet launch decision needs the retrieval gate"


async def test_live_slack_event_reaches_retrieval_and_context_gate() -> None:
    services, _install, _selected = await installed_selected_services()
    raw_envelope = await _persist_selected_message(services)
    source_objects = InMemorySourceObjectRepository()
    source_files = InMemorySourceFileRepository()
    source_chunks = InMemorySourceChunkRepository()
    normalization = SourceNormalizationService(
        raw_events=services.raw_events,
        payload_store=services.payload_store,
        source_objects=source_objects,
        source_files=source_files,
        relationship_seeds=InMemoryRelationshipSeedRepository(),
        source_object_publisher=SourceObjectPublisher(services.event_bus),
        source_file_publisher=SourceFilePublisher(services.event_bus),
    )
    normalized = await normalization.handle_raw_event_persisted(raw_envelope)
    source_envelope = services.event_bus.list_events()[1]
    chunking = ChunkingService(
        source_objects=source_objects,
        source_files=source_files,
        source_chunks=source_chunks,
        chunker=SourceAwareChunker(load_retrieval_config().chunking),
        publisher=SourceChunkPublisher(services.event_bus),
    )

    chunked = await chunking.handle_source_object_upserted(source_envelope)
    embedding_worker = _embedding_worker(source_chunks, services.event_bus)
    queued_embedding = await embedding_worker.handle_source_chunk_upserted(
        services.event_bus.list_events()[2]
    )
    completed_embedding = await embedding_worker.handle_embedding_requested(
        services.event_bus.list_events()[3]
    )
    retrieval = _retrieval_service(source_chunks, services.event_bus)
    response = await retrieval.retrieve_context(
        workspace_id="ws_1",
        query="project comet launch decision",
        provider_filters=["slack"],
    )
    gate = ContextGateService(
        retrieval_service=retrieval,
        repository=InMemoryContextGateResultRepository(),
        publisher=ContextGatePublisher(services.event_bus),
    )
    gate_response = await gate.check_context_gate(
        workspace_id="ws_1",
        query="project comet launch decision",
        provider_filters=["slack"],
    )

    assert normalized.status == "processed"
    assert chunked.source_chunk_count == 1
    assert queued_embedding["status"] == "queued"
    assert completed_embedding["status"] == "completed"
    assert response.ok is True
    assert "Slack thread" in response.text
    assert MESSAGE_TEXT in response.text
    assert gate_response.ok is True
    assert gate_response.status == "allow"
    assert _event_payloads_are_content_free(services.event_bus)


async def test_duplicate_slack_event_replay_does_not_create_duplicate_chunks() -> None:
    services, _install, _selected = await installed_selected_services()
    raw_envelope = await _persist_selected_message(services)
    source_objects = InMemorySourceObjectRepository()
    source_files = InMemorySourceFileRepository()
    source_chunks = InMemorySourceChunkRepository()
    normalization = SourceNormalizationService(
        raw_events=services.raw_events,
        payload_store=services.payload_store,
        source_objects=source_objects,
        source_files=source_files,
        relationship_seeds=InMemoryRelationshipSeedRepository(),
        source_object_publisher=SourceObjectPublisher(services.event_bus),
        source_file_publisher=SourceFilePublisher(services.event_bus),
    )
    await normalization.handle_raw_event_persisted(raw_envelope)
    source_envelope = services.event_bus.list_events()[1]
    chunking = ChunkingService(
        source_objects=source_objects,
        source_files=source_files,
        source_chunks=source_chunks,
        chunker=SourceAwareChunker(load_retrieval_config().chunking),
        publisher=SourceChunkPublisher(services.event_bus),
    )
    first = await chunking.handle_source_object_upserted(source_envelope)
    second = await chunking.handle_source_object_upserted(source_envelope)
    source_object_id = source_envelope.subject.id

    assert first.published_count == 1
    assert second.published_count == 0
    assert len(source_chunks.list_by_source_object("ws_1", source_object_id)) == 1


async def _persist_selected_message(services: object):
    body = {
        "team_id": "T123",
        "event_id": "EvPhase85",
        "event_time": 1_700_000_000,
        "event": {
            "type": "message",
            "channel": "C123",
            "user": "U123",
            "ts": "1700000000.000100",
            "text": MESSAGE_TEXT,
            "files": [
                {
                    "id": "F123",
                    "name": "secret-roadmap.png",
                    "url_private": "https://files.slack.com/private",
                }
            ],
            "links": [{"url": "https://private.example/doc", "domain": "example.com"}],
        },
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    headers = signed_headers(body, "test-secret")
    result = await services.webhooks.handle(
        workspace_id="ws_1",
        body=raw,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )
    assert result.status == "persisted"
    return services.event_bus.list_events()[0]


def _retrieval_service(
    source_chunks: InMemorySourceChunkRepository, event_bus: InMemoryEventBus
) -> RetrievalService:
    return RetrievalService(
        config=load_retrieval_config(),
        source_chunks=source_chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(event_bus),
    )


def _embedding_worker(
    source_chunks: InMemorySourceChunkRepository, event_bus: InMemoryEventBus
) -> EmbeddingWorkerSkeleton:
    return EmbeddingWorkerSkeleton(
        EmbeddingService(
            source_chunks=source_chunks,
            embeddings=InMemoryEmbeddingRecordRepository(),
            provider=DeterministicEmbeddingProvider(
                dimensions=16,
                version=load_retrieval_config().embeddings.version,
            ),
            publisher=EmbeddingPublisher(event_bus),
        )
    )


def _event_payloads_are_content_free(event_bus: InMemoryEventBus) -> bool:
    payloads = [event.payload for event in event_bus.list_events()]
    text = str(payloads)
    return (
        MESSAGE_TEXT not in text
        and "secret-roadmap.png" not in text
        and "files.slack.com" not in text
        and "private.example" not in text
    )
