import json
from dataclasses import dataclass, replace
from typing import cast

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.config import Settings
from cortex.embeddings.gemini import GeminiEmbeddingProvider
from cortex.embeddings.profile import EmbeddingIndexProfile
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.qdrant import QdrantVectorIndex
from cortex.ingestion.payloads import FilePayloadStore
from cortex.permissions.scopes import InMemoryPermissionScopeRepository
from cortex.permissions.service import PermissionService
from cortex.retrieval.query import QueryPlanner
from cortex.retrieval.vector import VectorRetriever
from cortex.runtime.durable import DurableContextRetrieval
from cortex.workers.factory import SqlPipelineDispatcher


@dataclass
class _UnusedSessionFactory:
    def __call__(self) -> object:
        raise AssertionError("not used while composing a profile")


def test_real_profile_uses_compatible_document_query_embedding_contract() -> None:
    profile = EmbeddingIndexProfile.from_settings(
        Settings(
            cortex_env="test",
            cortex_embedding_mode="real",
            gemini_api_key="test-key",
            qdrant_url="http://localhost:6333",
        )
    )

    document = profile.document_embedder()
    query = profile.query_embedder()

    assert isinstance(document, GeminiEmbeddingProvider)
    assert isinstance(query, GeminiEmbeddingProvider)
    assert (document.model, document.version, document.dimensions) == (
        query.model,
        query.version,
        query.dimensions,
    )
    assert document.task_type == "RETRIEVAL_DOCUMENT"
    assert query.task_type == "RETRIEVAL_QUERY"
    assert profile.collection.endswith("gemini-embedding-2-gemini2-1536-v1-1536")
    assert "test-key" not in repr(profile)


def test_durable_retrieval_and_pipeline_share_exact_profile_collection(
    tmp_path,
) -> None:
    settings = Settings(
        cortex_env="test",
        qdrant_url="http://localhost:6333",
        cortex_embedding_mode="deterministic",
    )
    dispatcher = SqlPipelineDispatcher(
        session_factory=cast(async_sessionmaker[AsyncSession], _UnusedSessionFactory()),
        payload_store=FilePayloadStore(tmp_path),
        event_bus=InMemoryEventBus(),
        settings=settings,
    )
    retrieval = DurableContextRetrieval(
        session_factory=cast(async_sessionmaker[AsyncSession], _UnusedSessionFactory()),
        settings=settings,
        vector_index=cast(QdrantVectorIndex, object()),
        permission_service_factory=lambda _session, _workspace_id: PermissionService(
            InMemoryPermissionScopeRepository()
        ),
    )

    assert dispatcher.embedding_profile == retrieval.embedding_profile
    assert retrieval.vector_collection == dispatcher.embedding_profile.collection
    assert retrieval.vector_collection != "fixture-cortex-dev"


class _NoResultVectorIndex:
    async def search_filtered(self, *args, **kwargs) -> list[dict[str, object]]:
        return []


async def test_real_profile_uses_distinct_compatible_document_and_query_calls() -> None:
    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(cast(dict[str, object], json.loads(request.content)))
        return httpx.Response(200, json={"embedding": {"values": [0.1] * 1536}})

    profile = EmbeddingIndexProfile.from_settings(
        Settings(
            cortex_env="test",
            cortex_embedding_mode="real",
            gemini_api_key="test-key",
            qdrant_url="http://localhost:6333",
        )
    )
    transport = httpx.MockTransport(handler)
    document = replace(
        cast(GeminiEmbeddingProvider, profile.document_embedder()),
        transport=transport,
    )
    query = replace(
        cast(GeminiEmbeddingProvider, profile.query_embedder()),
        transport=transport,
    )

    document_output = await document.embed("hash-document", "document body")
    retriever = VectorRetriever(
        vector_index=_NoResultVectorIndex(),  # type: ignore[arg-type]
        source_chunks=object(),
        embedder=query,
        collection=profile.collection,
    )
    await retriever.retrieve(
        workspace_id="workspace_1",
        plan=QueryPlanner().plan(query="find service ownership"),
        limit=5,
    )

    assert len(document_output.vector) == profile.dimensions
    assert all("taskType" not in request for request in requests)
    assert requests[0]["content"] == {
        "parts": [{"text": "title: none | text: document body"}]
    }
    assert requests[1]["content"] == {
        "parts": [
            {"text": "task: search result | query: find service ownership"}
        ]
    }
